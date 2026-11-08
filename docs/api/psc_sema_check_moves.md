# psc.sema.check.moves

> Source: `src/psc/sema/check/moves.pengu`

psc/sema/check/moves.pengu — move-by-default para tipos con destructor.

Un valor de un rune `derive Drop` tiene un dueño y se mueve: al enlazarlo,
asignarlo o devolverlo, el binding de origen deja de ser válido. El checker
marca el símbolo movido (`SYM_DROP_MOVED`) y cualquier lectura posterior es
`E0080`; mover desde un sitio prestado (un parámetro, un campo de otro
valor, un `ref`) es `E0081`.

Es un análisis intra-procedural y conservador: no hay lifetimes ni préstamos
que sobrevivan al scope. Lo que no se puede mover se copia con `.clone()`.

## Memoria
Sin destructor; sólo toca la tabla de símbolos y el bag.

---

### `type_is_drop`

> **type_is_drop**(s: ref to SemaState, ty: int) -> bool

 `true` si el tipo declara `derive Drop` (siguiendo alias y seal).

 ## Memoria
 O(1).

### `mark_moved`

> **mark_moved**(s: ref to SemaState, sid: int) -> void

 Marca el símbolo como movido (si aún no lo estaba).

 ## Memoria
 Sin asignaciones.

### `consume_value`

> **consume_value**(s: ref to SemaState, vnode: int) -> void

 Consume un valor `Drop` en un contexto de movimiento.

 `vnode` es la expresión que se enlaza, asigna o devuelve. Si es un binding
 local, queda movido; si vive en un sitio prestado, es `E0081`.

 ## Memoria
 Puede emitir un diagnóstico.

### `check_moved_use`

> **check_moved_use**(s: ref to SemaState, sv: SemaSymbol, at_node: int, name: string) -> bool

 Comprueba que un valor `Drop` no se use después de moverse.

 ## Memoria
 Puede emitir un diagnóstico.

### `SHARE_NAMES`

> **SHARE_NAMES** : string

 Nombres base de los handles de `std.consortium` que se copian compartiendo
 (la copia retiene; no es un movimiento).

### `type_is_share`

> **type_is_share**(s: ref to SemaState, ty: int) -> bool

 `true` si `ty` es un handle `Rc`/`WeakRc`/`WeakArc`.

 ## Memoria
 Compara nombres; no asigna.

### `consortium_kind`

> **consortium_kind**(s: ref to SemaState, ty: int) -> int

 Clase de handle de `std.consortium` de un tipo.

 `0` no es un handle, `1` `Rc`, `2` `WeakRc`, `3` `Arc`, `4` `WeakArc`.

### `arc_payload_shared`

> **arc_payload_shared**(s: ref to SemaState, ty: int) -> bool

 Comprueba que el payload de un `Arc of T` / `WeakArc of T` sea `@shared`.

