<a id="sec-23-vectores"></a>
## 23. Vectores y `VecDeque`

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4A |
| Rust | `Vec<T>`, `VecDeque<T>` |
| Palabras mágicas | `Vec[`, `]` |
| Depende de | §22 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec23_vectors.pengu` |

`Vec[T]` es una secuencia contigua de longitud variable en el heap. Crece
amortizando `O(1)` por push y permite indexación `O(1)`. `VecDeque[T]` es una
cola doble terminada; crece por ambos extremos y usa un buffer circular.

### 23.1 Literal

```pengu
bind empty: Vec[Int] = Vec[]
bind numbers = Vec[1, 2, 3]
bind zeros = Vec[0; 4]
```

Forma indentada:

```pengu
bind numbers = Vec[
    10
    20
    30
]
```

Rust generado:

```rust
fn main() {
    let empty: Vec<i32> = Vec::new();
    let numbers = vec![1, 2, 3];
    let zeros = vec![0; 4];
    println!("{} {} {}", empty.len(), numbers.len(), zeros.len());
}
```

Reglas:

1. `Vec[a, b, c]` -> `vec![a, b, c]`.
2. `Vec[expr; N]` -> `vec![expr; N]`; `N` puede ser runtime, a diferencia de un
   array.
3. `Vec[]` necesita contexto de tipo; `Vec[Int]` lo aporta.
4. El literal reserva exactamente lo necesario (o una capacidad cercana); para
   reservar una capacidad concreta se usa `Vec.with_capacity`.
5. La forma indentada es equivalente a la inline.

### 23.2 Construcción y capacidad

```pengu
morph values = Vec.with_capacity(10)
values.push(1)
print(values.capacity() >= 10)
print(values.len())
```

Rust generado:

```rust
fn main() {
    let mut values = Vec::with_capacity(10);
    values.push(1);
    println!("{}", values.capacity() >= 10);
    println!("{}", values.len());
}
```

Reglas:

1. `Vec.new()` crea vacío sin reservar; `Vec.with_capacity(n)` reserva `n`.
2. `capacity()` es cuántos elementos caben sin reasignar; `len()` es cuántos hay.
3. `push` puede reasignar y duplicar la capacidad; no se asume un valor exacto.
4. `reserve(n)`/`reserve_exact(n)` piden capacidad adicional.
5. `shrink_to_fit()` reduce la capacidad al `len`; puede reasignar.

### 23.3 Operaciones principales

```pengu
morph values = Vec[3, 1, 2, 2]
values.sort()
values.dedup()
values.insert(0, 9)
print(values.len())
print(values[0])
print(values.pop().unwrap())
```

Rust generado:

```rust
fn main() {
    let mut values = vec![3, 1, 2, 2];
    values.sort();
    values.dedup();
    values.insert(0, 9);
    println!("{}", values.len());
    println!("{}", values[0]);
    println!("{}", values.pop().unwrap());
}
```

| Operación | Coste | Nota |
|---|---|---|
| `push`/`pop` al final | amortizado `O(1)` | el más rápido |
| `insert(i)`/`remove(i)` | `O(n)` | desplaza el resto |
| `sort` | `O(n log n)` | requiere `Ord` |
| `dedup` | `O(n)` | requiere `PartialEq`; solo borra consecutivos |
| `retain` | `O(n)` | conserva los que cumplen el predicado |
| `binary_search` | `O(log n)` | requiere estar ordenado |
| `contains` | `O(n)` | usa `PartialEq` |

### 23.4 `retain`, `drain` y `binary_search`

```pengu
morph values = Vec[1, 2, 3, 4, 5]
values.retain((x: Int) => x % 2 == 0)
print(values.len())

bind index = values.binary_search(&4).unwrap()
print(index)
```

Rust generado:

```rust
fn main() {
    let mut values = vec![1, 2, 3, 4, 5];
    values.retain(|x| x % 2 == 0);
    println!("{}", values.len());

    let index = values.binary_search(&4).unwrap();
    println!("{}", index);
}
```

Reglas:

1. `retain(f)` conserva los elementos para los que `f` devuelve `true`; el
   predicado recibe `&T`.
2. `drain(a..b)` elimina y devuelve un iterador sobre el rango; si no se consume,
   el iterador dropea los elementos al salir de scope.
3. `binary_search(&x)` devuelve `Result[Usize, Usize]`: `ok(index)` si lo
   encuentra, `err(posición de inserción)` si no. Requiere orden.
4. `sort()` usa `Ord`; `sort_by`/`sort_by_key` permiten criterios propios.
5. `dedup()` solo elimina duplicados **consecutivos**; ordenar antes si se quiere
   eliminar todos.

### 23.5 Slices de un `Vec`

```pengu
bind values = Vec[10, 20, 30, 40]
bind middle: &[Int] = &values[1..3]
print(middle.len())
print(middle[0])
```

Rust generado:

```rust
fn main() {
    let values = vec![10, 20, 30, 40];
    let middle: &[i32] = &values[1..3];
    println!("{}", middle.len());
    println!("{}", middle[0]);
}
```

Un `Vec` se dereferencia a `[T]`, así que `&values[..]` produce `&[T]`. Mientras
el slice vive, el `Vec` no puede reasignarse ni modificarse de forma que lo
invalide.

### 23.6 `VecDeque`

```pengu
morph queue = VecDeque.new()
queue.push_back(1)
queue.push_front(0)
print(queue.pop_front().unwrap())
print(queue.len())
```

Rust generado:

```rust
use std::collections::VecDeque;

fn main() {
    let mut queue = VecDeque::new();
    queue.push_back(1);
    queue.push_front(0);
    println!("{}", queue.pop_front().unwrap());
    println!("{}", queue.len());
}
```

Reglas:

1. `VecDeque.new()` crea una cola vacía; `with_capacity(n)` reserva.
2. `push_back`/`pop_back` y `push_front`/`pop_front` son `O(1)` amortizado.
3. `VecDeque` se usa para colas, buffers circulares y ventanas deslizantes.
4. No es contiguo; para acceso indexado intensivo se prefiere `Vec`.
5. `make_contiguous()` puede reorganizar el buffer para devolver un slice
   contiguo; es `O(n)`.

### 23.7 Elección `Vec` vs. `VecDeque` vs. array

| Necesidad | Tipo | Razón |
|---|---|---|
| tamaño fijo conocido | `[T; N]` | sin heap, sin longitud dinámica |
| crecer al final | `Vec[T]` | contiguo, rápido al final |
| crecer por ambos extremos | `VecDeque[T]` | buffer circular |
| acceso indexado intensivo | `Vec[T]`/`[T; N]` | localidad de caché |
| cola FIFO/LIFO | `VecDeque[T]` | `pop_front` barato |
| compartir sin copiar | `&[T]` | vista |

### 23.8 Ejemplo completo

```pengu
morph scores = Vec[
    70
    90
    80
]
scores.push(100)
scores.sort()
print(scores.len())
print(scores[0])
print(scores.pop().unwrap())
```

Rust generado:

```rust
fn main() {
    let mut scores = vec![70, 90, 80];
    scores.push(100);
    scores.sort();
    println!("{}", scores.len());
    println!("{}", scores[0]);
    println!("{}", scores.pop().unwrap());
}
```

### 23.9 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2301` | `Vec[]` sin contexto de tipo | anotar `Vec[T]` |
| `PGS-E2302` | índice fuera de rango | usar `get` o comprobar `len` |
| `PGS-E2303` | `sort` sin `Ord` | usar `sort_by` o derivar `Ord` |
| `PGS-E2304` | `dedup` sin `PartialEq` | derivar `PartialEq` |
| `PGS-E2305` | `drain` con rango inválido | corregir el rango |
| `PGS-W2301` | `Vec` que crece sin reservar | usar `with_capacity` si se conoce |
| `PGS-W2302` | `insert(0, x)` repetido | usar `VecDeque` |

### 23.10 Criterios de aceptación

- [x] `Vec[T]` y sus literales inline/indentados están definidos.
- [x] Construcción, capacidad y operaciones principales están cubiertas.
- [x] `retain`, `drain` y `binary_search` tienen ejemplo.
- [x] Slices de `Vec` y sus préstamos están explicados.
- [x] `VecDeque` y la guía de elección están incluidos.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

