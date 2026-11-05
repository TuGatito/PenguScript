# psc.sema.check.json

> Source: `src/psc/sema/check/json.pengu`

psc/sema/check/json.pengu — validación y registro de `derive Json`.

Pass 1.5 de F3: después de recolectar tipos y firmas (y antes de chequear
cuerpos) valida las runas que derivan `Json` y registra sus dos métodos
sintéticos:

- `to_json into string`: instancia, `_pengu_json_encode_<T>`.
- `ritual from_json with text as string into result of T to string`:
  estático, `_pengu_json_decode_<T>`.

La validación es puramente estructural: no genera C. El codegen (`jsongen`)
lee `NIF_JSON`, los nombres JSON de `types->json_names` y los flags
`FIELD_JSON_SKIP` para emitir los codecs de cada tipo vivo.

## Memoria
Presta `SemaState`; internamente crea strings temporales owned.

---

### `JSON_MAX_TYPE_DEPTH`

> **JSON_MAX_TYPE_DEPTH** : int

 Profundidad máxima al validar un tipo anidado (evita recursión patológica).

### `check_all_json`

> **check_all_json**(p: ref to SemaProgram) -> void

 Valida todas las runas `derive Json` del programa y registra sus métodos.

 ## Memoria
 Presta el programa; crea `SemaState` por módulo y lo descarta.

### `check_module_json`

> **check_module_json**(s: ref to SemaState) -> void

 Valida las runas Json declaradas en el módulo actual.

 ## Memoria
 O(tipos + campos del módulo).

### `check_one`

> **check_one**(s: ref to SemaState, ty: int, info: ref to SemaNominalInfo) -> void

 Valida una runa Json concreta.

 ## Memoria
 O(campos del tipo); los nombres temporales se liberan aquí.

### `check_field`

> **check_field**(s: ref to SemaState, info: ref to SemaNominalInfo, fidx: int, used: ref to map of int to int) -> void

 Valida un campo: atributos y tipo.

 `used` acumula los `NameId` de los nombres JSON ya vistos en la runa.

 ## Memoria
 O(1) por campo; libera los textos temporales.

### `check_field_type`

> **check_field_type**(s: ref to SemaState, f: SemaField, fname: string) -> void

 Comprueba que el tipo del campo se puede serializar.

 ## Memoria
 Recursivo por la forma del tipo.

### `type_reason`

> **type_reason**(s: ref to SemaState, t: int, depth: int) -> int

 Motivo por el que `t` no es serializable (`0` si lo es).

 - `1`: tipo no soportado.
 - `2`: runa anidada sin `derive Json`.
 - `3`: omen con payload.

 ## Memoria
 Recursivo; no posee recursos.

### `type_display`

> **type_display**(s: ref to SemaState, t: int) -> string

 Nombre legible de un tipo nominal (para mensajes).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `parse_json_name`

> **parse_json_name**(s: ref to SemaState, attr: int) -> int

 Lee `@json("...")` y devuelve el `NameId` externo (`-1` si es inválido).

 ## Memoria
 Interna el nombre; emite diagnóstico si el atributo está mal formado.

### `strip_quotes`

> **strip_quotes**(raw: string) -> string

 Quita las comillas de un literal string (soporta `"x"` y `"""x"""`).

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `register_methods`

> **register_methods**(s: ref to SemaState, ty: int, info: ref to SemaNominalInfo) -> void

 Registra `to_json` y `from_json` en el tipo.

 ## Memoria
 Añade símbolos, firmas y parámetros a las tablas.

### `codec_name`

> **codec_name**(kind: string, ctype: string) -> string

 `_pengu_json_<kind>_<T>` como string owned.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

