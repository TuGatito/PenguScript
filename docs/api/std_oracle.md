# std.oracle

> Source: `std/oracle.pengu`

std/oracle.pengu — optional values (`maybe T`) and fallible computations
(`result of T to E`): builders, inspection, transformation, recovery and
conversion.

Every operation exists twice with the same semantics: as a method
(`calling m.map with f`) and as a module function
(`calling oracle.map_maybe with m, f`). The duplication is deliberate: the
module functions are the fallback where a method cannot be written (type
parameters in the return position, `where` bounds, the legacy bridges).

## Example
```pengu
import std.oracle

var port as maybe int is calling oracle.some_of with 8080
var label as string is calling port.describe          # "some(8080)"
var missing as maybe int is calling oracle.none_of of int
var fallback as int is calling missing.unwrap_or with 80
```

## Memory
A `maybe T` and a `result of T to E` own their payload, and the builders
(`some`, `ok_of`, `err_of`, `some_of`, `oracle.none_of`) hand that ownership to
the caller. `unwrap`, `unwrap_err`, `expect` and `expect_err` return a copy of
the stored value and leave the container valid, so the container is still the
caller's to release. Every returned `list` and every `Pair`/`Triple` is owned
by the caller and must be released with `banish`; `partition_results` returns
two owned lists inside its `Pair`, and the legacy `MaybeString`/`ResultString`
wrappers own their string field.

## Design notes
- **The reconstruction invariant (why nothing is returned as-is).** No
  function ever returns `self` or a container parameter directly: every
  container result is rebuilt (`some v`, `maybe none`, `calling ok_of with v`,
  `calling err_of with e`). PenguScript has no move semantics, so returning
  the same container would leave the receiver and the result aliasing one heap
  box, and the two owners would free it twice. The rebuild is an ownership
  decision, not a stylistic one.
- **No `map_or`/`inspect` convenience methods.** They were prototyped during
  this rewrite and dropped: adding a `map_or` method to the `maybe` and
  `result` enchantings makes the compiler resolve `map`, `filter` and
  `map_err` callbacks to the wrong C symbol (`maybe_int_map_or_int`), so the
  existing callback API stops compiling. Keeping the 1.x surface intact wins
  over extra helpers until method lookup is fixed.
- **Nothing moves out of the runtime header.** `pengu_maybe_*` and
  `pengu_result_*` stay in `pengu_runtime.h`: the code generator emits them
  from every module, not only from `oracle`, so they are ABI-critical.
- **No tuples.** Operations that must return two values use the generic runes
  `Pair` and `Triple`, defined in this module
  (`oracle.Pair of int and string`). `Pair` derives `Par`, `Vinculum`,
  `Imago` and `Nexus`, so it can be compared and used as a `map` key.
- **Type parameters in the return position are not inferred.** `none_of shard
  T` reports `E0005`, so callers name the type (`calling none_of of int`); that
  is why the typed builders `none_int`, `none_string`, `none_float` and
  `none_bool` survive.
- **No `where` inside methods**, so an operation that needs a bound stays a
  module-level `weave shard T where T: ...`.
- **`flatten` cannot collapse `maybe maybe U`.** The shard binds to the
  receiver's element and methods have no `where`; `flatten` therefore re-boxes
  the payload in a fresh container. Use `and_then` to chain for real.
- **Module functions come in two flavours.** A `weave shard T` that merely
  delegates to a generic method emits unspecialised C, and a name of the form
  `<family>_<method>` is mistaken for a method specialisation; hence the
  suffixed names (`unwrap_maybe`) and the reimplemented bodies.
- **Documentary deprecation, not enforced.** The toolchain *does* support the
  real `@deprecated("Use X instead")` attribute (it emits `W0006`), but the
  aliases here use the docstring convention `## @deprecated Use X instead.`
  and therefore emit no warning. Turning it into a real attribute would first
  require migrating the internal callers (`result_ok_string` and
  `result_err_string` in `std.ward`); the inventory with replacements and
  removal versions lives in `docs/DEPRECATIONS.md`.
- **`result` constructors are intrinsics.** `ok_of` / `err_of` are compiler
  builtins (both the bare form and `oracle.ok_of` / `oracle.err_of`) and need
  type context: an `as result of T to E` binding or a `return` from a `weave`
  that declares that type. They are not defined here.
- **Internal tests.** The harness is private (`_expect*` over `spark.panic`)
  because `import std.ward` would create a cycle (`E0004`).

## Migration
2.0.0 rewrites the module in Pengunic style with English prose. Every public
symbol of the 1.x line is preserved, including the legacy 0.14.x
`Maybe*`/`Result*` runes, their enchantings and the module functions that carry
the `## @deprecated` docstring markers. No signature and no observable result
changed: only the documentation language and the local style (`let` over
`var`, `judge`, `if c then a else b`) did. The optional `map_or`/`inspect`
helpers were prototyped and dropped (see the design notes), so the public
surface is exactly the 1.x surface.

---

### `ORACLE_VERSION`

> **ORACLE_VERSION** : string

 Revision of the `oracle` API.

 Deliberately not the toolchain version: it only moves when an `oracle`
 signature changes.

### `Pair`

> rune Pair

```pengu
    first as A
    second as B
```

 Generic pair of values; the base of every operation that returns two things.

 ## Parámetros
 - `A`: the type of `first`.
 - `B`: the type of `second`.

 ## Retorno
 A value rune deriving `Par` (structural equality), `Vinculum` (ordering),
 `Imago` (rendering) and `Nexus` (hashing), so a `Pair` can be compared and
 used as a `map` key.

 ## Ejemplo
 ```pengu
 var p as oracle.Pair of int and string with:
     set .first is 1
     set .second is "one"
 ```

### `Triple`

> rune Triple

```pengu
    first as A
    second as B
    third as C
```

 Generic triple of values; used for three-way partitions.

 ## Parámetros
 - `A`: the type of `first`.
 - `B`: the type of `second`.
 - `C`: the type of `third`.

 ## Retorno
 A value rune deriving `Par`, `Vinculum`, `Imago` and `Nexus`, like `Pair`.

### `is_some`

> **is_some**() -> bool

 Returns `true` when the container holds a value (alias of the
 `is_present` field).

 ## Retorno
 `true` when present, `false` when empty. The receiver is borrowed.

 ## Ejemplo
 ```pengu
 calling m.is_some     # true for `some(3)`
 ```

### `is_none`

> **is_none**() -> bool

 Returns `true` when the container is empty.

 ## Retorno
 `true` when empty, `false` when present. The receiver is borrowed.

 ## Ejemplo
 ```pengu
 calling n.is_none     # true for `maybe none`
 ```

### `unwrap`

> **unwrap**() -> T

 Returns the stored value, or panics with `"Unwrapped none maybe"` when the
 container is empty.

 ## Retorno
 A copy of the payload; the container stays valid and owned by the caller.

 ## Ejemplo
 ```pengu
 calling m.unwrap      # 3 for `some(3)`
 ```

### `unwrap_or`

> **unwrap_or**(fallback: T) -> T

 Returns the stored value, or `fallback` when the container is empty.

 ## Parámetros
 - `fallback`: the `T` returned when there is no value.

 ## Retorno
 The payload, or `fallback`; the container itself is untouched.

 ## Ejemplo
 ```pengu
 calling n.unwrap_or with 0     # 0 for `maybe none`
 ```

### `unwrap_or_else`

> **unwrap_or_else**(f: weave with  into T) -> T

 Returns the stored value, or the result of invoking `f` when empty.

 ## Parámetros
 - `f`: a zero-argument weave producing the `T` to use as fallback.

 ## Retorno
 The payload, or `f()`; `f` is only invoked when the container is empty.

### `expect`

> **expect**(message: string) -> T

 Returns the stored value, or panics with `message` when empty.

 ## Parámetros
 - `message`: the text passed to `spark.panic` when there is no value.

 ## Retorno
 A copy of the payload; the container stays valid.

 ## Ejemplo
 ```pengu
 calling m.expect with "expected a port"
 ```

### `value_or`

> **value_or**(fallback: T) -> T

 Alias of `unwrap_or`: the stored value or `fallback`.

 ## Parámetros
 - `fallback`: the `T` returned when there is no value.

 ## Retorno
 The payload, or `fallback`.

### `map`

> **map**(f: weave with x: T into U) -> maybe U

 Applies `f` to the payload, keeping the container.

 ## Parámetros
 - `f`: a weave from `T` into `U`; called only when a value is stored.

 ## Retorno
 A rebuilt `some(f(v))` when present, `maybe none` when empty; the result
 is never the receiver, per the reconstruction invariant.

 ## Ejemplo
 ```pengu
 var doubled as maybe int is calling m.map of int with double_it
 ```

### `filter`

> **filter**(predicate: weave with x: T into bool) -> maybe T

 Keeps the payload only when `predicate` returns `true`.

 ## Parámetros
 - `predicate`: a weave from `T` into `bool`, called only when a value is
   stored.

 ## Retorno
 A rebuilt `some(v)` when the predicate accepts, `maybe none` otherwise.

 ## Ejemplo
 ```pengu
 var evens as maybe int is calling m.filter with is_even
 ```

### `and_then`

> **and_then**(f: weave with x: T into maybe U) -> maybe U

 Chains `f`, which itself produces a `maybe U` (so containers never nest).

 ## Parámetros
 - `f`: a weave from `T` into `maybe U`; called only when a value is
   stored.

 ## Retorno
 The `maybe U` rebuilt from `f`'s payload, or `maybe none`.

 ## Ejemplo
 ```pengu
 var halved as maybe int is calling m.and_then of int with half_of
 ```

### `or_else`

> **or_else**(fallback: maybe T) -> maybe T

 Returns this container when it has a value; otherwise `fallback`.

 ## Parámetros
 - `fallback`: the optional consulted when this one is empty.

 ## Retorno
 A rebuilt container holding whichever payload was found.

 ## Ejemplo
 ```pengu
 var chosen as maybe int is calling n.or_else with alt
 ```

### `and`

> **and**(other: maybe T) -> maybe T

 Returns `other` only when this container has a value.

 ## Parámetros
 - `other`: the optional whose payload is kept.

 ## Retorno
 A rebuilt `some` with `other`'s payload when both are present, `maybe
 none` otherwise.

### `or`

> **or**(other: maybe T) -> maybe T

 Returns this container when it has a value; otherwise `other`.

 ## Parámetros
 - `other`: the optional consulted when this one is empty.

 ## Retorno
 A rebuilt container holding the first payload available.

### `to_result`

> **to_result**(error_value: string) -> result of T to string

 Promotes the container to `result of T to string`.

 ## Parámetros
 - `error_value`: the error stored when the container is empty.

 ## Retorno
 `ok(payload)` when present, `err(error_value)` when empty.

 ## Ejemplo
 ```pengu
 var r as result of int to string is calling m.to_result with "missing"
 ```

### `to_list`

> **to_list**() -> list of T

 Returns a one-element list with the payload, or an empty list.

 ## Retorno
 A newly allocated owned `list of T`; release it with `banish`.

 ## Ejemplo
 ```pengu
 var xs as list of int is calling m.to_list     # [3]
 ```

### `describe`

> **describe**() -> string

 Returns a readable rendering of the container.

 ## Retorno
 An owned string: `"some(v)"` when present, `"none"` when empty. Release it
 with `banish`.

 ## Ejemplo
 ```pengu
 calling m.describe     # "some(3)"
 ```

### `iter`

> **iter**() -> list of T

 Alias of `to_list`: the payload as a zero- or one-element list.

 ## Retorno
 A newly allocated owned `list of T`; release it with `banish`.

### `zip`

> **zip**(other: maybe U) -> maybe Pair__T__U

 Combines two present optionals into a `Pair`.

 ## Parámetros
 - `other`: the second optional.

 ## Retorno
 `some(Pair)` when both are present, `maybe none` otherwise. The `Pair` is
 owned by the caller.

 ## Ejemplo
 ```pengu
 var both as maybe Pair of int and string is calling a.zip of string with b
 ```

### `flatten`

> **flatten**() -> maybe T

 Re-boxes the payload in a fresh container (structural identity).

 ## Retorno
 `some(v)` when present, `maybe none` when empty. It cannot collapse
 `maybe maybe U`; use `and_then` for that.

 ## Ejemplo
 ```pengu
 var same as maybe int is calling m.flatten
 ```

### `is_ok`

> **is_ok**() -> bool

 Returns `true` when the result represents success (alias of the `is_ok`
 field).

 ## Retorno
 `true` for `ok`, `false` for `err`. The receiver is borrowed.

 ## Ejemplo
 ```pengu
 calling r.is_ok     # true for `ok(3)`
 ```

### `is_err`

> **is_err**() -> bool

 Returns `true` when the result represents an error.

 ## Retorno
 `true` for `err`, `false` for `ok`.

 ## Ejemplo
 ```pengu
 calling r.is_err     # true for `err("boom")`
 ```

### `unwrap_err`

> **unwrap_err**() -> E

 Returns the stored error, or panics with `"unwrap_err on ok result"` when
 the result is `ok`.

 ## Retorno
 A copy of the stored error; the result stays valid.

 ## Ejemplo
 ```pengu
 calling r.unwrap_err     # "boom" for `err("boom")`
 ```

### `expect_err`

> **expect_err**(message: string) -> E

 Returns the stored error, or panics with `message` when the result is
 `ok`.

 ## Parámetros
 - `message`: the text passed to `spark.panic` for `ok`.

 ## Retorno
 A copy of the stored error; the result stays valid.

### `map_err`

> **map_err**(f: weave with x: E into F) -> result of T to F

 Applies `f` to the error, propagating success.

 ## Parámetros
 - `f`: a weave from `E` into `F`, called only for `err`.

 ## Retorno
 A rebuilt `result of T to F`: `err(f(e))` or the original success.

### `ok`

> **ok**() -> maybe T

 Discards the error: a `maybe` with the success payload.

 ## Retorno
 `some(v)` for `ok`, `maybe none` for `err`.

 ## Ejemplo
 ```pengu
 var m as maybe int is calling r.ok
 ```

### `err`

> **err**() -> maybe E

 Discards the success: a `maybe` with the error.

 ## Retorno
 `some(e)` for `err`, `maybe none` for `ok`.

### `to_maybe`

> **to_maybe**() -> maybe T

 Alias of `ok`: the success payload as a `maybe T`.

 ## Retorno
 `some(v)` for `ok`, `maybe none` for `err`.

### `MaybeInt`

> rune MaybeInt

```pengu
    is_present as bool
    value as int
```

 @deprecated Legacy int optional (`is_present` + `value` fields; `value` is 0 when empty). Use `maybe T` / `result of T to E` instead.
 Legacy int optional: `is_present` is true when a value is stored, and `value`
 holds it.

### `MaybeFloat`

> rune MaybeFloat

```pengu
    is_present as bool
    value as float
```

 @deprecated Legacy float optional (`is_present` + `value` fields; `value` is 0.0 when empty). Use `maybe T` / `result of T to E` instead.
 Legacy float optional: `is_present` is true when a value is stored, and
 `value` holds it (0.0 when empty).

### `MaybeString`

> rune MaybeString

```pengu
    is_present as bool
    value as string
```

 @deprecated Legacy string optional (`is_present` + `value` fields; `value` is "" when empty). Use `maybe T` / `result of T to E` instead.
 Legacy string optional: `is_present` is true when a value is stored, and
 `value` holds it ("" when empty). The payload string is owned by the wrapper.

### `ResultInt`

> rune ResultInt

```pengu
    is_ok as bool
    value as int
    error_msg as string
```

 @deprecated Legacy int result (`is_ok`, `value`, `error_msg` fields). Use `maybe T` / `result of T to E` instead.
 Legacy fallible int: `is_ok` is true when `value` is meaningful, false when the
 operation failed and `error_msg` describes why.

### `ResultString`

> rune ResultString

```pengu
    is_ok as bool
    value as string
    error_msg as string
```

 @deprecated Legacy string result (`is_ok`, `value`, `error_msg` fields). Use `maybe T` / `result of T to E` instead.
 Legacy fallible string: `is_ok` is true when `value` is meaningful, false when
 the operation failed and `error_msg` describes why. The payload string is
 owned by the wrapper.

### `is_present`

> **is_present**() -> bool

 Returns `true` when the wrapper holds a value (mirrors the `is_present`
 field).

 ## Retorno
 `true` when present, `false` when empty.

### `maybe_some_int`

> **maybe_some_int**(val: int) -> MaybeInt

 @deprecated Use `oracle.some_of shard T` instead.
 Builds a present `MaybeInt` holding `val`.

 ## Retorno
 A `MaybeInt` with `is_present` true and `value` set to `val`.

### `maybe_none_int`

> **maybe_none_int**() -> MaybeInt

 @deprecated Use `oracle.none_of of int` instead.
 Builds an empty `MaybeInt`.

 ## Retorno
 A `MaybeInt` with `is_present` false and `value` 0.

### `maybe_some_string`

> **maybe_some_string**(val: string) -> MaybeString

 @deprecated Use `oracle.some_of shard T` instead.
 Builds a present `MaybeString` holding `val`.

 ## Retorno
 A `MaybeString` with `is_present` true and `value` set to `val`.

### `maybe_none_string`

> **maybe_none_string**() -> MaybeString

 @deprecated Use `oracle.none_of of string` instead.
 Builds an empty `MaybeString`.

 ## Retorno
 A `MaybeString` with `is_present` false and `value` "".

### `result_ok_int`

> **result_ok_int**(val: int) -> ResultInt

 @deprecated Use the `ok_of` intrinsic (`calling ok_of with v`) instead.
 Builds a successful `ResultInt` holding `val`.

 ## Retorno
 A `ResultInt` with `is_ok` true, `value` set to `val` and `error_msg` "".

### `result_err_int`

> **result_err_int**(msg: string) -> ResultInt

 @deprecated Use the `err_of` intrinsic (`calling err_of with e`) instead.
 Builds a failed `ResultInt` carrying `msg`.

 ## Retorno
 A `ResultInt` with `is_ok` false, `value` 0 and `error_msg` set to `msg`.

### `result_ok_string`

> **result_ok_string**(val: string) -> ResultString

 @deprecated Use the `ok_of` intrinsic (`calling ok_of with v`) instead.
 Builds a successful `ResultString` holding `val`.

 ## Retorno
 A `ResultString` with `is_ok` true, `value` set to `val` and `error_msg` "".

### `result_err_string`

> **result_err_string**(msg: string) -> ResultString

 @deprecated Use the `err_of` intrinsic (`calling err_of with e`) instead.
 Builds a failed `ResultString` carrying `msg`.

 ## Retorno
 A `ResultString` with `is_ok` false, `value` "" and `error_msg` set to `msg`.

### `some_int`

> **some_int**(val: int) -> maybe int

 @deprecated Use `oracle.some_of shard T` instead.
 Boxes an `int` in a native `maybe int`.

 ## Retorno
 `some(val)`, owned by the caller.

### `some_float`

> **some_float**(val: float) -> maybe float

 @deprecated Use `oracle.some_of shard T` instead.
 Boxes a `float` in a native `maybe float`.

 ## Retorno
 `some(val)`, owned by the caller.

### `some_string`

> **some_string**(val: string) -> maybe string

 @deprecated Use `oracle.some_of shard T` instead.
 Boxes a `string` in a native `maybe string`.

 ## Retorno
 `some(val)`, owned by the caller.

### `some_bool`

> **some_bool**(val: bool) -> maybe bool

 @deprecated Use `oracle.some_of shard T` instead.
 Boxes a `bool` in a native `maybe bool`.

 ## Retorno
 `some(val)`, owned by the caller.

### `none_int`

> **none_int**() -> maybe int

 @deprecated Use `oracle.none_of of int` instead.
 Builds an empty native `maybe int`.

 ## Retorno
 `maybe none` with element type `int`.

### `none_float`

> **none_float**() -> maybe float

 @deprecated Use `oracle.none_of of float` instead.
 Builds an empty native `maybe float`.

 ## Retorno
 `maybe none` with element type `float`.

### `none_string`

> **none_string**() -> maybe string

 @deprecated Use `oracle.none_of of string` instead.
 Builds an empty native `maybe string`.

 ## Retorno
 `maybe none` with element type `string`.

### `none_bool`

> **none_bool**() -> maybe bool

 @deprecated Use `oracle.none_of of bool` instead.
 Builds an empty native `maybe bool`.

 ## Retorno
 `maybe none` with element type `bool`.

### `unwrap_int`

> **unwrap_int**(m: maybe int) -> int

 @deprecated Use `oracle.unwrap_maybe shard T` instead.
 Returns the payload of `m`, or panics with `"Unwrapped none maybe int"` when
 `m` is empty.

 ## Retorno
 The stored `int`.

### `unwrap_float`

> **unwrap_float**(m: maybe float) -> float

 @deprecated Use `oracle.unwrap_maybe shard T` instead.
 Returns the payload of `m`, or panics with `"Unwrapped none maybe float"` when
 `m` is empty.

 ## Retorno
 The stored `float`.

### `unwrap_string`

> **unwrap_string**(m: maybe string) -> string

 @deprecated Use `oracle.unwrap_maybe shard T` instead.
 Returns the payload of `m`, or panics with `"Unwrapped none maybe string"`
 when `m` is empty.

 ## Retorno
 The stored string.

### `unwrap_bool`

> **unwrap_bool**(m: maybe bool) -> bool

 @deprecated Use `oracle.unwrap_maybe shard T` instead.
 Returns the payload of `m`, or panics with `"Unwrapped none maybe bool"` when
 `m` is empty.

 ## Retorno
 The stored `bool`.

### `unwrap_or_int`

> **unwrap_or_int**(m: maybe int, fallback: int) -> int

 @deprecated Use `oracle.unwrap_or_maybe shard T` instead.
 Returns the payload of `m`, or `fallback` when `m` is empty.

 ## Retorno
 The stored value, or `fallback`.

### `unwrap_or_float`

> **unwrap_or_float**(m: maybe float, fallback: float) -> float

 @deprecated Use `oracle.unwrap_or_maybe shard T` instead.
 Returns the payload of `m`, or `fallback` when `m` is empty.

 ## Retorno
 The stored value, or `fallback`.

### `unwrap_or_string`

> **unwrap_or_string**(m: maybe string, fallback: string) -> string

 @deprecated Use `oracle.unwrap_or_maybe shard T` instead.
 Returns the payload of `m`, or `fallback` when `m` is empty.

 ## Retorno
 The stored value, or `fallback`.

### `unwrap_or_bool`

> **unwrap_or_bool**(m: maybe bool, fallback: bool) -> bool

 @deprecated Use `oracle.unwrap_or_maybe shard T` instead.
 Returns the payload of `m`, or `fallback` when `m` is empty.

 ## Retorno
 The stored value, or `fallback`.

### `to_native_int`

> **to_native_int**(m: MaybeInt) -> maybe int

 @deprecated Use the native `maybe int` API (`calling m.is_some` / `calling m.unwrap`) instead.
 Lifts a legacy `MaybeInt` into a native `maybe int`.

 ## Retorno
 `some(value)` when the wrapper is present, `maybe none` otherwise.

### `from_native_int`

> **from_native_int**(m: maybe int) -> MaybeInt

 @deprecated Use the native `maybe int` API (`oracle.some_of`) instead.
 Lowers a native `maybe int` into a legacy `MaybeInt`.

 ## Retorno
 A `MaybeInt` mirroring the native container's presence and value.

### `to_native_string`

> **to_native_string**(m: MaybeString) -> maybe string

 @deprecated Use the native `maybe string` API instead.
 Lifts a legacy `MaybeString` into a native `maybe string`.

 ## Retorno
 `some(value)` when the wrapper is present, `maybe none` otherwise.

### `from_native_string`

> **from_native_string**(m: maybe string) -> MaybeString

 @deprecated Use the native `maybe string` API instead.
 Lowers a native `maybe string` into a legacy `MaybeString`.

 ## Retorno
 A `MaybeString` mirroring the native container's presence and value.

### `describe_maybe_int`

> **describe_maybe_int**(m: maybe int) -> string

 @deprecated Use `oracle.describe_optional shard T` instead.
 Renders a native `maybe int` as `"some(v)"` or `"none"`.

 ## Retorno
 The rendered string.

### `describe_maybe_string`

> **describe_maybe_string**(m: maybe string) -> string

 @deprecated Use `oracle.describe_optional shard T` instead.
 Renders a native `maybe string` as `"some(\"v\")"` or `"none"`.

 ## Retorno
 The rendered string, with the payload quoted.

### `describe_maybe_float`

> **describe_maybe_float**(m: maybe float) -> string

 @deprecated Use `oracle.describe_optional shard T` instead.
 Renders a native `maybe float` as `"some(v)"` or `"none"`.

 ## Retorno
 The rendered string.

### `describe_maybe_bool`

> **describe_maybe_bool**(m: maybe bool) -> string

 @deprecated Use `oracle.describe_optional shard T` instead.
 Renders a native `maybe bool` as `"some(v)"` or `"none"`.

 ## Retorno
 The rendered string.

### `describe_int`

> **describe_int**(m: MaybeInt) -> string

 @deprecated Use `oracle.describe_optional shard T` instead.
 Renders a legacy `MaybeInt` as `"some(v)"` or `"none"`.

 ## Retorno
 The rendered string.

### `describe_string`

> **describe_string**(m: MaybeString) -> string

 @deprecated Use `oracle.describe_optional shard T` instead.
 Renders a legacy `MaybeString` as `"some(\"v\")"` or `"none"`.

 ## Retorno
 The rendered string, with the payload quoted.

### `describe_result_int`

> **describe_result_int**(r: ResultInt) -> string

 @deprecated Use `oracle.describe_result shard T and E` instead.
 Renders a legacy `ResultInt` as `"ok(v)"` or `"err(e)"`.

 ## Retorno
 The rendered string.

### `describe_result_string`

> **describe_result_string**(r: ResultString) -> string

 @deprecated Use `oracle.describe_result shard T and E` instead.
 Renders a legacy `ResultString` as `"ok(\"v\")"` or `"err(e)"`.

 ## Retorno
 The rendered string, with a successful payload quoted.

### `is_ok_int_result`

> **is_ok_int_result**(r: result of int to string) -> bool

 @deprecated Use `oracle.is_ok_result shard T and E` instead.
 Returns `true` when the native result `r` is `ok`.

 ## Retorno
 The `is_ok` field of `r`.

### `is_err_int_result`

> **is_err_int_result**(r: result of int to string) -> bool

 @deprecated Use `oracle.is_err_result shard T and E` instead.
 Returns `true` when the native result `r` is `err`.

 ## Retorno
 `true` for `err`, `false` for `ok`.

### `unwrap_int_result`

> **unwrap_int_result**(r: result of int to string) -> int

 @deprecated Use `oracle.unwrap_result shard T and E` instead.
 Returns the success payload of `r`, or panics with the stored error when `r`
 is `err`.

 ## Retorno
 The stored `int` for `ok`.

### `unwrap_or_int_result`

> **unwrap_or_int_result**(r: result of int to string, fallback: int) -> int

 @deprecated Use `oracle.unwrap_or_result shard T and E` instead.
 Returns the success payload of `r`, or `fallback` when `r` is `err`.

 ## Retorno
 The stored `int`, or `fallback`.

### `some_of`

> **some_of**(value: T) -> maybe T

 Wraps `value` in a present `maybe T`.

 ## Parámetros
 - `value`: the payload to box.

 ## Retorno
 `some(value)`, owned by the caller.

 ## Ejemplo
 ```pengu
 var m as maybe int is calling oracle.some_of with 42
 ```

### `none_of`

> **none_of**() -> maybe T

 Returns an empty `maybe T`. The type argument must be explicit.

 ## Retorno
 `maybe none` with element type `T`.

 ## Ejemplo
 ```pengu
 var m as maybe int is calling oracle.none_of of int
 ```

### `is_some_maybe`

> **is_some_maybe**(m: maybe T) -> bool

 Returns `true` when `m` holds a value.

 ## Parámetros
 - `m`: the optional to inspect. Borrowed.

 ## Retorno
 `true` when present, `false` when empty. Functional alias of `m.is_some`.

### `is_none_maybe`

> **is_none_maybe**(m: maybe T) -> bool

 Returns `true` when `m` is empty.

 ## Parámetros
 - `m`: the optional to inspect. Borrowed.

 ## Retorno
 `true` when empty, `false` when present. Functional alias of `m.is_none`.

### `unwrap_maybe`

> **unwrap_maybe**(m: maybe T) -> T

 Returns the payload of `m`, or panics with `"Unwrapped none maybe"` when `m`
 is empty.

 ## Parámetros
 - `m`: the optional to extract from. Borrowed.

 ## Retorno
 A copy of the payload.

### `unwrap_or_maybe`

> **unwrap_or_maybe**(m: maybe T, fallback: T) -> T

 Returns the payload of `m`, or `fallback` when `m` is empty.

 ## Parámetros
 - `m`: the optional to extract from. Borrowed.
 - `fallback`: the `T` returned when `m` is empty.

 ## Retorno
 The payload, or `fallback`.

### `unwrap_or_else_maybe`

> **unwrap_or_else_maybe**(m: maybe T, f: weave with  into T) -> T

 Returns the payload of `m`, or the result of invoking `f` when `m` is empty.

 ## Parámetros
 - `m`: the optional to extract from. Borrowed.
 - `f`: a zero-argument weave producing the `T` to use as fallback.

 ## Retorno
 The payload, or `f()`; `f` is only invoked when `m` is empty.

### `expect_maybe`

> **expect_maybe**(m: maybe T, message: string) -> T

 Returns the payload of `m`, or panics with `message` when `m` is empty.

 ## Parámetros
 - `m`: the optional to extract from. Borrowed.
 - `message`: the text passed to `spark.panic` when `m` is empty.

 ## Retorno
 A copy of the payload.

### `value_or_maybe`

> **value_or_maybe**(m: maybe T, fallback: T) -> T

 Alias of `unwrap_or_maybe`: the payload of `m`, or `fallback`.

 ## Parámetros
 - `m`: the optional to extract from. Borrowed.
 - `fallback`: the `T` returned when `m` is empty.

 ## Retorno
 The payload, or `fallback`.

### `map_maybe`

> **map_maybe**(m: maybe T, f: weave with x: T into U) -> maybe U

 Applies `f` to the payload of `m`, keeping the container.

 ## Parámetros
 - `m`: the optional to transform. Borrowed.
 - `f`: a weave from `T` into `U`; called only when `m` is present.

 ## Retorno
 A rebuilt `some(f(v))` when present, `maybe none` when empty.

### `filter_maybe`

> **filter_maybe**(m: maybe T, predicate: weave with x: T into bool) -> maybe T

 Keeps the payload of `m` only when `predicate` returns `true`.

 ## Parámetros
 - `m`: the optional to filter. Borrowed.
 - `predicate`: a weave from `T` into `bool`; called only when `m` is present.

 ## Retorno
 A rebuilt `some(v)` when the predicate accepts, `maybe none` otherwise.

### `and_then_maybe`

> **and_then_maybe**(m: maybe T, f: weave with x: T into maybe U) -> maybe U

 Chains `f` over the payload of `m` (so containers never nest).

 ## Parámetros
 - `m`: the optional to transform. Borrowed.
 - `f`: a weave from `T` into `maybe U`; called only when `m` is present.

 ## Retorno
 The `maybe U` rebuilt from `f`'s payload, or `maybe none`.

### `or_else_maybe`

> **or_else_maybe**(m: maybe T, fallback: maybe T) -> maybe T

 Returns `m` when it has a value; otherwise `fallback`.

 ## Parámetros
 - `m`: the first optional. Borrowed.
 - `fallback`: the optional consulted when `m` is empty.

 ## Retorno
 A rebuilt container holding whichever payload was found.

### `and_maybe`

> **and_maybe**(left: maybe T, right: maybe T) -> maybe T

 Returns `right` only when `left` has a value.

 ## Parámetros
 - `left`: the optional that gates the result. Borrowed.
 - `right`: the optional whose payload is kept.

 ## Retorno
 A rebuilt `some` with `right`'s payload when both are present, `maybe none`
 otherwise.

### `or_maybe`

> **or_maybe**(left: maybe T, right: maybe T) -> maybe T

 Returns `left` when it has a value; otherwise `right`.

 ## Parámetros
 - `left`: the first optional. Borrowed.
 - `right`: the optional consulted when `left` is empty.

 ## Retorno
 A rebuilt container holding the first payload available.

### `to_result_maybe`

> **to_result_maybe**(m: maybe T, error_value: string) -> result of T to string

 Promotes `m` to `result of T to string`, using `error_value` as the error.

 ## Parámetros
 - `m`: the optional to promote. Borrowed.
 - `error_value`: the error stored when `m` is empty.

 ## Retorno
 `ok(payload)` when present, `err(error_value)` when empty.

### `to_list_maybe`

> **to_list_maybe**(m: maybe T) -> list of T

 Returns a one-element list with the payload of `m`, or an empty list.

 ## Parámetros
 - `m`: the optional to convert. Borrowed.

 ## Retorno
 A newly allocated owned `list of T`; release it with `banish`.

### `describe_optional`

> **describe_optional**(m: maybe T) -> string

 Renders `m` as `"some(v)"` or `"none"`.

 ## Parámetros
 - `m`: the optional to render. Borrowed.

 ## Retorno
 The rendered string.

### `iter_maybe`

> **iter_maybe**(m: maybe T) -> list of T

 Alias of `to_list_maybe`.

 ## Parámetros
 - `m`: the optional to convert. Borrowed.

 ## Retorno
 A newly allocated owned `list of T`; release it with `banish`.

### `zip_maybe`

> **zip_maybe**(left: maybe T, right: maybe U) -> maybe Pair__T__U

 Combines two present optionals into a `Pair of T and U`.

 ## Parámetros
 - `left`: the first optional. Borrowed.
 - `right`: the second optional. Borrowed.

 ## Retorno
 `some(Pair)` when both are present, `maybe none` otherwise. The `Pair` is
 owned by the caller.

### `flatten_maybe`

> **flatten_maybe**(m: maybe T) -> maybe T

 Re-boxes the payload of `m` in a fresh container.

 ## Parámetros
 - `m`: the optional to re-box. Borrowed.

 ## Retorno
 `some(v)` when present, `maybe none` when empty; it cannot collapse
 `maybe maybe U`.

### `is_ok_result`

> **is_ok_result**(r: result of T to E) -> bool

 Returns `true` when `r` represents success.

 ## Parámetros
 - `r`: the result to classify. Borrowed.

 ## Retorno
 `true` for `ok`, `false` for `err`. Functional alias of `r.is_ok`.

### `is_err_result`

> **is_err_result**(r: result of T to E) -> bool

 Returns `true` when `r` represents an error.

 ## Parámetros
 - `r`: the result to classify. Borrowed.

 ## Retorno
 `true` for `err`, `false` for `ok`. Functional alias of `r.is_err`.

### `unwrap_result`

> **unwrap_result**(r: result of T to E) -> T

 Returns the success payload of `r`, or panics with `"Unwrapped err result"`
 when `r` is `err`.

 ## Parámetros
 - `r`: the result to extract from. Borrowed.

 ## Retorno
 A copy of the success payload.

### `unwrap_err_result`

> **unwrap_err_result**(r: result of T to E) -> E

 Returns the error of `r`, or panics with `"unwrap_err on ok result"` when `r`
 is `ok`.

 ## Parámetros
 - `r`: the result to extract from. Borrowed.

 ## Retorno
 A copy of the stored error.

### `unwrap_or_result`

> **unwrap_or_result**(r: result of T to E, fallback: T) -> T

 Returns the success payload of `r`, or `fallback` when `r` is `err`.

 ## Parámetros
 - `r`: the result to extract from. Borrowed.
 - `fallback`: the `T` returned for `err`.

 ## Retorno
 The success payload, or `fallback`.

### `unwrap_or_else_result`

> **unwrap_or_else_result**(r: result of T to E, f: weave with x: E into T) -> T

 Returns the success payload of `r`, or `f(error)` when `r` is `err`.

 ## Parámetros
 - `r`: the result to extract from. Borrowed.
 - `f`: a weave from `E` into `T`, called only for `err`.

 ## Retorno
 The success payload, or the value produced by `f`.

### `expect_result`

> **expect_result**(r: result of T to E, message: string) -> T

 Returns the success payload of `r`, or panics with `message` when `r` is
 `err`.

 ## Parámetros
 - `r`: the result to extract from. Borrowed.
 - `message`: the text passed to `spark.panic` for `err`.

 ## Retorno
 A copy of the success payload.

### `expect_err_result`

> **expect_err_result**(r: result of T to E, message: string) -> E

 Returns the error of `r`, or panics with `message` when `r` is `ok`.

 ## Parámetros
 - `r`: the result to extract from. Borrowed.
 - `message`: the text passed to `spark.panic` for `ok`.

 ## Retorno
 A copy of the stored error.

### `map_result`

> **map_result**(r: result of T to E, f: weave with x: T into U) -> result of U to E

 Applies `f` to the success payload of `r`, propagating the error.

 ## Parámetros
 - `r`: the result to transform. Borrowed.
 - `f`: a weave from `T` into `U`, called only for `ok`.

 ## Retorno
 A rebuilt `result of U to E`: `ok(f(v))` or the original error.

### `map_err_result`

> **map_err_result**(r: result of T to E, f: weave with x: E into F) -> result of T to F

 Applies `f` to the error of `r`, propagating success.

 ## Parámetros
 - `r`: the result to transform. Borrowed.
 - `f`: a weave from `E` into `F`, called only for `err`.

 ## Retorno
 A rebuilt `result of T to F`: `err(f(e))` or the original success.

### `and_then_result`

> **and_then_result**(r: result of T to E, f: weave with x: T into result of U to E) -> result of U to E

 Chains `f` over the success payload of `r`.

 ## Parámetros
 - `r`: the result to chain from. Borrowed.
 - `f`: a weave from `T` into `result of U to E`, called only for `ok`.

 ## Retorno
 The rebuilt result produced by `f`, or the original error.

### `or_else_result`

> **or_else_result**(r: result of T to E, fallback: result of T to E) -> result of T to E

 Returns `r` when it is `ok`; otherwise `fallback` (same error type).

 ## Parámetros
 - `r`: the first result. Borrowed.
 - `fallback`: the result consulted when `r` is `err`.

 ## Retorno
 A rebuilt result holding whichever outcome was chosen.

### `ok_result`

> **ok_result**(r: result of T to E) -> maybe T

 Discards the error of `r`: a `maybe` with the success payload.

 ## Parámetros
 - `r`: the result to convert. Borrowed.

 ## Retorno
 `some(v)` for `ok`, `maybe none` for `err`.

### `err_result`

> **err_result**(r: result of T to E) -> maybe E

 Discards the success of `r`: a `maybe` with the error.

 ## Parámetros
 - `r`: the result to convert. Borrowed.

 ## Retorno
 `some(e)` for `err`, `maybe none` for `ok`.

### `to_maybe_result`

> **to_maybe_result**(r: result of T to E) -> maybe T

 Alias of `ok_result`: the success payload as a `maybe T`.

 ## Parámetros
 - `r`: the result to convert. Borrowed.

 ## Retorno
 `some(v)` for `ok`, `maybe none` for `err`.

### `to_list_result`

> **to_list_result**(r: result of T to E) -> list of T

 Returns a one-element list with the success payload of `r`, or an empty list.

 ## Parámetros
 - `r`: the result to convert. Borrowed.

 ## Retorno
 A newly allocated owned `list of T`; release it with `banish`.

### `describe_result`

> **describe_result**(r: result of T to E) -> string

 Renders `r` as `"ok(v)"` or `"err(e)"`.

 ## Parámetros
 - `r`: the result to render. Borrowed.

 ## Retorno
 The rendered string.

### `all_present`

> **all_present**(ms: list of maybe T) -> bool

 Returns `true` when every element of `ms` is present.

 ## Parámetros
 - `ms`: the list of optionals to scan. Borrowed.

 ## Retorno
 `true` for an empty list (vacuous truth) and for a list whose elements are all
 present, `false` as soon as one is empty.

### `first_present`

> **first_present**(ms: list of maybe T) -> maybe T

 Returns the first payload present in `ms`, or `maybe none`.

 ## Parámetros
 - `ms`: the list of optionals to scan, in order. Borrowed.

 ## Retorno
 A rebuilt `some(v)` for the first present element, `maybe none` when every
 element is empty.

### `any_present`

> **any_present**(ms: list of maybe T) -> bool

 Returns `true` when at least one element of `ms` is present.

 ## Parámetros
 - `ms`: the list of optionals to scan. Borrowed.

 ## Retorno
 `true` on the first present element, `false` when every element is empty.

### `collect_ok`

> **collect_ok**(rs: list of result of T to E) -> list of T

 Gathers the success payloads of `rs`, in order.

 ## Parámetros
 - `rs`: the list of results to scan. Borrowed.

 ## Retorno
 A newly allocated owned `list of T` with one entry per `ok`, in order; release
 it with `banish`.

### `collect_err`

> **collect_err**(rs: list of result of T to E) -> list of E

 Gathers the errors of `rs`, in order.

 ## Parámetros
 - `rs`: the list of results to scan. Borrowed.

 ## Retorno
 A newly allocated owned `list of E` with one entry per `err`, in order;
 release it with `banish`.

### `partition_results`

> **partition_results**(rs: list of result of T to E) -> Pair__list_T__list_E

 Splits `rs` into a `Pair` of successes and errors.

 ## Parámetros
 - `rs`: the list of results to partition. Borrowed.

 ## Retorno
 A `Pair` whose `first` is the owned `list of T` of successes (in order) and
 whose `second` is the owned `list of E` of errors (in order). The caller
 releases both lists with `banish`.

 ## Ejemplo
 ```pengu
 var p as oracle.Pair of list of int and list of string is calling oracle.partition_results with rs
 ```

### `_expect`

> **_expect**(cond: bool, label: string) -> void

 Test harness: panics with `label` when `cond` is false.

### `_expect_eq_int`

> **_expect_eq_int**(actual: int, expected: int, label: string) -> void

 Test harness: int equality.

### `_expect_eq_string`

> **_expect_eq_string**(actual: string, expected: string, label: string) -> void

 Test harness: string equality.

### `_expect_eq_bool`

> **_expect_eq_bool**(actual: bool, expected: bool, label: string) -> void

 Test harness: bool equality.

### `"maybe.is_some is true when a value is stored"`

> test "maybe.is_some is true when a value is stored"

 --- Tests ---
 Callback-driven operations are also exercised from `tests/test_oracle.py`.

### `"maybe.is_some is false when empty"`

> test "maybe.is_some is false when empty"

_Undocumented._

### `"maybe.is_none is true when empty"`

> test "maybe.is_none is true when empty"

_Undocumented._

### `"maybe.is_none is false when a value is stored"`

> test "maybe.is_none is false when a value is stored"

_Undocumented._

### `"maybe.unwrap returns the int payload"`

> test "maybe.unwrap returns the int payload"

_Undocumented._

### `"maybe.unwrap returns the string payload"`

> test "maybe.unwrap returns the string payload"

_Undocumented._

### `"maybe.unwrap_or returns the payload when present"`

> test "maybe.unwrap_or returns the payload when present"

_Undocumented._

### `"maybe.unwrap_or returns the fallback when empty"`

> test "maybe.unwrap_or returns the fallback when empty"

_Undocumented._

### `"maybe.value_or returns the payload when present"`

> test "maybe.value_or returns the payload when present"

_Undocumented._

### `"maybe.value_or returns the fallback when empty"`

> test "maybe.value_or returns the fallback when empty"

_Undocumented._

### `"maybe.expect returns the payload"`

> test "maybe.expect returns the payload"

_Undocumented._

### `"maybe.to_result produces ok with the payload"`

> test "maybe.to_result produces ok with the payload"

_Undocumented._

### `"maybe.to_result produces err when empty"`

> test "maybe.to_result produces err when empty"

_Undocumented._

### `"maybe.to_list has one element when a value is stored"`

> test "maybe.to_list has one element when a value is stored"

_Undocumented._

### `"maybe.to_list is empty without a value"`

> test "maybe.to_list is empty without a value"

_Undocumented._

### `"maybe.iter is an alias of to_list"`

> test "maybe.iter is an alias of to_list"

_Undocumented._

### `"maybe.describe renders a present value"`

> test "maybe.describe renders a present value"

_Undocumented._

### `"maybe.describe renders an empty container"`

> test "maybe.describe renders an empty container"

_Undocumented._

### `"maybe.zip combines two present optionals"`

> test "maybe.zip combines two present optionals"

_Undocumented._

### `"maybe.zip is empty when one side is empty"`

> test "maybe.zip is empty when one side is empty"

_Undocumented._

### `"maybe.flatten re-boxes a present payload"`

> test "maybe.flatten re-boxes a present payload"

_Undocumented._

### `"maybe.flatten of an empty optional is empty"`

> test "maybe.flatten of an empty optional is empty"

_Undocumented._

### `"maybe.or_else keeps the present payload"`

> test "maybe.or_else keeps the present payload"

_Undocumented._

### `"maybe.or_else uses the present fallback"`

> test "maybe.or_else uses the present fallback"

_Undocumented._

### `"maybe.or_else of two empty optionals is empty"`

> test "maybe.or_else of two empty optionals is empty"

_Undocumented._

### `"maybe.and returns the second when both are present"`

> test "maybe.and returns the second when both are present"

_Undocumented._

### `"maybe.and is empty when the second is missing"`

> test "maybe.and is empty when the second is missing"

_Undocumented._

### `"maybe.or returns the first when it is present"`

> test "maybe.or returns the first when it is present"

_Undocumented._

### `"maybe.or returns the second when the first is missing"`

> test "maybe.or returns the second when the first is missing"

_Undocumented._

### `"maybe.or of two empty optionals is empty"`

> test "maybe.or of two empty optionals is empty"

_Undocumented._

### `"result.is_ok classifies success"`

> test "result.is_ok classifies success"

_Undocumented._

### `"result.is_ok is false for err"`

> test "result.is_ok is false for err"

_Undocumented._

### `"result.is_err classifies an error"`

> test "result.is_err classifies an error"

_Undocumented._

### `"result.is_err is false for ok"`

> test "result.is_err is false for ok"

_Undocumented._

### `"result.unwrap returns the success payload"`

> test "result.unwrap returns the success payload"

_Undocumented._

### `"result.unwrap_err returns the error"`

> test "result.unwrap_err returns the error"

_Undocumented._

### `"result.unwrap_or returns the payload for ok"`

> test "result.unwrap_or returns the payload for ok"

_Undocumented._

### `"result.unwrap_or returns the fallback for err"`

> test "result.unwrap_or returns the fallback for err"

_Undocumented._

### `"result.expect returns the success payload"`

> test "result.expect returns the success payload"

_Undocumented._

### `"result.expect_err returns the error"`

> test "result.expect_err returns the error"

_Undocumented._

### `"result.ok turns success into a maybe"`

> test "result.ok turns success into a maybe"

_Undocumented._

### `"result.ok of an err is empty"`

> test "result.ok of an err is empty"

_Undocumented._

### `"result.err exposes the error as a maybe"`

> test "result.err exposes the error as a maybe"

_Undocumented._

### `"result.err of an ok is empty"`

> test "result.err of an ok is empty"

_Undocumented._

### `"result.to_maybe is an alias of ok"`

> test "result.to_maybe is an alias of ok"

_Undocumented._

### `"result.to_list has one element for ok"`

> test "result.to_list has one element for ok"

_Undocumented._

### `"result.to_list is empty for err"`

> test "result.to_list is empty for err"

_Undocumented._

### `"result.describe formats success"`

> test "result.describe formats success"

_Undocumented._

### `"result.describe formats an error"`

> test "result.describe formats an error"

_Undocumented._

### `"some_of boxes an int"`

> test "some_of boxes an int"

_Undocumented._

### `"some_of boxes a string"`

> test "some_of boxes a string"

_Undocumented._

### `"none_of with an explicit type builds an empty optional"`

> test "none_of with an explicit type builds an empty optional"

_Undocumented._

### `"is_some_maybe detects a present value"`

> test "is_some_maybe detects a present value"

_Undocumented._

### `"is_some_maybe is false for an empty optional"`

> test "is_some_maybe is false for an empty optional"

_Undocumented._

### `"is_none_maybe detects an empty optional"`

> test "is_none_maybe detects an empty optional"

_Undocumented._

### `"is_none_maybe is false with a value"`

> test "is_none_maybe is false with a value"

_Undocumented._

### `"unwrap_maybe returns the payload"`

> test "unwrap_maybe returns the payload"

_Undocumented._

### `"unwrap_or_maybe uses the present payload"`

> test "unwrap_or_maybe uses the present payload"

_Undocumented._

### `"unwrap_or_maybe uses the fallback when empty"`

> test "unwrap_or_maybe uses the fallback when empty"

_Undocumented._

### `"expect_maybe returns the payload"`

> test "expect_maybe returns the payload"

_Undocumented._

### `"value_or_maybe uses the present payload"`

> test "value_or_maybe uses the present payload"

_Undocumented._

### `"value_or_maybe uses the fallback when empty"`

> test "value_or_maybe uses the fallback when empty"

_Undocumented._

### `"or_else_maybe prefers the first value"`

> test "or_else_maybe prefers the first value"

_Undocumented._

### `"or_else_maybe uses the fallback when empty"`

> test "or_else_maybe uses the fallback when empty"

_Undocumented._

### `"and_maybe requires both values"`

> test "and_maybe requires both values"

_Undocumented._

### `"and_maybe is empty when the second is missing"`

> test "and_maybe is empty when the second is missing"

_Undocumented._

### `"or_maybe prefers the first"`

> test "or_maybe prefers the first"

_Undocumented._

### `"or_maybe uses the second when the first is missing"`

> test "or_maybe uses the second when the first is missing"

_Undocumented._

### `"to_result_maybe produces ok with the payload"`

> test "to_result_maybe produces ok with the payload"

_Undocumented._

### `"to_result_maybe produces err when empty"`

> test "to_result_maybe produces err when empty"

_Undocumented._

### `"to_list_maybe has one element when a value is stored"`

> test "to_list_maybe has one element when a value is stored"

_Undocumented._

### `"to_list_maybe is empty without a value"`

> test "to_list_maybe is empty without a value"

_Undocumented._

### `"describe_optional formats a present value"`

> test "describe_optional formats a present value"

_Undocumented._

### `"describe_optional formats an empty optional"`

> test "describe_optional formats an empty optional"

_Undocumented._

### `"iter_maybe is an alias of to_list_maybe"`

> test "iter_maybe is an alias of to_list_maybe"

_Undocumented._

### `"zip_maybe combines two present optionals"`

> test "zip_maybe combines two present optionals"

_Undocumented._

### `"zip_maybe is empty when one side is empty"`

> test "zip_maybe is empty when one side is empty"

_Undocumented._

### `"flatten_maybe re-boxes the payload"`

> test "flatten_maybe re-boxes the payload"

_Undocumented._

### `"flatten_maybe of an empty optional is empty"`

> test "flatten_maybe of an empty optional is empty"

_Undocumented._

### `"is_ok_result classifies success"`

> test "is_ok_result classifies success"

_Undocumented._

### `"is_ok_result is false for err"`

> test "is_ok_result is false for err"

_Undocumented._

### `"is_err_result classifies an error"`

> test "is_err_result classifies an error"

_Undocumented._

### `"is_err_result is false for ok"`

> test "is_err_result is false for ok"

_Undocumented._

### `"unwrap_result returns the payload"`

> test "unwrap_result returns the payload"

_Undocumented._

### `"unwrap_err_result returns the error"`

> test "unwrap_err_result returns the error"

_Undocumented._

### `"unwrap_or_result uses the payload for ok"`

> test "unwrap_or_result uses the payload for ok"

_Undocumented._

### `"unwrap_or_result uses the fallback for err"`

> test "unwrap_or_result uses the fallback for err"

_Undocumented._

### `"expect_result returns the payload"`

> test "expect_result returns the payload"

_Undocumented._

### `"expect_err_result returns the error"`

> test "expect_err_result returns the error"

_Undocumented._

### `"ok_result turns success into a maybe"`

> test "ok_result turns success into a maybe"

_Undocumented._

### `"err_result turns the error into a maybe"`

> test "err_result turns the error into a maybe"

_Undocumented._

### `"to_maybe_result is an alias of ok_result"`

> test "to_maybe_result is an alias of ok_result"

_Undocumented._

### `"to_list_result has one element for ok"`

> test "to_list_result has one element for ok"

_Undocumented._

### `"to_list_result is empty for err"`

> test "to_list_result is empty for err"

_Undocumented._

### `"describe_result formats ok"`

> test "describe_result formats ok"

_Undocumented._

### `"describe_result formats err"`

> test "describe_result formats err"

_Undocumented._

### `"all_present is true when every element has a value"`

> test "all_present is true when every element has a value"

_Undocumented._

### `"all_present is false with one empty element"`

> test "all_present is false with one empty element"

_Undocumented._

### `"all_present of an empty list is true"`

> test "all_present of an empty list is true"

_Undocumented._

### `"first_present returns the first payload"`

> test "first_present returns the first payload"

_Undocumented._

### `"first_present is empty without payloads"`

> test "first_present is empty without payloads"

_Undocumented._

### `"any_present detects at least one payload"`

> test "any_present detects at least one payload"

_Undocumented._

### `"any_present is false without payloads"`

> test "any_present is false without payloads"

_Undocumented._

### `"collect_ok gathers successes in order"`

> test "collect_ok gathers successes in order"

_Undocumented._

### `"collect_err gathers errors in order"`

> test "collect_err gathers errors in order"

_Undocumented._

### `"collect_ok and collect_err of an empty list"`

> test "collect_ok and collect_err of an empty list"

_Undocumented._

### `"partition_results splits successes and errors"`

> test "partition_results splits successes and errors"

_Undocumented._

### `"partition_results with only errors"`

> test "partition_results with only errors"

_Undocumented._

### `"partition_results keeps the values"`

> test "partition_results keeps the values"

_Undocumented._

### `"legacy MaybeInt keeps its methods"`

> test "legacy MaybeInt keeps its methods"

_Undocumented._

### `"legacy MaybeString keeps its unwrap"`

> test "legacy MaybeString keeps its unwrap"

_Undocumented._

### `"legacy ResultInt keeps its methods"`

> test "legacy ResultInt keeps its methods"

_Undocumented._

### `"legacy ResultString keeps its unwrap_err"`

> test "legacy ResultString keeps its unwrap_err"

_Undocumented._

### `"legacy native maybe builders"`

> test "legacy native maybe builders"

_Undocumented._

### `"legacy native float and bool builders"`

> test "legacy native float and bool builders"

_Undocumented._

### `"legacy none_bool and unwrap_or_bool"`

> test "legacy none_bool and unwrap_or_bool"

_Undocumented._

### `"legacy describe_maybe_int keeps its format"`

> test "legacy describe_maybe_int keeps its format"

_Undocumented._

### `"legacy describe_maybe_string keeps its format"`

> test "legacy describe_maybe_string keeps its format"

_Undocumented._

### `"legacy describe_maybe_int of an empty optional"`

> test "legacy describe_maybe_int of an empty optional"

_Undocumented._

### `"legacy describe_int and describe_string keep their format"`

> test "legacy describe_int and describe_string keep their format"

_Undocumented._

### `"legacy describe_result_int and describe_result_string"`

> test "legacy describe_result_int and describe_result_string"

_Undocumented._

### `"legacy to_native_int and from_native_int bridges"`

> test "legacy to_native_int and from_native_int bridges"

_Undocumented._

### `"legacy to_native_string and from_native_string bridges"`

> test "legacy to_native_string and from_native_string bridges"

_Undocumented._

### `"legacy native result helpers"`

> test "legacy native result helpers"

_Undocumented._

### `"legacy result_ok_string is still exposed"`

> test "legacy result_ok_string is still exposed"

_Undocumented._

