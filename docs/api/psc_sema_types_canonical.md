# psc.sema.types.canonical

> Source: `src/psc/sema/types/canonical.pengu`

psc/sema/types/canonical.pengu — nombres canónicos y mangled.

`canonical_name` produce lo que `type of` y los diagnósticos muestran al
usuario (`list of int`, `ref to Point`, `byte`). `mangled_name` produce la
identidad C estable que usará F4 y las claves de instancia.

Ambos se calculan una vez por `TypeId` y se guardan como `NameId` en las
cachés de `SemaTypeTable`.

## Memoria
Devuelve un `NameId`; el texto vive en el `NamePool` del programa.

---

### `canonical_name`

> **canonical_name**(t: ref to SemaTypeTable, id: int) -> int

 Nombre canónico de un tipo, internado.

 ## Memoria
 Puede construir un string temporal y añadir una entrada al pool/caché.

### `build_canonical`

> **build_canonical**(t: ref to SemaTypeTable, ty: SemaType) -> string

 Texto canónico de un tipo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `display_base`

> **display_base**(t: ref to SemaTypeTable, nid: int) -> string

 Texto de un primitivo con los overrides de `type of`.

 ## Memoria
 Devuelve un literal o un préstamo del pool.

### `append_type`

> **append_type**(sb: ref to StringBuilder, t: ref to SemaTypeTable, id: int) -> void

 Añade un tipo por id al builder.

 ## Memoria
 Construye el nombre canónico (puede internarlo).

### `append_fn`

> **append_fn**(sb: ref to StringBuilder, t: ref to SemaTypeTable, info_idx: int) -> void

 Añade una firma de función.

 ## Memoria
 Construye el texto; no libera nada más.

### `append_nominal`

> **append_nominal**(sb: ref to StringBuilder, t: ref to SemaTypeTable, ty: SemaType) -> void

 Añade un tipo nominal y, si tiene argumentos, `of ...`.

 ## Memoria
 Construye el texto; no libera nada más.

### `mangled_name`

> **mangled_name**(t: ref to SemaTypeTable, id: int) -> int

 Nombre mangled de un tipo, internado.

 ## Memoria
 Puede construir un string temporal y añadir una entrada al pool/caché.

### `build_mangled`

> **build_mangled**(t: ref to SemaTypeTable, ty: SemaType) -> string

 Construye el nombre mangled.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `append_mangled`

> **append_mangled**(sb: ref to StringBuilder, t: ref to SemaTypeTable, id: int) -> void

 Añade el mangled de un tipo al builder.

 ## Memoria
 Construye el nombre (puede internarlo).

