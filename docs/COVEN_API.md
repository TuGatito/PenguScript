# `std.coven` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `COVEN_VERSION`.
>
> Module revision: **`2.2.0`**.
> Source: [`std/coven.pengu`](../std/coven.pengu).

`coven` owns unique-element collections. Every set is a rune whose single field
is a `map of ... to int` in which the elements are the keys and the value is a
constant `1`; membership, insertion and removal are the backing map's
`contains`, `put` and `remove`, i.e. the `std.atlas` enchantings — `coven` is a
thin layer over `std.atlas`. It also imports `std.scrolls` (`string.starts_with`,
used by `filter_starts_with`) and `std.spark` (`parse_int`, test `panic`). No
module in `std/` imports `coven`; its consumers are user programs and tests.

Three types make up the surface. `SetString` and `SetInt` are the legacy
concrete runes of the 0.14.x line, kept verbatim for 0.14.x/0.15.0
compatibility: same names, same signatures, same observable results. The new
`rune Set shard T` generalises sets to any hashable `T` (`Vinculum`), backed by
`map of T to int`. The legacy runes are deprecated in favour of the generic one;
new code should use `Set of T`.

All three types share one method vocabulary (`add`, `contains`, `remove`, `len`,
`clear`, `is_empty`, the set algebra, `clone`, `to_list`, …). The generic set adds
the generic module functions `make_set shard T` / `from_items_set shard T` and the
nine concrete constructors `new_int_set`, `new_string_set`, `new_float_set`,
`new_bool_set`, `new_char_set`, `new_i64_set`, `new_u64_set`, `new_usize_set` and
`new_isize_set`. There is deliberately no `Set.empty` (see below).

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| `self` in every method | borrowed receiver; `add`/`remove`/`clear` mutate `self.items` in place | never `banish self` |
| `other`, `item`, `prefix`, `n`, `items` parameters | borrowed, read-only; never mutated or freed | caller keeps its own release |
| the backing map `s.items` of any set | owned by the set; `add` copies the element into it (string elements for `SetString`/`SetInt`) | **`banish s.items`** |
| every set return (`union`, `intersect`, `difference`, `symmetric_difference`, `clone`, `filter_starts_with`, `filter_length_ge`, `to_set_int`, `to_set_string`, all constructors) | owned, freshly allocated | `banish <name>.items` |
| every list return (`to_list`, `to_list_int`) | owned, freshly allocated in backing-map hash order | `banish xs` |
| scalar returns (`bool`, `int`) | plain value | never `banish` |

> **A set has no runtime cleanup — release the backing map with
> `banish s.items`.** `SetString`, `SetInt` and `Set of T` are runes, so the
> compiler emits no `banish` entry point for them: `banish s` does not exist and
> nothing frees `s.items` for you. This was measured during the migration and is
> a real constraint of the frozen contract. Free every set you own explicitly —
> `banish s.items`, or `defer banish s.items` — including the sets returned by
> `clone`, `union`, `intersect`, `difference` and `symmetric_difference`.

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `COVEN_VERSION` | `string` | `"2.2.0"` | Revision of the **coven API**, not of the toolchain. 2.1.0 added the generic `Set of T`; 2.2.0 adds the wide-integer constructors (`new_i64_set`, `new_u64_set`, `new_usize_set`, `new_isize_set`) and records the verified element-type matrix. It bumps only when a signature on this page changes. |

## Legacy `SetString`

`rune SetString:` holds `items as map of string to int`. Creating an element
already present is a no-op; its methods are declared in `enchanting SetString`.
The rune docstring carries
``## @deprecated Use the generic `Set of string` instead.``

### Construction

| Symbol | Signature | Semantics |
|---|---|---|
| `new_set_string` | `() -> SetString` | Owned empty `SetString`; backing map freshly allocated. |
| `empty_set_string` | `() -> SetString` | `ritual` alias of `new_set_string`. |
| `from_list_string` | `(items: list of string) -> SetString` | Owned set holding each distinct element of `items` once; `items` is borrowed. |
| `SetString.empty` | `() -> SetString` | Static `ritual` on the rune; alias of `new_set_string`. |
| `SetString.from_items` | `(items: list of string) -> SetString` | Static `ritual`; forwards to `from_list_string`. |

### Instance methods

| Method | Signature | Semantics |
|---|---|---|
| `add` | `(item: string) -> void` | Puts `item → 1`; a duplicate is a no-op. |
| `contains` | `(item: string) -> bool` | Membership; reads only. |
| `remove` | `(item: string) -> bool` | `true` when `item` was present and has been removed. |
| `len` | `() -> int` | Number of distinct elements. |
| `clear` | `() -> void` | Removes every element in place. |
| `is_empty` | `() -> bool` | True when the set holds no elements. |
| `union` | `(other: SetString) -> SetString` | Fresh set with the elements of both; `other` borrowed. |
| `intersect` | `(other: SetString) -> SetString` | Fresh set with the elements present in both. |
| `difference` | `(other: SetString) -> SetString` | Fresh set with the elements of `self` absent from `other`. |
| `symmetric_difference` | `(other: SetString) -> SetString` | Fresh set with the elements in exactly one side; built as `self.difference(other)` union `other.difference(self)`. |
| `is_subset` | `(other: SetString) -> bool` | True when every element of `self` is in `other`. |
| `is_superset` | `(other: SetString) -> bool` | True when every element of `other` is in `self`; delegates to `other.is_subset`. |
| `is_disjoint` | `(other: SetString) -> bool` | True when the sets share no element. |
| `equals` | `(other: SetString) -> bool` | Equal length and `self.is_subset(other)`; order-independent. |
| `clone` | `() -> SetString` | Fresh independent copy. |
| `to_list` | `() -> list of string` | Owned list of the elements in backing-map hash order (not insertion order). |
| `to_set_int` | `() -> SetInt` | Fresh `SetInt` from `spark.parse_int` of each element; unparseable elements are skipped. |
| `filter_starts_with` | `(prefix: string) -> SetString` | Fresh set of the elements with `starts_with(prefix)`. |
| `filter_length_ge` | `(n: int) -> SetString` | Fresh set of the elements whose byte length is `>= n`. |

## Legacy `SetInt`

`rune SetInt:` holds `items as map of string to int`; each element is stored
under its decimal string (`item to string`), unlike the generic `Set of int`,
which stores the `int` itself. Deduplication behaviour matches `SetString`; its
methods are declared in `enchanting SetInt`. The rune docstring carries
``## @deprecated Use the generic `Set of int` instead.``

### Construction

| Symbol | Signature | Semantics |
|---|---|---|
| `new_set_int` | `() -> SetInt` | Owned empty `SetInt`; backing map freshly allocated. |
| `empty_set_int` | `() -> SetInt` | `ritual` alias of `new_set_int`. |
| `from_list_int` | `(items: list of int) -> SetInt` | Owned set holding each distinct element of `items` once; `items` is borrowed. |
| `SetInt.empty` | `() -> SetInt` | Static `ritual` on the rune; alias of `new_set_int`. |
| `SetInt.from_items` | `(items: list of int) -> SetInt` | Static `ritual`; forwards to `from_list_int`. |

### Instance methods

| Method | Signature | Semantics |
|---|---|---|
| `add` | `(item: int) -> void` | Puts the decimal string of `item → 1`; a duplicate is a no-op. |
| `contains` | `(item: int) -> bool` | Membership under the decimal key; reads only. |
| `remove` | `(item: int) -> bool` | `true` when `item` was present and has been removed. |
| `len` | `() -> int` | Number of distinct elements. |
| `clear` | `() -> void` | Removes every element in place. |
| `is_empty` | `() -> bool` | True when the set holds no elements. |
| `union` | `(other: SetInt) -> SetInt` | Fresh set with the elements of both; `other` borrowed. |
| `intersect` | `(other: SetInt) -> SetInt` | Fresh set with the elements present in both. |
| `difference` | `(other: SetInt) -> SetInt` | Fresh set with the elements of `self` absent from `other`. |
| `symmetric_difference` | `(other: SetInt) -> SetInt` | Fresh set with the elements in exactly one side; two temporaries plus a union. |
| `is_subset` | `(other: SetInt) -> bool` | True when every element of `self` is in `other`. |
| `is_superset` | `(other: SetInt) -> bool` | True when every element of `other` is in `self`; delegates to `other.is_subset`. |
| `is_disjoint` | `(other: SetInt) -> bool` | True when the sets share no element. |
| `equals` | `(other: SetInt) -> bool` | Equal length and `self.is_subset(other)`; order-independent. |
| `clone` | `() -> SetInt` | Fresh independent copy of the backing map. |
| `to_list_int` | `() -> list of int` | Owned list of the parsed elements in hash order; unparseable keys are skipped. |
| `sum_ints` | `() -> int` | Sum of the parsed elements; the empty set collapses to the identity `0`. |
| `min_int` | `() -> int` | Smallest parsed element; empty set → `0`. |
| `max_int` | `() -> int` | Largest parsed element; empty set → `0`. |
| `to_set_string` | `() -> SetString` | Fresh `SetString` with the same (stringified) keys. |

## `Set of T` — generic set

```pengu
rune Set shard T:
    items as map of T to int
```

`T` may be any hashable type: every integer width (`int`, `i8`..`i64`,
`u8`..`u64`, `byte`, `usize`, `isize`), `float`/`f32`/`f64`, `char`, `bool`,
`string`, or a user `rune ... derive Par, Vinculum`. The element is stored as the
map key, so a narrow width is **not** widened to `int`. A `rune` has no `where`
clause, so `rune Set shard T` cannot spell `where T: Vinculum`; the requirement is
enforced by the backing field `items as map of T to int`, which only
instantiates for a `Vinculum` key type. One behavioural sharp edge: `Set of float`
compares keys by bit pattern, so `0.0` and `-0.0` are two distinct elements even
though `0.0 == -0.0`.

### Constructor functions

| Symbol | Signature | Semantics |
|---|---|---|
| `make_set shard T` | `() -> Set of T` | Owned empty generic set; `T` must be named (`calling make_set of int`). |
| `from_items_set shard T` | `(items: list of T) -> Set of T` | Owned set with each distinct element of `items` once; `items` is borrowed. |
| `new_int_set` | `() -> Set of int` | Concrete `ritual` constructor for `Set of int`. |
| `new_string_set` | `() -> Set of string` | Concrete `ritual` constructor for `Set of string`. |
| `new_float_set` | `() -> Set of float` | Concrete `ritual` constructor for `Set of float`. |
| `new_bool_set` | `() -> Set of bool` | Concrete `ritual` constructor for `Set of bool`. |
| `new_char_set` | `() -> Set of char` | Concrete `ritual` constructor for `Set of char`. |
| `new_i64_set` | `() -> Set of i64` | Concrete `ritual` constructor for `Set of i64` (added in `2.2.0`). |
| `new_u64_set` | `() -> Set of u64` | Concrete `ritual` constructor for `Set of u64` (added in `2.2.0`). |
| `new_usize_set` | `() -> Set of usize` | Concrete `ritual` constructor for `Set of usize` (added in `2.2.0`). |
| `new_isize_set` | `() -> Set of isize` | Concrete `ritual` constructor for `Set of isize` (added in `2.2.0`; negative keys stay distinct). |

The nine concrete constructors are ordinary module-level `weave ritual`s; they
are the safe way to build a set of a widely-used element type without naming `T`
at the call site. For any other `T` use `make_set of T` /
`from_items_set of T with xs`, which keep working with several specialisations.

### Instance methods

Defined in `enchanting Set shard T`. The bodies read `self->items` (or
`other.items`) directly; see the codegen note below.

| Method | Signature | Semantics |
|---|---|---|
| `add` | `(item: T) -> void` | Puts `item → 1`; a duplicate is a no-op. |
| `contains` | `(item: T) -> bool` | Membership; reads only. |
| `remove` | `(item: T) -> bool` | `true` when `item` was present and has been removed. |
| `len` | `() -> int` | Number of distinct elements. |
| `clear` | `() -> void` | Removes every element in place. |
| `is_empty` | `() -> bool` | True when the set holds no elements. |
| `union` | `(other: Set of T) -> Set of T` | Fresh set with the elements of both; `other` borrowed. |
| `intersect` | `(other: Set of T) -> Set of T` | Fresh set with the elements present in both. |
| `difference` | `(other: Set of T) -> Set of T` | Fresh set with the elements of `self` absent from `other`. |
| `symmetric_difference` | `(other: Set of T) -> Set of T` | Fresh set with the elements in exactly one side; walks both maps. |
| `is_subset` | `(other: Set of T) -> bool` | True when every element of `self` is in `other`. |
| `is_superset` | `(other: Set of T) -> bool` | True when every element of `other` is in `self`. |
| `is_disjoint` | `(other: Set of T) -> bool` | True when the sets share no element. |
| `equals` | `(other: Set of T) -> bool` | Equal length and mutual membership; order-independent. |
| `clone` | `() -> Set of T` | Fresh independent copy. |
| `to_list` | `() -> list of T` | Owned list of the elements in backing-map hash order. |

### No `Set.empty` / `Set.from_items`

There is **no** `ritual` constructor on the generic rune: no `Set.empty`, no
`Set.from_items`, no bare `Set.empty`. A type-qualified generic `ritual`
(`Set.empty of T`) is accepted by the checker but miscompiles or misbinds as
soon as the bundle holds more than one `Set of T` specialisation — always the
case in a real program — because the ritual is emitted once for the
unspecialised `T`. This is a compiler bug found in this chunk, not a design
choice that documentation can lift. Use `make_set of T` /
`from_items_set of T with xs`, or one of the nine concrete `new_*_set`
constructors. (`make_set` is named that way on purpose: `new_set of string`
would mangle to `new_set_string` and hijack the legacy module constructor of
that exact name, which then fails with `E0005`.)

### The `of T` argument is required at the call site

`T` is not inferred, so a bare `calling Set.empty` or `calling make_set` cannot
type-check (`E0005`). The call site must name the element type:

```pengu
var s as Set of int is calling make_set of int
var t as Set of string is calling from_items_set of string with names
var u as Set of float is calling new_float_set
```

### A method body cannot call another method of the same rune

Inside `enchanting Set shard T`, a body that calls another method of `Set`
(e.g. `calling self.contains with k`) makes the codegen emit the unspecialised
`_T` template and the C compilation fails. Every generic method therefore
reaches the `items` map of the receiver and of its `other` parameter directly,
and never another `Set` method. This is why `equals`, `is_subset` and the set
algebra above are self-contained rather than one-line forwards. The two legacy
concrete runes are unaffected: their methods may call each other by name.

## Compatibility and migration

* Every 0.14.x/0.15.0 name and signature of `SetString` and `SetInt` is
  preserved verbatim, including `empty_set_*`, `from_list_*`, the
  `SetString.empty`/`SetInt.empty` and `SetString.from_items`/`SetInt.from_items`
  statics, `to_set_int`, `to_set_string`, `sum_ints`, `min_int` and `max_int`.
* The two legacy runes carry the docstring marker
  ``## @deprecated Use the generic `Set of <T>` instead.`` — the docstring
  convention only. They carry no real `@deprecated(...)` attribute, so they emit
  no `W0006`. See [`DEPRECATIONS.md`](DEPRECATIONS.md).
* `2.1.0` is purely additive: the generic `rune Set shard T`, its `enchanting`,
  `make_set`, `from_items_set` and five concrete constructors. `2.2.0` adds four
  more concrete constructors (`new_i64_set`, `new_u64_set`, `new_usize_set`,
  `new_isize_set`) and documents the verified element-type matrix. Nothing is
  removed and no existing signature changes. `SetString` and `SetInt` are
  different types from `Set of string` / `Set of int` and convert only through
  `to_set_int` / `to_set_string` (or by rebuilding from a list).

| Before (0.14.x/0.15.0) | Now (`2.2.0`) |
|---|---|
| `calling new_set_string` + `s.add "x"` | `calling make_set of string` or `calling new_string_set` |
| `calling new_set_int` + `s.add 7` | `calling make_set of int` or `calling new_int_set` |
| (new in `2.2.0`) | `calling new_i64_set`, `new_u64_set`, `new_usize_set` or `new_isize_set`, or `calling make_set of i64` |
| `calling from_list_string with xs` | `calling from_items_set of string with xs` |
| `calling SetString.empty` | `calling new_string_set` (no `Set.empty`) |
| `calling s.to_list_int` | `calling s.to_list` on `Set of int` |
| `calling s.sum_ints` / `s.min_int` / `s.max_int` | no generic equivalent; keep `SetInt` or fold over `s.to_list` |

## Private helpers (internal)

Not part of the frozen surface; do not call them.

| Symbol | Signature | Role |
|---|---|---|
| `_expect_coven` | `(cond: bool, label: string) -> void` | Test harness; panics with `"coven test failed: {label}"` when `cond` is false. |
| `_expect_coven_eq_int` | `(actual: int, expected: int, label: string) -> void` | Integer equality assertion for the in-file `test` blocks. |
| `_expect_coven_eq_string` | `(actual: string, expected: string, label: string) -> void` | String equality assertion for the in-file `test` blocks. |
| `_expect_coven_eq_bool` | `(actual: bool, expected: bool, label: string) -> void` | Boolean equality assertion for the in-file `test` blocks. |
| `_TestPlayer` | `rune _TestPlayer derive Par, Vinculum`, field `id as int` | Test-only value type proving `Set of T` works with a user `rune`. |
