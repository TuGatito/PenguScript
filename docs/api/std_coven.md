# std.coven

> Source: `std/coven.pengu`

std/coven.pengu — unique-element collections: the legacy concrete sets
(`SetString`, `SetInt`) and the generic `Set of T`.

A set stores each element at most once and answers membership in average
O(1). All three types share the same core: a rune with a single
`items as map of ... to int` field, where the elements are the map keys.

- `SetString` holds `string` elements (legacy 0.14.x API).
- `SetInt` holds `int` elements directly as the `map of int to int` key
  (the 0.14.x decimal-string key was replaced; legacy 0.14.x API name).
- `Set of T` is the generic set: `items as map of T to int`, so `T` may be
  any hashable type — every integer width (`int`, `i8`..`i64`, `u8`..`u64`,
  `byte`, `usize`, `isize`), `float`/`f32`/`f64`, `char`, `bool`, `string`
  or a `rune ... derive Par, Vinculum`. The backing map enforces the
  `Vinculum` requirement when the set is instantiated.

`SetString` and `SetInt` keep every name, signature and observable result of
the 0.14.x line; new code should prefer `Set of T`.

## Example
```pengu
import std.coven
import std.spark

weave main into int:
    var ids as coven.Set of int is calling coven.new_int_set
    calling ids.add with 7
    calling ids.add with 7              # duplicate: no-op
    var names as coven.Set of string is calling coven.new_string_set
    calling names.add with "ada"
    var total as int is (calling ids.len) + (calling names.len)
    calling spark.println with "size={total}"
    defer banish ids.items
    defer banish names.items
    return 0
```

## Memory
A set **borrows** the string elements it stores. `add` copies the
`PenguString` header into the backing map but never the characters it points
at: under ABI v3 a runtime container "never clones on store and never recurses
on release" (`pengu_runtime.h`). An element passed to `add` must therefore
outlive the set. Handing `add` a temporary and then releasing it leaves the
set holding a dangling key, and a later `contains` reads freed memory -
exactly the lifetime rule `std.scrolls` documents for its views.

That same rule is what makes `banish s.items` a *complete* release: the map
owns only its own entry buffers.

Call `add_owned` when the set must own the element instead: it stores a
private copy, so the caller may release its own string immediately. Borrowed
and owned elements may be mixed in one set - every stored key carries its own
`is_owned` flag - and `release` frees exactly the owned ones before freeing
the map:

```pengu
var s as SetString is calling new_set_string
var src as string is "ada"
var tmp as string is calling src.upper
calling s.add_owned with tmp      # the set owns a private copy
banish tmp                        # safe: the set's copy survives
calling s.release                 # frees the owned copies, then the map
```

Release a set built with `add` using `banish s.items`; release one that used
`add_owned` (or `clone_owned`) with `release`. Calling `banish s.items` on a
set that owns copies frees the map entries but leaks the copies. `SetInt` and
`Set of int` store plain `int` keys, so they own nothing and need no
`add_owned`/`release`.

A set returned by `union`, `intersect`, `difference`,
`symmetric_difference` or `filter_*` **borrows from `self` and `other`**: the
result is a fresh map, but its keys are the same headers, so both inputs must
outlive it. `clone_owned` is the way to obtain a set that owns its own keys.
`SetInt.to_set_string` is the one exception: it mints a fresh key per element,
hands that buffer to the result (`_put_owned`) and therefore returns a set
that **owns its keys** - release it with `release`, never `banish t.items`.

Every constructor (`new_set_string`, `new_set_int`, `make_set shard T`,
`from_items_set shard T` and the nine concrete generic constructors) returns a
fresh set owned by the caller. Methods that answer with a new set (`union`,
`intersect`, `difference`, `symmetric_difference`, `clone`, `filter_*`)
allocate it for the caller; methods that answer with a `list` (`to_list`,
`to_list_int`) allocate that list. Release a returned `list` with `banish`, and
never release a set received as a parameter.

A set value is a rune, so the compiler emits no cleanup entry point for it:
`banish s` fails at the C stage with an implicit declaration of
`_pengu_cleanup_Set_<T>`. To release a set explicitly, free its backing map
with `defer banish s.items`; the compiler-owned temporary lists and strings
returned by the methods are released the usual way.

## Design notes
- **No `where` on a rune.** `rune_decl` has no `where` clause, so
  `rune Set shard T` cannot spell `where T: Vinculum`. The requirement is
  enforced by the backing field `items as map of T to int`, which only
  instantiates for types implementing `Vinculum`.
- **Generic bodies are self-contained.** When a method of a generic rune
  calls another method of that same rune, the compiler emits the
  unspecialised `_T` template and the C compilation fails. Every method below
  therefore reaches the `items` map of the receiver and of its value
  parameters directly and never calls another `Set` method.
- **No generic `ritual` constructor.** A type-qualified generic ritual
  (`Set.empty of T`) is accepted by the checker but miscompiles as soon as the
  bundle holds more than one `Set of T` specialisation: the C compiler stops
  with an invalid-initializer error at the second call site. That is always
  the case here, because these very `test` blocks instantiate `Set of
  string`, `Set of float` and `Set of _TestPlayer`. `calling Set.empty` alone
  cannot infer `T` (`E0005`), and bare `Set.empty` is deliberately NOT
  offered. Element types are created with the generic module functions
  `make_set shard T` / `from_items_set shard T with xs`, which keep working
  with several specialisations, or with the concrete constructors
  (`new_int_set`, `new_string_set`, `new_float_set`, `new_bool_set`,
  `new_char_set`, `new_i64_set`, `new_u64_set`, `new_usize_set`,
  `new_isize_set`). `T` must still be named at the call site
  (`calling make_set of int`).
- **Why `make_set` and not `new_set`.** A generic function specialisation is
  mangled as `<name>_<element type>`, so `new_set of string` and the legacy
  `new_set_string` collapse onto the same C symbol. Under the current
  compiler this no longer fails with `E0005`; instead one body silently wins
  for both call sites (verified in the emitted C), which is the same
  misbinding hazard with a quieter symptom. The collision-free name
  `make_set` is used instead; `from_items_set` mangles to
  `from_items_set_<type>`, which collides with nothing.
- **Element types.** `Set of T` was verified for `int`, `i8`..`i64`,
  `u8`..`u64`, `byte`, `usize`, `isize`, `float`, `f32`, `f64`, `char`,
  `bool`, `string` and a user `rune ... derive Par, Vinculum`; the element is
  stored as the map key, so a narrow width is not widened to `int`. The one
  behavioural sharp edge is `Set of float`: keys compare by bit pattern, so
  `0.0` and `-0.0` are two distinct elements even though `0.0 == -0.0`.
- **Legacy storage.** Both `SetInt` and the generic `Set of int` store the
  `int` itself as the map key, so both deduplicate identically and neither
  allocates a key payload per element. `SetInt` keeps its 0.14.x method set;
  the generic `Set of int` is the supported spelling for new code.
- **`is_empty`** reads the backing map (`calling self->items.is_empty`); the
  equivalent `(calling self->items.len) == 0` is used where a map method is not
  available.

## Migration
2.1.0 added the generic `Set of T`, its `enchanting` and the constructors
`make_set shard T`, `from_items_set shard T`, `new_int_set`, `new_string_set`,
`new_float_set`, `new_bool_set` and `new_char_set`. 2.2.0 adds the concrete
constructors `new_i64_set`, `new_u64_set`, `new_usize_set` and
`new_isize_set`, and records the verified element-type matrix. Nothing is
removed and no signature changes: `SetString` and `SetInt` remain fully
supported and keep their exact 0.14.x/2.0.0 behaviour. The generic type has no
`Set.empty` ritual (type-qualified generic rituals miscompile); use
`make_set of T`. New code should use `Set of T`; the legacy types stay for
programs written against the older API.

---

### `COVEN_VERSION`

> **COVEN_VERSION** : string

 Revision of the `coven` API.

 Deliberately not the toolchain version: it moves only when a `coven`
 signature changes. 2.1.0 added the generic `Set of T`; 2.2.0 adds the wide
 integer constructors (`new_i64_set`, `new_u64_set`, `new_usize_set`,
 `new_isize_set`).

### `coven_copy_string`

> **coven_copy_string**(s: string) -> string

 Returns a fresh owned copy of `s`.

 ## Memoria
 Allocates one owned buffer; release it with `banish`. `s` is borrowed and
 never freed.

### `_coven_release_string_set`

> **_coven_release_string_set**(m: ref to map of string to int) -> void

 Frees every key the map owns, and then the map itself.

 ## Memoria
 `pengu_banish_string` is a no-op for a borrowed key (`is_owned == 0`) and
 frees a copied one (`is_owned == 1`), so a set that mixes `add` and
 `add_owned` releases each element exactly once.

### `_coven_free_owned_keys`

> **_coven_free_owned_keys**(m: ref to map of string to int) -> void

 Frees every key the map owns, leaving the map's entries in place.

### `_coven_put_borrowed`

> **_coven_put_borrowed**(m: ref to map of string to int, item: string) -> void

 Inserts `item` into the map as a **non-owning** key: the set borrows it.

 ## Motivo
 `pengu_map_put` copies the caller's `PenguString` header verbatim, so a
 borrowed key arrives with `is_owned == 1` whenever the *caller* owns the
 buffer. That makes "may the set free this key?" indistinguishable from "does
 anybody own this view?", and a set that releases its own copies would free a
 caller-owned buffer as well (a double free once the caller banishes it).
 Clearing `is_owned` on the stored header reserves `is_owned == 1` *inside the
 map* to mean "the set owns this copy", which is the invariant
 `_coven_free_owned_keys` and `_coven_remove_string_key` rely on. The caller's
 own `PenguString` is untouched: only the map's private header is rewritten.

### `_coven_remove_string_key`

> **_coven_remove_string_key**(m: ref to map of string to int, item: string) -> bool

 Removes `item`, freeing the owned key buffer when the set owned one.

 ## Motivo
 The owned buffer must be captured *before* `pengu_map_remove` frees the entry
 holding the pointer to it, and the removal itself has to hash the caller's
 still-intact `item` rather than the key that is being released.

### `SetString`

> rune SetString

```pengu
    items as map of string to int
```

 A set of unique `string` elements: inserting a string already present is a
 no-op. Create one with `new_set_string` (or `empty_set_string`) and use the
 `SetString` methods (`add`, `contains`, `remove`, `len`, `clear`,
 `is_empty`, the set algebra and the `filter_*` helpers).

 @deprecated Use the generic `Set of string` instead.

 ## Example
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "ada"
 calling s.add with "ada"          # no-op
 var n as int is calling s.len      # 1
 ```

 ## Memoria
 The rune owns its backing map but **borrows** the string elements stored by
 `add`. Release a borrowing set with `banish s.items`; release one that used
 `add_owned` or `clone_owned` with `release`. A set received as a parameter is
 borrowed and never released by these methods.

### `SetInt`

> rune SetInt

```pengu
    items as map of int to int
```

 A set of unique `int` elements with the same behaviour as `SetString`.
 Values are stored directly as the `int` map key (no per-element string),
 so adding or removing an element allocates only the map entry itself.
 Create one with `new_set_int` (or `empty_set_int`) and use the `SetInt`
 methods.

 @deprecated Use the generic `Set of int` instead.

 ## Example
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 7
 calling s.add with 7              # no-op
 var n as int is calling s.len      # 1
 ```

 ## Memoria
 The rune owns its backing map. Release it with `banish s.items`; a set
 received as a parameter is borrowed and never released by these methods.

### `Set`

> rune Set

```pengu
    items as map of T to int
```

 A generic set of unique `T` elements, backed by `map of T to int`.

 `T` must implement `Vinculum` (the map-key contract); the backing field
 enforces it when the set is instantiated. Every integer width (`int`,
 `i8`..`i64`, `u8`..`u64`, `byte`, `usize`, `isize`), `float`/`f32`/`f64`,
 `char`, `bool`, `string` and any `rune ... derive Par, Vinculum` are valid.

 Create one with the generic module functions `make_set of T` /
 `from_items_set of T with xs`, or with the concrete constructors `new_int_set`,
 `new_string_set`, `new_float_set`, `new_bool_set`, `new_char_set`,
 `new_i64_set`, `new_u64_set`, `new_usize_set` and `new_isize_set`. There is
 no `Set.empty` ritual (see the module design notes).

 ## Example
 ```pengu
 var s as Set of int is calling make_set of int
 calling s.add with 7
 calling s.add with 7              # no-op
 var n as int is calling s.len      # 1
 ```

 ## Memoria
 The rune owns its backing map but **borrows** every element stored by `add`,
 exactly like `SetString`: only the key header is copied, never the payload a
 `string`, `list` or heap-owning rune element points at. An element must
 outlive the set. Release the set with `banish s.items`; a set received as a
 parameter is borrowed and never released by these methods.

 There is no `add_owned` for `Set of T`. A generic deep copy would have to call
 the `Imago` clone callback of `T`, and `Imago` deliberately adds no callable
 `.clone()` method to a type (LANGUAGE.md, derived concepts) - it only emits a
 C-level helper whose name depends on the monomorphized `T`. Until the language
 exposes a callable clone concept, use `SetString.add_owned` /
 `SetString.clone_owned` when a set of strings must own its elements, or copy
 each element yourself before inserting it.

### `new_set_string`

> **new_set_string**() -> SetString

 Builds a new, empty `SetString` ready to receive `add` calls.

 ## Parámetros
 - None: the backing map is created empty.

 ## Retorno
 An owned empty `SetString`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "a"
 ```

### `new_set_int`

> **new_set_int**() -> SetInt

 Builds a new, empty `SetInt` ready to receive `add` calls.

 ## Parámetros
 - None: the backing map is created empty.

 ## Retorno
 An owned empty `SetInt`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 1
 ```

### `empty_set_string`

> **empty_set_string**() -> SetString

 Creates an empty `SetString`. Alias of `new_set_string`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `SetString`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as SetString is calling empty_set_string
 ```

### `empty_set_int`

> **empty_set_int**() -> SetInt

 Creates an empty `SetInt`. Alias of `new_set_int`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `SetInt`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling empty_set_int
 ```

### `from_list_string`

> **from_list_string**(items: list of string) -> SetString

 Builds a `SetString` from a list of strings, automatically deduplicating
 items.

 ## Parámetros
 - `items`: the source list of strings. It is borrowed and never modified.

 ## Retorno
 An owned `SetString` holding each distinct element of `items` once. Release
 its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var xs as list of string is ["a", "a", "b"]
 var s as SetString is calling from_list_string with xs
 ```

### `from_list_int`

> **from_list_int**(items: list of int) -> SetInt

 Builds a `SetInt` from a list of ints, automatically deduplicating items.

 ## Parámetros
 - `items`: the source list of integers. It is borrowed and never modified.

 ## Retorno
 An owned `SetInt` holding each distinct element of `items` once. Release its
 backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [1, 1, 2]
 var s as SetInt is calling from_list_int with xs
 ```

### `empty`

> **empty**() -> SetString

 Creates an empty `SetString`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `SetString`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as SetString is calling SetString.empty
 ```

### `from_items`

> **from_items**(items: list of string) -> SetString

 Builds a `SetString` from a list of strings.

 ## Parámetros
 - `items`: the source list of strings; borrowed, never modified.

 ## Retorno
 An owned `SetString` with each distinct element once. Release its backing
 map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var xs as list of string is ["a", "b"]
 var s as SetString is calling SetString.from_items with xs
 ```

### `add`

> **add**(item: string) -> void

 Inserts `item` into the set, **borrowing** it. Inserting a string already
 present is a no-op, because a set stores each element at most once.

 ## Parámetros
 - `item`: the string to insert. Only its header is copied into the backing
   map; the characters stay owned by the caller.

 ## Retorno
 Nothing; the method returns `void` and mutates the receiver in place.

 ## Memoria
 **`item` must outlive the set.** Only the `PenguString` header is copied;
 the character buffer is aliased, so releasing `item` while the set still
 holds it leaves a dangling key and a later `contains` reads freed memory.
 Use `add_owned` when the set must own the element.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "ada"
 ```

### `add_owned`

> **add_owned**(item: string) -> void

 Inserts a **private copy** of `item`, so the set owns the element and the
 caller may release its own string immediately. Inserting a string already
 present is a no-op.

 ## Parámetros
 - `item`: the string to copy into the set; borrowed for the duration of
   the call only.

 ## Retorno
 Nothing; the method returns `void` and mutates the receiver in place.

 ## Memoria
 Allocates one owned copy per new element. A set that used `add_owned` (or
 `clone_owned`) must be released with `release`, not `banish s.items`, or
 the copies leak.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 var src as string is "ada"
 var tmp as string is calling src.upper
 calling s.add_owned with tmp
 banish tmp                        # the set's copy survives
 ```

### `_put_owned`

> **_put_owned**(item: string) -> void

 Inserts `item` **taking ownership** of its character buffer, without
 copying it. The set owns `item` afterwards; the caller must not release
 it.

 ## Parámetros
 - `item`: a freshly allocated owning string whose buffer is transferred to
   the set. Only call this with a string the caller does not keep.

 ## Retorno
 Nothing; the method returns `void` and mutates the receiver in place.

 ## Motivo
 `pengu_map_put` copies the key header verbatim, `is_owned` included, so an
 interpolated string reaches the backing map still marked as owned. `add`
 deliberately clears that flag (`_coven_put_borrowed`) because it only
 borrows; `_put_owned` is the inverse bridge for the one internal caller
 that hands the map a buffer nobody else holds, and it is what lets
 `release` free that copy later. It allocates nothing, so - unlike
 `add_owned` - it pays no second copy.

 ## Memoria
 The set owns `item` afterwards; releasing `item` leaves a dangling key and
 makes `release` double-free. A set filled through `_put_owned` must be
 released with `release`, never `banish s.items`.

 Precondition: none. A key already present is dropped first (releasing it
 when the set owned it), because `pengu_map_put` overwrites only the
 *value* on a match and would otherwise leak the transferred buffer.
 `SetInt.to_set_string` mints one distinct key per distinct `int` and never
 hits that path, so the extra lookup costs nothing in practice; it is there
 so the helper cannot be reused unsafely.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 let key as string is "ada"
 var tmp as string is "{key}"
 calling s._put_owned with tmp
 # no banish tmp: the set owns the buffer now
 ```

### `contains`

> **contains**(item: string) -> bool

 Returns true when `item` is currently a member of the set.

 ## Parámetros
 - `item`: the string to look up; borrowed, never modified.

 ## Retorno
 `true` when the set holds `item`, `false` otherwise. Reads only.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "ada"
 var found as bool is calling s.contains with "ada"    # true
 ```

### `remove`

> **remove**(item: string) -> bool

 Removes `item` from the set. Returns true when it was present (and has
 been removed); returns false when the set did not contain it.

 ## Parámetros
 - `item`: the string to remove; borrowed, never modified.

 ## Retorno
 `true` when the element was present and has been removed, `false` when it
 was absent.

 ## Memoria
 Frees the element's own copy when the set owned one (an element inserted
 with `add_owned` or `clone_owned`); a borrowed element is left to its
 owner.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "ada"
 var removed as bool is calling s.remove with "ada"    # true
 ```

### `len`

> **len**() -> int

 Returns the number of distinct elements currently stored in the set.

 ## Parámetros
 - None: the receiver is measured.

 ## Retorno
 The element count as an `int`. Reads only.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "ada"
 var n as int is calling s.len    # 1
 ```

### `clear`

> **clear**() -> void

 Removes every element, leaving the set empty.

 ## Parámetros
 - None.

 ## Retorno
 Nothing; the method returns `void` and mutates the receiver in place.

 ## Memoria
 Frees the owned copy of every element the set owns (those inserted with
 `add_owned` or `clone_owned`); borrowed elements are left to their owners.
 The set itself stays usable and its backing map stays allocated.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "ada"
 calling s.clear
 ```

### `release`

> **release**() -> void

 Frees the whole set: every element the set owns, and then the backing map.

 ## Parámetros
 - None.

 ## Retorno
 Nothing; the method returns `void` and consumes the receiver. Do not use
 the set again after calling it.

 ## Motivo
 `banish s.items` frees only the map's entry buffers, which is complete for a
 set built with the borrowing `add`. A set that owns copies needs those
 buffers released too, so this method walks the entries first and lets
 `pengu_banish_string` free exactly the owned ones.

 ## Memoria
 Releases every owned element buffer, then the map. Equivalent to `clear`
 followed by `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 var src as string is "ada"
 var tmp as string is calling src.upper
 calling s.add_owned with tmp
 banish tmp
 calling s.release
 ```

### `is_empty`

> **is_empty**() -> bool

 Returns true when the set holds no elements at all.

 ## Parámetros
 - None: the receiver is inspected.

 ## Retorno
 `true` for an empty set, `false` otherwise. Reads only.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 var empty as bool is calling s.is_empty    # true
 ```

### `union`

> **union**(other: SetString) -> SetString

 Returns a fresh `SetString` containing every element present in `self` or
 `other`.

 ## Parámetros
 - `other`: the second set; borrowed, never modified or released.

 ## Retorno
 An owned fresh `SetString`. Release its backing map with `banish u.items`.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "y"
 var u as SetString is calling a.union with b
 ```

### `intersect`

> **intersect**(other: SetString) -> SetString

 Returns a fresh `SetString` containing only elements present in both
 `self` and `other`.

 ## Parámetros
 - `other`: the second set; borrowed, never modified or released.

 ## Retorno
 An owned fresh `SetString`. Release its backing map with `banish i.items`.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "x"
 var i as SetString is calling a.intersect with b
 ```

### `difference`

> **difference**(other: SetString) -> SetString

 Returns a fresh `SetString` with elements present in `self` but absent
 from `other`.

 ## Parámetros
 - `other`: the second set; borrowed, never modified or released.

 ## Retorno
 An owned fresh `SetString`. Release its backing map with `banish d.items`.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 var d as SetString is calling a.difference with b
 ```

### `symmetric_difference`

> **symmetric_difference**(other: SetString) -> SetString

 Returns a fresh `SetString` with elements in either `self` or `other`,
 but not both.

 ## Parámetros
 - `other`: the second set; borrowed, never modified or released.

 ## Retorno
 An owned fresh `SetString`. Release its backing map with `banish x.items`.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "y"
 var x as SetString is calling a.symmetric_difference with b
 ```

### `is_subset`

> **is_subset**(other: SetString) -> bool

 Returns true if every element in `self` is also present in `other`.

 ## Parámetros
 - `other`: the candidate superset; borrowed, never modified.

 ## Retorno
 `true` when `self` is a subset of `other`, `false` otherwise. Reads only.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "x"
 var sub as bool is calling a.is_subset with b    # true
 ```

### `is_superset`

> **is_superset**(other: SetString) -> bool

 Returns true if every element in `other` is also present in `self`.

 ## Parámetros
 - `other`: the candidate subset; borrowed, never modified.

 ## Retorno
 `true` when `self` is a superset of `other`, `false` otherwise. Reads only.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "x"
 var sup as bool is calling a.is_superset with b    # true
 ```

### `is_disjoint`

> **is_disjoint**(other: SetString) -> bool

 Returns true if `self` and `other` have no elements in common.

 ## Parámetros
 - `other`: the second set; borrowed, never modified.

 ## Retorno
 `true` when the sets are disjoint, `false` otherwise. Reads only.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "y"
 var d as bool is calling a.is_disjoint with b    # true
 ```

### `equals`

> **equals**(other: SetString) -> bool

 Returns true if `self` and `other` contain exactly the same set of
 elements.

 ## Parámetros
 - `other`: the set to compare against; borrowed, never modified.

 ## Retorno
 `true` when both sets have the same members, `false` otherwise. Reads
 only; the insertion order is irrelevant.

 ## Ejemplo
 ```pengu
 var a as SetString is calling new_set_string
 var b as SetString is calling new_set_string
 calling a.add with "x"
 calling b.add with "x"
 var same as bool is calling a.equals with b    # true
 ```

### `clone`

> **clone**() -> SetString

 Returns a fresh copy of `self` whose keys are **borrowed** from `self`.

 ## Parámetros
 - None: the receiver is copied.

 ## Retorno
 A fresh `SetString` with its own map; release it with `banish c.items`,
 which is complete because the elements stay owned by `self`.

 ## Memoria
 **`self` must outlive the copy.** The new map holds the same key headers,
 not copies of the characters. Use `clone_owned` for a set that owns its
 own keys.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "x"
 var c as SetString is calling s.clone
 ```

### `clone_owned`

> **clone_owned**() -> SetString

 Returns a fresh copy of `self` that **owns** a private copy of every key,
 so it outlives `self`.

 ## Parámetros
 - None: the receiver is deep-copied.

 ## Retorno
 A fresh `SetString` independent of `self`. Release it with `release`, not
 `banish c.items`, or the copied keys leak.

 ## Memoria
 Allocates one owned copy per element. `self` may be released immediately
 afterwards.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "x"
 var c as SetString is calling s.clone_owned
 calling s.release
 calling c.release
 ```

### `to_list`

> **to_list**() -> list of string

 Returns a fresh list containing all elements of `self` in internal hash
 order.

 ## Parámetros
 - None: the receiver is listed.

 ## Retorno
 An owned fresh `list of string`; release it with `banish`. The order is
 hash order, not insertion order.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "x"
 var xs as list of string is calling s.to_list
 ```

### `to_set_int`

> **to_set_int**() -> SetInt

 Converts this `SetString` to a `SetInt`, parsing each element with
 `std.spark.parse_int`. Elements that cannot be parsed are skipped.

 ## Parámetros
 - None: the receiver is converted.

 ## Retorno
 An owned fresh `SetInt` with the parseable elements. Release its backing
 map with `banish s.items`. `SetInt` keys are plain `int`, so it owns no
 extra element buffer.

 ## Memoria
 Each `spark.parse_int` result is a fresh `maybe int` box; nothing releases
 it automatically, so every box - parseable or not - is banished inside the
 loop. The returned `SetInt` itself only owns its backing map.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "7"
 var ints as SetInt is calling s.to_set_int
 ```

### `filter_starts_with`

> **filter_starts_with**(prefix: string) -> SetString

 Returns a fresh `SetString` containing only elements that start with
 `prefix`.

 ## Parámetros
 - `prefix`: the required prefix; borrowed, never modified.

 ## Retorno
 An owned fresh `SetString` with the matching elements. Release its backing
 map with `banish r.items`.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "alpha"
 var r as SetString is calling s.filter_starts_with with "al"
 ```

### `filter_length_ge`

> **filter_length_ge**(n: int) -> SetString

 Returns a fresh `SetString` containing only elements with string length
 greater than or equal to `n`.

 ## Parámetros
 - `n`: the minimum byte length; elements shorter than `n` are dropped.

 ## Retorno
 An owned fresh `SetString` with the matching elements. Release its backing
 map with `banish r.items`.

 ## Ejemplo
 ```pengu
 var s as SetString is calling new_set_string
 calling s.add with "abc"
 var r as SetString is calling s.filter_length_ge with 3
 ```

### `to_list_int`

> **to_list_int**() -> list of int

 Returns a fresh list containing all parsed integer elements of `self`.

 ## Parámetros
 - None: the receiver is listed.

 ## Retorno
 An owned fresh `list of int`; release it with `banish`. Order is hash
 order, not insertion order.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 7
 var xs as list of int is calling s.to_list_int
 ```

### `sum_ints`

> **sum_ints**() -> int

 Returns the arithmetic sum of all integers in `self`. Returns 0 if empty.

 ## Parámetros
 - None: the receiver is reduced.

 ## Retorno
 The sum as an `int`; the empty set collapses to the identity `0`.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 2
 calling s.add with 3
 var total as int is calling s.sum_ints    # 5
 ```

### `min_int`

> **min_int**() -> int

 Returns the minimum integer in `self`. Returns 0 if empty.

 ## Parámetros
 - None: the receiver is reduced.

 ## Retorno
 The smallest element as an `int`; the empty set collapses to `0`.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 5
 calling s.add with -2
 var lo as int is calling s.min_int    # -2
 ```

### `max_int`

> **max_int**() -> int

 Returns the maximum integer in `self`. Returns 0 if empty.

 ## Parámetros
 - None: the receiver is reduced.

 ## Retorno
 The largest element as an `int`; the empty set collapses to `0`.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 5
 calling s.add with 9
 var hi as int is calling s.max_int    # 9
 ```

### `to_set_string`

> **to_set_string**() -> SetString

 Converts this `SetInt` to an equivalent `SetString` with stringified
 keys.

 ## Parámetros
 - None: the receiver is converted.

 ## Retorno
 An owned fresh `SetString`. Unlike every other set-returning method, this
 one **owns its keys**: each key is a fresh interpolation whose buffer is
 handed to the result, so release it with `release`, **not**
 `banish t.items` (which would leak the key buffers).

 ## Memoria
 One owned key buffer per element. Free them, and then the map, with
 `calling t.release`.

 ## Ejemplo
 ```pengu
 var s as SetInt is calling new_set_int
 calling s.add with 7
 var t as SetString is calling s.to_set_string
 calling t.release
 ```

### `make_set`

> **make_set**() -> Set__T

 Creates an empty `Set of T`.

 `T` is named explicitly at the call site (`calling make_set of int`) because it
 cannot be inferred. Unlike a generic `ritual` constructor, this module
 function keeps working when the bundle holds several `Set of T`
 specialisations.

 ## Parámetros
 - None: the backing map is created empty.

 ## Retorno
 An owned empty `Set of T`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of int is calling make_set of int
 calling s.add with 7
 ```

### `from_items_set`

> **from_items_set**(items: list of T) -> Set__T

 Builds a `Set of T` from a list of `T`, automatically deduplicating items.

 ## Parámetros
 - `items`: the source list; borrowed, never modified. `T` is named at the
   call site.

 ## Retorno
 An owned `Set of T` holding each distinct element of `items` once. Release its
 backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var xs as list of int is [1, 1, 2]
 var s as Set of int is calling from_items_set of int with xs
 ```

### `new_int_set`

> **new_int_set**() -> Set__int

 Creates an empty `Set of int`.

 The concrete constructors spell the element type for the common cases; they
 and the generic module functions (`make_set`, `from_items_set`) are the
 supported way to start a generic set, because a type-qualified generic
 `ritual` constructor miscompiles (see the module design notes).

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of int`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of int is calling new_int_set
 calling s.add with 7
 ```

### `new_string_set`

> **new_string_set**() -> Set__string

 Creates an empty `Set of string`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of string`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of string is calling new_string_set
 calling s.add with "ada"
 ```

### `new_float_set`

> **new_float_set**() -> Set__float

 Creates an empty `Set of float`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of float`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of float is calling new_float_set
 calling s.add with 1.5
 ```

### `new_bool_set`

> **new_bool_set**() -> Set__bool

 Creates an empty `Set of bool`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of bool`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of bool is calling new_bool_set
 calling s.add with true
 ```

### `new_char_set`

> **new_char_set**() -> Set__char

 Creates an empty `Set of char`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of char`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of char is calling new_char_set
 calling s.add with (65 to char)
 ```

### `new_i64_set`

> **new_i64_set**() -> Set__i64

 Creates an empty `Set of i64`.

 The backing map keys on the full 64-bit value, so elements above the `int`
 range are neither truncated nor merged.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of i64`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of i64 is calling new_i64_set
 calling s.add with 5000000000
 ```

### `new_u64_set`

> **new_u64_set**() -> Set__u64

 Creates an empty `Set of u64`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of u64`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of u64 is calling new_u64_set
 calling s.add with 12000000000
 ```

### `new_usize_set`

> **new_usize_set**() -> Set__usize

 Creates an empty `Set of usize`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of usize`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of usize is calling new_usize_set
 calling s.add with 9000000000
 ```

### `new_isize_set`

> **new_isize_set**() -> Set__isize

 Creates an empty `Set of isize`.

 ## Parámetros
 - None.

 ## Retorno
 An owned empty `Set of isize`. Release its backing map with `banish s.items`.

 ## Ejemplo
 ```pengu
 var s as Set of isize is calling new_isize_set
 calling s.add with -9000000000
 ```

### `_expect_coven`

> **_expect_coven**(cond: bool, label: string) -> void

 Test harness: panics with `label` when `cond` is false.

### `_expect_coven_eq_int`

> **_expect_coven_eq_int**(actual: int, expected: int, label: string) -> void

 Test harness: int equality.

### `_expect_coven_eq_string`

> **_expect_coven_eq_string**(actual: string, expected: string, label: string) -> void

 Test harness: string equality.

### `_expect_coven_eq_bool`

> **_expect_coven_eq_bool**(actual: bool, expected: bool, label: string) -> void

 Test harness: bool equality.

### `_TestPlayer`

> rune _TestPlayer

```pengu
    id as int
```

 Test-only value type used to exercise `Set of T` with a user `rune`.

### `"generic set of custom rune deduplicates"`

> test "generic set of custom rune deduplicates"

 The generic module functions `make_set of T` / `from_items_set of T` are the
 supported constructors: unlike a type-qualified generic ritual they keep
 working when the bundle holds several `Set of T` specialisations. See the
 design notes.

### `"make_set of int builds an empty set"`

> test "make_set of int builds an empty set"

_Undocumented._

### `"make_set of string builds an empty set"`

> test "make_set of string builds an empty set"

_Undocumented._

### `"make_set of float builds an empty set"`

> test "make_set of float builds an empty set"

_Undocumented._

### `"from_items_set deduplicates for int and string"`

> test "from_items_set deduplicates for int and string"

_Undocumented._

### `"set_string.add deduplicates elements"`

> test "set_string.add deduplicates elements"

_Undocumented._

### `"set_string.remove reports membership"`

> test "set_string.remove reports membership"

_Undocumented._

### `"set_string.clear empties the set"`

> test "set_string.clear empties the set"

_Undocumented._

### `"set_string.union merges both sets"`

> test "set_string.union merges both sets"

_Undocumented._

### `"set_string.intersect keeps common elements"`

> test "set_string.intersect keeps common elements"

_Undocumented._

### `"set_string.difference keeps only the left side"`

> test "set_string.difference keeps only the left side"

_Undocumented._

### `"set_string.symmetric_difference keeps elements in exactly one set"`

> test "set_string.symmetric_difference keeps elements in exactly one set"

_Undocumented._

### `"set_string.is_subset and is_superset"`

> test "set_string.is_subset and is_superset"

_Undocumented._

### `"set_string.is_disjoint detects shared elements"`

> test "set_string.is_disjoint detects shared elements"

_Undocumented._

### `"set_string.equals compares membership"`

> test "set_string.equals compares membership"

_Undocumented._

### `"set_string.clone is independent"`

> test "set_string.clone is independent"

_Undocumented._

### `"set_string.to_list lists every element"`

> test "set_string.to_list lists every element"

_Undocumented._

### `"set_string.to_set_int parses numeric elements"`

> test "set_string.to_set_int parses numeric elements"

_Undocumented._

### `"set_string.filter_starts_with keeps the prefix"`

> test "set_string.filter_starts_with keeps the prefix"

_Undocumented._

### `"set_string.filter_length_ge keeps long elements"`

> test "set_string.filter_length_ge keeps long elements"

_Undocumented._

### `"empty_set_string and from_list_string deduplicate"`

> test "empty_set_string and from_list_string deduplicate"

_Undocumented._

### `"set_string.from_items builds a set from a list"`

> test "set_string.from_items builds a set from a list"

_Undocumented._

### `"set_string.empty ritual builds an empty set"`

> test "set_string.empty ritual builds an empty set"

_Undocumented._

### `"set_int.add deduplicates elements"`

> test "set_int.add deduplicates elements"

_Undocumented._

### `"set_int.remove and is_empty"`

> test "set_int.remove and is_empty"

_Undocumented._

### `"set_int.union merges both sets"`

> test "set_int.union merges both sets"

_Undocumented._

### `"set_int.intersect and difference"`

> test "set_int.intersect and difference"

_Undocumented._

### `"set_int.symmetric_difference"`

> test "set_int.symmetric_difference"

_Undocumented._

### `"set_int.is_subset is_superset and is_disjoint"`

> test "set_int.is_subset is_superset and is_disjoint"

_Undocumented._

### `"set_int.equals and clone"`

> test "set_int.equals and clone"

_Undocumented._

### `"set_int.to_list_int and sum_ints"`

> test "set_int.to_list_int and sum_ints"

_Undocumented._

### `"set_int.min_int and max_int"`

> test "set_int.min_int and max_int"

_Undocumented._

### `"set_int.to_set_string roundtrips"`

> test "set_int.to_set_string roundtrips"

_Undocumented._

### `"empty_set_int and from_list_int"`

> test "empty_set_int and from_list_int"

_Undocumented._

### `"set_int.from_items builds a set from a list"`

> test "set_int.from_items builds a set from a list"

_Undocumented._

### `"set_int.empty ritual builds an empty set"`

> test "set_int.empty ritual builds an empty set"

_Undocumented._

### `"generic set of int deduplicates and removes"`

> test "generic set of int deduplicates and removes"

_Undocumented._

### `"generic set of int set algebra"`

> test "generic set of int set algebra"

_Undocumented._

### `"generic set of int subset superset disjoint equals clone"`

> test "generic set of int subset superset disjoint equals clone"

_Undocumented._

### `"generic set of string stores and lists strings"`

> test "generic set of string stores and lists strings"

_Undocumented._

### `"generic set of string clear and is_empty"`

> test "generic set of string clear and is_empty"

_Undocumented._

### `"generic set of float stores floats"`

> test "generic set of float stores floats"

_Undocumented._

### `"concrete bool and char constructors build sets"`

> test "concrete bool and char constructors build sets"

_Undocumented._

### `"generic set of i64 keys on the full 64-bit value"`

> test "generic set of i64 keys on the full 64-bit value"

_Undocumented._

### `"new_i64_set and new_u64_set build working sets"`

> test "new_i64_set and new_u64_set build working sets"

_Undocumented._

### `"new_usize_set and new_isize_set handle wide and negative keys"`

> test "new_usize_set and new_isize_set handle wide and negative keys"

_Undocumented._

### `"generic set of usize supports set algebra"`

> test "generic set of usize supports set algebra"

_Undocumented._

### `"from_items_set of isize round-trips through to_list"`

> test "from_items_set of isize round-trips through to_list"

_Undocumented._

### `"narrow integer and byte element types work"`

> test "narrow integer and byte element types work"

_Undocumented._

### `"f32 and f64 element types work"`

> test "f32 and f64 element types work"

_Undocumented._

### `"generic set of float keys 0.0 and -0.0 separately"`

> test "generic set of float keys 0.0 and -0.0 separately"

_Undocumented._

### `"empty string is a valid set element"`

> test "empty string is a valid set element"

_Undocumented._

### `"generic union and intersect deduplicate shared elements"`

> test "generic union and intersect deduplicate shared elements"

_Undocumented._

### `"custom rune elements deduplicate by derived value equality"`

> test "custom rune elements deduplicate by derived value equality"

_Undocumented._

### `"add_owned survives releasing the source string"`

> test "add_owned survives releasing the source string"

_Undocumented._

### `"borrowing add keeps its documented lifetime rule"`

> test "borrowing add keeps its documented lifetime rule"

_Undocumented._

### `"clone_owned outlives the set it came from"`

> test "clone_owned outlives the set it came from"

_Undocumented._

### `"remove and clear free the copies the set owns"`

> test "remove and clear free the copies the set owns"

_Undocumented._

### `"_put_owned replaces a duplicate key without leaking the old buffer"`

> test "_put_owned replaces a duplicate key without leaking the old buffer"

_Undocumented._

### `"coven version is 2.3.0"`

> test "coven version is 2.3.0"

_Undocumented._

