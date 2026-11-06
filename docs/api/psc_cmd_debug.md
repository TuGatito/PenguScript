# psc.cmd.debug

> Source: `src/psc/cmd/debug.pengu`

psc/cmd/debug.pengu — `psc debug`: compila en modo debug y abre gdb/lldb.

El bundle generado lleva `#line` hacia los `.pengu` y el perfil debug añade
`-g`, así que los breakpoints se ponen sobre rutas y líneas PenguScript:

    psc debug . -- arg1 arg2

En gdb: `break /ruta/src/main.pengu:12`, `run`, `bt`. Para fibras
(corrutinas) usa `pengu-fibers`: lista las corrutinas vivas y la pila
capturada en su último yield (PENGU_FIBER_TRACE=1, activado aquí).

---

### `print_help`

> **print_help**() -> void

 Ayuda.

 ## Memoria
 No asigna.

### `run_debug`

> **run_debug**(args: list of string) -> int

 Implementa `psc debug`.

 ## Memoria
 Libera opciones/resultado.

