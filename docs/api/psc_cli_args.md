# psc.cli.args

> Source: `src/psc/cli/args.pengu`

psc/cli/args.pengu — parser de argv compartido.

Acepta `--flag`, `--flag=value`, `--flag value`, flags cortas y `--`.
Cada comando declara qué flags consumen valor, cuáles son switches y cuáles
se acumulan (`-D`).

---

### `ParsedArgs`

> rune ParsedArgs

```pengu
    values as map of string to string
    switches as map of string to bool
    lists as map of string to list of string
    positionals as list of string
```

 Argumentos ya parseados.

 ## Memoria
 Strings propios; liberar con `free_parsed`.

### `ParseResult`

> rune ParseResult

```pengu
    ok as bool
    error as string
    args as ParsedArgs
```

 Resultado del parser.

 ## Memoria
 `args` y `error` propios; liberar con `free_parse_result`.

### `empty_args`

> **empty_args**() -> ParsedArgs

 Argumentos vacíos.

 ## Memoria
 Mapas/listas propios.

### `copy`

> **copy**(s: string) -> string

 Copia un string.

 ## Memoria
 Devuelve string owned.

### `has_str`

> **has_str**(xs: list of string, s: string) -> bool

 `true` si `xs` contiene `s`.

 ## Memoria
 O(n).

### `ensure_list`

> **ensure_list**(a: ref to ParsedArgs, key: string) -> void

 Añade una lista vacía para `key` si no existe.

 ## Memoria
 No asigna si ya existe.

### `add_list`

> **add_list**(a: ref to ParsedArgs, key: string, value: string) -> void

 Añade un valor repetible.

 ## Memoria
 Copia el valor.

### `parse`

> **parse**(argv: list of string, start: int, value_flags: list of string, switch_flags: list of string, list_flags: list of string) -> ParseResult

 Parser principal.

 `value_flags`: flags que consumen el siguiente argv o `=`.
 `switch_flags`: flags booleanas.
 `list_flags`: flags repetibles que consumen valor.

 ## Memoria
 Devuelve ParseResult owned.

### `value`

> **value**(a: ref to ParsedArgs, key: string) -> string

 Valor de un flag, o `""`.

 ## Memoria
 Devuelve string prestado.

### `enabled`

> **enabled**(a: ref to ParsedArgs, key: string) -> bool

 `true` si el switch está activo.

 ## Memoria
 O(1).

### `list`

> **list**(a: ref to ParsedArgs, key: string) -> list of string

 Lista de un flag repetible (prestada).

 ## Memoria
 Devuelve lista prestada; puede estar vacía.

### `first_positional`

> **first_positional**(a: ref to ParsedArgs) -> string

 Primer posicional o `""`.

 ## Memoria
 Devuelve string prestado.

### `free_parsed`

> **free_parsed**(a: ref to ParsedArgs) -> void

 Libera argumentos.

 ## Memoria
 Libera valores, listas y posicionales.

### `free_parse_result`

> **free_parse_result**(r: ref to ParseResult) -> void

 Libera un resultado.

 ## Memoria
 Libera args/error.

