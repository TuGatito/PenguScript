# psc.token_dump

> Source: `src/psc/token_dump.pengu`

psc/token_dump.pengu — volcado TSV canónico de tokens y comentarios.

El formato es estable y determinista; los golden tests comparan estos bytes.

```text
# psc-token-dump v1
# file: <path>
# sha256: <hex>
# bytes: <n>
# lines: <n>
# columns: index  kind  lexeme  start  end  line  col  end_line  end_col  aux
0	Keyword(Import)	import	0	6	1	1	1	7	0
```

## Memoria
`dump` devuelve un `string` owned; liberar con `banish`.

---

### `dump`

> **dump**(src: ref to SourceFile, result: ref to LexResult, keywords: ref to KeywordTable, include_comments: bool) -> string

 Volcado completo.

 ## Parámetros
 - `src`: fuente.
 - `result`: tokens, comentarios y tablas.
 - `keywords`: tabla para imprimir `Keyword(Name)`.
 - `include_comments`: añadir la sección de trivia.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `comment_kind_name`

> **comment_kind_name**(k: CommentKind) -> string

 Nombre de un tipo de comentario.

 ## Memoria
 Literal estático; no liberar.

### `tab`

> **tab**(sb: ref to StringBuilder) -> void

 Añade un tabulador.

 ## Memoria
 O(1), el builder crece si hace falta.

### `ps_token_dump_newline`

> **ps_token_dump_newline**(sb: ref to StringBuilder) -> void

 Añade un salto de línea.

 ## Memoria
 O(1), el builder crece si hace falta.

### `append_escaped`

> **append_escaped**(sb: ref to StringBuilder, s: string) -> void

 Añade un lexema escapado en una línea.

 ## Memoria
 O(bytes), sin temporales owned.

### `ps_token_dump_append_hex_byte`

> **ps_token_dump_append_hex_byte**(sb: ref to StringBuilder, b: int) -> void

 Añade dos dígitos hex de un byte.

 ## Memoria
 O(1), no asigna.

### `ps_token_dump_hex_char`

> **ps_token_dump_hex_char**(n: int) -> int

 Valor ASCII de un nibble hex.

 ## Memoria
 O(1), no asigna.

