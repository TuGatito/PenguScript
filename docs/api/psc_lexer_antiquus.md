# psc.lexer_antiquus

> Source: `src/psc/lexer_antiquus.pengu`

psc/lexer_antiquus.pengu — reconocimiento nativo de cuerpos `antiquus`.

Un `antiquus` declara una función cuyo cuerpo es C literal delimitado por
`"""` o `r"""`. El cuerpo se guarda como span y `decode_antiquus` aplica la
dedent; el lexer no reescribe el texto.

## Reglas (réplica de `_extract_antiquus_bodies`)
- La apertura debe ser el primer contenido de la línea siguiente a la
  cabecera (se admiten líneas en blanco).
- Cuerpo de una línea: `"""C"""`.
- Cuerpo multilínea: termina en la primera línea cuyo contenido recortado es
  exactamente `"""`.
- Se quitan las líneas en blanco finales y la indentación común.

## Memoria
`scan_body` añade un `AntiquusInfo` POD y un token; no asigna strings.

---

### `scan_body`

> **scan_body**(lx: ref to LexerState) -> bool

 Intenta escanear el cuerpo de un `antiquus` en la posición actual.

 Se llama justo después del `NEWLINE` que sigue al `:` de la cabecera.

 ## Retorno
 `true` si consumió un cuerpo (aunque esté vacío o falte el cierre).

 ## Memoria
 Añade metadatos y token; no asigna strings.

### `antiquus_name`

> **antiquus_name**(lx: ref to LexerState) -> string

 Nombre de la declaración `antiquus` para diagnósticos.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `line_end_at`

> **line_end_at**(lx: ref to LexerState, start: int) -> int

 Fin de la línea de `start`, sin `\n` ni `\r`.

 ## Memoria
 O(longitud), no asigna.

### `next_line_start`

> **next_line_start**(lx: ref to LexerState, line_end: int) -> int

 Inicio de la línea siguiente, o `-1`.

 ## Memoria
 O(1), no asigna.

### `find_triple`

> **find_triple**(lx: ref to LexerState, from: int, limit: int) -> int

 Primer `"""` en `[from, limit)`, o `-1`.

 ## Memoria
 O(limit - from), no asigna.

### `is_close_line`

> **is_close_line**(lx: ref to LexerState, start: int, end: int) -> bool

 `true` si la línea `[start, end)` es exactamente `"""` tras blanks.

 ## Memoria
 O(longitud), no asigna.

### `compute_indent`

> **compute_indent**(lx: ref to LexerState, start: int, end: int) -> int

 Indentación común de las líneas no vacías del cuerpo.

 ## Memoria
 O(body), no asigna.

### `body_is_empty`

> **body_is_empty**(lx: ref to LexerState, start: int, end: int) -> bool

 `true` si el cuerpo solo contiene blanks.

 ## Memoria
 O(body), no asigna.

