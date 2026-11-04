# psc.cmd.meta

> Source: `src/psc/cmd/meta.pengu`

psc/cmd/meta.pengu — `psc metadata` y `psc tree`.

---

### `print_help`

> **print_help**(name: string) -> void

 Ayuda.

 ## Memoria
 No asigna.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `find_root`

> **find_root**(start: string) -> string

 Busca `pengu.toml`.

 ## Memoria
 Devuelve string owned o `""`.

### `jstr`

> **jstr**(sb: ref to StringBuilder, s: string) -> void

 Añade una cadena JSON.

 ## Memoria
 No retiene.

### `jkey`

> **jkey**(sb: ref to StringBuilder, s: string) -> void

 Añade `"key":` a un builder JSON.

 ## Memoria
 No retiene.

### `run_metadata`

> **run_metadata**(args: list of string) -> int

 Implementa `psc metadata`.

 ## Memoria
 Libera resultado.

### `run_tree`

> **run_tree**(args: list of string) -> int

 Implementa `psc tree`.

 ## Memoria
 Libera resultado.

