# psc.lexer_decode

> Source: `src/psc/lexer_decode.pengu`

psc/lexer_decode.pengu — decodificación demand-driven de literales.

El lexer guarda spans; estas funciones materializan el valor cuando el parser
o el codegen lo necesitan. Incluye escapes, dedent de triples, UTF-8 e
`antiquus`.

## Memoria
Las funciones `decode_*` devuelven un `string` owned; el llamador hace
`banish`.

---

### `decode_string`

> **decode_string**(src: ref to SourceFile, info: StringInfo, parts: list of StringPart) -> string

 Decodifica un string literal completo.

 Para literales con interpolación devuelve **solo los segmentos de texto**
 concatenados (las expresiones las evalúa el código generado). Los tests de
 F1 usan literales sin interpolación para comparar bytes.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `decode_text_parts`

> **decode_text_parts**(src: ref to SourceFile, info: StringInfo, parts: list of StringPart) -> string

 Decodifica solo los segmentos de texto de un string con interpolación.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `decode_part`

> **decode_part**(src: ref to SourceFile, p: StringPart, is_raw: bool, is_triple: bool, dedent: int, content_start: int) -> string

 Decodifica un `StringPart` de texto.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `append_byte_char`

> **append_byte_char**(sb: ref to StringBuilder, b: int) -> void

 Añade un byte al builder como char.

 ## Memoria
 O(1); el builder crece si hace falta.

### `decode_text`

> **decode_text**(text: string, is_raw: bool) -> string

 Decodifica escapes de un texto completo sin interpolación.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `decode_escape_into`

> **decode_escape_into**(src: ref to SourceFile, i: int, limit: int, sb: ref to StringBuilder) -> int

 Decodifica un escape desde `i` en un string, añadiendo bytes al builder.

 ## Retorno
 Bytes consumidos (>=1), o `0` si no es un escape.

 ## Memoria
 O(1), no asigna (salvo el builder).

### `decode_escape_bytes_into`

> **decode_escape_bytes_into**(raw: ref to frozen u8, i: int, limit: int, sb: ref to StringBuilder) -> int

 Igual que `decode_escape_into`, sobre un buffer prestado.

 ## Memoria
 O(1), no asigna.

### `append_codepoint`

> **append_codepoint**(sb: ref to StringBuilder, cp: int) -> bool

 Añade un codepoint como UTF-8. Ignora valores fuera de rango o surrogates.

 ## Memoria
 O(1), no asigna.

### `dedent_content`

> **dedent_content**(text: string, dedent: int) -> string

 Aplica la dedent de un triple a un contenido completo.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `src_byte_of`

> **src_byte_of**(s: string, i: int) -> int

 Byte de un string en `i`.

 ## Memoria
 O(1), no asigna.

### `src_last_byte`

> **src_last_byte**(s: string) -> int

 Último byte de un string.

 ## Memoria
 O(1), no asigna.

### `decode_antiquus`

> **decode_antiquus**(src: ref to SourceFile, info: AntiquusInfo) -> string

 Decodifica un cuerpo `antiquus` (C literal, sin escapes).

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `decode_string_part`

> **decode_string_part**(src: ref to SourceFile, p: StringPart, is_raw: bool, is_triple: bool, dedent: int, content_start: int) -> string

 Decodifica un `StringPart` de texto por separado (API para F2/F4).

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

