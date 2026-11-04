# psc.pkg.manifest

> Source: `src/psc/pkg/manifest.pengu`

psc/pkg/manifest.pengu — dependencias y edición quirúrgica de pengu.toml.

Sólo TOML. `pengu.yaml`, `pengu.yml` y `pengu.json` se rechazan
explícitamente; no hay parser YAML/JSON de manifiesto.

---

### `Dependency`

> rune Dependency

```pengu
    name as string
    kind as string
    source as string
    branch as string
    tag as string
    constraint as string
```

 Dependencia declarada.

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `find_root`

> **find_root**(start: string) -> string

 Busca la raíz con `pengu.toml`; rechaza formatos legados.

 Devuelve `""` si no hay manifiesto; el caller distingue el error con
 `legacy_manifest`.

### `legacy_manifest`

> **legacy_manifest**(base: string) -> string

 Ruta de un manifiesto legado en `base`, o `""`.

### `load`

> **load**(base: string) -> list of Dependency

 Carga dependencias.

### `find_dep`

> **find_dep**(ds: list of Dependency, name: string) -> int

 Índice de una dependencia o -1.

### `clone_dep`

> **clone_dep**(d: Dependency) -> Dependency

 Copia owned de una dependencia.

### `free`

> **free**(ds: list of Dependency) -> void

 Libera una lista de dependencias.

### `free_one`

> **free_one**(d: ref to Dependency) -> void

 Libera una dependencia.

### `valid_name`

> **valid_name**(name: string) -> bool

 `true` si el nombre es seguro.

### `starts_with`

> **starts_with**(s: string, p: string) -> bool

_Undocumented._

### `ends_with`

> **ends_with**(s: string, p: string) -> bool

_Undocumented._

### `find_sub`

> **find_sub**(s: string, p: string) -> int

_Undocumented._

### `escape`

> **escape**(s: string) -> string

 Escapa un string TOML básico.

### `entry_line`

> **entry_line**(d: Dependency) -> string

 Entrada TOML de una dependencia.

### `upsert`

> **upsert**(base: string, d: Dependency) -> bool

 Escribe/actualiza una dependencia en `[dependencies]` sin reformatear el resto.

### `remove`

> **remove**(base: string, name: string) -> bool

 Elimina una dependencia del manifiesto.

