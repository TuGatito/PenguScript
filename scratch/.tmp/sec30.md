<a id="sec-30-pattern-matching"></a>
## 30. Pattern matching

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4B |
| Rust | `match`, `if let`, `while let`, `let-else` |
| Palabras mágicas | `match`, `when`, `else`, `@` (pattern) |
| Depende de | §13, §14, §28, §29 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec30_patterns.pengu` |

El **pattern matching** descompone un valor y elige un camino según su forma. Un
patrón puede ser refutable (no cubre todos los valores) o irrefutable (cubre
todos). `bind` y los parámetros exigen patrones irrefutables; `match`, `if` y
`while` aceptan refutables.

### 30.1 `match`

```pengu
label = (n: Int) -> Str
    match n
        when 0 then "cero"
        when 1 | 2 | 3 then "pequeño"
        when 4..=9 then "mediano"
        else "grande"

print(label(0))
print(label(2))
print(label(7))
print(label(42))
```

Rust generado:

```rust
fn label(n: i32) -> &'static str {
    match n {
        0 => "cero",
        1 | 2 | 3 => "pequeño",
        4..=9 => "mediano",
        _ => "grande",
    }
}

fn main() {
    println!("{}", label(0));
    println!("{}", label(2));
    println!("{}", label(7));
    println!("{}", label(42));
}
```

Reglas:

1. La cabecera es `match expr`; los brazos van indentados.
2. Cada brazo empieza por `when`; el patrón va después.
3. `then expr` es un brazo inline; si se omite `then`, el cuerpo es un bloque
   indentado.
4. `else expr` es el brazo por defecto; debe ser el último.
5. El `match` evalúa el scrutinee una vez y elige el primer brazo que coincide.
6. Todos los brazos deben producir el mismo tipo; `Never` se unifica con
   cualquiera (§8).
7. Sin `else`, el `match` debe ser exhaustivo (`PGS-E3005`).

### 30.2 Patrones

| Patrón | Ejemplo | Rust |
|---|---|---|
| literal | `when 0` | `0` |
| binding | `when x` | `x` |
| wildcard | `when _` | `_` |
| tupla | `when (a, b)` | `(a, b)` |
| struct | `when Point(x, y)` | `Point { x, y }` |
| struct con nombres | `when Point(x: a, y: b)` | `Point { x: a, y: b }` |
| enum unitaria | `when none` | `None` |
| enum de tupla | `when some(x)` | `Some(x)` |
| enum de struct | `when Move(x: x, y: y)` | `Move { x, y }` |
| slice | `when [first, .., last]` | `[first, .., last]` |
| rango | `when 0..=9` | `0..=9` |
| or | `when 1 | 2` | `1 | 2` |
| binding `@` | `when whole @ 1..=9` | `whole @ 1..=9` |
| `ref` | `when ref x` | `ref x` |
| `ref mut` | `when ref mut x` | `ref mut x` |
| rest | `when Point(x, ..)` | `Point { x, .. }` |

### 30.3 Guardas

```pengu
classify = (n: Int) -> Str
    match n
        when x if x < 0 then "negativo"
        when x if x == 0 then "cero"
        when x then "positivo"

print(classify(-3))
print(classify(0))
print(classify(5))
```

Rust generado:

```rust
fn classify(n: i32) -> &'static str {
    match n {
        x if x < 0 => "negativo",
        x if x == 0 => "cero",
        x => "positivo",
    }
}

fn main() {
    println!("{}", classify(-3));
    println!("{}", classify(0));
    println!("{}", classify(5));
}
```

Una guarda es `if condición` después del patrón, antes de `then`. Si la guarda
falla, se prueba el siguiente brazo; el binding del patrón no se filtra.

### 30.4 Structs, enums y `..`

```pengu
rune Point
    x: Int
    y: Int

enchanting Shape
    Circle(Int)
    Rectangle(Int, Int)
    Empty

origin = (shape: &Shape) -> Point
    match shape
        when Circle(r) then Point(x: 0, y: 0)
        when Rectangle(w, h) then Point(x: w, y: h)
        when Empty then Point(x: 0, y: 0)

bind s = Rectangle(3, 4)
bind p = origin(&s)
print(p.x)
print(p.y)
```

Rust generado:

```rust
struct Point {
    x: i32,
    y: i32,
}

enum Shape {
    Circle(i32),
    Rectangle(i32, i32),
    Empty,
}

fn origin(shape: &Shape) -> Point {
    match shape {
        Shape::Circle(r) => Point { x: 0, y: 0 },
        Shape::Rectangle(w, h) => Point { x: *w, y: *h },
        Shape::Empty => Point { x: 0, y: 0 },
    }
}

fn main() {
    let s = Shape::Rectangle(3, 4);
    let p = origin(&s);
    println!("{}", p.x);
    println!("{}", p.y);
}
```

En un patrón de struct, `Point(x, y)` es shorthand de `Point(x: x, y: y)`. El
resto `..` ignora los campos no mencionados: `Point(x, ..)`.

### 30.5 `@` como binding de patrón

`@` en un patrón **no** es el receptor `@`; liga el valor completo a un nombre:

```pengu
describe = (n: Int) -> Str
    match n
        when whole @ 1..=9 then "dígito #{whole}"
        else "fuera"

print(describe(7))
```

Rust generado:

```rust
fn describe(n: i32) -> String {
    match n {
        whole @ 1..=9 => format!("dígito {}", whole),
        _ => "fuera".to_string(),
    }
}

fn main() {
    println!("{}", describe(7));
}
```

El contexto distingue `@` de receptor: en un patrón siempre es binding; en una
expresión o en la cabecera de un método es `self`. No se puede usar `@` como
nombre de binding.

### 30.6 `ref` y `ref mut`

El match ergonomics de Rust ya toma préstamos automáticamente cuando el
scrutinee es una referencia. `ref`/`ref mut` fuerzan un préstamo explícito:

```pengu
rune Pair(Int, Int)

bind pair = Pair(1, 2)
match &pair
    when Pair(ref a, _) then print(a)
```

Rust generado:

```rust
struct Pair(i32, i32);

fn main() {
    let pair = Pair(1, 2);
    match &pair {
        Pair(ref a, _) => println!("{}", a),
    }
}
```

Reglas:

1. `ref x` liga `&T`; `ref mut x` liga `&mut T` y exige un scrutinee mutable.
2. En la mayoría de casos no se necesitan; el compilador aplica match ergonomics.
3. `ref`/`ref mut` no se usan en `bind`; allí el binding ya decide el préstamo.
4. Un `ref mut` sobre un valor no mutable es error (`PGS-E3007`).

### 30.7 `if let`

La forma `if PATRÓN = EXPR` es azúcar de `match` con un solo brazo y `else`
opcional:

```pengu
bind maybe: ?Int = some(3)

if some(x) = maybe then
    print(x)
else
    print(0)
```

Rust generado:

```rust
fn main() {
    let maybe: Option<i32> = Some(3);

    if let Some(x) = maybe {
        println!("{}", x);
    } else {
        println!("0");
    }
}
```

Reglas:

1. El patrón a la izquierda de `=` debe ser refutable; un binding simple es
   error (`PGS-E3008`).
2. El `if` produce `Unit` salvo que ambas ramas produzcan el mismo tipo; sin
   `else`, produce `Unit`.
3. `elseif` no se usa con `if let`; se anida o se usa `match`.
4. El binding solo vive en la rama `then`.

### 30.8 `while let`

```pengu
morph values = Vec[1, 2, 3]

while some(x) = values.pop()
    print(x)
```

Rust generado:

```rust
fn main() {
    let mut values = vec![1, 2, 3];

    while let Some(x) = values.pop() {
        println!("{}", x);
    }
}
```

`while PATRÓN = EXPR` reevalúa `EXPR` en cada iteración y termina cuando el
patrón no coincide. El cuerpo es `Unit`; no hay `break value`.

### 30.9 `let-else`

`bind`/`morph` con `else` es la forma `let-else`: si el patrón es refutable y no
coincide, se ejecuta el bloque `else`, que debe divergir.

```pengu
first = (maybe: ?Int) -> Int
    bind some(x) = maybe else
        return 0
    x

print(first(some(7)))
print(first(none))
```

Rust generado:

```rust
fn first(maybe: Option<i32>) -> i32 {
    let Some(x) = maybe else {
        return 0;
    };
    x
}

fn main() {
    println!("{}", first(Some(7)));
    println!("{}", first(None));
}
```

Reglas:

1. Sin `else`, el patrón de `bind`/`morph` debe ser irrefutable.
2. Con `else`, el patrón puede ser refutable; el bloque `else` debe divergir
   (`return`, `break`, `continue`, `panic` o `Never`).
3. El binding vive después del `bind`/`else`; no en el bloque `else`.
4. `morph` con `else` permite mutar el binding resultante.

### 30.10 Exhaustividad y refutabilidad

- Un patrón es **irrefutable** si cubre todos los valores del tipo: un binding,
  `_`, una tupla de irrefutables, una struct de irrefutables.
- Es **refutable** si puede fallar: literales, rangos, variantes concretas,
  slices con longitud fija.
- `match` sin `else` exige cubrir todas las variantes; los rangos deben cubrir
  todo el dominio o tener `else`.
- `if let`/`while let` aceptan refutables por definición.
- `bind`/`morph` exigen irrefutables salvo que tengan `else`.
- `Bool` requiere `true` y `false`; no hay truthiness (§12).

### 30.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3001` | patrón irrefutable en `if let` | usar `bind` o un patrón refutable |
| `PGS-E3002` | `match` no exhaustivo | añadir variante/`else` |
| `PGS-E3003` | tipo incompatible entre brazos | unificar o convertir |
| `PGS-E3004` | `..` en posición inválida | moverlo al final del patrón |
| `PGS-E3005` | falta `else` en `match` abierto | añadir `else` |
| `PGS-E3006` | binding `@` con nombre reservado | renombrar |
| `PGS-E3007` | `ref mut` sobre valor inmutable | usar `morph` |
| `PGS-E3008` | `if` con patrón irrefutable | usar `bind` |
| `PGS-E3009` | `else` de `let-else` no diverge | añadir `return`/`panic` |
| `PGS-E3010` | guarda no `Bool` | usar una condición `Bool` |
| `PGS-W3001` | `_` que oculta un valor útil | nombrar el binding |
| `PGS-W3002` | `match` con un solo brazo | considerar `if let` |

### 30.12 Criterios de aceptación

- [x] `match`, brazos `when`, `else` y guardas están definidos.
- [x] Todos los patrones de tipos agregados están cubiertos.
- [x] `if let`, `while let` y `let-else` tienen ejemplo.
- [x] `@` de patrón se distingue del receptor `@`.
- [x] Exhaustividad y refutabilidad están explicadas.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

