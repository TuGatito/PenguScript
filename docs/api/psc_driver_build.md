# psc.driver.build

> Source: `src/psc/driver/build.pengu`

psc/driver/build.pengu — driver mínimo: F3 + F4 + cc + link.

F5 no cachea, no resuelve dependencias y sólo soporta `pengu.toml` TOML.

---

### `BuildOptions`

> rune BuildOptions

```pengu
    target as string
    platform as Target
    target_explicit as bool
    profile as string
    cc as string
    out_path as string
    verbose as bool
    strict_c99 as bool
    release_unsafe as bool
    is_library as bool
    is_test as bool
    test_json as bool
    bundle_only as bool
    check_only as bool
    no_dce as bool
    prune_types as bool
    no_line_markers as bool
    prune_native as bool
    dce_scope_user as bool
    pch as bool
    compiler_path as string
    no_cache as bool
    clear_cache as bool
    ephemeral as bool
    locked as bool
    frozen as bool
    force_exe as bool
    defines as list of string
```

 Opciones de build.

 ## Memoria
 Strings owned; liberar con `free_options`.

### `BuildResult`

> rune BuildResult

```pengu
    ok as bool
    error as string
    artifact as string
    bundle_path as string
```

 Resultado de un build.

 ## Memoria
 Strings owned; liberar con `free_result`.

### `copy`

> **copy**(s: string) -> string

 Copia un string.

 ## Memoria
 Devuelve string owned.

### `free_strings`

> **free_strings**(xs: list of string) -> void

 Libera una lista de strings owned.

 ## Memoria
 Libera elementos y lista.

### `ends_with`

> **ends_with**(s: string, suffix: string) -> bool

 `true` si `s` termina en `suffix`.

 ## Memoria
 O(suffix); no asigna.

### `push_dir_hashes`

> **push_dir_hashes**(cparts: ref to list of string, dir: string) -> void

 Añade a la clave de caché el contenido de todos los archivos de un directorio.

 Los `include "..."`, los `.c` de `c_dir` y los headers locales cambian el
 artefacto pero no estaban en la clave: un header editado reutilizaba el
 binario viejo (bug 20).

 ## Memoria
 Libera los strings temporales.

### `current_dir`

> **current_dir**() -> string

 Directorio actual.

 ## Memoria
 Devuelve string owned.

### `find_manifest_root`

> **find_manifest_root**(start: string) -> string

 Busca el directorio con `pengu.toml` subiendo desde `start`.

 ## Memoria
 Devuelve string owned o `""`.

### `default_options`

> **default_options**() -> BuildOptions

 Opciones por defecto.

 ## Memoria
 Strings owned; liberar con `free_options`.

### `free_options`

> **free_options**(o: ref to BuildOptions) -> void

 Libera opciones.

 ## Memoria
 Libera strings.

### `free_result`

> **free_result**(r: ref to BuildResult) -> void

 Libera un resultado.

 ## Memoria
 Libera strings.

### `needs_threads`

> **needs_threads**(p: ref to SemaProgram) -> bool

 `true` si el programa importa `std.filum`.

 Es la misma condición que decide `-pthread`/`PENGU_ENABLE_THREADS`; si
 divergen, el runtime y el bundle no enlazan.

### `needs_js`

> **needs_js**(p: ref to SemaProgram) -> bool

 `true` si el programa usa la capa JS (`std.web.js`).

 Todos los módulos web importan `std.web.js`, así que comprobar su path es
 suficiente. Los programas sin JS no pagan `--js-library` ni exports extra.

### `emar_for`

> **emar_for**(cc: string) -> string

 Archivero para wasm: `emar` del mismo emsdk que `emcc`, o `emar` del PATH.

 ## Memoria
 Devuelve string owned.

### `wasm_unsupported`

> **wasm_unsupported**(p: ref to SemaProgram) -> string

 Módulo std no disponible en wasm: mensaje accionable, o `""`.

 `std.net` usa sockets BSD (no existen en el navegador; Node necesita `ws`);
 dynlib/ffi/secrets/petitio dependen de librerías nativas que no están en el
 sysroot wasm. Se rechazan antes de llegar a un error de linker.

### `build`

> **build**(o: BuildOptions) -> BuildResult

 Construye un proyecto o un archivo.

 ## Memoria
 Devuelve BuildResult owned; liberar con `free_result`.

