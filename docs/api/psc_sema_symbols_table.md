# psc.sema.symbols.table

> Source: `src/psc/sema/symbols/table.pengu`

psc/sema/symbols/table.pengu — tabla de símbolos, scopes y registros.

Es el equivalente de `SymbolTable` de stage0, pero con IDs enteros y mapas
indexados por `NameId`. El checker entra y sale de scopes; el colector
registra tipos, funciones, métodos, consts, genéricos e imports.

## Memoria
`SemaSymbols` es dueño de `symbols`, `scopes`, `templates`, `instances`,
`const_values`, sus mapas y sus listas de strings. `free_symbols` lo libera
todo. El `NamePool` y la tabla de tipos son prestados y viven más.

---

### `SemaSymbols`

> rune SemaSymbols

```pengu
    names as ref to NamePool
    types as ref to SemaTypeTable
    symbols as list of SemaSymbol
    scopes as list of SemaScope
    current as int
    runes as map of int to int
    echos as map of int to int
    omens as map of int to int
    aliases as map of int to int
    seals as map of int to int
    concepts as map of int to int
    functions as map of int to int
    consts as map of int to int
    methods as map of int to int
    method_receiver as map of int to int
    mutating_methods as map of int to int
    generic_runes as map of int to int
    generic_echos as map of int to int
    generic_omens as map of int to int
    generic_aliases as map of int to int
    generic_concepts as map of int to int
    generic_functions as map of int to int
    generic_methods as map of int to int
    container_methods as map of int to int
    generic_owner as map of int to int
    bind_owner as map of int to int
    primitive_owner as map of int to int
    shard_bounds as map of int to int
    templates as list of SemaTemplate
    instances as list of SemaInstance
    instance_keys as map of int to int
    instance_by_type as map of int to int
    instance_args as list of int
    const_values as list of SemaConst
    symbol_bounds as list of int
    module_type_keys as map of int to int
    module_types as map of int to int
    includes as list of string
    links as list of string
    link_modules as list of int
    ldflags as list of string
    imports as list of string
    import_order as list of int
    import_graph as list of int
    has_includes as bool
    insignia as int
    current_module as int
```

 Tabla de símbolos completa.

 ## Memoria
 Sin `derive Nexus`: los mapas de cada scope y las listas de strings se
 liberan explícitamente en `free_symbols`.

### `new_symbols`

> **new_symbols**(t: ref to SemaTypeTable, pool: ref to NamePool) -> SemaSymbols

 Crea la tabla y registra builtins.

 ## Memoria
 Asigna listas/mapas; `free_symbols` los libera.

### `free_symbols`

> **free_symbols**(s: ref to SemaSymbols) -> void

 Libera la tabla completa.

 ## Memoria
 Libera mapas de scopes, listas y strings; no libera el pool ni los tipos.

### `free_strings`

> **free_strings**(xs: list of string) -> void

 Libera una lista de strings owned.

 ## Memoria
 Libera cada elemento y la lista.

### `new_global_scope`

> **new_global_scope**(s: ref to SemaSymbols) -> void

 Crea el scope global y lo activa.

 ## Memoria
 Añade un scope a la lista.

### `push_scope`

> **push_scope**(s: ref to SemaSymbols, kind: SemaScopeKind, start_line: int, end_line: int) -> int

 Entra en un scope hijo.

 Hereda `in_loop`, `in_or_block`, `return_type`, `enchanting_type` y
 `is_ritual` del padre si no se especifican.

 ## Memoria
 Añade un scope; liberar con `pop_scope`.

### `pop_scope`

> **pop_scope**(s: ref to SemaSymbols, end_line: int) -> void

 Sale del scope actual.

 ## Memoria
 Ajusta `end_line`; no libera nada.

### `mark_or_block`

> **mark_or_block**(s: ref to SemaSymbols, scope_id: int) -> void

 Marca un scope como cuerpo de `or:`.

 `in_or_block` hereda a los scopes hijos para que `error` siga siendo
 visible dentro de `if`/`when`/`for` anidados en el bloque.

 ## Memoria
 O(1); escribe el scope indicado.

### `current_scope`

> **current_scope**(s: ref to SemaSymbols) -> SemaScope

 Scope actual.

 ## Memoria
 Copia POD.

### `lookup`

> **lookup**(s: ref to SemaSymbols, name: int) -> int

 Lookup por `NameId` desde el scope actual.

 ## Memoria
 O(profundidad de scopes).

### `lookup_name`

> **lookup_name**(s: ref to SemaSymbols, name: string) -> int

 Lookup por string.

 ## Memoria
 Busca el nombre en el pool; si no existe no asigna.

### `symbol_lookup_local`

> **symbol_lookup_local**(s: ref to SemaSymbols, name: int) -> int

 Lookup local por `NameId`.

 ## Memoria
 O(1).

### `symbol_define`

> **symbol_define**(s: ref to SemaSymbols, symbol: SemaSymbol) -> int

 Define un símbolo en el scope actual.

 ## Memoria
 Añade a `symbols` y al mapa del scope.

### `add_symbol`

> **add_symbol**(s: ref to SemaSymbols, symbol: SemaSymbol) -> int

 Añade un símbolo sin ligarlo a un scope (métodos).

 ## Memoria
 Hace `push` en `symbols`.

### `symbol_define_in`

> **symbol_define_in**(s: ref to SemaSymbols, scope_id: int, symbol: SemaSymbol) -> int

 Define un símbolo en un scope concreto.

 ## Memoria
 Añade a `symbols`.

### `make_symbol`

> **make_symbol**(names: ref to NamePool, name: string, type_id: int, kind: SemaSymbolKind) -> SemaSymbol

 Crea un símbolo con defaults.

 ## Memoria
 Devuelve un POD; no asigna.

### `symbol_define_type`

> **symbol_define_type**(s: ref to SemaSymbols, kind: SemaSymbolKind, name: int, type_id: int) -> int

 Registra un tipo nominal por nombre.

 ## Memoria
 O(1) promedio.

### `lookup_type`

> **lookup_type**(s: ref to SemaSymbols, name: int) -> int

 Lookup de tipo por `NameId`.

 ## Memoria
 O(1) promedio.

### `lookup_in_scope`

> **lookup_in_scope**(s: ref to SemaSymbols, scope_id: int, name: int) -> int

 Lookup local en un scope concreto.

 ## Memoria
 O(1) promedio.

### `lookup_type_name`

> **lookup_type_name**(s: ref to SemaSymbols, name: string) -> int

 Lookup de tipo por string.

 ## Memoria
 Busca en el pool.

### `symbol_substring`

> **symbol_substring**(s: string, start: int, end: int) -> string

 Substring con copia owned.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `symbol_define_function`

> **symbol_define_function**(s: ref to SemaSymbols, name: int, fn_type: int) -> int

 Registra una función en el scope actual y en `functions`.

 ## Memoria
 Añade símbolo/mapa.

### `lookup_function`

> **lookup_function**(s: ref to SemaSymbols, name: int) -> int

 Lookup de función por `NameId`.

 ## Memoria
 O(1).

### `symbol_define_const`

> **symbol_define_const**(s: ref to SemaSymbols, name: int, type_id: int, value: SemaConst) -> int

 Registra una constante.

 ## Memoria
 Añade símbolo y mapa.

### `lookup_const`

> **lookup_const**(s: ref to SemaSymbols, name: int) -> int

 Lookup de constante.

 ## Memoria
 O(1).

### `method_key`

> **method_key**(s: ref to SemaSymbols, receiver: int, method: int) -> int

 Construye una clave `recv \x1f method` y la interna.

 ## Memoria
 Devuelve un `NameId`; el string temporal se libera.

### `_has_param`

> **_has_param**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si el tipo contiene un `TkTypeParam`.

 ## Memoria
 O(profundidad).

### `_is_container_kind`

> **_is_container_kind**(k: SemaTypeKind) -> bool

 `true` si la clase es un contenedor con métodos genéricos.

 ## Memoria
 O(1).

### `container_method_key`

> **container_method_key**(s: ref to SemaSymbols, kind: SemaTypeKind, method: int) -> int

 Clave `kind \x1f method` para el fallback de métodos de contenedor.

 ## Memoria
 Devuelve un `NameId`; el string temporal se libera.

### `symbol_define_method`

> **symbol_define_method**(s: ref to SemaSymbols, receiver: int, method: int, fn_type: int) -> int

 Registra un método.

 ## Memoria
 Añade símbolo y mapa.

### `lookup_method`

> **lookup_method**(s: ref to SemaSymbols, receiver: int, method: int) -> int

 Lookup de método.

 ## Memoria
 O(1).

### `lookup_method_exact`

> **lookup_method_exact**(s: ref to SemaSymbols, receiver: int, method: int) -> int

 Busca sólo el método exacto del receptor (sin fallback genérico).

 ## Memoria
 O(1) promedio.

### `instance_for_type`

> **instance_for_type**(s: ref to SemaSymbols, type_id: int) -> int

 Devuelve la instancia nominal de un `TypeId` (`-1` si no lo es).

 ## Memoria
 O(1).

### `has_name`

> **has_name**(s: ref to SemaSymbols, name: int) -> bool

 `true` si el nombre está en el pool.

 ## Memoria
 O(1).

### `name_text`

> **name_text**(s: ref to SemaSymbols, name: int) -> string

 Texto de un `NameId`.

 ## Memoria
 Préstamo.

### `symbol_at`

> **symbol_at**(s: ref to SemaSymbols, id: int) -> SemaSymbol

 `NameId` de un símbolo.

 ## Memoria
 Copia POD.

### `symbol_set`

> **symbol_set**(s: ref to SemaSymbols, id: int, v: SemaSymbol) -> void

 Actualiza un símbolo tras crearlo.

 ## Memoria
 O(1).

### `init_builtins`

> **init_builtins**(s: ref to SemaSymbols) -> void

 Registra primitivos, `print` y conceptos builtin.

 ## Memoria
 Añade símbolos y tipos a la tabla prestada.

### `builtin_concept`

> **builtin_concept**(s: ref to SemaSymbols, name: string) -> void

 Registra un concepto integrado.

 ## Memoria
 Añade info nominal y símbolo global.

### `builtin_type`

> **builtin_type**(s: ref to SemaSymbols, spelled: string, canonical: string) -> void

 Registra un tipo primitivo y su símbolo.

 ## Memoria
 Añade un símbolo por alias; el `TypeId` se comparte.

