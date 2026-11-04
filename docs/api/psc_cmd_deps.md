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

### `fail`

> **fail**(msg: string) -> int

 Imprime un error de fase.

### `check_legacy`

> **check_legacy**(base: string) -> int

 Rechaza manifiestos YAML/JSON.

### `sync`

> **sync**(base: string, lib_dir: string, write_lock: bool, trusted: bool, exe: string, run_build: bool) -> int

 Resuelve, instala y escribe lock.

### `dep_by_name`

> **dep_by_name**(base: string, name: string) -> Dependency

 Lee una dependencia del manifiesto.

### `run_add`

> **run_add**(args: list of string) -> int

 `psc add`.

### `derive_name`

> **derive_name**(source: string) -> string

 Deriva nombre de una fuente.

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

