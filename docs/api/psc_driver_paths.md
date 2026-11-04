# psc.driver.paths

> Source: `src/psc/driver/paths.pengu`

psc/driver/paths.pengu — localización del runtime, std y build dir.

El driver nunca asume el layout del checkout: busca en variables de
entorno, en el proyecto, en el checkout y en el prefijo FHS.

---

### `Paths`

> rune Paths

```pengu
    ok as bool
    error as string
    repo_root as string
    runtime_archive as string
    runtime_include as string
    std_c_dir as string
    std_dirs as list of string
    wasm_shell as string
    js_library as string
    js_pre as string
```

 Rutas del toolchain para un proyecto.

 ## Memoria
 Todos los strings/listas son owned; liberar con `free_paths`.

### `find_repo_root`

> **find_repo_root**(base_dir: string) -> string

 Busca el checkout subiendo desde `base_dir`.

 ## Memoria
 Devuelve un string owned o `""`.

### `first_file`

> **first_file**(xs: list of string) -> string

 Primer archivo existente de una lista.

 ## Memoria
 Devuelve string owned o `""`; no libera la lista.

### `first_dir`

> **first_dir**(xs: list of string) -> string

 Primer directorio existente de una lista.

 ## Memoria
 Devuelve string owned o `""`; no libera la lista.

### `env_or_empty`

> **env_or_empty**(name: string) -> string

 Lee una variable de entorno o `""`.

 ## Memoria
 Devuelve string owned.

### `find_paths`

> **find_paths**(base_dir: string, t: Target) -> Paths

 Resuelve las rutas del runtime.

 ## Memoria
 Resultado owned; liberar con `free_paths`.

### `free_paths`

> **free_paths**(p: ref to Paths) -> void

 Libera rutas.

 ## Memoria
 Libera cada string y lista.

### `free_strings`

> **free_strings**(xs: list of string) -> void

 Libera una lista de strings owned.

 ## Memoria
 Libera elementos y la lista.

