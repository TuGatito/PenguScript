# 🐧 Auditoría de imports y tamaño de `bundle.c`

> **Proyecto:** PenguScript **2.16.5** · **Fecha:** 23 de octubre de 2026
> **Alcance:** cómo se resuelven e incluyen los `import`, qué se emite en `build/bundle.c`, qué se puede podar, y qué bugs/fugas aparecen por el camino.
> **Estado:** auditoría **sin cambios de código**. Todo lo que sigue se midió sobre esta copia del repositorio.
>
> **Actualización (23 oct 2026):** las fases **0, 1 y 4** ya están implementadas
> (**2.17.0** y **2.18.0**; ver `CHANGELOG.md`). La fase 2 quedó absorbida por el
> worklist de la fase 1. En 2.18.0 los helpers `derive` se podan por defecto y
> `--prune-types` añade la poda opt-in de tipos/constantes: `cipher` 1 función
> queda en **11,4 KB** (6,7 KB con el flag), `petitio` sin usar en **15,9 KB**
> (4,4 KB) y `cipher`/`petitio` ya no arrastran `derive` ni tipos muertos.
> Queda la fase **3** (módulos de usuario) y la poda nativa de includes/links
> (conservadora por el C glue). **B4** se cerró en **2.19.0**, **B10** en
> **2.20.0** y **B11/B12** en **2.21.0** (`--no-line-markers` 4–13 % e higiene
> de docs; gates ya por import + prefijo C).

---

## 📌 TL;DR — lo que necesitas saber en 90 segundos

| Pregunta | Respuesta corta |
|---|---|
| ¿Ya se puede importar `std.spark` y que solo entre `println`? | ✅ **Sí.** `import std.spark` + `spark.println` produce **3 de 67 weaves** y un `bundle.c` de **3,7 KB** (96 líneas). |
| ¿Funciona igual para todo el `std`? | ❌ **No.** `import std.cipher` usando **una** función genera **581,7 KB**; `import std.petitio` sin usar nada, **782,2 KB**; `import std.json` sin usar nada, **142,2 KB**. Entre el **80 % y el 90 %** de esos bundles es código inalcanzable. |
| ¿Por qué? | 🧬 Las **instancias monomorfizadas** de genéricos se recolectan *todas* y se marcan como raíces: 546 de 580 weaves en `cipher`, 591 de 740 en `petitio`. |
| ¿Y los módulos del usuario? | ❌ **Nunca se podan.** *Todas* sus funciones son raíces (`pengu_dce.py`), aunque el ejecutable no las llame. |
| ¿Y tipos, constantes y `derive`? | ❌ Tampoco se podan. En un `import std.petitio` sin usar, **11,9 KB de 15,1 KB** que quedarían tras podar funciones son tipos, forward decls y constantes. |
| ¿Hay bugs? | 🔴 **Sí, cuatro importantes:** el DCE **se desactiva solo** en instalaciones FHS/pip; una **expresión por defecto** que llama a un weave de `std` hace que el DCE lo pode y **la compilación C falle**; dos módulos con un tipo del mismo nombre generan **C inválido** (y `pengu check` dice “Clean”); una **función genérica usada como valor** emite el nombre de la plantilla y no compila. |
| ¿Es factible optimizarlo? | ✅ **Sí, y sin tocar la semántica.** El 90–99 % del beneficio viene de una sola idea: **alcanzabilidad por símbolo C real** con un *worklist*, en vez del escaneo de nombres Pengu actual. |
| Techo medido | `cipher` con una función: **581,7 KB → ~10,5 KB** (−98,2 %); `petitio` sin usar: **782,2 KB → ~15,1 KB** (−98,1 %); `bench_stdlib_ops`: **568,9 KB → ~9,9 KB** (−98,3 %). Tiempo de `gcc -O2`: **9,2 s → 0,18 s**. |

> [!IMPORTANT]
> **Veredicto:** el DCE actual tiene la forma correcta (registros con `name`/`c_name`/`refs`/`filepath`), pero su política es “podar por nombre y solo `std`/`lib`”. El salto grande no requiere reescribir el compilador: requiere cambiar **qué es una raíz** y **cómo se demuestra que algo se usa**. El plan de 6 fases está en [§6](#-6-diseño-propuesto-cómo-hacerlo-bien).

---

## 🗂️ Índice

1. [TL;DR](#-tldr--lo-que-necesitas-saber-en-90-segundos)
2. [Metodología](#-2-metodología)
3. [Cómo funciona hoy](#-3-cómo-funciona-hoy-el-pipeline-de-imports-y-dce)
4. [Mediciones](#-4-mediciones)
5. [Hallazgos: bugs y fugas](#-5-hallazgos-bugs-y-fugas)
6. [Diseño propuesto](#-6-diseño-propuesto-cómo-hacerlo-bien)
7. [Plan de pruebas](#-7-plan-de-pruebas-y-ci)
8. [Riesgos](#-8-riesgos-y-mitigaciones)
9. [Impacto esperado](#-9-impacto-esperado)
10. [Roadmap sugerido](#-10-roadmap-sugerido)
11. [Checklist de aceptación](#-11-checklist-de-aceptación)
12. [Apéndices](#-12-apéndices)

---

## 🧪 2. Metodología

### 2.1 Entorno

| Dato | Valor |
|---|---|
| PenguScript | `2.16.5` (`VERSION`, `pengu_parser.pengu_version`) |
| SO | Linux 7.2.11 (CachyOS), x86_64 |
| Python | 3.14.8 (el del `.venv` del repo) |
| `gcc` | 16.2.1 |
| `tcc` | 0.9.28rc (bundleado en `build/tcc-dist/…`) |
| CPUs | 36 |

### 2.2 Herramientas de medida

| Qué | Cómo |
|---|---|
| Bundle y su tamaño | `pengu expand script.pengu -o out.c` (misma fase de codegen que `run`/`build`, sin compilar C) |
| Bundle con/sin DCE | `PENGU_NO_DCE=1 pengu expand ...` (el flag `--no-dce` existe en `build`/`run`/`time`, no en `expand`) |
| Secciones del bundle | Parseo de los marcadores `/* … * … */` que emite `pengu_codegen` |
| Código muerto real | Analizador propio en Python: extrae **definiciones de funciones C**, construye el grafo de llamadas directas y calcula alcanzabilidad desde `main`/`pengu_main` |
| Coste en C | `gcc -c -O2 -std=c11 …` sobre el bundle (solo compilación, sin enlazar) |
| Binario final | `pengu run/build`, `strip`, `nm`, `-Wl,-Map` |
| Fases del compilador | `pengu time script.pengu` |

> [!NOTE]
> **Caveat 1 — el analizador de alcanzabilidad es directo.** Cuenta llamadas `f(...)`, no llamadas por puntero. En los programas medidos no hay punteros a función entre las funciones muertas; en el diseño propuesto (§6) la implementación real **sí** maneja punteros, `@export`, tests y C glue.
>
> **Caveat 2 — los bytes dependen de la longitud de las rutas de `#line`.** `pengu expand -o dir/out.c` emite rutas relativas al directorio de salida. Por eso un mismo programa expandido desde otro `cwd` puede variar unos KB. Todas las comparaciones de esta auditoría se hicieron dentro del mismo directorio; los porcentajes son lo relevante, no el byte exacto.
>
> **Caveat 3 — el `build/bundle.c` del repo es un bundle de tests.** Se usa solo para composición de secciones y para el peso de los `#line`, no para el % de código muerto (sus raíces son los tests, no `main`).

### 2.3 Reproducción

Cada hallazgo de §5 trae su repro. Los comandos generales están en el [Apéndice A](#a-comandos-de-reproducción).

---

## 🧱 3. Cómo funciona hoy: el pipeline de imports y DCE

### 3.1 Diagrama

```
                    ┌──────────────────────────────────────────────┐
  main.pengu ──────▶│ resolve_imports  (DFS + orden topológico)    │
  import std.X      │  std/*.pengu + src/**.pengu + lib/**.pengu   │
                    └──────────────────────┬───────────────────────┘
                                           │  List[str] de rutas absolutas
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ PenguParser (Lark) → AST por módulo          │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ PenguChecker + TypeInferrer                  │
                    │  · registra runes/omens/aliases/consts       │
                    │  · MONOMORFIZA todos los genéricos del       │
                    │    cierre transitivo (aunque no se usen)     │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ PenguCodegen.collect_declarations             │
                    │  · weaves reales  (filepath real)             │
                    │  · instancias genéricas (filepath = ".")      │
                    │  · tipos, consts, includes, links, tests      │
                    └──────────────────────┬───────────────────────┘
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ DCE  prune_weaves()  ← ¡solo aquí se poda!   │
                    │  · raíces: todo weave no-std/lib              │
                    │  · raíces: TODA instancia (subst_map)         │
                    │  · raíces: @export, main                      │
                    │  · cierre por NOMBRES del AST (no por símbolo)│
                    └──────────────────────┬───────────────────────┘
                                           ▼
   forward decls → tipos → derived → consts → prototipos → lambdas →
   definiciones (orden topológico) → tests (si --test) → entry point
                                           ▼
                                      bundle.c
```

### 3.2 Qué poda el DCE actual y qué no

| Artefacto | ¿Se poda hoy? | Notas |
|---|---|---|
| Weave de `std/` o `lib/` no referenciado | ✅ Sí | Por nombre; conservador |
| Weave de módulo de usuario (`src/`) | ❌ No | **Todas** son raíces |
| Weave de `.d.pengu` | ❌ No | El archivo entero es binding |
| Instancia monomorfizada (`subst_map`) | ❌ No | Se mantiene **siempre** (`pengu_dce.py:205`) |
| Plantilla genérica (`shard`) | ❌ No | No se emite sola; sus instancias sí |
| `@export(...)` | ❌ No | Por contrato FFI |
| `main` / `pengu_main` | ❌ No | Raíz |
| Runes / echos / omens / aliases / `seal` | ❌ No | “Son baratos y podarlos cambia layouts/ABI” (decisión actual) |
| Constantes (`const`) | ❌ No | Incluidas las de módulos no usados |
| Implementaciones derivadas (`Par`, `Ordo`, `Imago`, `Nexus`, …) | ❌ No | Se emiten para **todos** los runes que derivan |
| Prototipos | ✅ Sí (indirecto) | Se generan de `self.weaves` ya podado |
| `declare` / `include` / `link` / `ldflag` | ❌ No | Se agregan por módulo importado |
| Lambdas | ❌ No | Se registran **antes** del DCE y se emiten todas |
| Refs de `test` blocks | ❌ No (fuera de `--test`) | Ver [B5](#-b5--los-test-blocks-de-un-build-normal-mantienen-código-de-std-vivo) |

### 3.3 Archivos y líneas clave

| Qué | Dónde |
|---|---|
| Raíz “repo” para decidir si un archivo es `std/` | `pengu_parser/pengu_dce.py:38` |
| `is_prunable_module` (solo `std/` y `lib/`) | `pengu_parser/pengu_dce.py:45-82` |
| Recolección de referencias (NOMBRES del AST) | `pengu_parser/pengu_dce.py:97-142` |
| `prune_weaves` (cierre + raíces) | `pengu_parser/pengu_dce.py:185-260` |
| Instancias siempre conservadas | `pengu_parser/pengu_dce.py:205-210` |
| Invocación del DCE y raíces de tests | `pengu_parser/pengu_codegen/bundle.py:85-106` |
| Marcador `/* Dead-code elimination … */` | `pengu_parser/pengu_codegen/bundle.py:162-169` |
| Feature gates desde `import_order` | `pengu_parser/pengu_codegen/bundle.py:226-248` |
| Recolección de instancias (`filepath="."`) | `pengu_parser/pengu_codegen/declarations.py:196-221` |
| `refs` de un weave = solo `body_stmts` | `pengu_parser/pengu_codegen/declarations.py:594` |
| `refs` de una instancia = solo `body_stmts` | `pengu_parser/pengu_codegen/declarations.py:837` |
| Nombre C de un tipo = `insignia + nombre` | `pengu_parser/pengu_codegen/declarations.py:241-263` |
| Registro global de tipos (last-wins) | `pengu_parser/pengu_checker.py:1407` |
| `emit_line_markers` fijo en `True` | `pengu_parser/pengu_codegen/main.py:185` |
| `test` blocks de std excluidos salvo entry | `pengu_parser/pengu_codegen/declarations.py:79-101` |

---

## 📊 4. Mediciones

### 4.1 El caso bueno: `spark.println`

```pengu
# hello.pengu
import std.spark

weave main into int:
    calling spark.println with "hello"
    return 0
```

```console
$ pengu expand hello.pengu -o hello.c
wrote hello.c (96 lines, 3758 bytes)
```

```c
/* Dead-code elimination: pruned 64 of 67 std/lib weave(s), 67 -> 3 */
...
void spark_pengu_println(PenguString s) { … fwrite … fputc('\n', stdout); }
PENGU_MAYBE_UNUSED static inline void spark_println(PenguString s) {
  pengu_frame_push("spark_println", "…/std/spark.pengu", 495);
  spark_pengu_println(s);
  pengu_frame_pop();
}
PENGU_MAYBE_UNUSED static inline int32_t pengu_main(void) { … }
```

✅ **Esto es exactamente lo que pedías** y ya funciona: entran `spark.println`, su `antiquus` `pengu_println` y `main`. Nada más.

| Programa | Líneas | Bytes | DCE |
|---|---:|---:|---|
| `main` vacío (piso del bundle) | 69 | 2.456 | — |
| `spark.println` | 96 | 3.758 | 64/67 → 3 |
| `scrolls.len` (una llamada) | 104 | 4.168 | 284/287 → 3 |
| `hello` **sin** DCE (`PENGU_NO_DCE=1`) | 924 | 42.885 | — |

> El “piso” de ~2,4 KB es el prólogo, el `entry point` y el `#include "pengu_runtime.h"`; no se puede bajar sin tocar el runtime.

### 4.2 El coste de importar un módulo `std` **sin usarlo**

Cada fila es un script con `import std.<m>` + `weave main into int: return 0`, expandido con `pengu expand` en el mismo directorio. Es, literalmente, **lo que cuesta un import que no usas**.

#### 🟢 Módulos “sanos” (< 10 KB): el DCE hace su trabajo

| Módulo | Bundle | Weaves kept |
|---|---:|---:|
| `spark` | 2.879 B (2,8 KB) | 1 |
| `rites` | 3.015 B (2,9 KB) | 1 |
| `scrolls` | 3.031 B (3,0 KB) | 1 |
| `web` | 3.044 B (3,0 KB) | 1 |
| `bitset` | 4.467 B (4,4 KB) | 1 |
| `builder` | 4.686 B (4,6 KB) | 1 |
| `ffi` | 5.547 B (5,4 KB) | 7 |
| `lingua` | 6.183 B (6,0 KB) | 1 |
| `sourcemap` | 6.954 B (6,8 KB) | 1 |
| `regulus` | 7.468 B (7,3 KB) | 1 |

#### 🟡 Módulos “medios” (10–100 KB)

| Módulo | Bundle | Kept |
|---|---:|---:|
| `functor` | 19.062 B (18,6 KB) | 28 |
| `compass` | 100.717 B (98,4 KB) | 111 |
| `oracle` | 100.355 B (98,0 KB) | 111 |
| `filum` | 101.470 B (99,1 KB) | 111 |
| `ward` | 105.805 B (103,3 KB) | 119 |
| `littera` | 105.958 B (103,5 KB) | 119 |
| `logica` | 105.950 B (103,5 KB) | 119 |
| `trial` | 106.092 B (103,6 KB) | 119 |
| `chronicle` | 106.423 B (103,9 KB) | 111 |
| `fractio` | 112.566 B (109,9 KB) | 135 |
| `memoria` | 119.542 B (116,7 KB) | 151 |
| `arena` | 122.402 B (119,5 KB) | 152 |
| `numerus` | 127.072 B (124,1 KB) | 165 |
| `integrum` | 148.838 B (145,3 KB) | 192 |
| `json` | 150.525 B (147,0 KB) | 164 |
| `arithmancy` | 164.741 B (160,9 KB) | 223 |
| `diagnostic` | 173.308 B (169,2 KB) | 171 |
| `lot` | 173.821 B (169,7 KB) | 232 |
| `jsonrpc` | 182.809 B (178,5 KB) | 175 |

#### 🔴 Módulos “pesados” (> 100 KB): aquí está la fuga

| Módulo | Bundle | Kept | Instancias kept |
|---|---:|---:|---:|
| `atlas` | 392.379 B (383,2 KB) | 391 | 357 |
| `coven` | 501.806 B (490,0 KB) | 576 | 520 |
| `archivum` | 611.523 B (597,2 KB) | 575 | 541 |
| `tally` | 610.643 B (596,3 KB) | 575 | 541 |
| `invoke` | 613.637 B (599,3 KB) | 577 | 541 |
| `ledger` | 616.035 B (601,6 KB) | 577 | 541 |
| `compressus` | 621.570 B (607,0 KB) | 579 | 541 |
| `cipher` | 625.699 B (611,0 KB) | 580 | 546 |
| `whisper` | 651.987 B (636,7 KB) | 609 | 541 |
| `loom` | 671.388 B (655,7 KB) | 670 | 581 |
| `petitio` | 834.069 B (814,5 KB) | 740 | 591 |

> [!WARNING]
> **Un `import` que no usas puede añadir ~800 KB a `bundle.c`.** `petitio` es el peor caso porque su cierre transitivo arrastra `json`, `scrolls`, `compass`, `atlas`, `builder`, `oracle`, `archivum`, `chronicle`, `ffi` y `arena`, y **cada** módulo aporta sus propias instancias genéricas.

### 4.3 Programas que usan poco

| Programa | Qué hace | Bundle | Kept | Muerto (grafo C) |
|---|---|---:|---:|---:|
| `hello.pengu` | `spark.println` | 3.758 B (3,7 KB) | 3/67 | 0 % |
| `s1.pengu` | `scrolls.len` | 4.168 B (4,1 KB) | 3/287 | 0 % |
| `k1.pengu` | `import std.json`, nada | 145.588 B (142,2 KB) | 164/565 | **80,3 %** |
| `ci1.pengu` | `cipher.encode_base64` (1 llamada) | 595.666 B (581,7 KB) | 582/1500 | **89,4 %** |
| `pt1.pengu` | `import std.petitio`, nada | 800.984 B (782,2 KB) | 740/1909 | **88,1 %** |
| `bench_stdlib_ops` | `tally.sum`, `tally.max_val`, `println` | 582.533 B (568,9 KB) | 579/1059 | **89,3 %** |
| `bench_loom_ops` | 5 llamadas a `loom` | 648.797 B (633,6 KB) | 678/1433 | **87,2 %** |
| `bench_atlas_ops` | 4 llamadas a `atlas` | 378.454 B (369,6 KB) | 396/862 | **85,9 %** |
| `bench_cipher_ops` | 2 llamadas a `cipher` | 601.017 B (586,9 KB) | 586/1500 | **88,6 %** |
| `bench_scrolls_ops` | 4 llamadas a `scrolls` | 18.214 B (17,8 KB) | 18/287 | **11,0 %** ✅ |

**Lectura:** cuando el módulo es “plano” (sin genéricos, como `scrolls`), el DCE deja el bundle casi mínimo. Cuando el módulo tiene `shard`/`enchanting` genérico (`cipher`, `tally`, `loom`, `atlas`, `petitio`…), el bundle explota **aunque solo llames a una función**.

### 4.4 ¿Dónde está exactamente el peso?

Bytes por sección (mismo `pengu expand`, mismo directorio):

| Sección | `hello` | `k1` (json sin usar) | `ci1` (cipher 1 fn) | `pt1` (petitio sin usar) |
|---|---:|---:|---:|---:|
| Forward decls | 306 | 1.800 | 1.762 | 3.097 |
| Type definitions | 0 | 2.316 | 1.668 | 4.884 |
| Derived concepts | 0 | 26.862 | 14.579 | 52.298 |
| Global constants | 303 | 1.584 | 1.633 | 3.873 |
| Function prototypes | 369 | 9.107 | 31.846 | 41.511 |
| Function definitions | 1.263 | 102.275 | 542.511 | 693.467 |
| Entry point | 577 | 577 | 577 | 577 |
| **Total** | **3.758** | **145.588** | **595.666** | **800.984** |

Conclusión:
- En `ci1` y `pt1`, **las definiciones son el 90–91 %** del bundle, y de ellas el 89 % es inalcanzable.
- En `k1` (json sin usar) las definiciones siguen siendo el 70 %, pero **los `derive` (26,9 KB) y los prototipos (9,1 KB)** son un porcentaje llamativo: se emiten para tipos que nadie usa.
- Los **prototipos** son ~55 B por weave; con 141 instancias muertas son ~9 KB solo de firmas muertas.

### 4.5 `#line`: un 12–23 % del bundle que no es código

| Bundle | `#line` bytes | % del total |
|---|---:|---:|
| `hello.c` | 498 | 13,3 % |
| `k1.c` | 23.147 | 15,9 % |
| `ci1.c` | 113.194 | 19,0 % |
| `bench_stdlib_ops.c` | 112.080 | 19,2 % |
| `pt1.c` | 181.609 | 22,7 % |
| `build/bundle.c` (repo) | 114.213 | 14,5 % |

Desactivando `emit_line_markers` (experimento con monkeypatch; no hay flag todavía):

| Bundle | Con markers | Sin markers | Ahorro |
|---|---:|---:|---:|
| `hello.c` | 3.758 B | 3.262 B | **−13 %** |
| `k1.c` | 145.588 B | 127.378 B | **−12 %** |
| `ci1.c` | 595.666 B | 513.204 B | **−13 %** |

> Los `#line` son valiosos para que los diagnósticos de C y las trazas de sanitizers apunten al `.pengu`. La recomendación no es quitarlos por defecto, sino **permitir apagarlos** en builds de release/CI o en targets de tamaño (WASM).

### 4.6 Tiempo de compilación: el coste real de la fuga

Compilación **solo C** (`gcc -c -O2 -std=c11`), sin enlazar:

| Bundle | Tiempo | Objeto `.o` |
|---|---:|---:|
| `hello.c` (3,7 KB) | 141 ms | 8,9 KB |
| `k1.c` (142 KB) | 1.499 ms | — |
| `ci1.c` (582 KB) | **9.152 ms** | **706 KB** |
| `pt1.c` (782 KB) | **10.321 ms** | — |
| `bench_stdlib_ops.c` (569 KB) | **8.758 ms** | — |

Fases del compilador (`pengu time`, gcc, `-O0`):

| Fase | `hello` | `ci1` |
|---|---:|---:|
| parse + check | 117,8 ms | 4.288 ms |
| codegen (Python) | 6,2 ms | 905 ms |
| C compiler + link | 108 ms | 1.188 ms |
| `bundle.c` | 3,7 KB | 581,7 KB |
| **total build** | **234,9 ms** | **6.394,8 ms** |

> Con TCC (el compilador por defecto de `pengu run`) el C compila en **33 ms**, pero el **codegen de Python sube a 1,1 s** y el chequeo a 2 s; además TCC **no hace `--gc-sections`**, así que el binario de desarrollo se queda con todo: `hello` 65 KB, `ci1` **774 KB** (295 KB tras `strip`). Con gcc release + `--gc-sections`, en cambio, `ci1` baja a **16,8 KB** de binario: la fuga duele sobre todo en `bundle.c`, en el `.o` y en el tiempo de `gcc`.

### 4.7 Cota de lo que se puede recuperar (simulación)

Simulación: se eliminaron del C generado todas las definiciones **inalcanzables desde `main`**, sus prototipos y sus `#line`; se dejaron tipos, consts y utilidades compartidas.

| Programa | Antes | Después | Ahorro | `gcc -O2` antes → después |
|---|---:|---:|---:|---:|
| `k1` (json sin usar) | 145.588 B | **8.486 B** | **−94,2 %** | 1.499 ms → **139 ms** |
| `ci1` (cipher 1 fn) | 595.666 B | **10.753 B** | **−98,2 %** | 9.152 ms → **176 ms** |
| `pt1` (petitio sin usar) | 800.984 B | **15.455 B** | **−98,1 %** | 10.321 ms → **131 ms** |
| `bench_stdlib_ops` | 582.533 B | **10.169 B** | **−98,3 %** | 8.758 ms → **351 ms** |

Composición de esos bundles “podados”:

| Sección | `k1_pruned` | `ci1_pruned` | `pt1_pruned` | `benchs_pruned` |
|---|---:|---:|---:|---:|
| Forward decls | 1.800 | 1.762 | 3.097 | 916 |
| Types | 2.316 | 1.668 | 4.884 | 808 |
| Derived | 262 | 249 | 286 | 249 |
| Consts | 1.584 | 1.633 | 3.873 | 666 |
| Prototypes | 260 | 427 | 260 | 460 |
| Definitions | 620 | 3.347 | 1.201 | 5.470 |
| Entry | 577 | 577 | 577 | 577 |
| **Total** | **8.486** | **10.753** | **15.455** | **10.169** |

**Dos conclusiones importantes:**

1. El grueso del ahorro es **podar funciones inalcanzables**, y dentro de ellas sobre todo **instancias genéricas** y **helpers derivados** (`static inline`).
2. Una vez podadas las funciones, lo que queda es **tipos + consts + forward decls**: entre el **24 %** (`benchs`) y el **77 %** (`pt1`) del bundle resultante. Podar tipos/consts es la segunda fase, y solo merece la pena cuando la primera ya está hecha.

---

## 🐞 5. Hallazgos: bugs y fugas

> [!NOTE]
> “Fuga” la uso en el sentido de **código o símbolos que se filtran al bundle** (size leaks). No he encontrado fugas de memoria **nuevas** atribuibles a los imports; las conocidas de temporales de string están documentadas en `docs/PERFORMANCE.md` y son ortogonales a esto.

### 🚦 Resumen

| ID | Severidad | Tipo | Hallazgo | Impacto medido |
|---|---|---|---|---|
| **B1** | 🔴 Alta | Fuga | El DCE **se desactiva solo** si `std/` no está bajo la raíz del repo (FHS, `PENGU_STD_DIR`, pip) | `hello`: 3,7 KB → **35,0 KB** (×9,5) |
| **B2** | 🔴 Alta | Fuga | Todas las **instancias genéricas** son raíces | 546/580 en `cipher`; 89 % de código muerto |
| **B3** | 🔴 Alta | **Bug** | Los **argumentos por defecto** no cuentan como referencias para el DCE | `pengu_len` podado → **falla la compilación C** |
| **B4** | 🔴 Alta | **Bug** | Tipos con el **mismo nombre en módulos distintos** colisionan; `pengu check` dice “Clean” | C inválido, o `E0041`/`E0046` con `json+cipher`, `diagnostic+sourcemap`, `invoke+json`, `petitio+jsonrpc`… |
| **B5** | 🟠 Media | Fuga | Los `test` blocks de un build **normal** mantienen vivos weaves de `std` | 7 weaves en vez de 1; +4,3 KB |
| **B6** | 🟠 Media | Fuga | Los **módulos del usuario nunca se podan** | 40 helpers / 1 usado → los 40 emitidos (+21 KB) |
| **B7** | 🟠 Media | Fuga | Tipos, consts, `derive` y lambdas **nunca se podan** | 24–77 % del bundle ya sin funciones muertas |
| **B8** | 🟠 Media | Precisión | El DCE es **por nombre Pengu**; nombres comunes mantienen weaves ajenos | +5 weaves / +2,8 KB con `len`, `values`… |
| **B9** | 🟠 Media | Fuga | Gates, `include` y `link` se deciden por **import**, no por uso | `filum` sin usar: gate=1, 99 KB, `-pthread` |
| **B10** | 🟡 Baja | **Bug** | Una **función genérica como valor** emite el nombre de la plantilla | `((int32_t (*)(int32_t))twice)` → no compila |
| **B11** | 🟡 Baja | Tamaño | `#line` es el 12–23 % y **no hay flag** para apagarlo | −12/−13 % al quitarlo |
| **B12** | 🟡 Baja | Higiene | Falta el test que el propio código referencia; docs y docstrings desactualizados | Deriva silenciosa |

---

### 🔴 B1 — El DCE se desactiva solo en instalaciones que no son el checkout

**Síntoma.** El bundle de `hello.pengu` pasa de 96 líneas a **923 líneas** y **no** lleva el marcador `/* Dead-code elimination … */`. No hay warning: el DCE simplemente no poda nada.

**Repro.**

```console
$ mkdir -p /tmp/fhs/share/pengu
$ cp -r std /tmp/fhs/share/pengu/std
$ PENGU_STD_DIR=/tmp/fhs/share/pengu/std pengu expand hello.pengu -o fhs_hello.c
wrote fhs_hello.c (923 lines, 35857 bytes)      # sin marcador DCE

$ pengu expand hello.pengu -o hello.c
wrote hello.c (96 lines, 3758 bytes)            # con marcador
```

También en un `run` real:

```console
$ PENGU_STD_DIR=/tmp/fhs/share/pengu/std pengu run hello.pengu --keep --no-cache
$ ls -l build/hello_run/bundle.c
37171 bytes
```

**Causa raíz.** `is_prunable_module()` decide que un archivo es `std/` comparándolo con dos raíces: `base_dir` del proyecto y `_REPO_ROOT` (`dirname(dirname(pengu_dce.py))`). En una instalación FHS el layout es `<prefix>/share/pengu/std/…`, mientras que el paquete Python puede vivir en `<prefix>/lib/python…/site-packages/` (pip) o dentro de `_MEIPASS` (onefile). En el primer caso, **ninguna** de las dos raíces coincide y todos los módulos se consideran “no podables”.

```python
# pengu_parser/pengu_dce.py:38, 68-82
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
...
roots = [base_dir, _REPO_ROOT]
for root in roots:
    rel = os.path.relpath(path, root) ...
    if rel.split("/", 1)[0] in ("std", "lib"): return True
return False
```

**Por qué importa.** El binario onefile de PyInstaller suele llevar `std/` dentro de `_MEIPASS`, así que el release oficial probablemente se salva; pero **`pip install`, FHS, `PENGU_STD_DIR` y cualquier empaquetado que resuelva `std` por `share/pengu/std` pierden el DCE entero**. Es un fallo silencioso: no hay diagnóstico, solo un bundle 10× más grande.

**Fix propuesto (pequeño y seguro).** Pasar las raíces reales de `std` al DCE:

```python
# pengu_parser/pengu_dce.py
from pengu_paths import std_dirs  # import perezoso, sin ciclo

def is_prunable_module(filepath, base_dir=None, std_roots=None):
    path = _norm(filepath)
    if path.endswith(".d.pengu"):
        return False
    # 1) Cualquier archivo que viva DENTRO de un std/ real (no su padre).
    roots = [str(p) for p in (std_roots or std_dirs())]
    if not std_roots:
        roots.append(os.path.join(_REPO_ROOT, "std"))   # checkout
    for std in roots:
        if path.startswith(_norm(std).rstrip("/") + "/"):
            return True
    # 2) lib/ y std/ del proyecto, anclados a base_dir (comportamiento actual).
    ...
```

o, mejor, calcular en `resolve_imports` el conjunto de rutas que son `std` y pasarlo a `prune_weaves(..., prunable_roots=...)`. Añadir un test que copie `std/` a un temporal, haga `monkeypatch.setenv("PENGU_STD_DIR", …)` y exija el marcador DCE.

---

### 🔴 B2 — Las instancias monomorfizadas son raíces: la fuga principal

**Síntoma.** Importar un módulo con genéricos (`shard`, `enchanting` genérico, contenedores) emite **todas** las instanciaciones que el checker creó para el cierre transitivo, aunque nada las llame.

**Evidencia.**

| Programa | Weaves kept (de N) | Instancias | % del bundle que es muerto |
|---|---:|---:|---:|
| `import std.cipher` (sin usar) | 580 (de 1500) | **546** | 89,7 % |
| `cipher.encode_base64` (1 llamada) | 582 (de 1500) | 546 | 89,4 % |
| `import std.petitio` (sin usar) | 740 (de 1909) | **591** | 88,1 % |
| `import std.tally` (sin usar) | 575 (de 1057) | 541 | 89,6 % |
| `import std.loom` (sin usar) | 670 (de 1428) | 581 | 88,3 % |
| `import std.atlas` (sin usar) | 391 (de 862) | 357 | 88,0 % |
| `import std.json` (sin usar) | 164 (de 565) | 141 | 80,3 % |

**Causa raíz.** Dos cosas se suman:

1. El checker monomorfiza **todo** el cierre transitivo, no solo lo alcanzable (es lo que permite type-checkear los módulos importados).
2. `collect_declarations` convierte **todas** esas instancias en weaves con `filepath="."`:

```python
# pengu_parser/pengu_codegen/declarations.py:196-221
for m_fn_name, (fn_ast, subst_map) in self.symbols.monomorphized_functions.items():
    ...
    self._collect_monomorphized_weave(m_fn_name, fn_ast, subst_map, None, filepath=".")
```

3. `prune_weaves` las conserva explícitamente como raíces:

```python
# pengu_parser/pengu_dce.py:205-210
if weave.get("subst_map") or weave.get("is_generic"):
    kept.append(weave)
    alive |= set(weave.get("refs") or ())
    continue
```

El comentario dice que “las instancias se crean durante la generación de cuerpos (después de este pase)”, pero la medición demuestra que **546/591/541 ya existen antes** del DCE, en la fase de colección. Las que se crean durante el codegen (`exprs.py:1471-1481`) son otro caso que el diseño debe cubrir.

> [!WARNING]
> **Quitar solo la guarda `if subst_map` no basta.** Aunque se eliminara, `is_prunable_module(".")` devuelve `False` (no está bajo `std/` ni `lib/`), así que las instancias seguirían entrando por la rama de “no podable” y seguirían siendo raíces. El fix tiene que tratar las instancias como **catálogo**, no como archivos, y decidir su emisión por alcanzabilidad (o darles un `filepath` de origen y marcarlas como sintéticas).

**Impacto.** No es un bug de correctitud, pero es la causa del 90 % del tamaño y de buena parte del tiempo de `gcc` y del codegen. Es la prioridad #1.

**Fix.** Catálogo + lista de emisión + worklist: las instancias siguen disponibles para resolver llamadas, pero **solo se traducen y emiten las que un cuerpo vivo referencia**. Detalle en [§6.3](#63-fase-1--alcanzabilidad-exacta-el-gran-win).

---

### 🔴 B3 — Argumentos por defecto: el DCE poda una función que sí se usa → build roto

**Síntoma.** Un weave con un valor por defecto que llama a otro weave de `std` compila “bien” (`pengu check` limpio), pero `pengu run`/`build` falla porque el DCE podó el weave llamado.

**Repro.**

```pengu
# src/u.pengu
import std.scrolls

weave measure with s as string is "abc", n as int is calling scrolls.len with "xy" into int:
    return n + 1
```

```pengu
# src/main.pengu
import u

weave main into int:
    return calling u.measure with "hello"
```

```console
$ pengu expand src/main.pengu -o bundle.c
wrote bundle.c (91 lines, 3522 bytes)
$ grep "Dead-code" bundle.c
/* Dead-code elimination: pruned 286 of 288 std/lib weave(s), 288 -> 2 */
$ pengu run src/main.pengu
… error: declaración implícita de la función ‘pengu_len’; ¿quiso decir ‘pengu_main’?
```

El C emitido contiene `pengu_len(…)` pero **no** la definición ni el prototipo de `pengu_len`.

**Causa raíz.** El DCE recolecta referencias **solo del cuerpo**:

```python
# pengu_parser/pengu_codegen/declarations.py:594
"refs": _dce_collect_refs(body_stmts),
```

Los valores por defecto viven en `weave["params"][i][2]` (nodos AST) y se traducen **en el call site**, pero no se escanean al recolectar. Lo mismo pasa con los defaults de métodos (`enchanting`) y con las instancias (`declarations.py:837`).

**Fix (inmediato).**

```python
defaults = [p[2] for p in params if len(p) >= 3 and p[2] is not None]
"refs": _dce_collect_refs(body_stmts) | _dce_collect_refs(defaults),
```

en `_collect_weave` **y** en `_collect_monomorphized_weave`. Añadir un test que compile y ejecute el programa de arriba.

> [!TIP]
> El diseño de [§6.3](#63-fase-1--alcanzabilidad-exacta-el-gran-win) elimina esta clase de bug de raíz: el default se traduce en el cuerpo del llamador, así que un worklist por símbolos C lo detecta **automáticamente**.

---

### 🔴 B4 — Colisiones de nombres de tipos entre módulos: C inválido con `check` limpio

> **✅ Implementado en 2.19.0.** El checker rechaza duplicados con `E0070`
> (`DuplicateTypeNameError`) en el mismo módulo o entre módulos importados, y
> los renombres del std (`cipher.CipherJsonValue`, `sourcemap.SourceSpan`,
> `invoke.CommandParser`, `jsonrpc…RpcRequest`, `HttpError.HttpIoError`,
> `HttpError.HttpOutOfMemory`, `RegexError.RegexOutOfMemory`) eliminan las
> colisiones que impedían importar todos los módulos juntos. Se verificó con
> `pengu check` y compilación C de un programa que importa **todo** el std.
> La solución elegida es el **diagnóstico claro** (opción 1/2 del diseño), no
> el mangling por módulo (opción 3), que queda para 3.0 si se quiere permitir
> `a.Config` + `b.Config`.

**Síntoma.** Dos módulos (std o del usuario) declaran un tipo con el mismo nombre. El checker no lo detecta; el codegen emite **un solo** `struct` con el layout del último registrado; el C resultante no compila (o el tipo “pertenece” al módulo equivocado).

**Repro A — dos módulos de usuario.**

```pengu
# src/a.pengu
rune Config:
    value as int

weave make_config into Config:
    return with value is 1
```

```pengu
# src/b.pengu
rune Config:
    value as string

weave make_config into Config:
    return with value is "b"
```

```pengu
# src/main.pengu
import a
import b

weave main into int:
    var ca as a.Config is calling a.make_config
    var cb as b.Config is calling b.make_config
    return ca.value
```

```console
$ pengu check
     Clean no errors found in 0.16s

$ pengu expand src/main.pengu -o bundle.c
wrote bundle.c (104 lines, 3729 bytes)     # ¡pero el C es inválido!

$ gcc -fsyntax-only bundle.c
… error: la inicialización de ‘char *’ desde ‘int’ crea un puntero desde un entero
… error: tipos incompatibles en la inicialización del tipo ‘int32_t’ usando el tipo ‘PenguString’
```

El bundle emite **un único** `struct Config` (el de `b`, que se registró después) y `a_make_config` intenta inicializarlo con un `int`.

**Repro B — std: `diagnostic.Span` + `sourcemap.Span`.**

```pengu
import std.diagnostic
import std.sourcemap

weave main into int:
    var d as diagnostic.Span is with file is "a.pengu", start_line is 1, start_col is 1, end_line is 1, end_col is 2, start_byte is 0, end_byte is 1
    var p1 as sourcemap.Position is with line is 1, col is 1
    var p2 as sourcemap.Position is with line is 1, col is 2
    var s as sourcemap.Span is with start is p1, end is p2
    if d.start_line == s.start.line:
        return 1
    return 0
```

```console
$ pengu check span1.pengu
     Clean no errors found in 3.40s

$ pengu expand span1.pengu -o span1.c
wrote span1.c (4768 lines, 171243 bytes)

$ gcc -fsyntax-only span1.c
… error: ‘Span’ no tiene un miembro llamado ‘file’
… error: ‘Span’ no tiene un miembro llamado ‘start_line’
```

**Repro C — std: `json` + `cipher`.**

```pengu
import std.json
import std.cipher

weave main into int:
    var v as json.JsonValue is calling json.JsonValue.null_value
    var r as maybe json.JsonValue is calling v.get with "k"
    …
```

```console
$ pengu check coll1.pengu
     Clean no errors found (15 warning(s))

$ pengu expand coll1.pengu
coll1.pengu:1:1 [E0041] 'Null' is not a field or variant of omen 'JsonValue'
```

Y sin `json.JsonValue` explícito, el codegen de `JsonValue.get` (que usa `judge … when Obj with entries`) revienta con `E0005: Cannot iterate over non-collection type 'None'` porque `entries` se resuelve contra la omen equivocada.

**Repro D — “importar todo el std”.**

```console
$ pengu check allstd.pengu
… [E0046] Omen variant name 'OutOfMemory' is used by both omen 'HttpError' and omen 'RegexError'
… [E0046] Omen variant name 'Request' of omen 'JsonRpcMessage' collides with the top-level symbol 'Request'
     Errors found in 19.94s
```

**Causa raíz.** El `SymbolTable` guarda los tipos en un diccionario **global por nombre**:

```python
# pengu_parser/pengu_checker.py:1407
self.symbols.runes[r_name] = rune_t     # el último gana
```

y el nombre C de un tipo es solo `insignia + nombre` (sin prefijo de módulo):

```python
# pengu_parser/pengu_codegen/declarations.py:246
c_name = f"{prefix}{name}" if prefix else name
```

Las funciones **sí** reciben prefijo de módulo cuando no son del entry (`a_make_config`, `b_make_config`); los tipos no. Además, la variante de una omen ocupa su nombre corto en el scope global, y eso choca con runes de otros módulos (`JsonRpcMessage.Request` vs `petitio.Request`).

**Evidencia de que ya se topó con esto.** `CHANGELOG.md:853`:

> `std.diagnostic` no longer imports `std.sourcemap`, whose `Span` rune collided with `std.diagnostic`'s `Span`; the two line helpers are internal C bridges.

Es decir: se resolvió **quitando un import**, no el problema general.

**Impacto.** Cualquier usuario que importe `diagnostic` + `sourcemap`, `json` + `cipher`, `invoke` + `json`, `petitio` + `jsonrpc`/`regulus`, o que tenga dos módulos con un `Config`/`Error`/`State` propio, obtiene C inválido o un error de codegen. `pengu check` no lo ve, y el mensaje de `gcc` apunta a la línea del `.pengu` pero no explica la causa.

**Fix.** Tres niveles (detalle en [§6.10](#610-track-b4--colisiones-de-tipos-entre-módulos)):

1. **Inmediato:** diagnóstico `E00xx` de “tipo duplicado entre módulos del mismo cierre”, con ayuda para renombrar o usar `insignia`. Convierte C inválido en un error claro, pero primero hay que arreglar el std o romperá combinaciones legítimas.
2. **Corto plazo:** renombrar las colisiones conocidas del std (`cipher.JsonValue`, `sourcemap.Span`, `invoke.Parser`, variantes `Request`/`OutOfMemory`) con alias de compatibilidad donde se pueda.
3. **Bien:** identidad de tipo por módulo (`(módulo, nombre)`), resolución por alias de import y, para tipos de usuario sin `insignia`, prefijo de módulo en el nombre C (igual que las funciones). Es invasivo: toca checker, infer, codegen, `CTypeMapper`, `derived_gen` y los bindings. Merece su propio diseño, pero es la solución de fondo.

> [!NOTE]
> Una variante silenciosa: si los dos tipos tienen **exactamente el mismo layout C**, el programa “funciona” por accidente y el checker cree que son tipos distintos. Eso es peor que el error, porque no hay señal.

---

### 🟠 B5 — Los `test` blocks de un build normal mantienen código de `std` vivo

**Síntoma.** Un `test` que llama a una función de `std` hace que esa función se emita en el bundle de producción, aunque el bloque de test **no se emita** (solo se emite con `--test`).

**Repro.**

```pengu
import std.scrolls

test "len works":
    let s as string is "abc"
    let n as int is calling scrolls.len with s
    if n != 3:
        calling scrolls.upper with s

weave main into int:
    return 0
```

```console
$ pengu expand testleak.pengu -o testleak.c
wrote testleak.c (168 lines, 6810 bytes)
$ grep "Dead-code" testleak.c
/* Dead-code elimination: pruned 280 of 287 std/lib weave(s), 287 -> 7 */
```

Se emiten `pengu_len` **y** `pengu_upper` (7 weaves) aunque `main` no hace nada (el piso es 1 weave / 2,4 KB).

**Causa raíz.**

```python
# pengu_parser/pengu_codegen/bundle.py:90-96
extra_roots: Set[str] = set()
for test in self.tests:
    extra_roots |= _dce_collect_refs(test.get("body_stmts") or [])
kept, dropped = prune_weaves(self.weaves, extra_refs=extra_roots, base_dir=self.base_dir)
```

Se añaden **siempre**, sin mirar `is_test`. Los tests de std se excluyen en `collect_declarations` (`declarations.py:79-101`), pero los de módulos de usuario sí se recogen, y sus referencias se convierten en raíces del build normal.

**Fix.** Pasar `is_test` y añadir `extra_roots` solo cuando el bundle sea de test:

```python
if is_test:
    for test in self.tests:
        extra_roots |= _dce_collect_refs(test.get("body_stmts") or [])
```

**Impacto.** Proporcional al tamaño de la suite. Un proyecto con tests que usan `json`/`petitio` mantiene vivos helpers (e instancias) solo por los tests. Es una fuga silenciosa y fácil de arreglar.

---

### 🟠 B6 — Los módulos del usuario nunca se podan

**Síntoma.** En un ejecutable, **todas** las funciones de `src/` se emiten, se llamen o no.

**Repro.**

```pengu
# src/util.pengu — 40 funciones helper_0 … helper_39, cada una con un bucle
# src/main.pengu
import util

weave main into int:
    return calling util.helper_0 with 1
```

```console
$ pengu expand src/main.pengu -o bundle.c
wrote bundle.c (750 lines, 24478 bytes)
$ grep -c "util_helper" bundle.c
80        # 40 prototipos + 40 definiciones
```

**Causa raíz.** `prune_weaves` considera raíz todo weave cuyo `filepath` **no** sea podable:

```python
# pengu_parser/pengu_dce.py:221-227
if is_prunable_module(weave.get("filepath", ""), base_dir):
    std_weaves.append(weave)
else:
    kept.append(weave)          # ← usuario: siempre raíz
    alive |= set(weave.get("refs") or ())
```

El docstring lo declara intencional (“public API of the user's project, bindings, static libraries”), y `docs/PERFORMANCE.md` lo repite: “user modules are always fully emitted”. Pero en un **ejecutable** esa API pública no existe; el usuario solo tiene `main`. La petición de “podar también módulos de usuario” es legítima.

**Fix.** Fase 3, **opt-in** (`--dce-scope=user`, alias `--tree-shake-user`): raíces = `main`, entry module, `@export`, tests (en modo test) y los símbolos que aparezcan en el C glue de `c/`. `output: static/shared/obj` mantiene todo (es una librería). Detalle en [§6.5](#65-fase-3--módulos-de-usuario-opcional).

**Impacto.** En el ejemplo, ~21 KB de 24,5 KB (86 %) es código muerto. En proyectos reales con utilidades, factories o handlers, puede ser más.

---

### 🟠 B7 — Tipos, constantes, `derive` y lambdas no se podan

**Síntoma.** Aun podando funciones, el bundle arrastra los tipos, constantes e implementaciones derivadas de todos los módulos importados.

**Evidencia.** Tras la simulación de §4.7:

| Bundle | Tipos + forward + consts | % del total podado |
|---|---:|---:|
| `k1_pruned` (json sin usar) | 5.700 B | **67 %** |
| `pt1_pruned` (petitio sin usar) | 11.854 B | **77 %** |
| `ci1_pruned` (cipher 1 fn) | 5.063 B | **47 %** |
| `benchs_pruned` | 2.390 B | **24 %** |

Y en el `k1` original, la sección `Derived Concept Implementations` sola son **26.862 B** (18 % del bundle) para tipos que nadie toca. En `pt1`, **52.298 B**.

**Causa raíz.** `generate_type_definitions`, `generate_constants`, `generate_derived_implementations` y `generate_lambdas` iteran **todos** los registros, sin consultar el conjunto vivo. `pengu_dce` documenta explícitamente que solo poda cuerpos y prototipos:

> “Only *weave bodies and prototypes* are pruned. Runes, omens, typedefs and constants are left alone: they are cheap and pruning them risks changing struct layouts or enum values.”

**Matiz importante:** podar **tipos** es la parte delicada (layout/ABI, C glue, bindings). Podar **helpers derivados `static inline`** y **lambdas no referenciadas** es mucho más seguro. Propongo separarlo:

- Fase 4a (segura): podar `derive`/lambdas no alcanzados por el texto C vivo.
- Fase 4b (opt-in): podar tipos y consts con cierre transitivo y excepciones (`.d.pengu`, `@export`, C glue).

Detalle en [§6.6](#66-fase-4--tipos-constantes-y-derive-opcional).

---

### 🟠 B8 — El DCE es por nombre Pengu: falsos positivos (y precisión mejorable)

**Síntoma.** Cualquier identificador del AST que coincida con el nombre de un weave de `std` lo mantiene vivo, aunque sea una variable local, un campo o un nombre de tipo.

**Repro.**

```pengu
import std.scrolls

weave main into int:
    var len as int is 5
    var values as int is 7
    var keys as int is 9
    var contains as bool is true
    var parse as int is 11
    if contains:
        return len + values + keys + parse
    return 0
```

vs. el mismo programa con variables `a`, `b`, `c`, `d`, `e`:

| Versión | Bundle | Weaves kept |
|---|---:|---:|
| nombres comunes (`fp1`) | 6.135 B | 6 |
| nombres neutros (`fp2`) | 3.352 B | 1 |

Se mantienen `pengu_len`, `pengu_contains`, `string_len`, `string_contains`, `pengu_pengu_string_contains` por el simple hecho de llamar a una variable `len` o `contains`. Con 16 nombres comunes (`value`, `count`, `index`, `first`, `last`, `size`, `data`, `items`, `keys`, `values`, `entries`, `name`, `tokens`, `copy`, `compare`, `hash`) el bundle sube **+7.729 B (+5,2 %)** y se mantienen 8 weaves extra.

**Por qué pasa.**

```python
# pengu_parser/pengu_dce.py:110
for tok in stmt.scan_values(lambda v: isinstance(v, Token) and v.type == "NAME"):
    refs.add(str(tok))
```

Se recogen **todos** los `NAME` del AST. Después `_is_referenced` compara contra `name` (nombre Pengu corto) y `c_name`, y además prueba sufijos multi-token. Eso es conservador (nunca rompe), pero:

- 73 nombres de weave están duplicados entre módulos de `std` (`_expect_eq_int` aparece en 5, `assert` en 3, etc.).
- El prefijo `get_` se expande a `name[4:]` “por si acaso” (necesario para `@mutates`, pero también mantiene coincidencias ajenas).
- Un nombre común mantiene weaves de **todos** los módulos, no solo del que lo declara.

**Fix.** El DCE por **símbolo C real** (§6.3/§6.4): el codegen ya sabe a qué `c_name` resuelve cada llamada; si se registra ese símbolo (o se escanea el C emitido), se eliminan los falsos positivos y, de paso, los falsos negativos como B3.

---

### 🟠 B9 — Gates, `include` y `link` se deciden por `import`, no por uso

**Síntoma.** Un módulo importado pero totalmente podado sigue aportando su gate, su header y su biblioteca.

**Evidencia.**

```pengu
import std.filum

weave main into int:
    return 0
```

```console
$ pengu expand fil1.pengu -o fil1.c
wrote fil1.c (2966 lines, 97692 bytes)
$ grep PENGU_ENABLE_THREADS fil1.c
#define PENGU_ENABLE_THREADS 1
```

`grep -c pengu_c_filum fil1.c` → **0**. Es decir: se activa el subsistema de hilos sin una sola llamada. En un build de proyecto, además, `pengu_project.py:1968` hace `needs_threads = "filum" in needed_std`, así que añade `-pthread` (y en Emscripten cambia el modelo de ejecución).

Un `import std.petitio` sin usar deja `#include "petitio.h"` en el bundle (y, en un build real, el `link`/`ldflag` del binding).

**Causa raíz.** `bundle.py:236-244` recorre `self.import_order` (todos los módulos) para los gates; `pengu_project.py:724-756` usa `import_order` + los `#line` del bundle; `symbols.links` se agrega sin filtrar. El propio código lo reconoce: “an over-approximation costs bytes, never correctness”.

**Fix.** Calcular los gates/includes/links a partir de los **módulos con al menos un weave/tipo/const vivo**, manteniendo el escaneo de prefijos C (`pengu_c_filum_`) como red de seguridad para `declare` manuales. Para `link`, conservar los del módulo si vive alguna de sus funciones. Detalle en [§6.7](#67-fase-5--line-gates-includes-y-links).

> [!NOTE]
> Un `@export` en un módulo que no se usa **sí** mantiene su símbolo, por contrato FFI: en `pt1` (petitio sin usar) los 3 comparadores de `atlas` (`atlas__atlas_cmp_*`) se emiten igual. Es un trade-off deliberado, no un bug; si el módulo no se importara, no existirían.

---

### 🟡 B10 — Función genérica como valor: se emite la plantilla, no la instancia

> **✅ Implementado en 2.20.0.** El inferrer instancia la función genérica a
> partir del `FnType` esperado (anotación, callback, retorno o campo):
> `twice_int`, `first_int_string`, `atlas_map_size_int_string`… Si no hay un
> tipo de función concreto, o queda una `T` genérica, se emite `E0005` claro en
> vez de C inválido. Se comparten la validación de `where` (`E0032`), el
> registro de la instancia y el worklist del DCE. El fix corto de "rechazar
> siempre" no fue necesario.

**Síntoma.** Usar un `weave shard T` como valor de función compila el checker, pero emite el nombre de la plantilla (que nunca se define).

**Repro.**

```pengu
weave twice shard T with x as T into T:
    return x

weave main into int:
    var f as weave with int into int is twice
    return calling f with 2
```

```console
$ pengu expand genfn.pengu -o genfn.c
wrote genfn.c (71 lines, 2557 bytes)
$ grep twice genfn.c
  int32_t (*f)(int32_t) = ((int32_t (*)(int32_t))twice);

$ gcc -fsyntax-only genfn.c
… error: ‘twice’ no se declaró aquí (primer uso en esta función)
```

**Causa raíz.** El camino de “valor de función” en `exprs.py` inyecta el `c_name` del símbolo, pero para un genérico no hay una instancia concreta; no se monomorfiza a partir del `FnType` esperado.

**Impacto.** Es un bug de correctitud independiente del DCE, pero **intersecta** con el diseño de instancias: un worklist por símbolos debe marcar viva la instancia cuando el codegen emite su nombre como valor. Si no se va a soportar la feature, al menos debe rechazarse con un error claro.

**Fix corto.** Rechazar con `E00xx` (“una función `shard` no puede usarse como valor sin argumentos de tipo explícitos”) hasta que se implemente la monomorfización desde el tipo esperado. **Fix largo:** resolver la instancia con el `FnType` de destino y marcarla viva.

---

### 🟡 B11 — `#line` es el 12–23 % y no hay forma de apagarlo

> **✅ Implementado en 2.21.0.** `--no-line-markers` /
> `PENGU_NO_LINE_MARKERS=1` omite las directivas y entra en la cache key y el
> config hash. Medido: `hello` 3,7 → 3,3 KB (−13 %), `cipher` 11,4 → 10,3 KB
> (−10 %), `petitio` 15,9 → 15,2 KB (−4 %), `stdlib_ops` 10,8 → 8,0 KB (−26 %),
> `atlas_ops` 16,7 → 12,4 KB (−26 %). Por defecto siguen encendidas para no
> perder la trazabilidad de los diagnósticos C.

**Síntoma.** `emit_line_markers` está fijado a `True`:

```python
# pengu_parser/pengu_codegen/main.py:185
self.emit_line_markers = True
```

No hay flag de CLI ni variable de entorno. En un bundle grande son 112–181 KB de directivas. Quitarlas ahorra **12–13 %** del archivo (§4.5).

**Fix.** `--no-line-markers` / `PENGU_NO_LINE_MARKERS=1`, por defecto **on** (los diagnósticos importan), y documentar que apagarlo empeora la trazabilidad. Añadirlo a la cache key.

---

### 🟡 B12 — Higiene: test referenciado que no existe, docs y docstrings desactualizados

> **✅ Limpiado en 2.21.0.** El test de tablas de feature gates existe, el
> docstring de `pengu_dce.py` ya no afirma que las instancias se crean durante
> la generación de cuerpos, y `docs/PERFORMANCE.md` documenta `#line` y la
> política conservadora de includes/links. Los números de línea históricos se
> sustituyeron por referencias al archivo/función cuando aplicaba.

| Qué | Dónde | Estado |
|---|---|---|
| `tests/compiler/test_binary_size_reduction.py` | comentario en `pengu_codegen/bundle.py:25` | **No existe**; se supone que verifica que las dos tablas de feature gates coinciden |
| `hello` = “65 lines / 2.3 KB” | `docs/PERFORMANCE.md:200` | Hoy: 73 líneas / 2,9 KB (`benches/hello_world.pengu`) o 96 / 3,7 KB (`spark.println`) |
| `prune_weaves()` en `pengu_dce.py:175` | `docs/ARCHITECTURE.md` | Hoy está en `:185`; los números de línea del monolito antiguo ya no aplican |
| “instances are created *during* body generation” | `pengu_dce.py:1-23` | Falso en la práctica: 546/591 ya existen antes del pase (se crean en `collect_declarations`, pass 3) |
| `FEATURE_GATE_MODULES` duplicado | `bundle.py:29` y `pengu_project.py:3336` | Hoy coinciden (`{'PENGU_ENABLE_THREADS': 'filum'}`), pero sin test que lo garantice |

No son bugs funcionales, pero son la clase de deriva que hace que un cambio futuro rompa el DCE sin que nadie lo note.

---

## 🧭 6. Diseño propuesto: cómo hacerlo bien

### 6.1 Principios

1. **Exactitud por símbolo C, no por nombre Pengu.** El codegen ya resuelve cada llamada a un `c_name`. Ese es el hecho verificable; los nombres del AST son una aproximación.
2. **Punto fijo con worklist.** Traducir un cuerpo descubre nuevas dependencias; repetir hasta que no haya cambios.
3. **Determinismo.** El orden de emisión final se mantiene (o se fija explícitamente); nada de iterar `set`s sin ordenar.
4. **Fallback conservador.** Si una referencia no se puede resolver con certeza (C glue, macro, `declare`), se conserva. El DCE nunca debe ser la causa de un fallo de compilación.
5. **Opt-in para lo que no se puede demostrar.** Podar módulos de usuario o tipos es una decisión de build, no una imposición.
6. **Invariante verificable:** todo `c_name` llamado en el bundle emitido tiene definición en el bundle, en el runtime o en un `declare` + header. Se comprueba con el compilador C (`-Werror=implicit-function-declaration`) en CI.

### 6.2 Fase 0 — correctitud y quick wins (tamaño: S, riesgo: bajo)

| Cambio | Archivo | Efecto |
|---|---|---|
| Raíces reales de `std` (`std_dirs()`) | `pengu_dce.py:45-82` | Restaura el DCE en FHS/pip (B1) |
| `refs` incluye defaults de parámetros | `declarations.py:594,837` | Arregla B3 (build roto) |
| `extra_roots` de tests solo si `is_test` | `bundle.py:90-96` | Arregla B5 |
| Test de layout instalado | `tests/compiler/test_dce.py` (nuevo) | Evita regresión de B1 |
| Test de default args | idem | Pin de B3 |
| Test “importar todo el std” | `tests/compiler/test_imports.py` (nuevo) | Detecta B4 y futuras colisiones |
| Crear el test que falta | `tests/compiler/test_binary_size_reduction.py` | Cierra B12 |
| Actualizar docs/docstrings | `PERFORMANCE.md`, `ARCHITECTURE.md`, `pengu_dce.py` | Cierra B12 |

**Resultado esperado:** `hello` en FHS vuelve a 3,7 KB; el programa de B3 compila y corre; los tests dejan de inflar el bundle de producción.

### 6.3 Fase 1 — alcanzabilidad exacta (el gran win)

**Idea.** Separar **catálogo** (todas las definiciones disponibles, para resolver llamadas) de **emisión** (solo las alcanzables). El catálogo ya existe: `self.weaves` + `fn_info`. Solo hay que dejar de tratarlo como “lista de emisión”.

**Algoritmo (worklist con escaneo del C emitido):**

```python
# Pseudocódigo; va en pengu_codegen/bundle.py, antes de generar secciones.
import re
IDENT_RE = re.compile(r"\b[A-Za-z_]\w*\b")

catalog   = {w["c_name"]: w for w in self.weaves if w.get("subst_map") or w.get("is_generic")}
prunable  = {w["c_name"]: w for w in self.weaves if is_prunable_module(w["filepath"], ...)}
emit_list = [w for w in self.weaves
             if w["c_name"] not in prunable and w["c_name"] not in catalog]  # raíces
queue     = deque(emit_list)
live      = set()
bodies    = {}

while queue:
    w = queue.popleft()
    if w["c_name"] in live:
        continue
    live.add(w["c_name"])
    body = generate_one_definition(w)          # extraído de generate_function_definitions(w)
    bodies[w["c_name"]] = body
    for ident in IDENT_RE.findall(body):       # \b[A-Za-z_]\w*\b
        for table in (catalog, prunable):
            dep = table.get(ident)
            if dep is not None and dep["c_name"] not in live:
                queue.append(dep)

# self.weaves = [w for w in self.weaves if w["c_name"] in live]  (orden original)
# prototipos = generate_function_prototypes(self.weaves)
# definiciones = concatenar bodies en el orden de self.weaves
```

**¿Por qué escanear el C emitido y no instrumentar cada `return f"{c_name}(...)"`?**

- El codegen tiene **decenas** de sitios que construyen llamadas (`exprs.py`, `calls.py`, `orchestrator`, `@mutates`, conceptos, operadores, defaults, lambdas, tests…). Instrumentarlos todos es frágil.
- El texto C ya contiene **exactamente** los símbolos que el compilador va a necesitar: llamadas, direcciones de función (`&f`, `= f`), tablas de callbacks, etc.
- Los falsos positivos por strings son mínimos: el único string con un `c_name` es el `pengu_frame_push("<self>", …)` de la propia función. Un identificador de variable local como `len` **no** coincide con `pengu_len` (el índice es por `c_name`), así que se eliminan de golpe los falsos positivos de B8.
- Es **monótono**: cada descubrimiento añade, nunca quita. Si algo se escapa, se puede añadir instrumentación puntual como refuerzo.

**Detalles que hay que cuidar:**

| Tema | Decisión |
|---|---|
| Instancias creadas **durante** el codegen (`exprs.py:1481`) | Al descubrir una llamada a un `c_name` que no está en el catálogo, intentar `_collect_monomorphized_weave` y añadirlo; si no se puede, conservar por nombre (fallback) |
| Orden de emisión | Mantener el orden original de `self.weaves` (los contadores de especialización y los nombres de temporales ya están asignados; reordenar cambia bytes pero no semántica). Para reproducibilidad, el worklist debe ser FIFO y determinista |
| Prototipos | Se generan **después** del worklist, de la lista filtrada. Nunca un prototipo `static inline` sin definición (eso rompe `-Werror`) |
| `@export` | Raíces siempre |
| `main` / `pengu_main` | Raíces siempre |
| Tests | Raíces solo en `--test` (B5) |
| `antiquus` | Su cuerpo es C literal: añadir `_identifiers_in_text(c_body)` a las dependencias (hoy no se escanea; solo `@export` lo salva) |
| Lambdas | Se emiten como funciones C independientes (`self.lambdas`), fuera de `self.weaves`. **Hay que escanear también su texto**: un weave llamado solo desde una lambda se podaría si no |
| Tests | En `--test`, sus cuerpos son otra sección C independiente y pueden llamar a **instancias** (`some(42)` → `some_of_int`). Opción simple y segura: en modo test, **no podar instancias** (como hoy); los bundles de test no se distribuyen. Opción exacta: traducir y escanear también el test section |
| Entry point | Llama a `pengu_main` y, en `--test`, al runner de tests. Es código generado: escanearlo también |
| Derived helpers | `static inline` generados aparte; si se podan (Fase 4a), su texto debe entrar en el worklist |
| Funciones usadas como valor | El nombre C aparece en el texto (`= pengu_len`, `&pengu_len`); el worklist lo detecta. Para genéricos, primero arreglar B10 o rechazarlo |
| Tipos | En esta fase **no** se podan; el worklist solo decide funciones |
| Determinismo | Nada de `for x in set` para decidir el orden de la cola; usar listas/deques ordenadas |

> [!IMPORTANT]
> **Regla general:** el worklist debe escanear **todo el texto C que se va a emitir**, no solo `self.weaves`. Cuerpos de weaves, lambdas, tests, `derive` y entry point son funciones C separadas; si una de ellas llama a un weave que el escaneo no ve, el DCE lo poda y el build falla. La implementación puede escanear cada sección al generarla, o hacer un punto fijo sobre el bundle completo (más simple, más lento).

**Resultado esperado (medido por simulación, §4.7):**

| Programa | Antes | Después | `gcc -O2` |
|---|---:|---:|---:|
| `ci1` (cipher 1 fn) | 581,7 KB | **~10,5 KB** | 9,2 s → **0,18 s** |
| `pt1` (petitio sin usar) | 782,2 KB | **~15,1 KB** | 10,3 s → **0,13 s** |
| `k1` (json sin usar) | 142,2 KB | **~8,3 KB** | 1,5 s → **0,14 s** |
| `bench_stdlib_ops` | 568,9 KB | **~9,9 KB** | 8,8 s → **0,35 s** |

**Riesgo principal.** Un weave que se usa pero cuyo nombre no aparece en el texto C emitido. Mitigaciones: (a) instrumentación de refuerzo en `var_ref`/`_resolve_weave_refs_in_stmts`; (b) barrido del `c_body` de antiquus; (c) fallback por nombre si una llamada no resuelve; (d) test diferencial DCE on/off sobre toda la suite.

### 6.4 Fase 2 — DCE de `std` por símbolos (sustituir el escaneo de nombres)

> [!NOTE]
> **Estado (2.17.0):** la fase 1 ya implementa el worklist por `c_name`, así que
> esta fase queda **absorbida para builds normales**. Lo que sigue pendiente es
> retirar los heurísticos de nombre del pase conservador que solo usa `--test`.

La fase 1 ya reduce el problema a “qué weaves de `std` son raíces”. Para eso:

- Raíces iniciales: los weaves **no podables** (usuario/bindings, hoy) + `main` + `@export`.
- El worklist descubre los `c_name` de `std` llamados desde los cuerpos vivos.
- Cada `c_name` resuelve a **un** registro (adiós a los 73 nombres duplicados y a `len`/`values`).
- Se pueden eliminar (o dejar como fallback) `collect_references` y `_is_referenced` basados en nombres; se conserva `collect_references` solo como red de seguridad para lo que el texto no cubre (p. ej. un `declare`/binding referenciado desde C glue).
- Los nombres privados `_foo` ya no necesitan heurísticas: el símbolo C exacto los distingue por módulo.

**Ventaja extra:** el codegen deja de traducir cuerpos muertos. En `ci1`, el codegen de Python baja de ~905 ms a ~50–100 ms (se traducen 4 funciones en vez de 582).

**Compatibilidad:** mantener `--no-dce` para reproducir el comportamiento anterior; el marcador y las stats se calculan igual.

### 6.5 Fase 3 — módulos de usuario (opcional)

**Flag:** `--dce-scope=user` (alias `--tree-shake-user`). Por defecto **off** para no romper builds existentes.

**Raíces:**

- `main` / `pengu_main` del entry.
- Cualquier weave con `@export("…")`.
- En `--test`: los `test` blocks y sus referencias.
- Cualquier `c_name` que aparezca en los fuentes de `c/` (`collect_c_sources()`) — escaneo conservador de identificadores.
- En `output: static|shared|obj`: **no se poda nada** (la API pública es el producto).

**Lo que hay que documentar:**

- `@export` es el contrato para que C llame a un weave de PenguScript (`docs` ya lo dice).
- Si cargas plugins por `dlopen` o resuelves símbolos por nombre en runtime, no actives esta opción.
- Los `test` blocks no se emiten en builds normales; sus funciones se podan salvo que otra cosa las use.

**Resultado esperado:** el ejemplo de B6 baja de 24,5 KB a ~3 KB (piso + 1 función). En proyectos reales, el ahorro depende de cuántos helpers “públicos” haya; suele ser modesto comparado con B2, pero es lo que pediste.

### 6.6 Fase 4 — tipos, constantes y `derive` (opcional)

**4a — seguro: helpers derivados y lambdas.**

- Los helpers `Par`/`Ordo`/`Vinculum`/`Imago`/`Nexus` son `static inline` y no tienen enlace externo. Se pueden podar con el mismo worklist: si su `c_name` no aparece en ningún cuerpo vivo, no se emiten.
- Las lambdas se registran antes del DCE; filtrar por las que pertenecen a weaves vivos (o cuyo `c_name` aparece en el texto).
- Ahorro medido: en `k1`, `Derived` pasa de 26.862 B a 262 B; en `pt1`, de 52.298 B a 286 B.

**4b — opt-in: tipos y constantes.**

Algoritmo de cierre:

1. Semillas: tipos mencionados en firmas y cuerpos vivos (el texto C contiene `sizeof(T)`, casts, `T x`, `struct T`), constantes mencionadas por nombre (`#define`), y tipos de `@export`.
2. Para cada tipo vivo, añadir los tipos de sus campos (recursivo), sus tuple-types, y el tipo base de `seal`/`alias`.
3. Para cada const viva, añadir los tipos de su valor (arrays, runes).
4. Emitir solo ese conjunto; conservar siempre:
   - tipos de `.d.pengu` (bindings/FFI),
   - tipos usados por `declare`/`include`/`link`,
   - tipos y consts referenciados desde `c/`,
   - `@export`/`main`.
5. Preservar el **orden** de declaración (el orden de campos y de typedefs puede importar para C).

**Riesgo:** si se olvida un tipo usado solo en C glue, el C no compila. Por eso: opt-in, test diferencial, y un `--no-prune-types` como escape.

**Ahorro medido (simulación):** `k1` 8,3 KB → ~3 KB; `pt1` 15,1 KB → ~3,5 KB; `ci1` 10,5 KB → ~3 KB. En bundles que **usan** tipos (una app real), el ahorro es menor; no lo pongas por defecto hasta validarlo.

### 6.7 Fase 5 — `#line`, gates, includes y links

| Cambio | Efecto | Riesgo |
|---|---|---|
| `--no-line-markers` | −12/−13 % | Diagnósticos C apuntan al bundle; opt-in |
| Gates por módulo vivo + prefijo C | apaga `PENGU_ENABLE_THREADS 0` si no se usa `filum` | mantener el escaneo `pengu_c_filum_` para `declare` manuales |
| Includes por módulo vivo | menos headers que parsear | conservar los de módulos con `declare` vivos |
| Links/ldflags por módulo vivo | binario/enlace más pequeño | conservador: si hay duda, mantener |
| Assets (`arca`) | **no afecta a `bundle.c`**: los arrays viven en `arca_assets.c` y la tabla `_{module}_assets[]` los retiene todos en el binario | fuera de alcance de esta auditoría; track aparte |

**`link`/`ldflag`:** hoy `pengu_project.py` agrega `symbols.links` de todos los módulos. Para satélites (`lib/<binding>`) esto puede arrastrar una librería nativa que ningún weave vivo usa. La regla segura: conservar el `link` de un módulo si **algún** weave de ese módulo sigue vivo, o si el bundle menciona el prefijo C del binding.

### 6.8 Lo que **no** hay que hacer

- ❌ **No reordenar `self.weaves` a lo bruto.** Los nombres de especialización llevan contadores y el orden actual es determinista; reordenar cambia bytes y puede romper snapshots. Filtra conservando el orden.
- ❌ **No podar `.d.pengu`.** Son la frontera C; sus `declare`/`enum`/`include` son el contrato.
- ❌ **No podar `@export`, `main` ni los tests en modo test.**
- ❌ **No podar tipos por defecto.** Un layout mal podado es corrupción de memoria, no un error de compilación.
- ❌ **No confiar en `--gc-sections`.** TCC no lo tiene; el `.o` y el `bundle.c` ya pagaron el coste; y el usuario que lee el bundle no ve el resultado del linker.
- ❌ **No usar `grep` de nombres para módulos de usuario.** Ahí no hay convención de prefijos y el C glue es invisible.
- ❌ **No cambiar el significado de `--no-dce`.** Debe seguir siendo el “modo seguro” para bug reports y comparaciones A/B.

### 6.9 Flags, configuración y cache key

| Flag | Default | Qué hace |
|---|---|---|
| `--no-dce` / `PENGU_NO_DCE=1` | off | Emite todo (comportamiento actual sin DCE) |
| `--dce-scope=std\|user` | `std` | `std` = hoy (pero exacto); `user` = poda también `src/` |
| `--prune-types` | off | Poda tipos/consts/derived no alcanzados (fase 4; requiere Fase 1 hecha) |
| `--no-line-markers` | markers on | Apaga `#line` |
| `--size-report` (opcional) | off | Imprime bytes por sección + kept/dropped por módulo |

Cada flag nuevo **debe entrar en la cache key** (`pengu_project.py:6561-6581`, `extra_digests`), como ya hace `dce=on/off`. Si no, un build con `--dce-scope=user` puede reutilizar el binario del build conservador.

### 6.10 Track B4 — colisiones de tipos entre módulos

Esto es **independiente** del DCE y merece su propio PR. Tres niveles, en orden de esfuerzo:

| Nivel | Qué se hace | Pros | Contras |
|---|---|---|---|
| **1. Diagnóstico** | Detectar dos tipos con el mismo nombre lógico en el cierre y emitir un error claro (`E00xx`) | Barato; convierte C inválido en un mensaje accionable | Rompe combinaciones que hoy “funcionan” por accidente (incluidas las del std) |
| **2. Lookup por módulo** | `(módulo, nombre)` en el `SymbolTable`; `json.JsonValue` resuelve al tipo de `json` aunque otro módulo declare `JsonValue` | Arregla la resolución cualificada sin tocar el ABI | No arregla el nombre C: dos `struct JsonValue` siguen colisionando si se emiten ambos |
| **3. Identidad completa** | Nivel 2 + prefijo de módulo en el nombre C de tipos de usuario sin `insignia` (como las funciones) | Correcto de verdad; permite importar todo el std | Invasivo: checker, infer, codegen, `CTypeMapper`, `derived_gen`, bindings, docs |

**Recomendación de secuencia:**

1. **Ahora:** arreglar las colisiones conocidas del std (renombrar o aislar):
   - `cipher.JsonValue` → `CipherJsonValue` (o moverlo a un módulo propio),
   - `sourcemap.Span` → `SourceSpan`,
   - `invoke.Parser` → `CommandParser`,
   - variante `JsonRpcMessage.Request` → `RpcRequest`,
   - variantes `OutOfMemory` de `HttpError`/`RegexError` con prefijo.
   Con alias/deprecación donde el ABI lo permita.
2. **Después:** el diagnóstico del nivel 1, para que el caso de usuario (`a.Config`/`b.Config`) falle claro en vez de generar C inválido.
3. **Más adelante:** el nivel 2/3. El campo `RuneType.module` ya existe (`pengu_checker.py:1406`), así que hay una base sobre la que construir.

**Invariantes para los tests:**

- Ningún par de módulos del std importables juntos produce C inválido.
- `import std.diagnostic` + `import std.sourcemap` + usar ambos `Span` compila y ejecuta.
- El mismo nombre de tipo en dos módulos de usuario: o error claro, o dos tipos C distintos.
- `pengu check` no puede decir “Clean” y luego `gcc` fallar por un tipo.

---

## 🧪 7. Plan de pruebas y CI

### 7.1 Tests que hay que añadir

| Test | Qué fija |
|---|---|
| `test_dce_spark_println_is_minimal` | `hello` = 3 weaves, < 5 KB |
| `test_unused_import_is_nearly_free` | `import std.json` sin usar < 5 KB (hoy 142 KB) |
| `test_generic_instance_is_reachable_only` | `cipher.encode_base64` no emite `some_of_int` ni las otras 545 |
| `test_default_argument_keeps_callee` | B3: `pengu run` compila y ejecuta |
| `test_test_refs_do_not_leak_in_normal_build` | B5: `--test` sí, build normal no |
| `test_user_module_tree_shaking_opt_in` | B6: helper no usado ausente; `@export` presente; `output=static` intacto |
| `test_installed_std_layout_still_prunes` | B1: `PENGU_STD_DIR` + `monkeypatch` |
| `test_all_std_modules_import_together` | B4: o compila, o da un error claro y accionable |
| `test_same_named_runes_in_two_modules` | B4: diagnóstico o mangling correcto |
| `test_generic_function_value` | B10: error claro o instancia correcta |
| `test_dce_on_off_equivalence` | Corpus: mismo stdout/exit con y sin DCE |
| `test_bundle_has_no_implicit_declarations` | `gcc -fsyntax-only -Werror=implicit-function-declaration` |
| `test_binary_size_reduction` | Tablas de gates + presupuestos de tamaño |

### 7.2 Matriz de CI

| Dimensión | Valores |
|---|---|
| Layout | checkout · `PENGU_STD_DIR` · FHS (`share/pengu/std`) · onefile PyInstaller |
| Compilador | gcc · clang · tcc |
| Perfil | debug · release · `--release-unsafe` |
| DCE | on · off · `--dce-scope=user` · `--prune-types` · `--no-line-markers` |
| C estándar | GNU extensions · `--strict-c99` |
| Target | nativo · WASM (si aplica) |

### 7.3 Invariantes

1. **Todo símbolo llamado está definido** (C compiler lo verifica).
2. **DCE on vs off**: mismo comportamiento observable (stdout, exit code, efectos).
3. **Reproducibilidad**: dos ejecuciones con la misma entrada producen bytes idénticos.
4. **Sin regresiones de tamaño**: presupuestos por escenario (hello ≤ 5 KB, unused import ≤ 5 KB, cipher 1 fn ≤ 15 KB, bench_stdlib_ops ≤ 15 KB).
5. **Sin `-Werror` nuevo**: `-Wall -Wextra -Werror -Wno-unused-function` sobre un corpus de bundles.

### 7.4 Medición continua

Añadir `benches/bundle_size.py` (hermano de `benches/binary_size_breakdown.py`) que:

- expanda un corpus (`hello`, los `benches/*.pengu`, casos de `tests/`),
- registre bytes totales y por sección,
- cuente kept/dropped e instancias,
- compile con `gcc -O2` y registre ms,
- compare DCE on/off,
- falle si un presupuesto se excede.

Así el tamaño deja de ser una impresión y pasa a ser un número en CI.

---

## ⚠️ 8. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El worklist omite una dependencia real | Media | Build roto (implícita) | Barrido textual + instrumentación de refuerzo + `antiquus` c_body + fallback por nombre + test de implícitas |
| Cambia el orden/bytes del bundle y rompe snapshots | Alta | Ruido en tests | Preservar orden de `weaves`; actualizar goldens; comparar comportamiento, no bytes |
| Podar tipos rompe layout/ABI | Media | Corrupción de memoria | Opt-in + cierre transitivo + conservar `.d.pengu`/`@export`/C glue + `_Static_assert` de layouts |
| Podar módulos de usuario rompe C glue/dlopen | Media | Link error | Opt-in + escaneo de `c/` + docs + `@export` |
| TCC/compiladores sin gc-sections | Alta | Binario dev grande | Es exactamente lo que el DCE arregla; medir con TCC en CI |
| Cache sirve un binario de otra política | Media | Comportamiento incoherente | Nuevos flags en `extra_digests` |
| FHS/pip sigue sin podar | Baja tras fix | 10× bundle | Test con `PENGU_STD_DIR` + CI de instalación |
| El checker sigue monomorfizando todo | Alta | `pengu check` lento | Fuera de alcance; el worklist evita traducir, no evita chequear. Roadmap separado |
| Llamada desde una macro/header de C, invisible en el bundle | Baja | weave podado | `@export` documentado; escanear `c/` y los headers del proyecto; ante duda, conservar |

---

## 📈 9. Impacto esperado

### 9.1 Por escenario

| Escenario | Hoy | Fase 0 | Fase 1 | Fase 4 |
|---|---:|---:|---:|---:|
| `hello` (spark.println) | 3,7 KB | 3,7 KB | 3,7 KB | ~3,2 KB |
| `import std.json` sin usar | 142,2 KB | 142,2 KB | **~8,3 KB** | ~3 KB |
| `cipher` 1 función | 581,7 KB | 581,7 KB | **~10,5 KB** | ~3 KB |
| `petitio` sin usar | 782,2 KB | 782,2 KB | **~15,1 KB** | ~3,5 KB |
| `bench_stdlib_ops` | 568,9 KB | 568,9 KB | **~9,9 KB** | ~2,5 KB |
| `hello` en FHS | **35,0 KB** | **3,7 KB** | 3,7 KB | ~3,2 KB |
| Módulo usuario 40 fns / 1 usada | 23,9 KB | 23,9 KB | 23,9 KB | ~3 KB (con `--dce-scope=user`) |

### 9.2 Tiempo

| Métrica | Hoy | Después (Fase 1) |
|---|---:|---:|
| `gcc -O2` de `ci1` | 9.152 ms | **~180 ms** |
| Codegen Python de `ci1` | 905 ms | **~50–100 ms** |
| Binario dev TCC de `ci1` (strip) | 295 KB | ~30 KB |
| `bundle.c` de `ci1` | 581,7 KB | ~10,5 KB |

> El `parse + check` (~2–4 s) **no** baja con esto: el checker sigue monomorfizando y chequeando todo el cierre transitivo. Es un objetivo distinto (deferir la monomorfización), y lo dejaría para una fase posterior.

---

## 🗺️ 10. Roadmap sugerido

```
Fase 0  Correctitud + FHS + default args + tests refs     [S, 1-2 días]
   │
   ├─▶ Fase 1  Instancias + worklist por símbolo C        [L, 3-5 días]  ← 90-99 % del win
   │      │
   │      ├─▶ Fase 2  DCE exacto de std (sustituir nombres) [M, 2-4 días]
   │      │
   │      ├─▶ Fase 3  Módulos de usuario (opt-in)           [M, 2-4 días]
   │      │
   │      └─▶ Fase 4  Tipos/consts/derived (opt-in)         [L, 3-5 días]
   │
   ├─▶ Fase 5  Line markers / gates / includes / links      [S, 1-2 días]
   │
   └─▶ Track B4  Colisiones de tipos entre módulos          [L, diseño aparte]
          ├─ diagnóstico E00xx + renombres de std           [S]
          ├─ resolución por alias de import                 [M]
          └─ identidad de tipo por módulo + prefijo C       [L]
```

**Orden recomendado:** Fase 0 → Fase 1 → Fase 2 → Fase 5 (barata) → Fase 3 → Fase 4. B4 (colisiones) puede ir en paralelo como track de correctitud, pero **no la mezcles** con el cambio de DCE: son fallos distintos y merecen PRs separados.

**Esfuerzos:** son estimaciones de orden de magnitud leyendo el código, no una promesa. La Fase 1 es la única que toca la arquitectura del codegen; el resto son cambios locales.

---

## ✅ 11. Checklist de aceptación

- [ ] `pengu expand hello.pengu` < 5 KB y conserva el marcador DCE.
- [ ] `PENGU_STD_DIR=<otro layout> pengu expand hello.pengu` también poda (B1).
- [ ] `import std.json` sin usar < 5 KB; `cipher` 1 función < 15 KB; `petitio` sin usar < 20 KB (Fase 1).
- [ ] Ningún `bundle.c` del corpus produce `implicit-function-declaration`.
- [ ] El programa de B3 (default arg) compila y ejecuta.
- [ ] `testleak.pengu` en build normal = 1 weave; con `--test` incluye sus dependencias.
- [ ] Dos módulos con `rune Config` dan un error claro **o** generan C correcto (nunca C inválido).
- [ ] `import std.diagnostic` + `import std.sourcemap` funciona si se usan ambos `Span` (o error claro).
- [ ] `pengu test` pasa con DCE on y off.
- [ ] `--dce-scope=user` no rompe `output=static` ni `@export`.
- [ ] Cache key distingue todas las combinaciones de flags.
- [ ] Bench de tamaño en CI con presupuestos.

---

## 📎 12. Apéndices

### A. Comandos de reproducción

```bash
# Bundle y estadísticas
pengu expand hello.pengu -o hello.c
PENGU_NO_DCE=1 pengu expand hello.pengu -o hello_nodce.c
pengu expand script.pengu --verbose

# FHS / instalación
mkdir -p /tmp/fhs/share/pengu && cp -r std /tmp/fhs/share/pengu/std
PENGU_STD_DIR=/tmp/fhs/share/pengu/std pengu expand hello.pengu -o fhs.c
PENGU_STD_DIR=/tmp/fhs/share/pengu/std pengu run hello.pengu --keep --no-cache

# Tiempo C
gcc -c -O2 -std=c11 -I std_c -I build/include -I . ci1.c -o /tmp/ci1.o

# Tiempo por fase
PENGU_CACHE=0 pengu time script.pengu
PENGU_NO_TCC=1 pengu time script.pengu --cc gcc

# ¿Hay código muerto? (analizador de grafo C)
python3 /tmp/dce_audit.py ci1.c k1.c
```

#### A.1 Analizador de alcanzabilidad C

Script autónomo (guárdalo como `/tmp/dce_audit.py`); reproduce las cifras de esta auditoría:

```python
import re, sys
from collections import deque

HDR = re.compile(r'^(?:PENGU_MAYBE_UNUSED\s+)?(?:static\s+)?(?:inline\s+)?'
                 r'(?:__attribute__\(\([^)]*\)\)\s*)?[\w\s\*]+?\b([A-Za-z_]\w*)\s*\([^;]*\)\s*\{\s*$')

def definitions(text):
    lines, out, i = text.splitlines(True), {}, 0
    while i < len(lines):
        m = HDR.match(lines[i])
        if m and not lines[i].lstrip().startswith(('#', '/*', '*')):
            depth, j = 0, i
            while j < len(lines):
                s = lines[j]
                if not s.startswith('#'):
                    s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
                    s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
                    depth += s.count('{') - s.count('}')
                if depth <= 0:
                    break
                j += 1
            out[m.group(1)] = ''.join(lines[i:j + 1])
            i = j + 1
        else:
            i += 1
    return out

def main(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    defs = definitions(text)
    call = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
    graph = {}
    for name, body in defs.items():
        body = re.sub(r'^#.*$', '', body, flags=re.M)
        body = re.sub(r'"(\\.|[^"\\])*"', '""', body)
        body = re.sub(r"'(\\.|[^'\\])*'", "''", body)
        graph[name] = {c for c in call.findall(body) if c in defs and c != name}
    roots = [r for r in ('main', 'pengu_main') if r in defs]
    seen, queue = set(), deque(roots)
    while queue:
        name = queue.popleft()
        if name not in seen:
            seen.add(name)
            queue.extend(graph.get(name, ()))
    dead = [n for n in defs if n not in seen]
    dead_bytes = sum(len(defs[n]) for n in dead)
    print(f'{path}: {len(defs)} funciones, {len(seen)} alcanzables, {len(dead)} muertas')
    print(f'  {len(text)} B totales, {dead_bytes} B muertos ({100 * dead_bytes / len(text):.1f} %)')
    print(f'  muertas (muestra): {", ".join(sorted(dead)[:8])}')

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        main(arg)
```

Uso:

```console
$ python3 /tmp/dce_audit.py ci1.c
ci1.c: 623 funciones, 4 alcanzables, 619 muertas
  595666 B totales, 532303 B muertos (89.4 %)
```

Caveat: cuenta llamadas directas (`f(...)`), no punteros a función. En la implementación real se sustituye por la lógica del compilador, que conoce los símbolos exactos.

### B. Fragmentos de código relevantes

**B.1 — La guarda de instancias (B2):**

```python
# pengu_parser/pengu_dce.py:205
if weave.get("subst_map") or weave.get("is_generic"):
    kept.append(weave)
    ...
```

**B.2 — Referencias solo del cuerpo (B3):**

```python
# pengu_parser/pengu_codegen/declarations.py:594
"refs": _dce_collect_refs(body_stmts),
```

**B.3 — Raíces de tests siempre (B5):**

```python
# pengu_parser/pengu_codegen/bundle.py:90
for test in self.tests:
    extra_roots |= _dce_collect_refs(test.get("body_stmts") or [])
```

**B.4 — Tipos sin prefijo de módulo (B4):**

```python
# pengu_parser/pengu_codegen/declarations.py:246
c_name = f"{prefix}{name}" if prefix else name
```

**B.5 — Registro global de tipos (B4):**

```python
# pengu_parser/pengu_checker.py:1407
self.symbols.runes[r_name] = rune_t
```

**B.6 — Gates desde import_order (B9):**

```python
# pengu_parser/pengu_codegen/bundle.py:236
for module in (self.import_order or []):
    stem = _std_module_stem(module)
    if stem: imported.add(stem)
```

### C. Matriz de colisiones detectadas

| Par | Tipo de fallo | Dónde |
|---|---|---|
| `json.JsonValue` + `cipher.JsonValue` | `E0041` en codegen; `E0005` al compilar `get` | `pengu expand` |
| `petitio.Request` + `jsonrpc.JsonRpcMessage.Request` | `E0046` en check | `pengu check` |
| `petitio.HttpError.OutOfMemory` + `regulus.RegexError.OutOfMemory` | `E0046` en check | `pengu check` |
| `diagnostic.Span` + `sourcemap.Span` | C inválido (miembros inexistentes) | `gcc` |
| `invoke.Parser` + `json.Parser` | C inválido (miembros inexistentes) | `gcc` |
| `a.Config` + `b.Config` (usuario) | C inválido (layout del último) | `gcc` |

Duplicados de **nombres de weave** en `std` (no son errores, pero alimentan B8): 73, entre ellos:

```
_expect_eq_int   → atlas, cipher, oracle, scrolls, tally
_expect_eq_string→ atlas, cipher, scrolls
assert           → spark, trial, ward
assert_msg       → spark, trial, ward
_expect          → functor, loom, oracle, petitio, scrolls, tally
```

### D. Glosario

| Término | Significado |
|---|---|
| **Weave** | Función de PenguScript; se emite como función C (a menudo `static inline`). |
| **Instancia / monomorfización** | Copia concreta de un `shard T` para un tipo concreto (`sum_int`, `sum_float`). |
| **DCE** | *Dead-code elimination*: quitar lo que no se alcanza. |
| **Raíz** | Símbolo que se conserva por definición (`main`, `@export`, API de librería). |
| **Worklist** | Cola de símbolos por descubrir; al traducir uno se añaden sus dependencias. |
| **Fuga (size leak)** | Código/símbolos que acaban en el bundle sin usarse. |
| **FHS** | *Filesystem Hierarchy Standard*: `<prefix>/share/pengu/std`, `<prefix>/bin/pengu`. |
| **C glue** | Fuentes `.c`/`.h` del proyecto en `c/` que se compilan junto al bundle. |

---

### E. Nota final

El DCE actual no es un fracaso: **hace exactamente lo que promete** y el caso `spark.println` ya está resuelto. El problema es que su política se queda corta justo donde el lenguaje es más potente: **genéricos, `derive` y módulos de usuario**. La buena noticia es que la infraestructura necesaria ya existe (`c_name` por weave, `refs`, `subst_map`, `@export`); falta cambiar la pregunta de *“¿aparece este nombre en el AST?”* a *“¿qué símbolo C llama realmente el código que voy a emitir?”*. Esa única idea es la que convierte 582 KB en 10 KB.

---

<sub>Auditoría generada leyendo `pengu_parser/pengu_dce.py`, `pengu_parser/pengu_codegen/*`, `pengu_parser/pengu_checker.py`, `pengu_project.py`, `pengu_paths.py`, `docs/PERFORMANCE.md`, `docs/PENGU_BUILD.md` y midiendo `pengu expand`/`pengu time`/`gcc` sobre casos sintéticos y los `benches/` del repo.</sub>
