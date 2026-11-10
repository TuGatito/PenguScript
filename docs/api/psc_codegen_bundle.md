# psc.codegen.bundle

> Source: `src/psc/codegen/bundle.pengu`

psc/codegen/bundle.pengu — ensamblado de `bundle.c`.

CP0: cabecera, prototipos, definiciones y wrapper de entry. Las secciones de
tipos, tests, line markers y DCE se añaden por subfases.

---

### `type_prunable`

> **type_prunable**(c: ref to CgContext, r: ref to CgReach, ty: int) -> bool

 ¿Es un tipo genérico instanciado que se puede podar? Los tipos no
 genéricos se emiten siempre: `size of`/`align of` y las declaraciones `.d`
 pueden referenciarlos sin anotar el AST.

 ## Memoria
 O(1).

### `is_libc_name`

> **is_libc_name**(c: ref to CgContext, f: CgFunction) -> bool

 ¿El `declare` corresponde a una función de la libc ya declarada por el runtime?

 ## Memoria
 O(1) por nombre.

### `finish_checked`

> **finish_checked**(e: ref to CgEmitter) -> string

 Verifica que el C generado no contenga bytes NUL (corrupción de heap).

 ## Memoria
 Consume el emisor; devuelve el string owned del llamador.

### `generate_bundle_c`

> **generate_bundle_c**(c: ref to CgContext, live_out: ref to list of int) -> string

 Emite el bundle completo.

 ## Memoria
 Devuelve string owned; el contexto conserva sus tablas.

### `CgUnit`

> rune CgUnit

```pengu
    name as string
    text as string
```

 Una unidad C generada.

 ## Memoria
 `name` y `text` son owned.

### `CgParts`

> rune CgParts

```pengu
    header as string
    core as string
    units as list of CgUnit
```

 Resultado de la emisión multi-unidad.

 ## Memoria
 `header` y `core` son owned; `units` también.

### `CgUnitBuffers`

> rune CgUnitBuffers

```pengu
    ids as list of int
    bufs as list of StringBuilder
```

 Buffers de unidades por módulo.

### `unit_slot`

> **unit_slot**(u: ref to CgUnitBuffers, mid: int) -> int

 Índice de la unidad de un módulo, creándola si no existe.

 ## Memoria
 Añade a `u`.

### `append_unit`

> **append_unit**(u: ref to CgUnitBuffers, mid: int, text: string) -> void

 Añade texto al buffer de un módulo.

 ## Memoria
 Presta `text`.

### `unit_name`

> **unit_name**(c: ref to CgContext, mid: int) -> string

 Nombre de archivo de una unidad a partir del módulo.

 ## Memoria
 Devuelve string owned.

### `generate_units_c`

> **generate_units_c**(c: ref to CgContext, live_out: ref to list of int) -> CgParts

 Emite una cabecera compartida y unidades por módulo (F7).

 Es la variante opt-in del bundle único. El llamador escribe los archivos y
 compila cada unidad por separado; `generate_bundle_c` sigue siendo el camino
 por defecto.

 ## Memoria
 Devuelve textos owned; el contexto conserva sus tablas.

