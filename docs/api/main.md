# main

> Source: `src/main.pengu`

psc/src/main.pengu — CLI de PSC (F1 + F2 + F3).

```text
psc lex <file> [--comments] [--no-indent] [--check]
               [--diagnostics=plain|json] [--color|--no-color]
psc lex --stdin ...
psc parse <file> [--check] [--no-header] [--stdin]
psc ast <file> ...
psc check <file> [--diagnostics=plain|json] [--json] [-D NAME] [--stdin]
psc version
```

Exit codes: 0 sin errores, 1 con diagnósticos de error, 2 uso/E-S.

## Memoria
El argv de `std.rites` se libera al final de `main`; cada recurso de una
ejecución se libera con `banish` antes de volver.

---

### `copy_path`

> **copy_path**(s: string) -> string

 Copia owned de un string.

 ## Memoria
 Devuelve string owned.

### `main`

> **main**() -> int

 Punto de entrada.

### `dispatch`

> **dispatch**(args: list of string) -> int

 Despacha el subcomando.

 ## Memoria
 No libera `args` (los libera `main`).

### `run_lex`

> **run_lex**(args: list of string) -> int

 Implementa `psc lex`.

 ## Memoria
 Libera todo lo que crea antes de volver.

### `run_parse`

> **run_parse**(args: list of string) -> int

 Implementa `psc parse`.

 ## Memoria
 Libera todo lo que crea antes de volver.

### `run_check`

> **run_check**(args: list of string) -> int

 Implementa `psc check`.

 ## Memoria
 Libera la opción/resultado antes de volver.

### `run_emit_c`

> **run_emit_c**(args: list of string) -> int

 Implementa `psc emit-c`: F3 + codegen, sin compilador C.

 ## Memoria
 Libera programa y bundle; las opciones las libera el programa.

### `report_check`

> **report_check**(result: SemaResult, json_diags: bool, json_u16: bool, force_color: bool, no_color: bool) -> int

 Renderiza y libera un resultado; devuelve el exit code.

 ## Memoria
 Libera el programa del resultado.

### `starts_with`

> **starts_with**(s: string, prefix: string) -> bool

 `true` si `s` empieza por `prefix`.

 ## Memoria
 O(prefix), no asigna.

### `print_parse_help`

> **print_parse_help**() -> void

 Ayuda de `parse`.

 ## Memoria
 No asigna.

### `open_input`

> **open_input**(path: string, use_stdin: bool, opts: LexOptions) -> Session

 Abre el fuente desde stdin o desde un archivo.

 ## Memoria
 Devuelve una sesión owned; liberar con `banish`.

### `starts_dash`

> **starts_dash**(s: string) -> bool

 `true` si el primer byte de `s` es `-`, sin asignar un substring.

 ## Memoria
 O(1), no asigna.

### `print_help`

> **print_help**() -> void

 Ayuda general.

 ## Memoria
 No asigna.

### `print_check_help`

> **print_check_help**() -> void

 Ayuda de `lex`.

 ## Memoria
 No asigna.
 Ayuda de `check`.

 ## Memoria
 No asigna.

### `print_emit_c_help`

> **print_emit_c_help**() -> void

 Ayuda de `emit-c`.

 ## Memoria
 No asigna.

### `print_lex_help`

> **print_lex_help**() -> void

 Ayuda de `lex`.

 ## Memoria
 No asigna.

