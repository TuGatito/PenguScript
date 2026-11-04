# std.chronicle

> Source: `std/chronicle.pengu`

std/chronicle.pengu — the clock: wall-clock time, monotonic timers, Unix
timestamps, UTC and local calendar fields, a decomposed `DateTime` value rune,
calendar boundaries, formatting/parsing and a `Stopwatch`.

All timestamps are Unix seconds expressed as `float`. `float` is 32-bit in
Pengunic, so at modern epochs (about 1.7e9 s) the resolution is already
~128 s: prefer whole-hour helpers, and treat sub-minute arithmetic after 1970
as approximate. The `f64` variants of the runtime bridges are exact, but the
public surface of this module keeps the historical `float` type.

`utc_*` getters interpret a timestamp in Coordinated Universal Time; the
`local_*` getters interpret it in the process's local time zone. `time` is a
wall clock (subject to system adjustments); `monotonic` is a steady clock
suited for measuring intervals and elapsed times.

## Example
```pengu
import std.chronicle
import std.spark

weave main into int:
    let ts as float is 1700000000.0
    let dt as chronicle.DateTime is calling chronicle.datetime_utc with ts
    calling spark.println with calling dt.to_iso                    # 2023-11-14T22:13:20Z
    calling spark.println with calling chronicle.weekday_name with ts    # Tuesday
    calling spark.println with calling chronicle.format_duration with 9045.0  # 2h 30m 45s
    calling spark.println with calling chronicle.to_date_string with ts   # 2023-11-14
    return 0
```

## Memory
Every timestamp, calendar field, `DateTime` and `Stopwatch` is a plain scalar
value: they own no heap memory and never need `banish`. The weaves that return
a `string` (`format`, `format_now`, `now_*`, `to_iso`, `from_iso`'s inverse,
`to_*_string`, `format_duration`, `weekday_name`, `month_name`) allocate a
fresh owned string that the caller releases with `banish`; the string
parameters (`fmt`, `s`) are borrowed and never freed. `parse`,
`parse_duration` and `from_iso` return a `maybe float` that owns nothing, and
`seconds_to_hms` returns an `oracle.Pair` of `int`s that owns nothing either.
No returned value aliases an argument and no argument is retained after the
call.

## Design notes
- **Two clocks.** `time` follows the system wall clock and can jump backwards;
  `monotonic` only moves forward and is the clock behind every interval and
  `Stopwatch` measurement.
- **UTC versus local.** The `utc_*` getters and `datetime_utc` never apply a
  time-zone offset, so `utc_is_dst` is always `false`; the `local_*` getters
  and `datetime_local` delegate that decision to the C runtime.
- **C bridges only.** Every primitive is a `declare` linked to the runtime;
  this module has no `antiquus` blocks and moves no runtime code.
- **One arithmetic path.** The `DateTime.plus_*` methods read `to_timestamp`,
  delegate to the module `add_*` weave and rebuild the record with
  `datetime_utc`, so the unit constants live in exactly one place.
- **Shared names without recursion.** `DateTime.weekday_name`,
  `DateTime.month_name` and `DateTime.is_leap_year` share their names with
  module functions, so each method maps its decomposed field through the
  private `_weekday_label` / `_month_label` / `_is_leap_year` helper instead of
  calling the same-named module function.
- **Absolute distances.** `days_between` and `hours_between` are non-negative,
  unlike the signed `diff_seconds` and `diff_days`.
- **Internal tests without `std.ward`** (`ward` imports `chronicle`, E0004):
  the `# --- Tests ---` section uses a private harness on top of `spark.panic`
  and fixed timestamps, so the suite is deterministic.

## Migration
2.1.0 adds a date/time API and removes or renames nothing; the 24 C bindings
are byte-identical to 2.0.0.

| New in 2.1.0 | Purpose |
|---|---|
| `calling dt.to_timestamp` | inverse of `datetime_utc` |
| `calling dt.plus_seconds` … `plus_weeks` | calendar arithmetic on a `DateTime` |
| `calling dt.is_before` / `is_after` / `is_same_day` | comparisons on a `DateTime` |
| `calling dt.weekday_name` / `month_name` | "Monday" … / "January" … |
| `calling dt.is_weekend` / `is_leap_year` | calendar predicates |
| `calling chronicle.weekday_name` / `month_name` | labels from a Unix timestamp |
| `calling chronicle.start_of_week` / `start_of_quarter` / `end_of_month` | boundaries |
| `calling chronicle.days_between` / `hours_between` | non-negative distances |
| `calling chronicle.seconds_to_hms` | hours plus a `Pair` of minutes/seconds |

---

### `CHRONICLE_VERSION`

> **CHRONICLE_VERSION** : string

 Chronicle module version constant.

### `pengu_c_time`

> **pengu_c_time**() -> float

 C bridge for `time()`: wall-clock seconds since the Unix epoch (UTC-based).

### `pengu_c_time_monotonic`

> **pengu_c_time_monotonic**() -> float

 C bridge for a high-resolution monotonic clock, in seconds.

### `pengu_c_sleep_ms`

> **pengu_c_sleep_ms**(ms: int) -> void

 C bridge that sleeps the current thread for `ms` milliseconds.

### `pengu_c_sleep_sec`

> **pengu_c_sleep_sec**(sec: float) -> void

 C bridge that sleeps the current thread for `sec` fractional seconds.

### `pengu_c_strftime`

> **pengu_c_strftime**(fmt: string, timestamp: float) -> string

 C bridge that formats `timestamp` with a strftime `fmt` pattern (UTC) into a
 new string; an empty `fmt` falls back to "%Y-%m-%d %H:%M:%S".

### `pengu_c_strptime`

> **pengu_c_strptime**(s: string, fmt: string) -> maybe f64

 C bridge that parses a date/time string into Unix seconds; returns a `maybe
 float` holding `none` when the text does not match a supported pattern.

### `pengu_c_get_utc_year`

> **pengu_c_get_utc_year**(ts: float) -> int

 C bridge returning the UTC year of a timestamp (e.g. 2026).

### `pengu_c_get_utc_month`

> **pengu_c_get_utc_month**(ts: float) -> int

 C bridge returning the UTC month of a timestamp, 1..12.

### `pengu_c_get_utc_day`

> **pengu_c_get_utc_day**(ts: float) -> int

 C bridge returning the UTC day-of-month of a timestamp, 1..31.

### `pengu_c_get_utc_hour`

> **pengu_c_get_utc_hour**(ts: float) -> int

 C bridge returning the UTC hour of a timestamp, 0..23.

### `pengu_c_get_utc_minute`

> **pengu_c_get_utc_minute**(ts: float) -> int

 C bridge returning the UTC minute of a timestamp, 0..59.

### `pengu_c_get_utc_second`

> **pengu_c_get_utc_second**(ts: float) -> int

 C bridge returning the UTC second of a timestamp, 0..60.

### `pengu_c_get_utc_weekday`

> **pengu_c_get_utc_weekday**(ts: float) -> int

 C bridge returning the UTC weekday of a timestamp, 0 = Sunday .. 6 = Saturday.

### `pengu_c_get_utc_yearday`

> **pengu_c_get_utc_yearday**(ts: float) -> int

 C bridge returning the UTC day-of-year of a timestamp, 0..365.

### `pengu_c_get_utc_is_dst`

> **pengu_c_get_utc_is_dst**(ts: float) -> bool

 C bridge reporting daylight-saving time for a timestamp in UTC (always false,
 since UTC itself never observes DST).

### `pengu_c_get_local_year`

> **pengu_c_get_local_year**(ts: float) -> int

 C bridge returning the local-timezone year of a timestamp (e.g. 2026).

### `pengu_c_get_local_month`

> **pengu_c_get_local_month**(ts: float) -> int

 C bridge returning the local-timezone month of a timestamp, 1..12.

### `pengu_c_get_local_day`

> **pengu_c_get_local_day**(ts: float) -> int

 C bridge returning the local-timezone day-of-month of a timestamp, 1..31.

### `pengu_c_get_local_hour`

> **pengu_c_get_local_hour**(ts: float) -> int

 C bridge returning the local-timezone hour of a timestamp, 0..23.

### `pengu_c_get_local_minute`

> **pengu_c_get_local_minute**(ts: float) -> int

 C bridge returning the local-timezone minute of a timestamp, 0..59.

### `pengu_c_get_local_second`

> **pengu_c_get_local_second**(ts: float) -> int

 C bridge returning the local-timezone second of a timestamp, 0..60.

### `pengu_c_get_local_weekday`

> **pengu_c_get_local_weekday**(ts: float) -> int

 C bridge returning the local-timezone weekday of a timestamp,
 0 = Sunday .. 6 = Saturday.

### `pengu_c_get_local_yearday`

> **pengu_c_get_local_yearday**(ts: float) -> int

 C bridge returning the local-timezone day-of-year of a timestamp, 0..365.

### `pengu_c_get_local_is_dst`

> **pengu_c_get_local_is_dst**(ts: float) -> bool

 C bridge reporting whether daylight-saving time is in effect for a timestamp
 in the local time zone.

### `time`

> **time**() -> float

 Returns the current wall-clock time as Unix seconds.

 ## Parámetros
 - None.

 ## Retorno
 The current Unix timestamp as a `float`, resolution set by the platform. The
 value follows the system clock and may jump forwards or backwards; use
 `monotonic` to measure intervals.

 ## Ejemplo
 ```pengu
 let now as float is calling chronicle.time
 ```

### `monotonic`

> **monotonic**() -> float

 Returns a high-resolution monotonic clock reading in seconds.

 ## Parámetros
 - None.

 ## Retorno
 A `float` that only ever moves forward. Its origin is unspecified, so only
 differences between two readings are meaningful.

 ## Ejemplo
 ```pengu
 let t0 as float is calling chronicle.monotonic
 ```

### `sleep_ms`

> **sleep_ms**(ms: int) -> void

 Suspends the current thread for `ms` milliseconds.

 ## Parámetros
 - `ms`: the delay in milliseconds. Zero or negative returns immediately.

 ## Retorno
 Nothing; the weave returns `void`. The call blocks and never aborts.

 ## Ejemplo
 ```pengu
 calling chronicle.sleep_ms with 250
 ```

### `sleep`

> **sleep**(sec: float) -> void

 Suspends the current thread for `sec` fractional seconds.

 ## Parámetros
 - `sec`: the delay in seconds; the fractional part is honoured.

 ## Retorno
 Nothing; the weave returns `void`. The call blocks and never aborts.

 ## Ejemplo
 ```pengu
 calling chronicle.sleep with 0.25
 ```

### `now_ms`

> **now_ms**() -> int

 Returns the current wall-clock time in milliseconds since the Unix epoch.

 ## Parámetros
 - None.

 ## Retorno
 The current Unix time truncated to whole milliseconds as an `int`. Derived
 from `time`, so it inherits the wall-clock behaviour.

 ## Ejemplo
 ```pengu
 let ms as int is calling chronicle.now_ms
 ```

### `time_ms`

> **time_ms**() -> int

 Alias of `now_ms`.

 ## Parámetros
 - None.

 ## Retorno
 The current Unix time in whole milliseconds as an `int`; identical to
 `now_ms`.

 ## Ejemplo
 ```pengu
 let ms as int is calling chronicle.time_ms
 ```

### `monotonic_ms`

> **monotonic_ms**() -> int

 Returns the monotonic clock in milliseconds.

 ## Parámetros
 - None.

 ## Retorno
 The monotonic reading truncated to whole milliseconds as an `int`. Use it for
 elapsed-time arithmetic that must never jump.

 ## Ejemplo
 ```pengu
 let ms as int is calling chronicle.monotonic_ms
 ```

### `utc_year`

> **utc_year**(ts: float) -> int

 Returns the UTC year of timestamp `ts` (e.g. 2026).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The four-digit year as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_year with 1700000000.0    # 2023
 ```

### `utc_month`

> **utc_month**(ts: float) -> int

 Returns the UTC month of timestamp `ts`, 1..12.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The month as an `int`, 1 = January. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_month with 1700000000.0    # 11
 ```

### `utc_day`

> **utc_day**(ts: float) -> int

 Returns the UTC day-of-month of timestamp `ts`, 1..31.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The day of the month as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_day with 1700000000.0    # 14
 ```

### `utc_hour`

> **utc_hour**(ts: float) -> int

 Returns the UTC hour of timestamp `ts`, 0..23.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The hour as an `int` in 24-hour form. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_hour with 1700000000.0    # 22
 ```

### `utc_minute`

> **utc_minute**(ts: float) -> int

 Returns the UTC minute of timestamp `ts`, 0..59.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The minute as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_minute with 1700000000.0    # 13
 ```

### `utc_second`

> **utc_second**(ts: float) -> int

 Returns the UTC second of timestamp `ts`, 0..60.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The second as an `int`; the range allows for a leap second. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_second with 1700000000.0    # 20
 ```

### `utc_weekday`

> **utc_weekday**(ts: float) -> int

 Returns the UTC day-of-week of timestamp `ts` (0 = Sunday .. 6 = Saturday).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The weekday index as an `int`, 0 = Sunday. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_weekday with 1700000000.0    # 2 (Tuesday)
 ```

### `utc_yearday`

> **utc_yearday**(ts: float) -> int

 Returns the UTC day-of-year of timestamp `ts`, 0..365.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The zero-based day of the year as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_yearday with 1700000000.0    # 317
 ```

### `utc_is_dst`

> **utc_is_dst**(ts: float) -> bool

 Reports daylight-saving time for a timestamp in UTC (always false).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 `false` for every `ts`, because UTC never observes DST. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.utc_is_dst with 1700000000.0    # false
 ```

### `local_year`

> **local_year**(ts: float) -> int

 Returns the local-timezone year of timestamp `ts` (e.g. 2026).

 ## Parámetros
 - `ts`: Unix seconds interpreted in the process's local time zone.

 ## Retorno
 The four-digit year as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let y as int is calling chronicle.local_year with 1700000000.0
 ```

### `local_month`

> **local_month**(ts: float) -> int

 Returns the local-timezone month of timestamp `ts`, 1..12.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The month as an `int`, 1 = January. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let m as int is calling chronicle.local_month with 1700000000.0
 ```

### `local_day`

> **local_day**(ts: float) -> int

 Returns the local-timezone day-of-month of timestamp `ts`, 1..31.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The day of the month as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let d as int is calling chronicle.local_day with 1700000000.0
 ```

### `local_hour`

> **local_hour**(ts: float) -> int

 Returns the local-timezone hour of timestamp `ts`, 0..23.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The hour as an `int` in 24-hour form. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let h as int is calling chronicle.local_hour with 1700000000.0
 ```

### `local_minute`

> **local_minute**(ts: float) -> int

 Returns the local-timezone minute of timestamp `ts`, 0..59.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The minute as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let mi as int is calling chronicle.local_minute with 1700000000.0
 ```

### `local_second`

> **local_second**(ts: float) -> int

 Returns the local-timezone second of timestamp `ts`, 0..60.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The second as an `int`; the range allows for a leap second. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let s as int is calling chronicle.local_second with 1700000000.0
 ```

### `local_weekday`

> **local_weekday**(ts: float) -> int

 Returns the local-timezone day-of-week of timestamp `ts` (0 = Sunday .. 6 = Saturday).

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The weekday index as an `int`, 0 = Sunday. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let wd as int is calling chronicle.local_weekday with 1700000000.0
 ```

### `local_yearday`

> **local_yearday**(ts: float) -> int

 Returns the local-timezone day-of-year of timestamp `ts`, 0..365.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 The zero-based day of the year as an `int`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let yd as int is calling chronicle.local_yearday with 1700000000.0
 ```

### `local_is_dst`

> **local_is_dst**(ts: float) -> bool

 Reports whether daylight-saving time is in effect for `ts` in the local time zone.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the local time zone.

 ## Retorno
 `true` while the local zone is observing DST, `false` otherwise. `ts` is
 borrowed.

 ## Ejemplo
 ```pengu
 let dst as bool is calling chronicle.local_is_dst with 1700000000.0
 ```

### `DateTime`

> rune DateTime

```pengu
    year as int
    month as int
    day as int
    hour as int
    minute as int
    second as int
    weekday as int
    yearday as int
    is_dst as bool
```

 Represents a decomposed date and time with individual calendar components.

 ## Parámetros
 - `year`: the civil year (e.g. 2026).
 - `month`: the month, 1..12.
 - `day`: the day of the month, 1..31.
 - `hour`: the hour, 0..23.
 - `minute`: the minute, 0..59.
 - `second`: the second, 0..60.
 - `weekday`: the day of the week, 0 = Sunday .. 6 = Saturday.
 - `yearday`: the zero-based day of the year, 0..365.
 - `is_dst`: whether DST is in effect at the source timestamp.

 ## Retorno
 A value rune of nine scalar fields; it owns no heap memory, so it never needs
 `banish`. `datetime_utc` leaves `is_dst` at `false`; `datetime_local` fills it
 from the local zone.

 ## Ejemplo
 ```pengu
 var dt as chronicle.DateTime with:
     set .year is 2024
     set .month is 2
     set .day is 29
     set .hour is 12
     set .minute is 0
     set .second is 0
     set .weekday is 4
     set .yearday is 59
     set .is_dst is false
 ```

### `to_date`

> **to_date**() -> string

 Formats this DateTime into a "YYYY-MM-DD" string.

 ## Parámetros
 - None: the receiver supplies `year`, `month` and `day`.

 ## Retorno
 A new owned `string`; release it with `banish`. Years are not padded, so
 year 5 renders as "5".

 ## Ejemplo
 ```pengu
 calling dt.to_date    # "2023-11-14"
 ```

### `to_time`

> **to_time**() -> string

 Formats this DateTime into an "HH:MM:SS" string.

 ## Parámetros
 - None: the receiver supplies `hour`, `minute` and `second`.

 ## Retorno
 A new owned `string`; release it with `banish`. Every field is zero-padded
 to two digits.

 ## Ejemplo
 ```pengu
 calling dt.to_time    # "22:13:20"
 ```

### `to_iso`

> **to_iso**() -> string

 Formats this DateTime into an ISO 8601 "YYYY-MM-DDTHH:MM:SSZ" string.

 ## Parámetros
 - None: the receiver supplies every date and time field.

 ## Retorno
 A new owned `string` ending in `Z`; release it with `banish`. The record is
 always rendered as if it were UTC.

 ## Ejemplo
 ```pengu
 calling dt.to_iso    # "2023-11-14T22:13:20Z"
 ```

### `to_timestamp`

> **to_timestamp**() -> float

 Converts this DateTime back into Unix seconds, the inverse of `datetime_utc`.

 ## Parámetros
 - None: the receiver supplies the UTC date and time fields.

 ## Retorno
 The Unix timestamp as a `float`, exact to the second. A record built by
 `datetime_utc` round-trips exactly; the field `weekday`, `yearday` and
 `is_dst` are ignored, and years below 1970 are outside the documented
 range.

 ## Ejemplo
 ```pengu
 calling (calling chronicle.datetime_utc with 1700000000.0).to_timestamp    # 1700000000.0
 ```

### `plus_seconds`

> **plus_seconds**(n: int) -> DateTime

 Adds `n` seconds and returns the resulting UTC DateTime.

 ## Parámetros
 - `n`: whole seconds to add; may be negative.

 ## Retorno
 A fresh `DateTime` built by `datetime_utc`, so `is_dst` is `false`; it owns
 no heap memory. The receiver is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling dt.plus_seconds with 90
 ```

### `plus_minutes`

> **plus_minutes**(n: int) -> DateTime

 Adds `n` minutes and returns the resulting UTC DateTime.

 ## Parámetros
 - `n`: whole minutes to add (60 seconds each); may be negative.

 ## Retorno
 A fresh `DateTime` built by `datetime_utc`; it owns no heap memory. The
 receiver is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling dt.plus_minutes with -30
 ```

### `plus_hours`

> **plus_hours**(n: int) -> DateTime

 Adds `n` hours and returns the resulting UTC DateTime.

 ## Parámetros
 - `n`: whole hours to add (3600 seconds each); may be negative.

 ## Retorno
 A fresh `DateTime` built by `datetime_utc`; it owns no heap memory. The
 receiver is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling dt.plus_hours with 1
 ```

### `plus_days`

> **plus_days**(n: int) -> DateTime

 Adds `n` days and returns the resulting UTC DateTime.

 ## Parámetros
 - `n`: whole days to add (86400 seconds each); may be negative.

 ## Retorno
 A fresh `DateTime` built by `datetime_utc`; it owns no heap memory. The
 receiver is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling dt.plus_days with 7
 ```

### `plus_weeks`

> **plus_weeks**(n: int) -> DateTime

 Adds `n` weeks and returns the resulting UTC DateTime.

 ## Parámetros
 - `n`: whole weeks to add (604800 seconds each); may be negative.

 ## Retorno
 A fresh `DateTime` built by `datetime_utc`; it owns no heap memory. The
 receiver is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling dt.plus_weeks with 2
 ```

### `is_before`

> **is_before**(other: DateTime) -> bool

 Reports whether this DateTime is strictly earlier than `other`.

 ## Parámetros
 - `other`: the DateTime to compare against.

 ## Retorno
 `true` when the receiver's Unix second is strictly less than `other`'s.
 Both records are borrowed.

 ## Ejemplo
 ```pengu
 calling a.is_before with b
 ```

### `is_after`

> **is_after**(other: DateTime) -> bool

 Reports whether this DateTime is strictly later than `other`.

 ## Parámetros
 - `other`: the DateTime to compare against.

 ## Retorno
 `true` when the receiver's Unix second is strictly greater than `other`'s.
 Both records are borrowed.

 ## Ejemplo
 ```pengu
 calling a.is_after with b
 ```

### `is_same_day`

> **is_same_day**(other: DateTime) -> bool

 Reports whether both DateTimes fall on the same UTC calendar day.

 ## Parámetros
 - `other`: the DateTime to compare against.

 ## Retorno
 `true` when `start_of_day` of both timestamps is equal, whatever the time
 of day. Both records are borrowed.

 ## Ejemplo
 ```pengu
 calling a.is_same_day with b
 ```

### `weekday_name`

> **weekday_name**() -> string

 Returns the English name of this DateTime's weekday.

 ## Parámetros
 - None: the receiver supplies `weekday`.

 ## Retorno
 A new owned `string` ("Sunday" .. "Saturday"); release it with `banish`.
 An out-of-range `weekday` yields the empty string.

 ## Ejemplo
 ```pengu
 calling dt.weekday_name    # "Tuesday"
 ```

### `month_name`

> **month_name**() -> string

 Returns the English name of this DateTime's month.

 ## Parámetros
 - None: the receiver supplies `month`.

 ## Retorno
 A new owned `string` ("January" .. "December"); release it with `banish`.
 An out-of-range `month` yields the empty string.

 ## Ejemplo
 ```pengu
 calling dt.month_name    # "November"
 ```

### `is_weekend`

> **is_weekend**() -> bool

 Reports whether this DateTime falls on a Saturday or a Sunday.

 ## Parámetros
 - None: the receiver supplies `weekday`.

 ## Retorno
 `true` when `weekday` is 0 (Sunday) or 6 (Saturday), `false` otherwise.

 ## Ejemplo
 ```pengu
 calling dt.is_weekend    # false on a Tuesday
 ```

### `is_leap_year`

> **is_leap_year**() -> bool

 Reports whether this DateTime's `year` is a leap year.

 ## Parámetros
 - None: the receiver supplies `year`.

 ## Retorno
 `true` for a Gregorian leap year, using the same rule as the module
 function `is_leap_year` (divisible by 4, except centuries not divisible by
 400).

 ## Ejemplo
 ```pengu
 calling dt.is_leap_year    # true for 2024
 ```

### `datetime_utc`

> **datetime_utc**(ts: float) -> DateTime

 Builds a DateTime record from `ts` interpreted in UTC.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 A fresh `DateTime` whose `is_dst` is always `false`. It owns no heap memory,
 so it never needs `banish`; `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let dt as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
 ```

### `datetime_local`

> **datetime_local**(ts: float) -> DateTime

 Builds a DateTime record from `ts` interpreted in the local time zone.

 ## Parámetros
 - `ts`: Unix seconds interpreted in the process's local time zone.

 ## Retorno
 A fresh `DateTime` whose fields come from the `local_*` getters and whose
 `is_dst` reflects the local zone. It owns no heap memory; `ts` is borrowed.

 ## Ejemplo
 ```pengu
 let dt as chronicle.DateTime is calling chronicle.datetime_local with 1700000000.0
 ```

### `days_in_month`

> **days_in_month**(y: int, m: int) -> int

 Returns the number of days in month `m` for year `y`.

 ## Parámetros
 - `y`: the civil year, used only to resolve February.
 - `m`: the month, 1-based (1 = January).

 ## Retorno
 The day count as an `int` (28..31). An out-of-range `m` returns 0 rather than
 silently reporting a 31-day month, so callers can validate input with
 `if calling days_in_month with y, m == 0`.

 ## Ejemplo
 ```pengu
 calling chronicle.days_in_month with 2024, 2    # 29
 ```

### `days_in_year`

> **days_in_year**(y: int) -> int

 Returns the number of days in year `y` (366 for leap years, 365 otherwise).

 ## Parámetros
 - `y`: the civil year to measure.

 ## Retorno
 `366` for a Gregorian leap year, `365` otherwise, as an `int`.

 ## Ejemplo
 ```pengu
 calling chronicle.days_in_year with 2024    # 366
 ```

### `start_of_day`

> **start_of_day**(ts: float) -> float

 Returns timestamp rounded down to the start of the UTC day (00:00:00 UTC).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The timestamp of 00:00:00 UTC on the same UTC day as `ts`, as a `float`.
 Negative `ts` is normalised to the correct day. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.start_of_day with 1700000000.0    # 1699920000.0
 ```

### `end_of_day`

> **end_of_day**(ts: float) -> float

 Returns timestamp of the end of the UTC day (23:59:59 UTC).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The timestamp of 23:59:59 UTC on the same UTC day as `ts`, as a `float`
 (`start_of_day` plus 86399 seconds). `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.end_of_day with 1700000000.0    # 1700006400.0 (float32)
 ```

### `today`

> **today**() -> float

 Returns the start of the current UTC day (00:00:00 UTC).

 ## Parámetros
 - None.

 ## Retorno
 A `float` derived from `time`, so it follows the wall clock and is not
 suitable for deterministic tests.

 ## Ejemplo
 ```pengu
 calling spark.println with calling chronicle.to_date_string with (calling chronicle.today)
 ```

### `yesterday`

> **yesterday**() -> float

 Returns the start of yesterday in UTC.

 ## Parámetros
 - None.

 ## Retorno
 `today` minus 86400 seconds, as a `float`.

 ## Ejemplo
 ```pengu
 let t as float is calling chronicle.yesterday
 ```

### `tomorrow`

> **tomorrow**() -> float

 Returns the start of tomorrow in UTC.

 ## Parámetros
 - None.

 ## Retorno
 `today` plus 86400 seconds, as a `float`.

 ## Ejemplo
 ```pengu
 let t as float is calling chronicle.tomorrow
 ```

### `start_of_month`

> **start_of_month**(ts: float) -> float

 Returns the start of the month in UTC (00:00:00 UTC on the 1st of the month).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The timestamp of midnight on day 1 of the same UTC month, as a `float`. `ts`
 is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.start_of_month with 1700000000.0    # 1698796800.0
 ```

### `start_of_year`

> **start_of_year**(ts: float) -> float

 Returns the start of the year in UTC (00:00:00 UTC on January 1st).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The timestamp of midnight on January 1st of the same UTC year, as a `float`.
 `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.start_of_year with 1700000000.0    # 1672531200.0
 ```

### `start_of_week`

> **start_of_week**(ts: float) -> float

 Returns the start of the week in UTC: Monday 00:00:00 UTC.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 The timestamp of the Monday on or before `ts`, at 00:00:00 UTC, as a `float`.
 Weeks start on Monday, following ISO 8601. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.start_of_week with 1700000000.0    # 1699833600.0 (Monday)
 ```

### `start_of_quarter`

> **start_of_quarter**(ts: float) -> float

 Returns the start of the quarter in UTC.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC, with a year of 1970 or later.

 ## Retorno
 The timestamp of 00:00:00 UTC on the first day of the calendar quarter
 (January, April, July or October) containing `ts`, as a `float`. `ts` is
 borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.start_of_quarter with 1700000000.0    # 1696118400.0 (Q4)
 ```

### `end_of_month`

> **end_of_month**(ts: float) -> float

 Returns the end of the month in UTC (23:59:59 UTC on the last day).

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC, with a year of 1970 or later.

 ## Retorno
 The timestamp of 23:59:59 UTC on the last day of the same UTC month, as a
 `float`, honouring leap Februaries. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.end_of_month with 1706745600.0    # 1709251200.0 (float32) (Feb 2024)
 ```

### `_weekday_label`

> **_weekday_label**(idx: int) -> string

 Maps a weekday index (0 = Sunday .. 6 = Saturday) to its English name.

### `_month_label`

> **_month_label**(idx: int) -> string

 Maps a month number (1 = January .. 12 = December) to its English name.

### `format`

> **format**(fmt: string, timestamp: float) -> string

 Formats `timestamp` (Unix seconds) with a strftime `fmt` pattern in UTC.

 ## Parámetros
 - `fmt`: the strftime pattern; an empty pattern falls back to
   "%Y-%m-%d %H:%M:%S".
 - `timestamp`: the Unix seconds to render, interpreted in UTC.

 ## Retorno
 A new owned `string`; release it with `banish`. Both arguments are borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.format with "%Y-%m-%d", 0.0    # "1970-01-01"
 ```

### `format_now`

> **format_now**(fmt: string) -> string

 Formats the current wall-clock time with a strftime `fmt` pattern in UTC.

 ## Parámetros
 - `fmt`: the strftime pattern.

 ## Retorno
 A new owned `string`; release it with `banish`. Derived from `time`, so it is
 not deterministic.

 ## Ejemplo
 ```pengu
 calling chronicle.format_now with "%Y-%m-%d %H:%M:%S"
 ```

### `parse`

> **parse**(s: string, fmt: string) -> maybe float

 Parses `s` into Unix seconds, returning a maybe float.

 ## Parámetros
 - `s`: the text to parse, in the layout described by `fmt`.
 - `fmt`: the strptime pattern.

 ## Retorno
 `some ts` with the parsed Unix seconds, or `maybe none` when `s` does not
 match `fmt`. The `maybe` owns nothing; both arguments are borrowed.

 ## Motivo
 The parser is anchored on the runtime's ISO-like bridge: it accepts
 `YYYY-MM-DD`, optionally followed by `THH:MM:SS`, and resolves the result in
 the process's local time zone. `fmt` is accepted so the signature stays
 stable, but the bridge does not honour an arbitrary pattern yet. A trailing
 time that cannot be read is taken as midnight rather than rejected.

 ## Ejemplo
 ```pengu
 let ts as maybe float is calling chronicle.parse with "1970-01-01", "%Y-%m-%d"
 ```

### `now_utc_iso`

> **now_utc_iso**() -> string

 Formats the current UTC time as an ISO 8601 string (e.g. "2026-09-25T14:30:00Z").

 ## Parámetros
 - None.

 ## Retorno
 A new owned `string`; release it with `banish`. Derived from `time`, so it is
 not deterministic.

 ## Ejemplo
 ```pengu
 calling spark.println with calling chronicle.now_utc_iso
 ```

### `now_local_iso`

> **now_local_iso**() -> string

 Formats the current local time as an ISO 8601 string (e.g. "2026-09-25T14:30:00").

 ## Parámetros
 - None.

 ## Retorno
 A new owned `string` without a trailing zone marker; release it with
 `banish`. Derived from `time`, so it is not deterministic.

 ## Ejemplo
 ```pengu
 calling spark.println with calling chronicle.now_local_iso
 ```

### `now_date`

> **now_date**() -> string

 Formats the current local date as "YYYY-MM-DD".

 ## Parámetros
 - None.

 ## Retorno
 A new owned `string`; release it with `banish`. Derived from `time`, so it is
 not deterministic.

 ## Ejemplo
 ```pengu
 calling spark.println with calling chronicle.now_date
 ```

### `now_time`

> **now_time**() -> string

 Formats the current local time as "HH:MM:SS".

 ## Parámetros
 - None.

 ## Retorno
 A new owned `string`; release it with `banish`. Derived from `time`, so it is
 not deterministic.

 ## Ejemplo
 ```pengu
 calling spark.println with calling chronicle.now_time
 ```

### `from_iso`

> **from_iso**(s: string) -> maybe float

 Parses an ISO 8601 date or datetime string into UTC Unix seconds.

 ## Parámetros
 - `s`: "2026-09-25T14:30:24Z", "2026-09-25T14:30:24",
   "2026-09-25 14:30:24" or "2026-09-25"; surrounding whitespace is trimmed.

 ## Retorno
 `some ts` with the UTC Unix seconds, or `maybe none` when the text is not a
 valid date in 1970.. with an optional valid time. Round-trip with `to_iso(ts)`
 is guaranteed exact to the second. The result owns nothing; `s` is borrowed.

 ## Ejemplo
 ```pengu
 let ts as maybe float is calling chronicle.from_iso with "1970-01-01T00:00:00Z"
 ```

### `to_date_string`

> **to_date_string**(ts: float) -> string

 Formats `ts` as a date string "YYYY-MM-DD" in UTC.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 A new owned `string`; release it with `banish`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.to_date_string with 0.0    # "1970-01-01"
 ```

### `to_time_string`

> **to_time_string**(ts: float) -> string

 Formats `ts` as a time string "HH:MM:SS" in UTC.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 A new owned `string`; release it with `banish`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.to_time_string with 3661.0    # "01:01:01"
 ```

### `to_datetime_string`

> **to_datetime_string**(ts: float) -> string

 Formats `ts` as a datetime string "YYYY-MM-DD HH:MM:SS" in UTC.

 ## Parámetros
 - `ts`: Unix seconds interpreted in UTC.

 ## Retorno
 A new owned `string`; release it with `banish`. `ts` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.to_datetime_string with 0.0    # "1970-01-01 00:00:00"
 ```

### `add_seconds`

> **add_seconds**(ts: float, n: int) -> float

 Adds `n` seconds to `ts`.

 ## Parámetros
 - `ts`: the starting Unix timestamp.
 - `n`: whole seconds to add; defaults to 1.

 ## Retorno
 The new timestamp as a `float`. `ts` is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling chronicle.add_seconds with 1700000000.0, 30
 ```

### `add_minutes`

> **add_minutes**(ts: float, n: int) -> float

 Adds `n` minutes (60s each) to `ts`.

 ## Parámetros
 - `ts`: the starting Unix timestamp.
 - `n`: whole minutes to add; defaults to 1.

 ## Retorno
 The new timestamp as a `float`. `ts` is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling chronicle.add_minutes with 1700000000.0, 15
 ```

### `add_hours`

> **add_hours**(ts: float, n: int) -> float

 Adds `n` hours (3600s each) to `ts`.

 ## Parámetros
 - `ts`: the starting Unix timestamp.
 - `n`: whole hours to add; defaults to 1.

 ## Retorno
 The new timestamp as a `float`. `ts` is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling chronicle.add_hours with 1700000000.0, 2
 ```

### `add_days`

> **add_days**(ts: float, n: int) -> float

 Adds `n` days (86400s each) to `ts`.

 ## Parámetros
 - `ts`: the starting Unix timestamp.
 - `n`: whole days to add; defaults to 1.

 ## Retorno
 The new timestamp as a `float`. `ts` is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling chronicle.add_days with 1700000000.0, 7
 ```

### `add_weeks`

> **add_weeks**(ts: float, n: int) -> float

 Adds `n` weeks (604800s each) to `ts`.

 ## Parámetros
 - `ts`: the starting Unix timestamp.
 - `n`: whole weeks to add; defaults to 1.

 ## Retorno
 The new timestamp as a `float`. `ts` is borrowed and not modified.

 ## Ejemplo
 ```pengu
 calling chronicle.add_weeks with 1700000000.0, 2
 ```

### `diff_seconds`

> **diff_seconds**(a: float, b: float) -> float

 Returns the difference in seconds between two timestamps (`a - b`).

 ## Parámetros
 - `a`: the minuend timestamp.
 - `b`: the subtrahend timestamp.

 ## Retorno
 `a - b` as a `float`, negative when `a` is earlier. Both are borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.diff_seconds with 10.0, 4.0    # 6.0
 ```

### `diff_days`

> **diff_days**(a: float, b: float) -> int

 Returns the difference in whole days between two timestamps (`(a - b) / 86400`).

 ## Parámetros
 - `a`: the minuend timestamp.
 - `b`: the subtrahend timestamp.

 ## Retorno
 The signed day count as an `int`, truncated towards zero. Both are borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.diff_days with 259200.0, 0.0    # 3
 ```

### `days_between`

> **days_between**(a: float, b: float) -> int

 Returns the non-negative number of whole days between two timestamps.

 ## Parámetros
 - `a`: the first timestamp.
 - `b`: the second timestamp.

 ## Retorno
 The absolute distance as an `int`, truncated towards zero, so the result does
 not depend on the argument order. Unlike `diff_days`, it is never negative.
 Both are borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.days_between with 0.0, 259200.0    # 3
 ```

### `hours_between`

> **hours_between**(a: float, b: float) -> int

 Returns the non-negative number of whole hours between two timestamps.

 ## Parámetros
 - `a`: the first timestamp.
 - `b`: the second timestamp.

 ## Retorno
 The absolute distance as an `int`, truncated towards zero, so the result does
 not depend on the argument order. Both are borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.hours_between with 0.0, 7200.0    # 2
 ```

### `is_between`

> **is_between**(ts: float, lo: float, hi: float) -> bool

 Returns true if `ts` falls within `[lo, hi]` inclusive.

 ## Parámetros
 - `ts`: the timestamp to test.
 - `lo`: the inclusive lower bound.
 - `hi`: the inclusive upper bound.

 ## Retorno
 `true` when `lo <= ts <= hi`, `false` otherwise. All three are borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.is_between with 5.0, 5.0, 5.0    # true
 ```

### `format_duration`

> **format_duration**(sec: float) -> string

 Formats duration in seconds into human-readable text (e.g. "2h 30m 45s", "15m 30s", "10s").

 ## Parámetros
 - `sec`: the duration in seconds; the fractional part is truncated.

 ## Retorno
 A new owned `string`; release it with `banish`. Zero and negative durations
 render as "0s". `sec` is borrowed.

 ## Ejemplo
 ```pengu
 calling chronicle.format_duration with 9045.0    # "2h 30m 45s"
 ```

### `parse_duration`

> **parse_duration**(s: string) -> maybe float

 Parses human duration string ("45s", "30m", "2h", "7d", or raw seconds "45") into seconds.

 ## Parámetros
 - `s`: the duration text; surrounding whitespace is trimmed. A trailing "s",
   "m", "h" or "d" selects the unit, and a bare integer counts as seconds.

 ## Retorno
 `some sec` with the duration in seconds, or `maybe none` when the text is not
 a supported duration. The `maybe` owns nothing; `s` is borrowed.

 ## Ejemplo
 ```pengu
 let d as maybe float is calling chronicle.parse_duration with "30m"
 ```

### `seconds_to_hms`

> **seconds_to_hms**(sec: int) -> Pair__int__Pair__int__int

 Splits a whole number of seconds into hours, minutes and seconds.

 ## Parámetros
 - `sec`: the number of seconds; its absolute value is used.

 ## Retorno
 An `oracle.Pair` whose `first` is the whole hours and whose `second` is an
 `oracle.Pair` of the remaining minutes (`second.first`) and seconds
 (`second.second`). It owns no heap memory; `sec` is borrowed.

 ## Ejemplo
 ```pengu
 let p as oracle.Pair of int and oracle.Pair of int and int is calling chronicle.seconds_to_hms with 3661
 calling spark.println with (p.first) to string            # 1
 calling spark.println with (p.second.first) to string     # 1
 calling spark.println with (p.second.second) to string    # 1
 ```

### `Stopwatch`

> rune Stopwatch

```pengu
    started_at as float
```

 High-resolution monotonic elapsed time measurement.

 ## Parámetros
 - `started_at`: a `monotonic` reading captured by `ritual new` or `reset`.

 ## Retorno
 A value rune holding one `float`; it owns no heap memory, so it never needs
 `banish`.

 ## Ejemplo
 ```pengu
 var sw as chronicle.Stopwatch is calling chronicle.new_stopwatch
 ```

### `new`

> **new**() -> Stopwatch

 Creates and starts a new Stopwatch using monotonic clock.

 ## Parámetros
 - None.

 ## Retorno
 A fresh `Stopwatch` whose `started_at` is the current `monotonic` reading;
 it owns no heap memory.

 ## Ejemplo
 ```pengu
 var sw as chronicle.Stopwatch is calling chronicle.Stopwatch.new
 ```

### `elapsed_sec`

> **elapsed_sec**() -> float

 Returns elapsed seconds since stopwatch was created or reset.

 ## Parámetros
 - None: the receiver supplies `started_at`.

 ## Retorno
 The elapsed monotonic seconds as a non-negative `float`. The receiver is
 borrowed and not modified.

 ## Ejemplo
 ```pengu
 let sec as float is calling sw.elapsed_sec
 ```

### `elapsed_ms`

> **elapsed_ms**() -> int

 Returns elapsed milliseconds since stopwatch was created or reset.

 ## Parámetros
 - None: the receiver supplies `started_at`.

 ## Retorno
 The elapsed monotonic milliseconds truncated as a non-negative `int`. The
 receiver is borrowed and not modified.

 ## Ejemplo
 ```pengu
 let ms as int is calling sw.elapsed_ms
 ```

### `reset`

> **reset**() -> void

 Resets the stopwatch start time to now.

 ## Parámetros
 - None.

 ## Retorno
 Nothing; the weave returns `void`. It overwrites `started_at` with the
 current `monotonic` reading and never aborts.

 ## Ejemplo
 ```pengu
 calling sw.reset
 ```

### `new_stopwatch`

> **new_stopwatch**() -> Stopwatch

 Creates and starts a new Stopwatch using monotonic clock.

 ## Parámetros
 - None.

 ## Retorno
 A fresh `Stopwatch`; it owns no heap memory. Equivalent to
 `calling Stopwatch.new`.

 ## Ejemplo
 ```pengu
 var sw as chronicle.Stopwatch is calling chronicle.new_stopwatch
 ```

### `_is_leap_year`

> **_is_leap_year**(y: int) -> bool

 True when `y` is a Gregorian leap year (divisible by 4, not by 100 unless by 400).

### `_epoch_days`

> **_epoch_days**(y: int, m: int, d: int) -> int

 Whole days between 1970-01-01 and the civil date `y`-`m`-`d`, all in UTC.

### `_parse_slice`

> **_parse_slice**(text: string, from_i: int, to_i: int) -> maybe int

 Parses the `[from_i, to_i)` slice of `text` as a decimal int, freeing the slice.

### `_pad2`

> **_pad2**(n: int) -> string

 Zero-pads `n` to two digits when it is below 10.

### `_chr_expect`

> **_chr_expect**(cond: bool, label: string) -> void

 Aborts via `spark.panic` unless `cond` holds.

### `_chr_expect_eq_int`

> **_chr_expect_eq_int**(got: int, want: int, label: string) -> void

 Aborts via `spark.panic` unless `got` equals `want`.

### `_chr_expect_eq_string`

> **_chr_expect_eq_string**(got: string, want: string, label: string) -> void

 Aborts via `spark.panic` unless the two strings are byte-equal.

### `_chr_expect_close`

> **_chr_expect_close**(got: float, want: float, label: string) -> void

 Aborts via `spark.panic` unless `got` and `want` differ by less than 0.000001.

### `_chr_expect_maybe_float`

> **_chr_expect_maybe_float**(opt: maybe float, want: float, label: string) -> void

 Aborts via `spark.panic` unless `opt` holds a value close to `want`.

### `"chronicle_version matches the CHRONICLE_VERSION constant"`

> test "chronicle_version matches the CHRONICLE_VERSION constant"

_Undocumented._

### `"pad2 zero-pads single digits and keeps two-digit values"`

> test "pad2 zero-pads single digits and keeps two-digit values"

_Undocumented._

### `"DateTime.to_date and to_time format a constructed record"`

> test "DateTime.to_date and to_time format a constructed record"

_Undocumented._

### `"to_iso and DateTime.to_iso format the epoch in UTC"`

> test "to_iso and DateTime.to_iso format the epoch in UTC"

_Undocumented._

### `"from_iso round-trips to_iso for fixed timestamps"`

> test "from_iso round-trips to_iso for fixed timestamps"

_Undocumented._

### `"from_iso accepts a space separator and a date-only form"`

> test "from_iso accepts a space separator and a date-only form"

_Undocumented._

### `"from_iso rejects malformed input with none"`

> test "from_iso rejects malformed input with none"

_Undocumented._

### `"to_timestamp inverts datetime_utc for fixed timestamps"`

> test "to_timestamp inverts datetime_utc for fixed timestamps"

_Undocumented._

### `"to_timestamp handles a leap day"`

> test "to_timestamp handles a leap day"

_Undocumented._

### `"plus_seconds and plus_minutes move a DateTime forward"`

> test "plus_seconds and plus_minutes move a DateTime forward"

_Undocumented._

### `"plus_hours, plus_days and plus_weeks use their unit"`

> test "plus_hours, plus_days and plus_weeks use their unit"

_Undocumented._

### `"DateTime.is_before and is_after compare timestamps"`

> test "DateTime.is_before and is_after compare timestamps"

_Undocumented._

### `"DateTime.is_same_day ignores the time of day"`

> test "DateTime.is_same_day ignores the time of day"

_Undocumented._

### `"DateTime.weekday_name labels known epochs"`

> test "DateTime.weekday_name labels known epochs"

_Undocumented._

### `"DateTime.month_name labels known epochs"`

> test "DateTime.month_name labels known epochs"

_Undocumented._

### `"module weekday_name and month_name label known epochs"`

> test "module weekday_name and month_name label known epochs"

_Undocumented._

### `"DateTime.is_weekend is true on Saturday and Sunday"`

> test "DateTime.is_weekend is true on Saturday and Sunday"

_Undocumented._

### `"DateTime.is_leap_year and the module is_leap_year agree"`

> test "DateTime.is_leap_year and the module is_leap_year agree"

_Undocumented._

### `"days_in_month and days_in_year count a leap year"`

> test "days_in_month and days_in_year count a leap year"

_Undocumented._

### `"start_of_day and end_of_day bound the UTC day"`

> test "start_of_day and end_of_day bound the UTC day"

_Undocumented._

### `"start_of_month and start_of_year truncate to boundaries"`

> test "start_of_month and start_of_year truncate to boundaries"

_Undocumented._

### `"start_of_week returns the Monday midnight"`

> test "start_of_week returns the Monday midnight"

_Undocumented._

### `"start_of_quarter returns the first day of the quarter"`

> test "start_of_quarter returns the first day of the quarter"

_Undocumented._

### `"end_of_month returns the last second of the month"`

> test "end_of_month returns the last second of the month"

_Undocumented._

### `"days_between and hours_between are non-negative"`

> test "days_between and hours_between are non-negative"

_Undocumented._

### `"diff_seconds and diff_days are signed"`

> test "diff_seconds and diff_days are signed"

_Undocumented._

### `"add_seconds through add_weeks use their unit and default of one"`

> test "add_seconds through add_weeks use their unit and default of one"

_Undocumented._

### `"is_before, is_after and is_between on timestamps"`

> test "is_before, is_after and is_between on timestamps"

_Undocumented._

### `"format_duration renders hours, minutes and seconds"`

> test "format_duration renders hours, minutes and seconds"

_Undocumented._

### `"parse_duration accepts suffixes and raw seconds"`

> test "parse_duration accepts suffixes and raw seconds"

_Undocumented._

### `"seconds_to_hms splits into hours, minutes and seconds"`

> test "seconds_to_hms splits into hours, minutes and seconds"

_Undocumented._

### `"format and the to_*_string helpers agree on UTC"`

> test "format and the to_*_string helpers agree on UTC"

_Undocumented._

### `"utc_* getters read the reviewed fields"`

> test "utc_* getters read the reviewed fields"

_Undocumented._

### `"datetime_local mirrors the local_* getters"`

> test "datetime_local mirrors the local_* getters"

_Undocumented._

### `"Stopwatch reports non-negative elapsed time and resets"`

> test "Stopwatch reports non-negative elapsed time and resets"

_Undocumented._

