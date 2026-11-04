# psc.cmd.watch

> Source: `src/psc/cmd/watch.pengu`

psc/cmd/watch.pengu — `psc watch` (polling portátil F7).

Observa el entry, todos los `.pengu` de su proyecto y `pengu.toml`, y
reinicia el hijo cuando cambia la huella (mtime+tamaño). Sin inotify.

---

### `print_help`

> **print_help**() -> void

 Ayuda.

### `copy`

> **copy**(s: string) -> string

 Copia owned.

### `ends_with`

> **ends_with**(s: string, p: string) -> bool

 `true` si `s` termina en `p`.

### `collect_paths`

> **collect_paths**(script: string, out: list of string) -> void

 Recolecta `.pengu` del proyecto y el manifiesto.

 ## Memoria
 `out` es prestado; los paths se copian.

### `fingerprint`

> **fingerprint**(paths: list of string) -> string

 Huella de mtime+tamaño.

 ## Memoria
 Devuelve string owned.

### `build_and_spawn`

> **build_and_spawn**(script: string, cc: string, child: list of string, verbose: bool) -> int

 Compila y lanza el hijo; devuelve PID (0 si falla).

 ## Memoria
 Libera build result/options.

### `run_watch`

> **run_watch**(args: list of string) -> int

 Implementa `psc watch`.

