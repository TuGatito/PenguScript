<a id="sec-32-aliases-casts"></a>
## 32. Type aliases, newtypes y casts (`essence`)

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4B |
| Rust | `type`, `struct`, `as`, `From`/`Into`, `TryFrom`/`TryInto` |
| Palabras mágicas | `essence`, `rune`, `as`, `curse` |
| Depende de | §4, §19, §28, §31 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec32_casts.pengu` |

PenguScript separa tres ideas que suelen confundirse:

- **Alias** (`essence`): otro nombre para un tipo existente. No crea un tipo
  nuevo ni cambia la coerción.
- **Newtype** (`rune` de un campo): un tipo nominal nuevo con el mismo layout,
  pero sin conversiones implícitas.
- **Cast** (`as`): una conversión explícita, posiblemente lossy, que el
  programador escribe a propósito.

### 32.1 Alias de tipo

```pengu
essence Meters = Float
essence Pair[T] = (T, T)
essence Callback = (Int, Int) -> Int

bind distance: Meters = 3.5
bind point: Pair[Int] = (1, 2)
bind add: Callback = (a: Int, b: Int) => a + b

print(distance)
print(point.0)
print(add(2, 3))
```

Rust generado:

```rust
type Meters = f64;
type Pair<T> = (T, T);
type Callback = fn(i32, i32) -> i32;

fn main() {
    let distance: Meters = 3.5;
    let point: Pair<i32> = (1, 2);
    let add: Callback = |a: i32, b: i32| a + b;

    println!("{}", distance);
    println!("{}", point.0);
    println!("{}", add(2, 3));
}
```

Reglas:

1. `essence Nombre = Tipo` declara un alias.
2. `essence Nombre[T] = Tipo` declara un alias genérico.
3. Un alias no crea un tipo nominal: `Meters` y `Float` son el mismo tipo para
   el compilador.
4. Los alias no pueden ser recursivos (`PGS-E3201`).
5. Un alias puede tener visibilidad: `unveil essence Meters = Float`.
6. Los alias no se pueden usar para implementar traits sobre tipos externos;
   la regla huérfana mira el tipo subyacente (`PGS-E3202`).
7. El alias no cambia el layout ni la representación.

### 32.2 Newtypes

```pengu
rune UserId(UInt)
rune Email(String)

ritual UserId
    value = (@) -> UInt
        @.0

bind id = UserId(7)
print(id.value())
```

Rust generado:

```rust
struct UserId(u32);
struct Email(String);

impl UserId {
    fn value(&self) -> u32 {
        self.0
    }
}

fn main() {
    let id = UserId(7);
    println!("{}", id.value());
}
```

Reglas:

1. Un newtype es un `rune` de tupla con un solo campo.
2. Es un tipo distinto: `UserId` no es `UInt` ni se convierte solo.
3. El campo `.0` existe, pero su visibilidad sigue las reglas de §28 (privado
   fuera del módulo).
4. Para exponer el valor se usa un método (`value`) o `unveil` en el campo
   cuando §28 lo permita.
5. Un newtype puede implementar métodos y traits como cualquier `rune`.
6. Los newtypes son la forma recomendada de dar semántica a un primitivo
   (`UserId`, `Meters`, `Email`) sin costo en runtime.

### 32.3 Casts con `as`

```pengu
bind a: Int = 300
bind b = a as U8
bind f = 3.9
bind i = f as Int
bind c = 'P' as U32

print(b)
print(i)
print(c)
```

Rust generado:

```rust
fn main() {
    let a: i32 = 300;
    let b = a as u8;
    let f = 3.9;
    let i = f as i32;
    let c = 'P' as u32;

    println!("{}", b);
    println!("{}", i);
    println!("{}", c);
}
```

Salida: `44`, `3`, `80`.

Reglas:

1. `as` es explícito y tiene alta precedencia (§11).
2. Los casts numéricos pueden ser lossy: `300 as U8` = `44`; `3.9 as Int` = `3`.
   El compilador avisa cuando el valor es constante y se pierde información
   (`PGS-W3201`).
3. No hay casts implícitos entre tipos numéricos; una suma `Int + Float` es
   error (`PGS-E3203`).
4. Se permite `Bool as Int`, `Char as U32`, `U8 as Char` (solo `U8`), enums
   fieldless a su entero, y punteros a enteros con `curse`.
5. No se permite `as` entre referencias de distinto tipo ni entre structs; para
   eso se usan `From`/`Into` o `transmute` en `curse`.
6. `as` sobre un enum con datos es error (`PGS-E3204`); se usa `match`.
7. Un cast de puntero conserva la dirección, no la validez; es `curse` (§19).

### 32.4 `From`/`Into`

```pengu
bind s = String.from("pengu")
bind t: String = "script".into()

print(s)
print(t)
```

Rust generado:

```rust
fn main() {
    let s = String::from("pengu");
    let t: String = "script".into();

    println!("{}", s);
    println!("{}", t);
}
```

Reglas:

1. `T.from(x)` llama a `From::from`; el tipo destino es `T`.
2. `x.into()` llama a `Into::into`; el tipo destino se infiere del contexto.
3. `From`/`Into` son conversiones **infalibles** y deben conservar la
   información; si puede fallar, se usa `TryFrom`/`TryInto`.
4. Una conversión `From` es la forma preferida para newtypes y tipos propios.
5. No se implementa `From` para conversiones lossy (`PGS-E3205`).

### 32.5 `TryFrom`/`TryInto`

```pengu
bind small: !U8 = U8.try_from(300)

match small
    when ok(value) then print(value)
    when err(_) then print("no cabe")
```

Rust generado:

```rust
fn main() {
    let small: Result<u8, Box<dyn std::error::Error + Send + Sync>> = u8::try_from(300).map_err(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>);

    match small {
        Ok(value) => println!("{}", value),
        Err(_) => println!("no cabe"),
    }
}
```

`TryFrom` devuelve `!T` (`Result<T, Error>`). El error se puede propagar con `?`
(§48). `TryInto` es la forma método: `x.try_into()`.

### 32.6 Coerciones permitidas

PenguScript solo aplica las coerciones que Rust considera seguras y automáticas:

| Desde | Hacia | Condición |
|---|---|---|
| `&[T; N]` | `&[T]` | unsizing de array a slice |
| `&mut [T; N]` | `&mut [T]` | unsizing |
| `&T` | `&dyn Pact` | `T: Pact` |
| `Box[T]` | `Box[dyn Pact]` | `T: Pact` |
| `fn` item | `fn` pointer | función sin captura |
| `!` | cualquier tipo | divergencia |

No se permite coerción implícita entre:

- `Int` y `Float`;
- `String` y `Str` (se usa `.as_str()` o `&s`);
- `T` y `?T` (se usa `some(x)`);
- `T` y `!T` (se usa `ok(x)`);
- dos newtypes distintos;
- `&T` y `&mut T`.

### 32.7 Tipos asociados (avance)

Dentro de un `pact`, `essence Nombre` sin `=` declara un tipo asociado:

```pengu
pact Container
    essence Item

    first = (@) -> ?&Item

rune Numbers
    values: Vec[Int]

ritual Container for Numbers
    essence Item = Int

    first = (@) -> ?&Int
        @.values.first()

bind n = Numbers(values: Vec[1, 2, 3])
print(n.first())
```

Rust generado:

```rust
trait Container {
    type Item;

    fn first(&self) -> Option<&Self::Item>;
}

struct Numbers {
    values: Vec<i32>,
}

impl Container for Numbers {
    type Item = i32;

    fn first(&self) -> Option<&i32> {
        self.values.first()
    }
}

fn main() {
    let n = Numbers { values: vec![1, 2, 3] };
    println!("{:?}", n.first());
}
```

El tipo asociado se proyecta como `Self::Item` en el trait y se fija en cada
implementación. §35 profundiza en asociados y bounds.

### 32.8 `transmute`

`transmute` solo existe dentro de `curse` y exige que origen y destino tengan el
mismo tamaño:

```pengu
curse
    bind bits: U32 = transmute(1.0_f32)
    print(bits)
```

Rust generado:

```rust
fn main() {
    unsafe {
        let bits: u32 = std::mem::transmute(1.0_f32);
        println!("{}", bits);
    }
}
```

Reglas:

1. `transmute` es la última opción; prefiere `as`, `From` o `to_bits`.
2. Origen y destino deben tener el mismo tamaño (`PGS-E3207`).
3. No se permite `transmute` fuera de `curse` (`PGS-E3206`).
4. El resultado puede ser un valor inválido (por ejemplo, un `bool` con bits
   distintos de 0/1); la responsabilidad es del programador.
5. Para punteros se prefiere `cast`/`as` antes que `transmute`.

### 32.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3201` | alias recursivo | romper el ciclo |
| `PGS-E3202` | alias usado para violar coherencia | usar un newtype local |
| `PGS-E3203` | operación entre numéricos distintos | convertir con `as` |
| `PGS-E3204` | `as` sobre enum con datos | usar `match` |
| `PGS-E3205` | `From` lossy | usar `TryFrom` |
| `PGS-E3206` | `transmute` fuera de `curse` | envolver en `curse` |
| `PGS-E3207` | `transmute` con tamaños distintos | usar otra conversión |
| `PGS-E3208` | cast de referencia inválido | usar `From`/`Into` |
| `PGS-W3201` | cast constante con pérdida | revisar el valor |
| `PGS-W3202` | newtype sin constructor validado | añadir `new` con validación |

### 32.10 Criterios de aceptación

- [x] Alias simple y genérico están definidos.
- [x] Newtype y su relación con el tipo subyacente están claros.
- [x] `as` numérico, de puntero y de enum está cubierto.
- [x] `From`/`Into` y `TryFrom`/`TryInto` tienen ejemplo.
- [x] Las coerciones permitidas y prohibidas están tabuladas.
- [x] El avance de tipos asociados es consistente con §35.
- [x] `transmute` solo se permite en `curse`.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

