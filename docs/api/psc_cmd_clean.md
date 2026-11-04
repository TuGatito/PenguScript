# psc.cmd.clean

> Source: `src/psc/cmd/clean.pengu`

psc/cmd/clean.pengu — `psc clean`.

---

### `print_help`

> **print_help**() -> void

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

 Busca `pengu.toml` subiendo desde `start`.

 ## Memoria
 Devuelve string owned o `""`.

### `inside`

> **inside**(path: string, base: string) -> bool

 `true` si `path` está dentro de `base`.

 ## Memoria
 O(n).

### `run_clean`

> **run_clean**(args: list of string) -> int

 Implementa `psc clean`.

 ## Memoria
 Libera argumentos y rutas.

