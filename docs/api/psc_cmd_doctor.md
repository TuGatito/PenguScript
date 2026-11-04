# psc.cmd.doctor

> Source: `src/psc/cmd/doctor.pengu`

psc/cmd/doctor.pengu — `psc doctor`.

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

### `check_line`

> **check_line**(as_json: bool, name: string, ok: bool, detail: string) -> void

 Imprime o acumula un check.

 ## Memoria
 No retiene strings.

### `run_doctor`

> **run_doctor**(args: list of string) -> int

 Implementa `psc doctor`.

 ## Memoria
 Libera ParseResult y Paths.

