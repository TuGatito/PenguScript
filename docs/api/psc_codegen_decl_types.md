# psc.codegen.decl_types

> Source: `src/psc/codegen/decl_types.pengu`

psc/codegen/types.pengu — definiciones C de runas, ecos, omens y alias.

La tabla de tipos de F3 ya contiene campos/variantes; este módulo sólo
decide el orden y el texto C.

---

### `type_name`

> **type_name**(c: ref to CgContext, t: CgType) -> string

 Nombre C owned de un tipo del catálogo.

 ## Memoria
 Devuelve string owned.

### `emit_tuple`

> **emit_tuple**(c: ref to CgContext, id: int) -> void

 Emite la definición de un tipo tupla usado en el programa.

 ## Memoria
 Strings temporales liberados.

### `emit_const`

> **emit_const**(c: ref to CgContext, k: CgConst) -> void

 Emite una constante de módulo.

 Los valores escalares simples conservan el `#define` compacto; los
 inicializadores de rune/echo (`const RAYWHITE as Color is with ...`), floats
 y cualquier expresión no plegada se emiten desde el AST con el tipo
 declarado (compound literal incluido).

 ## Memoria
 Strings temporales liberados.

### `emit_forward`

> **emit_forward**(c: ref to CgContext, t: CgType) -> void

 Emite la declaración adelantada de un tipo.

 ## Memoria
 Strings temporales liberados.

### `emit_clone`

> **emit_clone**(c: ref to CgContext, t: CgType) -> void

 Emite el clon superficial de un tipo.

 Los helpers derivados (`Nexus`/`Imago`) llaman `_pengu_clone_T` desde
 antiquus; el codegen debe declararlo antes de esos bloques.

 ## Memoria
 Strings temporales liberados.

### `emit_omen_cleanup`

> **emit_omen_cleanup**(c: ref to CgContext, ty: SemaType, cname: string) -> void

 Emite el cleanup de un omen con payload (libera el payload de la variante
 activa). Se emite desde `emit_cleanup`, que corre después de `emit_definition`.

 ## Memoria
 Strings temporales liberados.

### `emit_cleanup`

> **emit_cleanup**(c: ref to CgContext, t: CgType) -> void

 Emite el cleanup derivado de un rune/echo.

 ## Memoria
 Strings temporales liberados.

### `nominal_type_id`

> **nominal_type_id**(c: ref to CgContext, tid: int) -> int

 Resuelve un `TypeId` a su tipo nominal (rune/eco/omen), siguiendo alias y seals.

 Devuelve `-1` cuando el tipo no es nominal o el id no es válido.

 ## Memoria
 No asigna.

### `collect_type_deps`

> **collect_type_deps**(c: ref to CgContext, i: int, idx: ref to list of int, out: ref to list of int) -> void

 Añade a `out` los índices de catálogo de los tipos nominales usados **por valor**
 en los campos/variantes de `i`.

 Los punteros no necesitan tipo completo, pero incluirlos sólo añade aristas
 conservadoras; el DFS corta ciclos, así que un ciclo de punteros no rompe nada.

 ## Memoria
 No retiene memoria.

### `visit_catalog_type`

> **visit_catalog_type**(c: ref to CgContext, i: int, idx: ref to list of int, state: ref to list of int, order: ref to list of int) -> void

 DFS de ordenación topológica de definiciones.

 ## Memoria
 Libera la lista temporal de dependencias.

### `order_types`

> **order_types**(c: ref to CgContext) -> list of int

 Ordena las definiciones de tipos para que los campos por valor encuentren el
 tipo completo (p.ej. un omen con payload `JsonArrayNode` declarado después).

 Emite el orden de índices de `c->catalog.types`; los tipos no vivos se filtran
 después. Los ciclos (posibles sólo vía punteros) se cortan sin fallar.

 ## Memoria
 Devuelve una lista owned; `idx`/`state` se liberan aquí.

### `layout_attr_suffix`

> **layout_attr_suffix**(info: SemaNominalInfo) -> string

 Emite la definición struct/enum de un tipo.

 ## Memoria
 Strings temporales liberados.
 Sufijo C para `@packed` / `@align(N)`.

### `emit_definition`

> **emit_definition**(c: ref to CgContext, t: CgType) -> void

_Undocumented._

