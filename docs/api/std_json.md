# std.json

> Source: `std/json.pengu`

std/json.pengu — strict JSON (RFC 8259): parser, serializer, DOM and JSON Pointer.

`std.json` is the complete JSON implementation for PenguScript: a strict
recursive-descent parser with byte-exact error positions, a serializer whose
float output round-trips, a DOM (`JsonValue`) that preserves object insertion
order, JSON Pointer (RFC 6901), recursive key search, deep merge, validation
without building a DOM, an arena mode for one-shot payloads, and a practical
JSON Schema subset.

It covers everything Python's `json` module does, and adds:
JSON Pointer, `find_key`, `validate` (no DOM), `deep_merge`, `parse_in_arena`
and `validate_schema`. The only deliberate difference is ownership: every
value is explicitly owned, and every query that hands out a subtree returns a
deep copy the caller can `banish`. There is no hidden GC.

## Example: parse, query, free
```pengu
import std.json
import std.spark

weave main into int:
    var parsed as result of JsonValue to JsonError is calling json.parse with "{\"name\":\"pengu\",\"tags\":[1,2]}"
    var root as JsonValue is parsed or:
        calling spark.panic with error.message
        return 1
    defer banish root

    var name as maybe JsonValue is calling root.get with "name"
    var n as JsonValue is name or:
        return 1
    defer banish n
    var text as string is (calling n.as_string) or else ""
    calling spark.println with text                       # pengu

    var second as JsonValue is (calling root.pointer with "/tags/1") or:
        return 1
    defer banish second
    calling spark.println with "{(calling second.as_int) or else 0}"   # 2
    return 0
```

## Ownership (read this once)
- `parse` and `parse_in_arena` return a `JsonValue` that owns every string,
  list and entry below it. `banish root` releases the whole tree (derived
  `Nexus` recurses through `list of JsonValue` and `list of JsonEntry`).
- A query that returns a `JsonValue` (`at`, `get`, `first`, `last`,
  `pointer`, `find_key`, `clone`) returns a **deep copy**. It is independent
  of the source value and must be banished.
- `as_string` returns an owned copy; `as_array`, `as_object`, `values` and
  `entries` return owned deep copies. Release a `list of JsonValue` with
  `free_values`, a `list of JsonEntry` with `free_entries`, and a
  `list of string` with `free_strings` (their `banish` only frees the list
  buffer, exactly like every other PenguScript list).
- The `maybe` wrapper around those results is released by `banish`; use the
  `or:` / `or else` forms to move the payload out and free the box in one
  step.
- `parse_in_arena` returns a value whose strings and list buffers live in the
  arena. `banish arena` releases everything at once, and banishing the
  returned value is a safe no-op. Do not mutate an arena-backed value: its
  lists are immutable (`cap < 0` marks them).
- `stringify` returns an owned string.

## Complexity
| Operation | Cost |
|---|---|
| `parse`, `validate` | O(n) time, O(depth) stack |
| `stringify` | O(size of the value) |
| `pointer` | O(path tokens × object size) |
| `find_key` | O(size of the tree) |
| `deep_merge` | O(size of both trees) |
| `clone` | O(size of the subtree) |
| `array_len`, `object_len`, `is_*` | O(1) |
| `has_key`, `get`, `at` | O(object/array size) |

## Errors
Every parser diagnostic carries `kind`, `message`, a 1-indexed `line` and
`col`, and the absolute `offset` in bytes. `JsonError.format` renders the
canonical `line:col: message` form.

## Divergences from Python `json`
- Integers are `i64`. A literal outside the `i64` range is `IntegerOverflow`,
  not a big integer (PenguScript is zero-cost and has no bigints).
- `parse` rejects `NaN`/`Infinity`, comments and trailing commas by default;
  `ParseOptions` opts in. Python always rejects NaN output unless
  `allow_nan=True`; so does this module.
- Duplicate object keys: the last value wins, at the position of the first
  occurrence (Python keeps the first insertion position too).
- Floats are printed with the shortest round-tripping representation, then
  formatted like Python (`1.0`, `10000000000.0`, `1e+20`, `1e-05`).

## Runtime note
List headers with `cap < 0` are non-owning views over arena memory. The
runtime treats their `data` pointer as borrowed, so `banish` is a no-op and
`push` refuses to grow them. `std.json` is the only producer today.

---

### `JSON_VERSION`

> **JSON_VERSION** : string

 JSON module version.

### `JSON_MAX_DEPTH`

> **JSON_MAX_DEPTH** : int

 Default maximum nesting depth accepted by `parse` (matches CPython's default
 recursion limit).

### `JSON_NEWLINE`

> **JSON_NEWLINE** : int

 The byte value of `\n`, used by the line/column tracker.

### `JSON_CARRIAGE_RETURN`

> **JSON_CARRIAGE_RETURN** : int

 The byte value of `\r`.

### `JSON_QUOTE`

> **JSON_QUOTE** : int

 The byte value of `"`.

### `JSON_BACKSLASH`

> **JSON_BACKSLASH** : int

 The byte value of `\`.

### `JSON_SLASH`

> **JSON_SLASH** : int

 The byte value of `/`.

### `JsonErrorKind`

> omen JsonErrorKind

```pengu
    UnexpectedEof
    UnexpectedChar
    InvalidNumber
    InvalidString
    InvalidEscape
    InvalidUnicode
    InvalidLiteral
    TrailingCharacters
    DepthExceeded
    IntegerOverflow
    InvalidUtf8
```

 What went wrong while parsing or validating JSON.

### `JsonError`

> rune JsonError

```pengu
    kind as JsonErrorKind
    message as string
    line as int
    col as int
    offset as int
```

 A parser or validation failure.

 ## Memoria
 Owns `message`; `banish err` releases it (derived `Nexus`).

### `JsonValue`

> omen JsonValue

```pengu
    Null
    Bool with value as bool
    Int with value as i64
    Float with value as f64
    Str with value as string
    Arr with items as list of JsonValue
    Obj with entries as list of JsonEntry
```

 A JSON value.

 The model is algebraic because each variant carries a different payload. It
 preserves object insertion order (`list of JsonEntry`, not a `map`), so
 `stringify` reproduces the document's member order unless `sort_keys` asks
 for alphabetical order.

 ## Variantes
 - `Null`: the literal `null`.
 - `Bool`: `true` or `false`.
 - `Int`: an integral number that fits `i64`.
 - `Float`: a number with a fraction or exponent, as `f64`.
 - `Str`: an unescaped UTF-8 string.
 - `Arr`: an array, in document order.
 - `Obj`: an object, in insertion order.

 ## Memoria
 A `JsonValue` owns every string and list below it. `banish v` releases the
 whole tree because the derived `Nexus` recurses through the two lists.

### `JsonEntry`

> rune JsonEntry

```pengu
    key as string
    value as JsonValue
```

 One member of a JSON object, in insertion order.

 ## Memoria
 Owns `key` and `value`; `banish entry` releases both.

### `ParseOptions`

> rune ParseOptions

```pengu
    allow_non_standard as bool
    max_depth as int
    allow_comments as bool
    allow_trailing_commas as bool
    strict as bool
```

 Knobs for `parse_with`, `validate` and `parse_in_arena`.

### `default_parse_options`

> **default_parse_options**() -> ParseOptions

 The strict RFC 8259 defaults.

 ## Retorno
 `{allow_non_standard: false, max_depth: 1000, allow_comments: false,
 allow_trailing_commas: false, strict: true}`.

 ## Ejemplo
 ```pengu
 var opts as json.ParseOptions is calling json.default_parse_options
 ```

### `SerializeOptions`

> rune SerializeOptions

```pengu
    indent as int
    sort_keys as bool
    ensure_ascii as bool
    escape_slash as bool
    allow_nan as bool
    compact_separators as bool
    trailing_newline as bool
```

 Knobs for `stringify_with` and `write_to_builder`.

### `default_serialize_options`

> **default_serialize_options**() -> SerializeOptions

 The default serializer settings: compact, insertion order, UTF-8 direct.

 ## Retorno
 `{indent: 0, sort_keys: false, ensure_ascii: false, escape_slash: false,
 allow_nan: false, compact_separators: true, trailing_newline: false}`.

 ## Ejemplo
 ```pengu
 var opts as json.SerializeOptions is calling json.default_serialize_options
 ```

### `_json_valid_utf8`

> **_json_valid_utf8**(s: string) -> int

 Returns `-1` when `s` is valid UTF-8, else the byte offset of the first
 offending sequence.

 ## Motivo
 The parser validates the whole source once, up front, so `parse_string` can
 copy multibyte sequences byte by byte without re-decoding them.

 ## Memoria
 Reads only; allocates nothing.

### `_json_strtoll`

> **_json_strtoll**(s: string, start: int, end: int, out: ref to i64) -> bool

 Parses the exact byte range `[start, end)` of `s` as a base-10 `i64`.

 ## Motivo
 `strtoll` detects `ERANGE` for both ends of the `i64` range, which the
 parser cannot do with an accumulator without special-casing `i64` min.

 ## Memoria
 Writes `out`; allocates nothing.

### `_json_strtod`

> **_json_strtod**(s: string, start: int, end: int, out: ref to f64) -> bool

 Parses the exact byte range `[start, end)` of `s` as an `f64`.

 ## Motivo
 `strtod` is the correctly-rounded decimal-to-binary conversion; the result
 must round-trip through `stringify`.

 ## Memoria
 Writes `out`; allocates nothing.

### `_json_format_f64`

> **_json_format_f64**(f: f64) -> string

 Formats an `f64` with the shortest representation that round-trips, in the
 same style as Python's `repr`: fixed notation for decimal exponents in
 `[-4, 16)`, scientific otherwise, always with a decimal part for integral
 values (`1.0`, `10000000000.0`).

 ## Motivo
 `snprintf("%g")` truncates to six significant digits, and `%.17g` is not the
 shortest form. The loop over precisions finds the minimal `p` for which
 `strtod` returns the original bit pattern, then rewrites it in the Python
 layout.

 ## Memoria
 Returns an owned string; release it with `banish`.

### `_json_clone_value`

> **_json_clone_value**(v: JsonValue) -> JsonValue

 Deep-copies a `JsonValue`, recursing into arrays and objects.

 ## Motivo
 Copying the handle would share the nested buffers: mutating the copy would
 change the original, and freeing one would dangle the other. `clone` must
 hand out an independent tree, so the walk re-allocates every string and list.

 ## Memoria
 Returns a fully independent tree; release it with `banish` or `free`.

### `_json_free_raw`

> **_json_free_raw**(v: ref to JsonValue) -> void

 Releases a `JsonValue` in place and zeroes it.

 ## Motivo
 `free` must work even when the caller has a `ref to JsonValue` (a method's
 `self`), where `banish` would release the pointer, not the payload.

 ## Memoria
 Frees every owned buffer; the value becomes `Null`.

### `_json_bytes_to_string`

> **_json_bytes_to_string**(s: slice of u8) -> string

 Copies a byte slice into a fresh owned string.

 ## Motivo
 `parse_bytes` / `validate_bytes` accept a `slice of byte`; the parser works
 on `string`, so one copy normalizes the representation.

 ## Memoria
 Allocates one owned buffer; release it with `banish`.

### `_json_obj_put`

> **_json_obj_put**(entries: ref to list of JsonEntry, key: string, value: JsonValue) -> void

 Inserts or replaces `key -> value` in an object entry list, taking ownership
 of both.

 ## Motivo
 A weave parameter is an immutable binding, so the pure version could not
 `set entries at i` and could not update the header when `push` reallocates.
 The bridge mutates the caller's real `PenguList` header through a `ref`.

 ## Memoria
 On duplicate, frees the replaced value and the new key; on insert, the list
 takes ownership of both.

### `_json_drop_result_box`

> **_json_drop_result_box**(r: ref to result of JsonValue to JsonError) -> void

 Releases only the box of a `result of JsonValue to JsonError`.

 ## Motivo
 `parse_in_arena` moves the value out of a successful result; the box must be
 freed without touching the payload, which now belongs to the caller.

 ## Memoria
 Frees the payload slot, not the payload.

### `_json_take_value`

> **_json_take_value**(m: ref to maybe JsonValue) -> JsonValue

 Moves the payload out of a `maybe JsonValue` and frees only the box.

 ## Motivo
 A caller that wants to own the payload without a copy needs to consume the
 box; `banish` on the box would release the payload too.

 ## Memoria
 Transfers the payload to the caller and zeroes the box.

### `_json_take_string`

> **_json_take_string**(m: ref to maybe string) -> string

 Moves the payload out of a `maybe string` and frees only the box.

 ## Motivo
 Same contract as `_json_take_value`, for the string accessors.

 ## Memoria
 Transfers the string to the caller and zeroes the box.

### `_json_drop_maybe_values`

> **_json_drop_maybe_values**(m: ref to maybe list of JsonValue) -> void

 Releases the box of a `maybe list of JsonValue` without its payload.

 ## Motivo
 `as_array` hands out an owned list; after `free_values` has released it the
 box must be freed without freeing the moved list again.

 ## Memoria
 Frees the box allocation only.

### `_json_drop_maybe_entries`

> **_json_drop_maybe_entries**(m: ref to maybe list of JsonEntry) -> void

 Releases the box of a `maybe list of JsonEntry` without its payload.

 ## Motivo
 Same contract as `_json_drop_maybe_values`, for `as_object`.

 ## Memoria
 Frees the box allocation only.

### `_json_substring`

> **_json_substring**(s: string, start: int, end: int) -> string

 Returns an owned copy of the byte range `[start, end)` of `s`.

 ## Motivo
 JSON Pointer tokenisation needs a substring without importing a full text
 module; the runtime helper already implements the exact ownership contract.

 ## Memoria
 Allocates one owned buffer; release it with `banish`.

### `_json_is_finite`

> **_json_is_finite**(f: f64) -> bool

 Reports whether `f` is finite.

 ## Motivo
 `stringify` must reject `NaN`/`Infinity` unless `allow_nan` is set, and
 `f != f` only detects NaN.

 ## Memoria
 Reads only; allocates nothing.

### `_json_drop_maybe`

> **_json_drop_maybe**(m: ref to maybe JsonValue) -> void

 Releases the *box* of a `maybe JsonValue` without releasing its payload.

 ## Motivo
 The `or:` form frees the box for you, but an `or:` block that does not
 mention `error` emits an unused variable in C. This helper lets internal
 code move the payload out and free only the box, keeping the generated C
 clean under `-Werror`.

 ## Memoria
 Frees the box allocation; the value it pointed at is left untouched.

### `_json_str_cmp`

> **_json_str_cmp**(a: string, b: string) -> int

 Compares two strings byte-wise.

 ## Motivo
 `sort_keys` only needs the ordering; routing it through one C helper keeps
 the contract identical to `pengu_string_compare` used by derived `Ordo`.

 ## Memoria
 Reads only; allocates nothing.

### `_json_push_arr`

> **_json_push_arr**(v: ref to JsonValue, item: JsonValue) -> void

 Pushes `item` onto the array payload of `v`.

 ## Motivo
 A method on an algebraic omen cannot mutate `self`'s active union member
 through the language (the `judge` binding is a copy), so the few in-place
 mutators go through a two-line C bridge. The PenguScript wrapper checks the
 tag and panics with a useful message first.

 ## Memoria
 The list owns the copied element; `item`'s buffers are not duplicated, so
 ownership of the payload transfers to the array.

### `_json_pop_arr`

> **_json_pop_arr**(v: ref to JsonValue, out: ref to JsonValue) -> bool

 Moves the last array element into `out` and shrinks the array.

 ## Motivo
 `pop` transfers ownership without copying; doing it from PenguScript would
 require reading an element after decrementing the length.

 ## Memoria
 `out` receives the element bytes; the array no longer references them.

### `_json_set_at_arr`

> **_json_set_at_arr**(v: ref to JsonValue, idx: int, item: JsonValue) -> bool

 Replaces array element `idx`, releasing the old payload.

 ## Motivo
 Replacing an element must release the subtree it held; that is the derived
 destructor, which is only reachable from C.

 ## Memoria
 Frees the old element, stores `item` (ownership transfers).

### `_json_set_key_obj`

> **_json_set_key_obj**(v: ref to JsonValue, key: string, item: JsonValue) -> void

 Inserts or replaces `key -> item` in an object, copying the key.

 ## Motivo
 The object stores owned keys, and replacing an existing value must release
 the old subtree.

 ## Memoria
 Copies `key`; takes ownership of `item`; frees a replaced value.

### `_json_remove_key_obj`

> **_json_remove_key_obj**(v: ref to JsonValue, key: string, out: ref to JsonValue) -> bool

 Removes `key` from an object, moving its value into `out`.

 ## Motivo
 Removal must free the object's key and shift the remaining entries.

 ## Memoria
 Frees the stored key; `out` receives the value; the entry is removed.

### `_json_arena_string`

> **_json_arena_string**(p: ref to u8, n: int) -> string

 Returns a non-owning `string` view over `[p, p + n)` in arena memory.

 ## Motivo
 `parse_in_arena` must not allocate string bytes on the heap; a header with
 `is_owned == 0` makes `banish` a no-op.

 ## Memoria
 Borrows the arena block. Valid until the arena is reset or freed.

### `_json_arena_list`

> **_json_arena_list**(p: ref to JsonValue, n: int) -> list of JsonValue

 Builds a non-owning `list of JsonValue` header over arena memory.

 ## Motivo
 The arena owns the element buffer. `cap = -1` marks the header as
 non-owning: `banish` does not `free` an arena pointer and `push` refuses to
 grow it.

 ## Memoria
 Borrows the arena block; valid until the arena is reset or freed.

### `_json_arena_entries`

> **_json_arena_entries**(p: ref to JsonEntry, n: int) -> list of JsonEntry

 Builds a non-owning `list of JsonEntry` header over arena memory.

 ## Motivo
 Same contract as `_json_arena_list`, for object entries.

 ## Memoria
 Borrows the arena block; valid until the arena is reset or freed.

### `i64_max`

> **i64_max**() -> i64

 Returns the `i64` value `9223372036854775807`.

 ## Retorno
 `i64` max, useful when clamping.

### `i64_min`

> **i64_min**() -> i64

 Returns the `i64` value `-9223372036854775808`.

 ## Retorno
 `i64` min. Written as `(-max) - 1` because the positive literal does not fit.

### `_append_codepoint`

> **_append_codepoint**(sb: ref to StringBuilder, cp: int) -> void

 Appends one Unicode codepoint to a builder as UTF-8.

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `cp`: a scalar value in `[0, 0x10FFFF]`, excluding the surrogate range.

 ## Retorno
 Nothing.

 ## Memoria
 Appends into the builder's buffer; no temporary string is allocated.

 ## Ejemplo
 ```pengu
 calling json._append_codepoint with (sigil of sb), 0x1F600
 ```

### `_hex_val`

> **_hex_val**(b: int) -> int

 Returns the value of one hexadecimal digit byte, or `-1`.

 ## Parámetros
 - `b`: an ASCII byte value.

 ## Retorno
 `0..15` for `0-9`, `a-f`, `A-F`; `-1` otherwise.

### `_hex_byte`

> **_hex_byte**(v: int) -> u8

 Returns the byte value of a lowercase hex digit.

 ## Parámetros
 - `v`: `0..15`.

 ## Retorno
 The ASCII byte for `0123456789abcdef`; `48` for an out-of-range value.

### `_append_u4`

> **_append_u4**(sb: ref to StringBuilder, cp: int) -> void

 Appends a `\uXXXX` escape for the low 16 bits of `cp`.

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `cp`: a UTF-16 code unit.

 ## Retorno
 Nothing.

### `free_values`

> **free_values**(items: list of JsonValue) -> void

 Frees every element of a `list of JsonValue`, then the list itself.

 ## Parámetros
 - `items`: an owned list (for example the result of `as_array`, `values`,
   `find_key` or `parse_in_arena` is **not** owned; do not free that one).

 ## Retorno
 Nothing.

 ## Memoria
 Banishes each value recursively, then the list buffer.

 ## Ejemplo
 ```pengu
 var items as maybe list of JsonValue is calling root.as_array
 if items.is_present:
     calling json.free_values with items.value
     banish items
 ```

### `free_entries`

> **free_entries**(entries: list of JsonEntry) -> void

 Frees every entry of a `list of JsonEntry`, then the list itself.

 ## Parámetros
 - `entries`: an owned list, such as the result of `as_object` or `entries`.

 ## Retorno
 Nothing.

 ## Memoria
 Banishes each entry (its key and value), then the list buffer.

### `free_strings`

> **free_strings**(items: list of string) -> void

 Frees every string of a `list of string`, then the list itself.

 ## Parámetros
 - `items`: an owned list of strings, such as the result of `keys`.

 ## Retorno
 Nothing.

 ## Memoria
 Banishes each string copy, then the list buffer.

### `take_value`

> **take_value**(m: ref to maybe JsonValue) -> JsonValue

 Moves the value out of a `maybe JsonValue`, freeing only the box.

 ## Parámetros
 - `m`: the optional. The box is consumed; do not use it afterwards.

 ## Retorno
 The payload (owned; release it with `banish`), or `JsonValue.Null` when the
 optional was absent.

 ## Ejemplo
 ```pengu
 var opt as maybe JsonValue is calling root.get with "key"
 var value as JsonValue is calling json.take_value with (sigil of opt)
 defer banish value
 ```

### `take_string`

> **take_string**(m: ref to maybe string) -> string

 Moves the string out of a `maybe string`, freeing only the box.

 ## Parámetros
 - `m`: the optional. The box is consumed; do not use it afterwards.

 ## Retorno
 The string (owned; release it with `banish`), or `""` when absent.

### `get_or_null`

> **get_or_null**(v: JsonValue, key: string) -> JsonValue

 Member `key` as an owned deep copy, or `JsonValue.Null` when absent.

 This is the box-free variant of `get`, for code that wants a plain value
 without a `maybe` wrapper.

 ## Parámetros
 - `v`: an object (other kinds return `Null`). Borrowed.
 - `key`: the member name. Borrowed.

 ## Retorno
 An owned `JsonValue`; release it with `banish`.

### `at_or_null`

> **at_or_null**(v: JsonValue, i: int) -> JsonValue

 Element `i` as an owned deep copy, or `JsonValue.Null` when out of range.

 ## Parámetros
 - `v`: an array (other kinds return `Null`). Borrowed.
 - `i`: the 0-based index.

 ## Retorno
 An owned `JsonValue`; release it with `banish`.

### `null_value`

> **null_value**() -> JsonValue

 Constructs the JSON `null`.

 ## Retorno
 `JsonValue.Null`.

### `bool_val`

> **bool_val**(b: bool) -> JsonValue

 Constructs a boolean value.

 ## Parámetros
 - `b`: the boolean. Copied.

 ## Retorno
 `JsonValue.Bool`.

### `int_val`

> **int_val**(i: i64) -> JsonValue

 Constructs an integer value.

 ## Parámetros
 - `i`: an `i64`. Copied.

 ## Retorno
 `JsonValue.Int`.

### `float_val`

> **float_val**(f: f64) -> JsonValue

 Constructs a floating-point value.

 ## Parámetros
 - `f`: an `f64`. Copied.

 ## Retorno
 `JsonValue.Float`.

### `string_val`

> **string_val**(s: string) -> JsonValue

 Constructs a string value, taking ownership of `s`.

 ## Parámetros
 - `s`: the text. The returned value owns the buffer; do not banish `s`
   after the call.

 ## Retorno
 `JsonValue.Str`.

### `empty_array`

> **empty_array**() -> JsonValue

 Constructs an empty array.

 ## Retorno
 `JsonValue.Arr` with a fresh empty list.

### `empty_object`

> **empty_object**() -> JsonValue

 Constructs an empty object.

 ## Retorno
 `JsonValue.Obj` with a fresh empty entry list.

### `_clone_values`

> **_clone_values**(items: list of JsonValue) -> list of JsonValue

 Deep-copies a list of JSON values.

 ## Parámetros
 - `items`: the list to copy. Borrowed.

 ## Retorno
 A new list whose elements are independent deep copies. Release it with
 `free_values`.

 ## Complejidad
 O(total size of the elements).

### `_clone_entries`

> **_clone_entries**(entries: list of JsonEntry) -> list of JsonEntry

 Deep-copies a list of object entries.

 ## Parámetros
 - `entries`: the entry list to copy. Borrowed.

 ## Retorno
 A new list whose entries are independent deep copies. Release it with
 `free_entries`.

### `_strict_eq`

> **_strict_eq**(a: JsonValue, b: JsonValue) -> bool

 Compares two JSON values with strict type identity.

 ## Parámetros
 - `a`, `b`: values to compare. Borrowed.

 ## Retorno
 `true` when both have the same variant and equal payload; `Int(1)` and
 `Float(1.0)` are **not** equal.

 ## Complejidad
 O(size of the values).

### `is_null`

> **is_null**() -> bool

 True when the value is `null`.

### `is_bool`

> **is_bool**() -> bool

 True when the value is a boolean.

### `is_int`

> **is_int**() -> bool

 True when the value is an integer.

### `is_float`

> **is_float**() -> bool

 True when the value is a float.

### `is_number`

> **is_number**() -> bool

 True when the value is an integer or a float.

### `is_string`

> **is_string**() -> bool

 True when the value is a string.

### `is_array`

> **is_array**() -> bool

 True when the value is an array.

### `is_object`

> **is_object**() -> bool

 True when the value is an object.

### `type_name`

> **type_name**() -> string

 The lowercase JSON type name.

 ## Retorno
 `"null"`, `"bool"`, `"int"`, `"float"`, `"string"`, `"array"` or
 `"object"`.

### `as_bool`

> **as_bool**() -> maybe bool

 The boolean payload, when the value is a boolean.

 ## Retorno
 `some b` or `none`. The box is a plain value; release it with `banish`.

### `as_int`

> **as_int**() -> maybe i64

 The integer payload, when the value is an integer.

 ## Retorno
 `some i` or `none`.

### `as_float`

> **as_float**() -> maybe f64

 The float payload, when the value is a float.

 ## Retorno
 `some f` or `none`. An `Int` is **not** converted; use `as_number`.

### `as_number`

> **as_number**() -> maybe f64

 The value as an `f64`, converting integers.

 ## Retorno
 `some f` for an `Int` or a `Float`, `none` otherwise.

### `as_string`

> **as_string**() -> maybe string

 An owned copy of the string payload.

 ## Retorno
 `some s` (owned copy; release it with `banish`) or `none`.

### `as_array`

> **as_array**() -> maybe list of JsonValue

 An owned deep copy of the array payload.

 ## Retorno
 `some items` (deep copy; release it with `free_values`) or `none`.

### `as_object`

> **as_object**() -> maybe list of JsonEntry

 An owned deep copy of the object payload.

 ## Retorno
 `some entries` (deep copy; release it with `free_entries`) or `none`.

### `array_len`

> **array_len**() -> int

 Number of elements in an array.

 ## Retorno
 The element count, or `0` when the value is not an array.

### `at`

> **at**(i: int) -> maybe JsonValue

 Element at `i`, as an owned deep copy.

 ## Parámetros
 - `i`: 0-based index.

 ## Retorno
 `some value` (owned; release it with `banish`) or `none` when the value
 is not an array or `i` is out of range.

### `first`

> **first**() -> maybe JsonValue

 First element, as an owned deep copy.

 ## Retorno
 `some value` or `none` for an empty/non-array value.

### `last`

> **last**() -> maybe JsonValue

 Last element, as an owned deep copy.

 ## Retorno
 `some value` or `none` for an empty/non-array value.

### `object_len`

> **object_len**() -> int

 Number of members in an object.

 ## Retorno
 The member count, or `0` when the value is not an object.

### `has_key`

> **has_key**(key: string) -> bool

 True when `key` is a member of the object.

 ## Parámetros
 - `key`: the member name. Borrowed.

### `get`

> **get**(key: string) -> maybe JsonValue

 Member `key`, as an owned deep copy.

 ## Retorno
 `some value` (owned; release it with `banish`) or `none`.

### `keys`

> **keys**() -> list of string

 An owned copy of every key, in insertion order.

 ## Retorno
 A `list of string` (release it with `free_strings`); empty for a
 non-object.

### `values`

> **values**() -> list of JsonValue

 An owned deep copy of every value, in insertion order.

 ## Retorno
 A `list of JsonValue` (release it with `free_values`); empty for a
 non-object.

### `entries`

> **entries**() -> list of JsonEntry

 An owned deep copy of every entry, in insertion order.

 ## Retorno
 A `list of JsonEntry` (release it with `free_entries`); empty for a
 non-object.

### `pointer`

> **pointer**(path: string) -> maybe JsonValue

 Resolves a JSON Pointer against the value.

 A pointer is a sequence of `/`-prefixed tokens. `""` addresses the
 value itself, `"/"` addresses the member with the empty key, `"~1"`
 decodes to `/` and `"~0"` to `~`. Array tokens must be canonical decimal
 indices (`0`, `7`; `01` is invalid).

 ## Parámetros
 - `path`: the pointer. Borrowed.

 ## Retorno
 `some value` (an owned deep copy; release it with `banish`) or `none`
 when a token is missing, an index is invalid/out of range, or the path
 does not start with `/`.

 ## Complejidad
 O(number of tokens × size of the current container).

 ## Ejemplo
 ```pengu
 var v as JsonValue is (calling root.pointer with "/a/b/0") or:
     return 1
 defer banish v
 ```

### `find_key`

> **find_key**(key: string) -> list of JsonValue

 Every value of a member named `key`, anywhere in the tree.

 The search is depth-first in document order, and it descends into both
 arrays and objects. The result contains owned deep copies.

 ## Parámetros
 - `key`: the member name to look for. Borrowed.

 ## Retorno
 A `list of JsonValue`; empty when nothing matches. Release it with
 `free_values`.

### `equals`

> **equals**(other: JsonValue) -> bool

 Strict structural equality.

 ## Parámetros
 - `other`: the value to compare against.

 ## Retorno
 `true` when both values have the same variant and equal payload.
 `Int(1)` and `Float(1.0)` are not equal; use `equals_numeric` for that.

### `equals_numeric`

> **equals_numeric**(other: JsonValue) -> bool

 Numeric-aware equality: `Int(1)` equals `Float(1.0)`.

 Arrays and objects compare structurally with the same numeric rule at the
 top level of each element/member.

 ## Parámetros
 - `other`: the value to compare against.

 ## Retorno
 `true` when both are numbers with the same IEEE-754 value, or both are
 the same non-numeric variant with equal payload, or arrays/objects whose
 elements are numerically equal.

### `clone`

> **clone**() -> JsonValue

 A deep, independent copy of the value.

 ## Retorno
 A new tree with its own strings and lists. Release it with `banish`.

### `free`

> **free**() -> void

 Releases the value and resets it to `null`.

 `free` is the method form of `banish`: it works on a `ref to JsonValue`
 (a method receiver) and is idempotent.

 ## Memoria
 Frees every owned buffer below the value.

### `push_json`

> **push_json**(v: JsonValue) -> void

 Appends `v` to an array, taking ownership of it.

 ## Parámetros
 - `v`: the element. Its ownership transfers to the array.

 ## Efectos
 Panics when the receiver is not an array.

### `pop_json`

> **pop_json**() -> maybe JsonValue

 Removes and returns the last array element.

 ## Retorno
 `some value` (owned) or `none` for an empty/non-array value.

 ## Efectos
 Panics when the receiver is not an array.

### `set_at`

> **set_at**(i: int, v: JsonValue) -> void

 Replaces array element `i`, releasing the old subtree.

 ## Parámetros
 - `i`: 0-based index.
 - `v`: the new element; its ownership transfers to the array.

 ## Efectos
 Panics when the receiver is not an array or `i` is out of range.

### `put_json`

> **put_json**(key: string, v: JsonValue) -> void

 Inserts or replaces `key`, taking ownership of `v`.

 The key is copied; replacing an existing member releases its old value.

 ## Parámetros
 - `key`: the member name. Borrowed.
 - `v`: the new value; its ownership transfers to the object.

 ## Efectos
 Panics when the receiver is not an object.

### `remove_key`

> **remove_key**(key: string) -> maybe JsonValue

 Removes `key` and returns its value.

 ## Parámetros
 - `key`: the member name. Borrowed.

 ## Retorno
 `some value` (owned) or `none` when the key is absent.

 ## Efectos
 Panics when the receiver is not an object.

### `set_key`

> **set_key**(key: string, v: JsonValue) -> void

 Inserts or replaces `key`; the explicit-name form of `put_json`.

 ## Parámetros
 - `key`: the member name. Borrowed.
 - `v`: the new value; its ownership transfers to the object.

### `merge`

> **merge**(other: JsonValue) -> void

 Shallow merge: every member of `other` is put into the receiver.

 ## Parámetros
 - `other`: a JSON object. Borrowed; its values are deep-copied.

 ## Efectos
 Panics when either value is not an object.

### `_unescape_pointer`

> **_unescape_pointer**(token: string) -> string

 Decodes one RFC 6901 reference token (`~1` -> `/`, `~0` -> `~`).

 ## Parámetros
 - `token`: the raw token (no `/`). Borrowed.

 ## Retorno
 An owned decoded string; release it with `banish`.

 ## Ejemplo
 ```pengu
 var t as string is calling json._unescape_pointer with "a~1b"   # "a/b"
 ```

### `_index_token`

> **_index_token**(token: string) -> int

 Parses a JSON Pointer array token as a canonical non-negative index.

 ## Parámetros
 - `token`: a decoded pointer token. Borrowed.

 ## Retorno
 The index, or `-1` when the token is empty, has a leading zero (`01`), is
 not all digits, or does not fit an `int`.

 ## Ejemplo
 ```pengu
 calling json._index_token with "12"   # 12
 calling json._index_token with "01"   # -1
 ```

### `_numeric_eq`

> **_numeric_eq**(a: JsonValue, b: JsonValue) -> bool

 Numeric-aware structural equality.

 ## Parámetros
 - `a`, `b`: values to compare. Borrowed.

 ## Retorno
 `true` when the values match, treating `Int(n)` and `Float(n)` as equal.

### `_find_key_into`

> **_find_key_into**(v: JsonValue, key: string, out: list of JsonValue) -> list of JsonValue

 Recursive worker for `JsonValue.find_key`.

 ## Parámetros
 - `v`: the subtree to scan. Borrowed.
 - `key`: the member name to look for. Borrowed.
 - `out`: accumulator. Appends owned deep copies.

### `Parser`

> rune Parser

```pengu
    src as string
    pos as int
    line as int
    col as int
    depth as int
    opts as ParseOptions
    build as bool
    failed as bool
    err_kind as JsonErrorKind
    err_message as string
    err_line as int
    err_col as int
    err_offset as int
```

 The recursive-descent JSON parser state.

 One `Parser` parses one document. It owns `err_message` only after a failure;
 `src` is **borrowed** (the caller keeps the source alive for the duration of
 the parse). The parser is not derived `Nexus`: it never owns the source.

### `_line_col_at`

> **_line_col_at**(s: string, offset: int, line: ref to int, col: ref to int) -> void

 Computes the 1-indexed `(line, col)` of a byte offset.

 ## Parámetros
 - `s`: the source. Borrowed.
 - `offset`: a byte offset (clamped to the string).
 - `line`: output, 1-indexed.
 - `col`: output, 1-indexed byte column.

### `peek_at`

> **peek_at**(off: int) -> int

 Returns the byte at `pos + off`, or `-1` past the end.

### `peek`

> **peek**() -> int

 Returns the current byte, or `-1` at end of input.

### `advance`

> **advance**() -> int

 Consumes one byte, updating the line/column counters.

 ## Retorno
 The byte consumed, or `-1` at end of input.

### `fail`

> **fail**(kind: JsonErrorKind, message: string) -> void

 Records the first error and releases a later competing message.

 ## Parámetros
 - `kind`: the category.
 - `message`: an owned message; ownership transfers to the parser.

### `take_error`

> **take_error**() -> JsonError

 Moves the recorded error out of the parser.

 ## Retorno
 A `JsonError` that owns the parser's message.

### `starts_with_word`

> **starts_with_word**(word: string) -> bool

 True when the remaining input begins with `word`.

 ## Parámetros
 - `word`: an ASCII literal (`null`, `true`, `false`, `NaN`, ...).

### `consume_word`

> **consume_word**(word: string) -> void

 Consumes `word` after `starts_with_word` returned true.

### `skip_whitespace`

> **skip_whitespace**() -> void

 Skips RFC 8259 whitespace and, when enabled, comments.

### `parse_document`

> **parse_document**() -> JsonValue

 Parses the whole document: one value plus optional trailing whitespace.

 ## Retorno
 The parsed value, or `JsonValue.Null` (with `failed` set) on error.

### `parse_value`

> **parse_value**() -> JsonValue

 Parses one value.

 ## Retorno
 The value, or `JsonValue.Null` with `failed` set.

### `parse_literal`

> **parse_literal**(word: string, v: JsonValue) -> JsonValue

 Parses `word` and returns `v`, or records `InvalidLiteral`.

### `parse_number`

> **parse_number**() -> JsonValue

 Parses an RFC 8259 number.

 Integers that do not fit `i64` are `IntegerOverflow`; numbers with a
 fraction or exponent are `Float`.

### `parse_string`

> **parse_string**() -> JsonValue

 Parses a quoted string with RFC 8259 escapes.

 ## Retorno
 `JsonValue.Str`, or `JsonValue.Null` with `failed` set.

### `parse_unicode_escape`

> **parse_unicode_escape**() -> int

 Parses the four hex digits of a `\u` escape, combining surrogate pairs.

 The leading `\u` must already be consumed.

 ## Retorno
 The Unicode scalar value, or `-1` with `failed` set.

### `parse_hex4`

> **parse_hex4**() -> int

 Parses exactly four hexadecimal digits.

 ## Retorno
 `0..65535`, or `-1` with `failed` set.

### `parse_array`

> **parse_array**() -> JsonValue

 Parses an array.

 ## Retorno
 `JsonValue.Arr`, or `JsonValue.Null` with `failed` set.

### `parse_object`

> **parse_object**() -> JsonValue

 Parses an object.

 ## Retorno
 `JsonValue.Obj`, or `JsonValue.Null` with `failed` set.

### `parse`

> **parse**(s: string) -> result of JsonValue to JsonError

 Parses `s` with the strict RFC 8259 defaults.

 ## Parámetros
 - `s`: the JSON text. Borrowed; the returned DOM owns its own buffers.

 ## Retorno
 `ok value`, or `err JsonError` with line, column and byte offset.

 ## Ejemplo
 ```pengu
 var r as result of JsonValue to JsonError is calling json.parse with "[1,2]"
 ```

### `parse_with`

> **parse_with**(s: string, opts: ParseOptions) -> result of JsonValue to JsonError

 Parses `s` with explicit options.

 ## Parámetros
 - `s`: the JSON text. Borrowed.
 - `opts`: parser knobs.

 ## Retorno
 `ok value`, or `err JsonError`.

 ## Ejemplo
 ```pengu
 var o as json.ParseOptions is calling json.default_parse_options
 var r as result of JsonValue to json.JsonError is calling json.parse_with with "// x\n{}", o
 ```

### `parse_bytes`

> **parse_bytes**(s: slice of u8) -> result of JsonValue to JsonError

 Parses a byte slice as JSON.

 ## Parámetros
 - `s`: the bytes. Borrowed; the parser takes one private copy internally.

 ## Retorno
 `ok value`, or `err JsonError`.

### `validate`

> **validate**(s: string) -> result of void to JsonError

 Checks that `s` is one valid JSON document, without building a DOM.

 Memory use is O(depth), independent of the document size.

 ## Parámetros
 - `s`: the JSON text. Borrowed.

 ## Retorno
 `ok 0`, or `err JsonError`.

 ## Ejemplo
 ```pengu
 var ok as bool is calling json.validate with "{\"a\":1}" is_ok
 ```

### `validate_bytes`

> **validate_bytes**(s: slice of u8) -> result of void to JsonError

 Checks that a byte slice is one valid JSON document.

 ## Parámetros
 - `s`: the bytes. Borrowed.

 ## Retorno
 `ok 0`, or `err JsonError`.

### `discard_result_box`

> **discard_result_box**(r: ref to result of JsonValue to JsonError) -> void

 Releases the box of a `result of JsonValue to JsonError` without its value.

 ## Parámetros
 - `r`: the result. The box is consumed; the payload must already have been
   moved out or released.

 ## Memoria
 Frees the box slot only.

 ## Ejemplo
 ```pengu
 var v as JsonValue is r.value
 calling json.discard_result_box with (sigil of r)
 ```

### `_json_to_arena`

> **_json_to_arena**(v: JsonValue, a: ref to Arena) -> JsonValue

 Copies a heap DOM into arena memory.

 Strings become non-owning views over arena blocks and list headers are
 marked `cap < 0` (non-owning). The result is therefore released by
 `banish arena`, while banishing any value inside it is a safe no-op.

 ## Parámetros
 - `v`: the heap value to copy. Borrowed; it is not modified.
 - `a`: destination arena. Mutated.

 ## Retorno
 The arena-backed equivalent of `v`.

 ## Memoria
 Allocates every string byte, list element and entry in `a`.

### `parse_in_arena`

> **parse_in_arena**(s: string, arena: ref to Arena) -> result of JsonValue to JsonError

 Parses `s` into an arena-backed DOM.

 Every string byte, array element and object entry lives in `arena`. A single
 `banish arena` (or `calling arena.free`) releases the whole document, and
 banishing the returned value is a safe no-op. The implementation parses into
 a temporary heap DOM and copies it into the arena, so the transient cost is
 O(size); the retained cost is entirely in the arena.

 ## Parámetros
 - `s`: the JSON text. Borrowed.
 - `arena`: destination arena. Mutated.

 ## Retorno
 `ok value` (arena-backed), or `err JsonError`.

 ## Ejemplo
 ```pengu
 var a as Arena is calling Arena.new
 defer calling a.free
 var v as JsonValue is (calling json.parse_in_arena with payload, sigil of a) or:
     return 1
 banish v          # safe no-op; the arena owns the memory
 ```

### `_utf8_len`

> **_utf8_len**(s: string, i: int) -> int

 Returns the UTF-8 length of the codepoint starting at byte `i`.

 ## Parámetros
 - `s`: a valid UTF-8 string (the parser guarantees this for its own output).
 - `i`: the offset of a lead byte.

 ## Retorno
 `1..4`; `1` for a stray continuation/invalid byte (treated as U+FFFD).

### `_utf8_cp`

> **_utf8_cp**(s: string, i: int) -> int

 Decodes one UTF-8 codepoint at byte `i`.

 ## Parámetros
 - `s`: the text. Borrowed.
 - `i`: offset of the lead byte.

 ## Retorno
 The scalar value, or `65533` (U+FFFD) for a malformed sequence.

### `_write_string`

> **_write_string**(s: string, opts: SerializeOptions, sb: ref to StringBuilder) -> void

 Writes a JSON string literal, including its surrounding quotes.

 ## Parámetros
 - `s`: the decoded text. Borrowed.
 - `opts`: serializer options.
 - `sb`: destination builder. Mutated.

 ## Memoria
 Appends only; no temporary string is allocated.

### `_write_float`

> **_write_float**(f: f64, opts: SerializeOptions, sb: ref to StringBuilder) -> void

 Writes one float, rejecting non-finite values unless `allow_nan`.

 ## Parámetros
 - `f`: the value.
 - `opts`: serializer options.
 - `sb`: destination builder. Mutated.

### `_write_newline_indent`

> **_write_newline_indent**(sb: ref to StringBuilder, depth: int, opts: SerializeOptions) -> void

 Writes `indent * depth` spaces, preceded by a newline.

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `depth`: nesting level (`0` is the top level).
 - `opts`: serializer options.

### `_write_comma`

> **_write_comma**(sb: ref to StringBuilder, opts: SerializeOptions) -> void

 Appends the currently active pair separator.

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `opts`: serializer options.

### `_write_colon`

> **_write_colon**(sb: ref to StringBuilder, opts: SerializeOptions) -> void

 Appends the currently active key/value separator.

 ## Parámetros
 - `sb`: destination builder. Mutated.
 - `opts`: serializer options.

### `_sorted_entries`

> **_sorted_entries**(entries: list of JsonEntry) -> list of JsonEntry

 Sorts a shallow copy of an object's entries by key.

 The copy aliases the entries' payloads; only the returned list buffer is
 owned. Release it with `banish sorted` (never `free_entries`).

 ## Parámetros
 - `entries`: the entry list. Borrowed.

 ## Retorno
 A new `list of JsonEntry` in byte-wise key order.

### `_write_value`

> **_write_value**(v: JsonValue, opts: SerializeOptions, sb: ref to StringBuilder, depth: int) -> void

 Writes `v` into `sb` using `opts`.

 This is the primitive every other serializer entry point uses.

 ## Parámetros
 - `v`: the value. Borrowed.
 - `opts`: serializer options.
 - `sb`: destination builder. Mutated.

 ## Efectos
 Panics on a non-finite float unless `opts.allow_nan` is set.

### `write_to_builder`

> **write_to_builder**(v: JsonValue, opts: SerializeOptions, sb: ref to StringBuilder) -> void

 Writes `v` into `sb` using `opts`.

 This is the primitive every other serializer entry point uses. A `builder`
 accumulates the output, so serializing a large tree is O(size) rather than
 O(size²).

 ## Parámetros
 - `v`: the value. Borrowed.
 - `opts`: serializer options.
 - `sb`: destination builder. Mutated.

 ## Efectos
 Panics on a non-finite float unless `opts.allow_nan` is set.

 ## Ejemplo
 ```pengu
 var sb as StringBuilder is calling StringBuilder.new
 calling json.write_to_builder with v, (calling json.default_serialize_options), (sigil of sb)
 var s as string is calling sb.finish
 ```

### `stringify_with`

> **stringify_with**(v: JsonValue, opts: SerializeOptions) -> string

 Serializes `v` with explicit options.

 ## Parámetros
 - `v`: the value. Borrowed.
 - `opts`: serializer options.

 ## Retorno
 An owned JSON string; release it with `banish`.

 ## Efectos
 Panics on a non-finite float unless `opts.allow_nan` is set.

 ## Ejemplo
 ```pengu
 var o as json.SerializeOptions is calling json.default_serialize_options
 var s as string is calling json.stringify_with with v, o
 ```

### `stringify`

> **stringify**(v: JsonValue) -> string

 Serializes `v` as compact JSON with the default options.

 ## Parámetros
 - `v`: the value. Borrowed.

 ## Retorno
 An owned JSON string; release it with `banish`.

 ## Ejemplo
 ```pengu
 var s as string is calling json.stringify with v    # {"a":1,"b":[2,3]}
 ```

### `stringify_pretty`

> **stringify_pretty**(v: JsonValue, indent: int) -> string

 Serializes `v` with `indent` spaces per nesting level.

 ## Parámetros
 - `v`: the value. Borrowed.
 - `indent`: spaces per level (`0` is compact).

 ## Retorno
 An owned pretty JSON string; release it with `banish`.

 ## Ejemplo
 ```pengu
 var s as string is calling json.stringify_pretty with v, 2
 ```

### `_has_non_finite`

> **_has_non_finite**(v: JsonValue) -> bool

 True when the tree contains a `NaN` or an infinity.

 ## Parámetros
 - `v`: the value to scan. Borrowed.

 ## Retorno
 `true` when any float is non-finite.

### `try_stringify`

> **try_stringify**(v: JsonValue, opts: SerializeOptions) -> result of string to JsonError

 Serializes `v`, returning an error instead of panicking on a non-finite float.

 ## Parámetros
 - `v`: the value. Borrowed.
 - `opts`: serializer options. `allow_nan` still opts in to emitting them.

 ## Retorno
 `ok string` (owned) or `err JsonError` with `InvalidNumber`.

### `deep_merge`

> **deep_merge**(base: JsonValue, overlay: JsonValue) -> JsonValue

 Recursively merges `overlay` into `base`, returning a new value.

 Object members merge recursively when both sides are objects; otherwise the
 overlay value wins. The inputs are never modified.

 ## Parámetros
 - `base`: the starting value. Borrowed.
 - `overlay`: the value applied on top. Borrowed.

 ## Retorno
 A new tree. Release it with `banish`.

 ## Ejemplo
 ```pengu
 var merged as JsonValue is calling json.deep_merge with defaults, user_config
 defer banish merged
 ```

### `_schema_type_matches`

> **_schema_type_matches**(v: JsonValue, name: string) -> bool

 True when `v` matches one JSON Schema `type` name.

 ## Parámetros
 - `v`: the value. Borrowed.
 - `name`: `null`, `boolean`, `object`, `array`, `string`, `number` or
   `integer`.

 ## Retorno
 `true` for a match; `false` for a mismatch or an unknown name.

### `_schema_push`

> **_schema_push**(out: list of string, path: string, detail: string) -> list of string

 Pushes one schema error, formatting the path and detail.

 ## Parámetros
 - `out`: accumulator. Mutated.
 - `path`: JSON-path-style location.
 - `detail`: the problem.

 ## Retorno
 The same accumulator, with one owned string appended.

### `_schema_check`

> **_schema_check**(v: JsonValue, schema: JsonValue, path: string, out: list of string) -> list of string

 Validates one value against one schema node, appending errors.

 ## Parámetros
 - `v`: the value. Borrowed.
 - `schema`: the schema node. Borrowed.
 - `path`: JSON-path-style location used in messages.
 - `out`: accumulator.

 ## Retorno
 The accumulator, with zero or more owned messages appended.

### `_schema_combinator`

> **_schema_combinator**(v: JsonValue, schema: JsonValue, keyword: string, path: string, out: list of string) -> list of string

 Applies one `allOf`/`anyOf`/`oneOf` combinator, if present.

 ## Parámetros
 - `v`, `schema`, `keyword`, `path`: the value, schema node, keyword and path.
 - `out`: accumulator.

 ## Retorno
 The accumulator, with one message when the combinator fails.

### `validate_schema`

> **validate_schema**(v: JsonValue, schema: JsonValue) -> list of string

 Validates `v` against a JSON Schema (a practical subset).

 Supported keywords: `type`, `const`, `enum`, `minimum`, `maximum`,
 `minLength`, `maxLength`, `minItems`, `maxItems`, `required`, `properties`,
 `additionalProperties` (boolean `false`), `items` (schema or tuple array),
 `allOf`, `anyOf`, `oneOf`.

 ## Parámetros
 - `v`: the value to validate. Borrowed.
 - `schema`: the schema document. Borrowed.

 ## Retorno
 A `list of string` of human-readable errors (`"$..."` paths); empty when the
 value is valid. Release it with `free_strings`.

 ## Ejemplo
 ```pengu
 var schema as JsonValue is (calling json.parse with r"""{"type":"object","required":["name"]}""") or:
     return 1
 var errs as list of string is calling json.validate_schema with v, schema
 if errs.len > 0:
     calling spark.println with (errs at 0)
 calling json.free_strings with errs
 ```

