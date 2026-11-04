# std.trial

> Source: `std/trial.pengu`

---

### `TRIAL_VERSION`

> **TRIAL_VERSION** : string

 std/trial.pengu - The Trial (Test Runner & Framework)
 Provides test suites, individual tests, and test reporting.
 Re-exports the common std.ward assertion helpers so a test program needs a
 single import (std.trial) for both the runner and the assertions.

 Typical usage:
   import std.trial
   weave my_test into void:
       calling trial.assert_eq_int with 1 + 1, 2
   var s as TestSuite is calling trial.new_suite with "Math"
   calling trial.test with sigil of s, "1 + 1 == 2", my_test
   calling trial.test_case with sigil of s, "direct check", true, ""
   var ok as bool is calling trial.summary with sigil of s

 Memory model:
   TestSuite is a plain rune value; the runner functions take it by
   reference (`ref to TestSuite`, so pass `sigil of` your variable) in order
   to mutate the counters in place. Everything else is passed/returned by
   value with normal PenguScript lifetimes - no returned value is
   caller-owned and there is nothing extra to banish.

### `assert`

> **assert**(cond: bool) -> void

 Asserts that `cond` is true; panics with "assertion failed" otherwise
 (re-export of ward.assert). Used inside test weaves to mark failures.

### `assert_msg`

> **assert_msg**(cond: bool, msg: string) -> void

 Asserts that `cond` is true; panics with the custom `msg` otherwise
 (re-export of ward.assert_msg).

### `assert_eq_int`

> **assert_eq_int**(a: int, b: int) -> void

 Asserts that integer `a` equals integer `b`; panics otherwise.

### `assert_eq_string`

> **assert_eq_string**(a: string, b: string) -> void

 Asserts that string `a` equals string `b`; panics otherwise.

### `assert_ne_int`

> **assert_ne_int**(a: int, b: int) -> void

 Asserts that integer `a` differs from integer `b`; panics otherwise.

### `assert_ne_string`

> **assert_ne_string**(a: string, b: string) -> void

 Asserts that string `a` differs from string `b`; panics otherwise.

### `assert_true`

> **assert_true**(cond: bool) -> void

 Asserts that `cond` is true; panics otherwise (re-export of ward.assert_true).

### `assert_false`

> **assert_false**(cond: bool) -> void

 Asserts that `cond` is false; panics otherwise (re-export of ward.assert_false).

### `assert_present_int`

> **assert_present_int**(m: MaybeInt) -> void

 Asserts that MaybeInt `m` holds a value (is present); panics when it is none.

### `assert_ok_int`

> **assert_ok_int**(r: ResultInt) -> void

 Asserts that ResultInt `r` is ok; panics when it holds an error.

### `TestSuite`

> rune TestSuite

```pengu
    name as string
    total as int
    passed as int
    failed as int
```

 A mutable test-suite accumulator: a display `name` plus running `total`,
 `passed` and `failed` counters. Build it with new_suite and hand it by
 reference (`ref to TestSuite`) to test, test_case and summary.

### `new_suite`

> **new_suite**(name: string) -> TestSuite

 Creates a new empty TestSuite named `name` and prints a
 "=== Suite: <name> ===" banner to stdout. Returns the fresh suite value.

### `test_case`

> **test_case**(s: ref to TestSuite, name: string, passed: bool, err_msg: string) -> void

 Records one already-evaluated result on suite `s`: increments `total` and,
 according to `passed`, increments `passed` or `failed`, printing a
 "  [PASS] <name>" or "  [FAIL] <name> - <err_msg>" line. `err_msg` is empty
 by default and only shown on failure.

### `test`

> **test**(s: ref to TestSuite, name: string, fn: weave with  into void) -> void

 Runs the test weave `fn` on suite `s`: increments `total`, calls `fn`, and
 records the test as passed (printing "  [PASS] <name>") when `fn` returns
 normally. Note there is no try/catch: a failing test must make `fn` panic
 (for example with the trial.assert* helpers), which aborts the program.

### `summary`

> **summary**(s: ref to TestSuite) -> bool

 Prints the full report for suite `s` (name, totals, pass/fail bars) and
 returns true when no test failed (failed == 0), false otherwise.

