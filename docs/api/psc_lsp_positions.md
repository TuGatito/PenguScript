# psc.lsp.positions

> Source: `src/psc/lsp/positions.pengu`

psc/lsp/positions.pengu — offsets de byte <-> (línea, UTF-16).

---

### `utf16_len`

> **utf16_len**(s: string) -> int

 Cuenta code units UTF-16 de un string.

### `line_start`

> **line_start**(text: string, line: int) -> int

 Inicio de byte de una línea 0-indexed.

### `position_json`

> **position_json**(text: string, off: int) -> JsonValue

 Posición LSP (0-indexed) de un offset de byte.

### `range_json`

> **range_json**(text: string, start: int, end: int) -> JsonValue

 Range LSP de un span de bytes.

### `offset_at`

> **offset_at**(text: string, line: int, character: int) -> int

 Offset de byte de una posición LSP (0-indexed, UTF-16).

