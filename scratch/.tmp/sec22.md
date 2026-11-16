<a id="sec-22-arrays"></a>
## 22. Arrays y slices

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4A |
| Rust | `[T; N]`, `&[T]`, `&mut [T]`, `array` |
| Palabras mágicas | `[`, `]`, `&` |
| Depende de | §2.6, §4, §17 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec22_arrays.pengu` |

Un **array** `[T; N]` tiene longitud fija conocida en compilación y vive en el
stack si no se boxea. Un **slice** `&[T]`/`&mut [T]` es una vista sobre una
secuencia contigua; no posee los elementos y no conoce su longitud en el tipo.

### 22.1 Tipo

| Forma | Significado | Tamaño |
|---|---|---|
| `[T; N]` | array de `N` elementos `T` | `N * size_of::<T>()` |
| `&[T]` | slice compartido | puntero + longitud |
| `&mut [T]` | slice mutable | puntero + longitud |
| `[[T; M]; N]` | array de arrays | `N * M * size_of::<T>()` |

`N` debe ser una constante evaluable (`Usize`). No se puede usar un valor de
runtime como longitud de array; para eso se usa `Vec[T]` (§23).

### 22.2 Literales

```pengu
bind empty: [Int; 0] = []
bind numbers = [1, 2, 3]
bind zeros = [0; 4]
bind grid = [[0; 3]; 2]
```

Forma indentada:

```pengu
bind numbers = [
    10
    20
    30
]
```

Rust generado:

```rust
fn main() {
    let empty: [i32; 0] = [];
    let numbers = [1, 2, 3];
    let zeros = [0; 4];
    let grid = [[0; 3]; 2];
    println!("{}", numbers[0] + zeros[0] + grid[0][0]);
}
```

Reglas:

1. `[a, b, c]` y la forma indentada producen `[T; N]`; `N` es el número de
   elementos.
2. `[expr; N]` repite `expr` `N` veces; `expr` debe ser `Copy` o const.
3. `[]` necesita contexto de tipo; `[Int; 0]` lo aporta.
4. Todos los elementos deben tener el mismo tipo; no hay arrays heterogéneos.
5. La forma indentada no cambia el tipo ni el orden.

### 22.3 Indexación y `get`

```pengu
bind numbers = [10, 20, 30]
print(numbers[0])
print(numbers.get(1).unwrap())
print(numbers.get(9).is_none())
```

Rust generado:

```rust
fn main() {
    let numbers = [10, 20, 30];
    println!("{}", numbers[0]);
    println!("{}", numbers.get(1).unwrap());
    println!("{}", numbers.get(9).is_none());
}
```

Reglas:

1. `array[i]` comprueba bounds en runtime y hace **panic** si `i >= N`
   (`PGS-R2201`). El compilador no puede demostrar todos los índices.
2. `array.get(i)` devuelve `?&T`; `get_mut(i)` devuelve `?&mut T`.
3. `get` es la forma segura cuando el índice viene de datos externos.
4. `len()` devuelve `Usize`; `is_empty()` equivale a `len() == 0`.
5. Un índice negativo no compila; los índices son `Usize`.

### 22.4 Slices

```pengu
bind numbers = [10, 20, 30, 40]
bind middle: &[Int] = &numbers[1..3]
print(middle.len())
print(middle[0])
```

Rust generado:

```rust
fn main() {
    let numbers = [10, 20, 30, 40];
    let middle: &[i32] = &numbers[1..3];
    println!("{}", middle.len());
    println!("{}", middle[0]);
}
```

Reglas:

1. `&array[a..b]` produce `&[T]`; `&mut array[a..b]` produce `&mut [T]`.
2. `a..b` es exclusivo; `a..=b` es inclusivo (§27).
3. El rango debe estar en bounds y en orden; si no, panic.
4. Un slice no puede vivir más que el array/`Vec` que lo respalda (§18).
5. `&array[..]` es el slice completo; `&array[1..]` va hasta el final.

### 22.5 Operaciones de slice

```pengu
bind numbers = [1, 2, 3, 4, 5, 6]
bind (left, right) = numbers.split_at(3)
print(left.len(), right.len())

for chunk in numbers.chunks(2)
    print(chunk.len())

bind window = numbers.windows(3).next().unwrap()
print(window.len())
```

Rust generado:

```rust
fn main() {
    let numbers = [1, 2, 3, 4, 5, 6];
    let (left, right) = numbers.split_at(3);
    println!("{} {}", left.len(), right.len());

    for chunk in numbers.chunks(2) {
        println!("{}", chunk.len());
    }

    let window = numbers.windows(3).next().unwrap();
    println!("{}", window.len());
}
```

Reglas:

1. `split_at(n)` devuelve `(&[T], &[T])`; `split_at_mut(n)` devuelve
   `(&mut [T], &mut [T])`.
2. `chunks(n)` produce slices de tamaño `n`; el último puede ser más corto.
3. `windows(n)` produce ventanas solapadas de tamaño `n`; si `n > len`, no hay
   ventanas.
4. `first()`/`last()` devuelven `?&T`; `first_mut()`/`last_mut()` son mutables.
5. `contains(&x)` requiere `T: PartialEq`.
6. `iter()` produce `&T`; `into_iter()` sobre `[T; N]` produce `T` (Rust 2021+).

### 22.6 Slice mutable

```pengu
morph numbers = [1, 2, 3]
bind part = &mut numbers[1..]
part[0] = 20
print(numbers[1])
```

Rust generado:

```rust
fn main() {
    let mut numbers = [1, 2, 3];
    let part = &mut numbers[1..];
    part[0] = 20;
    println!("{}", numbers[1]);
}
```

Mientras `part` vive, `numbers` no puede leerse ni moverse; el préstamo mutable
es exclusivo (§17). El `print(numbers[1])` ocurre después del último uso de
`part`, así que NLL lo permite.

### 22.7 Arrays multidimensionales

```pengu
bind grid = [
    [1, 2, 3]
    [4, 5, 6]
]
print(grid[1][2])
```

Rust generado:

```rust
fn main() {
    let grid = [[1, 2, 3], [4, 5, 6]];
    println!("{}", grid[1][2]);
}
```

Un array multidimensional es un array de arrays; todas las filas tienen la misma
longitud. Para matrices de tamaño dinámico se usa `Vec[Vec[T]]` o una crate de
álgebra lineal.

### 22.8 Conversiones

| Operación | PenguScript | Rust |
|---|---|---|
| array a slice | `&array[..]` | `&array[..]` |
| slice a array | `array.try_into().unwrap()` | `TryInto` |
| array a `Vec` | `Vec.from(array)` | `Vec::from(array)` |
| `Vec` a slice | `&vec[..]` | `&vec[..]` |
| repetir | `[expr; N]` | `[expr; N]` |
| generar | `array.from_fn(N, f)` | `std::array::from_fn` |

`array.try_into()` falla si la longitud no coincide; el resultado es
`![T; N]`-style `Result<[T; N], _>`. PenguScript exige `unwrap()` o `match`; no
hay conversión implícita de slice a array.

### 22.9 Ejemplo completo

```pengu
bind scores = [
    90
    80
    70
]

bind total = scores[0] + scores[1] + scores[2]
print(total)

bind average = total / scores.len() as Int
print(average)

bind top = &scores[0..2]
print(top.len())
```

Rust generado:

```rust
fn main() {
    let scores = [90, 80, 70];

    let total = scores[0] + scores[1] + scores[2];
    println!("{}", total);

    let average = total / scores.len() as i32;
    println!("{}", average);

    let top = &scores[0..2];
    println!("{}", top.len());
}
```

### 22.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2201` | longitudes de array incompatibles | usar `Vec` o convertir |
| `PGS-E2202` | índice de tipo no entero | usar `Usize` |
| `PGS-E2203` | array sin contexto de tipo | anotar `[T; N]` |
| `PGS-E2204` | slice con rango invertido | corregir `a..b` |
| `PGS-E2205` | array demasiado grande para el stack | usar `Vec`/`Box` |
| `PGS-W2201` | indexación directa con índice externo | usar `get` |
| `PGS-W2202` | slice que retiene un préstamo largo | acortar el scope |

### 22.11 Criterios de aceptación

- [x] `[T; N]`, `&[T]` y `&mut [T]` están diferenciados.
- [x] Literales inline e indentados producen el mismo tipo.
- [x] Indexación, `get` y bounds están explicados.
- [x] Slices, `split_at`, `chunks`, `windows` y `iter` están cubiertos.
- [x] Arrays multidimensionales y conversiones están documentados.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

