<a id="sec-28-structs"></a>
## 28. Structs (`rune`)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4B |
| Rust | `struct` |
| Palabras mágicas | `rune`, `unveil`, `@@derive`, `@@repr` |
| Depende de | §4, §17, §24 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec28_structs.pengu` |

Un **`rune`** es un tipo producto con nombre. Tiene tres formas: nombrada (campos
con nombre), de tupla (campos posicionales) y unitaria (sin campos). Es nominal:
`Point` y `Vector` con los mismos campos son tipos distintos.

### 28.1 Struct nombrada

```pengu
rune Point
    x: Float
    y: Float

bind p = Point(x: 3.0, y: 4.0)
print(p.x)
print(p.y)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    println!("{}", p.x);
    println!("{}", p.y);
}
```

Reglas:

1. La cabecera `rune Nombre` va en una línea; los campos van indentados un nivel.
2. Cada campo es `nombre: Tipo`; no hay valores por defecto.
3. El orden de los campos es el orden de declaración; afecta al layout y al drop.
4. Un `rune` sin campos y sin paréntesis es unitario (§28.3).
5. Los campos son privados por defecto; `unveil` los expone (§28.4).

### 28.2 Struct de tupla

```pengu
rune Pair(Int, Int)
rune UserId(UInt)

bind pair = Pair(1, 2)
bind id = UserId(7)
print(pair.0)
print(id.0)
```

Rust generado:

```rust
struct Pair(i32, i32);
struct UserId(u32);

fn main() {
    let pair = Pair(1, 2);
    let id = UserId(7);
    println!("{}", pair.0);
    println!("{}", id.0);
}
```

Reglas:

1. `rune Nombre(T1, T2, ...)` declara campos posicionales.
2. Se accede con `.0`, `.1`, …; no hay nombres.
3. Los campos de un tuple struct son **privados** en PenguScript; si se necesita
   exponerlos, se usa una struct nombrada con `unveil` por campo. Esto evita una
   sintaxis de visibilidad posicional ambigua (`PGS-E2805`).
4. Un tuple struct de un campo es la forma canónica de **newtype** (§32).
5. Se puede usar en patterns: `when Pair(a, b)`.

### 28.3 Struct unitaria

```pengu
rune Marker
rune Ready

bind marker = Marker
bind ready = Ready
print(marker == Marker)
```

Rust generado:

```rust
#[derive(PartialEq)]
struct Marker;
#[derive(PartialEq)]
struct Ready;

fn main() {
    let marker = Marker;
    let ready = Ready;
    println!("{}", marker == Marker);
}
```

Una struct unitaria es un **ZST** (zero-sized type): no ocupa bytes y se usa como
marcador de tipo, token o estado. `Marker` y `Ready` son tipos distintos aunque
ambos sean ZST.

### 28.4 Visibilidad de campos

```pengu
unveil rune PublicPoint
    unveil x: Float
    y: Float

bind p = PublicPoint(x: 1.0, y: 2.0)
print(p.x)
```

Rust generado:

```rust
pub struct PublicPoint {
    pub x: f64,
    y: f64,
}

fn main() {
    let p = PublicPoint { x: 1.0, y: 2.0 };
    println!("{}", p.x);
}
```

Formas:

| Forma | Efecto | Rust |
|---|---|---|
| sin `unveil` | privado al módulo | campo privado |
| `unveil` | público | `pub` |
| `unveil(tome)` | visible en el tome | `pub(crate)` |
| `unveil(scroll)` | visible en el padre | `pub(super)` |

`unveil` en un campo debe ir al inicio de la línea del campo. No se permite
`unveil` en campos de tuple structs ni en variantes de enum; esas variantes
heredan la visibilidad del tipo contenedor.

### 28.5 Genéricos y `where`

```pengu
rune Holder[T]
    value: T

rune Wrapper[T] where T: Clone
    value: T

bind h = Holder(value: 42)
bind w = Wrapper(value: "pengu")
print(h.value)
print(w.value)
```

Rust generado:

```rust
struct Holder<T> {
    value: T,
}

struct Wrapper<T>
where
    T: Clone,
{
    value: T,
}

fn main() {
    let h = Holder { value: 42 };
    let w = Wrapper { value: "pengu" };
    println!("{}", h.value);
    println!("{}", w.value);
}
```

Reglas:

1. Los parámetros de tipo van entre `[T]` después del nombre.
2. Los bounds pueden ir en la cabecera con `where`, como en funciones.
3. Un `rune` genérico puede tener campos que usan `T`, `[T; N]`, `?T`, etc.
4. La inferencia del parámetro ocurre en el literal o en la anotación.
5. Sin `PhantomData`, un parámetro de tipo no usado es error (`PGS-E2803`).

### 28.6 `@@derive` y `@@repr`

```pengu
@@derive(Clone, Debug, PartialEq)
rune Version
    major: Int
    minor: Int

@@repr(C)
rune Header
    tag: U8
    len: U32

bind v = Version(major: 1, minor: 2)
print(v.clone().major)
print(size_of[Header]())
```

Rust generado:

```rust
#[derive(Clone, Debug, PartialEq)]
struct Version {
    major: i32,
    minor: i32,
}

#[repr(C)]
struct Header {
    tag: u8,
    len: u32,
}

fn main() {
    let v = Version { major: 1, minor: 2 };
    println!("{}", v.clone().major);
    println!("{}", std::mem::size_of::<Header>());
}
```

Reglas:

1. `@@derive(...)` se traduce a `#[derive(...)]`; los traits permitidos son los
   de Rust (`Clone`, `Copy`, `Debug`, `PartialEq`, `Eq`, `PartialOrd`, `Ord`,
   `Hash`, `Default`).
2. `@@derive(Copy)` exige que todos los campos sean `Copy`; `Clone` no implica
   `Copy`.
3. `@@repr(C)`, `@@repr(transparent)`, `@@repr(packed)` y `@@repr(u8/u16/...)`
   se traducen literalmente.
4. `@@repr(packed)` puede producir referencias desalineadas; se documenta en
   §21 y §52.
5. Los atributos van antes del `rune`, en líneas propias; no dentro del cuerpo.

### 28.7 `PhantomData`

```pengu
rune Tagged[T]
    value: Int
    marker: PhantomData[T]

bind tagged: Tagged[Str] = Tagged(value: 1, marker: PhantomData)
print(tagged.value)
```

Rust generado:

```rust
use std::marker::PhantomData;

struct Tagged<T> {
    value: i32,
    marker: PhantomData<T>,
}

fn main() {
    let tagged: Tagged<&str> = Tagged {
        value: 1,
        marker: PhantomData,
    };
    println!("{}", tagged.value);
}
```

`PhantomData[T]` no ocupa espacio; le dice al compilador que `Tagged[T]` “posee”
un `T` a efectos de variance, drop y auto traits. Se usa cuando `T` no aparece en
ningún campo real.

### 28.8 DST y ZST

Un **DST** (dynamically sized type) no tiene tamaño conocido en compilación. El
último campo de una struct puede ser unsized:

```pengu
rune Buffer
    len: Usize
    data: [U8]
```

Rust generado:

```rust
struct Buffer {
    len: usize,
    data: [u8],
}
```

No se puede crear un `Buffer` por valor; se usa detrás de `&Buffer`, `Box[Buffer]`
o `Rc[Buffer]`. El compilador calcula el tamaño del prefijo y guarda la longitud
del DST en el puntero graso.

Un **ZST** es una struct unitaria o una struct con solo campos ZST. No ocupa
espacio, pero conserva identidad de tipo. `PhantomData` es el ZST estándar para
marcar parámetros.

### 28.9 Literales: shorthand y actualización

```pengu
rune Point
    x: Float
    y: Float

bind x = 1.0
bind y = 2.0
bind p = Point(x: x, y: y)
bind moved = Point(x: 3.0, ..p)
print(moved.x)
print(moved.y)
```

Rust generado:

```rust
struct Point {
    x: f64,
    y: f64,
}

fn main() {
    let x = 1.0;
    let y = 2.0;
    let p = Point { x, y };
    let moved = Point { x: 3.0, ..p };
    println!("{}", moved.x);
    println!("{}", moved.y);
}
```

Reglas:

1. `Point(x: x, y: y)` usa **field init shorthand** cuando el nombre del binding
   coincide con el campo; se genera `Point { x, y }`.
2. La sintaxis de actualización es `Point(campo: valor, ..base)`: `..base` va al
   final y copia/mueve los campos no mencionados.
3. `..base` requiere que `base` sea del mismo tipo; los campos movidos no pueden
   usarse después si no son `Copy`.
4. Un literal debe mencionar todos los campos o usar `..base`; no hay defaults.
5. `Point(..)` no es válido como literal; el rest solo aparece con `base`.

### 28.10 Acceso y mutación

```pengu
rune Counter
    value: Int

morph counter = Counter(value: 0)
counter.value += 1
print(counter.value)
```

Rust generado:

```rust
struct Counter {
    value: i32,
}

fn main() {
    let mut counter = Counter { value: 0 };
    counter.value += 1;
    println!("{}", counter.value);
}
```

Un campo se lee con `obj.campo` y se escribe con `obj.campo = valor` si `obj` es
`morph`. La mutabilidad del binding se propaga al campo; no hay campos `mut`
individuales. Para mutabilidad interior se usa `Cell`/`RefCell`/`Mutex` (§20).

### 28.11 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2801` | campo duplicado | eliminar o renombrar |
| `PGS-E2802` | campo faltante en el literal | añadir el campo o `..base` |
| `PGS-E2803` | parámetro de tipo no usado | añadir `PhantomData` |
| `PGS-E2804` | `@@derive` no soportado en el campo | derivar en el `rune` |
| `PGS-E2805` | `unveil` en campo de tuple struct | usar struct nombrada |
| `PGS-E2806` | `..base` no es el último | moverlo al final |
| `PGS-W2801` | struct con muchos campos públicos | revisar encapsulación |
| `PGS-W2802` | `repr(packed)` en API pública | revisar alineación |

### 28.12 Criterios de aceptación

- [x] Structs nombradas, de tupla y unitarias están diferenciadas.
- [x] La visibilidad por campo y sus límites están definidos.
- [x] Genéricos, `where`, `@@derive` y `@@repr` tienen ejemplo.
- [x] `PhantomData`, DST y ZST están cubiertos.
- [x] Shorthand y `..base` están especificados.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

