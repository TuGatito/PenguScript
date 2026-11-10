# psc.sema.types.embeds

> Source: `src/psc/sema/types/embeds.pengu`

psc/sema/types/embeds.pengu — promoción de campos de `fundere`.

Un embed es un `SemaField` con `FIELD_EMBED` en el prefijo de campos del
host, así que la promoción es pura resolución de nombres sobre esa tabla:
nada de vtable ni de tipos nuevos. Este módulo solo depende de la tabla de
tipos (no de `SemaState`) para que el codegen use exactamente la misma
resolución que el checker.

## Memoria
`route_into` y `field_type_via` no asignan si no se les pasa una ruta; las
rutas usan listas owned del llamador.

---

### `ROUTE_FOUND`

> **ROUTE_FOUND** : int

 El campo se alcanza (la ruta quedó en `path`).

### `ROUTE_NONE`

> **ROUTE_NONE** : int

 El campo no existe en el tipo ni en sus embeds.

### `ROUTE_AMBIGUOUS`

> **ROUTE_AMBIGUOUS** : int

 El campo existe en más de un embed: hace falta la ruta explícita.

### `unwrap`

> **unwrap**(t: ref to SemaTypeTable, ty: int) -> int

 Desenvuelve alias/seal (no `ref`).

 ## Memoria
 O(profundidad); no asigna.

### `own_field_index`

> **own_field_index**(t: ref to SemaTypeTable, ty: int, nid: int) -> int

 Índice del campo propio `nid` en `ty` (rune/echo), o `-1`.

 ## Memoria
 No asigna.

### `own_field_type`

> **own_field_type**(t: ref to SemaTypeTable, ty: int, nid: int) -> int

 Tipo de un campo propio (sin promoción); `0` si no existe.

 ## Memoria
 No asigna.

### `is_embed_field`

> **is_embed_field**(t: ref to SemaTypeTable, ty: int, idx: int) -> bool

 `true` si el campo `idx` de `ty` es un embed.

 ## Memoria
 No asigna.

### `route_into`

> **route_into**(t: ref to SemaTypeTable, ty: int, nid: int, path: ref to list of int, depth: int) -> int

 Ruta de embeds que lleva al campo `nid`.

 Añade a `path` los `NameId` de los campos-embed que hay que atravesar; el
 último tramo es el campo `nid` dentro del último embed. Una ruta vacía con
 `ROUTE_FOUND` significa campo propio. La regla es la del diseño: el campo
 propio gana; si aparece en exactamente un embed, se promociona; si aparece
 en más de uno, es ambiguo.

 ## Memoria
 O(embeds × profundidad); las listas temporales se liberan aquí.

### `field_type_via`

> **field_type_via**(t: ref to SemaTypeTable, ty: int, nid: int, path: ref to list of int) -> int

 Tipo del campo `nid` siguiendo `path`; `0` si la ruta no lleva a un campo.

 ## Memoria
 No asigna.

### `field_type_at`

> **field_type_at**(t: ref to SemaTypeTable, ty: int, nid: int) -> int

 Tipo del campo `nid` con promoción (sin diagnóstico): `0` si no existe o es
 ambiguo. Los llamadores que tienen un nodo usan `route_into` para emitir
 E0087 antes de caer aquí.

 ## Memoria
 Asigna una ruta temporal.

### `field_module`

> **field_module**(t: ref to SemaTypeTable, ty: int, nid: int) -> int

 Modulo del nominal que declara el campo `nid` visto desde `ty`, siguiendo la
 promocion de `fundere`; `-1` si no se encuentra.

 ## Memoria
 Asigna una ruta temporal.

### `field_is_public`

> **field_is_public**(t: ref to SemaTypeTable, ty: int, nid: int) -> bool

 `true` si el campo `nid` (propio o promovido) lleva `@public`.

 ## Memoria
 Asigna una ruta temporal.

### `has_embeds`

> **has_embeds**(t: ref to SemaTypeTable, ty: int) -> bool

 `true` si el rune tiene al menos un embed.

 ## Memoria
 No asigna.

