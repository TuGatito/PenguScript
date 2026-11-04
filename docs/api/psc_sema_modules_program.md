# psc.sema.modules.program

> Source: `src/psc/sema/modules/program.pengu`

psc/sema/modules/program.pengu — programa completo: módulos, orden y tablas.

`SemaProgram` posee las tablas y los módulos cargados. El descubrimiento es
DFS: un import se carga antes que su importador y se registra en `order`.
Los ciclos se detectan con la pila `visiting`.

## Memoria
`free_program` libera módulos, tablas, pool, bag y opciones.

---

### `SemaProgram`

> rune SemaProgram

```pengu
    options as SemaOptions
    names as NamePool
    types as SemaTypeTable
    symbols as SemaSymbols
    diagnostics as DiagnosticBag
    modules as list of SemaModule
    by_path as map of string to int
    order as list of int
    root as int
```

 Programa semántico.

 ## Memoria
 Sin `derive Nexus`; `free_program` libera en orden seguro.

### `new_program`

> **new_program**(options: SemaOptions) -> ref to SemaProgram

 Crea un programa vacío.

 ## Memoria
 Inicializa tablas; liberar con `free_program`.

### `free_program`

> **free_program**(p: ref to SemaProgram) -> void

 Libera el programa completo.

 ## Memoria
 Módulos, tablas, pool, bag y opciones.

### `canonical_path`

> **canonical_path**(p: ref to SemaProgram, path: string) -> string

 Ruta canónica (identidad) de un módulo.

 Absolutiza y normaliza para que el mismo archivo no entre dos veces con
 grafías distintas (relativa vs absoluta, `./`, `..`, separadores).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `display_path`

> **display_path**(p: ref to SemaProgram, canonical: string) -> string

 Ruta de display de un módulo: relativa a `base_dir` si es posible.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `module_id`

> **module_id**(p: ref to SemaProgram, path: string) -> int

 Busca un módulo ya cargado.

 ## Memoria
 O(1) promedio.

### `discover`

> **discover**(p: ref to SemaProgram, path: string, is_entry: bool, depth: int, visiting: ref to list of string, vcount: int) -> int

 Descubre un módulo y sus imports.

 `depth` es la profundidad de import. `visiting` es la pila de paths
 canónicos.

 ## Memoria
 Añade módulos; liberar con `free_program`.

### `discover_imports_of`

> **discover_imports_of**(p: ref to SemaProgram, m: SemaModule, depth: int, visiting: ref to list of string, vcount: int) -> void

 Descubre los imports de un módulo ya cargado y lo añade al orden.

 Se usa tanto para archivos (`discover`) como para texto en memoria
 (`check_text`, stdin), que no existe en disco.

 ## Memoria
 Añade módulos; liberar con `free_program`.

### `ends_with_path`

> **ends_with_path**(s: string, suffix: string) -> bool

 ¿Termina `s` con `suffix`?

 ## Memoria
 O(suffix); no asigna.

### `companion_path`

> **companion_path**(path: string) -> string

 Path del binding companion `.d.pengu`, o `""`.

 ## Memoria
 Devuelve un string owned.

### `visiting_has`

> **visiting_has**(visiting: ref to list of string, path: string, count: int) -> bool

 ¿El path está en la pila de ciclos?

 ## Memoria
 O(n).

### `path_is_std`

> **path_is_std**(path: string) -> bool

 `true` si el path contiene un componente `std`.

 ## Memoria
 O(n).

### `scan_imports`

> **scan_imports**(p: ref to SemaProgram, m: SemaModule, out: ref to list of string, nodes: ref to list of int) -> void

 Recoge los imports de un módulo.

 ## Memoria
 Añade strings/nodos owned a las listas del llamador.

### `program_dotted_text`

> **program_dotted_text**(m: SemaModule, node: int) -> string

 Texto de un `dotted_path`.

 ## Memoria
 Devuelve un string owned.

### `create_module_scopes`

> **create_module_scopes**(p: ref to SemaProgram) -> void

 Crea un scope global por módulo, hijo del scope global de builtins.

 ## Memoria
 Añade scopes; el scope 0 sigue siendo el global de builtins.

