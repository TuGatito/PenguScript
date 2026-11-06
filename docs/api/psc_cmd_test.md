# psc.cmd.test

> Source: `src/psc/cmd/test.pengu`

psc/cmd/test.pengu — `psc test`.

---

### `print_help`

> **print_help**() -> void

 Ayuda.

 ## Memoria
 No asigna.

### `fingerprint`

> **fingerprint**(path: string) -> string

 Huella de un archivo/directorio.

### `run_test`

> **run_test**(args: list of string) -> int

 Implementa `psc test`.

 ## Memoria
 Libera opciones/resultado.

### `cov_has_suffix`

> **cov_has_suffix**(s: string, suffix: string) -> bool

 ¿Termina `s` con `suffix`?

### `cov_index_of`

> **cov_index_of**(s: string, needle: string) -> int

 Índice de `needle` en `s`, o -1.

### `report_coverage`

> **report_coverage**() -> void

 Resume los `.gcov` de PenguScript y silencia las cabeceras del runtime.

### `emit_coverage`

> **emit_coverage**(artifact: string) -> void

 Ejecuta gcov sobre el artefacto y deja los reportes `.gcov` (con `#line`,
 las rutas son los `.pengu` originales).

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `copy_path`

> **copy_path**(s: string) -> string

 Copia owned de una ruta.

 ## Memoria
 Devuelve string owned; liberar con `banish`.

