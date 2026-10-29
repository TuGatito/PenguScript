# `psc` — CLI F6

`psc` es el compilador y driver de PenguScript. Esta página resume la
superficie estable de F6.

## Comandos

```text
psc lex | parse | ast | check | emit-c
psc build | run | expand
psc init | new | clean | doctor | metadata | tree
psc test | watch | eval | time
psc fmt | doc | assets
psc gc | benchmark | selftest
psc version | help
```

`--target` está disponible en `build`, `run`, `test`, `check`, `emit-c` y
`expand`. `wasm`, `wasm32`, `emscripten` y `wasm32-unknown-emscripten` son
equivalentes; `wasm32-wasi` se rechaza con un mensaje explícito.

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
psc remove NAME [--keep-files]
psc update [--trust] [--no-build]
psc upgrade NAME [--version=V] [--branch=B]
psc verify [--verbose]
psc vendor [--verbose]
psc tree [--json]
psc metadata [--json]
psc build [--locked|--frozen]
```

- Fuentes: path local, `file://` o URL git. Las versiones son tags git.
- `add` instala en `lib/<name>`, resuelve transitivas y escribe `pengu.lock`.
- `build.pengu` sólo se ejecuta con `--trust` o `PENGU_TRUST_ALL=1`.
- `--locked` verifica el lock sin reescribirlo; `--frozen` además exige lock y
  restaura desde `vendor/` sin red.
- `verify` comprueba commit y SHA-256 del árbol.


## Build

```bash
psc build [TARGET] [opciones]
```

- `TARGET`: archivo `.pengu` o directorio de proyecto (default: cwd).
- `--profile=debug|release|small`, `--cc`, `--out`/`-o`, `--entry`/`-e`.
- `-D NAME[=VALUE]` repetible.
- `--test`, `--strict-c99`, `--release-unsafe`, `--verbose`, `--json`.
- `--target=wasm|wasm32-unknown-emscripten` (o `[build] target` en el manifiesto).
- Tipos de salida del manifiesto: `exe`, `c`, `obj`, `static`, `shared`.

`psc run` compila y ejecuta; propaga el exit code y acepta `-- args...`.
Con `--target wasm` ejecuta `node app.js`; sin Node imprime la ruta del HTML y
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
```

Ubicación: `PSC_CACHE_DIR`, `$XDG_CACHE_HOME/pengu/psc`, `~/.cache/pengu/psc`
o `/tmp/pengu-psc-cache`. `psc gc --all` la vacía.

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
psc fmt src/
psc fmt --check src/
psc fmt --stdin < file.pengu
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
