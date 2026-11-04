# psc.cmd.fmt

> Source: `src/psc/cmd/fmt.pengu`

psc/cmd/fmt.pengu — `psc fmt` (formato conservador F6).

Normaliza indentación, espacios finales, saltos y líneas en blanco. No
reinterpreta strings, triples ni bloques `antiquus`; las líneas dentro de un
triple se dejan intactas.

---

### `print_help`

> **print_help**() -> void

 Ayuda.

 ## Memoria
 No asigna.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `ends_with`

> **ends_with**(s: string, suffix: string) -> bool

 `true` si `s` termina en `suffix`.

 ## Memoria
 O(suffix).

### `triple_count`

> **triple_count**(line: string) -> int

 `true` si la línea abre/cierra un triple string.

 ## Memoria
 O(1).

### `FmtConfig`

> rune FmtConfig

```pengu
    width as int
    tabs as bool
    blank as int
```

 Configuración de formato.

 ## Memoria
 POD.

### `load_config`

> **load_config**(path: string) -> FmtConfig

 Carga `.pengufmt.toml` (claves planas `indent`, `tabs`, `blank_lines_max`).

 ## Memoria
 Devuelve POD; no retiene.

### `detect_unit`

> **detect_unit**(lines: list of string, fallback: int) -> int

 Detecta la unidad de indentación del fuente.

 ## Memoria
 O(n).

### `normalize_code`

> **normalize_code**(s: string) -> string

 Normaliza espacios en código (nunca dentro de strings).

 ## Memoria
 Devuelve string owned.

### `indent_line`

> **indent_line**(line: string, source_unit: int, width: int, tabs: bool) -> string

 Convierte la indentación de una línea.

 ## Memoria
 Devuelve string owned.

### `format_text`

> **format_text**(text: string, width: int, tabs: bool, blank_max: int) -> string

 Formatea texto.

 ## Memoria
 Devuelve string owned.

### `run_stdin`

> **run_stdin**(width: int, tabs: bool, blank_max: int, check_only: bool) -> int

 Formatea stdin.

 ## Memoria
 Libera texto.

### `write_atomic`

> **write_atomic**(path: string, text: string) -> bool

 Escritura atómica (tmp + rename).

 ## Memoria
 Libera temporales.

### `run_fmt`

> **run_fmt**(args: list of string) -> int

 Implementa `psc fmt`.

 ## Memoria
 Libera ParseResult.

