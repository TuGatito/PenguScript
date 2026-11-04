# psc.codegen.options

> Source: `src/psc/codegen/options.pengu`

psc/codegen/options.pengu — opciones de emisión C de F4.

Las opciones son valores POD con strings prestados por el llamador; el
generador no las libera. El driver (F5) las construye desde el manifiesto o
la CLI.

---

### `CgOptions`

> rune CgOptions

```pengu
    base_dir as string
    entry_file as string
    is_test as bool
    test_json as bool
    is_library as bool
    dce as bool
    dce_scope_user as bool
    prune_types as bool
    prune_native as bool
    line_markers as bool
    strict_c99 as bool
    target_compiler as string
    release_unsafe as bool
    debug as bool
    os_name as string
    arch as string
    compiler as string
    wasm as bool
    wasm_target as string
    target_triple as string
    defines as list of string
```

 Opciones de una emisión de C.

### `default_options`

> **default_options**(base_dir: string) -> CgOptions

 Opciones por defecto para un proyecto.

 ## Memoria
 Devuelve strings prestados; no asigna.

### `CgStats`

> rune CgStats

```pengu
    types as int
    prototypes as int
    functions as int
    instances as int
    includes as int
    bytes as int
    lines as int
```

 Estadísticas de emisión.

