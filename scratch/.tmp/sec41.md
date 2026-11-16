<a id="sec-41-modulos"></a>
## 41. Módulos (scroll)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 6 |
| Rust | `mod`, `use`, `crate`, `super` |
| Palabras mágicas | `scroll`, `summon`, `crate`, `super` |
| Depende de | §3, §7, §42 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec41_modules.pengu` |

Un **módulo** agrupa items y controla su visibilidad. En PenguScript se declara
con `scroll`. Un archivo `.pengu` es un módulo; la raíz del programa es
`main.pengu` (binario) o `lib.pengu` (librería). `scroll` inline permite agrupar
sin archivo; `scroll` sin cuerpo carga un archivo hermano.

### 41.1 Raíces y archivos

| Archivo | Crate | Rust |
|---|---|---|
| `main.pengu` | binario | `src/main.rs` |
| `lib.pengu` | librería | `src/lib.rs` |
| `geometry.pengu` | módulo `geometry` | `src/geometry.rs` |
| `geometry/scroll.pengu` | módulo `geometry` | `src/geometry/mod.rs` |

Reglas:

1. Solo hay una raíz por crate: `main.pengu` o `lib.pengu`.
2. Un `scroll foo` sin cuerpo busca `foo.pengu` o `foo/scroll.pengu`, en ese
   orden. Si ambos existen, error `PGS-E4112`.
3. Un `scroll foo` con cuerpo indentado es inline y no carga archivo.
4. El archivo se resuelve relativo al directorio del módulo padre.
5. `@@path("ruta.pengu")` sobre el `scroll` sustituye la resolución automática.
6. No se permite `mod.rs`; el nombre `scroll.pengu` es el equivalente moderno.

### 41.2 `scroll` inline

```pengu
scroll geometry
    unveil rune Point
        unveil x: Int
        unveil y: Int

    unveil norm = (p: &Point) -> Float
        ((p.x * p.x + p.y * p.y) as Float).sqrt()

bind p = geometry::Point(x: 3, y: 4)
print(geometry::norm(&p))
```

Rust generado:

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }

    pub fn norm(p: &Point) -> f64 {
        (((p.x * p.x + p.y * p.y) as f64).sqrt())
    }
}

fn main() {
    let p = geometry::Point { x: 3, y: 4 };
    println!("{}", geometry::norm(&p));
}
```

1. El cuerpo del `scroll` va indentado un nivel.
2. Los items internos se acceden con `geometry::Point` desde el padre.
3. `scroll` puede anidarse; el hijo se declara dentro del padre.
4. `unveil` decide qué sale del módulo (§42); sin él, el item es privado.
5. Un `scroll` inline no genera archivo separado; el codegen lo emite en el
   mismo `.rs`.

### 41.3 `scroll` desde archivo

`main.pengu`:

```pengu
scroll geometry
unveil summon crate::geometry::Point

bind p = Point(x: 3, y: 4)
print(p.x)
```

`geometry.pengu`:

```pengu
unveil rune Point
    unveil x: Int
    unveil y: Int
```

Rust generado (en el ejemplo de un solo archivo, el módulo se inlinea para
poder compilarlo aislado):

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }
}

use crate::geometry::Point;

fn main() {
    let p = Point { x: 3, y: 4 };
    println!("{}", p.x);
}
```

1. `scroll geometry` sin cuerpo es una declaración de módulo externo.
2. `geometry.pengu` se compila a `src/geometry.rs`; el `mod geometry;` de Rust
   queda en la raíz.
3. `unveil summon` reexporta el tipo desde la raíz del crate.
4. `summon crate::geometry::Point` también funciona sin reexportar.
5. La resolución es determinista: archivo hermano antes que carpeta.

### 41.4 `summon` y paths

```pengu
scroll geometry
    unveil rune Point
        unveil x: Int
        unveil y: Int

summon crate::geometry::Point
summon crate::geometry::Point as P

bind a = Point(x: 1, y: 2)
bind b = P(x: 3, y: 4)
print(a.x + b.x)
```

Rust generado:

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }
}

use crate::geometry::Point;
use crate::geometry::Point as P;

fn main() {
    let a = Point { x: 1, y: 2 };
    let b = P { x: 3, y: 4 };
    println!("{}", a.x + b.x);
}
```

1. `summon path` importa un item o un módulo.
2. `summon path as Alias` renombra.
3. `summon path::*` importa el glob; se desaconseja en APIs públicas.
4. `summon` debe ir antes de los items que lo usan, o en el prelude del módulo.
5. `crate::` empieza en la raíz del crate; `super::` sube un módulo.
6. No se escribe `self::`; dentro del módulo se usa el nombre sin prefijo.
7. Un path absoluto de dependencia empieza por el nombre del crate:
   `summon serde::Serialize`.

### 41.5 Reexportar

```pengu
scroll geometry
    unveil rune Point
        unveil x: Int
        unveil y: Int

unveil summon crate::geometry::Point

bind p = Point(x: 1, y: 2)
print(p.x)
```

Rust generado:

```rust
mod geometry {
    pub struct Point {
        pub x: i32,
        pub y: i32,
    }
}

pub use crate::geometry::Point;

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", p.x);
}
```

1. `unveil summon` es un `pub use`: reexporta con la visibilidad indicada.
2. Se usa para fachadas de crate (`prelude`, `api`) y para no exponer la ruta
   interna.
3. Un reexport no copia el item; cambia su camino público.
4. `unveil(tome) summon` reexporta solo dentro del crate.

### 41.6 Árbol de módulos

```text
src/
  main.pengu
  geometry.pengu
  shapes/
    scroll.pengu
    circle.pengu
```

`main.pengu`:

```pengu
scroll geometry
scroll shapes
```

`shapes/scroll.pengu`:

```pengu
scroll circle
unveil summon crate::shapes::circle::Circle
```

`shapes/circle.pengu`:

```pengu
unveil rune Circle
    unveil radius: Float
```

El árbol de Rust correspondiente:

```text
src/
  main.rs
  geometry.rs
  shapes/
    mod.rs
    circle.rs
```

1. `shapes/scroll.pengu` es el `mod.rs` de `shapes`.
2. `circle.pengu` es el hijo `shapes::circle`.
3. Los `scroll` de `main.pengu` declaran los hijos de la raíz.
4. El codegen conserva el árbol; no aplana módulos.

### 41.7 Prelude y resolución

- El prelude del crate contiene `Option`, `Result`, `String`, `Vec`, `Box`,
  `print`, `format`, `panic`, `assert` y los traits de operadores.
- Un `summon` en la raíz no se hereda automáticamente a los hijos; cada módulo
  importa lo que usa.
- Un nombre local gana al prelude; un `summon` explícito gana al prelude.
- Dos `summon` con el mismo nombre sin alias son ambiguos (`PGS-E4113`).
- Los módulos no se importan implícitamente; hay que declararlos con `scroll`.
- El orden de declaración no importa para la resolución; sí para la lectura.

### 41.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4110` | `scroll` sin archivo y sin cuerpo | crear el archivo o el cuerpo |
| `PGS-E4111` | dos raíces (`main.pengu` y `lib.pengu`) | elegir una |
| `PGS-E4112` | `foo.pengu` y `foo/scroll.pengu` a la vez | borrar uno o usar `@@path` |
| `PGS-E4113` | dos `summon` con el mismo nombre | aliasar uno |
| `PGS-E4114` | `scroll` dentro de una función | moverlo al nivel de módulo |
| `PGS-E4115` | path `self::` | usar `crate::`/`super::` o el nombre directo |
| `PGS-W4110` | glob import en API pública | importar nombres explícitos |

### 41.9 Criterios de aceptación

- [x] La resolución de archivos es determinista.
- [x] `scroll` inline y externo están definidos.
- [x] `summon`, alias, glob y reexport están cubiertos.
- [x] El árbol de módulos tiene ejemplo.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
