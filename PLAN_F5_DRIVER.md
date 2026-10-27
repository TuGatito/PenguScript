# 🚀 Plan de implementación — F5: driver mínimo y primer auto-compilado

> **Estado:** plan para revisión. **No se ha modificado código.**
> Este documento es el único artefacto nuevo de esta conversación.
>
> **Fase:** F5 de
> [`AUDITORIA_AUTO_HOSPEDAJE.md`](AUDITORIA_AUTO_HOSPEDAJE.md) §9.
> La auditoría estimó **4–6 persona-semanas** asumiendo F4 cerrado. El
> *preflight* de esta fase demuestra que esa suposición no se cumple: F5 debe
> incluir **F5a, el cierre de la brecha de codegen que impide que PSC compile
> PSC**. La estimación revisada es **9,5–12 persona-semanas**.
>
> **Regla de la fase:** el driver no se declara terminado porque “compila un
> hello world”. F5 termina cuando **stage2 y stage3 producen el mismo C**, PSC
> compila su propio fuente, pasa el corpus y todo eso está automatizado. Nada de
> placeholders, nada de “se compila de casualidad”.
>
> **Descubrimiento clave:** `psc emit-c psc/src/main.pengu` **sí emite** un
> bundle de 48 512 líneas en 5,8 s, pero `gcc` lo rechaza con **702 errores**.
> No son 702 bugs independientes: se agrupan en ~8 causas raíz
> (módulos duplicados, punteros a función, `defer` fuera de scope, constantes
> cualificadas, `if` como valor, `when` comptime, `to string`, resolución de
> miembros/llamadas, enlaces nativos). F5a las cierra.

---

## 📑 Índice

0. [Resumen ejecutivo](#-0-resumen-ejecutivo)
1. [Punto de partida y evidencia](#-1-punto-de-partida-y-evidencia)
2. [Alcance y no-alcance](#-2-alcance-y-no-alcance)
3. [Arquitectura del driver](#-3-arquitectura-del-driver)
4. [F5a — Self-compile gate](#-4-f5a--self-compile-gate)
5. [F5b — Paths, manifiesto y toolchain](#-5-f5b--paths-manifiesto-y-toolchain)
6. [F5c — build, run, expand y check](#-6-f5c--build-run-expand-y-check)
7. [F5d — Diagnósticos y errores](#-7-f5d--diagnósticos-y-errores)
8. [F5e — Bootstrap stage1 → stage2 → stage3](#-8-f5e--bootstrap-stage1--stage2--stage3)
9. [Tests, paridad, ASan y rendimiento](#-9-tests-paridad-asan-y-rendimiento)
10. [Checkpoints y calendario](#-10-checkpoints-y-calendario)
11. [Riesgos y mitigaciones](#-11-riesgos-y-mitigaciones)
12. [Decisiones que necesito de ti](#-12-decisiones-que-necesito-de-ti)
13. [Criterios de aceptación](#-13-criterios-de-aceptación)
14. [Mapa de archivos y ownership](#-14-mapa-de-archivos-y-ownership)
15. [Anexos](#-15-anexos)
16. [Cierre](#-16-cierre)

---

## 🎯 0. Resumen ejecutivo

F5 tiene dos mitades inseparables:

1. **Un driver real** (`psc build`, `psc run`, `psc expand`, `psc check` de
   proyecto): resolver el manifiesto, descubrir el runtime, emitir C, invocar
   `gcc`/`clang`, enlazar `libpengu_runtime.a`, escribir en `build/`, propagar
   diagnósticos y exit codes.
2. **La primera prueba de fuego del compilador**: usar ese driver para que PSC
   se compile a sí mismo, y comprobar que el resultado es un punto fijo
   (`stage2 == stage3`).

La segunda mitad es la que manda. F4 cerró contra su corpus de fixtures
(**66/66** de conformidad y **17** tests de aceptación), pero ese corpus no
cubría varios patrones que PSC usa en su propio fuente. El primer
`psc emit-c psc/src/main.pengu` + `gcc` lo revela sin ambigüedad.

### Resultado esperado

| Área | Resultado |
|---|---|
| Self-compile gate | `psc emit-c psc/src/main.pengu` compila con gcc/clang sin errores y el binario responde `version` |
| Driver | `psc build`, `psc run`, `psc expand`, `psc check` de archivo y de proyecto |
| Manifiesto | subconjunto TOML de `pengu.toml`: proyecto, build, perfiles, links, flags |
| Runtime | descubrimiento de header/archivo/std en checkout, portable y FHS |
| Enlazado | `-lpengu_runtime` + `links` declarados en fuentes y manifiesto |
| Diagnósticos | errores de C mapeados a `.pengu` mediante `#line`; exit codes estables |
| Bootstrap | stage1 (compilado por stage0) → stage2 → stage3; C de stage2 == C de stage3 |
| Corpus | 66/66 de conformidad compilados y ejecutados **con el driver**, no con el runner de F4 |
| stdlib | `std/` compila como biblioteca (gate completo; ver D3) |
| Memoria | ASan/UBSan limpio en el auto-compilado y en el corpus |
| CI | job `selfhost` en Linux; bootstrap completo en nightly |

### Números que resumen la situación

| Métrica | Valor |
|---|---:|
| Fuente de PSC | **70 archivos**, **25 713 líneas** |
| `psc emit-c psc/src/main.pengu` | **48 512 líneas**, **2,94 MB**, **5,8 s** |
| `gcc -fsyntax-only` sobre ese bundle | **702 errores** |
| Archivos `.pengu` afectados | **42** (436 errores en `psc/src`, 2 en `std/`, 264 en la sección de tipos del bundle) |
| F4 conformidad | **66/66** |
| F4 tests de aceptación | **17 passed** en 4,2 s |
| `psc check psc/src/main.pengu` | **0 errores**, 1,6 s |
| Build de PSC con stage0 | **10,25 s** (caché), binario de 1,44 MB |
| Versión actual de PSC | `psc 0.3.0 (F3)` |

### Lo que esto significa

- **F5 es viable.** El emisor llega al final; los fallos son de bajada, no de
  arquitectura.
- **F5 no puede empezar por el driver.** Si se escribe el driver y se intenta
  el bootstrap, se descubre lo mismo 3 semanas después y con más código encima.
  Por eso el orden es **F5a → F5b → F5c → F5d → F5e**.
- **La estimación cambia.** La auditoría asumía F4 cerrado; F5a cuesta
  **4,5–6,5 semanas**. El total honesto es **9,5–12 persona-semanas**, con
  riesgo de 13 si aparece una causa raíz nueva en la ola 3.

### Go / no-go

Después de la ola 3 de F5a (CP4), si el preflight sigue por encima de **50
errores** o aparece una causa que exija cambiar el lenguaje, **paro y replanifico
contigo**. No se continúa al bootstrap “a ver si suena la flauta”.

---

## 🧱 1. Punto de partida y evidencia

### 1.1 Estado de F0–F4

| Fase | Estado verificado | Evidencia |
|---|---|---|
| F0 | Cerrada | `std.digest`, `std.toml`, `std.io`, `std.rites.run_capture_all` existentes; runtime y `std_c/` presentes |
| F1 | Cerrada | lexer, source, diagnósticos, dump de tokens; oráculo de tokens |
| F2 | Cerrada | parser, AST por índices, recuperación, profundidad; oráculo AST |
| F3 | Cerrada | `psc check` acepta `std/`, `tests/`, `psc/src`; 225 válidos + 1 negativo |
| F4 | Cerrada **contra su corpus** | 66/66 conformidad; 17 tests; `emit-c` determinista; gcc/clang |

F4 no está “roto” en el sentido de su contrato: cumple los fixtures que se le
dieron. El problema es que **el contrato de F4 no incluía el propio fuente de
PSC como caso de prueba**. F5 lo añade y descubre la brecha.

### 1.2 Medidas tomadas para este plan

Todos los comandos se ejecutaron en el checkout actual, sin modificar archivos.

```bash
# 1. PSC emite C de sí mismo (éxito de emisión)
time ./psc/build/psc emit-c psc/src/main.pengu --out=/tmp/psc_main.c
# -> wrote /tmp/psc_main.c (48512 lines, 2938435 bytes, 2 includes)
# -> 5.8 s

# 2. gcc intenta compilarlo (fallo de compilación)
gcc -std=c11 -w -fsyntax-only -I . -I build/include -I std_c /tmp/psc_main.c
# -> 702 líneas "error:"

# 3. F4 sigue verde
python psc/tools/run_f4_conformance.py
# -> F4 conformance: 66/66
.venv/bin/python -m pytest -q tests/psc/test_f4_acceptance.py
# -> 17 passed in 4.20s

# 4. Stage0 construye PSC
cd psc && ../.venv/bin/python ../pengu_project.py build
# -> Finished (cached) [debug] target(s) in 10.25s -> psc/build/psc

# 5. F3 acepta el fuente de PSC
./psc/build/psc check psc/src/main.pengu
# -> exit 0, 1.6 s
```

### 1.3 Qué cubre F4 hoy y qué no

Cubre, con tests:

- tipos, runas, ecos, omens, aliases, tuplas;
- funciones, métodos, `ritual`, `declare`, `antiquus`;
- expresiones básicas, interpolación, `judge`, `with`, `or else`, lambdas;
- `defer`/`banish` en casos simples;
- DCE conservadora, `--test`, `--strict-c99`, `#line`;
- 66 fixtures con librerías nativas.

No cubre, y PSC lo usa:

- módulos cargados con dos grafías del mismo path (relativo y absoluto);
- campos de puntero a función (`ref to weave ...`) y callbacks en structs;
- `defer` / `banish` dentro de `if`, `while`, `for` con salida temprana;
- `if`/`when` como **valor** (`return if ... then ... else ...`);
- `when os` / `when defined` de nivel superior, incluyendo `include` dentro de
  `when`;
- conversión `x to string`;
- constantes cualificadas (`sdiag.CODE_UNDEFINED`);
- `calling x.len` y resolución de miembros por tipo;
- igualdad de strings en expresiones compuestas (`(list at i) == "x"`);
- literales de lista pasados como argumento;
- metadatos de `link`/`ldflag` expuestos al driver.

### 1.4 Preflight: 702 errores, ~8 causas

La clasificación es heurística, sobre las líneas de error de gcc. **No son 702
causas independientes**; muchas son cascadas de la misma causa.

| Grupo | Causa raíz | Errores aprox. | % |
|---|---|---:|---:|
| **G1** | Módulos duplicados por path relativo/absoluto | **320** | 46 % |
| **G2** | Punteros a función mal declarados | **125** | 18 % |
| **G3** | `defer`/`banish` y locales fuera de su bloque | **~130** | 18 % |
| **G4** | Constantes cualificadas (`mod.CONST`) y nombres C de consts | **~44** | 6 % |
| **G5** | `if`/`when` como valor, `when` comptime, `to string` | **~5** | 1 % |
| **G6** | Resolución de miembros/llamadas (`calling x.len`, método vs función) | **~19** | 3 % |
| **G7** | Igualdad de strings compuesta, listas, indexación, omens | **~30** | 4 % |
| **G8** | Varios / no clasificados | **~29** | 4 % |
| **Total** | | **702** | 100 % |

Desglose por archivo (top):

| Archivo | Errores |
|---|---:|
| `<sección de tipos del bundle>` | 264 |
| `psc/src/psc/parse/state.pengu` | 115 (89 + 26 duplicados) |
| `psc/src/psc/sema/check/body.pengu` | 52 |
| `psc/src/psc/lexer_state.pengu` | 25 |
| `psc/src/psc/parse/expr/ops.pengu` | 23 |
| `psc/src/psc/sema/infer/core.pengu` | 22 |
| `psc/src/psc/parse/api.pengu` | 21 |
| `psc/src/psc/sema/check/collect.pengu` | 19 |
| `psc/src/psc/sema/state.pengu` | 18 |
| `psc/src/main.pengu` | 16 |

### 1.5 Las tres lecciones que gobiernan F5

1. **El corpus de F4 era necesario pero no suficiente.** Hay que añadir un
   *self-compile gate* permanente; no basta con 66 fixtures.
2. **Los bugs de bajada se multiplican si se escriben encima.** F5a va primero.
3. **El criterio de cierre es el punto fijo, no “compila”.** Un compilador que
   compila PSC pero produce un stage3 distinto no está auto-hospedado: está
   divergiendo.

---

## 📐 2. Alcance y no-alcance

### 2.1 Dentro de F5

1. **F5a — Self-compile gate:** cerrar las causas G1–G8, propagar errores
   internos de codegen y exponer `links`/`ldflags`.
2. **F5b — Paths, manifiesto y toolchain:** `pengu.toml` mínimo, perfiles,
   búsqueda de runtime/std, flags de cc, variables de entorno.
3. **F5c — Driver:** `psc build`, `psc run`, `psc expand`, `psc check` de
   proyecto; un solo archivo y proyecto; salida a `build/`; C glue básico.
4. **F5d — Diagnósticos:** semánticos, internos de codegen y de C; exit codes.
5. **F5e — Bootstrap:** stage1 → stage2 → stage3; punto fijo; corpus con el
   driver; ASan.
6. **F5f — Calidad (transversal, §9–§10):** tests, oráculos, determinismo,
   benchmark, CI y docs.

### 2.2 Fuera de F5 (por fase)

| Fuera | Fase |
|---|---|
| Caché en disco, `--no-cache`, `--clear-cache`, binarios cacheados | F6 |
| CLI completo: `init`, `new`, `clean`, `doctor`, `gc`, `watch`, `fmt`, `doc`, `assets`, `test`, `eval`, `time`, `benchmark` | F6/F7 |
| `--json`, matrices de flags, `--locked`/`--frozen`, dependencias | F6/F9 |
| LSP, sockets, UTF-16 | F8 |
| Package manager, lockfile, `vendor` | F9 |
| `pengu-bind` | F10 |
| Cross-compilation, WASM, MSVC, TCC como gate | F11 |
| YAML/JSON como manifiesto | F6/F9 (o nunca) |
| Cambios en `std/`, runtime o ABI | No se hacen |
| Cambios en el compilador Python (stage0) | No se hacen |

### 2.3 “F5 cerrado” significa

- `psc` compila **su propio fuente** y el binario resultante funciona.
- `stage2` compila PSC y produce `stage3`; **el C de stage2 y stage3 es
  equivalente** tras normalizar rutas.
- PSC compila y ejecuta el corpus de conformidad **66/66** usando el driver.
- `std/` compila como biblioteca (ver D3 para el alcance exacto).
- ASan/UBSan limpio en el auto-compilado y en el corpus.
- CI automatiza el gate y hay documento `docs/selfhost/BOOTSTRAP.md`.
- F1–F4 siguen verdes; no hay regresiones en stage0 ni en `std/`.

---

## 🏗️ 3. Arquitectura del driver

### 3.1 Pipeline

```text
psc build <file|dir>
        │
        ▼
┌──────────────────────┐
│ 1. resolve target    │  archivo .pengu o directorio con pengu.toml
│    project/manifest  │  (o cwd si no hay target)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 2. BuildPlan         │  base_dir, entry, build_dir, out, profile,
│    project/paths     │  cc, flags, links, includes, std_dirs
│    project/toolchain │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 3. sema              │  check_file(entry, opts) -> SemaProgram + diags
│    (F3)              │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 4. codegen           │  generate_c(program, CgOptions) -> bundle + links
│    (F4)              │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 5. write bundle.c    │  <build_dir>/bundle.c (atómico)
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 6. cc + link         │  cc flags -I... bundle.c [c_glue] -L... -l...
│    project/cc        │  enlaza libpengu_runtime.a y links declarados
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ 7. install artifact  │  <out> (temp + rename)
└──────────┬───────────┘
           ▼
    artifact / diagnostics / exit code
```

`psc run` = pipeline + `exec` del artefacto con los args del usuario.
`psc expand` = pipeline hasta el paso 5, sin cc.
`psc check` = pasos 1–3, sin codegen ni cc.

### 3.2 Módulos propuestos

```text
psc/src/psc/
├── cli/
│   ├── args.pengu              parseo de flags, `--`, help común
│   └── help.pengu              textos de ayuda (una sola fuente)
├── project/
│   ├── manifest.pengu          pengu.toml -> ProjectManifest
│   ├── paths.pengu             layouts, runtime, std, std_c, build dir
│   ├── toolchain.pengu         cc, flags, dialecto, link line
│   └── cc.pengu                run_capture_all, CCompilerIssue, remapeo
├── driver/
│   ├── build.pengu             BuildOptions/BuildResult, orquestación
│   ├── run.pengu               build + exec
│   └── expand.pengu            build hasta bundle
└── cmd/
    ├── lex.pengu               mover el actual run_lex
    ├── parse.pengu             mover run_parse
    ├── check.pengu             run_check + target de proyecto
    ├── emit_c.pengu            run_emit_c (dev; sigue existiendo)
    ├── build.pengu             run_build
    ├── run.pengu               run_run
    └── expand.pengu            run_expand
```

Reglas:

- Cada archivo **400–800 líneas**; si crece, se parte por responsabilidad.
- `main.pengu` queda como dispatcher y ayuda (~150 líneas), no como
  implementación de todos los comandos.
- `insignia psc_<área>_` por archivo.
- Nada de estado global mutable. Todo viaja en `BuildPlan` / `BuildResult`.
- `psc emit-c` se conserva para desarrollo y oráculos; `psc expand` es la
  superficie de usuario con resolución de proyecto. Ambos comparten el mismo
  camino de emisión.

### 3.3 Tipos principales

```pengu
## Opciones de una compilación (valores prestados por el llamador).
rune BuildOptions:
    target as string          # "" = cwd; archivo .pengu o directorio
    profile as string         # "debug" | "release"
    cc as string              # "" = autodetectar
    out_path as string        # "" = <build_dir>/<output_name>
    verbose as bool
    release_unsafe as bool
    strict_c99 as bool

## Plan resuelto y validado; dueño de sus strings.
##
## ## Memoria
## Liberar con `free_plan`.
rune BuildPlan:
    base_dir as string
    project_root as string
    entry as string
    build_dir as string
    bundle_path as string
    out_path as string
    profile as string
    cc as string
    cflags as list of string
    ldflags as list of string
    links as list of string
    lib_dirs as list of string
    include_dirs as list of string
    defines as list of string
    c_sources as list of string
    is_single_file as bool
    output_c_only as bool
    is_library as bool

## Resultado de un build.
##
## ## Memoria
## `bundle` y las listas son owned; `free_build_result` los libera.
rune BuildResult:
    ok as bool
    artifact as string
    bundle_path as string
    bundle as string
    exit_code as int
    cc_stdout as string
    cc_stderr as string
    diagnostics as ref to diag.DiagnosticBag
```

API interna:

```pengu
weave build with opts as BuildOptions into BuildResult
weave run with opts as BuildOptions, child_args as list of string into int
weave expand with opts as BuildOptions into BuildResult
weave free_build_result with r as ref to BuildResult into void
weave free_plan with p as ref to BuildPlan into void
```

### 3.4 Layouts soportados

El driver debe encontrar runtime/std en los cuatro layouts que ya usa
`pengu_paths.py`, al menos para Linux:

```text
1. Source checkout
   <repo>/build/lib/libpengu_runtime.a
   <repo>/build/include/pengu_runtime.h
   <repo>/std/*.pengu
   <repo>/std_c/*.h

2. Portable bundle
   <exe_dir>/runtime/lib/libpengu_runtime.a
   <exe_dir>/runtime/include/pengu_runtime.h
   <exe_dir>/std/*.pengu

3. FHS
   <prefix>/lib/pengu/libpengu_runtime.a
   <prefix>/include/pengu/pengu_runtime.h
   <prefix>/share/pengu/std/*.pengu

4. Proyecto con runtime vendorizado
   <project>/runtime/{lib,include}/
   <project>/build/{lib,include}/
```

Orden de búsqueda (primer hit gana):

1. `PENGU_RUNTIME_ARCHIVE` (archivo exacto), `PENGU_LIB_DIR`,
   `PENGU_INCLUDE_DIR`, `PENGU_STD_DIR`, `PENGU_PREFIX`.
2. Directorios del proyecto: `<base>/build/{lib,include}`, `<base>/runtime/...`.
3. Directorio del ejecutable y sus padres: `<exe_dir>`, `<exe_dir>/..`,
   `<exe_dir>/../..`, hasta 4 niveles; en cada uno `build/lib`,
   `build/include`, `std`, `std_c`, `runtime/...`.
4. `$PENGU_PREFIX`, `~/.local`, `/usr/local`, `/usr` (FHS).
5. `PATH` para `cc`; std solo por las rutas anteriores.

Si falta el archivo o el header, **error accionable** (exit 2) que lista las
rutas probadas y sugiere `python build_runtime.py` o `PENGU_PREFIX`.

### 3.5 Manifiesto

F5 soporta este subconjunto de `pengu.toml`; todo lo demás se rechaza con un
mensaje explícito “not yet (F6/F9)” en vez de ignorarse.

```toml
[project]
name = "psc"
version = "0.5.0"
entry = "src/main.pengu"       # obligatorio en proyecto
output = "exe"                 # exe | c
output_name = "psc"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
includes = []
links = ["pengu_runtime"]
lib_dirs = []
include_dirs = []
cflags = ["-Wall", "-std=c11"]
ldflags = []
defines = []
cc = "gcc"

[profiles.debug]
cflags = ["-g", "-O0", "-Wall"]
defines = ["DEBUG"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG"]
defines = ["NDEBUG"]
```

Reglas:

- `pengu.toml` se parsea con `std.toml` (F0); no se reimplementa TOML.
- `profiles.<perfil>.cflags` y `.defines` se **fusionan** con `[build]`.
- `links` se combinan con los `link` declarados en fuentes; sin duplicados.
- `pengu_runtime` se añade siempre si no está.
- `dependencies`, `assets`, `target`, `strict_c99` fuera del subconjunto:
  `dependencies`/`assets` no vacíos -> error claro; `strict_c99` se acepta
  porque ya existe en F4; `target` no.
- `pengu.yaml` / `pengu.json`: error “not supported in F5” (F6).
- Si no hay manifiesto y el target es un `.pengu`: modo *single file*.
  `base_dir` = directorio del archivo, `src_dir` = ".", sin links extra.
- Si el target es un directorio sin `pengu.toml`: error 2.
- Si no hay target: se busca `pengu.toml` en cwd (y se sube hasta 64
  directorios, igual que stage0).

### 3.6 Toolchain

Prioridad de `cc`:

1. `--cc=NAME` de la CLI.
2. `PSC_CC` (nuevo) o `PENGU_CC`.
3. `[build].cc` del manifiesto.
4. `cc` / `gcc` / `clang` en `PATH`.

Dialecto:

| cc | `target_compiler` | Estado F5 |
|---|---|---|
| `gcc` | `gcc` | ✅ gate |
| `clang` | `clang` | ✅ gate |
| `tcc` | `tcc` | 🟡 best-effort |
| `cl`/`cl.exe` | `msvc` | ❌ “not yet (F11)” |

Flags base (Linux/macOS):

```text
-std=c11
<manifest cflags> <profile cflags>
-D<manifest defines> -D<profile defines>
-I<build_dir> -I<project/include> -I<std_c> -I<runtime/include>
-I<lib/*/include>
-L<runtime/lib> -L<project/lib> -L<lib/*/lib>
<manifest ldflags> <profile ldflags> <source ldflags>
-pthread -lm -ldl
```

`PENGU_CFLAGS` y `PENGU_LDFLAGS` se añaden al final (para ASan en CI y tests).
No se usa shell `eval`: `std.rites.run_capture_all` ya escapa cada argumento;
se prueba con paths que contienen espacios, comillas y `;`.

`-Wall -Wextra` en el gate; `-Werror` solo en el cierre, cuando el bundle está
limpio. TCC no recibe flags GNU que no soporta.

### 3.7 Diagnósticos

Tres capas, sin inventar códigos nuevos:

| Capa | Fuente | Salida |
|---|---|---|
| Semántica | `DiagnosticBag` de F3 | `file:line:col: error[E....]`, exit 1 |
| Codegen | `CgResult.ok = false` + mensaje | `psc: error interno de codegen: ...`, exit 1 |
| C compiler | stderr de gcc/clang/tcc | `file.pengu:line:col: error: ...`, exit 1 |
| Uso / E-S / entorno | driver | `psc: ...`, exit 2 |

`#line` es obligatorio en el bundle de build. El driver **no** expone
`--no-line-markers` en F5; `psc emit-c` sí lo conserva para depuración. Si en el
futuro se expone, el `OriginMap` de F4 tendrá que formar parte de `CgResult`
(ver 4.9).

### 3.8 Artefactos, determinismo y ownership

- `bundle.c`: `<build_dir>/bundle.c`; escritura atómica (temp + rename).
- Artefacto: `<build_dir>/<output_name>` o `--out=PATH`; se crean los
  directorios padre que falten.
- `psc expand`: `--out=PATH` o stdout; nunca invoca cc.
- Si el artefacto coincide con el ejecutable en curso, se compila a
  `<out>.tmp.<pid>` y se hace `rename`: así el auto-build no falla con
  `ETXTBSY` en Linux.
- Nada de timestamps, rutas absolutas del checkout ni orden de mapas en el C.
- C de dos ejecuciones con las mismas entradas: **byte-idéntico**.
- Ownership:
  - `BuildPlan` es dueño de sus strings/listas;
  - `BuildResult` es dueño de `bundle` y de `--stdout/--stderr` de cc;
  - `SemaResult`/`CgResult` se liberan en el driver;
  - cada `run_capture_all` devuelve `ProcessResult` owned: `banish` de ambos
    strings;
  - cada función nueva lleva su sección `## ## Memoria`.

---

## 🧩 4. F5a — Self-compile gate

**Objetivo:** que `psc emit-c psc/src/main.pengu` produzca C que gcc/clang
acepten y cuyo binario ejecute `version`, `check` y `emit-c` sobre el propio
PSC.

### 4.1 Método: preflight tool + burn-down por olas

Herramienta nueva, dev-only, Python (no runtime):

```text
psc/tools/selfhost_preflight.py
```

Hace:

1. `psc emit-c <entry> --out=<tmp>/bundle.c` (mide tiempo/tamaño).
2. `cc -std=c11 -w -fsyntax-only -I ... <bundle.c>`.
3. Parsea y normaliza los errores.
4. Agrupa por causa y por archivo; descarta duplicados exactos.
5. Opcionalmente compila, enlaza y ejecuta `version`.
6. Sale 0 si `errors <= --budget` y el smoke pasa; 1 si no.

Ejemplo de salida:

```text
program: psc/src/main.pengu
bundle:  48512 lines, 2.94 MB, 5.8 s
cc:      gcc -std=c11 -fsyntax-only ...
errors:  702 (unique files: 42)
  G1 duplicate module/type ................ 320
  G2 function pointer declarator .......... 125
  G3 defer/local out of scope ............. 130
  G4 qualified constant .................... 44
  G5 value-if / comptime when / to string .. 5
  G6 member/call resolution ................ 19
  G7 string cmp/list/index/omen ............ 30
  G8 other ................................. 29
status:  BLOCKED (budget 0)
```

Uso:

```bash
python psc/tools/selfhost_preflight.py --psc psc/build/psc --budget 0
python psc/tools/selfhost_preflight.py --psc psc/build/psc --json > /tmp/preflight.json
python psc/tools/selfhost_preflight.py --psc psc/build/psc --top 10 --keep
```

Se ejecuta en cada checkpoint y en CI. Es la métrica objetiva de F5a.

### 4.2 G1 — Identidad de módulo y paths canónicos

**Síntoma**

- `SourceErrorKind`, `TokenKind`, `KeywordKind` y sus structs aparecen **dos
  veces** en la sección de tipos.
- `psc/src/psc/parse/state.pengu` tiene 63 marcadores `#line` con path relativo
  y 63 con path absoluto.
- 320 errores de redeclaración/redefinición.

**Causa**

`SemaProgram.by_path` usa el string tal como se resolvió. El entry llega
relativo (`psc/src/main.pengu` con `base_dir` absoluto), los imports resuelven
unas veces relativo al importador y otras por `src_dir` absoluto. El mismo
archivo entra dos veces con dos grafías; el orden topológico lo emite dos veces
y el codegen declara los tipos dos veces.

**Fix**

- Definir una **identidad canónica**:
  `canonical = normpath(absolute(path))` (sin symlinks en F5; `realpath`
  opcional).
- `by_path` se indexa por `canonical`; `module_id` canonicaliza antes de
  buscar.
- `SemaModule` guarda:
  - `canonical_path` (identidad, no se muestra),
  - `path` (display, estable: relativo a `base_dir` si está dentro, absoluto
    si no).
- `SourceFile.path`, `#line` y diagnósticos usan el display.
- `check_text`/`<stdin>` conserva su path lógico sin absolutizar.
- Test: entry relativo + `base_dir` absoluto -> un solo módulo, una sola
  definición de tipo, marcadores coherentes.
- Test: importar el mismo módulo desde dos directorios -> un solo módulo.
- Regresión: F3 corpus (225 válidos + 1 negativo) y oráculo semántico.

**Criterio de salida G1:** 0 errores de redeclaración; `grep -c` de cada tipo
nominal = 1; conteo de módulos estable entre ejecuciones.

### 4.3 G2 — Punteros a función y declaradores C

**Síntoma**

```c
struct PsHooks {
    int32_t (*)(PsParser*)* value;
    int32_t (*)(PsParser*)* when;
    ...
};
```

- 73 errores `expected identifier or '(' before ')' token`.
- 52 errores `'PsHooks' no tiene un miembro llamado '...'`.
- `ref to weave ...` se baja como “puntero a puntero a función”.

**Causa**

- `ctype.c_type` aplica `TkRef` después de `TkFn`: genera
  `<ret> (*)(params)*` en vez de `<ret> (*)(params)`.
- Los campos y parámetros se emiten como `tipo nombre` sin `to_c_decl`, así que
  el nombre del campo se pierde.

**Fix**

- `c_type`:
  - `TkRef` cuyo `inner` es `TkFn` -> devuelve el declarador de función, **sin**
    `*` extra;
  - `TkRef` de `TkRef` -> un solo `*` (o error interno si el lenguaje no lo
    permite).
- Nuevo `to_c_decl(name, type)`:
  - función: `<ret> (*<name>)(<params>)`;
  - array: `<elem> <name>[N]` (campos/params) o `<elem>*` fuera de struct;
  - `const`/`frozen`: en el pointee, nunca en el puntero;
  - `void*` para opacos.
- Usar `to_c_decl` en:
  - campos de `decl_types.emit_definition`;
  - parámetros y retorno de `function.signature`/`emit_function`;
  - variables locales cuando el tipo es función/array;
  - prototipos.
- `typedef` de tipos función complejos cuando el declarador se repita (optativo,
  pero recomendado para legibilidad del C).
- Tests:
  - struct con hooks como `PsHooks`;
  - campo `ref to weave`;
  - callback pasado a función y llamado;
  - array multidimensional en struct;
  - `ref to frozen weave ...`.

**Criterio de salida:** el struct de hooks compila; se puede llamar a un hook
desde C generado; 0 errores de declarador.

### 4.4 G3 — Scope de `defer`, `banish` y locales

**Síntoma**

```c
if (...) {
    PenguString detail = ...;
}
pengu_banish_string(&(detail));   // ❌ detail no existe aquí
```

- ~130 errores de identificador no declarado (`detail`, `msg`, `txt`, …).
- Además, aunque compilara, sería una fuga/UB: el `banish` se ejecuta fuera del
  bloque y se pierde en `return`.
- En bucles, un `defer` de una iteración se acumula hasta el final de la
  función.

**Causa**

`CgContext.defers` es una **lista única por función**; `emit_function` vacía
todos los defers al final. No hay pila de scopes ni emisión en `return`,
`break`, `continue`, `judge` o `goto`. `locals` tiene el mismo problema: no se
eliminan al salir del bloque.

**Fix**

- Sustituir `defers: list of int` por una pila:

```pengu
rune CgScope:
    locals as list of CgLocal
    defers as list of CgDefer     # LIFO
    is_loop as bool
    cleanup_target as int          # label de salida si aplica
```

- `push_scope`/`pop_scope` en **todo** bloque C: función, `if`, `else`,
  `while`, `for`, `do`, `with`, `judge` arm, `unsafe`, `or:`.
- Al cerrar un scope:
  - emitir sus defers en orden inverso;
  - restaurar `locals`.
- En `return`:
  - emitir todos los defers de los scopes abiertos, de dentro hacia fuera,
    después de evaluar el valor de retorno;
  - devolver el temporal si el valor lo necesita.
- En `break`/`continue`:
  - emitir los defers de los scopes que se abandonan hasta el loop;
  - no emitir los del propio loop.
- En `goto` de labels: emitir los defers de los scopes abandonados; si el
  análisis no puede garantizarlo, **error interno de codegen** (mejor fallar
  que generar C incorrecto).
- `banish x` se registra como defer del scope actual (no del función).
- `errdefer` solo en caminos de error; mismo mecanismo.
- Tests:
  - `defer` en `if`, `else`, `while`, `for`, anidado;
  - `return` temprano desde dentro de un bloque;
  - `break`/`continue` con defer;
  - `banish` de un string interpolado dentro de un `if`;
  - ASan en todos.

**Criterio de salida:** 0 errores de “no declarado” por scope; ASan sin fugas
en los tests de defer; el C de los fixtures no cambia salvo donde había bug.

### 4.5 G4 — Constantes cualificadas y nombres C de consts

**Síntoma**

```c
sema_diag_node_error(..., sdiag.CODE_UNDEFINED, ...);
```

- 28 errores `'sdiag' no se declaró aquí`.
- 8 `types`, 8 `sym` por `types.NIF_PUBLIC`, `sym.SYM_MUTATING`.
- Las consts se emiten como `#define CODE_UNDEFINED ...` sin prefijo de módulo,
  lo que puede colisionar entre módulos.

**Causa**

- F4 no resuelve el acceso `mod.CONST` a la const ya recolectada; emite el
  `dotted_path` tal cual.
- `CgConst.c_name` no aplica insignia/módulo; stage0 usa el nombre lógico y
  resuelve colisiones.

**Fix**

- Resolver `dotted_path` de 2 componentes con `symbol_of`/tabla de consts de
  F3; emitir el `c_name` de la const.
- Dar a cada const un nombre C estable y sin colisiones:
  `insignia + nombre` si el módulo tiene insignia; si no, nombre lógico con
  resolución determinista (misma política que funciones).
- No cambiar el nombre lógico en diagnósticos.
- Tests:
  - `mod.CONST` dentro de una función y como valor por defecto;
  - dos módulos con `const X` distinto -> dos nombres C distintos;
  - const string/int/bool/float;
  - `sym.SYM_MUTATING` y `sdiag.CODE_*` (los casos reales del fuente).

**Criterio de salida:** 0 errores `'sdiag'`/`'types'`/`'sym'`; una const de cada
módulo tiene nombre único; `emit-c` de PSC no contiene `mod.CONST`.

### 4.6 G5 — `if`/`when` como valor, `when` comptime y `to string`

#### G5.1 `if` como valor

**Síntoma**

```pengu
weave cp_sep into string:
    return if calling cp_win then "\\" else "/"
```

emite:

```c
PenguString cp_sep(void) {
    return 0;   // ❌
}
```

Y:

```pengu
weave pick into int:
    return if 1 < 2 then 30 else 40
```

emite `return 0;`.

**Fix**

- Implementar `if` como expresión con una de dos estrategias:
  1. **statement expression GNU** (por defecto):
     ```c
     __extension__({ int32_t _r; if (cond) _r = a; else _r = b; _r; })
     ```
  2. **hoisting** a un temporal + preludio antes del statement que la contiene
     (obligatorio con `--strict-c99`).
- El preludio debe pertenecer al statement que posee la expresión; no puede
  quedar huérfano.
- Si una rama contiene `return`/`break`/`continue`, no usar statement
  expression: hoisting o error interno.
- Aplicar la misma maquinaria a `when` como valor y a `do:` como valor.
- Tests: `return if`, `let x is if`, `var x is if`, anidado, con strings,
  `--strict-c99`.

#### G5.2 `when` comptime de nivel superior y `include`

**Síntoma**

`std/rites.pengu`:

```pengu
when os == "windows":
    include "io.h"
else:
    include "sys/wait.h"
```

PSC no emite ninguno de los dos includes; el bundle usa `waitpid` sin
declaración:

```text
error: implicit declaration of function 'waitpid'
```

Además:

```pengu
weave cp_win into bool:
    when os == "windows":
        return true
    else:
        return false
```

emite `0;` (sin `return`) en Linux.

**Fix**

- Evaluar `when` en codegen con la misma semántica que F3:
  - `os`, `arch`, `defined(NAME)`, `compiler`, `main`, `debug`, constantes;
  - rama `else`/`otherwise`;
  - `when` anidado.
- Soportar `when` en:
  - nivel superior: `include`, `link`, `ldflag`, declaraciones, `antiquus`;
  - statements: `when ...: ... else: ...`;
  - expresiones: valor.
- Para includes/links, recolectar solo la rama viva; el catálogo debe verlos.
- Tests: `when os`, `when defined(DEBUG)`, `when arch`, rama else, include
  condicional, `std/rites` compilando (waitpid declarado).

#### G5.3 `to string`

**Síntoma**

`std/spark.pengu`:

```pengu
weave println_int with value as int into void:
    calling pengu_println with (value to string)
```

emite:

```c
pengu_println((((PenguString)(value))));   // ❌ cast, no conversión
```

**Fix**

- `to string` sobre tipos no string usa los helpers del runtime:
  - `pengu_string_from_int`, `pengu_string_from_float`,
    `pengu_string_from_bool`, `pengu_string_from_char`/`_from_int` para char;
  - `pengu_to_string` `_Generic` cuando el tipo C sea inequívoco;
  - string -> identidad (no copia).
- Ownership: el resultado es owned; si se pasa como argumento a una función
  `string`, aplicar la misma regla de liberación de temporales que stage0
  (statement expression con `banish`), o documentar la excepción hasta F6.
- Tests: int, i64, u64, float, bool, char, string; interpolación vs `to
  string`; `std.spark.println_int/float/bool`; ASan.

**Criterio de salida G5:** `cp_sep` devuelve `"/"` en Linux y `"\\"` en Windows
comptime; `std/rites` compila; `println_int` imprime; `to string` no emite
casts.

### 4.7 G6 — Resolución de miembros, llamadas y paridad F3

**Síntoma A — `calling x.len`**

`std/rites.pengu`:

```pengu
if (calling matches_list.len) > 0:
```

emite:

```c
if (Num_len(&(matches_list)) > 0)   // ❌ Num_len espera PenguString*
```

`calling` delante de una propiedad de lista/mapa debe bajar al campo `.len`,
no a un método de string.

**Síntoma B — colisión función local vs método primitivo**

`psc/src/main.pengu` define:

```pengu
weave starts_with with s as string, prefix as string into bool:
```

y `std.scrolls` tiene `enchanting string` con `starts_with`. La llamada
`calling starts_with with a, "--x"` emite:

```c
Num_starts_with(&(starts_with), a, "--max-errors=")   // ❌
```

Stage0 resuelve la función local; PSC elige el método primitivo.

**Síntoma C — `r.is_err`**

PSC acepta `r.is_err` y emite `r.is_err`; stage0 lo rechaza con `E0013`
(`Result has no field 'is_err'`). Es una divergencia de F3, no una feature.

**Fix**

- Resolución de miembros por **tipo anotado** del receptor, en este orden:
  1. campo/propiedad del tipo (`.len`, `.value`, `.is_ok`, `.is_present`);
  2. método de `enchanting` aplicable al tipo;
  3. función del módulo/scope;
  4. error.
- Para `calling expr.prop`, bajar `prop` como acceso de campo si el tipo tiene
  ese campo; no como llamada.
- Para llamadas no cualificadas, preferir el símbolo local/módulo sobre un
  método primitivo de extensión; stage0 ya lo hace así.
- `is_err` debe ser `E0013` en F3 (paridad). Añadir test negativo.
- `or:`/`or return` sobre `result`: F3 debe desenvolver el `result` como
  stage0. Si el coste es bajo, arreglarlo en F5a y bajar `or` en F4 (hoy emite
  `entries = 0`); si no, documentar el workaround `if not r.is_ok` y abrir
  deuda para F6. **Recomendado arreglarlo**: el driver y F6 lo necesitan.
- Tests:
  - `calling xs.len` en lista, mapa y string;
  - función local `starts_with` vs método de string;
  - `r.is_ok`/`r.value`, `r.is_err` rechazado;
  - `or:` y `or return` sobre `result` (si se implementa).

### 4.8 G7 — Strings, listas, indexación y omens

**Síntoma A — igualdad de strings compuesta**

`std/compass.pengu`:

```pengu
if (tp at common) == (bp at common):
```

emite:

```c
if (((*(PenguString*)pengu_list_at(...))) == ((*(PenguString*)...)))
```

`==` sobre `PenguString` no compila.

**Fix:** decidir la comparación por el **tipo anotado** de ambos operandos, no
por la forma sintáctica. Si alguno es `string`, emitir
`pengu_string_equal(a, b)` (o `pengu_string_compare` para orden). Aplicar a
`==`, `!=`, `<`, `<=`, `>`, `>=` con strings si el lenguaje lo permite.

**Síntoma B — literales de lista en llamadas**

```pengu
calling compass.cp_join with ["/tmp/f5_proj", "pengu.toml"]
```

emite elementos `void*` y gcc avisa de inicialización incompatible.

**Fix:** propagar el tipo esperado del parámetro al literal de lista/mapa;
inferir el tipo de elemento y emitir `PenguList` tipada. Si no hay tipo
esperado, error de F3 con span, no `void*`.

**Síntoma C — indexación**

12 errores “el valor del subíndice no es ni matriz ni puntero ni vector”.
Revisar `at` sobre:
- listas (`PenguList` -> `pengu_list_at`),
- `bytes of` (`ref to frozen byte`),
- slices (`PenguSlice`),
- arrays,
- strings (`string at i` debe devolver string de 1 byte o char según tipo).

**Síntoma D — omens**

2 errores `request for member 'tag' in something not a struct`. Revisar el
acceso a `.tag`/payload de omens con payload y `judge`; usar el nombre C
correcto (`_Tag` + campos).

**Tests:** cada síntoma con un fixture propio y ejecución; `std/compass`
`cp_relative_to` compila.

### 4.9 G8 — Propagación de errores, `links` y `#line`

#### 4.9.1 Codegen que falla en silencio

Hoy `generate_c` devuelve siempre `ok = true`:

```pengu
return with ok is true, bundle is code, stats is st
```

y `CgContext.errors` no se incrementa en ningún sitio. Un nodo no soportado
puede producir C inválido sin que el driver lo sepa.

**Fix**

- Añadir un canal de diagnóstico interno:
  - `CgContext.errors` se incrementa en cada `unsupported`/`missing annotation`;
  - `CgResult.ok = (errors == 0)`;
  - `CgResult.message`/`diagnostics` con el primer error y el span;
  - `free_result` libera el mensaje.
- El driver, si `ok = false`, **no invoca cc**: imprime el error interno y sale
  1.
- Tests: fixture con nodo no soportado (o inyección de error) -> `ok=false`,
  sin cc.

#### 4.9.2 `links` y `ldflags`

F4 recolecta `include` pero **no** `link`/`ldflag`; el driver no puede enlazar
`std.petitio`, `std.compressus`, `std.regulus`, etc.

**Fix**

- `CgCatalog` añade:

```pengu
rune CgLink:
    text as string
    module as int
    is_ldflag as bool
```

- `catalog_collect` recorre `NdLinkStmt`/`NdLdflagStmt` (incluidas las ramas
  vivas de `when`).
- `CgResult` expone `links as list of string` y `ldflags as list of string`.
- DCE nativa: si `prune_native` está activo, descartar los links de módulos no
  vivos; por defecto (`false`) conservarlos.
- El driver combina: manifiesto + `CgResult.links` + runtime, sin duplicados.
- Tests:
  - `.d.pengu` con `link "demo"` + `libdemo.a` -> binario ejecuta;
  - `include` condicional de `when`;
  - `--prune-native` no rompe lo vivo (si se implementa).

#### 4.9.3 `#line` exacto

**Síntoma:** los errores de gcc caen 15–20 líneas por debajo del origen (a
veces en un comentario `##` de la función siguiente). El `#line` se emite para
cada statement, pero no siempre con el nodo correcto; en expresiones
multilínea se pierde el span.

**Fix**

- Emitir `#line <línea>` con la **línea del nodo** (no del bloque) antes de:
  - cada statement,
  - cada expresión que pueda fallar en C (llamada, acceso, cast),
  - cada `return`.
- No emitir `#line` dentro de una misma línea C ya cubierta.
- Mantener `OriginMap` (si se añade) como `C line -> Span`.
- Test: 20 errores de C sintéticos (por ejemplo `antiquus` con `#error` o
  llamada a función inexistente) deben mapear a la línea `.pengu` exacta;
  `--no-line-markers` conserva el origin map (si existe).
- F5 no expone `--no-line-markers` en `build`.

### 4.10 Tests de F5a

Nuevos fixtures en `psc/tests/fixtures/f5/`:

| Fixture | Cubre |
|---|---|
| `module_identity/` (proyecto) | G1: entry relativo, imports absolutos, un solo tipo |
| `hooks.pengu` | G2: struct de punteros a función, callback |
| `fn_ptr_array.pengu` | G2: array de callbacks, `ref to frozen weave` |
| `defer_scope.pengu` | G3: defer en if/loop, return temprano |
| `banish_block.pengu` | G3: banish en bloque + interpolación |
| `value_if.pengu` | G5.1: `return if`, `let is if`, anidado |
| `when_os.pengu` | G5.2: include/link/return condicional |
| `to_string.pengu` | G5.3: int/float/bool/char |
| `qualified_const.pengu` | G4: `mod.CONST` |
| `member_len.pengu` | G6: `calling xs.len` |
| `name_collision.pengu` | G6: función local vs método |
| `result_fields.pengu` | G6: `is_ok`/`is_err`/`or` |
| `string_cmp.pengu` | G7: `(list at i) == "x"` |
| `list_literal_call.pengu` | G7: `f with ["a", "b"]` |
| `at_index.pengu` | G7: list/bytes/slice/array |
| `omen_payload.pengu` | G7: `tag` y payload |
| `cc_error.pengu` | G8: `antiquus` con error C -> mapeo `.pengu` |

Cada fixture se compila y ejecuta con gcc y clang; los de memoria se ejecutan
con ASan/UBSan. Golden C solo para los casos nuevos estables (no para todos).

### 4.11 Timebox y go/no-go de F5a

| Ola | Contenido | Salida esperada |
|---|---|---|
| Ola 0 | Preflight tool + baseline | 702 errores medidos, categorizados |
| Ola 1 | G1 + G2 | ~800 -> ~250 errores |
| Ola 2 | G3 + G4 | ~250 -> ~50 |
| Ola 3 | G5 + G6 + G7 + G8 | ~50 -> 0 |
| Ola 4 | `-Wall -Wextra -Werror`, ASan, golden | gate verde |

- **Timebox:** 4,5–6,5 semanas.
- Al final de la ola 3: si quedan >50 errores o una causa exige cambio de
  lenguaje, **paro y replanifico**.
- No se empieza F5b hasta que el preflight dé 0 y el smoke (`version`,
  `check`, `emit-c`) funcione.

---

## 🗂️ 5. F5b — Paths, manifiesto y toolchain

**Objetivo:** convertir un target (archivo o directorio) en un `BuildPlan`
completo y validado.

### 5.1 Resolución del target

```text
resolve_target(target):
  if target == "":
      start = cwd
      mode = project
  elif is_dir(target):
      start = target
      mode = project
  else:
      start = dirname(target)
      mode = single_file (con manifiesto si se encuentra)

  root = find_manifest_root(start)   # sube hasta 64 niveles
  if root != "":
      manifest = load_manifest(root)
      base_dir = root
      entry = manifest.entry si mode == project
              si no, target
  else:
      if mode == project and no target file:
          error "no pengu.toml found in <start>"
      base_dir = dirname(target)
      entry = target
      manifest = defaults(base_dir)
```

Reglas:

- Un archivo dentro de un proyecto usa el manifiesto (dirs, links, flags) pero
  el entry es el archivo.
- Un directorio con `pengu.toml` usa `entry` del manifiesto.
- Un directorio sin manifiesto: error 2.
- `psc check <dir>` resuelve el entry y solo ejecuta F3.
- `psc run <file> -- args` no reutiliza el manifiesto para el `run`, solo para
  el build.

### 5.2 `ProjectManifest`

```pengu
rune ProjectManifest:
    base_dir as string
    name as string
    version as string
    entry as string
    output as string            # "exe" | "c"
    output_name as string
    src_dir as string
    lib_dir as string
    include_dir as string
    c_dir as string
    build_dir as string
    includes as list of string
    links as list of string
    lib_dirs as list of string
    include_dirs as list of string
    cflags as list of string
    ldflags as list of string
    defines as list of string
    cc as string
    strict_c99 as bool
```

Carga:

1. `std.archivum.read_text(<root>/pengu.toml)`.
2. `std.toml.parse`.
3. Si `err`: mensaje con línea (`std.toml` ya la incluye), exit 1.
4. Leer `project.*`, `build.*`, `profiles.<perfil>.*`.
5. Arrays: `std.toml.get_array`; liberar con `free_strings`.
6. Defaults de stage0 si faltan.
7. Validar:
   - `output` en `exe|c`; otro -> “not yet (F6)”;
   - `entry` existe (o candidatos `src/main.pengu`, `main.pengu`);
   - `name`/`output_name` no vacíos;
   - `dependencies`/`assets` no vacíos -> “not yet (F9/F7)”;
   - `target` no vacío -> “not yet (F11)”;
   - `cc` válido.
8. `free_manifest`.

Perfiles:

- `debug` por defecto; `release` opcional.
- Fusionar `[build].cflags` + `profiles.<p>.cflags` sin duplicar.
- `defines` idem.
- Si el perfil no existe: error 2 con lista de perfiles.

### 5.3 `ToolchainPaths`

```pengu
rune ToolchainPaths:
    repo_root as string
    runtime_archive as string
    runtime_include as string
    std_dirs as list of string
    std_c_dir as string
    layout as string            # "checkout" | "portable" | "fhs" | "project"
```

- `repo_root`: primer ancestro que contiene `std/` o `build/lib`; si no, "".
- `runtime_archive`: búsqueda de 3.4; error si falta.
- `runtime_include`: directorio que contiene `pengu_runtime.h`.
- `std_dirs`: `<repo>/std`, `<exe_dir>/std`, `$PENGU_STD_DIR`,
  `<prefix>/share/pengu/std`; deduplicar.
- `std_c_dir`: `<repo>/std_c` (headers `utf8.h`, `toml_min.h`, `re.h`).
- `layout`: para mensajes y tests.
- `free_paths`.

### 5.4 `Toolchain`

```pengu
rune Toolchain:
    cc as string
    cc_path as string
    dialect as string           # gcc|clang|tcc|msvc
    cflags as list of string
    ldflags as list of string
    include_dirs as list of string
    lib_dirs as list of string
    links as list of string
```

Resolución:

1. `--cc` / `PSC_CC` / `PENGU_CC` / manifest / PATH.
2. `dialect` por basename.
3. Si `msvc`: error “not yet (F11)”.
4. Flags base + manifiesto + perfil + `PENGU_CFLAGS/LDFLAGS`.
5. `include_dirs`:
   - `<build_dir>`, `<base>/include`, `<base>/lib/*/include`,
   - `<runtime_include>`, `<std_c_dir>`,
   - `include_dirs` del manifiesto.
6. `lib_dirs`:
   - `<runtime_lib>`, `<base>/lib`, `<base>/lib/*/lib`,
   - `lib_dirs` del manifiesto,
   - `<base>/build/lib` si existe.
7. `links`: manifiesto + `pengu_runtime` (siempre).
8. Comando final:
   ```text
   <cc> <cflags> <defines> <include flags> <bundle.c> <c_sources>
        <lib dirs> <link flags> <ldflags> -o <out>
   ```
9. `cc --version` una vez para `--verbose` y detección (capturar y liberar).
10. `cc` se ejecuta con **cwd = `base_dir`**, porque los `#line` del bundle son
    relativos a ese directorio. Si `base_dir` no existe, exit 2.

### 5.5 Errores de entorno y entrada

Salvo el manifiesto inválido (que es un error del proyecto, exit 1), estos
errores son de entorno/uso y salen con exit 2, con mensaje accionable:

| Situación | Mensaje |
|---|---|
| no hay cc | `psc: no C compiler found (tried: ...); use --cc or PSC_CC` |
| falta runtime | `psc: cannot find libpengu_runtime.a; searched: ...; run python build_runtime.py or set PENGU_LIB_DIR` |
| falta header | `psc: cannot find pengu_runtime.h; ...` |
| manifiesto inválido | `psc: invalid pengu.toml: <line>` (exit 1 si es del usuario) |
| entry no existe | `psc: entry file '<path>' not found` |
| output no soportado | `psc: output 'static' is not supported in F5 (planned F6)` |

---

## 🔨 6. F5c — build, run, expand y check

### 6.1 `psc build`

```text
psc build [TARGET] [options]

TARGET   archivo .pengu o directorio con pengu.toml; sin target: cwd

options:
  --profile=debug|release
  --cc=NAME
  --out=PATH
  --release-unsafe
  --strict-c99
  --verbose
  --help
```

Pipeline:

1. `resolve_target` -> `BuildPlan`.
2. Validar entry, cc, runtime, dirs.
3. Crear `build_dir` (`create_dir` con `parents=true`) y el directorio padre
   de `out_path` si `--out` lo necesita.
4. `sema.check_file(entry, opts)`.
   - Si hay errores: renderizar el bag a stderr, liberar, exit 1.
5. `codegen.generate_c(program, cg_options)`.
   - `base_dir`, `entry_file`, `is_test=false`, `is_library=false`,
     `line_markers=true`, `strict_c99`, `release_unsafe`, `target_compiler`.
   - Si `ok=false`: error interno con span, exit 1.
6. Escribir `<build_dir>/bundle.c` (temp + rename).
7. Si `manifest.output == "c"`: liberar, imprimir la ruta del bundle, exit 0.
   No se invoca cc (equivalente a `expand --out`).
8. `build_cc_command` (5.4).
9. `run_capture_all(cc, args)` con `cwd = base_dir`.
   - exit 0: instalar artefacto (temp + rename).
   - exit != 0: parsear stderr, imprimir; exit 1.
10. Imprimir `Finished [profile] -> <artifact>` si no `--verbose`/quiet.
11. Liberar todo.
12. Exit 0.

`--verbose` imprime:
- manifiesto y layout;
- módulos y tiempo de F3/F4;
- comando cc exacto;
- stdout/stderr de cc si falla.

### 6.2 `psc run`

```text
psc run [TARGET] [-- args...]
```

1. `build` con las mismas opciones.
2. Si `ok`: `run_capture_all` **no**; ejecutar el artefacto con
   `rites.exec`/`spawn` y propagar stdout/stderr/exit.
   - `rites.exec` no captura; es lo correcto para `run`.
   - args del usuario tras `--`.
   - cwd = `base_dir`.
3. Exit code:
   - 0–255 del hijo;
   - señal en POSIX -> 128 + señal;
   - build fallido -> el exit del build.

`psc run` no debe recompilar dos veces. No cachea.

### 6.3 `psc expand`

```text
psc expand [TARGET] [--out=PATH] [--library] [--test]
```

- Pasos 1–6 de build; **no** invoca cc.
- `--out`: escribe el bundle; sin `--out`: stdout.
- `--library`: sin wrapper `main` (F4 ya lo soporta).
- `--test`: sección de tests (F4 ya lo soporta), sin ejecutar.
- `psc emit-c` sigue existiendo y comparte implementación; `expand` resuelve
  proyecto con manifiesto, `emit-c` mantiene el comportamiento actual de F4
  (para no romper tests/oráculos).

### 6.4 `psc check`

- Archivo: comportamiento actual.
- Directorio: resolver manifiesto/entry y `check_file`.
- Sin target: cwd.
- No genera C, no invoca cc.
- Exit 0/1; JSON sigue siendo `--diagnostics=json` (existente).

### 6.5 C glue

Soporte básico:

- `.c` en `<base>/<c_dir>` (por defecto `c/`).
- `.c` en `<base>/<lib_dir>/<binding>/c/`.
- Orden determinista (sorted por path).
- Añadir sus include dirs.
- No generar `main` propio si el usuario ya tiene uno (el bundle wrapper siempre
  genera `main`; si hay C glue con `main`, error de enlace claro).
- Test: proyecto con `c/glue.c` que exporta una función y un `declare` en
  PenguScript que la llama.

### 6.6 Refactor de CLI

- Mover `run_lex`, `run_parse`, `run_check`, `run_emit_c` a `cmd/*.pengu`.
- `main.pengu` solo despacha y construye `BuildOptions`.
- Parser común `cli/args.pengu`:
  - `--flag`, `--flag=value`, `--` y posición;
  - errores “unknown option” exit 2;
  - ayuda generada desde `cli/help.pengu`.
- Mantener los textos/exit codes actuales de `lex/parse/ast/check/emit-c` para
  no romper F1–F4.
- `psc version` -> `psc 0.5.0 (F5)`.
- `psc --version` idem.

### 6.7 Flags no soportados

Se reconocen y fallan con mensaje, no se ignoran:

```text
--json, --locked, --frozen, --pch, --target, --no-cache,
--clear-cache, --ephemeral, --keep, --assets, --test-runner
```

Mensaje: `psc build: --locked is not supported in F5 (planned F6/F9)`.
Exit 2.

### 6.8 Ejemplos

```bash
# Un archivo
psc build hello.pengu
./build/hello

# Proyecto
cd psc
psc build
psc run
psc expand --out=/tmp/psc.c

# Auto-build a otro path (bootstrap)
psc build . --out=build/bootstrap/stage2/psc --verbose

# Diagnóstico
psc check psc
psc build psc --cc=clang
```

---

## 🩺 7. F5d — Diagnósticos y errores

### 7.1 Semánticos

- Reutilizar `DiagnosticBag.render_plain` (o `render_colored` si TTY).
- No duplicar mensajes.
- Warnings no fallan (salvo `--deny-deprecated`, fuera de F5).
- Exit 1 si `error_count > 0` o `SemaResult.ok = false`.

### 7.2 Internos de codegen

- `CgResult.ok = false` y mensaje con:
  - nodo/constructo,
  - archivo/línea/columna si hay span,
  - nota “this is a PSC codegen bug; report it”.
- Nunca invocar cc con un bundle parcial.
- Test con un nodo forzado/no soportado.

### 7.3 C compiler

Parser de stderr (sin dependencias externas):

```text
GCC/Clang: file:line:col: error|warning|fatal error|note: message
TCC:       file:line: error|warning: message
MSVC:      file(line,col): error Cxxxx: message   (F11)
```

- Si `file` termina en `.pengu`: imprimir tal cual, con prefijo `psc:` solo en
  la cabecera.
- Si `file` es `.c`/`bundle.c`: imprimir y añadir nota `generated from
  <entry>`; no ocultar.
- Si no matchea: relay de las líneas crudas.
- Preservar el código/mensaje del compilador; **no inventar E/W**.
- `--verbose`: mostrar comando y stderr completo.
- Tests:
  - error sintético en `antiquus` -> línea `.pengu`;
  - warning no falla;
  - stderr con rutas y mensajes localizados (gcc en español) no rompe el
    parser;
  - stderr multilínea/notas.

### 7.4 `#line`

- `--line-markers` siempre en build.
- `#line` antes de statements/expresiones con posible error (4.9.3).
- Si un error de C no se puede mapear: mostrar archivo C y nota; no fingir una
  posición `.pengu`.

### 7.5 Formato de salida

```text
psc: C compilation failed (gcc, exit 1)

psc/src/psc/source.pengu:123:9: error: ...
  |
  = note: generated C: build/bundle.c:4567
```

(El formato exacto puede ajustarse; lo importante es archivo/línea/columna y
que el mensaje del compilador no se pierda.)

---

## 🔁 8. F5e — Bootstrap stage1 → stage2 → stage3

### 8.1 Definiciones

```text
stage0  = compilador Python actual (3.0.3), oráculo
stage1  = PSC compilado por stage0      (psc/build/psc)
stage2  = PSC compilado por stage1
stage3  = PSC compilado por stage2
```

`stage1` ya existe si `psc/build/psc` se construye con el fuente actual. F5
añade el driver a ese fuente; por tanto stage1 incluye el driver.

### 8.2 Diagrama T

```text
        stage0 (Python)
          │  compila psc/src
          ▼
        stage1 (PSC)
          │  psc build .
          ▼
        stage2 (PSC)
          │  psc build .
          ▼
        stage3 (PSC)

        stage2 ──emit-c──▶ C2
        stage3 ──emit-c──▶ C3
        C2 == C3  (punto fijo)
```

### 8.3 Comandos

```bash
cd psc

# stage1: stage0 construye PSC
../.venv/bin/python ../pengu_project.py build
cp build/psc build/bootstrap/stage1/psc

# stage1 compila PSC -> stage2
./build/bootstrap/stage1/psc check src/main.pengu
./build/bootstrap/stage1/psc build . \
    --out=build/bootstrap/stage2/psc --verbose

# stage2 compila PSC -> stage3
./build/bootstrap/stage2/psc check src/main.pengu
./build/bootstrap/stage2/psc build . \
    --out=build/bootstrap/stage3/psc --verbose

# punto fijo
./build/bootstrap/stage2/psc emit-c src/main.pengu \
    --out=build/bootstrap/stage2/bundle.c
./build/bootstrap/stage3/psc emit-c src/main.pengu \
    --out=build/bootstrap/stage3/bundle.c
python ../psc/tools/compare_bundles.py \
    build/bootstrap/stage2/bundle.c \
    build/bootstrap/stage3/bundle.c
```

### 8.4 Seguridad del auto-reemplazo

- El driver compila a `<out>.tmp.<pid>` y hace `rename`.
- Si `out` es el ejecutable en curso (`argv[0]`), el `rename` es seguro en
  POSIX: el proceso sigue con el inodo viejo.
- En Windows, `rename` sobre un ejecutable en uso falla: F5 no lo garantiza;
  el bootstrap usa `--out` distinto.
- El bootstrap **nunca** escribe sobre el stage que está ejecutando.
- Si el build falla, se elimina el temporal; no se deja un binario parcial.

### 8.5 Punto fijo

`compare_bundles.py`:

1. Normaliza:
   - rutas absolutas del checkout -> `<root>`;
   - `\r\n` -> `\n`;
   - espacios/tabs finales;
   - opcionalmente `#line` (no por defecto; deben coincidir).
2. Compara byte a byte.
3. Si difiere:
   - muestra el primer offset/línea;
   - usa `#line` para mapear a `.pengu`;
   - reporta el bloque C y el archivo fuente.
4. Calcula SHA-256 de ambos y del normalizado.
5. Sale 0 solo si son iguales.

Además del C, comparar:

- `stage2 version` == `stage3 version`;
- `stage2 check` vs `stage3 check` en 10 fixtures (mismos códigos/líneas);
- `stage2 build` y `stage3 build` de un hello (misma salida/exit);
- corpus 66 con stage2 y stage3 (misma salida).

### 8.6 `psc/tools/bootstrap.py`

Dev-only, Python:

```text
python psc/tools/bootstrap.py \
    --psc psc/build/psc \
    --out psc/build/bootstrap \
    --profile debug \
    [--keep] [--full] [--no-corpus]
```

Pasos:

1. Verifica `psc` stage1 y `version`.
2. `stage1 check` del entry.
3. `stage1 build` -> stage2.
4. Smoke de stage2: `version`, `check`, `emit-c` (compila y ejecuta).
5. `stage2 build` -> stage3.
6. Smoke de stage3.
7. `compare_bundles` stage2/stage3.
8. Corpus (66) con stage2 (y stage3 en `--full`).
9. Escribe `report.json`:
   ```json
   {
     "date": "...",
     "stage1": {"version": "...", "sha256": "..."},
     "stage2": {"version": "...", "bundle_sha256": "...", "build_s": 12.3},
     "stage3": {"version": "...", "bundle_sha256": "...", "build_s": 12.4},
     "fixed_point": true,
     "corpus": {"passed": 66, "total": 66},
     "std": {"passed": 40, "total": 40}
   }
   ```
10. En fallo, conserva artefactos con `--keep`; sin `--keep`, limpia.

No se commitean binarios ni `report.json`; sí un resumen en
`docs/selfhost/BOOTSTRAP.md` (versión, fecha, host, números; sin hashes
específicos de máquina o con nota).

### 8.7 Triage de fallos

| Síntoma | Causa probable | Acción |
|---|---|---|
| stage1 no compila PSC | G1–G8 incompletos | volver a F5a; preflight |
| stage1 compila, stage2 no arranca | miscompile de stage1 | comparar C de stage1 vs stage0; aislar fixture |
| stage2 compila, stage3 difiere | no determinismo o miscompile | `compare_bundles`, `#line`, orden de mapas |
| corpus falla con stage2 | codegen/link/driver | probar mismo caso con stage1 y `emit-c` |
| ASan falla | ownership/defer | fixture mínimo, `defer` scope |
| time/link | flags/runtime | `--verbose`, comando cc |

---

## 🧪 9. Tests, paridad, ASan y rendimiento

### 9.1 Unitarios .pengu

En `psc/tests/`:

- `manifest_unit.pengu`: TOML mínimo, perfiles, arrays, defaults, errores.
- `paths_unit.pengu`: checkout/portable/FHS simulados con archivos temporales.
- `toolchain_unit.pengu`: prioridad de cc, flags, dedupe de links.
- `build_plan_unit.pengu`: target archivo/dir, entry, `--out`.

Se ejecutan con stage0 (`pengu_project.py run`) como los tests actuales.

### 9.2 `tests/psc/test_f5_acceptance.py`

Casos (~20):

1. `build` single file -> artifact runs, exit 0.
2. `build` project con `pengu.toml` -> artifact en `build/`.
3. `build --out=` -> artifact en el path pedido.
4. `run` -> stdout y exit code del hijo.
5. `run -- arg1 arg2` -> args visibles.
6. `expand` -> C por stdout; no invoca cc.
7. `expand --out` -> archivo.
8. `check` proyecto -> 0; `check` con error -> 1.
9. `--profile=release` -> flags aplicados (probar con `antiquus` `#if`).
10. `defines` del manifiesto -> `#if` pasa.
11. `links` + `libdemo.a` -> enlaza y ejecuta.
12. C glue (`c/glue.c`) -> enlaza y ejecuta.
13. path con espacios/comillas/`;` -> funciona (escape).
14. falta runtime -> exit 2, mensaje con rutas.
15. falta cc -> exit 2.
16. entry inexistente -> exit 2.
17. manifiesto inválido -> exit 1, línea.
18. output `static` -> exit 2 “not yet”.
19. flag no soportado -> exit 2.
20. `--verbose` -> muestra comando cc.
21. determinismo: dos builds -> bundle idéntico.
22. C error mapeado -> `.pengu:line`, no `bundle.c`.
23. `psc build` no invoca Python (PATH sin python; solo binario).
24. `psc build` sobre `psc/src/main.pengu` (smoke, opt-in por coste).

### 9.3 `tests/psc/test_f5_selfcompile.py`

- `test_emit_self_compiles`: `emit-c psc/src/main.pengu`, gcc -> binario.
- `test_self_binary_version`: `version` = `psc 0.5.0 (F5)`.
- `test_self_binary_check`: `check src/main.pengu` -> 0.
- `test_self_binary_emit_c`: emite bundle no vacío y compila.
- `test_self_binary_build_hello`: construye un hello con stage1.
- Marcados `selfhost`; no corren en la suite rápida por defecto.

### 9.4 `tests/psc/test_f5_bootstrap.py`

Opt-in `PSC_F5_FULL=1` (o CI nightly):

- stage1 -> stage2 -> stage3;
- fixed point;
- corpus 66;
- std `--library`;
- ASan.

### 9.5 Corpus y std

- **Conformidad:** 66/66 ejecutables con stage2 (y stage3). La auditoría habla
  de 126 casos; en este árbol hay **66** en `tests/conformance/compliance/` y
  **55** archivos en `tests/compiler/`. El gate usa los 66 ejecutables y, como
  mínimo, los 55 de `tests/compiler` que tengan `main`; si aparece el corpus
  completo de 126, se añade sin cambiar el criterio.
- **Compiler tests:** los ejecutables de `tests/compiler` que tengan `main`;
  los negativos se comparan por código/línea.
- **F3:** `psc check` sobre `std/`, `tests/`, `psc/src`; 0 errores inesperados.
- **std:** para cada `std/*.pengu`, `psc emit-c --library` y
  `gcc -fsyntax-only`; reportar el total. Gate completo según D3.
- **Negativos:** `coherence_conflict` sigue rechazado.

### 9.6 ASan/UBSan

- Compilar el bundle de PSC y los 66 con `-fsanitize=address,undefined`.
- Ejecutar `psc check/emit-c/build` sobre el corpus con ASan.
- Casos de defer/banish/scope con `detect_leaks=1`.
- Diferencia explícita runtime vs codegen; no ocultar fugas del runtime.

### 9.7 Determinismo

- Dos `emit-c` seguidos -> byte-idéntico.
- Dos `build` seguidos -> mismo bundle (el binario puede variar por `-g`? no).
- `stage2`/`stage3` -> mismo C normalizado.
- Sin timestamps ni orden de mapas.
- SHA-256 en el reporte.

### 9.8 Rendimiento

| Métrica | Objetivo F5 |
|---|---|
| `psc emit-c` PSC | ≤ 10 s debug (hoy 5,8 s) |
| `psc build` PSC | ≤ 30 s debug (stage0 tarda ~10 s con caché) |
| Bootstrap completo (3 stages) | ≤ 3 min en CI |
| Bundle PSC | ≤ 20 % más que stage0 |
| Memoria | < 2 GB |
| Sin O(n²) en strings/flags | revisión + benchmark |

`psc/tests/bench_build.pengu` o `bench_codegen.py` existente; reportar en
`BENCHMARKS.md`/`docs/selfhost/BOOTSTRAP.md`.

### 9.9 CI

Añadir a `.github/workflows/ci.yml` (Linux):

```yaml
psc-selfhost:
  runs-on: ubuntu-latest
  timeout-minutes: 30
  steps:
    - checkout
    - setup-pengu (runtime)
    - cd psc && python ../pengu_project.py build
    - pytest -q tests/psc/test_f1_acceptance.py tests/psc/test_f2_acceptance.py \
        tests/psc/test_f3_acceptance.py tests/psc/test_f4_acceptance.py
    - python psc/tools/selfhost_preflight.py --budget 0
    - python psc/tools/bootstrap.py --out psc/build/bootstrap --no-corpus
    - pytest tests/psc/test_f5_acceptance.py
```

- `nightly.yml`: `PSC_F5_FULL=1` + corpus + std + ASan + clang/tcc.
- Windows/macOS: mantener F1–F4; selfhost según D2.
- Cache: runtime sí; PSC binario no (se construye).

---

## 🗓️ 10. Checkpoints y calendario

| CP | Subfase | Entregable | Semanas |
|---|---|---|---:|
| **CP0** | F5a | preflight tool + baseline + fixtures de gaps | 0,5 |
| **CP1** | F5a G1 | identidad de módulos; 0 duplicados | 0,5–1 |
| **CP2** | F5a G2 | `to_c_decl`, punteros a función, hooks | 0,5–1 |
| **CP3** | F5a G3 | scopes de `defer`/`banish`/locales | 1–1,5 |
| **CP4** | F5a G4–G7 | consts, value-if, comptime, `to string`, miembros, strings/listas | 1–1,5 |
| **CP5** | F5a G8 | `CgResult.ok`, links/ldflags, `#line` | 0,5 |
| **CP6** | F5a | self-compile smoke + Werror + ASan + F1–F4 verdes | 0,5 |
| **CP7** | F5b | manifiesto, paths, toolchain; `build` de un archivo | 1 |
| **CP8** | F5c | build/run/expand/check de proyecto; CLI refactor | 1 |
| **CP9** | F5e | stage1 -> stage2; smoke | 1 |
| **CP10** | F5e | stage2 -> stage3; fixed point | 0,5 |
| **CP11** | F5f | corpus 66, std, ASan, determinismo, CI | 1 |
| **CP12** | cierre | docs, `BOOTSTRAP.md`, CHANGELOG, revisión | 0,5–1 |
| **Total** | | | **9,5–12** |

Dependencias:

```text
CP0 → CP1 → CP2 → CP3 → CP4 → CP5 → CP6
                                      │
                                      ▼
                                    CP7 → CP8 → CP9 → CP10 → CP11 → CP12
```

- CP3 y CP4 no se paralelizan (comparten `expr`/`stmt`).
- CP7/CP8 pueden empezar en paralelo con los últimos tests de F5a solo si el
  preflight ya está a 0; en la práctica, no.
- El bootstrap (CP9–CP10) es el hito que decide la viabilidad.

### Comparación con la auditoría

| Estimación | Semanas |
|---|---:|
| Auditoría F5 (asumiendo F4 cerrado) | 4–6 |
| Revisada (F5a incluido) | **9,5–12** |
| F5a | 4,5–6,5 |
| Driver + bootstrap + cierre | 5–5,5 |

La diferencia es exactamente la deuda que el corpus de F4 no cubría. No es
“scope creep”: es el coste real de llegar al primer auto-compilado.

---

## ⚠️ 11. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| F5a descubre más causas raíz | Alta | Alto | preflight semanal, olas, go/no-go en CP4 |
| Los fixes de F3/F4 rompen F1–F4 | Media | Alto | correr suites + oráculos en cada CP |
| `defer`/scope es más complejo de lo previsto | Media | Alto | ASan, fixtures mínimos, revisión de ownership |
| stage1 compila PSC pero miscompila en silencio | Media | Crítico | punto fijo, corpus, diff de C, ASan |
| El C de stage2/stage3 diverge | Media | Alto | normalización, `#line`, sin mapas en orden |
| Windows/macOS rompen el driver | Alta | Medio | Linux gate en F5; F11 |
| TCC no acepta el C | Media | Medio | best-effort; gcc/clang obligatorios |
| Enlaces nativos incompletos | Media | Alto | `CgResult.links`, tests con `.d.pengu` |
| Runtime no se encuentra en instalaciones | Media | Medio | tests de los 4 layouts, mensajes claros |
| Manifiesto TOML con casos raros | Media | Medio | corpus contra `tomllib`, tests negativos |
| Inyección/espacios en args | Baja | Alto | `shell_escape` + tests adversariales |
| Sin caché, builds lentos | Alta | Bajo | aceptado en F5; F6 |
| El bootstrap tarda demasiado en CI | Media | Medio | job separado, nightly full |
| Documentación sobreestima el estado | Alta | Bajo | corregir `CODEGEN.md`; este plan es la verdad |
| Se intenta portar el CLI completo | Alta | Medio | F5 = build/run/expand/check; resto F6 |

---

## ❓ 12. Decisiones que necesito de ti

Marca una opción por decisión. Las recomendadas son las que usaré si apruebas el
plan tal cual.

### D1 — ¿F5 incluye el cierre de F4 (F5a)?

- ✅ **Recomendado: sí.** El primer auto-compilado es imposible sin ello. Se
  etiqueta como F5a dentro de F5; no se reabre F4 como fase separada.
- ⚠️ Alternativa: reabrir F4 y llamarlo F4.5. Es el mismo trabajo, distinto
  nombre; retrasa el driver.
- ❌ No hacerlo: F5 no puede cumplir su criterio. No lo recomiendo.

### D2 — Plataforma del gate F5

- ✅ **Recomendado: Linux primero**, gcc y clang obligatorios; tcc best-effort;
  Windows/macOS en F11 (con tests F1–F4 en CI).
- ⚠️ Alternativa: los tres sistemas desde F5. Añade 2–4 semanas y riesgo de
  paths/MSVC; no es necesario para el primer auto-compilado.

### D3 — Alcance de `std/` en el gate

- ✅ **Recomendado:** obligatorio `std/` que PSC importa + los 66 de
  conformidad; **adicional** `std/` completo con `emit-c --library`, con
  timebox de 1 semana. Si aparecen causas ajenas al auto-compilado, se abre
  F5.5/F6 con tu aprobación.
- ⚠️ Alternativa estricta: `std/` completo es obligatorio para cerrar F5.
  Más fiel a la auditoría, pero puede alargar F5 sin aportar al bootstrap.
- ❌ Alternativa laxa: solo PSC. Deja std sin probar; no lo recomiendo.

### D4 — Caché en F5

- ✅ **Recomendado: ninguna.** Cada build compila de cero. La caché es F6.
- ⚠️ Alternativa: caché mínima por hash de fuentes. Añade complejidad y
  `impl_id`; no es necesaria para el gate.

### D5 — Alcance del CLI

- ✅ **Recomendado:** `build`, `run`, `expand`, `check`, más los comandos
  actuales (`lex`, `parse`, `ast`, `emit-c`, `version`). Nada más.
- ⚠️ Alternativa: añadir `test`/`init`/`clean` ahora. Es F6/F7 y desvía.

### D6 — Manifiestos

- ✅ **Recomendado:** solo `pengu.toml` (subconjunto de 3.5). `pengu.yaml` y
  `pengu.json` -> error “not supported in F5”.
- ⚠️ Alternativa: YAML de compatibilidad. Es un parser más y no aporta al
  bootstrap.

### D7 — Metadatos de enlace

- ✅ **Recomendado:** extender el catálogo/`CgResult` de F4 con `links` y
  `ldflags` (una sola fuente de verdad). El driver no reescanea el AST.
- ⚠️ Alternativa: que el driver escanee el AST. Duplica lógica y se
  desincroniza con DCE.

### D8 — Política de paths

- ✅ **Recomendado:** identidad canónica absoluta; display relativo a
  `base_dir` cuando sea posible; normalización en el comparador de bundles.
- ⚠️ Alternativa: todo absoluto. Rompe la reproducibilidad entre checkouts y
  ensucia los diffs.

### D9 — CI

- ✅ **Recomendado:** job `selfhost` en cada PR (preflight + stage1→stage2),
  bootstrap completo/ASan/corpus en nightly.
- ⚠️ Alternativa: solo nightly. Más barato, pero los fallos llegan tarde.

### D10 — Versión

- ✅ **Recomendado:** `psc 0.5.0 (F5)`; `psc/pengu.toml` 0.5.0. No tocar la
  versión del repo (stage0 3.0.x).
- ⚠️ Alternativa: mantener 0.3.0. Confunde los reportes de bootstrap.

### D11 — Política de go/no-go

- ✅ **Recomendado:** si al final de la ola 3 de F5a quedan >50 errores o una
  causa exige cambiar el lenguaje, paro y replanifico.
- ❌ Seguir “hasta que salga”: riesgo de semanas sin señal.

### D12 — C glue

- ✅ **Recomendado:** soporte básico (`c/`, `lib/*/c/`) desde F5c; un test.
- ⚠️ Alternativa: diferir a F6. PSC no lo necesita, pero muchos proyectos sí;
  el coste es bajo.

Si apruebas D1–D12 recomendadas, empiezo por **CP0** (preflight tool + fixtures
+ baseline) y no toco el driver hasta que CP6 esté verde.

---

## ✅ 13. Criterios de aceptación

F5 se considera cerrada solo si:

1. `psc emit-c psc/src/main.pengu` produce C que compila con
   `gcc -std=c11 -Wall -Wextra -Werror` y con `clang` (y el binario responde
   `version`, `check`, `emit-c`).
2. `psc build` funciona para un archivo y para un proyecto con `pengu.toml`;
   `psc run` propaga stdout/stderr/exit; `psc expand` no invoca cc.
3. `psc check` acepta archivo y directorio de proyecto; los exit codes son
   0/1/2 como se especifica.
4. `psc build` usa `libpengu_runtime.a`, respeta `links`/`lib_dirs`/`includes`/
   `cflags`/`ldflags`/`defines` y compila C glue básico.
5. **stage1 compila PSC -> stage2** y stage2 funciona.
6. **stage2 compila PSC -> stage3**.
7. `C(stage2) == C(stage3)` tras normalizar rutas; `version` y
   comportamiento equivalentes.
8. PSC (stage2) compila y ejecuta **66/66** de conformidad; los negativos
   siguen rechazados; `std/` según D3.
9. `std/` usado por PSC compila; `psc check` sobre `std/`, `tests/`, `psc/src`
   sin errores inesperados.
10. Diagnósticos de C mapeados a `.pengu` con línea/columna; sin códigos
    inventados.
11. ASan/UBSan limpio en el auto-compilado y en el corpus.
12. Determinismo: dos builds -> mismo bundle; dos ejecuciones -> mismo C.
13. F1–F4 y la suite completa siguen verdes; el compilador Python no cambió.
14. CI `selfhost` verde; nightly con bootstrap completo.
15. `docs/selfhost/BOOTSTRAP.md` con diagrama T, comandos, resultados y
    limitaciones; `psc/docs/DRIVER.md`, `CODEGEN.md`, `PARITY.md`,
    `OWNERSHIP.md` y `psc/README.md` actualizados.
16. Sin TODO/placeholder/“not yet” en el camino de `build/run/expand` de F5;
    los flags no soportados fallan con mensaje explícito.
17. El binario `psc` no requiere Python en runtime (el bootstrap sí es
    dev-only).

---

## 🗂️ 14. Mapa de archivos y ownership

### 14.1 Archivos nuevos

```text
psc/src/psc/cli/args.pengu
psc/src/psc/cli/help.pengu
psc/src/psc/project/manifest.pengu
psc/src/psc/project/paths.pengu
psc/src/psc/project/toolchain.pengu
psc/src/psc/project/cc.pengu
psc/src/psc/driver/build.pengu
psc/src/psc/driver/run.pengu
psc/src/psc/driver/expand.pengu
psc/src/psc/cmd/{lex,parse,check,emit_c,build,run,expand}.pengu

psc/tests/fixtures/f5/*
psc/tests/manifest_unit.pengu
psc/tests/paths_unit.pengu
psc/tests/toolchain_unit.pengu
psc/tests/build_plan_unit.pengu
psc/tests/bench_build.pengu

psc/tools/selfhost_preflight.py
psc/tools/bootstrap.py
psc/tools/compare_bundles.py
psc/tools/run_f5_corpus.py

tests/psc/test_f5_acceptance.py
tests/psc/test_f5_selfcompile.py
tests/psc/test_f5_bootstrap.py

psc/docs/DRIVER.md
docs/selfhost/BOOTSTRAP.md
```

### 14.2 Archivos modificados

| Archivo | Cambio |
|---|---|
| `psc/src/main.pengu` | dispatcher; comandos extraídos |
| `psc/src/psc/sema/modules/program.pengu` | identidad canónica de módulos |
| `psc/src/psc/sema/modules/loader.pengu` | paths display/canónicos |
| `psc/src/psc/sema/types/convert.pengu` | sin cambios salvo bugs G6 |
| `psc/src/psc/sema/infer/core.pengu` | resolución de miembros/`to string` (si aplica) |
| `psc/src/psc/sema/check/*` | paridad `is_err`/`or` (si aplica) |
| `psc/src/psc/codegen/ctype.pengu` | `TkRef(TkFn)`, `to_c_decl` |
| `psc/src/psc/codegen/decl_types.pengu` | campos con declaradores |
| `psc/src/psc/codegen/function.pengu` | params/return, scopes |
| `psc/src/psc/codegen/stmt.pengu` | scopes, `when`, defers |
| `psc/src/psc/codegen/expr.pengu` | value-if, strings, listas, `to string`, miembros |
| `psc/src/psc/codegen/catalog.pengu` | `CgLink`, consts |
| `psc/src/psc/codegen/bundle.pengu` | includes/links vivos, errores |
| `psc/src/psc/codegen/origin.pengu` | `#line` exacto |
| `psc/src/psc/codegen/api.pengu` | `CgResult.ok`, links, message |
| `psc/src/psc/codegen/options.pengu` | campos nuevos si hacen falta |
| `psc/pengu.toml` | versión 0.5.0 |
| `psc/README.md`, `psc/docs/CODEGEN.md`, `PARITY.md`, `OWNERSHIP.md` | estado F5 |
| `tests/psc/*` | regresiones F5 |
| `.github/workflows/ci.yml`, `nightly.yml` | job selfhost |
| `.gitignore` | `psc/build/bootstrap/` |

No se toca:

- `std/`, `std_c/`, `pengu_runtime.h`, `build_runtime.py`;
- `pengu_parser/*`, `pengu_project.py`, `pengu_lsp/*` (stage0);
- `tests/` existentes salvo añadir `tests/psc/test_f5_*`;
- `AUDITORIA_AUTO_HOSPEDAJE.md` (salvo una nota de estado al cerrar F5, si lo
  apruebas).

### 14.3 Ownership

| Recurso | Dueño | Liberación |
|---|---|---|
| `BuildPlan` | `resolve_target` | `free_plan` |
| `BuildResult.bundle` | `build` | `free_build_result` |
| `BuildResult.cc_stdout/stderr` | `run_capture_all` | `free_build_result` |
| `ProjectManifest` + entries TOML | `load_manifest` | `free_manifest` |
| `ToolchainPaths`/`Toolchain` | `resolve` | `free_paths`/`free_toolchain` |
| `SemaResult.program` | driver | `sema.free_result` |
| `CgResult` | driver | `codegen.free_result` |
| `ProcessResult` | driver | `banish` de stdout/stderr |
| strings temporales | función | `defer banish` |
| `DiagnosticBag` | `SemaProgram` | `sema.free_result` |

Regla: si una función devuelve `string`/`list`/`map`/`maybe`/`result`, el
llamador es dueño; si recibe `ref to`, no lo libera. Cada función nueva lleva
`## ## Memoria`.

### 14.4 Estilo

- ≤ 800 líneas por archivo.
- `insignia psc_<área>_`.
- Nada de `"{a}{b}"` en bucles; `StringBuilder`.
- Nada de interpolación directa como argumento; variable + `defer banish`.
- `when os` solo en `project/paths.pengu` y `project/toolchain.pengu`.
- Tests en `psc/tests/`; corpus compartido en `tests/conformance`.
- Docs en español en los planes; comentarios de código y mensajes CLI en
  inglés, como el resto de PSC.

---

## 📎 15. Anexos

### A. Comandos de reproducción

```bash
# Baseline (no modifica nada)
cd /home/tugatito/Documentos/GitHub/PenguScript
./psc/build/psc version
time ./psc/build/psc emit-c psc/src/main.pengu --out=/tmp/psc_main.c
gcc -std=c11 -w -fsyntax-only -I . -I build/include -I std_c /tmp/psc_main.c 2>&1 | grep -c 'error:'
gcc -std=c11 -w -I . -I build/include -I std_c /tmp/psc_main.c \
    build/lib/libpengu_runtime.a -lm -lpthread -o /tmp/psc_main

# F4
python psc/tools/run_f4_conformance.py
.venv/bin/python -m pytest -q tests/psc/test_f4_acceptance.py

# Stage0 construye PSC
cd psc
../.venv/bin/python ../pengu_project.py build

# F3
./build/psc check src/main.pengu
```

### B. Clusters de error (evidencia)

| ID | Mensaje representativo | Nº | Origen |
|---|---|---:|---|
| G1 | `redeclaración de 'enum SourceErrorKind'` | 320 | tipos duplicados |
| G2 | `expected identifier or '(' before ')' token` | 73 | `int32_t (*)(PsParser*)*` |
| G2 | `'PsHooks' no tiene un miembro llamado 'value'` | 52 | campo sin nombre |
| G3 | `'detail' no se declaró aquí` | 3+ | banish fuera del bloque |
| G3 | `'txt'/'msg'/'ptxt' no se declaró aquí` | ~130 | locales/defers |
| G4 | `'sdiag' no se declaró aquí` | 28 | `mod.CONST` |
| G4 | `'types'/'sym' no se declaró aquí` | 16 | `mod.CONST` |
| G5 | `tipos incompatible ... 'PenguString'` | 1 | `return if` -> `0` |
| G5 | `declaración implícita de 'waitpid'` | 1 | `when` + include |
| G6 | `too many arguments to 'Num_starts_with'` | 7 | método vs función |
| G6 | argumento `PenguList*` a `Num_len(PenguString*)` | 7 | `calling xs.len` |
| G7 | `invalid operands to binary == (PenguString, PenguString)` | 1 | `(list at i) == ...` |
| G7 | `tipos incompatibles ... 'void *' ... 'PenguString'` | 4 | lista literal |
| G7 | `el valor del subíndice no es ...` | 12 | `at` |
| G7 | `member 'tag' ...` | 2 | omen |
| G8 | duplicados/varios | ~29 | cascadas |

### C. Fragmentos de C que demuestran cada causa

**G1 — tipo duplicado**

```c
typedef enum SourceErrorKind { ... } SourceErrorKind;   /* línea 82 */
/* ... token, keyword ... */
typedef enum SourceErrorKind { ... } SourceErrorKind;   /* línea 95 */
```

**G2 — puntero a función**

```c
struct PsHooks {
    int32_t (*)(PsParser*)* value;
    int32_t (*)(PsParser*)* when;
    ...
};
```

Esperado:

```c
struct PsHooks {
    int32_t (*value)(PsParser*);
    int32_t (*when)(PsParser*);
    ...
};
```

**G3 — `banish` fuera de bloque**

```c
if ((tab_line > 0) && (space_line > 0)) {
    PenguString detail = ...;
    ...
}
pengu_banish_string(&(detail));   /* ❌ */
```

**G5.1 — `if` como valor**

Fuente:

```pengu
weave cp_sep into string:
    return if calling cp_win then "\\" else "/"
```

C:

```c
PenguString cp_sep(void) {
    return 0;   /* ❌ */
}
```

**G5.2 — `when` comptime**

```c
bool cp_win(void) {
    0;   /* ❌ falta return false */
}
```

Y `std/rites.pengu` no emite `#include "sys/wait.h"`.

**G5.3 — `to string`**

```c
pengu_println((((PenguString)(value))));   /* ❌ cast */
```

Esperado: `pengu_string_from_int(value)`.

**G4 — const cualificada**

```c
sema_diag_node_error(..., sdiag.CODE_UNDEFINED, ...);   /* ❌ */
```

Esperado: `<insignia>_CODE_UNDEFINED`.

**G6 — método vs función**

```c
Num_starts_with(&(starts_with), a, "--max-errors=")   /* ❌ */
```

Esperado: `psc_main_starts_with(a, "--max-errors=")`.

**G7 — igualdad de strings**

```c
if (((*(PenguString*)pengu_list_at(...))) == ((*(PenguString*)...)))   /* ❌ */
```

Esperado: `pengu_string_equal(a, b)`.

### D. Ejemplo de `pengu.toml` de F5

```toml
[project]
name = "demo"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
output_name = "demo"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
links = ["pengu_runtime"]
cflags = ["-Wall", "-std=c11"]
defines = ["DEMO"]

[profiles.debug]
cflags = ["-g", "-O0"]
defines = ["DEBUG"]
```

### E. Glosario

| Término | Significado |
|---|---|
| **stage0** | Compilador Python actual; construye PSC |
| **stage1** | PSC compilado por stage0 |
| **stage2** | PSC compilado por stage1 |
| **stage3** | PSC compilado por stage2 |
| **punto fijo** | stage2 y stage3 producen el mismo C normalizado |
| **driver** | Capa que resuelve proyecto, invoca F3/F4 y cc |
| **plan** | `BuildPlan`: todo lo necesario para compilar |
| **layout** | checkout, portable, FHS o runtime vendorizado |
| **gap** | Causa raíz de C inválido descubierta por el preflight |

### F. Lo que no se ha hecho

- No se ha modificado código, `std/`, runtime, stage0, auditoría ni los planes
  F1–F4.
- No se han creado binarios ni artefactos en el repo.
- El único archivo nuevo es este `PLAN_F5_DRIVER.md`.
- Los spikes (`/tmp/f5_*.pengu`) son desechables y no forman parte del repo.

---

## 🏁 16. Cierre

F5 es mucho más que “un `build` que llama a gcc”. Es el primer momento en que
el compilador se mira al espejo. El espejo ya nos ha dicho lo que falta:
**~8 causas raíz, no 702 bugs**, y un camino claro para cerrarlas.

Si apruebas este plan (o cambias D1–D12):

1. empiezo por **CP0**: `selfhost_preflight.py`, fixtures de gaps y baseline
   reproducible;
2. cierro **F5a** por olas, con el preflight como métrica y sin tocar el driver
   hasta que el gate esté verde;
3. construyo **F5b/F5c** con `build`/`run`/`expand`/`check` y un solo archivo
   de prueba primero;
4. hago **F5e**: stage1 → stage2 → stage3 y comparo el C;
5. cierro con corpus, ASan, CI y `docs/selfhost/BOOTSTRAP.md`.

No he modificado nada. Dime si aceptas las decisiones recomendadas o cuáles
cambias, y arranco con CP0.
