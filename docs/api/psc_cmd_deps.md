# psc.cmd.deps

> Source: `src/psc/cmd/deps.pengu`

psc/cmd/deps.pengu — package manager F9.

Sólo TOML: pengu.yaml/json se rechazan explícitamente.

---

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `project_root`

> **project_root**() -> string

 Raíz del proyecto o `""`.

### `project_lib_dir`

> **project_lib_dir**(base: string) -> string

 `lib_dir` efectivo del proyecto.

### `fail`

> **fail**(msg: string) -> int

 Imprime un error de fase.

### `check_legacy`

> **check_legacy**(base: string) -> int

 Rechaza manifiestos YAML/JSON.

### `sync`

> **sync**(base: string, lib_dir: string, write_lock: bool, trusted: bool, exe: string, run_build: bool, force: bool) -> int

 Resuelve, instala y escribe lock.

### `dep_by_name`

> **dep_by_name**(base: string, name: string) -> Dependency

 Lee una dependencia del manifiesto.

### `run_add`

> **run_add**(args: list of string) -> int

 `psc add`.

### `adopt_import_name`

> **adopt_import_name**(base: string, lib_dir: string, old_name: string) -> maybe string

 Si el paquete instalado declara `[project] import`, mueve su directorio
 a `lib/<import>` y devuelve el nombre nuevo. Solo se usa cuando el usuario
 no paso `--name`: asi `psc add <url-de-raylib-pengu>` queda importable como
 `import raylib`. Devuelve `none` si no hay import, si el nombre es invalido
 o si el destino ya existe.

### `derive_name`

> **derive_name**(source: string) -> string

 Deriva el nombre del paquete a partir de la fuente (ruta o URL).
 `source` es prestado: no se libera aquí. El nombre devuelto es propio.

### `ends_with`

> **ends_with**(s: string, p: string) -> bool

_Undocumented._

### `run_remove`

> **run_remove**(args: list of string) -> int

 `psc remove`.

### `run_update`

> **run_update**(args: list of string) -> int

 `psc update`.

### `run_upgrade`

> **run_upgrade**(args: list of string) -> int

 `psc upgrade`.

### `run_verify`

> **run_verify**(args: list of string) -> int

 `psc verify`.

### `run_vendor`

> **run_vendor**(args: list of string) -> int

 `psc vendor`.

