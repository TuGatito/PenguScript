# PLAN F6 — CLI completo

> **Estado:** propuesta para aprobación. No implementado todavía.
> **Base:** F5 cerrada en `main` (driver build/run/expand/check, manifiesto,
> toolchain, bootstrap con punto fijo, TCC, tests/CI/docs).
> **Objetivo:** que `psc` sea un CLI completo y autosuficiente para el ciclo de
> vida de un proyecto PenguScript, sin depender del CLI Python (`pengu`).

---

## 1. Resumen ejecutivo

F5 dejó un compilador que se auto-compila y un driver mínimo. F6 completa la
**superficie de usuario**:

1. Un framework de CLI único (parser, help, errores, colores, JSON, exit codes).
2. Caché en disco y `gc`, para que `run`/`eval` se sientan instantáneos.
3. Comandos de proyecto: `init`, `new`, `clean`, `doctor`, `metadata`, `tree`.
4. Comandos de desarrollo: `test`, `watch`, `eval`, `time`, `benchmark`.
5. Herramientas: `fmt`, `doc`, `assets`.
6. `build`/`run`/`expand`/`check` con todas las flags y tipos de salida.
7. Stubs explícitos para lo que pertenece a fases posteriores (dependencias F9,
   LSP F8, `bind` F10, cross/WASM F11): se reconocen, se documentan y fallan con
   un mensaje de fase, nunca se ignoran.

**No se toca** stage0 Python, `std/`, el runtime ni el ABI. Toda la lógica nueva
vive en `psc/src/psc/**` y, si hace falta, en `psc/tools/**`.

---

## 2. Estado actual (F5) y brechas

### 2.1 Lo que ya existe

```text
psc lex | parse | ast | check | emit-c | build | run | expand | version | help
```

- `build/run/expand/check` de archivo y proyecto.
- `pengu.toml` mínimo (`project`, `build`, `profiles`).
- Rutas `PENGU_*`, runtime, `std/`, `std_c/`.
- gcc/clang/TCC; `run` propaga exit code.
- Bootstrap stage1→stage4 con C idéntico.
- Tests F1–F5, CI `psc-selfhost`, nightly bootstrap, ASan smoke.

### 2.2 Brechas frente al CLI Python

El CLI stage0 (`python pengu_project.py --help`) expone:

```text
init new add remove upgrade tree metadata verify vendor build run doctor gc
benchmark expand time eval watch test selftest check update bind fmt clean lsp
doc assets
```

F5 sólo cubre `build/run/expand/check` y los comandos de compilador. Faltan:

- Framework común: hoy cada `run_*` parsea a mano, no hay `cli/args` ni help
  generado, y `--out value` no funciona (sólo `--out=value`).
- Caché, `gc`, `doctor`, `clean`, `watch`, `fmt`, `doc`, `assets`, `test`,
  `eval`, `time`, `benchmark`, `metadata`, `tree`, `init`, `new`.
- Flags de build completas (`-D`, `--json`, `--pch`, `--no-dce`, `--keep`,
  `--locked`, `--frozen`, `--target`, etc.).
- Tipos de salida `obj`, `static`, `shared` (F5 sólo `exe`/`c`).
- JSON Lines estable para CI.
- Stubs explícitos de dependencias/LSP/bind/cross.

### 2.3 Deuda de F5 que F6 debe cerrar primero

| Deuda | Impacto | Acción F6 |
|---|---|---|
| `free_paths` no libera | fuga por invocación | auditoría de ownership; liberar con copias profundas |
| Autodetección desde `cwd` inestable | `psc build` fuera del checkout exige `PENGU_*` | normalizar/copiar rutas; test sin env |
| `psc check <proyecto>` genera bundle | `check` no es puro | ruta check-only sin codegen ni runtime obligatorio |
| `rites.exec` usa shell y no escapa | args con espacios/inyección | capa `proc` con argv, sin shell |
| `--flag value` no soportado | UX inconsistente | parser único |
| `psc version` dice `0.3.0 (F3)` | confuso | `0.6.0 (F6)` |
| `which` en stage3 falla | driver depende de fallback | proceso/which robusto + test stage3 |

---

## 3. Definición de “CLI completo” para F6

### 3.1 Matriz de comandos

| Comando | F5 | F6 | Fase posterior |
|---|---:|---:|---|
| `lex`, `parse`, `ast`, `check`, `emit-c` | ✅ | completar flags/JSON | — |
| `build`, `run`, `expand`, `check` proyecto | ✅ | flags completas, cache, tipos | — |
| `version`, `help` | ✅ | help por comando, `help <cmd>` | — |
| `init`, `new` | ❌ | ✅ | — |
| `clean`, `doctor`, `gc` | ❌ | ✅ | — |
| `metadata`, `tree` | ❌ | ✅ sin dependencias | grafo con deps F9 |
| `test`, `watch`, `eval`, `time` | ❌ | ✅ | — |
| `benchmark` | ❌ | ✅ casos PSC nativos | baselines Rust/Zig/C F7 |
| `fmt`, `doc`, `assets` | ❌ | ✅ | — |
| `selftest` | ❌ | ✅ dev-only (checkout) | — |
| `add`, `remove`, `upgrade`, `verify`, `vendor`, `update` | ❌ | stub explícito | F9 |
| `lsp` | ❌ | stub explícito | F8 |
| `bind` | ❌ | stub explícito | F10 |
| `--target`, WASM, MSVC | ❌ | error de fase | F11 |

“Stub explícito” significa: aparece en `--help`, valida flags, imprime
`psc add: not available until F9 (package manager)` y sale con **2**. No se
simula éxito.

### 3.2 Fuera de alcance de F6

- Resolución/instalación de dependencias, lockfile, `vendor`, `add/remove`.
- LSP (stdio/TCP), UTF-16, sockets.
- `bind` (traducción de headers C).
- Cross-compilation, WASM, MSVC.
- Cambios de lenguaje, `std/`, runtime o ABI.
- Publicación/registro de paquetes.

---

## 4. Decisiones

### D1 — Alcance de F6

- ✅ **Recomendado:** todos los comandos del §3.1 salvo los marcados como fase
  posterior; los posteriores quedan como stubs explícitos.
- ⚠️ Alternativa: sólo `fmt`/`test`/`init` y dejar `doc`/`assets`/`benchmark`
  para F7. Menos trabajo, pero “CLI completo” quedaría a medias.

### D2 — Caché en disco

- ✅ **Recomendado:** sí. Caché content-addressed para `run`, `eval` y builds
  de script; opción de cachear `build` de proyecto. `gc` la administra.
- ⚠️ Alternativa: sólo cachear `run`/`eval` (como stage0). Menos cobertura,
  suficiente para el “script feel”.
- ❌ Sin caché: F5 ya demostró que compilar de cero en cada `run` no es CLI
  completo.

### D3 — Tipos de salida

- ✅ **Recomendado:** `exe`, `c`, `obj`, `static`, `shared`.
- ⚠️ Alternativa: sólo `exe`/`c` y error para el resto hasta F7. Rompe
  `init --template pengu-lib`/`cbind`.

### D4 — Formatos de manifiesto

- ✅ **Recomendado:** `pengu.toml` canónico. `pengu.yaml`/`pengu.json` se
  detectan y fallan con “planned F9” (no se implementa un parser YAML).
- ⚠️ Alternativa: leer JSON con `std.json` y dejar YAML para F9. Añade una
  superficie de compatibilidad sin necesidad inmediata.

### D5 — Formatter

- ✅ **Recomendado:** portar la semántica de `pengu_lsp/formatting.py` (306
  líneas): indentación, espacios, strings/triples, comentarios, `@generated`,
  `.pengufmt.toml`; `--check`, `--diff`, `--stdin`.
- ⚠️ Alternativa: formatter mínimo sólo de indentación. No es “completo”.

### D6 — Documentación

- ✅ **Recomendado:** portar `pengu_doc.py` (443 líneas): Markdown por módulo,
  firmas, doc comments `##`, índice y búsqueda HTML opcional.
- ⚠️ Alternativa: sólo Markdown por módulo, sin HTML.

### D7 — Assets

- ✅ **Recomendado:** portar `pengu_assets.py` (577 líneas): recolectar
  `assets/`, generar `src/<module>.pengu` y `build/<module>_assets.c`, modo
  `embed` y `disk`, `--list`, `--force`, exclusión, determinismo.
- ⚠️ Alternativa: sólo `--list` y dejar generación a F7. El comando quedaría
  inútil para proyectos reales.

### D8 — Test runner

- ✅ **Recomendado:** `psc test` construye con `--test` (testgen de F4), ejecuta
  el runner integrado, resume por test y soporta `--json`/`--watch`.
- ⚠️ Alternativa: reutilizar `psc build --test` y un script externo. No es un
  comando de primera clase.

### D9 — Watch

- ✅ **Recomendado:** polling de mtime/ tamaño cada 200–500 ms sobre el grafo de
  imports resuelto por F3; sin inotify para mantener portabilidad.
- ⚠️ Alternativa: inotify en Linux + fallback polling. Más código y plataforma.

### D10 — Ejecución de procesos

- ✅ **Recomendado:** capa `psc.os.proc` con argv (sin shell), captura de
  stdout/stderr, stdin heredado para `run`, exit code real, timeout opcional.
- ⚠️ Alternativa: seguir con `rites.exec` y escapar. Inseguro y frágil con
  espacios.

### D11 — JSON

- ✅ **Recomendado:** JSON Lines con `schema_version: 1` para
  `build/run/check/test/doctor/gc`; un objeto por evento/línea.
- ⚠️ Alternativa: JSON distinto por comando. Peor para CI.

### D12 — Plantillas `init/new`

- ✅ **Recomendado:** paridad stage0: `exe`, `cli`, `pengu-lib`, `cbind`;
  `--type exe|c|obj|static|shared`; `--force`; TOML.
- ⚠️ Alternativa: sólo `exe`. No cubre librerías, que son parte del CLI.

### D13 — Benchmark

- ✅ **Recomendado:** runner nativo PSC para los casos `.pengu` de `benches/`
  (build/run/size, `--repeat`, `--csv`, `--only`). Sin baselines Rust/Zig/C en
  F6.
- ⚠️ Alternativa: invocar `benches/run_bench.py` (requiere Python). Rompe la
  independencia del CLI.

### D14 — Dependencias

- ✅ **Recomendado:** stubs explícitos F9. `metadata`/`tree` funcionan sin
  dependencias; con `[dependencies]` no vacío, error F9.
- ⚠️ Alternativa: implementar lockfile mínimo ahora. Es F9 y desvía F6.

### D15 — Comandos de desarrollo

- ✅ **Recomendado:** `selftest` y `benchmark` son dev-only: detectan checkout y
  fallan con mensaje claro fuera de él. No se usan en el camino de build.
- ⚠️ Alternativa: omitirlos del CLI. stage0 los tiene; “completo” incluye la
  superficie.

---

## 5. Arquitectura propuesta

```text
psc/src/
  main.pengu                     # sólo dispatch + construye CliContext
  psc/cli/
    args.pengu                   # parser argv, --flag=value, --, short flags
    command.pengu                # registro CommandSpec
    context.pengu                # cwd, color, quiet, json, env
    help.pengu                   # help global y por comando
    output.pengu                 # print/eprint, color, JSON Lines
    errors.pengu                 # CliError {code, message, help}
  psc/cmd/
    lex.pengu parse.pengu ast.pengu check.pengu emit_c.pengu
    build.pengu run.pengu expand.pengu
    init.pengu new.pengu clean.pengu doctor.pengu gc.pengu
    metadata.pengu tree.pengu
    test.pengu watch.pengu eval.pengu time.pengu benchmark.pengu
    fmt.pengu doc.pengu assets.pengu
    selftest.pengu
    stubs.pengu                   # add/remove/.../lsp/bind
  psc/cache/
    key.pengu store.pengu lookup.pengu gc.pengu
  psc/fmt/
    config.pengu format.pengu
  psc/docgen/
    model.pengu render.pengu
  psc/assets/
    collect.pengu emit.pengu
  psc/project/
    manifest.pengu paths.pengu toolchain.pengu
    output_types.pengu
    metadata.pengu
  psc/os/
    proc.pengu fs.pengu
  psc/driver/
    build.pengu check.pengu run.pengu (refactor)
```

`main.pengu` queda por debajo de ~120 líneas: crea `CliContext`, busca el
comando en el registro y ejecuta. Nada de parseo de flags en `main`.

---

## 6. Contrato de CLI

### 6.1 Parser

- `--flag`, `--flag=value`, `--flag value` (para flags que consumen valor),
  `--` (todo lo siguiente es posicional/forward), `-p`, `-c`, `-e`, `-o`, `-D`,
  `-t`, `-l`, `-f`, `-b`, `-n`.
- Flags repetibles: `-D/--define`.
- Un flag desconocido -> error `E_CLI_UNKNOWN_OPTION`, exit 2.
- Un flag que falta valor -> `E_CLI_MISSING_VALUE`, exit 2.
- Un posicional de más -> `E_CLI_UNEXPECTED_ARG`, exit 2.
- Los comandos declaran sus flags en `CommandSpec`; el help se genera de ahí.
- `--help`/`-h` en cualquier posición -> ayuda del comando, exit 0.
- `psc help <cmd>` alias de `<cmd> --help`.
- `psc` sin args -> help global, exit 2.
- `psc --version` / `psc -V` / `psc version` -> `psc 0.6.0 (F6)`.
- `--quiet`/`-q`: suprime progreso; errores siguen en stderr.
- `--no-color`: desactiva ANSI; también `NO_COLOR=1`; auto-off si no TTY.

### 6.2 Exit codes

| Código | Significado |
|---:|---|
| 0 | éxito |
| 1 | error de compilación, test fallido, check con errores, fmt `--check` con cambios |
| 2 | uso incorrecto, flag desconocido, comando no implementado, error de E/S de CLI |
| 3 | reservado para “interno” (no se usa en F6) |

`run` propaga el exit code del hijo (incluido 1/2), excepto errores propios del
CLI (2).

### 6.3 Salida

- Humana por defecto: mensajes `Finished`, rutas, resumen.
- `--json`: JSON Lines, sin colores, un objeto por evento.
- Todos los comandos respetan `--quiet`, `--no-color`, `--json` cuando aplica.
- Errores siempre a stderr; stdout sólo resultados.

Esquema JSON v1 (ejemplo `build`):

```json
{"schema_version":1,"event":"start","command":"build","target":"."}
{"schema_version":1,"event":"phase","phase":"codegen","status":"ok","ms":12}
{"schema_version":1,"event":"done","status":"ok","artifact":"build/app","ms":340}
```

`test`:

```json
{"schema_version":1,"event":"test","name":"math.add","status":"pass","ms":1}
{"schema_version":1,"event":"summary","passed":12,"failed":1,"skipped":0}
```

### 6.4 Help

Cada comando documenta: descripción, uso, flags, variables de entorno, exit
codes y un ejemplo ejecutable. `psc --help` lista todos, incluidos los stubs con
su fase.

---

## 7. Comandos

### 7.1 `psc build`

Uso:

```bash
psc build [TARGET] [flags]
```

Flags F6:

```text
-p, --profile=debug|release|small
-c, --config=PATH
-e, --entry=PATH
-o, --output=PATH          # alias de --out
-D, --define=NAME[=VALUE]  # repetible
--cc=NAME
--verbose
--json
--test
--strict-c99
--target-compiler=gcc|clang|tcc|msvc
--release-unsafe
--deny-deprecated
--no-dce
--prune-types
--no-line-markers
--dce-scope=std|user
--prune-native
--pch / --no-pch
--no-cache / --clear-cache / --ephemeral
--locked / --frozen         # sin deps: no-op; con deps: error F9
--keep
--help
```

Comportamiento:

- Archivo o proyecto; sin target, `cwd`.
- `output` del manifiesto: `exe`, `c`, `obj`, `static`, `shared`.
  - `exe`: enlaza runtime y produce ejecutable.
  - `c`: bundle C únicamente.
  - `obj`: `cc -c` del bundle, sin link.
  - `static`: `ar rcs lib<output_name>.a` (con `-fPIC` si el perfil lo pide).
  - `shared`: `cc -shared -fPIC -o lib<output_name>.so`.
- `--test`: usa `testgen` y enlaza el runner de tests.
- `--json`: eventos; en error, `{"event":"diagnostic",...}`.
- Caché: ver §8. `--no-cache` desactiva lectura/escritura.
- C glue: `.c` en `c/` y en `lib/*/c/`, orden determinista, include dirs.
- Sin `main` de usuario si `--test`/`--library`; error claro si glue define `main`.
- `--out` y `--output` son sinónimos; `--out value` y `--out=value`.

### 7.2 `psc run`

```bash
psc run [SCRIPT|TARGET] [-- args...]
psc run . --profile=release -- arg1 arg2
psc run hello.pengu a b        # forwards a b
```

- Sin target: proyecto.
- Con `.pengu`: script; el `main` del script es el entry.
- Compila con la misma ruta que `build`, usando caché.
- `stdin` heredado; stdout/stderr heredados; exit code real.
- `--test`: ejecuta tests en vez del main.
- `--keep`: deja `build/<name>_run/`.
- `--no-cache`, `--clear-cache`, `--ephemeral`.
- `--` separa args del programa; también acepta args tras el script si no
  empiezan por `-` (paridad stage0).

### 7.3 `psc expand`

- Igual que F5, más `--output`/`-o`, `--verbose`, `-D`, `--prune-types`,
  `--no-line-markers`, `--dce-scope`, `--prune-native`.
- Nunca invoca `cc` ni lee runtime.

### 7.4 `psc check`

```bash
psc check                    # proyecto/cwd
psc check src/ app.pengu     # archivos o directorios
psc check --json
```

- **No genera C, no pide runtime, no invoca cc.**
- Proyecto: resuelve manifiesto/entry y checkea el grafo de imports.
- Archivos: checkea cada uno con sus imports.
- `--json`: diagnósticos JSON.
- `--deny-deprecated`, `-D`, `--profile`, `--entry`.
- Exit 1 si hay errores; 0 si sólo warnings.

### 7.5 `psc test`

```bash
psc test [--profile=debug|release] [--json] [--watch] [--filter=REGEX]
```

- Construye con `--test`; ejecuta el runner integrado (no un `main` normal).
- Resume `passed/failed/skipped` y nombres.
- Exit 0 si todos pasan; 1 si alguno falla; 2 si el proyecto no compila.
- `--json`: un objeto por test + `summary`.
- `--watch`: re-ejecuta al cambiar imports.
- `--filter`: opcional F6 (paridad stage0 no lo tiene; se documenta).
- Sin tests: exit 0 con `0 tests` (no error).

### 7.6 `psc init` / `psc new`

`init`:

```bash
psc init NAME [--type=exe|c|obj|static|shared]
             [--template=exe|cli|pengu-lib|cbind]
             [--links=a,b] [--cc=gcc] [--output-name=NAME]
             [--force]
```

`new` es la forma template-first:

```bash
psc new exe NAME
psc new cli NAME
psc new pengu-lib NAME
psc new cbind NAME
```

Genera:

- `pengu.toml` con `[project]`, `[build]`, `[assets]`, `[dependencies]`,
  `[profiles.debug|release|small]`.
- `src/main.pengu` (exe/cli) con `main` y un `println`.
- `pengu/<name>.pengu` (pengu-lib) o `<name>.d.pengu` (cbind).
- `lib/`, `include/`, `c/`, `assets/` cuando aplica.
- `.gitignore` con `build/`.
- No sobrescribe directorio no vacío sin `--force`.
- `--type` y `--template` incompatibles: error 2.
- `cbind` genera `declare` de ejemplo y `links`.

### 7.7 `psc clean`

- Resuelve manifiesto; borra `<base>/<build_dir>`.
- Nunca borra fuera del proyecto; rechaza `..`/rutas absolutas fuera.
- `--dry-run` opcional F6 (recomendado para seguridad).
- No borra `src/`, `lib/`, `c/`, `assets/`.
- Exit 0 aunque no exista `build/`.

### 7.8 `psc doctor`

Comprueba:

- Versión de `psc`, stage (stage1/stage2/stage3).
- `gcc`, `clang`, `tcc` y versión de cada uno.
- `libpengu_runtime.a`, `pengu_runtime.h`, `std/`, `std_c/`.
- `PENGU_*` efectivas.
- Build dir escribible, cache dir escribible.
- `git` (informativo).
- Proyecto: manifiesto, entry, perfiles.

Salida humana + `--json`. Exit 0 si todo lo obligatorio está; 1 si falta algo
que impide compilar.

### 7.9 `psc gc`

- Limpia `PSC_CACHE_DIR` / `$XDG_CACHE_HOME/pengu/psc` / `~/.cache/pengu/psc`.
- `--all`, `--max-age=N` (días, default 30), `--verbose`, `--json`.
- Sólo borra entradas dentro de la raíz de caché resuelta; nunca sigue
  symlinks fuera.
- Informa bytes liberados.

### 7.10 `psc watch`

```bash
psc watch SCRIPT [--cc=...] [--keep] [-D...]
```

- Ejecuta el script.
- Observa entry + imports resueltos + manifiesto + runtime.
- Polling 300 ms; re-ejecuta al cambiar mtime/size.
- Ctrl-C sale limpio (130).
- No usa inotify.

### 7.11 `psc eval`

```bash
psc eval "1 + 2"
psc eval "calling spark.range with 0, 5"
```

- Envuelve en un `main` temporal, compila, ejecuta e imprime el resultado.
- Caché por expresión + flags.
- `--cc`, `--no-cache`, `-D`.
- Si la expresión no es un valor, error de compilación con diagnóstico.

### 7.12 `psc time`

- Igual que `run`, pero mide fases: parse, sema, codegen, cc, link, run.
- Tabla humana; `--json` opcional.
- No altera el binario; `--keep` para inspeccionar.

### 7.13 `psc benchmark`

- Casos nativos: `benches/*.pengu` con metadatos en `benches/cases.toml`
  (nuevo) o tabla embebida.
- `--repeat=N` (default 3), `--only=NAME`, `--csv=PATH`.
- Mide build, run (mejor de N), tamaño del artefacto.
- Sin baselines C/Rust/Zig en F6; se reportan como `not-run`.
- Si no hay `benches/`, error claro.

### 7.14 `psc fmt`

```bash
psc fmt [paths...] [--check] [--diff] [--stdin] [--verbose]
        [--indent=N] [--tabs] [--config=PATH]
```

- Archivos/directorios recursivos `.pengu`.
- Omite archivos con `@generated` en las primeras líneas.
- Idempotente: `fmt(fmt(x)) == fmt(x)`.
- `--check`: no escribe; exit 1 si cambiaría.
- `--diff`: unified diff.
- `--stdin`: stdin -> stdout; `--check` sale 1 si cambiaría.
- `.pengufmt.toml`: `indent`, `tabs`, `blank_lines_max`.
- Preserva strings/triples/comentarios; no reformatea dentro de `antiquus`.
- Paridad con `pengu_lsp.formatting` mediante goldens.

### 7.15 `psc doc`

```bash
psc doc [--output=DIR] [--entry=PATH]
```

- Genera Markdown por módulo en `<output>` (default `docs/api`).
- Extrae `##` comments, firmas, tipos, constantes, ejemplos.
- Índice `docs/api/README.md`.
- HTML de búsqueda opcional (`--html`), no obligatorio F6.
- Determinista: orden de módulos/símbolos estable.
- No modifica fuentes.

### 7.16 `psc assets`

```bash
psc assets [--list] [--force]
```

- `[assets] dir/module/embed/exclude` del manifiesto.
- `--list`: nombre, bytes, constante generada, modo.
- Sin `--list`: genera `src/<module>.pengu` y `build/<module>_assets.c`.
- `embed`: arrays C + API PenguScript (`bytes`, `text`, `len`).
- `disk`: lectura en runtime desde `assets/`.
- Nombres estables (sanitize, colisiones -> error).
- Integración con `build`: el `.c` generado se añade al link.
- Determinista: orden por path relativo; hashes estables.

### 7.17 `psc metadata` / `psc tree`

- `metadata`: JSON con nombre, versión, entry, output, perfiles, flags, assets,
  dependencias (vacías).
- `tree`: árbol legible; `--json` para grafo.
- Sin deps: funciona. Con deps no vacías: error F9.
- Esquema estable `schema_version: 1`.

### 7.18 `psc selftest`

- Dev-only: exige checkout (`psc/tests`, `tests/`, `pengu_project.py`).
- Ejecuta la suite del compilador; en F6 delega en el runner existente
  (`python -m pytest`) **sólo** si está disponible, o falla con instrucciones.
- `--smoke`; no forma parte del build.
- No se usa en CI de usuario.

### 7.19 Stubs de fases posteriores

```text
psc add ...        -> F9 (package manager)
psc remove ...     -> F9
psc upgrade ...    -> F9
psc verify ...     -> F9
psc vendor ...     -> F9
psc update ...     -> F9
psc lsp ...        -> F8
psc bind ...       -> F10
psc build --target -> F11
```

Todos: help, flags reconocidas, error 2 con fase.

---

## 8. Caché

### 8.1 Ubicación

Orden:

1. `PSC_CACHE_DIR` si está definido.
2. `$XDG_CACHE_HOME/pengu/psc`.
3. `~/.cache/pengu/psc` (Linux/macOS), `%LOCALAPPDATA%` (Windows).

Estructura:

```text
<root>/v1/<key>/
  meta.json        # schema, key, timestamps, flags, artifact
  bundle.c
  artifact         # ejecutable/objeto/lib
```

### 8.2 Clave

`sha256` con `std.digest.sha256_hex` sobre:

- versión de PSC y hash del binario (`sha256_file`).
- path/tamaño/mtime de entry y de **todos** los imports resueltos (o su
  contenido, para robustez).
- manifiesto efectivo (no comentarios).
- perfil + cflags/ldflags/defines/links/include dirs.
- `--cc`/target compiler/strict/release-unsafe.
- hash de `libpengu_runtime.a`, `pengu_runtime.h`, `std/` usados.
- tipo de salida (`exe`/`c`/...).
- `--test`/`--library`.
- args de `run` no entran en la clave del binario; la expresión de `eval` sí.

### 8.3 Escritura

- Construir en `build/.tmp-<pid>/` y renombrar atómicamente.
- `meta.json` al final; una entrada sin meta se considera incompleta y se
  reconstruye.
- Nunca cachear fallos.
- Permisos `0700` en el directorio de caché.
- Lock por entrada con `flock`/`O_EXCL`; stale > 10 min se recupera.
- `--no-cache`: no lee ni escribe.
- `--clear-cache`: vacía la entrada/raíz antes de compilar.
- `--ephemeral`: temp dir, no toca caché.

### 8.4 Invalidación

- Cualquier cambio en entry/imports/manifiesto/compilador/runtime invalida.
- Cambiar de perfil/cc/define invalida.
- `--test` y `--library` son claves distintas.
- `gc` borra por edad o todo.

### 8.5 Rendimiento objetivo

- Cache hit de `run`/`eval`: <100 ms en Linux (sin contar el proceso hijo).
- Cache miss no debe ser más lento que F5 (>10% aceptable).
- `psc build` de proyecto cacheado: reutiliza bundle si la clave coincide.

---

## 9. Manifiesto F6

Extender el parser actual (`std.toml`) con:

```toml
[project]
name = "app"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"            # exe | c | obj | static | shared
output_name = "app"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
c_dir = "c"
build_dir = "build"
includes = ["mylib.h"]
links = ["m"]
lib_dirs = []
include_dirs = []
cflags = ["-O2", "-Wall"]
ldflags = []
defines = []
cc = "gcc"
strict_c99 = false
target_compiler = "gcc"
release_unsafe = false

[assets]
dir = "assets"
module = "arca"
embed = true
exclude = ["*.tmp"]

[profiles.debug]
cflags = ["-g", "-O0"]
defines = ["DEBUG"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG"]
defines = ["NDEBUG"]

[profiles.small]
cflags = ["-Os", "-fno-unwind-tables"]
defines = ["NDEBUG", "PENGU_SIZE_OPT"]

[dependencies]
# no soportado hasta F9; si no está vacío -> error F9
```

Reglas:

- `output` inválido -> error E_CONFIG con lista válida.
- `dependencies` no vacío -> error “planned F9”, no warning.
- `pengu.json`/`pengu.yaml`: error “use pengu.toml (F9 adds compatibility)”,
  salvo que en el futuro se apruebe D4 alternativa.
- `assets` se valida aunque `assets` no se use en build.
- Perfiles desconocidos: error; `debug/release/small` por defecto.
- `build_dir` relativo al proyecto; absoluto permitido pero `clean` lo valida.

---

## 10. Procesos, seguridad y portabilidad

### 10.1 `proc`

- `spawn(argv, cwd, env, inherit_stdin, capture)`.
- Sin `system()`/shell para cc, git, tests, binarios de usuario.
- `run` hereda stdin/stdout/stderr; `build` captura stderr para diagnósticos.
- Decodifica wait status: exit code real, señal -> 128+signal.
- `--verbose`: imprime argv con quoting informativo, no ejecuta shell.
- Timeout opcional para `doctor`/`git`; no para `run`/`test`.
- Linux/macOS POSIX; Windows en F6 best-effort (CreateProcess) o error
  documentado hasta F11.

### 10.2 Seguridad

- `clean`: resolver path, comprobar que está dentro de `base_dir`, no seguir
  symlinks; `rm -rf` sólo del build dir validado.
- `gc`: root de caché resuelto; no borrar fuera; no seguir symlinks.
- `fmt`: no escribir si el archivo es symlink fuera del proyecto sin `--force`.
- `assets`: nombres sanitizados; colisiones -> error; no path traversal.
- `doc`: salida dentro del proyecto o ruta explícita; no sobrescribir fuentes.
- `init`: no sobrescribir no vacío sin `--force`.
- `--json`: nunca mezclar progreso humano en stdout.

---

## 11. Limpieza de F5 (obligatoria antes de F6)

1. **Paths:** eliminar el no-op de `free_paths`; copiar profundamente al cruzar
   `cp_normalize`/`getcwd`; test de `psc build` sin `PENGU_*` desde el checkout y
   desde un proyecto fuera.
2. **Check puro:** `psc check` no debe escribir bundle ni resolver toolchain C.
3. **Proc:** reemplazar `rites.exec` por argv; `run` conserva stdin y exit.
4. **Parser:** `--out value` y `--out=value`; tests de flags.
5. **Version:** `0.6.0 (F6)`.
6. **Bootstrap:** F6 no puede romper stage1→stage4; el job debe seguir pasando.

---

## 12. Tests y calidad

### 12.1 Unitarios/golden

- Parser de args: cada flag, `--`, valores, errores, help.
- Help: snapshot de `psc --help` y de cada comando (incluidos stubs).
- JSON: esquema y una línea por evento.
- Cache: clave estable, hit/miss, invalidación, corrupción, concurrencia.
- `fmt`: goldens de entrada/salida, idempotencia, `--check`/`--diff`/stdin.
- `doc`: snapshot Markdown de un proyecto fixture.
- `assets`: embed/disk, nombres, exclusión, colisiones, determinismo.
- `init`: cada template, `--force`, output types, TOML exacto.
- `clean`/`gc`: seguridad de rutas y symlinks.

### 12.2 Integración

- `init` → `build` → `run` → `test` → `clean` en un proyecto temporal.
- `fmt --check` en el repo (debe pasar tras formatear).
- `doc`/`assets` sobre fixtures.
- `doctor` con runtime presente/ausente.
- `watch`: modificar archivo y observar segunda ejecución (con timeout).
- `eval`, `time`, `benchmark` con casos pequeños.
- Paridad con stage0 para `fmt`, `doc`, `init`, `check`, `test`, `build`
  (si stage0 está disponible).

### 12.3 Regresión

- F1–F5 verdes.
- Bootstrap con punto fijo (`psc/tools/bootstrap.py`).
- Preflight gcc/clang/TCC.
- ASan/UBSan del self-compile y de un proyecto.
- Corpus 66 con el driver (si aplica).
- Fuzz: args, manifiesto, formatter, assets.

### 12.4 CI

- Job `psc-cli` Linux: build stage1, tests F6, `init/build/run/test/clean`,
  `fmt --check`, `doc`, `assets`, `doctor`, `gc`.
- Job `psc-selfhost` existente sigue.
- Nightly: bootstrap + F6 completo + ASan.
- Matriz opcional macOS; Windows best-effort.

### 12.5 Criterios de rendimiento

- `psc --help` < 50 ms.
- `psc build` cache hit < 300 ms (sin cc).
- `psc run` cache hit < 100 ms + hijo.
- `psc fmt` 1k líneas < 100 ms.
- Sin regresión >10% en bootstrap.

---

## 13. Fases y estimación

| Fase | Contenido | Estimación |
|---|---|---:|
| F6.0 | Deuda F5: paths, check puro, proc, version | 1 semana |
| F6a | CLI framework: args/help/context/registry/JSON/exit | 1 semana |
| F6b | Caché + `gc` + `doctor` + `clean` | 1.5–2 semanas |
| F6c | `build/run/expand/check` flags completas, tipos de salida, glue | 2 semanas |
| F6d | `init/new/metadata/tree` + stubs F9/F8/F10 | 1 semana |
| F6e | `test/watch/eval/time/benchmark` | 2 semanas |
| F6f | `fmt/doc/assets` | 2.5 semanas |
| F6g | Tests, CI, docs, fuzz, rendimiento, bootstrap | 1.5 semanas |
| **Total** | | **11–13 semanas** |

Timebox sugerido: si `fmt`/`doc`/`assets` se desbordan, se cierran en F6.5 con
aprobación, pero **el resto de F6 no se retrasa**.

---

## 14. Criterios de aceptación

F6 se considera cerrado cuando:

1. `psc --help` lista todos los comandos del §3.1, con stubs marcados.
2. Cada comando implementado tiene `--help`, tests y docs.
3. `init` crea y `build/run/test` funcionan en los 4 templates.
4. `fmt --check` es idempotente y pasa en el propio repo.
5. `doc` genera Markdown determinista para `std/` y un proyecto.
6. `assets --list` y generación embed/disk funcionan y se enlazan.
7. `test` devuelve 0/1 correctos y JSON válido.
8. `watch` re-ejecuta al cambiar un import.
9. `eval`, `time`, `benchmark` funcionan sin Python en el camino normal.
10. `build/run` usan argv (sin shell) y soportan paths con espacios.
11. Caché acierta, invalida y `gc` limpia sin tocar fuera.
12. `doctor` detecta runtime/std/cc/TCC.
13. `psc build` sin `PENGU_*` funciona desde el checkout y con las variables.
14. F1–F5 y bootstrap con punto fijo siguen verdes.
15. Preflight gcc/clang/TCC y ASan siguen verdes.
16. No hay comandos que “simulan” éxito: los no implementados fallan con fase.
17. El árbol queda limpio y el commit final está en `main` (sin push).

---

## 15. Riesgos y mitigaciones

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| Formatter no alcanza paridad | Alta | Medio | port 1:1 + goldens + idempotencia; timebox |
| Docs/assets divergen de stage0 | Media | Medio | usar stage0 como oráculo; snapshots |
| Caché incorrecta (stale) | Media | Alto | clave completa; tests de invalidación; borrar si meta falta |
| Proceso sin shell rompe Windows | Media | Medio | POSIX F6; Windows documentado/F11 |
| Scope creep a dependencias | Alta | Alto | stubs F9; no lockfile |
| Regresión del bootstrap | Media | Alto | gate stage1→stage4 en cada PR |
| `clean`/`gc` borran de más | Baja | Crítico | validación de raíz, tests de symlink, `--dry-run` |
| `fmt` reescribe strings | Media | Alto | no tocar strings/triples/antiquus; goldens |
| JSON inestable | Baja | Medio | schema_version + snapshots |
| TCC diverge | Media | Medio | gate TCC; build con TCC |

---

## 16. Archivos previstos

```text
psc/src/main.pengu                       (reducir a dispatch)
psc/src/psc/cli/*.pengu                  (nuevo)
psc/src/psc/cmd/*.pengu                  (nuevo/refactor)
psc/src/psc/cache/*.pengu                (nuevo)
psc/src/psc/fmt/*.pengu                  (nuevo)
psc/src/psc/docgen/*.pengu              (nuevo)
psc/src/psc/assets/*.pengu              (nuevo)
psc/src/psc/os/proc.pengu               (nuevo)
psc/src/psc/project/output_types.pengu  (nuevo)
psc/src/psc/driver/*.pengu              (refactor)
psc/tools/bootstrap.py                   (sin cambios funcionales)
psc/tests/fixtures/f6/**                 (nuevo)
tests/psc/test_f6_*.py                   (nuevo)
psc/docs/CLI.md                          (nuevo)
docs/selfhost/CLI.md                     (nuevo)
.github/workflows/ci.yml                 (job psc-cli)
.github/workflows/nightly.yml            (F6 nightly)
```

---

## 17. Ejemplos de uso (contrato)

```bash
psc init my_game
cd my_game
psc run
psc test
psc fmt src/
psc doc
psc assets --list
psc build --profile=release --json
psc doctor --json
psc clean --dry-run
psc gc --all
psc eval "1 + 2"
psc time src/main.pengu
psc watch src/main.pengu
psc benchmark --only=fib_40 --repeat=5
psc metadata > metadata.json
```

---

## 18. Migración y compatibilidad

- Los comandos y flags de F5 se mantienen; `--out=value` sigue funcionando.
- `--out value` se añade.
- `psc check` de archivo conserva salida/exit; el de proyecto deja de generar
  bundle (mejora).
- El manifiesto F5 sigue siendo válido; los campos nuevos son opcionales.
- `pengu.toml` con `dependencies` no vacío falla con F9 (antes se ignoraba).
- `psc version` cambia a `0.6.0 (F6)`.
- Los stubs nunca existieron antes; no rompen nada.

---

## 19. Preguntas para aprobar

Las decisiones D1–D15 ya llevan una recomendación. Para arrancar necesito:

1. ¿Aprobado el alcance del §3.1, con dependencias/LSP/bind/cross como stubs?
2. ¿Aprobada la caché en F6 (D2)?
3. ¿Aprobados los tipos `obj/static/shared` (D3)?
4. ¿Aprobado TOML-only (D4)?
5. ¿Aprobado portar `fmt/doc/assets` completos (D5–D7)?
6. ¿Aprobado el timebox de 11–13 semanas y el cierre F6.5 si `fmt/doc/assets`
   se desbordan?

Si hay cambios, los incorporo al plan antes de tocar código.
