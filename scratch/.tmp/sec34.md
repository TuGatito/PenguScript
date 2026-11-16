<a id="sec-34-constraints"></a>
## 34. Constraints y where

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | Bounds `T: Trait`, `where`, `?Sized` |
| Palabras mágicas | `where`, `:`, `+`, `?Sized` |
| Depende de | §33, §18, §35 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec34_constraints.pengu` |

Un **constraint** (bound) declara qué debe cumplir un parámetro de tipo o un
lifetime para que el item sea válido. PenguScript usa la misma relación que
Rust: el bound se comprueba en la definición y en cada uso; no hay duck typing
ni comprobaciones en runtime.

### 34.1 Bounds en la cabecera

```pengu
largest = [T: PartialOrd + Copy](items: &[T]) -> T
    morph best = items[0]
    for item in &items[1..]
        if *item > best
            best = *item
    best

bind nums = [3, 1, 4, 1]
print(largest(&nums))
```

Rust generado:

```rust
fn largest<T: PartialOrd + Copy>(items: &[T]) -> T {
    let mut best = items[0];
    for item in &items[1..] {
        if *item > best {
            best = *item;
        }
    }
    best
}

fn main() {
    let nums = [3, 1, 4, 1];
    println!("{}", largest(&nums));
}
```

Reglas:

1. Los bounds van después de `:` dentro del corchete: `[T: Pact + Clone]`.
2. `+` combina bounds; todos deben cumplirse.
3. Un bound puede ser un `pact`, un lifetime (`T: 'a`) o `?Sized`.
4. Los bounds se aplican a funciones, `rune`, `enchanting`, `pact`, `ritual` y
   `essence` genérica.
5. Un bound no puede ser una expresión ni un valor; solo un `pact` o lifetime.
6. No hay bounds negativos (`T: !Copy`) ni especialización.

### 34.2 `where`

Para listas largas o bounds que dependen de varios parámetros se usa `where`:

```pengu
describe = [T](value: T) -> String where T: Display + Clone
    format!("#{value}")

print(describe(42))
print(describe("pengu"))
```

Rust generado:

```rust
fn describe<T>(value: T) -> String
where
    T: std::fmt::Display + Clone,
{
    format!("{}", value)
}

fn main() {
    println!("{}", describe(42));
    println!("{}", describe("pengu"));
}
```

Reglas:

1. `where` va al final de la firma, antes del cuerpo.
2. Cada bound se separa con coma: `where T: A + B, U: C`.
3. No se puede repetir un bound idéntico (`PGS-W3401`); sí se pueden repartir
   bounds entre cabecera y `where`.
4. El `where` de un `ritual` debe ser compatible con el del tipo; no puede
   relajar los bounds del tipo (§31).
5. El `where` de un `pact` puede declarar bounds sobre tipos asociados
   (`I: Iterator[Item = Int]`).
6. Un `where` vacío es error (`PGS-E3401`).

### 34.3 Bounds de lifetime

```pengu
pick = ['a, T: 'a](a: &'a T, _b: &'a T) -> &'a T
    a

bind x = 1
bind y = 2
print(pick(&x, &y))
```

Rust generado:

```rust
fn pick<'a, T: 'a>(a: &'a T, _b: &'a T) -> &'a T {
    a
}

fn main() {
    let x = 1;
    let y = 2;
    println!("{}", pick(&x, &y));
}
```

1. `T: 'a` significa que `T` vive al menos tanto como `'a`.
2. `'a: 'b` significa que `'a` vive al menos tanto como `'b`.
3. Los bounds de lifetime no crean valores; solo restringen préstamos.
4. Un lifetime `'static` cumple cualquier bound de lifetime.

### 34.4 `?Sized`

Por defecto todo parámetro de tipo es `Sized`. `?Sized` lo relaja para aceptar
tipos Dynamically Sized (`Str`, `[T]`, `dyn Pact`):

```pengu
debug = [T: ?Sized + Debug](value: &T) -> String
    format!("{:?}", value)

bind text = "pengu"
print(debug(text))
```

Rust generado:

```rust
fn debug<T: ?Sized + std::fmt::Debug>(value: &T) -> String {
    format!("{:?}", value)
}

fn main() {
    let text = "pengu";
    println!("{}", debug(text));
}
```

1. `?Sized` solo tiene sentido detrás de una referencia, `Box[T]` o un puntero.
2. No se puede pasar un `T: ?Sized` por valor; el compilador no conoce su tamaño
   (`PGS-E3404`).
3. `?Sized` no implica `Copy` ni `Clone`.

### 34.5 Bounds sobre tipos asociados

```pengu
total = [I](iter: I) -> Int where I: Iterator[Item = Int]
    iter.sum()

bind values = [1, 2, 3]
print(total(values.iter().copied()))
```

Rust generado:

```rust
fn total<I>(iter: I) -> i32
where
    I: Iterator<Item = i32>,
{
    iter.sum()
}

fn main() {
    let values = [1, 2, 3];
    println!("{}", total(values.iter().copied()));
}
```

Reglas:

1. La forma `Pact[Item = Tipo]` fija un tipo asociado en el bound.
2. Se pueden fijar varios: `Pact[A = Int, B = Str]`.
3. Un tipo asociado no fijado sigue siendo opaco; el compilador no lo infiere
   por el uso.
4. Los bounds de tipo asociado se comprueban en la implementación (§36).

### 34.6 Supertraits y bounds de `pact`

```pengu
pact Show
    show = (@) -> String

pact Pretty: Show
    pretty = (@) -> String
        "**#{@.show()}**"

rune Point
    x: Int
    y: Int

ritual Show for Point
    show = (@) -> String
        format!("(#{@.x}, #{@.y})")

ritual Pretty for Point

bind p = Point(x: 1, y: 2)
print(p.pretty())
```

Rust generado:

```rust
trait Show {
    fn show(&self) -> String;
}

trait Pretty: Show {
    fn pretty(&self) -> String {
        format!("**{}**", self.show())
    }
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

impl Pretty for Point {}

fn main() {
    let p = Point { x: 1, y: 2 };
    println!("{}", p.pretty());
}
```

1. `pact Pretty: Show` declara que implementar `Pretty` exige `Show`.
2. El supertrait no se implementa automáticamente; `ritual Pretty for Point`
   debe ir acompañado de `ritual Show for Point`.
3. Un bound `T: Pretty` implica `T: Show`.
4. Los supertraits múltiples se separan con `+`: `pact Pretty: Show + Clone`.

### 34.7 Resolución de bounds

1. El compilador resuelve los bounds en el punto de uso, no en runtime.
2. Un bound no satisfecho es `PGS-E3402`; el mensaje debe indicar qué
   implementación falta.
3. Los bounds se pueden inferir por el contexto de retorno; si no, se escriben.
4. El orden de los bounds no importa.
5. Un bound redundante se acepta con warning (`PGS-W3401`), salvo que sea
   necesario para legibilidad.
6. No hay `where` clauses en lambdas; sus tipos se infieren o se anotan en el
   binding.

### 34.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3401` | `where` vacío | eliminarlo |
| `PGS-E3402` | bound no satisfecho | implementar el `pact` o cambiar el tipo |
| `PGS-E3403` | bound sobre un parámetro no declarado | añadirlo a `[T]` |
| `PGS-E3404` | `T: ?Sized` usado por valor | pasar `&T`, `Box[T]` o un puntero |
| `PGS-E3405` | lifetime bound imposible | acortar el préstamo o usar `'static` |
| `PGS-E3406` | bound de tipo asociado mal formado | usar `Pact[Item = Tipo]` |
| `PGS-E3407` | `where` en un `ritual` incompatible con el tipo | alinear los bounds |
| `PGS-W3401` | bound redundante | eliminar o justificar |

### 34.9 Criterios de aceptación

- [x] Bounds en cabecera y `where` son equivalentes.
- [x] Bounds de lifetime y `?Sized` tienen ejemplo.
- [x] Bounds sobre tipos asociados están definidos.
- [x] Supertraits y su implementación están explicados.
- [x] La resolución y los diagnósticos están cubiertos.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
