# psc.codegen.type_ast

> Source: `src/psc/codegen/type_ast.pengu`

psc/codegen/type_ast.pengu — conversión de un nodo de tipo AST a `TypeId`.

Vive fuera de `stmt`/`expr` para que ambos puedan usarla sin ciclos.

---

### `from_ast`

> **from_ast**(c: ref to CgContext, m: SemaModule, node: int) -> int

 Convierte un nodo de tipo AST usando el estado de F3.

 ## Memoria
 Puede añadir diagnósticos F3; no posee strings.

### `type_from_ast_subst`

> **type_from_ast_subst**(c: ref to CgContext, m: SemaModule, node: int) -> int

 Convierte un nodo de tipo AST a `TypeId` aplicando la sustitución actual
 (`c->names.subst`).  A diferencia de `from_ast`, sí instancia nominales
 cuyos argumentos contienen type params (`Pair of list of T and list of E`).

 ## Memoria
 Puede crear tipos internados; no posee strings.

### `c_type_ast`

> **c_type_ast**(c: ref to CgContext, m: SemaModule, node: int) -> string

 Tipo C de un nodo de tipo, resolviendo type params por sustitución.

 A diferencia de `from_ast`, no depende de que F3 tenga registrados los
 type params del `shard`; construye refs/base/nominales directamente.

 ## Memoria
 Devuelve string owned.

### `deep_token`

> **deep_token**(ast: ref to PsAst, node: int) -> int

 Primer token de un tipo compuesto.

 ## Memoria
 O(nodos).

