# psc.codegen.jsongen

> Source: `src/psc/codegen/jsongen.pengu`

psc/codegen/jsongen.pengu — codecs C para `derive Json`.

Por cada runa `derive Json` viva emite cinco funciones `static`:

- `_pengu_json_encode_<T>(T* self)`: `PenguString` con el objeto JSON.
- `_pengu_json_write_<T>(PenguJsonOut*, const T*)`: escritor streaming.
- `_pengu_json_decode_<T>(PenguString)`: `PenguResult` (`T*` o `PenguString*`).
- `_pengu_json_read_<T>(PenguJsonIn*, T*, PenguString*)`: lector streaming.
- `_pengu_json_free_<T>(T*)`: liberador exacto de lo que asigna el lector.

Contenedores y omens se generan en línea. Cada camino de fallo libera lo que
ya vive dentro del destino (`_pengu_json_free_<T>`) y los temporales en vuelo
(clave, elemento, valor de mapa): el decodificador no depende del cleanup
superficial `_pengu_cleanup_<T>`.

## Memoria
Presta `CgContext`; los textos temporales se liberan en cada emisor.

---

### `mark_json_types`

> **mark_json_types**(c: ref to CgContext, r: ref to CgReach) -> void

 Marca como vivos los tipos de la clausura `Json` (definición + codecs).

 ## Memoria
 Recursivo; no posee recursos.

### `mark_closure`

> **mark_closure**(c: ref to CgContext, ty: int, r: ref to CgReach, seen: ref to map of int to int) -> void

 Marca `ty` y sus tipos Json anidados.

 ## Memoria
 Recursivo; no posee recursos.

### `mark_nested`

> **mark_nested**(c: ref to CgContext, ty: int, r: ref to CgReach, seen: ref to map of int to int) -> void

 Marca los tipos nominales anidados de un tipo componible.

 ## Memoria
 Recursivo; no posee recursos.

### `emit_all`

> **emit_all**(c: ref to CgContext, r: ref to CgReach) -> void

 Emite prototipos y cuerpos de todos los codecs vivos.

 ## Memoria
 Presta el contexto; libera las listas temporales.

### `register_methods`

> **register_methods**(c: ref to CgContext) -> void

 Registra los dos métodos sintéticos de cada runa `derive Json`.

 El catálogo necesita la entrada para que una llamada `x.to_json` pase
 `&x` y `User.from_json` no pase `self`.

 ## Memoria
 Añade al catálogo; libera los textos temporales.

### `register_one`

> **register_one**(c: ref to CgContext, ty: int, mod: int, mname: string, cname: string, ritual: bool) -> void

 Registra un método sintético.

 ## Memoria
 Añade al catálogo.

### `nom_ctype`

> **nom_ctype**(c: ref to CgContext, ty: int) -> string

 Nombre C de un tipo nominal.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `value_ctype`

> **value_ctype**(c: ref to CgContext, ty: int) -> string

 Tipo C de un valor.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `base_name`

> **base_name**(c: ref to CgContext, ty: int) -> string

 Nombre canónico de una base (`string`, `int`, ...).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `json_field_name`

> **json_field_name**(c: ref to CgContext, fidx: int) -> string

 Nombre JSON externo de un campo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `field_cname`

> **field_cname**(c: ref to CgContext, fidx: int) -> string

 Nombre C del campo.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `next_sfx`

> **next_sfx**(c: ref to CgContext) -> string

 Sufijo único para locales del código emitido.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `int_sfx`

> **int_sfx**(n: int) -> string

 Sufijo numérico para locales (`0`, `1`, ...).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `c_escape`

> **c_escape**(text: string) -> string

 Escapa un texto para un literal C.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `eline`

> **eline**(c: ref to CgContext, text: string) -> void

 Línea al emisor.

 ## Memoria
 Presta el texto.

### `ein`

> **ein**(c: ref to CgContext) -> void

 Aumenta indentación.

 ## Memoria
 O(1).

### `eout`

> **eout**(c: ref to CgContext) -> void

 Reduce indentación.

 ## Memoria
 O(1).

### `emit_protos`

> **emit_protos**(c: ref to CgContext, ty: int) -> void

 Prototipos de las cinco funciones de una runa.

 ## Memoria
 Strings temporales liberados.

### `emit_bodies`

> **emit_bodies**(c: ref to CgContext, ty: int) -> void

 Cuerpos encode/write/decode/read/free de una runa.

 ## Memoria
 Strings temporales liberados.

### `emit_encode`

> **emit_encode**(c: ref to CgContext, cn: string) -> void

 `_pengu_json_encode_<T>`.

 ## Memoria
 Presta textos temporales.

### `emit_write`

> **emit_write**(c: ref to CgContext, cn: string, info: ref to SemaNominalInfo) -> void

 `_pengu_json_write_<T>`.

 ## Memoria
 Strings temporales liberados.

### `emit_write_field`

> **emit_write_field**(c: ref to CgContext, fidx: int, f: SemaField) -> void

 Un campo del escritor.

 ## Memoria
 Strings temporales liberados.

### `emit_decode`

> **emit_decode**(c: ref to CgContext, cn: string) -> void

 `_pengu_json_decode_<T>`.

 ## Memoria
 Strings temporales liberados.

### `emit_guard`

> **emit_guard**(c: ref to CgContext, cn: string, call: string, extra: string) -> void

 Emite una guarda de fallo del lector: `if (!call) { [extra] free; return false; }`.

 ## Memoria
 Presta `extra`.

### `emit_read`

> **emit_read**(c: ref to CgContext, cn: string, info: ref to SemaNominalInfo) -> void

 `_pengu_json_read_<T>`.

 ## Memoria
 Strings temporales liberados.

### `emit_read_field`

> **emit_read_field**(c: ref to CgContext, fidx: int, slot: int, f: SemaField, cn: string) -> void

 Una rama `if (pengu_json_key_eq(...))` del lector.

 ## Memoria
 Strings temporales liberados.

### `emit_free`

> **emit_free**(c: ref to CgContext, cn: string, info: ref to SemaNominalInfo) -> void

 `_pengu_json_free_<T>`.

 ## Memoria
 Strings temporales liberados.

### `write_value`

> **write_value**(c: ref to CgContext, ty: int, ptr: string, d: int) -> void

 Emite la escritura del valor apuntado por `ptr`.

 ## Memoria
 Strings temporales liberados.

### `write_base`

> **write_base**(c: ref to CgContext, ty: int, ptr: string) -> void

 Escritura de una base escalar.

 ## Memoria
 Strings temporales liberados.

### `read_value`

> **read_value**(c: ref to CgContext, ty: int, lvalue: string, label: string, d: int, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Emite la lectura del valor apuntado por `lvalue`.

 `ftys`/`fexprs` son los temporales en vuelo que hay que liberar si falla:
 `ftys` = -1 significa "sentencia plana en `fexprs`".

 ## Memoria
 Strings temporales liberados.

### `read_base`

> **read_base**(c: ref to CgContext, ty: int, lvalue: string, label: string, d: int, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Lectura de una base escalar.

 ## Memoria
 Strings temporales liberados.

### `read_list`

> **read_list**(c: ref to CgContext, ty: int, lvalue: string, label: string, d: int, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Lectura de `list of X`.

 ## Memoria
 Strings temporales liberados.

### `read_maybe`

> **read_maybe**(c: ref to CgContext, ty: int, lvalue: string, label: string, d: int, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Lectura de `maybe X`.

 ## Memoria
 Strings temporales liberados.

### `read_map`

> **read_map**(c: ref to CgContext, ty: int, lvalue: string, label: string, d: int, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Lectura de `map of string to X`.

 ## Memoria
 Strings temporales liberados.

### `read_omen`

> **read_omen**(c: ref to CgContext, ty: int, lvalue: string, d: int, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Lectura de un omen sin payload (string con el nombre de la variante).

 ## Memoria
 Strings temporales liberados.

### `emit_fail`

> **emit_fail**(c: ref to CgContext, ftys: ref to list of int, fexprs: ref to list of string) -> void

 Libera los temporales en vuelo y retorna `false`.

 ## Memoria
 Emite llamadas de liberación.

### `free_value`

> **free_value**(c: ref to CgContext, ty: int, ptr: string, d: int) -> void

 Emite la liberación del valor apuntado por `ptr`.

 ## Memoria
 Emite llamadas; libera temporales.

### `is_optional`

> **is_optional**(c: ref to CgContext, ty: int) -> bool

 `true` si el tipo es un `maybe` (campo opcional).

 ## Memoria
 O(1).

### `is_unsigned`

> **is_unsigned**(nm: string) -> bool

 `true` si la base es sin signo.

 ## Memoria
 O(1).

### `bits_of`

> **bits_of**(nm: string) -> int

 Bits de una base entera.

 ## Memoria
 O(1).

### `cat2`

> **cat2**(a: string, b: string) -> string

 Concatenación owned de dos textos.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `cat3`

> **cat3**(a: string, b: string, cc: string) -> string

 Concatenación owned de tres textos.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

