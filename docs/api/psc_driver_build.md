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
    lint_cow as bool
    legacy_copy as bool
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
    coverage as bool
    sanitize_kind as int
    split as bool
    jobs as int
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
    is_wasm as bool
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

### `str_cmp`

> **str_cmp**(a: string, b: string) -> int

 Compara dos strings por bytes (orden lexicográfico sin locale).

 ## Memoria
 No asigna.

### `str_starts`

> **str_starts**(s: string, prefix: string) -> bool

 `true` si `s` empieza por `prefix`.

 ## Memoria
 No asigna.

### `str_contains`

> **str_contains**(s: string, needle: string) -> bool

 `true` si `s` contiene `needle`.

 ## Memoria
 No asigna.

### `sort_strings_in_place`

> **sort_strings_in_place**(xs: list of string) -> void

 Ordena una lista de strings in place (inserción estable).

 La clave de caché debe ser determinista: `find_files` devuelve el orden del
 sistema de archivos, que cambia entre ejecuciones y plataformas.

 ## Memoria
 No copia ni libera strings; mueve las celdas de la lista.

### `ext_allowed`

> **ext_allowed**(path: string, mode: string) -> bool

 `true` si la extensión de `path` está en la familia `mode`.

 Modos: `pengu` (.pengu), `c` (.c/.h/.hpp/.inc), `h` (.h/.hpp/.inc),
 `all` (cualquier archivo).

 ## Memoria
 Libera la extensión temporal.

### `seen_has`

> **seen_has**(seen: ref to list of string, dir: string) -> bool

 `true` si `dir` ya se hasheó (dedup de std/include dirs).

 ## Memoria
 No asigna.

### `push_tree_hashes`

> **push_tree_hashes**(cparts: ref to list of string, dir: string, mode: string, skip: string, seen: ref to list of string) -> void

 Añade a `cparts` el path y el hash de cada archivo de `dir`.

 `mode` filtra por extensión; `skip` es el directorio de build del proyecto
 (nunca entra en la clave). Los archivos se ordenan para que la clave sea
 determinista. `seen` deduplica directorios ya hasheados en la misma clave.

 ## Memoria
 Libera la lista de archivos y los hashes temporales.

### `push_file_hash`

> **push_file_hash**(cparts: ref to list of string, path: string) -> void

 Añade a la clave el hash de un archivo suelto (manifest, lock, runtime).

 ## Memoria
 Libera el hash temporal.

### `same_file_content`

> **same_file_content**(a: string, b: string) -> bool

 `true` si dos archivos tienen el mismo contenido.

 Se usa cuando copiar la entrada de caché falla porque el destino es el
 binario que se está ejecutando (`ETXTBSY`): en ese caso el artefacto ya es
 el deseado y el build es un no-op.

 ## Memoria
 Libera las lecturas temporales.

### `compute_cache_key`

> **compute_cache_key**(o: ref to BuildOptions, man: ref to Manifest, p: ref to Paths, tc: ref to Toolchain, eff: ref to Target, base: string, entry: string, is_project: bool, is_file: bool, eff_output: string, out_name: string, dep_dirs: list of string) -> string

 Construye la clave de caché ANTES de sema/codegen.

 La clave incluye todo lo que puede cambiar el artefacto: compilador, target,
 flags del manifiesto y del CLI (incluidos `cflags`, `links`, `lib_dirs`), el
 runtime, el manifiesto, el lock y el contenido de todos los árboles de
 fuentes (proyecto, dependencias y stdlib). El directorio de build queda
 excluido: sus artefactos no son entradas.

 ## Memoria
 Devuelve string owned; libera todas las partes temporales.

### `module_fingerprints`

> **module_fingerprints**(sr: ref to SemaResult) -> list of string

 Fingerprints `ruta\tsha256` de los módulos semánticos.

 Se guardan en el build dir para explicar, con `--verbose`, qué módulo
 invalidó la caché entre dos builds. No forman parte de la clave: la clave
 ya hashea cada fuente; esto solo mejora el diagnóstico.

 ## Memoria
 Devuelve una lista owned.

### `fingerprint_path`

> **fingerprint_path**(line: string) -> string

 Ruta de una línea `ruta\tsha`.

 ## Memoria
 Devuelve string owned.

### `fingerprint_hash`

> **fingerprint_hash**(line: string) -> string

 Hash de una línea `ruta\tsha`.

 ## Memoria
 Devuelve string owned (`""` si no hay tabulador).

### `fingerprint_has`

> **fingerprint_has**(lines: list of string, path: string) -> bool

 `true` si `lines` contiene una fingerprint para `path`.

 ## Memoria
 No retiene nada.

### `fingerprint_of`

> **fingerprint_of**(lines: list of string, path: string) -> string

 Hash guardado para `path`.

 ## Memoria
 Devuelve string owned (`""` si no existe).

### `report_fingerprint_changes`

> **report_fingerprint_changes**(old_lines: list of string, cur_lines: list of string) -> void

 Imprime módulos añadidos, cambiados y eliminados.

 ## Memoria
 No retiene nada.

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

### `unit_object_key`

> **unit_object_key**(header_hash: string, src: string, cc: string, flags: list of string) -> string

 Módulo std no disponible en wasm: mensaje accionable, o `""`.

 `std.net` usa sockets BSD (no existen en el navegador; Node necesita `ws`);
 dynlib/ffi/secrets/petitio dependen de librerías nativas que no están en el
 sysroot wasm. Se rechazan antes de llegar a un error de linker.
 Clave de caché de un objeto de unidad: cabecera + fuente + flags + cc.

### `compile_units`

> **compile_units**(cc: string, flags: list of string, srcs: list of string, objs: list of string, jobs: int) -> int

 Compila `srcs` a `objs` en paralelo (máximo `jobs` procesos).

 Devuelve 0 si todos los objetos se generaron. Windows usa `spawn_argv`,
 que no implementa fork: allí cae a ejecución secuencial.

 ## Memoria
 Los argv temporales se liberan tras cada spawn.

### `wasm_unsupported`

> **wasm_unsupported**(p: ref to SemaProgram) -> string

_Undocumented._

### `build`

> **build**(o: BuildOptions) -> BuildResult

 Construye un proyecto o un archivo.

 ## Memoria
 Devuelve BuildResult owned; liberar con `free_result`.

