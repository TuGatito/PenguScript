# psc.lexer_comment

> Source: `src/psc/lexer_comment.pengu`

psc/lexer_comment.pengu — comentarios de línea, doc e bloques `##`.

Los comentarios no entran en la lista de tokens: se guardan como trivia con
sus spans. F7 (doc) y F8 (hover) podrán reconstruir el texto sin volver a
lexar.

## Regla del bloque doc
Un `##` aislado abre un bloque si la línea no tiene más contenido, la línea
anterior no empieza por `#` y la siguiente tampoco. El bloque cierra en una
línea `##` o `## ... ##`, o consume el resto del archivo si no cierra. Es
exactamente la regla de `PenguParser._strip_comments`: hay 54 archivos del
corpus que dependen de ella.

## Memoria
`scan_comment` solo hace `push` de valores POD y avanza el lexer.

---

### `scan_comment`

> **scan_comment**(lx: ref to LexerState) -> void

 Escanea un comentario que empieza en `#`.

 ## Memoria
 Añade un `Comment` POD; no asigna strings.

### `line_end_at`

> **line_end_at**(lx: ref to LexerState, start: int) -> int

 Fin de la línea que contiene `start`, sin `\n` ni `\r`.

 ## Memoria
 O(longitud de línea), no asigna.

### `only_blanks`

> **only_blanks**(lx: ref to LexerState, start: int, end: int) -> bool

 `true` si `[start, end)` solo tiene espacios/tabs.

 ## Memoria
 O(n), no asigna.

### `previous_line_is_comment`

> **previous_line_is_comment**(lx: ref to LexerState, line_start: int) -> bool

 `true` si la línea anterior a `line_start` empieza por `#` tras blanks.

 ## Memoria
 O(longitud de la línea anterior), no asigna.

### `line_starts_with_hash`

> **line_starts_with_hash**(lx: ref to LexerState, start: int) -> bool

 `true` si la línea que empieza en `start` empieza por `#`.

 ## Memoria
 O(blanks iniciales), no asigna.

### `next_line_start`

> **next_line_start**(lx: ref to LexerState, line_end: int) -> int

 Offset del inicio de la línea siguiente, o `-1` en EOF.

 ## Memoria
 O(1), no asigna.

### `find_doc_block_end`

> **find_doc_block_end**(lx: ref to LexerState, next_start: int) -> int

 Busca la línea de cierre de un bloque doc que empieza en `next_start`.

 ## Retorno
 Offset del final de la línea de cierre, o `-1` si no cierra.

 ## Memoria
 O(archivo), no asigna.

### `is_doc_close_line`

> **is_doc_close_line**(lx: ref to LexerState, start: int, end: int) -> bool

 `true` si la línea `[start, end)` es `##` o empieza/termina en `##`.

 ## Memoria
 O(longitud), no asigna.

### `doc_line_closed`

> **doc_line_closed**(lx: ref to LexerState, rest_start: int, line_end: int) -> bool

 `true` si una línea doc termina en `##` (forma `## texto ##`).

 ## Memoria
 O(1), no asigna.

