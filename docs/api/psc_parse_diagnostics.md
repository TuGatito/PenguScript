# psc.parse.diagnostics

> Source: `src/psc/parse/diagnostics.pengu`

psc/parse/diagnostics.pengu — diagnósticos sintácticos de F2.

Todos los errores de sintaxis comparten el código `E0000`, igual que
stage0. Lo que cambia es el mensaje, el `help` y el `note`, que aquí son
específicos para que un humano sepa qué corregir.

## Memoria
`parse_issue_message` devuelve un `string` owned. Los `help`/`note` son
literales estáticos. `emit_parse_issue` copia lo que necesita el
`DiagnosticBag` y libera el mensaje.

---

### `PSC_E_SYNTAX`

> **PSC_E_SYNTAX** : string

 Código público de todos los errores sintácticos.

### `ParseIssue`

> omen ParseIssue

```pengu
    ParseExpectedToken
    ParseUnexpectedToken
    ParseExpectedExpression
    ParseExpectedType
    ParseExpectedName
    ParseExpectedNewline
    ParseExpectedIndent
    ParseExpectedDedent
    ParseEmptyBlock
    ParseMultipleStatements
    ParseLegacyAndSeparator
    ParseAtIndexPrecedence
    ParseMaxDepth
    ParseMaxBlockDepth
    ParseInvalidSetTarget
    ParseInvalidCallTarget
    ParseInvalidAttribute
    ParseInvalidDeclareParams
    ParseInvalidWhenClause
    ParseInvalidType
    ParseUnexpectedEof
```

 Cada problema que puede detectar el parser.

### `parse_issue_message`

> **parse_issue_message**(issue: ParseIssue, detail: string) -> string

 Mensaje principal de un issue.

 `detail` se interpola solo en los issues que lo necesitan. El resultado es
 owned; el llamador lo libera.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `parse_issue_help`

> **parse_issue_help**(issue: ParseIssue) -> string

 Texto de ayuda del issue ("" si no tiene).

 ## Memoria
 Devuelve un literal estático; no liberar.

### `parse_issue_note`

> **parse_issue_note**(issue: ParseIssue) -> string

 Nota adicional del issue ("" si no tiene).

 ## Memoria
 Devuelve un literal estático; no liberar.

### `emit_parse_issue`

> **emit_parse_issue**(bag: ref to DiagnosticBag, src: ref to SourceFile, issue: ParseIssue, start: int, end: int, detail: string) -> void

 Emite el diagnóstico de un issue en `[start, end)`.

 `detail` es prestado. El mensaje se construye y se libera aquí; el
 `DiagnosticBag` pasa a ser dueño del `Span` y de las copias internas.

 ## Memoria
 Asigna el mensaje y el diagnóstico; liberar el bag al final.

