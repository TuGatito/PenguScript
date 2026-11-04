# std.chrono

> Source: `std/chrono.pengu`

std/chrono.pengu — high-precision instants and durations.

This is the additive vaqt-backed API.  The historical `std.chronicle` API
(Unix seconds as `float`, libc `strftime`/`localtime`) remains unchanged for
compatibility; new code that needs nanoseconds, ISO 8601 round-trips or
calendar arithmetic should use `Instant`/`Duration` here.

`Instant` stores seconds since 0001-01-01 UTC plus nanoseconds within the
second, exactly like Go's `time.Time` (and vaqt).  `Duration` is a signed
64-bit nanosecond count (about ±290 years).

## Memory
`Instant` and `Duration` are plain values.  `format_iso`/`format_date`/
`format_datetime` return an owned string (release with `banish`); the rest
allocate nothing.

## Example
```pengu
import std.chrono
import std.spark

weave main into int:
    var t as chrono.Instant is calling chrono.now
    var s as string is calling t.format_iso with 0
    calling spark.println with s
    banish s
    return 0
```

---

### `CHRONO_VERSION`

> **CHRONO_VERSION** : string

_Undocumented._

### `NANOSECOND`

> **NANOSECOND** : i64

 Nanoseconds in one microsecond/millisecond/second/minute/hour.

### `MICROSECOND`

> **MICROSECOND** : i64

_Undocumented._

### `MILLISECOND`

> **MILLISECOND** : i64

_Undocumented._

### `SECOND`

> **SECOND** : i64

_Undocumented._

### `MINUTE`

> **MINUTE** : i64

_Undocumented._

### `HOUR`

> **HOUR** : i64

_Undocumented._

### `Instant`

> rune Instant

```pengu
    sec as i64
    nsec as i32
```

 A high-precision instant: seconds since 0001-01-01 UTC and nanoseconds.

### `Duration`

> alias Duration

 A signed duration in nanoseconds.

### `pengu_vaqt_now`

> **pengu_vaqt_now**(sec: ref to i64, nsec: ref to i32) -> void

_Undocumented._

### `pengu_vaqt_from_unix`

> **pengu_vaqt_from_unix**(sec: i64, nsec: i32, out_sec: ref to i64, out_nsec: ref to i32) -> void

_Undocumented._

### `pengu_vaqt_to_unix`

> **pengu_vaqt_to_unix**(sec: i64, nsec: i32, out_sec: ref to i64, out_nsec: ref to i32) -> void

_Undocumented._

### `pengu_vaqt_year`

> **pengu_vaqt_year**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_month`

> **pengu_vaqt_month**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_day`

> **pengu_vaqt_day**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_hour`

> **pengu_vaqt_hour**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_minute`

> **pengu_vaqt_minute**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_second`

> **pengu_vaqt_second**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_nano`

> **pengu_vaqt_nano**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_weekday`

> **pengu_vaqt_weekday**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_yearday`

> **pengu_vaqt_yearday**(sec: i64, nsec: i32) -> int

_Undocumented._

### `pengu_vaqt_compare`

> **pengu_vaqt_compare**(asec: i64, ansec: i32, bsec: i64, bnsec: i32) -> int

_Undocumented._

### `pengu_vaqt_add`

> **pengu_vaqt_add**(sec: i64, nsec: i32, add_sec: i64, add_nsec: i32, out_sec: ref to i64, out_nsec: ref to i32) -> void

_Undocumented._

### `pengu_vaqt_add_date`

> **pengu_vaqt_add_date**(sec: i64, nsec: i32, years: int, months: int, days: int, out_sec: ref to i64, out_nsec: ref to i32) -> void

_Undocumented._

### `pengu_vaqt_format_iso`

> **pengu_vaqt_format_iso**(sec: i64, nsec: i32, offset: int) -> string

_Undocumented._

### `pengu_vaqt_format_date`

> **pengu_vaqt_format_date**(sec: i64, nsec: i32, offset: int) -> string

_Undocumented._

### `pengu_vaqt_format_datetime`

> **pengu_vaqt_format_datetime**(sec: i64, nsec: i32, offset: int) -> string

_Undocumented._

### `pengu_vaqt_parse_iso`

> **pengu_vaqt_parse_iso**(s: string, out_sec: ref to i64, out_nsec: ref to i32) -> bool

_Undocumented._

### `now`

> **now**() -> Instant

 Current UTC instant.

### `from_unix`

> **from_unix**(sec: i64, nsec: i32) -> Instant

 Builds an Instant from a Unix timestamp (seconds since 1970 UTC).

### `from_unix_sec`

> **from_unix_sec**(sec: i64) -> Instant

 Builds an Instant from a Unix timestamp expressed as whole seconds.

### `to_unix`

> **to_unix**(t: Instant) -> i64

 Returns the Unix timestamp in whole seconds (truncating sub-second part).

### `to_unix_nano`

> **to_unix_nano**(t: Instant) -> i64

 Returns the Unix timestamp in nanoseconds.

### `format_iso`

> **format_iso**(t: Instant, offset: int) -> string

 ISO 8601 representation. `offset` is seconds east of UTC (0 = Z).

### `format_date`

> **format_date**(t: Instant, offset: int) -> string

_Undocumented._

### `format_datetime`

> **format_datetime**(t: Instant, offset: int) -> string

_Undocumented._

### `parse_iso`

> **parse_iso**(s: string) -> maybe Instant

 Parses the ISO/fecha/hora layouts supported by vaqt. Returns `maybe none`
 for text that is not a valid zero-valued instant.

### `year`

> **year**(t: Instant) -> int

 Calendar fields in UTC.

### `month`

> **month**(t: Instant) -> int

_Undocumented._

### `day`

> **day**(t: Instant) -> int

_Undocumented._

### `hour`

> **hour**(t: Instant) -> int

_Undocumented._

### `minute`

> **minute**(t: Instant) -> int

_Undocumented._

### `second`

> **second**(t: Instant) -> int

_Undocumented._

### `nanosecond`

> **nanosecond**(t: Instant) -> int

_Undocumented._

### `weekday`

> **weekday**(t: Instant) -> int

_Undocumented._

### `yearday`

> **yearday**(t: Instant) -> int

_Undocumented._

### `compare`

> **compare**(a: Instant, b: Instant) -> int

 -1, 0 or 1.

### `is_before`

> **is_before**(a: Instant, b: Instant) -> bool

_Undocumented._

### `is_after`

> **is_after**(a: Instant, b: Instant) -> bool

_Undocumented._

### `equals`

> **equals**(a: Instant, b: Instant) -> bool

_Undocumented._

### `add_duration`

> **add_duration**(t: Instant, d: Duration) -> Instant

 Adds a duration in nanoseconds.

### `add_date`

> **add_date**(t: Instant, years: int, months: int, days: int) -> Instant

 Adds calendar years, months and days.

### `sub`

> **sub**(a: Instant, b: Instant) -> Duration

_Undocumented._

### `to_iso`

> **to_iso**() -> string

_Undocumented._

### `to_unix_sec`

> **to_unix_sec**() -> i64

_Undocumented._

### `plus_nanos`

> **plus_nanos**(d: i64) -> Instant

_Undocumented._

### `plus_days`

> **plus_days**(d: int) -> Instant

_Undocumented._

### `is_before_with`

> **is_before_with**(other: Instant) -> bool

_Undocumented._

### `is_after_with`

> **is_after_with**(other: Instant) -> bool

_Undocumented._

