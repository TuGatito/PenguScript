# psc.lsp.uri

> Source: `src/psc/lsp/uri.pengu`

psc/lsp/uri.pengu — file:// <-> path.

---

### `copy`

> **copy**(s: string) -> string

 Copia owned.

### `hexd`

> **hexd**(n: int) -> char

 Hex de un nibble.

### `safe`

> **safe**(c: int) -> bool

 `true` si un byte es seguro sin percent-encoding.

### `path_to_uri`

> **path_to_uri**(path: string) -> string

 Convierte un path a `file://...`.

 ## Memoria
 Devuelve string owned.

### `uri_to_path`

> **uri_to_path**(uri: string) -> string

 Convierte `file://...` a path.

 ## Memoria
 Devuelve string owned.

### `hexv`

> **hexv**(c: int) -> int

 Valor hex o -1.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

 `true` si `s` empieza por `p`.

