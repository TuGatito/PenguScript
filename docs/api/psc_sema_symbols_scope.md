# psc.sema.symbols.scope

> Source: `src/psc/sema/symbols/scope.pengu`

psc/sema/symbols/scope.pengu — scopes léxicos.

Cada scope guarda un mapa `NameId -> SymbolId`. Usar `NameId` como clave
evita copiar strings y hace que el lookup sea un entero. Los scopes se
apilan en `SemaSymbols`; este módulo solo conoce la estructura y las
operaciones puras de un scope.

## Memoria
Cada `SemaScope` posee sus dos mapas. `SemaSymbols.free` los libera.

---

### `SemaScopeKind`

> omen SemaScopeKind

```pengu
    SgGlobal
    SgWeave
    SgEnchanting
    SgLambda
    SgIf
    SgWhile
    SgFor
    SgWith
    SgOrBlock
    SgBlock
    SgTest
```

 Clase de scope.

### `SemaScope`

> rune SemaScope

```pengu
    parent as int
    kind as SemaScopeKind
    bindings as map of int to int
    with_type as int
    with_mutable as bool
    with_target as int
    enchanting_type as int
    return_type as int
    in_loop as bool
    in_or_block as bool
    is_ritual as bool
    start_line as int
    end_line as int
    loop_label as int
    loop_labels as map of int to int
    bounds_first as int
    bounds_count as int
```

 Scope léxico.

 ## Memoria
 Sin destructor; `free_scope` libera los mapas.

### `new_scope`

> **new_scope**(kind: SemaScopeKind, parent: int, start_line: int, end_line: int) -> SemaScope

 Crea un scope.

 ## Memoria
 Asigna dos mapas; liberar con `free_scope`.

### `free_scope`

> **free_scope**(s: ref to SemaScope) -> void

 Libera los mapas del scope.

 ## Memoria
 Libera `bindings` y `loop_labels`.

### `scope_define`

> **scope_define**(s: ref to SemaScope, name: int, symbol: int) -> void

 Define un símbolo en el scope.

 Si el nombre ya existe, el último gana (stage0 hace lo mismo en locales).

 ## Memoria
 O(1) promedio; el mapa copia la cabecera del int.

### `scope_lookup_local`

> **scope_lookup_local**(s: ref to SemaScope, name: int) -> int

 Lookup local.

 ## Memoria
 O(1) promedio; no asigna.

### `has_local`

> **has_local**(s: ref to SemaScope, name: int) -> bool

 ¿Existe el nombre en este scope?

 ## Memoria
 O(1) promedio.

### `local_count`

> **local_count**(s: ref to SemaScope) -> int

 Número de nombres locales.

 ## Memoria
 O(1).

### `define_label`

> **define_label**(s: ref to SemaScope, name: int, label_id: int) -> void

 Define un label de loop.

 ## Memoria
 O(1) promedio.

### `lookup_label`

> **lookup_label**(s: ref to SemaScope, name: int) -> int

 Lookup de label local.

 ## Memoria
 O(1) promedio.

