---

<a id="sec-03"></a>
## 3. Programa, módulos y entrada

### 3.1 Archivos y raíces

Un programa PenguScript se compone de archivos `.pengu`.

- La raíz de un binario es `main.pengu`.
- La raíz de una librería es `lib.pengu`.
- Un módulo llamado `geometry` se busca en `geometry.pengu` o en
  `geometry/scroll.pengu`, en ese orden.
- No hay `mod`, `use`, `pub` ni `crate`: esos nombres pertenecen al backend.

### 3.2 Módulos

```pengu
scroll geometry
    rune Point
        x: Float
        y: Float

    unveil norm = (p: Point) -> Float
        (p.x * p.x + p.y * p.y).sqrt()
```

`scroll` declara un módulo inline. También puede declarar un módulo de archivo:

```pengu
scroll geometry
```

En ese caso se carga `geometry.pengu` o `geometry/scroll.pengu`.

Un módulo puede contener records, sums, funciones, constantes, pacts, rituals y
submódulos. No puede contener `bind` ni `morph` en su nivel superior: el estado
global mutable no existe.

### 3.3 Imports

```pengu
summon geometry::Point
summon geometry::norm as length
```

`summon` importa un item o un módulo. No hay imports glob. Un nombre importado
puede renombrarse con `as`.

Los items del mismo módulo se ven sin importación. Los items de un submódulo se
importan con su ruta.

### 3.4 Visibilidad

Por defecto todo es privado al módulo.

| Forma | Alcance |
|---|---|
| `unveil` | público |
| `unveil(tome)` | visible en el tome actual |
| `unveil(scroll)` | visible en el módulo padre |

`unveil` se escribe antes del item, del campo o de la variante. No existe
`pub`, `pub(crate)` ni `pub(in ...)`.

```pengu
scroll geometry
    unveil rune Point
        unveil x: Float
        unveil y: Float

    unveil(tome) origin = () -> Point
        Point(x: 0.0, y: 0.0)
```

Un campo sin `unveil` solo se lee y se escribe dentro del módulo que declara el
record. Un campo `unveil` puede leerse desde fuera; para escribirlo se usa un
método `@mut`, no una asignación directa.

### 3.5 Entrada

`grimoire` es el punto de entrada del binario. No recibe argumentos y devuelve
`Unit` o `Result[Unit, E]`.

```pengu
rune Args
    program: String
    rest: Vec[String]

grimoire
    print("hola, pengu")
```

Si el `grimoire` declara `Result[Unit, E]`, un `err` se imprime en stderr y el
proceso termina con código 1.

```pengu
enchanting StartError
    MissingName

grimoire: Result[Unit, StartError]
    bind name = "pengu"
    if name.len() == 0 then
        return err(MissingName)
    print(name)
    ok(())
```

No hay `main`, `argc`, `argv` ni `std::env::args` en la superficie: la librería
`std.env` expone `args()` cuando hace falta.

### 3.6 Un programa completo

```pengu
scroll app
    rune Config
        name: String
        verbose: Bool

    unveil load = () -> Config
        Config(name: "pengu", verbose: false)

summon app::load

grimoire
    bind config = load()
    if config.verbose then
        print("modo verboso")
    print(config.name)
```

### 3.7 Tome

Un **tome** es la unidad de compilación. Su manifiesto es `Tome.toml`:

```toml
[tome]
name = "hello"
version = "0.1.0"
pengu = "0.5"
edition = "2024"

[dependencies]
text = "1.2"

[features]
default = []
json = []

[[bin]]
name = "hello"
path = "main.pengu"
```

Solo se aceptan las claves `[tome]`, `[dependencies]`, `[features]`, `[[bin]]`,
`[[lib]]`, `[[test]]` y `[[example]]`. No hay `[cargo]`, `[profile]` ni tablas
de tooling: el backend decide esos detalles.

### 3.8 Pipeline

El compilador:

1. lee `Tome.toml`;
2. carga la raíz;
3. lexea, parsea y resuelve nombres;
4. verifica tipos, ownership y visibilidad;
5. baja a su representación interna;
6. emite código al backend;
7. produce el binario o la librería.

Los errores del backend se traducen a diagnósticos PenguScript. El usuario no
edita archivos generados y no ve el código del backend.

### 3.9 Diagnósticos del programa

| Código | Situación |
|---|---|
| `PGS-E2001` | No se encuentra `Tome.toml`. |
| `PGS-E2002` | Falta `main.pengu` o `lib.pengu`. |
| `PGS-E2003` | Módulo no encontrado. |
| `PGS-E2004` | `summon` de un nombre inexistente. |
| `PGS-E2005` | Import duplicado. |
| `PGS-E2006` | Item privado usado fuera del módulo. |
| `PGS-E2007` | `unveil` inválido en este contexto. |
| `PGS-E2008` | `grimoire` duplicado. |
| `PGS-E2009` | `grimoire` ausente en un binario. |
| `PGS-E2010` | `Tome.toml` inválido. |
| `PGS-E2011` | Dependencia no declarada. |
| `PGS-E2012` | Ciclo de módulos. |

[↑ Volver al índice](#indice)
