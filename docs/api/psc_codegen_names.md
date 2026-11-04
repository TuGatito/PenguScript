# psc.codegen.names

> Source: `src/psc/codegen/names.pengu`

psc/codegen/names.pengu — nombres C estables.

F3 guarda nombres lógicos; F4 decide el nombre C final. Esta tabla cachea
tipos/símbolos y evita que dos módulos emitan el mismo identificador.

---

### `CgNames`

> rune CgNames

```pengu
    names as ref to NamePool
    types as ref to SemaTypeTable
    type_names as map of int to int
    symbol_names as map of int to int
    subst as map of int to int
```

 Tabla de nombres C.

 ## Memoria
 Dueña de los mapas; `free` los libera.

### `new_names`

> **new_names**(names: ref to NamePool, types: ref to SemaTypeTable) -> CgNames

 Crea la tabla.

 ## Memoria
 Asigna los mapas; liberar con `free`.

### `names_free`

> **names_free**(n: ref to CgNames) -> void

 Libera la tabla.

 ## Memoria
 Libera los mapas; los strings son del pool.

### `type_name`

> **type_name**(n: ref to CgNames, id: int) -> string

 Nombre C de un tipo nominal.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `symbol_name`

> **symbol_name**(n: ref to CgNames, s: SemaSymbol) -> string

 Nombre C final de un símbolo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `function_name`

> **function_name**(n: ref to CgNames, s: SemaSymbol) -> string

 Nombre C de una función; `main` se renombra a `pengu_main`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `local_name`

> **local_name**(n: ref to CgNames, nid: int) -> string

 Nombre C de un campo/parámetro/local.

 ## Memoria
 Devuelve un string owned.

