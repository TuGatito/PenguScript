# psc.dap.mi

> Source: `src/psc/dap/mi.pengu`

psc/dap/mi.pengu — parser mínimo de GDB/MI.

GDB/MI no es JSON: las respuestas son `^done,clave="valor",...`, los eventos
`*stopped,...` y las listas `[frame={...},frame={...}]`. Este módulo extrae
los campos de primer nivel y los objetos de una lista, sin intentar modelar
todo el protocolo. Es suficiente para el adapter y se puede probar aislado.

---

### `MiField`

> rune MiField

```pengu
    key as string
    value as string
```

 Campo `clave=valor` de un registro MI.

### `digit_value`

> **digit_value**(c: string) -> int

 Valor decimal de un dígito ASCII, o -1.

 ## Memoria
 No asigna.

### `is_key_char`

> **is_key_char**(c: string) -> bool

 `true` si `c` puede formar parte de una clave MI.

 ## Memoria
 No asigna.

### `unescape`

> **unescape**(s: string) -> string

 Deshace los escapes de un string C de MI.

 ## Memoria
 Devuelve un string owned.

### `parse_value`

> **parse_value**(s: string, start: int) -> string

 Valor de un campo, ya desescapado si era un string C.

 ## Memoria
 Devuelve un string owned.

### `parse_fields`

> **parse_fields**(line: string) -> list of MiField

 Divide un registro MI (`^done,...`, `*stopped,...`) en campos.

 ## Memoria
 Devuelve una lista owned; liberar con `banish`.

### `field`

> **field**(fields: ref to list of MiField, key: string) -> string

 Busca un campo de primer nivel y devuelve su valor.

 ## Memoria
 Devuelve un string owned (`""` si no existe).

### `is_response`

> **is_response**(line: string) -> bool

 `true` si el registro es una respuesta (`^done`, `^error`, ...).

### `token_of`

> **token_of**(line: string) -> int

 Token numérico de una respuesta MI, o -1.

### `result_class`

> **result_class**(line: string) -> string

 Clase de resultado: `done`, `running`, `error`, `stopped`, ...

 ## Memoria
 Devuelve un string owned.

### `split_objects`

> **split_objects**(text: string) -> list of string

 Extrae los objetos `{...}` de una lista MI.

 Ejemplo: `[frame={level="0"},frame={level="1"}]` devuelve dos strings.

 ## Memoria
 Devuelve una lista owned; liberar con `banish`.

