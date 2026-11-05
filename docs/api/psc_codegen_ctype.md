# psc.codegen.ctype

> Source: `src/psc/codegen/ctype.pengu`

psc/codegen/ctype.pengu — traducción `SemaType` → C.

Es la única puerta de tipos C. Ningún emisor debe escribir un tipo C a mano.

---

### `type_has_param`

> **type_has_param**(t: ref to SemaTypeTable, id: int) -> bool

 `true` si un tipo contiene un `TkTypeParam`.

 ## Memoria
 O(profundidad).

### `nominal_erased`

> **nominal_erased**(t: ref to SemaTypeTable, info: SemaNominalInfo) -> bool

 `true` si la instancia no tiene campos dependientes de T.

 Los contenedores `LinkedList of T`, `UnorderedSet of T`, etc. solo guardan
 un handle; pueden compartir el struct C de la plantilla aunque el `TypeId`
 semántico sea distinto. Esto evita generar un struct por `T` sin perder la
 comprobación de tipos.

 ## Memoria
 O(campos).

### `template_type_of`

> **template_type_of**(t: ref to SemaTypeTable, info: SemaNominalInfo) -> int

 `TypeId` de la plantilla de una instancia.

 ## Memoria
 O(tipos); solo se usa para nombres C de instancias borradas.

### `type_kind_code`

> **type_kind_code**(ns: ref to CgNames, id: int) -> int

 Código de `kind` para los descriptores de contenedores CC.

 0 = entero/POD numérico, 1 = string, 2 = float, 9 = bytes.

 ## Memoria
 O(1).

### `c_type`

> **c_type**(ns: ref to CgNames, id: int) -> string

 Tipo C de un `TypeId`.

 Devuelve un string owned; el llamador lo libera con `banish`.

### `declare`

> **declare**(ct: string, name: string) -> string

 Declarador C de un nombre con el tipo `ct`.

 Si `ct` contiene el hueco `(*)` de un puntero a función, el nombre se inserta
 ahí (`int32_t (*value)(PsParser*)`); en otro caso se usa `tipo nombre`.

 ## Memoria
 Devuelve un string owned; liberar con `banish`.

### `base_c_type`

> **base_c_type**(ns: ref to CgNames, nid: int) -> string

 Tipo C de un primitivo canónico.

 Devuelve un string owned (literal o pool).

### `std_text`

> **std_text**(ns: ref to CgNames, nid: int) -> string

 Texto de un NameId (owned).

### `tuple_c_name`

> **tuple_c_name**(ns: ref to CgNames, id: int) -> string

 Nombre de una tupla sintética.

### `fn_c_type`

> **fn_c_type**(ns: ref to CgNames, info_idx: int) -> string

 Tipo C de una función, como declarador sin nombre.

### `pointer_type_name`

> **pointer_type_name**(pt: string) -> string

 Nombre C de un puntero a `pt`, válido también si `pt` es un puntero a función.

 `c_type` imprime los punteros a función como `R (*)(A)`, donde el `*` va
 dentro del paréntesis; añadir otro `*` al final produce un tipo C inválido.
 El puntero a `R (*)(A)` es `R (**)(A)`.

 ## Memoria
 Devuelve un string owned.

