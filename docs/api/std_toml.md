# std.toml

> Source: `std/toml.pengu`

std.toml.pengu — TOML 1.0 reader and writer for manifests and lockfiles.

`pengu.toml` and `pengu.lock` are TOML.  The compiler cannot rely on
Python's `tomllib` once it runs as a native binary, so this module provides a
small, dependency-free parser and serializer.  Parsing returns a flat list of
`TomlEntry` values whose keys are dotted paths (`project.name`), with array
elements spelled `[0]`, `[1]` and array-of-tables elements spelled
`package[0]`, `package[1]`.  That representation is deterministic, easy to
search, and needs no recursive AST allocation.

## Example
```pengu
import std.toml
import std.spark

weave main into int:
    let doc as result of list of toml.TomlEntry to string is calling toml.parse with "name = \"demo\"\n"
    if doc.is_ok:
        let name as string is calling toml.get with doc.value, "name"
        calling spark.println with name
        banish name
        calling toml.free_entries with doc.value
    return 0
```

## Memory
`parse` returns an owned list; every `TomlEntry.key`/`.value` is owned, so
release the list with `toml.free_entries`.  Getters (`get`, `get_array`)
return freshly allocated strings owned by the caller.

## Design notes
- **Flat, stable keys.** No map iteration is involved in parsing or
  serialization, which keeps golden files reproducible (B9).
- **C block parser, Pengu API.** The TOML grammar (multiline strings, arrays,
  inline tables, quoted keys, escapes) lives in `std_c/toml_min.h`; the
  public surface and ownership stay in PenguScript.
- **Dates are strings.** A manifest/lockfile never needs calendar arithmetic;
  date/time values keep their original text and kind `TomlKind.STRING`.
- **Errors carry line numbers.** `parse` returns `err("... line N")` instead of
  silently returning an empty document.

---

### `TOML_VERSION`

> **TOML_VERSION** : string

 std.toml.pengu — TOML 1.0 reader and writer for manifests and lockfiles.

 `pengu.toml` and `pengu.lock` are TOML.  The compiler cannot rely on
 Python's `tomllib` once it runs as a native binary, so this module provides a
 small, dependency-free parser and serializer.  Parsing returns a flat list of
 `TomlEntry` values whose keys are dotted paths (`project.name`), with array
 elements spelled `[0]`, `[1]` and array-of-tables elements spelled
 `package[0]`, `package[1]`.  That representation is deterministic, easy to
 search, and needs no recursive AST allocation.

 ## Example
 ```pengu
 import std.toml
 import std.spark

 weave main into int:
     let doc as result of list of toml.TomlEntry to string is calling toml.parse with "name = \"demo\"\n"
     if doc.is_ok:
         let name as string is calling toml.get with doc.value, "name"
         calling spark.println with name
         banish name
         calling toml.free_entries with doc.value
     return 0
 ```

 ## Memory
 `parse` returns an owned list; every `TomlEntry.key`/`.value` is owned, so
 release the list with `toml.free_entries`.  Getters (`get`, `get_array`)
 return freshly allocated strings owned by the caller.

 ## Design notes
 - **Flat, stable keys.** No map iteration is involved in parsing or
   serialization, which keeps golden files reproducible (B9).
 - **C block parser, Pengu API.** The TOML grammar (multiline strings, arrays,
   inline tables, quoted keys, escapes) lives in `std_c/toml_min.h`; the
   public surface and ownership stay in PenguScript.
 - **Dates are strings.** A manifest/lockfile never needs calendar arithmetic;
   date/time values keep their original text and kind `TomlKind.STRING`.
 - **Errors carry line numbers.** `parse` returns `err("... line N")` instead of
   silently returning an empty document.

### `TOML_STRING`

> **TOML_STRING** : int

 Kind tags returned by `TomlEntry.kind`.

### `TOML_INT`

> **TOML_INT** : int

_Undocumented._

### `TOML_FLOAT`

> **TOML_FLOAT** : int

_Undocumented._

### `TOML_BOOL`

> **TOML_BOOL** : int

_Undocumented._

### `TOML_ARRAY`

> **TOML_ARRAY** : int

_Undocumented._

### `TOML_TABLE`

> **TOML_TABLE** : int

_Undocumented._

### `TOML_ARRAY_TABLE`

> **TOML_ARRAY_TABLE** : int

_Undocumented._

### `TomlEntry`

> rune TomlEntry

```pengu
    key as string
    value as string
    kind as int
```

 One flattened TOML key/value pair.

 `key` is a dotted path; array elements use `[n]`.  `kind` is one of the
 `TOML_*` constants above.

### `parse`

> **parse**(text: string) -> result of list of TomlEntry to string

 Parses `text` as TOML.

 ## Retorno
 `ok(entries)` on success, `err(message)` with a line number on failure.

 ## Memoria
 On success the caller owns every entry string and the list; release them with
 `free_entries`.

### `parse_file`

> **parse_file**(path: string) -> result of list of TomlEntry to string

 Parses the TOML file at `path`.

### `free_entries`

> **free_entries**(entries: list of TomlEntry) -> void

 Releases every string in `entries` and then the list itself.

### `find`

> **find**(entries: list of TomlEntry, key: string) -> int

 Returns the index of `key` in `entries`, or `-1`.

### `has`

> **has**(entries: list of TomlEntry, key: string) -> bool

 True when `entries` contains `key`.

### `get`

> **get**(entries: list of TomlEntry, key: string) -> string

 Returns a copy of the scalar value stored at `key` ("" when absent).

 ## Memoria
 The result is owned; release it with `banish`.

### `get_int`

> **get_int**(entries: list of TomlEntry, key: string, fallback: int) -> int

 Returns `key` as an int, or `fallback` when absent/unparseable.

### `get_float`

> **get_float**(entries: list of TomlEntry, key: string, fallback: float) -> float

 Returns `key` as a float, or `fallback` when absent/unparseable.

### `get_bool`

> **get_bool**(entries: list of TomlEntry, key: string, fallback: bool) -> bool

 Returns `key` as a bool, or `fallback` when absent.

### `get_array`

> **get_array**(entries: list of TomlEntry, key: string) -> list of string

 Returns every element of the array at `key` as owned strings.

 Elements are read from `key[0]`, `key[1]`, ... until the first gap.  A
 missing array returns an empty list.

 ## Memoria
 The list and every element are owned; release them with `free_strings`.

### `free_strings`

> **free_strings**(values: list of string) -> void

 Releases a list of strings returned by `get_array`.

### `keys_with_prefix`

> **keys_with_prefix**(entries: list of TomlEntry, prefix: string) -> list of string

 Returns every scalar key that starts with `prefix`.

### `stringify`

> **stringify**(entries: list of TomlEntry) -> string

 Serializes `entries` back to TOML text.

 Tables are emitted from their `TOML_TABLE` markers, scalar arrays are grouped
 from their `[n]` elements, and values are quoted/escaped according to their
 kind.  The result is deterministic (source order).

### `_toml_render_array`

> **_toml_render_array**(entries: list of TomlEntry, key: string) -> string

_Undocumented._

### `_toml_array_base`

> **_toml_array_base**(key: string) -> string

_Undocumented._

### `_toml_relative_key`

> **_toml_relative_key**(key: string, current: string) -> string

_Undocumented._

### `_toml_format_value`

> **_toml_format_value**(e: TomlEntry) -> string

_Undocumented._

### `_toml_quote`

> **_toml_quote**(s: string) -> string

_Undocumented._

### `_toml_parse`

> **_toml_parse**(text: string) -> ref to void

 ----------------------------------------------------------------------------
 C bridge
 ----------------------------------------------------------------------------

### `_toml_free`

> **_toml_free**(doc: ref to void) -> void

_Undocumented._

### `_toml_count`

> **_toml_count**(doc: ref to void) -> int

_Undocumented._

### `_toml_key`

> **_toml_key**(doc: ref to void, i: int) -> string

_Undocumented._

### `_toml_value`

> **_toml_value**(doc: ref to void, i: int) -> string

_Undocumented._

### `_toml_kind`

> **_toml_kind**(doc: ref to void, i: int) -> int

_Undocumented._

### `_toml_error`

> **_toml_error**(doc: ref to void) -> string

_Undocumented._

### `_toml_copy`

> **_toml_copy**(s: string) -> string

_Undocumented._

### `_toml_to_int`

> **_toml_to_int**(s: string, fallback: int) -> int

_Undocumented._

### `_toml_to_float`

> **_toml_to_float**(s: string, fallback: float) -> float

_Undocumented._

