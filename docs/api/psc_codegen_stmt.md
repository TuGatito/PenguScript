# psc.codegen.stmt

> Source: `src/psc/codegen/stmt.pengu`

psc/codegen/stmt.pengu — statements C.

CP0 cubre returns, declaraciones locales, bloques y expresiones-statement.
El resto de statements se añade por subfases manteniendo `emit_stmt`.

---

### `type_from_ast`

> **type_from_ast**(c: ref to CgContext, m: SemaModule, node: int) -> int

 Convierte un nodo de tipo AST a `TypeId`.

 ## Memoria
 Puede añadir diagnósticos F3; no posee strings.

### `begin_scope`

> **begin_scope**(c: ref to CgContext, is_loop: bool) -> void

 Abre un scope C para `defer` y `break`/`continue`.

 ## Memoria
 Añade marcas POD al contexto.

### `end_scope`

> **end_scope**(c: ref to CgContext) -> void

 Emite los `defer` pendientes del scope actual y lo cierra.

 ## Memoria
 Vacía el tramo de defers; los nodos son del AST.

### `emit_block_body`

> **emit_block_body**(c: ref to CgContext, block: int) -> void

 Emite el cuerpo de un bloque sin abrir/cerrar scope C.

 ## Memoria
 Strings owned en cada línea.

### `emit_block`

> **emit_block**(c: ref to CgContext, block: int) -> void

 Emite un bloque de statements con su propio scope C.

 ## Memoria
 Strings owned en cada línea.

### `emit_loop_block`

> **emit_loop_block**(c: ref to CgContext, block: int) -> void

 Emite el cuerpo de un loop con scope marcado como loop.

 ## Memoria
 Strings owned en cada línea.

### `emit_stmt`

> **emit_stmt**(c: ref to CgContext, node: int) -> void

 Emite un statement.

 ## Memoria
 No posee el AST; libera strings temporales.

### `emit_expr_statement`

> **emit_expr_statement**(c: ref to CgContext, e2: int, ast: ref to PsAst) -> void

 Emite una expresión como statement, incluyendo las llamadas a métodos
 `@mutates` (que se asignan de vuelta al receptor).

 ## Memoria
 Strings owned.

### `emit_for_in`

> **emit_for_in**(c: ref to CgContext, node: int, ast: ref to PsAst) -> void

 Emite un `for var in start to end`.

 ## Memoria
 Strings owned.

### `emit_when_branch`

> **emit_when_branch**(c: ref to CgContext, node: int, ast: ref to PsAst) -> void

 Emite una rama de `when` (bloque o statement).

 ## Memoria
 Strings owned.

### `emit_when_stmt`

> **emit_when_stmt**(c: ref to CgContext, node: int, ast: ref to PsAst) -> void

 Emite un `when` comptime como statement.

 El AST tiene `cond` + N statements + `else` opcional; no asumir que el
 segundo hijo es el cuerpo y el tercero el `else` (ese supuesto perdía todas
 las sentencias intermedias).

 ## Memoria
 Strings owned; los nodos son del AST.

### `emit_if_binding`

> **emit_if_binding**(c: ref to CgContext, node: int, cond_node: int, ast: ref to PsAst, negate: bool) -> void

 Emite `if NAME as T is maybe:` / `unless ...`.

 El `maybe` se materializa una sola vez en un temporal para no evaluar dos
 veces la expresión, y el binding se declara dentro del bloque del `if`.

 ## Memoria
 Strings owned.

### `emit_if`

> **emit_if**(c: ref to CgContext, node: int, ast: ref to PsAst, negate: bool) -> void

 Emite un `if`/`unless`.

 ## Memoria
 Strings owned.

### `target_text`

> **target_text**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

 Texto C de un target de asignación simple.

 ## Memoria
 Devuelve string owned.

### `emit_pending_defers`

> **emit_pending_defers**(c: ref to CgContext) -> void

 Emite y vacía los `defer` del scope C actual, en orden LIFO.

 ## Memoria
 Vacía el tramo de defers; los nodos son del AST.

### `emit_all_defers`

> **emit_all_defers**(c: ref to CgContext) -> void

 Emite todos los `defer` pendientes (salida de función).

 ## Memoria
 Vacía la lista; los nodos son del AST.

### `emit_loop_exit_defers`

> **emit_loop_exit_defers**(c: ref to CgContext) -> void

 Emite los `defer` de los scopes que abandona un `break`/`continue`.

 Recorre de dentro hacia fuera hasta el loop más interno (incluido).

 ## Memoria
 Vacía el tramo de defers; los nodos son del AST.

### `emit_errdefers`

> **emit_errdefers**(c: ref to CgContext) -> void

 Emite los `errdefer` pendientes (ruta de error), en orden LIFO.

 ## Memoria
 Strings owned; los nodos son del AST.

### `emit_defer`

> **emit_defer**(c: ref to CgContext, node: int) -> void

 Emite un `defer` pendiente.

 ## Memoria
 Strings owned.

### `emit_destructure`

> **emit_destructure**(c: ref to CgContext, node: int, ast: ref to PsAst, vlist: int) -> void

 Emite `let (a, b) is expr` para una tupla.

 ## Memoria
 Strings owned.

### `decl_token`

> **decl_token**(ast: ref to PsAst, node: int) -> int

 Token del nombre de una declaración (`var` directo o `let` con lista).

 ## Memoria
 O(nodos).

### `is_type_node`

> **is_type_node**(ast: ref to PsAst, node: int) -> bool

 ¿Un nodo es un nodo de tipo?

 ## Memoria
 O(1).

### `emit_judge_stmt`

> **emit_judge_stmt**(c: ref to CgContext, node: int, ast: ref to PsAst) -> void

 Emite un `judge` usado como statement: ejecuta las ramas y efectos.

 ## Memoria
 Strings owned.

### `emit_judge_block_value`

> **emit_judge_block_value**(c: ref to CgContext, node: int, ast: ref to PsAst, rt: int) -> string

 Emite un `judge` cuyo cuerpo es un bloque, dejando el valor en un temporal.

 Se usa desde `emit_local` para no crear un ciclo `expr` -> `stmt`.

 ## Memoria
 Strings owned.

### `emit_local`

> **emit_local**(c: ref to CgContext, node: int, ast: ref to PsAst) -> void

 Emite una declaración local.

 ## Memoria
 Añade el local al contexto.

### `token_slot`

> **token_slot**(ast: ref to PsAst, node: int) -> int

 Primer slot de token de un nodo.

 ## Memoria
 O(nodos).

