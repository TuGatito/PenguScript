# Migración del backend de PenguScript: C → C++

**Informe de auditoría y plan de ruta**
Fecha: 2026-11-10 · Estado: **auditoría cerrada y Ruta A′ adoptada; F0 y F1 completadas** (backend C++ con la semántica de hoy: el `psc` se emite, compila, enlaza y se auto-hospeda en C++, con 895/895 tests) · Alcance: `PenguScript` (repo del `psc`) + `PenguScript-Python` (repo hermano) + `docs/LANGUAGECPP.es.md` + `scratch/AUDITORIA_CPP.es.md`

---

## 0. Resumen ejecutivo

**Veredicto: el cambio es posible y no requiere reescribir el compilador.** El C que el `psc` emite hoy ya es, en su inmensa mayoría, C++ válido: **41 de los 44 golden tests compilan con `g++` sin tocar el código generado**, y el bundle completo del compilador queda a **228 errores de compilación C++**, de los que **170 (75 %) son identificadores que colisionan con keywords de C++** y **39 son designadores** (26 mezclados, 13 desordenados); los 9 restantes son cascadas. Ninguno es semántico. El desglose es reproducible con `scratch/audit_cpp/classify_cpp_errors.py` (§4.2). Un programa generado por el `psc` se compila como C++, enlaza con el runtime C actual y **se ejecuta** (probado con `g01_hello`).

**Estado de ejecución (2026-11-10).** F0 (decisiones A1–A7 firmadas, plumbing de familia, mangling) y **F1 completadas**: el bundle C++ del `psc` compila con `g++` y `clang++` en ISO C++20 estricto (`-pedantic-errors`), enlaza con el runtime C, el binario pasa los **895 tests**, y `psc build --backend=cpp` reconstruye el compilador en 32 s. Además **todo `std/` compila en C++**: `psc test . --backend=cpp` emite el bundle de test (que instancia la std completa, no el cierre podado del compilador) y pasa 895/895 — es el gate que evita que una regresión del emisor se esconda tras el DCE. El inventario de `s at i` de §14.1 está medido con el propio compilador (**75** sitios sobre `string`, no 175). F2 (sintaxis nueva) es lo siguiente.

**Ruta recomendada: A′ — "un solo emisor, dos dialectos; dos ejes separados".**

1. **Un solo emisor** (los 17.374 de `src/psc/codegen/`) con un parámetro de familia (`c` | `cpp`), **no** un segundo emisor. Un emisor paralelo son ~17k líneas duplicadas y deriva garantizada entre backends.
2. **Dos ejes que no se tocan a la vez**: primero *dialecto* (emitir C++ válido con la semántica de hoy), después *sintaxis* (sintaxis nueva con la semántica de hoy), y solo al final *semántica* (STL, RAII, sin COW). Cada fase deja un compilador que compila el siguiente: la cadena de bootstrap nunca se rompe hasta el paso irreversible, y ese paso se da con una red de seguridad ya construida.
3. **El hito que hace todo seguro es F2**, no F1: al final de F2 el `psc` (backend C) compila *cualquier* fuente en sintaxis nueva → es la **semilla universal** para reconstruir el compilador si la rama C++ se rompe. Por eso F2 va **antes** de F3.
4. **Python no es el puente.** Es un compilador completo y sólido del lenguaje 3.0.3, pero *también* tiene la semántica vieja y *también* emite C: extenderlo a C++/semántica-nueva es escribir otro compilador (56k líneas Python) para obtener lo mismo. Se queda como **oráculo independiente** de conformidad, no como vehículo.
5. **Backend JS: no.** El repo ya lleva a la web con wasm (`--target=wasm32-unknown-emscripten`, `std/web/` con 18 módulos, `runtime/pengu_js.c` + `pengu_js.js`, `pengu_wasm_shell.html`). Un backend JS nativo sería otro producto, no un paso de esta migración.

**Duración estimada (1 persona a tiempo completo): 11–16 meses.** Suma de las fases de §11: F0–F2 (lo que hay que hacer *antes* de tocar semántica): 5–7 meses. F3 (semántica + std): 4–6 meses. F4–F5 (doble autohosteo + limpieza): 2–3 meses. La incertidumbre grande sigue en F3, pero las mediciones de §14 la han estrechado (sobre todo R13 y FFI); F1 se re-estima al terminarlo. *(La versión anterior decía 8–13: era un número de titular que no salía de sumar las fases. Manda la suma.)*

**Los cuatro huecos de F3, ya medidos** (§14): el cambio `s at i`→`char` tiene **175 candidatos heurísticos** (132 al resolver el tipo por ámbito; 8 bucles `for`), de los que **29 son comparaciones mecánicas con un literal** y `to int` sobre un `string` real es **0** (de los 92 `to int` sobre índice, 91 son `ref to frozen byte` y 1 es un falso positivo); los omens algebraicos son **4 tipos y 18 variantes con payload**, ninguno en el compilador; la frontera FFI tiene **202 `declare`, de los que 87 cruzan `string`/`list`/`maybe`** y **0 runes por valor** (el trabajo de `@repr(c)` hoy es cero); y `ritual new` es **9 sitios** que pueden quedarse (se manglan) porque `born` es opcional.

### Las cinco afirmaciones del borrador que hay que corregir

| # | Dice el borrador | Lo medido | Consecuencia |
|---|---|---|---|
| 1 | "62k líneas" | `src/` = 61.839, pero el **cierre de compilación** (128 módulos `psc` + 25 de `std`) = **105.710 líneas** | El port de sintaxis no es 62k, es ~106k; pero solo ~3.100 son ediciones mecánicas (§3) |
| 2 | "el compilador no usa `derive`" | **Falso**: 44 declaraciones reales en el cierre (21 en `src/`, 20 tipos: `ByteSpan`, `Token`, `PsNode`, `Session`…; y 23 en `std/`, incluidos `derive Vinculum` en `std/oracle.pengu`) | F2 no puede "retirar `derive`" sin que el backend C aprenda antes a autogenerar `==` y cleanup (§7) |
| 3 | "`Rc`/`Arc` 82, `@mutates` 91 usos" | En el **cierre del `psc`**: `Rc`/`Arc`/`Weak` **0**, `@mutates` **0**, `fundere` **0**, `cyclus` **0** | El port inicial no toca ningún modelo de propiedad compartida (§8). Las cifras del audit son de todo el repo, fuera del cierre |
| 4 | "`psc fmt --migrate` aplica las transformaciones" | **No existe**: `psc fmt` es un normalizador *de texto* (`format_text`, `indent_line`) y solo acepta `--check --diff --stdin --indent --tabs --verbose` | Hay que escribir el migrador (§7). Es la herramienta que hace barato el port |
| 5 | "si Python está completo, la Ruta B es la más corta" | Python 3.0.3 está completo **para el lenguaje viejo** y **emite C**; no parsea el cierre del `psc` (6 fallos) ni tiene la semántica nueva | Extenderlo = escribir un compilador nuevo. Queda como oráculo (§2) |

**Lo que el borrador acierta**: el problema es el bootstrap, no C++; F1 no debe tocar el lenguaje; refactorizar el codegen para varios backends desde el día 1; no empezar por F4; no reescribir desde cero.

---

## 1. Método: qué se ha medido y con qué

Todo lo que sigue es reproducible desde la raíz del repo. La instrumentación está en `scratch/audit_cpp/`:

- `scratch/audit_cpp/closure_and_counts.py` — calcula el cierre de compilación del `psc` (siguiendo `import`) y cuenta sintaxis vieja **solo en código** (quita comentarios `#`/`##` y strings `"…"`/`"""…"""`). Sin `--per-file` da los totales; con él, la tabla por archivo.
- `scratch/audit_cpp/cpp_dialect_probe.sh goldens|goldens-strict|bundle|runtime` — compila el C emitido con `g++ -std=gnu++20 -fpermissive -D_Atomic= -fsyntax-only` y cuenta fallos; `goldens-strict` hace lo mismo **sin** `-fpermissive` y con la macro de `std_c/sds/sds.h` parcheada (el estado del runtime tras las 3 líneas de F1).
- `scratch/audit_cpp/count_string_iterations.py` — cuenta `for ch in s` y `s at i` sobre receptores declarados `string`, separando las rebanadas `s at a to b` (que no cambian de tipo). §14.1.
- `scratch/audit_cpp/count_semantic_hotspots.py` — omens algebraicos, `judge`, `weave ritual` y los mismos bucles/indexados en una pasada. §14.2/§14.4.
- `scratch/audit_cpp/audit_ffi_types.py` — clasifica cada `declare` del cierre (con companions `.d.pengu`) por tipo: escalar/puntero/rune/librería, y resuelve los `rune` recursivamente para ver si son `@repr(c)`. §14.3.
- `scratch/audit_cpp/classify_cpp_errors.py` — reparte los 228 errores de `g++` por causa raíz leyendo la línea de PenguScript que `#line` atribuye a cada uno. §4.2.
- `scratch/audit_cpp/dump_index_types.sh` — corre `psc emit-c --dump-index-types` sobre el cierre y resume cada `at` por tipo receptor/resultado; deja el TSV crudo en `scratch/audit_cpp/index_types.tsv`. §14.1.

**Línea base del repo (medida hoy, no de la documentación):**

| Dato | Valor | Cómo |
|---|---|---|
| Versión del fuente | 0.60.0 (`VERSION`); `pengu.toml` dice 0.53.9 y el README 0.53.9 (desactualizados) | `cat VERSION` |
| Binarios en `build/` | `psc` = 0.59.0, `psc-stage0` = 0.53.9 → **ambos stale** | `./build/psc --version` |
| Suite del compilador | **895 tests, todos pasan** | `./build/psc test .` |
| `src/` | **128** archivos `.pengu`, 61.839 líneas | `find`/`wc` |
| `std/` | **76** archivos `.pengu`, 82.915 líneas | `find`/`wc` |
| Bundle C del compilador | 138.978 líneas, 6.534.985 bytes, 16 `#include` | `./build/psc emit-c src/main.pengu --out=/tmp/psc_bundle.c` |
| Tiempo de emisión | **7,9 s** | `time` |
| Tiempo de compilación del bundle | **52,7 s** con `gcc -std=c11 -O2` | `time` |
| Stage-0 | 3 bundles C commiteados (~6,2 MB, 132.596 líneas), generados por `tools/gen_stage0.sh`, verificados byte a byte con `--check` | `bootstrap/`, `tools/` |
| Toolchain probada | g++ 16.2.1, clang++ 23.1.4; gcc/g++ de Arch; **MSVC no probado** | `--version` |

> Nota: `docs/BUILD_CACHE.md` documenta builds calientes de ~0,3 s y `psc check .` de 0,18 s con caché. El dato de 52,7 s es el *peor caso* (una sola TU, sin caché, `-O2`).

---

## 2. Estado del compilador Python (§2.1)

**Hecho: `../PenguScript-Python/` es un compilador completo y sólido del lenguaje 3.0.3 — el lenguaje viejo — que emite C.**

| Pregunta del §2.1 | Respuesta medida |
|---|---|
| ¿Compilador completo del PenguScript actual? | No del 0.60.0: del **3.0.3**. Commit `f6264b6 chore: snapshot stage0 before F11 switchover`, 1,2 GB, venv con Python 3.14.9 |
| ¿Qué backend usa? | **C**, no C++ (`pengu_parser/pengu_codegen/`). No hay backend C++ ni JS |
| ¿Cobertura de std? | Tiene **std propio** (~69.000 líneas). No es el `std/` de este repo |
| ¿Compila el `psc` actual? | **No tal cual**: parsea 198 de los 204 archivos de `src/` + `std/` (2 fallos en `src/`, 4 en `std/`); falla en `std/coro.pengu:72`, `std/filum.pengu:862` (`run_box of A`, valor de función genérica con argumento explícito), `std/ffi.pengu:129` (`align of T`), y 3 archivos con un bug del lexer de doc-comments (`## ## Memoria` tras un `weave` concreto) |
| ¿Qué tests tiene y cuántos pasan? | Suite amplia (`tests/{build,codegen,compat,compiler,conformance,lsp,psc,stdlib,tooling,wasm}`). En **este** checkout, `pytest -n 4 tests/compiler` = **199 failed / 633 passed**; el fallo típico **no es del compilador**: el `-I` del test coge `PenguScript/build/include/pengu_runtime.h` (ABI 4) en vez del runtime ABI 2 de 3.0.3 → `error: falló la aserción estática: "pengu_runtime.h ABI mismatch: bundle expects v2"`. El "1.400 tests pasados" de `AUDITORIA_AUTO_HOSPEDAJE.md` es de 3.0.1 y **no se reproduce sin aislar el include path** |
| ¿Tiene LSP, `fmt`, `test`, `doc`? | Sí, CLI completa (`init/new/add/remove/build/run/check --json/fmt/lsp/doc/assets/test`). `pengu_project.py` son 8.702 líneas |
| ¿Es extensible? | Sí (Lark LALR + `Indenter`, checker 8.444 líneas, inferencia 5.357). Pero **no es el camino** (§10) |

**Conclusión operativa.** Python sirve para tres cosas concretas y baratas:

1. **Oráculo de conformidad**: compilar los mismos programas con `psc` y con Python y comparar comportamiento; detecta regresiones del front end sin depender de goldens de texto. (Ojo: `scratch/audit/01-python-compiler-gaps.md` ya documenta 11 regresiones OLD→NEW; sirve como lista de casos a no perder.)
2. **Validador del migrador**: tras `psc migrate`, el parser de Python debe aceptar el resultado (parsea el 97% del fuente) como comprobación independiente de que la sintaxis nueva es válida.
3. **Plan B de emergencia**: si el backend C++ del `psc` se atasca de forma irrecoverable, Python 3.0.3 puede reconstruir un compilador del lenguaje viejo. No es un plan de migración, es un seguro.

**No sirve como vehículo de migración** porque: emite C, implementa la semántica vieja (COW incluido), no parsea el cierre del `psc`, y su std es distinto. Extenderlo a la semántica nueva = escribir el compilador nuevo en Python, que es *más* trabajo que extender el `psc` (que ya tiene el codegen y se auto-hospeda).

---

## 3. Uso de sintaxis vieja en el fuente del `psc` (§2.2)

Cierre de compilación: siguiendo `import` desde `src/main.pengu` → **153 módulos, 105.710 líneas** (128 de `psc`, 61.839 líneas + **25 de `std`, ~43.900 líneas**). El `psc` importa `std.filum` (vía `src/psc/dap/adapter.pengu:11`), que arrastra `coro`, `oracle`, `reactor`… y eso explica que el cierre std sea grande.

### 3.1 Totales (solo código, sin comentarios ni strings)

| Construcción | En el cierre | En `src/` solo | Comentario |
|---|---:|---:|---|
| `list of` | **2.480** | 1.178 | Renombrado mecánico a `vector of` |
| `map of` | **588** | 172 | Cambia la coma: `map of K to V` → `map of K, V` |
| `slice of` | 7 | 0 | Renombrado a `span of` |
| `array of` | 14 | 14 | `std::array` (misma forma) |
| `derive` | **44** (declaraciones) | 21 | **No es mecánico**: ver §7.3 |
| `Rc` / `Arc` / `Weak` | **0** | 0 | — |
| `@mutates` | **0** | 0 | — |
| `fundere` | **0** reales (3 menciones en textos) | 0 | — |
| `cyclus` | **0** | 0 | — |
| `enchanting` | 58 | 3 | Se conserva (bloques de métodos) |
| `declare` | **168** | 0 | 9 módulos FFI → `extern c:` |
| `banish` | 4.738 | 4.009 | Se conserva; en C++ pasa a `std::move` |
| `antiquus` | **180** | 22 | Bloques de C crudo: 34 usan tipos/funciones del runtime C |
| `@shared` | 13 | 0 | Ya existe y significa lo mismo en el doc C++ |
| `defer` | 1.631 | — | Se conserva (§2.15 del audit) |

### 3.2 `derive`: 44 declaraciones en el cierre

`src/`: `ByteSpan`, `Token`, `KeywordEntry`, `PsNode`, `PsLoopLabel`, `Comment`, `StringPart`, `StringInfo`, `CharInfo`, `AntiquusInfo` (`derive Par`); `KeywordTable`, `LexResult`, `PsAst`, `PsParseOptions`, `PsParseResult`, `SourceError`, `SourceFile`, `Session`, `InterpParseResult`, `MiField` (`derive Nexus`).
`std/` (23 declaraciones): `std/arena.pengu:96 Arena` (Nexus), `std/builder.pengu:89 StringBuilder` (Nexus), `std/sourcemap.pengu:78/89 Position, SourceSpan` (Par), `:102 SourceMap` (Nexus), `std/diagnostic.pengu:127/158/174 Span, Label, Diagnostic` (Nexus, Par, Imago), `191 RenderOptions` (Par), `213 DiagnosticBag` (Nexus), `std/json.pengu:160/195/215/226/254` (Nexus, Par, Imago — incluye el `omen` recursivo `JsonValue`), `std/jsonrpc.pengu:97/107/125/169/184/198` (Nexus, Par, Imago), **`std/oracle.pengu:122/135 Pair, Triple` (`derive Par, Vinculum, Imago, Nexus`)**.

**No hay `derive Drop` ni `derive Json` en el cierre.** `derive Vinculum` sí: **2** (`std/oracle.pengu:122/135 Pair`, `Triple`) → en el dialecto pasan a `bind T with Vinculum` + `weave hash` (§2.7 del doc). `derive Imago` en el cierre = **11** (diagnostic 3, json 2, jsonrpc 4, oracle 2). `derive Drop` (4) está fuera del cierre, en el resto de `std/`.

### 3.3 Dónde está el volumen (top del cierre)

| Archivo | `list of` | `map of` | `derive` | `declare` | `banish` | `antiquus` |
|---|---:|---:|---:|---:|---:|---:|
| `src/psc/codegen/expr.pengu` | 100 | — | — | 2 | 560 | — |
| `std/tally.pengu` | 574 | 10 | — | — | 29 | — |
| `std/atlas.pengu` | 142 | **368** | — | — | — | 6 |
| `std/scrolls.pengu` | 108 | — | — | 1 | 245 | 26 |
| `src/psc/lsp/server.pengu` | 35 | 16 | — | — | 314 | — |
| `src/psc/driver/build.pengu` | 66 | — | — | — | 279 | — |
| `src/psc/dap/adapter.pengu` | 44 | — | — | — | 251 | — |
| `std/archivum.pengu` | 114 | 14 | — | 21 | 88 | 2 |
| `std/json.pengu` | 76 | — | 5 | — | 67 | 25 |
| `src/psc/sema/symbols/table.pengu` | 36 | 66 | — | — | 57 | — |

Dos avisos de lectura: `std/atlas.pengu` **implementa** mapas ordenados (368 `map of`) → parte de ese módulo puede quedar redundante con `std::map`; y `std/json.pengu` es el módulo con más riesgo semántico del cierre (5 `derive`, `slice of`, 25 `antiquus`, `omen` recursivo con `Imago`).

---

## 4. F1: ¿se puede añadir un backend C++ al `psc` viejo? (§2.3)

Esta era la pregunta que el borrador quería resolver "compilando un módulo pequeño a mano". Se hizo algo mejor: **medir el 100% del compilador**.

### 4.1 El experimento de los 44 goldens

```
$ scratch/audit_cpp/cpp_dialect_probe.sh goldens
goldens: 41 OK, 3 FAIL  (g23_many.c g25_iteration.c g30_drop_table.c)
```

**41 de 44 programas generados por el `psc` compilan como C++ sin ningún cambio** en el código generado. Dos matices que conviene tener claros:

- Con `-fpermissive` compilan 41/44 tal cual. **Sin `-fpermissive` fallan los 44**, pero no por el código generado: fallan todos en la misma línea del header vendorizado `build/include/sds.h:83`, la macro `SDS_HDR_VAR` (`struct sdshdr##T *sh = (void*)(...)`, conversión implícita de `void*` que C permite y C++ no).
- **Parcheando esa única macro** (un cast explícito, 1 línea) y neutralizando los 2 `_Atomic` del runtime, **vuelven a compilar 41/44 sin `-fpermissive`** — verificado: los mismos 3 fallos, por las mismas causas. O sea: el runtime C está a **3 líneas** de ser C++-limpio.

Los 3 fallos son tres patrones concretos, no tres módulos:

| Fallo | Causa exacta | Arreglo |
|---|---|---|
| `g23_many`, `g25_iteration`, `g30_drop_table` | `designator order for field 'PenguSlice::len' does not match declaration order` / `goto` salta sobre una inicialización / `either all initializer clauses should be designated or none` | Ordenar designadores al emitir, no mezclar posicional+designado, y no saltar sobre inicializaciones |

### 4.2 El bundle completo del compilador

```
$ g++ -std=gnu++20 -fpermissive -D_Atomic= -fsyntax-only /tmp/psc_bundle.c
228 errores
```

Repartidos por causa raíz con `scratch/audit_cpp/classify_cpp_errors.py`, que lee la línea de PenguScript que `#line` atribuye a cada error (no adivina por el mensaje de g++):

```
$ scratch/audit_cpp/classify_cpp_errors.py
# errores: 228  (g++ -std=gnu++20 -fpermissive -D_Atomic=)
  170  keyword-ident
   26  designador-mezcla
   13  designador-orden
   10  otro
    9  cascada
```

| # | Causa | Errores | Dónde | Arreglo |
|---|---|---:|---|---|
| 1 | **Identificadores de Pengu que son keywords de C++** (`concept`, `template`, `new`, `explicit`, `public`, `operator`…) emitidos sin manglar | **170** (75 %) | `std/json.pengu` 54, `std/lingua.pengu` 30, `std/jsonrpc.pengu` 24, `src/psc/cmd/init.pengu` 23, `sema/generics/instantiate.pengu` 19, `lsp/server.pengu` 17 — 21 archivos | Una pasada de mangling en `names.pengu` (sufijo `_p`, como ya especifica el doc §1.3). **El fuente no cambia** |
| 2 | **Designadores mezclados con posicionales** (`either all initializer clauses…`) | **26** | `std/json.pengu:1143-1181` y todos los `return with Bool is b` / `is with` | Emitir todos los campos designados o todos posicionales; nunca mezclar |
| 3 | **Designadores fuera de orden** | **13** | `PenguSlice::len`, `PsHooks::arg_expr`, literales de `rune`/`omen` | Ordenar por el orden de declaración del struct |
| 4 | **Cascadas** de un error anterior (símbolo no declarado) | **9** | `sema/types/compat.pengu`, `generics/instantiate.pengu`, `cmd/init.pengu` | Desaparecen al arreglar 1–3 |
| 5 | **`otro`** (líneas que no contienen el token; al leerlas son también keywords: `concept`, `template`, `explicit`) | **10** | `cmd/build.pengu:320`, `cmd/init.pengu:178`, `types/compat.pengu:569` | Igual que 1 |

O sea: **keyword-mangling ≈ 75 % y designadores ≈ 17 %; los 9 restantes son cascadas**. El `_Atomic` del runtime no aparece en esta lista porque ya se neutraliza con `-D_Atomic=`; son 2 errores aparte (§4.3). Y el `goto` sobre inicialización no aparece en el bundle del `psc` (solo en `g25_iteration.c`); los 6 `goto` del inventario son de bajada de `for` etiquetado y compilan.

Y un dato que acota el trabajo: al aplicar el mangling de keywords *a mano* sobre el bundle (sed), los errores bajan de **228 a 125**, y de los 125 restantes ~80 son designadores. Es decir: **mangling + designadores ≈ 95% del problema**.

**Constructos C-only presentes en la salida** (inventario para F1): 3.561 *statement expressions* `__extension__(({…}))`, 339 *compound literals* designados, 41 designadores anidados de unión, 4 `_Atomic`, 9 `__attribute__`, 4 `_Static_assert`, 6 `goto`, 0 `typeof`, 1 `_Generic` (dentro de un string literal, no es código).

### 4.3 El runtime

```
$ g++ -std=gnu++20 -fpermissive -fsyntax-only -I. -Ibuild/include pengu_runtime.h
2 errores: '_Atomic' no nombra un tipo (pengu_runtime.h:5956, 5957)
```

`pengu_runtime.h` son 5.994 líneas; `runtime/*.c` otras 5.752; `std_c/` 14.880. **El runtime C está a tres líneas de compilar como C++**: los 2 `_Atomic` (`pengu_runtime.h:5956-5957`) y la macro `SDS_HDR_VAR` de `build/include/sds.h:83`. `sds.h` (vendored, 3ª parte) solo da avisos de conversión `void*` bajo `-fpermissive`; la solución limpia es compilar el runtime y `std_c` como C (siguen siendo C) y declararlos `extern "C"` desde el bundle C++.

### 4.4 Prueba de extremo a extremo: un programa del `psc` corriendo como C++

```
$ g++ -std=gnu++20 -fpermissive -D_Atomic= -I. -Ibuild/include \
      tests/golden_c/g01_hello.c /tmp/abi.cpp -o /tmp/g01_cpp \
      build/lib/libpengu_runtime.a build/lib/libminiz.a -lm -pthread -ldl
$ /tmp/g01_cpp
hello, pengu
```

El único símbolo que hubo que aportar fue `pengu_abi_version()` (se mangla en C++; en un backend real se declara `extern "C"`). **Conclusión: la cadena "C emitido + runtime C" ya es compilable y ejecutable como C++ con arreglos léxicos.**

### 4.5 Por qué esto cambia la estimación de F1

El acoplamiento del emisor a C está concentrado y es pequeño de tocar:

| Métrica | Valor |
|---|---:|
| Líneas de `src/psc/codegen/` | 17.374 |
| Archivos con referencias `pengu_*` | **11** |
| Llamadas `emit.line` (puntos de emisión) | 375 |
| Sitios que emiten `__extension__(({` | **38** |
| Plantillas que emiten designadores | **8** |
| Sitios que emiten `goto` | **6** |

**F1 no es "escribir un emisor C++": es añadir un dialecto al emisor existente.** Presupuesto: tocar `ctype.pengu` (nombres de tipos), `names.pengu` (mangling), `expr.pengu`/`stmt.pengu` (literales, bloques, bucles), `bundle.pengu` (includes/`extern "C"`), `drop.pengu` (cleanup), `api.pengu` (orquestación), más driver/manifest/toolchain. Del orden de **1.500–3.000 líneas tocadas**, no 17.000.

**Un aviso honesto sobre F1**: el doc C++ exige `-std=c++20` estándar sin extensiones GNU, y los 3.561 *statement expressions* son GNU. F1 se puede cerrar con `-std=gnu++20` (transitorio) y una sub-fase **F1b** que los sustituya por lambdas `[&]{…}()` (los 38 sitios) para cumplir el contrato del doc. Recomiendo hacer F1b inmediatamente después de F1: es barato y evita que la deuda se filtre a F3.

### 4.6 Lo que F1 **no** resuelve (y hay que decir desde el principio)

- **ABI/FFI**: en cuanto el backend emite `std::string`, un `declare` que espera `PenguString` deja de valer. F1 compila el C++ *con los tipos C* (`PenguString`, `PenguList`…) para no cambiar la frontera; la frontera estricta es F3 (el audit lo llama "el precio de la representación").
- **COW**: el runtime COW sigue vivo en F1 (compilado como C). Quitarlo es F3.
- **Rendimiento**: el binario C++ de F1 es el mismo modelo de datos, así que el rendimiento es comparable; la copia profunda llega con F3.

---

## 5. Dependencias `psc` ↔ `std` (§2.4)

**El cierre es de 153 módulos: 128 del `psc` + 25 de `std`. No hay ciclos: ningún archivo de `std/` hace `import psc.*`.**

Los 25 módulos std del cierre, por capas (de hoja a raíz):

| Nivel | Módulos | Notas |
|---|---|---|
| 0 | `io`, `spark` | Únicos sin dependencias internas |
| 1 | `builder`, `coro`, `oracle`, `rites`, `scrolls`, `sourcemap` | — |
| 2 | `atlas`, `chronicle`, `compass`, `filum`, `lingua`, `ward` | `filum` = 57 `declare` |
| 3 | `memoria`, `reactor`, `tally` | `tally` = 574 `list of` (el mayor del cierre) |
| 4 | `archivum`, `arena`, `net` | `archivum` 21 `declare` |
| 5 | `digest`, `json`, `toml` | — |
| 6 | `diagnostic`, `jsonrpc` | `json`/`jsonrpc`: riesgo semántico alto (§3.3) |

Niveles calculados con el grafo real de `import` (nivel = 1 + máx(nivel de las dependencias)). El orden de migración recomendado es por nivel ascendente; los de nivel 5–6 (`json`, `jsonrpc`) se dejan para el final.

**¿Se puede migrar `std` antes que el `psc`?** Sí, y **conviene**: capa 0 primero, en paralelo a F2 (el audit lo llama F2.5). El `psc` solo necesita que esas APIs sigan existiendo con la misma semántica; el port interno es invisible para él.

**¿Hay dependencia circular?** No. La única dependencia "rara" es `psc.dap.adapter → std.filum` (el adaptador de depuración), que arrastra el subsistema de hilos al cierre. Se puede romper opcionalmente (cargar el DAP aparte) para reducir el cierre en ~8 módulos, pero no es necesario.

**`derive Json`**: no existe en el cierre; `std/json` implementa su codec a mano. La retirada de `@json`/`derive Json` (fase 5) **no afecta** al bootstrap.

**Dos notas de secuenciación de F2.5:**

- **`std/filum` puede quedarse para F3.** Es el módulo con más FFI del cierre (57 `declare`, de los que 44 cruzan `string`; 13 `@shared`) y su API está llena de handles. F2.5 empieza por nivel 0–1 y baja; si `filum` no se puede migrar sin tocar su semántica de hilos, se queda en C durante F2.5 y se migra con el resto del FFI en F3.
- **`std/atlas` es candidata a desaparecer.** Implementa un mapa ordenado (368 `map of`) que en F3 es `std::map`; tras la migración puede quedar como capa fina o retirarse y dejar `map`/`umap` del lenguaje (§14.2 del doc). Es una **reducción** de superficie, no un problema; decisión en F3/F5.

---

## 6. Build, stage-0 y tiempos (§2.5)

| Pregunta | Respuesta |
|---|---|
| ¿Cuánto tarda `psc build` del `psc`? | Emitir 7,9 s; compilar el bundle 52,7 s (`gcc -O2`, una TU). Con caché, build caliente ~0,3 s y `psc check .` 0,18 s |
| ¿Y en C++? | Estimación 1,3–2× el tiempo de C en la misma TU (plantillas + `std::`). Medido: `-fsyntax-only` del bundle en C++ = 1,95 s; el compilado completo está por medir en F1 |
| ¿Cómo se regenera stage-0? | `tools/gen_stage0.sh` emite 3 bundles (`linux_x64`, `macos_arm64`, `windows_x64`) con `psc emit-c --target-os/--target-arch/--target-compiler`; `--check` compara byte a byte. `tools/build_bootstrap.sh` los compila con `cc -std=c11 -O2` + `libpengu_runtime.a libminiz.a libre.a` |
| ¿Es reproducible? | Sí: bundle commiteado + `--check` en CI. Depende del `psc` que lo emite (por eso el `--check` falla si el emisor cambia) |
| ¿Dos stage-0 en paralelo? | **Sí, y es trivial**: `gen_stage0.sh` es una tabla de 3 líneas; añadir `psc_stage0_<os>_<arch>_cpp.c` (o `.cpp`) y un `--backend` al `emit` es un cambio de ~10 líneas. Recomendado desde F1: el stage-0 C++ se convierte en el *smoke test* permanente del dialecto |
| ¿El manifiesto sabe de C++? | **No.** `pengu.toml` solo tiene `cc`, `cflags`, `ldflags`; `src/psc/driver/manifest.pengu` no conoce `cxx`. `psc build --cc=g++` hoy **falla**: pasa `-std=c11` a `g++` y muere en `sds.h`. Hay que añadir `family`, `cxx`, `cxxflags`, y elegir flags por familia |
| ¿`--split-codegen`? | Existe (`--split-codegen --jobs=N`), pensado para paralelizar la compilación del bundle. Es la válvula para el tiempo de compilación en C++ |

**Riesgo de tiempo de compilación (R1 del audit)**: 105.710 líneas de Pengu → 138.978 líneas de C en una sola TU (52,7 s a `-O2`, medido). A `-O0` el audit midió ≈ 1,0 s por 1.605 líneas. Con plantillas de C++ puede duplicarse. Mitigaciones ya previstas: PCH (`--pch`), `-O0` en debug, `--split-codegen` y, en F5, partir el bundle en varias TUs.

---

## 7. F2: ¿se puede poner la sintaxis nueva como alias de la vieja? (§2.6)

**Sí, en su mayor parte es "solo spelling", y el parser del `psc` está preparado para hacerlo barato.**

### 7.1 Por qué es barato: los tipos son *soft words*, no keywords

En el `psc`, `list`, `map`, `slice`, `array`, `ref`, `frozen`, `many`, `maybe`, `result`, `opaque` **no son keywords**: se reconocen como palabras contextuales en `src/psc/parse/types.pengu` (`ptype_parse_type`). Los keywords de verdad viven en `src/psc/token.pengu` (`add_keyword … KwMany`). Por tanto:

- `vector of T` = alias de `list of T`, `span of T` = alias de `slice of T`, `umap of K, V`/`set of T` = alias de las tablas actuales: **un `if` en el parser de tipos**, sin tocar el lexer.
- `unique`/`shared`/`weak` son tipos de frontera → misma mecánica, **sin colisión** con el `weave unique` de `std/tally.pengu:1027` (que seguirá siendo válido).
- `born`/`die`/`mirror`/`operator`/`inherit`/`extern` son **contextuales según el doc §1.3** (solo son palabra en su posición) → `die`, `shared`, `span` como identificadores siguen funcionando. Medido en el cierre: `die` 0 usos como identificador, `shared` 0, `span` 45 (params/vars, todos válidos porque `span of` es contextual).
- `map of K to V` → `map of K, V`: cambio en el parser de tipos y en el *emitter* de tipos, nada más.

### 7.2 Lo que **no** es azúcar y hay que decidir

| Construcción nueva | ¿Azúcar sobre lo de hoy? | ¿La usa el `psc`? |
|---|---|---|
| `born` / `die` (constructor/destructor reales) | **No**: exige RAII y orden de destrucción. En C se baja a `<T>_new`/`_pengu_cleanup_T` (§2.8 del audit) | No los usa (usa `ritual new` y `derive Nexus`) |
| `derive` retirado → `==`/`<=>`/RAII automáticos | **No** en el backend C: hay que autogenerar `==` campo a campo y cleanup para *todos* los tipos | **Sí**: 44 declaraciones (§3.2) |
| `inherit` (herencia real con upcast) | **No** en C: layout con base embebida; en C++ sí es natural | No |
| `unique`/`shared`/`weak` | `shared`/`weak` = `Arc`/`WeakArc` actuales (sí); `unique` es nuevo | No |
| `extern c:` / `extern cpp:` | `extern c:` = `declare` actual (sí); `extern cpp:` solo tiene sentido en C++ | 168 `declare` |
| `@repr(c)`, `operator`, `for ch`, bucles como expresión | Mixto | No |
| `regnum` | Nombre nuevo para el prefijo de módulo | No |

**El único nudo real es `derive`**, y tiene solución ordenada (§7.3).

### 7.3 El orden correcto para retirar `derive` (el hueco del plan del audit)

El audit dice que `derive` desaparece en F2 y que el backend C "baja" las construcciones nuevas (§2.8). Pero `derive Nexus` es lo que hoy genera el cleanup que usan los 4.738 `banish` del cierre. Si F2 borra las 44 líneas `derive` del fuente **antes** de que el backend C sepa generar cleanup automáticamente, el compilador empieza a fugar memoria (y con `derive Par`, a perder `==`). Orden correcto, en F2:

1. **Primero el backend C**: que genere `_pengu_cleanup_T` y `==`/`<=>` campo a campo **para todo tipo automáticamente** (lo que hacía `derive`), y que `banish` siga funcionando. Criterio: los 895 tests pasan **con las 44 líneas `derive` todavía presentes** (no deben cambiar nada: ahora son redundantes).
2. **Después el fuente**: borrar las 44 líneas `derive` (mecánico, con `psc migrate`), recompilar, 895 tests.
3. **Después el parser**: `derive` pasa a error con fix-it (o se acepta deprecado hasta F3).

Esto convierte una retirada semántica en dos pasos verificables y elimina el riesgo de "F2 rompe el bootstrap".

### 7.4 El migrador: hay que escribirlo (`psc fmt` no vale)

`src/psc/cmd/fmt.pengu` es un **normalizador de texto** (`format_text`, `normalize_code`, `indent_line`, `triple_count`): no hay AST ni pretty-printer. El doc promete `psc fmt --migrate`, pero **no existe**. Hay que añadir un comando nuevo, `psc migrate`, que:

- lexea con el lexer real (respeta strings, `##` doc-comments, `antiquus` y `"""`),
- aplica sustituciones **solo en posición de código** (no en comentarios ni strings): `list of`→`vector of`, `slice of`→`span of`, `map of K to V`→`map of K, V`, `declare`→`extern c:`, `Rc`/`Arc`→`shared`, retirada de `@mutates`/`cyclus` (los 9 `ritual new` **no** se renombran: §14.4),
- preserva el formato (reemplazo de tokens, no reimpresión),
- tiene `--check`/`--diff` para CI.

**Casos límite que el spec tiene que fijar antes de escribir código** (todos existen en el fuente del `psc`):

| Caso | Dónde | Regla |
|---|---|---|
| Comentarios `#` y doc `##` | 1.680 líneas `^## ##` en `src/` | No se tocan; el migrador solo sustituye fuera de comentario (incluido `##` dentro de un string) |
| Strings `"…"` con `#`, `of`, `map of`… | `src/psc/cmd/web.pengu:46` (JSON con `{"…"}`) | No se tocan; el lexer real delimita |
| Strings triples de tres comillas | `std/scrolls.pengu`, tests | No se tocan; `triple_count` del formatter ya sabe contarlas |
| Raw `r"…"` y raw triple | `antiquus` y tests | No se tocan |
| `antiquus … end` | 180 en el cierre | Se migra el cuerpo como código normal, pero **no** se reindenta el bloque (lo reescribe el usuario) |
| Continuaciones de línea | `_merge_chain_continuations` del parser Python | Respetar la línea física: la sustitución no parte una expresión en dos |
| `map of K to V` anidado | `map of string to map of string to int` | Sustitución por comas con paréntesis/`of` anidados, no un `sed` |
| `derive` | 44 declaraciones | Borrar la línea; el `==`/cleanup lo emite el backend (§7.3) |
| Identificadores reservados | 66 (§14.6) | Renombrar por token con tabla explícita (`result`→`res`, `span`→`sp`), nunca por texto |

**Lo que el migrador no puede hacer**: las 87 firmas FFI (§14.3) son decisiones de tipo, no de token y van a mano. Las 29 comparaciones `(s at i) == "x"` **sí** son léxicas (se convierten en `'x'`); el resto de sitios de `s at i` (§14.1) queda para revisión.

Es un comando de ~500–900 líneas, se prueba con los 895 tests y con el parser de Python como oráculo. **Es la herramienta que convierte "106k líneas" en "3.100 sustituciones revisadas".**

### 7.5 Riesgo léxico real (y su solución)

El emisor C++ necesita **mangling de keywords de C++** porque el fuente usa identificadores legales en Pengu que en C++ no lo son: `new` (922 apariciones: es el constructor `ritual new`), `module` (484), `this` (271), `explicit` (70), `public` (68), `concept` (61), `private` (56), `template` (53), `requires` (41)… El doc §1.3 ya define la regla (sufijo `_p`: `class_p`). Es **una función** en `names.pengu` aplicada a todo identificador emitido; el fuente no se toca. Sin ella, F1 no compila (son ~120 de los 228 errores).

---

## 8. F4: ¿depende el `psc` de la semántica vieja? (§2.7)

Pregunta: si el backend C++ cambia a `std::vector`/`std::string` (sin COW), RAII y `map` ordenado, ¿el fuente del `psc` sigue siendo correcto?

| Dependencia | En el cierre | Veredicto |
|---|---:|---|
| COW explícito (`is_shared`, `make_unique`, `.clone()`) | 0 usos reales | El fuente **no pide** COW; solo se beneficia de él |
| `derive Drop` / `Imago` / `Vinculum` | 0 `Drop` · 11 `Imago` · **2 `Vinculum`** (`std/oracle`) | `Imago`/`Drop`: sin problema (copia por defecto y RAII). `Vinculum`: 2 sitios a mano → `bind` + `weave hash` |
| `Rc` / `Arc` / `Weak` | 0 | — |
| `@mutates` | 0 | — |
| `fundere` | 0 | — |
| `cyclus` | 0 | — |
| `banish` | 4.738 | Sigue siendo válido (en C++: `std::move` + destructor). Los `banish` de temporales desaparecen solos |
| `antiquus` | 180 bloques, **34 con `pengu_*`/tipos C** | **Trabajo manual real**: hay que portarlos a C++/STL o aislarlos tras `extern c` |
| `enchanting` | 58 | Se conserva (métodos) |
| `@shared` | 13 (solo `std/filum`) | Ya significa lo mismo en el doc C++ |

**Dónde sí hay riesgo (y no es el que el borrador temía):**

1. **Rendimiento, no corrección.** `var b is a` pasa de O(1) (COW) a copia profunda. En un compilador que copia ASTs, listas de tokens y strings, esto puede multiplicar el tiempo. Se mide en F3 con los 895 tests y con `time psc build`; si duele, la salida es `ref to`, no volver al COW.
2. **`antiquus`** (§8, 34 sitios): es el único trabajo manual no mecánico del port, junto con `std/json`.
3. **Orden de iteración de `map`.** Hoy `map` es una tabla hash (orden de cubeta); en C++ `map` es ordenado por clave. Si el compilador itera un `map` para decidir el orden de la salida, el bundle cambia de orden (determinista, pero distinto). Revisado: en el cierre las iteraciones de mapa están en CLI (`src/psc/cli/args.pengu:190`) y LSP, **no** en el emisor; aun así, regla para F3: *el compilador nunca decide el orden de salida iterando un `map`/`umap`; si lo necesita, lista paralela de claves*. Y `umap` (hash de C++) tiene orden no especificado → **prohibido iterarlo para emitir**.
4. **`std::variant` sin excepciones** para `omen`/`result` (`-fno-exceptions`): el doc ya da la receta (`pengu/core.hpp`), pero es el punto donde un compilador C++ se pone quisquilloso. Es F3, no F1.

**Cómo se comprobará, no cómo se supone**: F3 no se acepta por inspección. Criterio binario: `psc` (compilado por el `psc` de F2) emite el bundle C++, ese binario pasa los 895 tests, y la salida de los goldens coincide funcionalmente con la del binario C. Además ASan/UBSan sobre la suite (`--sanitize=address` ya existe en el driver).

---

## 9. Arquitectura del codegen y coste de un backend JS (§2.8)

### 9.1 Estado real

- **No hay trait/interfaz `Backend`.** `src/psc/codegen/api.pengu` expone `weave generate_c with p as ref to program.SemaProgram, o as CgOptions into CgResult` y devuelve un `string` (el bundle). `emit.pengu` es un escritor de bajo nivel (`CgEmitter` con `sb`, `indent`, `temps`) y `ctype.pengu` es "la única puerta de tipos C".
- El acoplamiento a C es **estrecho y localizado**: 381 referencias `pengu_*` en **11 archivos**, 375 `emit.line`, 40 `PenguString`, 13 `PenguList`, 12 `PenguMap`.
- Ya existe un segundo *target* (wasm), pero es un target de **C**: `--target=wasm32-unknown-emscripten` cambia el compilador y la plataforma, no el lenguaje emitido (`src/psc/driver/target.pengu`, `std/web/`).

### 9.2 Recomendación: `Dialect`, no `trait Backend`

Añadir un trait con `emit_stmt`/`emit_expr`/`emit_type`/`emit_decl` es atractivo en teoría, pero con un solo emisor real implica:

- duplicar ~17k líneas o llenar el código de `if dialect == cpp` de todos modos,
- deriva entre backends (riesgo R9 del audit: dos emisores que se separan),
- y no resuelve nada que un parámetro de familia no resuelva.

La forma que sí escala con este código es **una familia de target** (`c` | `cpp`) atravesando el emisor, con funciones pequeñas por familia donde de verdad difieren:

| Punto | `c` | `cpp` |
|---|---|---|
| `ctype.pengu` | `PenguString`, `PenguList`, `PenguMap` | `std::string`, `std::vector`, `std::map` (F3) o los mismos tipos C (F1) |
| `names.pengu` | sin mangling | sufijo `_p` para keywords C++ |
| `expr.pengu` (literales) | `(T){.a=1}` | `T{.a=1}` ordenado, sin anidar unión |
| `stmt.pengu` (bloques) | `__extension__(({…}))` | lambda `[&]{…}()` |
| `bundle.pengu` | `#include`, `_Static_assert` | `extern "C"`, `static_assert`, runtime C declarado |
| `drop.pengu` | `_pengu_cleanup_T` | RAII (F3) / cleanup (F1) |

Con esto, **F1 es un dialecto del emisor** (1.500–3.000 líneas tocadas) y **F3 es el mismo emisor con otra capa de tipos** (no un backend nuevo). Es también el punto de extensión correcto para un futuro JS, si alguna vez se quiere.

### 9.3 Backend JS: no ahora, y probablemente nunca

- **La web ya está cubierta**: `--target=wasm32-unknown-emscripten`, `std/web/` (18 módulos: `dom`, `canvas`, `http`, `websocket`, `storage`, `crypto`, `router`…), puente `runtime/pengu_js.c` (293 líneas, callbacks con generación) + `runtime/pengu_js.js`, `pengu_wasm_shell.html`, `docs/CROSS_COMPILE.md`. Un programa Pengu corre en el navegador hoy.
- Un `--backend=js` nativo (Node sin emscripten) es **otro producto**: exige reimplementar el modelo de memoria, `Result`/`defer`, `unique`/`shared` (que en JS no existen), los 4.738 `banish`, y toda la std de sistema (`archivum`, `net`, `coro` → event loop). Meses, y el resultado sería un lenguaje distinto con la misma sintaxis.
- Si algún día se hace: el dialecto de §9.2 es el punto de extensión; el codegen de C++ no se "reutiliza cambiando el target type" (las construcciones son distintas), pero sí se reutilizan lexer, parser, checker y el 80% de la lógica de emisión de sentencias.

---

## 10. Las rutas: comparación y recomendación (§3)

| Criterio | **A′** (un emisor, dos dialectos) | B (bootstrap con Python) | C (híbrida) | D (greenfield) |
|---|---|---|---|---|
| ¿Rompe el bootstrap? | **No**: cada fase compila la siguiente; F2 crea semilla universal | Sí en el salto (Python debe compilar el `psc` nuevo) | No en F1; sí en el salto por Python | N/A |
| Depende de Python | No (solo oráculo) | **Sí, totalmente** | Sí, para el salto grande | No |
| Estado de Python | — | Completo para 3.0.3, **emite C**, no parsea el cierre | Igual: hay que completarlo a C++ + semántica nueva | — |
| Trabajo manual (antiquus, json, std) | Sí, acotado | Sí, el mismo, más Python | Sí, el mismo | Enorme (106k líneas desde cero) |
| Mantener 2 modelos semánticos | Solo en F3 (C sigue con el viejo para la semilla) | No (un solo modelo) | Solo durante la transición | No |
| Reversibilidad | **Alta** hasta F3 | Baja (depende de Python) | Media | Ninguna |
| Estimación (desglosada en §11) | **11–16 meses** | 10–16+ (y riesgo de contaminar el `psc` con bugs de Python) | 9–15, **sin desglosar** y sin contar completar el emisor C++ en Python | 18+ |

**Recomendación: A′.** Razones, en orden de peso:

1. **Los datos**: el C emitido ya es 93% C++ válido (41/44 goldens) y los 228 errores del bundle son **todos léxicos**: keywords en identificadores (170), designadores desordenados o mezclados (39), cascadas (9) y 10 que al leerlos son también keywords. No hay ninguna señal de que el emisor sea "irrecuperable", que es la premisa de la Ruta B.
2. **Python no aporta semántica nueva**: tiene exactamente el mismo modelo viejo (COW, `derive`) y emite C. La ventaja teórica de B ("un solo modelo semántico") es falsa: el modelo nuevo hay que escribirlo igual, en Python o en Pengu, y en Python es un compilador nuevo desde cero.
3. **El riesgo dominante es el bootstrap**, y A′ lo elimina por construcción: F1 deja el backend C intacto, F2 deja un compilador (C) que acepta ambas sintaxis y es semilla universal, y F3 se puede intentar, fallar y volver a intentar sin quedarse sin compilador.
4. **La Ruta C no aporta nada que A′ no tenga**: era la respuesta a "si Python está completo, saltamos con Python"; con A′ el salto lo hace el propio `psc` con el dialecto C++, sin tercera herramienta.
5. **D (greenfield)**: descartada; 106k líneas de cierre, un LSP, un formateador, un DAP y 895 tests no se tiran.

---

## 11. Plan por fases (con criterios binarios de aceptación)

Convención: **cada fase termina en un repo verde** (`./build/psc test .` = 895/895, `tools/gen_stage0.sh --check` OK) y con un binario que compila el siguiente. Las estimaciones son persona-meses de 1 dev a tiempo completo; la confianza se indica.

### F0 — Andamiaje e instrumentación · 3–4 semanas · confianza alta

- Congelar línea base: 895 tests, `--check` de stage-0, goldens C.
- Añadir al emisor el parámetro **familia** (`c` | `cpp`) sin cambiar la salida C (plumbing puro).
- `pengu.toml`: sección `cxx`, `cxxflags`, `family`; driver elige flags por familia; `psc build --backend=cpp`, `psc emit-cpp`.
- `tools/gen_stage0.sh`: 4º/5º bundle por familia (`--backend` en `emit`).
- CI: `g++` y `clang++` además de `gcc`; job `cpp-dialect` que corre `scratch/audit_cpp/cpp_dialect_probe.sh goldens` y exige 44/44.
- Un script de *burndown* (p. ej. `tools/check_cpp_dialect.sh`): compila el bundle del `psc` con `g++` y publica el número de errores (empieza en 228).
- **Aceptación**: la salida C es byte-idéntica a la de hoy (goldens + stage-0); el job `cpp-dialect` mide y publica el número.

### F1 — Dialecto C++ con la semántica de hoy · 1,5–2 meses · confianza media-alta

- Mangling de keywords C++ (`names.pengu`) — el mayor bocado, ~120 errores. **Hecho** (F0.2).
- Literales de `rune`/`omen`: designadores ordenados, sin mezcla, unión anidada bien emitida. **Hecho** (F0.3) + literales compuestos eliminados en F1 (arrays locales, vistas `antiquus`, `pengu_string_split`).
- `goto` sobre inicializaciones (6 sitios): **no aparece en el bundle**; los 6 `goto` inventariados compilan. Solo falla en `g25_iteration.c` (golden).
- Runtime: `_Atomic` (2), `extern "C"` para `pengu_runtime.h` + `std_c`, `pengu_abi_version`. **Hecho** (F1): macros `PENGU_ATOMIC_INT32`, guards `extern "C"` en `pengu_runtime.h` y `std_c/sds/sds.h`, ABI pin con linkage C.
- `bundle.pengu`: `static_assert`, `extern "C"`, includes C++. **Hecho**.
- Burndown **228 → 0** y gate con `-std=c++20 -pedantic-errors` (no solo `gnu++20`). **Hecho**.
- **Driver por familia** (F1): `psc build`/`psc run`/`psc test --backend=cpp` eligen g++/clang++, emiten `bundle.cpp` y enlazan con el runtime C. **Hecho**: el `psc` se reconstruye con `--backend=cpp` en 32 s, el binario pasa 895/895, y `psc test . --backend=cpp` compila la std completa como C++ (895/895). Handles opacos de la FFI (`reactor`) cruzan como `void *` en C y C++ (A2).
- `--dump-index-types` (**hecho** en F1, no en F3): el emisor imprime a stderr, por cada `at`, `archivo:línea<TAB>tipo receptor<TAB>tipo resultado`; `emit-c --dump-index-types` da la lista exacta que sustituye a los 175 candidatos heurísticos de §14.1. Medido: 75 sitios sobre `string`.
- **Aceptación**: `psc` emite un bundle que compila con `g++` y con `clang++` (`-std=c++20 -pedantic-errors`), enlaza con el runtime C, **y el binario resultante pasa los 895 tests**. Es decir: el `psc` se auto-hospeda en C++ con la semántica de hoy. **Cumplida** (`tests/cpp_backend/run.sh` y `--link`). Los tres stage-0 C++ se generan y verifican reproducibles en CI (`--stage0`, `tools/gen_stage0.sh --family=cpp`); no se commitean aún porque durante F1–F3 el bootstrap canónico es el C y duplicar ~20 MB por commit no aporta: pasan a commiteados en F4.
- **Aceptación (instrumentación)**: `psc emit-c --dump-index-types src/main.pengu` emite la lista exacta de sitios `at` del cierre con sus tipos. **Cumplida**: 1.765 líneas, 1.649 sitios distintos, de los que **75** son `string at i → string` (el resto: 1.302 `list`, 242 `ref to frozen byte`, 18 `list*`, 11 `map`). Sustituye a los 175 candidatos heurísticos de §14.1.

### F1b — C++20 estricto · 2–3 semanas · confianza alta

- Sustituir los 3.561 *statement expressions* por lambdas `[&]{…}()` (38 sitios de emisión). Matiz medido en F1: g++ y clang++ **aceptan** `__extension__(({…}))` incluso con `-std=c++20 -pedantic-errors` (la extensión está silenciada), así que esto **no** es necesario para F1 ni para el gate; solo lo será para MSVC (A5 permite dejar Windows en el backend C hasta F5) y para un compilador sin extensiones GNU.
- `-std=c++20 -Wall -Wextra -Wpedantic`, cero warnings (contrato del doc §1.2/§1.3).
- **Aceptación**: probe del audit (`scratch/audit_cpp/probe_*.cpp`) y bundle del `psc` limpios con `-std=c++20 -Wpedantic`; 895 tests.

### F2 — Sintaxis nueva, semántica vieja · 2–3 meses · confianza media

- Parser dual: alias de tipos (`vector`/`span`/`umap`/`set`), `map of K, V`, `born`/`die`/`mirror` (contextuales), `inherit`, `extern c:`/`extern cpp:`, `regnum`, `unique`/`shared`/`weak`.
- Backend C: autogenerar `==`/`<=>`/cleanup para todo tipo (requisito para retirar `derive`, §7.3); bajar cada construcción nueva según la tabla de paridad (§2.8 del audit).
- **Paso 1**: backend C autogenera y los 895 tests siguen verdes *con* `derive` (redundante).
- **Paso 2**: `psc migrate` (token-level, `--check`/`--diff`) y borrado de las 44 líneas `derive` + 2.480 `list of` + 588 `map of` + 7 `slice of` + 168 `declare` del fuente del `psc` y de los 25 módulos std del cierre.
- **Paso 3**: `derive`/`Rc`/`Arc`/`@mutates`/`cyclus` → error con fix-it (solo en sintaxis nueva; el modo viejo sigue aceptándolos hasta F5).
- F2.5 en paralelo: migrar `std/` por niveles (nivel 0: `io`, `spark`; 1: `builder`, `coro`, `oracle`, `rites`, `scrolls`, `sourcemap`; 2: `atlas`, `chronicle`, `compass`, `filum`, `lingua`, `ward`), módulo a módulo.
- **Hecho (F2.1, 2026-11-11)**: alias de tipos en parser y expresiones (`vector of T`, `span of T`, `map of K, V` aceptando `to` o `,`), comando nuevo `psc migrate` (token-level sobre el AST: `--check`/`--diff`, idempotente, no toca comentarios/strings ni los `to` de rangos y `result`) y migración del árbol completo (130 archivos, 2.480 `list of` + 588 `map of` + 7 `slice of` + renames). Verificación decisiva: el bundle C del `psc` es **byte a byte idéntico** antes y después de migrar (140.799 líneas), `psc test .` y `psc test . --backend=cpp` 895/895, `tests/regress_migrate.sh` nuevo. `umap`/`set`/`uset` y la retirada de `derive` quedan para F2.2/F2.3.
- **Hecho (F2.2, 2026-11-11)**: igualdad estructural en el runtime (`PenguEqFn`, `pengu_{array,list,slice,maybe,result,map}_equal`, `pengu_map_find_eq` por contenido) y módulo nuevo `src/psc/codegen/eq.pengu` que emite `_pengu_eqv_<ty>`/`_pengu_eq_<T>` campo a campo (string→`pengu_string_equal`, contenedores→helpers, nominales→`_pengu_eq_*`, omen con payload→`switch` por `tag`, sin payload→`==` del enum); `==`/`!=` de runas/ecos/omens ya no usan `memcmp` sobre punteros. `banish` ya no exige `derive Nexus` (toda runa/eco tiene `_pengu_cleanup_T`). `derive` retirado salvo `Json` (F5) y `Drop` (F2.3): `Par`/`Ordo`/`Nexus`/`Imago`/`Vinculum`/`Donum` dan `E0005` con el sustituto exacto, y `psc migrate --drop-derive` reescribe las cláusulas (123 archivos migrados, idempotente). Verificación: 895/895 en C y `--backend=cpp`, 88 regresiones, 44 goldens regenerados, gate g++ 0 errores.
- **Aceptación**: `./build/psc test .` 895/895 **con los dos backends**; `gen_stage0 --check` OK; el fuente del `psc` no contiene sintaxis vieja (ni `derive`: se retira en el paso 2); conformance C completo.
- **Aceptación de herramientas** (las tres cosas dejan de ser "trabajo de F2" y pasan a criterio binario):
  - `psc fmt --check` sobre el fuente ya migrado no produce cambios (verificado en §14.5: el formatter es textual y acepta `born`/`die`/`operator`/`inherit`/`extern c:`/`regnum`). Además, test de regresión con esas construcciones.
  - `psc doc --check` sobre un módulo con `born`/`die`/`operator`/`inherit`/`regnum` **renderiza bien, no solo no rompe**: `weave born with x as int` aparece como constructor de `T`, `weave operator () with x as int` como call operator, `rune … inherit Base` muestra la base. Sin esto, la doc miente en F3.
  - `psc lsp`: hover sobre `born` dice "constructor de `T`"; go-to-definition sobre `inherit` salta al `rune` base; hover sobre `operator ()` da la firma. Sin esto, el LSP miente y el usuario se queja en F3.
  - `psc bind --extern=cpp` **no** entra en F2.
- **Entregable de F2.5 — `docs/ABI_C.md`** (§14.3): diseño, para cada uno de los 87 `declare` que cruzan tipos de librería, del tipo nuevo (`ref to frozen char` + `usize` de longitud, etc.), el tipo viejo, si necesita shim y si el contrato binario cambia. Se diseña en F2.5 (medio día por módulo FFI), se migra en F3. Caso testigo: `std/archivum.read_file_result` devuelve `maybe string` **binario-seguro** (longitud explícita); si pasa a `char*` sin `out` de longitud, se pierde esa propiedad.
- **Tarea de F2 — spike de `std::variant` con `-fno-exceptions`**: ya hecho y ejecutado (ver §14.2 y `scratch/audit_cpp/spike_variant.cpp`). Resultado: los cuatro patrones (`switch(index)`, `holds_alternative`, `get_if`, `visit`) compilan y corren con `-fno-exceptions -fsanitize=undefined`, 0 warnings; **`get` con el índice equivocado aborta el proceso (SIGABRT, rc 134), no lanza**. Conclusión: `std::variant` vale, pero el codegen solo puede emitir `get` detrás de un `judge` exhaustivo y el checker debe demostrar esa exhaustividad (lo que el doc ya exige). No hace falta `pengu::Variant` propio.

### F3 — Semántica nueva en el dialecto C++ · 4–6 meses · confianza media-baja (es el tramo grande)

- `ctype`: `string`→`std::string`, `list`→`std::vector`, `map`→`std::map`, `umap`→`unordered_map`, `set`/`uset`, `maybe`→`optional`, `result`→`variant`, `span`→`std::span`, `array`→`std::array`, `Rc`→`shared_ptr`.
- `drop`/`banish`: RAII, sin `_pengu_cleanup_*`; `banish`→`std::move`; préstamos sin cleanup.
- `pengu/core.hpp` (~250 líneas, doc §0.4) + `pengu/plat.c`; `with`/`omen`/`judge` con STL; `inherit` con upcast; `extern c` real; `@repr(c)`; `==`/`<=>` automáticos; `map` ordenado.
- Port de los 34 `antiquus` con runtime C y de `std/json`/`jsonrpc` (los casos difíciles).
- Reescritura de las **87 firmas `declare`** que cruzan tipos de biblioteca (`string`, `maybe string`, `list of`) a ABI C explícita o shim (§14.3).
- Revisión de los **75** sitios `string at i` que da `emit-c --dump-index-types` (antes: 175 candidatos heurísticos); 29 comparaciones con literal mecánicas, ~4 con `""` a decidir; §14.1.
- Migración del resto del cierre std (43.900 líneas, de las que se tocan las partes sensibles a COW/`declare`/`derive`).
- **Aceptación**: `psc` (construido por el `psc` de F2) emite el bundle C++ de sí mismo; ese binario pasa 895/895; salida de goldens funcionalmente igual a la del binario C; ASan/UBSan limpios; el binario C++ **no** enlaza `libpengu_runtime.a`.
- **Punto de no retorno**: a partir de aquí el backend C ya no es el camino principal (pero se conserva hasta F4).
- **Puerta de replanteo (mes 2 de F3)**: si el `psc` de F2 aún no compila su propio bundle C++ con `std/json` y los `antiquus` portados, replantear el alcance antes de seguir: adelantar la retirada de `std/json` a mano o dejar `antiquus` en C hasta F5. Es el indicador temprano de que F3 se va a los 7 meses.

### F4 — Doble autohosteo y estabilización · 1–2 meses · confianza media

- `psc_c` (F2) → `psc_cpp` (F3) → `psc_cpp2`; comparar los tres en la suite y en la salida.
- Stage-0 C++ (bundle + `build_bootstrap`) reproducible; CI construye desde stage-0 C++ sin el backend C.
- **Aceptación**: los tres binarios pasan 895/895 y generan bundles funcionalmente idénticos; bootstrap desde cero en una máquina sin `psc` funciona.

### F5 — Limpieza · 1 mes · confianza alta

- Retirar backend C, `pengu_runtime.c`, `pengu_containers.c`, `--strict-c99`, `derive`, `Rc`/`Arc`/`WeakRc`/`WeakArc`, `@mutates`, `cyclus`, `fundere`; `slice of`/`list of` como errores.
- Bundle en varias TUs (tiempo de compilación), PCH por defecto en debug.
- Rehacer `std.json`/`std.toml` sobre la semántica nueva; retirar lo que quede vacío (`std.consortium`, y `std.atlas` si no aporta nada sobre `std::map`).
- Actualizar `docs/LANGUAGE.es.md`, `README.md`, `VERSION`, `pengu.toml`.

### F6 — Futuro (no forma parte de esta migración)

- Revisar `--backend=js` **solo si** se quiere Node nativo sin emscripten; la web ya está resuelta con wasm.
- El dialecto (§9.2) es el punto de extensión.

**Calendario agregado** (suma de las fases de arriba, que es la cifra que manda): F0+F1+F1b ≈ 2,75–3,75 meses; F2 ≈ 2–3 meses → **5–7 para "sintaxis nueva, semántica vieja, doble backend"**; F3 ≈ 4–6; F4+F5 ≈ 2–3. **Total 11–16 meses**, con la mayor incertidumbre todavía en F3.

---

## 12. Riesgos abiertos y decisiones pendientes

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R1 | **Tiempo de compilación C++** (plantillas en una TU) | Alta | Medio (DX) | PCH, `-O0` en debug, `--split-codegen`, F5 multi-TU; medir en F1 y publicar el número en CI |
| R2 | **MSVC** no probado (solo g++/clang++ aquí) | Media | Alto (soporte Windows) | **Decisión: job de `windows-latest` con MSVC desde F1b**; si algo no se arregla en una semana, Windows se queda en el backend C hasta F5 (coherente con el README). `clang-cl` no cuenta como prueba |
| R3 | **Diagnósticos de plantillas** ilegibles para el usuario | Alta | Medio (usabilidad) | Traductor de diagnósticos (§8.3 del audit) en F1, no después |
| R4 | **`derive` roto a medias** (cleanup/`==` perdidos) | Media | Alto (fugas/incorrección) | Orden de §7.3: backend C aprende primero, fuente después; criterio binario |
| R5 | **Copia profunda** degrada el rendimiento del compilador | Media | Medio | Medir en F3; `ref to` donde duela; no resucitar COW |
| R6 | **`antiquus` con C** (34 sitios) y `std/json` | Alta | Medio | Aislar tras `extern c` o portar a STL; `std/json` tiene fase propia (F5) |
| R7 | **Orden de iteración de `map`/`umap`** altera la salida | Baja | Medio | Regla: no iterar mapas para decidir orden de salida; `umap` prohibido para emitir; diff de bundles C vs C++ en CI |
| R8 | **FFI cambia de ABI** (string C++ vs `PenguString`) | Alta | Alto | F1 compila con tipos C (no cambia ABI); F3 migra `declare` a `extern c:` con tipos C explícitos; los `.d.pengu` no mienten |
| R9 | **Deriva entre backends** | Media | Alto | **Un solo emisor** (§9.2) + job diferencial C/C++ en cada PR |
| R10 | **El `psc` de `build/` está stale** (0.59.0 vs fuente 0.60.0) | Certeza | Bajo | Regenerar y commitear en F0; `gen_stage0 --check` en CI |
| R11 | **Ruido de goldens** (el `.cpp` cambia con cualquier ajuste) | Alta | Bajo | Comparar comportamiento, no texto, hasta F3 |
| R12 | **Decisión de nombres A1** (`born`/`die`/`mirror`/`inherit`) | — | Alto si se pospone | Decidir en F0; el doc ya la recomienda y `std/` no los usa, así que el coste de cambiarla después es alto |
| R13 | **`s at i` cambia de `string` a `char`**: las comparaciones con literales dejan de compilar; el índice fuera de rango hoy revienta y mañana devuelve `char` | Alta | **Bajo** (era Medio) | §14.1: medido con `--dump-index-types`, **75 sitios** `string at i` (no 175); 29 comparaciones mecánicas (`'x'`), **0 `to int` reales** (91 de 92 son `ref to frozen byte`); no hay corrupción silenciosa |

**Decisiones que hay que tomar antes de F2** (detalle y recomendación en §15; ninguna bloquea F0/F1):

1. **A1 — nombres**: `born`/`die`/`mirror`/`inherit` (recomendado, ya en el doc) vs latín. Cambiarlo después toca `std/` entero.
2. **Representación de `string`**: `std::string` (doc) — confirmar que no se necesita la ABI C de `PenguString` en la std migrada (los `declare` deberán hablar en `const char*`/`bytes of`).
3. **`map` ordenado por defecto** (doc §2.7): aceptar que iterar un `map` cambia de orden respecto a hoy, o mantener una tabla hash como `umap` y migrar los `map` existentes a `umap` cuando el orden no importe.
4. **JSON**: `derive Json` se retira y `std.json` se rehace a mano (fase 5). Confirmar que se acepta que el codec no sea "automático" en el lenguaje.

---

## 13. Arranque: antes de F0 y las dos primeras semanas de F0 (sin tocar el lenguaje)

**Antes de F0 — setup, no trabajo de fase** (1–2 días, y sin esto las mediciones no valen):

1. **Commit de este informe** y de `scratch/audit_cpp/{closure_and_counts.py,count_string_iterations.py,count_semantic_hotspots.py,audit_ffi_types.py,classify_cpp_errors.py,cpp_dialect_probe.sh,spike_variant.cpp}`.
2. **Regenerar el `psc` stale**: `./build/psc` es 0.59.0; construir desde el fuente 0.60.0, correr los 895 tests, `tools/gen_stage0.sh --check`. Sin esto, cualquier medición posterior es sobre un binario viejo.

**Primeras dos semanas de F0** (F0 son 3–4 semanas; esto es la mitad):

3. **F0.1 — plumbing de familia**: añadir `family` a `CgOptions`/`Target` y `--backend=cc|cpp` al CLI, sin cambiar nada de la salida; verificar que los goldens C son byte-idénticos.
4. **F0.2 — mangling de keywords**: implementar la tabla C++ en `names.pengu` con un test unitario (goldens con `new`, `module`, `concept`, `template`, `public`, `explicit`). Es el 75% de los 228 errores (§4.2) y es independiente del resto.
5. **F0.3 — burndown visible**: job que compila el bundle con `g++` y publica el número de errores; empezar en 228 y bajar.
6. **F0.4 — decisiones**: confirmar A1 (nombres, ya decididos por el doc; el coste medido es 66 renombrados, §14.6) y cerrar `map` ordenado y ABI de `string` con una nota de 1 página (§15); son las únicas que bloquean F2.

Con eso, F1 empieza con el terreno medido y sin sorpresas.

**Ya hecho** (no entra en las dos semanas): el spike de `std::variant` con `-fno-exceptions` (§14.2) — cuatro patrones OK y `get` inválido aborta, así que F3 usa `std::variant` sin envoltorio propio. **Programado en F2.5**: `docs/ABI_C.md` con el diseño de los 87 `declare` (§11). **Programado en F1**: `psc check --dump-index-types` como criterio de aceptación (§11).

## 14. Huecos a auditar antes de F3 (medidos, no estimados)

Los cuatro puntos que el plan de fases no cubría. Los números salen de scripts del repo (`scratch/audit_cpp/`), no de estimaciones.

### 14.1 `for ch in s` y `s at i`: el cambio de `string` a `char`

El doc (§5.3, §19.5) cambia el elemento de `for ch in s` de `string` (1 byte) a `char`, y lo mismo `s at i`. `s at a to b` **no** cambia: sigue devolviendo `string` (`substr`, §2.19 del audit).

**Verificado hoy con el `psc` de `build/` (0.59.0), no supuesto:**

```
$ psc run  # var c as char is s at 1     → error[E0005]: type mismatch: expected 'char', got 'string'
$ psc run  # var t as string is s at 1   → compila y corre
$ psc run  # (s at 1) == "b"             → true
$ psc run  # s at 5   (fuera de rango)   → [PENGU] Index out of bounds: 5 (length 3)  → crash
```

Y lo mismo en el bucle: `for ch in s:` + `var x as string is ch` compila; `var x as char is ch` da el mismo `E0005`. O sea: hoy **tanto `for ch in s` como `s at i` dan un `string` de un byte con índice comprobado**, no un `""` fuera de rango; el cambio a `char` es real y está documentado igual (`docs/LANGUAGE.es.md:642`: "`string` de un byte (vista prestada)").

**Cuánto toca** (`scratch/audit_cpp/count_string_iterations.py`, heurístico, sin chequeo de tipos):

```
# for X in string  (pasa a char): 8
# s at i           (pasa a char): 175   (solo receptor = variable/parámetro)
# s at i por campo (pasa a char): 11    (receptor con `.`/`->`; cota superior)
# s at a to b      (sigue string, substr): 255

## verificado por ámbito (última declaración anterior en el archivo)
# for X in string  (pasa a char): 1
# s at i           (pasa a char): 132
#   de ellos, compara con un literal de string (== "x"): 29  -> pasa a 'x'
#   de ellos, con `to int` (revisar a mano): 1
#   `to int` sobre índice, por tipo del receptor: ref to frozen byte 91, string 1
#     string real? src/psc/cmd/doc.pengu:128 [body] set params is body at (with_i + 6) to into_i
```

El heurístico **sobrecuenta**: 175 candidatos bajan a **132** al resolver el tipo por ámbito (la última `var x as string` anterior en el archivo). Los falsos positivos son de dos clases:

- receptores `ref to frozen byte` (`var raw as ref to frozen byte is bytes of s`, `var b as ref to frozen byte is bytes of t`): `at` ya devuelve un byte. De los **92** sitios con `to int` sobre un índice, **91** son de este tipo y **1** es una rebanada mal clasificada (`body at (with_i + 6) to into_i`, `src/psc/cmd/doc.pengu:128`). O sea: **no hay ni un `to int` sobre un `string` real** en el cierre, y la alarma de "cambio silencioso" que yo mismo había escrito antes era infundada.
- receptores `list of string` (`path at i`, `stem at i`): `at` devuelve `string` y **sigue devolviendo `string`** en el dialecto nuevo.

Lo que **sí** es trabajo real: **29 comparaciones con un literal de string**, de dos tipos. Las que comparan con un literal no vacío (`(path at i) == "/"`, `(stem at i) == "s"`) son **mecánicas**: en el dialecto nuevo `char` contra `string` es error de tipo y se arreglan con `'/'`/`'s'` (el migrador puede, es un patrón léxico). Las que comparan con `""` (`src/psc/codegen/catalog.pengu:227`, `src/psc/sema/infer/core.pengu:656`, `src/psc/codegen/expr.pengu:5522`, `src/psc/cmd/doc.pengu:247`) son **código muerto** hoy (fuera de rango el índice revienta en runtime, así que `== ""` nunca es verdadero sobre un `string`); al pasar a `char` hay que decidir caso por caso si se sustituyen por una comprobación de longitud.

**Medido con el compilador (F1, ya no heurística).** `psc emit-c --dump-index-types` está implementado (flag en `emit-c`, hook en `at_expr`, `dump_index_type` en `src/psc/codegen/expr.pengu`) e imprime una línea por cada `at` emitido con el tipo del receptor y el del resultado. Sobre el cierre del `psc`:

```
$ bash scratch/audit_cpp/dump_index_types.sh
lienes emitidas: 1765
sitios distintos (archivo:línea+tipo): 1649
  receptor list of T      : 1302
  receptor ref to frozen byte: 242
  receptor string         :   75
  receptor ref to list    :   18
  receptor map            :   11
```

Los **75** sitios `string at i → string` (todos devuelven `string`, ninguno `byte`) son la lista real de F3; el heurístico de arriba sobrecontaba 2,3×. Por archivo: `src/psc/dap/mi.pengu` 25, `src/psc/sema/modules/resolver.pengu` 6, `src/psc/sema/check/collect.pengu` 5, `src/psc/dap/adapter.pengu` 5, `src/psc/codegen/expr.pengu` 4, `src/psc/codegen/bundle.pengu` 4, y el resto repartido entre 12 archivos (1–3 cada uno). Los 242 `ref to frozen byte` son los que ya devuelven byte y no cambian.

**Consecuencia para el plan**: la lista exacta existe y se regenera en un comando (`emit-c --dump-index-types`, gate de F1 en §11). F3 migra **75** sitios, no 130–180; de ellos ~29 son comparaciones con literal (mecánicas) y ~4 con `""` (código muerto a decidir), y los ~40 restantes son `chr`/índices/`to int` ya correctos con `char`.

### 14.2 Omens algebraicos: 4, y ninguno en el compilador

```
$ scratch/audit_cpp/count_semantic_hotspots.py
# omens en el cierre: 22 (4 algebraicos)
# variantes totales: 505; con payload: 18; payload caro (string/list/map): 6
# judge en el cierre: 78
```

Los 4 algebraicos son de `std/`: `JsonValue` (7 variantes, 6 con payload), `LinguaError` (6/6), `JsonRpcId` (2/2), `JsonRpcMessage` (4/4). **En `src/` no hay ninguno**: el AST del `psc` es un `rune PsNode` plano (`kind` + offsets + `aux as int`) sobre arrays, y los 22 omens del compilador son enums sin payload (505 variantes en total, la mayoría códigos de diagnóstico).

`judge`: 78 en el cierre, 38 en `std/json.pengu`, 10 en `std/oracle.pengu`, 5 en `std/jsonrpc.pengu`; en `src/` solo 13. O sea: el patrón `std::variant` + `-fno-exceptions` afecta a **4 tipos y ~53 `judge`**, todos en la std, no al camino caliente del compilador.

**Spike ejecutado** (`scratch/audit_cpp/spike_variant.cpp`, g++ 16.2.1, `-std=c++20 -fno-exceptions -fsanitize=undefined -O1 -Wall -Wextra -Wpedantic`):

```
$ /tmp/spike_variant
index=nada           holds=nada           get_if=nada           visit=nada
index=string:hola    holds=string:hola    get_if=string:hola    visit=string:hola
index=int:42         holds=int:42         get_if=int:42         visit=int:42
index=point:3,4      holds=point:3,4      get_if=point:3,4      visit=point:3,4
spike: OK (4 patrones, 0 fallos)          ← sin warnings, UBSan limpio

$ /tmp/spike_variant --bad   # std::get<2> sobre un monostate
antes del get invalido
Abortado (core generado)                  ← rc 134, SIGABRT
```

Conclusión: **`std::variant` sirve con `-fno-exceptions`**, sin `pengu::Variant` propio. Pero `std::get<N>` con el índice equivocado **no lanza: aborta**, así que el codegen solo puede emitir `get` detrás de un `judge` exhaustivo y el checker tiene que demostrar esa exhaustividad (§7.3 del doc ya lo pide). Los cuatro patrones del spike son los que el emisor debe saber bajar; `get_if` es la red de seguridad si alguna vez no puede demostrar exhaustividad.

### 14.3 FFI: 202 `declare`, 87 con tipos de biblioteca, **0 runes por valor**

```
$ scratch/audit_cpp/audit_ffi_types.py
# declares en el cierre (con companions .d.pengu): 202
# solo tipos C-compatibles (escalares/punteros): 98
# pasan tipos de librería (string/list/map/…): 87
# pasan runes: 0; de ellos con campos no triviales: 0
```

- Los 202 incluyen los **companions `.d.pengu`**, que el resolver carga solos: `std/lingua.d.pengu` aporta 41 (`pengu bind` desde `std_c/utf8.h`). Los otros tres `.d.pengu` (`compressus`, `petitio`, `regulus`) no están en el cierre.
- Los 87 con tipos de biblioteca se concentran en `std/filum.pengu` 44/57, `std/archivum.pengu` 21/21, `std/rites.pengu` 14/18, `std/compass.pengu` 5/5, `std/scrolls.pengu` 1/1, `std/chronicle.pengu` 2/24.
- **Cero runes cruzan por valor**: todo va por escalares, punteros y tipos de biblioteca. Es decir, el trabajo de `@repr(c)` que el plan temía **hoy es cero**; lo que hay es 87 firmas que en el dialecto nuevo son `E0110` (un `extern c` no puede usar `string`) y hay que pasar a `ref to frozen char` + longitud, o a un shim C.
- Aviso de corrección: `archivum.read_file` devuelve `maybe string` y es binario-seguro (longitud). Pasarlo a `char*` pierde esa propiedad salvo que se añada un `out` de longitud. Decidir en F3, no en F2.

`psc bind --extern=cpp` (envolver cabeceras C++ con `libclang`) **no** está implementado y es F3; no lo necesita F2.

### 14.4 `ritual new` → `born`: 9 sitios, y `born` es opcional

```
$ scratch/audit_cpp/count_semantic_hotspots.py --samples 5
# weave ritual: 28
```

De los 28, **9 se llaman `new`** (`std/filum.pengu` 4, `std/builder.pengu`, `std/diagnostic.pengu`, `std/arena.pengu`, `std/chronicle.pengu`, `std/reactor.pengu`). Los otros 19 tienen nombre propio (`with_capacity` 5, `from_str`, `cwd`, `from_text`, `from_bytes`, `from_source`, `with_block_size`, `null_value`, `bool_val`…).

Dos correcciones al borrador:

1. **`ritual` no se retira** en el dialecto nuevo (§6.6): sigue siendo la función estática del tipo. Lo que se retira es `nasci`/`mori`/`imago` (→ `born`/`die`/`mirror`).
2. **`born` es opcional**: sin miembros especiales el tipo es un agregado y se construye con `is with`. En el compilador solo hay 2 `weave ritual` (`SourceFile.from_text`/`from_bytes`), así que "cada tipo con constructor tiene un `ritual new`" es falso: el `psc` construye con `is with` (**225 ocurrencias en el cierre**, 348 en todo `src`+`std`; contando comentarios, 284 y 434 respectivamente). Ninguna migra: `is with` es la misma sintaxis en el dialecto nuevo (§5.7 del doc), así que no entra en el presupuesto del migrador. *(Corregido: la versión anterior de este párrafo decía "376 sitios… de los que 434 en el cierre", dos cifras que no cuadraban entre sí ni con el conteo.)*

**Decisión**: los 9 `ritual new` pueden quedarse tal cual (el emisor los mangla a `new_p` por colisión con el keyword de C++) o reescribirse a `born` por estilo. No es un requisito de corrección; el migrador **no** debe renombrarlos sin una decisión explícita.

### 14.5 `psc fmt`, `doc` y `lsp` con la sintaxis nueva

`psc fmt` es un normalizador **textual** (`format_text`, `normalize_code`, `indent_line`; `src/psc/cmd/fmt.pengu`), no re-parsea. Verificado con un fuente que usa `extern c:`, `regnum`, `rune … inherit`, `vector of`, `map of K, V`, `umap`, `enchanting`/`born`/`die`, `operator ()()`:

```
$ ./build/psc fmt --check /tmp/fmt_new.pengu
0 file(s) would be reformatted.        # no lo toca
$ ./build/psc fmt /tmp/fmt_new_bad.pengu
1 file(s) formatted.                   # normaliza indentación por bloques `:`, tokens intactos
```

Conclusión: **F2 no rompe el formatter**; hay que añadir un test de regresión con esas construcciones (y no fiarse: el formatter no conoce `operator ()(` ni `extern c:`, solo cuenta `:` y paréntesis). `psc doc` (renderiza firmas `##`) y `psc lsp` (parser dual) son trabajo de F2; `psc bind --extern=cpp` es F3.

### 14.6 Nombres reservados que hoy se usan como identificadores

El apéndice A del doc convierte en **reservados** los nombres de tipo de la biblioteca: `vector`, `map`, `umap`, `set`, `uset`, `array`, `span`, `maybe`, `result`, `string`, `unique`, `shared`, `weak`, `many` (declararlos da `W0018`). En el cierre ya se usan algunos:

| Nombre | Sitios en el cierre | Dónde | Arreglo |
|---|---:|---|---|
| `result` | **47** | variables locales y parámetros (`var result as list of int` en `std/spark.pengu:1072`, `weave report_check with result as sema_api.SemaResult` en `src/main.pengu:817`) | Renombrar (`res`, `out`); mecánico pero hay que hacerlo con AST o con cuidado de sombras |
| `span` | **12** | `std/diagnostic.pengu:421` (`span as Span`), `std/scrolls.pengu`, `src/psc/...` | Renombrar (`sp`); 12 sitios |
| `set` | 3 | `src/psc/sema/annotate.pengu:87` (`weave set`), `src/psc/codegen/expr.pengu:4037` (`var set as string`) | Renombrar |
| `map` | 2 | `std/oracle.pengu:260/582` (`weave map shard U`) | Renombrar |
| `unique` | 2 | `std/tally.pengu:1027/2417` (`weave unique`) | Renombrar |
| `vector`/`umap`/`array`/`maybe`/`string`/`shared`/`weak`/`many` | 0 | — | — |

Son ~66 renombrados, todos locales y sin cambio de comportamiento. Es la parte que el plan llamaba "A1 — nombres": la decisión ya está tomada por el doc; lo que faltaba era **el coste de aplicarla al fuente**, que es este. Entra en F2 (con el migrador, que sí puede renombrar identificadores) y verifica el criterio de aceptación "el fuente no usa nombres reservados" con `W0018` en CI.

### 14.7 Resumen de lo que cambia en el plan

| Hueco | Medido | Fase | Quién lo arregla |
|---|---|---|---|
| `for ch in s` / `s at i` | 8 + 175 candidatos (132 por ámbito); 29 comparaciones con literal (algunas código muerto) | F3 | parte por migrador; resto manual (§14.1) |
| Omens → `std::variant` | 4 tipos, 18 variantes con payload, 78 `judge` | F3 | emisor + `std/json` |
| FFI `@repr(c)` | 202 declares; 87 con tipos de biblioteca; 0 runes por valor | F3 | manual + shims |
| `ritual new` → `born` | 9 sitios; `born` opcional | F2 (estilo) | decisión, no migrador |
| `fmt`/`doc`/`lsp` | fmt OK (textual); doc/lsp a adaptar | F2 | equipo |
| Nombres reservados (`result`, `span`, `set`, `map`, `unique`) | 66 sitios | F2 | `psc migrate` + revisión |
| MSVC | sin probar | F1b | job CI + decisión de respaldo |

## 15. Decisiones de F0.4 (firmadas 2026-11-10)

Las siete están firmadas en **`docs/MIGRACION_CPP_DECISIONES.es.md`**, que es el registro canónico (dentro del repo, no en `scratch/`): incluye recomendación, motivo, coste medido, cuándo se aplica y condición de revisión de cada una. Esta tabla es el resumen.

| # | Decisión | Recomendación | Coste medido | Quién |
|---|---|---|---|---|
| A1 | **Nombres**: `born`/`die`/`mirror`/`inherit`/`vector`/`map`/`span`/`unique`/`shared`/`weak`/`extern c`/`extern cpp`/`regnum` | **Adoptar tal cual el doc** (v1.0). Son los del apéndice A; los contextuales siguen siendo identificadores, así que el fuente solo sufre por los **reservados** | 66 renombrados (§14.6) | F0 (confirmar), F2 (aplicar) |
| A2 | **Representación de `string`** | `std::string` (doc §0.4), sin ABI C. La frontera C usa `ref to frozen char` + longitud | 87 firmas `declare` (§14.3) | F3 |
| A3 | **`map` ordenado por defecto** | Aceptar `std::map` y `umap` para hash. Regla de oro: **no iterar un `map` para decidir el orden de salida** del compilador (si hace falta, ordenar explícitamente) | 588 `map of` en el cierre; `std/atlas` revisable | F3 |
| A4 | **JSON** | `derive Json` fuera de alcance; `std/json` se rehace a mano (ya lo está hoy) | 4 omens algebraicos, 38 `judge` (§14.2) | F3/F5 |
| A5 | **MSVC** | Job de `windows-latest` desde F1b; si algo no se arregla en una semana, Windows se queda en el backend C hasta F5 | 0 hoy (sin probar) | F1b |
| A6 | **Omens algebraicos** | `std::variant` (doc), sin `pengu::Variant` propio. **Ya validado** con `spike_variant.cpp` (§14.2): 4 patrones OK con `-fno-exceptions`; `get` inválido aborta, así que solo se emite detrás de un `judge` exhaustivo | 4 tipos, 18 variantes con payload | F3 |
| A7 | **`ritual new`** | Se quedan: el emisor los mangla (`new_p`); `born` es opcional y no hay que renombrarlos | 9 sitios | F2 (no hacer nada) |

---

## Apéndice A — Comandos reproducibles

```bash
cd ~/Documentos/GitHub/PenguScript

# Línea base
./build/psc --version
./build/psc test .                                   # 895 tests
wc -l $(find src -name '*.pengu') | tail -1          # 61.839

# Emisión y compilación del bundle
time ./build/psc emit-c src/main.pengu --out=/tmp/psc_bundle.c
wc -l /tmp/psc_bundle.c                              # 138.978
time gcc -std=c11 -O2 -I. -Ibuild/include -c /tmp/psc_bundle.c -o /tmp/psc_bundle.o

# Sonda C++
scratch/audit_cpp/cpp_dialect_probe.sh goldens        # 41 OK / 3 FAIL (con -fpermissive)
scratch/audit_cpp/cpp_dialect_probe.sh goldens-strict # 41 OK / 3 FAIL (sin -fpermissive, sds.h parcheado)
scratch/audit_cpp/cpp_dialect_probe.sh bundle         # 228 errores
scratch/audit_cpp/cpp_dialect_probe.sh runtime        # 0 errores (con -D_Atomic=; sin él, 2)

# Runtime como C++
g++ -std=gnu++20 -fpermissive -fsyntax-only -I. -Ibuild/include pengu_runtime.h

# Cierre y conteos
python3 scratch/audit_cpp/closure_and_counts.py
python3 scratch/audit_cpp/closure_and_counts.py --per-file

# Huecos de F3 (§14)
python3 scratch/audit_cpp/count_string_iterations.py --per-file   # 8 for / 175 at (132 por ámbito) / 29 literales
python3 scratch/audit_cpp/count_semantic_hotspots.py --per-file   # 22 omens (4 algebraicos), 78 judge, 28 ritual
python3 scratch/audit_cpp/audit_ffi_types.py --per-file           # 202 declare, 87 con tipos de librería, 0 runes
python3 scratch/audit_cpp/classify_cpp_errors.py                  # 228 → 170/26/13/9/10

# Stage-0
tools/gen_stage0.sh --check
```

Reproducción del "hello" como C++ (usada en §4.4):

```bash
printf 'int pengu_abi_version(void) { return 4; }\n' > /tmp/abi.cpp
g++ -std=gnu++20 -fpermissive -D_Atomic= -I. -Ibuild/include \
    tests/golden_c/g01_hello.c /tmp/abi.cpp -o /tmp/g01_cpp \
    build/lib/libpengu_runtime.a build/lib/libminiz.a -lm -pthread -ldl
/tmp/g01_cpp     # hello, pengu
```

## Apéndice B — Evidencia y ficheros citados

- Referencia de sintaxis/código C++: `docs/LANGUAGECPP.es.md` (4.512 líneas, v1.0). Secciones clave: §0.4 (`pengu/core.hpp`, ~250 líneas), §1.3 (mangling de keywords, `_p`), §2.8 (paridad C), §19.7 y apéndice D.1 (retiradas).
- Auditoría previa del dialecto (diseño, no plan de migración): `scratch/AUDITORIA_CPP.es.md` (§0.3 cifras del repo, §2.8 paridad C, §3.x lo que se elimina, §2239–2245 fases F1–F5, riesgos R1–R12).
- Estado del lenguaje actual: `docs/LANGUAGE.es.md` (`derive` en línea 1424; `fundere`, `@mutates`, `Rc`/`Arc`).
- Tipos soft-word: `src/psc/parse/types.pengu` (`ptype_parse_type`); keywords reales: `src/psc/token.pengu`.
- Emisor: `src/psc/codegen/{api,emit,ctype,names,expr,stmt,bundle,drop,jsongen}.pengu`; `generate_c` en `api.pengu`.
- FFI: `std/{archivum,chronicle,compass,coro,filum,memoria,reactor,rites,scrolls}.pengu` + companions `.d.pengu` (`std/lingua.d.pengu` aporta 41) = **202 `declare`**; 87 cruzan `string`/`list`/`maybe`; 0 runes por valor.
- Scripts de medición: `scratch/audit_cpp/{closure_and_counts,count_string_iterations,count_semantic_hotspots,audit_ffi_types,classify_cpp_errors}.py` y `cpp_dialect_probe.sh`.
- Semántica de `char`/`substr`: `docs/LANGUAGECPP.es.md` §5.3, §19.5; `x at i to j` → `substr` en `scratch/AUDITORIA_CPP.es.md` §2.19.
- Riesgo semántico: `std/json.pengu` (recursivo, `Imago`, 25 `antiquus`), `std/jsonrpc.pengu`, `std/diagnostic.pengu`.
- Cierre std: `std/filum.pengu` (57 `declare`, `@shared` 13), `src/psc/dap/adapter.pengu:11` (`import std.filum`).
- Build: `tools/gen_stage0.sh`, `tools/build_bootstrap.sh`, `pengu.toml`, `src/psc/driver/{manifest,build,target}.pengu`.
- wasm/web: `src/psc/driver/target.pengu`, `std/web/` (18 módulos), `runtime/pengu_js.{c,js}`, `pengu_wasm_shell.html`, `docs/CROSS_COMPILE.md`.
- Formateador (texto, no AST): `src/psc/cmd/fmt.pengu` (`format_text`, `normalize_code`).
- Python: `../PenguScript-Python/` (3.0.3, `AUDITORIA_AUTO_HOSPEDAJE.md`), `scratch/audit/01-python-compiler-gaps.md` (OLD 3.0.3 vs NEW 0.36.0).
- Deuda abierta del runtime actual: `scratch/next-steps.md` (P2/P5/P6/P7, bugs de `banish`/`maybe`/`result`).
