# psc.os.proc

> Source: `src/psc/os/proc.pengu`

psc/os/proc.pengu — ejecución de argv sin shell.

POSIX: fork + execvp + waitpid. El hijo hereda stdin/stdout/stderr, así que
`psc run` conserva la interactividad y los argumentos nunca pasan por `sh`.

---

### `exec_replace`

> **exec_replace**(argv: list of string) -> int

 Ejecuta un argv y devuelve el exit code (o 128+señal).

 ## Memoria
 Los strings de `argv` son prestados.
 Reemplaza el proceso actual por `argv[0]` (execvp). No vuelve si tiene
 éxito; si falla, devuelve 127.

 ## Memoria
 Los strings de `argv` son prestados y deben sobrevivir a la llamada.

### `run_argv`

> **run_argv**(argv: list of string) -> int

_Undocumented._

### `spawn_argv`

> **spawn_argv**(argv: list of string) -> int

 Lanza un argv sin esperar y devuelve el PID (0 si falla).

 ## Memoria
 Los strings de `argv` son prestados.

### `wait_pid`

> **wait_pid**(pid: int) -> int

 Espera bloqueante por un PID; devuelve el exit code.

### `pid_alive`

> **pid_alive**(pid: int) -> bool

 `true` si el PID sigue vivo (reap no bloqueante).

### `terminate`

> **terminate**(pid: int) -> bool

 Termina un PID (SIGTERM), sin esperar.

### `run_argv_quiet`

> **run_argv_quiet**(argv: list of string) -> int

 Ejecuta un argv descartando stdout/stderr (benchmarks).

