# `std.tally` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `TALLY_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/tally.pengu`](../std/tally.pengu).

`tally` owns list algorithms: reductions, statistics, search, sorting, selection,
filtering and transformation. Its only import is `std.spark` (for the harness
`panic`); it does **not** import `std.oracle`, which is why `min_max`,
`enumerate_pairs` and `partition_by` return lists instead of tuples.

Every operation exists twice with the same semantics: as a method on `list of T`
(`calling xs.sum`) and as a module function whose first parameter is the list
(`calling tally.sum with xs`). Methods are generic and live in seven `enchanting`
blocks; module functions keep the concrete `list of int` signature of 0.14.x and
delegate to the method, plus a newer generic `shard T` family.

`tally` is the **sentinel** family: an empty list collapses to a natural identity
(`sum([]) == 0`, `product([]) == 1`, `max_val([]) == 0`, `mode([]) == 0`,
`min_max([]) == []`) and fractional statistics truncate to `int`
(`mean([1, 2]) == 1`). Callers that need absence signalled must use `std.loom`.

## Relationship with `std.loom` (named exception)

`std.loom` and `std.tally` deliberately share 15 public names with **different**
contracts: `tally` is the *sentinel* family (an empty list collapses to a natural
identity; `mean` truncates to `int`) and `loom` is the *safe* family (`mean` is a
`float`; `mode`/`median`/`min_max` return `maybe none` on an empty list). This is
a documented, deliberate exception — `LANGUAGE.md` §19.1.1 and
`PenguScriptGuideSpanish.md` §15 — not drift. The two modules are not merged, no
symbol is renamed and no `_safe`/`_sentinel` suffix is introduced.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every input (`self`, `l`, `xs`, `ys`, `a`, `b`) | borrowed, read-only (`essence of self`); never mutated or freed | never `banish` |
| scalar returns (`T` / `int` / `bool`: reductions, statistics, indices, predicates, `len`, `dot`, `at_or`) | plain value | never `banish` |
| `at_safe`, `find_first_gt`, `find_first_lt` | `maybe T` boxing a heap cell | `banish` the whole `maybe` |
| every `list`/`map` return (`reverse`, `take`, `drop`, `sort_*`, `unique`, `filter_*`, `map_*`, `abs_all`, `clamp_all`, `concat`, `zip_sum`, `repeat`, `chunk`, `windowed`, `scan_left`, `running_sum`, `enumerate_pairs`, `partition_by`, `frequencies`, `group_count`) | owned, freshly allocated; inner lists too | `banish` each inner list and the outer container |

## Constants

`TALLY_VERSION as string is "2.1.0"` — the revision of the **tally API**, not of
the toolchain. It bumps only when a signature on this page changes.

## Methods on `list of T` (enchanting blocks)

A method cannot carry `where`, so each block fixes the bound for all its methods.

### `enchanting list of shard T where T: Donum`

| Method | Signature | Semantics |
|---|---|---|
| `first` | `() -> T` | First element, or `donum T` (0 for `int`) when empty. |
| `last` | `() -> T` | Last element, or `donum T` when empty. |
| `at_safe` | `(idx: int) -> maybe T` | `some v`, or `none` when `idx` is negative or `>= len`. |
| `reverse` | `() -> list of T` | New reversed copy; `self` untouched. |
| `flatten` | `() -> list of T` | Identity copy (flattens one level of logical nesting). |
| `take` | `(n: int is 1) -> list of T` | First `n` elements, clipped to `[0, len]`. |
| `drop` | `(n: int is 1) -> list of T` | Elements from index `n` on; negative `n` clamps to 0. |
| `slice_list` | `(start: int, end_idx: int) -> list of T` | Sub-list `[start, end_idx)`, clamped; empty range → empty list. |

### `enchanting list of shard T where T: Num`

| Method | Signature | Semantics |
|---|---|---|
| `sum` | `() -> T` | Left-to-right total; empty → `donum T` (0 for `int`). |
| `product` | `() -> T` | Left-to-right product; empty → identity `1`. |
| `mean` | `() -> T` | `sum / len` truncated towards zero (`[1, 2]` → 1); empty → `donum T`. |
| `average` | `() -> T` | *(deprecated — use `mean`)* Same body, same semantics. |
| `sum_of_squares` | `() -> T` | Σ x². Empty → `donum T`. |
| `map_double` | `() -> list of T` | New list with every element doubled. |
| `map_square` | `() -> list of T` | New list with every element squared. |
| `map_negate` | `() -> list of T` | New list with `0 - x` (works for `float` too). |
| `map_add_scalar` | `(k: T) -> list of T` | New list with `k` added to every element. |
| `map_increment` | `(delta: int is 1) -> list of T` | New list with integer `delta` added to every element. |

### `enchanting list of shard T where T: Ordo`

| Method | Signature | Semantics |
|---|---|---|
| `max_val` | `() -> T` | Largest element; empty → `donum T` (deliberate sentinel). |
| `min_val` | `() -> T` | Smallest element; empty → `donum T`. |
| `max_index` | `() -> int` | First index of the maximum; empty → -1. |
| `min_index` | `() -> int` | First index of the minimum; empty → -1. |
| `argmin` | `() -> int` | *(deprecated — use `min_index`)* |
| `argmax` | `() -> int` | *(deprecated — use `max_index`)* |
| `sort_asc` | `() -> list of T` | New ascending copy; insertion sort, O(n²). |
| `sort_desc` | `() -> list of T` | New descending copy; insertion sort, O(n²). |
| `is_sorted_asc` | `() -> bool` | True when adjacent pairs never decrease; empty/one → true. |
| `is_sorted_desc` | `() -> bool` | True when adjacent pairs never increase; empty/one → true. |
| `all_positive` | `() -> bool` | True when no element is `<= donum T`; empty → true. |
| `any_negative` | `() -> bool` | True as soon as one element is `< donum T`; empty → false. |
| `filter_positive` | `() -> list of T` | New list of the strictly positive elements (0 dropped). |
| `filter_negative` | `() -> list of T` | New list of the strictly negative elements (0 dropped). |
| `find_first_gt` | `(threshold: T) -> maybe T` | First element `> threshold`, else `none`. |
| `find_first_lt` | `(threshold: T) -> maybe T` | First element `< threshold`, else `none`. |

### `enchanting list of shard T where T: Num, T: Ordo`

| Method | Signature | Semantics |
|---|---|---|
| `abs_all` | `() -> list of T` | New list with the absolute value of every element. |
| `median` | `() -> T` | Median after sorting; even length averages the two central values with truncation towards zero; empty → `donum T`. |
| `all_in_range` | `(lo: T, hi: T) -> bool` | True when every element is in `[lo, hi]`; empty → true. |
| `filter_in_range` | `(lo: T, hi: T) -> list of T` | New list of the elements inside `[lo, hi]`. |
| `filter_range` | `(lo: T, hi: T) -> list of T` | *(deprecated — use `filter_in_range`)* |

### `enchanting list of shard T where T: Par`

| Method | Signature | Semantics |
|---|---|---|
| `all_zero` | `() -> bool` | True when every element equals `donum T`; empty → true. |
| `mode` | `() -> T` | Most frequent value, earliest wins on a tie; empty → `donum T`; O(n²). |
| `unique` | `() -> list of T` | New list without duplicates, first-appearance order; O(n²). |
| `dedup` | `() -> list of T` | *(deprecated — use `unique`)* |
| `count_of` | `(item: T) -> int` | Occurrences of `item` (0 when absent). |
| `last_index_of` | `(item: T) -> int` | Index of the last occurrence, or -1 when absent. |

### `enchanting list of shard T where T: Integrum and T: Par`

| Method | Signature | Semantics |
|---|---|---|
| `filter_even` | `() -> list of T` | New list of the elements with `x % 2 == 0`. |
| `filter_odd` | `() -> list of T` | New list of the elements with `x % 2 != 0`. |

### `enchanting list of int`

| Method | Signature | Semantics |
|---|---|---|
| `at_or` | `(idx: int, default: int is 0) -> int` | Element at `idx`, or `default` when negative or `>= len`; `int`-typed default forces the concrete block. |
| `clamp_all` | `(lo: int is 0, hi: int is 100) -> list of int` | New list with every value clipped to `[lo, hi]`. |

## Module functions — concrete `list of int` (0.14.x compatibility)

These keep their exact 0.14.x signature and delegate to the matching method.

### Reductions and statistics

| Symbol | Signature | Semantics |
|---|---|---|
| `sum` | `(list of int) -> int` | Total; empty → 0. |
| `product` | `(list of int) -> int` | Product; empty → 1. |
| `mean` | `(list of int) -> int` | Truncated towards zero (`[1, 2]` → 1); empty → 0. |
| `average` | `(list of int) -> int` | *(deprecated — use `mean`)* |
| `sum_of_squares` | `(list of int) -> int` | Σ x²; empty → 0. |
| `median` | `(list of int) -> int` | Sorting median; even length averages the central values; empty → 0. |
| `mode` | `(list of int) -> int` | Most frequent (first wins on a tie); empty → 0. |
| `max_val` | `(list of int) -> int` | Maximum; empty → sentinel 0. |
| `min_val` | `(list of int) -> int` | Minimum; empty → sentinel 0. |
| `dot` | `(a: list of int, b: list of int) -> int` | Dot product up to the shorter list; 0 when either side is empty. |

### Access, search and predicates

| Symbol | Signature | Semantics |
|---|---|---|
| `len` | `(list of int) -> int` | Element count; alias of the built-in `l.len`. |
| `is_empty` | `(list of int) -> bool` | True when `l` has no elements. |
| `first` | `(list of int) -> int` | First element, or 0 when empty. |
| `last` | `(list of int) -> int` | Last element, or 0 when empty. |
| `at_or` | `(l: list of int, idx: int, default: int is 0) -> int` | Element at `idx`, or `default` out of range. |
| `at_safe` | `(l: list of int, idx: int) -> maybe int` | `some v`, or `none` out of range; `banish` the `maybe`. |
| `contains` | `(l: list of int, item: int) -> bool` | Membership; alias of the built-in `l.contains`. |
| `index_of` | `(l: list of int, item: int) -> int` | First occurrence, or -1. |
| `last_index_of` | `(l: list of int, item: int) -> int` | Last occurrence, or -1. |
| `count_of` | `(l: list of int, item: int) -> int` | Occurrences of `item`. |
| `find_first_gt` | `(l: list of int, threshold: int) -> maybe int` | First element `> threshold`, else `none`. |
| `find_first_lt` | `(l: list of int, threshold: int) -> maybe int` | First element `< threshold`, else `none`. |
| `max_index` | `(list of int) -> int` | First index of the maximum; empty → -1. |
| `min_index` | `(list of int) -> int` | First index of the minimum; empty → -1. |
| `argmin` | `(list of int) -> int` | *(deprecated — use `min_index`)* |
| `argmax` | `(list of int) -> int` | *(deprecated — use `max_index`)* |
| `is_sorted_asc` | `(list of int) -> bool` | Non-descending order test. |
| `is_sorted_desc` | `(list of int) -> bool` | Non-ascending order test. |
| `all_positive` | `(list of int) -> bool` | Every element strictly positive; empty → true. |
| `all_zero` | `(list of int) -> bool` | Every element zero; empty → true. |
| `any_negative` | `(list of int) -> bool` | At least one strictly negative; empty → false. |
| `all_in_range` | `(l: list of int, lo: int, hi: int) -> bool` | Every element in `[lo, hi]`; empty → true. |

### Transformation, selection and filtering

| Symbol | Signature | Semantics |
|---|---|---|
| `concat` | `(a: list of int, b: list of int) -> list of int` | New list `a` followed by `b`. |
| `zip_sum` | `(a: list of int, b: list of int) -> list of int` | Element-wise sum up to the shorter list. |
| `repeat` | `(val: int, times: int) -> list of int` | New list with `val` repeated `times` times. |
| `reverse` | `(list of int) -> list of int` | New reversed copy. |
| `sort_asc` | `(list of int) -> list of int` | New ascending copy. |
| `sort_desc` | `(list of int) -> list of int` | New descending copy. |
| `unique` | `(list of int) -> list of int` | New list without duplicates, first-appearance order. |
| `dedup` | `(list of int) -> list of int` | *(deprecated — use `unique`)* |
| `flatten` | `(list of int) -> list of int` | Identity copy. |
| `take` | `(l: list of int, n: int is 1) -> list of int` | First `n` elements, clipped to the length. |
| `drop` | `(l: list of int, n: int is 1) -> list of int` | Elements from index `n` onwards. |
| `slice_list` | `(l: list of int, start: int, end_idx: int) -> list of int` | Sub-list `[start, end_idx)`. |
| `abs_all` | `(list of int) -> list of int` | New copy with absolute values. |
| `clamp_all` | `(l: list of int, lo: int is 0, hi: int is 100) -> list of int` | New copy clipped to `[lo, hi]`. |
| `map_double` | `(list of int) -> list of int` | New copy with every element doubled. |
| `map_square` | `(list of int) -> list of int` | New copy with every element squared. |
| `map_negate` | `(list of int) -> list of int` | New copy with every element negated. |
| `map_add_scalar` | `(l: list of int, k: int) -> list of int` | New copy with `k` added to every element. |
| `map_increment` | `(l: list of int, delta: int is 1) -> list of int` | New copy with `delta` added to every element. |
| `filter_even` | `(list of int) -> list of int` | Elements with `x % 2 == 0`. |
| `filter_odd` | `(list of int) -> list of int` | Elements with `x % 2 != 0`. |
| `filter_positive` | `(list of int) -> list of int` | Strictly positive elements. |
| `filter_negative` | `(list of int) -> list of int` | Strictly negative elements. |
| `filter_in_range` | `(l: list of int, lo: int, hi: int) -> list of int` | Elements inside `[lo, hi]`. |
| `filter_range` | `(l: list of int, lo: int, hi: int) -> list of int` | *(deprecated — use `filter_in_range`)* |

## Module functions — newer `shard T` API

| Symbol | Signature | Semantics |
|---|---|---|
| `zip_with shard T and U and V` | `(xs: list of T, ys: list of U, f: weave with a as T, b as U -> V) -> list of V` | Combine pairwise up to the shorter list. |
| `chunk shard T` | `(xs: list of T, span: int) -> list of list of T` | Consecutive runs of `span` (last may be shorter); `span <= 0` → empty. |
| `windowed shard T` | `(xs: list of T, width: int) -> list of list of T` | Sliding windows of width `width`; `width <= 0` or `> len` → empty. |
| `scan_left shard T where T: Num` | `(xs: list of T, f: weave with acc as T, x as T -> T) -> list of T` | Cumulative scan seeded with `xs[0]`, same length; empty → empty. |
| `running_sum shard T where T: Num` | `(xs: list of T) -> list of T` | Prefix sums; `out[i] == sum(xs[0..i])`; empty → empty. |
| `min_max` | `(xs: list of int) -> list of int` | `[min, max]`, or `[]` when empty; no tuples, no `std.oracle`. |
| `enumerate_pairs` | `(xs: list of int) -> list of list of int` | One `[index, value]` pair per element, in order. |
| `partition_by` | `(xs: list of int, predicate: weave with x as int -> bool) -> list of list of int` | `[matching, non_matching]` (either may be empty). |
| `frequencies` | `(xs: list of int) -> map of int to int` | Value → count map; empty list → empty map. |
| `group_count` | `(xs: list of int) -> map of int to int` | *(deprecated — use `frequencies`)* |

## Compatibility and migration

* Every 0.14.x symbol keeps its name and concrete `list of int` signature; the generic methods and the `shard T` family are additive.
* Deprecated symbols are ordinary `weave`s whose docstring starts with
  `## @deprecated Use X instead.` — there is **no** real `@deprecated` attribute,
  so none of them emits `W0006`. See [`DEPRECATIONS.md`](DEPRECATIONS.md).
* Deprecated aliases repeat the base body on purpose: a generic body cannot call
  another generic `weave`/method (the compiler emits the `_T` template), so
  `average`, `argmin`, `argmax`, `dedup` and `filter_range` are self-contained
  copies, not one-line forwards.

| Before (0.14.x) | Now (`2.1.0`) |
|---|---|
| `calling tally.sum with xs` | same, or `calling xs.sum` |
| `calling tally.sort_asc with xs` | same, or `calling xs.sort_asc` |
| `calling tally.clamp_all with xs, 0, 9` | same, or `calling xs.clamp_all with 0, 9` |
| `calling tally.map_increment with xs, 2` | same, or `calling xs.map_increment with 2` |
| `calling tally.group_count with xs` | `calling tally.frequencies with xs` |
| (new) | `zip_with`, `chunk`, `windowed`, `running_sum`, `scan_left`, `partition_by`, `enumerate_pairs`, `min_max` |

## Private helpers (internal)

Not public API; do not call them. Importing `std.ward` would create the cycle `ward -> tally` (E0004), so the harness uses `spark.panic`.

| Symbol | Signature | Role |
|---|---|---|
| `_expect` | `(cond: bool, label: string) -> void` | Panics with `label` when `cond` is false. |
| `_expect_eq_int` | `(actual: int, expected: int, label: string) -> void` | Integer equality assertion. |
| `_expect_eq_float` | `(actual: float, expected: float, label: string) -> void` | Float equality assertion. |
| `_expect_eq_bool` | `(actual: bool, expected: bool, label: string) -> void` | Boolean equality assertion. |
