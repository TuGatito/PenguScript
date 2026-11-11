# `psc` — CLI F6

`psc` es el compilador y driver de PenguScript. Esta página resume la
superficie estable de F6.

## Comandos

```text
psc lex | parse | ast | check | emit-c
psc build | run | expand
psc init | new | clean | doctor | metadata | tree
psc test | debug | watch | eval | time
psc fmt | doc | assets
psc gc | benchmark | selftest
psc version | help
```

`--target` está disponible en `build`, `run`, `test`, `check`, `emit-c` y
`expand`. `wasm`, `wasm32`, `emscripten` y `wasm32-unknown-emscripten` son
equivalentes; `wasm32-wasi` se rechaza con un mensaje explícito.

## Familia de backend (F1)

`build`, `run`, `test` y `emit-c` aceptan `--backend=c|cpp` (por defecto `c`;
`cc` es sinónimo de `c`). Con `cpp` el driver elige `g++`/`clang++` (o el `…-g++`
equivalente de un toolchain prefijado), compila con `-std=c++20`, ignora los
`-std=` del manifiesto (describen el lenguaje C) y escribe
`<build>/bundle.cpp` en lugar de `bundle.c`. El runtime (`pengu_runtime.h` y
`libpengu_runtime.a`) se sigue compilando como C y se enlaza con linkage C,
así que un binario construido en C++ ejecuta la misma std.

`psc test . --backend=cpp` compila la suite completa (todo `std/`, no solo el
cierre del compilador) con el emisor C++: es el gate que mantiene compilable
cada módulo.

`emit-c --dump-index-types` añade a la salida, por stderr, una línea
`archivo:línea<TAB>receptor<TAB>resultado` por cada indexación (`at`). Con
`--backend=cpp` permite medir qué `s at i` siguen siendo `string` y cuáles van
a `char` en el dialecto nuevo.

## Bind (F10)

```bash
psc bind HEADER [--prefix P] [--links L...] [--ignore S...]
                [--include-paths D...] [--output PATH|-]
                [--define NAME[=V]] [--cpp-flags FLAGS]
                [--system-includes] [--preprocessed FILE.i]
                [--no-blank-extensions] [--no-cpp]
                [--auto-import[=DIR]] [--no-comments]
                [--helper-version] [--print-helper]
```

`psc bind` localiza `pengu-bind` en `$PENGU_BIND`, junto a `psc`,
`libexec/pengu`, `$PENGU_HOME` o `PATH`. El helper por defecto es el binario C
construido por `tools/build_bind.sh` contra **libclang**; no requiere Python.

## Release

```bash
tools/build_bind.sh
tools/release.sh
```

`tools/release.sh` usa `build/psc` y `build/pengu-bind` y genera portable/FHS,
`release.toml` y `SHA256SUMS` sin Python.

Genera portable y FHS, `release.toml` y `SHA256SUMS`. El paquete incluye
`psc`, `pengu-bind`, `std/`, headers, runtime y stubs.

## Dependencias (F9)

Sólo `pengu.toml`; `pengu.yaml`, `pengu.yml` y `pengu.json` se rechazan.

```bash
psc add SOURCE [--name=NAME] [--branch=B] [--tag=T] [--version=CONSTRAINT]
                [--trust] [--no-build] [--rebuild]
psc remove NAME [--keep-files]
psc update [--trust] [--no-build]
psc upgrade NAME [--version=V] [--branch=B] [--trust]
psc verify [--verbose]
psc vendor [--verbose]
psc tree [--json]
psc metadata [--json]
psc build [--locked|--frozen]
```

- Fuentes: path local, `file://`, URL git (GitHub, GitLab, Codeberg,
  self-hosted) o `scp`-style. Se aceptan `#ref` y `/-/tree/<ref>` (GitLab);
  el ref se guarda como `branch`/`tag`. Las versiones publicadas son tags git.
- `add` instala en `lib/<name>`. Si el paquete declara `[project] import` y no
  se pasó `--name`, usa ese nombre: `psc add https://github.com/TuGatito/raylib-pengu`
  queda importable como `import raylib` (no como `raylib-pengu`).
- El layout del paquete (`[build] src_dir`, `include_dir`, `lib_dir`) se
  respeta: el driver añade `<paquete>/<src_dir>` a módulos,
  `<paquete>/<include_dir>` a `-I` y `<paquete>/<lib_dir>` a `-L`.
- `add` resuelve transitivas, valida constraints, escribe `pengu.lock` y es
  transaccional: si falla la instalación restaura `pengu.toml` y no deja un
  paquete nuevo a medias.
- `build.pengu` de cada dependencia se ejecuta sólo con `--trust` o
  `PENGU_TRUST_ALL=1`; sin trust se omite con un aviso. `--no-build` no lo
  ejecuta. `--rebuild` fuerza la ejecución aunque el paquete ya exista.
- `update` reinstala respetando el manifiesto y ejecuta builds con `--trust`.
- `upgrade` cambia versión/rama y reconstruye con `--trust`.
- `--locked` verifica el lock sin reescribirlo; `--frozen` además exige lock y
  restaura desde `vendor/` sin red. Ambos fallan con `E0061: pengu.lock is out
  of date` si el lock no coincide con el manifiesto o el árbol instalado.
- El lock es schema 2 e incluye `target`; los locks viejos (`targets = [...]`)
  se siguen leyendo. `verify` comprueba commit, SHA-256, constraints del lock y
  del manifiesto, y paquetes que falten.
- `vendor` copia también las librerías nativas de `<paquete>/<lib_dir>`
  (`.a/.so/.dylib/.dll/.lib`), no sólo el código PenguScript.


## Build

```bash
psc build [TARGET] [opciones]
```

- `TARGET`: archivo `.pengu` o directorio de proyecto (default: cwd).
- `--profile=debug|release|small`, `--cc`, `--out`/`-o`, `--entry`/`-e`.
- `-D NAME[=VALUE]` repetible.
- `--test`, `--exe`, `--strict-c99`, `--release-unsafe`, `--verbose`, `--json`.
- `--backend=c|cpp` (también en `run`, `test` y `emit-c`; ver «Familia de backend»).
- `--split-codegen` emite `bundle.h`, `core.c` y una unidad por módulo, y las
  compila por separado; `--jobs=N` limita cuántas compilaciones C corren a la
  vez (solo `exe` nativo). Es opt-in: el camino de un único TU suele ser más
  rápido con la cabecera actual.
- `--target=wasm|wasm32-unknown-emscripten` (o `[build] target` en el manifiesto).
- Tipos de salida del manifiesto: `exe`, `c`, `obj`, `static`, `shared`.
- `--exe` fuerza el enlazado de un ejecutable aunque el manifiesto declare
  `output = "c"` (útil para compilar un ejemplo suelto de un binding).

`psc run` compila y ejecuta; propaga el exit code y acepta `-- args...`.
Aunque el manifiesto sea una librería (`output = "c"`/`"static"`), `run` fuerza
un ejecutable. Un archivo `.pengu` dentro de un proyecto conserva el `c/` glue C
del manifiesto (por ejemplo `raygui_impl.c`).
Con `--target wasm` ejecuta `node app.js`; si Node no puede crear el canvas
(raylib web) o se pasa `--browser`, sirve el HTML por HTTP y lo ejecuta en
Chromium/Chrome headless. Sin Node ni navegador imprime la ruta del HTML y
devuelve 2.
`psc expand` emite el bundle C sin invocar `cc`.
`psc check` de proyecto valida checker + codegen sin escribir bundle.

## Caché

`run`, `eval` y los builds de proyecto usan una caché content-addressed:

```bash
psc run script.pengu
psc run script.pengu --no-cache
psc run script.pengu --clear-cache
psc gc --all
psc build . --target=aarch64-unknown-linux-gnu
psc build . --target=wasm32-unknown-emscripten
```

Ubicación: `PSC_CACHE_DIR`, `$XDG_CACHE_HOME/pengu/psc`, `~/.cache/pengu/psc`
o `/tmp/pengu-psc-cache`. `psc gc --all
psc build . --target=aarch64-unknown-linux-gnu
psc build . --target=wasm32-unknown-emscripten` la vacía.

## Proyecto

```bash
psc init my_app
psc init my_lib --template pengu-lib
psc new cli my_cli
psc clean --dry-run
psc metadata
psc tree
psc doctor --json
```

`init/new` escriben `pengu.toml` (TOML canónico). `pengu.yaml`/`pengu.json`
no se aceptan en F6.

## Tests y desarrollo

```bash
psc test
psc test --watch
psc test . --coverage          # gcov mapeado a líneas .pengu
psc test . --sanitize=address  # ASan (undefined | thread)
psc debug .                    # build con DWARF + gdb
psc debug . --llvm -- --flag   # lldb y argumentos del programa
psc fmt src/
psc fmt --check src/
psc fmt --stdin < file.pengu
psc migrate src/               # F2: sintaxis C++ mecánica
psc migrate --check src/
psc migrate --diff src/
psc doc
psc assets --list
psc assets
psc watch src/main.pengu --once
psc watch src/main.pengu --interval=300
psc doc --html
psc benchmark --only=f7_arith --repeat=3 --json
psc selftest --smoke
psc eval "1 + 2"
psc time src/main.pengu
```

`psc benchmark` y `psc selftest` son **dev-only** y requieren el checkout y
Python; no forman parte del camino de build de usuario.

### `psc migrate` (F2)

Migra a las grafías del dialecto C++ solo lo que es **mecánico** (mismo AST,
mismo código emitido en los dos backends):

| Antes | Después |
|---|---|
| `list of T` | `vector of T` |
| `slice of T` | `span of T` |
| `map of K to V` | `map of K, V` |
| `nasci` / `mori` / `imago` | `born` / `die` / `mirror` |
| `namespace` | `regnum` |

`--check` no escribe y sale con 1 si habría cambios; `--diff` muestra las
líneas afectadas; sin flags escribe in place. El comando es idempotente y no
toca comentarios, strings ni los `to` que no son separador de `map`
(`for i in 0 to 5`, `result of T to E`).

Lo que **no** hace, porque necesita semántica nueva o resolución de tipos:
`umap`/`set`/`uset`, la retirada de `derive`, los identificadores que pasan a
ser reservados (`result`, `span`, `set`, `map`, `unique`) y las firmas de la
FFI. Cada una tiene su fase.

## LSP

`psc lsp [--stdio|--tcp] [--host=HOST] [--port=PORT]` inicia el
servidor de lenguaje. Ver [`docs/LSP.md`](../LSP.md).

## Assets

El manifiesto configura:

```toml
[assets]
dir = "assets"
module = "arca"
embed = true
exclude = ["*.tmp"]
```

`psc assets` genera `src/<module>.pengu`, `build/<module>_assets.h`,
`build/<module>_assets.c` y un hash incremental; `build` los incluye y enlaza.
Usa arrays C o `.incbin` para assets >= `PENGU_ASSETS_INCBIN_THRESHOLD`
(default 1 MB); TCC usa el fallback portable.

## JSON

`--json` emite JSON Lines estable con `schema_version: 1` para
`build`, `test`, `doctor` y `gc`. Los errores van a stderr.

## Variables

- `PENGU_STD_DIR`, `PENGU_LIB_DIR`, `PENGU_INCLUDE_DIR`.
- `PSC_CC` / `PENGU_CC` para el compilador C.
- `PSC_CACHE_DIR` para la caché.
- `NO_COLOR`.

## Exit codes

- `0` éxito.
- `1` error de compilación/check/tests.
- `2` uso incorrecto, flag desconocido o comando de fase posterior.
