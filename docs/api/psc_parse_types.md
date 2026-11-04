# psc.parse.types

> Source: `src/psc/parse/types.pengu`

psc/parse/types.pengu — parser de tipos.

Replica `?type` de la gramática de stage0. No necesita expresiones: los
tamaños de `array` son `INT`/`NAME` y los parámetros de `fn` no tienen
valores por defecto. Por eso este módulo está por debajo de expresiones y
declaraciones en el DAG de imports.

## Memoria
Construye nodos en `PsParser.ast`; no asigna strings salvo diagnósticos.

---

### `ptype_parse_type`

> **ptype_parse_type**(p: ref to PsParser) -> int

 Parsea un tipo.

 ## Memoria
 Crea nodos en el AST del parser.

### `ptype_parse_type_or_param`

> **ptype_parse_type_or_param**(p: ref to PsParser) -> int

 Parsea un `type_or_param`: `shard T` o un tipo.

 ## Memoria
 Crea nodos en el AST.

### `ptype_parse_ref`

> **ptype_parse_ref**(p: ref to PsParser) -> int

 Parsea `ref to T`.

 ## Memoria
 Crea un nodo `ref_type`.

### `ptype_parse_frozen`

> **ptype_parse_frozen**(p: ref to PsParser) -> int

 Parsea `frozen T`.

 ## Memoria
 Crea un nodo `frozen_type`.

### `ptype_parse_fn`

> **ptype_parse_fn**(p: ref to PsParser) -> int

 Parsea un tipo función `weave [with ...] [into T]`.

 ## Memoria
 Crea un nodo `fn_type`.

### `ptype_parse_fn_params`

> **ptype_parse_fn_params**(p: ref to PsParser) -> int

 Parsea `with fn_param (,|and fn_param)*`.

 ## Memoria
 Crea un nodo `fn_param_list`.

### `ptype_parse_fn_param`

> **ptype_parse_fn_param**(p: ref to PsParser) -> int

 Parsea `[NAME as] type`.

 ## Memoria
 Crea un nodo `fn_param`.

### `ptype_parse_array`

> **ptype_parse_array**(p: ref to PsParser) -> int

 Parsea `array of T [with size (INT|NAME)]`.

 ## Memoria
 Crea un nodo `array_type`.

### `ptype_parse_slice`

> **ptype_parse_slice**(p: ref to PsParser) -> int

 Parsea `slice of T`.

 ## Memoria
 Crea un nodo `slice_type`.

### `ptype_parse_many`

> **ptype_parse_many**(p: ref to PsParser) -> int

 Parsea `many T`.

 ## Memoria
 Crea un nodo `many_type`.

### `ptype_parse_list`

> **ptype_parse_list**(p: ref to PsParser) -> int

 Parsea `list of T`.

 ## Memoria
 Crea un nodo `list_type`.

### `ptype_parse_map`

> **ptype_parse_map**(p: ref to PsParser) -> int

 Parsea `map of K to V`.

 ## Memoria
 Crea un nodo `map_type`.

### `ptype_parse_maybe`

> **ptype_parse_maybe**(p: ref to PsParser) -> int

 Parsea `maybe T`.

 ## Memoria
 Crea un nodo `maybe_type`.

### `ptype_parse_result`

> **ptype_parse_result**(p: ref to PsParser) -> int

 Parsea `result of T [to E]`.

 ## Memoria
 Crea un nodo `result_type`.

### `ptype_parse_opaque`

> **ptype_parse_opaque**(p: ref to PsParser) -> int

 Parsea `opaque`.

 ## Memoria
 Crea un nodo `opaque_type` con el token.

### `ptype_parse_base`

> **ptype_parse_base**(p: ref to PsParser) -> int

 Parsea un tipo base (`int`, `float`, ...).

 ## Memoria
 Crea un nodo `base_type` con el token.

### `ptype_parse_custom`

> **ptype_parse_custom**(p: ref to PsParser) -> int

 Parsea un tipo cualificado/genérico.

 ## Memoria
 Crea un nodo `custom_type`.

### `ptype_parse_dotted_path`

> **ptype_parse_dotted_path**(p: ref to PsParser) -> int

 Parsea `NAME (. NAME)*`.

 ## Memoria
 Crea un nodo `dotted_path`.

### `ptype_parse_paren`

> **ptype_parse_paren**(p: ref to PsParser) -> int

 Parsea `(` type ["," type...] `)`.

 Un solo tipo entre paréntesis se devuelve tal cual; dos o más forman
 `tuple_type`, como en la gramática.

 ## Memoria
 Crea un nodo `tuple_type` si hay más de un tipo.

### `ptype_parse_shard_ref`

> **ptype_parse_shard_ref**(p: ref to PsParser) -> int

 Parsea `shard NAME` como tipo/parámetro.

 ## Memoria
 Crea un nodo `shard_param_ref`.

### `ptype_parse_shard_params`

> **ptype_parse_shard_params**(p: ref to PsParser) -> int

 Parsea `shard NAME (,|and NAME)* [where ...]`.

 ## Memoria
 Crea un nodo `shard_params`.

### `ptype_parse_where_clause`

> **ptype_parse_where_clause**(p: ref to PsParser) -> int

 Parsea `where bound (,|and bound)*`.

 ## Memoria
 Crea un nodo `where_clause`.

### `ptype_parse_where_bound`

> **ptype_parse_where_bound**(p: ref to PsParser) -> int

 Parsea `(NAME | type) ":" custom_type`.

 ## Memoria
 Crea un nodo `where_bound`.

### `ptype_parse_custom_after_start`

> **ptype_parse_custom_after_start**(p: ref to PsParser) -> int

 Parsea un `custom_type` sin volver a comprobar el inicio.

 ## Memoria
 Crea un nodo `custom_type`.

### `ptype_parse_derive_clause`

> **ptype_parse_derive_clause**(p: ref to PsParser) -> int

 Parsea `derive A (,|and B)*`.

 ## Memoria
 Crea un nodo `derive_clause`.

### `ptype_is_base_word`

> **ptype_is_base_word**(p: ref to PsParser) -> bool

 `true` si el identificador actual es un tipo base.

 ## Memoria
 O(nombres), no asigna.

