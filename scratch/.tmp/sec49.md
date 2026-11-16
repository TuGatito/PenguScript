<a id="sec-49-iteradores"></a>
## 49. Iteradores

| Campo | Valor |
|---|---|
| Estado | `revisión` |
| Fase | 7 |
| Rust | `Iterator`, `IntoIterator`, adaptadores |
| Palabras mágicas | `iter`, `iter_mut`, `into_iter` |
| Depende de | §14, §22–§27, §35, §38 |
| Ejemplos ejecutables | `sí` — `scratch/examples/sec49_iterators.pengu` |

Un iterador produce una secuencia de valores de forma perezosa. Los adaptadores
construyen una nueva secuencia; los consumidores la recorren y producen un
resultado. Un `for` es azúcar sobre `IntoIterator`.

### 49.1 `Iterator` e `IntoIterator`

| Forma | Produce | Rust |
|---|---|---|
| `collection.iter()` | referencias `&T` | `iter()` |
| `collection.iter_mut()` | referencias `&mut T` | `iter_mut()` |
| `collection.into_iter()` | valores `T` | `into_iter()` |
| `for x in collection` | valores o referencias según `IntoIterator` | `for` |
| `for x in collection.iter()` | referencias | `for` |

1. `Iterator` tiene un método `next() -> ?Item`.
2. `IntoIterator` convierte un valor en un iterador.
3. `for x in array` consume el array si sus elementos no son `Copy`; para
   conservarlo se usa `.iter()`.
4. `iter_mut` requiere un binding `morph` y produce préstamos mutables.
5. Un iterador no se reutiliza después de consumirse; se crea otro.

```pengu
values = [1, 2, 3]

grimoire
    for value in values.iter()
        print(value)

    morph mutable = [1, 2, 3]
    for value in mutable.iter_mut()
        *value *= 2

    print(mutable)
```

Rust generado:

```rust
fn main() {
    let values = [1, 2, 3];

    for value in values.iter() {
        println!("{}", value);
    }

    let mut mutable = [1, 2, 3];
    for value in mutable.iter_mut() {
        *value *= 2;
    }

    println!("{:?}", mutable);
}
```

### 49.2 Adaptadores

| Adaptador | Efecto | Ejemplo |
|---|---|---|
| `map` | transforma cada elemento | `xs.iter().map((x: &Int) => *x * 2)` |
| `filter` | conserva los que cumplen | `xs.iter().filter((x: &&Int) => **x > 0)` |
| `filter_map` | filtra y transforma | `xs.iter().filter_map((x: &&Int) => some(**x))` |
| `flat_map` | aplana el resultado | `xs.iter().flat_map((x: &&Int) => [**x, **x])` |
| `flatten` | aplana un iterador de iteradores | `nested.iter().flatten()` |
| `fold` | acumula con estado | `xs.iter().fold(0, (acc: Int, x: &Int) => acc + *x)` |
| `reduce` | acumula sin estado inicial | `xs.iter().reduce((a: &Int, b: &Int) => a + b)` |
| `scan` | acumula y emite | `xs.iter().scan(0, (acc: &mut Int, x: &Int) => ...)` |
| `take` | primeros `n` | `xs.iter().take(2)` |
| `skip` | omite `n` | `xs.iter().skip(2)` |
| `take_while` | mientras se cumpla | `xs.iter().take_while((x: &Int) => **x < 3)` |
| `skip_while` | omite mientras se cumpla | `xs.iter().skip_while((x: &Int) => **x < 3)` |
| `chain` | concatena | `a.iter().chain(b.iter())` |
| `zip` | empareja | `a.iter().zip(b.iter())` |
| `enumerate` | añade índice | `xs.iter().enumerate()` |
| `peekable` | permite `peek` | `xs.iter().peekable()` |
| `rev` | invierte | `xs.iter().rev()` |
| `cycle` | repite infinitamente | `xs.iter().cycle()` |
| `inspect` | observa sin consumir | `xs.iter().inspect((x: &Int) => print(x))` |
| `step_by` | cada `n` | `xs.iter().step_by(2)` |
| `fuse` | termina tras el primer `none` | `xs.iter().fuse()` |

1. Los adaptadores son perezosos: no ejecutan nada hasta un consumidor.
2. Cada adaptador devuelve un tipo distinto; no se guarda en una variable sin
   `impl Iterator` o `Box<dyn Iterator>`.
3. `map`/`filter` reciben referencias si el iterador es `.iter()`.
4. `filter_map` usa `?T`; `flatten` requiere un iterador de iteradores.
5. `scan` recibe el estado por referencia mutable.
6. `cycle` es infinito; se combina con `take`.
7. `rev` requiere `DoubleEndedIterator`.
8. `inspect` es para depuración, no para efectos secundarios de negocio.

### 49.3 Consumidores

| Consumidor | Resultado |
|---|---|
| `collect` | colección o `Result`/`Option` |
| `sum` | suma |
| `product` | producto |
| `min` / `max` | `?T` |
| `count` | `Usize` |
| `any` / `all` | `Bool` |
| `find` | `?T` |
| `position` | `?Usize` |
| `partition` | dos colecciones |
| `unzip` | dos colecciones |
| `for_each` | `Unit` |

```pengu
values = [1, 2, 3, 4, 5]

bind doubled = values.iter().map((x: &Int) => *x * 2).collect[Vec[Int]]()
bind total = values.iter().sum[Int]()
bind first_even = values.iter().find((x: &&Int) => **x % 2 == 0)
bind (evens, odds) = values.iter().partition((x: &&Int) => **x % 2 == 0)

print(doubled)
print(total)
print(first_even)
print(evens)
print(odds)
```

Rust generado:

```rust
fn main() {
    let values = [1, 2, 3, 4, 5];

    let doubled: Vec<i32> = values.iter().map(|x| *x * 2).collect();
    let total: i32 = values.iter().sum();
    let first_even = values.iter().find(|x| **x % 2 == 0);
    let (evens, odds): (Vec<&i32>, Vec<&i32>) =
        values.iter().partition(|x| **x % 2 == 0);

    println!("{:?}", doubled);
    println!("{}", total);
    println!("{:?}", first_even);
    println!("{:?}", evens);
    println!("{:?}", odds);
}
```

1. `collect` necesita el tipo de destino; se usa turbofish
   `collect[Vec[Int]]()`.
2. `collect` también puede producir `Result[Vec[T], E]` si el iterador es de
   `Result`.
3. `sum`/`product` necesitan un tipo numérico concreto.
4. `min`/`max` devuelven `?T`; no hay valor por defecto.
5. `partition` requiere anotar el tipo de las dos colecciones si no se infiere.
6. `unzip` separa pares en dos colecciones.
7. `for_each` se usa por efectos secundarios; un `for` suele ser más claro.

### 49.4 Iteradores custom

```pengu
rune Counter
    current: Int

ritual Iterator for Counter
    essence Item = Int

    next = (@mut) -> ?Int
        if @.current >= 3
            none
        else
            bind value = @.current
            @.current += 1
            some(value)
```

Rust generado:

```rust
struct Counter {
    current: i32,
}

impl Iterator for Counter {
    type Item = i32;

    fn next(&mut self) -> Option<i32> {
        if self.current >= 3 {
            None
        } else {
            let value = self.current;
            self.current += 1;
            Some(value)
        }
    }
}
```

1. Un iterador custom implementa `Iterator` y declara `Item`.
2. `next` recibe `@mut` y devuelve `?Item`.
3. El estado vive en el `rune`; no se usan generadores ni `yield`.
4. `size_hint` es opcional; si se omite, se usa el default.
5. Un iterador que termina y luego vuelve a producir viola el contrato; `fuse`
   lo protege.
6. Para un iterador que presta datos, el lifetime se declara en el `rune`
   (§18).

### 49.5 `impl Iterator`

```pengu
evens = (limit: Int) -> impl Iterator[Item = Int]
    (0..limit).filter((x: &Int) => *x % 2 == 0)
```

Rust generado:

```rust
fn evens(limit: i32) -> impl Iterator<Item = i32> {
    (0..limit).filter(|x| *x % 2 == 0)
}
```

1. `impl Iterator[Item = T]` oculta el tipo concreto y conserva el contrato.
2. No se puede devolver `impl Iterator` con dos tipos concretos distintos; para
   eso se usa `Box<dyn Iterator<Item = T>>`.
3. `impl Trait` en retorno es monomórfico y de coste cero.
4. El llamador no puede nombrar el tipo, pero puede recorrerlo.
5. Si el iterador presta datos, el lifetime debe aparecer en la firma.

### 49.6 `DoubleEndedIterator`, `ExactSizeIterator`, `FusedIterator`

| Trait | Permite | Ejemplo |
|---|---|---|
| `DoubleEndedIterator` | `next_back`, `rev` | `vec.iter().rev()` |
| `ExactSizeIterator` | `len` exacto | `array.iter().len()` |
| `FusedIterator` | `next` sigue devolviendo `none` | `iter.fuse()` |

1. `rev` solo existe si el iterador es `DoubleEndedIterator`.
2. `len` solo es exacto si el iterador es `ExactSizeIterator`.
3. `FusedIterator` es una garantía, no un adaptador; `fuse` la produce.
4. Un `filter` no es `ExactSizeIterator`; no se usa `len` para saber cuántos
   quedan.
5. Estas traits son marcadores: no cambian la lógica, solo habilitan métodos.

### 49.7 Pereza y comprehensions

Una comprensión produce una colección de inmediato:

```pengu
bind squares = [x * x for x in 0..5]
```

Un iterador es perezoso:

```pengu
bind squares = (0..5).map((x: Int) => x * x)
```

1. La comprensión es azúcar para un bucle que construye una colección; se
   evalúa al crearse.
2. El iterador no se evalúa hasta `collect`, `sum`, `for`, etc.
3. No se mezclan: `[x for x in iter]` consume el iterador; `iter.map(...)` no.
4. Una comprensión no puede ser infinita; un iterador sí (`cycle`).
5. Para depurar pereza, se usa `inspect`.

### 49.8 Diagnósticos

| Código | Situación | Solución |
|---|---|---|
| `PGS-E4901` | `for` sobre un valor no iterable | usar `.iter()`/`IntoIterator` |
| `PGS-E4902` | `iter_mut` sin binding `morph` | declarar `morph` |
| `PGS-E4903` | `collect` sin tipo de destino | añadir turbofish |
| `PGS-E4904` | `rev` sin `DoubleEndedIterator` | usar `collect` + `rev` |
| `PGS-E4905` | `len` en iterador no exacto | contar con `count` |
| `PGS-E4906` | adaptador que no se consume | añadir consumidor |
| `PGS-E4907` | `?` dentro de `map` sin `Result` | usar `filter_map`/`collect` |
| `PGS-W4901` | `cycle` sin `take` | limitar |
| `PGS-W4902` | `for_each` con lógica compleja | usar `for` |

### 49.9 Criterios de aceptación

- [x] `Iterator`/`IntoIterator` y las tres formas de iterar están definidos.
- [x] La tabla de adaptadores y consumidores está completa.
- [x] Los iteradores custom y `impl Iterator` tienen ejemplo.
- [x] La diferencia con comprehensions es explícita.
- [x] Los ejemplos Rust compilan.

[↑ Volver al índice](#indice)
