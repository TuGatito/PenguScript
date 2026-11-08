# psc.diagnostics

> Source: `src/psc/diagnostics.pengu`

psc/diagnostics.pengu — diagnósticos léxicos con códigos compatibles.

PSC no reimplementa el renderizador: usa `std.diagnostic` (`DiagnosticBag`,
`Span`, `Label`, render plain/ANSI/JSON) y añade una fachada con los códigos
que el compilador ya publica:

| Código | Uso |
|---|---|
| `E0000` | errores léxicos y de indentación |
| `E0059` | `antiquus` sin cuerpo o con cuerpo vacío |
| `W0005` | indentación mixta (tabs y espacios) |

`E0057` (char > 0x7F) es semántico y lo emite F3; F1 solo guarda el valor.

## Memoria
`emit_issue` construye el mensaje, lo copia dentro del diagnóstico y lo
libera. `help`/`note` se transfieren al `Diagnostic`. El `DiagnosticBag` es
dueño de todo lo añadido.

---

### `PSC_E_LEX`

> **PSC_E_LEX** : string

 Código de error léxico/sintáctico genérico.

### `PSC_E_ANTIQUUS`

> **PSC_E_ANTIQUUS** : string

 Código de error de cuerpo `antiquus`.

### `PSC_W_INDENT`

> **PSC_W_INDENT** : string

 Código de warning por indentación mixta.

### `LexIssue`

> omen LexIssue

```pengu
    LexUnterminatedString
    LexUnterminatedTripleString
    LexUnterminatedRawString
    LexUnterminatedChar
    LexInvalidCharLiteral
    LexInvalidNumber
    LexUnknownCharacter
    LexInvalidUtf8
    LexUnexpectedBom
    LexIndentMismatch
    LexMixedIndentation
    LexUnmatchedCloseBracket
    LexUnclosedBracket
    LexAntiquusMissingBody
    LexAntiquusEmptyBody
    LexInterpolationTooDeep
```

 Cada problema que puede detectar la fase léxica.

 El código público se calcula con `issue_code`; varios issues comparten
 `E0000`, igual que en stage0.

### `issue_code`

> **issue_code**(issue: LexIssue) -> string

 Código público de un issue.

 ## Memoria
 Devuelve un literal estático; no asignar ni liberar.

### `issue_severity`

> **issue_severity**(issue: LexIssue) -> Severity

 Severidad de un issue.

 ## Memoria
 O(1), no asigna.

### `issue_message`

> **issue_message**(issue: LexIssue, detail: string) -> string

 Texto principal del issue.

 `detail` se interpola solo en los issues que lo necesitan; el resto lo
 ignora. El resultado es owned.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `issue_help`

> **issue_help**(issue: LexIssue) -> string

 Texto de ayuda del issue ("" si no tiene).

 ## Memoria
 Devuelve un literal estático; no liberar.

### `issue_note`

> **issue_note**(issue: LexIssue) -> string

 Nota adicional del issue ("" si no tiene).

 ## Memoria
 Devuelve un literal estático; no liberar.

### `diag_span`

> **diag_span**(src: ref to SourceFile, s: ByteSpan) -> Span

 Construye el `diag.Span` de un rango, clampando y ordenando.

 ## Memoria
 Copia la ruta del archivo dentro del `Span`; el `Span` es owned.

### `emit_error`

> **emit_error**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, message: string, s: ByteSpan, help: string, note: string) -> void

 Emite un error con código, mensaje, span, help y note.

 `message`, `help` y `note` son prestados; este helper copia lo que necesita.
 El `Span` se construye desde `src`.

 ## Memoria
 Asigna el `Span`, el `Label` y las copias internas del diagnóstico; el bag
 pasa a ser dueño. No libera los parámetros.

### `emit_warning`

> **emit_warning**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, message: string, s: ByteSpan, help: string) -> void

 Emite un warning con código, mensaje, span y help.

 ## Memoria
 Igual que `emit_error`, con severidad `Warning`.

### `emit_info`

> **emit_info**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, message: string, s: ByteSpan, help: string) -> void

 Emite un aviso informativo con código, mensaje, span y help.

 ## Memoria
 Igual que `emit_warning`, con severidad `Info`.

### `emit_issue`

> **emit_issue**(bag: ref to DiagnosticBag, src: ref to SourceFile, issue: LexIssue, s: ByteSpan, detail: string) -> void

 Emite el diagnóstico correspondiente a un `LexIssue`.

 ## Memoria
 Construye y libera el mensaje; el diagnóstico pasa a ser propiedad del bag.

### `render_forced`

> **render_forced**(bag: ref to DiagnosticBag) -> string

 Renderiza el bag forzando ANSI, incluso si stderr no es un TTY.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

