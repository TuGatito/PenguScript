#!/usr/bin/env python3
"""End-to-end tests for ``std.oracle`` (Chunk 2 of the Pengunic 2.0 migration).

Every test here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout and exit code.  Nothing inspects the generated C: the
contract under test is behaviour, and the compiler is free to change how it gets
there.

The suite is deliberately self-contained.  Each test writes its own throw-away
program into a temporary directory and runs it with the binary cache disabled, so
no test can observe another test's state and a failure names exactly one program.

The compiler is invoked through the repository's own CLI (``pengu_project.py``):
a source checkout has no installed ``pengu`` binary, and the CLI is what CI runs.
``-q`` suppresses the build progress lines so the assertions can compare the
program's output byte for byte.

A note on assertions: ``maybe T`` and ``result of T to E`` are opaque containers
that cannot be compared with ``==``.  The programs below therefore unwrap with
``or else`` / ``unwrap_or`` / ``describe`` and compare the payloads, which is the
observable behaviour the public API promises.
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
    with tempfile.TemporaryDirectory(prefix="pengu_oracle_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


def _prog(body: str) -> str:
    """A program whose ``main`` runs ``body``, with the shared oracle callbacks.

    Args:
        body: the indented statements of ``main``.  The helper adds the two
            imports, the callback weaves the transformations need, and the
            trailing ``return 0``.
    """
    callbacks = (
        'import std.oracle\n'
        'import std.spark\n'
        '\n'
        '## Doubles an int.\n'
        'weave double_it with x as int into int:\n'
        '    return x * 2\n'
        '\n'
        '## Halves an even int, or `none` for an odd one.\n'
        'weave half_of with x as int into maybe int:\n'
        '    if (x % 2) == 0:\n'
        '        return some (x / 2)\n'
        '    return maybe none\n'
        '\n'
        '## The fixed length of an error string.\n'
        'weave err_len with e as string into int:\n'
        '    return 5\n'
        '\n'
        '## Advances a successful result by one.\n'
        'weave next_ok with x as int into result of int to string:\n'
        '    return calling ok_of with (x + 1)\n'
        '\n'
        '## Always fails with "nope".\n'
        'weave fail_ok with x as int into result of int to string:\n'
        '    return calling err_of with "nope"\n'
        '\n'
        'weave main into int:\n'
    )
    return callbacks + textwrap.indent(textwrap.dedent(body).strip("\n"), "    ") + "\n    return 0\n"


# ---------------------------------------------------------------------------
# maybe — presence, extraction and fallbacks
# ---------------------------------------------------------------------------

def test_some_unwrap_returns_payload():
    """`maybe.unwrap` returns the value stored by `some`."""
    res = run_pengu(_prog('''
        var m as maybe int is some 42
        calling spark.println_int with (calling m.unwrap)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "42\n"


def test_none_is_some_is_false():
    """`maybe.is_some` is false for `maybe none`."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        calling spark.println with calling spark.str_bool with (calling n.is_some)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\n"


def test_none_is_none_is_true():
    """`maybe.is_none` is true for `maybe none`."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        calling spark.println with calling spark.str_bool with (calling n.is_none)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n"


def test_unwrap_or_returns_fallback():
    """`maybe.unwrap_or` returns the fallback when the container is empty."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        calling spark.println_int with (calling n.unwrap_or with 7)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "7\n"


def test_unwrap_or_returns_payload():
    """`maybe.unwrap_or` returns the payload when the container is present."""
    res = run_pengu(_prog('''
        var m as maybe int is some 4
        calling spark.println_int with (calling m.unwrap_or with 7)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n"


# ---------------------------------------------------------------------------
# maybe — transformation and combination
# ---------------------------------------------------------------------------

def test_maybe_map_transforms_payload():
    """`maybe.map` applies its callback to a present payload."""
    res = run_pengu(_prog('''
        var m as maybe int is some 21
        var d as maybe int is calling m.map of int with double_it
        calling spark.println_int with (calling d.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "42\n"


def test_maybe_map_of_none_is_none():
    """`maybe.map` on an empty container stays empty without calling back."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        var d as maybe int is calling n.map of int with double_it
        calling spark.println with calling d.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "none\n"


def test_maybe_and_then_chains():
    """`maybe.and_then` chains a callback that itself returns a `maybe`."""
    res = run_pengu(_prog('''
        var m as maybe int is some 8
        var d as maybe int is calling m.and_then of int with half_of
        calling spark.println_int with (calling d.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n"


def test_maybe_and_then_odd_is_none():
    """`maybe.and_then` propagates the `none` produced by the callback."""
    res = run_pengu(_prog('''
        var m as maybe int is some 7
        var d as maybe int is calling m.and_then of int with half_of
        calling spark.println with calling d.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "none\n"


def test_maybe_or_else_uses_fallback():
    """`maybe.or_else` returns the fallback optional when the receiver is empty."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        var alt as maybe int is some 9
        var d as maybe int is calling n.or_else with alt
        calling spark.println_int with (calling d.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "9\n"


def test_maybe_or_else_keeps_present():
    """`maybe.or_else` keeps the receiver's payload when it is present."""
    res = run_pengu(_prog('''
        var m as maybe int is some 2
        var alt as maybe int is some 9
        var d as maybe int is calling m.or_else with alt
        calling spark.println_int with (calling d.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n"


def test_maybe_zip_pairs_payloads():
    """`maybe.zip` combines two present optionals into a `Pair`."""
    res = run_pengu(_prog('''
        var a as maybe int is some 1
        var b as maybe string is some "one"
        var p as maybe oracle.Pair of int and string is calling a.zip of string with b
        if q as oracle.Pair of int and string is p:
            calling spark.println with "{q.first}:{q.second}"
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1:one\n"


def test_maybe_zip_is_none_when_one_side_is_none():
    """`maybe.zip` is empty when either side is empty."""
    res = run_pengu(_prog('''
        var a as maybe int is some 1
        var n as maybe string is maybe none
        var p as maybe oracle.Pair of int and string is calling a.zip of string with n
        calling spark.println with calling spark.str_bool with (calling p.is_some)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\n"


# ---------------------------------------------------------------------------
# maybe — conversion and rendering
# ---------------------------------------------------------------------------

def test_maybe_to_result_ok():
    """`maybe.to_result` produces `ok(payload)` when present."""
    res = run_pengu(_prog('''
        var m as maybe int is some 11
        var r as result of int to string is calling m.to_result with "missing"
        calling spark.println_int with (calling r.unwrap)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "11\n"


def test_maybe_to_result_err():
    """`maybe.to_result` produces `err(error_value)` when empty."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        var r as result of int to string is calling n.to_result with "missing"
        calling spark.println with (calling r.unwrap_err)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "missing\n"


def test_maybe_describe_some():
    """`maybe.describe` renders a present container as `some(v)`."""
    res = run_pengu(_prog('''
        var m as maybe int is some 42
        calling spark.println with calling m.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "some(42)\n"


def test_maybe_describe_none():
    """`maybe.describe` renders an empty container as `none`."""
    res = run_pengu(_prog('''
        var n as maybe int is maybe none
        calling spark.println with calling n.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "none\n"


# ---------------------------------------------------------------------------
# result — presence, extraction and transformation
# ---------------------------------------------------------------------------

def test_result_ok_unwrap():
    """`result.unwrap` returns the success payload of an `ok`."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 5
        calling spark.println_int with (calling a.unwrap)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n"


def test_result_err_unwrap_err():
    """`result.unwrap_err` returns the stored error of an `err`."""
    res = run_pengu(_prog('''
        var b as result of int to string is calling err_of with "boom"
        calling spark.println with (calling b.unwrap_err)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "boom\n"


def test_result_map_transforms_ok():
    """`result.map` applies its callback to the success payload."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 21
        var d as result of int to string is calling a.map of int with double_it
        calling spark.println_int with (calling d.unwrap)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "42\n"


def test_result_map_propagates_err():
    """`result.map` leaves an `err` untouched and skips the callback."""
    res = run_pengu(_prog('''
        var b as result of int to string is calling err_of with "boom"
        var d as result of int to string is calling b.map of int with double_it
        calling spark.println with (calling d.unwrap_err)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "boom\n"


def test_result_map_err_transforms_err():
    """`result.map_err` applies its callback to the stored error."""
    res = run_pengu(_prog('''
        var b as result of int to string is calling err_of with "boom"
        var d as result of int to int is calling b.map_err of int with err_len
        calling spark.println_int with (calling d.unwrap_err)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n"


def test_result_and_then_ok():
    """`result.and_then` chains a callback that returns another result."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 5
        var d as result of int to string is calling a.and_then of int with next_ok
        calling spark.println_int with (calling d.unwrap)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "6\n"


def test_result_and_then_err_propagates():
    """`result.and_then` records the error produced by the callback."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 5
        var d as result of int to string is calling a.and_then of int with fail_ok
        calling spark.println with (calling d.unwrap_err)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "nope\n"


def test_result_or_else_uses_fallback():
    """`result.or_else` returns the fallback result when the receiver is `err`."""
    res = run_pengu(_prog('''
        var b as result of int to string is calling err_of with "boom"
        var good as result of int to string is calling ok_of with 5
        var d as result of int to string is calling b.or_else with good
        calling spark.println_int with (calling d.unwrap)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n"


def test_result_ok_to_maybe():
    """`result.ok` promotes the success payload to a `maybe`."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 5
        var m as maybe int is calling a.ok
        calling spark.println_int with (calling m.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n"


def test_result_ok_to_maybe_empty_for_err():
    """`result.ok` is empty for an `err`."""
    res = run_pengu(_prog('''
        var b as result of int to string is calling err_of with "boom"
        var m as maybe int is calling b.to_maybe
        calling spark.println with calling m.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "none\n"


def test_result_describe_ok_and_err():
    """`result.describe` renders `ok(v)` and `err(e)`."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 3
        var b as result of int to string is calling err_of with "boom"
        calling spark.println with calling a.describe
        calling spark.println with calling b.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "ok(3)\nerr(boom)\n"


# ---------------------------------------------------------------------------
# Module functions — collect, partition and presence scans
# ---------------------------------------------------------------------------

def test_collect_ok_keeps_successes_in_order():
    """`oracle.collect_ok` gathers the `ok` payloads in order and drops errors."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 1
        var b as result of int to string is calling err_of with "e"
        var c as result of int to string is calling ok_of with 3
        var rs as list of result of int to string is [a, b, c]
        var oks as list of int is calling oracle.collect_ok of int and string with rs
        calling spark.println_int with oks.length
        calling spark.println_int with (oks at 1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n3\n"


def test_collect_err_keeps_errors_in_order():
    """`oracle.collect_err` gathers the stored errors in order."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 1
        var b as result of int to string is calling err_of with "e"
        var rs as list of result of int to string is [a, b]
        var errs as list of string is calling oracle.collect_err of int and string with rs
        calling spark.println_int with errs.length
        calling spark.println with (errs at 0)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\ne\n"


def test_partition_results_splits_ok_and_err():
    """`oracle.partition_results` returns a `Pair` of owned success/error lists."""
    res = run_pengu(_prog('''
        var a as result of int to string is calling ok_of with 1
        var b as result of int to string is calling err_of with "e"
        var c as result of int to string is calling ok_of with 3
        var rs as list of result of int to string is [a, b, c]
        var p as oracle.Pair of list of int and list of string is calling oracle.partition_results of int and string with rs
        var oks as list of int is p.first
        var errs as list of string is p.second
        calling spark.println_int with oks.length
        calling spark.println_int with errs.length
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n"


def test_first_present_returns_none_when_all_empty():
    """`oracle.first_present` is empty when every element is empty."""
    res = run_pengu(_prog('''
        var ms as list of maybe int is [maybe none, maybe none]
        var f as maybe int is calling oracle.first_present of int with ms
        calling spark.println with calling f.describe
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "none\n"


def test_first_present_returns_first_payload():
    """`oracle.first_present` returns the first payload in list order."""
    res = run_pengu(_prog('''
        var ms as list of maybe int is [maybe none, some 4, some 5]
        var f as maybe int is calling oracle.first_present of int with ms
        calling spark.println_int with (calling f.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n"


def test_all_present_is_false_with_one_none():
    """`oracle.all_present` is false as soon as one element is empty."""
    res = run_pengu(_prog('''
        var ms as list of maybe int is [some 1, maybe none]
        calling spark.println with calling spark.str_bool with (calling oracle.all_present of int with ms)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\n"


def test_all_present_is_true_when_all_present():
    """`oracle.all_present` is true when every element carries a value."""
    res = run_pengu(_prog('''
        var ms as list of maybe int is [some 1, some 2]
        calling spark.println with calling spark.str_bool with (calling oracle.all_present of int with ms)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n"


# ---------------------------------------------------------------------------
# Types, version and the generic module builders
# ---------------------------------------------------------------------------

def test_pair_equality_from_derive_par():
    """`Pair` derives `Par`, so `==` compares its fields structurally."""
    res = run_pengu(_prog('''
        var a as oracle.Pair of int and string with:
            set .first is 1
            set .second is "one"
        var b as oracle.Pair of int and string with:
            set .first is 1
            set .second is "one"
        var c as oracle.Pair of int and string with:
            set .first is 2
            set .second is "one"
        calling spark.println with calling spark.str_bool with (a == b)
        calling spark.println with calling spark.str_bool with (a == c)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\n"


def test_oracle_version_constant():
    """`oracle.ORACLE_VERSION` is the 2.0 API revision."""
    res = run_pengu(_prog('''
        calling spark.println with calling spark.str_bool with (oracle.ORACLE_VERSION == "2.0.0")
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n"


def test_module_some_of_and_describe():
    """`oracle.some_of` builds a present optional that `describe_optional` renders."""
    res = run_pengu(_prog('''
        var m as maybe int is calling oracle.some_of of int with 8080
        calling spark.println with calling oracle.describe_optional of int with m
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "some(8080)\n"


def test_module_none_of_is_none():
    """`oracle.none_of` builds an empty optional and `is_none_maybe` sees it."""
    res = run_pengu(_prog('''
        var m as maybe int is calling oracle.none_of of int
        calling spark.println with calling spark.str_bool with (calling oracle.is_none_maybe of int with m)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n"


def test_module_map_maybe():
    """`oracle.map_maybe` mirrors the `maybe.map` method."""
    res = run_pengu(_prog('''
        var m as maybe int is calling oracle.some_of of int with 21
        var d as maybe int is calling oracle.map_maybe of int and int with m, double_it
        calling spark.println_int with (calling d.unwrap_or with -1)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "42\n"


# ---------------------------------------------------------------------------
# Legacy 0.14.x surface
# ---------------------------------------------------------------------------

def test_legacy_maybe_int_roundtrip():
    """The legacy `MaybeInt` builders and methods still behave."""
    res = run_pengu(_prog('''
        var m as oracle.MaybeInt is calling oracle.maybe_some_int with 5
        var n as oracle.MaybeInt is calling oracle.maybe_none_int
        calling spark.println with calling spark.str_bool with (calling m.is_present)
        calling spark.println_int with (calling n.unwrap_or with 2)
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n2\n"


def test_legacy_result_string_helpers():
    """The legacy `ResultString` builders keep their `describe_string` format."""
    res = run_pengu(_prog('''
        var ok_r as oracle.ResultString is calling oracle.result_ok_string with "fine"
        var err_r as oracle.ResultString is calling oracle.result_err_string with "e"
        calling spark.println with calling oracle.describe_result_string with ok_r
        calling spark.println with calling oracle.describe_result_string with err_r
    '''))
    assert res.returncode == 0, res.stderr
    assert res.stdout == 'ok("fine")\nerr(e)\n'
