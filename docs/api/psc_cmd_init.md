# psc.cmd.init

> Source: `src/psc/cmd/init.pengu`

psc/cmd/init.pengu — `psc init` y `psc new` (plantillas de proyecto F6).

---

### `print_init_help`

> **print_init_help**() -> void

 Ayuda de `init`.

 ## Memoria
 No asigna.

### `print_new_help`

> **print_new_help**() -> void

 Ayuda de `new`.

 ## Memoria
 No asigna.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `safe_name`

> **safe_name**(s: string) -> string

 Nombre seguro para un identificador C/PenguScript.

 ## Memoria
 Devuelve string owned.

### `split_links`

> **split_links**(s: string) -> list of string

 Lista de links desde `a,b`.

 ## Memoria
 Devuelve lista owned.

### `toml_list`

> **toml_list**(xs: list of string) -> string

 Render TOML de una lista de strings.

 ## Memoria
 Devuelve string owned.

### `create_project`

> **create_project**(name: string, template: string, out_type: string, links: list of string, cc: string, out_name: string, force: bool) -> int

 Crea un proyecto.

 ## Memoria
 Libera argumentos y strings temporales.

### `run_init`

> **run_init**(args: list of string) -> int

 Implementa `psc init`.

 ## Memoria
 Libera ParseResult y links.

### `run_new`

> **run_new**(args: list of string) -> int

 Implementa `psc new`.

 ## Memoria
 Libera ParseResult.

