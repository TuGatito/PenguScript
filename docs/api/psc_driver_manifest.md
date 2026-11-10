# psc.driver.manifest

> Source: `src/psc/driver/manifest.pengu`

psc/driver/manifest.pengu — lectura del subconjunto TOML de `pengu.toml`.

F5 no implementa dependencias ni assets; los rechaza con un error claro.

---

### `Manifest`

> rune Manifest

```pengu
    found as bool
    ok as bool
    error as string
    base_dir as string
    name as string
    version as string
    entry as string
    output as string
    output_name as string
    target as string
    src_dir as string
    lib_dir as string
    include_dir as string
    c_dir as string
    build_dir as string
    assets_dir as string
    assets_module as string
    assets_embed as bool
    assets_exclude as list of string
    links as list of string
    lib_dirs as list of string
    include_dirs as list of string
    cflags as list of string
    ldflags as list of string
    defines as list of string
    cc as string
    web_dir as string
    web_scripts as list of string
    web_assets as list of string
    web_base as string
    strict_c99 as bool
    legacy_copy as bool
```

 Manifiesto resuelto.

 ## Memoria
 Todos los strings/listas son owned; liberar con `free_manifest`.

### `copy`

> **copy**(s: string) -> string

 Copia owned de un string.

 ## Memoria
 Devuelve string owned.

### `copy_list`

> **copy_list**(xs: list of string) -> list of string

 Copia una lista de strings.

 ## Memoria
 Devuelve lista owned con copias.

### `free_strings`

> **free_strings**(xs: list of string) -> void

 Libera una lista de strings owned.

 ## Memoria
 Libera elementos y lista.

### `stem_of`

> **stem_of**(path: string) -> string

 Stem de un path (sin extensión).

 ## Memoria
 Devuelve string owned.

### `text_or`

> **text_or**(entries: list of TomlEntry, key: string, fallback: string) -> string

 Valor de texto, o `fallback` si la clave no existe.

 ## Memoria
 Devuelve string owned.

### `default_manifest`

> **default_manifest**(base_dir: string, entry: string) -> Manifest

 Manifiesto por defecto para un archivo suelto.

 ## Memoria
 Devuelve Manifest owned.

### `starts_with`

> **starts_with**(s: string, prefix: string) -> bool

 `true` si `s` empieza por `prefix`.

 ## Memoria
 O(prefix).

### `load_manifest`

> **load_manifest**(base_dir: string, profile: string) -> Manifest

 Carga `pengu.toml` desde `base_dir`.

 `profile` puede ser `debug` o `release`. Si el archivo no existe,
 `found=false` y se devuelven defaults.

 ## Memoria
 Devuelve Manifest owned.

### `free_manifest`

> **free_manifest**(m: ref to Manifest) -> void

 Libera un manifiesto.

 ## Memoria
 Libera todos los campos.

