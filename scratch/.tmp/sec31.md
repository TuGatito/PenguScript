<a id="sec-31-implementaciones"></a>
## 31. Implementaciones (`ritual`)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4B |
| Rust | `impl` |
| Palabras mágicas | `ritual`, `pact`, `@`, `@mut`, `@own`, `Self` |
| Depende de | §15, §28, §29 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec31_impls.pengu` |

Un **`ritual`** implementa métodos y funciones asociadas para un tipo. Es el
equivalente de `impl` en Rust: no crea herencia ni subtipos; agrupa
comportamiento.

### 31.1 `ritual` inherente

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    new = (x: Float, y: Float) -> Point
        Point(x: x, y: y)

    origin = () -> Point
        Point(x: 0.0, y: 0.0)

    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    translate = (@mut, dx: Float, dy: Float) -> Unit
        @.x = @.x + dx
        @.y = @.y + dy

    into_pair = (@own) -> (Float, Float)
        (@.x, @.y)

bind p = Point.new(3.0, 4.0)
print(p.length())
print(Point.origin().length())
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn new(x: f64, y: f64) -> Point {
        Point { x, y }
    }

    fn origin() -> Point {
        Point { x: 0.0, y: 0.0 }
    }

    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.x = self.x + dx;
        self.y = self.y + dy;
    }

    fn into_pair(self) -> (f64, f64) {
        (self.x, self.y)
    }
}

fn main() {
    let p = Point::new(3.0, 4.0);
    println!("{}", p.length());
    println!("{}", Point::origin().length());
}
```

Reglas:

1. La cabecera es `ritual Tipo`; el cuerpo va indentado.
2. Un método es `nombre = (receptores, params) -> Tipo`.
3. `@` = `&self`, `@mut` = `&mut self`, `@own` = `self`.
4. Una función asociada no lleva receptor: `origin = () -> Point`.
5. `@` solo existe dentro de un método con receptor; en una función asociada
   es error (`PGS-E3101`).
6. `Self` se refiere al tipo implementado; se puede usar como tipo de retorno o
   en parámetros.
7. Los métodos no se sobrecargan: un nombre por `ritual` y tipo (`PGS-E3102`).
8. Las implementaciones inherentes solo se permiten para tipos locales
   (`PGS-E3105`).

### 31.2 Receptores

| Receptor | Rust | Mutabilidad | Consumo |
|---|---|---|---|
| `@` | `&self` | no | préstamo |
| `@mut` | `&mut self` | sí | préstamo mutable |
| `@own` | `self` | sí | mueve |

```pengu
rune Counter
    value: Int

ritual Counter
    get = (@) -> Int
        @.value

    add = (@mut, n: Int) -> Unit
        @.value = @.value + n

    consume = (@own) -> Int
        @.value

morph c = Counter(value: 0)
c.add(3)
print(c.get())
print(c.consume())
```

Rust generado:

```rust
struct Counter {
    value: i32,
}

impl Counter {
    fn get(&self) -> i32 {
        self.value
    }

    fn add(&mut self, n: i32) {
        self.value = self.value + n;
    }

    fn consume(self) -> i32 {
        self.value
    }
}

fn main() {
    let mut c = Counter { value: 0 };
    c.add(3);
    println!("{}", c.get());
    println!("{}", c.consume());
}
```

Llamar a `@mut` exige un binding `morph`; llamar a `@own` mueve el valor y no se
puede volver a usar.

### 31.3 `Self`

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    shifted = (@, dx: Float, dy: Float) -> Self
        Point(x: @.x + dx, y: @.y + dy)

    same = (@) -> Bool
        @.x == 0.0 and @.y == 0.0

bind p = Point(x: 1.0, y: 2.0)
print(p.shifted(1.0, 1.0).same())
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn shifted(&self, dx: f64, dy: f64) -> Self {
        Point {
            x: self.x + dx,
            y: self.y + dy,
        }
    }

    fn same(&self) -> bool {
        self.x == 0.0 && self.y == 0.0
    }
}

fn main() {
    let p = Point { x: 1.0, y: 2.0 };
    println!("{}", p.shifted(1.0, 1.0).same());
}
```

`Self` no se puede usar fuera de un `ritual` (`PGS-E3103`). En una función
asociada, `Self` es el tipo; para construir se usa el nombre del tipo o
`Self(...)`.

### 31.4 Genéricos y `where`

```pengu
rune Holder[T]
    value: T

ritual Holder[T]
    get = (@) -> &T
        &@.value

    replace = (@mut, value: T) -> T
        bind old = @.value
        @.value = value
        old
```

Rust generado:

```rust
struct Holder<T> {
    value: T,
}

impl<T> Holder<T> {
    fn get(&self) -> &T {
        &self.value
    }

    fn replace(&mut self, value: T) -> T {
        let old = self.value;
        self.value = value;
        old
    }
}
```

Con `where`:

```pengu
rune Wrapper[T]
    value: T

ritual Wrapper[T] where T: Clone
    duplicate = (@) -> T
        @.value.clone()

bind w = Wrapper(value: 7)
print(w.duplicate())
```

Rust generado:

```rust
struct Wrapper<T> {
    value: T,
}

impl<T: Clone> Wrapper<T> {
    fn duplicate(&self) -> T {
        self.value.clone()
    }
}

fn main() {
    let w = Wrapper { value: 7 };
    println!("{}", w.duplicate());
}
```

El `where` del `ritual` debe ser compatible con el del tipo; se permiten bounds
adicionales solo para los métodos que los necesitan.

### 31.5 Implementaciones de trait

Un `pact` declara el contrato; `ritual Tipo for Pact` lo implementa:

```pengu
pact Show
    show = (@) -> String

rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

ritual Point for Show
    show = (@) -> String
        format!("Point(#{@.x}, #{@.y})")

bind p = Point(x: 3.0, y: 4.0)
print(p.show())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }
}

impl Show for Point {
    fn show(&self) -> String {
        format!("Point({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.show());
}
```

Reglas de coherencia:

1. Una implementación inherente solo vale para un tipo local.
2. `ritual Tipo for Pact` exige que el tipo o el trait sea local (regla huérfana
   de Rust, `PGS-E3106`).
3. No hay implementaciones blanket en PenguScript; se reservan para §36.
4. Un trait no puede implementarse dos veces para el mismo tipo (`PGS-E3107`).
5. Todos los métodos requeridos por el `pact` deben existir; los métodos con
   default son opcionales.
6. El orden de resolución es inherente antes que trait; si ambos tienen el mismo
   nombre, se usa el inherente y se avisa (`PGS-W3101`).

### 31.6 Visibilidad de métodos

Por defecto, un método es tan visible como su tipo. `unveil` lo hace público y
`unveil(tome)`/`unveil(scroll)` limitan la visibilidad:

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    unveil length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    unveil(tome) reset = (@mut) -> Unit
        @.x = 0.0
        @.y = 0.0
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    pub fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    pub(crate) fn reset(&mut self) {
        self.x = 0.0;
        self.y = 0.0;
    }
}
```

### 31.7 Constantes asociadas

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    sigil ORIGIN: Point = Point(x: 0.0, y: 0.0)

print(Point.ORIGIN.x)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    const ORIGIN: Point = Point { x: 0.0, y: 0.0 };
}

fn main() {
    println!("{}", Point::ORIGIN.x);
}
```

Una constante asociada debe ser evaluable en `const`; no puede llamar a métodos
no `const` (§19).

### 31.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3101` | `@` en función asociada | añadir receptor o quitar `@` |
| `PGS-E3102` | método duplicado | renombrar |
| `PGS-E3103` | `Self` fuera de `ritual` | mover dentro |
| `PGS-E3104` | receptor incompatible con el uso | usar `morph`/`@mut` |
| `PGS-E3105` | `ritual` inherente sobre tipo externo | mover a un newtype |
| `PGS-E3106` | violación de coherencia/huérfano | implementar trait local o tipo local |
| `PGS-E3107` | trait implementado dos veces | eliminar duplicado |
| `PGS-E3108` | falta un método del `pact` | implementarlo |
| `PGS-W3101` | método inherente y de trait con el mismo nombre | renombrar |
| `PGS-W3102` | `@own` en un método que no consume | usar `@` |

### 31.9 Criterios de aceptación

- [x] `ritual` inherente y sus métodos están definidos.
- [x] `@`, `@mut`, `@own` mapean a `&self`, `&mut self`, `self`.
- [x] Funciones asociadas y `Self` tienen ejemplo.
- [x] Genéricos, `where` y métodos con bounds están cubiertos.
- [x] `ritual Tipo for Pact` y coherencia están definidos.
- [x] Visibilidad y constantes asociadas tienen ejemplo.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

