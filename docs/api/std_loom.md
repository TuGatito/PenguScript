# std.loom

> Source: `std/loom.pengu`

std/loom.pengu — the safe family of list helpers: sequence generation,
slicing, windows, folds, combinations, set operations over sorted lists,
search, structural editing and statistics.

Every operation is a **module function** (`calling loom.chunks with xs, 2`):
the module declares no `enchanting` block, so it never invades the methods
of `std.tally`. Since 2.2.0 the entry points are **generic over the element
type** (`weave chunks shard T with items as list of T, n as int`): a
`list of int` call still behaves exactly as in 0.14.x/0.15.0, while `float`,
`i64`, `string` and bound `seal`/`rune` element types work wherever the
operation is meaningful. Ordering operations are bounded `where T: Ordered`
(`std.atlas`) and compare with `calling a.cmp with b`, because `>` inside a
generic body has no `PenguString` translation; equality works generically, so
the predicate group needs no ordering concept.

## Example
```pengu
import std.loom
import std.spark

weave main into int:
    var xs as list of int is calling loom.range with 1, 6, 1
    var total as int is calling loom.sum with xs
    var exact as float is calling loom.mean with xs
    calling spark.println with "total={total} mean={exact}"
    return 0
```

## Memory
No function mutates or frees its inputs: it only reads them and returns new
owned lists that the caller releases with `banish` (the scalar results,
including `maybe int` / `maybe float` / `maybe Pair`, need no release).
`banish` on a list frees only that list's own buffer: for a nested result
(`chunks`, `chunk_every`, `windows`, `windowed`, `pairwise`, `zip_longest`,
`enumerate`) every inner list is owned by the caller too, so release each
inner list and then the outer one. A `list of Pair` (a flat rune) or a
`maybe Pair` is released with a single `banish` or not at all.

## Design notes
- **Module functions, no `enchanting`.** The inherited surface is functional
  (`calling loom.sum with xs`) and the list methods live in `std.tally`. The
  absence of an `enchanting` block is deliberate: declaring one here would
  collide with `tally`'s methods and merge two contracts that must stay
  separate.
- **Generic core.** The public entry points are themselves `shard T` since
  2.2.0. A generic weave body cannot call another generic weave or method, so
  every body is implemented directly; the older typed cores (`generic_take`,
  `generic_take_last`, `generic_reverse`, `generic_chain`,
  `generic_index_of`, `first_or`, `flatten_generic`, `_slice_shard`,
  `_drop_shard`, `_repeat_shard`) survive for explicit `of T` calls. The
  `int`-specific helpers (`_mean_int`, `_variance_int`, ...) stay because the
  internal tests pin the concrete contract through them.
- **Ordering needs a concept.** `>` inside a generic body lowers to a raw C
  `>` that does not compile for `PenguString`, so every ordering entry point
  is bounded `where T: Ordered` and compares with `calling a.cmp with b`
  (`std.atlas`). Equality is fine generically, so the `Par` group carries no
  extra concept.
- **Bounds by group.** No bound: slicing, windows, rotations, structural
  editing and the `generic_*` cores. `T: Num`: the arithmetic folds.
  `T: Ordered`: extremes, search, order predicates and the sorted-set
  operations. `T: Par`: predicates and searches that only compare for
  equality. `T: Num and T: Ordo`: the statistics, which both order and
  convert to `float`.
- **`enumerate` is numeric.** Its row is homogeneous (`[index, value]`), so
  the index shares the element type and the weave is bounded `T: Num`;
  `enumerate_pairs` is the unconstrained `Pair of int and T` variant.
- **No `T`-dependent defaults.** `pad_left`, `pad_right` and `zip_longest`
  keep the concrete `list of int` signature: their `fill` parameter has the
  element type, a generic parameter cannot carry a default value that depends
  on `T`, and dropping the default would break existing two-argument call
  sites.
- **Pair variants.** `enumerate`, `pairwise`, `pairwise_pairs`, `enumerate_pairs`
  and `min_max` keep their 0.15.0 names; the `Pair`-shaped ones
  (`enumerate_pairs`, `pairwise_pairs`, `min_max`) are documented beside their
  list-of-lists counterparts.
- **One alias, documented only.** `flatten` follows the repository
  deprecation convention: a `## @deprecated Use flat_map_identity instead.`
  docstring line (no real `@deprecated` attribute, so it emits no `W0006`),
  catalogued in `docs/DEPRECATIONS.md`.
- **Internal tests.** The `# --- Tests ---` section uses a private `_expect*`
  harness built on `spark.panic`, so `loom` keeps no test-only dependency on
  `std.ward` (which would drag `std.oracle` into every program that uses it).

## Relationship with std.tally
`loom` and `std.tally` intentionally share 15 public names with **different
contracts**: `mean`, `median`, `mode`, `min_max`, `sum`, `flatten`, `take`,
`windowed`, `zip_with`, `running_sum`, `scan_left`, `repeat`,
`enumerate_pairs`, `is_sorted_asc` and `is_sorted_desc`. This is a documented
named exception to the cross-module naming rule: see `LANGUAGE.md` §19.1.1 and
the style guide (`PenguScriptGuideSpanish.md` §15, "Excepciones
documentadas"). `loom` is the **safe** family: an empty list is represented as
absence (`median`, `mode` and `min_max` return `maybe none`) and fractional
statistics keep the fraction (`calling loom.mean with [1, 2]` is `1.5`).
`std.tally` is the reduction family with a natural identity: an empty list
collapses to a sentinel (`sum` -> 0, `product_num` -> 1, `max_val` -> 0) and
fractional statistics truncate to `int` (`calling tally.mean with [1, 2]` is
`1`). Reach for `loom` when an empty list has no answer and a sentinel would
hide a bug. The two families are **not** merged and **not** renamed. Since
2.2.0 both are generic over the element type (`shard T` with the bound each
operation needs), and the contracts above hold for `float`, `i64`, `string`
and bound `seal`/`rune` elements too.

## Migration
| Before (0.14.x/0.15.0) | Now |
|---|---|
| `take` / `skip` / `chain` / `repeat` | unchanged; generic core `calling loom.generic_take of T with xs, n` |
| `calling loom.chunks with xs, n` | unchanged, or `calling loom.chunk_every with xs, n, n` |
| `calling loom.windows with xs, n` | unchanged, or `calling loom.windowed with xs, n` |
| `calling loom.pairwise with xs` | unchanged, or `calling loom.pairwise_pairs with xs` (`Pair`) |
| `calling loom.enumerate with xs` | unchanged, or `calling loom.enumerate_pairs with xs` (`Pair`) |
| `calling loom.zip_with with a, b, op` | unchanged, or `calling loom.zip_with_op with a, b, f` |
| `calling loom.flatten` / `min_int` / `max_int` | unchanged; new `flat_map_identity` and `min_max` |
| `calling loom.range with 5, stop, step` | unchanged; new `calling loom.unfold_range with 5, count, step` |
| (new) | `calling loom.is_partitioned with xs, predicate` |
| `list of int` entry points | generic since 2.2.0: `calling loom.sum with floats`, `calling loom.min_max with words`, ... |
| `calling loom.take of int with xs, n` | unchanged; the generic core also works as `calling loom.generic_take of T with xs, n` |

---

### `LOOM_VERSION`

> **LOOM_VERSION** : string

 The version of the loom module.

### `range`

> **range**(start: int, end: int, step: int) -> list of int

 Returns the sequence `[start, end)` advancing by `step`; `step == 0` gives `[]`.

 ## Parámetros
 - `start`: the first value, included.
 - `end`: the exclusive bound.
 - `step`: the increment (default `1`); positive walks up, negative walks down.

 ## Retorno
 A new owned `list of int`; release it with `banish`. It stays empty when the
 sign of `step` never reaches `end`.

 ## Ejemplo
 ```pengu
 calling loom.range with 1, 5, 1      # [1, 2, 3, 4]
 calling loom.range with 5, 0, -2     # [5, 3, 1]
 ```

### `repeat`

> **repeat**(value: T, times: int) -> list of T

 Returns `value` repeated `times` times; `times <= 0` gives `[]`.

 ## Parámetros
 - `value`: the value to repeat.
 - `times`: how many copies to produce; `<= 0` yields an empty list.

 ## Retorno
 A new owned `list of int`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.repeat with 7, 3      # [7, 7, 7]
 ```

### `unfold_range`

> **unfold_range**(start: int, count: int, step: int) -> list of int

 Returns an arithmetic progression of exactly `count` elements
 (`start, start + step, ...`).

 ## Parámetros
 - `start`: the first value.
 - `count`: how many elements to produce; `count <= 0` yields `[]`.
 - `step`: the difference between consecutive elements (default `1`).

 ## Retorno
 A new owned `list of int` of length `count`; release it with `banish`. Unlike
 `range`, it counts elements instead of comparing against an upper bound.

 ## Ejemplo
 ```pengu
 calling loom.unfold_range with 5, 3, 2      # [5, 7, 9]
 ```

### `take`

> **take**(items: list of T, n: int) -> list of T

 Returns the first `n` elements of `items` for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: how many elements to take; `n > len` clamps to the whole list and
   `n < 0` yields `[]`.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.take with [1, 2, 3, 4], 2         # [1, 2]
 calling loom.take with ["a", "b", "c"], 1     # ["a"]
 ```

### `skip`

> **skip**(items: list of T, n: int) -> list of T

 Returns the elements of `items` from index `n` on, for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: the first index to keep; `n < 0` behaves like `n == 0` and
   `n > len` yields `[]`.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.skip with [1, 2, 3, 4], 2        # [3, 4]
 calling loom.skip with ["a", "b", "c"], 1     # ["b", "c"]
 ```

### `chain`

> **chain**(a: list of T, b: list of T) -> list of T

 Concatenates `a` and `b` into a new list of any element type `T`.

 ## Parámetros
 - `a`: the first list, copied first.
 - `b`: the second list, copied after `a`.

 ## Retorno
 A new owned `list of T` with `len(a) + len(b)` elements; release it with
 `banish`. Both inputs are only read.

 ## Ejemplo
 ```pengu
 calling loom.chain with [1, 2], [3, 4]        # [1, 2, 3, 4]
 calling loom.chain with ["a"], ["b"]          # ["a", "b"]
 ```

### `chunks`

> **chunks**(items: list of T, n: int) -> list of list of T

 Splits `items` into consecutive blocks of up to `n` elements, for any `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: the block size; `n <= 0` yields `[]`.

 ## Retorno
 A new owned `list of list of T`; the last block may be shorter.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.chunks with [1, 2, 3, 4, 5], 2          # [[1, 2], [3, 4], [5]]
 calling loom.chunks with ["a", "b", "c"], 2          # [["a", "b"], ["c"]]
 ```

### `chunk_every`

> **chunk_every**(items: list of T, n: int, step: int) -> list of list of T

 Splits `items` into blocks of up to `n` elements taken every `step` positions.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: the block size; `n <= 0` yields `[]`.
 - `step`: the distance between block starts (default `1`); `step <= 0` yields
   `[]`.

 ## Retorno
 A new owned `list of list of T`; `step == n` matches `chunks`, `step < n`
 overlaps and `step > n` skips elements.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.chunk_every with [1, 2, 3, 4], 3, 1     # [[1, 2, 3], [2, 3, 4], [3, 4], [4]]
 ```

### `windows`

> **windows**(items: list of T, n: int) -> list of list of T

 Returns the contiguous windows of exactly `n` elements, for any `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: the window size; `n <= 0` or `n > len` yields `[]`.

 ## Retorno
 A new owned `list of list of T` with `len - n + 1` complete windows.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.windows with [1, 2, 3], 2          # [[1, 2], [2, 3]]
 calling loom.windows with ["a", "b"], 2         # [["a", "b"]]
 ```

### `windowed`

> **windowed**(items: list of T, n: int) -> list of list of T

 Pengunic name of `windows`; same signature and same result for any `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: the window size; `n <= 0` or `n > len` yields `[]`.

 ## Retorno
 A new owned `list of list of T`; same result as `windows`.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.windowed with [1, 2, 3], 2          # [[1, 2], [2, 3]]
 calling loom.windowed with ["a", "b"], 2         # [["a", "b"]]
 ```

### `pairwise`

> **pairwise**(items: list of T) -> list of list of T

 Returns the overlapping adjacent pairs `[[x0, x1], ...]`, for any `T`.

 ## Parámetros
 - `items`: the source list; it is only read. `len < 2` yields `[]`.

 ## Retorno
 A new owned `list of list of T` of size `len - 1`; `pairwise_pairs` is the
 `Pair` variant.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.pairwise with [1, 2, 3]            # [[1, 2], [2, 3]]
 calling loom.pairwise with ["a", "b"]           # [["a", "b"]]
 ```

### `pairwise_pairs`

> **pairwise_pairs**(items: list of T) -> list of Pair__T__T

 Returns the adjacent pairs as `Pair(first = xi, second = xi+1)` for any `T`.

 ## Parámetros
 - `items`: the source list; it is only read. `len < 2` yields `[]`.

 ## Retorno
 A new owned `list of Pair of T and T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.pairwise_pairs with [1, 2, 3]      # [Pair(1, 2), Pair(2, 3)]
 calling loom.pairwise_pairs with ["a", "b"]     # [Pair("a", "b")]
 ```

### `sum`

> **sum**(nums: list of T) -> T

 Adds every element of `nums` for any numeric `T` (`0` for an empty list).

 ## Parámetros
 - `nums`: the values to add; the list is only read.

 ## Retorno
 The sum as a `T` (`0` for an empty list); nothing to release.

 ## Ejemplo
 ```pengu
 calling loom.sum with [1, 2, 3]           # 6
 calling loom.sum with [1.5, 2.5]          # 4.0
 ```

### `product_num`

> **product_num**(nums: list of T) -> T

 Multiplies every element for any numeric `T` (`1` for an empty list).

 ## Parámetros
 - `nums`: the values to multiply; the list is only read.

 ## Retorno
 The product as a `T` (`1` for an empty list); nothing to release.

 ## Ejemplo
 ```pengu
 calling loom.product_num with [2, 3, 4]      # 24
 ```

### `max_int`

> **max_int**(items: list of T) -> T

 Returns the greatest element for any ordered `T` (`0` for an empty list).

 ## Parámetros
 - `items`: the values to scan; the list is only read.

 ## Retorno
 The maximum as a `T`, or `donum T` (`0` for the numeric types) when the list
 is empty. Use `min_max` when an empty list must be distinguishable.

 ## Ejemplo
 ```pengu
 calling loom.max_int with [3, 9, 4]      # 9
 calling loom.max_int with ["a", "c"]     # "c"
 ```

### `min_int`

> **min_int**(items: list of T) -> T

 Returns the smallest element for any ordered `T` (`0` for an empty list).

 ## Parámetros
 - `items`: the values to scan; the list is only read.

 ## Retorno
 The minimum as a `T`, or `donum T` (`0` for the numeric types) when the list
 is empty. Use `min_max` when an empty list must be distinguishable.

 ## Ejemplo
 ```pengu
 calling loom.min_int with [3, 9, 4]      # 3
 calling loom.min_int with ["a", "c"]     # "a"
 ```

### `min_max`

> **min_max**(items: list of T) -> maybe Pair__T__T

 Returns the minimum and the maximum as `Pair(first = min, second = max)`.

 ## Parámetros
 - `items`: the values to scan; the list is only read.

 ## Retorno
 `some Pair` with the bounds for any ordered `T`, or `maybe none` when the
 list is empty; nothing to release either way.

 ## Ejemplo
 ```pengu
 calling loom.min_max with [3, 9, 4]          # some Pair(3, 9)
 calling loom.min_max with ["b", "a"]         # some Pair("a", "b")
 ```

### `_min_max_int`

> **_min_max_int**(items: list of int) -> maybe Pair__int__int

 Core of `min_max`.

### `mean`

> **mean**(nums: list of T) -> float

 Returns the arithmetic mean as a `float` (`0.0` for an empty list).

 ## Parámetros
 - `nums`: the values to average; the list is only read.

 ## Retorno
 The mean as a `float`, keeping the fraction (`calling loom.mean with [1, 2]`
 is `1.5`). Unlike `std.tally.mean`, it is not truncated to `int`.

 ## Ejemplo
 ```pengu
 calling loom.mean with [1, 2, 3, 4]      # 2.5
 calling loom.mean with [1.5, 2.5]        # 2.0
 ```

### `sum_squares`

> **sum_squares**(nums: list of T) -> T

 Adds the squares of `nums` (`0` for an empty list) for any numeric `T`.

 ## Parámetros
 - `nums`: the values whose squares are added; the list is only read.

 ## Retorno
 The sum of squares as a `T`; nothing to release.

 ## Ejemplo
 ```pengu
 calling loom.sum_squares with [1, 2, 3]      # 14
 ```

### `running_sum`

> **running_sum**(nums: list of T) -> list of T

 Returns the running (prefix) sums, one per element, for any numeric `T`.

 ## Parámetros
 - `nums`: the values to accumulate; the list is only read.

 ## Retorno
 A new owned `list of T` of the same length as `nums` (`[]` stays `[]`);
 release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.running_sum with [1, 2, 3]      # [1, 3, 6]
 ```

### `running_max`

> **running_max**(nums: list of T) -> list of T

 Returns the running (prefix) maxima, one per element, for any ordered `T`.

 ## Parámetros
 - `nums`: the values to accumulate; the list is only read.

 ## Retorno
 A new owned `list of T` of the same length as `nums` (`[]` stays `[]`);
 release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.running_max with [3, 1, 4]      # [3, 3, 4]
 calling loom.running_max with ["b", "a"]     # ["b", "b"]
 ```

### `running_min`

> **running_min**(nums: list of T) -> list of T

 Returns the running (prefix) minima, one per element, for any ordered `T`.

 ## Parámetros
 - `nums`: the values to accumulate; the list is only read.

 ## Retorno
 A new owned `list of T` of the same length as `nums` (`[]` stays `[]`);
 release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.running_min with [3, 1, 4]      # [3, 1, 1]
 calling loom.running_min with ["b", "a"]     # ["b", "a"]
 ```

### `differences`

> **differences**(nums: list of T) -> list of T

 Returns the adjacent differences `[x1 - x0, x2 - x1, ...]` for numeric `T`.

 ## Parámetros
 - `nums`: the values to difference; the list is only read. `len <= 1` yields
   `[]`.

 ## Retorno
 A new owned `list of T` of size `len - 1`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.differences with [1, 4, 9]      # [3, 5]
 ```

### `scan_left`

> **scan_left**(items: list of T, f: weave with acc: T, x: T into T) -> list of T

 Returns the running accumulation of `items` with `f`.

 Each output slot is `calling f with acc, items[i]`, where `acc` is the
 previous output and `donum T` (0 for the numeric types) for `i == 0`; with a
 cumulative operator such as addition that makes `out[0] == items[0]`.

 ## Parámetros
 - `items`: the values to scan; `[]` yields `[]`.
 - `f`: the pure combining weave `(T, T) -> T`.

 ## Retorno
 A new owned `list of T` of the same length as `items`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.scan_left of int with [4, 6, 8], arithmancy.gcd      # [4, 2, 2]
 ```

### `any_zero`

> **any_zero**(nums: list of T) -> bool

 Returns `true` when some element is equal to the zero of `T`.

 ## Parámetros
 - `nums`: the values to test; the list is only read.

 ## Retorno
 `true` when at least one element equals `donum T`, `false` otherwise (also
 for `[]`).

 ## Ejemplo
 ```pengu
 calling loom.any_zero with [1, 0, 3]      # true
 ```

### `all_equal`

> **all_equal**(nums: list of T) -> bool

 Returns `true` when every element is equal.

 ## Parámetros
 - `nums`: the values to compare; the list is only read. `len <= 1` yields
   `true`.

 ## Retorno
 `true` when all elements are equal, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.all_equal with [4, 4, 4]      # true
 calling loom.all_equal with ["x", "x"]      # true
 ```

### `is_strictly_asc`

> **is_strictly_asc**(nums: list of T) -> bool

 Returns `true` when every element is strictly smaller than the next.

 ## Parámetros
 - `nums`: the values to check; the list is only read.

 ## Retorno
 `true` for a strictly ascending list (lists of fewer than two elements are
 ascending), `false` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.is_strictly_asc with [1, 2, 3]      # true
 calling loom.is_strictly_asc with ["a", "b"]     # true
 ```

### `is_strictly_desc`

> **is_strictly_desc**(nums: list of T) -> bool

 Returns `true` when every element is strictly greater than the next.

 ## Parámetros
 - `nums`: the values to check; the list is only read.

 ## Retorno
 `true` for a strictly descending list (lists of fewer than two elements are
 descending), `false` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.is_strictly_desc with [3, 2, 1]      # true
 ```

### `is_sorted_asc`

> **is_sorted_asc**(nums: list of T) -> bool

 Returns `true` when `nums` is sorted in non-decreasing order.

 ## Parámetros
 - `nums`: the values to check; the list is only read.

 ## Retorno
 `true` when consecutive elements never decrease, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.is_sorted_asc with [1, 1, 2]      # true
 calling loom.is_sorted_asc with ["a", "a", "b"]      # true
 ```

### `is_sorted_desc`

> **is_sorted_desc**(nums: list of T) -> bool

 Returns `true` when `nums` is sorted in non-increasing order.

 ## Parámetros
 - `nums`: the values to check; the list is only read.

 ## Retorno
 `true` when consecutive elements never increase, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.is_sorted_desc with [3, 3, 1]      # true
 ```

### `is_partitioned`

> **is_partitioned**(items: list of T, predicate: weave with x: T into bool) -> bool

 Returns `true` when the elements that satisfy `predicate` precede all the
 ones that do not.

 ## Parámetros
 - `items`: the values to check; the list is only read. `[]` and one-element
   lists yield `true`.
 - `predicate`: a pure weave `(T) -> bool`.

 ## Retorno
 `true` when the list is partitioned, `false` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.is_partitioned with [2, 3, 4], arithmancy.is_prime      # true
 ```

### `zip_with`

> **zip_with**(a: list of T, b: list of T, op: int) -> list of T

 Combines `a` and `b` with the operator code `op`, for any numeric and ordered
 `T`.

 ## Parámetros
 - `a`: the left operands; the list is only read.
 - `b`: the right operands; the list is only read.
 - `op`: `0` adds (also the default and the fallback), `1` subtracts, `2`
   multiplies, `3` takes the minimum and `4` the maximum.

 ## Retorno
 A new owned `list of T` that stops at the shorter input; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.zip_with with [1, 2], [10, 20], 0      # [11, 22]
 calling loom.zip_with with [1.5, 2.5], [1.0, 1.0], 1      # [0.5, 1.5]
 ```

### `_zip_with_int`

> **_zip_with_int**(a: list of int, b: list of int, op: int) -> list of int

 Core of `zip_with` (see its docstring for the `op` codes).

### `zip_with_op`

> **zip_with_op**(a: list of T, b: list of T, f: weave with x: T, y: T into T) -> list of T

 Combines `a` and `b` with the weave `f`, up to the shorter list, for any `T`.

 ## Parámetros
 - `a`: the left operands; the list is only read.
 - `b`: the right operands; the list is only read.
 - `f`: a pure weave `(T, T) -> T`.

 ## Retorno
 A new owned `list of T` of size `min(len(a), len(b))`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.zip_with_op with [12, 8], [8, 6], arithmancy.gcd      # [4, 2]
 ```

### `zip_longest`

> **zip_longest**(a: list of int, b: list of int, fill: int) -> list of list of int

 Returns the pairs `[a_i, b_i]` up to the longer list, filling with `fill`.

 The signature stays concrete (`list of int`): `fill` has the element type and
 a generic parameter cannot carry a default value that depends on `T` (E0005),
 while dropping the default would break the two-argument call sites.

 ## Parámetros
 - `a`: the left operands; the list is only read.
 - `b`: the right operands; the list is only read.
 - `fill`: the value used where a list is exhausted (default `0`).

 ## Retorno
 A new owned `list of list of int` of size `max(len(a), len(b))`.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.zip_longest with [1, 2, 3], [9], 7      # [[1, 9], [2, 7], [3, 7]]
 ```

### `enumerate`

> **enumerate**(items: list of T) -> list of list of T

 Returns the `[index, value]` pairs in order for any numeric `T`.

 The row is homogeneous, so the index shares the element type and the weave is
 bounded `T: Num`; use `enumerate_pairs` for the unconstrained `Pair` variant.

 ## Parámetros
 - `items`: the values to index; the list is only read.

 ## Retorno
 A new owned `list of list of T` with one two-element list per input element.

 ## Memoria
 Each inner list is a separate owned value: release every inner list and then
 the outer one. The input list is only read.

 ## Ejemplo
 ```pengu
 calling loom.enumerate with [10, 20]      # [[0, 10], [1, 20]]
 ```

### `enumerate_pairs`

> **enumerate_pairs**(items: list of T) -> list of Pair__int__T

 Returns the `Pair(first = index, second = value)` entries in order for any
 element type `T`.

 ## Parámetros
 - `items`: the values to index; the list is only read.

 ## Retorno
 A new owned `list of Pair of int and T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.enumerate_pairs with [10, 20]      # [Pair(0, 10), Pair(1, 20)]
 calling loom.enumerate_pairs with ["a"]         # [Pair(0, "a")]
 ```

### `_enumerate_pairs_int`

> **_enumerate_pairs_int**(items: list of int) -> list of Pair__int__int

 Core of `enumerate_pairs`.

### `interleave`

> **interleave**(a: list of T, b: list of T) -> list of T

 Alternates elements of `a` and `b` up to the shorter list: `[a0, b0, a1, ...]`.

 ## Parámetros
 - `a`: the first list; the list is only read.
 - `b`: the second list; the list is only read.

 ## Retorno
 A new owned `list of T` of size `2 * min(len(a), len(b))`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.interleave with [1, 2], [10]      # [1, 10]
 calling loom.interleave with ["a"], ["b"]      # ["a", "b"]
 ```

### `round_robin`

> **round_robin**(lists: list of list of T) -> list of T

 Takes turns over every list of `lists` until all of them are exhausted.

 ## Parámetros
 - `lists`: the lists to interleave; only read.

 ## Retorno
 A new owned `list of T`; release it with `banish`. Position `i` is taken
 from every list that still has `i` elements.

 ## Ejemplo
 ```pengu
 calling loom.round_robin with [[1, 2], [10, 11]]      # [1, 10, 2, 11]
 ```

### `rotate_left`

> **rotate_left**(items: list of T, k: int) -> list of T

 Rotates `items` to the left by `k` positions, for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `k`: the number of positions; negative values rotate the other way and
   values larger than the length wrap around.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.rotate_left with [10, 20, 30], 1      # [20, 30, 10]
 calling loom.rotate_left with ["a", "b"], 1        # ["b", "a"]
 ```

### `rotate_right`

> **rotate_right**(items: list of T, k: int) -> list of T

 Rotates `items` to the right by `k` positions, for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `k`: the number of positions; negative values rotate the other way and
   values larger than the length wrap around.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.rotate_right with [10, 20, 30], 1      # [30, 10, 20]
 ```

### `intersperse`

> **intersperse**(items: list of T, sep: T) -> list of T

 Inserts `sep` between every pair of adjacent elements, for any `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `sep`: the separator inserted between elements.

 ## Retorno
 A new owned `list of T` of size `2 * len - 1` for a non-empty input, or the
 empty list; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.intersperse with [1, 2, 3], 0      # [1, 0, 2, 0, 3]
 calling loom.intersperse with ["a", "b"], "-"   # ["a", "-", "b"]
 ```

### `flat_map_identity`

> **flat_map_identity**(nested: list of list of T) -> list of T

 Flattens one level of nesting: concatenates the inner lists of `nested`.

 ## Parámetros
 - `nested`: the list of lists to flatten; it is only read.

 ## Retorno
 A new owned `list of T` with the elements of every inner list, in order;
 release it with `banish`.

 ## Ejemplo
 ```pengu
 let blocks as list of list of int is calling loom.chunks with [1, 2, 3, 4], 2
 calling loom.flat_map_identity with blocks      # [1, 2, 3, 4]
 ```

### `flatten`

> **flatten**(nested: list of list of T) -> list of T

 Flattens one level of nesting: concatenates the inner lists of `nested`.

 @deprecated Use flat_map_identity instead.

 ## Parámetros
 - `nested`: the list of lists to flatten; it is only read.

 ## Retorno
 A new owned `list of T`, exactly as `flat_map_identity`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.flatten with (calling loom.chunks with [1, 2], 1)      # [1, 2]
 ```

### `flatten_generic`

> **flatten_generic**(nested: list of list of T) -> list of T

 Flattens one level of nesting for any type `T`.

 It is the generic core of `flat_map_identity` and `flatten`.

 ## Parámetros
 - `nested`: the list of lists to flatten; it is only read.

 ## Retorno
 A new owned `list of T` with the elements of every inner list, in order;
 release it with `banish`. The elements are copied, so for element types that
 own memory the caller keeps the original ownership of the inner payloads.

 ## Ejemplo
 ```pengu
 calling loom.flatten_generic of int with (calling loom.chunks with [1, 2, 3], 2)      # [1, 2, 3]
 ```

### `union_sorted`

> **union_sorted**(a: list of T, b: list of T) -> list of T

 Returns the deduplicated union of two ascending lists of any ordered `T`.

 ## Parámetros
 - `a`: the first ascending list; only read.
 - `b`: the second ascending list; only read.

 ## Retorno
 A new owned ascending `list of T` without duplicates; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.union_sorted with [1, 2], [2, 3]      # [1, 2, 3]
 calling loom.union_sorted with ["a", "b"], ["b"]   # ["a", "b"]
 ```

### `intersect_sorted`

> **intersect_sorted**(a: list of T, b: list of T) -> list of T

 Returns the deduplicated intersection of two ascending lists.

 ## Parámetros
 - `a`: the first ascending list; only read.
 - `b`: the second ascending list; only read.

 ## Retorno
 A new owned ascending `list of T` with the values present in both; release
 it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.intersect_sorted with [1, 2, 3], [2, 3]      # [2, 3]
 ```

### `difference_sorted`

> **difference_sorted**(a: list of T, b: list of T) -> list of T

 Returns the deduplicated difference `a \ b` of two ascending lists.

 ## Parámetros
 - `a`: the first ascending list; only read.
 - `b`: the second ascending list; only read.

 ## Retorno
 A new owned ascending `list of T` with the values of `a` not present in
 `b`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.difference_sorted with [1, 2, 3], [2, 3]      # [1]
 ```

### `symmetric_difference_sorted`

> **symmetric_difference_sorted**(a: list of T, b: list of T) -> list of T

 Returns the deduplicated symmetric difference of two ascending lists.

 ## Parámetros
 - `a`: the first ascending list; only read.
 - `b`: the second ascending list; only read.

 ## Retorno
 A new owned ascending `list of T` with the values present in exactly one of
 the inputs; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.symmetric_difference_sorted with [1, 2], [2, 3]      # [1, 3]
 ```

### `find_first`

> **find_first**(items: list of T, target: T) -> maybe int

 Returns the index of the first occurrence of `target`.

 ## Parámetros
 - `items`: the values to search; the list is only read.
 - `target`: the value looked up.

 ## Retorno
 `some index` for the first match, or `maybe none` when `target` is absent.

 ## Ejemplo
 ```pengu
 calling loom.find_first with [10, 20, 10], 10      # some 0
 ```

### `find_last`

> **find_last**(items: list of T, target: T) -> maybe int

 Returns the index of the last occurrence of `target`.

 ## Parámetros
 - `items`: the values to search; the list is only read.
 - `target`: the value looked up.

 ## Retorno
 `some index` for the last match, or `maybe none` when `target` is absent.

 ## Ejemplo
 ```pengu
 calling loom.find_last with [10, 20, 10], 10      # some 2
 ```

### `binary_search`

> **binary_search**(sorted_items: list of T, target: T) -> maybe int

 Searches `sorted_items` (ascending, any ordered `T`) with binary search.

 ## Parámetros
 - `sorted_items`: an ascending list; the list is only read. On an unsorted
   list the result is undefined.
 - `target`: the value looked up.

 ## Retorno
 `some index` when the value is found, `maybe none` otherwise.

 ## Ejemplo
 ```pengu
 calling loom.binary_search with [1, 2, 4, 5], 4      # some 2
 calling loom.binary_search with ["a", "c"], "c"      # some 1
 ```

### `count_if_even`

> **count_if_even**(items: list of T) -> int

 Counts the even elements (negative even values included) for integer `T`.

 ## Parámetros
 - `items`: the values to test; the list is only read.

 ## Retorno
 How many elements satisfy `x % 2 == 0`, as an `int`.

 ## Ejemplo
 ```pengu
 calling loom.count_if_even with [-2, 0, 3]      # 2
 ```

### `count_if_positive`

> **count_if_positive**(items: list of T) -> int

 Counts the strictly positive elements for numeric and ordered `T`.

 ## Parámetros
 - `items`: the values to test; the list is only read.

 ## Retorno
 How many elements satisfy `x > 0`, as an `int`.

 ## Ejemplo
 ```pengu
 calling loom.count_if_positive with [-2, 0, 3]      # 1
 ```

### `index_min`

> **index_min**(items: list of T) -> maybe int

 Returns the index of the first minimum, for any ordered `T`.

 ## Parámetros
 - `items`: the values to scan; the list is only read.

 ## Retorno
 `some index` of the first smallest element, or `maybe none` for `[]`.

 ## Ejemplo
 ```pengu
 calling loom.index_min with [3, 1, 4, 1]      # some 1
 ```

### `index_max`

> **index_max**(items: list of T) -> maybe int

 Returns the index of the first maximum, for any ordered `T`.

 ## Parámetros
 - `items`: the values to scan; the list is only read.

 ## Retorno
 `some index` of the first greatest element, or `maybe none` for `[]`.

 ## Ejemplo
 ```pengu
 calling loom.index_max with [3, 1, 4, 1]      # some 2
 ```

### `insert_at`

> **insert_at**(items: list of T, index: int, value: T) -> list of T

 Returns a copy with `value` inserted at `index`, for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `index`: the insertion position, clamped to `[0, len]`.
 - `value`: the value to insert.

 ## Retorno
 A new owned `list of T` of size `len + 1`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.insert_at with [1, 2, 3], 1, 9      # [1, 9, 2, 3]
 calling loom.insert_at with ["a"], 1, "b"        # ["a", "b"]
 ```

### `remove_at`

> **remove_at**(items: list of T, index: int) -> list of T

 Returns a copy without the element at `index`, for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `index`: the position to drop; an out-of-range index returns a full copy.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.remove_at with [1, 2, 3], 1      # [1, 3]
 ```

### `replace_at`

> **replace_at**(items: list of T, index: int, value: T) -> list of T

 Returns a copy with `value` at `index`, for any element type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `index`: the position to replace; an out-of-range index returns a full
   copy.
 - `value`: the replacement value.

 ## Retorno
 A new owned `list of T` of the same length as `items`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.replace_at with [1, 2, 3], 1, 7      # [1, 7, 3]
 ```

### `swap_at`

> **swap_at**(items: list of T, i: int, j: int) -> list of T

 Returns a copy with the elements at `i` and `j` swapped when both are in
 range.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `i`: the first position.
 - `j`: the second position.

 ## Retorno
 A new owned `list of T` of the same length as `items`; an out-of-range
 index leaves the copy untouched. Release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.swap_at with [1, 2, 3], 0, 2      # [3, 2, 1]
 ```

### `pad_left`

> **pad_left**(items: list of int, target_len: int, fill: int) -> list of int

 Returns a copy padded on the left with `fill` up to `target_len`.

 The signature stays concrete (`list of int`): `fill` has the element type and
 a generic parameter cannot carry a default value that depends on `T` (E0005),
 while dropping the default would break the two-argument call sites.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `target_len`: the target length; a smaller value returns a full copy.
 - `fill`: the padding value (default `0`).

 ## Retorno
 A new owned `list of int` of length `max(len, target_len)`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.pad_left with [1, 2], 4, -1      # [-1, -1, 1, 2]
 ```

### `pad_right`

> **pad_right**(items: list of int, target_len: int, fill: int) -> list of int

 Returns a copy padded on the right with `fill` up to `target_len`.

 The signature stays concrete (`list of int`): `fill` has the element type and
 a generic parameter cannot carry a default value that depends on `T` (E0005),
 while dropping the default would break the two-argument call sites.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `target_len`: the target length; a smaller value returns a full copy.
 - `fill`: the padding value (default `0`).

 ## Retorno
 A new owned `list of int` of length `max(len, target_len)`; release it with
 `banish`.

 ## Ejemplo
 ```pengu
 calling loom.pad_right with [1, 2], 4, -1      # [1, 2, -1, -1]
 ```

### `median`

> **median**(items: list of T) -> maybe float

 Returns the median as a `float`; an even length averages the two middle
 values.

 ## Parámetros
 - `items`: the values to summarise; the list is only read.

 ## Retorno
 `some median`, or `maybe none` for `[]` (the safe-family contract).

 ## Ejemplo
 ```pengu
 calling loom.median with [1, 2, 3, 4]      # some 2.5
 calling loom.median with [1.5, 2.5]        # some 2.0
 ```

### `_median_int`

> **_median_int**(items: list of int) -> maybe float

 Core of `median`.

### `mode`

> **mode**(items: list of T) -> maybe T

 Returns the most frequent value; on a tie the first value to reach the
 maximum wins.

 ## Parámetros
 - `items`: the values to summarise; the list is only read.

 ## Retorno
 `some value`, or `maybe none` for `[]` (the safe-family contract).

 ## Ejemplo
 ```pengu
 calling loom.mode with [1, 2, 2, 3]      # some 2
 ```

### `_mode_int`

> **_mode_int**(items: list of int) -> maybe int

 Core of `mode`.

### `variance`

> **variance**(items: list of T) -> maybe float

 Returns the population variance, dividing by `len`.

 ## Parámetros
 - `items`: the values to summarise; the list is only read.

 ## Retorno
 `some variance` as a `float`, or `maybe none` for `[]`.

 ## Ejemplo
 ```pengu
 calling loom.variance with [1, 2, 3, 4, 5]      # some 2.0
 ```

### `stddev`

> **stddev**(items: list of T) -> maybe float

 Returns the population standard deviation.

 ## Parámetros
 - `items`: the values to summarise; the list is only read.

 ## Retorno
 `some deviation` as a `float` (the `arithmancy.sqrt` of the variance), or
 `maybe none` for `[]`.

 ## Ejemplo
 ```pengu
 calling loom.stddev with [1, 2, 3, 4, 5]      # some 1.414...
 ```

### `percentile`

> **percentile**(items: list of T, p: float) -> maybe float

 Returns the percentile `p` in `[0.0, 100.0]` with linear interpolation.

 ## Parámetros
 - `items`: the values to summarise; the list is only read.
 - `p`: the percentile in `[0.0, 100.0]`; outside that range it yields
   `maybe none`.

 ## Retorno
 `some value` as a `float`, or `maybe none` when the list is empty or `p` is
 out of range.

 ## Ejemplo
 ```pengu
 calling loom.percentile with [1, 2, 3, 4], 50.0      # some 2.5
 ```

### `first_or`

> **first_or**(items: list of T, default_val: T) -> T

 Returns the first element of `items`, or `default_val` when it is empty.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `default_val`: the value returned for an empty list.

 ## Retorno
 A `T` copied out of the list (or `default_val`); no allocation.

 ## Ejemplo
 ```pengu
 calling loom.first_or of int with [1, 2], 0      # 1
 ```

### `generic_take`

> **generic_take**(items: list of T, n: int) -> list of T

 Returns the first `n` elements of a list of any type `T`.

 `n > len` clamps and `n < 0` yields `[]`. A generic body cannot invoke
 another generic, so this `weave` is self-contained.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: how many elements to take.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.generic_take of string with ["a", "b", "c"], 2      # ["a", "b"]
 ```

### `generic_take_last`

> **generic_take_last**(items: list of T, n: int) -> list of T

 Returns the last `n` elements of a list of any type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.
 - `n`: how many trailing elements to keep; `n > len` clamps and `n <= 0`
   yields `[]`.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.generic_take_last of string with ["a", "b", "c"], 2      # ["b", "c"]
 ```

### `generic_reverse`

> **generic_reverse**(items: list of T) -> list of T

 Returns a reversed copy of a list of any type `T`.

 ## Parámetros
 - `items`: the source list; it is only read.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.generic_reverse of string with ["a", "b"]      # ["b", "a"]
 ```

### `generic_chain`

> **generic_chain**(a: list of T, b: list of T) -> list of T

 Concatenates two lists of any type `T`.

 ## Parámetros
 - `a`: the first list, copied first; only read.
 - `b`: the second list, copied after `a`; only read.

 ## Retorno
 A new owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 calling loom.generic_chain of string with ["a"], ["b"]      # ["a", "b"]
 ```

### `generic_index_of`

> **generic_index_of**(items: list of T, target: T) -> int

 Returns the index of the first occurrence of `target` in a list of type `T`,
 or `-1`.

 `T: Par` because the search compares with `==`.

 ## Parámetros
 - `items`: the values to search; the list is only read.
 - `target`: the value looked up.

 ## Retorno
 The zero-based index of the first match, or `-1` when absent.

 ## Ejemplo
 ```pengu
 calling loom.generic_index_of of string with ["a", "b"], "b"      # 1
 ```

### `_slice_shard`

> **_slice_shard**(items: list of T, start_idx: int, end_idx: int) -> list of T

 Generic core: the elements `[start_idx, end_idx)` clamped to the list length.

### `_drop_shard`

> **_drop_shard**(items: list of T, n: int) -> list of T

 Generic core: drops the first `n` elements (`n < 0` copies the whole list).

### `_repeat_shard`

> **_repeat_shard**(value: T, times: int) -> list of T

 Generic core: `value` repeated `times` times (`times <= 0` yields `[]`).

### `_pick_len_int`

> **_pick_len_int**(a: list of int, b: list of int, want_max: bool) -> int

 Length of the shorter (or longer, when `want_max`) of two lists.

### `_apply_op_int`

> **_apply_op_int**(va: int, vb: int, op: int) -> int

 Applies a `zip_with` operator code to a pair of values.

### `_sum_int`

> **_sum_int**(items: list of int) -> int

 Integer sum.

### `_product_int`

> **_product_int**(items: list of int) -> int

 Integer product (`1` for an empty list).

### `_mean_int`

> **_mean_int**(items: list of int) -> float

 Arithmetic mean (`0.0` for an empty list).

### `_variance_int`

> **_variance_int**(items: list of int) -> maybe float

 Population variance (`maybe none` for an empty list).

### `_sorted_asc_int`

> **_sorted_asc_int**(items: list of int) -> list of int

 Ascending copy (insertion sort, stable).

### `_chunk_every_int`

> **_chunk_every_int**(items: list of int, n: int, step: int) -> list of list of int

 Blocks of up to `n` elements taken every `step`.

### `_windows_int`

> **_windows_int**(items: list of int, n: int) -> list of list of int

 Contiguous windows of exactly `n` elements.

### `_rotate_left_int`

> **_rotate_left_int**(items: list of int, k: int) -> list of int

 Rotates left by `k` positions (`n == 0` yields `[]`).

### `_dedup_int`

> **_dedup_int**(items: list of int) -> list of int

 Removes the adjacent duplicates of a sorted list.

### `_union_sorted_int`

> **_union_sorted_int**(a: list of int, b: list of int) -> list of int

 Deduplicated union of two ascending lists (the result is ascending).

### `_intersect_sorted_int`

> **_intersect_sorted_int**(a: list of int, b: list of int) -> list of int

 Deduplicated intersection of two ascending lists.

### `_difference_sorted_int`

> **_difference_sorted_int**(a: list of int, b: list of int) -> list of int

 Deduplicated difference `a \ b` of two ascending lists.

### `_index_of_extreme_int`

> **_index_of_extreme_int**(items: list of int, want_max: bool) -> maybe int

 Index of the first extreme (`maybe none` for an empty list).

### `_is_ordered_int`

> **_is_ordered_int**(items: list of int, strict: bool, ascending: bool) -> bool

 True when `items` is ordered (`strict` requires inequality, `ascending` fixes
 the direction). Lists of fewer than two elements are ordered.

### `_running_sum_int`

> **_running_sum_int**(nums: list of int) -> list of int

 Core of `running_sum`: the prefix sums.

### `_running_extreme_int`

> **_running_extreme_int**(items: list of int, want_max: bool) -> list of int

 Prefix extremes: maxima when `want_max`, minima otherwise.

### `map_ctx`

> **map_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into U) -> list of U

 Applies `f` to every element of `xs`, passing `ctx` on each call.

 ## Parámetros
 - `xs`: the source list; it is only read.
 - `ctx`: the borrowed context; it is passed to every call unchanged.
 - `f`: the callback, `(ref to C, T) -> U`.

 ## Retorno
 A new owned `list of U` with one element per input element; release it with
 `banish`.

 ## Memoria
 No posee `ctx`: el llamador lo libera (si aloca) después de la última
 llamada. El `list` de salida es nuevo y suyo.

 ## Ejemplo
 ```pengu
 rune Scaler:
     factor as int

 weave scale with s as ref to Scaler, x as int into int:
     return s->factor * x

 var s as Scaler is with factor is 3
 var xs as list of int is [1, 2, 3]
 var ys as list of int is calling loom.map_ctx with xs, (sigil of s), scale
 # ys == [3, 6, 9]
 ```

### `filter_ctx`

> **filter_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into bool) -> list of T

 Keeps the elements for which `f` returns `true`, passing `ctx` on each call.

 ## Parámetros
 - `xs`: the source list; it is only read.
 - `ctx`: the borrowed context; it is passed to every call unchanged.
 - `f`: the predicate, `(ref to C, T) -> bool`.

 ## Retorno
 A new owned `list of T` with the matching elements, in input order; release
 it with `banish`.

 ## Memoria
 El `list` de salida es nuevo; los elementos se copian tal cual (un `string`
 o `list` dentro de `T` sigue siendo un préstamo, no una copia profunda).
 `ctx` no se posee.

 ## Ejemplo
 ```pengu
 weave is_multiple with m as ref to int, x as int into bool:
     return (x % (essence of m)) == 0

 var m as int is 3
 var xs as list of int is [1, 2, 3, 4, 5, 6]
 calling loom.filter_ctx with xs, (sigil of m), is_multiple    # [3, 6]
 ```

### `fold_ctx`

> **fold_ctx**(xs: list of T, init: U, ctx: ref to C, f: weave with c: ref to C, acc: U, x: T into U) -> U

 Left-folds `xs` from `init`, passing `ctx` on each call.

 ## Parámetros
 - `xs`: the source list; it is only read.
 - `init`: the initial accumulator; its type may differ from the element type.
 - `ctx`: the borrowed context; it is passed to every call unchanged.
 - `f`: the step, `(ref to C, U, T) -> U`.

 ## Retorno
 The final accumulator. No list is allocated.

 ## Memoria
 No aloca memoria. Si `U` posee memoria, `init` y cada resultado de `f` se
 mueven al acumulador; el llamador sigue siendo el dueño de `init`.

 ## Ejemplo
 ```pengu
 rune Separator:
     sep as string

 weave join_step with s as ref to Separator, acc as string, x as int into string:
     return "{acc}{s->sep}{x}"

 var s as Separator is with sep is "-"
 calling loom.fold_ctx with [1, 2, 3], "0", (sigil of s), join_step    # "0-1-2-3"
 ```

### `for_each_ctx`

> **for_each_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into void) -> void

 Calls `f` on every element of `xs`, passing `ctx` on each call.

 Use it for side effects (accumulating into the context, printing, updating a
 counter). The callback returns `void`.

 ## Parámetros
 - `xs`: the source list; it is only read.
 - `ctx`: the borrowed context; it is passed to every call unchanged.
 - `f`: the callback, `(ref to C, T) -> void`.

 ## Retorno
 Nothing.

 ## Memoria
 No aloca memoria por sí misma. El `ctx` puede mutar; si el callback aloca,
 el llamador es responsable de liberarlo.

 ## Ejemplo
 ```pengu
 rune Counter:
     total as int

 weave add_up with c as ref to Counter, x as int into void:
     set c->total is c->total + x

 var c as Counter is with total is 0
 calling loom.for_each_ctx with [1, 2, 3], (sigil of c), add_up
 # c.total == 6
 ```

### `zip_with_ctx`

> **zip_with_ctx**(xs: list of T, ys: list of U, ctx: ref to C, f: weave with c: ref to C, x: T, y: U into V) -> list of V

 Combines `xs` and `ys` element by element with `f`, passing `ctx` on each
 call; stops at the shorter list, exactly like `zip_with_op`.

 ## Parámetros
 - `xs`: the left operands; only read.
 - `ys`: the right operands; only read.
 - `ctx`: the borrowed context; it is passed to every call unchanged.
 - `f`: the combiner, `(ref to C, T, U) -> V`.

 ## Retorno
 A new owned `list of V` of size `min(len(xs), len(ys))`; release it with
 `banish`.

 ## Memoria
 El `list` de salida es nuevo; las dos entradas solo se leen. `ctx` no se posee.

 ## Ejemplo
 ```pengu
 weave add_bias with bias as ref to int, x as int, y as int into int:
     return x + y + (essence of bias)

 var bias as int is 10
 calling loom.zip_with_ctx with [1, 2], [3], (sigil of bias), add_bias    # [14]
 ```

### `find_first_ctx`

> **find_first_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into bool) -> maybe T

 Returns the first element for which `f` returns `true`, passing `ctx`.

 Unlike `find_first` (equality search that returns an **index**), this is a
 predicate search that returns the **element** itself. The context is the
 only thing `f` needs beyond the element, so it is passed on every call.

 ## Parámetros
 - `xs`: the source list; only read.
 - `ctx`: the borrowed context; passed to every call unchanged.
 - `f`: the predicate, `(ref to C, T) -> bool`.

 ## Retorno
 `some element` for the first match, or `maybe none` when nothing matches.

 ## Memoria
 No aloca memoria. El elemento se copia en el `maybe`; si `T` presta memoria,
 el préstamo sigue siendo del llamador.

 ## Ejemplo
 ```pengu
 weave over with limit as ref to int, x as int into bool:
     return x > (essence of limit)

 var limit as int is 10
 calling loom.find_first_ctx with [1, 12, 20], (sigil of limit), over    # some 12
 ```

### `any_ctx`

> **any_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into bool) -> bool

 `true` when `f` returns `true` for at least one element of `xs`.

 ## Parámetros
 - `xs`: the source list; only read.
 - `ctx`: the borrowed context; passed to every call unchanged.
 - `f`: the predicate, `(ref to C, T) -> bool`.

 ## Retorno
 `false` for an empty list (there is no witness). Stops at the first match.

 ## Memoria
 No aloca memoria.

 ## Ejemplo
 ```pengu
 calling loom.any_ctx with [1, 2, 3], (sigil of limit), over    # true
 ```

### `all_ctx`

> **all_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into bool) -> bool

 `true` when `f` returns `true` for every element of `xs`.

 ## Parámetros
 - `xs`: the source list; only read.
 - `ctx`: the borrowed context; passed to every call unchanged.
 - `f`: the predicate, `(ref to C, T) -> bool`.

 ## Retorno
 `true` for an empty list (the vacuous truth). Stops at the first failure.

 ## Memoria
 No aloca memoria.

 ## Ejemplo
 ```pengu
 calling loom.all_ctx with [12, 20], (sigil of limit), over    # true
 ```

### `partition_ctx`

> **partition_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into bool) -> (list of T, list of T)

 Splits `xs` in two: the elements matching `f` and the ones that do not,
 preserving input order in both halves.

 ## Parámetros
 - `xs`: the source list; only read.
 - `ctx`: the borrowed context; passed to every call unchanged.
 - `f`: the predicate, `(ref to C, T) -> bool`.

 ## Retorno
 A fresh tuple `(matching, rest)`. Both lists are owned by the caller: release
 each one with `banish` (a tuple of lists is not itself released).

 ## Memoria
 Dos `list` nuevos, en el orden de entrada. `ctx` no se posee.

 ## Ejemplo
 ```pengu
 let (yes, no) is calling loom.partition_ctx with xs, (sigil of m), is_multiple
 ```

### `filter_map_ctx`

> **filter_map_ctx**(xs: list of T, ctx: ref to C, f: weave with c: ref to C, x: T into maybe U) -> list of U

 Maps and filters in one pass: keeps the `some` results of `f` and drops the
 `none`s, passing `ctx` on every call.

 ## Parámetros
 - `xs`: the source list; only read.
 - `ctx`: the borrowed context; passed to every call unchanged.
 - `f`: the callback, `(ref to C, T) -> maybe U`.

 ## Retorno
 A new owned `list of U` with the present results, in input order; release it
 with `banish`.

 ## Memoria
 El `list` de salida es nuevo; `ctx` no se posee.

 ## Ejemplo
 ```pengu
 weave half_if_even with m as ref to int, x as int into maybe int:
     if (x % 2) == 0:
         return some (x * (essence of m))
     return maybe none

 calling loom.filter_map_ctx with [1, 2, 3, 4], (sigil of m), half_if_even    # [6, 12]
 ```

### `_ctx_add`

> **_ctx_add**(offset: ref to int, x: int) -> int

 Adds `offset` to its element.

### `_ctx_above`

> **_ctx_above**(limit: ref to int, x: int) -> bool

 True when `x` is above `limit`.

### `_ctx_fold_add`

> **_ctx_fold_add**(offset: ref to int, acc: int, x: int) -> int

 Folds by adding the element and the context offset to the accumulator.

### `_ctx_collect`

> **_ctx_collect**(c: ref to _CtxCollector, x: int) -> void

 Appends the element to the rune's list and adds it to the rune's total.

### `_ctx_half_if_even`

> **_ctx_half_if_even**(factor: ref to int, x: int) -> maybe int

 Multiplies an even element by `factor` and drops an odd one.

### `_ctx_add_pair`

> **_ctx_add_pair**(bias: ref to int, x: int, y: int) -> int

 Adds two elements and the context bias.

### `_ctx_word_for`

> **_ctx_word_for**(word: ref to string, x: int) -> string

 Returns the context word for a positive element, `"other"` otherwise.

### `_CtxCollector`

> rune _CtxCollector

```pengu
    total as int
    items as list of int
```

 A mutable accumulator used by the `for_each_ctx` test.

### `_expect`

> **_expect**(cond: bool, label: string) -> void

 Internal harness: panics with `label` when `cond` is false.

### `_expect_eq`

> **_expect_eq**(actual: T, expected: T, label: string) -> void

 Internal harness: scalar equality (int, float, bool).

### `_expect_float_near`

> **_expect_float_near**(actual: float, expected: float, tolerance: float, label: string) -> void

 Internal harness: float equality within a tolerance.

### `_expect_eq_ints`

> **_expect_eq_ints**(actual: list of int, expected: list of int, label: string) -> void

 Internal harness: integer-list equality (length and elements).

### `_expect_eq_chunks`

> **_expect_eq_chunks**(actual: list of list of int, expected: list of list of int, label: string) -> void

 Internal harness: equality of lists of integer lists.

### `_expect_eq_shard_list`

> **_expect_eq_shard_list**(actual: list of T, expected: list of T, label: string) -> void

 Internal harness: equality of lists of any comparable `T` (length and elements).

### `_expect_some`

> **_expect_some**(m: maybe T, expected: T, label: string) -> void

 Internal harness: `maybe T` is present and equal to `expected`.

### `_expect_none`

> **_expect_none**(m: maybe T, label: string) -> void

 Internal harness: `maybe T` is absent.

### `_expect_pair`

> **_expect_pair**(first_expected: int, second_expected: int, label: string, pair: Pair__int__int) -> void

 Internal harness: integer `Pair` (the `Pair` argument goes last because of the parser).

### `_expect_some_pair`

> **_expect_some_pair**(first_expected: int, second_expected: int, label: string, m: maybe Pair__int__int) -> void

 Internal harness: `maybe Pair` is present and matches both values.

### `LoomUserId`

> rune LoomUserId

```pengu
    raw as int
```

 A nominal integer wrapper used by the ordering tests of this module.

 It is a `rune`, not a `seal`: a seal shares its method table with the
 primitive it wraps, so binding `Ordered` to a sealed `int` collides with
 atlas' own `bind int with Ordered`. The rune keeps `cmp` on its own type.

### `cmp`

> **cmp**(other: LoomUserId) -> int

_Undocumented._

### `_uid`

> **_uid**(raw: int) -> LoomUserId

 Builds a `LoomUserId` for the ordering tests.

### `"range builds the half-open interval"`

> test "range builds the half-open interval"

 Sequence generation

### `"range with a step greater than one"`

> test "range with a step greater than one"

_Undocumented._

### `"range with a negative step walks backwards"`

> test "range with a negative step walks backwards"

_Undocumented._

### `"range with a zero step returns empty"`

> test "range with a zero step returns empty"

_Undocumented._

### `"range with start greater than end and a positive step is empty"`

> test "range with start greater than end and a positive step is empty"

_Undocumented._

### `"unfold_range produces count elements"`

> test "unfold_range produces count elements"

_Undocumented._

### `"unfold_range with a negative step descends"`

> test "unfold_range with a negative step descends"

_Undocumented._

### `"unfold_range with a non-positive count returns empty"`

> test "unfold_range with a non-positive count returns empty"

_Undocumented._

### `"repeat repeats the value times times"`

> test "repeat repeats the value times times"

_Undocumented._

### `"repeat with zero times returns empty"`

> test "repeat with zero times returns empty"

_Undocumented._

### `"repeat with a negative times returns empty"`

> test "repeat with a negative times returns empty"

_Undocumented._

### `"take returns the first n elements"`

> test "take returns the first n elements"

 Slicing and composition

### `"take clamps when n exceeds the length"`

> test "take clamps when n exceeds the length"

_Undocumented._

### `"take with zero n returns empty"`

> test "take with zero n returns empty"

_Undocumented._

### `"take with a negative n returns empty"`

> test "take with a negative n returns empty"

_Undocumented._

### `"skip drops the first n elements"`

> test "skip drops the first n elements"

_Undocumented._

### `"skip with n greater than the length returns empty"`

> test "skip with n greater than the length returns empty"

_Undocumented._

### `"skip with zero n returns a copy"`

> test "skip with zero n returns a copy"

_Undocumented._

### `"take of the empty list returns empty"`

> test "take of the empty list returns empty"

_Undocumented._

### `"skip of the empty list returns empty"`

> test "skip of the empty list returns empty"

_Undocumented._

### `"skip with a negative n behaves like zero"`

> test "skip with a negative n behaves like zero"

_Undocumented._

### `"chain concatenates two lists"`

> test "chain concatenates two lists"

_Undocumented._

### `"chain with an empty second list returns the first"`

> test "chain with an empty second list returns the first"

_Undocumented._

### `"chunks splits into exact blocks"`

> test "chunks splits into exact blocks"

 Blocks and windows

### `"chunks leaves the last block short"`

> test "chunks leaves the last block short"

_Undocumented._

### `"chunks with a non-positive n returns empty"`

> test "chunks with a non-positive n returns empty"

_Undocumented._

### `"chunks with n greater than the length returns one block"`

> test "chunks with n greater than the length returns one block"

_Undocumented._

### `"windows with zero n returns empty"`

> test "windows with zero n returns empty"

_Undocumented._

### `"chunk_every overlaps when step is smaller than n"`

> test "chunk_every overlaps when step is smaller than n"

_Undocumented._

### `"chunk_every with step equal to n matches chunks"`

> test "chunk_every with step equal to n matches chunks"

_Undocumented._

### `"chunk_every with step greater than n skips elements"`

> test "chunk_every with step greater than n skips elements"

_Undocumented._

### `"chunk_every with non-positive n or step returns empty"`

> test "chunk_every with non-positive n or step returns empty"

_Undocumented._

### `"windows produces every complete window"`

> test "windows produces every complete window"

_Undocumented._

### `"windows with n equal to the length returns one window"`

> test "windows with n equal to the length returns one window"

_Undocumented._

### `"windows with n greater than the length returns empty"`

> test "windows with n greater than the length returns empty"

_Undocumented._

### `"windows with zero n or an empty list returns empty"`

> test "windows with zero n or an empty list returns empty"

_Undocumented._

### `"windowed delegates to the concrete windows core"`

> test "windowed delegates to the concrete windows core"

 `windowed` is not called unqualified here on purpose: in a bundle that imports
 both `std.loom` and `std.tally`, an unqualified `windowed` resolves to tally's
 generic `windowed shard T` and the checker cannot infer `T` (E0005). The public
 wrapper is covered by `tests/stdlib/test_loom.py`; these tests pin the
 implementation it delegates to.

### `"windowed with n greater than the length returns empty"`

> test "windowed with n greater than the length returns empty"

_Undocumented._

### `"pairwise returns overlapping pairs"`

> test "pairwise returns overlapping pairs"

_Undocumented._

### `"pairwise with fewer than two elements returns empty"`

> test "pairwise with fewer than two elements returns empty"

_Undocumented._

### `"pairwise_pairs returns adjacent Pair values"`

> test "pairwise_pairs returns adjacent Pair values"

_Undocumented._

### `"pairwise_pairs with one element returns empty"`

> test "pairwise_pairs with one element returns empty"

_Undocumented._

### `"pairwise_pairs keeps both components in order"`

> test "pairwise_pairs keeps both components in order"

_Undocumented._

### `"sum adds every element"`

> test "sum adds every element"

 Folds

### `"sum of the empty list is zero"`

> test "sum of the empty list is zero"

_Undocumented._

### `"product_num multiplies every element"`

> test "product_num multiplies every element"

_Undocumented._

### `"product_num of the empty list is one"`

> test "product_num of the empty list is one"

_Undocumented._

### `"max_int returns the greatest element"`

> test "max_int returns the greatest element"

_Undocumented._

### `"min_int returns the smallest element"`

> test "min_int returns the smallest element"

_Undocumented._

### `"max_int and min_int of the empty list return zero"`

> test "max_int and min_int of the empty list return zero"

_Undocumented._

### `"max_int and min_int with negative values"`

> test "max_int and min_int with negative values"

_Undocumented._

### `"min_max returns a min-max Pair"`

> test "min_max returns a min-max Pair"

_Undocumented._

### `"min_max of one element repeats the value"`

> test "min_max of one element repeats the value"

_Undocumented._

### `"min_max of the empty list returns none"`

> test "min_max of the empty list returns none"

_Undocumented._

### `"min_max pairs the smallest and the largest element"`

> test "min_max pairs the smallest and the largest element"

_Undocumented._

### `"mean computes the arithmetic average"`

> test "mean computes the arithmetic average"

_Undocumented._

### `"mean of the empty list is zero"`

> test "mean of the empty list is zero"

_Undocumented._

### `"mean of a single element is that element"`

> test "mean of a single element is that element"

_Undocumented._

### `"running_sum of one element is that element"`

> test "running_sum of one element is that element"

_Undocumented._

### `"sum_squares adds the squares"`

> test "sum_squares adds the squares"

_Undocumented._

### `"sum_squares of the empty list is zero"`

> test "sum_squares of the empty list is zero"

_Undocumented._

### `"running_sum accumulates the prefix sums"`

> test "running_sum accumulates the prefix sums"

 Stateful folds, differences and scanning

### `"running_max and running_min accumulate the extremes"`

> test "running_max and running_min accumulate the extremes"

_Undocumented._

### `"the prefixes of an empty list are empty"`

> test "the prefixes of an empty list are empty"

_Undocumented._

### `"differences computes the adjacent differences"`

> test "differences computes the adjacent differences"

_Undocumented._

### `"differences of an empty or one-element list is empty"`

> test "differences of an empty or one-element list is empty"

_Undocumented._

### `"scan_left accumulates with a weave value"`

> test "scan_left accumulates with a weave value"

_Undocumented._

### `"any_zero detects zero"`

> test "any_zero detects zero"

 Predicates

### `"any_zero of the empty list is false"`

> test "any_zero of the empty list is false"

_Undocumented._

### `"all_equal recognises repeated elements"`

> test "all_equal recognises repeated elements"

_Undocumented._

### `"all_equal of an empty or one-element list is true"`

> test "all_equal of an empty or one-element list is true"

_Undocumented._

### `"the order predicates recognise strict sequences"`

> test "the order predicates recognise strict sequences"

_Undocumented._

### `"the order predicates accept ties and short lists"`

> test "the order predicates accept ties and short lists"

_Undocumented._

### `"is_partitioned separates the matching prefix"`

> test "is_partitioned separates the matching prefix"

_Undocumented._

### `"zip_with adds by default"`

> test "zip_with adds by default"

 Transformations and combinations

### `"zip_with applies subtraction, product, minimum and maximum"`

> test "zip_with applies subtraction, product, minimum and maximum"

_Undocumented._

### `"zip_with stops at the shorter list"`

> test "zip_with stops at the shorter list"

_Undocumented._

### `"zip_with with an unknown operator adds"`

> test "zip_with with an unknown operator adds"

_Undocumented._

### `"zip_with_op combines with a weave value"`

> test "zip_with_op combines with a weave value"

_Undocumented._

### `"zip_longest fills with fill up to the longer list"`

> test "zip_longest fills with fill up to the longer list"

_Undocumented._

### `"zip_longest with equal-length lists does not fill"`

> test "zip_longest with equal-length lists does not fill"

_Undocumented._

### `"enumerate returns index-value pairs"`

> test "enumerate returns index-value pairs"

_Undocumented._

### `"enumerate_pairs returns Pair values in order"`

> test "enumerate_pairs returns Pair values in order"

_Undocumented._

### `"enumerate and enumerate_pairs of an empty list are empty"`

> test "enumerate and enumerate_pairs of an empty list are empty"

_Undocumented._

### `"interleave alternates up to the shorter list"`

> test "interleave alternates up to the shorter list"

_Undocumented._

### `"round_robin takes turns over every list"`

> test "round_robin takes turns over every list"

_Undocumented._

### `"rotate_left moves the first element to the end"`

> test "rotate_left moves the first element to the end"

_Undocumented._

### `"rotate_right moves the last element to the front"`

> test "rotate_right moves the last element to the front"

_Undocumented._

### `"rotations wrap around with a large or negative k"`

> test "rotations wrap around with a large or negative k"

_Undocumented._

### `"intersperse inserts the separator between elements"`

> test "intersperse inserts the separator between elements"

_Undocumented._

### `"intersperse of an empty or one-element list adds nothing"`

> test "intersperse of an empty or one-element list adds nothing"

_Undocumented._

### `"flat_map_identity flattens one level of nesting"`

> test "flat_map_identity flattens one level of nesting"

_Undocumented._

### `"flat_map_identity matches the generic core"`

> test "flat_map_identity matches the generic core"

_Undocumented._

### `"flatten_generic flattens lists of any type"`

> test "flatten_generic flattens lists of any type"

_Undocumented._

### `"the generic flatten core with empty lists gives empty"`

> test "the generic flatten core with empty lists gives empty"

_Undocumented._

### `"union_sorted merges ascending lists and deduplicates"`

> test "union_sorted merges ascending lists and deduplicates"

 Sets over sorted lists

### `"the set operations with empty lists are empty"`

> test "the set operations with empty lists are empty"

_Undocumented._

### `"intersect_sorted keeps the common part"`

> test "intersect_sorted keeps the common part"

_Undocumented._

### `"difference_sorted and symmetric_difference_sorted keep what is exclusive"`

> test "difference_sorted and symmetric_difference_sorted keep what is exclusive"

_Undocumented._

### `"find_first and find_last locate the occurrences"`

> test "find_first and find_last locate the occurrences"

 Search and indices

### `"find and binary_search return none when they miss"`

> test "find and binary_search return none when they miss"

_Undocumented._

### `"binary_search finds the index in sorted lists"`

> test "binary_search finds the index in sorted lists"

_Undocumented._

### `"count_if_even counts the even values, negative ones included"`

> test "count_if_even counts the even values, negative ones included"

_Undocumented._

### `"count_if_positive counts the strictly positive values"`

> test "count_if_positive counts the strictly positive values"

_Undocumented._

### `"index_min and index_max locate the first extreme"`

> test "index_min and index_max locate the first extreme"

_Undocumented._

### `"index_min of the empty list returns none"`

> test "index_min of the empty list returns none"

_Undocumented._

### `"insert_at inserts at the requested position"`

> test "insert_at inserts at the requested position"

 Structural editing

### `"remove_at removes the given element"`

> test "remove_at removes the given element"

_Undocumented._

### `"remove_at with an out-of-range index copies the list"`

> test "remove_at with an out-of-range index copies the list"

_Undocumented._

### `"replace_at with an out-of-range index copies the list"`

> test "replace_at with an out-of-range index copies the list"

_Undocumented._

### `"replace_at replaces the given element"`

> test "replace_at replaces the given element"

_Undocumented._

### `"swap_at swaps two positions"`

> test "swap_at swaps two positions"

_Undocumented._

### `"swap_at with an out-of-range index copies the list"`

> test "swap_at with an out-of-range index copies the list"

_Undocumented._

### `"intersperse of a single element returns the element"`

> test "intersperse of a single element returns the element"

_Undocumented._

### `"pad_left and pad_right pad the ends"`

> test "pad_left and pad_right pad the ends"

_Undocumented._

### `"median with an odd length"`

> test "median with an odd length"

 Statistics

### `"median with an even length averages the middle values"`

> test "median with an even length averages the middle values"

_Undocumented._

### `"median of the empty list is none"`

> test "median of the empty list is none"

_Undocumented._

### `"mode returns the most frequent value"`

> test "mode returns the most frequent value"

_Undocumented._

### `"mode of the empty list is none"`

> test "mode of the empty list is none"

_Undocumented._

### `"variance and stddev measure the spread"`

> test "variance and stddev measure the spread"

_Undocumented._

### `"variance of the empty list is none"`

> test "variance of the empty list is none"

_Undocumented._

### `"percentile interpolates linearly"`

> test "percentile interpolates linearly"

_Undocumented._

### `"percentile out of range returns none"`

> test "percentile out of range returns none"

_Undocumented._

### `"first_or returns the first element or the default"`

> test "first_or returns the first element or the default"

 Generic core and version

### `"first_or is generic for strings too"`

> test "first_or is generic for strings too"

_Undocumented._

### `"generic_take and generic_take_last slice string lists"`

> test "generic_take and generic_take_last slice string lists"

_Undocumented._

### `"generic_reverse and generic_chain work with strings"`

> test "generic_reverse and generic_chain work with strings"

_Undocumented._

### `"generic_index_of finds the target or returns minus one"`

> test "generic_index_of finds the target or returns minus one"

_Undocumented._

### `"product_num multiplies float lists"`

> test "product_num multiplies float lists"

 Widened element types (2.2.0)

### `"sum_squares and differences widen to float lists"`

> test "sum_squares and differences widen to float lists"

_Undocumented._

### `"max_int and min_int order float lists"`

> test "max_int and min_int order float lists"

_Undocumented._

### `"running_max and running_min widen to float lists"`

> test "running_max and running_min widen to float lists"

_Undocumented._

### `"chunks and rotate_left work with strings"`

> test "chunks and rotate_left work with strings"

_Undocumented._

### `"windows and chunk_every widen to float lists"`

> test "windows and chunk_every widen to float lists"

_Undocumented._

### `"enumerate keeps the element type of a float list"`

> test "enumerate keeps the element type of a float list"

_Undocumented._

### `"pairwise_pairs and intersperse work with strings"`

> test "pairwise_pairs and intersperse work with strings"

_Undocumented._

### `"insert_at and replace_at work with strings"`

> test "insert_at and replace_at work with strings"

_Undocumented._

### `"union_sorted and intersect_sorted merge string lists"`

> test "union_sorted and intersect_sorted merge string lists"

_Undocumented._

### `"binary_search and the order predicates accept strings"`

> test "binary_search and the order predicates accept strings"

_Undocumented._

### `"find_first and all_equal compare strings"`

> test "find_first and all_equal compare strings"

_Undocumented._

### `"index_min and index_max accept strings"`

> test "index_min and index_max accept strings"

_Undocumented._

### `"count_if_even and count_if_positive accept i64 lists"`

> test "count_if_even and count_if_positive accept i64 lists"

_Undocumented._

### `"the generic helpers widen to i64 lists"`

> test "the generic helpers widen to i64 lists"

_Undocumented._

### `"a rune bound to Ordered sorts through the generic entry points"`

> test "a rune bound to Ordered sorts through the generic entry points"

_Undocumented._

### `"map_ctx applies the callback with the context"`

> test "map_ctx applies the callback with the context"

 Context-taking pipelines (`*_ctx`)

### `"filter_ctx keeps the elements the predicate accepts"`

> test "filter_ctx keeps the elements the predicate accepts"

_Undocumented._

### `"fold_ctx threads the context through every step"`

> test "fold_ctx threads the context through every step"

_Undocumented._

### `"for_each_ctx can mutate the context"`

> test "for_each_ctx can mutate the context"

_Undocumented._

### `"zip_with_ctx truncates at the shorter list"`

> test "zip_with_ctx truncates at the shorter list"

_Undocumented._

### `"find_first_ctx returns the first matching element"`

> test "find_first_ctx returns the first matching element"

_Undocumented._

### `"any_ctx and all_ctx handle the empty list"`

> test "any_ctx and all_ctx handle the empty list"

_Undocumented._

### `"partition_ctx splits in input order"`

> test "partition_ctx splits in input order"

_Undocumented._

### `"filter_map_ctx keeps the some results"`

> test "filter_map_ctx keeps the some results"

_Undocumented._

### `"a string context works in map_ctx"`

> test "a string context works in map_ctx"

_Undocumented._

### `"LOOM_VERSION is version 3.0.3"`

> test "LOOM_VERSION is version 3.0.3"

_Undocumented._

