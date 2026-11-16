<a id="sec-25-mapas"></a>
## 25. Mapas y sets

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 4A |
| Rust | `HashMap<K,V>`, `HashSet<T>`, `BTreeMap<K,V>`, `BTreeSet<T>` |
| Palabras mágicas | `{`, `}`, `:`, `Set[`, `Map[` |
| Depende de | §2.6, §22–§24 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec25_maps.pengu` |

Un **mapa** asocia claves únicas con valores. Un **set** es un mapa sin valores:
solo claves. PenguScript expone las cuatro variantes de Rust con nombres
explícitos; no hay un “mapa por defecto” implícito.

| Tipo | Orden | Inserción | Búsqueda | Uso |
|---|---|---|---|---|
| `HashMap[K,V]` | no | `O(1)` promedio | `O(1)` promedio | uso general |
| `BTreeMap[K,V]` | por clave | `O(log n)` | `O(log n)` | iterar ordenado |
| `HashSet[T]` | no | `O(1)` promedio | `O(1)` promedio | pertenencia |
| `BTreeSet[T]` | por valor | `O(log n)` | `O(log n)` | pertenencia ordenada |

### 25.1 Literales

```pengu
bind ages = {
    "pengu": 3
    "seal": 5
}

bind tags = Set[
    "magic"
    "static"
]
```

Rust generado:

```rust
use std::collections::{HashMap, HashSet};

fn main() {
    let ages = HashMap::from([
        ("pengu", 3),
        ("seal", 5),
    ]);

    let tags = HashSet::from([
        "magic",
        "static",
    ]);

    println!("{} {}", ages.len(), tags.len());
}
```

Reglas:

1. `{ "clave": valor, ... }` produce un `HashMap` por defecto.
2. `Set[valor, ...]` produce un `HashSet` por defecto.
3. Para `BTreeMap`/`BTreeSet` se usa `BTreeMap.from(...)`/`BTreeSet.from(...)` o
   una anotación de tipo; el literal no elige el orden.
4. Las claves deben implementar `Eq + Hash` para `HashMap`/`HashSet`, y `Ord`
   para `BTreeMap`/`BTreeSet`.
5. Claves duplicadas en un literal: gana la última; el compilador avisa
   (`PGS-W2501`).
6. `name: 1` (clave identificador) equivale a `"name": 1`; una clave calculada
   usa `[expr]: valor`.

### 25.2 Inserción, lectura y actualización

```pengu
morph ages = HashMap.new()
ages.insert("pengu", 3)
ages.insert("seal", 5)
ages.insert("pengu", 4)

print(ages.len())
print(ages.get("pengu").unwrap())
print(ages.contains_key("seal"))
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let mut ages = HashMap::new();
    ages.insert("pengu", 3);
    ages.insert("seal", 5);
    ages.insert("pengu", 4);

    println!("{}", ages.len());
    println!("{}", ages.get("pengu").unwrap());
    println!("{}", ages.contains_key("seal"));
}
```

Reglas:

1. `insert(k, v)` devuelve `?V`: el valor anterior si la clave ya existía.
2. `get(&k)` devuelve `?&V`; `get_mut(&k)` devuelve `?&mut V`.
3. `contains_key(&k)` devuelve `Bool`; no inserta.
4. `remove(&k)` devuelve `?V`.
5. `len()` es el número de claves; `is_empty()` equivale a `len() == 0`.
6. `clear()` elimina todas las entradas sin cambiar la capacidad reservada.

### 25.3 `entry`

```pengu
morph counts = HashMap.new()
bind count = counts.entry("a").or_insert(0)
*count += 1
print(counts.get("a").unwrap())
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let mut counts = HashMap::new();
    let count = counts.entry("a").or_insert(0);
    *count += 1;
    println!("{}", counts.get("a").unwrap());
}
```

`entry(k)` devuelve una `Entry`; las operaciones principales son:

| Método | Efecto |
|---|---|
| `or_insert(v)` | inserta `v` si falta; devuelve `&mut V` |
| `or_insert_with(f)` | calcula `v` solo si falta |
| `or_default()` | usa `V::default()` si falta |
| `and_modify(f)` | modifica el valor existente |
| `key()` | devuelve la clave de la entrada |

`entry` evita hacer dos búsquedas (una para `get`, otra para `insert`).

### 25.4 Sets

```pengu
morph tags = Set["magic", "static"]
tags.insert("safe")
tags.remove("static")
print(tags.contains("magic"))
print(tags.len())
```

Rust generado:

```rust
use std::collections::HashSet;

fn main() {
    let mut tags = HashSet::from(["magic", "static"]);
    tags.insert("safe");
    tags.remove("static");
    println!("{}", tags.contains("magic"));
    println!("{}", tags.len());
}
```

Reglas:

1. `insert(x)` devuelve `Bool`: `true` si era nuevo, `false` si ya estaba.
2. `contains(&x)` no modifica.
3. `remove(&x)` devuelve `Bool`.
4. Las operaciones de conjuntos son `union`, `intersection`, `difference` y
   `symmetric_difference`; devuelven iteradores.
5. `is_subset`/`is_superset`/`is_disjoint` comparan dos sets.

### 25.5 Mapas ordenados

```pengu
bind sorted = BTreeMap.from([
    ("b", 2)
    ("a", 1)
    ("c", 3)
])

for (key, value) in sorted
    print(key, value)
```

Rust generado:

```rust
use std::collections::BTreeMap;

fn main() {
    let sorted = BTreeMap::from([
        ("b", 2),
        ("a", 1),
        ("c", 3),
    ]);

    for (key, value) in sorted {
        println!("{} {}", key, value);
    }
}
```

`BTreeMap` itera en orden de clave (`Ord`), no en orden de inserción. Es la
elección cuando se necesita `range(a..b)` o una salida determinista sin ordenar
después.

### 25.6 `Hash` y `Eq`

Para usar una clave en `HashMap`/`HashSet`, el tipo debe implementar `Eq` y
`Hash` de forma coherente: si `a == b`, entonces `hash(a) == hash(b)`. En un
`rune`, se deriva con:

```pengu
@@derive(PartialEq, Eq, Hash)
rune UserId(Int)
```

Reglas:

1. `f64` no implementa `Eq`/`Hash`; no puede ser clave de un `HashMap`.
2. Los tipos con campos mutables no deberían usarse como clave si el hash cambia.
3. `BTreeMap` requiere `Ord`, no `Hash`.
4. Un hasher personalizado se pasa con `HashMap.with_hasher(...)`; el hasher debe
   implementar `BuildHasher`.
5. La coherencia `Eq`/`Hash` es responsabilidad del tipo; el compilador no la
   demuestra.

### 25.7 Indexar vs. `get`

```pengu
bind ages = { "pengu": 3 }
print(ages["pengu"])
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let ages = HashMap::from([("pengu", 3)]);
    println!("{}", ages["pengu"]);
}
```

`map[k]` hace panic si la clave no existe (`PGS-R2501`); `get` devuelve `?V` y
obliga a manejar el caso ausente. En API pública se prefiere `get`; en un
invariante interno demostrado se puede usar `[]`.

### 25.8 Complejidad y elección

| Operación | `HashMap` | `BTreeMap` |
|---|---|---|
| insert | `O(1)` promedio | `O(log n)` |
| get | `O(1)` promedio | `O(log n)` |
| remove | `O(1)` promedio | `O(log n)` |
| iterar ordenado | no | sí |
| rango por clave | no | sí |
| peor caso | `O(n)` | `O(log n)` |

`HashMap` es más rápido en promedio, pero su orden no está especificado y puede
sufrir ataques de colisiones si las claves son adversarias. `BTreeMap` es más
predecible y permite rangos.

### 25.9 Ejemplo completo

```pengu
bind text = "pengu pengu seal"
morph counts = HashMap.new()

for word in text.split_whitespace()
    bind count = counts.entry(word).or_insert(0)
    *count += 1

print(counts.len())
print(counts.get("pengu").unwrap())
```

Rust generado:

```rust
use std::collections::HashMap;

fn main() {
    let text = "pengu pengu seal";
    let mut counts = HashMap::new();

    for word in text.split_whitespace() {
        let count = counts.entry(word).or_insert(0);
        *count += 1;
    }

    println!("{}", counts.len());
    println!("{}", counts.get("pengu").unwrap());
}
```

### 25.10 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E2501` | clave sin `Eq + Hash` | derivar o usar `BTreeMap` |
| `PGS-E2502` | clave sin `Ord` en `BTreeMap` | derivar `Ord` |
| `PGS-E2503` | `map[k]` con clave posiblemente ausente | usar `get`/`entry` |
| `PGS-E2504` | préstamo mutable y lectura simultánea | separar scopes |
| `PGS-E2505` | set con elemento no hashable | cambiar el tipo |
| `PGS-W2501` | clave duplicada en literal | eliminar duplicado |
| `PGS-W2502` | `HashMap` iterado esperando orden | usar `BTreeMap` |

### 25.11 Criterios de aceptación

- [x] Los cuatro tipos de mapa/set están diferenciados.
- [x] Literales inline/indentados y claves identificador están definidos.
- [x] Inserción, `get`, `entry`, `remove` y `contains` están cubiertos.
- [x] `Hash`/`Eq` y la elección `HashMap` vs. `BTreeMap` están explicados.
- [x] Indexar vs. `get` y los diagnósticos están incluidos.
- [x] Todos los ejemplos Rust compilan.

[↑ Volver al índice](#indice)

