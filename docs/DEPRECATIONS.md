# PenguScript stdlib deprecations

Every `@deprecated` marker in `std/` is listed here with its replacement and the
release it is scheduled to disappear in. The format of the tables is checked by
`tests/test_std_deprecations_doc.py`: the **symbol column must match the
`@deprecated` markers actually present in the sources**, so this file cannot
silently drift from the code.

## How the marker works — and an important caveat

The toolchain has a **real** `@deprecated` attribute with the syntax
`@deprecated("Use X instead")`. It is parsed by the grammar
(`attribute: "@" NAME ["(" attribute_args ")"]`), stored on the symbol, and emits
`W0006` at the *use* site. `pengu check --deny-deprecated` and
`pengu test --deny-deprecated` promote `W0006` to an error. Tests:
`tests/test_deprecation.py` (the mechanism, Phase 2) and
`tests/test_deprecation_policy.py` (surfacing + CI denial, Phase 5).

**The stdlib uses only the docstring convention today, not that attribute.**
Every marker in `std/` is a `## @deprecated Use X instead.` doc comment, and the
checker reads the *attribute*, not the docstring — so **none of these aliases
currently emits `W0006`**. Measured during Phase 6: 90 docstring markers, 0 real
`@deprecated(...)` attributes in `std/`.

Applying the real attribute is a 1.1 change, not a 1.0 one: it needs three
things done together (each measured during Phase 6).

1. **Migrate the internal users first**, or the stdlib warns about itself:
   `string.find` (10 sites in `std/invoke` and `std/precis`), `string.rfind`
   (1 site in `std/precis`), `oracle.maybe_some_string` (7 sites in
   `std/precis`), and `oracle.result_ok_string` / `oracle.result_err_string`
   (11 each, in `std/seal` and `std/ward`).
2. **Move the alias coverage out of the `test` blocks.** `std/scrolls` and
   `std/tally` exercise their aliases from in-file `test` blocks, and
   `pengu check --entry std/<mod>.pengu` type-checks those too, so keeping both
   the alias and its coverage triggers `W0006` on the module itself.
3. **Carry the position.** `W0006` currently renders as `file:0:0` because the
   checker's warning channel is a plain string list; item 6.3 fixed that for
   `W0001` only. Until `W0006` carries `on line L col C`, an enforced stdlib
   deprecation would be unlocatable.

Until then, this file is the contract users actually get: **documented, not
enforced**. Read a row as "this name is scheduled to change", not as "the
compiler will warn you".

Policy (decision D6, 1.x): the stdlib is coupled to the compiler. Deprecated
symbols are **kept for the whole 1.x line** and removed in **2.0**, unless the
table below says otherwise. Nothing is removed in a minor release, so existing
programs keep compiling across 1.x.

Statuses:

- **1.x** — still shipped, scheduled for removal in 2.0.
- **blocked** — cannot be retired yet because the stdlib itself still calls it;
  the retirement is gated on an internal migration.

---

## 1. `std.tally` — legacy alias family

Aliases kept for 0.14.x source compatibility. All of them are one-line
forwarders whose replacement is strictly better-named; no external caller in the
repository was found (measured: 0 uses in `std/` outside `tally.pengu`).

| Symbol | Replacement | Since | Status |
| --- | --- | --- | --- |
| `tally.average` | `tally.mean` | 0.14.0 | 1.x |
| `tally.argmin` | `tally.min_index` | 0.14.0 | 1.x |
| `tally.argmax` | `tally.max_index` | 0.14.0 | 1.x |
| `tally.filter_range` | `tally.filter_in_range` | 0.14.0 | 1.x |
| `tally.dedup` | `tally.unique` | 0.14.0 | 1.x |
| `tally.group_count` | `tally.frequencies` | 0.14.0 | 1.x |

Both the generic (`list of shard T`) and the concrete (`list of int`) overloads
carry the marker, which is why the table has one row per alias.

## 2. `std.scrolls` — legacy string-method names

The `enchanting string` block kept the 0.14.x spellings after the 0.15.0
renames. Each is a one-line forwarder to the canonical method.

| Symbol | Replacement | Since | Status |
| --- | --- | --- | --- |
| `string.find` | `string.index_of` | 0.14.0 | 1.x |
| `string.rfind` | `string.last_index_of` | 0.14.0 | 1.x |
| `string.count_matches` | `string.count` | 0.14.0 | 1.x |
| `string.to_lower` | `string.lower` | 0.14.0 | 1.x |
| `string.to_upper` | `string.upper` | 0.14.0 | 1.x |
| `string.title_case` | `string.title` | 0.14.0 | 1.x |
| `string.lstrip` | `string.trim_start` | 0.14.0 | 1.x |
| `string.rstrip` | `string.trim_end` | 0.14.0 | 1.x |
| `string.is_whitespace` | `string.is_space` | 0.14.0 | 1.x |
| `string.pad_left` | `string.rjust` | 0.14.0 | 1.x |
| `string.pad_right` | `string.ljust` | 0.14.0 | 1.x |

The module-level wrappers of these names (`scrolls.find`, `scrolls.pad_left`, …)
are **not** separately deprecated: they delegate to the methods above, so using
them already produces `W0006` through the method call.

## 3. `std.loom`

| Symbol | Replacement | Since | Status |
| --- | --- | --- | --- |
| `loom.flatten` | `loom.flat_map_identity` | 0.15.0 | 1.x |

`flatten` still exists because `flat_map_identity` is the same operation under a
name that matches the rest of the `flat_map_*` family.

## 4. `std.oracle` — legacy `Maybe*` / `Result*` value types

The pre-0.15.0 optional/result types were superseded by the language-level
`maybe T` / `result of T to E` and the `some_of` / `none_of` / `ok_of` /
`err_of` intrinsics.

| Symbol | Replacement | Since | Status |
| --- | --- | --- | --- |
| `oracle.MaybeInt` | `maybe int` | 0.14.0 | blocked |
| `oracle.MaybeFloat` | `maybe float` | 0.14.0 | blocked |
| `oracle.MaybeString` | `maybe string` | 0.14.0 | blocked |
| `oracle.ResultInt` | `result of int to string` | 0.14.0 | blocked |
| `oracle.ResultString` | `result of string to string` | 0.14.0 | blocked |
| `oracle.is_present` | `m is present` (native `maybe T`); marker on `MaybeInt`, `MaybeFloat`, `MaybeString` | 0.14.0 | blocked |
| `oracle.is_ok` | `r is ok` (native `result of T to E`); marker on `ResultInt`, `ResultString` | 0.14.0 | blocked |
| `oracle.maybe_some_int` | `oracle.some_of shard T` | 0.14.0 | blocked |
| `oracle.maybe_none_int` | `oracle.none_of of int` | 0.14.0 | blocked |
| `oracle.maybe_some_string` | `oracle.some_of shard T` | 0.14.0 | blocked |
| `oracle.maybe_none_string` | `oracle.none_of of string` | 0.14.0 | blocked |
| `oracle.result_ok_int` | `calling ok_of with v` | 0.14.0 | blocked |
| `oracle.result_err_int` | `calling err_of with e` | 0.14.0 | blocked |
| `oracle.result_ok_string` | `calling ok_of with v` | 0.14.0 | blocked |
| `oracle.result_err_string` | `calling err_of with e` | 0.14.0 | blocked |
| `oracle.some_int` | `oracle.some_of shard T` | 0.14.0 | blocked |
| `oracle.some_float` | `oracle.some_of shard T` | 0.14.0 | blocked |
| `oracle.some_string` | `oracle.some_of shard T` | 0.14.0 | blocked |
| `oracle.some_bool` | `oracle.some_of shard T` | 0.14.0 | blocked |
| `oracle.none_int` | `oracle.none_of of int` | 0.14.0 | blocked |
| `oracle.none_float` | `oracle.none_of of float` | 0.14.0 | blocked |
| `oracle.none_string` | `oracle.none_of of string` | 0.14.0 | blocked |
| `oracle.none_bool` | `oracle.none_of of bool` | 0.14.0 | blocked |
| `oracle.unwrap_int` | `oracle.unwrap_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_float` | `oracle.unwrap_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_string` | `oracle.unwrap_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_bool` | `oracle.unwrap_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_or_int` | `oracle.unwrap_or_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_or_float` | `oracle.unwrap_or_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_or_string` | `oracle.unwrap_or_maybe shard T` | 0.14.0 | blocked |
| `oracle.unwrap_or_bool` | `oracle.unwrap_or_maybe shard T` | 0.14.0 | blocked |
| `oracle.to_native_int` | native `maybe int` (`m.is_some` / `m.value`), build with `oracle.some_of` | 0.14.0 | blocked |
| `oracle.from_native_int` | native `maybe int` (`oracle.some_of`) | 0.14.0 | blocked |
| `oracle.to_native_string` | native `maybe string` | 0.14.0 | blocked |
| `oracle.from_native_string` | native `maybe string` | 0.14.0 | blocked |
| `oracle.describe_maybe_int` | `oracle.describe_optional shard T` | 0.14.0 | blocked |
| `oracle.describe_maybe_string` | `oracle.describe_optional shard T` | 0.14.0 | blocked |
| `oracle.describe_maybe_float` | `oracle.describe_optional shard T` | 0.14.0 | blocked |
| `oracle.describe_maybe_bool` | `oracle.describe_optional shard T` | 0.14.0 | blocked |
| `oracle.describe_int` | `oracle.describe_optional shard T` | 0.14.0 | blocked |
| `oracle.describe_string` | `oracle.describe_optional shard T` | 0.14.0 | blocked |
| `oracle.describe_result_int` | `oracle.describe_result shard T and E` | 0.14.0 | blocked |
| `oracle.describe_result_string` | `oracle.describe_result shard T and E` | 0.14.0 | blocked |
| `oracle.is_ok_int_result` | `oracle.is_ok_result shard T and E` | 0.14.0 | blocked |
| `oracle.is_err_int_result` | `oracle.is_err_result shard T and E` | 0.14.0 | blocked |
| `oracle.unwrap_int_result` | `oracle.unwrap_result shard T and E` | 0.14.0 | blocked |
| `oracle.unwrap_or_int_result` | `oracle.unwrap_or_result shard T and E` | 0.14.0 | blocked |

### Why `std.oracle` is "blocked" rather than "1.x"

Measured during Phase 6: `oracle.result_ok_string` and
`oracle.result_err_string` are still called by `std/seal.pengu` and
`std/ward.pengu` (29 call sites of the legacy `maybe_*` / `some_*` / `none_*` /
`result_*` / `unwrap_*` family across `std/`). `crc32_file` was migrated off
`MaybeInt` in the same phase (item 6.1), so the optional family is closer to
retirement than the result family, but neither can be removed until the
remaining internal callers are migrated.

**Reopening criterion:** migrate `std/seal` and `std/ward` to the intrinsic
constructors, then flip the whole table to `1.x` with removal in 2.0. Until
then the markers keep warning correctly and no program breaks.
