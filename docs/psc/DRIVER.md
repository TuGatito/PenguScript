# Driver `psc` (F5)

`psc build`, `psc run` y `psc expand` compilan un archivo `.pengu` o un proyecto
con `pengu.toml`, enlazan `libpengu_runtime.a` y ejecutan el binario.

## Manifiesto

```toml
[project]
name = "app"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"          # exe | c
output_name = "app"

[build]
src_dir = "src"
lib_dir = "lib"
include_dir = "include"
build_dir = "build"
cc = "gcc"              # opcional; --cc lo sobreescribe
links = ["m"]
cflags = ["-O2"]
defines = ["FEATURE"]

[profiles.release]
cflags = ["-O2", "-DNDEBUG"]
```

`dependencies` se resuelve en F9 (local/git, lock y vendor). Sólo `pengu.toml`; YAML/JSON se rechazan.

## Comandos

```bash
psc build .                         # proyecto; build/<output_name>
psc build src/main.pengu            # archivo suelto
psc build . --cc=tcc --out=app      # compilador y salida explícitos
psc build . --profile=release --verbose
psc run . -- arg1 arg2              # compila y ejecuta; propaga el exit code
psc expand . --out=bundle.c         # sólo C, sin invocar cc
psc check .                         # checker + codegen del proyecto (sin cc)
```

Opciones: `--profile=debug|release`, `--cc=NAME`, `--out=PATH`,
`--strict-c99`, `--release-unsafe`, `--verbose`, `--target=TRIPLE`, `--help`.

`--target wasm` selecciona `wasm32-unknown-emscripten`: usa `emcc`/`emar`,
busca el runtime en `build/wasm/lib` (o `PENGU_RUNTIME_CROSS`), produce
`app.html`/`app.js`/`app.wasm` y ejecuta con Node en `run`/`test`.

## Rutas

Orden de búsqueda del runtime/std:

1. `PENGU_RUNTIME_ARCHIVE`, `PENGU_LIB_DIR`, `PENGU_INCLUDE_DIR`,
   `PENGU_STD_DIR`, `PENGU_RUNTIME_CROSS`.
2. El checkout que contiene `std/` y `build/lib/` o `build/wasm/lib/`.
3. El directorio de trabajo actual (subiendo hasta la raíz del checkout).

En Linux **TCC es obligatorio** para el gate de F5; `psc run` puede usar
`--cc=tcc` para el camino rápido.

## Códigos de salida

- `0`: éxito.
- `1`: error de compilación/checker/enlazado.
- `2`: uso incorrecto de la CLI.
