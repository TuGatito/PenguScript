# psc.lexer_state

> Source: `src/psc/lexer_state.pengu`

psc/lexer_state.pengu — estado compartido del lexer y artefactos de salida.

Los módulos `lexer*.pengu` comparten este estado mutable. `LexerState` solo
vive durante una llamada a `lex`; no es global ni se guarda en `Session`.

## Contrato de `Token.aux`

| `Token.kind` | `aux` |
|---|---|
| `TokNewline` | ancho de indentación de la última línea del run |
| `TokKeyword` | `0` (el keyword está en `tok.kw`) |
| `TokIntLit` / `TokFloatLit` | base `2/8/10/16`; `0` = float |
| `TokStringLit` | índice en `LexResult.strings` |
| `TokCharLit` | índice en `LexResult.chars` |
| `TokAntiquusBody` | índice en `LexResult.antiquus` |
| `TokError` | reservado (`0` en el MVP) |
| resto | `0` |

## Memoria
`LexerState` no tiene destructor: al terminar, `result` se transfiere por
valor al llamador. Si se añade un camino de salida anticipada, debe liberar
`result` explícitamente.

---

### `LexOptions`

> rune LexOptions

```pengu
    keep_comments as bool
    keep_indent_tokens as bool
    warn_mixed_indentation as bool
    tab_width as int
    max_interp_depth as int
    fold_chain_continuations as bool
```

 Opciones de lexación.

### `default_lex_options`

> **default_lex_options**() -> LexOptions

 Opciones por defecto (las de stage0 salvo `max_interp_depth`).

 ## Memoria
 Valor puro.

### `CommentKind`

> omen CommentKind

```pengu
    ComLine
    ComDoc
    ComDocBlock
```

 Tipo de comentario capturado como trivia.

### `Comment`

> rune Comment

```pengu
    kind as CommentKind
    start as int
    end as int
    line as int
    col as int
    closed as bool
```

 Un comentario. No entra en la lista de tokens.

 ## Memoria
 Valor puro: solo offsets y flags.

### `StringPartKind`

> omen StringPartKind

```pengu
    SegText
    SegInterp
```

 Tipo de segmento de un string.

### `StringPart`

> rune StringPart

```pengu
    kind as StringPartKind
    start as int
    end as int
```

 Un segmento de un string.

 ## Memoria
 Valor puro.

### `StringInfo`

> rune StringInfo

```pengu
    is_raw as bool
    is_triple as bool
    has_interp as bool
    content_start as int
    content_end as int
    part_start as int
    part_count as int
    dedent as int
```

 Metadatos de un string literal.

 `content_start`/`content_end` excluyen las comillas. `dedent` es la
 indentación común que hay que quitar al decodificar un triple (0 si no es
 triple). `part_start`/`part_count` indexan `LexResult.parts`.

 ## Memoria
 Valor puro.

### `CharInfo`

> rune CharInfo

```pengu
    content_start as int
    content_end as int
    codepoint as int
    width as int
```

 Metadatos de un char literal.

 ## Memoria
 Valor puro.

### `AntiquusInfo`

> rune AntiquusInfo

```pengu
    body_start as int
    body_end as int
    indent as int
    is_raw as bool
    empty as bool
```

 Metadatos de un cuerpo `antiquus`.

 ## Memoria
 Valor puro.

### `LexResult`

> rune LexResult

```pengu
    tokens as list of Token
    comments as list of Comment
    strings as list of StringInfo
    parts as list of StringPart
    chars as list of CharInfo
    antiquus as list of AntiquusInfo
```

 Resultado completo de una lexación.

 ## Memoria
 `banish result` libera las listas. Todos los elementos son POD.

### `LexerState`

> rune LexerState

```pengu
    src as ref to SourceFile
    bag as ref to DiagnosticBag
    keywords as ref to KeywordTable
    opts as LexOptions
    pos as int
    line as int
    line_start as int
    pending_antiquus as bool
    antiquus_colon as bool
    antiquus_name_start as int
    antiquus_name_end as int
    result as LexResult
```

 Estado mutable de una lexación.

 ## Memoria
 Sin destructor: `result` se transfiere al terminar.

### `new_lexer_state`

> **new_lexer_state**(src: ref to SourceFile, bag: ref to DiagnosticBag, keywords: ref to KeywordTable, opts: LexOptions) -> LexerState

 Construye un estado vacío.

 ## Memoria
 Asigna las seis listas de `result`; liberar con `banish result`.

### `lex_source_len`

> **lex_source_len**(lx: ref to LexerState) -> int

 Longitud total del fuente.

 ## Memoria
 O(1), no asigna.

### `lex_byte_at`

> **lex_byte_at**(lx: ref to LexerState, offset: int) -> int

 Byte en `offset`, o `-1` fuera de rango.

 ## Memoria
 O(1), no asigna.

### `lex_peek`

> **lex_peek**(lx: ref to LexerState) -> int

 Byte actual, o `-1` en EOF.

 ## Memoria
 O(1), no asigna.

### `lex_peek_at`

> **lex_peek_at**(lx: ref to LexerState, offset: int) -> int

 Byte a `offset` desde la posición actual, o `-1`.

 ## Memoria
 O(1), no asigna.

### `lex_advance`

> **lex_advance**(lx: ref to LexerState) -> void

 Avanza un byte, actualizando línea y `line_start`.

 ## Memoria
 O(1), no asigna.

### `lex_advance_to`

> **lex_advance_to**(lx: ref to LexerState, new_pos: int) -> void

 Avanza hasta `new_pos` (exclusivo).

 ## Memoria
 O(bytes recorridos), no asigna.

### `lex_advance_codepoint`

> **lex_advance_codepoint**(lx: ref to LexerState) -> void

 Avanza un codepoint UTF-8 (1–4 bytes) para recuperación.

 ## Memoria
 O(1), no asigna.

### `lex_current_col`

> **lex_current_col**(lx: ref to LexerState) -> int

 Columna de byte actual, 1-indexed.

 ## Memoria
 O(1), no asigna.

### `lex_emit_token`

> **lex_emit_token**(lx: ref to LexerState, kind: TokenKind, kw: KeywordKind, start: int, end: int, line: int, col: int, aux: int) -> void

 Añade un token con posición explícita.

 ## Memoria
 Hace `push` en la lista; el token es POD.

### `lex_emit_here`

> **lex_emit_here**(lx: ref to LexerState, kind: TokenKind, kw: KeywordKind, start: int, end: int, aux: int) -> void

 Añade un token que empieza en la posición actual.

 ## Memoria
 Hace `push` en la lista; el token es POD.

### `lex_issue`

> **lex_issue**(lx: ref to LexerState, problem: LexIssue, start: int, end: int, detail: string) -> void

 Emite el diagnóstico de un `LexIssue` en `[start, end)`.

 `detail` es prestado. `emit_issue` construye y libera el mensaje.

 ## Memoria
 Asigna el diagnóstico; el bag pasa a ser dueño.

### `lex_slice_abs`

> **lex_slice_abs**(lx: ref to LexerState, start: int, end: int) -> string

 Copia el texto `[start, end)` del fuente.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `lex_is_letter`

> **lex_is_letter**(b: int) -> bool

 `true` si `b` es una letra ASCII.

 ## Memoria
 O(1), no asigna.

### `lex_is_digit`

> **lex_is_digit**(b: int) -> bool

 `true` si `b` es un dígito ASCII.

 ## Memoria
 O(1), no asigna.

### `is_word_byte`

> **is_word_byte**(b: int) -> bool

 `true` si `b` es una letra o dígito ASCII (o `_`).

 ## Memoria
 O(1), no asigna.

### `lex_is_hex_digit`

> **lex_is_hex_digit**(b: int) -> bool

 `true` si `b` es un dígito hexadecimal.

 ## Memoria
 O(1), no asigna.

### `is_octal_digit`

> **is_octal_digit**(b: int) -> bool

 `true` si `b` es un dígito octal.

 ## Memoria
 O(1), no asigna.

### `is_binary_digit`

> **is_binary_digit**(b: int) -> bool

 `true` si `b` es un dígito binario.

 ## Memoria
 O(1), no asigna.

### `lex_is_blank`

> **lex_is_blank**(b: int) -> bool

 `true` si `b` es espacio o tab.

 ## Memoria
 O(1), no asigna.

### `is_newline_at`

> **is_newline_at**(lx: ref to LexerState, offset: int) -> bool

 `true` si `b` es un fin de línea (`\n` o `\r\n`).

 ## Memoria
 O(1), no asigna.

### `utf8_width`

> **utf8_width**(b: int) -> int

 Longitud de un codepoint UTF-8 que empieza en `b` (1–4).

 ## Memoria
 O(1), no asigna.

### `last_kind`

> **last_kind**(lx: ref to LexerState) -> TokenKind

 Último token emitido, o un `TokEof` sintético si aún no hay.

 ## Memoria
 O(1), no asigna.

### `last_is_newline`

> **last_is_newline**(lx: ref to LexerState) -> bool

 `true` si el último token es un `TokNewline`.

 ## Memoria
 O(1), no asigna.

