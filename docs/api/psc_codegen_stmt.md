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

### `block_value`

> **block_value**(c: ref to CgContext, node: int, expected: int) -> string

 Reduce un bloque (`block`/`do_expr`) en posición de valor a una expresión C.

 Emite las sentencias del bloque dentro de una statement expression GNU
 (`__extension__(({ … }))`) y devuelve el valor de la última expresión.
 Lo instala `bundle` en `c->block_value` para evitar el ciclo expr→stmt.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

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

### `simple_place_text`

> **simple_place_text**(txt: string) -> bool

 Texto C de un target de asignación simple.

 ## Memoria
 Devuelve string owned.
 `true` si `txt` es un nombre simple de variable local (sin `.`, `->`, `[`,
 `(` ni espacios). Se usa para decidir si un `set` puede liberar el valor
 anterior: un campo o un elemento pueden ser memoria sin inicializar.

### `target_text`

> **target_text**(c: ref to CgContext, node: int, ast: ref to PsAst) -> string

_Undocumented._

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

### `emit_pending_drops`

> **emit_pending_drops**(c: ref to CgContext) -> void

 Emite los destructores automáticos pendientes del scope actual.

 Va después de los `defer` del mismo scope: lo escrito a mano corre primero
 y el destructor automático cierra lo que quedó vivo.

 ## Memoria
 Vacía el tramo de drops.

### `emit_all_drops`

> **emit_all_drops**(c: ref to CgContext) -> void

 Emite todos los destructores automáticos pendientes (salida de función).

 ## Memoria
 O(n); no vacía la lista (el `return` termina el cuerpo).

### `emit_loop_exit_drops`

> **emit_loop_exit_drops**(c: ref to CgContext) -> void

 Emite los destructores de los scopes que abandona un `break`/`continue`.

 ## Memoria
 O(n); no vacía la lista (los scopes lo harán al cerrarse).

### `emit_one_drop`

> **emit_one_drop**(c: ref to CgContext, idx: int) -> void

 Emite el destructor de una entrada de `drop_names` (`type = -1` = movida).

 ## Memoria
 C owned; el nombre se copia para el emisor.

### `loop_label_c`

> **loop_label_c**(c: ref to CgContext, ast: ref to PsAst, node: int) -> string

 Nombre C de la etiqueta del loop (`""` si no tiene).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `emit_loop_mark`

> **emit_loop_mark**(c: ref to CgContext, lbl: string) -> void

 Declara usadas las etiquetas `break`/`continue` de un loop etiquetado.

 Un `goto` muerto bajo `if (0)` evita `-Wunused-label` sin cambiar la
 semántica; sólo se emite para loops que declaran etiqueta.

 ## Memoria
 Strings owned.

### `emit_continue_label`

> **emit_continue_label**(c: ref to CgContext, lbl: string) -> void

 Emite la etiqueta `continue` al final del cuerpo de un loop con etiqueta.

 ## Memoria
 Strings owned.

### `emit_loop_close`

> **emit_loop_close**(c: ref to CgContext, lbl: string) -> void

 Cierra el `}` del loop y emite su etiqueta `break` si se usa.

 Sólo se emite la etiqueta si el cuerpo tiene un `break label`/`continue
 label` que la nombre: una etiqueta sin usar dispara `-Wunused-label` y los
 goldens compilan con `-Werror`.

 ## Memoria
 Strings owned.

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

### `emit_judge_body`

> **emit_judge_body**(c: ref to CgContext, body: int, ast: ref to PsAst) -> void

 Emite el cuerpo de un brazo de `judge` (bloque, retorno o sentencia).

 ## Memoria
 Strings owned; el cuerpo es del AST.

### `judge_bind_payload`

> **judge_bind_payload**(c: ref to CgContext, st: int, payload: int, ast: ref to PsAst, stmp: string, variant: string) -> void

 Enlaza los campos del payload de un brazo en el scope actual.

 ## Memoria
 Strings owned; los nombres son del pool.

### `emit_judge_arm_body`

> **emit_judge_arm_body**(c: ref to CgContext, body: int, ast: ref to PsAst, vty: int, vtmp: string) -> void

 Emite el cuerpo de un brazo de `judge`.

 Con `vty > 0` deja el valor de la rama en `vtmp` (modo valor). Con
 `vty <= 0` ejecuta el brazo como sentencia; si la función devuelve algo,
 la última expresión del brazo se convierte en `return`.

 ## Memoria
 Strings owned; el AST es del programa.

### `judge_case_label`

> **judge_case_label**(c: ref to CgContext, st: int, tk: int, ast: ref to PsAst) -> string

 Etiqueta C de `case` para un token de patrón.

 Los números se emiten tal cual; las variantes se traducen al nombre C
 del omen. Debe llamarse sólo con sujetos conmutables (`switch`).

 ## Memoria
 Strings owned.

### `emit_judge_core`

> **emit_judge_core**(c: ref to CgContext, node: int, ast: ref to PsAst, vty: int, vtmp: string) -> void

 Emite el despacho de un `judge` (sentencia o valor).

 Sujetos `string` y brazos con guarda se emiten como cadena de `if` con
 `expr.judge_cond_c` (no hay `switch` sobre cadenas). El resto usa
 `switch` con una etiqueta por variante de la alternancia.

 ## Memoria
 Strings owned; el AST es del programa.

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

### `is_share_type`

> **is_share_type**(c: ref to CgContext, ty: int) -> bool

 `true` si el tipo es una runa con `derive Drop` (siguiendo alias y seals).

 ## Memoria
 O(profundidad del alias).
 `true` si `ty` es un handle que se copia compartiendo (`Rc`/`Weak*`).

 ## Memoria
 No asigna.

### `value_is_place`

> **value_is_place**(c: ref to CgContext, node: int, ast: ref to PsAst) -> bool

 `true` si la expresión es una referencia a una variable/parámetro (un
 préstamo que hay que retener al copiarlo a un `Rc`/`Weak`).

 ## Memoria
 No asigna.

### `share_assigned`

> **share_assigned**(c: ref to CgContext, ty: int, vnode: int, ast: ref to PsAst, target: string) -> void

 Emite el `share` de COW cuando el valor asignado viene de un lugar (otra
 variable).  Un temporal (`f(...)`, `a + b`, un literal) ya es dueño único y
 no necesita contador.

 ## Memoria
 O(1) si ya es COW; O(n) al promocionar un valor legacy.

### `is_drop_type`

> **is_drop_type**(c: ref to CgContext, ty: int) -> bool

_Undocumented._

### `register_local`

> **register_local**(c: ref to CgContext, nid: int, ty: int, cnode: int) -> void

 Registra un local y, si su tipo es `Drop`, su destructor automático.

 ## Memoria
 Añade a `locals` y a las pilas de drops.

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

