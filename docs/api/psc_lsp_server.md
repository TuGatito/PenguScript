# psc.lsp.server

> Source: `src/psc/lsp/server.pengu`

psc/lsp/server.pengu — servidor LSP mínimo (lifecycle + diagnósticos).

---

### `Document`

> rune Document

```pengu
    text as string
    version as int
    sema as ref to SemaResult
```

 Documento abierto.

### `State`

> rune State

```pengu
    tr as Transport
    docs as map of string to Document
    uris as list of string
    root as string
    exe as string
    std_dir as string
    inlay_enabled as bool
    inlay_sizes as bool
    inlay_types as bool
    semantic_enabled as bool
    ws_cache as JsonValue
    ws_ready as bool
    initialized as bool
    shutdown as bool
```

 Estado del servidor.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

 `true` si `s` empieza por `p`.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

### `collect_param_labels`

> **collect_param_labels**(inner: string, out: ref to list of string) -> void

 Añade a `out` las etiquetas de parámetro de `inner` (`a: int, b: int`).

 ## Memoria
 Cada etiqueta es un string owned (el llamador lo banea); `inner` se presta.

### `copy_id`

> **copy_id**(id: JsonRpcId) -> JsonRpcId

 Copia un id JSON-RPC.

### `send_msg`

> **send_msg**(st: ref to State, msg: JsonRpcMessage) -> bool

 Envía un mensaje.

### `send_method_error`

> **send_method_error**(st: ref to State, id: JsonRpcId, method: string) -> void

 Envía error de método.

### `severity_num`

> **severity_num**(sev: Severity) -> int

 Número de severidad LSP.

### `main_span`

> **main_span**(d: Diagnostic) -> maybe Span

 Primer span de un diagnóstico.

### `diag_json`

> **diag_json**(text: string, d: Diagnostic) -> JsonValue

 Construye un diagnóstico LSP.

### `jint`

> **jint**(v: JsonValue, key: string, dflt: int) -> int

 Publica diagnósticos para un documento.
 Extrae un int de un objeto.

### `jstr`

> **jstr**(v: JsonValue, key: string) -> string

 Extrae un string de un objeto.

### `subprocess_diag`

> **subprocess_diag**(text: string, o: JsonValue) -> JsonValue

 Convierte un diagnóstico de `psc check --diagnostics=json` a LSP.

### `free_doc`

> **free_doc**(d: ref to Document) -> void

 Libera el estado owned de un documento.

 ## Memoria
 Libera el `SemaResult` y el texto.

### `check_document`

> **check_document**(st: ref to State, document_uri: string, text: string) -> ref to SemaResult

 Chequea el texto y devuelve un `SemaResult` owned en heap.

 ## Memoria
 El llamador debe liberarlo con `free_doc`/`free_result`.

### `span_range`

> **span_range**(path: string, text: string, span: Span) -> JsonValue

 Rango LSP de un span, leyendo el fuente si el span es de otro archivo.

 ## Memoria
 Devuelve un `JsonValue` owned.

### `diag_to_lsp`

> **diag_to_lsp**(path: string, text: string, d: Diagnostic) -> JsonValue

 Construye un `Diagnostic` LSP con help/note y relatedInformation.

 ## Memoria
 Devuelve owned.

### `publish`

> **publish**(st: ref to State, document_uri: string, version: int, sr: ref to SemaResult) -> void

 Publica los diagnósticos de un resultado ya chequeado.

 ## Memoria
 `sr` sigue siendo propiedad del documento.

### `initialize_result`

> **initialize_result**() -> JsonValue

 Respuesta initialize.

### `handle_initialize`

> **handle_initialize**(st: ref to State, id: JsonRpcId, params: maybe JsonValue) -> void

 Responde initialize.

### `handle_shutdown`

> **handle_shutdown**(st: ref to State, id: JsonRpcId) -> void

 Responde shutdown.

### `field_string`

> **field_string**(v: JsonValue, key: string) -> string

 Obtiene un string de un objeto.

### `field_bool`

> **field_bool**(v: JsonValue, key: string, dflt: bool) -> bool

 Obtiene un bool de un objeto.

### `field_int`

> **field_int**(v: JsonValue, key: string, dflt: int) -> int

 Obtiene un int de un objeto.

### `did_open`

> **did_open**(st: ref to State, params: JsonValue) -> void

 didOpen.

### `did_change`

> **did_change**(st: ref to State, params: JsonValue) -> void

 didChange (incremental: `textDocumentSync.change = 2`).

### `did_close`

> **did_close**(st: ref to State, params: JsonValue) -> void

 didClose.

### `is_word`

> **is_word**(c: int) -> bool

 ¿Carácter de identificador?

### `remember_uri`

> **remember_uri**(st: ref to State, u: string) -> void

 Registra una URI abierta una sola vez.

### `doc_text`

> **doc_text**(st: ref to State, u: string) -> string

 Texto del documento abierto.

### `word_at`

> **word_at**(text: string, off: int) -> string

 Palabra bajo un offset.

### `doc_sema`

> **doc_sema**(st: ref to State, u: string) -> ref to SemaResult

 `SemaResult` de un documento abierto (`-1` no aplica; el llamador comprueba).

### `doc_module`

> **doc_module**(st: ref to State, u: string) -> int

 Módulo semántico de un documento abierto (`-1` si no).

### `is_type_symbol`

> **is_type_symbol**(sid_kind: SemaSymbolKind) -> bool

 `true` si el símbolo es de tipo nominal/estructura.

### `hover_type_details`

> **hover_type_details**(p: ref to SemaResult, sb: ref to StringBuilder, type_id: int) -> void

 Añade campos/variantes de un tipo nominal a un hover.

 ## Memoria
 No retiene; libera los strings auxiliares.

### `symbol_hover`

> **symbol_hover**(p: ref to SemaResult, sid: int) -> string

 Markdown de hover para un símbolo.

 ## Memoria
 Devuelve string owned.

### `keyword_doc`

> **keyword_doc**(w: string) -> string

 Documentación breve de keywords/tipos/operadores para hover.

### `in_literal`

> **in_literal**(m: SemaModule, off: int) -> bool

 `true` si el offset cae dentro de un string, char o comentario.

### `member_dot_before`

> **member_dot_before**(text: string, off: int) -> int

 Offset del punto/arrow antes del miembro bajo `off` (`-1` si no).

### `member_hover`

> **member_hover**(p: ref to SemaResult, mid: int, text: string, dot: int, name: string) -> string

 Markdown de hover para un miembro (`receptor.miembro`).

 ## Memoria
 Devuelve string owned; `""` si no hay nada que mostrar.

### `decl_line`

> **decl_line**(text: string, word: string) -> string

 Línea de una declaración que contiene `word`, o `""`.

### `handle_hover`

> **handle_hover**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Hover básico.

### `handle_definition`

> **handle_definition**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Definition semántica (local, misma archivo o std/módulo importado).

### `decl_name_line`

> **decl_name_line**(line: string) -> string

 Nombre declarado en una línea, o `""`.

### `decl_kind_line`

> **decl_kind_line**(line: string) -> int

 Kind LSP aproximado de una línea de declaración.

### `symbol_kind_lsp`

> **symbol_kind_lsp**(k: SemaSymbolKind) -> int

 Kind LSP de un símbolo para el outline.

### `handle_document_symbols`

> **handle_document_symbols**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Document symbols desde la tabla de símbolos.

### `ends_with`

> **ends_with**(s: string, suffix: string) -> bool

 `true` si `s` termina en `suffix`.

### `add_completion`

> **add_completion**(arr: ref to JsonValue, seen: ref to map of string to bool, label: string, kind: int, detail: string, insert: string, doc: string) -> void

 Añade una completion si no existe.

 ## Memoria
 Copia label/detail/insert/doc; no retiene los parámetros.

### `completion_kind`

> **completion_kind**(k: SemaSymbolKind) -> int

 Kind LSP de un símbolo.

### `add_symbol_completion`

> **add_symbol_completion**(p: ref to SemaResult, arr: ref to JsonValue, seen: ref to map of string to bool, sid: int, prefix: string) -> void

 Añade un símbolo semántico a la lista.

 ## Memoria
 Libera el texto de tipo.

### `module_stem`

> **module_stem**(name: string) -> string

 Stem de un archivo de módulo (`spark.pengu` -> `spark`).

### `add_std_modules`

> **add_std_modules**(p: ref to SemaResult, arr: ref to JsonValue, seen: ref to map of string to bool, prefix: string) -> void

 Añade los módulos `std.*` de los directorios configurados.

 ## Memoria
 Libera las listas de `read_dir`.

### `add_module_exports`

> **add_module_exports**(p: ref to SemaResult, arr: ref to JsonValue, seen: ref to map of string to bool, mid: int, prefix: string) -> void

 Añade exports de un módulo importado.

 ## Memoria
 Libera la lista de exports.

### `add_method_completions`

> **add_method_completions**(p: ref to SemaResult, arr: ref to JsonValue, seen: ref to map of string to bool, type_id: int, prefix: string) -> void

 Añade los métodos de encantamiento de un tipo.

 ## Memoria
 Libera la lista de ids y los textos auxiliares.

### `add_field_completions`

> **add_field_completions**(p: ref to SemaResult, arr: ref to JsonValue, seen: ref to map of string to bool, type_id: int, prefix: string) -> void

 Añade los campos de un `rune`/`echo`.

 ## Memoria
 Libera los nombres de campo ya copiados.

### `add_variant_completions`

> **add_variant_completions**(p: ref to SemaResult, arr: ref to JsonValue, seen: ref to map of string to bool, type_id: int, prefix: string) -> void

 Añade las variantes de un `omen`.

### `handle_completion`

> **handle_completion**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Completion semántica.

### `add_occurrence`

> **add_occurrence**(arr: ref to JsonValue, text: string, u: string, start: int, end: int) -> void

 Añade una Location de una ocurrencia.

### `handle_references`

> **handle_references**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 References basadas en símbolos (mismo `sid`, no texto plano).

### `handle_highlight`

> **handle_highlight**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Highlight del símbolo bajo el cursor (declaración vs lecturas).

### `indent_len`

> **indent_len**(line: string) -> int

 Indentación de una línea.

### `handle_folding`

> **handle_folding**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Folding por bloques con `:` e indentación.

### `handle_formatting`

> **handle_formatting**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Formatea con el `psc fmt` de F7.

### `handle_rename`

> **handle_rename**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Rename basado en símbolos: sólo edita identificadores que resuelven al
 mismo `sid` (no toca strings, comentarios ni homónimos de otro scope).

### `handle_prepare_rename`

> **handle_prepare_rename**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Prepare rename: valida que el cursor esté sobre un símbolo renombrable.

### `handle_implementation`

> **handle_implementation**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Implementation: reutiliza definition (métodos/tipos en F8.1).

### `handle_signature`

> **handle_signature**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Signature help: resuelve la llamada `calling f with a, b` bajo el cursor.

 Usa el símbolo semántico (no la línea de declaración) y cuenta las comas
 para calcular `activeParameter`.

### `handle_workspace_symbols`

> **handle_workspace_symbols**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Workspace symbols por escaneo de texto.

### `handle_code_lens`

> **handle_code_lens**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Code lens para `main` y tests.

### `SemToken`

> rune SemToken

```pengu
    start as int
    end as int
    ty as int
```

 Token semántico pendiente de ordenar.

### `add_sem`

> **add_sem**(xs: ref to list of SemToken, start: int, end: int, ty: int) -> void

 Añade un token semántico si tiene longitud.

### `sem_symbol_kind`

> **sem_symbol_kind**(si: SemaSymbol) -> int

 Kind semántico de un símbolo.

### `is_operator_token`

> **is_operator_token**(k: TokenKind) -> bool

 `true` si el token es un operador.

### `handle_semantic`

> **handle_semantic**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Semantic tokens desde el lexer/AST (UTF-16, sin adivinar).

### `line_of`

> **line_of**(text: string, off: int) -> int

 Línea (0-based) de un offset.

### `add_hint`

> **add_hint**(arr: ref to JsonValue, text: string, pos: int, label: string, kind: int, tooltip: string) -> void

 Añade un inlay hint.

### `handle_inlay`

> **handle_inlay**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Inlay hints: tipos inferidos en variables y tamaño de tipos nominales.

 Las variables no muestran tamaño (basta el hover); las declaraciones de
 tipo muestran `≈ N B` para que el layout sea visible sin abrir el hover.

### `handle_code_action`

> **handle_code_action**(st: ref to State, id: JsonRpcId, params: JsonValue) -> void

 Code actions: por ahora "Format document".

### `handle_request`

> **handle_request**(st: ref to State, id: JsonRpcId, method: string, params: maybe JsonValue) -> void

 Dispatch de request.

### `apply_configuration`

> **apply_configuration**(st: ref to State, params: JsonValue) -> void

 Dispatch de notification.
 Aplica settings en caliente (`workspace/didChangeConfiguration`).

### `handle_notification`

> **handle_notification**(st: ref to State, method: string, params: maybe JsonValue) -> void

_Undocumented._

### `run_with`

> **run_with**(tr: Transport, root: string, exe: string) -> int

 Bucle principal.

