# `std.loom` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `LOOM_VERSION`.
>
> Module revision: **`2.12.0`** (`LOOM_VERSION`).
> Source: [`std/loom.pengu`](../std/loom.pengu).

`loom` is the **safe** family of list helpers: sequence generation, slicing,
blocks and windows, folds, predicates, transformations and combinations, set
operations over sorted lists, search and indices, pure structural editing,
statistics, and a small `shard T` generic core. All public entry points are
**module functions** (`calling loom.chunks with xs, 2`); the module declares
**no `enchanting` block on purpose**, so it never invades the list methods of
`std.tally` (see the named-exception section below).

It imports `std.arithmancy` (`arithmancy.sqrt` for `stddev`; `gcd` / `is_prime`
appear in the `_with_op` and predicate examples), `std.atlas` (`Ordered` for every
ordering entry point), `std.oracle` (`Pair`) and `std.spark` (only the private
`_expect*` test harness calls `spark.panic`). Since `2.2.0` the surface is
**generic in the element type** (`weave chunks shard T with items as list of T,
n as int`): a `list of int` call behaves exactly as in 0.14.x–2.1.0, while
`float`, `i64`, `string` and bound `seal`/`rune` elements work wherever the
operation is meaningful. The `int`-defaulted entry points (`pad_left`,
`pad_right`, `zip_longest`) stay concrete. The module is a leaf consumer: no
other module in `std/` imports `loom`, so it may not grow a dependency that would
close a cycle through `tally`.

The module declares `insignia loom_`, so every module function is emitted with a
C prefix (`loom_sum`, `loom_min_max`, …). That is what makes a **qualified
generic call** resolve to the correct monomorphisation when a program uses
several element types: `calling loom.sum with floats` names the exact
instantiation instead of relying on a bare `sum` symbol (the compiler's old
"only one match" heuristic resolved the wrong C symbol as soon as two
specialisations existed).

Because it is the safe family, absence is representable: `mode`, `median`,
`min_max`, `variance`, `stddev` and `percentile` return `maybe ...` and answer
`none` on an empty list. `mean` is the one deliberate sentinel in the family:
it returns a `float` (`0.0` on an empty list) because it must keep the
fraction (`calling loom.mean with [1, 2]` is `1.5`).

## Relationship with `std.tally` (named exception)

`std.loom` and `std.tally` deliberately share 15 public names with **different**
contracts: `tally` is the *sentinel* family (an empty list collapses to a natural
identity; `mean` truncates to `int`) and `loom` is the *safe* family (`mean` is a
`float`; `mode`/`median`/`min_max` return `maybe none` on an empty list). This is
a documented, deliberate exception — `LANGUAGE.md` §19.1.1 and
`PenguScriptGuideSpanish.md` §15 — not drift. The two modules are not merged, no
symbol is renamed and no `_safe`/`_sentinel` suffix is introduced.

The 15 shared names are `mean`, `median`, `mode`, `min_max`, `sum`, `flatten`,
`take`, `windowed`, `zip_with`, `running_sum`, `scan_left`, `repeat`,
`enumerate_pairs`, `is_sorted_asc` and `is_sorted_desc`. Keeping them distinct
is why `loom` has no `enchanting` block: an enchantment here would collide with
`tally`'s methods and silently merge the two contracts. Since `2.2.0` both
families are generic over the element type (`shard T` with the bound each
operation needs), and the contracts above hold for `float`, `i64`, `string` and
bound `seal`/`rune` elements too.

## Element-type bounds

| Bound | Meaning | Operations |
|---|---|---|
| *(none)* `shard T` | the body only moves or copies elements | `repeat`, `take`, `skip`, `chain`, `chunks`, `chunk_every`, `windows`, `windowed`, `pairwise`, `pairwise_pairs`, `zip_with_op`, `interleave`, `round_robin`, `rotate_left`, `rotate_right`, `intersperse`, `flat_map_identity`, `flatten`, `flatten_generic`, `is_partitioned`, `insert_at`, `remove_at`, `replace_at`, `swap_at`, `enumerate_pairs`, `first_or`, the `generic_*` cores |
| `T: Num` | arithmetic (`+ - * / %`, `0`/`1`) | `sum`, `product_num`, `mean`, `sum_squares`, `running_sum`, `differences`, `scan_left`, `enumerate` |
| `T: Ordered` | **order comparisons through the concept** | `max_int`, `min_int`, `min_max`, `running_max`, `running_min`, `is_strictly_asc`, `is_strictly_desc`, `is_sorted_asc`, `is_sorted_desc`, `union_sorted`, `intersect_sorted`, `difference_sorted`, `symmetric_difference_sorted`, `binary_search`, `index_min`, `index_max` |
| `T: Par` | `==` / `!=` only | `any_zero`, `all_equal`, `find_first`, `find_last` |
| `T: Integrum and T: Par` | `% 2` plus equality | `count_if_even` |
| `T: Num and T: Ordo` | numeric, ordered by the built-in `Ordo` | `count_if_positive`, `median`, `mode`, `variance`, `stddev`, `percentile` |
| `T: Num and T: Ordered` | numeric **and** orderable through the concept | `zip_with` (its op codes cover arithmetic and `min`/`max`) |
| `list of int` only | a `T`-dependent `is` default is impossible | `range`, `unfold_range`, `pad_left`, `pad_right`, `zip_longest` |

### Why the ordering operations need `T: Ordered`

A generic body lowers `>` and `<` to a raw C comparison, which does not compile
for `PenguString`, and a concrete string operand rejects `>` with `E0005`.
`std.atlas` therefore ships `concept Ordered shard T` (a `cmp` method returning
`0`, `-1` or `1`) and the `bind`s for `int`, `i32`, `i64`, `float`, `f32`, `f64`
and `string`. Every ordering entry point above is bounded `where T: Ordered` and
compares with `calling a.cmp with b`, which is what lets
`calling loom.min_max with words`, `calling loom.binary_search with words, w` and
`calling loom.union_sorted with a, b` work on `list of string`. User types opt in
with an **unqualified** `bind MyType with Ordered:` after `import std.atlas`
(see the test-only `LoomUserId` below). Equality (`==`) works generically on
strings, so the `Par` group needs no concept. The `Ordo`-bounded group
(`median`, `percentile`, …) is numeric by construction and is not string-capable.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every function returning `string`-free `list of T` / `list of int` | new owned list | `banish` / `defer banish` |
| `chunks`, `chunk_every`, `windows`, `windowed`, `pairwise`, `enumerate`, `zip_longest` | owned outer list of owned inner lists | `banish` each inner list, then the outer |
| `pairwise_pairs`, `enumerate_pairs`, `list of Pair` results | owned flat rune | one `banish` |
| `min_max` | `maybe Pair` (payload is a flat rune) | nothing to release |
| `mode`, `index_min`, `index_max`, `find_first`, `find_last`, `binary_search` | `maybe int` / `maybe T` scalar box | nothing to release |
| every other scalar (`int`, `bool`, `float`, `maybe float`) | value | nothing to release |
| all parameters (`items`, `a`, `b`, `n`, …) | borrowed | never `banish`; `loom` never mutates or frees an input |

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `LOOM_VERSION` | `string` | `"2.2.0"` | Revision of the **loom API**. Bumps only when a signature on this page changes; it is not the toolchain version. |

## Generation

| Symbol | Signature | Semantics |
|---|---|---|
| `range` | `(int, int, int is 1) -> list of int` | `[start, end)` advancing by `step`; positive walks up, negative walks down, `step == 0` gives `[]`. Concrete: its literals are `int`. |
| `repeat shard T` | `(value: T, times: int) -> list of T` | `value` repeated `times` times; `times <= 0` gives `[]`. |
| `unfold_range` | `(int, int, int is 1) -> list of int` | Exactly `count` elements `start, start + step, …`; `count <= 0` gives `[]`. Counts elements, unlike `range`. |

## Slices

| Symbol | Signature | Semantics |
|---|---|---|
| `take shard T` | `(items: list of T, n: int) -> list of T` | First `n` elements; `n > len` clamps to the whole list and `n < 0` gives `[]`. |
| `skip shard T` | `(items: list of T, n: int) -> list of T` | Elements from index `n` on; `n < 0` behaves like `0`, `n > len` gives `[]`. |
| `chain shard T` | `(a: list of T, b: list of T) -> list of T` | New list of `len(a) + len(b)` elements, `a` copied first. |

## Blocks and windows

| Symbol | Signature | Semantics |
|---|---|---|
| `chunks shard T` | `(items: list of T, n: int) -> list of list of T` | Consecutive blocks of up to `n`; `n <= 0` gives `[]`; the last block may be shorter. |
| `chunk_every shard T` | `(items: list of T, n: int, step: int is 1) -> list of list of T` | Blocks of up to `n` taken every `step` positions; `n <= 0` or `step <= 0` gives `[]`. `step == n` matches `chunks`, `step < n` overlaps, `step > n` skips. |
| `windows shard T` | `(items: list of T, n: int) -> list of list of T` | Contiguous windows of exactly `n`: `len - n + 1` of them; `n <= 0` or `n > len` gives `[]`. |
| `windowed shard T` | `(items: list of T, n: int) -> list of list of T` | Pengunic name of `windows`; same signature, same result. |
| `pairwise shard T` | `(items: list of T) -> list of list of T` | Overlapping adjacent two-element lists, size `len - 1`; `len < 2` gives `[]`. |
| `pairwise_pairs shard T` | `(items: list of T) -> list of Pair of T and T` | Same data as `Pair(first = xi, second = xi+1)`; `len < 2` gives `[]`. |

## Folds

| Symbol | Signature | Semantics |
|---|---|---|
| `sum shard T where T: Num` | `(nums: list of T) -> T` | Sum; `donum T` for `[]`. |
| `product_num shard T where T: Num` | `(nums: list of T) -> T` | Product; `1` for `[]`. |
| `max_int shard T where T: Ordered and T: Donum` | `(items: list of T) -> T` | Greatest element, or the sentinel `donum T` for `[]`; use `min_max` when absence must stay visible. |
| `min_int shard T where T: Ordered and T: Donum` | `(items: list of T) -> T` | Smallest element, or the sentinel `donum T` for `[]`; use `min_max` when absence must stay visible. |
| `min_max shard T where T: Ordered` | `(items: list of T) -> maybe Pair of T and T` | `some Pair(first = min, second = max)`, or `maybe none` for `[]` (safe family). |
| `mean shard T where T: Num` | `(nums: list of T) -> float` | Arithmetic mean as `float`, fraction preserved (`[1, 2]` -> `1.5`); `0.0` for `[]`. |
| `sum_squares shard T where T: Num` | `(nums: list of T) -> T` | Sum of the squares; `donum T` for `[]`. |
| `running_sum shard T where T: Num` | `(nums: list of T) -> list of T` | Prefix sums, one per element; `[]` stays `[]`. |
| `running_max shard T where T: Ordered` | `(nums: list of T) -> list of T` | Prefix maxima, one per element; `[]` stays `[]`. |
| `running_min shard T where T: Ordered` | `(nums: list of T) -> list of T` | Prefix minima, one per element; `[]` stays `[]`. |
| `differences shard T where T: Num` | `(nums: list of T) -> list of T` | Adjacent differences `[x1 - x0, x2 - x1, …]`, size `len - 1`; `len <= 1` gives `[]`. |
| `scan_left shard T where T: Num` | `(items: list of T, f: weave with acc as T, x as T into T) -> list of T` | `out[i] = f(out[i-1], items[i])` with `donum T` seeding `i == 0`; `[]` stays `[]`. `f` must be pure. |

## Predicates

| Symbol | Signature | Semantics |
|---|---|---|
| `any_zero shard T where T: Par` | `(nums: list of T) -> bool` | `true` when some element equals `donum T`; `false` for `[]`. |
| `all_equal shard T where T: Par` | `(nums: list of T) -> bool` | `true` when every element is equal; `len <= 1` gives `true`. |
| `is_strictly_asc shard T where T: Ordered` | `(nums: list of T) -> bool` | Every element strictly smaller than the next; `len < 2` gives `true`. |
| `is_strictly_desc shard T where T: Ordered` | `(nums: list of T) -> bool` | Every element strictly greater than the next; `len < 2` gives `true`. |
| `is_sorted_asc shard T where T: Ordered` | `(nums: list of T) -> bool` | Non-decreasing (`x[i] <= x[i+1]`). |
| `is_sorted_desc shard T where T: Ordered` | `(nums: list of T) -> bool` | Non-increasing (`x[i] >= x[i+1]`). |
| `is_partitioned shard T` | `(items: list of T, predicate: weave with x as T into bool) -> bool` | `true` when every element satisfying the predicate precedes every element that does not; `[]` and one-element lists give `true`. |

## Context-taking pipelines (`*_ctx`)

Added in 2.8.0. These are the no-closure answer to `map(xs, lambda …)`: the
callback takes the borrowed context as its first parameter, so configuration
travels without an environment.

| Function | Signature (all `shard T, …, C`) |
|---|---|
| `map_ctx` | `(list of T, ref to C, (ref to C, T) -> U) -> list of U` |
| `filter_ctx` | `(list of T, ref to C, (ref to C, T) -> bool) -> list of T` |
| `fold_ctx` | `(list of T, U, ref to C, (ref to C, U, T) -> U) -> U` |
| `for_each_ctx` | `(list of T, ref to C, (ref to C, T) -> void) -> void` |
| `zip_with_ctx` | `(list of T, list of U, ref to C, (ref to C, T, U) -> V) -> list of V` |
| `find_first_ctx` | `(list of T, ref to C, (ref to C, T) -> bool) -> maybe T` |
| `any_ctx` | `(list of T, ref to C, (ref to C, T) -> bool) -> bool` |
| `all_ctx` | `(list of T, ref to C, (ref to C, T) -> bool) -> bool` |
| `partition_ctx` | `(list of T, ref to C, (ref to C, T) -> bool) -> (list of T, list of T)` |
| `filter_map_ctx` | `(list of T, ref to C, (ref to C, T) -> maybe U) -> list of U` |

Every function is self-contained (there is no context-free `map`/`filter`/
`fold` in `loom` to delegate to) and uses no `transmute`: the callback is
monomorphized like any other function parameter. `zip_with_ctx` truncates at the
shorter list, exactly like `zip_with_op`. `find_first_ctx` is predicate-based
and returns the **element**; the older `find_first` is equality-based and
returns an **index**. `any_ctx` on `[]` is `false`; `all_ctx` on `[]` is `true`.
`partition_ctx` returns two owned lists (release each one, not the tuple).

Memory: the context is **borrowed** and must live for the synchronous call; the
returned list is new and released by the caller with `banish`.

## Transformations and combinations

| Symbol | Signature | Semantics |
|---|---|---|
| `zip_with shard T where T: Num and T: Ordered` | `(a: list of T, b: list of T, op: int is 0) -> list of T` | Combines the pair with code `op`: `0` add (also the default and the fallback), `1` subtract, `2` multiply, `3` min, `4` max; stops at the shorter input. |
| `zip_with_op shard T` | `(a: list of T, b: list of T, f: weave with x as T, y as T into T) -> list of T` | Same shape as `zip_with` with a caller weave; size `min(len a, len b)`; `f` must be pure. |
| `zip_longest` | `(list of int, list of int, int is 0) -> list of list of int` | `[a_i, b_i]` up to the longer input, using `fill` (default `0`) where a side is exhausted. Concrete: the default depends on the element type. |
| `enumerate shard T where T: Num` | `(items: list of T) -> list of list of T` | `[index, value]` pairs, one two-element list per element. The row is homogeneous, so `index` shares the element type (`T: Num`); use `enumerate_pairs` for the mixed `int` index. |
| `enumerate_pairs shard T` | `(items: list of T) -> list of Pair of int and T` | The same entries as `Pair(first = index, second = value)`. |
| `interleave shard T` | `(a: list of T, b: list of T) -> list of T` | Alternates `a` and `b` up to the shorter, size `2 * min(len a, len b)`. |
| `round_robin shard T` | `(lists: list of list of T) -> list of T` | Takes turn `i` over every inner list that still has an `i`-th element, until all are exhausted. |
| `rotate_left shard T` | `(items: list of T, k: int) -> list of T` | Left rotation by `k`; `k` wraps around the length and a negative `k` rotates the other way. |
| `rotate_right shard T` | `(items: list of T, k: int) -> list of T` | Right rotation by `k`; same wrapping and sign rules as `rotate_left`. |
| `intersperse shard T` | `(items: list of T, sep: T) -> list of T` | Inserts `sep` between adjacent elements: size `2 * len - 1`, or `[]`. |
| `flat_map_identity shard T` | `(nested: list of list of T) -> list of T` | Flattens one level: concatenates the inner lists in order. |
| `flatten shard T` | `(nested: list of list of T) -> list of T` | *(deprecated — use `flat_map_identity`)*. Identical behaviour; kept as a documented alias only. |
| `flatten_generic shard T` | `(nested: list of list of T) -> list of T` | Generic core of `flat_map_identity` / `flatten`; elements are copied, so inner payload ownership stays with the caller. |

## Sets over sorted lists

Each function takes two **ascending** lists, returns a new ascending,
deduplicated list, and only reads its inputs. The order test goes through
`calling a.cmp with b`, so `T: Ordered` and strings are supported.

| Symbol | Signature | Semantics |
|---|---|---|
| `union_sorted shard T where T: Ordered` | `(a: list of T, b: list of T) -> list of T` | Values present in either input. |
| `intersect_sorted shard T where T: Ordered` | `(a: list of T, b: list of T) -> list of T` | Values present in both inputs. |
| `difference_sorted shard T where T: Ordered` | `(a: list of T, b: list of T) -> list of T` | Values of `a` not present in `b` (`a \ b`). |
| `symmetric_difference_sorted shard T where T: Ordered` | `(a: list of T, b: list of T) -> list of T` | Values present in exactly one of the inputs. |

## Search and indices

| Symbol | Signature | Semantics |
|---|---|---|
| `find_first shard T where T: Par` | `(items: list of T, target: T) -> maybe int` | `some index` of the first occurrence of `target`, else `maybe none`. Linear scan. |
| `find_last shard T where T: Par` | `(items: list of T, target: T) -> maybe int` | `some index` of the last occurrence of `target`, else `maybe none`. Linear scan. |
| `binary_search shard T where T: Ordered` | `(sorted_items: list of T, target: T) -> maybe int` | Binary search of an ascending list through `cmp`; `some index` or `maybe none`. Undefined on an unsorted input. |
| `count_if_even shard T where T: Integrum and T: Par` | `(items: list of T) -> int` | How many elements satisfy `x % 2 == 0` (negative even values included). |
| `count_if_positive shard T where T: Num and T: Ordo` | `(items: list of T) -> int` | How many elements satisfy `x > donum T`. |
| `index_min shard T where T: Ordered` | `(items: list of T) -> maybe int` | `some index` of the first smallest element; `maybe none` for `[]`. |
| `index_max shard T where T: Ordered` | `(items: list of T) -> maybe int` | `some index` of the first greatest element; `maybe none` for `[]`. |

## Editing (pure)

Every function returns a **copy**; no input is mutated. Out-of-range indices are
clamped or ignored as noted, never a panic.

| Symbol | Signature | Semantics |
|---|---|---|
| `insert_at shard T` | `(items: list of T, index: int, value: T) -> list of T` | Copy with `value` inserted at `index` (clamped to `[0, len]`); size `len + 1`. |
| `remove_at shard T` | `(items: list of T, index: int) -> list of T` | Copy without the element at `index`; an out-of-range index returns a full copy. |
| `replace_at shard T` | `(items: list of T, index: int, value: T) -> list of T` | Copy with `value` at `index`; an out-of-range index returns a full copy. |
| `swap_at shard T` | `(items: list of T, i: int, j: int) -> list of T` | Copy with positions `i` and `j` swapped when both are in range, else an untouched copy. |
| `pad_left` | `(items: list of int, target_len: int, fill: int is 0) -> list of int` | Copy padded on the left with `fill` up to `target_len`; length `max(len, target_len)`, a smaller target returns a full copy. Concrete: the default depends on the element type. |
| `pad_right` | `(items: list of int, target_len: int, fill: int is 0) -> list of int` | Mirror of `pad_left` on the right. |

## Statistics

| Symbol | Signature | Semantics |
|---|---|---|
| `median shard T where T: Num and T: Ordo` | `(items: list of T) -> maybe float` | `some median` as `float`; an even length averages the two middle values; `maybe none` for `[]`. |
| `mode shard T where T: Num and T: Ordo` | `(items: list of T) -> maybe T` | `some` most frequent value; on a tie the first value to reach the maximum wins; `maybe none` for `[]`. |
| `variance shard T where T: Num and T: Ordo` | `(items: list of T) -> maybe float` | `some` population variance (divides by `len`); `maybe none` for `[]`. |
| `stddev shard T where T: Num and T: Ordo` | `(items: list of T) -> maybe float` | `some` population standard deviation = `arithmancy.sqrt(variance)`; `maybe none` for `[]`. |
| `percentile shard T where T: Num and T: Ordo` | `(items: list of T, p: float) -> maybe float` | `some` percentile `p` in `[0.0, 100.0]` by linear interpolation; `maybe none` when the list is empty or `p` is out of range. |

## Generic helpers (compatibility core)

| Symbol | Signature | Semantics |
|---|---|---|
| `first_or shard T` | `(items: list of T, default_val: T) -> T` | First element, or `default_val` when the list is empty; no allocation. |
| `generic_take shard T` | `(items: list of T, n: int) -> list of T` | First `n` elements; `n > len` clamps and `n < 0` gives `[]`. Self-contained generic body. |
| `generic_take_last shard T` | `(items: list of T, n: int) -> list of T` | Last `n` elements; `n > len` clamps and `n <= 0` gives `[]`. |
| `generic_reverse shard T` | `(items: list of T) -> list of T` | Reversed copy. |
| `generic_chain shard T` | `(a: list of T, b: list of T) -> list of T` | Concatenation of two lists of any `T`. |
| `generic_index_of shard T where T: Par` | `(items: list of T, target: T) -> int` | Zero-based index of the first match, or `-1`; `T: Par` because the search compares with `==`. |

## Test-only orderable type

`loom` publishes one non-`_` name that exists only to exercise the `Ordered`
bound end to end; it is not part of the useful surface.

| Symbol | Signature | Semantics |
|---|---|---|
| `seal LoomUserId as int` | — | Sealed integer alias whose `bind LoomUserId with Ordered:` gives it a `cmp`; the internal tests read `list of LoomUserId`. |
| `LoomUserId.cmp` | `(other: LoomUserId) -> int` | `1` / `-1` / `0`, implemented on the underlying `int`. Bound with an **unqualified** `bind LoomUserId with Ordered:` (a qualified `atlas.Ordered` is `E0004`). |

## Compatibility and migration

* Every pre-`2.2.0` public symbol keeps its name and its `list of int` call
  form; nothing was renamed or removed. The `2.2.0` change is the widening of
  the declarations to `shard T` plus the bounds above.
* `windowed` is the Pengunic name of `windows`, `pairwise_pairs` /
  `enumerate_pairs` are the `Pair` variants of `pairwise` / `enumerate`, and
  `chunk_every` / `zip_with_op` / `flat_map_identity` / `min_max` /
  `unfold_range` / `is_partitioned` are new names — no overload replaces an old
  one.
* `min_max` is the safe replacement for reading "no elements" out of the
  sentinel-returning `min_int` / `max_int`, which are kept unchanged. The three
  are now generic (`shard T`) and `min_max` returns `maybe Pair of T and T`.
* The `int`-defaulted entry points (`range`, `unfold_range`, `pad_left`,
  `pad_right`, `zip_longest`) stay concrete on purpose: a generic parameter
  cannot carry a default value that depends on `T`, and dropping the default
  would break existing two-argument call sites.
* **`flatten` is deprecated** in favour of `flat_map_identity`. The deprecation
  lives in the docstring only (`## @deprecated Use flat_map_identity instead.`),
  so it emits no `W0006`; it is catalogued in
  [`DEPRECATIONS.md`](DEPRECATIONS.md) with replacement
  `loom.flat_map_identity`, since `0.15.0`, retirement `1.x`.
* The absence of an `enchanting` block is part of the contract, not an
  oversight: adding one here would collide with `std.tally`'s methods.

## Private helpers (internal)

Not part of the frozen surface; they may be renamed or inlined without a
`LOOM_VERSION` bump. None is exported and none may be called from another module.

| Signature | Helpers |
|---|---|
| `(list of int) -> int` | `_sum_int`, `_product_int` |
| `(list of int) -> float` | `_mean_int` |
| `(list of int) -> maybe float` | `_variance_int`, `_median_int` |
| `(list of int) -> maybe int` | `_mode_int` |
| `(list of int) -> maybe Pair of int and int` | `_min_max_int` |
| `(list of int) -> list of int` | `_sorted_asc_int`, `_dedup_int`, `_running_sum_int` |
| `(list of int) -> list of Pair of int and int` | `_enumerate_pairs_int` |
| `(list of int, bool) -> list of int` | `_running_extreme_int` |
| `(list of int, bool) -> maybe int` | `_index_of_extreme_int` |
| `(list of int, bool, bool) -> bool` | `_is_ordered_int` |
| `(list of int, int) -> list of int` | `_rotate_left_int` |
| `(list of int, int) -> list of list of int` | `_windows_int` |
| `(list of int, int, int) -> list of list of int` | `_chunk_every_int` |
| `(list of int, int, int) -> list of int` | `_zip_with_int` |
| `(list of int, list of int) -> list of int` | `_union_sorted_int`, `_intersect_sorted_int`, `_difference_sorted_int` |
| `(list of int, list of int, bool) -> int` | `_pick_len_int` |
| `(int, int, int) -> int` | `_apply_op_int` |
| `_slice_shard shard T`: `(list of T, int, int) -> list of T`; `_drop_shard shard T`: `(list of T, int) -> list of T`; `_repeat_shard shard T`: `(T, int) -> list of T` | generic cores |
| `_expect`: `(bool, string) -> void`; `_expect_float_near`: `(float, float, float, string) -> void`; `_expect_eq_ints`: `(list of int, list of int, string) -> void`; `_expect_eq_chunks`: `(list of list of int, list of list of int, string) -> void`; `_expect_pair`: `(int, int, string, Pair of int and int) -> void`; `_expect_some_pair`: `(int, int, string, maybe Pair of int and int) -> void` | test harness (panics via `spark.panic`) |
| `_expect_eq shard T where T: Par`: `(T, T, string) -> void`; `_expect_some shard T where T: Par`: `(maybe T, T, string) -> void`; `_expect_eq_shard_list shard T where T: Par`: `(list of T, list of T, string) -> void` | generic test harness |
