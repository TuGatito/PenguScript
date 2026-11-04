# psc.codegen.comptime

> Source: `src/psc/codegen/comptime.pengu`

psc/codegen/comptime.pengu — evaluación de `when` en codegen.

F3 comprueba ambas ramas; F4 debe emitir sólo la viva. Este módulo evalúa
las condiciones comptime que el driver conoce (`os`, `arch`, `compiler`,
`defined`, `debug` y booleanos). Devuelve `-1` si no sabe evaluarlas.

---

### `is_defined`

> **is_defined**(o: CgOptions, name: string) -> bool

 `true` si `name` está en `defines` (`NAME` o `NAME=value`).

 ## Memoria
 O(defines).

### `unquote`

> **unquote**(m: SemaModule, node: int) -> string

 Texto sin comillas de un `string_lit`.

 ## Memoria
 Devuelve string owned.

### `var_name`

> **var_name**(m: SemaModule, node: int) -> string

 Texto de un `var_ref`.

 ## Memoria
 Devuelve string owned.

### `option_value`

> **option_value**(o: CgOptions, name: string) -> string

 Valor de un `var_ref` comptime (`os`, `arch`, `compiler`, `wasm_target`), o "".

 ## Memoria
 Devuelve string owned.

### `option_known`

> **option_known**(name: string) -> bool

 `true` si `name` es una variable comptime de tipo string conocida.

 ## Memoria
 O(1).

### `bool_option`

> **bool_option**(o: CgOptions, m: SemaModule, name: string) -> int

 Valor booleano de un `var_ref` comptime, o -1 si no es booleano.

 ## Memoria
 No asigna.

### `evaluate`

> **evaluate**(o: CgOptions, m: SemaModule, node: int) -> int

 Evalúa una condición comptime.

 Devuelve 1 (true), 0 (false) o -1 (desconocido).

 ## Memoria
 Strings temporales liberados.

