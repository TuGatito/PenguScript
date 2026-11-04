# psc.lexer_string

> Source: `src/psc/lexer_string.pengu`

psc/lexer_string.pengu — strings, raw strings, triples, chars e interpolación.

La delimitación, el split en segmentos y la decodificación están separados:
el lexer guarda spans (sin asignar un string por literal) y F2/F4 piden el
valor con `decode_string` cuando lo necesitan.

## Reglas de delimitación
- `"..."`: cierra en la primera `"` no escapada y fuera de un grupo `{...}`
  equilibrado. Puede contener `\n` (stage0 también lo permite).
- `"""..."""`: cierra en el primer `"""`; los escapes no protegen el cierre.
- `r"..."`: cierra en la primera `"`; sin escapes ni interpolación.
- `r"""..."""`: cierra en el primer `"""`.
- `'...'`: exactamente una unidad entre comillas.

## Memoria
Las funciones `scan_*` añaden metadatos POD a `lx->result` y avanzan el
lexer. Las funciones `decode_*` viven en `lexer_decode.pengu` y devuelven un
`string` owned; el llamador hace `banish`.

---

### `scan_any`

> **scan_any**(lx: ref to LexerState) -> void

 Escanea cualquier forma de string en la posición actual.

 ## Memoria
 Añade un `StringInfo`, sus `StringPart` y un `Token`; no devuelve heap.

### `scan_double`

> **scan_double**(lx: ref to LexerState) -> void

 Escanea un string normal que empieza en `"`.

 ## Memoria
 Añade un `StringInfo`, sus `StringPart` y un `Token`; no devuelve heap.

### `scan_raw`

> **scan_raw**(lx: ref to LexerState) -> void

 Escanea un raw string que empieza en `r"`.

 ## Memoria
 Igual que `scan_double`.

### `scan_string_generic`

> **scan_string_generic**(lx: ref to LexerState, raw: bool, triple: bool) -> void

 Núcleo de escaneo de strings.

 ## Parámetros
 - `lx`: estado.
 - `raw`: no interpretar escapes ni interpolación.
 - `triple`: usar `"""`.

 ## Memoria
 Añade metadatos y token; no asigna strings.

### `find_byte`

> **find_byte**(lx: ref to LexerState, from: int, limit: int, needle: int) -> int

 Busca la primera aparición de `needle` en `[from, limit)`.

 ## Memoria
 O(limit - from), no asigna.

### `find_triple_close`

> **find_triple_close**(lx: ref to LexerState, from: int, limit: int) -> int

 Busca el primer `"""` en `[from, limit)`.

 ## Memoria
 O(limit - from), no asigna.

### `find_plain_close`

> **find_plain_close**(lx: ref to LexerState, from: int, limit: int) -> int

 Busca el cierre de un string normal, respetando escapes e interpolación.

 ## Memoria
 O(limit - from), no asigna.

### `skip_escape_at`

> **skip_escape_at**(lx: ref to LexerState, i: int, limit: int) -> int

 Salta un escape desde `i` y devuelve el siguiente índice.

 ## Memoria
 O(1), no asigna.

### `find_balanced`

> **find_balanced**(lx: ref to LexerState, open: int, limit: int) -> int

 Busca el `}` que equilibra un `{` en `open`.

 Respeta strings `"..."`/`'...'` anidados y sus escapes.

 ## Memoria
 O(limit - open), no asigna.

### `find_line_end`

> **find_line_end**(lx: ref to LexerState, from: int, limit: int) -> int

 Índice del `\n` que termina la línea de `from`, o `limit`.

 ## Memoria
 O(limit - from), no asigna.

### `compute_dedent`

> **compute_dedent**(lx: ref to LexerState, start: int, end: int) -> int

 Calcula la indentación común de un triple.

 ## Memoria
 O(content), no asigna.

### `split_parts`

> **split_parts**(lx: ref to LexerState, start: int, end: int, raw: bool, triple: bool) -> list of StringPart

 Divide el contenido en segmentos de texto e interpolación.

 ## Memoria
 Devuelve un `list of StringPart` owned; liberar con `banish`.

### `scan_char`

> **scan_char**(lx: ref to LexerState) -> void

 Escanea un char literal que empieza en `'`.

 ## Memoria
 Añade un `CharInfo` y un `Token`.

### `scan_char_unit_end`

> **scan_char_unit_end**(lx: ref to LexerState, from: int, n: int) -> int

 Calcula el final de la unidad de un char empezando en `from`.

 ## Memoria
 O(1), no asigna.

### `decode_char_codepoint`

> **decode_char_codepoint**(lx: ref to LexerState, start: int, end: int) -> int

 Decodifica el codepoint de un char `[start, end)`; `-1` si es inválido.

 ## Memoria
 O(bytes), no asigna.

### `decode_utf8_at`

> **decode_utf8_at**(lx: ref to LexerState, start: int, end: int) -> int

 Decodifica el primer codepoint UTF-8 de `[start, end)`.

 ## Memoria
 O(1), no asigna.

### `hex_value`

> **hex_value**(b: int) -> int

 Valor de un dígito hex, o `-1`.

 ## Memoria
 O(1), no asigna.

