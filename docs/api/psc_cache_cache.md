# psc.cache.cache

> Source: `src/psc/cache/cache.pengu`

psc/cache/cache.pengu — caché content-addressed del CLI (F6).

La clave cubre el contenido del script, el compilador y las flags. La
entrada se escribe de forma atómica dentro de `<root>/<key>/`.

---

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `root`

> **root**() -> string

 Raíz de la caché.

 ## Memoria
 Devuelve string owned.

### `key`

> **key**(parts: list of string) -> string

 Hash de una lista de partes.

 ## Memoria
 Devuelve string owned.

### `get`

> **get**(k: string) -> string

 Entrada existente para `k`, o `""`.

 ## Memoria
 Devuelve string owned o `""`.

### `put`

> **put**(k: string, artifact: string) -> bool

 Guarda un artefacto.

 ## Memoria
 Copia el artefacto y libera temporales.

### `clear`

> **clear**() -> int

 Borra toda la caché.

 ## Memoria
 Libera la raíz.

### `size`

> **size**() -> int

 Tamaño aproximado de la caché.

 ## Memoria
 Devuelve bytes o 0.

