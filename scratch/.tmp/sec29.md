<a id="sec-29-enums"></a>
## 29. Enums (`enchanting`)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4B |
| Rust | `enum` |
| Palabras mágicas | `enchanting`, `@@repr`, `@@non_exhaustive` |
| Depende de | §28, §30 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec29_enums.pengu` |

Un **`enchanting`** es un tipo suma: un valor es exactamente una de sus
variantes. Cada variante puede ser unitaria, de tupla o de struct. Es la forma
de modelar “uno de varios casos” sin null ni herencia.

### 29.1 Variantes

```pengu
enchanting Shape
    Circle(Float)
    Rectangle(Float, Float)
    Empty
```

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
    Empty,
}
```

Reglas:

1. `Circle(Float)` es una variante de tupla con un campo.
2. `Rectangle(Float, Float)` tiene dos campos posicionales.
3. `Empty` es una variante unitaria (sin datos).
4. Una variante de struct se escribe con campos indentados:

```pengu
enchanting Message
    Quit
    Move
        x: Int
        y: Int
    Write(String)
```

Rust generado:

```rust
enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}
```

5. Los nombres de variante deben ser únicos dentro del enum (`PGS-E2902`).
6. Las variantes heredan la visibilidad del enum; no se permite `unveil` por
   variante.

### 29.2 Construcción

```pengu
bind circle = Circle(2.0)
bind rect = Rectangle(3.0, 4.0)
bind empty = Empty
bind move = Move(x: 1, y: 2)
```

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
    Empty,
}

enum Message {
    Quit,
    Move { x: i32, y: i32 },
    Write(String),
}

fn main() {
    let circle = Shape::Circle(2.0);
    let rect = Shape::Rectangle(3.0, 4.0);
    let empty = Shape::Empty;
    let mv = Message::Move { x: 1, y: 2 };
    println!("{}", match empty { Shape::Empty => "empty", _ => "other" });
    println!("{}", match circle { Shape::Circle(r) => r, _ => 0.0 });
    println!("{}", match rect { Shape::Rectangle(w, h) => w * h, _ => 0.0 });
    println!("{}", match mv { Message::Move { x, y } => x + y, _ => 0 });
}
```

En PenguScript, el nombre de la variante es suficiente si el tipo esperado es
conocido (`bind circle: Shape = Circle(2.0)`). Si hay ambigüedad entre enums, se
califica con `Shape.Circle(2.0)` o se anota el binding.

### 29.3 `Option` y `Result` son enums

`?T` es `Option[T]` y `!T` es `Result[T, Error]`. Sus variantes son `some(x)` /
`none` y `ok(x)` / `err(e)`:

```pengu
bind maybe: ?Int = some(3)
bind result: !Int = ok(7)

match maybe
    when some(x) then print(x)
    when none then print(0)

match result
    when ok(x) then print(x)
    when err(e) then print(e)
```

Rust generado:

```rust
fn main() {
    let maybe: Option<i32> = Some(3);
    let result: Result<i32, Box<dyn std::error::Error + Send + Sync>> = Ok(7);

    match maybe {
        Some(x) => println!("{}", x),
        None => println!("0"),
    }

    match result {
        Ok(x) => println!("{}", x),
        Err(e) => println!("{}", e),
    }
}
```

`Option` y `Result` están en la prelude; no se redeclaran. Un `match` sobre ellos
debe cubrir ambas variantes o usar `else`.

### 29.4 Discriminantes y `@@repr`

```pengu
@@repr(u8)
enchanting Level
    Low = 1
    High = 2

bind level = High
print(level as Int)
```

Rust generado:

```rust
#[repr(u8)]
enum Level {
    Low = 1,
    High = 2,
}

fn main() {
    let level = Level::High;
    println!("{}", level as i32);
}
```

Reglas:

1. Los discriminantes solo se permiten en variantes unitarias.
2. Sin `@@repr`, el discriminante se infiere desde 0; con `@@repr(u8)`, el
   almacenamiento es `u8`.
3. `as` convierte una variante fieldless a su discriminante; no se permite `as`
   sobre una variante con datos (`PGS-E2904`).
4. `@@repr(C)` fija el layout para FFI; `@@repr(u8/u16/u32/u64/usize)` fija el
   entero subyacente.
5. Los discriminantes no pueden repetirse (`PGS-E2903`).

### 29.5 `@@non_exhaustive`

```pengu
@@non_exhaustive
enchanting ApiError
    NotFound
    Denied
    Unknown
```

`@@non_exhaustive` se traduce a `#[non_exhaustive]`: los consumidores de otra
crate deben incluir un brazo `_`/`else`. Dentro de la crate que lo define, el
`match` sigue siendo exhaustivo sin `else`.

### 29.6 Optimización de nicho

Rust puede reutilizar un valor inválido de un tipo para representar una variante
sin ocupar espacio extra (niche optimization). Ejemplos:

| Tipo | Tamaño típico | Nicho |
|---|---|---|
| `?&T` | igual que `&T` | puntero nulo |
| `?Box[T]` | igual que `Box[T]` | puntero nulo |
| `?Bool` | 1 byte | tercer valor de `bool` |
| `?Char` | 4 bytes | escalar inválido |

PenguScript no garantiza un tamaño concreto salvo con `@@repr`; la optimización
es una propiedad de Rust que puede cambiar. Para FFI se usa `@@repr(C)` y no se
asume nicho.

### 29.7 Métodos

```pengu
enchanting Shape
    Circle(Float)
    Rectangle(Float, Float)

ritual Shape
    area = (@) -> Float
        match @
            when Circle(r) then 3.141592653589793 * r * r
            when Rectangle(w, h) then w * h

bind s = Circle(2.0)
print(s.area())
```

Rust generado:

```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

impl Shape {
    fn area(&self) -> f64 {
        match self {
            Shape::Circle(r) => 3.141592653589793 * r * r,
            Shape::Rectangle(w, h) => w * h,
        }
    }
}

fn main() {
    let s = Shape::Circle(2.0);
    println!("{}", s.area());
}
```

### 29.8 `match` y exhaustividad

```pengu
label = (shape: &Shape) -> Str
    match shape
        when Circle(_) then "círculo"
        when Rectangle(_, _) then "rectángulo"

bind s = Circle(1.0)
print(label(&s))
```

Un `match` sin `else` debe cubrir todas las variantes. Si `Shape` es
`@@non_exhaustive` desde otra crate, el compilador exige `else`. §30 define
patrones, guardas y `if let`.

### 29.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2901` | variante duplicada | renombrar |
| `PGS-E2902` | nombre de variante no único | renombrar |
| `PGS-E2903` | discriminante duplicado | cambiar el valor |
| `PGS-E2904` | `as` sobre variante con datos | usar `match` |
| `PGS-E2905` | `match` no exhaustivo | añadir variante o `else` |
| `PGS-E2906` | `@@repr` inválido para la variante | usar fieldless o cambiar repr |
| `PGS-W2901` | enum con una sola variante | considerar un `rune` |
| `PGS-W2902` | `@@non_exhaustive` sin `else` fuera de la crate | añadir `else` |

### 29.10 Criterios de aceptación

- [x] Variantes unitarias, de tupla y de struct están diferenciadas.
- [x] Construcción y calificación de variantes están definidas.
- [x] `Option`/`Result` se reconocen como enums de la prelude.
- [x] Discriminantes, `@@repr` y `@@non_exhaustive` están cubiertos.
- [x] La optimización de nicho se explica sin garantizar tamaños.
- [x] `ritual` sobre un enum tiene ejemplo.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

