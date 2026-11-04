# psc.pkg.lock

> Source: `src/psc/pkg/lock.pengu`

psc/pkg/lock.pengu — `pengu.lock` v1.

Formato TOML plano idéntico a stage0:
version, targets, y [[package]] con name/source/constraint/version/commit/
sha256/required_by/children.

---

### `Package`

> rune Package

```pengu
    name as string
    source as string
    constraint as string
    version as string
    commit as string
    sha256 as string
    required_by as list of string
    children as list of string
```

 Paquete bloqueado.

### `Lock`

> rune Lock

```pengu
    target as string
    packages as list of Package
```

 Lock completo.

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `tree_hash`

> **tree_hash**(root: string) -> string

 Hash SHA-256 del árbol (ignora .git/build/caches).

### `contains`

> **contains**(s: string, p: string) -> bool

 `true` si `s` contiene `p`.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

_Undocumented._

### `read`

> **read**(base: string) -> maybe Lock

 Lee un lock; `none` si no existe o es inválido.

### `dumps`

> **dumps**(lock: Lock) -> string

 Serializa un lock.

### `write`

> **write**(base: string, lock: Lock) -> bool

 Escribe un lock de forma atómica.

