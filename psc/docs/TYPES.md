# Tipos semánticos (F3)

## Representación

`SemaType` es un registro POD:

```pengu
rune SemaType:
    kind as SemaTypeKind
    flags as int
    name as int        # NameId
    a as int           # payload 1
    b as int           # payload 2
```

Todo tipo se identifica por un `TypeId` entero (`>0`). `0` es error/ausente.
La tabla (`SemaTypeTable`) es plana y propiedad de `SemaProgram`.

## Interning

`types.intern` canonicaliza y busca en `intern_keys` (map `int -> int`) usando
una clave estructural estable. Las claves son buffers owned por la tabla; no se
liberan al devolver un `TypeId`.

Los constructores públicos son:

```
base, ref_to, frozen, slice_of, many_of, list_of, maybe_of, array_of,
map_of, result_of, tuple_of, range_of, fn_type, named_type,
named_with_target, type_param_type
```

`type_param_type` cachea por `NameId`: `T` es el mismo `TypeId` dentro de todos
los usos de un módulo, lo que permite comparar firmas genéricas.

## Nominales

Runas, ecos, omens, aliases, seals y concepts comparten `SemaNominalInfo`:

```pengu
kind, name, fields_first, fields_count, variants_first, variants_count,
tparams_first, tparams_count, underlying, module, decl_node
```

Los campos (`SemaField`) y variantes (`SemaVariant`) viven en tablas laterales.
Las variantes de omen guardan `payload_first/payload_count` para tipar el
payload de `judge` (p. ej. `when Arr with items`).

## Firmas

`SemaFnInfo` guarda `params_first/count`, `return_type`, `tparams_first/count`,
flags y `attrs_node`. Los parámetros son `SemaFnParam` con nombre, tipo, flags y
nodo por defecto. `fn_type` interná la firma; los nombres de parámetro no forman
parte de la identidad estructural.

## Compatibilidad

`compat.compatible(got, expected)` implementa:

- identidad y nombres canónicos iguales;
- `any`/error/type-param como comodines;
- null → ref/any/opaque/void;
- refs (con `void *` y pointees compatibles);
- frozen/alias/seal (desenvuelven su target);
- arrays/slices/many y contenedores por elemento;
- runas/ecos por nombre, módulo y argumentos;
- firmas de función por aridad y retorno;
- casts explícitos (`can_cast`) para `to`.

`canonical_name` genera el nombre textual estable usado por diagnósticos,
oráculos y F4. `mangled_name` añade la firma y el módulo para C.

## Límites deliberados

`SemaType` no contiene punteros a heap ni strings propios: nombres, campos,
variantes y firmas están en tablas laterales. Esto mantiene el contrato POD para
F4 y evita ciclos de ownership.
