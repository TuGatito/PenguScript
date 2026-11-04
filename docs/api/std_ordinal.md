# std.ordinal

> Source: `std/ordinal.pengu`

std/ordinal.pengu — CC-backed generic containers.

These types are additive; the existing `list`, `map`, `Set` and `SetString`
APIs are untouched.

- `LinkedList of T` → CC `list`
- `UnorderedSet of T` → CC `set`
- `OrderedSet of T` → CC `oset`
- `OrderedMap of K and V` → CC `omap`

The compiler monomorphizes each instantiation, so `T`/`K`/`V` can be any
value type (including strings and user runes).  Elements are stored by
bytes; the containers never clone or free the payloads they reference.
Call `release` on the handle; iteration helpers return an owned `list`.

UnorderedSet hashes/compares `string` by content and other built-ins by
value. Other types use a bytewise fallback (suitable for POD without
padding). OrderedSet/OrderedMap likewise order built-in keys and fall back
to bytewise order for user types.

---

### `ccx_ll_new`

> **ccx_ll_new**(elem_size: int, kind: int) -> ref to void

 --- C bridges ------------------------------------------------------------

### `ccx_ll_push_back`

> **ccx_ll_push_back**(h: ref to void, value: ref to void) -> void

_Undocumented._

### `ccx_ll_push_front`

> **ccx_ll_push_front**(h: ref to void, value: ref to void) -> void

_Undocumented._

### `ccx_ll_pop_front_into`

> **ccx_ll_pop_front_into**(h: ref to void, out: ref to void, elem_size: int) -> void

_Undocumented._

### `ccx_ll_items_into`

> **ccx_ll_items_into**(h: ref to void, out: ref to void, elem_size: int) -> void

_Undocumented._

### `ccx_ll_len`

> **ccx_ll_len**(h: ref to void) -> int

_Undocumented._

### `ccx_ll_clear`

> **ccx_ll_clear**(h: ref to void) -> void

_Undocumented._

### `ccx_ll_free`

> **ccx_ll_free**(h: ref to void) -> void

_Undocumented._

### `ccx_uset_new`

> **ccx_uset_new**(key_size: int, kind: int) -> ref to void

_Undocumented._

### `ccx_uset_add`

> **ccx_uset_add**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_uset_has`

> **ccx_uset_has**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_uset_remove`

> **ccx_uset_remove**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_uset_items_into`

> **ccx_uset_items_into**(h: ref to void, out: ref to void, key_size: int) -> void

_Undocumented._

### `ccx_uset_len`

> **ccx_uset_len**(h: ref to void) -> int

_Undocumented._

### `ccx_uset_clear`

> **ccx_uset_clear**(h: ref to void) -> void

_Undocumented._

### `ccx_uset_free`

> **ccx_uset_free**(h: ref to void) -> void

_Undocumented._

### `ccx_oset_new`

> **ccx_oset_new**(key_size: int, kind: int) -> ref to void

_Undocumented._

### `ccx_oset_add`

> **ccx_oset_add**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_oset_has`

> **ccx_oset_has**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_oset_remove`

> **ccx_oset_remove**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_oset_items_into`

> **ccx_oset_items_into**(h: ref to void, out: ref to void, key_size: int) -> void

_Undocumented._

### `ccx_oset_len`

> **ccx_oset_len**(h: ref to void) -> int

_Undocumented._

### `ccx_oset_clear`

> **ccx_oset_clear**(h: ref to void) -> void

_Undocumented._

### `ccx_oset_free`

> **ccx_oset_free**(h: ref to void) -> void

_Undocumented._

### `ccx_omap_new`

> **ccx_omap_new**(key_size: int, val_size: int, kind: int) -> ref to void

_Undocumented._

### `ccx_omap_put`

> **ccx_omap_put**(h: ref to void, key: ref to void, value: ref to void) -> bool

_Undocumented._

### `ccx_omap_has`

> **ccx_omap_has**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_omap_remove`

> **ccx_omap_remove**(h: ref to void, key: ref to void) -> bool

_Undocumented._

### `ccx_omap_get_into`

> **ccx_omap_get_into**(h: ref to void, key: ref to void, out: ref to void, val_size: int) -> void

_Undocumented._

### `ccx_omap_keys_into`

> **ccx_omap_keys_into**(h: ref to void, out: ref to void, key_size: int) -> void

_Undocumented._

### `ccx_omap_values_into`

> **ccx_omap_values_into**(h: ref to void, out: ref to void, val_size: int) -> void

_Undocumented._

### `ccx_omap_len`

> **ccx_omap_len**(h: ref to void) -> int

_Undocumented._

### `ccx_omap_clear`

> **ccx_omap_clear**(h: ref to void) -> void

_Undocumented._

### `ccx_omap_free`

> **ccx_omap_free**(h: ref to void) -> void

_Undocumented._

### `cc_type_kind`

> **cc_type_kind**() -> int

 Constante de tipo para el descriptor CC; el codegen la sustituye por una
 constante según `T` (0 entero, 1 string, 2 float, 9 bytes).

### `LinkedList`

> rune LinkedList

```pengu
    _handle as ref to void
```

 --- Types ----------------------------------------------------------------

### `UnorderedSet`

> rune UnorderedSet

```pengu
    _handle as ref to void
```

_Undocumented._

### `OrderedSet`

> rune OrderedSet

```pengu
    _handle as ref to void
```

_Undocumented._

### `OrderedMap`

> rune OrderedMap

```pengu
    _handle as ref to void
```

_Undocumented._

### `new_linked_list`

> **new_linked_list**() -> LinkedList__T

_Undocumented._

### `new_unordered_set`

> **new_unordered_set**() -> UnorderedSet__T

_Undocumented._

### `new_ordered_set`

> **new_ordered_set**() -> OrderedSet__T

_Undocumented._

### `new_ordered_map`

> **new_ordered_map**() -> OrderedMap__K__V

_Undocumented._

### `push_back`

> **push_back**(value: T) -> void

 Appends `value` at the back.

### `push_front`

> **push_front**(value: T) -> void

 Adds `value` at the front.

### `pop_front`

> **pop_front**() -> maybe T

 Removes and returns the front value, or `maybe none`.

### `size`

> **size**() -> int

 Number of elements.

### `items`

> **items**() -> list of T

 Owned list copy, front to back.

### `clear`

> **clear**() -> void

_Undocumented._

### `release`

> **release**() -> void

 Releases the CC handle. The receiver is unusable afterwards.

### `add`

> **add**(value: T) -> bool

_Undocumented._

### `has`

> **has**(value: T) -> bool

_Undocumented._

### `remove`

> **remove**(value: T) -> bool

_Undocumented._

### `put`

> **put**(key: K, value: V) -> bool

_Undocumented._

### `get`

> **get**(key: K) -> maybe V

_Undocumented._

### `keys`

> **keys**() -> list of K

 Keys in ascending order.

### `values`

> **values**() -> list of V

 Values in ascending key order.

