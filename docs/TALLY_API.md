# `std.tally` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `TALLY_VERSION`.
>
> Module revision: **`2.2.0`**.
> Source: [`std/tally.pengu`](../std/tally.pengu).

`tally` owns list algorithms: reductions, statistics, search, sorting, selection,
filtering and transformation. It imports `std.spark` (for the harness `panic`)
and, since `2.2.0`, `std.atlas` (for the `Ordered` concept). It does **not**
import `std.oracle`, which is why `min_max`, `enumerate_pairs` and `partition_by`
return lists instead of tuples.

Every operation exists twice with the same semantics: as a method on `list of T`
(`calling xs.sum`) and as a module function whose first parameter is the list
(`calling tally.sum with xs`). Since `2.2.0` **both** forms are generic over the
element type: the methods live in `enchanting list of shard T where T: …` blocks
and each module function carries its own `where` clause, so `calling sum with xs`
accepts `list of int`, `list of float`, `list of i64`, `list of string` or a list
of any bound `seal`/`rune`. Only four symbols stay concrete: `at_or` and
`clamp_all` keep their `int`-defaulted `list of int` signature (the widened
forms are `at_or_shard` / `clamp_all_shard`), and `enumerate_pairs` /
`partition_by` mix an `int` component with the element type.

`tally` is the **sentinel** family: an empty list collapses to a natural identity
(`sum([]) == 0`, `product([]) == 1`, `max_val([]) == donum T`, `mode([]) == donum
T`, `min_max([]) == []`) and fractional statistics truncate to `int`
(`mean([1, 2]) == 1`). Callers that need absence signalled must use `std.loom`.

The module declares `insignia tally_`, so every module function is emitted with a
C prefix (`tally_sum`, `tally_sort_asc`, …). That is what makes a **qualified
generic call** resolve to the right monomorphisation when a program uses several
element types: `calling tally.sum with floats` names the exact instantiation
instead of relying on a bare `sum` symbol. (Without the insignia, the compiler's
old "only one match" heuristic picked the wrong C symbol as soon as two
specialisations existed.)

## Relationship with `std.loom` (named exception)

`std.loom` and `std.tally` deliberately share 15 public names with **different**
contracts: `tally` is the *sentinel* family (an empty list collapses to a natural
identity; `mean` truncates to `int`) and `loom` is the *safe* family (`mean` is a
`float`; `mode`/`median`/`min_max` return `maybe none` on an empty list). This is
a documented, deliberate exception — `LANGUAGE.md` §19.1.1 and
`PenguScriptGuideSpanish.md` §15 — not drift. The two modules are not merged, no
symbol is renamed and no `_safe`/`_sentinel` suffix is introduced.

## Element-type bounds

Since `2.2.0` each entry point carries the bound its body actually needs, so a
`list of int` call site keeps working unchanged while the same call accepts
`float`, `i64`, `string` or any user type that implements the bound.

| Bound | Meaning | Operations |
|---|---|---|
| *(none)* `shard T` | the body only moves or copies elements | `is_empty`, `len`, `concat`, `repeat`, `reverse`, `flatten`, `take`, `drop`, `slice_list`, `zip_with`, `chunk`, `windowed` |
| `T: Donum` | needs the default value `donum T` (the empty-list sentinel) | `first`, `last`, `at_safe`, `at_or_shard` |
| `T: Num` | arithmetic (`+ - * / %`, `0`/`1`) | `sum`, `product`, `mean`, `average`, `sum_of_squares`, `dot`, `zip_sum`, `map_double`, `map_square`, `map_negate`, `map_add_scalar`, `map_increment`, `scan_left`, `running_sum` |
| `T: Ordered` | **order comparisons through the concept** | `max_index`, `min_index`, `argmin`, `argmax`, `sort_asc`, `sort_desc`, `is_sorted_asc`, `is_sorted_desc`, `find_first_gt`, `find_first_lt`, `all_in_range`, `filter_in_range`, `filter_range`, `min_max` (`max_val`/`min_val` also need `T: Donum`, next row) |
| `T: Par` | `==` / `!=` only | `all_zero`, `mode`, `unique`, `dedup`, `count_of`, `last_index_of`, `contains`, `index_of` |
| `T: Integrum and T: Par` | `% 2` plus equality | `filter_even`, `filter_odd` |
| `T: Num and T: Ordo` | numeric, ordered by the built-in `Ordo` | `abs_all`, `all_positive`, `any_negative`, `filter_positive`, `filter_negative` |
| `T: Num and T: Ordered` | numeric **and** orderable through the concept | `median` |
| `T: Donum and T: Par` | equality plus the empty sentinel (`mode`) | `mode` |
| `T: Donum and T: Ordered` | the empty sentinel plus order comparisons | `max_val`, `min_val` (module and method); the method block of `all_in_range`, `filter_in_range`, `filter_range` (their module functions need `T: Ordered` only) |
| `T: Vinculum` | usable as a map key | `frequencies`, `group_count` |
| `list of int` only | a `T`-dependent `is` default is impossible | `at_or`, `clamp_all` |

### Why the ordering operations need `T: Ordered`

A generic body lowers `>` and `<` to a raw C comparison, which does not compile
for `PenguString`, and a concrete string operand rejects `>` with `E0005`.
`std.atlas` therefore ships `concept Ordered shard T` (a `cmp` method returning
`0`, `-1` or `1`) and the `bind`s for `int`, `i32`, `i64`, `float`, `f32`, `f64`
and `string`. Every ordering operation above is bounded `where T: Ordered` and
compares with `calling a.cmp with b`, which is what lets
`calling tally.sort_asc with words` work on `list of string`. User types opt in
with an **unqualified** `bind MyType with Ordered:` after `import std.atlas`.
Equality (`==`) works generically on strings, so the `Par` group needs no
concept. The `Ordo`-bounded group (`all_positive`, `filter_negative`, …) is
numeric by construction — `Ordo` is the built-in numeric order — and is not
string-capable.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every input (`self`, `l`, `xs`, `ys`, `a`, `b`) | borrowed, read-only (`essence of self`); never mutated or freed | never `banish` |
| scalar returns (`T` / `int` / `bool`: reductions, statistics, indices, predicates, `len`, `dot`, `at_or`, `at_or_shard`) | plain value | never `banish` |
| `at_safe`, `find_first_gt`, `find_first_lt` | `maybe T` boxing a heap cell | `banish` the whole `maybe` |
| every `list`/`map` return (`reverse`, `take`, `drop`, `sort_*`, `unique`, `filter_*`, `map_*`, `abs_all`, `clamp_all*`, `concat`, `zip_sum`, `repeat`, `chunk`, `windowed`, `scan_left`, `running_sum`, `enumerate_pairs`, `partition_by`, `frequencies`, `group_count`, `min_max`) | owned, freshly allocated; inner lists too | `banish` each inner list and the outer container |

## Constants

`TALLY_VERSION as string is "2.2.0"` — the revision of the **tally API**, not of
the toolchain. It bumps only when a signature on this page changes. `2.2.0`
widened the module functions to `list of shard T` (except `at_or`, `clamp_all`,
`enumerate_pairs` and `partition_by`, see below) and added `at_or_shard` /
`clamp_all_shard`; nothing was removed and `at_or` / `clamp_all` still declare
their `int` defaults.

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

### `enchanting list of shard T where T: Donum and T: Ordered`

The source splits this bound over two blocks; both are listed here.

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
| `find_first_gt` | `(threshold: T) -> maybe T` | First element `> threshold`, else `none`. |
| `find_first_lt` | `(threshold: T) -> maybe T` | First element `< threshold`, else `none`. |
| `all_in_range` | `(lo: T, hi: T) -> bool` | True when every element is in `[lo, hi]`; empty → true. |
| `filter_in_range` | `(lo: T, hi: T) -> list of T` | New list of the elements inside `[lo, hi]`. |
| `filter_range` | `(lo: T, hi: T) -> list of T` | *(deprecated — use `filter_in_range`)* |

### `enchanting list of shard T where T: Num and T: Ordered`

| Method | Signature | Semantics |
|---|---|---|
| `median` | `() -> T` | Median after sorting; even length averages the two central values with truncation towards zero; empty → `donum T`. |

### `enchanting list of shard T where T: Num and T: Ordo`

| Method | Signature | Semantics |
|---|---|---|
| `abs_all` | `() -> list of T` | New list with the absolute value of every element. |
| `all_positive` | `() -> bool` | True when no element is `<= donum T`; empty → true. |
| `any_negative` | `() -> bool` | True as soon as one element is `< donum T`; empty → false. |
| `filter_positive` | `() -> list of T` | New list of the strictly positive elements (0 dropped). |
| `filter_negative` | `() -> list of T` | New list of the strictly negative elements (0 dropped). |

### `enchanting list of shard T where T: Donum and T: Par`

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
| `at_or` | `(idx: int, default: int is 0) -> int` | Element at `idx`, or `default` when negative or `>= len`; the `int` default forces the concrete block. |
| `clamp_all` | `(lo: int is 0, hi: int is 100) -> list of int` | New list with every value clipped to `[lo, hi]`. |

## Module functions — generic `shard T`

Each symbol keeps the call form and the `list of int` result of 0.14.x while the
declaration is now generic. The table gives the declaration as written in the
source and the argument/return shape it implies.

### Reductions and statistics

| Symbol | Signature | Semantics |
|---|---|---|
| `sum shard T where T: Num` | `(l: list of T) -> T` | Total; empty → `donum T`. |
| `product shard T where T: Num` | `(l: list of T) -> T` | Product; empty → `1`. |
| `mean shard T where T: Num` | `(l: list of T) -> T` | Truncated towards zero (`[1, 2]` → 1); empty → `donum T`. |
| `average shard T where T: Num` | `(l: list of T) -> T` | *(deprecated — use `mean`)* |
| `sum_of_squares shard T where T: Num` | `(l: list of T) -> T` | Σ x²; empty → `donum T`. |
| `median shard T where T: Num and T: Ordered` | `(l: list of T) -> T` | Sorting median; even length averages the central values; empty → `donum T`. |
| `mode shard T where T: Donum and T: Par` | `(l: list of T) -> T` | Most frequent (first wins on a tie); empty → `donum T`. |
| `max_val shard T where T: Donum and T: Ordered` | `(l: list of T) -> T` | Maximum; empty → the `donum T` sentinel. |
| `min_val shard T where T: Donum and T: Ordered` | `(l: list of T) -> T` | Minimum; empty → the `donum T` sentinel. |
| `dot shard T where T: Num` | `(a: list of T, b: list of T) -> T` | Dot product up to the shorter list; `donum T` when either side is empty. |

### Access, search and predicates

| Symbol | Signature | Semantics |
|---|---|---|
| `len shard T` | `(l: list of T) -> int` | Element count; alias of the built-in `l.len`. |
| `is_empty shard T` | `(l: list of T) -> bool` | True when `l` has no elements. |
| `first shard T where T: Donum` | `(l: list of T) -> T` | First element, or `donum T` when empty. |
| `last shard T where T: Donum` | `(l: list of T) -> T` | Last element, or `donum T` when empty. |
| `at_or` | `(l: list of int, idx: int, default: int is 0) -> int` | Element at `idx`, or `default` out of range. **Concrete on purpose**: a generic parameter cannot carry a `T`-dependent `is` default. |
| `at_or_shard shard T where T: Donum` | `(l: list of T, idx: int, default: T) -> T` | Widened form of `at_or`; the default is explicit because no `T` default exists. |
| `at_safe shard T where T: Donum` | `(l: list of T, idx: int) -> maybe T` | `some v`, or `none` out of range; `banish` the `maybe`. |
| `contains shard T where T: Par` | `(l: list of T, item: T) -> bool` | Membership; alias of the built-in `l.contains`. |
| `index_of shard T where T: Par` | `(l: list of T, item: T) -> int` | First occurrence, or -1. |
| `last_index_of shard T where T: Par` | `(l: list of T, item: T) -> int` | Last occurrence, or -1. |
| `count_of shard T where T: Par` | `(l: list of T, item: T) -> int` | Occurrences of `item`. |
| `find_first_gt shard T where T: Ordered` | `(l: list of T, threshold: T) -> maybe T` | First element `> threshold`, else `none`. |
| `find_first_lt shard T where T: Ordered` | `(l: list of T, threshold: T) -> maybe T` | First element `< threshold`, else `none`. |
| `max_index shard T where T: Ordered` | `(l: list of T) -> int` | First index of the maximum; empty → -1. |
| `min_index shard T where T: Ordered` | `(l: list of T) -> int` | First index of the minimum; empty → -1. |
| `argmin shard T where T: Ordered` | `(l: list of T) -> int` | *(deprecated — use `min_index`)* |
| `argmax shard T where T: Ordered` | `(l: list of T) -> int` | *(deprecated — use `max_index`)* |
| `is_sorted_asc shard T where T: Ordered` | `(l: list of T) -> bool` | Non-descending order test. |
| `is_sorted_desc shard T where T: Ordered` | `(l: list of T) -> bool` | Non-ascending order test. |
| `all_positive shard T where T: Num and T: Ordo` | `(l: list of T) -> bool` | Every element strictly positive; empty → true. |
| `all_zero shard T where T: Donum and T: Par` | `(l: list of T) -> bool` | Every element equal to `donum T`; empty → true. |
| `any_negative shard T where T: Num and T: Ordo` | `(l: list of T) -> bool` | At least one strictly negative; empty → false. |
| `all_in_range shard T where T: Ordered` | `(l: list of T, lo: T, hi: T) -> bool` | Every element in `[lo, hi]`; empty → true. |

### Transformation, selection and filtering

| Symbol | Signature | Semantics |
|---|---|---|
| `concat shard T` | `(a: list of T, b: list of T) -> list of T` | New list `a` followed by `b`. |
| `zip_sum shard T where T: Num` | `(a: list of T, b: list of T) -> list of T` | Element-wise sum up to the shorter list. |
| `repeat shard T` | `(val: T, times: int) -> list of T` | New list with `val` repeated `times` times. |
| `reverse shard T` | `(l: list of T) -> list of T` | New reversed copy. |
| `sort_asc shard T where T: Ordered` | `(l: list of T) -> list of T` | New ascending copy. |
| `sort_desc shard T where T: Ordered` | `(l: list of T) -> list of T` | New descending copy. |
| `unique shard T where T: Par` | `(l: list of T) -> list of T` | New list without duplicates, first-appearance order. |
| `dedup shard T where T: Par` | `(l: list of T) -> list of T` | *(deprecated — use `unique`)* |
| `flatten shard T` | `(l: list of T) -> list of T` | Identity copy. |
| `take shard T` | `(l: list of T, n: int is 1) -> list of T` | First `n` elements, clipped to the length. |
| `drop shard T` | `(l: list of T, n: int is 1) -> list of T` | Elements from index `n` onwards. |
| `slice_list shard T` | `(l: list of T, start: int, end_idx: int) -> list of T` | Sub-list `[start, end_idx)`. |
| `abs_all shard T where T: Num and T: Ordo` | `(l: list of T) -> list of T` | New copy with absolute values. |
| `clamp_all` | `(l: list of int, lo: int is 0, hi: int is 100) -> list of int` | New copy clipped to `[lo, hi]`. **Concrete on purpose** (see `clamp_all_shard`). |
| `clamp_all_shard shard T where T: Num and T: Ordo` | `(l: list of T, lo: T, hi: T) -> list of T` | Widened form of `clamp_all`; both bounds are explicit. |
| `map_double shard T where T: Num` | `(l: list of T) -> list of T` | New copy with every element doubled. |
| `map_square shard T where T: Num` | `(l: list of T) -> list of T` | New copy with every element squared. |
| `map_negate shard T where T: Num` | `(l: list of T) -> list of T` | New copy with every element negated. |
| `map_add_scalar shard T where T: Num` | `(l: list of T, k: T) -> list of T` | New copy with `k` added to every element. |
| `map_increment shard T where T: Num` | `(l: list of T, delta: int is 1) -> list of T` | New copy with `delta` added to every element. |
| `filter_even shard T where T: Integrum and T: Par` | `(l: list of T) -> list of T` | Elements with `x % 2 == 0`. |
| `filter_odd shard T where T: Integrum and T: Par` | `(l: list of T) -> list of T` | Elements with `x % 2 != 0`. |
| `filter_positive shard T where T: Num and T: Ordo` | `(l: list of T) -> list of T` | Strictly positive elements. |
| `filter_negative shard T where T: Num and T: Ordo` | `(l: list of T) -> list of T` | Strictly negative elements. |
| `filter_in_range shard T where T: Ordered` | `(l: list of T, lo: T, hi: T) -> list of T` | Elements inside `[lo, hi]`. |
| `filter_range shard T where T: Ordered` | `(l: list of T, lo: T, hi: T) -> list of T` | *(deprecated — use `filter_in_range`)* |

## Module functions — newer `shard T` API

| Symbol | Signature | Semantics |
|---|---|---|
| `zip_with shard T and U and V` | `(xs: list of T, ys: list of U, f: weave with a as T, b as U -> V) -> list of V` | Combine pairwise up to the shorter list. |
| `chunk shard T` | `(xs: list of T, span: int) -> list of list of T` | Consecutive runs of `span` (last may be shorter); `span <= 0` → empty. |
| `windowed shard T` | `(xs: list of T, width: int) -> list of list of T` | Sliding windows of width `width`; `width <= 0` or `> len` → empty. |
| `scan_left shard T where T: Num` | `(xs: list of T, f: weave with acc as T, x as T -> T) -> list of T` | Cumulative scan seeded with `xs[0]`, same length; empty → empty. |
| `running_sum shard T where T: Num` | `(xs: list of T) -> list of T` | Prefix sums; `out[i] == sum(xs[0..i])`; empty → empty. |
| `min_max shard T where T: Ordered` | `(xs: list of T) -> list of T` | `[min, max]`, or `[]` when empty; no tuples, no `std.oracle`. |
| `enumerate_pairs` | `(xs: list of int) -> list of list of int` | One `[index, value]` pair per element, in order. |
| `partition_by` | `(xs: list of int, predicate: weave with x as int into bool) -> list of list of int` | `[matching, non_matching]` (either may be empty). |
| `frequencies shard T where T: Vinculum` | `(xs: list of T) -> map of T to int` | Value → count map; empty list → empty map. |
| `group_count shard T where T: Vinculum` | `(xs: list of T) -> map of T to int` | *(deprecated — use `frequencies`)* |

`enumerate_pairs` and `partition_by` stay concrete: they mix an `int` index or an
`int`-typed predicate with the element, so a `shard T` form would need a second
type parameter and a heterogeneous row.

## Compatibility and migration

* Every 0.14.x/2.1.0 symbol keeps its name; the generic widening is additive at
  the call site (a `list of int` argument still resolves and behaves identically)
  and `at_or` / `clamp_all` still declare their exact concrete `int` signature.
* Deprecated symbols are ordinary `weave`s whose docstring starts with
  `## @deprecated Use X instead.` — there is **no** real `@deprecated` attribute,
  so none of them emits `W0006`. See [`DEPRECATIONS.md`](DEPRECATIONS.md).
* Deprecated aliases repeat the base body on purpose: a generic body cannot call
  another generic `weave`/method (the compiler emits the `_T` template), so
  `average`, `argmin`, `argmax`, `dedup` and `filter_range` are self-contained
  copies, not one-line forwards.
* `2.2.0` adds `at_or_shard` and `clamp_all_shard`; no symbol is removed or
  renamed.

| Before (0.14.x) | Now (`2.2.0`) |
|---|---|
| `calling tally.sum with xs` | same, or `calling xs.sum`; also `calling tally.sum with floats`, `… with words` |
| `calling tally.sort_asc with xs` | same, or `calling xs.sort_asc`; strings work through `T: Ordered` |
| `calling tally.clamp_all with xs, 0, 9` | same (`list of int`), or `calling tally.clamp_all_shard with fs, 0.0, 9.0` |
| `calling tally.at_or with xs, 3` | same (`list of int`), or `calling tally.at_or_shard with ws, 3, "?"` |
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
