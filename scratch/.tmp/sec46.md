<a id="sec-46-derives"></a>
## 46. Derives y traits comunes

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 6 |
| Rust | `#[derive(...)]` |
| Palabras mágicas | `@@derive` |
| Depende de | §28, §29, §35, §44 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec46_derives.pengu` |

Un **derive** es una implementación generada automáticamente por el compilador
para un `rune` o un `enchanting`. En PenguScript se escribe con `@@derive(...)`;
el codegen lo traduce a `#[derive(...)]`.

### 46.1 Sintaxis

```pengu
@@derive(Debug, Clone, PartialEq)
rune Point
    x: Int
    y: Int

@@derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)
rune Id
    value: UInt
```

Rust generado:

```rust
#[derive(Debug, Clone, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
struct Id {
    value: u32,
}
```

1. `@@derive` solo se aplica a `rune` y `enchanting`.
2. Los nombres son los del trait que se deriva; deben estar en scope.
3. El orden de los derives se conserva, aunque el orden no cambia la semántica.
4. Un derive en un campo, función o `scroll` es error (`PGS-E4602`).
5. Los derives de una crate externa se importan con `summon`.
6. Un derive de una proc macro se documenta en la crate que lo define.

### 46.2 Derives built-in

| Derive | Genera | Requisito |
|---|---|---|
| `Clone` | `fn clone(&self) -> Self` | todos los campos `Clone` |
| `Copy` | copia bit a bit | `Clone`; todos los campos `Copy`; sin `Drop` |
| `Debug` | `fmt::Debug` | todos los campos `Debug` |
| `PartialEq` | `eq`/`ne` | todos los campos `PartialEq` |
| `Eq` | marca de equivalencia | `PartialEq`; todos los campos `Eq` |
| `PartialOrd` | `partial_cmp` | `PartialEq`; campos `PartialOrd` |
| `Ord` | `cmp` | `Eq` + `PartialOrd`; campos `Ord` |
| `Hash` | `hash` | `Eq`; campos `Hash` |
| `Default` | `default()` | todos los campos `Default` |

1. `Copy` implica `Clone`; no se puede derivar `Copy` sin `Clone`.
2. Un tipo con `Drop` no puede ser `Copy`.
3. `Eq` no se puede derivar para un tipo que contiene `Float`.
4. `Ord` no se puede derivar para un tipo que contiene `Float`.
5. `Hash` debe ser consistente con `Eq`: dos valores iguales tienen el mismo
   hash.
6. `Default` usa el valor por defecto de cada campo, no un constructor.

### 46.3 `Clone` y `Copy`

```pengu
@@derive(Debug, Clone, Copy, PartialEq)
rune Id
    value: UInt

grimoire
    bind a = Id(value: 7)
    bind b = a
    print(a == b)
```

Rust generado:

```rust
#[derive(Debug, Clone, Copy, PartialEq)]
struct Id {
    value: u32,
}

fn main() {
    let a = Id { value: 7 };
    let b = a;
    println!("{}", a == b);
}
```

1. `Copy` hace que `bind b = a` copie el valor; `a` sigue siendo usable.
2. Sin `Copy`, `bind b = a` mueve `a`; usarlo después es error (§16).
3. `Clone` es explícito: `a.clone()` para tipos no `Copy`.
4. Un `rune` con un `String` puede ser `Clone`, pero no `Copy`.
5. `Copy` es una promesa de bajo costo; no se deriva en tipos grandes sin
   medir.

### 46.4 `Debug` y `Display`

```pengu
@@derive(Debug)
rune Point
    x: Float
    y: Float

grimoire
    bind p = Point(x: 1.0, y: 2.0)
    print("#{p:?}")
```

Rust generado:

```rust
#[derive(Debug)]
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    println!("{:?}", p);
}
```

1. `Debug` es para diagnóstico; el formato puede cambiar.
2. `Display` **no** se deriva; se implementa con `ritual` (§35).
3. `print("#{p}")` requiere `Display`; `print("#{p:?}")` requiere `Debug`.
4. `{:#?}` es el formato multilínea de `Debug`.
5. Un tipo público debe implementar `Debug` salvo que exponga secretos.

`Display` manual:

```rust
use std::fmt;

struct Point {
    x: f64,
    y: f64,
}

impl fmt::Display for Point {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    println!("{}", p);
}
```

### 46.5 Igualdad y orden

```pengu
@@derive(Debug, PartialEq, Eq, PartialOrd, Ord)
rune Version
    major: UInt
    minor: UInt

grimoire
    bind a = Version(major: 1, minor: 2)
    bind b = Version(major: 1, minor: 3)
    print(a < b)
```

Rust generado:

```rust
#[derive(Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Version {
    major: u32,
    minor: u32,
}

fn main() {
    let a = Version { major: 1, minor: 2 };
    let b = Version { major: 1, minor: 3 };
    println!("{}", a < b);
}
```

1. `PartialEq` compara campo a campo, en orden de declaración.
2. `Eq` no cambia la implementación; es una marca de equivalencia total.
3. `PartialOrd` usa el orden lexicográfico de los campos.
4. `Ord` es un orden total; requiere `Eq` y `PartialOrd`.
5. `Float` no implementa `Eq` ni `Ord`; un `rune` con `Float` no puede
   derivarlos.
6. El orden derivado es el orden de los campos, no el nombre.

### 46.6 `Hash`

```pengu
@@derive(Debug, PartialEq, Eq, Hash)]
rune Key
    id: UInt

grimoire
    summon std::collections::HashSet
    morph seen = HashSet.new()
    seen.insert(Key(id: 1))
    print(seen.contains(&Key(id: 1)))
```

Rust generado:

```rust
use std::collections::HashSet;

#[derive(Debug, PartialEq, Eq, Hash)]
struct Key {
    id: u32,
}

fn main() {
    let mut seen = HashSet::new();
    seen.insert(Key { id: 1 });
    println!("{}", seen.contains(&Key { id: 1 }));
}
```

1. `Hash` debe ser consistente con `Eq`.
2. `Hash` no garantiza un orden ni un valor estable entre ejecuciones.
3. Un `HashMap` con un tipo custom necesita `Eq + Hash`.
4. Para un hasher distinto, se usa `HashMap.with_hasher(...)` (§25).
5. No se deriva `Hash` en un tipo con `Float`.

### 46.7 `Default`

```pengu
@@derive(Debug, Default)
rune Config
    retries: UInt
    verbose: Bool

grimoire
    bind c = Config.default()
    print("#{c:?}")
```

Rust generado:

```rust
#[derive(Debug, Default)]
struct Config {
    retries: u32,
    verbose: bool,
}

fn main() {
    let c = Config::default();
    println!("{:?}", c);
}
```

1. `Default` usa `0`, `false`, `String::new()`, `Vec::new()`, etc.
2. Un campo sin `Default` impide derivar `Default`.
3. `Default` no es un constructor con argumentos; para eso se escribe `new`.
4. Un tipo público puede implementar `Default` y `new` a la vez.
5. `Config.default()` es la forma PenguScript de `Config::default()`.

### 46.8 Derives externos

```pengu
summon serde::Serialize
summon serde::Deserialize

@@cfg_attr(feature = "serde", derive(Serialize, Deserialize))
rune User
    name: String
```

1. Un derive externo es una proc macro; debe estar en `Tome.toml`.
2. `@@cfg_attr` permite activarlo solo con una feature.
3. La crate debe declarar la feature `serde`.
4. El derive puede añadir bounds automáticos; se documentan en su crate.
5. PenguScript no reexporta derives de terceros.

### 46.9 Errores y límites

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4601` | `@@derive` en un item no válido | moverlo a `rune`/`enchanting` |
| `PGS-E4602` | derive desconocido | importar la crate o corregir el nombre |
| `PGS-E4603` | `Copy` sin `Clone` | añadir `Clone` |
| `PGS-E4604` | `Copy` en un tipo con `Drop` | quitar `Copy` o `Drop` |
| `PGS-E4605` | `Eq`/`Ord` con `Float` | no derivarlos; implementar a mano |
| `PGS-E4606` | `Hash` sin `Eq` | añadir `Eq` |
| `PGS-W4601` | `Debug` en un tipo con secretos | implementar `Debug` a mano |
| `PGS-W4602` | derive innecesario | eliminarlo |

1. Un derive no puede violar la coherencia: no se implementa un trait externo
   para un tipo externo.
2. Un derive generado no se puede especializar por campo.
3. Si el comportamiento automático no sirve, se escribe el `ritual` a mano.
4. Un derive puede ser más lento de compilar que una implementación simple.
5. Los derives no sustituyen a los tests de igualdad/orden.

### 46.10 Criterios de aceptación

- [x] Los nueve derives built-in están definidos.
- [x] Requisitos y límites están claros.
- [x] `Clone`/`Copy`, `Debug`/`Display`, orden y `Hash` tienen ejemplo.
- [x] Los derives externos se consumen, no se definen.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
