# psc.codegen.drop

> Source: `src/psc/codegen/drop.pengu`

psc/codegen/drop.pengu — el lowering de liberar un valor, por tipo.

Una sola tabla para `banish`, `defer` y los `_pengu_cleanup_T` derivados:
cada tipo tiene UNA forma de liberarse y se ve en `psc emit-c`.

El modelo actual es de handles prestados: liberar un contenedor libera su
búfer, no sus elementos (§13.4 de `docs/LANGUAGE.md`). El bucle que libera
elementos entra cuando el contenedor pase a ser dueño de lo que guarda
(fase COW), porque sólo entonces el drop recursivo es seguro.

## Memoria
Emite C; los strings C que construye son owned.

---

### `cow_kind_of`

> **cow_kind_of**(c: ref to CgContext, ty: int) -> int

 Emite la liberación del valor que vive en `target`.

 `target` es una expresión C direccionable (`x`, `p->campo`,
 `xs.data[i]`). Un `TypeId` inválido o `-1` no emite nada: los tipos
 escalares no tienen nada que liberar.

 ## Memoria
 Emite C; los strings C que construye son owned.
 Clasifica un tipo de contenedor para el COW: 0 ninguno, 1 string, 2 list,
 3 map.  Con `--legacy-copy` (o `[build] legacy_copy`) devuelve 0: el
 compilador emite entonces la copia de handle de 0.51 y ninguna llamada
 `ensure_unique`, que es lo que necesita el autohospedaje durante la
 transicion.

 ## Memoria
 O(1).

### `emit_cow_share`

> **emit_cow_share**(c: ref to CgContext, kind: int, target: string) -> void

 Emite el `share` de COW del handle `target` (incrementa el contador o copia
 un alias legacy a un buffer propio).

 ## Memoria
 O(1) si ya es COW; O(n) al promocionar un valor legacy.

### `emit_cow_unique`

> **emit_cow_unique**(c: ref to CgContext, kind: int, target: string) -> void

 Emite el `ensure_unique` de COW: separa el buffer si el handle lo comparte.

 ## Memoria
 O(1) si es unico; O(n) si esta compartido.

### `emit_drop_value`

> **emit_drop_value**(c: ref to CgContext, ty: int, target: string) -> void

_Undocumented._

### `omen_has_payload`

> **omen_has_payload**(c: ref to CgContext, nominal: int) -> bool

 `true` si alguna variante del omen `nominal` lleva payload.

 ## Memoria
 No asigna.

### `note_move_source`

> **note_move_source**(c: ref to CgContext, node: int, ast: ref to PsAst) -> void

 Anota que el valor de `node` sale del binding que lo contiene.

 Un `Drop` se mueve al enlazarlo, asignarlo o devolverlo: el destructor del
 binding de origen no debe ejecutarse (el destino pasa a ser el dueño).

 ## Memoria
 Sin asignaciones.

### `emit_cow_promote_source`

> **emit_cow_promote_source**(c: ref to CgContext, kind: int, node: int, ast: ref to PsAst) -> void

 Promueve el búfer del binding origen de una copia COW.

 ## Memoria
 Si el binding es un `NdVarRef` de tipo lista/mapa, emite la promoción en
 sitio (`pengu_cow_*_promote`): el origen pasa a tener cabecera COW con
 `rc = 1` y la copia siguiente solo incrementa el contador (O(1)).

### `clone_value`

> **clone_value**(c: ref to CgContext, ty: int, dst: string, src: string) -> void

 Emite la copia profunda de un valor de `src` a `dst`.

 Es la pieza que hace de `.clone()` una copia de verdad: los búferes owned
 (strings, listas, mapas) se duplican y los runes con `derive Drop` se clonan
 recursivamente. Los tipos sin propiedad (`ref`, punteros, escalares) se
 copian tal cual.

 ## Memoria
 Emite C; los strings C que construye son owned.

### `consortium_kind_of`

> **consortium_kind_of**(c: ref to CgContext, ty: int) -> int

 Qué envoltorio de `std.consortium` es `ty`: 0 ninguno, 1 `Rc`, 2 `WeakRc`,
 3 `Arc`, 4 `WeakArc`.

 El compilador conoce estos cuatro nombres a propósito: son los únicos tipos
 con política de copia `share` (D11). Un `Rc of int` es un nominal
 instanciado (`Rc__int`) que comparte struct C con la plantilla, así que la
 comparación se hace sobre el nominal de la plantilla (`template_info`).

 ## Memoria
 No asigna; copia el nombre base al pool del contexto.

### `emit_consortium_drop`

> **emit_consortium_drop**(c: ref to CgContext, kind: int, ty: int, target: string, t: SemaType) -> void

 Emite la liberación de un `Rc`/`Arc`/`Weak`.

 El payload lo destruye `pengu_rc_release`/`pengu_arc_release` con el thunk
 que guardó `new` (el compilador emite `_pengu_rc_drop_<T>` por instancia),
 así que aquí no hace falta conocer `T`.

 ## Memoria
 Emite C; los strings C que construye son owned.

### `emit_drop_thunk_ptr`

> **emit_drop_thunk_ptr**(c: ref to CgContext, ty: int) -> string

 Expresión C con el destructor de `ty` con firma `void (void*)`, o
 `NULL` si el tipo no tiene nada que liberar.

 `Rc`/`Arc` guardan ese puntero en su cabecera, así que liberarlos no
 necesita conocer `T`.

 ## Memoria
 El string devuelto es owned.

### `emit_clone_thunk_ptr`

> **emit_clone_thunk_ptr**(c: ref to CgContext, ty: int) -> string

 Expresión C con la copia profunda de `ty` con firma
 `void (const void*, void*)`, o `NULL` si basta con `memcpy`.

 ## Memoria
 El string devuelto es owned.

