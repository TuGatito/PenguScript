# std.atlas

> Source: `std/atlas.pengu`

std/atlas.pengu — maps (`map of K to V`): access, query, mutation, reduction,
filtering and transformation, with a **generic** API (`K: Par`, `V: Par`,
`V: Num`, `K: Ordered`, `V: Ordered`) and 100% compatibility with the concrete
`map of string to int` API of 0.15.0.

One `enchanting map of shard K to shard V where K: Par, V: Par` covers every
hashable combination, a second one (`V: Num and V: Ordo`) adds the arithmetic
and two more (`K: Ordered` / `V: Ordered`) give a deterministic order through
the `Ordered` concept. Only the `string`-keyed filters need concrete blocks
(the compiler cannot infer `K` for a method returning `map of K to string`).

## Example
```pengu
import std.atlas
import std.spark

weave main into int:
    var m as map of string to int is map of string to int
    with m:
        calling .put with "apple", 10
        calling .put with "apricot", 30
    calling spark.println with "{calling m.size}"
    var ap as map of string to int is calling m.filter_keys_startswith with "ap"
    calling spark.println with "{calling ap.size}"
    var ks as list of string is calling m.keys_sorted
    return 0
```

## Memory
- The mutators (`update`, `rename_key`, `remove`, `clear`, `put_all`, ...)
  change the map **in place**; the methods that return `list`/`map` build new
  containers the caller releases with `banish`. The receiver is never consumed.
- `keys`, `values` and `entries` walk the internal hash order; use
  `keys_sorted`/`values_sorted` when a deterministic order matters.

## Design notes
- **Generic core and compatibility aliases.** Every public 0.15.0 name still
  exists as a one-line *forwarder* over the equivalent generic method.
- **`insignia atlas_`** keeps the `remove` wrapper from colliding with the C
  `remove` symbol of `stdio.h`, without renaming any Pengu symbol.
- **`concept Ordered`.** The concept adds a `cmp with other as T into int`
  method to the primitives bound below (`int`, `i32`, `i64`, `float`, `f32`,
  `f64`, `string`). A user type extends the order with an **unqualified**
  `bind <Type> with Ordered:` (import atlas first) plus the `cmp` body. A
  `seal`/`rune` key needs that bind; an `alias` unwraps to its base type and
  needs **no** extra bind — the base type's bind already covers it. The
  recipe is exercised by the external suite `tests/stdlib/test_atlas.py`,
  which declares its own `seal UserId as int` and an unqualified
  `bind UserId with Ordered:`; this module exports **no** test-only type.
- **Two `bind` restrictions.** The target of a `bind` cannot be `_`-private
  (`seal _X` + `bind _X` fails with `E0004 Undefined type ''`), and the
  concept cannot be named qualified: after `import std.atlas` the recipe is
  `bind UserId with Ordered:`, while `bind UserId with atlas.Ordered:` is
  `E0004`. User types are therefore bound unqualified.
- **Compiler limitation on `bind`.** `bind <T> with Ordered:` only accepts the
  type names the compiler registers as primitives. `i8`, `i16`, `u8`, `u16`,
  `u32`, `u64`, `usize`, `isize`, `char` and `double` are rejected with
  `E0004 Undefined type '<name>' in bind declaration`, so `keys_sorted` /
  `values_sorted` are not available for those key/value types. There is
  deliberately no per-type concrete block for them: generalising is the
  contract, and duplicating the sort for each primitive was rejected.
- **`count_true`/`count_false` and the second shard parameter.** The boolean
  block reads `map of shard K to bool shard K and V where K: Par, V: Par`. A
  map carries two type arguments and the compiler only resolves a generic
  method when the number of shard parameters matches them; with a single shard
  parameter every call fails with `E0005 Could not infer type parameter(s) K`.
  The second parameter does not occur in the receiver type: it only lets the
  compiler bind the two type arguments of the map.
- **Why the `string` filters stay concrete.** `map of shard K to string`
  cannot infer `K` for a method returning `map of K to string` (measured), so
  `filter_keys_contains`, `filter_keys_startswith` and
  `filter_values_contains` live in concrete `map of string to *` blocks. The
  generic module function `map_filter_values_contains` does infer `K` from its
  argument and is the portable alternative.
- **C sorts (`antiquus`).** `keys_sorted_ii`, `values_sorted_ii`,
  `keys_sorted_is`, `keys_sorted_ss`, `values_sorted_ss`, `values_sorted_is`,
  `keys_sorted_sf`, `values_sorted_sf` and the private `_sort_strings` build
  the list and sort it with `qsort` through one `antiquus` comparator per
  element type (`int32_t`, `float`, `PenguString`).
- **Private test harness.** The `test` blocks use `_expect_eq_int`,
  `_expect_eq_string` and `_expect_true` over `std.spark` (never
  `std.ward`: ward imports atlas and the cycle would be `E0004`).
- **Known defect: module-level mutators receive the map by value.** The
  compiler passes a `map` **parameter** as a C struct copy, so the void
  compatibility wrappers (`put`, `put_*`, `remove`, `remove_*`, `clear`,
  `clear_*`, `update` and the generic `map_put`/`map_remove`/`map_clear`)
  cannot change the caller's map: the copy shares the entry buffer but the
  caller's `len` is never updated and `clear_*` leaves `size_*`/`is_empty_*`
  reading the old length. Use the **method** form instead (`calling m.put`,
  `calling m.remove`, `calling m.clear`, `calling m.update`,
  `calling m.rename_key`, `calling m.remove_all`, ...), whose `self` is a
  `ref to` the receiver and which therefore mutates in place. A future chunk
  can migrate the wrappers to `ref to map of ...` (that would force callers to
  write `sigil of m`, so it is deliberately out of scope here).
- **No test-only type in the public surface.** The custom-key extension
  (`seal`/`rune`/`alias` plus an unqualified `bind <Type> with Ordered:`) is
  covered by the external suite `tests/stdlib/test_atlas.py`. The internal
  `test` blocks keep to the bound primitives so that no fixture type is
  exported by the module.

## Migration
| Before (0.15.0) | Now |
|---|---|
| `calling atlas.size_ss with m` | `calling m.size` |
| `calling atlas.get_or_ii with m, k, 0` | `calling m.get_or with k, 0` |
| `calling atlas.merge_ss with a, b` | `calling map_merge with a, b` |
| `calling atlas.from_lists_sf with ks, vs` | `calling map_from_lists with ks, vs` |
| `calling m.to_keys_list` | `calling m.keys` |
| — | `calling m.entries`, `m.invert`, `m.take_keys` (new) |
| — | `calling m.filter_entries`, `m.map_values_with`, `m.count_where` (new) |
| — | `calling atlas.from_pairs`, `atlas.merge_all` (new) |
| generic sorters bound `K: Ordo` | `K: Ordered` (also works for `string`) |

---

### `Ordered`

> concept Ordered

 Total order over a type: the concept that backs `keys_sorted`/`values_sorted`.

 ## Design notes
 A `bind` adds a `cmp` method to the bound type; `keys_sorted`/`values_sorted`
 call `calling left.cmp with key`. After `import std.atlas`, extend the order
 of a user type with an **unqualified** `bind MyKey with Ordered:` plus a `cmp`
 body (the qualified `atlas.Ordered` is `E0004`, and a `_`-private target is
 also `E0004`). An `alias` needs no bind: it unwraps to its base type, whose
 bind applies.

### `cmp`

> **cmp**(other: int) -> int

_Undocumented._

### `ATLAS_VERSION`

> **ATLAS_VERSION** : string

 Version of the `std.atlas` module.

 ## Parámetros
 - None.

 ## Retorno
 The literal `"2.14.0"` as a `string`.

 ## Ejemplo
 ```pengu
 calling spark.println with ATLAS_VERSION    # 2.1.0
 ```

### `size`

> **size**() -> int

 Number of entries in the receiver.

 ## Parámetros
 - None: the receiver is the map to measure.

 ## Retorno
 The number of entries as an `int`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var m as map of string to int is map of string to int
 calling m.put with "a", 1
 calling m.size    # 1
 ```

### `is_empty`

> **is_empty**() -> bool

 `true` when the receiver has no entries.

 ## Parámetros
 - None: the receiver is the map to inspect.

 ## Retorno
 `true` when `size` is `0`; `false` otherwise. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var m as map of string to int is map of string to int
 calling m.is_empty    # true
 ```

### `has_key`

> **has_key**(key: K) -> bool

 `true` when `key` is present in the receiver.

 ## Parámetros
 - `key`: the key to look up. Borrowed.

 ## Retorno
 `true` when the map holds `key`; `false` otherwise. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.has_key with "beta"    # true
 ```

### `has_any_key`

> **has_any_key**(keys: list of K) -> bool

 `true` when at least one key of `keys` is present.

 ## Parámetros
 - `keys`: the candidate keys to test. Read only.

 ## Retorno
 `true` on the first match; `false` for an empty list or no match. Borrows both arguments.

 ## Ejemplo
 ```pengu
 var ks as list of string is ["zeta", "beta"]
 calling m.has_any_key with ks    # true
 ```

### `has_all_keys`

> **has_all_keys**(keys: list of K) -> bool

 `true` when every key of `keys` is present.

 ## Parámetros
 - `keys`: the keys that must all be present. Read only.

 ## Retorno
 `true` for an empty list and when every key is present; `false` on the first missing key. Borrows both arguments.

 ## Ejemplo
 ```pengu
 var ks as list of string is ["alpha", "gamma"]
 calling m.has_all_keys with ks    # true
 ```

### `get_or`

> **get_or**(key: K, fallback: V) -> V

 Value stored under `key`, or `fallback` when the key is absent.

 ## Parámetros
 - `key`: the key to look up. Borrowed.
 - `fallback`: the value returned when `key` is missing.

 ## Retorno
 The stored value or `fallback`, by value. Borrows the receiver and both parameters.

 ## Ejemplo
 ```pengu
 calling m.get_or with "beta", 0    # 2
 calling m.get_or with "zeta", -1    # -1
 ```

### `get_safe`

> **get_safe**(key: K) -> maybe V

 `some v` when `key` is present, `maybe none` otherwise.

 ## Parámetros
 - `key`: the key to look up. Borrowed.

 ## Retorno
 A `maybe V` wrapping the stored value, or `maybe none`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var got as maybe int is calling m.get_safe with "beta"
 ```

### `find_key_by_value`

> **find_key_by_value**(target: V) -> maybe K

 First key whose value equals `target`.

 ## Parámetros
 - `target`: the value to search for.

 ## Retorno
 `some k` for the first matching key in internal hash order, or `maybe none`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var got as maybe string is calling m.find_key_by_value with 2
 ```

### `update`

> **update**(key: K, value: V) -> bool

 Replaces the value of an existing key; never inserts.

 ## Parámetros
 - `key`: the key to update. Borrowed.
 - `value`: the new value.

 ## Retorno
 `true` when `key` existed and was updated; `false` when it was not inserted. Mutates the receiver in place.

 ## Ejemplo
 ```pengu
 calling m.update with "beta", 9    # true
 ```

### `rename_key`

> **rename_key**(old_key: K, new_key: K) -> bool

 Renames `old_key` to `new_key`, keeping the value.

 ## Parámetros
 - `old_key`: the key to move. Borrowed.
 - `new_key`: the destination key. Borrowed.

 ## Retorno
 `true` when `old_key` existed; `false` when it did not. A collision overwrites the destination and the old key is removed. Mutates the receiver in place.

 ## Ejemplo
 ```pengu
 calling m.rename_key with "alpha", "omega"    # true
 ```

### `remove`

> **remove**(key: K) -> bool

 Removes `key` when it is present.

 ## Parámetros
 - `key`: the key to remove. Borrowed.

 ## Retorno
 `true` when the key existed and was removed; `false` otherwise. Mutates the receiver in place.

 ## Ejemplo
 ```pengu
 calling m.remove with "beta"    # true
 ```

### `clear`

> **clear**() -> void

 Removes every entry from the receiver.

 ## Parámetros
 - None: the receiver is the map to empty.

 ## Retorno
 Nothing; the map is left empty in place.

 ## Ejemplo
 ```pengu
 calling m.clear
 calling m.is_empty    # true
 ```

### `remove_all`

> **remove_all**(keys: list of K) -> int

 Removes every key of `keys` that is present.

 ## Parámetros
 - `keys`: the keys to remove. Read only.

 ## Retorno
 The number of entries actually removed as an `int`. Mutates the receiver in place.

 ## Ejemplo
 ```pengu
 var ks as list of string is ["alpha", "zeta"]
 calling m.remove_all with ks    # 1
 ```

### `put_all`

> **put_all**(other: map of K to V) -> void

 Copies every entry of `other` into the receiver.

 ## Parámetros
 - `other`: the map to copy from. Read only.

 ## Retorno
 Nothing; existing keys are overwritten and new keys are inserted in place. Borrows `other`.

 ## Ejemplo
 ```pengu
 calling m.put_all with other
 ```

### `keys`

> **keys**() -> list of K

 New list with all keys, in internal hash order.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 An owned `list of K` the caller releases with `banish`. The order is the internal hash order, not sorted.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling m.keys
 ```

### `values`

> **values**() -> list of V

 New list with all values, in internal hash order.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 An owned `list of V` the caller releases with `banish`. The order is the internal hash order, not sorted.

 ## Ejemplo
 ```pengu
 var vs as list of int is calling m.values
 ```

### `clone`

> **clone**() -> map of K to V

 Independent shallow copy of the receiver.

 ## Parámetros
 - None: the receiver is the map to copy.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Keys and values are copied by value; owned values are shared, not deep-copied.

 ## Ejemplo
 ```pengu
 var c as map of string to int is calling m.clone
 ```

### `copy`

> **copy**() -> map of K to V

 Alias of `clone`.

 ## Parámetros
 - None: the receiver is the map to copy.

 ## Retorno
 The same owned copy as `calling self.clone`.

 ## Ejemplo
 ```pengu
 var c as map of string to int is calling m.copy
 ```

### `is_equal`

> **is_equal**(other: map of K to V) -> bool

 Structural key/value equality.

 ## Parámetros
 - `other`: the map to compare against. Read only.

 ## Retorno
 `true` when both maps have the same size and the same value for every key; `false` otherwise. Borrows both maps.

 ## Ejemplo
 ```pengu
 calling m.is_equal with other    # true
 ```

### `to_keys_list`

> **to_keys_list**() -> list of K

 Alias of `keys`.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 The same owned `list of K` as `calling self.keys`.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling m.to_keys_list
 ```

### `to_values_list`

> **to_values_list**() -> list of V

 Alias of `values`.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 The same owned `list of V` as `calling self.values`.

 ## Ejemplo
 ```pengu
 var vs as list of int is calling m.to_values_list
 ```

### `entries`

> **entries**() -> list of Pair__K__V

 New list of `oracle.Pair` key/value entries.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 An owned `list of oracle.Pair of K and V` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var es as list of oracle.Pair of string and int is calling m.entries
 ```

### `invert`

> **invert**() -> map of V to K

 Swaps keys and values.

 ## Parámetros
 - None: the receiver is the map to invert.

 ## Retorno
 An owned `map of V to K`. When several keys share a value the last one visited in internal hash order wins. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var inv as map of int to string is calling m.invert
 ```

### `take_keys`

> **take_keys**(ks: list of K) -> map of K to V

 Submap holding only the requested keys.

 ## Parámetros
 - `ks`: the keys to keep. Read only.

 ## Retorno
 An owned `map of K to V` with the keys of `ks` that exist in the receiver; missing keys are skipped. Borrows both arguments.

 ## Ejemplo
 ```pengu
 var ks as list of string is ["alpha"]
 var sub as map of string to int is calling m.take_keys with ks
 ```

### `count_where`

> **count_where**(predicate: weave with k: K, v: V into bool) -> int

 Counts the entries accepted by `predicate`.

 ## Parámetros
 - `predicate`: `weave with k as K, v as V into bool`. Called once per entry.

 ## Retorno
 The number of entries for which `predicate` returned `true`, as an `int`. Borrows the receiver; the predicate must not consume it.

 ## Ejemplo
 ```pengu
 calling m.count_where with _value_gt_one    # 2
 ```

### `filter_entries`

> **filter_entries**(predicate: weave with k: K, v: V into bool) -> map of K to V

 Submap with the entries accepted by `predicate`.

 ## Parámetros
 - `predicate`: `weave with k as K, v as V into bool`. Called once per entry.

 ## Retorno
 An owned `map of K to V` with the accepted entries. Borrows the receiver and the predicate.

 ## Ejemplo
 ```pengu
 var sub as map of string to int is calling m.filter_entries with _value_gt_one
 ```

### `map_values_with`

> **map_values_with**(f: weave with x: V into V) -> map of K to V

 New map with `f` applied to every value.

 ## Parámetros
 - `f`: `weave with x as V into V`. Called once per value.

 ## Retorno
 An owned `map of K to V` with the same keys and the transformed values. Borrows the receiver; the returned map is owned by the caller.

 ## Ejemplo
 ```pengu
 var out as map of string to int is calling m.map_values_with with _inc
 ```

### `merge_all`

> **merge_all**(others: list of map of K to V) -> map of K to V

 Receiver merged with each map of `others`.

 ## Parámetros
 - `others`: the maps to merge in order. Read only.

 ## Retorno
 An owned `map of K to V`; later maps win on collision. Borrows the receiver and `others`.

 ## Ejemplo
 ```pengu
 var merged as map of string to int is calling m.merge_all with others
 ```

### `sum_values`

> **sum_values**() -> V

 Sum of all values; `donum V` (zero) for an empty map.

 ## Parámetros
 - None: the receiver is the map to reduce.

 ## Retorno
 The total as `V`; `donum V` (`0`) when the map is empty. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.sum_values    # 6
 ```

### `sum_values_filtered`

> **sum_values_filtered**(lo: V, hi: V) -> V

 Sum of the values inside `[lo, hi]` inclusive.

 ## Parámetros
 - `lo`: lower bound of the accepted range, inclusive.
 - `hi`: upper bound of the accepted range, inclusive.

 ## Retorno
 The total as `V`, or `donum V` when no value falls in the range. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.sum_values_filtered with 2, 3    # 5
 ```

### `all_values_positive`

> **all_values_positive**() -> bool

 `true` when every value is greater than zero.

 ## Parámetros
 - None: the receiver is the map to scan.

 ## Retorno
 `true` for an empty map and when no value is `<= 0`; `false` otherwise. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.all_values_positive    # true
 ```

### `any_value_negative`

> **any_value_negative**() -> bool

 `true` when at least one value is negative.

 ## Parámetros
 - None: the receiver is the map to scan.

 ## Retorno
 `true` on the first negative value; `false` for an empty map. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.any_value_negative    # false
 ```

### `count_if_value_positive`

> **count_if_value_positive**() -> int

 Counts the values greater than zero.

 ## Parámetros
 - None: the receiver is the map to scan.

 ## Retorno
 The number of positive values as an `int`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.count_if_value_positive    # 3
 ```

### `count_if_value_negative`

> **count_if_value_negative**() -> int

 Counts the values smaller than zero.

 ## Parámetros
 - None: the receiver is the map to scan.

 ## Retorno
 The number of negative values as an `int`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.count_if_value_negative    # 1
 ```

### `map_values_double`

> **map_values_double**() -> map of K to V

 New map with every value doubled (`v + v`).

 ## Parámetros
 - None: the receiver is the map to transform.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var out as map of string to int is calling m.map_values_double
 ```

### `map_values_negate`

> **map_values_negate**() -> map of K to V

 New map with every value negated (`-v`).

 ## Parámetros
 - None: the receiver is the map to transform.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var out as map of string to int is calling m.map_values_negate
 ```

### `map_values_scale`

> **map_values_scale**(factor: V) -> map of K to V

 New map with every value multiplied by `factor`.

 ## Parámetros
 - `factor`: the multiplier applied to every value.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var out as map of string to float is calling m.map_values_scale with 2.0
 ```

### `max_value`

> **max_value**() -> V

 Largest value; `donum V` (zero) for an empty map.

 ## Parámetros
 - None: the receiver is the map to reduce.

 ## Retorno
 The maximum as `V`, or `donum V` when the map is empty. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.max_value    # 3
 ```

### `min_value`

> **min_value**() -> V

 Smallest value; `donum V` (zero) for an empty map.

 ## Parámetros
 - None: the receiver is the map to reduce.

 ## Retorno
 The minimum as `V`, or `donum V` when the map is empty. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.min_value    # 1
 ```

### `values_in_range`

> **values_in_range**(lo: V, hi: V) -> bool

 `true` when every value lies inside `[lo, hi]`.

 ## Parámetros
 - `lo`: lower bound, inclusive.
 - `hi`: upper bound, inclusive.

 ## Retorno
 `true` for an empty map and when no value is out of range; `false` otherwise. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.values_in_range with 1, 3    # true
 ```

### `filter_values_range`

> **filter_values_range**(lo: V, hi: V) -> map of K to V

 Submap with the values inside `[lo, hi]` inclusive.

 ## Parámetros
 - `lo`: lower bound, inclusive.
 - `hi`: upper bound, inclusive.

 ## Retorno
 An owned `map of K to V` with the entries in range. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var sub as map of string to int is calling m.filter_values_range with 2, 3
 ```

### `keys_sorted`

> **keys_sorted**() -> list of K

 New list with the keys sorted ascending through `calling K.cmp`.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 An owned `list of K` sorted ascending with the `Ordered` bind of `K`. Works for any `K` that implements `Ordered` (`int`, `float`, `string`, a bound `seal`/`rune`, ...). Borrows the receiver.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling m.keys_sorted
 calling ks at 0    # "alpha"
 ```

### `values_sorted`

> **values_sorted**() -> list of V

 New list with the values sorted ascending through `calling V.cmp`.

 ## Parámetros
 - None: the receiver is the map to read.

 ## Retorno
 An owned `list of V` sorted ascending with the `Ordered` bind of `V`. Works for `int`, `float`, `string` and bound `seal`/`rune` values. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var vs as list of string is calling m.values_sorted
 calling vs at 0    # "dos"
 ```

### `count_true`

> **count_true**() -> int

 Counts the entries whose value is `true`.

 ## Parámetros
 - None: the receiver is the `map of K to bool` to count.

 ## Retorno
 The number of `true` values as an `int`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 var m as map of int to bool is map of int to bool
 calling m.put with 1, true
 calling m.count_true    # 1
 ```

### `count_false`

> **count_false**() -> int

 Counts the entries whose value is `false`.

 ## Parámetros
 - None: the receiver is the `map of K to bool` to count.

 ## Retorno
 The number of `false` values as an `int`. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.count_false    # 1
 ```

### `filter_keys_contains`

> **filter_keys_contains**(sub: string) -> map of string to int

 Submap with the entries whose key contains `sub`.

 ## Parámetros
 - `sub`: the substring to look for inside each key.

 ## Retorno
 An owned `map of string to int` with the matching entries. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.filter_keys_contains with "a"
 ```

### `filter_keys_startswith`

> **filter_keys_startswith**(prefix: string) -> map of string to int

 Submap with the entries whose key starts with `prefix`.

 ## Parámetros
 - `prefix`: the prefix each key must start with.

 ## Retorno
 An owned `map of string to int` with the matching entries. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.filter_keys_startswith with "be"
 ```

### `filter_values_contains`

> **filter_values_contains**(sub: string) -> map of string to string

 Submap with the entries whose value contains `sub`.

 ## Parámetros
 - `sub`: the substring to look for inside each value.

 ## Retorno
 An owned `map of string to string` with the matching entries. Borrows the receiver.

 ## Ejemplo
 ```pengu
 calling m.filter_values_contains with "do"
 ```

### `map_size`

> **map_size**(m: map of K to V) -> int

 Number of entries of the generic map `m`.

 ## Parámetros
 - `m`: the map to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling map_size with m    # 3
 ```

### `map_is_empty`

> **map_is_empty**(m: map of K to V) -> bool

 `true` when the generic map `m` has no entries.

 ## Parámetros
 - `m`: the map to inspect. Read only.

 ## Retorno
 `true` when the map is empty; `false` otherwise. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling map_is_empty with m    # false
 ```

### `map_has_key`

> **map_has_key**(m: map of K to V, key: K) -> bool

 `true` when `key` exists in the generic map `m`.

 ## Parámetros
 - `m`: the map to query. Read only.
 - `key`: the key to look up. Borrowed.

 ## Retorno
 `true` when `key` is present; `false` otherwise. Borrows both arguments.

 ## Ejemplo
 ```pengu
 calling map_has_key with m, "beta"    # true
 ```

### `map_get_or`

> **map_get_or**(m: map of K to V, key: K, fallback: V) -> V

 Value of `key` in `m`, or `fallback` when the key is absent.

 ## Parámetros
 - `m`: the map to query. Read only.
 - `key`: the key to look up. Borrowed.
 - `fallback`: the value returned when `key` is missing.

 ## Retorno
 The stored value or `fallback`, by value. Borrows the map.

 ## Ejemplo
 ```pengu
 calling map_get_or with m, "zeta", -1    # -1
 ```

### `map_keys`

> **map_keys**(m: map of K to V) -> list of K

 New list with all keys of the generic map `m`.

 ## Parámetros
 - `m`: the map to read. Read only.

 ## Retorno
 An owned `list of K` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling map_keys with m
 ```

### `map_values`

> **map_values**(m: map of K to V) -> list of V

 New list with all values of the generic map `m`.

 ## Parámetros
 - `m`: the map to read. Read only.

 ## Retorno
 An owned `list of V` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var vs as list of int is calling map_values with m
 ```

### `map_put`

> **map_put**(m: map of K to V, key: K, value: V) -> void

 Inserts or updates `key -> value` in the generic map `m`.

 ## Parámetros
 - `m`: the map to mutate in place.
 - `key`: the key to insert or update. Borrowed.
 - `value`: the value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling map_put with m, "a", 4
 ```

### `map_remove`

> **map_remove**(m: map of K to V, key: K) -> bool

 Removes `key` from the generic map `m`.

 ## Parámetros
 - `m`: the map to mutate in place.
 - `key`: the key to remove. Borrowed.

 ## Retorno
 `true` when `key` existed and was removed; `false` otherwise. Mutates `m` in place.

 ## Ejemplo
 ```pengu
 calling map_remove with m, "a"    # true
 ```

### `map_clear`

> **map_clear**(m: map of K to V) -> void

 Removes every entry from the generic map `m`.

 ## Parámetros
 - `m`: the map to empty in place.

 ## Retorno
 Nothing; `m` is left empty in place.

 ## Ejemplo
 ```pengu
 calling map_clear with m
 ```

### `keys_sorted_of`

> **keys_sorted_of**(m: map of K to V) -> list of K

 New list with the keys of `m` sorted ascending.

 ## Parámetros
 - `m`: the map to read. Read only.

 ## Retorno
 An owned `list of K` sorted with the `Ordered` bind of `K`; unlike the 0.15.0 version it also works when `K` is `string`. Borrows `m`.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling keys_sorted_of with m
 calling ks at 0    # "alpha"
 ```

### `values_sorted_of`

> **values_sorted_of**(m: map of K to V) -> list of V

 New list with the values of `m` sorted ascending.

 ## Parámetros
 - `m`: the map to read. Read only.

 ## Retorno
 An owned `list of V` sorted with the `Ordered` bind of `V`, so it also works when `V` is `string`. Borrows `m`.

 ## Ejemplo
 ```pengu
 var vs as list of int is calling values_sorted_of with m
 ```

### `map_merge`

> **map_merge**(a: map of K to V, b: map of K to V) -> map of K to V

 Combines `a` and `b` into a new map; `b` wins on collision.

 ## Parámetros
 - `a`: the left map. Read only.
 - `b`: the right map. Read only.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling map_merge with a, b
 ```

### `map_merge_keep_left`

> **map_merge_keep_left**(a: map of K to V, b: map of K to V) -> map of K to V

 Combines `a` and `b` into a new map; keys of `a` keep their value.

 ## Parámetros
 - `a`: the left map, whose values win. Read only.
 - `b`: the right map. Read only.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling map_merge_keep_left with a, b
 ```

### `map_merge_all`

> **map_merge_all**(maps: list of map of K to V) -> map of K to V

 Combines every map of `maps` into one; later maps win.

 ## Parámetros
 - `maps`: the maps to merge in order. Read only.

 ## Retorno
 An owned `map of K to V` the caller releases with `banish`. Borrows `maps`.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling map_merge_all with maps
 ```

### `map_from_lists`

> **map_from_lists**(ks: list of K, vs: list of V) -> map of K to V

 Builds a map from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, consumed up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of K to V` with `min(ks.len, vs.len)` entries; later duplicate keys overwrite earlier ones. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling map_from_lists with ks, vs
 ```

### `from_pairs`

> **from_pairs**(ps: list of Pair__K__V) -> map of K to V

 Builds a map from a list of `oracle.Pair`.

 ## Parámetros
 - `ps`: the key/value pairs to insert in order. Read only.

 ## Retorno
 An owned `map of K to V`; later duplicate keys overwrite earlier ones. Borrows `ps`.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling from_pairs with ps
 ```

### `map_filter_values_contains`

> **map_filter_values_contains**(m: map of K to string, sub: string) -> map of K to string

 Submap of `m` with the entries whose `string` value contains `sub`.

 ## Parámetros
 - `m`: the map to filter. Read only.
 - `sub`: the substring to look for inside each value.

 ## Retorno
 An owned `map of K to string`. Unlike the method form, the module function infers `K` from its argument, so it works for any key type without a concrete block. Borrows `m`.

 ## Ejemplo
 ```pengu
 var f as map of int to string is calling map_filter_values_contains with m, "un"
 ```

### `size_ss`

> **size_ss**(m: map of string to string) -> int

 Number of entries in `m`; equivalent to `calling m.size`.

 ## Parámetros
 - `m`: the `map of string to string` to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.size_ss with m    # 3
 ```

### `is_empty_ss`

> **is_empty_ss**(m: map of string to string) -> bool

 `true` when `m` has no entries.

 ## Parámetros
 - `m`: the `map of string to string` to inspect. Read only.

 ## Retorno
 `true` when the map is empty; `false` otherwise. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.is_empty_ss with m    # false
 ```

### `has_key_ss`

> **has_key_ss**(m: map of string to string, k: string) -> bool

 `true` when `k` exists in the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to query. Read only.
 - `k`: the string key to look up. Borrowed.

 ## Retorno
 `true` when the key is present; `false` otherwise. Borrows both arguments.

 ## Ejemplo
 ```pengu
 calling atlas.has_key_ss with m, "x"    # true
 ```

### `get_or_ss`

> **get_or_ss**(m: map of string to string, k: string, default: string) -> string

 Value of `k` in `m`, or `default` when the key is absent.

 ## Parámetros
 - `m`: the `map of string to string` to query. Read only.
 - `k`: the string key to look up. Borrowed.
 - `default`: the string value returned when the key is missing.

 ## Retorno
 The stored value or `default`, by value. Borrows the map.

 ## Ejemplo
 ```pengu
 calling atlas.get_or_ss with m, "x", ""
 ```

### `get_safe_ss`

> **get_safe_ss**(m: map of string to string, k: string) -> maybe string

 `some v` when `k` is present in the `map of string to string`, `maybe none` otherwise.

 ## Parámetros
 - `m`: the `map of string to string` to query. Read only.
 - `k`: the string key to look up. Borrowed.

 ## Retorno
 A `maybe string` wrapping the stored value, or `maybe none`. Borrows the map.

 ## Ejemplo
 ```pengu
 var got as maybe string is calling atlas.get_safe_ss with m, "x"
 ```

### `put_ss`

> **put_ss**(m: map of string to string, k: string, v: string) -> void

 Inserts or updates `k -> v` in the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to mutate in place.
 - `k`: the string key. Borrowed.
 - `v`: the string value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling atlas.put_ss with m, "x", "x"
 ```

### `remove_ss`

> **remove_ss**(m: map of string to string, k: string) -> bool

 Removes `k` from the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to mutate in place.
 - `k`: the string key to remove. Borrowed.

 ## Retorno
 `true` when the key existed and was removed; `false` otherwise. Mutates `m` in place.

 ## Ejemplo
 ```pengu
 calling atlas.remove_ss with m, "x"    # true
 ```

### `clear_ss`

> **clear_ss**(m: map of string to string) -> void

 Removes every entry from the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to empty in place.

 ## Retorno
 Nothing; the map is left empty in place.

 ## Ejemplo
 ```pengu
 calling atlas.clear_ss with m
 ```

### `keys_ss`

> **keys_ss**(m: map of string to string) -> list of string

 New list with all keys of the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling atlas.keys_ss with m
 ```

### `values_ss`

> **values_ss**(m: map of string to string) -> list of string

 New list with all values of the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var vs as list of string is calling atlas.values_ss with m
 ```

### `clone_ss`

> **clone_ss**(m: map of string to string) -> map of string to string

 Independent shallow copy of the `map of string to string`.

 ## Parámetros
 - `m`: the `map of string to string` to copy. Read only.

 ## Retorno
 An owned `map of string to string` the caller releases with `banish`. Keys and values are copied by value.

 ## Ejemplo
 ```pengu
 var c as map of string to string is calling atlas.clone_ss with m
 ```

### `size_ii`

> **size_ii**(m: map of int to int) -> int

 Number of entries in `m`; equivalent to `calling m.size`.

 ## Parámetros
 - `m`: the `map of int to int` to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.size_ii with m    # 3
 ```

### `is_empty_ii`

> **is_empty_ii**(m: map of int to int) -> bool

 `true` when `m` has no entries.

 ## Parámetros
 - `m`: the `map of int to int` to inspect. Read only.

 ## Retorno
 `true` when the map is empty; `false` otherwise. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.is_empty_ii with m    # false
 ```

### `has_key_ii`

> **has_key_ii**(m: map of int to int, k: int) -> bool

 `true` when `k` exists in the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to query. Read only.
 - `k`: the int key to look up. Borrowed.

 ## Retorno
 `true` when the key is present; `false` otherwise. Borrows both arguments.

 ## Ejemplo
 ```pengu
 calling atlas.has_key_ii with m, 1    # true
 ```

### `get_or_ii`

> **get_or_ii**(m: map of int to int, k: int, default: int) -> int

 Value of `k` in `m`, or `default` when the key is absent.

 ## Parámetros
 - `m`: the `map of int to int` to query. Read only.
 - `k`: the int key to look up. Borrowed.
 - `default`: the int value returned when the key is missing.

 ## Retorno
 The stored value or `default`, by value. Borrows the map.

 ## Ejemplo
 ```pengu
 calling atlas.get_or_ii with m, 1, 0
 ```

### `get_safe_ii`

> **get_safe_ii**(m: map of int to int, k: int) -> maybe int

 `some v` when `k` is present in the `map of int to int`, `maybe none` otherwise.

 ## Parámetros
 - `m`: the `map of int to int` to query. Read only.
 - `k`: the int key to look up. Borrowed.

 ## Retorno
 A `maybe int` wrapping the stored value, or `maybe none`. Borrows the map.

 ## Ejemplo
 ```pengu
 var got as maybe int is calling atlas.get_safe_ii with m, 1
 ```

### `put_ii`

> **put_ii**(m: map of int to int, k: int, v: int) -> void

 Inserts or updates `k -> v` in the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to mutate in place.
 - `k`: the int key. Borrowed.
 - `v`: the int value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling atlas.put_ii with m, 1, 1
 ```

### `remove_ii`

> **remove_ii**(m: map of int to int, k: int) -> bool

 Removes `k` from the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to mutate in place.
 - `k`: the int key to remove. Borrowed.

 ## Retorno
 `true` when the key existed and was removed; `false` otherwise. Mutates `m` in place.

 ## Ejemplo
 ```pengu
 calling atlas.remove_ii with m, 1    # true
 ```

### `clear_ii`

> **clear_ii**(m: map of int to int) -> void

 Removes every entry from the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to empty in place.

 ## Retorno
 Nothing; the map is left empty in place.

 ## Ejemplo
 ```pengu
 calling atlas.clear_ii with m
 ```

### `keys_ii`

> **keys_ii**(m: map of int to int) -> list of int

 New list with all keys of the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to read. Read only.

 ## Retorno
 An owned `list of int` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var ks as list of int is calling atlas.keys_ii with m
 ```

### `values_ii`

> **values_ii**(m: map of int to int) -> list of int

 New list with all values of the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to read. Read only.

 ## Retorno
 An owned `list of int` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var vs as list of int is calling atlas.values_ii with m
 ```

### `clone_ii`

> **clone_ii**(m: map of int to int) -> map of int to int

 Independent shallow copy of the `map of int to int`.

 ## Parámetros
 - `m`: the `map of int to int` to copy. Read only.

 ## Retorno
 An owned `map of int to int` the caller releases with `banish`. Keys and values are copied by value.

 ## Ejemplo
 ```pengu
 var c as map of int to int is calling atlas.clone_ii with m
 ```

### `sum_values_ii`

> **sum_values_ii**(m: map of int to int) -> int

 Sum of all values of the `map of int to int`; zero when empty.

 ## Parámetros
 - `m`: the `map of int to int` to reduce. Read only.

 ## Retorno
 The total as `int`, or `0` when the map is empty. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.sum_values_ii with m
 ```

### `max_value_ii`

> **max_value_ii**(m: map of int to int) -> int

 Largest value of the `map of int to int`; zero when empty.

 ## Parámetros
 - `m`: the `map of int to int` to reduce. Read only.

 ## Retorno
 The maximum as `int`, or `0` when the map is empty. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.max_value_ii with m
 ```

### `min_value_ii`

> **min_value_ii**(m: map of int to int) -> int

 Smallest value of the `map of int to int`; zero when empty.

 ## Parámetros
 - `m`: the `map of int to int` to reduce. Read only.

 ## Retorno
 The minimum as `int`, or `0` when the map is empty. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.min_value_ii with m
 ```

### `size_is`

> **size_is**(m: map of int to string) -> int

 Number of entries in `m`; equivalent to `calling m.size`.

 ## Parámetros
 - `m`: the `map of int to string` to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.size_is with m    # 3
 ```

### `is_empty_is`

> **is_empty_is**(m: map of int to string) -> bool

 `true` when `m` has no entries.

 ## Parámetros
 - `m`: the `map of int to string` to inspect. Read only.

 ## Retorno
 `true` when the map is empty; `false` otherwise. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.is_empty_is with m    # false
 ```

### `has_key_is`

> **has_key_is**(m: map of int to string, k: int) -> bool

 `true` when `k` exists in the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to query. Read only.
 - `k`: the int key to look up. Borrowed.

 ## Retorno
 `true` when the key is present; `false` otherwise. Borrows both arguments.

 ## Ejemplo
 ```pengu
 calling atlas.has_key_is with m, 1    # true
 ```

### `get_or_is`

> **get_or_is**(m: map of int to string, k: int, default: string) -> string

 Value of `k` in `m`, or `default` when the key is absent.

 ## Parámetros
 - `m`: the `map of int to string` to query. Read only.
 - `k`: the int key to look up. Borrowed.
 - `default`: the string value returned when the key is missing.

 ## Retorno
 The stored value or `default`, by value. Borrows the map.

 ## Ejemplo
 ```pengu
 calling atlas.get_or_is with m, 1, 0
 ```

### `get_safe_is`

> **get_safe_is**(m: map of int to string, k: int) -> maybe string

 `some v` when `k` is present in the `map of int to string`, `maybe none` otherwise.

 ## Parámetros
 - `m`: the `map of int to string` to query. Read only.
 - `k`: the int key to look up. Borrowed.

 ## Retorno
 A `maybe string` wrapping the stored value, or `maybe none`. Borrows the map.

 ## Ejemplo
 ```pengu
 var got as maybe string is calling atlas.get_safe_is with m, 1
 ```

### `put_is`

> **put_is**(m: map of int to string, k: int, v: string) -> void

 Inserts or updates `k -> v` in the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to mutate in place.
 - `k`: the int key. Borrowed.
 - `v`: the string value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling atlas.put_is with m, 1, "x"
 ```

### `remove_is`

> **remove_is**(m: map of int to string, k: int) -> bool

 Removes `k` from the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to mutate in place.
 - `k`: the int key to remove. Borrowed.

 ## Retorno
 `true` when the key existed and was removed; `false` otherwise. Mutates `m` in place.

 ## Ejemplo
 ```pengu
 calling atlas.remove_is with m, 1    # true
 ```

### `clear_is`

> **clear_is**(m: map of int to string) -> void

 Removes every entry from the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to empty in place.

 ## Retorno
 Nothing; the map is left empty in place.

 ## Ejemplo
 ```pengu
 calling atlas.clear_is with m
 ```

### `keys_is`

> **keys_is**(m: map of int to string) -> list of int

 New list with all keys of the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to read. Read only.

 ## Retorno
 An owned `list of int` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var ks as list of int is calling atlas.keys_is with m
 ```

### `values_is`

> **values_is**(m: map of int to string) -> list of string

 New list with all values of the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var vs as list of string is calling atlas.values_is with m
 ```

### `clone_is`

> **clone_is**(m: map of int to string) -> map of int to string

 Independent shallow copy of the `map of int to string`.

 ## Parámetros
 - `m`: the `map of int to string` to copy. Read only.

 ## Retorno
 An owned `map of int to string` the caller releases with `banish`. Keys and values are copied by value.

 ## Ejemplo
 ```pengu
 var c as map of int to string is calling atlas.clone_is with m
 ```

### `size_sf`

> **size_sf**(m: map of string to float) -> int

 Number of entries in `m`; equivalent to `calling m.size`.

 ## Parámetros
 - `m`: the `map of string to float` to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.size_sf with m    # 3
 ```

### `is_empty_sf`

> **is_empty_sf**(m: map of string to float) -> bool

 `true` when `m` has no entries.

 ## Parámetros
 - `m`: the `map of string to float` to inspect. Read only.

 ## Retorno
 `true` when the map is empty; `false` otherwise. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.is_empty_sf with m    # false
 ```

### `has_key_sf`

> **has_key_sf**(m: map of string to float, k: string) -> bool

 `true` when `k` exists in the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to query. Read only.
 - `k`: the string key to look up. Borrowed.

 ## Retorno
 `true` when the key is present; `false` otherwise. Borrows both arguments.

 ## Ejemplo
 ```pengu
 calling atlas.has_key_sf with m, "x"    # true
 ```

### `get_or_sf`

> **get_or_sf**(m: map of string to float, k: string, default: float) -> float

 Value of `k` in `m`, or `default` when the key is absent.

 ## Parámetros
 - `m`: the `map of string to float` to query. Read only.
 - `k`: the string key to look up. Borrowed.
 - `default`: the float value returned when the key is missing.

 ## Retorno
 The stored value or `default`, by value. Borrows the map.

 ## Ejemplo
 ```pengu
 calling atlas.get_or_sf with m, "x", 0.0
 ```

### `get_safe_sf`

> **get_safe_sf**(m: map of string to float, k: string) -> maybe float

 `some v` when `k` is present in the `map of string to float`, `maybe none` otherwise.

 ## Parámetros
 - `m`: the `map of string to float` to query. Read only.
 - `k`: the string key to look up. Borrowed.

 ## Retorno
 A `maybe float` wrapping the stored value, or `maybe none`. Borrows the map.

 ## Ejemplo
 ```pengu
 var got as maybe float is calling atlas.get_safe_sf with m, "x"
 ```

### `put_sf`

> **put_sf**(m: map of string to float, k: string, v: float) -> void

 Inserts or updates `k -> v` in the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to mutate in place.
 - `k`: the string key. Borrowed.
 - `v`: the float value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling atlas.put_sf with m, "x", 1.0
 ```

### `remove_sf`

> **remove_sf**(m: map of string to float, k: string) -> bool

 Removes `k` from the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to mutate in place.
 - `k`: the string key to remove. Borrowed.

 ## Retorno
 `true` when the key existed and was removed; `false` otherwise. Mutates `m` in place.

 ## Ejemplo
 ```pengu
 calling atlas.remove_sf with m, "x"    # true
 ```

### `clear_sf`

> **clear_sf**(m: map of string to float) -> void

 Removes every entry from the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to empty in place.

 ## Retorno
 Nothing; the map is left empty in place.

 ## Ejemplo
 ```pengu
 calling atlas.clear_sf with m
 ```

### `keys_sf`

> **keys_sf**(m: map of string to float) -> list of string

 New list with all keys of the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling atlas.keys_sf with m
 ```

### `values_sf`

> **values_sf**(m: map of string to float) -> list of float

 New list with all values of the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to read. Read only.

 ## Retorno
 An owned `list of float` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var vs as list of float is calling atlas.values_sf with m
 ```

### `clone_sf`

> **clone_sf**(m: map of string to float) -> map of string to float

 Independent shallow copy of the `map of string to float`.

 ## Parámetros
 - `m`: the `map of string to float` to copy. Read only.

 ## Retorno
 An owned `map of string to float` the caller releases with `banish`. Keys and values are copied by value.

 ## Ejemplo
 ```pengu
 var c as map of string to float is calling atlas.clone_sf with m
 ```

### `sum_values_sf`

> **sum_values_sf**(m: map of string to float) -> float

 Sum of all values of the `map of string to float`; zero when empty.

 ## Parámetros
 - `m`: the `map of string to float` to reduce. Read only.

 ## Retorno
 The total as `float`, or `0` when the map is empty. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.sum_values_sf with m
 ```

### `max_value_sf`

> **max_value_sf**(m: map of string to float) -> float

 Largest value of the `map of string to float`; zero when empty.

 ## Parámetros
 - `m`: the `map of string to float` to reduce. Read only.

 ## Retorno
 The maximum as `float`, or `0` when the map is empty. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.max_value_sf with m
 ```

### `min_value_sf`

> **min_value_sf**(m: map of string to float) -> float

 Smallest value of the `map of string to float`; zero when empty.

 ## Parámetros
 - `m`: the `map of string to float` to reduce. Read only.

 ## Retorno
 The minimum as `float`, or `0` when the map is empty. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.min_value_sf with m
 ```

### `size_sb`

> **size_sb**(m: map of string to bool) -> int

 Number of entries in `m`; equivalent to `calling m.size`.

 ## Parámetros
 - `m`: the `map of string to bool` to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.size_sb with m    # 3
 ```

### `is_empty_sb`

> **is_empty_sb**(m: map of string to bool) -> bool

 `true` when `m` has no entries.

 ## Parámetros
 - `m`: the `map of string to bool` to inspect. Read only.

 ## Retorno
 `true` when the map is empty; `false` otherwise. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.is_empty_sb with m    # false
 ```

### `has_key_sb`

> **has_key_sb**(m: map of string to bool, k: string) -> bool

 `true` when `k` exists in the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to query. Read only.
 - `k`: the string key to look up. Borrowed.

 ## Retorno
 `true` when the key is present; `false` otherwise. Borrows both arguments.

 ## Ejemplo
 ```pengu
 calling atlas.has_key_sb with m, "x"    # true
 ```

### `get_or_sb`

> **get_or_sb**(m: map of string to bool, k: string, default: bool) -> bool

 Value of `k` in `m`, or `default` when the key is absent.

 ## Parámetros
 - `m`: the `map of string to bool` to query. Read only.
 - `k`: the string key to look up. Borrowed.
 - `default`: the bool value returned when the key is missing.

 ## Retorno
 The stored value or `default`, by value. Borrows the map.

 ## Ejemplo
 ```pengu
 calling atlas.get_or_sb with m, "x", false
 ```

### `get_safe_sb`

> **get_safe_sb**(m: map of string to bool, k: string) -> maybe bool

 `some v` when `k` is present in the `map of string to bool`, `maybe none` otherwise.

 ## Parámetros
 - `m`: the `map of string to bool` to query. Read only.
 - `k`: the string key to look up. Borrowed.

 ## Retorno
 A `maybe bool` wrapping the stored value, or `maybe none`. Borrows the map.

 ## Ejemplo
 ```pengu
 var got as maybe bool is calling atlas.get_safe_sb with m, "x"
 ```

### `put_sb`

> **put_sb**(m: map of string to bool, k: string, v: bool) -> void

 Inserts or updates `k -> v` in the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to mutate in place.
 - `k`: the string key. Borrowed.
 - `v`: the bool value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling atlas.put_sb with m, "x", true
 ```

### `remove_sb`

> **remove_sb**(m: map of string to bool, k: string) -> bool

 Removes `k` from the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to mutate in place.
 - `k`: the string key to remove. Borrowed.

 ## Retorno
 `true` when the key existed and was removed; `false` otherwise. Mutates `m` in place.

 ## Ejemplo
 ```pengu
 calling atlas.remove_sb with m, "x"    # true
 ```

### `clear_sb`

> **clear_sb**(m: map of string to bool) -> void

 Removes every entry from the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to empty in place.

 ## Retorno
 Nothing; the map is left empty in place.

 ## Ejemplo
 ```pengu
 calling atlas.clear_sb with m
 ```

### `keys_sb`

> **keys_sb**(m: map of string to bool) -> list of string

 New list with all keys of the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling atlas.keys_sb with m
 ```

### `values_sb`

> **values_sb**(m: map of string to bool) -> list of bool

 New list with all values of the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to read. Read only.

 ## Retorno
 An owned `list of bool` the caller releases with `banish`, in internal hash order.

 ## Ejemplo
 ```pengu
 var vs as list of bool is calling atlas.values_sb with m
 ```

### `clone_sb`

> **clone_sb**(m: map of string to bool) -> map of string to bool

 Independent shallow copy of the `map of string to bool`.

 ## Parámetros
 - `m`: the `map of string to bool` to copy. Read only.

 ## Retorno
 An owned `map of string to bool` the caller releases with `banish`. Keys and values are copied by value.

 ## Ejemplo
 ```pengu
 var c as map of string to bool is calling atlas.clone_sb with m
 ```

### `count_true_sb`

> **count_true_sb**(m: map of string to bool) -> int

 Number of entries of the `map of string to bool` whose value is `true`.

 ## Parámetros
 - `m`: the `map of string to bool` to count. Read only.

 ## Retorno
 The number of `true` values as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.count_true_sb with m    # 2
 ```

### `count_false_sb`

> **count_false_sb**(m: map of string to bool) -> int

 Number of entries of the `map of string to bool` whose value is `false`.

 ## Parámetros
 - `m`: the `map of string to bool` to count. Read only.

 ## Retorno
 The number of `false` values as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.count_false_sb with m    # 1
 ```

### `put`

> **put**(m: map of string to int, key: string, value: int) -> void

 Inserts or updates `key -> value` in the `map of string to int`.

 ## Parámetros
 - `m`: the `map of string to int` to mutate in place.
 - `key`: the string key. Borrowed.
 - `value`: the int value to store.

 ## Retorno
 Nothing; the map is mutated in place.

 ## Ejemplo
 ```pengu
 calling atlas.put with m, "x", 1
 ```

### `map_len_str_int`

> **map_len_str_int**(m: map of string to int) -> int

 Number of entries of the `map of string to int`; historical alias of `atlas.size`.

 ## Parámetros
 - `m`: the `map of string to int` to measure. Read only.

 ## Retorno
 The number of entries as an `int`. Borrows `m`.

 ## Ejemplo
 ```pengu
 calling atlas.map_len_str_int with m    # 3
 ```

### `keys_sorted_ss`

> **keys_sorted_ss**(m: map of string to string) -> list of string

 New list with the keys of the `map of string to string` sorted ascending.

 ## Parámetros
 - `m`: the `map of string to string` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling atlas.keys_sorted_ss with m
 ```

### `values_sorted_ss`

> **values_sorted_ss**(m: map of string to string) -> list of string

 New list with the values of the `map of string to string` sorted ascending.

 ## Parámetros
 - `m`: the `map of string to string` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var vs as list of string is calling atlas.values_sorted_ss with m
 ```

### `keys_sorted_ii`

> **keys_sorted_ii**(m: map of int to int) -> list of int

 New list with the keys of the `map of int to int` sorted ascending.

 ## Parámetros
 - `m`: the `map of int to int` to read. Read only.

 ## Retorno
 An owned `list of int` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var ks as list of int is calling atlas.keys_sorted_ii with m
 ```

### `values_sorted_ii`

> **values_sorted_ii**(m: map of int to int) -> list of int

 New list with the values of the `map of int to int` sorted ascending.

 ## Parámetros
 - `m`: the `map of int to int` to read. Read only.

 ## Retorno
 An owned `list of int` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var vs as list of int is calling atlas.values_sorted_ii with m
 ```

### `keys_sorted_is`

> **keys_sorted_is**(m: map of int to string) -> list of int

 New list with the keys of the `map of int to string` sorted ascending.

 ## Parámetros
 - `m`: the `map of int to string` to read. Read only.

 ## Retorno
 An owned `list of int` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var ks as list of int is calling atlas.keys_sorted_is with m
 ```

### `values_sorted_is`

> **values_sorted_is**(m: map of int to string) -> list of string

 New list with the values of the `map of int to string` sorted ascending.

 ## Parámetros
 - `m`: the `map of int to string` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var vs as list of string is calling atlas.values_sorted_is with m
 ```

### `keys_sorted_sf`

> **keys_sorted_sf**(m: map of string to float) -> list of string

 New list with the keys of the `map of string to float` sorted ascending.

 ## Parámetros
 - `m`: the `map of string to float` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling atlas.keys_sorted_sf with m
 ```

### `values_sorted_sf`

> **values_sorted_sf**(m: map of string to float) -> list of float

 New list with the values of the `map of string to float` sorted ascending.

 ## Parámetros
 - `m`: the `map of string to float` to read. Read only.

 ## Retorno
 An owned `list of float` the caller releases with `banish`, sorted with `qsort` through the matching `antiquus` comparator.

 ## Ejemplo
 ```pengu
 var vs as list of float is calling atlas.values_sorted_sf with m
 ```

### `keys_sorted_sb`

> **keys_sorted_sb**(m: map of string to bool) -> list of string

 New list with the keys of the `map of string to bool` sorted ascending.

 ## Parámetros
 - `m`: the `map of string to bool` to read. Read only.

 ## Retorno
 An owned `list of string` the caller releases with `banish`, sorted ascending through the generic `Ordered` sort.

 ## Ejemplo
 ```pengu
 var ks as list of string is calling atlas.keys_sorted_sb with m
 ```

### `merge`

> **merge**(a: map of string to int, b: map of string to int) -> map of string to int

 Combines `a` and `b` into a new `map of string to int`; `b` wins on collision.

 ## Parámetros
 - `a`: the left `map of string to int`. Read only.
 - `b`: the right `map of string to int`. Read only.

 ## Retorno
 An owned `map of string to int` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling atlas.merge with a, b
 ```

### `merge_keep_left`

> **merge_keep_left**(a: map of string to int, b: map of string to int) -> map of string to int

 Combines `a` and `b` into a new `map of string to int`; keys already present in `a` keep their value.

 ## Parámetros
 - `a`: the left `map of string to int`, whose values win. Read only.
 - `b`: the right `map of string to int`. Read only.

 ## Retorno
 An owned `map of string to int` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling atlas.merge_keep_left with a, b
 ```

### `merge_keep_right`

> **merge_keep_right**(a: map of string to int, b: map of string to int) -> map of string to int

 Combines `a` and `b` into a new `map of string to int`; `b` wins on collision (same as `atlas.merge`).

 ## Parámetros
 - `a`: the left `map of string to int`. Read only.
 - `b`: the right `map of string to int`. Read only.

 ## Retorno
 An owned `map of string to int` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling atlas.merge_keep_right with a, b
 ```

### `from_lists`

> **from_lists**(ks: list of string, vs: list of int) -> map of string to int

 Builds an `map of string to int` from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, read up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of string to int` the caller releases with `banish`. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of string to int is calling atlas.from_lists with ks, vs
 ```

### `merge_ss`

> **merge_ss**(a: map of string to string, b: map of string to string) -> map of string to string

 Combines `a` and `b` into a new `map of string to string`; `b` wins on collision.

 ## Parámetros
 - `a`: the left `map of string to string`. Read only.
 - `b`: the right `map of string to string`. Read only.

 ## Retorno
 An owned `map of string to string` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to string is calling atlas.merge_ss with a, b
 ```

### `merge_keep_left_ss`

> **merge_keep_left_ss**(a: map of string to string, b: map of string to string) -> map of string to string

 Combines `a` and `b` into a new `map of string to string`; keys already present in `a` keep their value.

 ## Parámetros
 - `a`: the left `map of string to string`, whose values win. Read only.
 - `b`: the right `map of string to string`. Read only.

 ## Retorno
 An owned `map of string to string` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to string is calling atlas.merge_keep_left_ss with a, b
 ```

### `merge_keep_right_ss`

> **merge_keep_right_ss**(a: map of string to string, b: map of string to string) -> map of string to string

 Combines `a` and `b` into a new `map of string to string`; `b` wins on collision (same as `atlas.merge_ss`).

 ## Parámetros
 - `a`: the left `map of string to string`. Read only.
 - `b`: the right `map of string to string`. Read only.

 ## Retorno
 An owned `map of string to string` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to string is calling atlas.merge_keep_right_ss with a, b
 ```

### `from_lists_ss`

> **from_lists_ss**(ks: list of string, vs: list of string) -> map of string to string

 Builds an `map of string to string` from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, read up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of string to string` the caller releases with `banish`. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of string to string is calling atlas.from_lists_ss with ks, vs
 ```

### `merge_sf`

> **merge_sf**(a: map of string to float, b: map of string to float) -> map of string to float

 Combines `a` and `b` into a new `map of string to float`; `b` wins on collision.

 ## Parámetros
 - `a`: the left `map of string to float`. Read only.
 - `b`: the right `map of string to float`. Read only.

 ## Retorno
 An owned `map of string to float` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to float is calling atlas.merge_sf with a, b
 ```

### `merge_keep_left_sf`

> **merge_keep_left_sf**(a: map of string to float, b: map of string to float) -> map of string to float

 Combines `a` and `b` into a new `map of string to float`; keys already present in `a` keep their value.

 ## Parámetros
 - `a`: the left `map of string to float`, whose values win. Read only.
 - `b`: the right `map of string to float`. Read only.

 ## Retorno
 An owned `map of string to float` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to float is calling atlas.merge_keep_left_sf with a, b
 ```

### `merge_keep_right_sf`

> **merge_keep_right_sf**(a: map of string to float, b: map of string to float) -> map of string to float

 Combines `a` and `b` into a new `map of string to float`; `b` wins on collision (same as `atlas.merge_sf`).

 ## Parámetros
 - `a`: the left `map of string to float`. Read only.
 - `b`: the right `map of string to float`. Read only.

 ## Retorno
 An owned `map of string to float` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to float is calling atlas.merge_keep_right_sf with a, b
 ```

### `from_lists_sf`

> **from_lists_sf**(ks: list of string, vs: list of float) -> map of string to float

 Builds an `map of string to float` from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, read up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of string to float` the caller releases with `banish`. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of string to float is calling atlas.from_lists_sf with ks, vs
 ```

### `merge_ii`

> **merge_ii**(a: map of int to int, b: map of int to int) -> map of int to int

 Combines `a` and `b` into a new `map of int to int`; `b` wins on collision.

 ## Parámetros
 - `a`: the left `map of int to int`. Read only.
 - `b`: the right `map of int to int`. Read only.

 ## Retorno
 An owned `map of int to int` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of int to int is calling atlas.merge_ii with a, b
 ```

### `merge_keep_left_ii`

> **merge_keep_left_ii**(a: map of int to int, b: map of int to int) -> map of int to int

 Combines `a` and `b` into a new `map of int to int`; keys already present in `a` keep their value.

 ## Parámetros
 - `a`: the left `map of int to int`, whose values win. Read only.
 - `b`: the right `map of int to int`. Read only.

 ## Retorno
 An owned `map of int to int` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of int to int is calling atlas.merge_keep_left_ii with a, b
 ```

### `merge_keep_right_ii`

> **merge_keep_right_ii**(a: map of int to int, b: map of int to int) -> map of int to int

 Combines `a` and `b` into a new `map of int to int`; `b` wins on collision (same as `atlas.merge_ii`).

 ## Parámetros
 - `a`: the left `map of int to int`. Read only.
 - `b`: the right `map of int to int`. Read only.

 ## Retorno
 An owned `map of int to int` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of int to int is calling atlas.merge_keep_right_ii with a, b
 ```

### `from_lists_ii`

> **from_lists_ii**(ks: list of int, vs: list of int) -> map of int to int

 Builds an `map of int to int` from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, read up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of int to int` the caller releases with `banish`. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of int to int is calling atlas.from_lists_ii with ks, vs
 ```

### `merge_is`

> **merge_is**(a: map of int to string, b: map of int to string) -> map of int to string

 Combines `a` and `b` into a new `map of int to string`; `b` wins on collision.

 ## Parámetros
 - `a`: the left `map of int to string`. Read only.
 - `b`: the right `map of int to string`. Read only.

 ## Retorno
 An owned `map of int to string` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of int to string is calling atlas.merge_is with a, b
 ```

### `merge_keep_left_is`

> **merge_keep_left_is**(a: map of int to string, b: map of int to string) -> map of int to string

 Combines `a` and `b` into a new `map of int to string`; keys already present in `a` keep their value.

 ## Parámetros
 - `a`: the left `map of int to string`, whose values win. Read only.
 - `b`: the right `map of int to string`. Read only.

 ## Retorno
 An owned `map of int to string` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of int to string is calling atlas.merge_keep_left_is with a, b
 ```

### `merge_keep_right_is`

> **merge_keep_right_is**(a: map of int to string, b: map of int to string) -> map of int to string

 Combines `a` and `b` into a new `map of int to string`; `b` wins on collision (same as `atlas.merge_is`).

 ## Parámetros
 - `a`: the left `map of int to string`. Read only.
 - `b`: the right `map of int to string`. Read only.

 ## Retorno
 An owned `map of int to string` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of int to string is calling atlas.merge_keep_right_is with a, b
 ```

### `from_lists_is`

> **from_lists_is**(ks: list of int, vs: list of string) -> map of int to string

 Builds an `map of int to string` from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, read up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of int to string` the caller releases with `banish`. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of int to string is calling atlas.from_lists_is with ks, vs
 ```

### `merge_sb`

> **merge_sb**(a: map of string to bool, b: map of string to bool) -> map of string to bool

 Combines `a` and `b` into a new `map of string to bool`; `b` wins on collision.

 ## Parámetros
 - `a`: the left `map of string to bool`. Read only.
 - `b`: the right `map of string to bool`. Read only.

 ## Retorno
 An owned `map of string to bool` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to bool is calling atlas.merge_sb with a, b
 ```

### `merge_keep_left_sb`

> **merge_keep_left_sb**(a: map of string to bool, b: map of string to bool) -> map of string to bool

 Combines `a` and `b` into a new `map of string to bool`; keys already present in `a` keep their value.

 ## Parámetros
 - `a`: the left `map of string to bool`, whose values win. Read only.
 - `b`: the right `map of string to bool`. Read only.

 ## Retorno
 An owned `map of string to bool` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to bool is calling atlas.merge_keep_left_sb with a, b
 ```

### `merge_keep_right_sb`

> **merge_keep_right_sb**(a: map of string to bool, b: map of string to bool) -> map of string to bool

 Combines `a` and `b` into a new `map of string to bool`; `b` wins on collision (same as `atlas.merge_sb`).

 ## Parámetros
 - `a`: the left `map of string to bool`. Read only.
 - `b`: the right `map of string to bool`. Read only.

 ## Retorno
 An owned `map of string to bool` the caller releases with `banish`. Borrows both maps.

 ## Ejemplo
 ```pengu
 var m as map of string to bool is calling atlas.merge_keep_right_sb with a, b
 ```

### `from_lists_sb`

> **from_lists_sb**(ks: list of string, vs: list of bool) -> map of string to bool

 Builds an `map of string to bool` from the parallel lists `ks` and `vs`.

 ## Parámetros
 - `ks`: the keys, read up to `min(ks.len, vs.len)`. Read only.
 - `vs`: the values. Read only.

 ## Retorno
 An owned `map of string to bool` the caller releases with `banish`. Borrows both lists.

 ## Ejemplo
 ```pengu
 var m as map of string to bool is calling atlas.from_lists_sb with ks, vs
 ```

### `_atlas_cmp_i32`

> **_atlas_cmp_i32**(a: ref to frozen void, b: ref to frozen void) -> int

 Compares two `int32_t` cells for `qsort`.

 ## Motivo
 `qsort` needs a C callback and the `int32_t` comparison is the branch-free
 `(x > y) - (x < y)`; expressing the byte offsets in PenguScript would cost one
 slice per comparison. It carries `@export` so dead-code elimination keeps it:
 nothing in PenguScript references a function only raw C calls.

 ## Memoria
 Reads the two borrowed cells; allocates nothing and frees nothing.

### `_atlas_sort_i32_in_place`

> **_atlas_sort_i32_in_place**(xs: list of int) -> void

 Sorts an `int` list in place with `qsort` (ascending).

 ## Motivo
 The compatibility wrappers (`keys_sorted_ii`, `values_sorted_ii`,
 `keys_sorted_is`) need one C implementation per element type; `qsort` over the
 `PenguList` buffer is faster than the generic insertion sort and reuses the
 same comparator.

 ## Memoria
 Sorts the caller's list buffer in place; allocates nothing and frees nothing.

### `_atlas_cmp_f32`

> **_atlas_cmp_f32**(a: ref to frozen void, b: ref to frozen void) -> int

 Compares two `float` cells for `qsort`.

 ## Motivo
 `float` is 32-bit, so the comparator dereferences the cells as `const float*`
 and returns `(x > y) - (x < y)`; `NaN` values compare as equal and keep their
 relative order. `@export` keeps it alive through dead-code elimination.

 ## Memoria
 Reads the two borrowed cells; allocates nothing and frees nothing.

### `_atlas_sort_f32_in_place`

> **_atlas_sort_f32_in_place**(xs: list of float) -> void

 Sorts a `float` list in place with `qsort` (ascending).

 ## Motivo
 `values_sorted_sf` needs the 32-bit element size (`sizeof(float)`); the
 generic insertion sort would call the `Ordered` bind once per comparison.

 ## Memoria
 Sorts the caller's list buffer in place; allocates nothing and frees nothing.

### `_atlas_cmp_string`

> **_atlas_cmp_string**(a: ref to frozen void, b: ref to frozen void) -> int

 Compares two `PenguString` cells for `qsort` (byte order).

 ## Motivo
 `string` has no C ordering operator, so the comparator reads
 `PenguString.data`/`.len` directly: `memcmp` over the common prefix and
 `len` as the tie-breaker, exact for NUL-containing strings and allocation
 free. `@export` keeps it alive through dead-code elimination.

 ## Memoria
 Reads the two borrowed `PenguString` cells; allocates nothing and frees
 nothing.

### `_atlas_sort_strings_in_place`

> **_atlas_sort_strings_in_place**(xs: list of string) -> void

 Sorts a `string` list in place with `qsort` (ascending).

 ## Motivo
 `keys_sorted_ss`, `values_sorted_ss`, `values_sorted_is`, `keys_sorted_sf`
 and `_sort_strings` share this one C sort; the element size is the
 `PenguString` cell, not the bytes it points to.

 ## Memoria
 Sorts the caller's list buffer in place; the `PenguString` cells are moved,
 not copied, so no string is duplicated or freed.

### `_sort_strings`

> **_sort_strings**(xs: list of string) -> list of string

 Sorts a copy of `xs` ascending through the C string comparator.

### `_expect_eq_int`

> **_expect_eq_int**(got: int, want: int, label: string) -> void

 Fails with `label` when `got != want`.

### `_expect_eq_string`

> **_expect_eq_string**(got: string, want: string, label: string) -> void

 Fails with `label` when `got != want` (compared with `std.scrolls.compare`).

### `_expect_true`

> **_expect_true**(cond: bool, label: string) -> void

 Fails with `label` when `cond` is false.

### `_one`

> **_one**(k: K, v: V) -> map of K to V

 Map with the single entry `k -> v` (test helper).

### `_count`

> **_count**(xs: list of T) -> int

 Number of elements of `xs` (test helper).

### `_sample_str_int`

> **_sample_str_int**() -> map of string to int

 Fixture `{"alpha": 1, "beta": 2, "gamma": 3}`.

### `_sample_str_str`

> **_sample_str_str**() -> map of string to string

 Fixture `{"alpha": "uno", "beta": "dos", "gamma": "tres"}`.

### `_sample_str_float`

> **_sample_str_float**() -> map of string to float

 Fixture `{"alpha": 1.5, "beta": -2.5, "gamma": 10.0}`.

### `_sample_str_bool`

> **_sample_str_bool**() -> map of string to bool

 Fixture `{"alpha": true, "beta": false, "gamma": true}`.

### `_sample_int_int`

> **_sample_int_int**() -> map of int to int

 Fixture `{1: 10, 2: -20, 3: 30}`.

### `_sample_int_str`

> **_sample_int_str**() -> map of int to string

 Fixture `{1: "uno", 2: "dos", 3: "tres"}`.

### `_value_gt_one`

> **_value_gt_one**(k: string, v: int) -> bool

 Test predicate: value greater than one.

### `_inc`

> **_inc**(x: int) -> int

 Test transformation: increment.

### `"size counts the entries"`

> test "size counts the entries"

_Undocumented._

### `"size of an empty map is zero"`

> test "size of an empty map is zero"

_Undocumented._

### `"is_empty is false with entries"`

> test "is_empty is false with entries"

_Undocumented._

### `"is_empty is true without entries"`

> test "is_empty is true without entries"

_Undocumented._

### `"has_key finds a present key"`

> test "has_key finds a present key"

_Undocumented._

### `"has_key rejects a missing key"`

> test "has_key rejects a missing key"

_Undocumented._

### `"has_any_key with one match"`

> test "has_any_key with one match"

_Undocumented._

### `"has_any_key without matches"`

> test "has_any_key without matches"

_Undocumented._

### `"has_all_keys with every key"`

> test "has_all_keys with every key"

_Undocumented._

### `"has_all_keys detects the missing key"`

> test "has_all_keys detects the missing key"

_Undocumented._

### `"get_or returns the stored value"`

> test "get_or returns the stored value"

_Undocumented._

### `"get_or returns the fallback when missing"`

> test "get_or returns the fallback when missing"

_Undocumented._

### `"get_safe wraps a present key in some"`

> test "get_safe wraps a present key in some"

_Undocumented._

### `"get_safe returns maybe none when missing"`

> test "get_safe returns maybe none when missing"

_Undocumented._

### `"find_key_by_value finds the key of a value"`

> test "find_key_by_value finds the key of a value"

_Undocumented._

### `"find_key_by_value misses absent values"`

> test "find_key_by_value misses absent values"

_Undocumented._

### `"update changes an existing value"`

> test "update changes an existing value"

_Undocumented._

### `"update returns false for a missing key"`

> test "update returns false for a missing key"

_Undocumented._

### `"rename_key keeps the value"`

> test "rename_key keeps the value"

_Undocumented._

### `"rename_key returns false for a missing key"`

> test "rename_key returns false for a missing key"

_Undocumented._

### `"rename_key overwrites the destination on collision"`

> test "rename_key overwrites the destination on collision"

_Undocumented._

### `"remove deletes a present key"`

> test "remove deletes a present key"

_Undocumented._

### `"remove returns false for a missing key"`

> test "remove returns false for a missing key"

_Undocumented._

### `"clear leaves the map empty"`

> test "clear leaves the map empty"

_Undocumented._

### `"remove_all deletes only present keys"`

> test "remove_all deletes only present keys"

_Undocumented._

### `"remove_all returns zero without matches"`

> test "remove_all returns zero without matches"

_Undocumented._

### `"put_all copies the entries of another map"`

> test "put_all copies the entries of another map"

_Undocumented._

### `"put_all overwrites repeated keys"`

> test "put_all overwrites repeated keys"

_Undocumented._

### `"keys returns every key"`

> test "keys returns every key"

_Undocumented._

### `"values returns every value"`

> test "values returns every value"

_Undocumented._

### `"to_values_list is an alias of values"`

> test "to_values_list is an alias of values"

_Undocumented._

### `"copy is an alias of clone"`

> test "copy is an alias of clone"

_Undocumented._

### `"is_equal compares by content"`

> test "is_equal compares by content"

_Undocumented._

### `"is_equal distinguishes different sizes"`

> test "is_equal distinguishes different sizes"

_Undocumented._

### `"is_equal distinguishes different values"`

> test "is_equal distinguishes different values"

_Undocumented._

### `"entries packs key and value"`

> test "entries packs key and value"

_Undocumented._

### `"invert swaps keys and values"`

> test "invert swaps keys and values"

_Undocumented._

### `"take_keys keeps only the requested keys"`

> test "take_keys keeps only the requested keys"

_Undocumented._

### `"count_where counts the entries that match"`

> test "count_where counts the entries that match"

_Undocumented._

### `"filter_entries keeps the entries that match"`

> test "filter_entries keeps the entries that match"

_Undocumented._

### `"map_values_with transforms every value"`

> test "map_values_with transforms every value"

_Undocumented._

### `"merge_all combines the receiver with other maps"`

> test "merge_all combines the receiver with other maps"

_Undocumented._

### `"sum_values adds int values"`

> test "sum_values adds int values"

_Undocumented._

### `"sum_values of an empty map is zero"`

> test "sum_values of an empty map is zero"

_Undocumented._

### `"sum_values_filtered honours the range"`

> test "sum_values_filtered honours the range"

_Undocumented._

### `"all_values_positive with every value positive"`

> test "all_values_positive with every value positive"

_Undocumented._

### `"all_values_positive on an empty map"`

> test "all_values_positive on an empty map"

_Undocumented._

### `"any_value_negative is false without negatives"`

> test "any_value_negative is false without negatives"

_Undocumented._

### `"count_if_value_positive counts the positives"`

> test "count_if_value_positive counts the positives"

_Undocumented._

### `"count_if_value_negative counts the negatives"`

> test "count_if_value_negative counts the negatives"

_Undocumented._

### `"map_values_double doubles every value"`

> test "map_values_double doubles every value"

_Undocumented._

### `"map_values_negate negates every value"`

> test "map_values_negate negates every value"

_Undocumented._

### `"map_values_scale multiplies by the factor"`

> test "map_values_scale multiplies by the factor"

_Undocumented._

### `"max_value returns the largest int"`

> test "max_value returns the largest int"

_Undocumented._

### `"max_value of an empty map is zero"`

> test "max_value of an empty map is zero"

_Undocumented._

### `"min_value returns the smallest int"`

> test "min_value returns the smallest int"

_Undocumented._

### `"values_in_range with every value inside"`

> test "values_in_range with every value inside"

_Undocumented._

### `"values_in_range detects an out-of-range value"`

> test "values_in_range detects an out-of-range value"

_Undocumented._

### `"filter_values_range keeps only the range"`

> test "filter_values_range keeps only the range"

_Undocumented._

### `"keys_sorted sorts string keys"`

> test "keys_sorted sorts string keys"

_Undocumented._

### `"keys_sorted sorts int keys"`

> test "keys_sorted sorts int keys"

_Undocumented._

### `"values_sorted sorts int values"`

> test "values_sorted sorts int values"

_Undocumented._

### `"values_sorted sorts string values"`

> test "values_sorted sorts string values"

_Undocumented._

### `"values_sorted sorts string values of an int-keyed map"`

> test "values_sorted sorts string values of an int-keyed map"

_Undocumented._

### `"keys_sorted_of sorts numeric keys"`

> test "keys_sorted_of sorts numeric keys"

_Undocumented._

### `"values_sorted_of sorts numeric values"`

> test "values_sorted_of sorts numeric values"

_Undocumented._

### `"filter_keys_contains finds substrings"`

> test "filter_keys_contains finds substrings"

_Undocumented._

### `"filter_keys_contains on string maps"`

> test "filter_keys_contains on string maps"

_Undocumented._

### `"filter_keys_startswith filters by prefix"`

> test "filter_keys_startswith filters by prefix"

_Undocumented._

### `"filter_values_contains filters by string value"`

> test "filter_values_contains filters by string value"

_Undocumented._

### `"filter_values_contains with int keys"`

> test "filter_values_contains with int keys"

_Undocumented._

### `"count_true counts true values"`

> test "count_true counts true values"

_Undocumented._

### `"count_false counts false values"`

> test "count_false counts false values"

_Undocumented._

### `"map_size counts generic entries"`

> test "map_size counts generic entries"

_Undocumented._

### `"map_is_empty detects an empty map"`

> test "map_is_empty detects an empty map"

_Undocumented._

### `"map_has_key queries a key"`

> test "map_has_key queries a key"

_Undocumented._

### `"map_get_or returns the value or the fallback"`

> test "map_get_or returns the value or the fallback"

_Undocumented._

### `"map_keys returns every key"`

> test "map_keys returns every key"

_Undocumented._

### `"map_values returns every value"`

> test "map_values returns every value"

_Undocumented._

### `"map_get_or reads an entry after put"`

> test "map_get_or reads an entry after put"

_Undocumented._

### `"map_remove deletes one entry"`

> test "map_remove deletes one entry"

_Undocumented._

### `"map_clear empties the map"`

> test "map_clear empties the map"

_Undocumented._

### `"map_len_str_int counts the entries"`

> test "map_len_str_int counts the entries"

_Undocumented._

### `"map_merge combines two maps"`

> test "map_merge combines two maps"

_Undocumented._

### `"map_merge_all combines every map"`

> test "map_merge_all combines every map"

_Undocumented._

### `"map_from_lists builds from parallel lists"`

> test "map_from_lists builds from parallel lists"

_Undocumented._

### `"from_pairs builds from pairs"`

> test "from_pairs builds from pairs"

_Undocumented._

### `"size_ss delegates to the method"`

> test "size_ss delegates to the method"

_Undocumented._

### `"has_key_ss delegates to the method"`

> test "has_key_ss delegates to the method"

_Undocumented._

### `"get_or_ss delegates to the method"`

> test "get_or_ss delegates to the method"

_Undocumented._

### `"get_safe_ss wraps the value"`

> test "get_safe_ss wraps the value"

_Undocumented._

### `"clear method empties the map"`

> test "clear method empties the map"

_Undocumented._

### `"keys_sorted_ss sorts alphabetically"`

> test "keys_sorted_ss sorts alphabetically"

_Undocumented._

### `"clone_ss copies the map"`

> test "clone_ss copies the map"

_Undocumented._

### `"size_sf delegates to the method"`

> test "size_sf delegates to the method"

_Undocumented._

### `"sum_values_sf adds the values"`

> test "sum_values_sf adds the values"

_Undocumented._

### `"max_value_sf returns the largest"`

> test "max_value_sf returns the largest"

_Undocumented._

### `"size_ii delegates to the method"`

> test "size_ii delegates to the method"

_Undocumented._

### `"get_or_ii delegates to the method"`

> test "get_or_ii delegates to the method"

_Undocumented._

### `"keys_sorted_ii sorts the keys"`

> test "keys_sorted_ii sorts the keys"

_Undocumented._

### `"sum_values_ii adds the values"`

> test "sum_values_ii adds the values"

_Undocumented._

### `"size_is delegates to the method"`

> test "size_is delegates to the method"

_Undocumented._

### `"get_or_is delegates to the method"`

> test "get_or_is delegates to the method"

_Undocumented._

### `"values_sorted_is sorts the values"`

> test "values_sorted_is sorts the values"

_Undocumented._

### `"size_sb delegates to the method"`

> test "size_sb delegates to the method"

_Undocumented._

### `"count_true_sb counts the true values"`

> test "count_true_sb counts the true values"

_Undocumented._

### `"merge keeps the right value"`

> test "merge keeps the right value"

_Undocumented._

### `"merge_keep_left keeps the left value"`

> test "merge_keep_left keeps the left value"

_Undocumented._

### `"merge_ss combines string maps"`

> test "merge_ss combines string maps"

_Undocumented._

### `"merge_ii combines int maps"`

> test "merge_ii combines int maps"

_Undocumented._

### `"merge_sb combines bool maps"`

> test "merge_sb combines bool maps"

_Undocumented._

### `"from_lists_ii builds from int lists"`

> test "from_lists_ii builds from int lists"

_Undocumented._

### `"from_lists_sf builds from float lists"`

> test "from_lists_sf builds from float lists"

_Undocumented._

### `"values_in_range module wrapper"`

> test "values_in_range module wrapper"

_Undocumented._

### `"filter_keys_contains module wrapper"`

> test "filter_keys_contains module wrapper"

_Undocumented._

### `"filter_keys_startswith module wrapper"`

> test "filter_keys_startswith module wrapper"

_Undocumented._

### `"map_values_double module wrapper"`

> test "map_values_double module wrapper"

_Undocumented._

### `"get_or module wrapper"`

> test "get_or module wrapper"

_Undocumented._

### `"put method inserts an entry"`

> test "put method inserts an entry"

_Undocumented._

### `"remove module wrapper"`

> test "remove module wrapper"

_Undocumented._

### `"update module wrapper"`

> test "update module wrapper"

_Undocumented._

### `"keys module wrapper"`

> test "keys module wrapper"

_Undocumented._

### `"is_empty module wrapper"`

> test "is_empty module wrapper"

_Undocumented._

### `"size module wrapper"`

> test "size module wrapper"

_Undocumented._

### `"has_key module wrapper"`

> test "has_key module wrapper"

_Undocumented._

### `"value_gt_one is a reusable predicate"`

> test "value_gt_one is a reusable predicate"

_Undocumented._

### `"keys_sorted sorts float keys"`

> test "keys_sorted sorts float keys"

_Undocumented._

### `"keys_sorted sorts i64 keys"`

> test "keys_sorted sorts i64 keys"

_Undocumented._

### `"keys_sorted sorts i32 keys"`

> test "keys_sorted sorts i32 keys"

_Undocumented._

### `"values_sorted sorts float values"`

> test "values_sorted sorts float values"

_Undocumented._

### `"count_true on an int-keyed map"`

> test "count_true on an int-keyed map"

_Undocumented._

### `"count_false on an int-keyed map"`

> test "count_false on an int-keyed map"

_Undocumented._

### `"map_filter_values_contains infers K"`

> test "map_filter_values_contains infers K"

_Undocumented._

### `"keys_sorted_of sorts string keys"`

> test "keys_sorted_of sorts string keys"

_Undocumented._

### `"values_sorted_of sorts string values"`

> test "values_sorted_of sorts string values"

_Undocumented._

### `"_sort_strings sorts a copy"`

> test "_sort_strings sorts a copy"

_Undocumented._

### `"_atlas_sort_i32_in_place sorts in place"`

> test "_atlas_sort_i32_in_place sorts in place"

_Undocumented._

### `"_atlas_sort_f32_in_place sorts in place"`

> test "_atlas_sort_f32_in_place sorts in place"

_Undocumented._

### `"_atlas_sort_strings_in_place sorts in place"`

> test "_atlas_sort_strings_in_place sorts in place"

_Undocumented._

### `"values_sorted_sf sorts float values"`

> test "values_sorted_sf sorts float values"

_Undocumented._

### `"keys_sorted_sf sorts string keys"`

> test "keys_sorted_sf sorts string keys"

_Undocumented._

### `"keys_sorted_sb sorts string keys"`

> test "keys_sorted_sb sorts string keys"

_Undocumented._

### `"keys_sorted_is sorts int keys"`

> test "keys_sorted_is sorts int keys"

_Undocumented._

### `"values_sorted_ii sorts int values"`

> test "values_sorted_ii sorts int values"

_Undocumented._

### `"values_sorted_ss sorts string values"`

> test "values_sorted_ss sorts string values"

_Undocumented._

### `"is_empty_sf delegates to the method"`

> test "is_empty_sf delegates to the method"

_Undocumented._

### `"values_ss returns every value"`

> test "values_ss returns every value"

_Undocumented._

### `"keys_sb returns every key"`

> test "keys_sb returns every key"

_Undocumented._

### `"clone_is copies the map"`

> test "clone_is copies the map"

_Undocumented._

### `"from_lists_ss builds from string lists"`

> test "from_lists_ss builds from string lists"

_Undocumented._

### `"merge_sf combines float maps"`

> test "merge_sf combines float maps"

_Undocumented._

### `"count_false_sb counts the false values"`

> test "count_false_sb counts the false values"

_Undocumented._

### `"to_keys_list is an alias of keys"`

> test "to_keys_list is an alias of keys"

_Undocumented._

