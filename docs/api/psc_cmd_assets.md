# psc.cmd.assets

> Source: `src/psc/cmd/assets.pengu`

psc/cmd/assets.pengu — `psc assets` (embed/disk, F6).

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

 Busca el manifiesto.

 ## Memoria
 Devuelve string owned o `""`.

### `excluded`

> **excluded**(patterns: list of string, name: string) -> bool

 `true` si `name` coincide con un patrón de exclusión simple.

 ## Memoria
 O(patrones).

### `safe`

> **safe**(s: string) -> string

 Identificador C seguro.

 ## Memoria
 Devuelve string owned.

### `hexc`

> **hexc**(n: int) -> char

 Carácter hex.

 ## Memoria
 Devuelve char.

### `emit_bytes`

> **emit_bytes**(sb: ref to StringBuilder, data: string, ident: string) -> void

 Emite una lista de bytes como array C.

 ## Memoria
 No retiene.

### `cstr`

> **cstr**(sb: ref to StringBuilder, s: string) -> void

 Escapa un nombre para C string.

 ## Memoria
 No retiene.

### `run_assets`

> **run_assets**(args: list of string) -> int

 Implementa `psc assets`.

 ## Memoria
 Libera temporales.

