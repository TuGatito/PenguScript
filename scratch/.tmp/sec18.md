<a id="sec-18-lifetimes"></a>
## 18. Lifetimes

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 3 |
| Rust | `'a`, `'static`, elisión, bounds, variance |
| Palabras mágicas | `'a`, `'static`, `for<'a>` |
| Depende de | §17, §33 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec18_lifetimes.pengu` |

Un **lifetime** es el rango en el que una referencia es válida. Rust lo comprueba
en tiempo de compilación; no hay coste en runtime. PenguScript usa la misma
sintaxis `'a` y `'static` que Rust, sin cambiarla.

### 18.1 Sintaxis

| Forma | Significado | Ejemplo |
|---|---|---|
| `&'a T` | referencia compartida con lifetime `'a` | `&'a Str` |
| `&'a mut T` | referencia mutable con lifetime `'a` | `&'a mut String` |
| `'static` | vive todo el programa | `&'static Str` |
| `['a]` | parámetro de lifetime | `Excerpt['a]` |
| `['a, T]` | lifetime y tipo | `Holder['a, T]` |
| `T: 'a` | `T` vive al menos `'a` | `T: 'a` |
| `'a: 'b` | `'a` vive al menos `'b` | `'a: 'b` |
| `for<'a>` | higher-ranked lifetime | `for<'a> (&'a T) -> &'a T` |

Los lifetimes no son valores: no se pueden almacenar, comparar ni imprimir. Solo
describen relaciones entre referencias.

### 18.2 Elisión

Rust permite omitir lifetimes en muchos casos. PenguScript aplica las mismas
reglas de elisión, en este orden:

| # | Situación | Resultado |
|---|---|---|
| 1 | Cada referencia de entrada sin lifetime recibe un lifetime distinto | `fn f(x: &T, y: &U)` → `fn f<'a, 'b>(x: &'a T, y: &'b U)` |
| 2 | Si hay exactamente un lifetime de entrada, la salida lo usa | `fn f(x: &T) -> &T` → `fn f<'a>(x: &'a T) -> &'a T` |
| 3 | Si hay un receptor `&self`/`&mut self`, la salida usa el lifetime del receptor | `fn f(&self, x: &T) -> &T` → salida ligada a `&self` |
| 4 | Si no se aplica ninguna regla, el lifetime de salida es obligatorio | error `PGS-E1801` |

Ejemplos:

```text
f(x: &T) -> &T                    -- elisión: salida = x
f(x: &T, y: &U) -> &T             -- error: dos entradas, salida ambigua
f<'a>(x: &'a T, y: &'a U) -> &'a T -- explícito: ambas entradas viven 'a
f(&self, x: &T) -> &T             -- salida ligada a &self
```

La elisión no cambia la semántica; solo evita escribir lifetimes cuando la
relación es obvia.

### 18.3 Lifetimes explícitos en funciones

```pengu
longest = ['a](a: &'a Str, b: &'a Str) -> &'a Str
    if a.len() >= b.len() then a else b

grimoire
    bind a = "pengu"
    bind b = "script"
    print(longest(a, b))
```

Rust generado:

```rust
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}

fn main() {
    let a = "pengu";
    let b = "script";
    println!("{}", longest(a, b));
}
```

Reglas:

1. `['a]` declara el parámetro de lifetime de la función.
2. `&'a Str` dice que la referencia vive al menos `'a`.
3. `-> &'a Str` liga el retorno a `'a`; el llamador no puede usar el resultado
   más allá de los argumentos.
4. Todos los argumentos que compartan `'a` deben vivir al menos ese lifetime.
5. Si se devuelve una referencia a un temporal local, el compilador lo rechaza
   (`PGS-E1802`).

### 18.4 `'static`

`'static` significa que la referencia vive durante todo el programa:

```pengu
grimoire
    bind name: &'static Str = "pengu"
    print(name)
```

Rust generado:

```rust
fn main() {
    let name: &'static str = "pengu";
    println!("{}", name);
}
```

Son `'static`:

- los literales de string (`"pengu"`);
- los `relic` inmutables;
- las referencias a datos estáticos;
- `Box<dyn Trait + 'static>` (el trait object no contiene referencias cortas).

No son `'static` las referencias a locales, ni un `&T` que depende de un
préstamo. `'static` no significa “inmortal” para valores con `Drop`: un
`&'static T` puede apuntar a un valor que nunca se libera, pero el valor puede
tener un dueño estático.

### 18.5 Structs con lifetimes

```pengu
rune Excerpt['a]
    text: &'a Str

ritual Excerpt['a]
    len = (@) -> Usize
        @.text.len()

grimoire
    bind text = "pengu"
    bind excerpt = Excerpt(text: text)
    print(excerpt.len())
```

Rust generado:

```rust
struct Excerpt<'a> {
    text: &'a str,
}

impl<'a> Excerpt<'a> {
    fn len(&self) -> usize {
        self.text.len()
    }
}

fn main() {
    let text = "pengu";
    let excerpt = Excerpt { text };
    println!("{}", excerpt.len());
}
```

Reglas:

1. Un `rune` con referencias declara todos los lifetimes que usa.
2. El `ritual` repite los parámetros: `ritual Excerpt['a]`.
3. El valor prestado debe vivir al menos tanto como el `rune`.
4. Un `rune` con `'static` solo acepta referencias `'static`; no se puede
   construir con un local.
5. Los campos con referencias no se pueden mover fuera del `rune` sin romper el
   lifetime; se prestan o se copian.

### 18.6 Bounds de lifetime

```pengu
rune Holder['a, T: 'a]
    value: &'a T

ritual Holder['a, T]
    get = (@) -> &'a T
        @.value
```

Rust generado:

```rust
struct Holder<'a, T: 'a> {
    value: &'a T,
}

impl<'a, T: 'a> Holder<'a, T> {
    fn get(&self) -> &'a T {
        self.value
    }
}
```

Reglas:

1. `T: 'a` exige que `T` viva al menos `'a`; es necesario para guardar `&'a T`.
2. `'a: 'b` exige que `'a` viva al menos `'b`.
3. Los bounds se pueden escribir en la lista de parámetros o en `where` (§34).
4. Un `impl` puede repetir o relajar bounds; no puede añadir un bound que el
   tipo no cumpla.
5. Los bounds de lifetime no cambian el layout ni el coste.

### 18.7 Variance

La varianza describe cómo un cambio de lifetime afecta a un tipo genérico:

| Tipo | Varianza en `'a` | Varianza en `T` |
|---|---|---|
| `&'a T` | covariante | covariante si `T` lo es |
| `&'a mut T` | covariante | invariante |
| `Cell[T]`, `RefCell[T]`, `Mutex[T]` | — | invariante |
| `fn(T)` | — | contravariante |
| `fn() -> T` | — | covariante |
| `Box[T]`, `Vec[T]` | — | covariante |

Reglas:

1. Covariante: un `&'long T` se puede usar como `&'short T`.
2. Invariante: no se puede cambiar el lifetime ni el tipo aunque parezca seguro;
   es la opción conservadora para mutabilidad interior.
3. Contravariante: un `fn(&'short T)` puede usarse como `fn(&'long T)`.
4. PenguScript no expone anotaciones de varianza; se heredan de Rust.
5. Si un tipo no compila por varianza, la solución es un límite explícito o
   rediseñar el contenedor, no un cast.

### 18.8 HRTB: adelanto

Un **higher-ranked trait bound** cuantifica sobre todos los lifetimes:

```pengu
apply = (f: for<'a> (&'a Int) -> Int, x: Int) -> Int
    f(&x)
```

Rust generado:

```rust
fn apply<F>(f: F, x: i32) -> i32
where
    F: for<'a> Fn(&'a i32) -> i32,
{
    f(&x)
}
```

La sintaxis `for<'a>` se documenta en §37; en §18 solo se introduce para
reconocerla. `Fn`/`FnMut`/`FnOnce` se detallan en §38.

### 18.9 Errores típicos

```text
error[E0106]: missing lifetime specifier
  --> src/main.rs:3:31
   |
 3 | fn longest(a: &str, b: &str) -> &str {
   |                               ^ expected named lifetime parameter
   |
   = help: this function's return type contains a borrowed value, but the
           signature does not say whether it is borrowed from `a` or `b`
```

Corrección:

```rust
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}
```

### 18.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E1801` | lifetime de salida ambiguo | añadir `'a` y ligarlo |
| `PGS-E1802` | retorno de referencia a un local | devolver el valor o mover el dueño |
| `PGS-E1803` | lifetime no declarado en el `rune` | añadir `['a]` |
| `PGS-E1804` | bound `T: 'a` incumplido | acortar el lifetime o cambiar el tipo |
| `PGS-E1805` | `'static` requerido pero el valor es local | usar un `String`/`Box` o un estático |
| `PGS-E1806` | varianza incompatible | rediseñar el contenedor |
| `PGS-W1801` | lifetime explícito innecesario | dejar la elisión |

### 18.11 Criterios de aceptación

- [x] La sintaxis de lifetimes y `'static` está definida.
- [x] La tabla de elisión cubre los casos estables.
- [x] Los lifetimes en funciones, structs e impls están cubiertos.
- [x] Los bounds y la varianza están explicados.
- [x] HRTB se introduce y se enlaza a §37.
- [x] Hay un error de elisión con corrección.
- [x] El ejemplo tiene Rust compilable.

[↑ Volver al índice](#indice)

