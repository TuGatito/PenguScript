# psc.pkg.semver

> Source: `src/psc/pkg/semver.pengu`

psc/pkg/semver.pengu — SemVer y constraints para dependencias.

Puerto de `pengu_semver.py`: versiones `1.2.3`, tags con `v`, prerelease y
constraints `^`, `~`, `>=`, `>`, `<=`, `<`, `=`, `*` y listas por coma.

---

### `Version`

> rune Version

```pengu
    major as int
    minor as int
    patch as int
    pre as string
```

 Versión SemVer.

### `Constraint`

> rune Constraint

```pengu
    op as int
    version as Version
```

 Constraint.

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `digit`

> **digit**(c: int) -> bool

 ¿Dígito?

### `parse_version`

> **parse_version**(text: string) -> maybe Version

 Parsea una versión; `none` si inválida.

### `cmp`

> **cmp**(a: Version, b: Version) -> int

 Compara versiones: -1, 0, 1.

### `pres_less`

> **pres_less**(a: string, b: string) -> bool

 Comparación simple de prerelease.

### `parse_constraint`

> **parse_constraint**(text: string) -> maybe Constraint

 Parsea un constraint; `none` si inválido.

### `parse_constraints`

> **parse_constraints**(text: string) -> list of Constraint

 Parsea una lista de constraints separadas por coma.

### `satisfies_one`

> **satisfies_one**(v: Version, c: Constraint) -> bool

 ¿La versión satisface el constraint?

### `satisfies`

> **satisfies**(v: Version, cs: list of Constraint) -> bool

 ¿Satisface todos?

### `select_tag`

> **select_tag**(tags: list of string, constraints: list of Constraint) -> string

 Elige el tag más alto que satisface; `""` si no.

