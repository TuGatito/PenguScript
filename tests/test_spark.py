#!/usr/bin/env python3
"""End-to-end tests for ``std.spark`` (Chunk 1 of the Pengunic 2.0 migration).

Every test here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

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

REPO = Path(__file__).resolve().parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process.

    Args:
        source: the whole PenguScript program.  It is dedented, so tests can
            indent it to match their own block.
        args: forwarded to the program after ``--``.
        stdin_text: what the program reads from stdin.
        timeout: seconds allowed for compile + run.

    Returns:
        The ``CompletedProcess`` of the CLI invocation.  With ``-q`` the CLI's
        own stdout/stderr are empty, so ``stdout``/``stderr`` are the program's.
    """
    with tempfile.TemporaryDirectory(prefix="pengu_spark_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


def _print_int(expr: str) -> str:
    """A program that prints int expression ``expr`` plus a newline."""
    return f"""
        import std.spark

        weave main into int:
            calling spark.println with calling spark.str_int with ({expr})
            return 0
    """


# ---------------------------------------------------------------------------
# stdout
# ---------------------------------------------------------------------------

def test_print_writes_to_stdout():
    """`spark.print` writes to stdout and adds no newline."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.print with "x"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x"
    assert res.stderr == ""


def test_println_appends_newline():
    """`spark.println` writes to stdout followed by exactly one newline."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.println with "x"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x\n"
    assert res.stderr == ""


def test_print_line_alias_matches_println():
    """`spark.print_line` is a compatibility alias of `spark.println`."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.print_line with "x"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x\n"


def test_println_int_formats_decimal():
    """`spark.println_int` formats an int with `%lld`."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.println_int with -7
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-7\n"


# ---------------------------------------------------------------------------
# stderr — the fd-2 bug fix
# ---------------------------------------------------------------------------

def test_eprint_writes_to_stderr():
    """`spark.eprint` writes to file descriptor 2, never to stdout."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.eprint with "y"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ""
    assert res.stderr == "y"


def test_eprintln_appends_newline():
    """`spark.eprintln` writes to stderr followed by exactly one newline."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.eprintln with "y"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ""
    assert res.stderr == "y\n"


def test_eprint_line_alias_uses_stderr():
    """`spark.eprint_line` is a compatibility alias of `spark.eprintln`.

    This is the regression pin for the pre-2.0 bug: the "e" helpers routed
    through stdout, so `2> file` captured nothing.
    """
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.eprint_line with "y"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ""
    assert res.stderr == "y\n"


def test_stdout_and_stderr_do_not_mix():
    """Redirecting one stream must not capture the other."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.println with "out"
            calling spark.eprintln with "err"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "out\n"
    assert res.stderr == "err\n"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def test_parse_int_valid():
    """`spark.parse_int` accepts a full base-10 integer."""
    res = run_pengu(_print_int('(calling spark.parse_int with "42") or else -1'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "42\n"


def test_parse_int_invalid():
    """`spark.parse_int` returns `none` for non-numeric input."""
    res = run_pengu(_print_int('(calling spark.parse_int with "abc") or else -1'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n"


def test_parse_int_rejects_overflow():
    """`spark.parse_int` returns `none` past the int32 range."""
    res = run_pengu(_print_int('(calling spark.parse_int with "999999999999") or else -1'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n"


def test_parse_bool_accepts_yes_no():
    """`spark.parse_bool` accepts `yes`/`no` as well as `true`/`false`/`1`/`0`."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            var yes as maybe bool is calling spark.parse_bool with "yes"
            var no as maybe bool is calling spark.parse_bool with "no"
            var other as maybe bool is calling spark.parse_bool with "maybe"
            calling spark.println with calling spark.str_bool with (yes or else false)
            calling spark.println with calling spark.str_bool with (no or else true)
            calling spark.println with calling spark.str_bool with (other or else false)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\nfalse\n"


def test_parse_int_hex():
    """`spark.parse_int_hex` parses base 16 and rejects non-digits."""
    res = run_pengu(_print_int('(calling spark.parse_int_hex with "FF") or else 0'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "255\n"


def test_parse_int_bin():
    """`spark.parse_int_bin` parses base 2."""
    res = run_pengu(_print_int('(calling spark.parse_int_bin with "1010") or else 0'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\n"


def test_parse_int_oct():
    """`spark.parse_int_oct` parses base 8."""
    res = run_pengu(_print_int('(calling spark.parse_int_oct with "17") or else 0'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "15\n"


def test_read_char_returns_none_on_eof():
    """`spark.read_char` returns `none` at end of input."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            var c as maybe int is calling spark.read_char
            calling spark.println with calling spark.str_int with (c or else -1)
            return 0
    ''', stdin_text="")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n"


# ---------------------------------------------------------------------------
# Ranges and integer math
# ---------------------------------------------------------------------------

def test_range_to_inclusive():
    """`spark.range_to` yields 0 up to (not including) its bound, in order."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            let xs as list of int is calling spark.range_to with 5
            for v in xs:
                calling spark.println with calling spark.str_int with v
            banish xs
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n1\n2\n3\n4\n"


def test_range_inclusive_includes_both_ends():
    """`spark.range_inclusive` yields `start` through `end_val`."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            let xs as list of int is calling spark.range_inclusive with 1, 3
            for v in xs:
                calling spark.println with calling spark.str_int with v
            banish xs
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n2\n3\n"


def test_range_down_countdown():
    """`spark.range_down` counts down to, but not including, its bound."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            let xs as list of int is calling spark.range_down with 5, 0
            for v in xs:
                calling spark.println with calling spark.str_int with v
            banish xs
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n4\n3\n2\n1\n"


def test_gcd_euclid():
    """`spark.gcd_int` uses the Euclidean algorithm."""
    res = run_pengu(_print_int('calling spark.gcd_int with 48, 18'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "6\n"


def test_lcm_int():
    """`spark.lcm_int` is `|a / gcd(a, b) * b|`."""
    res = run_pengu(_print_int('calling spark.lcm_int with 4, 6'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "12\n"


def test_pow_int_binary():
    """`spark.pow_int` implements binary exponentiation."""
    res = run_pengu(_print_int('calling spark.pow_int with 2, 10'))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1024\n"


def test_sign_and_clamp():
    """`spark.sign_int` and `spark.clamp_int` respect their bounds."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.println_int with calling spark.sign_int with -9
            calling spark.println_int with calling spark.clamp_int with 9, 0, 5
            calling spark.println_int with calling spark.clamp_int with -1, 0, 5
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n5\n0\n"


# ---------------------------------------------------------------------------
# Assertions, panics and process control
# ---------------------------------------------------------------------------

def test_assert_failure_panics():
    """A failed `spark.assert` prints `Assertion failed` to stderr and exits 1."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.assert with false
            return 0
    ''')
    assert res.returncode == 1
    assert "Assertion failed" in res.stderr
    assert res.stdout == ""


def test_assert_msg_reports_the_message():
    """`spark.assert_msg` panics with the caller's message."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.assert_msg with false, "boom"
            return 0
    ''')
    assert res.returncode == 1
    assert "boom" in res.stderr


def test_assert_success_continues():
    """A passing assertion does not terminate the program."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.assert with true
            calling spark.println with "ok"
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "ok\n"


def test_exit_code():
    """`spark.exit` terminates with the given status."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.exit with 42
            return 0
    ''')
    assert res.returncode == 42


def test_exit_failure_uses_status_one():
    """`spark.exit_failure` terminates with status 1."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.exit_failure
            return 0
    ''')
    assert res.returncode == 1


def test_flush_before_exit():
    """`spark.exit_success` flushes buffered stdout written without a newline."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.print with "buffered"
            calling spark.exit_success
            return 0
    ''')
    assert res.returncode == 0
    assert res.stdout == "buffered"


def test_explicit_flush_keeps_stdout_order():
    """`spark.flush` and `spark.eflush` flush without changing the streams."""
    res = run_pengu('''
        import std.spark

        weave main into int:
            calling spark.print with "a"
            calling spark.flush
            calling spark.eprint with "b"
            calling spark.eflush
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a"
    assert res.stderr == "b"
