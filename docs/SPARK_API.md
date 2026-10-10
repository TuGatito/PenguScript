# `std.spark` — frozen public API contract

> **Status: frozen.** This is the API that Wave 1 (`scrolls`, `oracle`, `ward`,
> `trial`, …) is built against. A change to a signature here is a breaking change
> and must bump `SPARK_VERSION`.
>
> Module revision: **`0.8.0-spark`** (`STD_VERSION` remains `"0.14.1"`).
> Source: [`std/spark.pengu`](../std/spark.pengu).

`spark` is the dependency-free core of the standard library: process I/O,
scalar conversions, parsing, integer ranges, integer math, assertions and
process control. It imports nothing, so any other `std.*` module may import it
without creating a cycle.

## Ownership model (summary)

| Producer | Ownership | Release |
|---|---|---|
| `input`, `read_line` | owned `string` | `banish` / `defer banish` |
| `str_int`, `str_float`, `str_bool` | owned `string` | `banish` / `defer banish` |
| `str`, `bool_to_string`, `spark_version` | borrowed view/literal | never `banish` |
| `parse_int`, `parse_float`, `parse_bool`, `parse_int_hex/bin/oct`, `read_char`, `read_int`, `read_float`, `read_bool` | `maybe T` boxing a heap cell | `banish` on the whole `maybe` |
| `range`, `range_to`, `range_inclusive`, `range_down` | owned `list of int` | `banish` / `defer banish` |
| every `print*` / `eprint*` / `assert*` / `flush*` / `panic` / `exit` argument | borrowed | never `banish`; the callee does not take possession |

`spark` never frees an argument it receives, and never returns a pointer into a
caller buffer.

## Constants

| Symbol | Type | Value | Notes |
|---|---|---|---|
| `SPARK_VERSION` | `string` | `"0.8.0-spark"` | Revision of the **spark API**, not of the toolchain. Bumps only when a signature changes. |
| `STD_VERSION` | `string` | `"0.14.1"` | Legacy stdlib tag, frozen. Superseded by per-module `<MOD>_VERSION`. |

## Conversions

| Symbol | Signature | Semantics |
|---|---|---|
| `len_string` | `(string) -> int` | Byte length of the string. `len_string("") == 0`. |
| `bool_to_string` | `(bool) -> string` | `true` → `"true"`, `false` → `"false"`. Borrowed literal. |
| `str` | `(string) -> string` | Identity. Borrowed. |
| `str_int` | `(int) -> string` | Decimal, `%lld`. New owned string. |
| `str_float` | `(float) -> string` | `%g`, identical to `"{x}"`. New owned string. |
| `str_bool` | `(bool) -> string` | `"true"` / `"false"`. New owned string. |

## Version

| Symbol | Signature | Semantics |
|---|---|---|
| `spark_version` | `() -> string` | Returns `SPARK_VERSION`. Borrowed. |

## Output — stdout

| Symbol | Signature | Semantics |
|---|---|---|
| `print` | `(string) -> void` | Writes `s`, no trailing newline. |
| `println` | `(string) -> void` | Writes `s` + `\n`. |
| `print_line` | `(string) -> void` | Compatibility alias of `println`. |
| `print_int` | `(int) -> void` | Decimal, no newline. |
| `println_int` | `(int) -> void` | Decimal + `\n`. |
| `print_float` | `(float) -> void` | `%g`, no newline. |
| `println_float` | `(float) -> void` | `%g` + `\n`. |
| `print_bool` | `(bool) -> void` | `true`/`false`, no newline. |
| `println_bool` | `(bool) -> void` | `true`/`false` + `\n`. |

## Output — stderr

| Symbol | Signature | Semantics |
|---|---|---|
| `eprint` | `(string) -> void` | Writes `s` to **fd 2**, no trailing newline. |
| `eprintln` | `(string) -> void` | Writes `s` to **fd 2** + `\n`. |
| `eprint_line` | `(string) -> void` | Compatibility alias of `eprintln`; also fd 2. |

> **Bug fixed in 0.8.0.** `eprintln` and `eprint_line` used to route through
> `println`, i.e. to stdout, so `program 2> file` captured nothing. They are real
> fd-2 writes now.

## Flushing

| Symbol | Signature | Semantics |
|---|---|---|
| `flush` | `() -> void` | `fflush(stdout)`. |
| `eflush` | `() -> void` | `fflush(stderr)`. |

## Assertions

| Symbol | Signature | Semantics |
|---|---|---|
| `assert` | `(bool) -> void` | Panics with `"Assertion failed"` (exit 1) when false. |
| `assert_msg` | `(bool, string) -> void` | Panics with the caller's message (exit 1) when false. |
| `assert_debug` | `(bool) -> void` | Same as `assert`, but compiled away under `--profile release`. |

## Errors and process control

| Symbol | Signature | Semantics |
|---|---|---|
| `panic` | `(string) -> void` | Prints `[PANIC] <msg>` to stderr and exits 1. Never returns. |
| `exit` | `(int) -> void` | Flushes both streams, then `exit(code)`. Never returns. |
| `exit_success` | `() -> void` | Flushes, then exits 0. Never returns. |
| `exit_failure` | `() -> void` | Flushes, then exits 1. Never returns. |

## Input — stdin

| Symbol | Signature | Semantics |
|---|---|---|
| `input` | `(string) -> string` | Writes the prompt (no newline, flushed), reads one line, strips the trailing `\r`/`\n`. Owned result; empty on EOF. Line limit 4095 bytes. |
| `read_line` | `() -> string` | `input` with no prompt. Owned. |
| `read_char` | `() -> maybe int` | One byte (0–255), or `none` at EOF. |
| `read_int` | `(string) -> maybe int` | Prompt, read a line, `parse_int` it. Releases the temporary line. |
| `read_float` | `(string) -> maybe float` | Prompt, read a line, `parse_float` it. Releases the temporary line. |
| `read_bool` | `(string) -> maybe bool` | Prompt, read a line, `parse_bool` it. Releases the temporary line. |

## Parsing

| Symbol | Signature | Semantics |
|---|---|---|
| `parse_int` | `(string) -> maybe int` | Base 10. Leading/trailing whitespace allowed. `none` on empty, trailing garbage, or out of `[INT32_MIN, INT32_MAX]`. |
| `parse_float` | `(string) -> maybe float` | C float grammar. Whitespace allowed. `none` on empty, trailing garbage, or `ERANGE`. |
| `parse_bool` | `(string) -> maybe bool` | Exact, case-sensitive: `true`/`false`/`yes`/`no`/`1`/`0`. `none` otherwise. |
| `parse_int_hex` | `(string) -> maybe int` | Base 16, optional `0x`/`0X`. No whitespace. |
| `parse_int_bin` | `(string) -> maybe int` | Base 2. No whitespace. |
| `parse_int_oct` | `(string) -> maybe int` | Base 8. No whitespace. |

## Ranges

| Symbol | Signature | Semantics |
|---|---|---|
| `range` | `(start: int, end_val: int, step: int is 1) -> list of int` | `[start, end_val)` stepping by `step`. Empty when `start >= end_val`. **`step` must be > 0** (a non-positive step with `start < end_val` does not terminate). |
| `range_to` | `(end_val: int) -> list of int` | `[0, end_val)`. Empty when `end_val <= 0`. |
| `range_inclusive` | `(start: int, end_val: int) -> list of int` | `[start, end_val]`. Empty when `start > end_val`. |
| `range_down` | `(start: int, end_val: int, step: int is 1) -> list of int` | `(end_val, start]` stepping down by `step`. Empty when `start <= end_val`. **`step` must be > 0**. |

Every range helper returns a **new owned list**; release it with `banish`.

## Integer math

| Symbol | Signature | Semantics |
|---|---|---|
| `min_int` | `(int, int) -> int` | Smaller value. |
| `max_int` | `(int, int) -> int` | Greater value. |
| `abs_int` | `(int) -> int` | Absolute value. `abs_int(INT32_MIN)` overflows by definition. |
| `clamp_int` | `(v, lo, hi) -> int` | Clamps into `[lo, hi]`; assumes `lo <= hi`. |
| `sign_int` | `(int) -> int` | `-1`, `0` or `1`. |
| `gcd_int` | `(int, int) -> int` | Non-negative GCD, Euclidean algorithm. `gcd_int(0, 0) == 0`. |
| `lcm_int` | `(int, int) -> int` | Non-negative LCM = `abs(a / gcd(a, b) * b)`. `lcm_int(0, 0) == 0`. |
| `pow_int` | `(base, exp) -> int` | `base ** exp` by binary exponentiation, `O(log exp)`. **`exp` must be >= 0.** Overflow past `int32` wraps in release and traps in debug. |

## C bridges (`antiquus`, internal)

These are the literal-C bodies that replaced the `static inline` helpers in
`pengu_runtime.h`. They are module-level declarations, not part of the frozen
public surface: they exist so DCE can drop the ones a program never calls, and
they are named `pengu_*` by the brief that introduced them.

| Bridge | Signature | Origin |
|---|---|---|
| `pengu_print` | `(string) -> void` | moved from `pengu_runtime.h` |
| `pengu_println` | `(string) -> void` | moved |
| `pengu_eprint` | `(string) -> void` | new |
| `pengu_eprintln` | `(string) -> void` | new |
| `pengu_flush_stdout` | `() -> void` | new |
| `pengu_flush_stderr` | `() -> void` | new |
| `pengu_input` | `(string) -> string` | moved |
| `pengu_read_char` | `() -> maybe int` | new |
| `pengu_parse_int` | `(string) -> maybe int` | moved |
| `pengu_parse_float` | `(string) -> maybe float` | moved |
| `pengu_parse_int_radix` | `(string, int) -> maybe int` | new |
| `pengu_panic` | `(string) -> void` | moved |
| `pengu_exit` | `(int) -> void` | new |

## Compatibility notes

* Every pre-0.8 public symbol keeps its name and signature; `print_line` and
  `eprint_line` are retained as aliases.
* The only observable behaviour change is the stderr fix: `eprintln` /
  `eprint_line` no longer write to stdout.
* The `pengu_parse_int` / `pengu_parse_float` C helpers are **no longer defined
  in `pengu_runtime.h`**. C code that included only the header and called them
  must go through the `spark` weaves instead; the C runtime test suite was
  updated accordingly.
