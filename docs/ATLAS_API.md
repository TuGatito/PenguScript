# `std.atlas` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `ATLAS_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/atlas.pengu`](../std/atlas.pengu).

`atlas` owns the associative container: `map of K to V` with its access, query,
mutation, reduction, filtering and transformation vocabulary. It imports
`std.oracle` (`Pair`, for `entries`/`from_pairs`), `std.scrolls`
(`starts_with`, `compare`) and `std.spark` (the private test harness); it is
imported by `std.coven` (a set is a map to `int`) and `std.invoke`, and it does
not import `std.ward` (the cycle would be `E0004`).

The 0.15.0 line was limited to string/int maps. 2.1.0 keeps **every** 0.15.0
name and concrete signature as a one-line forwarder over a generic method, and
adds the generic core: `enchanting map of shard K to shard V where K: Par,
V: Par` for any hashable `K`/`V`, a numeric block, two order blocks and a bool
block. `insignia atlas_` keeps the `remove` wrapper from colliding with the C
`remove` of `stdio.h` without renaming any Pengu symbol. The headline is the
ordering extension point: `keys_sorted`/`values_sorted` are no longer
string/int-only but run through the `concept Ordered`.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| `self` in the mutating methods (`put`, `update`, `rename_key`, `remove`, `clear`, `remove_all`, `put_all`) | `ref to` the receiver; mutated in place | never `banish self` |
| every other input (`m`, `other`, `a`, `b`, `keys`, `ks`, `vs`, `ps`, `maps`, `f`, `predicate`, `factor`, `lo`, `hi`) | borrowed, read-only; never mutated or freed | never `banish` |
| scalar returns (`int`, `bool`, `V`) | plain value | never `banish` |
| `get_safe`, `find_key_by_value` | `maybe` boxing a heap cell | `banish` the whole `maybe` |
| every `list` return (`keys`, `values`, `entries`, `keys_sorted`, `values_sorted`, `to_keys_list`, `to_values_list` and the `_sorted_*` wrappers) | owned, freshly allocated in internal hash order unless the name says `sorted` | `banish` the list (and every owned `Pair` field of `entries`) |
| every `map` return (`clone`, `copy`, `invert`, `take_keys`, `filter_entries`, `map_values_with`, `merge_all`, `map_values_*`, `filter_values_range`, `filter_keys_*`, `filter_values_contains`, `map_merge*`, `map_from_lists`, `from_pairs`, `map_filter_values_contains`) | owned, freshly allocated; a shallow copy (`clone`/`copy` share owned values, they do not deep-copy) | `banish` the map, then any owned value it shares |

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `ATLAS_VERSION` | `string` | `"2.1.0"` | Revision of the **atlas API**, not of the toolchain. Bumps only when a signature on this page changes. |

## Ordering extension point (`concept Ordered`)

`keys_sorted` / `values_sorted` need a total order that also works for
`PenguString`. An `enchanting` bound such as `K: Ordo` cannot provide it:
**`enchanting` bounds are not enforced at method resolution**, and a generic
body that compares with `>` emits a raw C `>`, which does not compile for
`PenguString`. A generic `keys_sorted` written against a bound is therefore
monomorphised — and fails — even when a concrete override exists. The module's
answer is a `concept` whose method is dispatched per bound type:

```pengu
concept Ordered shard T:
    weave cmp with other as T into int
```

`cmp` returns `1` when the receiver sorts after `other`, `-1` before, `0` equal.
`int`, `i32`, `i64`, `f32`, `f64` use the native operators; `float` is 32-bit
like `f32`; `string` delegates to `calling me.compare` (byte order, NUL-safe).

| Bind | Method added | Semantics |
|---|---|---|
| `bind int with Ordered` | `cmp(other: int) -> int` | Native comparison of the two `int` values. |
| `bind i32 with Ordered` | `cmp(other: i32) -> int` | Native comparison of the two `i32` values. |
| `bind i64 with Ordered` | `cmp(other: i64) -> int` | Native comparison of the two `i64` values. |
| `bind float with Ordered` | `cmp(other: float) -> int` | Native comparison of the two 32-bit floats. |
| `bind f32 with Ordered` | `cmp(other: f32) -> int` | Native comparison of the two `f32` values. |
| `bind f64 with Ordered` | `cmp(other: f64) -> int` | Native comparison of the two `f64` values. |
| `bind string with Ordered` | `cmp(other: string) -> int` | `1`/`-1`/`0` from `calling me.compare`; byte order, NUL-safe. |

### Extending the order to a user type

After `import std.atlas`, a `seal`/`rune` key (or value) gets its own
**unqualified** bind; an `alias` needs no bind, because it unwraps to its base
type and inherits that type's bind.

```pengu
import std.atlas

seal UserId as int                 # a `rune` key works the same way

bind UserId with Ordered:          # UNQUALIFIED: `atlas.Ordered` is E0004
    weave cmp with other as UserId into int:
        ...                        # 1 / -1 / 0, like the primitive binds

var ks as list of UserId is calling m.keys_sorted
```

Both `bind` restrictions are compiler behaviour, not atlas policy: the qualified
`bind X with atlas.Ordered:` is `E0004`, and a `_`-private target (`seal _X` +
`bind _X`) is `E0004 Undefined type ''` too.

### Which types are covered

`bind <T> with Ordered:` only accepts names the compiler registers as primitive:
`i8`, `i16`, `u8`, `u16`, `u32`, `u64`, `usize`, `isize`, `char`, `double`,
`byte` and the C spellings (`int32_t`, …) are all rejected with
`E0004 Undefined type '<name>' in bind declaration`. The generic `keys_sorted` /
`values_sorted` therefore cover exactly `{int, i32, i64, float, f32, f64,
string}`, `alias`es of those, and user types with their own bind. Narrow and
unsigned integers are out of scope, and 2.1.0 deliberately declares **no**
per-type concrete block for them: generalising is the contract, and duplicating
the sort per primitive was rejected.

## Generic methods

A method cannot carry `where`, so each `enchanting` block fixes the bound for
all its methods. `K` must be hashable; `V: Ordo` in the numeric block is what
allows the `>`/`<` reductions (the ordering **sorter** uses `Ordered`, not
`Ordo`).

### `enchanting map of shard K to shard V where K: Par, V: Par`

| Method | Signature | Semantics |
|---|---|---|
| `size` | `() -> int` | Number of entries; `(essence of self).len`. |
| `is_empty` | `() -> bool` | True when `size == 0`. |
| `has_key` | `(key: K) -> bool` | Membership; `calling self.contains with key`. |
| `has_any_key` | `(keys: list of K) -> bool` | True on the first match; empty list → false. |
| `has_all_keys` | `(keys: list of K) -> bool` | True when every key is present; empty list → true. |
| `get_or` | `(key: K, fallback: V) -> V` | Stored value, or `fallback` when absent. |
| `get_safe` | `(key: K) -> maybe V` | `some v`, or `maybe none`; caller releases the `maybe`. |
| `find_key_by_value` | `(target: V) -> maybe K` | First key equal to `target` in hash order, else `maybe none`. |
| `update` | `(key: K, value: V) -> bool` | Replaces an existing key only; `false` (and no insert) when absent. |
| `rename_key` | `(old_key: K, new_key: K) -> bool` | Moves the value; `false` when `old_key` is absent; a collision overwrites the destination. |
| `remove` | `(key: K) -> bool` | `true` when the key existed and was removed. |
| `clear` | `() -> void` | Empties the receiver in place. |
| `remove_all` | `(keys: list of K) -> int` | Number of entries actually removed. |
| `put_all` | `(other: map of K to V) -> void` | Copies every entry of `other`, overwriting existing keys. |
| `keys` | `() -> list of K` | Owned list in internal hash order. |
| `values` | `() -> list of V` | Owned list in internal hash order. |
| `clone` | `() -> map of K to V` | Owned shallow copy. |
| `copy` | `() -> map of K to V` | Alias of `clone`. |
| `is_equal` | `(other: map of K to V) -> bool` | Same size and same value for every key, order-independent. |
| `to_keys_list` | `() -> list of K` | Alias of `keys`. |
| `to_values_list` | `() -> list of V` | Alias of `values`. |
| `entries` | `() -> list of oracle.Pair of K and V` | Owned `[key, value]` pairs, in hash order. |
| `invert` | `() -> map of V to K` | Swaps keys and values; on a value collision the last key visited wins. |
| `take_keys` | `(ks: list of K) -> map of K to V` | Submap with the requested keys that exist; missing keys skipped. |
| `count_where` | `(predicate: weave with k as K, v as V -> bool) -> int` | Entries accepted by `predicate`. |
| `filter_entries` | `(predicate: weave with k as K, v as V -> bool) -> map of K to V` | Owned submap with the accepted entries. |
| `map_values_with` | `(f: weave with x as V -> V) -> map of K to V` | Owned map with the same keys and `f` applied to every value. |
| `merge_all` | `(others: list of map of K to V) -> map of K to V` | Owned merge of the receiver with each map of `others`; later maps win. |

### `enchanting map of shard K to shard V where K: Par, V: Num and V: Ordo`

| Method | Signature | Semantics |
|---|---|---|
| `sum_values` | `() -> V` | Sum of all values; empty map → `donum V` (`0`). |
| `sum_values_filtered` | `(lo: V, hi: V) -> V` | Sum of the values inside `[lo, hi]`; none in range → `donum V`. |
| `all_values_positive` | `() -> bool` | True when no value is `<= donum V`; empty → true. |
| `any_value_negative` | `() -> bool` | True on the first value `< donum V`; empty → false. |
| `count_if_value_positive` | `() -> int` | Number of values `> 0`. |
| `count_if_value_negative` | `() -> int` | Number of values `< 0`. |
| `map_values_double` | `() -> map of K to V` | Owned map with every value `v + v`. |
| `map_values_negate` | `() -> map of K to V` | Owned map with every value `-v`. |
| `map_values_scale` | `(factor: V) -> map of K to V` | Owned map with every value `v * factor`. |
| `max_value` | `() -> V` | Largest value; empty map → `donum V` (sentinel, not an error). |
| `min_value` | `() -> V` | Smallest value; empty map → `donum V`. |
| `values_in_range` | `(lo: V, hi: V) -> bool` | True when every value is in `[lo, hi]`; empty → true. |
| `filter_values_range` | `(lo: V, hi: V) -> map of K to V` | Owned submap with the values inside `[lo, hi]`. |

### Ordering blocks — `keys_sorted` / `values_sorted`

| Block | Method | Signature | Semantics |
|---|---|---|---|
| `enchanting map of shard K to shard V where K: Ordered, V: Par` | `keys_sorted` | `() -> list of K` | Owned keys sorted ascending through `calling K.cmp`; insertion sort, O(n²). |
| `enchanting map of shard K to shard V where K: Par, V: Ordered` | `values_sorted` | `() -> list of V` | Owned values sorted ascending through `calling V.cmp`. |

### `enchanting map of shard K to bool shard K and V where K: Par, V: Par`

| Method | Signature | Semantics |
|---|---|---|
| `count_true` | `() -> int` | Entries whose value is `true`. |
| `count_false` | `() -> int` | Entries whose value is `false`. |

The second shard parameter (`shard K and V`) is a **compiler workaround**: a map
carries two type arguments and a generic method only resolves when the number of
shard parameters matches them. With a single shard parameter every call fails
with `E0005 Could not infer type parameter(s) K`. `V` does not occur in the
receiver type; it only lets the compiler bind the map's two arguments.

### Concrete blocks that keep the string filters

A mixed `map of string to shard V` cannot infer `V` for a method whose return
type mentions it (`E0005`), so the three string filters stay in concrete blocks.
`map of shard K to bool` returning `int` is fine, which is why `count_true` /
`count_false` were generalised instead.

| Block | Method | Signature |
|---|---|---|
| `enchanting map of string to int` | `filter_keys_contains` | `(sub: string) -> map of string to int` |
| `enchanting map of string to int` | `filter_keys_startswith` | `(prefix: string) -> map of string to int` |
| `enchanting map of string to float` | `filter_keys_contains` | `(sub: string) -> map of string to float` |
| `enchanting map of string to float` | `filter_keys_startswith` | `(prefix: string) -> map of string to float` |
| `enchanting map of string to string` | `filter_keys_contains` | `(sub: string) -> map of string to string` |
| `enchanting map of string to string` | `filter_keys_startswith` | `(prefix: string) -> map of string to string` |
| `enchanting map of string to string` | `filter_values_contains` | `(sub: string) -> map of string to string` |
| `enchanting map of string to bool` | `filter_keys_contains` | `(sub: string) -> map of string to bool` |
| `enchanting map of int to string` | `filter_values_contains` | `(sub: string) -> map of int to string` |

`filter_keys_contains` keeps the entries whose key contains `sub`;
`filter_keys_startswith` those whose key starts with `prefix`;
`filter_values_contains` those whose value contains `sub`. All return owned
submaps; all borrow the receiver.

## Module functions — generic `shard K`/`shard V`

| Symbol | Signature | Semantics |
|---|---|---|
| `map_size shard K, V` | `(m: map of K to V) -> int` | Entry count. |
| `map_is_empty shard K, V` | `(m: map of K to V) -> bool` | `m.len == 0`. |
| `map_has_key shard K, V` | `(m: map of K to V, key: K) -> bool` | Membership. |
| `map_get_or shard K, V` | `(m: map of K to V, key: K, fallback: V) -> V` | Value or `fallback`. |
| `map_keys shard K, V` | `(m: map of K to V) -> list of K` | Owned keys in hash order. |
| `map_values shard K, V` | `(m: map of K to V) -> list of V` | Owned values in hash order. |
| `map_put shard K, V` | `(m: map of K to V, key: K, value: V) -> void` | Inserts/updates — **cannot mutate the caller's map** (see limitation). |
| `map_remove shard K, V` | `(m: map of K to V, key: K) -> bool` | Removes — **cannot mutate the caller's map**. |
| `map_clear shard K, V` | `(m: map of K to V) -> void` | Empties — **cannot mutate the caller's map**. |
| `keys_sorted_of shard K and V where K: Ordered, V: Par` | `(m: map of K to V) -> list of K` | Owned keys sorted through the `Ordered` bind of `K`. |
| `values_sorted_of shard K and V where K: Par, V: Ordered` | `(m: map of K to V) -> list of V` | Owned values sorted through the `Ordered` bind of `V`. |
| `map_merge shard K and V where K: Par, V: Par` | `(a: map of K to V, b: map of K to V) -> map of K to V` | Owned union; `b` wins on collision. |
| `map_merge_keep_left shard K and V where K: Par, V: Par` | `(a: map of K to V, b: map of K to V) -> map of K to V` | Owned union; `a` wins on collision. |
| `map_merge_all shard K and V where K: Par, V: Par` | `(maps: list of map of K to V) -> map of K to V` | Owned fold; later maps win. |
| `map_from_lists shard K and V where K: Par, V: Par` | `(ks: list of K, vs: list of V) -> map of K to V` | Owned map of `min(ks.len, vs.len)` entries; later duplicates win. |
| `from_pairs shard K and V where K: Par, V: Par` | `(ps: list of oracle.Pair of K and V) -> map of K to V` | Owned map; later duplicate keys win. |
| `map_filter_values_contains shard K where K: Par` | `(m: map of K to string, sub: string) -> map of K to string` | Owned submap with the values containing `sub`; infers `K`, so it is the portable form of the concrete `filter_values_contains`. |

## 0.15.0 compatibility wrappers

Every 0.15.0 symbol survives verbatim as a one-line forwarder to the matching
generic **method** (never to another module function). Because a module `map`
parameter is passed by value, the mutating wrappers below are recorded with the
limitation in `## Known limitation (tracked debt)`.

### `map of string to int` — the original 0.15.0 names

| Symbol | Signature | Semantics |
|---|---|---|
| `size` | `(m: map of string to int) -> int` | `calling m.size`. |
| `is_empty` | `(m: map of string to int) -> bool` | `calling m.is_empty`. |
| `has_key` | `(m: map of string to int, key: string) -> bool` | `calling m.has_key with key`. |
| `get_or` | `(m: map of string to int, key: string, default: int is 0) -> int` | Value or `default`. |
| `get_safe` | `(m: map of string to int, key: string) -> maybe int` | `maybe`; banish it. |
| `put` | `(m: map of string to int, key: string, value: int) -> void` | Insert/update — by-value copy (limitation). |
| `remove` | `(m: map of string to int, key: string) -> bool` | Remove — by-value copy (limitation). |
| `clear` | `(m: map of string to int) -> void` | Clear — by-value copy (limitation). |
| `keys` | `(m: map of string to int) -> list of string` | Owned keys, hash order. |
| `values` | `(m: map of string to int) -> list of int` | Owned values, hash order. |
| `sum_values` | `(m: map of string to int) -> int` | Total; empty → 0. |
| `max_value` | `(m: map of string to int) -> int` | Maximum; empty → 0. |
| `min_value` | `(m: map of string to int) -> int` | Minimum; empty → 0. |
| `all_values_positive` | `(m: map of string to int) -> bool` | Every value `> 0`; empty → true. |
| `any_value_negative` | `(m: map of string to int) -> bool` | Any value `< 0`. |
| `values_in_range` | `(m: map of string to int, lo: int, hi: int) -> bool` | Every value in `[lo, hi]`. |
| `update` | `(m: map of string to int, key: string, value: int) -> bool` | Replace existing only — by-value copy (limitation). |
| `filter_keys_contains` | `(m: map of string to int, sub: string) -> map of string to int` | Owned submap; key contains `sub`. |
| `filter_keys_startswith` | `(m: map of string to int, prefix: string) -> map of string to int` | Owned submap; key starts with `prefix`. |
| `filter_values_range` | `(m: map of string to int, lo: int, hi: int) -> map of string to int` | Owned submap; value in `[lo, hi]`. |
| `map_values_double` | `(m: map of string to int) -> map of string to int` | Owned map with doubled values. |
| `map_values_negate` | `(m: map of string to int) -> map of string to int` | Owned map with negated values. |
| `to_keys_list` | `(m: map of string to int) -> list of string` | Alias of `keys`. |
| `to_values_list` | `(m: map of string to int) -> list of int` | Alias of `values`. |
| `map_len_str_int` | `(m: map of string to int) -> int` | `calling m.len`; legacy alias of `size`. |
| `keys_sorted` | `(m: map of string to int) -> list of string` | Ascending keys via the `Ordered` bind. |

### `map of string to string` (`_ss`)

| Symbol | Signature | Semantics |
|---|---|---|
| `size_ss` | `(m: map of string to string) -> int` | Entry count. |
| `is_empty_ss` | `(m: map of string to string) -> bool` | Empty test. |
| `has_key_ss` | `(m: map of string to string, k: string) -> bool` | Membership. |
| `get_or_ss` | `(m: map of string to string, k: string, default: string is "") -> string` | Value or `default`. |
| `get_safe_ss` | `(m: map of string to string, k: string) -> maybe string` | `maybe`; banish it. |
| `put_ss` | `(m: map of string to string, k: string, v: string) -> void` | Insert/update — by-value copy (limitation). |
| `remove_ss` | `(m: map of string to string, k: string) -> bool` | Remove — by-value copy (limitation). |
| `clear_ss` | `(m: map of string to string) -> void` | Clear — by-value copy (limitation). |
| `keys_ss` | `(m: map of string to string) -> list of string` | Owned keys. |
| `values_ss` | `(m: map of string to string) -> list of string` | Owned values. |
| `clone_ss` | `(m: map of string to string) -> map of string to string` | Owned shallow copy. |

### `map of int to int` (`_ii`)

| Symbol | Signature | Semantics |
|---|---|---|
| `size_ii` | `(m: map of int to int) -> int` | Entry count. |
| `is_empty_ii` | `(m: map of int to int) -> bool` | Empty test. |
| `has_key_ii` | `(m: map of int to int, k: int) -> bool` | Membership. |
| `get_or_ii` | `(m: map of int to int, k: int, default: int is 0) -> int` | Value or `default`. |
| `get_safe_ii` | `(m: map of int to int, k: int) -> maybe int` | `maybe`; banish it. |
| `put_ii` | `(m: map of int to int, k: int, v: int) -> void` | Insert/update — by-value copy (limitation). |
| `remove_ii` | `(m: map of int to int, k: int) -> bool` | Remove — by-value copy (limitation). |
| `clear_ii` | `(m: map of int to int) -> void` | Clear — by-value copy (limitation). |
| `keys_ii` | `(m: map of int to int) -> list of int` | Owned keys. |
| `values_ii` | `(m: map of int to int) -> list of int` | Owned values. |
| `clone_ii` | `(m: map of int to int) -> map of int to int` | Owned shallow copy. |
| `sum_values_ii` | `(m: map of int to int) -> int` | Total; empty → 0. |
| `max_value_ii` | `(m: map of int to int) -> int` | Maximum; empty → 0. |
| `min_value_ii` | `(m: map of int to int) -> int` | Minimum; empty → 0. |

### `map of int to string` (`_is`)

| Symbol | Signature | Semantics |
|---|---|---|
| `size_is` | `(m: map of int to string) -> int` | Entry count. |
| `is_empty_is` | `(m: map of int to string) -> bool` | Empty test. |
| `has_key_is` | `(m: map of int to string, k: int) -> bool` | Membership. |
| `get_or_is` | `(m: map of int to string, k: int, default: string is "") -> string` | Value or `default`. |
| `get_safe_is` | `(m: map of int to string, k: int) -> maybe string` | `maybe`; banish it. |
| `put_is` | `(m: map of int to string, k: int, v: string) -> void` | Insert/update — by-value copy (limitation). |
| `remove_is` | `(m: map of int to string, k: int) -> bool` | Remove — by-value copy (limitation). |
| `clear_is` | `(m: map of int to string) -> void` | Clear — by-value copy (limitation). |
| `keys_is` | `(m: map of int to string) -> list of int` | Owned keys. |
| `values_is` | `(m: map of int to string) -> list of string` | Owned values. |
| `clone_is` | `(m: map of int to string) -> map of int to string` | Owned shallow copy. |

### `map of string to float` (`_sf`)

| Symbol | Signature | Semantics |
|---|---|---|
| `size_sf` | `(m: map of string to float) -> int` | Entry count. |
| `is_empty_sf` | `(m: map of string to float) -> bool` | Empty test. |
| `has_key_sf` | `(m: map of string to float, k: string) -> bool` | Membership. |
| `get_or_sf` | `(m: map of string to float, k: string, default: float is 0.0) -> float` | Value or `default`. |
| `get_safe_sf` | `(m: map of string to float, k: string) -> maybe float` | `maybe`; banish it. |
| `put_sf` | `(m: map of string to float, k: string, v: float) -> void` | Insert/update — by-value copy (limitation). |
| `remove_sf` | `(m: map of string to float, k: string) -> bool` | Remove — by-value copy (limitation). |
| `clear_sf` | `(m: map of string to float) -> void` | Clear — by-value copy (limitation). |
| `keys_sf` | `(m: map of string to float) -> list of string` | Owned keys. |
| `values_sf` | `(m: map of string to float) -> list of float` | Owned values. |
| `clone_sf` | `(m: map of string to float) -> map of string to float` | Owned shallow copy. |
| `sum_values_sf` | `(m: map of string to float) -> float` | Total; empty → 0.0. |
| `max_value_sf` | `(m: map of string to float) -> float` | Maximum; empty → 0.0. |
| `min_value_sf` | `(m: map of string to float) -> float` | Minimum; empty → 0.0. |

### `map of string to bool` (`_sb`)

| Symbol | Signature | Semantics |
|---|---|---|
| `size_sb` | `(m: map of string to bool) -> int` | Entry count. |
| `is_empty_sb` | `(m: map of string to bool) -> bool` | Empty test. |
| `has_key_sb` | `(m: map of string to bool, k: string) -> bool` | Membership. |
| `get_or_sb` | `(m: map of string to bool, k: string, default: bool is false) -> bool` | Value or `default`. |
| `get_safe_sb` | `(m: map of string to bool, k: string) -> maybe bool` | `maybe`; banish it. |
| `put_sb` | `(m: map of string to bool, k: string, v: bool) -> void` | Insert/update — by-value copy (limitation). |
| `remove_sb` | `(m: map of string to bool, k: string) -> bool` | Remove — by-value copy (limitation). |
| `clear_sb` | `(m: map of string to bool) -> void` | Clear — by-value copy (limitation). |
| `keys_sb` | `(m: map of string to bool) -> list of string` | Owned keys. |
| `values_sb` | `(m: map of string to bool) -> list of bool` | Owned values. |
| `clone_sb` | `(m: map of string to bool) -> map of string to bool` | Owned shallow copy. |
| `count_true_sb` | `(m: map of string to bool) -> int` | Entries whose value is `true`. |
| `count_false_sb` | `(m: map of string to bool) -> int` | Entries whose value is `false`. |

### Sorted wrappers using the C sorts

| Symbol | Signature | Semantics |
|---|---|---|
| `keys_sorted_ss` | `(m: map of string to string) -> list of string` | Owned ascending keys (`_atlas_sort_strings_in_place`). |
| `values_sorted_ss` | `(m: map of string to string) -> list of string` | Owned ascending values (C string sort). |
| `keys_sorted_ii` | `(m: map of int to int) -> list of int` | Owned ascending keys (`_atlas_sort_i32_in_place`). |
| `values_sorted_ii` | `(m: map of int to int) -> list of int` | Owned ascending values (C `int32_t` sort). |
| `keys_sorted_is` | `(m: map of int to string) -> list of int` | Owned ascending keys (C `int32_t` sort). |
| `values_sorted_is` | `(m: map of int to string) -> list of string` | Owned ascending values (C string sort). |
| `keys_sorted_sf` | `(m: map of string to float) -> list of string` | Owned ascending keys (C string sort). |
| `values_sorted_sf` | `(m: map of string to float) -> list of float` | Owned ascending values (C 32-bit float sort); new in 2.1.0. |
| `keys_sorted_sb` | `(m: map of string to bool) -> list of string` | Owned ascending keys; forwards to the generic `m.keys_sorted` (no C sort). |

### Merges and list constructors

| Symbol | Signature | Semantics |
|---|---|---|
| `merge` | `(a: map of string to int, b: map of string to int) -> map of string to int` | Owned union; `b` wins. |
| `merge_keep_left` | `(a: map of string to int, b: map of string to int) -> map of string to int` | Owned union; `a` wins. |
| `merge_keep_right` | `(a: map of string to int, b: map of string to int) -> map of string to int` | Owned union; `b` wins (alias of `merge`). |
| `from_lists` | `(ks: list of string, vs: list of int) -> map of string to int` | Owned map of `min(len)` pairs. |
| `merge_ss` | `(a: map of string to string, b: map of string to string) -> map of string to string` | Owned union; `b` wins. |
| `merge_keep_left_ss` | `(a: map of string to string, b: map of string to string) -> map of string to string` | Owned union; `a` wins. |
| `merge_keep_right_ss` | `(a: map of string to string, b: map of string to string) -> map of string to string` | Owned union; `b` wins. |
| `from_lists_ss` | `(ks: list of string, vs: list of string) -> map of string to string` | Owned map of `min(len)` pairs. |
| `merge_sf` | `(a: map of string to float, b: map of string to float) -> map of string to float` | Owned union; `b` wins. |
| `merge_keep_left_sf` | `(a: map of string to float, b: map of string to float) -> map of string to float` | Owned union; `a` wins. |
| `merge_keep_right_sf` | `(a: map of string to float, b: map of string to float) -> map of string to float` | Owned union; `b` wins. |
| `from_lists_sf` | `(ks: list of string, vs: list of float) -> map of string to float` | Owned map of `min(len)` pairs. |
| `merge_ii` | `(a: map of int to int, b: map of int to int) -> map of int to int` | Owned union; `b` wins. |
| `merge_keep_left_ii` | `(a: map of int to int, b: map of int to int) -> map of int to int` | Owned union; `a` wins. |
| `merge_keep_right_ii` | `(a: map of int to int, b: map of int to int) -> map of int to int` | Owned union; `b` wins. |
| `from_lists_ii` | `(ks: list of int, vs: list of int) -> map of int to int` | Owned map of `min(len)` pairs. |
| `merge_is` | `(a: map of int to string, b: map of int to string) -> map of int to string` | Owned union; `b` wins. |
| `merge_keep_left_is` | `(a: map of int to string, b: map of int to string) -> map of int to string` | Owned union; `a` wins. |
| `merge_keep_right_is` | `(a: map of int to string, b: map of int to string) -> map of int to string` | Owned union; `b` wins. |
| `from_lists_is` | `(ks: list of int, vs: list of string) -> map of int to string` | Owned map of `min(len)` pairs. |
| `merge_sb` | `(a: map of string to bool, b: map of string to bool) -> map of string to bool` | Owned union; `b` wins. |
| `merge_keep_left_sb` | `(a: map of string to bool, b: map of string to bool) -> map of string to bool` | Owned union; `a` wins. |
| `merge_keep_right_sb` | `(a: map of string to bool, b: map of string to bool) -> map of string to bool` | Owned union; `b` wins. |
| `from_lists_sb` | `(ks: list of string, vs: list of bool) -> map of string to bool` | Owned map of `min(len)` pairs. |

## What was removed

* `enchanting map of int to int:` is **gone**. It held only `keys_sorted` and
  `values_sorted`; both are fully covered by the generic `K: Ordered` /
  `V: Ordered` blocks, which also work for `string` keys and values.
* The concrete `keys_sorted` / `values_sorted` **methods** were deleted with
  that block. The concrete `keys_sorted` / `keys_sorted_*` / `values_sorted_*`
  **module wrappers** remain (see above), and `values_sorted_sf` is new.
* `keys_sorted_of` / `values_sorted_of` changed bound from `K: Ordo` /
  `V: Ordo` to `K: Ordered` / `V: Ordered`, so they now accept `string` too.

No public symbol was removed: the 0.15.0 name set is a subset of the 2.1.0 name
set. The only additions are `cmp` (the concept method), the bound types,
`map_filter_values_contains` and `values_sorted_sf`.

## C bridges (`antiquus`, internal)

Six `antiquus` bridges back the `_sorted_*` wrappers. The generic insertion
sort is O(n²); these use `qsort` over the `PenguList` buffer instead.

| Symbol | Signature | Semantics |
|---|---|---|
| `_atlas_cmp_i32` | `(a: ref to frozen void, b: ref to frozen void) -> int` | `(x > y) - (x < y)` over two `int32_t` cells. |
| `_atlas_sort_i32_in_place` | `(xs: list of int) -> void` | `qsort(xs.data, xs.len, sizeof(int32_t), _atlas_cmp_i32)`. |
| `_atlas_cmp_f32` | `(a: ref to frozen void, b: ref to frozen void) -> int` | `(x > y) - (x < y)` over two `const float*` cells (`float` is 32-bit). |
| `_atlas_sort_f32_in_place` | `(xs: list of float) -> void` | `qsort(…, sizeof(float), _atlas_cmp_f32)`. |
| `_atlas_cmp_string` | `(a: ref to frozen void, b: ref to frozen void) -> int` | `memcmp` over the common prefix, `len` as tie-breaker; reads `PenguString.data`/`.len`. |
| `_atlas_sort_strings_in_place` | `(xs: list of string) -> void` | `qsort(…, sizeof(PenguString), _atlas_cmp_string)`; cells are moved, not copied. |

**`## ## Motivo`.** `qsort` replaces the O(n²) Pengu sort: one C implementation
per element type is faster and reuses the same comparator. `_atlas_cmp_i32`,
`_atlas_cmp_f32` and `_atlas_cmp_string` carry `@export` (`atlas__atlas_cmp_i32`
etc.) because dead-code elimination prunes weaves that only raw C references;
the three `..._in_place` sorts are called from Pengu and need no attribute.

**`## ## Memoria`.** All six are `antiquus` over borrowed memory: they read the
two comparator cells, or sort the caller's list buffer in place. They allocate
nothing and free nothing; the `PenguString` cells are moved, so no string is
duplicated or freed. A `list of T` `antiquus` parameter arrives **by value** as
a `PenguList` struct, so the body uses `xs.data` and `xs.len` (no `->`).

## Known limitation (tracked debt)

A `map` **parameter** is passed by value as a `PenguMap` struct copy, so no
module-level mutator can change the caller's map: the copy shares the entry
buffer but the caller's `len` is never updated, and `clear_*` leaves
`size_*`/`is_empty_*` reading the old length. Affected:
`map_put`, `map_remove`, `map_clear`, `put`, `put_ii`/`put_is`/`put_sb`/`put_sf`/`put_ss`,
`remove`, `remove_ii`/`remove_is`/`remove_sb`/`remove_sf`/`remove_ss`,
`clear`, `clear_ii`/`clear_is`/`clear_sb`/`clear_sf`/`clear_ss`, and `update`.

Use the **method** form: `self` is a `ref to` the receiver, so
`calling m.put`, `calling m.remove`, `calling m.clear`, `calling m.update`,
`calling m.rename_key` and `calling m.remove_all` do mutate in place. This is
also why `rename_key` exists only as a method (there is no module-level
`rename_key`): its sole form is the safe one.

The signatures are **frozen as they are**; do not change them. Migrating the
wrappers to `ref to map of …` would force every call site to write
`sigil of m`, so it is deliberately out of scope and left as debt for a
dedicated chunk.

## Compatibility and migration

`2.1.0` is additive: every 0.15.0 name, concrete signature and observable
result is preserved. The generic methods and module functions are new surface;
the old wrappers are thin forwarders over them. `map of string to int` remains
the canonical compatibility map and keeps the extra names `map_len_str_int`,
`to_keys_list` and `to_values_list` that the other families do not have.

| Before (0.15.0) | Now (`2.1.0`) |
|---|---|
| `calling atlas.size_ss with m` | `calling m.size` (or keep `size_ss`) |
| `calling atlas.get_or_ii with m, k, 0` | `calling m.get_or with k, 0` |
| `calling atlas.merge_ss with a, b` | `calling map_merge with a, b` |
| `calling atlas.from_lists_sf with ks, vs` | `calling map_from_lists with ks, vs` |
| `calling atlas.keys_sorted_ii with m` | `calling m.keys_sorted` (generic, `K: Ordered`) |
| `calling m.to_keys_list` | `calling m.keys` |
| `calling atlas.put with m, k, v` (silently ineffective) | `calling m.put with k, v` |
| generic sorters bound `K: Ordo` | `K: Ordered` (also works for `string`) |
| (new) | `m.entries`, `m.invert`, `m.take_keys`, `m.filter_entries`, `m.map_values_with`, `m.count_where`, `m.clone`, `m.is_equal` |
| (new) | `atlas.from_pairs`, `atlas.map_merge_all`, `atlas.map_filter_values_contains` |

## Private helpers (internal)

Not part of the frozen surface; do not call them. The test harness uses
`std.spark` directly because importing `std.ward` would create the cycle
`ward -> atlas` (`E0004`).

| Symbol | Signature | Role |
|---|---|---|
| `_sort_strings` | `(xs: list of string) -> list of string` | Copies `xs` and sorts it through `_atlas_sort_strings_in_place`. |
| `_one shard K and V where K: Par, V: Par` | `(k: K, v: V) -> map of K to V` | One-entry map for the tests. |
| `_count shard T` | `(xs: list of T) -> int` | List length for the tests. |
| `_value_gt_one` | `(k: string, v: int) -> bool` | Test predicate `v > 1`. |
| `_inc` | `(x: int) -> int` | Test callback `x + 1`. |
| `_expect_eq_int` | `(got: int, want: int, label: string) -> void` | Panics via `spark.panic` when `got != want`. |
| `_expect_eq_string` | `(got: string, want: string, label: string) -> void` | Equality assertion using `std.scrolls.compare`. |
| `_expect_true` | `(cond: bool, label: string) -> void` | Panics when `cond` is false. |
| `_sample_str_int` | `() -> map of string to int` | Test fixture. |
| `_sample_str_str` | `() -> map of string to string` | Test fixture. |
| `_sample_str_float` | `() -> map of string to float` | Test fixture. |
| `_sample_str_bool` | `() -> map of string to bool` | Test fixture. |
| `_sample_int_int` | `() -> map of int to int` | Test fixture. |
| `_sample_int_str` | `() -> map of int to string` | Test fixture. |

The six `_atlas_*` C bridges of the previous section are the remaining private
declarations (20 private declarations in total). The in-file `test` blocks
(153 of them) are not exported and are not part of this contract; the custom-key
extension is exercised by `tests/stdlib/test_atlas.py`, which declares its own
`seal UserId as int` and unqualified `bind UserId with Ordered:` — `atlas`
exports **no** test-only type.
