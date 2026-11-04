# psc.parse.api

> Source: `src/psc/parse/api.pengu`

psc/parse/api.pengu — API pública del parser de F2.

Instala los hooks entre módulos y expone `parse_file`/`parse_expr`. El
llamador conserva `SourceFile` y `LexResult`; el `PsParseResult` es dueño
del AST.

## Memoria
`ps_parse_file` no libera `src`, `bag` ni `lex`. El resultado se libera con
`banish result`.

---

### `InterpParseResult`

> rune InterpParseResult

```pengu
    source as SourceFile
    lex as LexResult
    diagnostics as DiagnosticBag
    ast as PsAst
    root as int
    ok as bool
```

 Resultado de parsear una expresión de interpolación.

 ## Memoria
 `banish result` libera `source`, `lex`, `diagnostics` y `ast`.

### `ps_parse_interpolation_expr`

> **ps_parse_interpolation_expr**(text: string) -> InterpParseResult

 Parsea una expresión de interpolación aislada.

 Las posiciones son relativas al texto de la expresión, como en stage0.

 ## Memoria
 Devuelve un bundle owned; liberar con `banish`.

### `ps_install_hooks`

> **ps_install_hooks**(p: ref to PsParser) -> void

 Instala todos los hooks en un parser recién creado.

 ## Memoria
 Asigna punteros a función; no tiene heap.

### `ps_parse_file`

> **ps_parse_file**(src: ref to SourceFile, bag: ref to DiagnosticBag, lex: ref to LexResult, opts: PsParseOptions) -> PsParseResult

 Parsea un archivo completo.

 ## Memoria
 Devuelve un `PsParseResult` owned; `src` y `lex` siguen siendo del llamador.

### `ps_parse_expr`

> **ps_parse_expr**(src: ref to SourceFile, bag: ref to DiagnosticBag, lex: ref to LexResult, opts: PsParseOptions) -> PsParseResult

 Parsea el fuente completo como una expresión (`start = expr`).

 ## Memoria
 Devuelve un `PsParseResult` owned; `src` y `lex` siguen siendo del llamador.

