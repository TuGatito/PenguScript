<a id="sec-15-funciones"></a>
## 15. Funciones y lambdas

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 2 |
| Rust | `fn`, closures, `impl`, `fn main` |
| Palabras mágicas | `->`, `=>`, `@`, `grimoire`, `dream`, `curse`, `eternal` |
| Depende de | §4, §5, §7, §8 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec15_functions.pengu` |

Una función nombrada se declara con `=` y `->`:

```pengu
sum = (x: Int, y: Int) -> Int
    x + y
```

`->` es el operador de función: separa los parámetros del tipo de retorno. Una
lambda usa `=>` y produce una closure:

```pengu
bind inc = (x: Int) => x + 1
```

La diferencia no es cosmética: `->` declara un **item** de función, sin captura;
`=>` declara una **closure**, que puede capturar el entorno. Esta distinción
elimina la ambigüedad entre una función y una variable global, y permite que
`name = (...) -> Tipo` sea un item de módulo aunque `bind`/`morph` no puedan
usarse a nivel de módulo (§5).

### 15.1 Sintaxis de funciones nombradas

```pengu
name = (param: Tipo, otro: Tipo) -> TipoDeRetorno
    cuerpo

name = [T](valor: T) -> T
    valor
```

Reglas:

1. El nombre es un identificador XID; no puede repetirse en el mismo scope
   (`PGS-E9612`).
2. El tipo de retorno es **obligatorio**. `->` sin tipo es error
   (`PGS-E9603`).
3. El cuerpo va indentado en las líneas siguientes. No hay cuerpo inline para
   funciones nombradas (`PGS-E9602`); para una expresión corta se usa una lambda
   o se escribe el cuerpo en varias líneas.
4. La función es un item: se ve en todo el módulo, puede llamarse antes de su
   definición y no captura variables.
5. Una función nombrada solo puede declararse en un módulo, `scroll`, `ritual`,
   `pact` o `foreign`; no dentro de otra función. Para una función local se usa
   una lambda.
6. No hay overloading, argumentos por defecto, varargs ni argumentos nombrados
   (`PGS-E9616`).
7. Los parámetros se pasan por posición; el número y los tipos se comprueban en
   la llamada (`PGS-E9618`).

### 15.2 Parámetros

| Forma | Significado | Rust |
|---|---|---|
| `x: T` | parámetro inmutable | `x: T` |
| `morph x: T` | parámetro mutable local | `mut x: T` |
| `_: T` | parámetro ignorado | `_: T` |
| `@` | receptor `&self` | `&self` |
| `@mut` | receptor `&mut self` | `&mut self` |
| `@own` | receptor `self` | `self` |

Reglas:

1. El receptor, si existe, debe ser el primer parámetro.
2. Un método tiene exactamente un receptor; una función libre no tiene.
3. `morph` en un parámetro permite mutar la copia local; no cambia el tipo ni
   el ownership del argumento.
4. `_` se usa para parámetros no usados; no introduce nombre.
5. No se permite `self`, `this` ni `me`; el receptor es `@`/`@mut`/`@own`
   (`PGS-E9606`).
6. Los parámetros no son patrones; para destructuring se usa un `bind` dentro del
   cuerpo (§5.6).

### 15.3 Retorno implícito y `return`

La última expresión del cuerpo es el valor de retorno:

```pengu
sum = (x: Int, y: Int) -> Int
    x + y
```

Si la última línea es una sentencia (`bind`, asignación, `print`), la función
devuelve `Unit` y el tipo declarado debe ser `Unit`:

```pengu
log = (msg: Str) -> Unit
    print(msg)
```

`return` sale antes:

```pengu
abs = (x: Int) -> Int
    if x < 0
        return -x
    x
```

Reglas:

1. `return expr` debe unificar con el tipo de retorno (`PGS-E9608`).
2. `return` sin valor solo es válido en una función `-> Unit` (`PGS-E9609`).
3. `return expr` en una función `-> Unit` es error (`PGS-E9610`).
4. `return` tiene tipo `Never` y puede aparecer en una rama de un `if` o
   `match` (§8.5).
5. No hay `return` implícito de `none`/`nil`; no existe `null`.

### 15.4 Recursión

Una función puede llamarse a sí misma o a otra función del módulo:

```pengu
fact = (n: UInt) -> UInt
    if n <= 1
        1
    else
        n * fact(n - 1)

is_even = (n: UInt) -> Bool
    if n == 0 then true else is_odd(n - 1)

is_odd = (n: UInt) -> Bool
    if n == 0 then false else is_even(n - 1)
```

La recursion mutua funciona porque los items se ven en todo el módulo (§7.3).
El tipo de retorno explícito es obligatorio para romper la inferencia circular.

### 15.5 Divergencia: `Never`

Una función que no retorna normalmente declara `Never`:

```pengu
fail = (msg: Str) -> Never
    panic(msg)
```

Rust generado:

```rust
fn fail(msg: &str) -> ! {
    panic!("{}", msg);
}
```

Reglas:

1. `Never` solo es válido si el cuerpo diverge en todas las rutas: `panic`,
   `loop` sin `break`, o una llamada a otra función `Never`.
2. Una función `-> Never` puede usarse donde se espera cualquier tipo.
3. No se puede `return` un valor desde una función `Never` (`PGS-E9611`).
4. `panic` es una función de prelude con tipo `(Str) -> Never`.

### 15.6 `grimoire`: el punto de entrada

`grimoire` declara `main`:

```pengu
grimoire
    print("hola, PenguScript")
```

Rust generado:

```rust
fn main() {
    println!("hola, PenguScript");
}
```

Un `grimoire` fallible devuelve `!Unit`:

```pengu
grimoire: !Unit
    bind text = read_file("Tome.toml")?
    print(text)
```

Rust generado:

```rust
fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let text = read_file("Tome.toml")?;
    println!("{}", text);
    Ok(())
}
```

Reglas:

1. `grimoire` no lleva parámetros (`PGS-E9613`).
2. Solo puede haber un `grimoire` por binario (`PGS-E9614`).
3. `grimoire` sin tipo o `grimoire: Unit` genera `fn main()`.
4. `grimoire: !Unit` genera un `main` con `Result<(), Error>` y permite `?`.
5. Otro tipo de retorno es error (`PGS-E9615`).
6. `grimoire` no es una función normal: no se llama, no se toma como valor y no
   se exporta.
7. El `grimoire` de un `lib.pengu` no existe; una librería no tiene `main`.
8. `main` no es una palabra mágica; el único punto de entrada es `grimoire`.

### 15.7 Lambdas y closures

```pengu
bind inc = (x: Int) => x + 1
bind add = (a: Int, b: Int) => a + b
bind make_adder = (n: Int) => (x: Int) => x + n
```

Reglas:

1. Una lambda se escribe `(params) => expr` o `(params) =>` seguido de un bloque
   indentado.
2. Puede capturar por referencia; `move` fuerza captura por valor:
   `move () => print(owner)`.
3. Debe estar ligada con `bind`/`morph`; una lambda a nivel de módulo es error
   (`PGS-E9605`).
4. El tipo de retorno se infiere; no se escribe `=> Tipo`.
5. Los tipos de los parámetros se pueden omitir si el contexto espera un tipo de
   función; si no, son obligatorios (`PGS-E9604`).
6. `return` dentro de una lambda retorna de la closure, no de la función
   envolvente.
7. Las lambdas no se pueden sobrecargar; el número de parámetros es fijo.

Ejemplo con tipo contextual:

```pengu
bind op: (Int, Int) -> Int = (a, b) => a + b
bind inc: (Int) -> Int = (x) => x + 1
```

### 15.8 Métodos y funciones asociadas

Dentro de un `ritual` o `pact`:

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    translate = (@mut, dx: Float, dy: Float) -> Unit
        @.x += dx
        @.y += dy

    origin = () -> Point
        Point(x: 0.0, y: 0.0)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.x += dx;
        self.y += dy;
    }

    fn origin() -> Point {
        Point { x: 0.0, y: 0.0 }
    }
}
```

Reglas:

1. `@` es `&self`, `@mut` es `&mut self`, `@own` es `self`.
2. En el cuerpo del método, `@` se refiere al receptor; no se escribe `self`.
3. `origin` no tiene receptor: es una función asociada y se llama
   `Point.origin()`.
4. Un método se llama `p.length()`; el codegen usa `p.length()`.
5. Un método `@mut` requiere un binding `morph` (`PGS-E9619`).
6. Un método `@own` consume el valor; después no se puede usar.
7. `@` en posición de patrón sigue siendo el operador de binding de Rust
   (`name @ pattern`, §30); el contexto distingue receptor de patrón.

### 15.9 Tipos de función y funciones como valores

Un tipo de función se escribe:

```pengu
bind op: (Int, Int) -> Int = add
bind apply: ((Int) -> Int, Int) -> Int = (f, x) => f(x)
```

Reglas:

1. `(A, B) -> C` es un tipo de función, no una declaración.
2. Una función nombrada se usa como valor escribiendo su nombre:
   `bind f = add`.
3. Una lambda se usa como valor directamente.
4. Las funciones `-> Never` son subtipo de cualquier tipo de función con los
   mismos parámetros.
5. Los tipos de función no llevan nombre de parámetro; solo tipos.

### 15.10 Genéricos: adelanto

La sintaxis de parámetros de tipo es `[T]`:

```pengu
identity = [T](value: T) -> T
    value

bind n = identity[Int](42)
bind s = identity[Str]("pengu")
```

Las restricciones (`where`, `pact`) se definen en §33–§34. En Fase 2 solo se
documenta la forma; el codegen es:

```rust
fn identity<T>(value: T) -> T {
    value
}

let n = identity::<i32>(42);
let s = identity::<&str>("pengu");
```

### 15.11 Modificadores: adelanto

| Modificador | Rust | Se detalla en |
|---|---|---|
| `dream` | `async fn` | §50 |
| `curse` | `unsafe fn` | §52 |
| `eternal` | `const fn` | §46 |
| `foreign` | `extern "C"` | §54 |

```pengu
dream fetch = (url: Str) -> !String
    -- cuerpo async
```

El tipo `!String` es `Result[String, Error]`; el `async` se añade por el
modificador. La semántica de `awaken`, `?` y errores se ve en §48–§50.

### 15.12 Ejemplo completo

```pengu
rune Point
    x: Float
    y: Float

ritual Point
    length = (@) -> Float
        (@.x * @.x + @.y * @.y).sqrt()

    translate = (@mut, dx: Float, dy: Float) -> Unit
        @.x += dx
        @.y += dy

    origin = () -> Point
        Point(x: 0.0, y: 0.0)

sum = (x: Int, y: Int) -> Int
    x + y

grimoire
    morph p = Point(x: 3.0, y: 4.0)
    print(p.length())
    p.translate(1.0, 2.0)
    print(p.length())

    bind q = Point.origin()
    print(q.length())
    print(sum(2, 3))
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn length(&self) -> f64 {
        (self.x * self.x + self.y * self.y).sqrt()
    }

    fn translate(&mut self, dx: f64, dy: f64) {
        self.x += dx;
        self.y += dy;
    }

    fn origin() -> Point {
        Point { x: 0.0, y: 0.0 }
    }
}

fn sum(x: i32, y: i32) -> i32 {
    x + y
}

fn main() {
    let mut p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.length());
    p.translate(1.0, 2.0);
    println!("{}", p.length());

    let q = Point::origin();
    println!("{}", q.length());
    println!("{}", sum(2, 3));
}
```

La salida es `5`, `6.324555320336759`, `0`, `5`.

### 15.13 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E9601` | falta `-> Tipo` en una función nombrada | añadir el tipo de retorno |
| `PGS-E9602` | cuerpo inline en función nombrada | indentar el cuerpo o usar `=>` |
| `PGS-E9603` | `->` sin tipo | escribir el tipo |
| `PGS-E9604` | no se puede inferir el tipo de un parámetro lambda | anotar el parámetro o el contexto |
| `PGS-E9605` | lambda a nivel de módulo | usar una función nombrada |
| `PGS-E9606` | `self`/`this` usado | usar `@`/`@mut`/`@own` |
| `PGS-E9607` | receptor fuera de la primera posición | moverlo al inicio |
| `PGS-E9608` | `return` incompatible con el retorno | ajustar el valor o el tipo |
| `PGS-E9609` | `return` sin valor en función no `Unit` | devolver un valor |
| `PGS-E9610` | `return valor` en función `Unit` | usar `return` sin valor |
| `PGS-E9611` | `return` en función `Never` | eliminar el retorno |
| `PGS-E9612` | nombre de función duplicado | renombrar |
| `PGS-E9613` | `grimoire` con parámetros | quitar los parámetros |
| `PGS-E9614` | más de un `grimoire` | dejar uno |
| `PGS-E9615` | tipo de retorno de `grimoire` inválido | usar `Unit` o `!Unit` |
| `PGS-E9616` | overloading/default/varargs | usar una sola firma |
| `PGS-E9617` | captura en función nombrada | usar una lambda |
| `PGS-E9618` | número o tipo de argumentos incorrecto | ajustar la llamada |
| `PGS-E9619` | método `@mut` sobre binding inmutable | usar `morph` |
| `PGS-E9620` | receptor incompatible con el método | ajustar `@`/`@mut`/`@own` |

### 15.14 Criterios de aceptación

- [x] `name = (...) -> Tipo` y `(params) => expr` están definidos.
- [x] El tipo de retorno de una función nombrada es obligatorio.
- [x] El cuerpo de una función nombrada es indentado, sin inline.
- [x] `bind`/`morph` siguen prohibidos a nivel de módulo; las funciones no son
      variables globales.
- [x] `return`, recursión y `Never` están definidos.
- [x] `grimoire` y `grimoire: !Unit` generan `main` y `Result`.
- [x] Los receptores `@`/`@mut`/`@own` y las funciones asociadas están definidos.
- [x] Las lambdas capturan, `move` fuerza captura por valor y su tipo se infiere.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

