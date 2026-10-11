# `std.ward` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `WARD_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/ward.pengu`](../std/ward.pengu).

`ward` owns assertions, invariants and non-panicking checks. It is the module
test programs and runtime guards reach for: the `assert_*` family aborts through
`spark.panic` with a message that renders the expected and actual values, the
`expect_*` family aborts with a caller-supplied `msg`, and the `check_*` families
report failure as a value instead of aborting.

The module imports only `std.spark` and `std.oracle`; it **no longer imports
`std.scrolls`**. `panic`, `fail`, `unreachable` and `fail_unreachable` abort
directly. The legacy nine `check_*` functions return the 0.14.x
`oracle.ResultString` and are deprecated; the seven `check_*_native` functions
return a native `result of string to string` built with the `ok_of` / `err_of`
intrinsics. Nothing here is generic beyond the `maybe T` / `result of T to E`
carriers, and no helper retains a handle after it returns.

The contract is exercised by `std.trial`, which imports this module and
re-exports ten of its signatures (see below), and by `tests/test_ward.py` for the
panic paths.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter of every helper (`int`, `bool`, `float`, `string`, `list`, `map`, `MaybeInt`, `MaybeString`, `ResultInt`, `ResultString`, `maybe T`, `result of T to E`) | borrowed — `ward` never frees an argument | caller keeps its own release |
| `check*` return value (`ResultString` or native `result of string to string`) | owned by the caller | `banish` / `defer banish` |
| the preview/message strings built before a panic | owned temporary handed to `spark.panic` | never — `spark.panic` does not return |
| `assert_*`, `expect_*`, `panic`, `fail`, `unreachable`, `fail_unreachable` | return `void`; abort on failure | n/a |

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `WARD_VERSION` | `string` | `"2.1.0"` | Revision of the **ward API**. Bumps only when a signature or a panic-message template changes. |

## `assert_*` — panicking asserts with rendered values

All members abort via `spark.panic` when their condition fails. `<x>` is the
value rendered the way the table says; string previews are quoted and truncated
to 80 bytes by the private `_w_fmt_string`.

### Core

| Symbol | Signature | Semantics |
|---|---|---|
| `assert` | `(bool) -> void` | Panics when `cond` is false. Exact message `assertion failed`. |
| `assert_msg` | `(bool, string) -> void` | Panics when `cond` is false. Exact message `msg`. |
| `assert_true` | `(bool) -> void` | Panics when `cond` is false. Exact message `assertion failed: expected true, got false`. |
| `assert_false` | `(bool) -> void` | Panics when `cond` is true. Exact message `assertion failed: expected false, got true`. |

### Equality and inequality

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_eq_int` | `(int, int) -> void` | Panics when `a != b`: `assertion failed: left != right: expected <b>, got <a>` (decimal). |
| `assert_eq_string` | `(string, string) -> void` | Panics when `a != b`: `assertion failed: left != right: expected "<b>", got "<a>"` (previews). |
| `assert_eq_bool` | `(bool, bool) -> void` | Panics when `a != b`: `assertion failed: left != right: expected <b>, got <a>` (`true`/`false`). |
| `assert_ne_int` | `(int, int) -> void` | Panics when `a == b`: `assertion failed: left == right: unexpected <a>` (decimal). |
| `assert_ne_string` | `(string, string) -> void` | Panics when `a == b`: `assertion failed: left == right: unexpected "<a>"` (preview). |
| `assert_ne_bool` | `(bool, bool) -> void` | Panics when `a == b`: `assertion failed: left == right: unexpected <a>` (`true`/`false`). |

### Floating point

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_eq_float` | `(float, float, epsilon: float is 0.000001) -> void` | Panics when `|a - b| > epsilon`: `assertion failed: left != right: expected <b>, got <a> (diff <d> > epsilon <e>)`. |
| `assert_ne_float` | `(float, float, epsilon: float is 0.000001) -> void` | Panics when `|a - b| <= epsilon`: `assertion failed: left == right: unexpected <a> within epsilon <e>`. |
| `assert_almost_eq` | `(float, float, epsilon: float is 0.000001) -> void` | Delegates to `assert_eq_float`; same trigger and same message. |

### Ordering and ranges

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_gt_int` | `(int, int) -> void` | Panics unless `a > b`: `assertion failed: expected <a> > <b>`. |
| `assert_ge_int` | `(int, int) -> void` | Panics unless `a >= b`: `assertion failed: expected <a> >= <b>`. |
| `assert_lt_int` | `(int, int) -> void` | Panics unless `a < b`: `assertion failed: expected <a> < <b>`. |
| `assert_le_int` | `(int, int) -> void` | Panics unless `a <= b`: `assertion failed: expected <a> <= <b>`. |
| `assert_gt_float` | `(float, float) -> void` | Panics unless `a > b`: `assertion failed: expected <a> > <b>`. |
| `assert_ge_float` | `(float, float) -> void` | Panics unless `a >= b`: `assertion failed: expected <a> >= <b>`. |
| `assert_lt_float` | `(float, float) -> void` | Panics unless `a < b`: `assertion failed: expected <a> < <b>`. |
| `assert_le_float` | `(float, float) -> void` | Panics unless `a <= b`: `assertion failed: expected <a> <= <b>`. |
| `assert_in_range_int` | `(int, int, int) -> void` | Panics unless `lo <= v <= hi`: `assertion failed: value <v> not in range [<lo>, <hi>]`. |
| `assert_in_range_float` | `(float, float, float) -> void` | Panics unless `lo <= v <= hi`: `assertion failed: value <v> not in range [<lo>, <hi>]`. |

### Strings

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_string_contains` | `(string, string) -> void` | Panics unless `haystack` contains `needle`: `assertion failed: expected <haystack> to contain <needle>` (both previews). |
| `assert_string_starts_with` | `(string, string) -> void` | Panics unless `s` starts with `prefix`: `assertion failed: expected <s> to start with <prefix>` (both previews). |
| `assert_string_ends_with` | `(string, string) -> void` | Panics unless `s` ends with `suffix`: `assertion failed: expected <s> to end with <suffix>` (both previews). |
| `assert_string_empty` | `(string) -> void` | Panics when `s` is non-empty: `assertion failed: expected empty string, got "<s>"` (preview). |
| `assert_string_not_empty` | `(string) -> void` | Panics when `s` is empty. Exact message `assertion failed: expected non-empty string, got empty string`. |

### Containers (lists and maps)

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_eq_int_list` | `(list of int, list of int) -> void` | Panics on mismatch: `assertion failed: list length mismatch: expected <nb>, got <na>`, or `assertion failed: element mismatch at index <i>: expected <vb>, got <va>`. |
| `assert_eq_string_list` | `(list of string, list of string) -> void` | Same two templates, with element previews quoted: `... expected "<vb>", got "<va>"`. |
| `assert_list_empty_int` | `(list of int) -> void` | Panics when non-empty: `assertion failed: expected empty list, got len <n>`. |
| `assert_list_not_empty_int` | `(list of int) -> void` | Panics when empty. Exact message `assertion failed: expected non-empty list, got len 0`. |
| `assert_list_len_int` | `(list of int, int) -> void` | Panics unless `l.len == expected`: `assertion failed: expected list len <expected>, got <l.len>`. |
| `assert_map_has_key` | `(map of string to string, string) -> void` | Panics when `key` is absent: `assertion failed: expected map to contain key "<key>"` (preview). |
| `assert_map_not_has_key` | `(map of string to string, string) -> void` | Panics when `key` is present: `assertion failed: unexpected key "<key>" in map` (preview). |

### Native `maybe` / `result`

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_maybe_present shard T` | `(maybe T) -> void` | Panics when `m` is `none`. Exact message `assertion failed: expected maybe to be present, got none`. |
| `assert_maybe_none shard T` | `(maybe T) -> void` | Panics when `m` is present. Exact message `assertion failed: expected maybe to be none, got present`. |
| `assert_result_ok shard T and E` | `(result of T to E) -> void` | Panics when `r` is `err`. Exact message `assertion failed: expected result to be ok, got err`. |
| `assert_result_err shard T and E` | `(result of T to E) -> void` | Panics when `r` is `ok`. Exact message `assertion failed: expected result to be err, got ok`. |
| `assert_result_ok_int` | `(result of int to string) -> void` | Panics when `r` is `err`: `assertion failed: result is error: <r.error>`. |
| `assert_result_err_int` | `(result of int to string) -> void` | Panics when `r` is `ok`: `assertion failed: result is ok: unexpected value <r.value>`. |

### Legacy 0.14.x optionals and results

| Symbol | Signature | Semantics |
|---|---|---|
| `assert_present_int` | `(MaybeInt) -> void` | Panics when `m.is_present` is false. Exact message `assertion failed: maybe is none`. |
| `assert_present_string` | `(MaybeString) -> void` | Panics when `m.is_present` is false. Exact message `assertion failed: maybe is none`. |
| `assert_none_int` | `(MaybeInt) -> void` | Panics when `m.is_present` is true: `assertion failed: maybe is present: unexpected value <m.value>`. |
| `assert_none_string` | `(MaybeString) -> void` | Same, with the value previewed: `... unexpected value "<m.value>"`. |
| `assert_ok_int` | `(ResultInt) -> void` | Panics when `r.is_ok` is false: `assertion failed: result is error: <r.error_msg>`. |
| `assert_ok_string` | `(ResultString) -> void` | Panics when `r.is_ok` is false: `assertion failed: result is error: <r.error_msg>`. |
| `assert_err_int` | `(ResultInt) -> void` | Panics when `r.is_ok` is true: `assertion failed: result is ok: unexpected value <r.value>`. |
| `assert_err_string` | `(ResultString) -> void` | Same, with the value previewed: `... unexpected value "<r.value>"`. |

## `expect_*` — panicking asserts with a caller message

Every `expect_*` aborts via `spark.panic` with **exactly** the caller's `msg`;
values are not rendered. The trigger is the negated condition named in the table.

| Symbol | Signature | Panics when |
|---|---|---|
| `expect` | `(bool, string) -> void` | `cond` is false. |
| `expect_eq_int` | `(int, int, string) -> void` | `a != b`. |
| `expect_eq_string` | `(string, string, string) -> void` | `a != b`. |
| `expect_eq_float` | `(float, float, string, epsilon: float is 0.000001) -> void` | `|a - b| > epsilon`. |
| `expect_ne_int` | `(int, int, string) -> void` | `a == b`. |
| `expect_ne_string` | `(string, string, string) -> void` | `a == b`. |
| `expect_ne_bool` | `(bool, bool, string) -> void` | `a == b`. |
| `expect_gt_int` | `(int, int, string) -> void` | `a <= b`. |
| `expect_ge_int` | `(int, int, string) -> void` | `a < b`. |
| `expect_lt_int` | `(int, int, string) -> void` | `a >= b`. |
| `expect_le_int` | `(int, int, string) -> void` | `a > b`. |
| `expect_present_int` | `(MaybeInt, string) -> void` | `m.is_present` is false. |
| `expect_present_string` | `(MaybeString, string) -> void` | `m.is_present` is false. |
| `expect_ok_int` | `(ResultInt, string) -> void` | `r.is_ok` is false. |
| `expect_ok_string` | `(ResultString, string) -> void` | `r.is_ok` is false. |

## `check_*_native` — native result checks

Never panic. Each returns a native `result of string to string` built with the
`ok_of` / `err_of` intrinsics: the success case is `ok "ok"` (the literal string
`"ok"`), the failure case is `err <msg>` with the caller's `msg` as payload. The
result composes with `std.oracle` (`is_ok`, `is_err`, `unwrap_err`, `map_err`, …)
and is owned by the caller. These are the canonical replacements for the legacy
`check_*` family.

| Symbol | Signature | Success when |
|---|---|---|
| `check_native` | `(bool, string) -> result of string to string` | `cond` is true. |
| `check_eq_int_native` | `(int, int, string) -> result of string to string` | `a == b`. |
| `check_eq_string_native` | `(string, string, string) -> result of string to string` | `a == b` (exact). |
| `check_eq_bool_native` | `(bool, bool, string) -> result of string to string` | `a == b`. |
| `check_eq_float_native` | `(float, float, string, epsilon: float is 0.000001) -> result of string to string` | `|a - b| <= epsilon`. |
| `check_present_native shard T` | `(maybe T, string) -> result of string to string` | `m` is present. |
| `check_ok_native shard T and E` | `(result of T to E, string) -> result of string to string` | `r.is_ok`. |

## Legacy `check_*` (kept, deprecated)

Never panic. Each returns the 0.14.x `oracle.ResultString` — `ok("ok")` on
success, `err(msg)` on failure — owned by the caller and released with `banish`.
They carry `## @deprecated` docstring markers rather than the `@deprecated`
attribute, because the attribute would emit `W0006` at every internal call site.

| Symbol | Signature | Semantics |
|---|---|---|
| `check` *(deprecated — use `check_native`)* | `(bool, string) -> ResultString` | `ok("ok")` when `cond`, else `err(msg)`. |
| `check_eq_int` *(deprecated — use `check_eq_int_native`)* | `(int, int, string) -> ResultString` | `ok("ok")` when `a == b`, else `err(msg)`. |
| `check_eq_string` *(deprecated — use `check_eq_string_native`)* | `(string, string, string) -> ResultString` | `ok("ok")` when `a == b`, else `err(msg)`. |
| `check_eq_bool` *(deprecated — use `check_eq_bool_native`)* | `(bool, bool, string) -> ResultString` | `ok("ok")` when `a == b`, else `err(msg)`. |
| `check_eq_float` *(deprecated — use `check_eq_float_native`)* | `(float, float, string, epsilon: float is 0.000001) -> ResultString` | `ok("ok")` when `|a - b| <= epsilon`, else `err(msg)`. |
| `check_present_int` *(deprecated — use `check_present_native`)* | `(MaybeInt, string) -> ResultString` | `ok("ok")` when `m.is_present`, else `err(msg)`. |
| `check_present_string` *(deprecated — use `check_present_native`)* | `(MaybeString, string) -> ResultString` | `ok("ok")` when `m.is_present`, else `err(msg)`. |
| `check_ok_int` *(deprecated — use `check_ok_native`)* | `(ResultInt, string) -> ResultString` | `ok("ok")` when `r.is_ok`, else `err(msg)`. |
| `check_ok_string` *(deprecated — use `check_ok_native`)* | `(ResultString, string) -> ResultString` | `ok("ok")` when `r.is_ok`, else `err(msg)`. |

## `panic`, `fail`, `unreachable`

| Symbol | Signature | Semantics |
|---|---|---|
| `panic` | `(string) -> void` | Aborts with exactly `msg` (delegates to `spark.panic`). Never returns. |
| `fail` | `(string) -> void` | Ergonomic alias of `panic`; aborts with exactly `msg`. Never returns. |
| `unreachable` | `(msg: string is "internal error: unreachable code") -> void` | Marks dead code; aborts with exactly `msg`. Never returns. |
| `fail_unreachable` | `(msg: string is "unreachable") -> void` | Aborts with `internal error: <msg>` (interpolated owned temporary). Never returns. |

## Design notes

* **Two result families.** The legacy `check_*` return `oracle.ResultString`; the
  `check_*_native` return the native `result of string to string` and compose
  with `std.oracle`. Both coexist on purpose; only the native family is
  recommended for new code.
* **No `std.scrolls` dependency.** `_w_fmt_string` renders a string as a quoted
  literal truncated to 80 bytes with the native `at 0 to 77` slice, and the
  three string predicates (`assert_string_contains`, `assert_string_starts_with`,
  `assert_string_ends_with`) compare native slices with `==`. This is the tradeoff
  for dropping the import: the scans allocate one temporary slice per candidate
  offset, whereas the previous `scrolls` versions ran allocation-free C `memcmp`
  helpers.
* **No string `+`.** Every composed message uses `"{expr}"` interpolation
  (E0005 forbids `+` on strings).
* **Internal tests stay panic-free.** The `# --- Tests ---` section uses the
  happy paths plus the non-panicking check families; the panic paths are verified
  by `tests/test_ward.py`.

## Relationship with `std.trial`

`std.trial` imports `ward` and re-exports ten load-bearing signatures, which are
therefore part of the frozen surface even though their bodies live in `trial`:
`assert`, `assert_msg`, `assert_eq_int`, `assert_eq_string`, `assert_ne_int`,
`assert_ne_string`, `assert_true`, `assert_false`, `assert_present_int` and
`assert_ok_int`. Their names, bounds and parameter lists must not move.

## Private helpers (internal)

Not part of the frozen surface.

| Symbol | Signature | Role |
|---|---|---|
| `_w_fmt_string` | `(string) -> string` | Quoted 80-byte preview used by every message that renders a string; `s.len > 80` yields `"<first 77 bytes>..."`. |

## Compatibility and migration

* Every 2.0.0 public signature is preserved; every visible result is unchanged.
* 2.1.0 rewrites the module in Pengunic style with English prose, drops the
  `std.scrolls` dependency, and **adds** the seven `check_*_native` checks.
* The nine legacy `check_*` functions keep working and are marked
  *(deprecated — use the matching `_native` symbol)*. `check_present_int` and
  `check_present_string` both map to `check_present_native`;
  `check_ok_int` and `check_ok_string` both map to `check_ok_native`.
* The panic-message templates in this document are the observable contract: they
  are what `tests/test_ward.py` asserts on, so rewording one is a breaking change.
