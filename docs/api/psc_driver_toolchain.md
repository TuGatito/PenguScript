# psc.driver.toolchain

> Source: `src/psc/driver/toolchain.pengu`

psc/driver/toolchain.pengu — cc, flags e includes/links.

---

### `Toolchain`

> rune Toolchain

```pengu
    ok as bool
    error as string
    cc as string
    cflags as list of string
    include_dirs as list of string
    lib_dirs as list of string
    links as list of string
```

 Toolchain resuelto.

 ## Memoria
 Strings/listas owned; liberar con `free_toolchain`.

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

### `choose_cc`

> **choose_cc**(override: string, configured: string, t: Target) -> string

 Elige un compilador.

 ## Memoria
 Devuelve string owned o `""`.

### `add_inc`

> **add_inc**(xs: ref to list of string, dir: string) -> void

 Añade un directorio de include si existe.

 ## Memoria
 Añade una copia owned a la lista.

### `add_lib`

> **add_lib**(xs: ref to list of string, dir: string) -> void

 Añade un directorio de librerías si existe.

 ## Memoria
 Añade una copia owned a la lista.

### `resolve`

> **resolve**(m: ref to Manifest, p: ref to Paths, t: Target, cc_override: string, profile: string, strict: bool, release_unsafe: bool) -> Toolchain

 Resuelve cc/flags.

 ## Memoria
 Resultado owned; liberar con `free_toolchain`.

### `free_toolchain`

> **free_toolchain**(t: ref to Toolchain) -> void

 Libera un toolchain.

 ## Memoria
 Libera strings/listas.

