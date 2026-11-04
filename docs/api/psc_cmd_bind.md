# psc.cmd.bind

> Source: `src/psc/cmd/bind.pengu`

psc/cmd/bind.pengu — `psc bind`: wrapper del helper `pengu-bind`.

No reimplementa el parser de cabeceras: localiza el binario congelado y le
pasa los flags por argv (sin shell).

---

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `starts_dash`

> **starts_dash**(s: string) -> bool

_Undocumented._

### `helper_name`

> **helper_name**() -> string

 Nombre del helper según plataforma.

### `is_windows`

> **is_windows**() -> bool

_Undocumented._

### `usable`

> **usable**(p: string) -> bool

 `true` si `p` es ejecutable/fichero.

### `locate`

> **locate**(exe: string) -> string

 Busca el helper.

 Orden: `PENGU_BIND`, sibling de `psc`, `libexec/pengu`, `bin`, `PATH`.
 Devuelve `""` si no aparece.

### `print_help`

> **print_help**() -> void

 Imprime ayuda.

### `run_helper`

> **run_helper**(helper: string, args: list of string) -> int

 Ejecuta un helper con argv y devuelve su exit code.

### `run`

> **run**(args: list of string) -> int

 Implementa `psc bind`.

