# std.tally

> Source: `std/tally.pengu`

std/tally.pengu — algorithms over lists: reductions, search, statistics,
sorting, selection, filtering and transformation, with a **generic** API
(`T: Num`, `T: Ordered`, `T: Par`, `T: Integrum`, `T: Donum`) and 100%
compatibility with the concrete `list of int` API of 0.14.x-2.1.0.

Every operation exists twice: as a method (`calling xs.sum`) and as a module
function (`calling sum with xs`). Both are generic now: the methods
live in `enchanting list of shard T where T: ...` blocks and the module
functions carry their own `where` clause, so `tally.sum` accepts
`list of int`, `list of float`, `list of i64`, `list of string` or a list of
any bound `seal`/`rune`. Every module function is **self-contained**: a
generic body never delegates to another generic weave/method.

## Example
```pengu
import std.tally

weave main into int:
    var xs as list of int is [3, 1, 2]
    var total as int is calling xs.sum
    var biggest as int is calling max_val with xs
    var evens as list of int is calling xs.filter_even
    var floats as list of float is [1.5, 0.5]
    var fsum as float is calling floats.sum
    var words as list of string is ["a", "c", "b"]
    var first_word as string is calling min_val with words
    return 0
```

## Memory
No operation mutates or frees the input list: it is only read (`essence of
self`) and the result is either a scalar or a **new list** that the caller
releases with `banish`. Input lists always belong to the caller. The
`## ## Memoria` note of an individual symbol repeats this where forgetting it
is easy.

## Relationship with std.loom
`std.tally` and `std.loom` both operate on lists and share 15 public names,
but they are **two deliberate contracts, not duplicates**:

- `tally` is the **sentinel** family: an empty list collapses to a natural
  identity (`sum` -> 0, `product` -> 1, `max_val` -> the `donum T` sentinel,
  `mode` -> `donum T`) and fractional statistics truncate to `T`
  (`calling xs.mean` on `[1, 2]` gives `1`). Reach for it when the sentinel is
  meaningful and no branching is wanted.
- `loom` is the **safe** family: `loom.mean` returns `float` (`1.5`) and
  `loom.median`/`loom.mode`/`loom.min_max` return `maybe` for an empty list.
  Reach for it when an empty list has no answer, because a sentinel would hide
  a bug.

The split is a **documented, named exception**: `LANGUAGE.md` §19.1.1 defines
it and §15 of `PenguScriptGuideSpanish.md` records it as a relaxed rule with a
named exception. The two families are neither merged nor renamed, and no alias
or suffix bridges them: the 15 shared names keep their different signatures on
purpose.

## Design notes
- **Generics in both forms.** A method cannot carry `where`: the bounds live
  in the `enchanting list of shard T where T: ...` blocks. A module function
  does carry one (`weave sum shard T where T: Num with l as list of T into
  T`), which is what widens `calling sum with xs` beyond `list of int`.
- **Ordering goes through `std.atlas`.** `>` does not compile for
  `PenguString`, so every order comparison uses the `Ordered` concept of
  `std.atlas` (`calling x.cmp with m`, returning 0, -1 or 1) and the block or
  `where` clause asks for `T: Ordered`. Equality is generic, so the
  `Par`-bounded operations need no concept.
- **No calls between generics.** A generic body cannot call another generic
  `weave`/method (the compiler emits the `_T` template), so every generic
  function and method is self-contained and the aliases (`argmin`, `average`,
  `dedup`, `filter_range`, `group_count`) repeat the base body.
- **Building generic lists.** Inside a generic body `push`/`pop` on
  `list of T` is not reliable: new lists come from comprehensions, and
  index-based work uses a local `list of int` (`var` plus concrete `push`)
  walked by another comprehension.
- **`at_or` and `clamp_all`** keep their `int` defaults (`default as int is
  0`, `lo as int is 0`, `hi as int is 100`), because a generic parameter
  accepts no `T`-dependent default. The widened forms are the separate
  `at_or_shard` and `clamp_all_shard`, whose defaults are explicit.
- **No tuples.** `min_max`, `enumerate_pairs` and `partition_by` return
  `list of int`/`list of list of int` to avoid depending on `std.oracle`;
  `min_max` is generic over `T` and `enumerate_pairs`/`partition_by` stay
  concrete because one of their components is an `int` index or an
  `int`-typed predicate.
- **No real `@deprecated`.** The aliases are ordinary `weave`s whose docstring
  starts with `## @deprecated Use X instead.`
- **Internal tests.** The `_expect*` harness uses `spark.panic`, so the module
  keeps its `std.spark`/`std.atlas` dependencies: importing `std.ward` (which
  pulls `std.oracle`) only for tests would load it into every program that
  uses `tally`.

## Migration
| Version | API |
|---|---|
| 0.14.x | concrete `calling sum with xs`, `calling xs.sum` |
| 2.1.0 | same, plus `zip_with`, `chunk`, `windowed`, `running_sum`, `scan_left` |
| 2.1.0 | same, plus `partition_by`, `enumerate_pairs`, `min_max` |
| 2.1.0 | same, plus `frequencies`, `group_count` |
| 2.2.0 | every module function widened to `list of shard T`; `at_or_shard` and `clamp_all_shard` added; the `int` signatures of `at_or` and `clamp_all` are unchanged |

---

### `TALLY_VERSION`

> **TALLY_VERSION** : string

 Version of the `tally` module.

### `first`

> **first**() -> T

 First element of `self`, or `donum T` when `self` is empty.

 ## Parámetros
 - None: the receiver is the list to read.

 ## Retorno
 The first element as `T`, or `donum T` (0 for `int`) when the list is
 empty. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.first    # 3
 ```

### `last`

> **last**() -> T

 Last element of `self`, or `donum T` when `self` is empty.

 ## Parámetros
 - None: the receiver is the list to read.

 ## Retorno
 The last element as `T`, or `donum T` when the list is empty. Borrows the
 receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.last    # 2
 ```

### `is_shared`

> **is_shared**() -> bool

 Element at `idx`, or `maybe none` when `idx` is out of range.

 ## Parámetros
 - `idx`: zero-based position. Negative, or `>= len`, yields `none`.

 ## Retorno
 `some v` with the element, or `maybe none`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.at_safe with 2    # some 2
 calling xs.at_safe with 9    # none
 ```
 `true` si el búfer de `self` lo comparte otro binding (COW).

 ## Retorno
 `false` mientras el búfer sea exclusivo. Es un diagnóstico: el
 compilador decide solo cuándo clonar.

 ## Ejemplo
 ```pengu
 var a as list of int is [1]
 var b as list of int is a
 calling a.is_shared    # true
 ```

### `ref_count`

> **ref_count**() -> int

 Número de bindings que comparten el búfer de `self` (COW).

 ## Retorno
 `1` si el búfer es exclusivo; `0` si no hay búfer. Diagnóstico.

### `make_unique`

> **make_unique**() -> void

 Fuerza que el búfer de `self` sea exclusivo, clonándolo si hace falta.

 ## Retorno
 Nada. Tras la llamada, `is_shared` es `false`. El coste es O(n) solo
 cuando el búfer estaba compartido.

 ## Ejemplo
 ```pengu
 var a as list of int is [1]
 var b as list of int is a
 calling b.make_unique
 ```

### `at_safe`

> **at_safe**(idx: int) -> maybe T

_Undocumented._

### `reverse`

> **reverse**() -> list of T

 Copy of `self` with the elements in reverse order.

 ## Parámetros
 - None: the receiver is copied and reversed.

 ## Retorno
 A new owned `list of T`; release it with `banish`. `self` is not mutated.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.reverse    # [2, 1, 3]
 ```

### `flatten`

> **flatten**() -> list of T

 Identity copy of `self`; flattens one level of logical nesting.

 ## Parámetros
 - None: the receiver is copied element by element.

 ## Retorno
 A new owned `list of T` with the same elements; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.flatten    # [3, 1, 2]
 ```

### `take`

> **take**(n: int) -> list of T

 First `n` elements of `self`, clipped to its length.

 ## Parámetros
 - `n`: how many elements to take; defaults to 1. Negative values are
   clamped to 0 and values above the length to the length.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.take with 2    # [3, 1]
 ```

### `drop`

> **drop**(n: int) -> list of T

 Elements of `self` from index `n` onwards.

 ## Parámetros
 - `n`: first index to keep; defaults to 1. Negative values are clamped
   to 0.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.drop with 1    # [1, 2]
 ```

### `slice_list`

> **slice_list**(start: int, end_idx: int) -> list of T

 Sub-list `[start, end_idx)` of `self`.

 ## Parámetros
 - `start`: first index; negative is clamped to 0.
 - `end_idx`: exclusive end; values above the length are clamped to it.

 ## Retorno
 A new owned `list of T`; release it with `banish`. An empty range gives an
 empty list.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.slice_list with 1, 3    # [1, 2]
 ```

### `sum`

> **sum**() -> T

 Sum of every element; the empty list gives `donum T`.

 ## Parámetros
 - None: the receiver is reduced left to right.

 ## Retorno
 The total as `T`, or `donum T` (0 for `int`) when the list is empty.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.sum    # 6
 ```

### `product`

> **product**() -> T

 Product of every element; the empty list gives 1.

 ## Parámetros
 - None: the receiver is reduced left to right.

 ## Retorno
 The product as `T`; the empty list gives the multiplicative identity `1`.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.product    # 6
 ```

### `mean`

> **mean**() -> T

 Arithmetic mean truncated towards zero; the empty list gives `donum T`.

 ## Parámetros
 - None: the receiver is summed and divided by its length.

 ## Retorno
 The mean as `T`, truncated towards zero (`[1, 2]` gives 1), or `donum T`
 when the list is empty. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4]
 calling xs.mean    # 2
 ```

### `average`

> **average**() -> T

 @deprecated Use `mean` instead.

 ## Parámetros
 - None: the receiver is summed and divided by its length.

 ## Retorno
 Same as `mean`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4]
 calling xs.average    # 2
 ```

### `sum_of_squares`

> **sum_of_squares**() -> T

 Sum of the squares of every element.

 ## Parámetros
 - None: the receiver is reduced left to right.

 ## Retorno
 The sum of squares as `T`, or `donum T` when the list is empty. Borrows
 the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.sum_of_squares    # 14
 ```

### `map_double`

> **map_double**() -> list of T

 Copy of `self` with every element multiplied by 2.

 ## Parámetros
 - None: the receiver is mapped element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.map_double    # [6, 2, 4]
 ```

### `map_square`

> **map_square**() -> list of T

 Copy of `self` with every element squared.

 ## Parámetros
 - None: the receiver is mapped element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.map_square    # [9, 1, 4]
 ```

### `map_negate`

> **map_negate**() -> list of T

 Copy of `self` with every element negated.

 ## Parámetros
 - None: the receiver is mapped element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Uses `0 - x`, so it
 works for every `T: Num`, floating point included.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, -1]
 calling xs.map_negate    # [-3, 1]
 ```

### `map_add_scalar`

> **map_add_scalar**(k: T) -> list of T

 Copy of `self` with the scalar `k` added to every element.

 ## Parámetros
 - `k`: the value added to each element.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1]
 calling xs.map_add_scalar with 10    # [13, 11]
 ```

### `map_increment`

> **map_increment**(delta: int) -> list of T

 Copy of `self` with `delta` added to every element (same as
 `map_add_scalar` after converting `delta` to `T`).

 ## Parámetros
 - `delta`: the integer added to each element; defaults to 1.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1]
 calling xs.map_increment    # [4, 2]
 ```

### `max_val`

> **max_val**() -> T

 Largest element; the empty list gives `donum T`.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 The maximum as `T`, or `donum T` (0 for `int`, `""` for `string`) when
 the list is empty. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.max_val    # 3
 ```

### `min_val`

> **min_val**() -> T

 Smallest element; the empty list gives `donum T`.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 The minimum as `T`, or `donum T` when the list is empty. Borrows the
 receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.min_val    # 1
 ```

### `max_index`

> **max_index**() -> int

 Index of the first maximum, or -1 when the list is empty.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 A zero-based `int` index; ties keep the first occurrence and an empty
 list gives -1. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.max_index    # 0
 ```

### `min_index`

> **min_index**() -> int

 Index of the first minimum, or -1 when the list is empty.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 A zero-based `int` index; ties keep the first occurrence and an empty
 list gives -1. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.min_index    # 1
 ```

### `argmin`

> **argmin**() -> int

 @deprecated Use `min_index` instead.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 Same as `min_index`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.argmin    # 1
 ```

### `argmax`

> **argmax**() -> int

 @deprecated Use `max_index` instead.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 Same as `max_index`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.argmax    # 0
 ```

### `find_first_gt`

> **find_first_gt**(threshold: T) -> maybe T

 First element strictly greater than `threshold`.

 ## Parámetros
 - `threshold`: exclusive lower bound to beat.

 ## Retorno
 `some x` for the first match, or `maybe none` when no element beats it.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.find_first_gt with 2    # some 3
 ```

### `find_first_lt`

> **find_first_lt**(threshold: T) -> maybe T

 First element strictly smaller than `threshold`.

 ## Parámetros
 - `threshold`: exclusive upper bound to beat.

 ## Retorno
 `some x` for the first match, or `maybe none` when no element beats it.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.find_first_lt with 2    # some 1
 ```

### `median`

> **median**() -> T

 Median after sorting; the empty list gives `donum T`.

 With an even length it averages the two central values (truncated
 towards zero for an integral `T`).

 ## Parámetros
 - None: the receiver is copied and sorted in place.

 ## Retorno
 The median as `T`, or `donum T` when the list is empty. Borrows the
 receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4]
 calling xs.median    # 3
 ```

### `all_in_range`

> **all_in_range**(lo: T, hi: T) -> bool

 True when every element falls in `[lo, hi]`.

 ## Parámetros
 - `lo`: inclusive lower bound.
 - `hi`: inclusive upper bound.

 ## Retorno
 `true` when no element is outside the span; the empty list gives `true`.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [1, 3, 5]
 calling xs.all_in_range with 1, 5    # true
 ```

### `filter_in_range`

> **filter_in_range**(lo: T, hi: T) -> list of T

 Copy of `self` with the elements inside `[lo, hi]`.

 ## Parámetros
 - `lo`: inclusive lower bound.
 - `hi`: inclusive upper bound.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4, 1, 5]
 calling xs.filter_in_range with 2, 4    # [3, 4]
 ```

### `filter_range`

> **filter_range**(lo: T, hi: T) -> list of T

 @deprecated Use `filter_in_range` instead.

 ## Parámetros
 - `lo`: inclusive lower bound.
 - `hi`: inclusive upper bound.

 ## Retorno
 Same as `filter_in_range`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4, 1, 5]
 calling xs.filter_range with 2, 4    # [3, 4]
 ```

### `abs_all`

> **abs_all**() -> list of T

 Copy of `self` with the absolute value of every element.

 ## Parámetros
 - None: the receiver is mapped element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Negatives become their
 distance to zero.

 ## Ejemplo
 ```pengu
 var xs as list of int is [-3, 1, -2]
 calling xs.abs_all    # [3, 1, 2]
 ```

### `all_positive`

> **all_positive**() -> bool

 True when every element is strictly positive.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 `true` when no element is `<= donum T`; the empty list gives `true`.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.all_positive    # true
 ```

### `any_negative`

> **any_negative**() -> bool

 True when at least one element is strictly negative.

 ## Parámetros
 - None: the receiver is scanned once.

 ## Retorno
 `true` as soon as an element is `< donum T`; the empty list gives `false`.
 Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, -1]
 calling xs.any_negative    # true
 ```

### `filter_positive`

> **filter_positive**() -> list of T

 Copy of `self` with the strictly positive elements.

 ## Parámetros
 - None: the receiver is filtered element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Zero and negatives are
 dropped.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, -1, 0]
 calling xs.filter_positive    # [3]
 ```

### `filter_negative`

> **filter_negative**() -> list of T

 Copy of `self` with the strictly negative elements.

 ## Parámetros
 - None: the receiver is filtered element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Zero is dropped.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, -1, 0]
 calling xs.filter_negative    # [-1]
 ```

### `all_zero`

> **all_zero**() -> bool

 True when every element equals `donum T`.

 ## Parámetros
 - None: the receiver is compared element by element.

 ## Retorno
 `true` when no element differs from `donum T`; the empty list gives
 `true`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [0, 0]
 calling xs.all_zero    # true
 ```

### `mode`

> **mode**() -> T

 Most frequent value; the empty list gives `donum T` (ties: the first).

 ## Parámetros
 - None: the receiver is scanned once per element, O(n^2).

 ## Retorno
 The value with the highest count as `T`, or `donum T` when the list is
 empty. On a tie the earliest value wins. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 3]
 calling xs.mode    # 3
 ```

### `unique`

> **unique**() -> list of T

 Copy of `self` without duplicates, keeping first-appearance order.

 ## Parámetros
 - None: the receiver is compared pairwise, O(n^2).

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 3, 2]
 calling xs.unique    # [3, 1, 2]
 ```

### `dedup`

> **dedup**() -> list of T

 @deprecated Use `unique` instead.

 ## Parámetros
 - None: the receiver is compared pairwise, O(n^2).

 ## Retorno
 Same as `unique`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 3, 2]
 calling xs.dedup    # [3, 1, 2]
 ```

### `count_of`

> **count_of**(item: T) -> int

 Number of occurrences of `item`.

 ## Parámetros
 - `item`: the value to count.

 ## Retorno
 The count as `int` (0 when absent). Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 3]
 calling xs.count_of with 3    # 2
 ```

### `last_index_of`

> **last_index_of**(item: T) -> int

 Index of the last occurrence of `item`, or -1 when absent.

 ## Parámetros
 - `item`: the value to search for.

 ## Retorno
 A zero-based `int` index, or -1 when `item` does not occur. Borrows the
 receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 3]
 calling xs.last_index_of with 3    # 2
 ```

### `filter_even`

> **filter_even**() -> list of T

 Copy of `self` with the even elements.

 ## Parámetros
 - None: the receiver is filtered element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Elements with
 `x % 2 == 0` are kept.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4, 1, 5]
 calling xs.filter_even    # [4]
 ```

### `filter_odd`

> **filter_odd**() -> list of T

 Copy of `self` with the odd elements.

 ## Parámetros
 - None: the receiver is filtered element by element.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Elements with
 `x % 2 != 0` are kept.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4, 1, 5]
 calling xs.filter_odd    # [3, 1, 1, 5]
 ```

### `at_or`

> **at_or**(idx: int, default: int) -> int

 Element at `idx`, or `default` when out of range.

 ## Parámetros
 - `idx`: zero-based position. Negative, or `>= len`, yields `default`.
 - `default`: value returned out of range; defaults to 0.

 ## Retorno
 The element as `int`, or `default`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling xs.at_or with 1, -1    # 1
 calling xs.at_or with 9, -1    # -1
 ```

### `clamp_all`

> **clamp_all**(lo: int, hi: int) -> list of int

 Copy of `self` with every value clipped to `[lo, hi]`.

 ## Parámetros
 - `lo`: inclusive lower bound; defaults to 0.
 - `hi`: inclusive upper bound; defaults to 100.

 ## Retorno
 A new owned `list of int`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [-5, 150]
 calling xs.clamp_all    # [0, 100]
 ```

### `sort_int_asc`

> **sort_int_asc**(l: list of int) -> list of int

 Stable merge sort of `list of int` (`asc`).

### `sort_int_desc`

> **sort_int_desc**(l: list of int) -> list of int

 Stable merge sort of `list of int` (`desc`).

### `sort_float_asc`

> **sort_float_asc**(l: list of float) -> list of float

 Stable merge sort of `list of float` (`asc`).

### `sort_float_desc`

> **sort_float_desc**(l: list of float) -> list of float

 Stable merge sort of `list of float` (`desc`).

### `sort_f64_asc`

> **sort_f64_asc**(l: list of f64) -> list of f64

 Stable merge sort of `list of f64` (`asc`).

### `sort_f64_desc`

> **sort_f64_desc**(l: list of f64) -> list of f64

 Stable merge sort of `list of f64` (`desc`).

### `sort_string_asc`

> **sort_string_asc**(l: list of string) -> list of string

 Stable merge sort of `list of string` (`asc`).

### `sort_string_desc`

> **sort_string_desc**(l: list of string) -> list of string

 Stable merge sort of `list of string` (`desc`).

### `_string_less`

> **_string_less**(a: string, b: string) -> bool

 Strict lexicographic order for `string` (UTF-8 bytes).

### `_string_greater`

> **_string_greater**(a: string, b: string) -> bool

 Strict reverse-lexicographic order for `string`.

### `is_sorted_int_asc`

> **is_sorted_int_asc**(l: list of int) -> bool

 True when `l` is non-decreasing.

### `is_sorted_int_desc`

> **is_sorted_int_desc**(l: list of int) -> bool

 True when `l` is non-increasing.

### `is_sorted_float_asc`

> **is_sorted_float_asc**(l: list of float) -> bool

 True when `l` is non-decreasing.

### `is_sorted_float_desc`

> **is_sorted_float_desc**(l: list of float) -> bool

 True when `l` is non-increasing.

### `is_sorted_f64_asc`

> **is_sorted_f64_asc**(l: list of f64) -> bool

 True when `l` is non-decreasing.

### `is_sorted_f64_desc`

> **is_sorted_f64_desc**(l: list of f64) -> bool

 True when `l` is non-increasing.

### `is_sorted_string_asc`

> **is_sorted_string_asc**(l: list of string) -> bool

 True when `l` is non-decreasing (UTF-8 byte order).

### `is_sorted_string_desc`

> **is_sorted_string_desc**(l: list of string) -> bool

 True when `l` is non-increasing (UTF-8 byte order).

### `is_empty`

> **is_empty**(l: list of T) -> bool

 Functional form of `is_empty`: true when `l` has no elements.

 ## Parámetros
 - `l`: the list to test. Read only.

 ## Retorno
 `true` when `l` is empty. Borrows `l`.

 ## Ejemplo
 ```pengu
 var xs as list of int is list of int
 calling is_empty with xs    # true
 ```

### `concat`

> **concat**(a: list of T, b: list of T) -> list of T

 Concatenation of `a` and `b` into a new list.

 ## Parámetros
 - `a`: first list. Read only.
 - `b`: second list. Read only.

 ## Retorno
 A new owned `list of T` with `a` followed by `b`; release it with `banish`.
 Neither input is mutated.

 ## Memoria
 The result is a fresh list, so it must be released with `banish`.

 ## Ejemplo
 ```pengu
 var a as list of int is [3, 1]
 var b as list of int is [4, 5]
 calling concat with a, b    # [3, 1, 4, 5]
 ```

### `zip_sum`

> **zip_sum**(a: list of T, b: list of T) -> list of T

 Element-wise sum up to the shorter list.

 ## Parámetros
 - `a`: first list. Read only.
 - `b`: second list. Read only.

 ## Retorno
 A new owned `list of T` as long as the shorter input; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 var a as list of int is [3, 1, 2]
 var b as list of int is [1, 1, 1]
 calling zip_sum with a, b    # [4, 2, 3]
 ```

### `dot`

> **dot**(a: list of T, b: list of T) -> T

 Dot product of two vectors.

 ## Parámetros
 - `a`: first list. Read only.
 - `b`: second list. Read only.

 ## Retorno
 The dot product as `T`, computed up to the shorter list; `donum T` when
 either side is empty. Borrows both inputs.

 ## Ejemplo
 ```pengu
 var a as list of int is [3, 1, 2]
 var b as list of int is [1, 1, 1]
 calling dot with a, b    # 6
 ```

### `repeat`

> **repeat**(val: T, times: int) -> list of T

 New list with `val` repeated `times` times.

 ## Parámetros
 - `val`: the value to repeat.
 - `times`: number of copies; `times <= 0` gives an empty list.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling repeat with 7, 3    # [7, 7, 7]
 ```

### `len`

> **len**(l: list of T) -> int

 Number of elements in `l`; alias of the built-in `l.len`.

 ## Parámetros
 - `l`: the list to measure. Read only.

 ## Retorno
 The element count as `int`. Borrows `l`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling len with xs    # 3
 ```

### `at_or_shard`

> **at_or_shard**(l: list of T, idx: int, default: T) -> T

 Element of `l` at `idx`, or `default` when out of range, for any `T: Donum`.

 ## Parámetros
 - `l`: the list to index. Read only.
 - `idx`: zero-based position. Negative, or `>= len`, yields `default`.
 - `default`: the `T` returned out of range; there is no implicit value, so it
   is always explicit.

 ## Retorno
 The element as `T`, or `default`. Borrows `l`.

 ## Ejemplo
 ```pengu
 var ws as list of string is ["a", "b"]
 calling at_or_shard with ws, 9, "?"    # "?"
 ```

### `contains`

> **contains**(l: list of T, item: T) -> bool

 True when `item` is in `l`; alias of the built-in `l.contains`.

 ## Parámetros
 - `l`: the list to search. Read only.
 - `item`: the value to look for.

 ## Retorno
 `true` when `item` occurs in `l`. Borrows `l`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling contains with xs, 1    # true
 ```

### `index_of`

> **index_of**(l: list of T, item: T) -> int

 Index of the first occurrence of `item`, or -1 when absent.

 ## Parámetros
 - `l`: the list to search. Read only.
 - `item`: the value to look for.

 ## Retorno
 A zero-based `int` index, or -1. Borrows `l`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4, 1]
 calling index_of with xs, 4    # 2
 ```

### `clamp_all_shard`

> **clamp_all_shard**(l: list of T, lo: T, hi: T) -> list of T

 Copy of `l` with every value clipped to `[lo, hi]`, for any `T: Num`.

 ## Parámetros
 - `l`: the list to map. Read only.
 - `lo`: inclusive lower bound as `T`; always explicit.
 - `hi`: inclusive upper bound as `T`; always explicit.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var fs as list of float is [-1.5, 4.5]
 calling clamp_all_shard with fs, 0.0, 2.0    # [0.0, 2.0]
 ```

### `zip_with`

> **zip_with**(xs: list of T, ys: list of U, f: weave with a: T, b: U into V) -> list of V

 Combines `xs` and `ys` with `f` up to the shorter list.

 ## Parámetros
 - `xs`: first list. Read only.
 - `ys`: second list. Read only.
 - `f`: binary weave `with a as T, b as U into V`.

 ## Retorno
 A new owned `list of V`, one element per position of the shorter input;
 release it with `banish`.

 ## Memoria
 `xs` and `ys` are only read; the result is a fresh list that the caller
 releases with `banish`.

 ## Ejemplo
 ```pengu
 weave add with a as int, b as int into int:
     return a + b

 var xs as list of int is [3, 1]
 var ys as list of int is [1, 1]
 calling zip_with with xs, ys, add    # [4, 2]
 ```

### `chunk`

> **chunk**(xs: list of T, span: int) -> list of list of T

 Splits `xs` into consecutive runs of `span` elements; the last one may be
 shorter.

 ## Parámetros
 - `xs`: the list to split. Read only.
 - `span`: run length; `span <= 0` gives an empty list.

 ## Retorno
 A new owned `list of list of T`; release every inner list and the outer one
 with `banish`.

 ## Memoria
 Each inner list and the outer list are freshly allocated.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4, 1, 5]
 calling chunk with xs, 2    # [[3, 1], [4, 1], [5]]
 ```

### `windowed`

> **windowed**(xs: list of T, width: int) -> list of list of T

 Sliding windows of width `width`.

 ## Parámetros
 - `xs`: the list to window. Read only.
 - `width`: window length; `width <= 0`, or greater than the list, gives an
   empty list.

 ## Retorno
 A new owned `list of list of T`; release every inner list and the outer one
 with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4]
 calling windowed with xs, 2    # [[3, 1], [1, 4]]
 ```

### `scan_left`

> **scan_left**(xs: list of T, f: weave with acc: T, x: T into T) -> list of T

 Cumulative scan with `f`, seeded with the first element.

 The result has the same length as `xs` and `out[0] = xs[0]`; every later
 position is `f(previous, current)`, so `scan_left` with `+` equals
 `running_sum`.

 ## Parámetros
 - `xs`: the list to scan. Read only.
 - `f`: binary weave `with acc as T, x as T into T`.

 ## Retorno
 A new owned `list of T` with the prefix results; release it with `banish`. An
 empty input gives an empty list.

 ## Ejemplo
 ```pengu
 var xs as list of int is [1, 2, 3]
 calling scan_left with xs, (lambda acc as int, x as int into acc + x)    # [1, 3, 6]
 ```

### `running_sum`

> **running_sum**(xs: list of T) -> list of T

 Cumulative (prefix) sums of `xs`.

 ## Parámetros
 - `xs`: the list to accumulate. Read only.

 ## Retorno
 A new owned `list of T` where position `i` is the sum of `xs[0..i]`; release
 it with `banish`. An empty input gives an empty list.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 2]
 calling running_sum with xs    # [3, 4, 6]
 ```

### `min_max`

> **min_max**(xs: list of T) -> list of T

 Minimum and maximum as a two-element list `[min, max]`.

 ## Parámetros
 - `xs`: the list to scan. Read only.

 ## Retorno
 A new owned `list of T` with exactly two elements, or an empty list when
 `xs` is empty; release it with `banish`. The module uses no tuples, so it
 does not depend on `std.oracle`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4]
 calling min_max with xs    # [1, 4]
 ```

### `_enumerate_pairs_int`

> **_enumerate_pairs_int**(xs: list of int) -> list of list of int

 `[index, value]` pairs of `xs`, in order.

 The pair stays `list of int` because its first component is an index, so this
 function keeps the concrete `list of int` receiver.

 ## Parámetros
 - `xs`: the list to enumerate. Read only.

 ## Retorno
 A new owned `list of list of int` with one `[index, value]` pair per element;
 release every inner list and the outer one with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1]
 calling enumerate_pairs with xs    # [[0, 3], [1, 1]]
 ```

### `enumerate_pairs`

> **enumerate_pairs**(xs: list of int) -> list of list of int

 Pairs every element with its index as `[index, value]`.

 ## Parámetros
 - `xs`: the list to enumerate. Read only.

 ## Retorno
 A new owned `list of list of int` with one two-element list per input
 element; release every inner list and the outer one with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1]
 calling enumerate_pairs with xs    # [[0, 3], [1, 1]]
 ```

### `partition_by`

> **partition_by**(xs: list of int, predicate: weave with x: int into bool) -> list of list of int

 Partitions `xs` with `predicate` into `[matching, non_matching]`.

 The predicate stays `int`-typed, so this function keeps the concrete
 `list of int` receiver.

 ## Parámetros
 - `xs`: the list to partition. Read only.
 - `predicate`: unary weave `with x as int into bool`.

 ## Retorno
 A new owned `list of list of int` with exactly two lists (either may be
 empty); release every inner list and the outer one with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 4]
 calling partition_by with xs, (lambda x as int into (x % 2) == 0)    # [[4], [3, 1]]
 ```

### `frequencies`

> **frequencies**(xs: list of T) -> map of T to int

 Frequency of every value of `xs` as a value -> count map.

 ## Parámetros
 - `xs`: the list to count. Read only.

 ## Retorno
 A new owned `map of T to int`; release it with `banish`. The empty list gives
 an empty map.

 ## Memoria
 The map is freshly allocated by the caller and released with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [3, 1, 3]
 calling frequencies with xs    # 3 -> 2, 1 -> 1
 ```

### `group_count`

> **group_count**(xs: list of T) -> map of T to int

 @deprecated Use `frequencies` instead.

 ## Parámetros
 - `xs`: the list to count. Read only.

 ## Retorno
 Same as `frequencies`; kept only for compatibility.

 ## Ejemplo
 ```pengu
 var xs as list of int is [2, 2]
 calling group_count with xs    # 2 -> 2
 ```

### `_expect`

> **_expect**(cond: bool, label: string) -> void

 Internal harness: panics with `label` when `cond` is false.

### `_expect_eq_int`

> **_expect_eq_int**(actual: int, expected: int, label: string) -> void

 Internal harness: integer equality.

### `_expect_eq_float`

> **_expect_eq_float**(actual: float, expected: float, label: string) -> void

 Internal harness: float equality.

### `_expect_eq_bool`

> **_expect_eq_bool**(actual: bool, expected: bool, label: string) -> void

 Internal harness: boolean equality.

### `"TALLY_VERSION is 2.14.0"`

> test "TALLY_VERSION is 2.14.0"

 --- Tests --------------------------------------------------------------

### `"is_empty is true for the empty list"`

> test "is_empty is true for the empty list"

 --- Length and access ---

### `"is_empty is false with elements"`

> test "is_empty is false with elements"

_Undocumented._

### `"len returns the number of elements"`

> test "len returns the number of elements"

_Undocumented._

### `"first returns the first element"`

> test "first returns the first element"

_Undocumented._

### `"first returns 0 on the empty list"`

> test "first returns 0 on the empty list"

_Undocumented._

### `"last returns the last element"`

> test "last returns the last element"

_Undocumented._

### `"last returns 0 on the empty list"`

> test "last returns 0 on the empty list"

_Undocumented._

### `"at_or returns the element in range"`

> test "at_or returns the element in range"

_Undocumented._

### `"at_or returns the default out of range"`

> test "at_or returns the default out of range"

_Undocumented._

### `"at_or returns the default for a negative index"`

> test "at_or returns the default for a negative index"

_Undocumented._

### `"the at_or method uses its default 0"`

> test "the at_or method uses its default 0"

_Undocumented._

### `"at_safe returns some for a valid index"`

> test "at_safe returns some for a valid index"

_Undocumented._

### `"at_safe returns none out of range"`

> test "at_safe returns none out of range"

_Undocumented._

### `"the at_safe method rejects negative indices"`

> test "the at_safe method rejects negative indices"

_Undocumented._

### `"the first and last methods work on int"`

> test "the first and last methods work on int"

_Undocumented._

### `"the reverse method matches the module function"`

> test "the reverse method matches the module function"

_Undocumented._

### `"the flatten method returns an identity copy"`

> test "the flatten method returns an identity copy"

_Undocumented._

### `"the take method clips and uses its default"`

> test "the take method clips and uses its default"

_Undocumented._

### `"the drop method skips leading elements"`

> test "the drop method skips leading elements"

_Undocumented._

### `"the slice_list method cuts a generic range"`

> test "the slice_list method cuts a generic range"

_Undocumented._

### `"contains finds a present element"`

> test "contains finds a present element"

 --- Search ---

### `"contains is false for an absent element"`

> test "contains is false for an absent element"

_Undocumented._

### `"index_of returns the first position"`

> test "index_of returns the first position"

_Undocumented._

### `"index_of returns -1 when absent"`

> test "index_of returns -1 when absent"

_Undocumented._

### `"last_index_of returns the last position"`

> test "last_index_of returns the last position"

_Undocumented._

### `"last_index_of returns -1 when absent"`

> test "last_index_of returns -1 when absent"

_Undocumented._

### `"count_of counts the occurrences"`

> test "count_of counts the occurrences"

_Undocumented._

### `"find_first_gt returns the first greater element"`

> test "find_first_gt returns the first greater element"

_Undocumented._

### `"find_first_gt returns none when nothing beats it"`

> test "find_first_gt returns none when nothing beats it"

_Undocumented._

### `"find_first_lt returns the first smaller element"`

> test "find_first_lt returns the first smaller element"

_Undocumented._

### `"the count_of method matches the function"`

> test "the count_of method matches the function"

_Undocumented._

### `"the last_index_of method matches the function"`

> test "the last_index_of method matches the function"

_Undocumented._

### `"the find_first methods return maybe"`

> test "the find_first methods return maybe"

_Undocumented._

### `"the find_first methods give none when nothing matches"`

> test "the find_first methods give none when nothing matches"

_Undocumented._

### `"sum adds every element"`

> test "sum adds every element"

 --- Reductions ---

### `"sum of the empty list is 0"`

> test "sum of the empty list is 0"

_Undocumented._

### `"the sum method matches the function"`

> test "the sum method matches the function"

_Undocumented._

### `"sum is generic over float"`

> test "sum is generic over float"

_Undocumented._

### `"product multiplies every element"`

> test "product multiplies every element"

_Undocumented._

### `"product of the empty list is 1"`

> test "product of the empty list is 1"

_Undocumented._

### `"dot multiplies and adds up to the shorter list"`

> test "dot multiplies and adds up to the shorter list"

_Undocumented._

### `"dot with different lengths uses the shorter one"`

> test "dot with different lengths uses the shorter one"

_Undocumented._

### `"dot of the empty list is 0"`

> test "dot of the empty list is 0"

_Undocumented._

### `"sum_of_squares accumulates the squares"`

> test "sum_of_squares accumulates the squares"

_Undocumented._

### `"the product method multiplies every element"`

> test "the product method multiplies every element"

_Undocumented._

### `"the mean method truncates towards zero"`

> test "the mean method truncates towards zero"

_Undocumented._

### `"the average method is an alias of mean"`

> test "the average method is an alias of mean"

_Undocumented._

### `"the sum_of_squares method accumulates squares"`

> test "the sum_of_squares method accumulates squares"

_Undocumented._

### `"max_val returns the largest"`

> test "max_val returns the largest"

 --- Statistics ---

### `"max_val of the empty list is 0"`

> test "max_val of the empty list is 0"

_Undocumented._

### `"min_val returns the smallest"`

> test "min_val returns the smallest"

_Undocumented._

### `"min_val of the empty list is 0"`

> test "min_val of the empty list is 0"

_Undocumented._

### `"max_val and min_val are generic over float"`

> test "max_val and min_val are generic over float"

_Undocumented._

### `"max_index returns the first maximum"`

> test "max_index returns the first maximum"

_Undocumented._

### `"max_index of the empty list is -1"`

> test "max_index of the empty list is -1"

_Undocumented._

### `"min_index returns the first minimum"`

> test "min_index returns the first minimum"

_Undocumented._

### `"argmin and argmax are aliases of min_index and max_index"`

> test "argmin and argmax are aliases of min_index and max_index"

_Undocumented._

### `"mean truncates the division towards zero"`

> test "mean truncates the division towards zero"

_Undocumented._

### `"mean of the empty list is 0"`

> test "mean of the empty list is 0"

_Undocumented._

### `"average is an alias of mean"`

> test "average is an alias of mean"

_Undocumented._

### `"median with odd length returns the centre"`

> test "median with odd length returns the centre"

_Undocumented._

### `"median with even length averages the centre"`

> test "median with even length averages the centre"

_Undocumented._

### `"median of the empty list is 0"`

> test "median of the empty list is 0"

_Undocumented._

### `"mode returns the most frequent value"`

> test "mode returns the most frequent value"

_Undocumented._

### `"mode of the empty list is 0"`

> test "mode of the empty list is 0"

_Undocumented._

### `"the mode method prefers the first appearance on a tie"`

> test "the mode method prefers the first appearance on a tie"

_Undocumented._

### `"the max_val and min_val methods match the functions"`

> test "the max_val and min_val methods match the functions"

_Undocumented._

### `"the max_index and min_index methods match the functions"`

> test "the max_index and min_index methods match the functions"

_Undocumented._

### `"the argmin and argmax methods are aliases"`

> test "the argmin and argmax methods are aliases"

_Undocumented._

### `"reverse returns a reversed copy"`

> test "reverse returns a reversed copy"

 --- Transformations ---

### `"sort_int_asc sorts ascending without mutating the input"`

> test "sort_int_asc sorts ascending without mutating the input"

_Undocumented._

### `"sort_int_desc sorts descending"`

> test "sort_int_desc sorts descending"

_Undocumented._

### `"sort_float_asc and sort_float_desc order floats"`

> test "sort_float_asc and sort_float_desc order floats"

_Undocumented._

### `"sort_f64_asc sorts 64-bit floats"`

> test "sort_f64_asc sorts 64-bit floats"

_Undocumented._

### `"sort_string_desc sorts strings in reverse order"`

> test "sort_string_desc sorts strings in reverse order"

_Undocumented._

### `"the 1000-element sort stays ordered"`

> test "the 1000-element sort stays ordered"

_Undocumented._

### `"is_sorted methods work for strings"`

> test "is_sorted methods work for strings"

_Undocumented._

### `"unique removes duplicates keeping the order"`

> test "unique removes duplicates keeping the order"

_Undocumented._

### `"dedup is an alias of unique"`

> test "dedup is an alias of unique"

_Undocumented._

### `"flatten returns an identity copy"`

> test "flatten returns an identity copy"

_Undocumented._

### `"abs_all turns negatives into positives"`

> test "abs_all turns negatives into positives"

_Undocumented._

### `"clamp_all clips to the given range"`

> test "clamp_all clips to the given range"

_Undocumented._

### `"clamp_all uses the default range [0, 100]"`

> test "clamp_all uses the default range [0, 100]"

_Undocumented._

### `"is_sorted_int_asc detects unsorted and sorted lists"`

> test "is_sorted_int_asc detects unsorted and sorted lists"

_Undocumented._

### `"is_sorted_int_desc detects descending order"`

> test "is_sorted_int_desc detects descending order"

_Undocumented._

### `"the map_square, map_negate and map_add_scalar methods transform"`

> test "the map_square, map_negate and map_add_scalar methods transform"

_Undocumented._

### `"the map_increment method uses delta 1 by default"`

> test "the map_increment method uses delta 1 by default"

_Undocumented._

### `"the abs_all method removes signs"`

> test "the abs_all method removes signs"

_Undocumented._

### `"the median method matches the module function"`

> test "the median method matches the module function"

_Undocumented._

### `"the clamp_all method clips to the span"`

> test "the clamp_all method clips to the span"

_Undocumented._

### `"take returns the first n elements"`

> test "take returns the first n elements"

 --- Selection ---

### `"take without an argument returns one element"`

> test "take without an argument returns one element"

_Undocumented._

### `"drop skips the first n elements"`

> test "drop skips the first n elements"

_Undocumented._

### `"slice_list returns the [start, end) range"`

> test "slice_list returns the [start, end) range"

_Undocumented._

### `"take and drop are generic over float"`

> test "take and drop are generic over float"

_Undocumented._

### `"take clips n above the length"`

> test "take clips n above the length"

_Undocumented._

### `"drop beyond the length is empty"`

> test "drop beyond the length is empty"

_Undocumented._

### `"slice_list with start above end is empty"`

> test "slice_list with start above end is empty"

_Undocumented._

### `"all_positive is true only with strict positives"`

> test "all_positive is true only with strict positives"

 --- Predicates ---

### `"all_zero is true only when everything is zero"`

> test "all_zero is true only when everything is zero"

_Undocumented._

### `"any_negative detects at least one negative"`

> test "any_negative detects at least one negative"

_Undocumented._

### `"all_in_range checks the inclusive range"`

> test "all_in_range checks the inclusive range"

_Undocumented._

### `"the is_sorted methods inspect the order"`

> test "the is_sorted methods inspect the order"

_Undocumented._

### `"the all_positive and any_negative methods scan the sign"`

> test "the all_positive and any_negative methods scan the sign"

_Undocumented._

### `"the all_zero method checks the zero sentinel"`

> test "the all_zero method checks the zero sentinel"

_Undocumented._

### `"the all_in_range method checks the inclusive span"`

> test "the all_in_range method checks the inclusive span"

_Undocumented._

### `"filter_even keeps the even elements"`

> test "filter_even keeps the even elements"

 --- Filters ---

### `"filter_odd keeps the odd elements"`

> test "filter_odd keeps the odd elements"

_Undocumented._

### `"filter_positive and filter_negative split by sign"`

> test "filter_positive and filter_negative split by sign"

_Undocumented._

### `"filter_in_range keeps the inclusive range"`

> test "filter_in_range keeps the inclusive range"

_Undocumented._

### `"filter_range is an alias of filter_in_range"`

> test "filter_range is an alias of filter_in_range"

_Undocumented._

### `"filter_positive is generic over float"`

> test "filter_positive is generic over float"

_Undocumented._

### `"the filter_even and filter_odd methods split by parity"`

> test "the filter_even and filter_odd methods split by parity"

_Undocumented._

### `"the filter_negative method keeps negatives"`

> test "the filter_negative method keeps negatives"

_Undocumented._

### `"the filter_in_range and filter_range methods agree"`

> test "the filter_in_range and filter_range methods agree"

_Undocumented._

### `"the unique and dedup methods remove duplicates"`

> test "the unique and dedup methods remove duplicates"

_Undocumented._

### `"map_double doubles every element"`

> test "map_double doubles every element"

 --- Maps ---

### `"map_square squares every element"`

> test "map_square squares every element"

_Undocumented._

### `"map_negate flips the sign"`

> test "map_negate flips the sign"

_Undocumented._

### `"map_add_scalar adds the scalar"`

> test "map_add_scalar adds the scalar"

_Undocumented._

### `"map_increment uses delta 1 by default"`

> test "map_increment uses delta 1 by default"

_Undocumented._

### `"map_double is generic over float"`

> test "map_double is generic over float"

_Undocumented._

### `"concat joins two lists into a new one"`

> test "concat joins two lists into a new one"

 --- Combination ---

### `"zip_sum adds element by element"`

> test "zip_sum adds element by element"

_Undocumented._

### `"repeat repeats a value"`

> test "repeat repeats a value"

_Undocumented._

### `"repeat with a non-positive times returns an empty list"`

> test "repeat with a non-positive times returns an empty list"

_Undocumented._

### `"zip_with combines two lists with a function"`

> test "zip_with combines two lists with a function"

 --- New API ---

### `"zip_with accepts different input types"`

> test "zip_with accepts different input types"

_Undocumented._

### `"chunk splits into consecutive runs"`

> test "chunk splits into consecutive runs"

_Undocumented._

### `"chunk with a span greater than the list gives one run"`

> test "chunk with a span greater than the list gives one run"

_Undocumented._

### `"windowed produces sliding windows"`

> test "windowed produces sliding windows"

_Undocumented._

### `"running_sum accumulates the prefixes"`

> test "running_sum accumulates the prefixes"

_Undocumented._

### `"scan_left accumulates with the given function"`

> test "scan_left accumulates with the given function"

_Undocumented._

### `"scan_left is generic over float"`

> test "scan_left is generic over float"

_Undocumented._

### `"min_max returns [min, max]"`

> test "min_max returns [min, max]"

_Undocumented._

### `"enumerate_pairs returns [index, value] pairs"`

> test "enumerate_pairs returns [index, value] pairs"

_Undocumented._

### `"partition_by splits according to the predicate"`

> test "partition_by splits according to the predicate"

_Undocumented._

### `"frequencies counts every value"`

> test "frequencies counts every value"

_Undocumented._

### `"group_count is an alias of frequencies"`

> test "group_count is an alias of frequencies"

_Undocumented._

### `"zip_with stops at the shorter list"`

> test "zip_with stops at the shorter list"

_Undocumented._

### `"zip_with is generic over float"`

> test "zip_with is generic over float"

_Undocumented._

### `"chunk with a non-positive span is empty"`

> test "chunk with a non-positive span is empty"

_Undocumented._

### `"windowed with a non-positive width is empty"`

> test "windowed with a non-positive width is empty"

_Undocumented._

### `"windowed wider than the list is empty"`

> test "windowed wider than the list is empty"

_Undocumented._

### `"running_sum and scan_left of the empty list are empty"`

> test "running_sum and scan_left of the empty list are empty"

_Undocumented._

### `"scan_left seeds the accumulator with the first element"`

> test "scan_left seeds the accumulator with the first element"

_Undocumented._

### `"min_max of the empty list is empty"`

> test "min_max of the empty list is empty"

_Undocumented._

### `"min_max of a single element repeats it"`

> test "min_max of a single element repeats it"

_Undocumented._

### `"enumerate_pairs of the empty list is empty"`

> test "enumerate_pairs of the empty list is empty"

_Undocumented._

### `"partition_by of the empty list returns two empty lists"`

> test "partition_by of the empty list returns two empty lists"

_Undocumented._

### `"frequencies of the empty list is an empty map"`

> test "frequencies of the empty list is an empty map"

_Undocumented._

### `"the sum module function adds floats"`

> test "the sum module function adds floats"

 --- Widened module functions ---

### `"the sum module function adds i64 values"`

> test "the sum module function adds i64 values"

_Undocumented._

### `"the product module function multiplies floats"`

> test "the product module function multiplies floats"

_Undocumented._

### `"the mean module function averages floats"`

> test "the mean module function averages floats"

_Undocumented._

### `"the max_val module function orders strings"`

> test "the max_val module function orders strings"

_Undocumented._

### `"the min_val module function orders strings"`

> test "the min_val module function orders strings"

_Undocumented._

### `"sort_string_asc sorts strings"`

> test "sort_string_asc sorts strings"

_Undocumented._

### `"the filter_even module function keeps i64 parity"`

> test "the filter_even module function keeps i64 parity"

_Undocumented._

### `"the contains module function compares strings"`

> test "the contains module function compares strings"

_Undocumented._

### `"the frequencies module function counts strings"`

> test "the frequencies module function counts strings"

_Undocumented._

### `"the at_or_shard module function returns its string default"`

> test "the at_or_shard module function returns its string default"

_Undocumented._

### `"the clamp_all_shard module function clips floats"`

> test "the clamp_all_shard module function clips floats"

_Undocumented._

### `"the min_max module function orders float values"`

> test "the min_max module function orders float values"

_Undocumented._

### `"the dot module function reduces floats"`

> test "the dot module function reduces floats"

_Undocumented._

### `"the root sum module function reduces floats"`

> test "the root sum module function reduces floats"

_Undocumented._

### `"the root max_val module function orders strings"`

> test "the root max_val module function orders strings"

_Undocumented._

### `"the root sort_string_asc module function sorts strings"`

> test "the root sort_string_asc module function sorts strings"

_Undocumented._

### `"the root at_or_shard module function returns its default"`

> test "the root at_or_shard module function returns its default"

_Undocumented._

### `"a one-element list reduces to itself"`

> test "a one-element list reduces to itself"

 --- Edge cases ---

### `"a list of negatives keeps its sign in the reductions"`

> test "a list of negatives keeps its sign in the reductions"

_Undocumented._

### `"duplicates affect count_of and unique"`

> test "duplicates affect count_of and unique"

_Undocumented._

### `"operations on the empty list are safe"`

> test "operations on the empty list are safe"

_Undocumented._

