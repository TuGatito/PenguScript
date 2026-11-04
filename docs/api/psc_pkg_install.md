# psc.pkg.install

> Source: `src/psc/pkg/install.pengu`

psc/pkg/install.pengu — instala una dependencia en lib/<name>.

---

### `Installed`

> rune Installed

```pengu
    name as string
    path as string
    version as string
    commit as string
    kind as string
    source as string
    constraint as string
```

 Resultado de instalar.

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `dep_version`

> **dep_version**(dir: string) -> string

 Lee `version` de un manifiesto de dependencia.

### `install`

> **install**(base: string, lib_dir: string, d: Dependency) -> maybe Installed

 Instala una dependencia.

 Devuelve `none` en error.

