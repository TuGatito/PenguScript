<a id="sec-33-genericos"></a>
## 33. Genéricos

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 5 |
| Rust | Genéricos `<T>`, `PhantomData<T>`, const generics |
| Palabras mágicas | `[T]`, `[const N: Usize]`, `PhantomData` |
| Depende de | §4, §18, §28, §31 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec33_generics.pengu` |

Un **genérico** es un item que se escribe una vez y se especializa para varios
tipos. PenguScript usa `[T]` para declarar parámetros y `Tipo[Arg]` para
aplicarlos. El compilador genera una instancia por combinación de argumentos
(monomorphization), igual que Rust: no hay despacho dinámico implícito ni
boxeo oculto.

### 33.1 Parámetros de tipo

```pengu
rune Pair[A, B]
    first: A
    second: B

bind p = Pair(first: 1, second: "one")
print(p.first)
print(p.second)
```

Rust generado:

```rust
struct Pair<A, B> {
    first: A,
    second: B,
}

fn main() {
    let p = Pair { first: 1, second: "one" };
    println!("{}", p.first);
    println!("{}", p.second);
}
```

Reglas:

1. Los parámetros van entre `[` y `]` inmediatamente después del nombre del
   item: `Pair[A, B]`, `identity[T]`, `pact Convert[T]`.
2. Se permiten en `rune`, `enchanting`, `pact`, funciones nombradas, `ritual` y
   `essence` genérica.
3. En posición de tipo se aplican con `Pair[Int, Str]`; no se usa `::<>`.
4. En expresión, una llamada genérica usa turbofish: `identity[Int](42)`.
   `identity[Int]` sin llamada solo es válido como valor de función ya
   instanciado y debe poder inferirse o anotarse.
5. La inferencia toma los argumentos de los valores y del contexto. Si un
   parámetro no aparece en parámetros ni en el retorno, es error
   (`PGS-E3304`): no hay parámetros “fantasma” sin `PhantomData`.
6. No hay valores por defecto para parámetros de tipo. `rune Box[T = Int]` es
   error (`PGS-E3305`).
7. Los nombres son convencionales: `T`, `U`, `K`, `V`, `A`, `B`. No son
   palabras clave.
8. Un parámetro de tipo no es un valor: no se puede usar en una expresión, solo
   en tipos y en `PhantomData`.

### 33.2 Funciones genéricas

```pengu
identity = [T](value: T) -> T
    value

bind n = identity[Int](42)
bind s = identity[Str]("pengu")
print(n)
print(s)
```

Rust generado:

```rust
fn identity<T>(value: T) -> T {
    value
}

fn main() {
    let n = identity::<i32>(42);
    let s = identity::<&str>("pengu");
    println!("{}", n);
    println!("{}", s);
}
```

Reglas:

1. El turbofish es obligatorio cuando el tipo no se puede inferir; por ejemplo,
   `identity[Int](42)` o `Vec[Int].new()`.
2. Si se infiere, se puede omitir: `identity(42)`.
3. Una función genérica sin argumentos que no permitan inferencia es error
   (`PGS-E3306`).
4. La función es un **item**, no una variable: se puede declarar en el módulo y
   no captura el entorno. Las lambdas genéricas no existen; una lambda puede
   recibir valores de cualquier tipo solo si su tipo se infiere por el contexto.

### 33.3 Structs y enums genéricos

```pengu
enchanting Maybe[T]
    Nothing
    Just(T)

unwrap_or = [T](value: Maybe[T], fallback: T) -> T
    match value
        when Just(x) then x
        when Nothing then fallback

bind value = Just(7)
bind result = unwrap_or[Int](value, 0)
print(result)
```

Rust generado:

```rust
enum Maybe<T> {
    Nothing,
    Just(T),
}

fn unwrap_or<T>(value: Maybe<T>, fallback: T) -> T {
    match value {
        Maybe::Just(x) => x,
        Maybe::Nothing => fallback,
    }
}

fn main() {
    let value = Maybe::Just(7);
    let result = unwrap_or::<i32>(value, 0);
    println!("{}", result);
}
```

Un `rune` genérico sigue las mismas reglas; sus campos pueden usar `T`,
`[T; N]`, `?T`, `&'a T` o cualquier tipo que dependa de los parámetros.

### 33.4 Parámetros de lifetime

```pengu
rune Excerpt['a]
    text: &'a Str

bind s = "pengu"
bind e = Excerpt(text: s)
print(e.text)
```

Rust generado:

```rust
struct Excerpt<'a> {
    text: &'a str,
}

fn main() {
    let s = "pengu";
    let e = Excerpt { text: s };
    println!("{}", e.text);
}
```

Los parámetros de lifetime se mezclan con los de tipo en el mismo corchete:

```pengu
rune Holder['a, T]
    value: &'a T
```

1. `'a` declara un lifetime; no es un tipo y no se puede usar como valor.
2. Los lifetimes se eliden cuando Rust puede inferirlos (§18); si no, se
   escriben.
3. Un lifetime de un `rune` debe usarse en un campo o en `PhantomData`.

### 33.5 Const generics

```pengu
rune Buffer[const N: Usize]
    data: [U8; N]

new = [const N: Usize]() -> Buffer[N]
    Buffer(data: [0; N])

bind b = new[4]()
print(b.data.len())
```

Rust generado:

```rust
struct Buffer<const N: usize> {
    data: [u8; N],
}

fn new<const N: usize>() -> Buffer<N> {
    Buffer { data: [0; N] }
}

fn main() {
    let b = new::<4>();
    println!("{}", b.data.len());
}
```

Reglas:

1. La sintaxis es `[const N: Usize]`. `Usize` es el único tipo permitido; no hay
   const generics de `Bool`, `Char` ni `Str`.
2. `N` es una constante de compile-time; se usa en tipos como `[T; N]`, no en
   expresiones de runtime.
3. La instanciación usa un literal o una constante: `Buffer[16]`, `Buffer[SIZE]`.
4. No se permiten expresiones aritméticas arbitrarias en el argumento
   (`Buffer[N + 1]`) en el subconjunto estable; se calcula una constante auxiliar
   fuera.
5. Un const generic no puede tener bounds de trait; su tipo ya es `Usize`.
6. El compilador genera una instancia por valor de `N` usado.

### 33.6 Genéricos en `ritual`

```pengu
rune Box[T]
    value: T

ritual Box[T]
    get = (@) -> &T
        &@.value

    replace = (@mut, value: T) -> T
        std.mem.replace(&mut @.value, value)

bind b = Box(value: 9)
print(b.get())
print(b.replace(10))
```

Rust generado:

```rust
struct Box<T> {
    value: T,
}

impl<T> Box<T> {
    fn get(&self) -> &T {
        &self.value
    }

    fn replace(&mut self, value: T) -> T {
        std::mem::replace(&mut self.value, value)
    }
}

fn main() {
    let mut b = Box { value: 9 };
    println!("{}", b.get());
    println!("{}", b.replace(10));
}
```

El `ritual` puede añadir bounds que el tipo no tiene, pero no puede quitar los
que el tipo exige. Un `ritual` genérico sin parámetros propios usa los del tipo:
`ritual Box[T]`; un `ritual` de trait usa `ritual Box[T] for Show`.

### 33.7 Monomorphization y costo

PenguScript no tiene genéricos en runtime. Cada uso concreto produce una
especialización:

- `identity[Int]` y `identity[Str]` generan dos funciones.
- El código especializado es zero-cost: no hay tabla de métodos ni boxing.
- El costo es tamaño de binario y tiempo de compilación.
- Para despacho dinámico se usa `dyn Pact` (§35); para evitar el costo de
  monomorphization se puede aceptar `&dyn Pact`.

No hay “generic constants” de runtime ni reflexión de tipos.

### 33.8 `PhantomData`

Un parámetro que no aparece en ningún campo cambia la varianza y la propiedad
del tipo. Para declararlo explícitamente se usa `PhantomData[T]`:

```pengu
rune Tagged[T]
    value: Int
    marker: PhantomData[T]

bind t: Tagged[Str] = Tagged(value: 1, marker: PhantomData)
print(t.value)
```

Rust generado:

```rust
use std::marker::PhantomData;

struct Tagged<T> {
    value: i32,
    marker: PhantomData<T>,
}

fn main() {
    let t: Tagged<&str> = Tagged { value: 1, marker: PhantomData };
    println!("{}", t.value);
}
```

1. `PhantomData[T]` ocupa cero bytes.
2. Sin `PhantomData`, un parámetro no usado es error (`PGS-E3304`).
3. `PhantomData` no se construye con `new`; el valor es el path `PhantomData`.
4. No se permite `PhantomData` para “inventar” un tipo que no participa en la
   API; documenta por qué está.

### 33.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E3301` | parámetro de tipo no declarado | añadirlo a `[T]` |
| `PGS-E3302` | aridad de argumentos incorrecta | ajustar `Tipo[A, B]` |
| `PGS-E3303` | argumento de tipo en posición de valor | usar turbofish o un valor |
| `PGS-E3304` | parámetro no usado ni en campos ni en retorno | usar `PhantomData[T]` o eliminarlo |
| `PGS-E3305` | default de parámetro de tipo | eliminar el default |
| `PGS-E3306` | no se puede inferir el parámetro | escribir `foo[Tipo](...)` |
| `PGS-E3307` | const generic con tipo distinto de `Usize` | usar `Usize` |
| `PGS-E3308` | expresión no constante como argumento const | usar un literal o `sigil` |
| `PGS-W3301` | nombre de parámetro de una sola letra no convencional | usar `T`/`K`/`V` o un nombre claro |

### 33.10 Criterios de aceptación

- [x] La sintaxis `[T]` no colisiona con indexación ni slices.
- [x] Funciones, structs, enums y `ritual` genéricos tienen ejemplo.
- [x] Lifetimes y const generics están definidos.
- [x] `PhantomData` y el parámetro no usado están cubiertos.
- [x] Monomorphization y el costo están explicados.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
