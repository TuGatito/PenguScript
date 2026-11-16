<a id="sec-39-function-pointers"></a>
## 39. Function pointers y higher-order functions

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | Funciones de orden superior, iteradores, `Option`/`Result` |
| Palabras mágicas | `Fn`, `map`, `filter`, `fold`, `impl` |
| Depende de | §15, §23, §34, §38 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec39_functional.pengu` |

PenguScript no es un lenguaje funcional puro, pero adopta lo útil de ese estilo:
funciones como valores, composición, iteradores perezosos y combinadores de
`Option`/`Result`. Todo se apoya en traits de Rust (`Fn`, `Iterator`), sin
monadas, sin notación `do` y sin currying automático.

### 39.1 Funciones como valores

```pengu
double = (x: Int) -> Int
    x * 2

apply = (f: (Int) -> Int, x: Int) -> Int
    f(x)

print(apply(double, 5))
```

Rust generado:

```rust
fn double(x: i32) -> i32 {
    x * 2
}

fn apply(f: fn(i32) -> i32, x: i32) -> i32 {
    f(x)
}

fn main() {
    println!("{}", apply(double, 5));
}
```

1. Un `fn` item se usa como valor y se convierte a function pointer cuando el
   contexto lo pide.
2. Un function pointer es `Copy`, no captura y no tiene estado.
3. Un parámetro `(Int) -> Int` es un function pointer; para aceptar closures se
   usa un genérico `F: Fn(Int) -> Int` o `impl Fn(Int) -> Int`.
4. No hay sobrecarga por firma; el tipo del parámetro decide.

### 39.2 Genéricos y `Fn`

```pengu
double = (x: Int) -> Int
    x * 2

apply = [F](f: F, x: Int) -> Int where F: Fn(Int) -> Int
    f(x)

print(apply(double, 5))
print(apply((x: Int) => x + 1, 5))
```

Rust generado:

```rust
fn double(x: i32) -> i32 {
    x * 2
}

fn apply<F>(f: F, x: i32) -> i32
where
    F: Fn(i32) -> i32,
{
    f(x)
}

fn main() {
    println!("{}", apply(double, 5));
    println!("{}", apply(|x| x + 1, 5));
}
```

1. `F: Fn(Int) -> Int` acepta funciones, closures y function pointers.
2. Para mutar estado se usa `FnMut`; para consumir, `FnOnce` (§38).
3. `impl Fn(Int) -> Int` es azúcar para un parámetro genérico; no permite
   nombrar `F` en el cuerpo.
4. El compilador monomorfiza: una instancia por tipo de closure.

### 39.3 Iteradores: adaptadores y consumidores

```pengu
bind nums = [1, 2, 3, 4]

bind doubled = nums.iter()
    .map((x: &Int) => *x * 2)
    .collect[Vec[Int]]()

print(doubled)
```

Rust generado:

```rust
fn main() {
    let nums = [1, 2, 3, 4];

    let doubled = nums
        .iter()
        .map(|x| *x * 2)
        .collect::<Vec<i32>>();

    println!("{:?}", doubled);
}
```

1. `iter()` produce `&T`; `into_iter()` consume y produce `T`; `iter_mut()`
   produce `&mut T`.
2. `map`, `filter`, `flat_map`, `take`, `skip`, `step_by`, `chain`, `zip` son
   adaptadores perezosos: no hacen trabajo hasta un consumidor.
3. `collect`, `fold`, `sum`, `count`, `for_each`, `any`, `all` son consumidores.
4. `collect[Vec[Int]]()` fija el tipo de destino con turbofish; sin él, el
   compilador no sabe qué colección construir.
5. Una cadena de iteradores no asigna un `Vec` intermedio; el compilador la
   fusiona.

### 39.4 `fold`

```pengu
bind nums = [1, 2, 3, 4]
bind total = nums.iter().fold(0, (acc: Int, x: &Int) => acc + *x)
print(total)
```

Rust generado:

```rust
fn main() {
    let nums = [1, 2, 3, 4];
    let total = nums.iter().fold(0, |acc, x| acc + *x);
    println!("{}", total);
}
```

1. `fold(inicial, f)` es el consumidor universal: suma, producto, construcción
   de colecciones, máquina de estados.
2. El acumulador puede cambiar de tipo: `fold(String.new(), ...)`.
3. Para cortocircuito se usa `try_fold` o `find`/`any`, no `fold`.
4. `reduce` existe para el primer elemento; falla en vacío (`none`).

### 39.5 `Option` como funtor

```pengu
bind value: ?Int = some(3)
bind doubled = value.map((x: Int) => x * 2)
print(doubled.unwrap_or(0))

bind chained = value.and_then((x: Int) => if x > 0 then some(x + 1) else none)
print(chained.unwrap_or(0))
```

Rust generado:

```rust
fn main() {
    let value: Option<i32> = Some(3);
    let doubled = value.map(|x| x * 2);
    println!("{}", doubled.unwrap_or(0));

    let chained = value.and_then(|x| if x > 0 { Some(x + 1) } else { None });
    println!("{}", chained.unwrap_or(0));
}
```

1. `map` transforma el valor presente; `none` se propaga.
2. `and_then` encadena funciones que devuelven `?U`; evita `Option[Option[U]]`.
3. `unwrap_or`, `unwrap_or_else`, `ok_or`, `filter` son los combinadores
   habituales.
4. `?` en una función que devuelve `?T` propaga `none`; en `!T` propaga `err`.
5. No hay `null`; la ausencia es un valor explícito.

### 39.6 `Result` como funtor

```pengu
parse = (text: &Str) -> !Int
    text.parse[Int]()

bind value: !Int = parse("41")
bind next = value.map((x: Int) => x + 1)
print(next.unwrap_or(0))
```

Rust generado:

```rust
fn parse(text: &str) -> Result<i32, Box<dyn std::error::Error + Send + Sync>> {
    text.parse::<i32>().map_err(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>)
}

fn main() {
    let value: Result<i32, Box<dyn std::error::Error + Send + Sync>> = parse("41");
    let next = value.map(|x| x + 1);
    println!("{}", next.unwrap_or(0));
}
```

1. `map` transforma el éxito; `map_err` transforma el error.
2. `and_then` encadena operaciones falibles; `or_else` recupera.
3. `?` propaga el error y convierte con `From`; el tipo de error debe ser
   compatible.
4. `unwrap_or` descarta el error; solo para prototipos o valores por defecto
   seguros.
5. `Error` es `Box<dyn Error + Send + Sync>` (§4.8).

### 39.7 Composición

```pengu
compose = [A, B, C](f: (B) -> C, g: (A) -> B) -> impl Fn(A) -> C
    move (x: A) => f(g(x))

bind inc = (x: Int) => x + 1
bind double = (x: Int) => x * 2
bind inc_then_double = compose(double, inc)
print(inc_then_double(3))
```

Rust generado:

```rust
fn compose<A, B, C, F, G>(f: F, g: G) -> impl Fn(A) -> C
where
    F: Fn(B) -> C,
    G: Fn(A) -> B,
{
    move |x| f(g(x))
}

fn main() {
    let inc = |x: i32| x + 1;
    let double = |x: i32| x * 2;
    let inc_then_double = compose(double, inc);
    println!("{}", inc_then_double(3));
}
```

1. `compose(f, g)` aplica `g` y luego `f`; el orden se documenta.
2. No hay operador `>>`/`<<`; se usa una función.
3. La composición devuelve `impl Fn` y captura por `move`.
4. Para pipelines largos, los iteradores suelen ser más legibles que componer
   funciones.

### 39.8 Qué no se adopta

- No hay currying automático: `f(a)(b)` requiere una función que devuelva otra.
- No hay typeclasses/HKT; los traits son el mecanismo de abstracción.
- No hay `do`-notation ni mónadas; `?` y `and_then` cubren el encadenamiento.
- No hay pattern matching en parámetros de closure; se hace en el cuerpo.
- No hay evaluación perezosa general; solo iteradores.
- No hay `compose` en el prelude; se define cuando se necesita.

### 39.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3901` | `map` sin tipo de `collect` | añadir turbofish `collect[Vec[Int]]()` |
| `PGS-E3902` | `fold` con acumulador incompatible | anotar el inicial o el retorno |
| `PGS-E3903` | `FnOnce` llamado dos veces | usar `Fn`/`FnMut` o consumir una vez |
| `PGS-E3904` | `?` en función que no devuelve `?T`/`!T` | cambiar el retorno o usar `match` |
| `PGS-E3905` | `and_then` devuelve `?T` dentro de `!T` | convertir con `ok_or`/`map_err` |
| `PGS-W3901` | cadena de iteradores con `collect` intermedio innecesario | eliminar el `Vec` intermedio |

### 39.10 Criterios de aceptación

- [x] Funciones como valores y `Fn` están definidas.
- [x] Iteradores perezosos, consumidores y `collect` tienen ejemplo.
- [x] `fold`, `Option` y `Result` tienen ejemplo.
- [x] Composición y límites del estilo funcional están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
