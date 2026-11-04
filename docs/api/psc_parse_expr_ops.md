# psc.parse.expr.ops

> Source: `src/psc/parse/expr/ops.pengu`

psc/parse/expr/ops.pengu — precedencia, operadores, llamadas y postfix.

Implementa la cadena de precedencia de `LANGUAGE.md` §6.1 tal como la
gramática real de stage0:

```text
or else / or return / or:  →  try  →  if/when/judge/for  →  or  →  and
  →  comparaciones  →  .. / to  →  |  →  &  →  ^  →  << >>  →  + -  →  * / %
  →  unarios  →  calling/postfix  →  átomos
```

`list_expr` corta antes de `or`/`and` booleanos: así `calling f with a and b`
se agrupa como `(calling f with a) and b`, igual que stage0, y F3 lo rechaza
con `E0005`.

## Memoria
Construye nodos en el AST; no asigna strings salvo diagnósticos.

---

### `pexpr_nested_expr`

> **pexpr_nested_expr**(p: ref to PsParser) -> int

 Pide una expresión completa al hook.

 ## Memoria
 O(1), no asigna.

### `pexpr_nested_list`

> **pexpr_nested_list**(p: ref to PsParser) -> int

 Pide una expresión de lista al hook.

 ## Memoria
 O(1), no asigna.

### `pexpr_nested_list_value`

> **pexpr_nested_list_value**(p: ref to PsParser) -> int

 Pide una expresión de lista de valor al hook.

 ## Memoria
 O(1), no asigna.

### `pexpr_parse_expr`

> **pexpr_parse_expr**(p: ref to PsParser) -> int

 Parsea `expr`.

 ## Memoria
 Construye el AST.

### `pexpr_parse_list_expr`

> **pexpr_parse_list_expr**(p: ref to PsParser) -> int

 Parsea `list_expr` (sin `and`/`or` booleanos).

 ## Memoria
 Construye el AST.

### `pexpr_parse_value_expr`

> **pexpr_parse_value_expr**(p: ref to PsParser) -> int

 Parsea `value_expr`: `if`/`unless`/`while`/`for` o `expr`.

 ## Memoria
 Construye el AST.

### `pexpr_parse_list_value_expr`

> **pexpr_parse_list_value_expr**(p: ref to PsParser) -> int

 Parsea `list_value_expr`: como `value_expr` pero con `list_expr`.

 ## Memoria
 Construye el AST.

### `pexpr_parse_list_or_else`

> **pexpr_parse_list_or_else**(p: ref to PsParser) -> int

 Parsea `list_or_else_expr` (sin `and`/`or` booleanos).

 ## Memoria
 Construye el AST.

### `pexpr_parse_list_try`

> **pexpr_parse_list_try**(p: ref to PsParser) -> int

 Parsea `list_try_expr`.

 ## Memoria
 Construye el AST.

### `pexpr_parse_or_else`

> **pexpr_parse_or_else**(p: ref to PsParser) -> int

 Parsea `or else`, `or return` y `or:`.

 ## Memoria
 Construye el nodo correspondiente.

### `pexpr_parse_try`

> **pexpr_parse_try**(p: ref to PsParser) -> int

 Parsea `try expr`.

 ## Memoria
 Construye un nodo `try_expr`.

### `pexpr_parse_bool_or`

> **pexpr_parse_bool_or**(p: ref to PsParser) -> int

 Parsea `bool_or_expr`.

 ## Memoria
 Construye nodos `bool_or`.

### `pexpr_parse_bool_and`

> **pexpr_parse_bool_and**(p: ref to PsParser) -> int

 Parsea `bool_and_expr`.

 ## Memoria
 Construye nodos `bool_and`.

### `pexpr_parse_comparison`

> **pexpr_parse_comparison**(p: ref to PsParser) -> int

 Parsea comparaciones, `is present/true/false` e `in`.

 ## Memoria
 Construye el nodo correspondiente.

### `pexpr_binary_op`

> **pexpr_binary_op**(p: ref to PsParser, kind: NodeKind, left: int) -> int

 Construye un binario consumiendo el operador actual.

 ## Memoria
 Crea el nodo y avanza.

### `pexpr_parse_range`

> **pexpr_parse_range**(p: ref to PsParser) -> int

 Parsea `..` y `to`.

 ## Memoria
 Construye `range_dotdot` o `to_expr`.

### `pexpr_parse_bit_or`

> **pexpr_parse_bit_or**(p: ref to PsParser) -> int

 Parsea `|`.

 ## Memoria
 Construye `bitwise_or`.

### `pexpr_parse_bit_and`

> **pexpr_parse_bit_and**(p: ref to PsParser) -> int

 Parsea `&`.

 ## Memoria
 Construye `bitwise_and`.

### `pexpr_parse_bit_xor`

> **pexpr_parse_bit_xor**(p: ref to PsParser) -> int

 Parsea `^`.

 ## Memoria
 Construye `bitwise_xor`.

### `pexpr_parse_shift`

> **pexpr_parse_shift**(p: ref to PsParser) -> int

 Parsea `<<` y `>>`.

 ## Memoria
 Construye `shl`/`shr`.

### `pexpr_parse_add`

> **pexpr_parse_add**(p: ref to PsParser) -> int

 Parsea `+` y `-`.

 ## Memoria
 Construye `add`/`sub`.

### `pexpr_parse_mul`

> **pexpr_parse_mul**(p: ref to PsParser) -> int

 Parsea `*`, `/` y `%`.

 ## Memoria
 Construye `mul`/`div`/`mod`.

### `pexpr_parse_expr_no_cast`

> **pexpr_parse_expr_no_cast**(p: ref to PsParser) -> int

 Parsea `expr_no_cast`.

 ## Memoria
 Construye comparaciones y operadores sin `to`/`is`/`in`.

### `pexpr_parse_logic_or_no_cast`

> **pexpr_parse_logic_or_no_cast**(p: ref to PsParser) -> int

 Nivel `|` de `expr_no_cast`.

 ## Memoria
 Construye `bitwise_or`.

### `pexpr_parse_logic_and_no_cast`

> **pexpr_parse_logic_and_no_cast**(p: ref to PsParser) -> int

 Nivel `&` de `expr_no_cast`.

 ## Memoria
 Construye `bitwise_and`.

### `pexpr_parse_xor_no_cast`

> **pexpr_parse_xor_no_cast**(p: ref to PsParser) -> int

 Nivel `^` de `expr_no_cast`.

 ## Memoria
 Construye `bitwise_xor`.

### `pexpr_parse_shift_no_cast`

> **pexpr_parse_shift_no_cast**(p: ref to PsParser) -> int

 Nivel `<<`/`>>` de `expr_no_cast`.

 ## Memoria
 Construye `shl`/`shr`.

### `pexpr_parse_add_no_cast`

> **pexpr_parse_add_no_cast**(p: ref to PsParser) -> int

 Nivel `+`/`-` de `expr_no_cast`.

 ## Memoria
 Construye `add`/`sub`.

### `pexpr_parse_mul_no_cast`

> **pexpr_parse_mul_no_cast**(p: ref to PsParser) -> int

 Nivel `*`/`/`/`%` de `expr_no_cast`.

 ## Memoria
 Construye `mul`/`div`/`mod`.

### `pexpr_parse_guard_expr`

> **pexpr_parse_guard_expr**(p: ref to PsParser) -> int

 Parsea una guarda de `when`.

 Usa la misma jerarquía que una expresión; la gramática de guardas es un
 subconjunto, pero aceptar de más aquí no cambia el AST de los casos válidos.

 ## Memoria
 Construye el AST.

