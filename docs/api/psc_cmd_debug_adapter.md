# psc.cmd.debug_adapter

> Source: `src/psc/cmd/debug_adapter.pengu`

psc/cmd/debug_adapter.pengu — entrada de `psc debug-adapter`.

El adapter habla DAP por stdio; no interpreta los argumentos de la línea de
comandos (el editor manda la configuración en `launch`). Se aceptan `--help`
y `--stdio` por compatibilidad, pero el protocolo siempre usa stdio.

---

### `print_help`

> **print_help**() -> void

_Undocumented._

### `run_debug_adapter`

> **run_debug_adapter**(args: list of string) -> int

_Undocumented._

