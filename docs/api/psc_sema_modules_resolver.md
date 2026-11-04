# psc.sema.modules.resolver

> Source: `src/psc/sema/modules/resolver.pengu`

psc/sema/modules/resolver.pengu — encontrar el archivo de un import.

Réplica del orden de `pengu_symbols.find_module_path`:
`std/`, directorio del importador, `src_dir`, `lib_dir` y raíz. Devuelve
`""` si no existe; el programa emite `E0004` con el contexto del import.

## Memoria
Devuelve strings owned; el llamador los libera.

---

### `join2`

> **join2**(a: string, b: string) -> string

 Concatena dos componentes con `/`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `join3`

> **join3**(a: string, b: string, c: string) -> string

 Concatena tres componentes.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `dot_to_path`

> **dot_to_path**(dot: string) -> string

 Convierte `a.b.c` en `a/b/c`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `first_component`

> **first_component**(path: string) -> string

 Primer componente de un path con `/`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `rest_after_first`

> **rest_after_first**(path: string) -> string

 Resto tras el primer `/`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `slice_prefix`

> **slice_prefix**(s: string, end: int) -> string

 Prefijo de `s` hasta `end`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `slice_from`

> **slice_from**(s: string, start: int) -> string

 Sufijo de `s` desde `start`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `try_prefix`

> **try_prefix**(prefix: string) -> string

 Prueba los cuatro candidatos de un prefijo.

 Devuelve el primero que exista, o `""`.

 ## Memoria
 Devuelve un string owned si encuentra; `""` es literal.

### `find_module`

> **find_module**(options: ref to SemaOptions, dot: string, from_dir: string) -> string

 Busca un import.

 `from_dir` es el directorio del archivo importador; `dot` es `a.b.c`.

 ## Memoria
 Devuelve un path owned o `""`; liberar si no está vacío.

### `dir_of`

> **dir_of**(path: string) -> string

 Directorio de un archivo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `normalize_path`

> **normalize_path**(path: string) -> string

 Normaliza un path absoluto/relativo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

