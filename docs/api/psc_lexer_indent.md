# psc.lexer_indent

> Source: `src/psc/lexer_indent.pengu`

psc/lexer_indent.pengu — post-lexer de `NEWLINE`/`INDENT`/`DEDENT`.

Replica el `Indenter` de Lark:
- `tab_width = 2`;
- los `NEWLINE` dentro de `()`, `[]` o `{}` se descartan y no generan
  indentación;
- la indentación de un `NEWLINE` es la de su última línea (la que empieza el
  siguiente token);
- al EOF se cierran todos los niveles.

A diferencia de stage0, un dedent inconsistente no aborta: se emite `E0000`
y se recuerda el nuevo nivel para no repetir el error en cada línea.

## Memoria
`apply` construye una lista nueva y libera la lista de entrada. Devuelve una
lista owned; liberar con `banish`.

---

### `lex_indent_apply`

> **lex_indent_apply**(src: ref to SourceFile, bag: ref to DiagnosticBag, tokens: list of Token, opts: LexOptions) -> list of Token

 Aplica la pasada de indentación.

 ## Memoria
 Libera `tokens` y devuelve una lista nueva; el llamador la libera.

### `lex_indent_emit_zero`

> **lex_indent_emit_zero**(src: ref to SourceFile, out: ref to list of Token, kind: TokenKind, offset: int, width: int) -> void

 Emite un token de ancho cero en `offset`.

 ## Memoria
 `push` de un valor POD; no asigna.

### `lex_indent_emit_zero_at`

> **lex_indent_emit_zero_at**(src: ref to SourceFile, out: ref to list of Token, kind: TokenKind, offset: int, line: int, col: int, width: int) -> void

 Emite un token de ancho cero con posición explícita.

 ## Memoria
 `push` de un valor POD; no asigna.

### `lex_indent_is_open`

> **lex_indent_is_open**(k: TokenKind) -> bool

 `true` si `k` abre un delimitador.

 ## Memoria
 O(1), no asigna.

### `lex_indent_is_close`

> **lex_indent_is_close**(k: TokenKind) -> bool

 `true` si `k` cierra un delimitador.

 ## Memoria
 O(1), no asigna.

### `lex_indent_closing_char`

> **lex_indent_closing_char**(k: TokenKind) -> string

 Carácter de cierre para el diagnóstico.

 ## Memoria
 Devuelve un literal estático; no liberar.

### `lex_indent_opening_char_at`

> **lex_indent_opening_char_at**(src: ref to SourceFile, offset: int) -> string

 Carácter de apertura en `offset`.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `lex_indent_emit_issue_at`

> **lex_indent_emit_issue_at**(src: ref to SourceFile, bag: ref to DiagnosticBag, problem: LexIssue, start: int, end: int, detail: string) -> void

 Emite un issue en `[start, end)`.

 ## Memoria
 Asigna el diagnóstico; el bag pasa a ser dueño.

### `lex_indent_warn_mixed_indentation`

> **lex_indent_warn_mixed_indentation**(src: ref to SourceFile, bag: ref to DiagnosticBag) -> void

 Emite `W0005` si se mezclan tabs y espacios en la indentación.

 ## Memoria
 Recorre el fuente sin asignar; emite un diagnóstico como máximo.

