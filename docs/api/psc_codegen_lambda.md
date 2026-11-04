# psc.codegen.lambda

> Source: `src/psc/codegen/lambda.pengu`

psc/codegen/lambda.pengu — funciones C para lambdas sin captura.

Las lambdas de PenguScript no capturan; se emiten como funciones `static`
de nivel superior con un nombre estable derivado de (módulo, nodo).

---

### `lambda_name`

> **lambda_name**(module_id: int, node: int) -> string

 Nombre C estable de una lambda.

 ## Memoria
 Devuelve string owned.

### `scan`

> **scan**(c: ref to CgContext, module_id: int, ast: ref to PsAst, node: int) -> void

 Recorre un nodo y registra lambdas.

 ## Memoria
 Añade a `c->lambdas`.

### `collect_lambdas`

> **collect_lambdas**(c: ref to CgContext) -> void

 Descubre todas las lambdas del programa.

 ## Memoria
 Añade a `c->lambdas`.

### `signature`

> **signature**(c: ref to CgContext, lam: CgLambda) -> string

 Firma C de una lambda.

 ## Memoria
 Strings owned.

### `emit_prototype`

> **emit_prototype**(c: ref to CgContext, lam: CgLambda) -> void

 Emite el prototipo de una lambda.

 ## Memoria
 Strings owned.

### `emit_body`

> **emit_body**(c: ref to CgContext, lam: CgLambda) -> void

 Emite el cuerpo de una lambda.

 ## Memoria
 Restaura el contexto del cuerpo anterior.

