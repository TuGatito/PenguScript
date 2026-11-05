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
    module_of_scope as map of int to int
    scope_of_module as map of int to int
    import_first as map of int to int
    import_count as map of int to int
    import_edges as list of int
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

### `register_module_scope`

> **register_module_scope**(s: ref to SemaSymbols, module_id: int, scope_id: int) -> void

 Registra el scope de un módulo y su inverso.

 ## Memoria
 Añade dos entradas de mapa.

### `register_import`

> **register_import**(s: ref to SemaSymbols, importer: int, target: int) -> void

 Registra un import directo entre módulos.

 ## Memoria
 Añade una entrada a `import_edges` y ajusta contadores.

### `scope_of_module`

> **scope_of_module**(s: ref to SemaSymbols, module_id: int) -> int

 Scope de un módulo (`-1` si no se registró).

 ## Memoria
 O(1).

### `lookup_scope_chain`

> **lookup_scope_chain**(s: ref to SemaSymbols, name: int) -> int

 Lookup por `NameId` sólo en la cadena de scopes actual.

 ## Memoria
 O(profundidad de scopes).

### `lookup_visible`

> **lookup_visible**(s: ref to SemaSymbols, name: int) -> int

 Lookup en los módulos visibles desde el módulo actual.

 Recorre el cierre de imports directos en anchura (primero el propio módulo
 ya lo cubre la cadena de scopes). Nunca consulta módulos ajenos al grafo de
 imports del archivo.

 ## Memoria
 Asigna dos contenedores temporales; los libera.

### `lookup`

> **lookup**(s: ref to SemaSymbols, name: int) -> int

 Lookup por `NameId` desde el scope actual.

 Orden: cadena de scopes (módulo actual incluido), módulos visibles por
 imports, y sólo como último recurso los registros globales históricos.

 ## Memoria
 O(profundidad de scopes + módulos visibles).

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

 Prefiere la declaración del módulo actual (bug 17): un `rune Handler` local
 no debe perder contra el alias `Handler` importado. Después busca en los
 módulos visibles y sólo al final en los registros globales heredados.

 ## Memoria
 O(profundidad de scopes + módulos visibles).

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

### `symbol_define_method_cname`

> **symbol_define_method_cname**(s: ref to SemaSymbols, receiver: int, method: int, fn_type: int, cname: string) -> int

 Registra un método con nombre C explícito (codecs de `derive Json`).

 ## Memoria
 Añade símbolo y mapa; el `c_name` se interna.

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

