# 🐧 Auditoría de auto-hospedaje de PenguScript

> **Versión auditada:** `3.0.1` · **Commit:** `0c20e3f` · **Fecha:** 2026-10-24
>
> **Alcance:** determinar si el lenguaje y su stdlib ya permiten reescribir el
> compilador, el CLI y el LSP en PenguScript; inventariar los bloqueos reales;
> proponer la arquitectura, el nuevo orden del proyecto y un plan por fases.
>
> **Regla de esta auditoría:** no se ha implementado nada. Solo se ha leído el
> repositorio, ejecutado la suite, hecho *spikes* aislados en `/tmp` y escrito
> este documento. El compilador Python sigue intacto.

---

## 📑 Índice

0. [Veredicto en 60 segundos](#-0-veredicto-en-60-segundos)
1. [Cómo se hizo esta auditoría](#-1-cómo-se-hizo-esta-auditoría)
2. [Estado actual del proyecto](#-2-estado-actual-del-proyecto)
3. [¿Puede el lenguaje auto-hospedarse?](#-3-puede-el-lenguaje-auto-hospedarse)
4. [Dependencias y reemplazos](#-4-dependencias-del-compilador-actual-y-su-reemplazo)
5. [Bugs, fugas y deudas](#-5-bugs-fugas-y-deudas-que-afectan-al-objetivo)
6. [Piezas que faltan en la stdlib](#-6-piezas-que-faltan-en-la-stdlib)
7. [Arquitectura y patrón de diseño](#-7-arquitectura-y-patrón-de-diseño)
8. [Nueva organización del proyecto](#-8-nueva-organización-del-proyecto)
9. [Plan completo por fases](#-9-plan-completo-por-fases)
10. [Estrategia de migración y paridad](#-10-estrategia-de-migración-y-paridad)
11. [Riesgos y mitigaciones](#-11-riesgos-y-mitigaciones)
12. [Decisiones que necesito de ti](#-12-decisiones-que-necesito-de-ti)
13. [Anexos](#-13-anexos)
14. [Resumen ejecutivo final](#-14-resumen-ejecutivo-final)

---

## 🎯 0. Veredicto en 60 segundos

**Sí, el lenguaje puede auto-hospedarse.** No hay ninguna construcción
sintáctica que impida escribir en PenguScript el lexer, el parser, el checker,
el generador de C, el CLI y el LSP. La stdlib ya contiene las piezas que hace
dos versiones eran el cuello de botella: `std.arena`, `std.builder`,
`std.diagnostic`, `std.sourcemap`, `std.json`, `std.jsonrpc` y `std.functor`.

**Pero el proyecto todavía no está listo para el cambio.** Lo que falta no es
“lenguaje”, es:

1. 🐞 **Dos bugs de monomorfización** que rompen la composición de genéricos
   (un genérico que llama a otro genérico, y los constructores `ritual`
   genéricos con más de una especialización). Son el mayor riesgo para escribir
   el compilador de forma idiomática.
2. 🧱 **Cinco primitivas de sistema que la stdlib no tiene:** captura de
   `stdout`+`stderr`+exit code de un proceso que falla, E/S binaria de `stdin`
   (para el LSP), sockets (LSP por TCP), SHA-256 y TOML.
3. 🧠 **Un modelo de memoria manual sin GC**, que obliga a una disciplina de
   ownership muy estricta. La stdlib auditada está limpia bajo ASan; el riesgo
   estará en el código nuevo del compilador.
4. ⚙️ **Un trabajo de paridad enorme:** el compilador actual (core + CLI + LSP)
   son ~56 000 líneas de Python; de ellas, ~7 200 son el LSP y ~8 700 el CLI.
   Un port razonable, no literal, puede rondar las **50 000–80 000 líneas de
   PenguScript**.

> **Conclusión corta:** el auto-hospedaje es **viable técnicamente**, pero es un
> proyecto de varios meses (o de un equipo pequeño durante varios trimestres),
> no un fin de semana. El camino recomendado es un compilador nuevo, por fases,
> con el Python actual como *stage0* y oráculo de paridad. `pengu bind` se queda
> como ejecutable externo, tal como planteaste.

### 📊 Los números que resumen el estado

| Métrica | Valor | Lectura |
|---|---:|---|
| Versión / commit | 3.0.1 / `0c20e3f` | Base estable, suite verde |
| Tests pasando | **1 400 pasados, 3 omitidos** en 112 s | El compilador actual es sólido |
| Corpus de conformidad | **126** programas `.pengu` | Excelente red de seguridad |
| Módulos std puros | **40** | Cobertura amplia |
| Declaraciones públicas std | **1 847** | 96,3 % documentadas |
| Líneas Python del core | **~56 300** | Tamaño del port |
| Líneas std puras | **~69 000** (con doc) | No hay que reescribirla |
| Códigos de diagnóstico `E` | **~43** | Hay que conservarlos |
| ASan sobre fundamentos | **6/6 tests limpios** | Arena/builder/jsonrpc no filtran |

---

## 🧭 1. Cómo se hizo esta auditoría

### 1.1 Qué se leyó

| Área | Archivos principales |
|---|---|
| Gramática y lexer | `pengu_parser/pengu_grammar.py`, `pengu_parser/pengu_parser.py` |
| Semántica | `pengu_parser/pengu_checker.py`, `pengu_infer.py`, `pengu_types.py`, `pengu_symbols.py` |
| Codegen | `pengu_parser/pengu_codegen/*.py`, `pengu_dce.py` |
| CLI / proyecto | `pengu_project.py`, `pengu_cache.py`, `pengu_paths.py`, `pengu_lock.py`, `pengu_semver.py` |
| LSP | `pengu_lsp/*.py` |
| Bind | `pengu_bind.py` (pycparser) |
| Runtime / ABI | `pengu_runtime.h`, `docs/ABI.md`, `docs/ARCHITECTURE.md` |
| Stdlib | `std/*.pengu`, `docs/api/*.md`, `LANGUAGE.md` §19 |
| Pruebas | `tests/`, `tests/conformance/`, `AGENT_TESTING.md` |
| Historia | `self_hosted_plan.md` (commit `88c97f9`, ya borrado), CHANGELOG 2.6–3.0 |

### 1.2 Qué se ejecutó

```bash
# Suite completa (paralela, configuración por defecto)
pytest tests/ -q
# -> 1400 passed, 3 skipped, 108 warnings in 112.24s

# Fugas de memoria en los módulos que usará el compilador
PENGU_CFLAGS="-fsanitize=address,undefined ..." \
PENGU_LDFLAGS="-fsanitize=address,undefined" \
ASAN_OPTIONS="detect_leaks=1:halt_on_error=1" \
pytest tests/stdlib/audit/test_fundamentals_memory.py -q -n 0
# -> 1 passed

PENGU_CFLAGS=... pytest tests/stdlib/audit/test_leaks_comprehensive.py -q -n 0
# -> 5 passed in 25.35s

# Sanidad del toolchain
pengu doctor          # -> everything looks good
pengu --version       # -> pengu 3.0.1
```

### 1.3 Spikes de capacidad (en `/tmp`, no en la repo)

| Spike | Resultado | Conclusión |
|---|---|---|
| AST recursivo con `rune` + `std.arena` + `judge over` + `map` genérico | ✅ compila y evalúa (`2+3)*2 = 10` | El patrón del compilador funciona |
| `Box shard T` con métodos que se llaman entre sí | ✅ compila para `int` y `string` | La limitación documentada en `coven` ya no reproduce en ese caso |
| Función genérica que llama a otra función genérica | ❌ C inválido (`ident_T`) | **Bloqueo B1** |
| Constructor `ritual` genérico con dos especializaciones | ❌ `Box of string = Box_empty_int()` | **Bloqueo B2** |
| `calling compass.Path.from_str` (tipo cualificado) | ❌ C inválido (`compass.Path.from_str`) | **Bloqueo B2b** |
| `spark.parse_float("3.5")` | ❌ imprime `0` | Bug abierto de stdlib (B10) |
| `"a{(chr 200)}b"` | ❌ longitud 4 en vez de 3 | Bug de codegen (B11) |
| 1 000 paréntesis anidados | ❌ “maximum recursion depth exceeded” en `0:0` | Falta límite de profundidad (B7) |

> Los spikes se hicieron con el compilador actual, sin tocar la repo. Los
> fragmentos exactos están en el Anexo B.

---

## 🏗️ 2. Estado actual del proyecto

### 2.1 Pipeline real

```text
.pengu + pengu.toml
        │
        ▼
┌──────────────────┐
│ 1. parse         │  Lark LALR(1) + indenter
│    pengu_parser  │  texto -> Tree
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 2. collect       │  resolve_imports + SymbolTable
│    symbols       │  módulos topológicos
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 3. check         │  PenguChecker (pass 1 + 1b + 2)
│    checker       │  errores acumulados, no excepciones
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 4. infer         │  TypeInferrer (bidireccional,
│    infer         │  monomorfiza genéricos)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 5. codegen       │  bundle.c + DCE
│    pengu_codegen │  + line markers + entry point
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 6. cc            │  gcc / clang / tcc / msvc
│    pengu_project │  enlaza libpengu_runtime.a
└────────┬─────────┘
         ▼
┌──────────────────┐
│ 7. cache         │  sha256 de fuentes + flags
│    pengu_cache   │  binario cacheado
└──────────────────┘
```

La descripción detallada está en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Es importante respetar **las mismas etapas y contratos**, aunque el código nuevo
se organice de otra forma.

### 2.2 Tamaño del código que habría que portar

| Componente | Archivos | Líneas aprox. | Dificultad |
|---|---|---:|---|
| Lexer + gramática + parser | `pengu_grammar.py`, `pengu_parser.py` | 1 800 | 🟡 Media |
| Errores + símbolos | `pengu_errors.py`, `pengu_symbols.py` | 1 830 | 🟡 Media |
| Tipos + inferencia | `pengu_types.py`, `pengu_infer.py` | 8 360 | 🔴 Alta |
| Checker | `pengu_checker.py` | 8 430 | 🔴 Alta |
| Comptime / DCE | `pengu_comptime.py`, `pengu_dce.py` | 780 | 🟠 Media-alta |
| Codegen | `pengu_codegen/*.py` | 14 440 | 🔴 Alta |
| CLI + proyecto + cache | `pengu_project.py` y soporte | 13 800 | 🟠 Media-alta |
| LSP | `pengu_lsp/*.py` | 7 235 | 🟠 Media-alta |
| Bind | `pengu_bind.py` | 1 560 | ⛔ Excluido / externo |
| **Total core + CLI + LSP** | | **~56 300** | |

No todo se porta línea a línea. Un buen diseño puede reducir líneas, pero
PenguScript es más explícito (llamadas, ownership, `banish`, `judge`), así que
el estimado realista es **0,9–1,4×** el tamaño Python para el mismo
comportamiento. Es decir: **50 000–80 000 líneas de PenguScript**.

### 2.3 Señales de madurez (lo bueno)

- ✅ **La suite está verde:** 1 400 tests, incluyendo compilación real con C.
- ✅ **Hay un corpus de conformidad ejecutable:** 126 programas.
- ✅ **La stdlib está auditada:** 1 847 declaraciones públicas, 96,3 %
  documentadas, con 40 módulos y tests internos.
- ✅ **ASan limpio** en arena, builder, sourcemap, bitset, json, jsonrpc y
  colecciones.
- ✅ **El lenguaje ya tiene**: genéricos monomorfizados, conceptos, `bind`,
  `enchanting`, `judge` sobre `rune`, `defer`/`errdefer`, `maybe`/`result`,
  `antiquus` (C embebido), `declare`, `link`, `insignia`, hilos y canales.
- ✅ **El precedente de auto-hospedaje ya existe** en la stdlib: `std.json`
  implementa un parser JSON recursivo en PenguScript, `std.diagnostic` un
  renderizador de errores y `std.jsonrpc` el framing del LSP.
- ✅ **La infraestructura de release** ya contempla layouts portable/FHS y
  localización de `std/` y del runtime.

### 2.4 Lo que no existe

- ❌ **No hay una implementación `.pengu` del compilador.** Cero líneas del
  pipeline actual están escritas en PenguScript.
- ❌ **No hay paridad de CLI/LSP medida contra una segunda implementación.**
- ❌ **No hay un *harness* de compilación diferencial** que compare dos
  compiladores.
- ❌ **No hay módulos std de TOML, SHA-256, E/S binaria ni red.**

---

## 🧬 3. ¿Puede el lenguaje auto-hospedarse?

### 3.1 Matriz de capacidades

| Necesidad del compilador | ¿Existe? | Evidencia / módulo | Veredicto |
|---|---|---|---|
| Tokens, palabras clave, comentarios | ✅ | Gramática + `NAME: /[a-zA-Z_][...]/` | Escribir lexer a mano |
| Indentación significativa | ✅ | `PenguIndenter` (Python) | Replicar como post-lexer |
| Strings con interpolación y raw | ✅ | `STRING`, `TRIPLE_STRING`, `RAW_*` | El lexer nuevo debe manejar anidamiento |
| AST recursivo | ✅ | `rune` + `cyclus` + `ref to`; `tests/conformance/compliance/arena_ast.pengu` | Arena + nodos |
| Uniones etiquetadas | ✅ | `omen` + `judge` | Sin problema |
| Pattern matching sobre `rune` | ✅ | `judge ... over ...` (LANGUAGE §7.4.1) | Sin problema |
| Genéricos | ⚠️ | `shard T`, `where`; **B1/B2** | Evitar composición genérica en PSC |
| Conceptos / `bind` | ✅ | Estático, sin vtables | Suficiente |
| Closures | ❌ | No hay captura; `std.functor` | Patrón explícito |
| `maybe` / `result` | ✅ | Nativo + `or return` / `or:` | Sin excepciones |
| Módulos, privacidad, `insignia` | ✅ | `import`, `_private`, `insignia` | Sin problema |
| C embebido / FFI | ✅ | `antiquus`, `declare`, `include`, `link` | Suficiente para syscalls |
| Hilos / canales | ✅ | `std.filum` | LSP con worker |
| Archivos y directorios | ✅ | `std.archivum` | Falta streaming (B4) |
| Procesos | ⚠️ | `std.rites` | Falta captura de error (B3) |
| JSON / JSON-RPC | ✅ | `std.json`, `std.jsonrpc` | Sin problema |
| Diagnósticos ricos | ✅ | `std.diagnostic` | Sin problema |
| Span / source map | ✅ | `std.sourcemap` | Sin problema |
| StringBuilder | ✅ | `std.builder` | Sin problema |
| Arena | ✅ | `std.arena` | Sin problema |
| UTF-8 / UTF-16 | ⚠️ | `std.lingua` | Falta conversión UTF-16 explícita |
| Regex | ⚠️ | `std.regulus` | Sin grupos ni alternancia; evitar |
| Hash criptográfico | ❌ | Solo CRC-32 | **Falta SHA-256** |
| TOML | ❌ | No existe | **Falta** |
| YAML | ⚠️ | Parser fallback en Python | Portar subconjunto o diferir |
| Sockets | ❌ | `std.petitio` es cliente HTTP | **Falta** para LSP TCP |
| Archivos comprimidos | ⚠️ | `std.compressus` (gzip/zlib) | Falta ZIP/TAR contenedor |

### 3.2 La prueba de fuego: un AST real

El propio repo ya tiene la prueba que importa:

```pengu
rune Expr:
    kind as int
    value as int
    left as ref to Expr
    right as ref to Expr

weave make_add with a as ref to Arena, left as ref to Expr,
                     right as ref to Expr into ref to Expr:
    var e as ref to Expr is calling arena_alloc_one of Expr with a
    set e->kind is 2
    set e->left is left
    set e->right is right
    return e
```

Está en [`tests/conformance/compliance/arena_ast.pengu`](tests/conformance/compliance/arena_ast.pengu)
y pasa. En el spike de esta auditoría se añadió `judge over kind`, un `map` de
entorno y una función recursiva de evaluación; también pasó.

**Por tanto: el patrón “AST recursivo + arena + pattern matching” está
validado.** No es teoría.

### 3.3 Los bloqueos reales (resumen)

| # | Bloqueo | Dónde duele | ¿Bloquea el auto-hospedaje? |
|---|---|---|---|
| **B1** | Genérico llamando a genérico emite `_T` | Cualquier helper genérico compuesto | 🔴 Sí, si el código nuevo usa genéricos |
| **B2** | Constructor `ritual` genérico se queda con la 1ª especialización | Constructores de contenedores genéricos | 🔴 Sí, si se usan constructores genéricos |
| **B2b** | Llamada a método de un tipo cualificado (`mod.Type.metodo`) | Organización modular, evitar colisiones | 🟠 Alto (hay workaround) |
| **B3** | No se puede capturar `stderr` de un proceso que falla | `pengu build` no puede mostrar errores de gcc | 🔴 Sí, para el CLI |
| **B4** | No hay `read(n)` binario ni sockets | LSP stdio/TCP | 🔴 Sí, para el LSP |
| **B5** | No hay SHA-256, TOML, YAML | Lockfile, manifiestos, verificación | 🔴 Sí, para el CLI completo |
| **B6** | LSP usa columnas de code points, no UTF-16 | Posiciones en archivos no ASCII | 🟠 Medio |
| **B7** | Sin límite de profundidad | Entradas maliciosas/muy anidadas | 🟠 Medio |
| **B8** | Memoria manual | Fugas si no se disciplina | 🔴 Sistémico |

### 3.4 Limitaciones que **no** son bloqueos

- **Sin closures:** se sustituyen por `std.functor` + contexto explícito, o por
  recursión directa. El compilador no necesita capturar variables para su
  pipeline.
- **Sin pattern matching de listas:** `items as [a, b]` no existe. Se escribe
  `if items.len == 2:` + `items at 0` / `items at 1`. El AST se recorre con
  `for`, así que no importa.
- **Sin despacho dinámico:** `concept` es estático. El checker puede usar
  `judge` sobre un `omen` de tipos, no vtables.
- **Sin herencia:** no se necesita; el compilador es composición de funciones.
- **Sin excepciones:** se usa `result`/`maybe` y un `DiagnosticBag`. Es una
  ventaja para el LSP, no un problema.
- **Sin `switch` con fallthrough:** `judge` cubre el caso.

### 3.5 Veredicto de capacidad

| Pregunta | Respuesta |
|---|---|
| ¿Se puede escribir el lexer? | ✅ Sí, a mano, con estados para strings e indentación |
| ¿Se puede escribir el parser? | ✅ Sí, recursive descent + Pratt; hay que replicar prioridades y soft keywords |
| ¿Se puede escribir el checker? | ✅ Sí, con arena, mapas, `omen` de tipos y `judge` |
| ¿Se puede escribir el codegen? | ✅ Sí, con `StringBuilder` y las mismas reglas de C |
| ¿Se puede escribir el CLI? | ✅ Sí, con `std.invoke`, `std.archivum`, `std.rites` (tras B3) |
| ¿Se puede escribir el LSP? | ✅ Sí, con `std.jsonrpc`, `std.diagnostic` (tras B4 y B6) |
| ¿Se puede compilar a sí mismo? | ✅ Sí, si PSC evita B1/B2 o éstos se arreglan antes |
| ¿Se puede prescindir de Python? | ✅ En runtime, salvo `pengu bind` (externo) |
| ¿Se puede hoy, sin tocar nada? | ❌ No: B1/B2/B3/B4/B5 lo impiden |

---

## 🧱 4. Dependencias del compilador actual y su reemplazo

### 4.1 De Python a la stdlib de PenguScript

| Dependencia actual | Uso | Reemplazo en PenguScript | Estado |
|---|---|---|---|
| `lark` | Lexer/parser LALR | Lexer + parser escritos a mano | ⏳ A implementar |
| `argparse` | CLI | `std.invoke` + parser manual para casos especiales | ✅ Base |
| `os`, `pathlib`, `shutil` | Rutas, copias, borrados | `std.compass`, `std.archivum` | ✅ |
| `subprocess` | gcc, git, build scripts | `std.rites` (falta captura, B3) | ⚠️ |
| `hashlib.sha256` | Cache, lockfile, TCC | `std.digest` (nuevo) | ❌ |
| `tomllib` / `tomli` | `pengu.toml`, `pengu.lock` | `std.toml` (nuevo) | ❌ |
| `pyyaml` | `pengu.yaml` legado | Subconjunto YAML propio o `libcyaml` | ⚠️ |
| `json` | Metadatos, `--json` | `std.json` | ✅ |
| `pygls` + `lsprotocol` | LSP | `std.jsonrpc` + servidor propio | ⚠️ |
| `pycparser` | `pengu bind` | Ejecutable externo `pengu-bind` | ⛔ Excluido |
| `PyInstaller` | Empaquetar el CLI | Binario nativo; solo release | ✅ |
| `re` (varios archivos del core y del LSP) | Parsing auxiliar, validaciones | Escáneres a mano; `std.regulus` no alcanza | ⚠️ |
| `threading` / `asyncio` | LSP, validación | `std.filum` + worker | ⚠️ |
| `zipfile` / `tarfile` | TCC, assets | ZIP/TAR propio o `tar`/`unzip` | ⏳ |
| `platform`, `sys` | Detección de SO/arquitectura | `when os`, `when arch`, `std.rites` | ✅ |

> ⚠️ **Sobre `re`:** `std.regulus` no soporta grupos, alternancia, `{n,m}`,
> lookaround ni Unicode. No es un reemplazo de `re`. Para el compilador nuevo
> **no hace falta**: se escriben escáneres a mano para identificadores, números y
> comentarios. Si se quisiera portar literalmente el código Python que usa `re`,
> habría que añadir PCRE2 como binding; no lo recomiendo.

### 4.2 Librerías / bindings extra: respuesta directa

**Para el compilador en sí no hace falta ningún binding C nuevo.** Todo lo que
necesita se puede hacer con:

- `std.archivum` para archivos,
- `std.rites` para procesos,
- `std.filum` para hilos,
- `std.memoria` / `std.arena` para memoria,
- `antiquus` para las pocas llamadas de sistema que falten.

Las únicas piezas nuevas son **módulos std**, no librerías externas:

| Pieza | ¿Binding externo? | Recomendación |
|---|---|---|
| SHA-256 | No | Implementar en PenguScript (~250 líneas) en `std.digest` |
| TOML | No (o `tomlc17` opcional) | Parser/escritor propio; `tomlc17` ya está en `extern/` si se prefiere |
| YAML | No (o `libcyaml` opcional) | Subconjunto para compatibilidad; YAML no es el formato canónico |
| E/S binaria / `read(n)` | No | `antiquus` sobre `stdio`/`read`; módulo `std.io` |
| Sockets | No | `antiquus` sobre sockets POSIX/Winsock; módulo `std.net` |
| ZIP/TAR | No | Contenedor ZIP sobre `std.compressus`, o invocar `tar`/`unzip` |
| Regex PCRE | Opcional | Solo si se decide portar `re` literalmente; no necesario |
| `pengu bind` | **Sí, Python** | Externo y congelado; es la excepción aceptada |

**Bindings que sí o sí hay que mantener fuera del binario principal:**

1. **`pengu bind`** → ejecutable `pengu-bind` (PyInstaller o equivalente).
   El CLI principal lo localiza y lo invoca. Sin él, `pengu bind` da un error
   claro. Es la única dependencia de Python aceptada en runtime.
2. **Release / empaquetado** (`make_release.py`, PyInstaller) → puede seguir en
   Python porque es infraestructura de desarrollo, no runtime del usuario.

### 4.3 Lo que se queda en Python (explícito)

| Componente | ¿Se porta? | Motivo |
|---|---|---|
| `make_release.py` | ❌ No, por ahora | Pipeline de release; no lo usa el usuario |
| Empaquetado PyInstaller | ❌ No | Solo para producir artefactos |
| `pengu bind` | ❌ No (helper) | `pycparser`; excepción aceptada |
| Tests con pytest | ⚠️ Puede quedarse | Es harness de desarrollo, no runtime |
| `pengu selftest` | ⚠️ Diferir | Si se queda pytest, es un comando de dev, no de usuario |
| Scripts de CI | ⚠️ Puede quedarse | No afecta al binario |

> **Definición de “sin Python” que propongo:** el binario `pengu` y el helper
> `pengu-bind` no requieren un intérprete de Python instalado. El desarrollo, los
> tests y el release pueden usar Python. Si quieres “ni Python en el helper”,
> eso es un proyecto aparte (parser de cabeceras C en C/PenguScript o libclang).

---

## 🐞 5. Bugs, fugas y deudas que afectan al objetivo

### 5.1 Resumen

| ID | Severidad | Tipo | Estado | ¿Bloquea? |
|---|---|---|---|---|
| **B1** | 🔴 Crítica | Monomorfización genérico→genérico | Abierto, verificado | Sí, si PSC usa genéricos |
| **B2** | 🔴 Crítica | `ritual` genérico multi-especialización | Abierto, verificado | Sí, si PSC usa constructores genéricos |
| **B2b** | 🟠 Alta | Llamada cualificada a tipo/método | Abierto (G-4), verificado | Workaround |
| **B3** | 🔴 Alta | `std.rites` pierde stderr al fallar | Abierto, por código | Sí, para CLI |
| **B4** | 🔴 Alta | Sin E/S binaria ni sockets | Abierto, por código | Sí, para LSP |
| **B5** | 🔴 Alta | Sin SHA-256/TOML/YAML | Abierto, por código | Sí, para CLI completo |
| **B6** | 🟠 Media | LSP sin UTF-16 | Abierto, por código | No, pero incorrecto |
| **B7** | 🟠 Media | Sin límite de profundidad | Abierto, verificado | Robustez |
| **B8** | 🔴 Sistémico | Memoria manual / fugas | Diseño documentado | Hay que disciplinarlo |
| **B9** | 🟠 Media | Orden de mapas no determinista | Documentado | Determinismo |
| **B10** | 🟠 Media | `spark.parse_float` devuelve 0 | Abierto, verificado | Datos incorrectos |
| **B11** | 🟡 Baja | `(chr N)` constante en interpolación | Abierto, verificado | Evitable |
| **B12** | 🟡 Baja | Ejemplos de docs que no compilan | Abierto, verificado | Confusión |

---

### 🔴 B1 — Un genérico no puede llamar a otro genérico

**Síntoma.** El compilador emite una única función `_T` sin especializar y el C
resultante no compila.

```pengu
weave ident shard T with x as T into T:
    return x

weave twice shard T with x as T into T:
    var y as T is calling ident with x     # 👈 llamada genérica dentro de genérica
    return y

weave main into int:
    calling spark.println_int with calling twice with 5
    calling spark.println with calling twice with "hi"
    return 0
```

**C generado (resumido):**

```c
void* ident_T(void* x);
int32_t twice_int(int32_t x);
PenguString twice_string(PenguString x);

int32_t twice_int(int32_t x) {
  int32_t y = ident_T(x);          /* ident_T espera void* */
  return y;
}

PenguString twice_string(PenguString x) {
  PenguString y = ident_T(x);      /* ident_T espera void* */
  return y;
}
```

**Causa raíz.** La llamada a `ident` dentro del cuerpo genérico se resuelve una
sola vez, sin sustituir `T` por el tipo del llamador. El codegen materializa la
plantilla `ident_T` en lugar de `ident_int` / `ident_string`.

**Impacto en el auto-hospedaje.** Cualquier helper genérico compuesto se rompe:

- `sort<T>` que llama a `compare<T>`.
- `hash_map<T>` que llama a `hash<T>`.
- `arena_list<T>` que llama a `grow<T>`.
- Un wrapper genérico sobre una función genérica de `std.atlas` o `std.loom`
  también falla (`atlas_map_get_or` sin especializar).

**Workarounds.**

1. ✅ **No escribir genéricos compuestos en el código fuente de PSC**:
   helpers concretos por tipo, o duplicación controlada. Es la vía más rápida
   para el bootstrap. (PSC **sí** tendrá que implementar la semántica de
   genéricos para el código de entrada; lo que evita es *usarlos* en su propio
   fuente.)
2. ⚠️ Llamar con argumentos de tipo explícitos **solo funciona si el llamador ya
   es concreto**; dentro de un genérico, `calling ident of T` sigue emitiendo
   `_T`.
3. ❌ No hay workaround general en el lenguaje actual.

**Fix recomendado.** En `pengu_infer`/`codegen`, al traducir una llamada dentro
de un cuerpo genérico, sustituir los parámetros del callee por la instanciación
del caller y registrar la especialización (nombre + firma) en la tabla de
monomorfización. Tests de regresión:

- genérico→genérico con 1 y 2 instanciaciones;
- genérico→genérico de `std.atlas`/`std.loom`;
- método de `enchanting shard T` → genérico;
- genérico→genérico→genérico;
- valores de función genéricos (B10 del changelog).

**Fase:** F0. Si no se arregla, **F3/F4 deben diseñarse sin genéricos propios**.

---

### 🔴 B2 — Constructor `ritual` genérico con varias especializaciones

**Síntoma.** La segunda instanciación usa el nombre C de la primera.

```pengu
rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T
    weave get into T:
        return self->value

weave main into int:
    var a as Box of int is calling Box.empty of int
    var b as Box of string is calling Box.empty of string    # 💥
    return 0
```

**C generado:**

```c
Box_int a = Box_empty_int();      /* bien */
Box_string b = Box_empty_int();   /* mal: debería ser Box_empty_string() */
```

El error de gcc es `invalid initializer` en la segunda línea. La primera
especialización “gana” el nombre.

**Impacto.** Los constructores genéricos son el patrón natural para AST,
tablas de símbolos, tipos, vectores y mapas. Sin esto, el código nuevo debe usar
funciones factoría de módulo:

```pengu
weave make_box shard T into Box of T:
    return with value is donum T

var b as Box of string is calling make_box of string   # ✅ funciona
```

**Workaround.** Factoría de módulo (probada). **Fix:** la clave de
monomorfización del constructor debe incluir los argumentos de tipo, no solo el
nombre base. Tests: dos/tres especializaciones, constructores con parámetros,
`Set.empty` de `std.coven`.

**Fase:** F0. Si no se arregla, prohibir `ritual` genérico en PSC.

---

### 🟠 B2b — Llamada cualificada a un tipo (`mod.Type.metodo`)

**Síntoma 1.** El checker acepta y el codegen emite C inválido:

```pengu
import std.compass

var p as compass.Path is calling compass.Path.from_str with "/tmp/x"
```

C generado:

```c
Path p = compass.Path.from_str(pengu_string_from_cstr("/tmp/x"));
/* error: 'compass' no se declaró aquí */
```

**Síntoma 2.** Con `Arena` el checker falla antes:

```pengu
var a as arena.Arena is calling arena.Arena.new
/* E0004: Type 'arena' has no method 'new' */
```

**Causa.** El *call target* se resuelve como una cadena de campos
(`arena` → `Arena` → `new`) en lugar de como un tipo cualificado. El checker y
el codegen no comparten la misma resolución.

**Impacto.** Un proyecto con 30 módulos necesita nombres cualificados para
evitar colisiones (`Parser.new`, `Lexer.new`, `Type.new`). Sin esto, hay que
usar nombres únicos (`new_parser`, `new_lexer`) o factorías de módulo.

**Workaround.** No usar la forma cualificada para constructores; usar el nombre
del tipo importado sin cualificar o una función de módulo. **Fix:** resolver
`mod.Type` como tipo y luego el método; probar `ritual` y métodos estáticos.
También corregir los ejemplos de `std/compass.pengu` y `std/chronicle.pengu`
que hoy muestran la forma rota.

**Fase:** F0/F1 (parser/resolución), antes de escribir muchos módulos.

---

### 🔴 B3 — `std.rites` no puede capturar el stderr de un comando que falla

**Síntoma.** `run_capture` y `run_capture_result` descartan el buffer cuando el
comando sale con código distinto de 0; `run_capture_stderr` devuelve `none`
también en ese caso. No hay API que devuelva a la vez:

- `stdout`,
- `stderr`,
- exit code,
- (opcional) timeout.

**Causa.** El puente `_rites_capture` en [`std/rites.pengu`](std/rites.pengu)
hace `free(buf)` en la rama de fallo y solo deja un mensaje
`"command exited with code N"`.

**Impacto directo.** El driver del compilador necesita ejecutar `gcc`/`clang` y
mapear sus diagnósticos a `.pengu`. Sin stderr, `pengu build` no puede explicar
por qué falló C. También afecta a `git`, a los build scripts y a
`pengu doctor`.

**Workaround actual.** Redirigir a un archivo temporal desde el shell y leerlo
con `archivum.read_file`:

```pengu
calling rites.run_shell with "gcc ... 2> /tmp/pengu_cc_err.txt"
var err as maybe string is calling archivum.read_file with "/tmp/pengu_cc_err.txt"
```

Es frágil, no es portable a Windows y complica el escape de argumentos.

**Fix recomendado.** Nuevo módulo `std.process` (o extensión de `rites`):

```pengu
rune ProcessResult:
    stdout as string
    stderr as string
    code as int
    timed_out as bool

weave run_capture with cmd as string, args as list of string into ProcessResult
```

Implementación C con `popen` para stdout y un archivo/pipe para stderr, o
`fork`/`exec`/`waitpid` en POSIX y `CreateProcess` en Windows. Como mínimo,
devolver el buffer capturado aunque el exit code no sea 0.

**Fase:** F0.

---

### 🔴 B4 — No hay E/S binaria de stdin ni sockets

**Síntoma.**

- `spark.read_line` usa `char buf[4096]`: una línea de más de 4 095 bytes se
  parte.
- `spark.read_char` devuelve `maybe int` y **aloca una caja por byte**.
- No hay `read(n)`, `read_all`, `write(bytes)`, `flush` genérico ni
  `is_tty(fd)`.
- No hay API de sockets.

**Impacto.** El LSP necesita leer un frame `Content-Length: N\r\n\r\n<body>`
exacto. Leer el body byte a byte con `read_char` es correcto pero
innecesariamente caro y con muchas asignaciones. Para `--tcp` no hay absolutamente
nada.

**Fix recomendado.** `std.io`:

```pengu
weave read_stdin with max as int into string
weave read_stdin_all into string
weave write_stdout with data as string into bool
weave write_stderr with data as string into bool
weave flush_stdout into void
weave is_tty with fd as int into bool
```

Y `std.net` (fase LSP, solo si se mantiene `--tcp`):

```pengu
weave listen with host as string, port as int into Socket
weave accept with s as ref to Socket into Socket
weave read with s as ref to Socket, max as int into string
weave write with s as ref to Socket, data as string into int
```

**Fase:** F0 (stdio), F8 (sockets).

---

### 🔴 B5 — Faltan SHA-256, TOML y YAML

**SHA-256.** `pengu_cache.py` y `pengu_lock.py` usan `hashlib.sha256`;
`pengu_tcc.py` verifica el zip de TCC con SHA-256. `std.cipher` solo tiene
CRC-32. Sin SHA-256 no se puede:

- verificar `pengu.lock` existente,
- validar la descarga de TCC,
- mantener claves de caché compatibles,
- cumplir `--locked`/`--frozen`.

**TOML.** `pengu.toml` y `pengu.lock` son TOML. Sin parser/escritor no hay
proyectos ni lockfile. `tomllib` está en Python 3.11+, pero el binario nuevo no
puede usarlo.

**YAML.** `pengu.yaml` es legado pero soportado. El fallback de Python es un
parser de ~35 líneas para un subconjunto; se puede portar. Si se quiere YAML
completo, `libcyaml` está en `extern/`, pero no lo veo necesario.

**Fix recomendado.**

1. `std.digest` con SHA-256 puro (y quizá FNV-1a para caché no criptográfica).
2. `std.toml` con parser y escritor; validar contra `tomllib` con un corpus.
3. Portar el subconjunto YAML actual, o declarar YAML fuera de alcance en la
   primera versión.

**Fase:** F0 (SHA/TOML de lectura), F9 (escritura/lockfile completo).

---

### 🟠 B6 — El LSP actual no usa columnas UTF-16

El protocolo LSP define posiciones en **code units UTF-16** por defecto. El
servidor Python construye `Position(character=err.col - 1)` y el parser cuenta
code points de Python, no bytes ni UTF-16. En un archivo con un emoji antes del
token, la columna se desplaza.

**Impacto.** Diagnósticos, hover, definición, rename y semantic tokens quedan
desalineados en código no ASCII. Los tests actuales son casi todos ASCII, por
eso no lo detectan.

**Fix.** En el LSP nuevo, convertir siempre:

```text
byte offset (lexer) -> code point (lingua) -> UTF-16 code units (LSP)
```

Añadir tests con `ñ`, `日本語`, `😀` y pares subrogados. Extender `std.lingua`
con `utf16_offset` / `encode_utf16` o hacerlo en `psc/lsp/position.pengu`.

**Fase:** F8; el core del compilador puede seguir usando offsets de byte.

---

### 🟠 B7 — Sin límite de profundidad: ~1 000 paréntesis anidados rompen

Con 1 000 paréntesis anidados, `pengu check` responde:

```text
deep.pengu:0:0 maximum recursion depth exceeded
```

No hay un diagnóstico `E…` con posición ni un límite explícito. Un parser
recursivo en C puede directamente desbordar la pila del proceso.

**Fix.** Definir `MAX_PARSE_DEPTH` (por ejemplo 512 o 1 024), contar en el
parser y emitir un error con span. Lo mismo para el checker y el evaluador de
`when`. Añadir tests de 10 000 y de entrada adversarial. Para el LSP, nunca
matar el proceso: diagnosticar y seguir.

**Fase:** F2 (parser), F3 (checker).

---

### 🔴 B8 — Memoria manual: la fuga es la norma si no se disciplina

El lenguaje no tiene GC ni borrow checker. `LANGUAGE.md` §13.4 lo dice con
claridad:

- `defer banish` es la única liberación al salir del scope;
- `"texto {expr}"` como argumento directo **aloca y nadie lo libera**;
- `for ch in s` aloca un `string` owned por iteración;
- las listas y mapas copian bytes, no clonan ni liberan elementos;
- `banish map` no libera las claves/valores que apuntan a buffers.

En un compilador esto se multiplica: tokens, nombres, tipos, mensajes,
manglings, rutas, C generado. Un descuido son cientos de MB en una compilación
grande o en un LSP de larga vida.

**Lo bueno:** la stdlib auditada está limpia bajo ASan (6/6 tests). El riesgo
está en el código nuevo, no en `std.arena`/`std.builder`/`std.json`.

**Reglas obligatorias para PSC:**

1. **Una arena por compilación** para AST, tokens, símbolos y tipos; `free` o
   `reset` al terminar. Nada de `banish` por nodo.
2. **StringBuilder** para codegen y mensajes grandes; nunca `"{out}{x}"` en un
   bucle (O(n²)).
3. **Nunca** pasar una interpolación directa a una función:
   ```pengu
   # ❌ fuga
   calling println with "{x}"
   # ✅
   var msg as string is "{x}"
   defer banish msg
   calling println with msg
   ```
4. **`for ch in s`**: `banish ch` en cada iteración o usar índice sobre
   `bytes of s`.
5. **Contenedores mutables por `ref to`**: un `map`/`list` pasado por valor es
   una copia del header; `put`/`push` no se reflejan en el llamador.
6. **`defer`/`errdefer`** en cada recurso: archivos, builders, arenas, listas.
7. **ASan en CI** para PSC desde la fase F1, no al final.
8. **Code review de ownership** en cada PR; checklist de `banish` y
   `defer`.

**Fase:** F1–F11, permanente.

---

### 🟠 B9 — Orden de mapas no determinista

`std.atlas` documenta que `keys`, `values` y `entries` recorren el orden interno
del hash. El codegen actual usa diccionarios Python (orden de inserción), pero
un PSC que use `map` para emisión puede producir C distinto entre ejecuciones.

**Reglas.**

- Nunca iterar un `map` para emitir código, símbolos o diagnósticos.
- Ordenar por clave (`atlas.keys_sorted` o una lista paralela).
- Los IDs de nodos/tipos deben ser estables y asignarse en orden de fuente.
- El cache key y los golden tests deben ser deterministas.

**Fase:** F4/F5, con tests de reproducibilidad.

---

### 🟠 B10 — `spark.parse_float` devuelve 0 (bug abierto de stdlib)

```pengu
var x as maybe float is calling spark.parse_float with "3.5"
# x.value == 0.0
```

El bug está documentado en `docs/BUGS_FIXED_CHUNK7.md` (X-1) como “hand-off”,
pero **sigue abierto** en 3.0.1. El runtime boxea un `double` y el checker lee
un `float` de 4 bytes.

**Impacto.** Cualquier CLI que parsee floats (configuración, flags, tiempos),
`std.chronicle`, `std.lot` y tests de usuario. El compilador nuevo puede evitar
`spark.parse_float` y escribir su propio parser, pero es deuda que hay que
cerrar.

**Fix.** En `pengu_parse_float`, alocar `sizeof(float)` y guardar
`(float)val`. Test de regresión con `"3.5"`, `"-0.25"`, `"1e3"`, `"nan"`.

**Fase:** F0 (stdlib).

---

### 🟡 B11 — `(chr N)` constante dentro de interpolación

```pengu
var s as string is "a{(chr 200)}b"
# longitud 4; debería ser 3 (a, 0xC8, b)
```

El plegado de constantes emite los dos bytes UTF-8 `c2 88` en lugar del byte
`0xC8`. Afecta a la generación de strings binarios desde código fuente.

**Impacto.** PSC puede evitarlo usando `\xNN` o construyendo el string desde un
`int` variable, pero un compilador que genere C con bytes debe conocerlo.

**Fase:** F4 (codegen), test de regresión.

---

### 🟡 B12 — Ejemplos de documentación que no compilan

`std/compass.pengu` documenta:

```pengu
let p as compass.Path is calling compass.Path.from_str with "a/b.txt"
```

y `std/chronicle.pengu`:

```pengu
var sw as chronicle.Stopwatch is calling chronicle.Stopwatch.new
```

Ambos fallan (B2b). La documentación va por delante del compilador. En un
proyecto auto-hospedado esto es peligroso: el código nuevo se guía por docs
rotas.

**Fix.** Convertir cada ejemplo de doc en un test ejecutable (o al menos
`pengu check`), y corregir la forma cualificada cuando B2b se arregle. Mientras
tanto, documentar la forma correcta (sin cualificar o factoría de módulo).

---

### 5.2 Fugas: evidencia y conclusión

| Prueba | Resultado |
|---|---|
| `test_fundamentals_memory.py` (arena, builder, sourcemap, bitset) con ASan | ✅ 1 passed |
| `test_leaks_comprehensive.py` (strings, listas, mapas, maybe/result, etc.) con ASan | ✅ 5 passed |
| Suite normal | ✅ 1 400 passed |

**Conclusión:** la stdlib que usará PSC **no filtra** en los caminos auditados.
El riesgo de fugas es del código nuevo. Por eso la arquitectura propuesta usa
arena + builders + reglas de ownership, y ASan se activa desde la primera fase.

---

## 📦 6. Piezas que faltan en la stdlib

### 6.1 Prioridad P0 (bloquean el compilador/CLI/LSP)

| Módulo | API mínima | Para qué | Dependencia |
|---|---|---|---|
| `std.digest` | `sha256(string)`, `sha256_file(path)`, `fnv1a` | Lockfile, cache, TCC | Ninguna (puro) |
| `std.toml` | `parse`, `parse_file`, `stringify` | `pengu.toml`, `pengu.lock` | Ninguna (o `tomlc17`) |
| `std.io` | `read_stdin(n)`, `read_all`, `write`, `flush`, `is_tty` | LSP stdio, frames | `antiquus`/libc |
| `std.process` | `run_capture` → `{stdout, stderr, code}` | Driver C, git, build scripts | `antiquus`/libc |
| `std.utf16` | `utf16_len`, `byte_to_utf16`, `utf16_to_byte` | LSP positions | `std.lingua` |

### 6.2 Prioridad P1 (CLI completo / LSP TCP)

| Módulo | API mínima | Para qué | Dependencia |
|---|---|---|---|
| `std.semver` | `parse`, `satisfies`, `compare` | Dependencias | Ninguna |
| `std.net` | `listen`, `accept`, `read`, `write`, `close` | LSP `--tcp` | Sockets del SO |
| `std.zip` / `std.tar` | `extract`, `list` | TCC, assets, vendor | `std.compressus` o `tar` |
| `std.fs` | handles, `read_chunk`, `write_chunk`, `seek` | Hash en streaming | `antiquus` |
| `std.watch` | `snapshot(paths)`, `changed_since` | `pengu watch`, LSP polling | `archivum` |

### 6.3 Prioridad P2 (calidad de vida, no bloquean)

| Módulo | Para qué |
|---|---|
| `std.cst` | Formatter con trivia (si se quiere un fmt más fino) |
| `std.graph` | Orden topológico/SCC de dependencias (se puede hacer a mano) |
| `std.regex` (PCRE2) | Solo si se porta `re` literalmente |
| `std.incremental` | Cache de análisis por hash (se puede hacer en `pengu_cache`) |

> **No propongo** añadir un parser combinatorio ni macros en esta fase. Un
> recursive descent + Pratt escrito a mano es más simple, más rápido y no
> depende de features nuevas del lenguaje.

---

## 🧠 7. Arquitectura y patrón de diseño

### 7.1 Principios

1. **Pipeline explícito, sin monolito.** Cada fase tiene una entrada, una salida
   y un contrato. Nada de un `PenguChecker` de 8 000 líneas.
2. **Sesión explícita.** Un `Session`/`CompileCtx` lleva arena, diagnósticos,
   opciones, source map, tablas y cache. No hay estado global mutable (salvo
   constantes y caches de solo lectura).
3. **Arena por compilación.** AST, tokens, símbolos y tipos viven en una arena;
   se liberan de golpe al terminar. Para el LSP, una arena por *snapshot* de
   documento.
4. **Diagnósticos como datos.** No excepciones para errores de usuario: un
   `DiagnosticBag` acumula y el driver decide el exit code.
5. **Determinismo.** Orden de fuente, IDs estables, mapas ordenados, sin
   timestamps en la salida.
6. **Ownership explícito.** Cada función documenta qué toma, qué presta y qué
   libera. `defer banish` obligatorio para recursos.
7. **El core es una librería.** CLI, LSP, fmt y doc son *frontends* del mismo
   `psc` core; no duplican pipeline.
8. **Compatibilidad de contrato.** Mismos códigos `E`, mismos flags, mismo ABI
   de runtime, mismos artefactos.

### 7.2 Componentes

```text
                    ┌──────────────────────────────┐
                    │          psc/session         │
                    │ arena · diagnostics · opts   │
                    └──────────────┬───────────────┘
                                   │
   ┌──────────────┬────────────────┼────────────────┬──────────────┐
   ▼              ▼                ▼                ▼              ▼
┌───────┐   ┌──────────┐    ┌────────────┐   ┌────────────┐  ┌──────────┐
│source │──▶│  lexer   │───▶│   parser   │──▶│    sema    │─▶│ codegen  │
│span   │   │ tokens   │    │ AST arena  │   │ symbols    │  │ C bundle │
└───────┘   └──────────┘    └────────────┘   │ types      │  └────┬─────┘
                                             │ check      │       │
                                             │ infer      │       ▼
                                             └────────────┘  ┌──────────┐
                                                             │ toolchain│
                                                             │ cc/link  │
                                                             └──────────┘

   Frontends:  psc CLI  ·  psc LSP  ·  psc fmt  ·  psc doc
```

### 7.3 AST: índices en arena, no punteros recursivos

**Recomendación:** nodos planos en un `list`/arena, referenciados por índice.

```pengu
rune Node:
    kind as NodeKind        # omen/int
    start as int            # offset de byte
    end as int
    a as int                # índices de hijos / payload
    b as int
    c as int
    text_id as int          # índice en el pool de strings
```

Ventajas:

- No hay punteros que se invaliden al crecer la lista.
- No hay `banish` por nodo; la arena/lista se libera de golpe.
- Es serializable, determinista y fácil de diffear en golden tests.
- El LSP puede guardar snapshots y comparar IDs.
- No se necesita `cyclus` ni `ref to Node` para el AST.

Desventajas:

- Menos type safety: `a`, `b`, `c` son enteros; hay que validar por `kind`.
- Hay que mantener tablas laterales para listas de hijos y strings.
- Es más verboso que un `rune` tipado por variante.

**Alternativa** (si se prefiere legibilidad): `rune Expr cyclus` con `ref to
Expr` + arena. Es válida (el conformance `arena_ast` la prueba), pero obliga a
que la arena viva más que todos los nodos y a tener cuidado con listas de
punteros. Para un compilador con parser incremental y LSP, los índices son más
robustos.

**Recomendación final:** índices para el AST; `rune` tipados para los objetos
“de dominio” (Type, Symbol, Diagnostic) que no crecen dentro de una lista
mutable.

### 7.4 Sesión, diagnósticos y spans

```pengu
rune Session:
    arena as Arena
    diags as DiagnosticBag
    sources as SourceMap
    options as Options
    symbols as SymbolTable
    types as TypeTable
```

- `SourceFile`: texto, offsets de línea, nombre, hash.
- `Span`: `start`/`end` de byte; el LSP convierte a línea/columna/UTF-16 en el
  borde.
- `DiagnosticBag`: severidad, código, mensaje, labels, help, note, related.
- El parser **nunca** lanza; emite `ParseError` como diagnóstico y produce un
  AST parcial.
- El checker acumula; el driver imprime y devuelve 1.
- Para el LSP, el mismo `check` produce diagnósticos sin abortar.

### 7.5 Ownership en la práctica

| Recurso | Dueño | Liberación |
|---|---|---|
| AST / tokens / símbolos | `Session.arena` | `arena.free` / `reset` |
| Strings de salida | `StringBuilder` | `banish sb` |
| Nombres temporales | variable local | `defer banish` |
| Mapas/listas mutables | llamador | `banish` o `ref to` |
| Archivos | `archivum` (path) | no hay handle; no aplica |
| Diagnósticos | `DiagnosticBag` | `free_diagnostics` / `banish` |
| Cache en disco | `psc/cache` | sin recurso vivo |

**Regla de oro:** si una función devuelve `string`/`list`/`map`/`maybe`/`result`,
el llamador es dueño; si recibe `ref to`, no lo libera. Documentarlo en cada
`## ## Memoria`.

### 7.6 Determinismo y cache

- IDs de nodos/tipos/símbolos en orden de fuente.
- Emisión de módulos en orden topológico estable.
- `map` solo para búsqueda, nunca para orden de salida.
- Cache key: `sha256(version + impl_id + fuentes + flags + runtime)`.
- `impl_id` distinto para `stage0-python` y `psc`, para no mezclar binarios.
- Cache separada por implementación durante la transición.
- Tests: compilar dos veces y comparar `bundle.c` normalizado.

### 7.7 CLI y LSP comparten el core

```text
psc build  ─┐
psc check  ─┼─▶ psc_core.compile(session, mode) ─▶ BuildResult
psc test   ─┤
psc lsp    ─┘   (modo diagnostics / symbols / completion)
```

El LSP no debe invocar al CLI por `subprocess`; llama al core en proceso. El
CLI y el LSP comparten:

- resolución de módulos,
- parser + checker + inferencia,
- source map,
- diagnósticos,
- cache de símbolos.

---

## 🗂️ 8. Nueva organización del proyecto

### 8.1 Árbol propuesto

```text
psc/                                  # 🆕 implementación en PenguScript
├── pengu.toml                        # proyecto PSC (entry, links, perfil)
├── README.md                         # cómo construir y probar PSC
├── src/
│   ├── main.pengu                    # entry del CLI (fino)
│   └── psc/
│       ├── session.pengu             # Session, options, arena, diags
│       ├── source.pengu              # SourceFile, LineIndex, Span
│       ├── diagnostics.pengu         # códigos E/W, bag, render
│       ├── token.pengu               # TokenKind, Token, helpers
│       ├── lexer.pengu               # escáner principal
│       ├── lexer_indent.pengu        # INDENT/DEDENT/NEWLINE
│       ├── ast.pengu                 # Node, NodeKind, side tables
│       ├── parser/
│       │   ├── parser.pengu          # recursive descent
│       │   ├── expr.pengu            # Pratt / precedencia
│       │   ├── types.pengu           # tipos y genéricos
│       │   ├── patterns.pengu        # judge / when
│       │   └── recovery.pengu        # errores y sincronización
│       ├── sema/
│       │   ├── modules.pengu         # imports, ciclos, topología
│       │   ├── symbols.pengu         # scopes, privacidad, insignia
│       │   ├── types.pengu           # Type, interning, unificación
│       │   ├── check.pengu           # declaraciones y statements
│       │   ├── infer.pengu           # expresiones
│       │   ├── generics.pengu        # monomorfización, bounds
│       │   ├── concepts.pengu        # concept/bind/enchanting
│       │   └── comptime.pengu        # when, defined, define
│       ├── codegen/
│       │   ├── ctype.pengu           # Type -> C
│       │   ├── names.pengu           # mangling, colisiones
│       │   ├── decls.pengu           # runes/omens/weaves
│       │   ├── exprs.pengu           # expresiones
│       │   ├── stmts.pengu           # statements/control
│       │   ├── generics.pengu        # especializaciones
│       │   ├── interpolate.pengu     # strings
│       │   ├── dce.pengu             # reachability
│       │   └── bundle.pengu          # secciones, line markers
│       ├── project/
│       │   ├── manifest.pengu        # pengu.toml
│       │   ├── lockfile.pengu        # pengu.lock
│       │   ├── paths.pengu           # layouts, std, runtime
│       │   ├── toolchain.pengu       # gcc/clang/tcc/msvc
│       │   ├── cache.pengu           # claves y binarios
│       │   ├── semver.pengu          # constraints
│       │   └── deps.pengu            # git/vendor/lock
│       ├── cmd/
│       │   ├── build.pengu
│       │   ├── run.pengu
│       │   ├── check.pengu
│       │   ├── test.pengu
│       │   ├── expand.pengu
│       │   ├── eval.pengu
│       │   ├── time.pengu
│       │   ├── watch.pengu
│       │   ├── init.pengu
│       │   ├── clean.pengu
│       │   ├── doctor.pengu
│       │   ├── gc.pengu
│       │   ├── fmt.pengu
│       │   ├── doc.pengu
│       │   ├── assets.pengu
│       │   ├── add.pengu
│       │   ├── remove.pengu
│       │   ├── update.pengu
│       │   ├── upgrade.pengu
│       │   ├── tree.pengu
│       │   ├── metadata.pengu
│       │   ├── verify.pengu
│       │   ├── vendor.pengu
│       │   └── bind.pengu            # wrapper del helper externo
│       ├── fmt.pengu                 # formatter
│       ├── docgen.pengu              # docs Markdown/HTML
│       └── lsp/
│           ├── server.pengu          # bucle y dispatch
│           ├── protocol.pengu        # initialize/capabilities
│           ├── transport.pengu       # stdio / TCP
│           ├── positions.pengu       # UTF-8 -> UTF-16
│           ├── symbols.pengu         # índice de workspace
│           ├── diagnostics.pengu     # publishDiagnostics
│           └── features/
│               ├── completion.pengu
│               ├── hover.pengu
│               ├── definition.pengu
│               ├── references.pengu
│               ├── symbols.pengu
│               ├── format.pengu
│               ├── semantic.pengu
│               ├── code_actions.pengu
│               ├── inlay.pengu
│               └── rename.pengu
├── tests/
│   ├── unit/                         # tests .pengu del core
│   ├── corpus/                       # enlaces/copias del corpus compartido
│   └── golden/                       # C, fmt, doc, diagnósticos
└── tools/
    └── bind/                         # contrato del helper (no el helper)
```

### 8.2 Qué se queda donde está

| Ruta actual | Se queda | Motivo |
|---|---|---|
| `std/` | ✅ Compartida | La usan stage0 y PSC; no duplicar |
| `pengu_runtime.h` | ✅ Raíz | ABI compartida |
| `std_c/` | ✅ Raíz | C nativo compartido |
| `build_runtime.py` | ✅ Raíz | Release/runtime; no runtime del usuario |
| `make_release.py` | ✅ Raíz | Release dev-only |
| `pengu_parser/`, `pengu_project.py`, `pengu_lsp/` | ✅ Intactos | Stage0, congelados |
| `tests/` | ✅ Compartidos | Oráculo de paridad |
| `docs/` | ✅ Compartidos | Documentación del lenguaje |
| `psc/` | 🆕 Nuevo | Implementación nueva |

**No mover nada del Python ahora.** El usuario lo pidió así y es lo correcto:
stage0 debe seguir funcionando y siendo el árbitro hasta que PSC pase el gate.

### 8.3 Mapa Python actual → módulo PSC

| Python actual | PSC |
|---|---|
| `pengu_parser/pengu_grammar.py` + `pengu_parser.py` | `psc/lexer/*` + `psc/parser/*` |
| `pengu_parser/pengu_errors.py` | `psc/diagnostics.pengu` |
| `pengu_parser/pengu_symbols.py` | `psc/sema/symbols.pengu` + `modules.pengu` |
| `pengu_parser/pengu_types.py` | `psc/sema/types.pengu` |
| `pengu_parser/pengu_infer.py` | `psc/sema/infer.pengu` |
| `pengu_parser/pengu_checker.py` | `psc/sema/check.pengu` (dividido) |
| `pengu_parser/pengu_comptime.py` | `psc/sema/comptime.pengu` |
| `pengu_parser/pengu_codegen/*` | `psc/codegen/*` |
| `pengu_parser/pengu_dce.py` | `psc/codegen/dce.pengu` |
| `pengu_project.py` | `psc/cmd/*` + `psc/project/*` |
| `pengu_cache.py` | `psc/project/cache.pengu` |
| `pengu_paths.py` | `psc/project/paths.pengu` |
| `pengu_lock.py` / `pengu_semver.py` | `psc/project/lockfile.pengu` / `semver.pengu` |
| `pengu_doc.py` | `psc/docgen.pengu` |
| `pengu_assets.py` | `psc/cmd/assets.pengu` + `psc/assets.pengu` |
| `pengu_lsp/*` | `psc/lsp/*` |
| `pengu_bind.py` | ❌ Ejecutable externo `pengu-bind` |

### 8.4 Reglas de estilo del proyecto nuevo

- Máximo **600–800 líneas por archivo**; split por responsabilidad.
- Un módulo = una etapa o un comando; no “utilidades varias”.
- `insignia psc_<modulo>_` por archivo para evitar colisiones de C.
- Nombres públicos sin `_`; helpers privados con `_`.
- Doc comments `##` con ejemplo y sección `## ## Memoria`.
- Prohibido `"{a}{b}"` en bucles; usar `StringBuilder`.
- Prohibido pasar interpolaciones directas a funciones; siempre variable +
  `defer banish`.
- `when os` solo en `psc/project/paths.pengu` y `psc/project/toolchain.pengu`.
- Tests en `psc/tests/` y reutilización del corpus de `tests/conformance/`.
- Nada de estado global mutable; todo por `Session`.

---

## 🗓️ 9. Plan completo por fases

### 9.1 Resumen

| Fase | Objetivo | Persona-semanas | Riesgo |
|---|---|---:|---|
| **F0** | Desbloquear bugs + infra de paridad + std P0 | 3–4 | 🔴 Alto |
| **F1** | Source map, diagnósticos y lexer | 3–4 | 🟡 Medio |
| **F2** | Parser completo + AST + recuperación | 6–8 | 🟠 Medio-alto |
| **F3** | Semántica: symbols, types, check, infer | 12–16 | 🔴 Muy alto |
| **F4** | Codegen C completo | 12–16 | 🔴 Muy alto |
| **F5** | Driver mínimo + primer auto-compilado | 4–6 | 🟠 Alto |
| **F6** | CLI completo (core + proyecto) | 8–10 | 🟠 Alto |
| **F7** | Herramientas: fmt, doc, assets, watch | 6–8 | 🟡 Medio |
| **F8** | LSP completo | 10–14 | 🟠 Alto |
| **F9** | Dependencias y package manager | 6–10 | 🟠 Medio-alto |
| **F10** | Bind externo + release | 3–4 | 🟡 Medio |
| **F11** | Bootstrap final y switchover | 4–6 | 🔴 Alto |
| **Total** | | **77–106** | |

> Son estimaciones de esfuerzo, no una promesa. Un solo desarrollador a tiempo
> completo: **18–24 meses**. Un equipo de 3 con perfiles senior: **7–10 meses**
> (F3 y F4 no se paralelizan fácilmente). El **MVP auto-compilable** (F0–F5) es
> aproximadamente la mitad.

### 9.2 Dependencias entre fases

```text
F0 ──▶ F1 ──▶ F2 ──▶ F3 ──▶ F4 ──▶ F5 ──▶ F6 ──▶ F9
                 │                 │        │
                 │                 │        └──▶ F7
                 │                 └──▶ F10
                 └──▶ F8 (LSP; solo necesita parser+sema)
```

- **F8** puede empezar en paralelo con F4/F5 en cuanto F3 estabilice el API de
  símbolos y diagnósticos.
- **F7** (fmt) puede empezar en cuanto F2 produzca AST/tokens; doc necesita F3.
- **F10** (bind) es independiente y se puede hacer en paralelo desde F0.
- **F9** requiere F6 (CLI y TOML de escritura).

---

### 🧱 F0 — Desbloqueo, std P0 e infraestructura de paridad

**Objetivo:** que el terreno esté firme antes de escribir el compilador.

**Tareas.**

1. **Congelar stage0.** Tag `stage0-3.0.1`; declarar el lenguaje congelado
   durante la migración. Cualquier feature nueva exige doble implementación.
2. **Harness de paridad** (`tools/parity/`, Python dev-only):
   - ejecuta stage0 y PSC sobre el mismo caso;
   - compara exit code, stdout, stderr y artefacto;
   - compara diagnósticos por código/línea/columna;
   - modo `--update-golden` para C/fmt/doc.
3. **Separar caché por implementación.** `impl_id` en la cache key; nunca
   mezclar binarios de stage0 y PSC.
4. **Arreglar B1 y B2** (o aprobar formalmente “PSC sin genéricos propios”).
   Yo recomiendo arreglarlos: es una inversión de alto retorno y elimina una
   restricción enorme del código nuevo. La estimación de 1–3 semanas es
   optimista; el arreglo real puede ser mayor según cuánto toque inferencia y
   codegen.
5. **Arreglar B2b** (resolución de tipo cualificado) y actualizar docs.
6. **Añadir `std.digest`, `std.toml` (lectura), `std.io`, `std.process`.**
7. **Crear `psc/`**: `pengu.toml`, `src/main.pengu`, esqueleto de módulos,
   CI que lo compile con stage0.
8. **Corpus y fuzz:** reutilizar `tests/conformance/` + los seeds de
   `scripts/fuzz/`.

**Entregables.**

- `tools/parity/` funcionando contra los 126 casos.
- Tests de regresión de B1/B2/B2b.
- `std.digest`, `std.toml`, `std.io`, `std.process` con tests.
- `psc/` compilando un “hello world” con stage0.
- ADR-0001: arquitectura y ownership; ADR-0002: AST por índices.

**Criterio de salida.**

- Suite actual sigue verde (1 400+).
- B1/B2 tienen tests que fallan antes y pasan después.
- `psc init`/`psc build` mínimo compila `hello.pengu`.
- El harness detecta una diferencia artificial entre dos compiladores de prueba.

---

### 🔤 F1 — Source, diagnósticos y lexer

**Objetivo:** convertir texto en tokens con spans exactos y errores útiles.

**Tareas.**

1. `SourceFile`: BOM, CRLF, `LineIndex`, offsets de byte, hash.
2. `TokenKind`: keywords, identificadores, números (dec/hex/bin/oct/float),
   strings (normal/triple/raw), char, operadores, `INDENT`/`DEDENT`/`NEWLINE`,
   `EOF`, tokens suaves (`type of`, `size of`, `over`, `frozen`, `and`/`or`).
3. Lexer por estados:
   - comentarios `#` y doc `##`;
   - strings con `\u{...}`, `\xNN`, escapes, interpolación `{expr}` con llaves
     balanceadas;
   - raw strings;
   - `antiquus` con cuerpo triple y extracción antes del parser;
   - números con `_`.
4. Post-lexer de indentación: pila de niveles, tabs/espacios, alineación,
   errores de dedent.
5. `DiagnosticBag` + render ANSI/plain/JSON; códigos `E0000`/`W0005`.
6. Token dump y golden tests.

**Tests.**

- Tokenizar los 126 casos + `std/*.pengu` + tests internos.
- Comparar tipo/lexema/posición con el lexer de stage0 (extraer tokens con un
  script de desarrollo).
- Fuzz con bytes aleatorios, BOM, CRLF, Unicode, strings sin cerrar,
  interpolaciones anidadas.
- Benchmarks: 1 MB de fuente, tokens/segundo.

**Criterio de salida.**

- 100 % de coincidencia de tokens en el corpus (salvo metadatos internos de
  Lark).
- Cero crashes con fuzz de 1 M de entradas.
- Errores de string/indentación con línea/columna.

---

### 🧩 F2 — Parser, AST y recuperación

**Objetivo:** producir el mismo árbol semántico que stage0 para todo el corpus.

**Tareas.**

1. AST por índices (`Node`, `NodeKind`, tablas laterales de hijos/strings).
2. Recursive descent:
   - declaraciones top-level: `import`, `include`, `link`, `ldflag`,
     `insignia`, `const`, `var`, `let`, `rune`, `echo`, `omen`, `alias`,
     `seal`, `concept`, `bind`, `weave`, `enchanting`, `antiquus`, `test`,
     `when`, `declare`;
   - statements: `set`, `if`/`unless`, `while`, `for`, `when` statement,
     `with`, `unsafe`, `defer`/`errdefer`, `banish`, `return`, `break`/
     `continue` con label, `expr_stmt`, `labeled_loop`;
   - expresiones Pratt con la tabla exacta de precedencia de `LANGUAGE.md`
     §6.1;
   - tipos: `ref to`, `frozen`, `weave`, `array`, `slice`, `many`, `list`,
     `map`, `maybe`, `result`, `opaque`, `shard`, `where`, tuplas;
   - `judge`/`when` con payloads, guardas, or-patterns y narrowing;
   - `with:` como expresión y como statement;
   - `lambda` sin captura;
   - `do:` como bloque-valor;
   - `or else` / `or return` / `or:`;
   - literales indentados, arrays, mapas, `donum`, `defined`.
3. Manejo de `NEWLINE`/`INDENT`/`DEDENT`, una línea por statement, `:` simple.
4. Recuperación de errores: sincronizar en `NEWLINE`/`DEDENT`; nodos `Error`;
   no abortar; límite de profundidad.
5. AST dump canónico para golden tests.

**Tests.**

- Parsear todo el corpus/std/tests; comparar éxito/fracaso y estructura
  normalizada.
- Golden de AST para 20–30 casos representativos.
- Errores: posición, código, ayuda; todos los casos de sintaxis del catálogo.
- Fuzz de parser; profundidad; entradas truncadas.
- LSP: parsear buffers incompletos sin crash.

**Criterio de salida.**

- 100 % del corpus parsea igual (éxito/fracaso y spans).
- AST equivalente en los casos dorados.
- Cero crashes; límite de profundidad probado.
- Tiempo de parseo ≤ stage0 (objetivo: mejor).

---

### 🧠 F3 — Semántica: módulos, símbolos, tipos, checker e inferencia

**Objetivo:** el corazón del compilador. Es la fase más grande y riesgosa.

**Subfases.**

| Subfase | Contenido |
|---|---|
| **F3a** | Resolución de imports, ciclos, orden topológico, `std/`, `src/`, `lib/`, privacidad, `insignia` |
| **F3b** | Scopes, símbolos, preludio de builtins, declaraciones, colisiones, `static var` |
| **F3c** | Modelo de tipos: primitivos, refs, arrays, slices, listas, mapas, maybe, result, tuplas, runas, omens, echos, seals, alias, conceptos, funciones, genéricos |
| **F3d** | Checker de declaraciones y statements: mutabilidad, `banish`/`defer`, control de flujo, `with:`, `unsafe`, labels, retornos |
| **F3e** | Inferencia de expresiones: operadores, llamadas, métodos, campos, índices, interpolación, `judge`, `when`, `or`, `try` |
| **F3f** | Genéricos: bounds, sustitución, monomorfización, valores de función, tipos anidados |
| **F3g** | `concept`/`bind`/`enchanting`, coherencia, métodos primitivos, `@mutates` |
| **F3h** | `when`/`defined`/`comptime`, `-D`, `os`/`arch`/`compiler`/`main`/`debug` |
| **F3i** | Catálogo de errores `E0000–E0070`, warnings `W0000–W0013`, `help`/`note` |
| **F3j** | Recuperación para LSP: símbolos parciales, diagnósticos sin abortar |

**Tareas clave.**

- Portar el modelo de tipos con canonicalización e interning.
- Respetar coerciones numéricas, punteros, `frozen`, `char`/`byte`.
- Respetar la semántica de ownership que el checker ya valida (`banish`,
  `some`, `ok_of`, `err_of`, `defer`, `errdefer`).
- Respetar la resolución de métodos: `enchanting`, `ritual`, módulos,
  prioridad, `self` como `ref to`.
- Reproducir los códigos de error y las posiciones; el texto puede empezar
  difiriendo, pero el harness debe marcar la diferencia.
- Nada de excepciones: `DiagnosticBag` + `result` interno.

**Tests.**

- `psc check` sobre los 126 casos y todo `std/` + tests internos.
- Comparar con stage0: aceptar/rechazar, código, línea, columna.
- Los tests negativos de `tests/compiler/` son el catálogo de casos.
- Fuzz semántico: mutaciones de programas válidos.
- ASan/UBSan sobre el checker.

**Criterio de salida.**

- 100 % de aceptación/rechazo igual en el corpus.
- ≥95 % de diagnósticos con código/línea/columna iguales (objetivo 100 %).
- Ningún crash con entradas adversariales.
- `psc check` de `std/` completo sin errores.
- El LSP puede obtener símbolos y diagnósticos parciales.

> **Riesgo:** si F3 se desvía, F4 y F5 se contaminan. No empezar F4 hasta que
> F3 tenga una tasa alta de paridad en el corpus.

---

### 🖨️ F4 — Codegen C

**Objetivo:** generar el mismo C semántico y compilarlo con gcc/clang/tcc.

**Subfases.**

| Subfase | Contenido |
|---|---|
| **F4a** | `Type -> C`, nombres, `insignia`, mangling de genéricos, orden topológico de tipos |
| **F4b** | Declaraciones: runes, echos, omens, seals, alias, consts, `declare`, `antiquus`, `include`, `link` |
| **F4c** | Prototipos y forward declarations; `static inline` |
| **F4d** | Expresiones: literales, operadores, casts, llamadas, métodos, campos, `->`, índices, slices, `some`, `ok_of`/`err_of`, `transmute`, `size of`, `type of`, `banish` |
| **F4e** | Statements: declaraciones, `set`, control, loops, `defer`/`errdefer`, `unsafe`, labels/gotos, `judge`/`when` |
| **F4f** | Genéricos: especialización, bounds, funciones como valores, callbacks, tipos anidados |
| **F4g** | `with:` builders, `or:`/`or else`/`or return`, bloques-valor |
| **F4h** | Interpolación, lambdas, `functor`, strings y bytes |
| **F4i** | Entry point, `--test` entry, `main`/`pengu_main`, ABI |
| **F4j** | Line markers, DCE exacto, `--no-dce`, `--prune-types`, `--dce-scope`, `--prune-native` |
| **F4k** | C99 estricto, MSVC, TCC, atributos, `restrict`, `#line` |
| **F4l** | Remapeo de diagnósticos de C a `.pengu` |

**Tareas clave.**

- El C generado debe compilar con `-Wall -Werror` en gcc y clang.
- Respetar `pengu_runtime.h` y `PENGU_ABI_VERSION` sin cambios.
- Reproducir el comportamiento de ownership: `banish`, `defer`, `errdefer`,
  `some`/`ok`/`err`, strings owned.
- Cuidado con `list of ref to T`, `map` de structs, arrays multidimensionales,
  callbacks y `opaque`.
- DCE: no eliminar nada alcanzable; comparar con stage0.
- Emitir en orden determinista.

**Tests.**

- Compilar y ejecutar los 126 casos + `std/` tests.
- Matriz gcc/clang/tcc; Windows/macOS en CI.
- ASan/UBSan de los programas generados.
- Golden de C normalizado para 20 casos.
- Tamaño y tiempo de compilación vs stage0 (no empeorar >20 %).
- Tests de los bugs B1/B2/B11.

**Criterio de salida.**

- Todos los casos compilan y se ejecutan con salida idéntica.
- `std/` completo compila.
- Cero fugas ASan en el corpus.
- `bundle.c` determinista entre ejecuciones.
- DCE y `--test` funcionan.

---

### 🚀 F5 — Driver mínimo y primer auto-compilado

**Objetivo:** demostrar que PSC puede compilarse a sí mismo **antes** de portar
todo el CLI y el LSP.

**Tareas.**

1. `psc check <file>` y `psc build <file>` para un solo archivo y un proyecto
   con `pengu.toml` mínimo.
2. Resolución de módulos, lectura de fuentes, invocación de cc, link contra
   `libpengu_runtime.a`, salida a `build/`.
3. `psc run <file>` (sin caché al principio), `psc expand`.
4. Diagnósticos y exit codes básicos.
5. Compilar PSC con stage0 → `psc-stage1`.
6. Compilar PSC con `psc-stage1` → `psc-stage2`.
7. Compilar PSC con `psc-stage2` → `psc-stage3`.
8. Comparar stage1/2/3: comportamiento, corpus, C normalizado.
9. Corregir lo que salga; aquí se descubren los límites reales de F3/F4.

**Criterio de salida.**

- `psc-stage2` compila `psc` y pasa el corpus.
- `stage2` y `stage3` producen C equivalente (fixed point).
- PSC compila los 126 casos y `std/`.
- Documento `docs/selfhost/BOOTSTRAP.md` con el diagrama T.

> **Este es el hito que decide si el proyecto es viable.** Si no se logra,
> conviene revisar la arquitectura antes de seguir con CLI/LSP.

---

### 🖥️ F6 — CLI completo

**Objetivo:** reemplazar el CLI Python para el uso diario.

**Comandos y prioridad.**

| Prioridad | Comandos |
|---|---|
| **P0** | `build`, `run`, `check`, `test`, `expand`, `eval`, `time` |
| **P1** | `init`, `new`, `clean`, `doctor`, `gc`, `watch`, `fmt`, `doc`, `assets` |
| **P2** | `add`, `remove`, `update`, `upgrade`, `tree`, `metadata`, `verify`, `vendor` |
| **P3** | `benchmark`, `selftest` (dev), `bind` (wrapper) |

**Tareas.**

- `std.invoke` + parser manual para `--`, `parse_known_args`, subcomandos,
  flags repetidos y valores por defecto.
- Config: TOML, perfiles, `src_dir`, `lib_dir`, `c_dir`, `cc`, `links`,
  `lib_dirs`, `include_dirs`, `cflags`, `ldflags`, `defines`, `assets`.
- Toolchain: gcc/clang/tcc/msvc, `--cc`, `--target-compiler`, PCH, `--strict-c99`.
- Cache: SHA-256, `--no-cache`, `--clear-cache`, `--ephemeral`, `--keep`.
- Salida JSON Lines para CI, `--deny-deprecated`, warnings.
- Exit codes y mensajes de error.
- Templates de `init`/`new` (exe, cli, pengu-lib, cbind).
- No implementar todavía cross/WASM avanzados; aceptar el flag y fallar con un
  mensaje claro “not yet” si se decide diferir.

**Criterio de salida.**

- Matriz de paridad de comandos: flags, exit code, stdout/stderr, artefactos.
- `psc build` y `psc run` sobre los proyectos de `tests/`.
- `--json` compatible.
- `psc doctor` sin Python.
- Cache correcta (misma fuente → hit; cambio → miss).

---

### 🛠️ F7 — Herramientas de desarrollo

**Objetivo:** `fmt`, `doc`, `assets`, `watch`, `benchmark`.

| Herramienta | Estrategia | Test |
|---|---|---|
| `psc fmt` | Portar el formatter line-based; preservar literales; indentación | Byte-idéntico en corpus; idempotencia |
| `psc fmt --stdin` | Leer `std.io` y escribir stdout | Tests |
| `psc doc` | Generar Markdown/HTML desde símbolos y `##` | Diff contra stage0 |
| `psc assets` | Generar `arca.pengu` + C embebido | Compilar y ejecutar assets |
| `psc watch` | Polling de mtimes (no inotify) | Test con archivo modificado |
| `psc benchmark` | Shell out a `benches/` | Smokes; no bloqueante |
| `psc selftest` | Si se queda pytest, marcar dev-only | Documentar |

**Criterio de salida.**

- `fmt` no cambia semántica y converge en 2 pasadas.
- `doc` produce el mismo contenido (puede cambiar el orden si es estable).
- `assets` genera código compilable.

---

### 🧠 F8 — LSP

**Objetivo:** reemplazar pygls con un servidor propio, sobre el core de PSC.

**Arquitectura.**

```text
stdin bytes ──▶ transport (Content-Length)
                    │
                    ▼
               JSON-RPC dispatch ──▶ worker/queue
                    │                    │
                    │                    ├─ parse/check (full sync)
                    │                    ├─ symbol index
                    │                    └─ diagnostics
                    ▼
              stdout (Content-Length)
```

**Fases internas.**

1. **Transporte:** `std.io.read(n)`, framing con `std.jsonrpc`, `Content-Length`,
   UTF-8. `--stdio` primero; `--tcp` después si se aprueba.
2. **Ciclo de vida:** `initialize`, `initialized`, `shutdown`, `exit`,
   `$/cancelRequest`, `workspace/didChangeConfiguration`,
   `workspace/didChangeWatchedFiles`, `textDocument/didOpen|didChange|didSave|
   didClose`.
3. **Diagnósticos:** parse+check con debounce; `publishDiagnostics` con versión;
   recuperación; UTF-16.
4. **Inteligencia:** completion, hover, signature help, definition,
   implementation, references, document highlight, document symbols, workspace
   symbols, folding, semantic tokens, inlay hints, code lens, code actions,
   prepareRename/rename, formatting, on-type formatting.
5. **Concurrencia:** un hilo worker con cola y `std.filum`; o validación
   síncrona con debounce si el rendimiento alcanza. Nunca bloquear el bucle de
   lectura más de lo necesario.
6. **Cachés:** símbolos por URI, grafo de imports, invalidación de dependientes,
   hash de contenido.
7. **Rutas/URI:** `file://`, Windows `C:\`, percent-encoding, espacios.
8. **Tests de cable:** un cliente real (Python o VS Code) que habla JSON-RPC.

**Criterio de salida.**

- La extensión de VS Code funciona con `psc lsp --stdio`.
- Diagnósticos, completion, hover, definition, references y symbols con
  paridad funcional.
- Posiciones correctas con `ñ`, CJK y emoji.
- Sin fugas en un LSP de 1 000 ciclos de didChange (ASan).
- Latencia acceptable en un proyecto de 100 módulos.

---

### 📦 F9 — Dependencias y package manager

**Objetivo:** `add`, `remove`, `update`, `upgrade`, `tree`, `metadata`,
`verify`, `vendor`.

**Tareas.**

- `std.toml` de escritura y `pengu.lock`.
- `semver` (constraints, tags).
- Git por `std.rites`: clone, pull, checkout, tags.
- Copia de árboles, vendor, caché global de dependencias.
- `build.pengu` de dependencias: ejecutar con `psc run` y `--trust`.
- `verify` con SHA-256.
- Resolución de conflictos y errores `E0061`/`E0062`.
- `--locked`/`--frozen` y cache offline.

**Criterio de salida.**

- Los tests de dependencias actuales pasan con PSC.
- Un proyecto con una dependencia local y una git se construye offline con
  `vendor`.
- `pengu.lock` existente se verifica sin reescribirlo.

---

### 🔌 F10 — Bind externo y release

**Objetivo:** integrar el helper y empaquetar el binario.

**Tareas.**

1. Extraer `pengu_bind.py` a un ejecutable `pengu-bind` (PyInstaller
   `--onefile`, o el mecanismo que prefieras).
2. Contrato estable:
   - mismos flags que hoy (`--prefix`, `--links`, `--output`, `--include-paths`,
     `--define`, `--preprocessed`, `--auto-import`, …);
   - salida `.d.pengu` a stdout o archivo;
   - exit codes 0/1/2;
   - errores a stderr.
3. `psc bind` localiza el helper: `$PENGU_BIND`, mismo directorio que `psc`,
   `PATH`. Si no está, error claro con instrucciones.
4. Tests de paridad del `.d.pengu` contra stage0.
5. Empaquetar `psc` + `pengu-bind` + `std/` + runtime en portable/FHS.
6. `make_release.py` puede seguir generando el paquete, pero el binario `psc` no
   debe requerir Python.

**Criterio de salida.**

- `pengu-bind` genera los mismos bindings en el corpus de headers.
- `psc bind` funciona sin Python instalado (el helper está congelado).
- El paquete portable funciona en Linux/Windows/macOS.

**Decisión pendiente:** si `pengu-bind` debe ser 100 % sin Python, esto se
convierte en F10b (parser de cabeceras C o libclang). Es un proyecto aparte.

---

### 🏁 F11 — Bootstrap final y switchover

**Objetivo:** que `pengu` sea PSC en producción, sin Python en runtime.

**Checklist de gate.**

- [ ] `psc` compila los 126 casos de conformidad con salida idéntica.
- [ ] `psc` compila `std/` completo.
- [ ] Pasa la suite de `tests/compiler/`, `tests/stdlib/`, `tests/codegen/`,
      `tests/build/`, `tests/tooling/`, `tests/compat/`.
- [ ] Pasa los tests de LSP (de cable).
- [ ] `psc fmt` byte-idéntico en el corpus.
- [ ] `psc doc` equivalente.
- [ ] `psc build/run/check/test` con paridad de flags/exit codes.
- [ ] Windows, Linux y macOS.
- [ ] ASan/UBSan sin fugas en el corpus.
- [ ] `stage2` y `stage3` con C equivalente (fixed point).
- [ ] Cache separada y correcta.
- [ ] `pengu-bind` congelado y probado.
- [ ] Documentación actualizada; Python marcado como stage0.

**Switchover.**

1. Publicar `pengu` (PSC) como comando principal; `pengu-stage0` como fallback.
2. Mantener `pengu-stage0` una release; anunciar deprecación.
3. Congelar/archivar el Python; no borrarlo de golpe.
4. Tener un plan de rollback: si PSC falla, `pengu-stage0` sigue disponible.
5. Actualizar CI/release para construir PSC con stage0 y luego self-compile.

**Criterio de salida.**

- Un usuario sin Python instalado puede `pengu build`, `pengu run`,
  `pengu fmt`, `pengu doc` y `pengu lsp`.
- `pengu bind` funciona con el helper congelado.
- El release es reproducible y verificable.

---

## 🚦 10. Estrategia de migración y paridad

### 10.1 Niveles de paridad

| Nivel | Qué exige | Cuándo |
|---|---|---|
| **A** | Mismo accept/reject, mismo exit code, mismo stdout/stderr, artefacto ejecutable | F3–F6 |
| **B** | Mismos códigos `E`/`W`, misma línea/columna, mismos help/notes | F3–F6 |
| **C** | Mismo `bundle.c` normalizado (sin line markers ni rutas), mismo `fmt`/`doc` | F4/F7 |
| **D** | Fixed point stage2=stage3, cache reproducible, release verificable | F5/F11 |

Para el switch se exige **A + B**. C es deseable para DCE/diagnósticos; D es
obligatorio para release.

### 10.2 Dual-run

Mientras dure la migración:

```text
              ┌──────────────┐
source.pengu ─┤ stage0 Python├─▶ binario A ─┐
              └──────────────┘              ├─▶ comparar
              ┌──────────────┐              │
source.pengu ─┤ PSC          ├─▶ binario B ─┘
              └──────────────┘
```

- El harness ejecuta ambos y compara salida/exit/diagnósticos.
- Los golden se actualizan solo con revisión manual.
- CI corre ambos en cada PR que toque `std/`, el lenguaje o PSC.
- Un fallo de paridad bloquea el merge.

### 10.3 Congelación del lenguaje

No añadir sintaxis nueva durante la migración. Si se necesita:

1. Se implementa en stage0.
2. Se añade test de lenguaje.
3. Se implementa en PSC **antes** de usarla.
4. Se actualiza la documentación y el corpus.

Esto evita el clásico “el compilador nuevo persigue al viejo”.

### 10.4 Cache y versionado

- `impl_id = "psc-<version>"` en la cache key.
- Directorios de cache separados durante la transición:
  `~/.cache/pengu/psc/...` vs `~/.cache/pengu/stage0/...`.
- La versión del compilador y el hash del runtime entran en la clave.
- No reutilizar binarios de stage0 para PSC ni al revés.
- Tests: mismo fuente + mismas flags → hit; cambio de versión → miss.

### 10.5 Estrategia de pruebas

| Tipo | Herramienta | Fase |
|---|---|---|
| Unidad del lexer/parser | tests `.pengu` + golden | F1/F2 |
| Semántica | comparación con stage0 | F3 |
| Codegen | ejecutar binarios + C normalizado | F4 |
| Fugas | ASan/UBSan | F1+ |
| Fuzz | seeds + mutaciones | F1/F2 |
| LSP | cliente JSON-RPC real | F8 |
| CLI | matriz de comandos/flags | F6 |
| Bootstrap | stage1/2/3 | F5/F11 |
| Rendimiento | benchmark vs stage0 | F4/F6 |

### 10.6 Estrategia de release

- `make_release.py` puede seguir siendo el orquestador dev-only.
- El artefacto incluye: `psc` (renombrado `pengu`), `pengu-bind`, `std/`,
  runtime, documentación.
- Layout portable y FHS ya definidos en `make_release.py`.
- Verificar que `pengu` corre sin Python y que `pengu-bind` es autónomo.
- Guardar una release con stage0 como fallback.

---

## ⚠️ 11. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| **F3 (checker/infer) no alcanza paridad** | Alta | Muy alto | Empezar por el corpus; aceptar mensajes distintos pero códigos/posiciones iguales; no avanzar a F4 sin ≥95 % |
| **F4 codegen diverge** | Alta | Muy alto | Golden de C normalizado; ejecutar binarios; DCE exacto; matriz gcc/clang/tcc |
| **B1/B2 no se arreglan** | Media | Alto | Diseñar PSC sin genéricos propios; factorías de módulo; documentar la restricción |
| **Fugas de memoria** | Alta | Alto | Arena + builders + `defer`; ASan desde F1; checklist de ownership |
| **LSP no funciona con VS Code** | Media | Alto | Tests de cable desde F8 temprano; UTF-16; `initialize` correcto |
| **TOML/SHA incompletos** | Media | Alto | Módulos P0; corpus contra `tomllib`/`hashlib` |
| **Windows/macOS rompen** | Alta | Medio-alto | CI matrix desde F1; `when os` aislado; no asumir POSIX |
| **Rendimiento pobre** | Media | Medio | Benchmarks; DCE; cache; evitar O(n²) en strings; release con `-O2` |
| **Doble mantenimiento** | Alta | Alto | Congelar stage0; solo fixes críticos; no features nuevas |
| **Scope creep** (cross/WASM/package manager) | Alta | Medio | MVP explícito; diferir P2/P3; decir “not yet” con claridad |
| **Cache mezclada** | Media | Medio | `impl_id`; directorios separados; tests |
| **Helper bind se rompe** | Media | Medio | Contrato congelado; tests de paridad; PyInstaller reproducible |
| **Stage0 tiene un bug** | Media | Medio | Tests; revisión; el bootstrap fija el comportamiento, no lo inventa |
| **Documentación obsoleta** | Alta | Bajo | Tests como fuente de verdad; corregir ejemplos B12 |

---

## ❓ 12. Decisiones que necesito de ti

Antes de convertir este plan en trabajo, necesito que decidas:

1. **¿Arreglamos B1/B2 en el compilador Python antes de empezar?**
   - ✅ Recomendado: elimina la restricción de “PSC sin genéricos propios” y
     mejora el lenguaje para todos.
   - ⚠️ Alternativa: diseñar PSC sin genéricos compuestos y dejar B1/B2 como
     deuda posterior. Más rápido al principio, más duplicación.

2. **¿`pengu-bind` puede ser un ejecutable con Python congelado?**
   - ✅ Sí: es la excepción que planteaste; el binario `pengu` no requiere
     Python.
   - ❌ No: entonces hay que añadir F10b (parser de C / libclang), un proyecto
     aparte.

3. **¿Qué alcance de CLI en la primera versión?**
   - **MVP:** `build`, `run`, `check`, `test`, `fmt`, `doc`, `init`, `clean`,
     `doctor`, `lsp`.
   - **Completo:** los 27 comandos, incluyendo dependencias, benchmark y
     `selftest`.

4. **¿Qué hacemos con YAML, cross-compilation, WASM y LSP TCP?**
   - Se pueden diferir con errores claros (“not yet”) o entrar en F9/F8.
   - Mi recomendación: TOML primero; YAML solo compatibilidad básica; TCP
     después del LSP stdio; cross/WASM después del switch.

5. **¿Plataformas objetivo del primer gate?**
   - Linux primero y Windows/macOS en F11, o los tres desde F1 (más caro).
   - La CI actual ya prueba los tres; mantenerla desde el principio es lo más
     seguro.

6. **¿El harness de tests/CI puede seguir en Python?**
   - ✅ Recomendado: es desarrollo, no runtime. El binario final no lo usa.
   - Si quieres cero Python absoluto, hay que portar también pytest/harness.

7. **¿Congelamos el lenguaje en 3.0.1 durante la migración?**
   - ✅ Recomendado. Cualquier feature nueva duplica trabajo.

8. **¿`psc` como binario separado y luego renombrar a `pengu`?**
   - ✅ Recomendado: permite probar en paralelo sin romper a los usuarios.

---

## 📎 13. Anexos

### A. Comandos y resultados

```text
$ pengu --version
pengu 3.0.1

$ pengu doctor
PenguScript doctor
  version            3.0.1
  python             3.14.8 (source checkout)
  C compiler         /usr/bin/gcc — gcc (GCC) 16.2.1
  tcc                .../tcc version 0.9.28rc
  runtime header     .../build/include/pengu_runtime.h
  std/               .../std
  everything looks good

$ pytest tests/ -q
1400 passed, 3 skipped, 108 warnings in 112.24s

$ ASan fundamentals
1 passed in 2.23s

$ ASan leaks comprehensive
5 passed in 25.35s
```

### B. Reproducciones de los bugs

#### B1 — genérico→genérico

```pengu
import std.spark

weave ident shard T with x as T into T:
    return x

weave twice shard T with x as T into T:
    var y as T is calling ident with x
    return y

weave main into int:
    calling spark.println_int with calling twice with 5
    calling spark.println with calling twice with "hi"
    return 0
```

Resultado: `gcc` falla con `ident_T` esperando `void*` y recibiendo
`int32_t`/`PenguString`.

#### B2 — constructor `ritual` genérico

```pengu
rune Box shard T:
    value as T

enchanting Box shard T:
    weave ritual empty into Box of T:
        return with value is donum T
    weave get into T:
        return self->value

weave main into int:
    var a as Box of int is calling Box.empty of int
    var b as Box of string is calling Box.empty of string
    return 0
```

C generado: `Box_string b = Box_empty_int();`.

#### B2b — llamada cualificada

```pengu
import std.compass
var p as compass.Path is calling compass.Path.from_str with "/tmp/x"
```

C generado: `Path p = compass.Path.from_str(...)`.

#### B3 — captura de stderr

No es un fragmento de PenguScript; es una limitación de API. En
[`std/rites.pengu`](std/rites.pengu), `_rites_capture` libera el buffer y
devuelve `""` cuando el comando falla. No hay `run_capture` que devuelva
`{stdout, stderr, code}`.

#### B10 — `parse_float`

```pengu
import std.spark
weave main into int:
    var x as maybe float is calling spark.parse_float with "3.5"
    if x is present:
        calling spark.println_float with x.value
    banish x
    return 0
```

Imprime `0`, no `3.5`.

### C. Glosario

| Término | Significado |
|---|---|
| **stage0** | Compilador Python actual; construye PSC |
| **PSC** | PenguScript Compiler: implementación nueva en `.pengu` |
| **auto-hospedaje** | PSC compila PSC |
| **fixed point** | stage2 y stage3 producen el mismo resultado |
| **paridad A/B/C/D** | Niveles de compatibilidad con stage0 |
| **arena** | Asignador de memoria por bloques; libera todo de golpe |
| **span** | Rango de bytes en el fuente |
| **DCE** | Dead Code Elimination |
| **LSP** | Language Server Protocol |

### D. Referencias internas

- [`LANGUAGE.md`](LANGUAGE.md) — especificación del lenguaje.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — pipeline actual.
- [`docs/ABI.md`](docs/ABI.md) — contrato del runtime.
- [`docs/api/README.md`](docs/api/README.md) — 1 847 símbolos de la stdlib.
- [`tests/conformance/compliance/arena_ast.pengu`](tests/conformance/compliance/arena_ast.pengu) — AST en arena.
- [`tests/stdlib/audit/test_leaks_comprehensive.py`](tests/stdlib/audit/test_leaks_comprehensive.py) — gate de fugas.
- [`std/rites.pengu`](std/rites.pengu) — procesos y captura.
- [`std/jsonrpc.pengu`](std/jsonrpc.pengu) — framing LSP.
- [`std/diagnostic.pengu`](std/diagnostic.pengu) — diagnósticos Rust-style.
- [`std/arena.pengu`](std/arena.pengu) — allocator.
- [`std/builder.pengu`](std/builder.pengu) — StringBuilder.
- [`docs/BUGS_FIXED_CHUNK7.md`](docs/BUGS_FIXED_CHUNK7.md) — bugs G-1..G-6, X-1, X-2.
- `self_hosted_plan.md` (commit `88c97f9`, ya borrado) — plan histórico, útil como antecedente.

---

## 🧾 14. Resumen ejecutivo final

| Pregunta | Respuesta |
|---|---|
| ¿El lenguaje puede auto-hospedarse? | **Sí**, con las reservas de B1/B2 y las primitivas de sistema. |
| ¿La stdlib alcanza? | **~90 %**. Faltan 5 módulos P0; ninguno requiere una librería C nueva obligatoria. |
| ¿Hay que reescribir `std/`? | **No.** Se comparte tal cual. |
| ¿Hay que reescribir `pengu bind`? | **No.** Helper externo congelado. |
| ¿Cuál es el mayor riesgo? | **La paridad del checker/inferencia (F3)** y del codegen (F4). |
| ¿Cuál es el mayor bug? | **B1**: los genéricos no se componen. Arreglarlo antes de F3. |
| ¿Qué patrón usar? | Pipeline + `Session` + AST por índices en arena + diagnósticos como datos + ownership explícito. |
| ¿Dónde va el código nuevo? | `psc/` (nuevo), compartiendo `std/`, `tests/` y `pengu_runtime.h`. |
| ¿Cuánto cuesta? | **77–106 persona-semanas**; MVP auto-compilable: la mitad. |
| ¿Qué hago primero? | F0: arreglar B1/B2/B2b, añadir `std.digest`/`std.toml`/`std.io`/`std.process`, crear `psc/` y el harness de paridad. |

> **Mi recomendación:** no empieces por el parser. Empieza por **F0**. Los bugs
> de genéricos y la falta de captura de procesos/TOML/SHA son los que
> convierten un port “divertido” en una pesadilla de workarounds. Con F0
> resuelto, el resto es grande pero mecánico, y el Python actual te da un
> oráculo de 1 400 tests para no perder el rumbo.
