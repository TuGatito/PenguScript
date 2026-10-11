# `std.oracle` — frozen public API contract

> **Status: frozen.** Chunk 2 of the Pengunic 2.0 migration. Every symbol below
> is public and must keep its signature; the legacy 0.14.x surface is kept on
> purpose and only marked deprecated.
>
> Module revision: **`2.0.0`** (`ORACLE_VERSION`).
> Source: [`std/oracle.pengu`](../std/oracle.pengu).

`oracle` is the container layer: `maybe T` (a value that may be absent) and
`result of T to E` (a computation that may fail). Every operation exists twice,
with the same semantics: as a method (`calling m.map with f`) and as a module
function (`calling oracle.map_maybe with m, f`).

## Memory model — the reconstruction invariant

A `maybe T` / `result of T to E` owns its payload. **No operation ever returns
its receiver or a container parameter as-is** (`return m`, `return self`): the
container is always rebuilt (`return some v`, `return maybe none`,
`return calling ok_of with v`, `return calling err_of with e`). PenguScript has
no move semantics, so handing back an owned container while the caller still
owns it would free the payload twice. The rebuild is deliberate and must not be
"optimised" away.

Lists returned by `to_list`, `collect_ok`, `collect_err` and
`partition_results` are new and released by the caller with `banish`.

## Types

| Type | Fields | Notes |
|---|---|---|
| `Pair shard A and B` | `first as A`, `second as B` | `derive Par, Vinculum, Imago, Nexus` — comparable, orderable, hashable, usable as a map key. |
| `Triple shard A and B and C` | `first as A`, `second as B`, `third as C` | Same derives. |
| `MaybeInt`* / `MaybeFloat`* / `MaybeString`* | `is_present as bool`, `value as T` | Legacy 0.14.x optional wrappers. |
| `ResultInt`* / `ResultString`* | `is_ok as bool`, `value as T`, `error_msg as string` | Legacy 0.14.x fallible wrappers. |

`ok_of` / `err_of` are compiler intrinsics, not module functions; they need a
type context (`as result of T to E`, or a `return` inside a weave that declares
it).

## Methods on `maybe T`

| Method | Signature | Semantics |
|---|---|---|
| `is_some` | `() -> bool` | The container holds a value. |
| `is_none` | `() -> bool` | The container is empty. |
| `unwrap` | `() -> T` | The payload; panics with `Unwrapped none maybe` when empty. |
| `unwrap_or` | `(fallback: T) -> T` | Payload or `fallback`. |
| `unwrap_or_else` | `(f: weave -> T) -> T` | Payload or `f()`. |
| `expect` | `(message: string) -> T` | Payload; panics with `message` when empty. |
| `value_or` | `(fallback: T) -> T` | Alias of `unwrap_or`. |
| `map shard U` | `(f: weave with x as T -> U) -> maybe U` | Transform the payload. |
| `filter` | `(predicate: weave with x as T -> bool) -> maybe T` | Keep the payload only when the predicate holds. |
| `and_then shard U` | `(f: weave with x as T -> maybe U) -> maybe U` | Chain, avoiding nesting. |
| `or_else` | `(fallback: maybe T) -> maybe T` | Receiver when present, else the (possibly empty) fallback. |
| `and` | `(other: maybe T) -> maybe T` | `other` only when the receiver is present. |
| `or` | `(other: maybe T) -> maybe T` | Receiver when present, else `other`. |
| `to_result` | `(error_value: string) -> result of T to string` | Promote; `error_value` is the error. |
| `to_list` | `() -> list of T` | Zero or one element. |
| `iter` | `() -> list of T` | Alias of `to_list`. |
| `describe` | `() -> string` | `some(v)` or `none`. |
| `zip shard U` | `(other: maybe U) -> maybe Pair of T and U` | Both present -> a `Pair`. |
| `flatten` | `() -> maybe T` | Repack the payload into a fresh container (structural identity). |

## Methods on `result of T to E`

| Method | Signature | Semantics |
|---|---|---|
| `is_ok` | `() -> bool` | The result is a success. |
| `is_err` | `() -> bool` | The result is a failure. |
| `unwrap` | `() -> T` | Success payload; panics with `Unwrapped err result` when err. |
| `unwrap_err` | `() -> E` | The error; panics with `unwrap_err on ok result` when ok. |
| `unwrap_or` | `(fallback: T) -> T` | Success payload or `fallback`. |
| `unwrap_or_else` | `(f: weave with x as E -> T) -> T` | Success payload or `f(error)`. |
| `expect` | `(message: string) -> T` | Success payload; panics with `message` when err. |
| `expect_err` | `(message: string) -> E` | The error; panics with `message` when ok. |
| `map shard U` | `(f: weave with x as T -> U) -> result of U to E` | Transform success, propagate the error. |
| `map_err shard F` | `(f: weave with x as E -> F) -> result of T to F` | Transform the error, propagate success. |
| `and_then shard U` | `(f: weave with x as T -> result of U to E) -> result of U to E` | Chain, propagating the error. |
| `or_else` | `(fallback: result of T to E) -> result of T to E` | Receiver when ok, else the fallback's own ok/err. |
| `ok` | `() -> maybe T` | Discard the error. |
| `err` | `() -> maybe E` | Discard the success. |
| `to_maybe` | `() -> maybe T` | Alias of `ok`. |
| `to_list` | `() -> list of T` | Zero or one element. |
| `describe` | `() -> string` | `ok(v)` or `err(e)`. |

## Module functions — native generic API

Every method also exists as a module function whose first parameter is the
receiver. Bounds (`where T: ...`) live here because `where` is not available
inside methods.

| Function | Signature |
|---|---|
| `some_of shard T` | `(value: T) -> maybe T` |
| `none_of shard T` | `() -> maybe T` (needs an explicit `of T`) |
| `is_some_maybe shard T` | `(m: maybe T) -> bool` |
| `is_none_maybe shard T` | `(m: maybe T) -> bool` |
| `unwrap_maybe shard T` | `(m: maybe T) -> T` |
| `unwrap_or_maybe shard T` | `(m: maybe T, fallback: T) -> T` |
| `unwrap_or_else_maybe shard T` | `(m: maybe T, f: weave -> T) -> T` |
| `expect_maybe shard T` | `(m: maybe T, message: string) -> T` |
| `value_or_maybe shard T` | `(m: maybe T, fallback: T) -> T` |
| `map_maybe shard T and U` | `(m: maybe T, f: weave with x as T -> U) -> maybe U` |
| `filter_maybe shard T` | `(m: maybe T, predicate: weave with x as T -> bool) -> maybe T` |
| `and_then_maybe shard T and U` | `(m: maybe T, f: weave with x as T -> maybe U) -> maybe U` |
| `or_else_maybe shard T` | `(m: maybe T, fallback: maybe T) -> maybe T` |
| `and_maybe shard T` | `(left: maybe T, right: maybe T) -> maybe T` |
| `or_maybe shard T` | `(left: maybe T, right: maybe T) -> maybe T` |
| `to_result_maybe shard T` | `(m: maybe T, error_value: string) -> result of T to string` |
| `to_list_maybe shard T` | `(m: maybe T) -> list of T` |
| `describe_optional shard T` | `(m: maybe T) -> string` |
| `iter_maybe shard T` | `(m: maybe T) -> list of T` |
| `zip_maybe shard T and U` | `(left: maybe T, right: maybe U) -> maybe Pair of T and U` |
| `flatten_maybe shard T` | `(m: maybe T) -> maybe T` |
| `is_ok_result shard T and E` | `(r: result of T to E) -> bool` |
| `is_err_result shard T and E` | `(r: result of T to E) -> bool` |
| `unwrap_result shard T and E` | `(r: result of T to E) -> T` |
| `unwrap_err_result shard T and E` | `(r: result of T to E) -> E` |
| `unwrap_or_result shard T and E` | `(r: result of T to E, fallback: T) -> T` |
| `unwrap_or_else_result shard T and E` | `(r: result of T to E, f: weave with x as E -> T) -> T` |
| `expect_result shard T and E` | `(r: result of T to E, message: string) -> T` |
| `expect_err_result shard T and E` | `(r: result of T to E, message: string) -> E` |
| `map_result shard T and E and U` | `(r: result of T to E, f: weave with x as T -> U) -> result of U to E` |
| `map_err_result shard T and E and F` | `(r: result of T to E, f: weave with x as E -> F) -> result of T to F` |
| `and_then_result shard T and E and U` | `(r, f: weave with x as T -> result of U to E) -> result of U to E` |
| `or_else_result shard T and E` | `(r: result of T to E, fallback: result of T to E) -> result of T to E` |
| `ok_result shard T and E` | `(r: result of T to E) -> maybe T` |
| `err_result shard T and E` | `(r: result of T to E) -> maybe E` |
| `to_maybe_result shard T and E` | `(r: result of T to E) -> maybe T` |
| `to_list_result shard T and E` | `(r: result of T to E) -> list of T` |
| `describe_result shard T and E` | `(r: result of T to E) -> string` |

### Collections of containers

| Function | Signature | Semantics |
|---|---|---|
| `all_present shard T` | `(ms: list of maybe T) -> bool` | True when every element is present (true for an empty list). |
| `first_present shard T` | `(ms: list of maybe T) -> maybe T` | First present payload, else `none`. |
| `any_present shard T` | `(ms: list of maybe T) -> bool` | True when at least one element is present. |
| `collect_ok shard T and E` | `(rs: list of result of T to E) -> list of T` | Success payloads, in order. |
| `collect_err shard T and E` | `(rs: list of result of T to E) -> list of E` | Errors, in order. |
| `partition_results shard T and E` | `(rs: list of result of T to E) -> Pair of list of T and list of E` | Both sides at once. |

## Legacy 0.14.x surface (kept, deprecated)

All of the following carry the **docstring** marker
`## @deprecated Use X instead.` and therefore do **not** emit `W0006`. See
[`DEPRECATIONS.md`](DEPRECATIONS.md) for the replacement and retirement table.

| Symbol | Kind | Replacement |
|---|---|---|
| `MaybeInt`, `MaybeFloat`, `MaybeString` | rune | `maybe T` |
| `ResultInt`, `ResultString` | rune | `result of T to E` |
| `enchanting MaybeInt` / `MaybeString` | methods | `enchanting maybe shard T` |
| `enchanting ResultInt` / `ResultString` | methods | `enchanting result of shard T to shard E` |
| `maybe_some_int`, `maybe_some_string` | function | `oracle.some_of shard T` |
| `maybe_none_int`, `maybe_none_string` | function | `oracle.none_of of T` |
| `result_ok_int`, `result_ok_string` | function | `calling ok_of with v` |
| `result_err_int`, `result_err_string` | function | `calling err_of with e` |
| `some_int`, `some_float`, `some_string`, `some_bool` | function | `oracle.some_of shard T` |
| `none_int`, `none_float`, `none_string`, `none_bool` | function | `oracle.none_of of T` |
| `unwrap_int`, `unwrap_float`, `unwrap_string`, `unwrap_bool` | function | `oracle.unwrap_maybe shard T` |
| `unwrap_or_int`, `unwrap_or_float`, `unwrap_or_string`, `unwrap_or_bool` | function | `oracle.unwrap_or_maybe shard T` |
| `to_native_int`, `from_native_int`, `to_native_string`, `from_native_string` | function | native `maybe T` API |
| `describe_maybe_int`, `describe_maybe_string`, `describe_maybe_float`, `describe_maybe_bool` | function | `oracle.describe_optional shard T` |
| `describe_int`, `describe_string` | function | `oracle.describe_optional shard T` |
| `describe_result_int`, `describe_result_string` | function | `oracle.describe_result shard T and E` |
| `is_ok_int_result`, `is_err_int_result` | function | `oracle.is_ok_result` / `is_err_result` |
| `unwrap_int_result`, `unwrap_or_int_result` | function | `oracle.unwrap_result` / `unwrap_or_result` |

## Compatibility

* Every pre-2.0 public symbol keeps its name and signature.
* `oracle` moves **nothing** out of `pengu_runtime.h`: the `pengu_maybe_*` /
  `pengu_result_*` helpers are emitted by the code generator in every bundle.
* The reconstruction invariant is unchanged; `restore`-style shortcuts are
  intentionally absent.
