# psc.cmd.build

> Source: `src/psc/cmd/build.pengu`

psc/cmd/build.pengu — comandos `build`, `run` y `expand` de F5.

---

### `compiler_identity`

> **compiler_identity**(path: string) -> string

 Identidad del compilador para la caché de scripts.

 ## Memoria
 Devuelve string owned.

### `starts_with`

> **starts_with**(s: string, prefix: string) -> bool

 `true` si `s` empieza por `prefix`.

 ## Memoria
 O(prefix); no asigna.

### `starts_dash`

> **starts_dash**(s: string) -> bool

 `true` si `s` empieza por `-`.

 ## Memoria
 O(1).

### `print_build_help`

> **print_build_help**() -> void

 Ayuda de `build`.

 ## Memoria
 No asigna.

### `print_run_help`

> **print_run_help**() -> void

 Ayuda de `run`.

 ## Memoria
 No asigna.

### `print_expand_help`

> **print_expand_help**() -> void

 Ayuda de `expand`.

 ## Memoria
 No asigna.

### `run_build`

> **run_build**(args: list of string) -> int

 Implementa `psc build`.

 ## Memoria
 Libera opciones y resultado.

### `run_check_project`

> **run_check_project**(path: string, t: Target, explicit: bool) -> int

 Implementa `psc check` sobre un proyecto.

 ## Memoria
 Libera opciones y resultado.

### `run_run`

> **run_run**(args: list of string) -> int

 Implementa `psc run`.

 ## Memoria
 Libera opciones, resultado y args del hijo.

### `run_expand`

> **run_expand**(args: list of string) -> int

 Implementa `psc expand`.

 ## Memoria
 Libera opciones, resultado y bundle.

### `copy_path`

> **copy_path**(s: string) -> string

 Copia owned de un path.

 ## Memoria
 Devuelve string owned.

