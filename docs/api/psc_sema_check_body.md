# psc.sema.check.body

> Source: `src/psc/sema/check/body.pengu`

psc/sema/check/body.pengu — checker de statements y bloques.

Pass 2. Instala los hooks hacia `infer` y valida declaraciones locales,
asignaciones, retornos, control de flujo, `with`, `defer`/`banish` y
llamadas. Las expresiones se delegan a `infer`.

## Memoria
Presta `SemaState`; los scopes/símbolos son tablas del programa.

---

### `install`

> **install**(s: ref to SemaState) -> void

 Instala los hooks del checker.

 ## Memoria
 Punteros a función; sin heap.

### `check_weave_body`

> **check_weave_body**(s: ref to SemaState, node: int) -> void

 Chequea el cuerpo de un `weave`/`enchanting`/`antiquus`.

 ## Memoria
 Entra/sale de un scope; no libera tablas.

### `body_type_has_drop`

> **body_type_has_drop**(s: ref to SemaState, ty: int) -> bool

 `true` si el tipo es una runa con `derive Drop` (siguiendo alias y seals).

 ## Memoria
 O(profundidad del alias).

### `define_params`

> **define_params**(s: ref to SemaState, pnode: int) -> void

 Define los parámetros en el scope actual.

 ## Memoria
 Añade símbolos.

### `check_block`

> **check_block**(s: ref to SemaState, node: int) -> void

 Chequea un bloque o un `stmt`.

 ## Memoria
 Recorre hijos; no asigna.

### `check_block_value`

> **check_block_value**(s: ref to SemaState, node: int, expected: int) -> int

 Tipo de un bloque como valor.

 ## Memoria
 O(1) salvo chequeo.

### `apply_symbol_bounds`

> **apply_symbol_bounds**(s: ref to SemaState, sid: int) -> void

 Aplica los bounds de un símbolo al scope actual.

 ## Memoria
 O(1); no asigna.

### `decl_text`

> **decl_text**(s: ref to SemaState, node: int) -> string

 Texto del nombre de una declaración.

 ## Memoria
 Devuelve string owned.

### `check_module_bodies`

> **check_module_bodies**(s: ref to SemaState) -> void

 Chequea los cuerpos de un módulo ya recolectado.

 ## Memoria
 Presta el estado; los scopes se abren/cierran.
 Comprueba declaraciones y cuerpos de un módulo.

### `check_stmt`

> **check_stmt**(s: ref to SemaState, node: int) -> void

 Chequea un statement.

 ## Memoria
 Puede emitir diagnósticos.

### `check_local`

> **check_local**(s: ref to SemaState, node: int, kind: NodeKind) -> void

 Declaración local.

 ## Memoria
 Añade un símbolo al scope actual.

### `check_set`

> **check_set**(s: ref to SemaState, node: int, compound: bool) -> void

 `set target is value`.

 ## Memoria
 Comprueba mutabilidad y tipo.

### `target_type`

> **target_type**(s: ref to SemaState, node: int) -> int

 Tipo de un target de asignación.

 ## Memoria
 O(1) para nombres; campos se infieren.

### `frozen_target`

> **frozen_target**(s: ref to SemaState, tid: int) -> bool

 Tipo apuntado congelado (`frozen T` o `ref to frozen T`).

 ## Memoria
 O(1).

### `check_mutable_target`

> **check_mutable_target**(s: ref to SemaState, node: int) -> void

 Comprueba que el target sea mutable.

 ## Memoria
 O(1).

### `escape_unwrap`

> **escape_unwrap**(ast: ref to PsAst, node: int) -> int

 Desenvuelve parens y statements hasta la expresión real.

 ## Memoria
 O(1).

### `local_addr_root`

> **local_addr_root**(s: ref to SemaState, node: int, depth: int) -> bool

 `true` si la expresión es la dirección de una variable local mutable.

 ## Memoria
 O(profundidad).

### `target_root`

> **target_root**(ast: ref to PsAst, node: int) -> int

 Raíz de un target de asignación (desenvuelve campo/índice).

 ## Memoria
 O(1).

### `var_escapes_local`

> **var_escapes_local**(s: ref to SemaState, sv: SemaSymbol, depth: int) -> bool

 `true` si una variable local contiene una dirección que escapa.

 ## Memoria
 O(nodos del AST).

### `expr_escapes_local`

> **expr_escapes_local**(s: ref to SemaState, node: int, depth: int) -> bool

 `true` si la expresión devuelve una dirección de la pila local.

 ## Memoria
 O(nodos).

### `check_dangling_return`

> **check_dangling_return**(s: ref to SemaState, e: int) -> void

 Diagnostica un retorno de dirección local.

 ## Memoria
 O(nodos).

### `check_return`

> **check_return**(s: ref to SemaState, node: int) -> void

 `return expr`.

 ## Memoria
 O(1).

### `begin_loop`

> **begin_loop**(s: ref to SemaState, node: int) -> void

 Control de flujo.

 ## Memoria
 Recurre a bloques.
 Entra en el scope de un loop y registra su label.

 ## Memoria
 Push de scope; liberar con `end_loop`.

### `end_loop`

> **end_loop**(s: ref to SemaState, node: int) -> void

 Sale del scope del loop.

 ## Memoria
 Pop de scope.

### `loop_visible`

> **loop_visible**(s: ref to SemaState) -> bool

 ¿Hay un loop visible o un label concreto?

 ## Memoria
 O(profundidad).

### `find_loop_label`

> **find_loop_label**(s: ref to SemaState, nid: int) -> bool

 Busca un label de loop visible.

 ## Memoria
 O(profundidad).

### `check_break`

> **check_break**(s: ref to SemaState, node: int) -> void

 Comprueba `break`/`continue` y su label.

 ## Memoria
 O(profundidad); puede emitir diagnósticos.

### `check_control`

> **check_control**(s: ref to SemaState, node: int) -> void

 Entra en el scope de un loop y registra su label.

### `check_with_stmt`

> **check_with_stmt**(s: ref to SemaState, node: int) -> void

 `with target:` statement.

 ## Memoria
 Entra en un scope `with`.

### `check_lambda`

> **check_lambda**(s: ref to SemaState, node: int) -> int

 Lambda: construye y comprueba la firma, y devuelve su tipo `weave`.

 ## Memoria
 O(1).

### `variant_has_name`

> **variant_has_name**(s: ref to SemaState, omen_info: int, vname: int) -> bool

 ¿El omen tiene una variante con ese nombre?

 ## Memoria
 O(variantes).

### `variant_has_field`

> **variant_has_field**(s: ref to SemaState, omen_info: int, vname: int, fname: int) -> bool

 ¿La variante `vname` tiene un campo `fname`?

 ## Memoria
 O(variantes * campos).

### `add_covered_pattern`

> **add_covered_pattern**(s: ref to SemaState, pat: int, covered: ref to list of int) -> void

 Añade a `covered` las variantes del patrón `when A | B | ...`.

 ## Memoria
 O(tokens); no asigna.

### `contains_int`

> **contains_int**(xs: ref to list of int, v: int) -> bool

 ¿La lista de ints contiene `v`?

 ## Memoria
 O(n).

### `check_judge`

> **check_judge**(s: ref to SemaState, node: int, expected: int) -> int

 `judge`: comprueba condiciones, payloads y ramas; devuelve el tipo común.

 ## Memoria
 O(1).

### `check_with`

> **check_with**(s: ref to SemaState, node: int, expected: int) -> int

 `with:` builder como expresión.

 Abre un scope `with` con el tipo esperado (o `any` si no hay contexto) y
 chequea los statements del cuerpo, igual que `check_with_stmt`. Sin esto los
 valores del builder nunca se infieren: una lambda asignada a un campo queda
 sin tipo y el codegen no emite su prototipo ni su cuerpo.

 ## Memoria
 Push/pop de scope; recurre a los statements.

### `body_name_slot`

> **body_name_slot**(s: ref to SemaState, node: int) -> int

 Primer token de un nodo.

 ## Memoria
 O(n).

### `body_type_ctx`

> **body_type_ctx**(s: ref to SemaState) -> TypeCtx

 Contexto de tipos.

 ## Memoria
 Valor puro.

### `mismatch`

> **mismatch**(s: ref to SemaState, node: int, expected: int, got: int) -> void

 Emite un mismatch con el nombre canónico de ambos tipos.

 ## Memoria
 O(1).

