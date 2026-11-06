# psc.pkg.install

> Source: `src/psc/pkg/install.pengu`

psc/pkg/install.pengu — instala una dependencia en lib/<name>.

La instalación se hace en un directorio de staging y sólo se mueve al
destino cuando el contenido es válido. Un fallo no deja `lib/<name>` a
medias y nunca libera strings prestados del manifiesto.

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

### `satisfies_text`

> **satisfies_text**(version: string, constraint: string) -> bool

 `true` si `version` satisface `constraint` (vacío y `*` = cualquiera).

### `replace_stage`

> **replace_stage**(stage: string, target: string) -> bool

 Limpia un staging y el destino anterior.

### `install_from`

> **install_from**(base: string, lib_dir: string, d: Dependency, origin: string) -> maybe Installed

 Instala una dependencia.

 `origin` es el directorio contra el que se resuelven las rutas relativas
 (la raíz del consumidor o el paquete que declara la dependencia).
 Devuelve `none` en error.

### `install`

> **install**(base: string, lib_dir: string, d: Dependency) -> maybe Installed

 Compatibilidad: instala resolviendo rutas relativas contra la raíz.

