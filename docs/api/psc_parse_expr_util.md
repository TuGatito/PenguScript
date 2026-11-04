# psc.parse.expr.util

> Source: `src/psc/parse/expr/util.pengu`

psc/parse/expr/util.pengu — helpers de nodos y spans para expresiones.

## Memoria
Construye nodos en el AST; no asigna strings.

---

### `pexpr_start_of`

> **pexpr_start_of**(p: ref to PsParser, id: int) -> int

 Inicio de un nodo, o el inicio del token actual si el nodo no existe.

 ## Memoria
 O(1), no asigna.

### `pexpr_end_of`

> **pexpr_end_of**(p: ref to PsParser, id: int) -> int

 Fin de un nodo, o el fin del token anterior si el nodo no existe.

 ## Memoria
 O(1), no asigna.

### `pexpr_binary`

> **pexpr_binary**(p: ref to PsParser, kind: NodeKind, left: int, op_index: int, right: int) -> int

 Construye un nodo binario con dos hijos.

 ## Memoria
 Crea un nodo `kind` con `left` y `right`.

### `pexpr_unary_node`

> **pexpr_unary_node**(p: ref to PsParser, kind: NodeKind, child: int, op_index: int, start: int) -> int

 Construye un nodo unario.

 ## Memoria
 Crea un nodo `kind` con un hijo.

