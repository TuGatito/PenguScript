# `std.chronicle` — frozen public API contract

> **Status: frozen.** This is the API that the following migration chunks
> (`atlas`, `coven`, `filum`, `precis`, `archivum`, `invoke`, …) are built
> against. A change to a signature here is a breaking change and must bump
> `CHRONICLE_VERSION`.
>
> Module revision: **`2.1.0`**.
> Source: [`std/chronicle.pengu`](../std/chronicle.pengu).

`chronicle` owns the clock: wall-clock time, a steady monotonic timer, Unix
timestamps, UTC and local calendar fields, the decomposed `DateTime` value rune,
calendar boundaries, formatting/parsing (including ISO 8601 and human durations)
and a `Stopwatch`. All timestamps are Unix seconds expressed as `float`.

The module imports `std.spark` (for `parse_int`/`parse_float`/`panic`),
`std.scrolls` and `std.oracle` (for the `oracle.Pair` returned by
`seconds_to_hms`). Every primitive is a `declare` linked to the C runtime; the
module has **no** `antiquus` block and moves no runtime code. There is no
`insignia`.

The `utc_*` getters interpret a timestamp in Coordinated Universal Time and the
`local_*` getters in the process's local zone; `time` follows the wall clock
(subject to system adjustments) while `monotonic` only moves forward and backs
every interval and `Stopwatch` reading. `DateTime` and `Stopwatch` are plain
scalar runes: they own no heap memory and never need `banish`, but the weaves
that return `string` allocate an owned buffer.

## Ownership model

| Producer | Ownership | Release |
|---|---|---|
| every parameter and receiver (`ts`, `fmt`, `s`, `y`, `m`, `sec`, `a`, `b`, `lo`, `hi`, `self`, `other`) | borrowed, read-only | never `banish` |
| scalar returns (`float`, `int`, `bool`) | plain value | never `banish` |
| `DateTime`, `Stopwatch`, `oracle.Pair` | scalar/aggregate value, no heap | never `banish` |
| `maybe float` / `maybe int` / `maybe bool` | values; owns nothing | never `banish` |
| `string` returns (`format`, `format_now`, `now_*`, `to_iso`, `to_*_string`, `format_duration`, `weekday_name`, `month_name`) | freshly allocated | `banish` |

## Constants

`CHRONICLE_VERSION as string is "2.1.0"` — the revision of the **chronicle
API**, not of the toolchain. It bumps only when a signature on this page changes.

## Native runtime declarations (internal C bridges)

These 24 `declare`s are the module's only clock access; they are byte-identical
to 2.0.0 and are the runtime contract, not the PenguScript API.

| Declaration | Signature |
|---|---|
| `pengu_c_time` | `() -> float` |
| `pengu_c_time_monotonic` | `() -> float` |
| `pengu_c_sleep_ms` | `(int) -> void` |
| `pengu_c_sleep_sec` | `(float) -> void` |
| `pengu_c_strftime` | `(string, float) -> string` |
| `pengu_c_strptime` | `(string, string) -> maybe float` |
| `pengu_c_get_utc_year` | `(float) -> int` |
| `pengu_c_get_utc_month` | `(float) -> int` |
| `pengu_c_get_utc_day` | `(float) -> int` |
| `pengu_c_get_utc_hour` | `(float) -> int` |
| `pengu_c_get_utc_minute` | `(float) -> int` |
| `pengu_c_get_utc_second` | `(float) -> int` |
| `pengu_c_get_utc_weekday` | `(float) -> int` |
| `pengu_c_get_utc_yearday` | `(float) -> int` |
| `pengu_c_get_utc_is_dst` | `(float) -> bool` |
| `pengu_c_get_local_year` | `(float) -> int` |
| `pengu_c_get_local_month` | `(float) -> int` |
| `pengu_c_get_local_day` | `(float) -> int` |
| `pengu_c_get_local_hour` | `(float) -> int` |
| `pengu_c_get_local_minute` | `(float) -> int` |
| `pengu_c_get_local_second` | `(float) -> int` |
| `pengu_c_get_local_weekday` | `(float) -> int` |
| `pengu_c_get_local_yearday` | `(float) -> int` |
| `pengu_c_get_local_is_dst` | `(float) -> bool` |

## Clocks and delays

| Symbol | Signature | Semantics |
|---|---|---|
| `time` | `() -> float` | Current wall-clock Unix seconds; can jump. |
| `monotonic` | `() -> float` | Steady clock reading in seconds; only moves forward. |
| `sleep_ms` | `(ms: int) -> void` | Suspends the current thread for `ms` milliseconds. |
| `sleep` | `(sec: float) -> void` | Suspends for `sec` fractional seconds. |
| `now_ms` | `() -> int` | Wall-clock milliseconds since the Unix epoch. |
| `time_ms` | `() -> int` | Alias of `now_ms`. |
| `monotonic_ms` | `() -> int` | Monotonic clock in milliseconds. |

## UTC calendar field getters

Each applies no time-zone offset.

| Symbol | Signature | Semantics |
|---|---|---|
| `utc_year` | `(ts: float) -> int` | Civil year, e.g. 2026. |
| `utc_month` | `(ts: float) -> int` | Month, 1..12. |
| `utc_day` | `(ts: float) -> int` | Day of month, 1..31. |
| `utc_hour` | `(ts: float) -> int` | Hour, 0..23. |
| `utc_minute` | `(ts: float) -> int` | Minute, 0..59. |
| `utc_second` | `(ts: float) -> int` | Second, 0..60. |
| `utc_weekday` | `(ts: float) -> int` | 0 = Sunday .. 6 = Saturday. |
| `utc_yearday` | `(ts: float) -> int` | Zero-based day of year, 0..365. |
| `utc_is_dst` | `(ts: float) -> bool` | Always `false` (UTC has no DST). |

## Local calendar field getters

Each interprets `ts` in the process's local time zone.

| Symbol | Signature | Semantics |
|---|---|---|
| `local_year` | `(ts: float) -> int` | Local civil year. |
| `local_month` | `(ts: float) -> int` | Local month, 1..12. |
| `local_day` | `(ts: float) -> int` | Local day of month, 1..31. |
| `local_hour` | `(ts: float) -> int` | Local hour, 0..23. |
| `local_minute` | `(ts: float) -> int` | Local minute, 0..59. |
| `local_second` | `(ts: float) -> int` | Local second, 0..60. |
| `local_weekday` | `(ts: float) -> int` | 0 = Sunday .. 6 = Saturday. |
| `local_yearday` | `(ts: float) -> int` | Zero-based local day of year, 0..365. |
| `local_is_dst` | `(ts: float) -> bool` | Whether DST is in effect for `ts` locally. |

## Rune `DateTime` and builders

`rune DateTime` is a nine-field value rune, no heap:

| Field | Type | Meaning |
|---|---|---|
| `year` | `int` | Civil year (e.g. 2026). |
| `month` | `int` | 1..12. |
| `day` | `int` | 1..31. |
| `hour` | `int` | 0..23. |
| `minute` | `int` | 0..59. |
| `second` | `int` | 0..60. |
| `weekday` | `int` | 0 = Sunday .. 6 = Saturday. |
| `yearday` | `int` | Zero-based day of year, 0..365. |
| `is_dst` | `bool` | DST in effect at the source timestamp. |

| Symbol | Signature | Semantics |
|---|---|---|
| `datetime_utc` | `(ts: float) -> DateTime` | Decomposes `ts` in UTC; `is_dst` is always `false`. |
| `datetime_local` | `(ts: float) -> DateTime` | Decomposes `ts` in the local zone and fills `is_dst`. |

## Methods on `DateTime` (`enchanting DateTime`)

The `plus_*` methods read `to_timestamp`, delegate to the module `add_*` weave and
rebuild with `datetime_utc`, so every result is a UTC record with `is_dst` false.
The receiver is borrowed and never modified.

| Method | Signature | Semantics |
|---|---|---|
| `to_date` | `() -> string` | `"YYYY-MM-DD"`; years are not zero-padded. |
| `to_time` | `() -> string` | `"HH:MM:SS"`. |
| `to_iso` | `() -> string` | `"YYYY-MM-DDTHH:MM:SSZ"`; always rendered as UTC. |
| `to_timestamp` | `() -> float` | Inverse of `datetime_utc`, exact to the second; `weekday`, `yearday` and `is_dst` are ignored. |
| `plus_seconds` | `(n: int) -> DateTime` | Adds whole seconds (may be negative). |
| `plus_minutes` | `(n: int) -> DateTime` | Adds `n` minutes. |
| `plus_hours` | `(n: int) -> DateTime` | Adds `n` hours. |
| `plus_days` | `(n: int) -> DateTime` | Adds `n` days. |
| `plus_weeks` | `(n: int) -> DateTime` | Adds `n` weeks. |
| `is_before` | `(other: DateTime) -> bool` | Strictly earlier Unix second. |
| `is_after` | `(other: DateTime) -> bool` | Strictly later Unix second. |
| `is_same_day` | `(other: DateTime) -> bool` | Equal `start_of_day` of both timestamps (UTC). |
| `weekday_name` | `() -> string` | `"Sunday"` .. `"Saturday"`; empty for an out-of-range `weekday`. |
| `month_name` | `() -> string` | `"January"` .. `"December"`; empty for an out-of-range `month`. |
| `is_weekend` | `() -> bool` | `weekday` is 0 (Sunday) or 6 (Saturday). |
| `is_leap_year` | `() -> bool` | Gregorian leap-year rule on the record's `year`. |

## Calendar helpers and boundaries

| Symbol | Signature | Semantics |
|---|---|---|
| `is_leap_year` | `(y: int) -> bool` | Divisible by 4, except centuries not divisible by 400. |
| `days_in_month` | `(y: int, m: int) -> int` | Days in month `m` for year `y`. |
| `days_in_year` | `(y: int) -> int` | 366 for a leap year, 365 otherwise. |
| `start_of_day` | `(ts: float) -> float` | Rounded down to 00:00:00 UTC. |
| `end_of_day` | `(ts: float) -> float` | 23:59:59 UTC of the same day. |
| `today` | `() -> float` | Start of the current UTC day. |
| `yesterday` | `() -> float` | Start of yesterday in UTC. |
| `tomorrow` | `() -> float` | Start of tomorrow in UTC. |
| `start_of_month` | `(ts: float) -> float` | 00:00:00 UTC on the 1st. |
| `start_of_year` | `(ts: float) -> float` | 00:00:00 UTC on January 1st. |
| `start_of_week` | `(ts: float) -> float` | Monday 00:00:00 UTC. |
| `start_of_quarter` | `(ts: float) -> float` | 00:00:00 UTC on the first day of the quarter. |
| `end_of_month` | `(ts: float) -> float` | 23:59:59 UTC on the last day of the month. |

## Calendar labels

| Symbol | Signature | Semantics |
|---|---|---|
| `weekday_name` | `(ts: float) -> string` | English UTC weekday name for `ts`. |
| `month_name` | `(ts: float) -> string` | English UTC month name for `ts`. |

## Formatting, parsing and ISO 8601

| Symbol | Signature | Semantics |
|---|---|---|
| `format` | `(fmt: string, timestamp: float) -> string` | `strftime` pattern applied in UTC. |
| `format_now` | `(fmt: string) -> string` | `format` on the current wall-clock time, in UTC. |
| `parse` | `(s: string, fmt: string) -> maybe float` | `strptime` parse to Unix seconds; `none` on mismatch. |
| `now_utc_iso` | `() -> string` | Current UTC time as `"YYYY-MM-DDTHH:MM:SSZ"`. |
| `now_local_iso` | `() -> string` | Current local time as an ISO 8601 string (no `Z`). |
| `now_date` | `() -> string` | Current local date `"YYYY-MM-DD"`. |
| `now_time` | `() -> string` | Current local time `"HH:MM:SS"`. |
| `to_iso` | `(ts: float) -> string` | `ts` as UTC ISO 8601, e.g. `"2026-09-25T14:30:00Z"`. |
| `from_iso` | `(s: string) -> maybe float` | Parses a date (`YYYY-MM-DD`) with optional `T`/space time and optional `Z`; years below 1970 are rejected; `to_iso` round-trips exactly to the second. |
| `to_date_string` | `(ts: float) -> string` | `"%Y-%m-%d"` in UTC. |
| `to_time_string` | `(ts: float) -> string` | `"%H:%M:%S"` in UTC. |
| `to_datetime_string` | `(ts: float) -> string` | `"%Y-%m-%d %H:%M:%S"` in UTC. |

## Arithmetic and comparisons

| Symbol | Signature | Semantics |
|---|---|---|
| `add_seconds` | `(ts: float, n: int is 1) -> float` | Adds `n` seconds. |
| `add_minutes` | `(ts: float, n: int is 1) -> float` | Adds `n` minutes (60 s each). |
| `add_hours` | `(ts: float, n: int is 1) -> float` | Adds `n` hours (3600 s each). |
| `add_days` | `(ts: float, n: int is 1) -> float` | Adds `n` days (86400 s each). |
| `add_weeks` | `(ts: float, n: int is 1) -> float` | Adds `n` weeks (604800 s each). |
| `diff_seconds` | `(a: float, b: float) -> float` | Signed difference `a - b`. |
| `diff_days` | `(a: float, b: float) -> int` | Signed whole days `(a - b) / 86400`. |
| `days_between` | `(a: float, b: float) -> int` | Non-negative whole days between the two. |
| `hours_between` | `(a: float, b: float) -> int` | Non-negative whole hours between the two. |
| `is_before` | `(a: float, b: float) -> bool` | `a` strictly before `b`. |
| `is_after` | `(a: float, b: float) -> bool` | `a` strictly after `b`. |
| `is_between` | `(ts: float, lo: float, hi: float) -> bool` | `ts` inside `[lo, hi]`, inclusive. |

## Durations

| Symbol | Signature | Semantics |
|---|---|---|
| `format_duration` | `(sec: float) -> string` | `"2h 30m 45s"`, `"15m 30s"` or `"10s"`; fractional part truncated; zero and negative render `"0s"`. |
| `parse_duration` | `(s: string) -> maybe float` | `"45s"`, `"30m"`, `"2h"`, `"7d"` or a bare integer (seconds); whitespace trimmed; `none` otherwise. |
| `seconds_to_hms` | `(sec: int) -> oracle.Pair of int and oracle.Pair of int and int` | `first` = hours, `second.first` = minutes, `second.second` = seconds; uses the absolute value. |

## Rune `Stopwatch`

`rune Stopwatch: started_at as float` holds the `monotonic` reading at creation or
reset; it owns no heap memory.

| Method | Signature | Semantics |
|---|---|---|
| `new` | `ritual () -> Stopwatch` | Starts a stopwatch at the current `monotonic` reading. |
| `elapsed_sec` | `() -> float` | Non-negative monotonic seconds since creation/reset. |
| `elapsed_ms` | `() -> int` | Same interval truncated to milliseconds. |
| `reset` | `() -> void` | Overwrites `started_at` with the current `monotonic` reading. |

| Symbol | Signature | Semantics |
|---|---|---|
| `new_stopwatch` | `() -> Stopwatch` | Module-level equivalent of `calling Stopwatch.new`. |

## Migración (2.0.0 → 2.1.0)

2.1.0 adds a date/time API and removes or renames nothing; the 24 C bindings are
byte-identical to 2.0.0.

| Added in 2.1.0 | Kind | Purpose |
|---|---|---|
| `to_timestamp` | `DateTime` method | Inverse of `datetime_utc`. |
| `plus_seconds`, `plus_minutes`, `plus_hours`, `plus_days`, `plus_weeks` | `DateTime` methods | Calendar arithmetic on a record. |
| `is_before`, `is_after`, `is_same_day` | `DateTime` methods | Comparisons; `is_same_day` compares UTC days. |
| `weekday_name`, `month_name` | `DateTime` methods | `"Monday"` … / `"January"` … from the record's fields. |
| `is_weekend`, `is_leap_year` | `DateTime` methods | Calendar predicates. |
| `weekday_name`, `month_name` | module weaves | Labels from a Unix timestamp. |
| `start_of_week`, `start_of_quarter`, `end_of_month` | module weaves | Additional UTC boundaries. |
| `days_between`, `hours_between` | module weaves | Non-negative distances, unlike `diff_seconds`/`diff_days`. |
| `seconds_to_hms` | module weave | Hours plus an `oracle.Pair` of minutes/seconds. |
| `# --- Tests ---` | internal | 35 `test` blocks on fixed timestamps; there were none in 2.0.0. |

The private helpers `_is_leap_year`, `_epoch_days`, `_parse_slice`, `_pad2`,
`_weekday_label`, `_month_label` and the `_chr_expect*` test harness are also new
and are not part of the API. No symbol is deprecated in this revision.

## Internal tests

The internal `# --- Tests ---` suite holds **35 `test` blocks** over the private
`_chr_expect*` harness (`spark.panic`; `std.ward` imports `chronicle`, E0004).
Every case uses fixed timestamps, so the suite is deterministic.

## Private helpers (internal)

Not public API; do not call them.

| Symbol | Signature | Role |
|---|---|---|
| `_is_leap_year` | `(y: int) -> bool` | Gregorian leap-year rule (used by the `DateTime` method to avoid a self-recursive call). |
| `_epoch_days` | `(y: int, m: int, d: int) -> int` | Whole UTC days between 1970-01-01 and a civil date. |
| `_parse_slice` | `(text: string, from_i: int, to_i: int) -> maybe int` | Parses a decimal slice; frees the slice. |
| `_pad2` | `(n: int) -> string` | Zero-pads to two digits when below 10. |
| `_weekday_label` | `(idx: int) -> string` | 0 = Sunday .. 6 = Saturday → English name. |
| `_month_label` | `(idx: int) -> string` | 1 = January .. 12 = December → English name. |
| `_chr_expect` | `(cond: bool, label: string) -> void` | Test assertion via `spark.panic`. |
| `_chr_expect_eq_int` | `(got: int, want: int, label: string) -> void` | Test assertion. |
| `_chr_expect_eq_string` | `(got: string, want: string, label: string) -> void` | Byte-equal test assertion. |
| `_chr_expect_close` | `(got: float, want: float, label: string) -> void` | Float comparison with 1e-6 tolerance. |
| `_chr_expect_maybe_float` | `(opt: maybe float, want: float, label: string) -> void` | Asserts a `maybe float` holds a close value. |
