# Build, check y caché

Cómo `pengu` convierte un proyecto en un binario, qué se cachea y cómo se
depuran los errores del backend Rust.

## Pipeline

```
main.pengu / lib.pengu
  → parse_program        (pengu-syntax)
  → lower_program        (pengu-hir, fusiona std y paquetes)
  → check_crate          (pengu-types)
  → check_ownership_with (pengu-check: movimientos y préstamos)
  → lower_crate          (pengu-lir)
  → generate             (pengu-codegen)
  → Cargo                (target/pengu/)
```

`pengu check` ejecuta las cuatro primeras etapas y **no** genera Rust ni llama a
Cargo: sirve para validar un proyecto en milisegundos o dentro de un editor.

## `pengu check`

```
pengu check                 # analiza main.pengu/lib.pengu del proyecto
pengu check archivo.pengu   # analiza un archivo concreto
pengu check --watch         # reanaliza al cambiar *.pengu o Tome.toml
```

Sale 0 si no hay errores, 1 si hay diagnósticos y 2 si el uso es incorrecto.
No crea `target/`.

## `pengu build`, `run`, `test`

`build` emite la crate en `target/pengu/` (`src/main.rs`, `Cargo.toml`,
`build.rs`, `sourcemap.json`) y compila con Cargo. `run` compila y ejecuta el
binario; `test` ejecuta los `@@test` generados.

Además de los archivos generados, `target/pengu/cache.json` guarda:

```json
{"version": 1, "fingerprint": "…", "bin_name": "demo"}
```

La caché solo se considera válida si el fingerprint SHA-256 coincide y el
binario existe. Cuando es válida, `build` responde sin invocar a Cargo y `run`
ejecuta el binario directamente.

## Fingerprint

El fingerprint cubre todas las entradas que afectan al Rust generado:

- la versión del formato de caché y la versión de `pengu-build`;
- `Tome.toml`, `main.pengu` o `lib.pengu`;
- el `lib.pengu`/`main.pengu` de cada paquete del lock;
- todas las fuentes de `std/` embebidas en `pengu-std`.

Cualquier cambio en esos archivos invalida la caché y obliga a recompilar; un
cambio de hora, de ruta o de comentarios en el código generado no.

`emit` solo reescribe los archivos cuyo contenido cambió, así que el
fingerprint interno de Cargo se mantiene y un segundo `build` tampoco
recompila.

## `--watch`

`pengu check --watch`, `build --watch`, `run --watch` y `test --watch` repiten
la acción cuando cambia un `.pengu` o `Tome.toml`. La detección es por polling
de mtime + tamaño cada 250 ms (sin dependencias): suficiente para proyectos
locales y sin inotify.

## Errores del backend

Los diagnósticos de `rustc` se remapean a spans de PenguScript usando
`sourcemap.json`. La nota del diagnóstico muestra la línea del Rust generado y
el texto original de `rustc`; si el error está en código generado sin span de
origen, se informa como `PGS-E2014` con la nota correspondiente.

## Ejemplos

`examples/` contiene programas completos que usan la stdlib real. El test
`crates/pengu-build/tests/examples.rs` compila y ejecuta cada uno, y exige que
estén formateados y sin avisos del linter; un cambio incompatible en `std` los
rompe antes de publicar.
