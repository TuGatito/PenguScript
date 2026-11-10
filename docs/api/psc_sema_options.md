# psc.sema.options

> Source: `src/psc/sema/options.pengu`

psc/sema/options.pengu — opciones de una comprobación semántica.

Las opciones son inmutables durante el chequeo. Los strings son owned por el
`SemaProgram`; el llamador puede liberar su copia después de `check_*`.

---

### `SemaOptions`

> rune SemaOptions

```pengu
    base_dir as string
    src_dir as string
    lib_dir as string
    std_dirs as list of string
    dep_dirs as list of string
    defines as list of string
    os_name as string
    arch as string
    compiler as string
    wasm_target as string
    is_main as bool
    is_debug as bool
    deny_deprecated as bool
    max_errors as int
    stop_after_first as bool
    include_antiquus as bool
    lint_cow as bool
    lint_shadow as bool
```

 Opciones de proyecto que necesita F3.

 `std_dirs` se consulta en orden; si está vacío se usa `<base_dir>/std`.

### `default_options`

> **default_options**(base_dir: string) -> SemaOptions

 Opciones por defecto para un archivo.

 `base_dir` se copia; el resto son literales.

 ## Memoria
 Devuelve strings owned; el llamador los libera con `free_options`.

### `free_options`

> **free_options**(opts: ref to SemaOptions) -> void

 Libera las opciones.

 ## Memoria
 Libera cada string y las dos listas.

