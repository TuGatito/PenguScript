# psc.parse.stmt.values

> Source: `src/psc/parse/stmt/values.pengu`

psc/parse/stmt/values.pengu — constructos con valor.

Implementa los hooks `PsHooks.value`, `when`, `do_block`, `with_init`,
`or_block` y `when_body`. Vive por encima de `stmt/core` y `expr/ops`; el
parser de expresiones lo llama a través de `PsHooks`, así no hay imports
cíclicos.

## Memoria
Construye nodos en el AST; no asigna strings salvo diagnósticos.

---

### `pvalues_parse_value`

> **pvalues_parse_value**(p: ref to PsParser) -> int

 Hook `value`: `if`/`unless`/`while`/`for` en posición de valor.

 ## Memoria
 Construye el nodo correspondiente.

### `pvalues_parse_if`

> **pvalues_parse_if**(p: ref to PsParser) -> int

 Parsea `if` como expresión (`then`) o como statement con bloque.

 ## Memoria
 Construye `if_expr` o `if_stmt`.

### `pvalues_parse_for`

> **pvalues_parse_for**(p: ref to PsParser) -> int

 Parsea `for` como comprehension o como statement.

 ## Memoria
 Construye `for_comp` o delega en `pstmt_parse_for`.

### `pvalues_add_name`

> **pvalues_add_name**(p: ref to PsParser) -> void

 Añade el nombre del loop al nodo en construcción.

 ## Memoria
 O(1), no asigna.

### `pvalues_parse_when`

> **pvalues_parse_when**(p: ref to PsParser) -> int

 Hook `when`: `when ... then ... else ...` o `when ...:` statement.

 ## Memoria
 Construye `when_expr` o `when_stmt`.

### `pvalues_parse_do`

> **pvalues_parse_do**(p: ref to PsParser) -> int

 Hook `do_block`: `do:` como expresión.

 ## Memoria
 Crea un nodo `do_expr` con `stmt` hijos.

### `pvalues_parse_with_init`

> **pvalues_parse_with_init**(p: ref to PsParser) -> int

 Hook `with_init`: `with:` como expresión.

 ## Memoria
 Crea un nodo `with_init_expr` con `stmt` hijos.

### `pvalues_parse_or_block`

> **pvalues_parse_or_block**(p: ref to PsParser, left: int) -> int

 Hook `or_block`: `or:` con el lado izquierdo ya parseado.

 El parser de expresiones ya consumió `or`; el `:` sigue siendo actual.

 ## Memoria
 Crea un nodo `or_block`.

### `pvalues_parse_when_body`

> **pvalues_parse_when_body**(p: ref to PsParser) -> int

 Hook `when_body`: cuerpo de una cláusula `when ... -> ...`.

 ## Memoria
 Devuelve la expresión, o un `do_expr` con el bloque.

