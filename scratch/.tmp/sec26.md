<a id="sec-26-estructuras-datos"></a>
## 26. Otras estructuras de datos

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4A |
| Rust | `VecDeque`, `LinkedList`, `BinaryHeap`, `BTreeSet` |
| Palabras mágicas | — |
| Depende de | §22–§25 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec26_structures.pengu` |

Este capítulo cubre las estructuras de la biblioteca estándar que no son
arrays, `Vec`, tuplas, mapas ni sets. Ninguna es “mejor” en abstracto: la
elección depende del patrón de acceso y de la complejidad que se necesita.

### 26.1 `VecDeque`

`VecDeque[T]` es una cola doble terminada con buffer circular. `push_front`,
`push_back`, `pop_front` y `pop_back` son `O(1)` amortizado.

```pengu
morph queue = VecDeque.new()
queue.push_back(1)
queue.push_back(2)
queue.push_front(0)

print(queue.pop_front().unwrap())
print(queue.pop_back().unwrap())
print(queue.len())
```

Rust generado:

```rust
use std::collections::VecDeque;

fn main() {
    let mut queue = VecDeque::new();
    queue.push_back(1);
    queue.push_back(2);
    queue.push_front(0);

    println!("{}", queue.pop_front().unwrap());
    println!("{}", queue.pop_back().unwrap());
    println!("{}", queue.len());
}
```

Usos: colas FIFO/LIFO, buffers circulares, ventanas deslizantes, planificadores.
No es contiguo; si se necesita un slice, `make_contiguous()` es `O(n)`.

### 26.2 `LinkedList`

`LinkedList[T]` es una lista doblemente enlazada. Insertar/eliminar en los
extremos es `O(1)`, pero acceder por índice es `O(n)` y cada nodo es una
asignación separada.

```pengu
morph list = LinkedList.new()
list.push_back(2)
list.push_front(1)
list.push_back(3)

print(list.len())
print(list.front().unwrap())
print(list.back().unwrap())
```

Rust generado:

```rust
use std::collections::LinkedList;

fn main() {
    let mut list = LinkedList::new();
    list.push_back(2);
    list.push_front(1);
    list.push_back(3);

    println!("{}", list.len());
    println!("{}", list.front().unwrap());
    println!("{}", list.back().unwrap());
}
```

En la práctica `LinkedList` se usa poco: `Vec`/`VecDeque` suelen ganar por
localidad de caché. Es útil para splicing frecuente si ya se tiene un cursor,
pero la API de Rust no expone cursores estables.

### 26.3 `BinaryHeap`

`BinaryHeap[T]` es un max-heap: `peek()`/`pop()` devuelven el mayor elemento.
Requiere `T: Ord`.

```pengu
morph heap = BinaryHeap.new()
heap.push(3)
heap.push(1)
heap.push(5)

print(heap.peek().unwrap())
print(heap.pop().unwrap())
print(heap.len())
```

Rust generado:

```rust
use std::collections::BinaryHeap;

fn main() {
    let mut heap = BinaryHeap::new();
    heap.push(3);
    heap.push(1);
    heap.push(5);

    println!("{}", heap.peek().unwrap());
    println!("{}", heap.pop().unwrap());
    println!("{}", heap.len());
}
```

Para un min-heap se envuelve el valor en `Reverse`:

```pengu
morph min_heap = BinaryHeap.new()
min_heap.push(Reverse(3))
min_heap.push(Reverse(1))
print(min_heap.pop().unwrap().0)
```

Rust generado:

```rust
use std::cmp::Reverse;
use std::collections::BinaryHeap;

fn main() {
    let mut min_heap = BinaryHeap::new();
    min_heap.push(Reverse(3));
    min_heap.push(Reverse(1));
    println!("{}", min_heap.pop().unwrap().0);
}
```

Usos: colas de prioridad, Dijkstra, `k` elementos mayores/menores, simulaciones
de eventos. `BinaryHeap` no es estable: elementos iguales pueden salir en
cualquier orden.

### 26.4 `BTreeSet`

`BTreeSet[T]` es un set ordenado; iterar produce los elementos en orden `Ord`.
Es la contraparte de `HashSet` cuando se necesita orden o rangos.

```pengu
bind values = BTreeSet.from([3, 1, 2])

for value in values
    print(value)
```

Rust generado:

```rust
use std::collections::BTreeSet;

fn main() {
    let values = BTreeSet::from([3, 1, 2]);

    for value in values {
        println!("{}", value);
    }
}
```

### 26.5 Comparación de complejidades

| Estructura | Acceso por índice | Inserción al final | Inserción al inicio | Búsqueda | Orden |
|---|---|---|---|---|---|
| `[T; N]` | `O(1)` | — | — | `O(n)` | no |
| `Vec[T]` | `O(1)` | `O(1)` amort. | `O(n)` | `O(n)` | no |
| `VecDeque[T]` | `O(1)` | `O(1)` amort. | `O(1)` amort. | `O(n)` | no |
| `LinkedList[T]` | `O(n)` | `O(1)` | `O(1)` | `O(n)` | no |
| `BinaryHeap[T]` | — | `O(log n)` | — | `O(n)` | parcial |
| `HashMap[K,V]` | — | `O(1)` prom. | — | `O(1)` prom. | no |
| `BTreeMap[K,V]` | — | `O(log n)` | — | `O(log n)` | sí |
| `HashSet[T]` | — | `O(1)` prom. | — | `O(1)` prom. | no |
| `BTreeSet[T]` | — | `O(log n)` | — | `O(log n)` | sí |

### 26.6 Crates externas

La biblioteca estándar no cubre todos los casos. Algunas alternativas comunes
(no forman parte del lenguaje; se declaran en `Tome.toml`):

| Crate | Estructura | Cuándo |
|---|---|---|
| `indexmap` | `IndexMap`/`IndexSet` | orden de inserción + búsqueda hash |
| `smallvec` | `SmallVec` | pocos elementos sin heap |
| `arrayvec` | `ArrayVec` | capacidad fija sin heap |
| `dashmap` | `DashMap` | concurrencia con sharding |
| `crossbeam` | colas | MPSC/MPMC |
| `petgraph` | grafos | algoritmos de grafos |
| `slotmap` | slots | claves estables con reuso |

Regla: una estructura externa debe justificar su dependencia; si la API pública
la expone, se documenta en el `pact` correspondiente para no acoplar a los
usuarios a la crate.

### 26.7 Ejemplo completo

```pengu
morph tasks = BinaryHeap.new()
tasks.push(2)
tasks.push(5)
tasks.push(1)

print(tasks.pop().unwrap())
print(tasks.pop().unwrap())
print(tasks.pop().unwrap())
```

Rust generado:

```rust
use std::collections::BinaryHeap;

fn main() {
    let mut tasks = BinaryHeap::new();
    tasks.push(2);
    tasks.push(5);
    tasks.push(1);

    println!("{}", tasks.pop().unwrap());
    println!("{}", tasks.pop().unwrap());
    println!("{}", tasks.pop().unwrap());
}
```

### 26.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2601` | `BinaryHeap` con tipo sin `Ord` | derivar `Ord` o usar `Reverse` |
| `PGS-E2602` | índice en `LinkedList` | usar `Vec`/`VecDeque` |
| `PGS-E2603` | `VecDeque` usado como slice | `make_contiguous()` |
| `PGS-E2604` | estructura externa sin dependencia | añadir a `Tome.toml` |
| `PGS-W2601` | `LinkedList` para acceso secuencial | preferir `Vec`/`VecDeque` |
| `PGS-W2602` | `BinaryHeap` esperando orden estable | añadir un contador de desempate |

### 26.9 Criterios de aceptación

- [x] `VecDeque`, `LinkedList`, `BinaryHeap` y `BTreeSet` están cubiertos.
- [x] Cada estructura tiene ejemplo Rust compilable.
- [x] La tabla de complejidades está incluida.
- [x] Las crates externas y su justificación están documentadas.
- [x] Los diagnósticos distinguen errores de rendimiento.

[↑ Volver al índice](#indice)

