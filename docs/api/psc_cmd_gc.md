# psc.cmd.gc

> Source: `src/psc/cmd/gc.pengu`

psc/cmd/gc.pengu — `psc gc`.

---

### `print_help`

> **print_help**() -> void

 Ayuda.

 ## Memoria
 No asigna.

### `prune_to_size`

> **prune_to_size**(limit: int) -> int

 Implementa `psc gc`.

 ## Memoria
 Libera ParseResult.
 Elimina entradas hasta que la caché quepa en `limit` bytes.

 No ordena por fecha: `find_dirs` no garantiza orden y cualquier entrada es
 prescindible. Devuelve cuántas se borraron.

 ## Memoria
 Libera `root`, `dirs`, sus strings y `sizes`.

### `run_gc`

> **run_gc**(args: list of string) -> int

 Implementa `psc gc`.

 ## Memoria
 Libera ParseResult.

