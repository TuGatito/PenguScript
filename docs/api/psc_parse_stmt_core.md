# psc.parse.stmt.core

> Source: `src/psc/parse/stmt/core.pengu`

psc/parse/stmt/core.pengu — statements, bloques y control de flujo.

Cubre `stmt` y `block` de la gramática. Los constructos que pueden usarse
como valor (`if`, `when`, `for`, `while`) también se implementan aquí; el
hook `PsHooks.value` los reutiliza desde `stmt/values.pengu`.

## Memoria
Construye nodos en el AST; no asigna strings salvo diagnósticos.

---

### `pstmt_parse_block_members`

> **pstmt_parse_block_members**(p: ref to PsParser) -> int

 Parsea el cuerpo de un bloque y añade sus `stmt` al nodo en construcción.

 ## Retorno
 Número de statements parseados.

 ## Memoria
 O(statements del bloque).

### `pstmt_parse_block`

> **pstmt_parse_block**(p: ref to PsParser) -> int

 Parsea `":"` + bloque.

 ## Memoria
 Crea un nodo `block` con `stmt` hijos.

### `pstmt_parse_block_into`

> **pstmt_parse_block_into**(p: ref to PsParser) -> void

 Parsea `":"` + bloque añadiendo los `stmt` directamente al nodo actual.

 Se usa en `weave`, `test`, `with_stmt`, `do:`, `with:` y `or:`.

 ## Memoria
 No crea nodo `block`; añade los `stmt` al nodo en construcción.

### `pstmt_parse_block_body`

> **pstmt_parse_block_body**(p: ref to PsParser) -> int

 Parsea el cuerpo de un bloque cuando el `:` ya se consumió.

 ## Memoria
 Crea un nodo `block` con `stmt` hijos.

### `pstmt_parse_block_body_into`

> **pstmt_parse_block_body_into**(p: ref to PsParser) -> void

 Parsea el cuerpo de un bloque (sin nodo `block`) cuando el `:` ya se consumió.

 ## Memoria
 Añade los `stmt` al nodo en construcción.

### `pstmt_check_multiple`

> **pstmt_check_multiple**(p: ref to PsParser) -> void

 Comprueba la regla de stage0 de “varios statements en una línea”.

 Se aplica a los starters duros `var`/`let`/`set`/`const`/`static`.

 ## Memoria
 No asigna.

### `pstmt_wrap_if_expr`

> **pstmt_wrap_if_expr**(p: ref to PsParser, start: int, inner: int) -> int

 Envuelve en `expr_stmt` un constructo que se usó como expresión.

 `if ... then ...` y `for ... then ...` producen `if_expr`/`for_comp`; en
 posición de statement stage0 los envuelve en `expr_stmt`.

 ## Memoria
 Crea un nodo `expr_stmt` si hace falta.

### `pstmt_parse_stmt`

> **pstmt_parse_stmt**(p: ref to PsParser) -> int

 Parsea un `stmt` completo y lo envuelve en el nodo `stmt`.

 ## Memoria
 Crea un nodo `stmt`.

### `pstmt_parse_stmt_inner`

> **pstmt_parse_stmt_inner**(p: ref to PsParser) -> int

 Despacha un statement sin envolverlo en `stmt`.

 ## Memoria
 Construye el nodo del statement.

### `pstmt_parse_decl_value`

> **pstmt_parse_decl_value**(p: ref to PsParser) -> int

 Parsea un valor de declaración: `indent_literal`, `with:` o `value_expr`.

 ## Memoria
 Construye el nodo del valor.

### `pstmt_parse_var`

> **pstmt_parse_var**(p: ref to PsParser) -> int

 Parsea `var NAME [as T] (is value | with:)`.

 ## Memoria
 Crea un nodo `var_decl`.

### `pstmt_parse_let`

> **pstmt_parse_let**(p: ref to PsParser) -> int

 Parsea `let nombres [as T] (is value | with:)`.

 ## Memoria
 Crea un nodo `let_decl`.

### `pstmt_parse_const`

> **pstmt_parse_const**(p: ref to PsParser) -> int

 Parsea `const NAME [as T] is value`.

 ## Memoria
 Crea un nodo `const_decl`.

### `pstmt_parse_static_var`

> **pstmt_parse_static_var**(p: ref to PsParser) -> int

 Parsea `static var NAME [as T] (is value | with:)`.

 ## Memoria
 Crea un nodo `static_var_decl`.

### `pstmt_add_name`

> **pstmt_add_name**(p: ref to PsParser, what: string) -> void

 Añade el nombre actual al nodo en construcción.

 ## Memoria
 O(1), no asigna.

### `pstmt_add_optional_type`

> **pstmt_add_optional_type**(p: ref to PsParser) -> void

 Añade `as type` o un hijo ausente.

 ## Memoria
 Crea el nodo de tipo si existe.

### `pstmt_parse_initializer_into`

> **pstmt_parse_initializer_into**(p: ref to PsParser) -> void

 Añade el inicializador (`is value` o `with:`) al nodo actual.

 ## Memoria
 Construye el valor.

### `pstmt_parse_var_names`

> **pstmt_parse_var_names**(p: ref to PsParser) -> int

 Parsea la lista de nombres de un `let`.

 Acepta `a, b` y `(a, b)`, como la gramática.

 ## Memoria
 Crea un nodo `var_name_list`.

### `pstmt_check_at_target`

> **pstmt_check_at_target**(p: ref to PsParser, target: int) -> void

 Detecta `set xs at n - 1 is v` y emite el diagnóstico específico de stage0.

 ## Memoria
 Construye y libera el detalle; el bag es dueño del diagnóstico.

### `pstmt_token_text`

> **pstmt_token_text**(p: ref to PsParser) -> string

 Texto del token actual.

 ## Memoria
 Devuelve un `string` owned; liberar con `banish`.

### `pstmt_parse_set`

> **pstmt_parse_set**(p: ref to PsParser) -> int

 Parsea `set target is value` o `set target OP value`.

 ## Memoria
 Crea `set_stmt` o `compound_set_stmt`.

### `pstmt_parse_set_target`

> **pstmt_parse_set_target**(p: ref to PsParser) -> int

 Parsea el target de un `set`.

 ## Memoria
 Crea `with_target`, `normal_target` o `essence_target`.

### `pstmt_parse_if_cond`

> **pstmt_parse_if_cond**(p: ref to PsParser) -> int

 Parsea la condición de un `if`, incluyendo la forma de binding.

 ## Memoria
 Crea `if_cond` o `if_cond_binding`.

### `pstmt_parse_if`

> **pstmt_parse_if**(p: ref to PsParser) -> int

 Parsea un `if` completo.

 ## Memoria
 Crea un nodo `if_stmt`.

### `pstmt_parse_if_tail`

> **pstmt_parse_if_tail**(p: ref to PsParser, start: int, cond: int) -> int

 Termina un `if` después de la condición.

 ## Memoria
 Crea `if_stmt` y opcionalmente `else_block`.

### `pstmt_parse_else_block`

> **pstmt_parse_else_block**(p: ref to PsParser) -> int

 Parsea `else ...`.

 ## Memoria
 Crea un nodo `else_block`.

### `pstmt_parse_unless`

> **pstmt_parse_unless**(p: ref to PsParser) -> int

 Parsea un `unless`.

 ## Memoria
 Crea un nodo `unless_stmt`.

### `pstmt_parse_while`

> **pstmt_parse_while**(p: ref to PsParser) -> int

 Parsea un `while`.

 ## Memoria
 Crea un nodo `while_stmt`.

### `pstmt_parse_for`

> **pstmt_parse_for**(p: ref to PsParser) -> int

 Parsea un `for` de rango o de colección.

 ## Memoria
 Crea `for_range_stmt` o `for_in_stmt`.

### `pstmt_parse_when_stmt`

> **pstmt_parse_when_stmt**(p: ref to PsParser) -> int

 Parsea un `when` statement y su `else`.

 ## Memoria
 Crea `when_stmt` y `when_else_plain`/`when_else_when`.

### `pstmt_parse_when_else`

> **pstmt_parse_when_else**(p: ref to PsParser) -> int

 Parsea el `else` de un `when` statement.

 ## Memoria
 Crea `when_else_plain` o `when_else_when`.

### `pstmt_parse_with_stmt`

> **pstmt_parse_with_stmt**(p: ref to PsParser) -> int

 Parsea `with target:` como statement.

 ## Memoria
 Crea `with_stmt` con `stmt` hijos.

### `pstmt_parse_unsafe`

> **pstmt_parse_unsafe**(p: ref to PsParser) -> int

 Parsea `unsafe:`.

 ## Memoria
 Crea `unsafe_stmt`.

### `pstmt_parse_defer`

> **pstmt_parse_defer**(p: ref to PsParser, kind: NodeKind) -> int

 Parsea `defer`/`errdefer`.

 ## Memoria
 Crea `defer_stmt`/`errdefer_stmt`.

### `pstmt_parse_banish`

> **pstmt_parse_banish**(p: ref to PsParser) -> int

 Parsea `banish expr`.

 ## Memoria
 Crea `banish_stmt`.

### `pstmt_parse_return`

> **pstmt_parse_return**(p: ref to PsParser) -> int

 Parsea `return [v, ...]`.

 ## Memoria
 Crea `return_stmt`.

### `pstmt_parse_break_continue`

> **pstmt_parse_break_continue**(p: ref to PsParser, kind: NodeKind) -> int

 Parsea `break [label]` / `continue [label]`.

 ## Memoria
 Crea `break_stmt`/`continue_stmt`.

### `pstmt_parse_labeled_loop`

> **pstmt_parse_labeled_loop**(p: ref to PsParser) -> int

 Parsea `label: for/while`.

 ## Memoria
 Crea el nodo del loop y registra la etiqueta en `PsAst.labels`.

### `pstmt_parse_expr_stmt`

> **pstmt_parse_expr_stmt**(p: ref to PsParser) -> int

 Parsea una expresión como statement.

 ## Memoria
 Crea `expr_stmt`.

### `pstmt_parse_simple_stmt`

> **pstmt_parse_simple_stmt**(p: ref to PsParser) -> int

 Parsea un `simple_stmt` de un bloque de una línea.

 ## Memoria
 Crea `continue_simple`, `break_simple`, `return_simple`, `set_simple`,
 `compound_set_simple` o `simple_stmt`.

### `pstmt_add_optional_label`

> **pstmt_add_optional_label**(p: ref to PsParser) -> void

 Añade un label opcional o `None`.

 ## Memoria
 O(1), no asigna.

