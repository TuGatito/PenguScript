# psc.session

> Source: `src/psc/session.pengu`

psc/session.pengu — sesión de compilación para F1.

`Session` es dueña de un `SourceFile`, su `DiagnosticBag`, la tabla de
keywords y las opciones. `Session.open` devuelve siempre una sesión; si el
archivo no se pudo leer, `ok` es `false` y `error` explica por qué. Así el
CLI no necesita mover un `Session` fuera de un `result` (el lenguaje no tiene
move semantics) y no hay que copiar sus listas.

## Memoria
`banish session` libera source, diagnostics, keywords y error.

---

### `Session`

> rune Session

```pengu
    ok as bool
    error as SourceError
    source as SourceFile
    diagnostics as DiagnosticBag
    keywords as KeywordTable
    options as LexOptions
```

 Una sesión de lexación.

 ## Memoria
 `banish session` libera todos los campos con heap.

### `open`

> **open**(path: string, options: LexOptions) -> Session

 Abre un archivo desde disco.

 ## Memoria
 Devuelve una sesión owned; liberar con `banish`.

### `open_text`

> **open_text**(path: string, text: string, options: LexOptions) -> Session

 Abre una sesión desde texto ya en memoria (LSP/tests).

 ## Memoria
 Devuelve una sesión owned; liberar con `banish`.

### `validate_utf8`

> **validate_utf8**(f: ref to SourceFile, bag: ref to DiagnosticBag) -> void

 Registra `E0000` si el fuente no es UTF-8 válido.

 ## Memoria
 Añade como máximo un diagnóstico.

### `lingua_error_offset`

> **lingua_error_offset**(err: LinguaError) -> int

 Offset de un `LinguaError`.

 ## Memoria
 O(1), no asigna.

### `lex`

> **lex**() -> LexResult

 Lexa el fuente de la sesión.

 ## Memoria
 Devuelve un `LexResult` owned; el llamador lo libera.

### `has_errors`

> **has_errors**() -> bool

 `true` si hay errores.

 ## Memoria
 O(1), no asigna.

### `render_plain`

> **render_plain**() -> string

 Renderiza los diagnósticos sin color.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `render_colored`

> **render_colored**() -> string

 Renderiza los diagnósticos con ANSI.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `render_forced`

> **render_forced**() -> string

 Renderiza los diagnósticos forzando ANSI.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `render_json`

> **render_json**() -> string

 Renderiza los diagnósticos como JSON LSP.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

