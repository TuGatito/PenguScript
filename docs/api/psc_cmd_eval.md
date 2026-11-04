# psc.cmd.eval

> Source: `src/psc/cmd/eval.pengu`

psc/cmd/eval.pengu — `psc eval`.

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

### `run_eval`

> **run_eval**(args: list of string) -> int

 Implementa `psc eval`.

 ## Memoria
 Libera opciones y temporales.

