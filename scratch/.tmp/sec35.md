<a id="sec-35-traits"></a>
## 35. Traits (pact)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | `trait`, `dyn Trait`, `impl Trait` |
| Palabras mágicas | `pact`, `ritual`, `dyn`, `impl` |
| Depende de | §31, §33, §34 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec35_traits.pengu` |

Un **`pact`** es un contrato nominal: declara métodos y tipos asociados que un
tipo puede implementar con `ritual`. No hay herencia de clases; la reutilización
se hace con `pact`, composición y `ritual`. Un `pact` no contiene estado.

### 35.1 Declaración

```pengu
pact Shape
    area = (@) -> Float
    name = (@) -> String
        "shape"

rune Circle
    radius: Float

ritual Circle for Shape
    area = (@) -> Float
        3.141592653589793 * @.radius * @.radius

bind c = Circle(radius: 2.0)
print(c.name())
print(c.area())
```

Rust generado:

```rust
trait Shape {
    fn area(&self) -> f64;

    fn name(&self) -> String {
        "shape".to_string()
    }
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.141592653589793 * self.radius * self.radius
    }
}

fn main() {
    let c = Circle { radius: 2.0 };
    println!("{}", c.name());
    println!("{}", c.area());
}
```

Reglas:

1. Un `pact` declara firmas con `name = (params) -> Tipo`; el cuerpo es opcional
   (método default).
2. Los métodos con receptor usan `@`, `@mut` o `@own`. Los métodos sin receptor
   son funciones asociadas y se llaman `Tipo.metodo(...)`.
3. Los métodos de un `pact` son públicos; la visibilidad se controla en el
   `pact`, no método a método.
4. Un `pact` no puede declarar campos ni estado.
5. Un `pact` puede ser genérico (`pact Convert[T]`) y tener supertraits
   (§34.6).
6. Un método default puede llamar a otros métodos del mismo `pact`, incluidos
   los requeridos.
7. No hay `pact` con implementación automática salvo los derives y los auto
   traits de Rust (§46).

### 35.2 Implementación

```pengu
pact Show
    show = (@) -> String

rune Point
    x: Int
    y: Int

ritual Show for Point
    show = (@) -> String
        format!("(#{@.x}, #{@.y})")

bind p = Point(x: 1, y: 2)
print(p.show())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

struct Point {
    x: i32,
    y: i32,
}

impl Show for Point {
    fn show(&self) -> String {
        format!("({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", p.show());
}
```

1. `ritual Tipo for Pact` implementa el contrato completo.
2. Todos los métodos requeridos deben existir; si falta uno, `PGS-E3501`.
3. Un método default se puede sobrescribir; si no, se hereda.
4. El tipo y el `pact` deben cumplir la regla huérfana (§35.9).
5. Un tipo puede implementar varios `pact`; los nombres de métodos pueden
   colisionar y se resuelven con `Pact.metodo(valor)` o `Tipo.metodo`.
6. No se puede implementar un `pact` dos veces para el mismo tipo
   (`PGS-E3502`).

### 35.3 Métodos default y `Self`

```pengu
pact Greet
    hello = (@) -> String
        "hello, #{@.name()}"

    name = (@) -> String

rune User
    name: String

ritual User for Greet
    name = (@) -> String
        @.name.clone()

bind u = User(name: "pengu")
print(u.hello())
```

Rust generado:

```rust
trait Greet {
    fn hello(&self) -> String {
        format!("hello, {}", self.name())
    }

    fn name(&self) -> String;
}

struct User {
    name: String,
}

impl Greet for User {
    fn name(&self) -> String {
        self.name.clone()
    }
}

fn main() {
    let u = User { name: "pengu".to_string() };
    println!("{}", u.hello());
}
```

`Self` dentro de un `pact` es el tipo que implementa el contrato; se usa en
tipos de retorno y parámetros. `Self` fuera de un `pact`/`ritual` es error
(`PGS-E3503`).

### 35.4 `pact` genérico

```pengu
pact Convert[T]
    convert = (@) -> T

rune Celsius
    degrees: Float

rune Fahrenheit
    degrees: Float

ritual Convert[Fahrenheit] for Celsius
    convert = (@) -> Fahrenheit
        Fahrenheit(degrees: @.degrees * 9.0 / 5.0 + 32.0)

bind c = Celsius(degrees: 100.0)
print(c.convert().degrees)
```

Rust generado:

```rust
trait Convert<T> {
    fn convert(&self) -> T;
}

struct Celsius {
    degrees: f64,
}

struct Fahrenheit {
    degrees: f64,
}

impl Convert<Fahrenheit> for Celsius {
    fn convert(&self) -> Fahrenheit {
        Fahrenheit { degrees: self.degrees * 9.0 / 5.0 + 32.0 }
    }
}

fn main() {
    let c = Celsius { degrees: 100.0 };
    println!("{}", c.convert().degrees);
}
```

Un `pact` genérico puede fijar el parámetro en el `ritual`
(`Convert[Fahrenheit]`) o dejarlo genérico (`ritual[T] Convert[T] for ...`).
La implementación debe ser coherente con los bounds del `pact`.

### 35.5 `dyn` y object safety

Un `dyn Pact` es un trait object: despacho dinámico a través de una tabla de
métodos. Solo es válido si el `pact` es **object safe**:

```pengu
pact Shape
    area = (@) -> Float

rune Circle
    radius: Float

ritual Shape for Circle
    area = (@) -> Float
        3.141592653589793 * @.radius * @.radius

bind shapes: Vec[Box[dyn Shape]] = Vec[Box.new(Circle(radius: 1.0))]
for shape in &shapes
    print(shape.area())
```

Rust generado:

```rust
trait Shape {
    fn area(&self) -> f64;
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.141592653589793 * self.radius * self.radius
    }
}

fn main() {
    let shapes: Vec<Box<dyn Shape>> = vec![Box::new(Circle { radius: 1.0 })];
    for shape in &shapes {
        println!("{}", shape.area());
    }
}
```

Reglas de object safety:

1. No puede tener métodos genéricos (`[T]`).
2. No puede devolver `Self` por valor; `&Self` sí.
3. No puede tener funciones asociadas sin receptor que usen `Self`.
4. No puede tener constantes asociadas (Rust las prohíbe en trait objects).
5. Los métodos con `@`, `@mut` y `@own` son aceptables si no violan lo anterior.
6. Un `pact` con métodos default que usen `Self` por valor no es object safe.
7. `dyn Pact` necesita un puntero: `&dyn Pact`, `Box[dyn Pact]`, `Rc[dyn Pact]`.
8. `dyn Pact + Send + Sync` se escribe con `+`; el trait object debe cumplir los
   auto traits.

### 35.6 `impl Trait`

`impl Pact` en posición de parámetro acepta cualquier tipo que implemente el
contrato; en retorno devuelve un tipo opaco:

```pengu
pact Shape
    area = (@) -> Float

rune Circle
    radius: Float

ritual Shape for Circle
    area = (@) -> Float
        3.141592653589793 * @.radius * @.radius

print_shape = (shape: impl Shape) -> Unit
    print(shape.area())

make = () -> impl Shape
    Circle(radius: 1.0)

print_shape(make())
```

Rust generado:

```rust
trait Shape {
    fn area(&self) -> f64;
}

struct Circle {
    radius: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.141592653589793 * self.radius * self.radius
    }
}

fn print_shape(shape: impl Shape) {
    println!("{}", shape.area());
}

fn make() -> impl Shape {
    Circle { radius: 1.0 }
}

fn main() {
    print_shape(make());
}
```

1. `impl Pact` en parámetro es azúcar para un parámetro genérico con bound.
2. `impl Pact` en retorno es un tipo opaco; el llamador solo puede usar los
   métodos del `pact`.
3. No se puede usar `impl Pact` en campos de `rune`; usa un parámetro genérico o
   `Box[dyn Pact]`.
4. `impl Pact` no es `dyn Pact`: no hay despacho dinámico ni tamaño de trait
   object.
5. En un `pact`, `impl Pact` en retorno es RPITIT (§36).

### 35.7 Blanket implementations

```pengu
pact Show
    show = (@) -> String

ritual[T] Show for T where T: Display
    show = (@) -> String
        format!("{}", @)

bind n = 7
print(n.show())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

impl<T: std::fmt::Display> Show for T {
    fn show(&self) -> String {
        format!("{}", self)
    }
}

fn main() {
    let n = 7;
    println!("{}", n.show());
}
```

1. Una blanket impl implementa un `pact` para todos los `T` que cumplen un
   bound: `ritual[T] Pact for T where ...`.
2. Debe ser coherente: no puede solaparse con otra implementación del mismo
   `pact` para un tipo concreto (`PGS-E3504`).
3. El `pact` debe ser local o el tipo debe ser local (regla huérfana).
4. Las blanket impls son potentes pero pueden impedir implementaciones futuras;
   se documentan y se prueban.

### 35.8 Auto traits y marker traits

- `Send`, `Sync`, `Sized`, `Unpin` son auto traits: el compilador los deriva de
  los campos.
- `Copy`, `Clone`, `Debug`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`,
  `Default` son traits normales; se implementan con `ritual` o `@@derive`.
- `Send`/`Sync` manuales solo se escriben con `curse ritual ... for ...` y
  requieren justificación de seguridad (§52).
- Un `pact` marker (sin métodos) se puede usar como bound: `pact Magic` +
  `T: Magic`.
- No hay `pact` con estado global ni métodos estáticos mutables.

### 35.9 Coherencia, huérfanos y sellado

1. `ritual Tipo for Pact` exige que `Tipo` o `Pact` sea local.
2. Un `pact` externo para un tipo externo es error de huérfano (`PGS-E3505`).
3. Dos implementaciones que pueden aplicar al mismo tipo son solapamiento
   (`PGS-E3504`).
4. No hay especialización ni `default` en `ritual`.
5. **Sellado por visibilidad:** si un `pact` público tiene un supertrait
   privado, los consumidores externos no pueden implementarlo. PenguScript no
   añade una palabra `seal`; el sellado se logra con `unveil` y un `pact`
   privado:

```pengu
pact Sealed
    hidden = (@) -> Unit

pact Public: Sealed
    value = (@) -> Int

rune Token
    id: Int

ritual Sealed for Token
    hidden = (@) -> Unit
        ()

ritual Public for Token
    value = (@) -> Int
        @.id
```

Rust generado:

```rust
trait Sealed {
    fn hidden(&self);
}

trait Public: Sealed {
    fn value(&self) -> i32;
}

struct Token {
    id: i32,
}

impl Sealed for Token {
    fn hidden(&self) {}
}

impl Public for Token {
    fn value(&self) -> i32 {
        self.id
    }
}

fn main() {
    let t = Token { id: 7 };
    println!("{}", t.value());
}
```

### 35.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3501` | falta un método requerido | implementarlo |
| `PGS-E3502` | `pact` implementado dos veces | eliminar duplicado |
| `PGS-E3503` | `Self` fuera de `pact`/`ritual` | moverlo dentro |
| `PGS-E3504` | implementaciones solapadas | separar tipos o bounds |
| `PGS-E3505` | violación de huérfano | hacer local el tipo o el `pact` |
| `PGS-E3506` | `dyn Pact` no object-safe | quitar genéricos/`Self` por valor |
| `PGS-E3507` | método de `pact` sin receptor mal usado | añadir `@` o llamar como asociado |
| `PGS-W3501` | método default sobrescrito sin necesidad | documentar la diferencia |
| `PGS-W3502` | blanket impl muy amplia | acotar el bound |

### 35.11 Criterios de aceptación

- [x] Declaración, métodos y default están definidos.
- [x] `pact` genérico y `dyn` tienen ejemplo.
- [x] Object safety está explicada.
- [x] `impl Trait` y blanket impls están cubiertas.
- [x] Coherencia, huérfanos y sellado por visibilidad están definidos.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
