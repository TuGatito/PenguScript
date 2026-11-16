---

<a id="sec-10"></a>
## 10. Colecciones

### 10.1 Arrays

```pengu
bind numbers: [Int; 3] = [1, 2, 3]
bind zeros = [0; 4]
```

Un array tiene tamaño fijo. `[expr; N]` repite `expr` `N` veces. `N` debe ser
un literal o un `sigil` entero.

```pengu
bind first = numbers[0]
bind last = numbers[2]
```

El índice debe ser `Usize`. Un índice fuera de rango hace panic. Para evitar el
panic se usa `numbers.get(i)`, que devuelve `Option[Int]`.

### 10.2 Slices

```pengu
bind view: &[Int] = &numbers
bind middle = &numbers[1..3]
```

Un slice es una vista. No se copia el contenido. `&mut [T]` permite modificar
la vista, no el tamaño.

```pengu
sum = (values: &[Int]) -> Int
    morph total = 0
    for value in values do
        total = total + value
    total
```

### 10.3 `Vec`

```pengu
morph values = Vec[1, 2, 3]
values.push(4)
bind last = values.pop()
```

| Operación | Firma |
|---|---|
| `Vec.new()` | `() -> Vec[T]` |
| `Vec.with_capacity(n)` | `(Usize) -> Vec[T]` |
| `push` | `(@mut, T) -> Unit` |
| `pop` | `(@mut) -> Option[T]` |
| `insert` | `(@mut, Usize, T) -> Unit` |
| `remove` | `(@mut, Usize) -> T` |
| `retain` | `(@mut, (T) -> Bool) -> Unit` |
| `len` | `(@) -> Usize` |
| `is_empty` | `(@) -> Bool` |
| `get` | `(@, Usize) -> Option[&T]` |
| `sort` | `(@mut) -> Unit` |
| `contains` | `(@, &T) -> Bool` |

`Vec[T]` es el tipo de secuencia dinámica del núcleo. `VecDeque`, `LinkedList`
y `BinaryHeap` viven en `std.collections`.

### 10.4 `Map`

```pengu
morph ages = { "ana": 30, "pengu": 2 }
ages.insert("lua", 5)
bind ana = ages.get("ana") -- Option[&Int]
bind removed = ages.remove("lua") -- Option[Int]
```

Las claves deben ser `Eq + Hash`. El orden de iteración no se garantiza.

| Operación | Firma |
|---|---|
| `Map.new()` | `() -> Map[K, V]` |
| `insert` | `(@mut, K, V) -> Option[V]` |
| `get` | `(@, &K) -> Option[&V]` |
| `get_mut` | `(@mut, &K) -> Option[&mut V]` |
| `remove` | `(@mut, &K) -> Option[V]` |
| `contains_key` | `(@, &K) -> Bool` |
| `len` | `(@) -> Usize` |

No hay `map[key]` en el núcleo. Se usa `get`/`insert` para hacer explícita la
ausencia.

### 10.5 `Set`

```pengu
morph tags = Set["magic", "static"]
tags.insert("sharp")
bind has = tags.contains("magic")
```

`Set[T]` requiere `T: Eq + Hash`. No conserva orden.

### 10.6 Literales

```pengu
bind a = [1, 2, 3]
bind b = Vec[1, 2, 3]
bind c = { "a": 1, "b": 2 }
bind d = Set["a", "b"]
```

Las comas finales están permitidas. Un `{` sin `clave: valor` es un error.

### 10.7 Iteración

```pengu
for value in values do
    print(value)

for (key, value) in ages do
    print("#{key}: #{value}")

for tag in tags do
    print(tag)
```

`for` es la única forma de recorrer una colección en el núcleo. No hay
`iterator`, `map`, `filter` ni `collect` en el lenguaje; esas operaciones son
métodos de `std.iter` cuando se necesitan.

### 10.8 Capacidad y movimiento

`Vec`, `Map`, `Set` y `String` son owned. Al pasarlos a una función se mueven,
salvo que se preste una vista (`&[T]`, `&Str`, `&Map[K, V]`).

```pengu
print_all = (values: &[Int]) -> Unit
    for value in values do
        print(value)

morph values = Vec[1, 2]
print_all(&values)
values.push(3) -- sigue siendo dueño
```

### 10.9 Diagnósticos de colecciones

| Código | Situación |
|---|---|
| `PGS-E3101` | Índice fuera de rango en tiempo de compilación. |
| `PGS-E3102` | `Map` con clave sin `Eq`/`Hash`. |
| `PGS-E3103` | `Set` con elemento sin `Eq`/`Hash`. |
| `PGS-E3104` | `Vec` con tipo no inferido. |
| `PGS-E3105` | Literal de mapa con entrada inválida. |
| `PGS-E3106` | `push` sobre un binding inmutable. |

[↑ Volver al índice](#indice)
