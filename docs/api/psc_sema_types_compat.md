# psc.sema.types.compat

> Source: `src/psc/sema/types/compat.pengu`

psc/sema/types/compat.pengu — compatibilidad y casts entre tipos.

Es un port de `Type.is_compatible`/`can_cast_to` de stage0. Las reglas no son
simétricas (`frozen`, `ref`, `alias`, `seal`, `null`) y por eso viven aquí,
no en `table.pengu`.

## Memoria
Todo es de solo lectura sobre la tabla; no asigna.

---

### `compatible`

> **compatible**(t: ref to SemaTypeTable, a: int, b: int) -> bool

 ¿`a` fluye implícitamente a `b`?

 ## Memoria
 O(profundidad de los tipos); sin asignaciones.

### `can_cast`

> **can_cast**(t: ref to SemaTypeTable, a: int, b: int) -> bool

 ¿`a` puede convertirse a `b` con `to`?

 ## Memoria
 O(profundidad); sin asignaciones.

### `base_name_text`

> **base_name_text**(t: ref to SemaTypeTable, nid: int) -> string

 Nombre de un primitivo.

 ## Memoria
 Devuelve un préstamo del pool.

### `pool_text`

> **pool_text**(t: ref to SemaTypeTable, nid: int) -> string

 Acceso indirecto al pool para no importar `names` en cada helper.

 ## Memoria
 Préstamo.

### `is_int`

> **is_int**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es un entero (incluye char/byte)?

 ## Memoria
 O(1).

### `is_float`

> **is_float**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es un float?

 ## Memoria
 O(1).

### `is_numeric`

> **is_numeric**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es numérico?

 ## Memoria
 O(1).

### `is_string`

> **is_string**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es string (o omen string-valued)?

 ## Memoria
 O(1)/O(1) según variante.

### `is_bool`

> **is_bool**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es bool?

 ## Memoria
 O(1).

### `is_iterable`

> **is_iterable**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es iterable?

 ## Memoria
 O(1).

### `element_type`

> **element_type**(t: ref to SemaTypeTable, id: int) -> int

 Tipo de elemento de una colección; `-1` si no aplica.

 ## Memoria
 O(1).

### `null_accepts`

> **null_accepts**(t: ref to SemaTypeTable, b: int) -> bool

 ¿`null` puede asignarse a `b`?

 ## Memoria
 O(1).

### `base_compatible`

> **base_compatible**(t: ref to SemaTypeTable, anid: int, b: int, tb: SemaType) -> bool

 Compatibilidad de un primitivo.

 ## Memoria
 O(1).

### `is_int_name`

> **is_int_name**(s: string) -> bool

 ¿Nombre de entero primitivo?

 ## Memoria
 O(1).

### `is_float_name`

> **is_float_name**(s: string) -> bool

 ¿Nombre de float primitivo?

 ## Memoria
 O(1).

### `ref_compatible`

> **ref_compatible**(t: ref to SemaTypeTable, ta: SemaType, b: int, tb: SemaType) -> bool

 Compatibilidad de referencias.

 ## Memoria
 O(profundidad).

### `is_frozen_target`

> **is_frozen_target**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es un target `frozen`?

 ## Memoria
 O(1).

### `is_cstr`

> **is_cstr**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es `ref to char` / `ref to frozen char` (o `byte`)?

 Reconoce alias, seal y `frozen` alrededor tanto de la referencia como del
 pointee. El checker usa esto para aceptar un literal string en contextos
 `const char*` (bindings C) sin inferir un `PenguString`.

 ## Memoria
 O(profundidad); no asigna.

### `void_pointer`

> **void_pointer**(t: ref to SemaTypeTable, id: int) -> bool

 ¿Es `ref to void/opaque`?

 ## Memoria
 O(1).

### `same_pointee`

> **same_pointee**(t: ref to SemaTypeTable, a: int, b: int) -> bool

 ¿Dos pointees son estrictamente iguales (con la excepción char/byte)?

 ## Memoria
 O(profundidad).

### `has_type_param`

> **has_type_param**(t: ref to SemaTypeTable, id: int) -> bool

 ¿El tipo contiene un parámetro de tipo?

 ## Memoria
 O(profundidad).

### `fn_compatible`

> **fn_compatible**(t: ref to SemaTypeTable, ta: SemaType, tb: SemaType) -> bool

 Compatibilidad de funciones.

 ## Memoria
 O(número de parámetros).

### `nominal_compatible`

> **nominal_compatible**(t: ref to SemaTypeTable, ta: SemaType, tb: SemaType) -> bool

 Compatibilidad nominal (runa/echo/omen).

 ## Memoria
 O(argumentos).

### `concept_satisfied`

> **concept_satisfied**(t: ref to SemaTypeTable, concrete: int, concept: int) -> bool

 ¿El tipo concreto satisface un concepto?

 Los primitivos tienen sus conceptos canónicos; las runas/ecos miran sus
 derivaciones. Un `TypeParam`/`any`/`opaque` se considera válido para no
 encadenar errores en contextos genéricos.

 ## Memoria
 O(derivaciones); no asigna.

