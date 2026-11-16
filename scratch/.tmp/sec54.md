<a id="sec-54-const-eval"></a>
## 54. Const eval

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 8 |
| Rust | `const`, `const fn`, `const {}`, const generics |
| Palabras mágicas | `sigil`, `eternal`, `relic` |
| Depende de | §6, §18, §33, §52 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec54_const_eval.pengu` |

PenguScript evalúa en compilación todo lo que pueda demostrarse puro. Hay tres
herramientas distintas:

| Herramienta | Declara | Se evalúa | Rust |
|---|---|---|---|
| `sigil` | una constante | en compilación | `const` |
| `eternal` | una función/bloque const | en compilación o runtime | `const fn` / `const {}` |
| `relic` | un static inmutable | inicializador const | `static` |

No hay `const` como palabra clave: `sigil` es el nombre mágico.

### 54.1 `sigil`: constantes

```pengu
sigil LIMIT: Usize = 64
sigil MASK: U64 = (1 << 8) - 1
sigil NAME: Str = "pengu"
```

Rust generado:

```rust
const LIMIT: usize = 64;
const MASK: u64 = (1 << 8) - 1;
const NAME: &str = "pengu";
```

1. `sigil` declara una constante de módulo; no es una variable global.
2. El tipo es explícito; no se infiere en items.
3. El inicializador debe ser una expresión const.
4. `sigil` se puede usar en tipos, arrays, const generics y patrones.
5. `sigil` no se puede reasignar ni tomar `&mut`.
6. `unveil sigil` lo hace visible fuera del módulo.
7. Un `sigil` no tiene dirección estable; para eso se usa `relic`.

### 54.2 `eternal`: funciones const

```pengu
eternal square = (x: Int) -> Int
    x * x

eternal checked = (n: Usize) -> Usize
    if n == 0 then
        panic("zero")
    else
        n
```

Rust generado:

```rust
const fn square(x: i32) -> i32 {
    x * x
}

const fn checked(n: usize) -> usize {
    if n == 0 {
        panic!("zero")
    } else {
        n
    }
}
```

1. `eternal` genera `const fn`; se puede llamar en runtime y en contexto const.
2. El cuerpo solo usa operaciones const.
3. `panic` con un literal es const; el formato con argumentos no lo es.
4. `eternal` no puede ser `dream`, `curse` ni `foreign`.
5. `eternal` puede ser genérico si el trait usado tiene métodos const.
6. La recursión const está limitada por el evaluation limit de rustc.
7. `eternal` no implica `inline`; se combina con `@@inline`.

### 54.3 Bloques `eternal`

```pengu
bind answer = eternal
    square(8) + 1
```

Rust generado:

```rust
const fn square(x: i32) -> i32 {
    x * x
}

let answer = const { square(8) + 1 };
```

1. Un bloque `eternal` evalúa su cuerpo en compilación.
2. El tipo se infiere del contexto.
3. Si el cuerpo no es const, error `PGS-E5401`.
4. Un bloque `eternal` puede usar `sigil` y `eternal` functions.
5. No puede usar heap, I/O, `println` ni aleatoriedad.
6. El bloque no crea un scope de runtime; no hay variables mutables.
7. `eternal` como prefijo de función y como bloque se distinguen por la
   posición: `eternal name = ...` vs `eternal` al inicio de una expresión.

### 54.4 Const generics

```pengu
rune Buffer[const N: Usize]
    data: [U8; N]

bind buf = Buffer[4](data: [0; 4])
```

Rust generado:

```rust
struct Buffer<const N: usize> {
    data: [u8; N],
}

let buf = Buffer::<4> { data: [0; 4] };
```

1. `[const N: Usize]` declara un parámetro const.
2. `N` se usa en tipos de array y en expresiones const.
3. El argumento se escribe `Buffer[4]` (turbofish de tipo).
4. Los const generics no tienen defaults en PenguScript v1.
5. El tipo debe ser entero, `Bool` o `Char`; `Float` no.
6. Las operaciones sobre `N` deben ser const y no desbordar.
7. Un const generic no puede depender de un tipo genérico.

### 54.5 `relic`: statics inmutables

```pengu
relic TABLE: [Int; 3] = [1, 2, 3]
relic START: Int = compute_start()

eternal compute_start = () -> Int
    1
```

Rust generado:

```rust
static TABLE: [i32; 3] = [1, 2, 3];
static START: i32 = compute_start();

const fn compute_start() -> i32 {
    1
}
```

1. `relic` genera `static`, no `const`.
2. El inicializador debe ser const.
3. `relic` tiene dirección estable y vive todo el programa.
4. `relic` es inmutable; no se puede `morph`.
5. `static mut` no existe en PenguScript; se usa `@@shared`.
6. `@@thread_local relic` genera un `thread_local!` con acceso por closure.
7. Un `relic` puede ser `unveil`.

### 54.6 Inicialización perezosa

```pengu
relic CACHE: OnceLock[Int] = OnceLock.new()

grimoire
    CACHE.set(42).unwrap()
    print(CACHE.get().unwrap())
```

Rust generado:

```rust
use std::sync::OnceLock;

static CACHE: OnceLock<i32> = OnceLock::new();

fn main() {
    CACHE.set(42).unwrap();
    println!("{}", CACHE.get().unwrap());
}
```

1. `OnceLock.new()` es const; el valor se inicializa en runtime.
2. `LazyLock.new(|| ...)` inicializa en el primer acceso.
3. `OnceLock` y `LazyLock` no son const-eval; son estado global seguro.
4. `@@shared` sigue siendo la forma de mutabilidad global explícita.
5. Un `relic` normal no se puede mutar; `OnceLock` encapsula la mutación.
6. `LazyLock` puede capturar solo lo que sea `Send + Sync` para un static.
7. La inicialización perezosa no debe esconder efectos costosos.

```rust
use std::sync::LazyLock;

static CONFIG: LazyLock<i32> = LazyLock::new(|| 7);

fn main() {
    println!("{}", *CONFIG);
}
```

### 54.7 Const panic

```rust
const fn checked(n: usize) -> usize {
    if n == 0 {
        panic!("zero")
    } else {
        n
    }
}

fn main() {
    println!("{}", checked(5));
}
```

1. `panic!` con un string literal es const.
2. `panic!` con formato (`{}`) no es const.
3. `assert!` con condición const es const; el mensaje debe ser literal.
4. Una panic const falla la compilación si se evalúa en const.
5. En runtime, una `const fn` que panic se comporta como una panic normal.
6. No se usa `panic` para validar entrada de usuario en const.

### 54.8 Límites de const eval

| Operación | ¿Const? | Nota |
|---|---|---|
| enteros, bools, chars | sí | aritmética y comparaciones |
| floats básicos | sí | sin `sqrt`/`sin` estables |
| arrays, tuples, structs | sí | si sus campos lo son |
| `if`/`match`/`loop`/`while` | sí | sin `for` |
| `panic!` literal | sí | sin formato |
| `size_of`/`align_of` | sí | `std::mem` |
| `transmute` | limitado | mismos tamaños; revisar |
| `Vec`/`String`/`Box` | no | heap |
| `println!`/I/O | no | efectos |
| `dyn Trait` | no | despacho dinámico |
| métodos de trait | no | salvo traits const inestables |
| `for` | no | usar `while`/`loop` |

1. La evaluación const tiene un límite de pasos; un bucle infinito es error.
2. No se permite asignación a memoria heap.
3. No se permite `Drop` no const.
4. No se permite lanzar una panic con formato.
5. Los traits const son inestables; se listan en §66.
6. La evaluación const no debe depender de la plataforma si el valor se usa
   en tipos.
7. Un `sigil` grande aumenta el binario; se prefiere `relic` para datos
   grandes.

### 54.9 `sigil` vs `relic` vs `eternal`

| Necesidad | Usar |
|---|---|
| valor escalar conocido en compilación | `sigil` |
| tabla/array grande con dirección | `relic` |
| función pura reutilizable en const | `eternal` |
| cálculo const local | bloque `eternal` |
| inicialización en runtime | `OnceLock`/`LazyLock` |
| mutabilidad global | `@@shared relic` |

### 54.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E5401` | operación no const en `sigil`/`eternal` | usar una operación const |
| `PGS-E5402` | `static mut` | `@@shared` + `Mutex` |
| `PGS-E5403` | const generic inválido | usar entero/`Bool`/`Char` |
| `PGS-E5404` | heap en const | mover a runtime |
| `PGS-E5405` | `panic!` con formato | usar literal |
| `PGS-E5406` | recursión const infinita | añadir caso base |
| `PGS-E5407` | `?` en const | usar `match`/`if` |
| `PGS-W5401` | `sigil` muy grande | usar `relic` |
| `PGS-W5402` | `sigil` que debería ser `eternal` | extraer función |

### 54.11 Criterios de aceptación

- [x] `sigil`, `eternal` y `relic` están diferenciados.
- [x] Los const generics y los bloques const están definidos.
- [x] La tabla de límites const es explícita.
- [x] `static mut` está prohibido.
- [x] `OnceLock`/`LazyLock` se distinguen de const eval.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
