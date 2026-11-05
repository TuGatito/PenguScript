# psc.sema.types.table

> Source: `src/psc/sema/types/table.pengu`

psc/sema/types/table.pengu — tabla plana de tipos con interning.

Un `TypeId` es un índice en `SemaTypeTable.types`. Los tipos compuestos
guardan IDs de hijos y los metadatos nominales/función viven en tablas
laterales con `first/count`. La identidad estructural se consigue internando
cada constructor con una clave canónica: dos construcciones equivalentes
devuelven el mismo `TypeId`.

## Por qué una tabla y no `ref to SemaType`
Los payloads de un `omen` de PenguScript se construyen completos; una runa o
una función necesita rellenar campos y métodos después de crear el tipo. La
tabla permite crear el tipo nominal primero y mutar su `SemaNominalInfo`,
mantiene IDs deterministas y hace que `banish` sea una operación de listas
planas, sin recorrer un grafo de punteros.

## Memoria
`SemaTypeTable` presta el `NamePool`; es dueño de todas las listas y del mapa
`intern`. `free_table` libera todo. Los `TypeId` dejan de ser válidos.

---

### `TYPE_ID_CVARARGS`

> **TYPE_ID_CVARARGS** : int

 `TypeId` del singleton `...` de las firmas `declare`.

 `new_table` inserta los singletons en este orden: error, any, null, void,
 opaque y cvarargs; el resto de IDs son dinámicos.

### `SemaNominalInfo`

> rune SemaNominalInfo

```pengu
    kind as SemaNominalKind
    base_name as int
    c_name as int
    module as int
    flags as int
    fields_first as int
    fields_count as int
    variants_first as int
    variants_count as int
    tparams_first as int
    tparams_count as int
    derived_first as int
    derived_count as int
    template_info as int
    attrs_node as int
    decl_node as int
    is_packed as bool
    align_override as int
```

 Información mutable de una runa/echo/omen/alias/seal/concepto.

### `SemaField`

> rune SemaField

```pengu
    name as int
    type as int
    flags as int
    attrs_node as int
    align_override as int
    decl_node as int
```

 Campo de una runa/echo o payload de una variante.

### `SemaVariant`

> rune SemaVariant

```pengu
    name as int
    value_i as int
    value_s as int
    payload_first as int
    payload_count as int
    flags as int
```

 Variante de un `omen`.

### `SemaTypeParamInfo`

> rune SemaTypeParamInfo

```pengu
    name as int
    bounds_first as int
    bounds_count as int
    flags as int
```

 Parámetro de tipo de una declaración genérica.

### `SemaFnParam`

> rune SemaFnParam

```pengu
    name as int
    type as int
    flags as int
    default_node as int
    default_module as int
    default_text as int
```

 Parámetro de una función.

### `SemaFnInfo`

> rune SemaFnInfo

```pengu
    params_first as int
    params_count as int
    return_type as int
    tparams_first as int
    tparams_count as int
    flags as int
    attrs_node as int
```

 Firma de una función o método.

### `SemaConceptMethod`

> rune SemaConceptMethod

```pengu
    name as int
    fn_type as int
    flags as int
```

 Método requerido por un concepto.

### `NIF_CYCLUS`

> **NIF_CYCLUS** : int

 Flags públicos de las tablas laterales. Se documentan aquí para que F4 no
 dependa de números mágicos.

### `NIF_ALGEBRAIC`

> **NIF_ALGEBRAIC** : int

_Undocumented._

### `NIF_STRING_VALUED`

> **NIF_STRING_VALUED** : int

_Undocumented._

### `NIF_PUBLIC`

> **NIF_PUBLIC** : int

_Undocumented._

### `NIF_AUTO_DONUM`

> **NIF_AUTO_DONUM** : int

_Undocumented._

### `NIF_OPAQUE`

> **NIF_OPAQUE** : int

_Undocumented._

### `NIF_SEALED`

> **NIF_SEALED** : int

_Undocumented._

### `NIF_DERIVED`

> **NIF_DERIVED** : int

_Undocumented._

### `NIF_SHARED`

> **NIF_SHARED** : int

 El tipo se puede compartir entre hilos con `ref to T`.

### `NIF_JSON`

> **NIF_JSON** : int

 La runa declaró `derive Json`.

### `FIELD_READONLY`

> **FIELD_READONLY** : int

_Undocumented._

### `FIELD_PRIVATE`

> **FIELD_PRIVATE** : int

_Undocumented._

### `FIELD_ALIGNED`

> **FIELD_ALIGNED** : int

_Undocumented._

### `FIELD_PACKED`

> **FIELD_PACKED** : int

_Undocumented._

### `FIELD_JSON_SKIP`

> **FIELD_JSON_SKIP** : int

 El campo lleva `@skip` en una runa `derive Json`.

### `VAR_HAS_INT`

> **VAR_HAS_INT** : int

_Undocumented._

### `VAR_HAS_STRING`

> **VAR_HAS_STRING** : int

_Undocumented._

### `VAR_PRIVATE`

> **VAR_PRIVATE** : int

_Undocumented._

### `TP_BOUNDED`

> **TP_BOUNDED** : int

_Undocumented._

### `TP_SHARD`

> **TP_SHARD** : int

_Undocumented._

### `PARAM_HAS_DEFAULT`

> **PARAM_HAS_DEFAULT** : int

_Undocumented._

### `PARAM_MANY`

> **PARAM_MANY** : int

_Undocumented._

### `PARAM_SELF`

> **PARAM_SELF** : int

_Undocumented._

### `FN_GENERIC`

> **FN_GENERIC** : int

_Undocumented._

### `FN_RITUAL`

> **FN_RITUAL** : int

_Undocumented._

### `FN_SELF_VALUE`

> **FN_SELF_VALUE** : int

_Undocumented._

### `FN_MUTATES`

> **FN_MUTATES** : int

_Undocumented._

### `FN_ANTIQUUS`

> **FN_ANTIQUUS** : int

_Undocumented._

### `FN_DECLARE`

> **FN_DECLARE** : int

_Undocumented._

### `FN_METHOD`

> **FN_METHOD** : int

_Undocumented._

### `FN_VARIADIC`

> **FN_VARIADIC** : int

_Undocumented._

### `FN_SPAWN`

> **FN_SPAWN** : int

 La función es el punto de entrada de `filum.start` (chequeo de propiedad).

### `FN_CORO`

> **FN_CORO** : int

 La función es el punto de entrada de `std.coro.start` (chequeo de propiedad).

### `CM_REQUIRED`

> **CM_REQUIRED** : int

_Undocumented._

### `SemaTypeTable`

> rune SemaTypeTable

```pengu
    names as ref to NamePool
    types as list of SemaType
    type_children as list of int
    nominal_infos as list of SemaNominalInfo
    fn_infos as list of SemaFnInfo
    fields as list of SemaField
    variants as list of SemaVariant
    tparams as list of SemaTypeParamInfo
    bounds as list of int
    derived as list of int
    concept_methods as list of SemaConceptMethod
    fn_params as list of SemaFnParam
    tparam_cache as map of int to int
    intern as map of string to int
    intern_keys as list of string
    canonical_cache as list of int
    mangled_cache as list of int
    json_names as map of int to int
    json_type_ids as list of int
```

 Tabla de tipos y metadatos.

 ## Memoria
 Dueña de todas las listas y del mapa `intern`; `free_table` las libera.

### `new_table`

> **new_table**(pool: ref to NamePool) -> SemaTypeTable

 Crea la tabla y preinterna los singletons y primitivos habituales.

 ## Memoria
 Asigna listas/mapa y el pool prestado debe vivir más que la tabla.

### `_add_singleton`

> **_add_singleton**(t: ref to SemaTypeTable, kind: SemaTypeKind) -> int

 Añade un singleton y lo interna.

 ## Memoria
 O(1); añade una entrada a `types` y una clave al mapa.

### `free_table`

> **free_table**(t: ref to SemaTypeTable) -> void

 Libera la tabla.

 ## Memoria
 Libera listas y el mapa de interning; el `NamePool` lo libera su dueño.

### `at`

> **at**(t: ref to SemaTypeTable, id: int) -> SemaType

 Devuelve el registro de un `TypeId`; `TkError` si es inválido.

 ## Memoria
 Copia POD; no asigna.

### `valid`

> **valid**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si el id existe.

 ## Memoria
 O(1), no asigna.

### `type_count`

> **type_count**(t: ref to SemaTypeTable) -> int

 Número de tipos.

 ## Memoria
 O(1), no asigna.

### `type_child_at`

> **type_child_at**(t: ref to SemaTypeTable, id: int, i: int) -> int

 Hijo `i` de un tipo con `first/count`; `-1` si no existe.

 ## Memoria
 O(1), no asigna.

### `canonical_primitive`

> **canonical_primitive**(s: string) -> string

 Nombre canónico de un primitivo (alias → canónico).

 ## Memoria
 Devuelve un literal prestado; no asigna.

### `base`

> **base**(t: ref to SemaTypeTable, spelled: string) -> int

 Crea/interna un primitivo.

 ## Memoria
 O(1) amortizado; puede añadir nombre/tipo.

### `intern_type`

> **intern_type**(t: ref to SemaTypeTable, ty: SemaType) -> int

 Interna un tipo estructural y devuelve su id.

 ## Memoria
 Puede añadir una entrada a `types`, `type_children` y `intern`.

### `key_of`

> **key_of**(t: ref to SemaTypeTable, ty: SemaType) -> string

 Construye la clave canónica de un tipo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `ref_to`

> **ref_to**(t: ref to SemaTypeTable, target: int) -> int

 `ref to target`.

 ## Memoria
 O(1) amortizado.

### `frozen`

> **frozen**(t: ref to SemaTypeTable, target: int) -> int

 `frozen target`.

 ## Memoria
 O(1) amortizado.

### `underlying`

> **underlying**(t: ref to SemaTypeTable, id: int) -> int

 Resuelve `alias`/`seal` hasta el tipo subyacente.

 ## Memoria
 O(profundidad de alias), máximo 32.

### `strip_frozen`

> **strip_frozen**(t: ref to SemaTypeTable, id: int) -> int

 Desenvuelve un `frozen T` a `T`; cualquier otro tipo se devuelve igual.

 ## Memoria
 O(1).

### `is_frozen`

> **is_frozen**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si el tipo es `frozen T`.

 ## Memoria
 O(1).

### `slice_of`

> **slice_of**(t: ref to SemaTypeTable, target: int) -> int

 `slice of target`.

 ## Memoria
 O(1) amortizado.

### `many_of`

> **many_of**(t: ref to SemaTypeTable, target: int) -> int

 `many target`.

 ## Memoria
 O(1) amortizado.

### `list_of`

> **list_of**(t: ref to SemaTypeTable, target: int) -> int

 `list of target`.

 ## Memoria
 O(1) amortizado.

### `maybe_of`

> **maybe_of**(t: ref to SemaTypeTable, target: int) -> int

 `maybe target`.

 ## Memoria
 O(1) amortizado.

### `range_of`

> **range_of**(t: ref to SemaTypeTable, target: int) -> int

 `range of target` (interno).

 ## Memoria
 O(1) amortizado.

### `_unary`

> **_unary**(t: ref to SemaTypeTable, kind: SemaTypeKind, target: int) -> int

 Constructor de un tipo con un solo hijo.

 ## Memoria
 O(1) amortizado.

### `array_of`

> **array_of**(t: ref to SemaTypeTable, elem: int, size: int) -> int

 `array of elem with size N`; `size < 0` significa desconocido.

 ## Memoria
 O(1) amortizado.

### `map_of`

> **map_of**(t: ref to SemaTypeTable, key: int, value: int) -> int

 `map of key to value`.

 ## Memoria
 O(1) amortizado.

### `result_of`

> **result_of**(t: ref to SemaTypeTable, ok: int, err: int) -> int

 `result of ok to err`.

 ## Memoria
 O(1) amortizado.

### `tuple_of`

> **tuple_of**(t: ref to SemaTypeTable, ids: list of int) -> int

 Tupla de `ids`.

 ## Memoria
 Añade los hijos y el tipo; el llamador conserva la lista `ids`.

### `named_type`

> **named_type**(t: ref to SemaTypeTable, info: SemaNominalInfo) -> int

 Tipo nominal a partir de una `SemaNominalInfo`.

 ## Memoria
 Añade la info y el tipo; devuelve el `TypeId`.

### `named_with_target`

> **named_with_target**(t: ref to SemaTypeTable, info: SemaNominalInfo, target: int) -> int

 Tipo alias/seal con target en `b`.

 ## Memoria
 Añade la info y el tipo; devuelve el `TypeId`.

### `fn_type`

> **fn_type**(t: ref to SemaTypeTable, info: SemaFnInfo) -> int

 Tipo función.

 ## Memoria
 Añade la firma y el tipo; devuelve el `TypeId`.

### `type_param_type`

> **type_param_type**(t: ref to SemaTypeTable, info: SemaTypeParamInfo) -> int

 Tipo parámetro a partir de su info.

 ## Memoria
 Añade la info y el tipo; devuelve el `TypeId`.

### `add_field`

> **add_field**(t: ref to SemaTypeTable, f: SemaField) -> int

 Añade un campo y devuelve su índice.

 ## Memoria
 `push`; el campo es POD.

### `add_variant`

> **add_variant**(t: ref to SemaTypeTable, v: SemaVariant) -> int

 Añade una variante y devuelve su índice.

 ## Memoria
 `push`; la variante es POD.

### `add_tparam`

> **add_tparam**(t: ref to SemaTypeTable, p: SemaTypeParamInfo) -> int

 Añade un type param y devuelve su índice.

 ## Memoria
 `push`; la info es POD.

### `add_fn_param`

> **add_fn_param**(t: ref to SemaTypeTable, p: SemaFnParam) -> int

 Añade un parámetro de función y devuelve su índice.

 ## Memoria
 `push`; el parámetro es POD.

### `add_bound`

> **add_bound**(t: ref to SemaTypeTable, concept: int) -> int

 Añade un bound de concepto (`NameId`) y devuelve su índice.

 ## Memoria
 `push`; es un int.

### `add_derived`

> **add_derived**(t: ref to SemaTypeTable, concept: int) -> int

 Añade una derivación de concepto y devuelve su índice.

 ## Memoria
 `push`; es un int.

### `add_concept_method`

> **add_concept_method**(t: ref to SemaTypeTable, m: SemaConceptMethod) -> int

 Añade un método de concepto y devuelve su índice.

 ## Memoria
 `push`; es POD.

### `set_nominal_fields`

> **set_nominal_fields**(t: ref to SemaTypeTable, info_idx: int, first: int, count: int) -> void

 Actualiza el rango de campos de una info nominal ya creada.

 ## Memoria
 O(1); no asigna.

### `set_nominal_variants`

> **set_nominal_variants**(t: ref to SemaTypeTable, info_idx: int, first: int, count: int) -> void

 Actualiza el rango de variantes de una info nominal ya creada.

 ## Memoria
 O(1); no asigna.

### `set_nominal_tparams`

> **set_nominal_tparams**(t: ref to SemaTypeTable, info_idx: int, first: int, count: int) -> void

 Actualiza el rango de type params de una info nominal.

 ## Memoria
 O(1); no asigna.

### `set_nominal_derived`

> **set_nominal_derived**(t: ref to SemaTypeTable, info_idx: int, first: int, count: int) -> void

 Actualiza el rango de derivaciones de una info nominal.

 ## Memoria
 O(1); no asigna.

### `is_base`

> **is_base**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si el tipo es un primitivo.

 ## Memoria
 O(1), no asigna.

### `is_error`

> **is_error**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si el tipo es `TkError`.

 ## Memoria
 O(1), no asigna.

