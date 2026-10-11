# `std.loom` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `LOOM_VERSION`.
>
> Module revision: **`2.1.0`** (`LOOM_VERSION`).
> Source: [`std/loom.pengu`](../std/loom.pengu).

`loom` is the **safe** family of list helpers: sequence generation, slicing,
blocks and windows, folds, predicates, transformations and combinations, set
operations over sorted lists, search and indices, pure structural editing,
statistics, and a small `shard T` generic core. All 73 public declarations are
**module functions** (`calling loom.chunks with xs, 2`); the module declares
**no `enchanting` block on purpose**, so it never invades the list methods of
`std.tally` (see the named-exception section below).

It imports `std.arithmancy` (`arithmancy.sqrt` for `stddev`; `gcd` / `is_prime`
appear in the `_with_op` and predicate examples), `std.oracle` (`Pair`) and
`std.spark` (only the private `_expect*` test harness calls `spark.panic`). The
frozen surface is concrete `list of int` signature by signature; the additions
use `Pair` or the `shard T` cores. The module is a leaf consumer: no other
module in `std/` imports `loom`, so it may not grow a dependency that would
close a cycle through `tally`.

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
`tally`'s methods and silently merge the two contracts.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every function returning `string`-free `list of int` / `list of T` | new owned list | `banish` / `defer banish` |
| `chunks`, `chunk_every`, `windows`, `windowed`, `pairwise`, `enumerate`, `zip_longest` | owned outer list of owned inner lists | `banish` each inner list, then the outer |
| `pairwise_pairs`, `enumerate_pairs`, `list of Pair` results | owned flat rune | one `banish` |
| `min_max` | `maybe Pair` (payload is a flat rune) | nothing to release |
| `mode`, `index_min`, `index_max`, `find_first`, `find_last`, `binary_search` | `maybe int` scalar box | nothing to release |
| every other scalar (`int`, `bool`, `float`, `maybe float`) | value | nothing to release |
| all parameters (`items`, `a`, `b`, `n`, …) | borrowed | never `banish`; `loom` never mutates or frees an input |

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `LOOM_VERSION` | `string` | `"2.1.0"` | Revision of the **loom API**. Bumps only when a signature on this page changes; it is not the toolchain version. |

## Generation

| Symbol | Signature | Semantics |
|---|---|---|
| `range` | `(int, int, int is 1) -> list of int` | `[start, end)` advancing by `step`; positive walks up, negative walks down, `step == 0` gives `[]`. |
| `repeat` | `(int, int) -> list of int` | `value` repeated `times` times; `times <= 0` gives `[]`. |
| `unfold_range` | `(int, int, int is 1) -> list of int` | Exactly `count` elements `start, start + step, …`; `count <= 0` gives `[]`. Counts elements, unlike `range`. |

## Slices

| Symbol | Signature | Semantics |
|---|---|---|
| `take` | `(list of int, int) -> list of int` | First `n` elements; `n > len` clamps to the whole list and `n < 0` gives `[]`. |
| `skip` | `(list of int, int) -> list of int` | Elements from index `n` on; `n < 0` behaves like `0`, `n > len` gives `[]`. |
| `chain` | `(list of int, list of int) -> list of int` | New list of `len(a) + len(b)` elements, `a` copied first. |

## Blocks and windows

| Symbol | Signature | Semantics |
|---|---|---|
| `chunks` | `(list of int, int) -> list of list of int` | Consecutive blocks of up to `n`; `n <= 0` gives `[]`; the last block may be shorter. |
| `chunk_every` | `(list of int, int, int is 1) -> list of list of int` | Blocks of up to `n` taken every `step` positions; `n <= 0` or `step <= 0` gives `[]`. `step == n` matches `chunks`, `step < n` overlaps, `step > n` skips. |
| `windows` | `(list of int, int) -> list of list of int` | Contiguous windows of exactly `n`: `len - n + 1` of them; `n <= 0` or `n > len` gives `[]`. |
| `windowed` | `(list of int, int) -> list of list of int` | Pengunic name of `windows`; same signature, same result. |
| `pairwise` | `(list of int) -> list of list of int` | Overlapping adjacent two-element lists, size `len - 1`; `len < 2` gives `[]`. |
| `pairwise_pairs` | `(list of int) -> list of Pair of int and int` | Same data as `Pair(first = xi, second = xi+1)`; `len < 2` gives `[]`. |

## Folds

| Symbol | Signature | Semantics |
|---|---|---|
| `sum` | `(list of int) -> int` | Sum; `0` for `[]`. |
| `product_num` | `(list of int) -> int` | Product; `1` for `[]`. |
| `max_int` | `(list of int) -> int` | Greatest element, or the sentinel `0` for `[]`; use `min_max` when absence must stay visible. |
| `min_int` | `(list of int) -> int` | Smallest element, or the sentinel `0` for `[]`; use `min_max` when absence must stay visible. |
| `min_max` | `(list of int) -> maybe Pair of int and int` | `some Pair(first = min, second = max)`, or `maybe none` for `[]` (safe family). |
| `mean` | `(list of int) -> float` | Arithmetic mean as `float`, fraction preserved (`[1, 2]` -> `1.5`); `0.0` for `[]`. |
| `sum_squares` | `(list of int) -> int` | Sum of the squares; `0` for `[]`. |
| `running_sum` | `(list of int) -> list of int` | Prefix sums, one per element; `[]` stays `[]`. |
| `running_max` | `(list of int) -> list of int` | Prefix maxima, one per element; `[]` stays `[]`. |
| `running_min` | `(list of int) -> list of int` | Prefix minima, one per element; `[]` stays `[]`. |
| `differences` | `(list of int) -> list of int` | Adjacent differences `[x1 - x0, x2 - x1, …]`, size `len - 1`; `len <= 1` gives `[]`. |
| `scan_left shard T where T: Num` | `(list of T, weave with acc as T, x as T into T) -> list of T` | `out[i] = f(out[i-1], items[i])` with `donum T` seeding `i == 0`; `[]` stays `[]`. `f` must be pure. |

## Predicates

| Symbol | Signature | Semantics |
|---|---|---|
| `any_zero` | `(list of int) -> bool` | `true` when some element is `0`; `false` for `[]`. |
| `all_equal` | `(list of int) -> bool` | `true` when every element is equal; `len <= 1` gives `true`. |
| `is_strictly_asc` | `(list of int) -> bool` | Every element strictly smaller than the next; `len < 2` gives `true`. |
| `is_strictly_desc` | `(list of int) -> bool` | Every element strictly greater than the next; `len < 2` gives `true`. |
| `is_sorted_asc` | `(list of int) -> bool` | Non-decreasing (`x[i] <= x[i+1]`). |
| `is_sorted_desc` | `(list of int) -> bool` | Non-increasing (`x[i] >= x[i+1]`). |
| `is_partitioned` | `(list of int, weave with x as int into bool) -> bool` | `true` when every element satisfying the predicate precedes every element that does not; `[]` and one-element lists give `true`. |

## Transformations and combinations

| Symbol | Signature | Semantics |
|---|---|---|
| `zip_with` | `(list of int, list of int, int is 0) -> list of int` | Combines the pair with code `op`: `0` add (also the default and the fallback), `1` subtract, `2` multiply, `3` min, `4` max; stops at the shorter input. |
| `zip_with_op` | `(list of int, list of int, weave with x as int, y as int into int) -> list of int` | Same shape as `zip_with` with a caller weave; size `min(len a, len b)`; `f` must be pure. |
| `zip_longest` | `(list of int, list of int, int is 0) -> list of list of int` | `[a_i, b_i]` up to the longer input, using `fill` (default `0`) where a side is exhausted. |
| `enumerate` | `(list of int) -> list of list of int` | `[index, value]` pairs, one two-element list per element. |
| `enumerate_pairs` | `(list of int) -> list of Pair of int and int` | The same entries as `Pair(first = index, second = value)`. |
| `interleave` | `(list of int, list of int) -> list of int` | Alternates `a` and `b` up to the shorter, size `2 * min(len a, len b)`. |
| `round_robin` | `(list of list of int) -> list of int` | Takes turn `i` over every inner list that still has an `i`-th element, until all are exhausted. |
| `rotate_left` | `(list of int, int) -> list of int` | Left rotation by `k`; `k` wraps around the length and a negative `k` rotates the other way. |
| `rotate_right` | `(list of int, int) -> list of int` | Right rotation by `k`; same wrapping and sign rules as `rotate_left`. |
| `intersperse` | `(list of int, int) -> list of int` | Inserts `sep` between adjacent elements: size `2 * len - 1`, or `[]`. |
| `flat_map_identity` | `(list of list of int) -> list of int` | Flattens one level: concatenates the inner lists in order. |
| `flatten` | `(list of list of int) -> list of int` | *(deprecated — use `flat_map_identity`)*. Identical behaviour; kept as a documented alias only. |
| `flatten_generic shard T` | `(list of list of T) -> list of T` | Generic core of `flat_map_identity` / `flatten`; elements are copied, so inner payload ownership stays with the caller. |

## Sets over sorted lists

Each function takes two **ascending** lists, returns a new ascending,
deduplicated list, and only reads its inputs.

| Symbol | Signature | Semantics |
|---|---|---|
| `union_sorted` | `(list of int, list of int) -> list of int` | Values present in either input. |
| `intersect_sorted` | `(list of int, list of int) -> list of int` | Values present in both inputs. |
| `difference_sorted` | `(list of int, list of int) -> list of int` | Values of `a` not present in `b` (`a \ b`). |
| `symmetric_difference_sorted` | `(list of int, list of int) -> list of int` | Values present in exactly one of the inputs. |

## Search and indices

| Symbol | Signature | Semantics |
|---|---|---|
| `find_first` | `(list of int, int) -> maybe int` | `some index` of the first occurrence of `target`, else `maybe none`. Linear scan. |
| `find_last` | `(list of int, int) -> maybe int` | `some index` of the last occurrence of `target`, else `maybe none`. Linear scan. |
| `binary_search` | `(list of int, int) -> maybe int` | Binary search of an ascending list; `some index` or `maybe none`. Undefined on an unsorted input. |
| `count_if_even` | `(list of int) -> int` | How many elements satisfy `x % 2 == 0` (negative even values included). |
| `count_if_positive` | `(list of int) -> int` | How many elements satisfy `x > 0`. |
| `index_min` | `(list of int) -> maybe int` | `some index` of the first smallest element; `maybe none` for `[]`. |
| `index_max` | `(list of int) -> maybe int` | `some index` of the first greatest element; `maybe none` for `[]`. |

## Editing (pure)

Every function returns a **copy**; no input is mutated. Out-of-range indices are
clamped or ignored as noted, never a panic.

| Symbol | Signature | Semantics |
|---|---|---|
| `insert_at` | `(list of int, int, int) -> list of int` | Copy with `value` inserted at `index` (clamped to `[0, len]`); size `len + 1`. |
| `remove_at` | `(list of int, int) -> list of int` | Copy without the element at `index`; an out-of-range index returns a full copy. |
| `replace_at` | `(list of int, int, int) -> list of int` | Copy with `value` at `index`; an out-of-range index returns a full copy. |
| `swap_at` | `(list of int, int, int) -> list of int` | Copy with positions `i` and `j` swapped when both are in range, else an untouched copy. |
| `pad_left` | `(list of int, int, int is 0) -> list of int` | Copy padded on the left with `fill` up to `target_len`; length `max(len, target_len)`, a smaller target returns a full copy. |
| `pad_right` | `(list of int, int, int is 0) -> list of int` | Mirror of `pad_left` on the right. |

## Statistics

| Symbol | Signature | Semantics |
|---|---|---|
| `median` | `(list of int) -> maybe float` | `some median` as `float`; an even length averages the two middle values; `maybe none` for `[]`. |
| `mode` | `(list of int) -> maybe int` | `some` most frequent value; on a tie the first value to reach the maximum wins; `maybe none` for `[]`. |
| `variance` | `(list of int) -> maybe float` | `some` population variance (divides by `len`); `maybe none` for `[]`. |
| `stddev` | `(list of int) -> maybe float` | `some` population standard deviation = `arithmancy.sqrt(variance)`; `maybe none` for `[]`. |
| `percentile` | `(list of int, float) -> maybe float` | `some` percentile `p` in `[0.0, 100.0]` by linear interpolation; `maybe none` when the list is empty or `p` is out of range. |

## Generic helpers (compatibility core)

| Symbol | Signature | Semantics |
|---|---|---|
| `first_or shard T` | `(list of T, T) -> T` | First element, or `default_val` when the list is empty; no allocation. |
| `generic_take shard T` | `(list of T, int) -> list of T` | First `n` elements; `n > len` clamps and `n < 0` gives `[]`. Self-contained generic body. |
| `generic_take_last shard T` | `(list of T, int) -> list of T` | Last `n` elements; `n > len` clamps and `n <= 0` gives `[]`. |
| `generic_reverse shard T` | `(list of T) -> list of T` | Reversed copy. |
| `generic_chain shard T` | `(list of T, list of T) -> list of T` | Concatenation of two lists of any `T`. |
| `generic_index_of shard T where T: Par` | `(list of T, T) -> int` | Zero-based index of the first match, or `-1`; `T: Par` because the search compares with `==`. |

## Compatibility and migration

* Every pre-`2.1.0` public symbol keeps its name and `list of int` signature;
  nothing was renamed or removed.
* `windowed` is the Pengunic name of `windows`, `pairwise_pairs` /
  `enumerate_pairs` are the `Pair` variants of `pairwise` / `enumerate`, and
  `chunk_every` / `zip_with_op` / `flat_map_identity` / `min_max` /
  `unfold_range` / `is_partitioned` are new names — no overload replaces an old
  one.
* `min_max` is the safe replacement for reading "no elements" out of the
  sentinel-returning `min_int` / `max_int`, which are kept unchanged.
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
| `_expect_eq shard T where T: Par`: `(T, T, string) -> void`; `_expect_some shard T where T: Par`: `(maybe T, T, string) -> void` | generic test harness |
