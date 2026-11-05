# psc.parse.state

> Source: `src/psc/parse/state.pengu`

psc/parse/state.pengu — estado, cursor, errores y construcción del AST.

`PsParser` es el estado mutable de un parseo. Vive en la pila de la API
pública; no hay estado global. El AST se transfiere al `PsParseResult` y las
dos listas de trabajo (`child_stack`/`marks`) se liberan al terminar.

## Ganchos de módulos
La gramática es mutuamente recursiva (`if` es statement y expresión, un
bloque contiene statements, un statement contiene expresiones). Para poder
repartir el parser en carpetas sin imports cíclicos, `PsHooks` guarda
punteros a las funciones que cruzan esa frontera. La API los instala antes
de parsear. Cada hook tiene un stub que no debería ejecutarse nunca; si se
ejecuta, el parser falla de forma controlada.

## Memoria
`PsParser` presta `SourceFile`, `LexResult` y `DiagnosticBag`. Es dueño del
`PsAst` y de las dos listas de trabajo; `finish_parse` las libera.

---

### `PsParseOptions`

> rune PsParseOptions

```pengu
    max_depth as int
    max_errors as int
    stop_after_first as bool
```

 Opciones de parseo.

### `ps_default_parse_options`

> **ps_default_parse_options**() -> PsParseOptions

 Opciones por defecto.

 ## Memoria
 Valor puro.

### `PsHooks`

> rune PsHooks

```pengu
    value as ref to weave with p: ref to PsParser into int
    when as ref to weave with p: ref to PsParser into int
    judge as ref to weave with p: ref to PsParser into int
    do_block as ref to weave with p: ref to PsParser into int
    with_init as ref to weave with p: ref to PsParser into int
    or_block as ref to weave with p: ref to PsParser, left: int into int
    when_body as ref to weave with p: ref to PsParser into int
    expr as ref to weave with p: ref to PsParser into int
    list_expr as ref to weave with p: ref to PsParser into int
    value_expr as ref to weave with p: ref to PsParser into int
    list_value_expr as ref to weave with p: ref to PsParser into int
    arg_expr as ref to weave with p: ref to PsParser into int
    expr_no_cast as ref to weave with p: ref to PsParser into int
    guard_expr as ref to weave with p: ref to PsParser into int
```

 Ganchos que el parser de expresiones usa para entrar en statements,
 bloques y patrones.

 ## Memoria
 Los punteros a función no tienen heap propio.

### `PsParser`

> rune PsParser

```pengu
    src as ref to SourceFile
    bag as ref to DiagnosticBag
    lex as ref to LexResult
    opts as PsParseOptions
    pos as int
    depth as int
    block_depth as int
    errors as int
    panic as bool
    guard_mode as bool
    stop as bool
    last_error_pos as int
    root as int
    ast as PsAst
    child_stack as list of int
    marks as list of int
    hooks as PsHooks
```

 Estado mutable de un parseo.

 ## Memoria
 Sin destructor. `ast` se transfiere al `PsParseResult`; `child_stack` y
 `marks` se liberan con `free_scratch`.

### `PsParseResult`

> rune PsParseResult

```pengu
    ok as bool
    root as int
    ast as PsAst
    error_count as int
```

 Resultado de un parseo.

 ## Memoria
 `banish result` libera `ast`. El llamador conserva `SourceFile` y
 `LexResult` (el AST los referencia por índice).

### `_no_value_hook`

> **_no_value_hook**(p: ref to PsParser) -> int

 Stubs de hooks. No deberían ejecutarse si la API instaló los reales.

### `_no_when_hook`

> **_no_when_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_judge_hook`

> **_no_judge_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_do_hook`

> **_no_do_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_with_hook`

> **_no_with_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_or_hook`

> **_no_or_hook**(p: ref to PsParser, left: int) -> int

_Undocumented._

### `_no_body_hook`

> **_no_body_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_expr_hook`

> **_no_expr_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_list_expr_hook`

> **_no_list_expr_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_value_expr_hook`

> **_no_value_expr_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_list_value_hook`

> **_no_list_value_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_arg_expr_hook`

> **_no_arg_expr_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_expr_no_cast_hook`

> **_no_expr_no_cast_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_no_guard_hook`

> **_no_guard_hook**(p: ref to PsParser) -> int

_Undocumented._

### `_hook_missing`

> **_hook_missing**(p: ref to PsParser, name: string) -> int

 Emite un error interno de gancho y devuelve el nodo `error`.

 ## Memoria
 Crea un nodo `error`.

### `ps_parser_new`

> **ps_parser_new**(src: ref to SourceFile, bag: ref to DiagnosticBag, lex: ref to LexResult, opts: PsParseOptions) -> PsParser

 Construye un parser vacío.

 ## Memoria
 Asigna las listas del AST y las dos de trabajo; liberar con
 `free_scratch` + transferir/liberar `ast`.

### `ps_free_scratch`

> **ps_free_scratch**(p: ref to PsParser) -> void

 Libera las listas de trabajo del parser.

 El AST **no** se libera aquí: se transfiere al `PsParseResult`.

 ## Memoria
 Libera `child_stack` y `marks`.

### `ps_token_count`

> **ps_token_count**(p: ref to PsParser) -> int

 Número de tokens.

 ## Memoria
 O(1), no asigna.

### `ps_current_token`

> **ps_current_token**(p: ref to PsParser) -> Token

 Corrige el helper anterior: devuelve un EOF sintético sin tocar el AST.

 ## Memoria
 O(1), no asigna.

### `ps_peek_at`

> **ps_peek_at**(p: ref to PsParser, offset: int) -> Token

 Token a `offset` desde el actual, o EOF.

 ## Memoria
 O(1), no asigna.

### `ps_kind_at`

> **ps_kind_at**(p: ref to PsParser) -> TokenKind

 Tipo del token actual.

 ## Memoria
 O(1), no asigna.

### `ps_kind_ahead`

> **ps_kind_ahead**(p: ref to PsParser, offset: int) -> TokenKind

 Tipo del token a `offset`.

 ## Memoria
 O(1), no asigna.

### `ps_kw_at`

> **ps_kw_at**(p: ref to PsParser) -> KeywordKind

 Keyword del token actual (`KwNotKeyword` si no es keyword).

 ## Memoria
 O(1), no asigna.

### `ps_kw_at_offset`

> **ps_kw_at_offset**(p: ref to PsParser, offset: int) -> KeywordKind

 Keyword a `offset` desde el actual (`KwNotKeyword` si no es keyword).

 ## Memoria
 O(1), no asigna.

### `ps_current_start`

> **ps_current_start**(p: ref to PsParser) -> int

 Offset de inicio del token actual.

 ## Memoria
 O(1), no asigna.

### `ps_current_end`

> **ps_current_end**(p: ref to PsParser) -> int

 Offset de fin del token actual.

 ## Memoria
 O(1), no asigna.

### `ps_previous_end`

> **ps_previous_end**(p: ref to PsParser) -> int

 Offset de fin del último token consumido, o 0.

 ## Memoria
 O(1), no asigna.

### `ps_check`

> **ps_check**(p: ref to PsParser, k: TokenKind) -> bool

 `true` si el token actual es de tipo `k`.

 ## Memoria
 O(1), no asigna.

### `ps_check_kw`

> **ps_check_kw**(p: ref to PsParser, k: KeywordKind) -> bool

 `true` si el token actual es el keyword `k`.

 ## Memoria
 O(1), no asigna.

### `ps_check_lexeme`

> **ps_check_lexeme**(p: ref to PsParser, k: TokenKind, text: string) -> bool

 `true` si el token actual es el operador de `kind` con el lexema dado.

 ## Memoria
 O(1), no asigna.

### `ps_byte_at`

> **ps_byte_at**(p: ref to PsParser, offset: int) -> int

 Byte del fuente en `offset`, o `-1`.

 ## Memoria
 O(1), no asigna.

### `ps_check_word`

> **ps_check_word**(p: ref to PsParser, word: string) -> bool

 `true` si el token actual es el identificador/soft keyword `word`.

 No asigna string: compara el rango del token con el literal.

 ## Memoria
 O(len), no asigna.

### `ps_word_at`

> **ps_word_at**(p: ref to PsParser, offset: int, word: string) -> bool

 `true` si el token a `offset` es el identificador/soft keyword `word`.

 ## Memoria
 O(len), no asigna.

### `ps_check_name_like`

> **ps_check_name_like**(p: ref to PsParser) -> bool

 `true` si el token actual puede usarse como nombre de campo.

 Stage0 usa un lexer contextual: después de `.`/`->` un keyword duro puede
 ser un nombre de campo (`lex->antiquus`). PSC replica esa excepción solo en
 posiciones de acceso, no en declaraciones.

 ## Memoria
 O(1), no asigna.

### `ps_check_name_like_at`

> **ps_check_name_like_at**(p: ref to PsParser, offset: int) -> bool

 `true` si el token a `offset` puede usarse como nombre.

 ## Memoria
 O(1), no asigna.

### `ps_add_name_like`

> **ps_add_name_like**(p: ref to PsParser) -> void

 Añade el token actual como nombre de campo, o emite un error.

 ## Memoria
 O(1), no asigna.

### `ps_check_kw_or_word`

> **ps_check_kw_or_word**(p: ref to PsParser, k: KeywordKind, word: string) -> bool

 `true` si el token actual es el keyword `k` o el soft keyword `word`.

 ## Memoria
 O(len), no asigna.

### `ps_advance`

> **ps_advance**(p: ref to PsParser) -> Token

 Avanza un token y devuelve el token consumido.

 ## Memoria
 O(1), no asigna.

### `ps_accept`

> **ps_accept**(p: ref to PsParser, k: TokenKind) -> bool

 Acepta el token actual si es de tipo `k`.

 ## Memoria
 O(1), no asigna.

### `ps_accept_kw`

> **ps_accept_kw**(p: ref to PsParser, k: KeywordKind) -> bool

 Acepta el token actual si es el keyword `k`.

 ## Memoria
 O(1), no asigna.

### `ps_accept_word`

> **ps_accept_word**(p: ref to PsParser, word: string) -> bool

 Acepta un soft keyword identificador.

 ## Memoria
 O(len), no asigna.

### `ps_expect`

> **ps_expect**(p: ref to PsParser, k: TokenKind, detail: string) -> Token

 Consume el token actual o emite `ExpectedToken`.

 Devuelve el token consumido o el actual sin consumir si falla.

 ## Memoria
 O(1), no asigna.

### `ps_expect_kw`

> **ps_expect_kw**(p: ref to PsParser, k: KeywordKind, detail: string) -> Token

 Consume el keyword actual o emite `ExpectedToken`.

 ## Memoria
 O(1), no asigna.

### `ps_skip_error_tokens`

> **ps_skip_error_tokens**(p: ref to PsParser) -> void

 Salta tokens `TokError` del lexer. Sus diagnósticos ya están en el bag.

 ## Memoria
 O(1) por token saltado.

### `ps_skip_newlines`

> **ps_skip_newlines**(p: ref to PsParser) -> void

 Salta `NEWLINE` (y `TokError`) sin consumir `INDENT`/`DEDENT`.

 ## Memoria
 O(1) por token saltado.

### `ps_is_stmt_starter`

> **ps_is_stmt_starter**(p: ref to PsParser) -> bool

 `true` si el token actual es un starter de declaración/statement.

 Se usa para sincronizar sin saltarse el inicio del siguiente constructo.

 ## Memoria
 O(1), no asigna.

### `ps_emit_issue`

> **ps_emit_issue**(p: ref to PsParser, issue: ParseIssue, start: int, end: int, detail: string) -> void

 Emite un issue y aplica el tope de errores.

 No duplica un error exactamente en el mismo offset.

 ## Memoria
 El `DiagnosticBag` es dueño del diagnóstico.

### `ps_emit_here`

> **ps_emit_here**(p: ref to PsParser, issue: ParseIssue, detail: string) -> void

 Emite un error en el token actual.

 ## Memoria
 O(1), no asigna.

### `ps_synchronize`

> **ps_synchronize**(p: ref to PsParser) -> void

 Entra en modo pánico y avanza hasta un separador.

 No consume `DEDENT` ni el starter del siguiente constructo.

 ## Memoria
 O(tokens saltados).

### `ps_finish_statement`

> **ps_finish_statement**(p: ref to PsParser) -> void

 Exige fin de statement y sincroniza si falta.

 ## Memoria
 Puede consumir el `NEWLINE`.

### `ps_pre_scan_depth`

> **ps_pre_scan_depth**(p: ref to PsParser) -> bool

 Pre-scan de delimitadores antes de parsear.

 Replica B7: rechaza el token 513 de `(`/`[`/`{` con posición exacta. Los
 delimitadores dentro de strings/`antiquus` son un solo token, así que no
 cuentan.

 ## Retorno
 `false` si se superó el límite (ya emitió el diagnóstico).

 ## Memoria
 O(tokens), no asigna.

### `ps_enter_block`

> **ps_enter_block**(p: ref to PsParser) -> bool

 Entra en un bloque.

 ## Retorno
 `false` si se superó el límite (ya emitió el diagnóstico).

 ## Memoria
 O(1), no asigna.

### `ps_leave_block`

> **ps_leave_block**(p: ref to PsParser) -> void

 Sale de un bloque.

 ## Memoria
 O(1), no asigna.

### `ps_enter_depth`

> **ps_enter_depth**(p: ref to PsParser) -> bool

 Entra en un nivel de profundidad.

 ## Retorno
 `false` si se superó el límite (ya emitió el diagnóstico).

 ## Memoria
 O(1), no asigna.

### `ps_leave_depth`

> **ps_leave_depth**(p: ref to PsParser) -> void

 Sale de un nivel de profundidad.

 ## Memoria
 O(1), no asigna.

### `ps_begin_children`

> **ps_begin_children**(p: ref to PsParser) -> void

 Empieza a acumular hijos para un nodo.

 ## Memoria
 Hace `push` en `marks`.

### `ps_add_child`

> **ps_add_child**(p: ref to PsParser, id: int) -> void

 Añade un nodo hijo.

 ## Memoria
 Hace `push` en `child_stack`.

### `ps_add_token`

> **ps_add_token**(p: ref to PsParser, token_index: int) -> void

 Añade un token hijo.

 ## Memoria
 Hace `push` en `child_stack`.

### `ps_add_absent`

> **ps_add_absent**(p: ref to PsParser) -> void

 Añade un hijo ausente (`None`).

 ## Memoria
 Hace `push` en `child_stack`.

### `ps_finish_node`

> **ps_finish_node**(p: ref to PsParser, kind: NodeKind, start: int, end: int, aux: int) -> int

 Cierra el nodo actual y lo añade al AST.

 Copia los hijos acumulados desde la última marca, los hace contiguos en
 `ast.children`, crea el `PsNode` y limpia la pila de trabajo.

 ## Memoria
 Hace `push` en `ast.nodes` y `ast.children`; no asigna por nodo.

### `ps_leaf_token`

> **ps_leaf_token**(p: ref to PsParser, kind: NodeKind, token_index: int, start: int, end: int) -> int

 Crea un nodo hoja con un token hijo.

 ## Memoria
 Crea un nodo y un hijo.

### `ps_error_node`

> **ps_error_node**(p: ref to PsParser, start: int, end: int) -> int

 Crea un nodo `error` de recuperación.

 ## Memoria
 Crea un nodo sin hijos.

### `ps_into_result`

> **ps_into_result**(p: ref to PsParser, ok: bool) -> PsParseResult

 Convierte un `PsParser` en `PsParseResult`, liberando la pila de trabajo.

 ## Memoria
 Transfiere `ast`; libera `child_stack` y `marks`.

