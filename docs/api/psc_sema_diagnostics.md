# psc.sema.diagnostics

> Source: `src/psc/sema/diagnostics.pengu`

psc/sema/diagnostics.pengu — fachada de diagnósticos semánticos.

F3 no reimplementa el renderizador: usa el `DiagnosticBag` de
`std.diagnostic` y las mismas convenciones de `psc/diagnostics.pengu`.
Cada emisión recibe el `SourceFile` del módulo, de modo que un bag compartido
por varios módulos conserva el archivo correcto en `Span.file`.

Los códigos son constantes `CODE_*` para que el checker no escriba literales
dispersos. `SEMA_ERRORS.md` documenta cada uno.

## Memoria
`emit_error`/`emit_warning` copian lo que el bag necesita; los mensajes
temporales los libera el llamador.

---

### `CODE_SYNTAX`

> **CODE_SYNTAX** : string

 ---------------------------------------------------------------------------
 Códigos semánticos
 ---------------------------------------------------------------------------

### `CODE_CONST_IN_WEAVE`

> **CODE_CONST_IN_WEAVE** : string

_Undocumented._

### `CODE_VAR_TOP_LEVEL`

> **CODE_VAR_TOP_LEVEL** : string

_Undocumented._

### `CODE_SELF_DOT`

> **CODE_SELF_DOT** : string

_Undocumented._

### `CODE_UNDEFINED`

> **CODE_UNDEFINED** : string

_Undocumented._

### `CODE_TYPE_MISMATCH`

> **CODE_TYPE_MISMATCH** : string

_Undocumented._

### `CODE_MUTABILITY`

> **CODE_MUTABILITY** : string

_Undocumented._

### `CODE_CONTROL_FLOW`

> **CODE_CONTROL_FLOW** : string

_Undocumented._

### `CODE_INTERP_PARSE`

> **CODE_INTERP_PARSE** : string

_Undocumented._

### `CODE_RETURN_TYPE`

> **CODE_RETURN_TYPE** : string

_Undocumented._

### `CODE_MEMORY_OP`

> **CODE_MEMORY_OP** : string

_Undocumented._

### `CODE_WITH_TARGET`

> **CODE_WITH_TARGET** : string

_Undocumented._

### `CODE_BUILDER`

> **CODE_BUILDER** : string

_Undocumented._

### `CODE_ARRAY_UNKNOWN`

> **CODE_ARRAY_UNKNOWN** : string

_Undocumented._

### `CODE_GENERIC_ARGS`

> **CODE_GENERIC_ARGS** : string

_Undocumented._

### `CODE_TYPE_PARAM_OUTSIDE`

> **CODE_TYPE_PARAM_OUTSIDE** : string

_Undocumented._

### `CODE_MANY_MULTIPLE`

> **CODE_MANY_MULTIPLE** : string

_Undocumented._

### `CODE_MANY_NOT_LAST`

> **CODE_MANY_NOT_LAST** : string

_Undocumented._

### `CODE_MANY_DEFAULT`

> **CODE_MANY_DEFAULT** : string

_Undocumented._

### `CODE_MANY_DECLARE`

> **CODE_MANY_DECLARE** : string

_Undocumented._

### `CODE_MAP_LITERAL_TYPE`

> **CODE_MAP_LITERAL_TYPE** : string

_Undocumented._

### `CODE_MULTIPLE_INSIGNIA`

> **CODE_MULTIPLE_INSIGNIA** : string

_Undocumented._

### `CODE_OMEN_DUP`

> **CODE_OMEN_DUP** : string

_Undocumented._

### `CODE_OMEN_PAYLOAD_VALUE`

> **CODE_OMEN_PAYLOAD_VALUE** : string

_Undocumented._

### `CODE_OMEN_CONST`

> **CODE_OMEN_CONST** : string

_Undocumented._

### `CODE_CONCEPT_SIG`

> **CODE_CONCEPT_SIG** : string

_Undocumented._

### `CODE_CONCEPT_MISSING`

> **CODE_CONCEPT_MISSING** : string

_Undocumented._

### `CODE_CONCEPT_BOUND`

> **CODE_CONCEPT_BOUND** : string

_Undocumented._

### `CODE_CONCEPT_OPERATOR`

> **CODE_CONCEPT_OPERATOR** : string

_Undocumented._

### `CODE_RITUAL_SELF`

> **CODE_RITUAL_SELF** : string

_Undocumented._

### `CODE_RITUAL_CALL`

> **CODE_RITUAL_CALL** : string

_Undocumented._

### `CODE_C_NAME`

> **CODE_C_NAME** : string

_Undocumented._

### `CODE_C_NAME_KIND`

> **CODE_C_NAME_KIND** : string

_Undocumented._

### `CODE_C_NAME_DUP`

> **CODE_C_NAME_DUP** : string

_Undocumented._

### `CODE_C_NAME_RESERVED`

> **CODE_C_NAME_RESERVED** : string

_Undocumented._

### `CODE_C_NAME_FIELD`

> **CODE_C_NAME_FIELD** : string

_Undocumented._

### `CODE_ARRAY_SIZE`

> **CODE_ARRAY_SIZE** : string

_Undocumented._

### `CODE_RANGE`

> **CODE_RANGE** : string

_Undocumented._

### `CODE_PRIVATE`

> **CODE_PRIVATE** : string

_Undocumented._

### `CODE_JUDGE_EXHAUSTIVE`

> **CODE_JUDGE_EXHAUSTIVE** : string

_Undocumented._

### `CODE_PRIMITIVE_METHOD`

> **CODE_PRIMITIVE_METHOD** : string

_Undocumented._

### `CODE_INFINITE_SIZE`

> **CODE_INFINITE_SIZE** : string

_Undocumented._

### `CODE_DANGLING`

> **CODE_DANGLING** : string

_Undocumented._

### `CODE_JSON_DERIVE`

> **CODE_JSON_DERIVE** : string

 `derive Json` mal formado: tipo/atributo/campo no soportado.

### `CODE_CONCEPT_DUP`

> **CODE_CONCEPT_DUP** : string

_Undocumented._

### `CODE_CHAIN`

> **CODE_CHAIN** : string

 Paso de cadena o pipe inválido (método/función equivocados).

### `CODE_ATTRIBUTE`

> **CODE_ATTRIBUTE** : string

_Undocumented._

### `CODE_CHAR_RANGE`

> **CODE_CHAR_RANGE** : string

_Undocumented._

### `CODE_STATIC_PLACEMENT`

> **CODE_STATIC_PLACEMENT** : string

_Undocumented._

### `CODE_TEST_NAME`

> **CODE_TEST_NAME** : string

_Undocumented._

### `CODE_C_FIELD_COLLISION`

> **CODE_C_FIELD_COLLISION** : string

_Undocumented._

### `CODE_MUTATES_EXPR`

> **CODE_MUTATES_EXPR** : string

_Undocumented._

### `CODE_MUTATES_ATTR`

> **CODE_MUTATES_ATTR** : string

_Undocumented._

### `CODE_MUTATES_GETTER`

> **CODE_MUTATES_GETTER** : string

_Undocumented._

### `CODE_DUP_LABEL`

> **CODE_DUP_LABEL** : string

_Undocumented._

### `CODE_DUP_TYPE`

> **CODE_DUP_TYPE** : string

_Undocumented._

### `CODE_NAMED_ARG`

> **CODE_NAMED_ARG** : string

 Argumento nombrado inválido (desconocido, duplicado o fuera de orden).

### `CODE_DEFAULT_ORDER`

> **CODE_DEFAULT_ORDER** : string

 Valor por defecto después de un parámetro sin él.

### `CODE_DEFAULT_VALUE`

> **CODE_DEFAULT_VALUE** : string

 Valor por defecto que no es constante o no encaja con el tipo.

### `CODE_BIND_COUNT`

> **CODE_BIND_COUNT** : string

 Desestructuración con cantidad de nombres o tipo incompatible.

### `WARN_TRANSMUTE`

> **WARN_TRANSMUTE** : string

_Undocumented._

### `WARN_ECHO_ACCESS`

> **WARN_ECHO_ACCESS** : string

_Undocumented._

### `WARN_UNREACHABLE`

> **WARN_UNREACHABLE** : string

_Undocumented._

### `WARN_SHADOW`

> **WARN_SHADOW** : string

_Undocumented._

### `WARN_DEPRECATED`

> **WARN_DEPRECATED** : string

_Undocumented._

### `WARN_UNSAFE`

> **WARN_UNSAFE** : string

_Undocumented._

### `WARN_RANGE`

> **WARN_RANGE** : string

_Undocumented._

### `sema_emit_error`

> **sema_emit_error**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, start: int, end: int, message: string, help: string, note: string) -> void

 Emite un error en `[start, end)` de `src`.

 `message`, `help` y `note` son prestados; `psdiag.sema_emit_error` copia lo que
 necesita. El bag pasa a ser dueño del diagnóstico.

 ## Memoria
 Asigna el diagnóstico; liberar el bag al final.

### `node_error`

> **node_error**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, node_start: int, node_end: int, message: string, help: string, note: string) -> void

 Emite un error sobre un nodo del AST.

 ## Memoria
 O(1); no asigna aparte del diagnóstico.

### `sema_emit_warning`

> **sema_emit_warning**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, start: int, end: int, message: string, help: string) -> void

 Emite un warning en `[start, end)`.

 `psdiag.sema_emit_warning` no acepta `note`; el código y el span son los datos
 estables que compara el oráculo.

 ## Memoria
 Asigna el diagnóstico; liberar el bag al final.

### `node_warning`

> **node_warning**(bag: ref to DiagnosticBag, src: ref to SourceFile, code: string, node_start: int, node_end: int, message: string, help: string) -> void

 Emite un warning sobre un nodo.

 ## Memoria
 O(1); no asigna aparte del diagnóstico.

### `char_range_message`

> **char_range_message**(codepoint: int) -> string

 Código de `E0057` para un char fuera del rango seguro de C.

 ## Memoria
 Devuelve un literal; no asigna.

