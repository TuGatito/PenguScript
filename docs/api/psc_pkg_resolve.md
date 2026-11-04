# psc.pkg.resolve

> Source: `src/psc/pkg/resolve.pengu`

psc/pkg/resolve.pengu — resolución e instalación de dependencias.

---

### `Graph`

> rune Graph

```pengu
    ok as bool
    error as string
    packages as list of Package
```

 Resultado.

### `copy`

> **copy**(s: string) -> string

_Undocumented._

### `find_pkg`

> **find_pkg**(ps: list of Package, name: string) -> int

 Busca un paquete por nombre.

### `ensure`

> **ensure**(base: string, lib_dir: string, d: Dependency, parent: string) -> maybe Package

 Asegura/instala y crea el paquete.

### `resolve`

> **resolve**(base: string, lib_dir: string, deps: list of Dependency) -> Graph

 Resuelve el grafo desde dependencias directas.

### `free`

> **free**(g: ref to Graph) -> void

 Libera un grafo.

