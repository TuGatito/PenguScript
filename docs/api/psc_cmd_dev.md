# psc.cmd.dev

> Source: `src/psc/cmd/dev.pengu`

psc/cmd/dev.pengu — comandos dev-only: `benchmark` y `selftest`.

No forman parte del camino de build de usuario; requieren el checkout y
Python (el harness histórico vive en benches/ y tests/).

---

### `copy`

> **copy**(s: string) -> string

 Copia owned.

 ## Memoria
 Devuelve string owned.

### `exists`

> **exists**(path: string) -> bool

 `true` si existe `path`.

 ## Memoria
 no asigna.

### `python_bin`

> **python_bin**(cwd: string) -> string

 Intérprete Python del checkout o `PSC_PYTHON`.

 ## Memoria
 Devuelve string owned.

### `BenchRow`

> rune BenchRow

```pengu
    name as string
    status as string
    build_ms as int
    run_ms as int
    size as int
```

 Medida de un caso.

### `run_case`

> **run_case**(name: string, cwd: string, compiler: string, repeat: int, warmup: int) -> BenchRow

 Ejecuta un caso nativo.

 ## Memoria
 Libera build/options.

### `run_benchmark`

> **run_benchmark**(args: list of string) -> int

 Implementa `psc benchmark` (nativo PSC, sin Python).

 ## Memoria
 Libera ParseResult y filas.

### `run_selftest`

> **run_selftest**(args: list of string) -> int

 Implementa `psc selftest`.

 ## Memoria
 Libera ParseResult.

