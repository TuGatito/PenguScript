<a id="sec-42-visibilidad"></a>
## 42. Visibilidad (unveil)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 6 |
| Rust | `pub`, `pub(crate)`, `pub(super)`, `pub(in path)` |
| Palabras mágicas | `unveil`, `tome`, `scroll` |
| Depende de | §41 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec42_visibility.pengu` |

En PenguScript **todo es privado por defecto**. `unveil` abre un item, un campo
o un módulo. No hay `public`/`private`; la palabra es parte del léxico mágico y
se traduce directamente a las formas de `pub` de Rust.

### 42.1 Tabla de visibilidad

| PenguScript | Rust | Visible desde |
|---|---|---|
| sin modificador | privado | módulo actual y descendientes |
| `unveil` | `pub` | cualquier crate que dependa |
| `unveil(tome)` | `pub(crate)` | cualquier módulo del crate |
| `unveil(scroll)` | `pub(super)` | módulo padre |
| `unveil(in crate::a::b)` | `pub(in crate::a::b)` | ese módulo y descendientes |
| `unveil summon` | `pub use` | según el `unveil` |

Reglas:

1. `unveil` se escribe antes de la palabra del item:
   `unveil rune`, `unveil enchanting`, `unveil pact`, `unveil ritual`,
   `unveil sigil`, `unveil relic`, `unveil scroll`, `unveil incantation`.
2. En campos: `unveil x: Int`; el campo pasa a `pub x`.
3. En variantes de enum no se escribe `unveil`: si el enum es público, sus
   variantes son públicas, como en Rust.
4. En items de trait no se escribe `unveil`: la visibilidad la decide el trait.
5. En campos de struct de tupla no se escribe `unveil`; son privados por
   decisión (§28), y se accede con métodos o con un constructor.
6. `unveil` no se hereda: un campo público dentro de un struct privado no hace
   público el struct.
7. La visibilidad se comprueba en el punto de uso; un item privado usado desde
   otro módulo produce `PGS-E4211`.

### 42.2 Ejemplo completo

```pengu
scroll inner
    unveil rune Public
        unveil value: Int
        hidden: Int

    rune Private
        value: Int

    unveil new = (value: Int) -> Public
        Public(value: value, hidden: 0)

    unveil(scroll) show = (p: &Public) -> Int
        p.value

unveil(tome) crate_only = () -> Int
    1

bind p = inner::new(7)
print(inner::show(&p))
print(crate_only())
```

Rust generado:

```rust
mod inner {
    pub struct Public {
        pub value: i32,
        hidden: i32,
    }

    struct Private {
        value: i32,
    }

    pub fn new(value: i32) -> Public {
        Public { value, hidden: 0 }
    }

    pub(super) fn show(p: &Public) -> i32 {
        p.value
    }
}

pub(crate) fn crate_only() -> i32 {
    1
}

fn main() {
    let p = inner::new(7);
    println!("{}", inner::show(&p));
    println!("{}", crate_only());
}
```

1. `Public` es público, pero `hidden` no; el constructor `new` es la única forma
   de crear el valor desde fuera.
2. `Private` no sale de `inner`.
3. `show` es `pub(super)`: visible en la raíz, no fuera del crate.
4. `crate_only` es `pub(crate)`: visible desde cualquier módulo del crate.
5. `main` puede llamar a `show` porque está en el padre de `inner`.

### 42.3 Campos y variantes

```pengu
unveil rune Config
    unveil name: String
    unveil retries: Int

unveil enchanting Status
    Active
    Failed(Int)
```

Rust generado:

```rust
pub struct Config {
    pub name: String,
    pub retries: i32,
}

pub enum Status {
    Active,
    Failed(i32),
}
```

1. Los campos públicos se pueden leer y escribir desde fuera; los privados solo
   desde el módulo y sus descendientes.
2. Las variantes de un enum público son públicas; no se puede hacer un enum
   público con variantes privadas.
3. Los campos de una variante de struct (`Failed { code: Int }`) siguen las
   reglas de campos de struct.
4. `unveil` en un campo de enum es error (`PGS-E4212`).
5. Un enum privado con variantes públicas no existe: la visibilidad del enum
   manda.

### 42.4 `unveil` en módulos y reexports

```pengu
unveil scroll api
    unveil rune Request
        unveil id: Int

unveil summon crate::api::Request
```

Rust generado:

```rust
pub mod api {
    pub struct Request {
        pub id: i32,
    }
}

pub use crate::api::Request;
```

1. `unveil scroll` hace público el módulo; sin él, sus items públicos no son
   alcanzables desde fuera.
2. Un módulo público puede contener items privados.
3. `unveil summon` reexporta; es la forma recomendada de construir una fachada.
4. `unveil(tome) scroll` limita el módulo al crate.
5. La ruta pública no tiene por qué coincidir con la ruta interna.

### 42.5 `pub(in path)`

```pengu
scroll outer
    unveil scroll inner
        unveil(in crate::outer) helper = () -> Int
            42
```

Rust generado:

```rust
mod outer {
    pub mod inner {
        pub(in crate::outer) fn helper() -> i32 {
            42
        }
    }
}
```

1. `unveil(in crate::a::b)` solo es visible dentro de ese módulo y sus
   descendientes.
2. El path debe ser un ancestro del item; si no, error (`PGS-E4213`).
3. Es útil para APIs internas de un subsistema.
4. No se puede usar `unveil(in super::super)`; se escribe la ruta completa desde
   `crate`.
5. En el crate raíz, `unveil(in crate)` equivale a `pub(crate)`.

### 42.6 Privacidad y fugas de tipos

- Un item público no puede exponer un tipo privado en su firma; Rust lo detecta
  como `private_interfaces` (`PGS-E4214`).
- Un campo público de un tipo privado no es alcanzable; el compilador lo
  permite, pero el codegen lo marca como advertencia.
- Un `unveil summon` de un item privado es error.
- Un trait público con un supertrait privado es un trait sellado; se permite con
  advertencia (`PGS-W4210`).
- La visibilidad no cambia el layout ni el código; solo el acceso.

### 42.7 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4210` | `unveil` sobre un item que no lo admite | quitar o mover al item |
| `PGS-E4211` | item privado usado desde otro módulo | `unveil` o reexportar |
| `PGS-E4212` | `unveil` en campo de variante de enum | la variante hereda del enum |
| `PGS-E4213` | `pub(in path)` que no es ancestro | usar un ancestro real |
| `PGS-E4214` | tipo privado en API pública | hacer público el tipo o privada la API |
| `PGS-W4210` | supertrait privado en trait público | documentar el sellado |
| `PGS-W4211` | `unveil` redundante en el crate raíz | simplificar |

### 42.8 Criterios de aceptación

- [x] La tabla cubre todas las formas de `pub`.
- [x] Campos, variantes, módulos y reexports están definidos.
- [x] `pub(in path)` y sus restricciones están explicados.
- [x] Privacidad por defecto y fugas de tipos están cubiertas.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
