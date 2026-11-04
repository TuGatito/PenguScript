# psc.parse.expr.calls

> Source: `src/psc/parse/expr/calls.pengu`

psc/parse/expr/calls.pengu — unarios, `calling`, postfix y argumentos.

## Memoria
Construye nodos en el AST; no asigna strings salvo diagnósticos.

---

### `pexpr_nested_list_value`

> **pexpr_nested_list_value**(p: ref to PsParser) -> int

 Pide una expresión de lista de valor al hook.

 ## Memoria
 O(1), no asigna.

### `pexpr_parse_unary`

> **pexpr_parse_unary**(p: ref to PsParser) -> int

 Parsea un unario completo.

 ## Memoria
 Construye el nodo correspondiente.

### `pexpr_parse_transmute`

> **pexpr_parse_transmute**(p: ref to PsParser) -> int

 Parsea `transmute expr to TYPE`.

 ## Memoria
 Construye un nodo `transmute`.

### `pexpr_parse_unary_no_cast`

> **pexpr_parse_unary_no_cast**(p: ref to PsParser) -> int

 Parsea un unario sin casts (`unary_no_cast`).

 ## Memoria
 Construye el nodo correspondiente.

### `pexpr_parse_postfix`

> **pexpr_parse_postfix**(p: ref to PsParser) -> int

 Parsea postfix con casts (`postfix`).

 ## Memoria
 Construye nodos `field_access`, `arrow_access`, `at_expr`,
 `slice_at_expr` y `length_expr`.

### `pexpr_parse_postfix_no_cast`

> **pexpr_parse_postfix_no_cast**(p: ref to PsParser) -> int

 Parsea postfix sin casts.

 ## Memoria
 Igual que `pexpr_parse_postfix`.

### `dot_after_newline`

> **dot_after_newline**(p: ref to PsParser) -> bool

 Indica si el `.` actual empieza una continuación de línea.

 ## Memoria
 O(1).

### `pexpr_postfix_tail`

> **pexpr_postfix_tail**(p: ref to PsParser, base: int) -> int

 Bucle común de postfix.

 ## Memoria
 Construye los nodos de acceso.

### `pexpr_parse_slice_range`

> **pexpr_parse_slice_range**(p: ref to PsParser, first: int) -> int

 Parsea el `to` de un slice (`first to second`).

 ## Memoria
 Construye un nodo `slice_range`.

### `pexpr_parse_calling`

> **pexpr_parse_calling**(p: ref to PsParser) -> int

 Parsea `calling target [of types] [with args]`.

 ## Memoria
 Construye un nodo `calling_expr`.

### `pexpr_parse_method_step`

> **pexpr_parse_method_step**(p: ref to PsParser) -> int

 Parsea un paso `.name [with args]` de una cadena de métodos.

 ## Memoria
 Construye un nodo `method_step`.

### `pexpr_parse_chain_tail`

> **pexpr_parse_chain_tail**(p: ref to PsParser, base: int) -> int

 Encadena pasos de método tras una llamada `calling`.

 ## Memoria
 Construye nodos `chain_expr`/`method_step`.

### `pexpr_parse_pipe_step`

> **pexpr_parse_pipe_step**(p: ref to PsParser) -> int

 Parsea un paso `pipe target [with args]` de una cadena de funciones.

 ## Memoria
 Construye un nodo `pipe_step`.

### `pexpr_parse_pipe_tail`

> **pexpr_parse_pipe_tail**(p: ref to PsParser, base: int) -> int

 Encadena pasos `pipe` tras una expresión.

 ## Memoria
 Construye nodos `chain_expr`/`pipe_step`.

### `pexpr_parse_normal_target`

> **pexpr_parse_normal_target**(p: ref to PsParser) -> int

 Parsea `NAME/self` seguido de accesos.

 ## Memoria
 Construye un nodo `normal_target`.

### `pexpr_parse_with_target`

> **pexpr_parse_with_target**(p: ref to PsParser) -> int

 Parsea `. NAME` seguido de accesos (`with_target`).

 ## Memoria
 Construye un nodo `with_target`.

### `pexpr_parse_access_ops`

> **pexpr_parse_access_ops**(p: ref to PsParser) -> void

 Añade accesos `.`, `->` y `at` al nodo actual.

 ## Memoria
 Añade hijos al nodo en construcción.

### `pexpr_parse_generic_args`

> **pexpr_parse_generic_args**(p: ref to PsParser) -> int

 Parsea `of type (,|and type)*`.

 ## Memoria
 Construye un nodo `generic_args`.

### `pexpr_parse_arg_list`

> **pexpr_parse_arg_list**(p: ref to PsParser) -> int

 Parsea `with arg (, arg)*`.

 ## Memoria
 Construye un nodo `arg_list`.

### `pexpr_parse_arg`

> **pexpr_parse_arg**(p: ref to PsParser) -> int

 Parsea un argumento posicional o nombrado.

 ## Memoria
 Construye `pos_arg` o `named_arg`.

