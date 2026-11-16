<a id="sec-38-closures"></a>
## 38. Closures

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | Closures, `Fn`/`FnMut`/`FnOnce`, `move` |
| Palabras mágicas | `=>`, `move`, `Fn`, `FnMut`, `FnOnce` |
| Depende de | §15, §17, §18, §37 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec38_closures.pengu` |

Una **closure** es una función anónima que puede capturar variables del entorno.
En PenguScript se escribe con `=>`; `->` se reserva para funciones nombradas y
tipos de función. La closure infiere sus tipos y su tipo de retorno; no se
declara `=> Tipo`.

### 38.1 Sintaxis

```pengu
bind inc = (x: Int) => x + 1
print(inc(4))

bind add = (a: Int, b: Int) =>
    a + b

print(add(2, 3))
```

Rust generado:

```rust
fn main() {
    let inc = |x: i32| x + 1;
    println!("{}", inc(4));

    let add = |a: i32, b: i32| {
        a + b
    };

    println!("{}", add(2, 3));
}
```

Reglas:

1. La forma corta es `(params) => expr`; la forma de bloque es `(params) =>`
   seguida de líneas indentadas.
2. Los tipos de los parámetros son opcionales si el contexto los infiere; en
   APIs públicas se escriben.
3. No se escribe tipo de retorno en la closure; se infiere.
4. Una closure se asigna con `bind` o `morph`, no se declara como item.
5. No hay closures genéricas; si necesitas genéricos, usa una función nombrada o
   un `pact`.
6. `=>` no se usa para `match`; los brazos usan `then`/bloques (§30).

### 38.2 Captura por referencia

```pengu
bind base = 10
bind add_base = (x: Int) => x + base
print(add_base(5))
```

Rust generado:

```rust
fn main() {
    let base = 10;
    let add_base = |x: i32| x + base;
    println!("{}", add_base(5));
}
```

1. Si la closure solo lee una variable, la captura es por referencia compartida
   (`&T`).
2. La variable debe vivir al menos lo que la closure.
3. El compilador infiere `Fn` si no muta ni consume.
4. No se puede mutar una captura compartida; para eso se usa `FnMut`.

### 38.3 Captura mutable y `FnMut`

```pengu
morph count = 0
morph inc = () => count += 1
inc()
inc()
drop(inc)
print(count)
```

Rust generado:

```rust
fn main() {
    let mut count = 0;
    let mut inc = || count += 1;
    inc();
    inc();
    drop(inc);
    println!("{}", count);
}
```

1. Una closure que muta una captura es `FnMut`.
2. El binding de la closure debe ser `morph`, porque llamarla requiere `&mut`.
3. Mientras la closure vive, la variable capturada está prestada mutuamente; no
   se puede usar directamente. Se libera con `drop(closure)` o al salir del
   scope.
4. `bind inc = ...` con una closure `FnMut` es error (`PGS-E3802`).

### 38.4 `move`

```pengu
bind owner = String.from("pengu")
bind take = move () => print(owner)
take()
```

Rust generado:

```rust
fn main() {
    let owner = String::from("pengu");
    let take = move || println!("{}", owner);
    take();
}
```

1. `move` captura por valor, no por referencia.
2. Es obligatorio cuando la closure sobrevive a la variable o se devuelve.
3. Mover un `String`/`Vec` transfiere la propiedad; la variable original queda
   movida y no se puede usar.
4. `move` no implica `FnOnce`; una closure `move` que solo lee puede ser `Fn`.

### 38.5 Devolver closures

```pengu
make_adder = (n: Int) -> impl Fn(Int) -> Int
    move (x: Int) => x + n

bind add5 = make_adder(5)
print(add5(3))
```

Rust generado:

```rust
fn make_adder(n: i32) -> impl Fn(i32) -> i32 {
    move |x| x + n
}

fn main() {
    let add5 = make_adder(5);
    println!("{}", add5(3));
}
```

1. El retorno es `impl Fn(...) -> ...`; el tipo concreto es opaco.
2. `move` es necesario para que `n` viva dentro de la closure.
3. No se puede devolver `dyn Fn` sin `Box`/`Rc`.
4. Si la closure muta estado, el retorno es `impl FnMut(...)` y el binding del
   llamador debe ser `morph`.

### 38.6 `Fn`, `FnMut`, `FnOnce`

| Trait | Puede llamarse | Captura | Binding |
|---|---|---|---|
| `Fn` | muchas veces | `&T` | `bind` |
| `FnMut` | muchas veces | `&mut T` | `morph` |
| `FnOnce` | una vez | `T` | `bind`/`morph` |

1. El compilador elige el trait más permisivo que la closure cumple.
2. `Fn` implica `FnMut`; `FnMut` implica `FnOnce`.
3. Una closure que consume una captura es `FnOnce`.
4. Un parámetro `f: impl Fn(Int) -> Int` acepta `Fn`; para `FnMut` se escribe
   `impl FnMut(Int) -> Int` y el parámetro debe ser `morph` para llamarlo.
5. `dyn Fn` necesita un puntero: `Box[dyn Fn(Int) -> Int]`.

### 38.7 Closures en structs

```pengu
rune Handler[F]
    run: F

bind h = Handler(run: (x: Int) => x + 1)
print((h.run)(1))
```

Rust generado:

```rust
struct Handler<F> {
    run: F,
}

fn main() {
    let h = Handler { run: |x: i32| x + 1 };
    println!("{}", (h.run)(1));
}
```

1. Un campo de closure usa un parámetro genérico `F` o `Box[dyn Fn...]`; no se
   puede usar `impl Fn` en un campo.
2. `Handler[F]` es genérico; cada closure produce una instancia distinta.
3. Para guardar closures heterogéneas se usa `Vec[Box[dyn Fn(Int) -> Int]]`.
4. La closure puede capturar; el struct se vuelve dueño de la captura si se usa
   `move`.

### 38.8 Recursión y closures

Una closure no puede llamarse a sí misma por el nombre del binding: el nombre
no existe hasta que termina la inicialización. Para recursión se usa una función
nombrada:

```pengu
factorial = (n: Int) -> Int
    if n <= 1 then 1 else n * factorial(n - 1)

print(factorial(5))
```

Rust generado:

```rust
fn factorial(n: i32) -> i32 {
    if n <= 1 { 1 } else { n * factorial(n - 1) }
}

fn main() {
    println!("{}", factorial(5));
}
```

1. Las funciones nombradas sí pueden ser recursivas.
2. Una closure recursiva requiere una indirección (`Rc<RefCell<...>>`) o un
   combinador; se desaconseja y se documenta como patrón avanzado.
3. No hay `let rec` ni `self` en closures.

### 38.9 HRTB y closures

```pengu
apply = [F](f: F, s: &Str) -> &Str where F: for<'a> Fn(&'a Str) -> &'a Str
    f(s)

bind first = (s: &Str) => &s[..1]
print(apply(first, "pengu"))
```

1. Una closure puede cumplir `for<'a> Fn(...)` si no fija el lifetime en una
   captura.
2. `move` puede ayudar, pero no cambia la firma; el HRTB se comprueba aparte.
3. Para callbacks que aceptan cualquier préstamo se prefiere `fn` item o
   `dyn for<'a> Fn`.
4. Los detalles de HRTB están en §37.

### 38.10 `dream` closures

La forma `dream (params) => ...` se reserva para closures asíncronas. Su
semántica, runtime y bounds se definen en §50; en Fase 5 no se generan ejemplos
ejecutables. Una closure normal no puede usar `awaken` sin un contexto async.

### 38.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3801` | closure con tipo de retorno explícito | quitarlo; se infiere |
| `PGS-E3802` | `bind` para una closure `FnMut` | usar `morph` |
| `PGS-E3803` | captura movida y usada después | reordenar o clonar |
| `PGS-E3804` | `move` innecesario que impide reutilizar | quitar `move` |
| `PGS-E3805` | closure devuelta sin `move` | añadir `move` |
| `PGS-E3806` | `impl Fn` en campo de struct | usar genérico o `Box[dyn Fn]` |
| `PGS-E3807` | recursión por nombre de closure | usar función nombrada |
| `PGS-W3801` | closure que podría ser función | extraer a `name = (...) -> ...` |

### 38.12 Criterios de aceptación

- [x] Sintaxis corta y de bloque están definidas.
- [x] Captura por referencia, mutable y `move` tienen ejemplo.
- [x] Devolver closures y `Fn`/`FnMut`/`FnOnce` están cubiertos.
- [x] Closures en structs, recursión y HRTB están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
