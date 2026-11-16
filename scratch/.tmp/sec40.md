<a id="sec-40-operator-overloading"></a>
## 40. Operator overloading

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | `Add`, `Sub`, `Mul`, `Index`, `Deref`, `PartialEq`, `Display` |
| Palabras mágicas | `ritual`, `essence`, `@`, `@own` |
| Depende de | §11, §31, §35, §36 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec40_operators.pengu` |

Un operador no es una construcción especial: es azúcar para un método de un
trait de `std`. PenguScript no permite inventar operadores ni precedencias; solo
implementar los traits existentes. Esto mantiene el código predecible y la
interoperabilidad con Rust.

### 40.1 `Add`, `Sub`, `Mul`, `Div`, `Rem`

```pengu
summon std::ops::Add

rune Point
    x: Int
    y: Int

ritual Point for Add
    essence Output = Point

    add = (@own, other: Point) -> Point
        Point(x: @.x + other.x, y: @.y + other.y)

bind p = Point(x: 1, y: 2) + Point(x: 3, y: 4)
print(p.x)
print(p.y)
```

Rust generado:

```rust
use std::ops::Add;

struct Point {
    x: i32,
    y: i32,
}

impl Add for Point {
    type Output = Point;

    fn add(self, other: Point) -> Point {
        Point {
            x: self.x + other.x,
            y: self.y + other.y,
        }
    }
}

fn main() {
    let p = Point { x: 1, y: 2 } + Point { x: 3, y: 4 };
    println!("{}", p.x);
    println!("{}", p.y);
}
```

Reglas:

1. El trait se nombra sin `std::ops::` si se importa con `summon`; también se
   puede escribir `std::ops::Add`.
2. `essence Output` fija el tipo de retorno; sin él, el trait no está completo.
3. `@own` es el receptor por valor (`self`); para operadores que consumen el
   operando izquierdo es lo correcto.
4. `add` recibe el operando derecho como parámetro normal.
5. `+` sigue la precedencia de §11; la implementación no la cambia.
6. `Add` no genera `AddAssign`; `+=` requiere `ritual Point for AddAssign`.
7. `Output` puede ser distinto de `Point` (por ejemplo, `Vector` + `Scalar`).

### 40.2 `AddAssign` y operadores de asignación

```pengu
summon std::ops::AddAssign

rune Counter
    value: Int

ritual Counter for AddAssign[Int]
    add_assign = (@mut, other: Int)
        @.value += other

morph c = Counter(value: 0)
c += 3
print(c.value)
```

Rust generado:

```rust
use std::ops::AddAssign;

struct Counter {
    value: i32,
}

impl AddAssign<i32> for Counter {
    fn add_assign(&mut self, other: i32) {
        self.value += other;
    }
}

fn main() {
    let mut c = Counter { value: 0 };
    c += 3;
    println!("{}", c.value);
}
```

1. `+=` usa `AddAssign`, no `Add`.
2. El receptor es `@mut` (`&mut self`).
3. La asignación compuesta es una sentencia, no una expresión (§8).
4. `SubAssign`, `MulAssign`, `DivAssign`, `RemAssign` siguen el mismo patrón.

### 40.3 `Neg`, `Not`, bitwise y shifts

| Operador | Trait | Receptor |
|---|---|---|
| `-x` | `Neg` | `@own` |
| `!x` | `Not` | `@own` |
| `x & y` | `BitAnd` | `@own` |
| `x | y` | `BitOr` | `@own` |
| `x ^ y` | `BitXor` | `@own` |
| `x << y` | `Shl` | `@own` |
| `x >> y` | `Shr` | `@own` |

1. `!` sobre `Bool` usa `Not`; sobre enteros también.
2. `&`, `|`, `^` son bitwise, no lógicos; los lógicos son `and`/`or` (§12).
3. Los shifts no comprueban el desplazamiento en modo release; usa `checked_shl`
   si el valor es no confiable.
4. `Neg` puede devolver otro tipo; `Output` lo declara.

### 40.4 `Index` e `IndexMut`

```pengu
summon std::ops::Index

rune Point
    x: Int
    y: Int

ritual Point for Index[Int]
    essence Output = Int

    index = (@, i: Int) -> &Int
        if i == 0 then &@.x else &@.y

bind p = Point(x: 10, y: 20)
print(p[0])
print(p[1])
```

Rust generado:

```rust
use std::ops::Index;

struct Point {
    x: i32,
    y: i32,
}

impl Index<i32> for Point {
    type Output = i32;

    fn index(&self, i: i32) -> &i32 {
        if i == 0 { &self.x } else { &self.y }
    }
}

fn main() {
    let p = Point { x: 10, y: 20 };
    println!("{}", p[0]);
    println!("{}", p[1]);
}
```

1. `Index[Int]` significa `Index<Idx = Int>`; el índice puede ser otro tipo.
2. `Output` es el tipo del elemento; `index` devuelve `&Output`.
3. `IndexMut` se implementa aparte y usa `@mut`; `p[i] = v` requiere `IndexMut`.
4. El operador `[]` puede entrar en pánico; no hay `get` sobrecargable. Para
   acceso seguro se usa un método propio que devuelva `?&T`.
5. `Index` no puede devolver un valor por movimiento.

### 40.5 `PartialEq`, `Eq`, `PartialOrd`, `Ord`

```pengu
rune Point
    x: Int
    y: Int

ritual Point for PartialEq
    eq = (@, other: &Point) -> Bool
        @.x == other.x and @.y == other.y
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

impl PartialEq for Point {
    fn eq(&self, other: &Point) -> bool {
        self.x == other.x && self.y == other.y
    }
}
```

1. `==`/`!=` usan `PartialEq`; `eq` recibe `&Point`.
2. Para igualdad total se implementa `Eq` (sin métodos adicionales).
3. `<`, `<=`, `>`, `>=` usan `PartialOrd`; `Ord` exige un orden total.
4. `@@derive(PartialEq, Eq, PartialOrd, Ord)` genera las implementaciones
   cuando los campos las cumplen; es la opción recomendada.
5. `NaN` hace que `Float` no implemente `Ord`; no se puede fingir un orden total.

### 40.6 `Display` y `Debug`

```pengu
summon std::fmt

rune Point
    x: Int
    y: Int

ritual Point for std::fmt::Display
    fmt = (@, f: &mut std::fmt::Formatter) -> std::fmt::Result
        f.write_str(format("(#{}, #{})", @.x, @.y))

print(Point(x: 1, y: 2))
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

impl std::fmt::Display for Point {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        f.write_str(&format!("({}, {})", self.x, self.y))
    }
}

fn main() {
    println!("{}", Point { x: 1, y: 2 });
}
```

1. `Display` es para el usuario; `Debug` para diagnóstico. No son intercambiables.
2. `print`/`format` usan `Display`; `{:?}` usa `Debug`.
3. `fmt` recibe `&mut Formatter` y devuelve `fmt::Result`.
4. No se implementa `Display` para un tipo que no tiene una representación
   textual estable; usa `Debug` o un método `to_text`.
5. `@@derive(Debug)` es preferible para `Debug`; `Display` casi siempre es manual.

### 40.7 `Deref` y `DerefMut`

```pengu
summon std::ops::Deref

rune Wrapper
    value: Int

ritual Wrapper for Deref
    essence Target = Int

    deref = (@) -> &Int
        &@.value

bind w = Wrapper(value: 7)
print(*w)
```

Rust generado:

```rust
use std::ops::Deref;

struct Wrapper {
    value: i32,
}

impl Deref for Wrapper {
    type Target = i32;

    fn deref(&self) -> &i32 {
        &self.value
    }
}

fn main() {
    let w = Wrapper { value: 7 };
    println!("{}", *w);
}
```

1. `Deref` habilita `*x` y coerciones; no es para “heredar” métodos.
2. `DerefMut` usa `@mut` y habilita `*x = v`.
3. El `Target` debe ser un tipo detrás de una referencia.
4. El abuso de `Deref` para simular herencia se rechaza en revisión; usa
   composición o un `pact`.

### 40.8 `From` e `Into`

```pengu
rune Point
    x: Int
    y: Int

ritual Point for From[(Int, Int)]
    from = (pair: (Int, Int)) -> Point
        Point(x: pair.0, y: pair.1)

bind p: Point = (3, 4).into()
print(p.x)
print(p.y)
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

impl From<(i32, i32)> for Point {
    fn from(pair: (i32, i32)) -> Point {
        Point {
            x: pair.0,
            y: pair.1,
        }
    }
}

fn main() {
    let p: Point = (3, 4).into();
    println!("{}", p.x);
    println!("{}", p.y);
}
```

1. `From[T]` se implementa para convertir `T` en el tipo local.
2. `Into` se obtiene gratis por el blanket impl de `std`; no se implementa a
   mano salvo casos especiales.
3. La conversión es infalible; para fallos se usa `TryFrom` (§32).
4. No hay conversiones implícitas entre tipos numéricos; `as` es explícito.
5. Coherencia: no puedes implementar `From` para un tipo externo y un tipo
   externo; al menos uno debe ser local.

### 40.9 Qué no se puede sobrecargar

- `=`, `==`, `!=`, `&&`, `||`, `..`, `?`, `as`, `.`, `@` y `=>` no son traits.
- No se puede cambiar la precedencia ni la asociatividad.
- No se pueden crear operadores nuevos (`**`, `++`, `===`).
- `print`/`format` no son operadores; usan `Display`.
- `Drop` se implementa con `ritual Tipo for Drop`, pero no es un operador.
- `Index` no reemplaza a `get`; el acceso seguro sigue siendo un método.

### 40.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4101` | `essence Output` faltante | declararlo en el `ritual` |
| `PGS-E4102` | receptor incorrecto | `@own` para operadores que consumen, `@mut` para asignación |
| `PGS-E4103` | `Index` devuelve un valor | devolver `&Output` |
| `PGS-E4104` | `PartialOrd` sin `PartialEq` | implementar ambos o derivar |
| `PGS-E4105` | `Display` para un tipo sin representación estable | usar `Debug` o un método |
| `PGS-E4106` | `From` con dos tipos externos | newtype local |
| `PGS-W4101` | `Deref` usado para simular herencia | composición o `pact` |

### 40.11 Criterios de aceptación

- [x] Operadores aritméticos y de asignación están definidos.
- [x] `Index`, comparación, `Display`, `Deref` y `From` tienen ejemplo.
- [x] Qué no se puede sobrecargar está claro.
- [x] Coherencia y precedencia se remiten a §11/§31.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
