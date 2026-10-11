#!/usr/bin/env python3
"""End-to-end tests for ``std.ward`` (Chunk 3 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the emitted C: the
contract under test is behaviour, and the compiler is free to change how it gets
there.

``ward`` is the assertion/invariant module.  Its ``assert_*`` and ``expect_*``
helpers abort the process through ``spark.panic`` when a condition fails, so the
panic cases are pinned by running a throw-away program and checking that it
returned 1 with the message somewhere on its output (the abort happens in the
child process, never in pytest).  The ``check_*`` helpers never panic: the nine
legacy ones return the 0.14.x ``oracle.ResultString`` and the seven
``check_*_native`` ones return a native ``result of string to string``.

The suite is deliberately self-contained.  Each test writes its own throw-away
program into a temporary directory and runs it with the binary cache disabled, so
no test can observe another test's state and a failure names exactly one program.

The compiler is invoked through the repository's own CLI (``pengu_project.py``):
a source checkout has no installed ``pengu`` binary, and the CLI is what CI runs.
``-q`` suppresses the build progress lines so the assertions can compare the
program's output byte for byte.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: Three levels up: tests/stdlib/test_ward.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script; returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_ward_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(cmd, capture_output=True, text=True,
                              input=stdin_text, timeout=timeout, cwd=str(REPO))


def ward_program(body: str) -> str:
    """Wraps ``body`` as the statements of a ``main`` that imports ``std.ward``.

    The body is dedented, so each test can indent it to match its own block, and
    the three std modules a ``ward`` program needs are imported for it.
    """
    statements = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    return (
        "import std.spark\n"
        "import std.ward\n"
        "import std.oracle\n"
        "\n"
        "weave main into int:\n"
        f"{statements}\n"
        "    return 0\n"
    )


def panics(body: str, needle: str) -> None:
    """Runs ``body`` and pins that it aborts (exit 1) mentioning ``needle``.

    The runtime may route the panic to stdout or stderr, so the message is
    searched for in the concatenation of both.
    """
    res = run_pengu(ward_program(body))
    combined = res.stdout + res.stderr
    assert res.returncode == 1, combined
    assert needle in combined, combined


# ---------------------------------------------------------------------------
# Metadata and happy paths
# ---------------------------------------------------------------------------


def test_ward_version_is_2_1_0():
    """The migrated module reports WARD_VERSION 2.1.0."""
    res = run_pengu(ward_program('''
        calling spark.println with ward.WARD_VERSION
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.1.0\n"


def test_assert_bool_helpers_accept_satisfied_conditions():
    """assert / assert_msg / assert_true / assert_false pass on true and false."""
    res = run_pengu(ward_program('''
        calling ward.assert with 2 > 1
        calling ward.assert_msg with true, "never shown"
        calling ward.assert_true with true
        calling ward.assert_false with false
        calling ward.assert_eq_bool with true, true
        calling ward.assert_ne_bool with true, false
        calling spark.println with "bool-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "bool-ok\n"


def test_assert_int_equality_and_order_helpers():
    """assert_eq_int / assert_ne_int and the int order helpers accept valid input."""
    res = run_pengu(ward_program('''
        calling ward.assert_eq_int with 2 + 2, 4
        calling ward.assert_ne_int with 3, 4
        calling ward.assert_gt_int with 5, 3
        calling ward.assert_ge_int with 4, 4
        calling ward.assert_lt_int with 3, 5
        calling ward.assert_le_int with 4, 4
        calling spark.println with "int-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "int-ok\n"


def test_assert_string_equality_and_shape_helpers():
    """assert_eq_string / assert_ne_string and empty/not-empty accept valid input."""
    res = run_pengu(ward_program('''
        calling ward.assert_eq_string with "ping", "ping"
        calling ward.assert_ne_string with "ping", "pong"
        calling ward.assert_string_empty with ""
        calling ward.assert_string_not_empty with "text"
        calling spark.println with "string-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "string-ok\n"


def test_assert_string_predicates_accept_matches_and_empty_affixes():
    """contains/starts_with/ends_with pass on matches and on empty needle/affix."""
    res = run_pengu(ward_program('''
        calling ward.assert_string_contains with "hello world", "world"
        calling ward.assert_string_contains with "", ""
        calling ward.assert_string_contains with "hello", ""
        calling ward.assert_string_starts_with with "https://example.org", "https://"
        calling ward.assert_string_starts_with with "abc", ""
        calling ward.assert_string_ends_with with "main.pengu", ".pengu"
        calling ward.assert_string_ends_with with "abc", ""
        calling spark.println with "predicate-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "predicate-ok\n"


def test_assert_float_helpers_honour_epsilon():
    """assert_eq_float / assert_ne_float / assert_almost_eq use the epsilon window."""
    res = run_pengu(ward_program('''
        calling ward.assert_eq_float with 1.0000001, 1.0, 0.001
        calling ward.assert_eq_float with 1.0000001, 1.0
        calling ward.assert_ne_float with 2.0, 1.0, 0.001
        calling ward.assert_almost_eq with 3.14159, 3.1416, 0.001
        calling spark.println with "float-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "float-ok\n"


def test_assert_float_order_helpers():
    """The float order helpers accept increasing and equal values."""
    res = run_pengu(ward_program('''
        calling ward.assert_gt_float with 2.5, 1.5
        calling ward.assert_ge_float with 1.5, 1.5
        calling ward.assert_lt_float with 1.5, 2.5
        calling ward.assert_le_float with 1.5, 1.5
        calling spark.println with "float-order-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "float-order-ok\n"


def test_assert_in_range_helpers_include_both_bounds():
    """assert_in_range_int / assert_in_range_float accept both inclusive bounds."""
    res = run_pengu(ward_program('''
        calling ward.assert_in_range_int with 1, 1, 12
        calling ward.assert_in_range_int with 12, 1, 12
        calling ward.assert_in_range_int with 5, 1, 12
        calling ward.assert_in_range_float with 0.0, 0.0, 1.0
        calling ward.assert_in_range_float with 1.0, 0.0, 1.0
        calling spark.println with "range-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "range-ok\n"


def test_assert_list_equality_helpers():
    """assert_eq_int_list / assert_eq_string_list accept identical lists."""
    res = run_pengu(ward_program('''
        let xs as list of int is [1, 2, 3]
        defer banish xs
        let ys as list of int is [1, 2, 3]
        defer banish ys
        calling ward.assert_eq_int_list with xs, ys
        let names as list of string is ["alpha", "beta"]
        defer banish names
        let same as list of string is ["alpha", "beta"]
        defer banish same
        calling ward.assert_eq_string_list with names, same
        calling spark.println with "list-eq-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "list-eq-ok\n"


def test_assert_list_shape_helpers():
    """assert_list_empty_int / not_empty / list_len_int accept the right shapes."""
    res = run_pengu(ward_program('''
        let empty as list of int is list of int
        defer banish empty
        calling ward.assert_list_empty_int with empty
        let xs as list of int is [7, 8]
        defer banish xs
        calling ward.assert_list_not_empty_int with xs
        calling ward.assert_list_len_int with xs, 2
        calling spark.println with "list-shape-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "list-shape-ok\n"


def test_assert_map_key_helpers():
    """assert_map_has_key / assert_map_not_has_key classify map keys."""
    res = run_pengu(ward_program('''
        var config as map of string to string is map of string to string
        defer banish config
        calling config.put with "host", "localhost"
        calling ward.assert_map_has_key with config, "host"
        calling ward.assert_map_not_has_key with config, "secret"
        calling spark.println with "map-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "map-ok\n"


def test_assert_maybe_and_result_helpers():
    """The generic maybe/result assertions accept the matching container shape."""
    res = run_pengu(ward_program('''
        let present as maybe int is some 7
        calling ward.assert_maybe_present with present
        let missing as maybe int is maybe none
        calling ward.assert_maybe_none with missing
        let good as result of int to string is calling ok_of with 1
        calling ward.assert_result_ok with good
        calling ward.assert_result_ok_int with good
        let bad as result of int to string is calling err_of with "boom"
        calling ward.assert_result_err with bad
        calling ward.assert_result_err_int with bad
        calling spark.println with "maybe-result-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "maybe-result-ok\n"


def test_legacy_assert_container_helpers():
    """The nine legacy assert_* container helpers accept matching containers."""
    res = run_pengu(ward_program('''
        let present_i as MaybeInt is calling oracle.maybe_some_int with 5
        calling ward.assert_present_int with present_i
        let none_i as MaybeInt is calling oracle.maybe_none_int
        calling ward.assert_none_int with none_i
        let ok_i as ResultInt is calling oracle.result_ok_int with 3
        calling ward.assert_ok_int with ok_i
        let err_i as ResultInt is calling oracle.result_err_int with "boom"
        calling ward.assert_err_int with err_i
        let present_s as MaybeString is calling oracle.maybe_some_string with "hi"
        calling ward.assert_present_string with present_s
        let none_s as MaybeString is calling oracle.maybe_none_string
        calling ward.assert_none_string with none_s
        let ok_s as ResultString is calling oracle.result_ok_string with "hi"
        calling ward.assert_ok_string with ok_s
        let err_s as ResultString is calling oracle.result_err_string with "boom"
        calling ward.assert_err_string with err_s
        calling spark.println with "legacy-assert-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "legacy-assert-ok\n"


def test_expect_family_accepts_satisfied_conditions():
    """Every expect_* helper passes through on a satisfied condition."""
    res = run_pengu(ward_program('''
        calling ward.expect with true, "never shown"
        calling ward.expect_eq_int with 4, 4, "never shown"
        calling ward.expect_eq_string with "same", "same", "never shown"
        calling ward.expect_eq_float with 1.0, 1.0, "never shown"
        calling ward.expect_ne_int with 1, 2, "never shown"
        calling ward.expect_ne_string with "left", "right", "never shown"
        calling ward.expect_ne_bool with true, false, "never shown"
        calling ward.expect_gt_int with 2, 1, "never shown"
        calling ward.expect_ge_int with 2, 2, "never shown"
        calling ward.expect_lt_int with 1, 2, "never shown"
        calling ward.expect_le_int with 2, 2, "never shown"
        let present_i as MaybeInt is calling oracle.maybe_some_int with 1
        calling ward.expect_present_int with present_i, "never shown"
        let present_s as MaybeString is calling oracle.maybe_some_string with "x"
        calling ward.expect_present_string with present_s, "never shown"
        let ok_i as ResultInt is calling oracle.result_ok_int with 1
        calling ward.expect_ok_int with ok_i, "never shown"
        let ok_s as ResultString is calling oracle.result_ok_string with "x"
        calling ward.expect_ok_string with ok_s, "never shown"
        calling spark.println with "expect-ok"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "expect-ok\n"


# ---------------------------------------------------------------------------
# Native result checks: result of string to string
# ---------------------------------------------------------------------------


def test_check_native_returns_ok_and_err():
    """check_native yields ok("ok") or err(msg) as a native result."""
    res = run_pengu(ward_program('''
        let good as result of string to string is calling ward.check_native with true, "boom"
        let bad as result of string to string is calling ward.check_native with false, "boom"
        let good_ok as string is calling spark.str_bool with good.is_ok
        let bad_is_err as bool is calling oracle.is_err_result with bad
        let bad_err as string is calling spark.str_bool with bad_is_err
        let payload as string is calling oracle.unwrap_err_result with bad
        calling spark.println with "{good_ok}|{bad_err}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|boom\n"


def test_check_eq_int_native_classifies_equality():
    """check_eq_int_native is ok on a match and err(msg) on a mismatch."""
    res = run_pengu(ward_program('''
        let same as result of string to string is calling ward.check_eq_int_native with 2 + 2, 4, "bad sum"
        let diff as result of string to string is calling ward.check_eq_int_native with 3, 4, "bad sum"
        let same_ok as string is calling spark.str_bool with same.is_ok
        let payload as string is calling oracle.unwrap_err_result with diff
        calling spark.println with "{same_ok}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|bad sum\n"


def test_check_eq_string_native_classifies_equality():
    """check_eq_string_native is ok on a match and err(msg) on a mismatch."""
    res = run_pengu(ward_program('''
        let same as result of string to string is calling ward.check_eq_string_native with "a", "a", "bad string"
        let diff as result of string to string is calling ward.check_eq_string_native with "a", "b", "bad string"
        let same_ok as string is calling spark.str_bool with same.is_ok
        let payload as string is calling oracle.unwrap_err_result with diff
        calling spark.println with "{same_ok}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|bad string\n"


def test_check_eq_bool_native_classifies_equality():
    """check_eq_bool_native is ok on a match and err(msg) on a mismatch."""
    res = run_pengu(ward_program('''
        let same as result of string to string is calling ward.check_eq_bool_native with true, true, "bad bool"
        let diff as result of string to string is calling ward.check_eq_bool_native with true, false, "bad bool"
        let same_ok as string is calling spark.str_bool with same.is_ok
        let payload as string is calling oracle.unwrap_err_result with diff
        calling spark.println with "{same_ok}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|bad bool\n"


def test_check_eq_float_native_honours_epsilon():
    """check_eq_float_native is ok within epsilon, explicit or default, else err."""
    res = run_pengu(ward_program('''
        let near as result of string to string is calling ward.check_eq_float_native with 1.0000001, 1.0, "far apart"
        let near2 as result of string to string is calling ward.check_eq_float_native with 1.05, 1.0, "far apart", 0.1
        let far as result of string to string is calling ward.check_eq_float_native with 2.0, 1.0, "far apart", 0.001
        let near_ok as string is calling spark.str_bool with near.is_ok
        let near2_ok as string is calling spark.str_bool with near2.is_ok
        let payload as string is calling oracle.unwrap_err_result with far
        calling spark.println with "{near_ok}|{near2_ok}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|far apart\n"


def test_check_present_native_classifies_a_maybe():
    """check_present_native is ok for some and err(msg) for none."""
    res = run_pengu(ward_program('''
        let present as maybe int is some 7
        let found as result of string to string is calling ward.check_present_native with present, "missing"
        let missing as maybe int is maybe none
        let lost as result of string to string is calling ward.check_present_native with missing, "missing"
        let found_ok as string is calling spark.str_bool with found.is_ok
        let lost_is_err as bool is calling oracle.is_err_result with lost
        let lost_err as string is calling spark.str_bool with lost_is_err
        let payload as string is calling oracle.unwrap_err_result with lost
        calling spark.println with "{found_ok}|{lost_err}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|missing\n"


def test_check_ok_native_classifies_a_result():
    """check_ok_native is ok for an ok result and err(msg) for an err result."""
    res = run_pengu(ward_program('''
        let good as result of int to string is calling ok_of with 1
        let accepted as result of string to string is calling ward.check_ok_native with good, "rejected"
        let bad as result of int to string is calling err_of with "nope"
        let rejected as result of string to string is calling ward.check_ok_native with bad, "rejected"
        let accepted_ok as string is calling spark.str_bool with accepted.is_ok
        let rejected_is_err as bool is calling oracle.is_err_result with rejected
        let rejected_err as string is calling spark.str_bool with rejected_is_err
        let payload as string is calling oracle.unwrap_err_result with rejected
        calling spark.println with "{accepted_ok}|{rejected_err}|{payload}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|rejected\n"


# ---------------------------------------------------------------------------
# Legacy ResultString checks: never panic
# ---------------------------------------------------------------------------


def test_legacy_check_family_returns_result_string_without_panicking():
    """The nine legacy check_* helpers classify failures as err(msg), never panic."""
    res = run_pengu(ward_program('''
        let okc as ResultString is calling ward.check with true, "nope"
        let badc as ResultString is calling ward.check with false, "nope"
        calling spark.println with "{calling spark.str_bool with okc.is_ok}"
        calling spark.println with "{badc.error_msg}"
        let eqi as ResultString is calling ward.check_eq_int with 1, 2, "bad sum"
        calling spark.println with "{eqi.error_msg}"
        let eqs as ResultString is calling ward.check_eq_string with "a", "b", "bad string"
        calling spark.println with "{eqs.error_msg}"
        let eqb as ResultString is calling ward.check_eq_bool with true, false, "bad bool"
        calling spark.println with "{eqb.error_msg}"
        let eqf as ResultString is calling ward.check_eq_float with 2.0, 1.0, "bad float", 0.001
        calling spark.println with "{eqf.error_msg}"
        let eqf2 as ResultString is calling ward.check_eq_float with 1.0, 1.0, "bad float"
        calling spark.println with "{calling spark.str_bool with eqf2.is_ok}"
        let present_i as MaybeInt is calling oracle.maybe_some_int with 1
        let none_i as MaybeInt is calling oracle.maybe_none_int
        let cpi as ResultString is calling ward.check_present_int with present_i, "missing int"
        calling spark.println with "{calling spark.str_bool with cpi.is_ok}"
        let npi as ResultString is calling ward.check_present_int with none_i, "missing int"
        calling spark.println with "{npi.error_msg}"
        let present_s as MaybeString is calling oracle.maybe_some_string with "x"
        let none_s as MaybeString is calling oracle.maybe_none_string
        let cps as ResultString is calling ward.check_present_string with present_s, "missing string"
        calling spark.println with "{calling spark.str_bool with cps.is_ok}"
        let nps as ResultString is calling ward.check_present_string with none_s, "missing string"
        calling spark.println with "{nps.error_msg}"
        let ok_i as ResultInt is calling oracle.result_ok_int with 1
        let err_i as ResultInt is calling oracle.result_err_int with "no"
        let coi as ResultString is calling ward.check_ok_int with ok_i, "not ok int"
        calling spark.println with "{calling spark.str_bool with coi.is_ok}"
        let noi as ResultString is calling ward.check_ok_int with err_i, "not ok int"
        calling spark.println with "{noi.error_msg}"
        let ok_s as ResultString is calling oracle.result_ok_string with "y"
        let err_s as ResultString is calling oracle.result_err_string with "no"
        let cos as ResultString is calling ward.check_ok_string with ok_s, "not ok string"
        calling spark.println with "{calling spark.str_bool with cos.is_ok}"
        let nos as ResultString is calling ward.check_ok_string with err_s, "not ok string"
        calling spark.println with "{nos.error_msg}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "true\n"
        "nope\n"
        "bad sum\n"
        "bad string\n"
        "bad bool\n"
        "bad float\n"
        "true\n"
        "true\n"
        "missing int\n"
        "true\n"
        "missing string\n"
        "true\n"
        "not ok int\n"
        "true\n"
        "not ok string\n"
    )


# ---------------------------------------------------------------------------
# Panic paths: a failing assertion aborts the child process
# ---------------------------------------------------------------------------


def test_assert_failure_aborts_the_process():
    """A false assert aborts with exit code 1 and the panic marker."""
    panics("calling ward.assert with false", "[PANIC] assertion failed")


def test_assert_msg_reports_the_caller_message():
    """assert_msg panics with exactly the caller-supplied message."""
    panics('calling ward.assert_msg with false, "guard failed: x"', "guard failed: x")


def test_assert_true_panic_names_the_expectation():
    """assert_true reports what it expected and what it saw."""
    panics("calling ward.assert_true with false",
           "assertion failed: expected true, got false")


def test_assert_eq_int_panic_reports_both_values():
    """assert_eq_int reports the expected and the actual integer."""
    panics("calling ward.assert_eq_int with 1, 2", "expected 2, got 1")


def test_assert_eq_string_panic_reports_quoted_values():
    """assert_eq_string reports both strings, quoted."""
    panics('calling ward.assert_eq_string with "left", "right"',
           'expected "right", got "left"')


def test_assert_in_range_int_panic_reports_the_range():
    """assert_in_range_int reports the offending value and the bounds."""
    panics("calling ward.assert_in_range_int with 99, 1, 12",
           "value 99 not in range [1, 12]")


def test_assert_string_contains_panic_reports_the_needle():
    """A missing substring aborts the program."""
    panics('calling ward.assert_string_contains with "hello", "needle"',
           'to contain "needle"')


def test_assert_string_starts_with_long_prefix_panics():
    """A prefix longer than the string cannot match, so it aborts."""
    panics('calling ward.assert_string_starts_with with "ab", "abc"',
           'to start with "abc"')


def test_assert_string_ends_with_long_suffix_panics():
    """A suffix longer than the string cannot match, so it aborts."""
    panics('calling ward.assert_string_ends_with with "ab", "abc"',
           'to end with "abc"')


def test_assert_string_contains_long_needle_panics():
    """A needle longer than the haystack cannot match, so it aborts."""
    panics('calling ward.assert_string_contains with "ab", "abc"',
           'to contain "abc"')


def test_assert_maybe_present_panic_when_none():
    """assert_maybe_present aborts when the optional is none."""
    panics('''
        let missing as maybe int is maybe none
        calling ward.assert_maybe_present with missing
    ''', "expected maybe to be present, got none")


def test_assert_maybe_none_panic_when_present():
    """assert_maybe_none aborts when the optional holds a value."""
    panics('''
        let present as maybe int is some 1
        calling ward.assert_maybe_none with present
    ''', "expected maybe to be none, got present")


def test_expect_panic_uses_the_caller_message():
    """A failed expect aborts with the caller-supplied message."""
    panics('calling ward.expect with false, "expectation failed: y"',
           "expectation failed: y")


def test_fail_aborts_with_the_given_message():
    """fail always aborts, carrying its message."""
    panics('calling ward.fail with "fatal: boom"', "fatal: boom")


def test_unreachable_aborts_with_its_default_message():
    """unreachable always aborts with its default message."""
    panics("calling ward.unreachable", "internal error: unreachable code")


def test_panic_aborts_with_the_panic_marker():
    """panic aborts and the runtime tags the message with `[PANIC]`."""
    res = run_pengu(ward_program('calling ward.panic with "kaboom"'))
    combined = res.stdout + res.stderr
    assert res.returncode == 1, combined
    assert "[PANIC] kaboom" in combined, combined
