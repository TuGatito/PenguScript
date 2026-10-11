#!/usr/bin/env python3
"""End-to-end tests for ``std.loom`` (Chunk 3 of the Pengunic 2.0 migration).

Every test here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout and exit code.  Nothing inspects the emitted C: the
contract under test is behaviour, and the compiler is free to change how it gets
there.

``loom`` is the *safe* family of list helpers.  Where ``std.tally`` collapses an
empty list onto a sentinel, ``loom`` reports absence (``maybe none``) and keeps
fractions as ``float``; these tests pin that separation deliberately, so the two
modules can never be homogenised into one contract:

* ``loom.mean([1, 2])`` is ``1.5``, not ``1``, and ``loom.mean([])`` is ``0``.
* ``loom.mode([])``, ``loom.median([])``, ``loom.min_max([])``,
  ``loom.variance([])``, ``loom.stddev([])`` and ``loom.percentile([], 50.0)``
  are all ``none``.

The suite is deliberately self-contained.  Each test writes its own throw-away
program into a temporary directory and runs it with the binary cache disabled,
so no test can observe another test's state and a failure names exactly one
program.

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

REPO = Path(__file__).resolve().parent.parent.parent

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script; returns the process.

    Args:
        source: the whole PenguScript program.  It is dedented, so tests can
            indent it to match their own block.
        args: forwarded to the program after ``--``.
        stdin_text: what the program reads from stdin.
        timeout: seconds allowed for compile + run.

    Returns:
        The ``CompletedProcess`` of the CLI invocation.  With ``-q`` the CLI's
        own stdout is empty, so ``stdout`` is the program's own output.
    """
    with tempfile.TemporaryDirectory(prefix="pengu_loom_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


#: Printing helpers spliced into every test program.  A ``list of int`` prints as
#: ``1,2,`` (one trailing comma per element) and a ``list of list of int`` as one
#: ``r``-prefixed, comma-terminated line per row, so an exact stdout comparison
#: pins every element without any Python-side formatting.
_PRELUDE = '''
    weave show_ints with xs as list of int into void:
        for x in xs:
            calling spark.print with calling spark.str_int with x
            calling spark.print with ","
        calling spark.println with ""

    weave show_rows with rows as list of list of int into void:
        for row in rows:
            calling spark.print with "r"
            for x in row:
                calling spark.print with calling spark.str_int with x
                calling spark.print with ","
            calling spark.println with ""

    weave show_maybe_int with m as maybe int into void:
        if m.is_present:
            calling spark.println with "{m.value}"
        else:
            calling spark.println with "none"

    weave show_maybe_float with m as maybe float into void:
        if m.is_present:
            calling spark.println with "{m.value}"
        else:
            calling spark.println with "none"

    weave show_pair with p as Pair of int and int into void:
        calling spark.println with "{p.first}:{p.second}"
'''


def run_body(body: str, helpers: str = "") -> subprocess.CompletedProcess:
    """Compiles and runs ``body`` as the statements of ``main``.

    Args:
        body: the statements of ``main``, indented in the caller's block.
        helpers: extra module-level ``weave`` definitions spliced in above
            ``main``; needed when a loom entry point takes a function value.

    Returns:
        The ``CompletedProcess`` of the run, as :func:`run_pengu` returns it.
    """
    program = (
        "import std.loom\n"
        "import std.spark\n"
        "import std.oracle\n"
        "import std.arithmancy\n"
        "\n"
        + textwrap.dedent(_PRELUDE).lstrip("\n")
        + "\n"
        + textwrap.dedent(helpers).lstrip("\n")
        + "\n"
        "weave main into int:\n"
        + textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
        + "\n    return 0\n"
    )
    return run_pengu(program)


def check(body: str, expected: str, helpers: str = "") -> None:
    """Runs ``body`` and asserts its exit code and exact stdout.

    ``res.stderr`` is the assertion message, so a compile failure shows the real
    diagnostic instead of a bare mismatch.
    """
    res = run_body(body, helpers)
    assert res.returncode == 0, res.stderr
    assert res.stdout == expected, res.stderr


# ---------------------------------------------------------------------------
# The safe contract: fractions survive, absence is `none`
# ---------------------------------------------------------------------------

def test_mean_keeps_the_fraction():
    """`loom.mean` is a float: `[1, 2]` averages to `1.5`, never a truncated `1`."""
    check('''
        var xs as list of int is [1, 2]
        var m as float is calling loom.mean with xs
        calling spark.println with "{m}"
        var ys as list of int is [1, 2, 3, 4]
        var m2 as float is calling loom.mean with ys
        calling spark.println with "{m2}"
    ''', "1.5\n2.5\n")


def test_mean_of_empty_list_is_zero():
    """`loom.mean([])` is the float `0` (the one non-absence scalar of the family)."""
    check('''
        var empty as list of int is list of int
        var m as float is calling loom.mean with empty
        calling spark.println with "{m}"
    ''', "0\n")


def test_absence_for_empty_inputs_is_none():
    """Every statistic returns `none`, not a sentinel, for an empty list."""
    check('''
        var empty as list of int is list of int
        var mo as maybe int is calling loom.mode with empty
        var me as maybe float is calling loom.median with empty
        var mm as maybe Pair of int and int is calling loom.min_max with empty
        var va as maybe float is calling loom.variance with empty
        var sd as maybe float is calling loom.stddev with empty
        var pc as maybe float is calling loom.percentile with empty, 50.0
        calling spark.println with "mode={mo.is_present}"
        calling spark.println with "median={me.is_present}"
        calling spark.println with "min_max={mm.is_present}"
        calling spark.println with "variance={va.is_present}"
        calling spark.println with "stddev={sd.is_present}"
        calling spark.println with "percentile={pc.is_present}"
    ''', "mode=false\nmedian=false\nmin_max=false\nvariance=false\n"
         "stddev=false\npercentile=false\n")


def test_min_max_returns_some_pair():
    """`loom.min_max` answers with `some Pair(first = min, second = max)`."""
    check('''
        var xs as list of int is [3, 1, 2]
        var m as maybe Pair of int and int is calling loom.min_max with xs
        calling spark.println with "present={m.is_present}"
        calling spark.println with "lo={m.value.first} hi={m.value.second}"
        var one as list of int is [7]
        var m2 as maybe Pair of int and int is calling loom.min_max with one
        calling show_pair with m2.value
    ''', "present=true\nlo=1 hi=3\n7:7\n")


# ---------------------------------------------------------------------------
# Sequence generation
# ---------------------------------------------------------------------------

def test_range_builds_half_open_interval():
    """`loom.range` walks `[start, end)` by `step`."""
    check('''
        calling show_ints with (calling loom.range with 1, 5, 1)
        calling show_ints with (calling loom.range with 0, 10, 3)
    ''', "1,2,3,4,\n0,3,6,9,\n")


def test_range_descending_zero_step_and_inverted():
    """A negative step walks down; a zero step or an inverted interval is empty."""
    check('''
        calling show_ints with (calling loom.range with 5, 0, -2)
        calling show_ints with (calling loom.range with 0, 5, 0)
        calling show_ints with (calling loom.range with 5, 1, 1)
    ''', "5,3,1,\n\n\n")


def test_repeat_and_unfold_range():
    """`repeat` copies a value; `unfold_range` yields exactly `count` elements."""
    check('''
        calling show_ints with (calling loom.repeat with 7, 3)
        calling show_ints with (calling loom.repeat with 7, 0)
        calling show_ints with (calling loom.repeat with 7, -2)
        calling show_ints with (calling loom.unfold_range with 5, 3, 2)
        calling show_ints with (calling loom.unfold_range with 5, 3, -2)
        calling show_ints with (calling loom.unfold_range with 1, 0, 1)
    ''', "7,7,7,\n\n\n5,7,9,\n5,3,1,\n\n")


# ---------------------------------------------------------------------------
# Slices and composition
# ---------------------------------------------------------------------------

def test_take_clamps_and_rejects_negative():
    """`take` clamps `n > len`, and `n <= 0` yields the empty list."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        calling show_ints with (calling loom.take with xs, 2)
        var short as list of int is [1, 2, 3]
        calling show_ints with (calling loom.take with short, 9)
        calling show_ints with (calling loom.take with short, 0)
        calling show_ints with (calling loom.take with short, -1)
        var empty as list of int is list of int
        calling show_ints with (calling loom.take with empty, 3)
    ''', "1,2,\n1,2,3,\n\n\n\n")


def test_skip_and_chain():
    """`skip` drops a prefix (`n < 0` behaves like `0`); `chain` concatenates."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        calling show_ints with (calling loom.skip with xs, 2)
        var two as list of int is [1, 2]
        calling show_ints with (calling loom.skip with two, 5)
        calling show_ints with (calling loom.skip with two, -3)
        var a as list of int is [1, 2]
        var b as list of int is [3, 4]
        calling show_ints with (calling loom.chain with a, b)
        var empty as list of int is list of int
        calling show_ints with (calling loom.chain with a, empty)
    ''', "3,4,\n\n1,2,\n1,2,3,4,\n1,2,\n")


# ---------------------------------------------------------------------------
# Blocks and windows
# ---------------------------------------------------------------------------

def test_chunks():
    """`chunks` splits into full blocks and leaves the last one short."""
    check('''
        var xs as list of int is [1, 2, 3, 4, 5]
        calling show_rows with (calling loom.chunks with xs, 2)
        var big as list of int is [1, 2]
        calling show_rows with (calling loom.chunks with big, 5)
    ''', "r1,2,\nr3,4,\nr5,\nr1,2,\n")


def test_chunk_every():
    """`chunk_every` overlaps when `step < n`, skips when `step > n`."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        calling show_rows with (calling loom.chunk_every with xs, 3, 1)
        var ys as list of int is [1, 2, 3, 4, 5]
        calling show_rows with (calling loom.chunk_every with ys, 2, 3)
        calling show_rows with (calling loom.chunk_every with xs, 2, 2)
    ''', "r1,2,3,\nr2,3,4,\nr3,4,\nr4,\nr1,2,\nr4,5,\nr1,2,\nr3,4,\n")


def test_windows_and_windowed():
    """`windows`/`windowed` yield only complete windows and agree on the result."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        calling show_rows with (calling loom.windows with xs, 3)
        calling show_rows with (calling loom.windows with xs, 4)
        calling show_rows with (calling loom.windows with xs, 5)
        calling show_rows with (calling loom.windows with xs, 0)
        var three as list of int is [1, 2, 3]
        calling show_rows with (calling loom.windowed with three, 2)
    ''', "r1,2,3,\nr2,3,4,\nr1,2,3,4,\nr1,2,\nr2,3,\n")


def test_pairwise_and_pairwise_pairs():
    """`pairwise` gives two-element lists; `pairwise_pairs` gives `Pair`s."""
    check('''
        var xs as list of int is [1, 2, 3]
        calling show_rows with (calling loom.pairwise with xs)
        var one as list of int is [1]
        calling show_rows with (calling loom.pairwise with one)
        var ps as list of Pair of int and int is calling loom.pairwise_pairs with xs
        for p in ps:
            calling show_pair with p
        var ps2 as list of Pair of int and int is calling loom.pairwise_pairs with one
        var n as int is calling ps2.len
        calling spark.println with "{n}"
    ''', "r1,2,\nr2,3,\n1:2\n2:3\n0\n")


def test_block_helpers_on_degenerate_inputs():
    """Non-positive sizes and empty inputs produce no blocks at all."""
    check('''
        var two as list of int is [1, 2]
        calling show_rows with (calling loom.chunks with two, 0)
        calling show_rows with (calling loom.chunks with two, -1)
        calling show_rows with (calling loom.chunk_every with two, 0, 1)
        calling show_rows with (calling loom.chunk_every with two, 2, 0)
        var empty as list of int is list of int
        calling show_rows with (calling loom.windows with empty, 2)
        calling show_rows with (calling loom.windows with two, -3)
        calling show_rows with (calling loom.pairwise with empty)
    ''', "")


# ---------------------------------------------------------------------------
# Folds
# ---------------------------------------------------------------------------

def test_sum_and_sum_squares():
    """`sum` and `sum_squares` add with `0` as the empty-list identity."""
    check('''
        var xs as list of int is [1, 2, 3]
        var empty as list of int is list of int
        var s as int is calling loom.sum with xs
        calling spark.println with "{s}"
        var s0 as int is calling loom.sum with empty
        calling spark.println with "{s0}"
        var q as int is calling loom.sum_squares with xs
        calling spark.println with "{q}"
        var q0 as int is calling loom.sum_squares with empty
        calling spark.println with "{q0}"
    ''', "6\n0\n14\n0\n")


def test_product_num():
    """`product_num` multiplies, with `1` as the empty-list identity."""
    check('''
        var xs as list of int is [2, 3, 4]
        var p as int is calling loom.product_num with xs
        calling spark.println with "{p}"
        var empty as list of int is list of int
        var p0 as int is calling loom.product_num with empty
        calling spark.println with "{p0}"
        var zeroed as list of int is [2, 0, 3]
        var pz as int is calling loom.product_num with zeroed
        calling spark.println with "{pz}"
    ''', "24\n1\n0\n")


def test_max_int_and_min_int():
    """`max_int`/`min_int` return `0` for the empty list and handle negatives."""
    check('''
        var xs as list of int is [3, 9, 4]
        var hi as int is calling loom.max_int with xs
        var lo as int is calling loom.min_int with xs
        calling spark.println with "{hi} {lo}"
        var neg as list of int is [-5, -1, -9]
        var hn as int is calling loom.max_int with neg
        var ln as int is calling loom.min_int with neg
        calling spark.println with "{hn} {ln}"
        var empty as list of int is list of int
        var h0 as int is calling loom.max_int with empty
        var l0 as int is calling loom.min_int with empty
        calling spark.println with "{h0} {l0}"
    ''', "9 3\n-1 -9\n0 0\n")


def test_running_folds():
    """`running_sum`, `running_max` and `running_min` accumulate prefixes."""
    check('''
        var xs as list of int is [1, 2, 3]
        calling show_ints with (calling loom.running_sum with xs)
        var ys as list of int is [3, 1, 4]
        calling show_ints with (calling loom.running_max with ys)
        calling show_ints with (calling loom.running_min with ys)
        var one as list of int is [7]
        calling show_ints with (calling loom.running_sum with one)
        var empty as list of int is list of int
        calling show_ints with (calling loom.running_max with empty)
    ''', "1,3,6,\n3,3,4,\n3,1,1,\n7,\n\n")


def test_differences():
    """`differences` is the adjacent delta and is empty for `len <= 1`."""
    check('''
        var xs as list of int is [1, 4, 9]
        calling show_ints with (calling loom.differences with xs)
        var empty as list of int is list of int
        calling show_ints with (calling loom.differences with empty)
        var one as list of int is [7]
        calling show_ints with (calling loom.differences with one)
    ''', "3,5,\n\n\n")


def test_scan_left_with_weave_value():
    """`scan_left` takes a combining weave and seeds slot 0 with the element."""
    check('''
        var xs as list of int is [4, 6, 8]
        calling show_ints with (calling loom.scan_left of int with xs, arithmancy.gcd)
        var empty as list of int is list of int
        calling show_ints with (calling loom.scan_left of int with empty, arithmancy.gcd)
    ''', "4,2,2,\n\n")


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------

def test_any_zero_and_all_equal():
    """`any_zero` and `all_equal` with their empty-list answers."""
    check('''
        var xs as list of int is [1, 0, 3]
        var az as bool is calling loom.any_zero with xs
        calling spark.println with "{az}"
        var empty as list of int is list of int
        var az0 as bool is calling loom.any_zero with empty
        calling spark.println with "{az0}"
        var same as list of int is [4, 4, 4]
        var eq as bool is calling loom.all_equal with same
        calling spark.println with "{eq}"
        var diff as list of int is [4, 4, 5]
        var eq2 as bool is calling loom.all_equal with diff
        calling spark.println with "{eq2}"
        var one as list of int is [9]
        var eq3 as bool is calling loom.all_equal with one
        calling spark.println with "{eq3}"
    ''', "true\nfalse\ntrue\nfalse\ntrue\n")


def test_order_predicates():
    """Strict and non-strict order checks, with ties and short lists."""
    check('''
        var asc as list of int is [1, 2, 3]
        var desc as list of int is [3, 2, 1]
        var ties as list of int is [1, 1, 2]
        var empty as list of int is list of int
        var a1 as bool is calling loom.is_strictly_asc with asc
        var a2 as bool is calling loom.is_strictly_desc with desc
        var a3 as bool is calling loom.is_sorted_asc with ties
        var a4 as bool is calling loom.is_strictly_asc with ties
        var a5 as bool is calling loom.is_sorted_desc with empty
        var a6 as bool is calling loom.is_sorted_desc with desc
        var a7 as bool is calling loom.is_sorted_asc with asc
        calling spark.println with "{a1}"
        calling spark.println with "{a2}"
        calling spark.println with "{a3}"
        calling spark.println with "{a4}"
        calling spark.println with "{a5}"
        calling spark.println with "{a6}"
        calling spark.println with "{a7}"
    ''', "true\ntrue\ntrue\nfalse\ntrue\ntrue\ntrue\n")


def test_is_partitioned_with_module_weave():
    """`is_partitioned` accepts a module function as its predicate value."""
    check('''
        var ok as list of int is [2, 3, 4]
        var bad as list of int is [2, 4, 3]
        var empty as list of int is list of int
        var p1 as bool is calling loom.is_partitioned with ok, arithmancy.is_prime
        var p2 as bool is calling loom.is_partitioned with bad, arithmancy.is_prime
        var p3 as bool is calling loom.is_partitioned with empty, arithmancy.is_prime
        calling spark.println with "{p1}"
        calling spark.println with "{p2}"
        calling spark.println with "{p3}"
    ''', "true\nfalse\ntrue\n")


def test_is_partitioned_with_local_weave():
    """`is_partitioned` also accepts a locally declared `weave` value."""
    check('''
        var ok as list of int is [3, 4, 5]
        var split as list of int is [3, 2, 5]
        var all_low as list of int is [1, 2, 2]
        var p1 as bool is calling loom.is_partitioned with ok, at_least_three
        var p2 as bool is calling loom.is_partitioned with split, at_least_three
        var p3 as bool is calling loom.is_partitioned with all_low, at_least_three
        calling spark.println with "{p1}"
        calling spark.println with "{p2}"
        calling spark.println with "{p3}"
    ''', "true\nfalse\ntrue\n", helpers='''
        weave at_least_three with x as int into bool:
            return x >= 3
    ''')


# ---------------------------------------------------------------------------
# Transformations and combinations
# ---------------------------------------------------------------------------

def test_zip_with_operator_codes():
    """`zip_with` maps op codes 0..4 to add/subtract/product/min/max."""
    check('''
        var a as list of int is [10, 20]
        var b as list of int is [3, 5]
        calling show_ints with (calling loom.zip_with with a, b, 0)
        calling show_ints with (calling loom.zip_with with a, b, 1)
        calling show_ints with (calling loom.zip_with with a, b, 2)
        calling show_ints with (calling loom.zip_with with a, b, 3)
        calling show_ints with (calling loom.zip_with with a, b, 4)
        calling show_ints with (calling loom.zip_with with a, b, 9)
    ''', "13,25,\n7,15,\n30,100,\n3,5,\n10,20,\n13,25,\n")


def test_zip_with_default_op_and_shorter_list():
    """`zip_with` defaults to addition and stops at the shorter input."""
    check('''
        var a as list of int is [1, 2, 3]
        var b as list of int is [10]
        calling show_ints with (calling loom.zip_with with a, b)
        var c as list of int is [1, 2]
        var d as list of int is [10, 20, 30]
        calling show_ints with (calling loom.zip_with with c, d)
        var empty as list of int is list of int
        calling show_ints with (calling loom.zip_with with empty, d)
    ''', "11,\n11,22,\n\n")


def test_zip_with_op_and_zip_longest():
    """`zip_with_op` combines with a weave; `zip_longest` fills the short side."""
    check('''
        var a as list of int is [12, 8]
        var b as list of int is [8, 6]
        calling show_ints with (calling loom.zip_with_op with a, b, arithmancy.gcd)
        var p as list of int is [1, 2, 3]
        var q as list of int is [9]
        calling show_rows with (calling loom.zip_longest with p, q, 7)
        var r as list of int is [1]
        var s as list of int is [2]
        calling show_rows with (calling loom.zip_longest with r, s)
        var empty as list of int is list of int
        calling show_rows with (calling loom.zip_longest with empty, empty, 5)
    ''', "4,2,\nr1,9,\nr2,7,\nr3,7,\nr1,2,\n")


def test_enumerate_and_enumerate_pairs():
    """`enumerate` yields `[index, value]`; `enumerate_pairs` yields `Pair`s."""
    check('''
        var xs as list of int is [10, 20]
        calling show_rows with (calling loom.enumerate with xs)
        var ps as list of Pair of int and int is calling loom.enumerate_pairs with xs
        for p in ps:
            calling show_pair with p
        var empty as list of int is list of int
        calling show_rows with (calling loom.enumerate with empty)
        var ps2 as list of Pair of int and int is calling loom.enumerate_pairs with empty
        var n as int is calling ps2.len
        calling spark.println with "{n}"
    ''', "r0,10,\nr1,20,\n0:10\n1:20\n0\n")


def test_interleave_and_round_robin():
    """`interleave` stops at the shorter list; `round_robin` drains every list."""
    check('''
        var a as list of int is [1, 2]
        var b as list of int is [10]
        calling show_ints with (calling loom.interleave with a, b)
        var lists as list of list of int is list of list of int
        var r1 as list of int is [1, 2]
        var r2 as list of int is [10, 11, 12]
        calling lists.push with r1
        calling lists.push with r2
        calling show_ints with (calling loom.round_robin with lists)
        var nogroups as list of list of int is list of list of int
        calling show_ints with (calling loom.round_robin with nogroups)
    ''', "1,10,\n1,10,2,11,12,\n\n")


def test_rotate_left_and_right():
    """Rotations wrap around large and negative `k` and keep an empty list empty."""
    check('''
        var xs as list of int is [10, 20, 30]
        calling show_ints with (calling loom.rotate_left with xs, 1)
        calling show_ints with (calling loom.rotate_right with xs, 1)
        calling show_ints with (calling loom.rotate_left with xs, 4)
        calling show_ints with (calling loom.rotate_left with xs, -1)
        calling show_ints with (calling loom.rotate_right with xs, 0)
        var empty as list of int is list of int
        calling show_ints with (calling loom.rotate_left with empty, 3)
        calling show_ints with (calling loom.rotate_right with empty, 3)
    ''', "20,30,10,\n30,10,20,\n20,30,10,\n30,10,20,\n10,20,30,\n\n\n")


def test_intersperse():
    """`intersperse` inserts the separator between elements only."""
    check('''
        var xs as list of int is [1, 2, 3]
        calling show_ints with (calling loom.intersperse with xs, 0)
        var one as list of int is [5]
        calling show_ints with (calling loom.intersperse with one, 0)
        var empty as list of int is list of int
        calling show_ints with (calling loom.intersperse with empty, 0)
    ''', "1,0,2,0,3,\n5,\n\n")


def test_flatten_family():
    """`flat_map_identity`, the deprecated `flatten` alias and `flatten_generic`."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        var blocks as list of list of int is calling loom.chunks with xs, 2
        calling show_ints with (calling loom.flat_map_identity with blocks)
        calling show_ints with (calling loom.flatten with blocks)
        calling show_ints with (calling loom.flatten_generic of int with blocks)
        var words as list of list of string is list of list of string
        var w1 as list of string is ["a", "b"]
        var w2 as list of string is ["c"]
        calling words.push with w1
        calling words.push with w2
        var flat as list of string is calling loom.flatten_generic of string with words
        for w in flat:
            calling spark.println with w
    ''', "1,2,3,4,\n1,2,3,4,\n1,2,3,4,\na\nb\nc\n")


# ---------------------------------------------------------------------------
# Sets over sorted lists
# ---------------------------------------------------------------------------

def test_union_sorted():
    """`union_sorted` merges two ascending lists and deduplicates the result."""
    check('''
        var a as list of int is [1, 2]
        var b as list of int is [2, 3]
        calling show_ints with (calling loom.union_sorted with a, b)
        var c as list of int is [1, 1, 2]
        var d as list of int is [2, 3, 3]
        calling show_ints with (calling loom.union_sorted with c, d)
        var empty as list of int is list of int
        calling show_ints with (calling loom.union_sorted with empty, empty)
    ''', "1,2,3,\n1,2,3,\n\n")


def test_intersect_difference_symmetric_difference():
    """The exclusive set operations over ascending lists."""
    check('''
        var a as list of int is [1, 2, 3]
        var b as list of int is [2, 3]
        calling show_ints with (calling loom.intersect_sorted with a, b)
        calling show_ints with (calling loom.difference_sorted with a, b)
        var c as list of int is [1, 2]
        var d as list of int is [2, 3]
        calling show_ints with (calling loom.symmetric_difference_sorted with c, d)
        var e as list of int is [1, 2]
        var f as list of int is [3, 4]
        calling show_ints with (calling loom.intersect_sorted with e, f)
    ''', "2,3,\n1,\n1,3,\n\n")


# ---------------------------------------------------------------------------
# Search and indices
# ---------------------------------------------------------------------------

def test_find_first_and_find_last():
    """`find_first`/`find_last` answer `some index` or `none`."""
    check('''
        var xs as list of int is [10, 20, 10]
        calling show_maybe_int with (calling loom.find_first with xs, 10)
        calling show_maybe_int with (calling loom.find_last with xs, 10)
        calling show_maybe_int with (calling loom.find_first with xs, 9)
        calling show_maybe_int with (calling loom.find_last with xs, 9)
        var empty as list of int is list of int
        calling show_maybe_int with (calling loom.find_first with empty, 1)
    ''', "0\n2\nnone\nnone\nnone\n")


def test_binary_search():
    """`binary_search` finds the index in an ascending list or answers `none`."""
    check('''
        var xs as list of int is [1, 2, 4, 5]
        calling show_maybe_int with (calling loom.binary_search with xs, 4)
        calling show_maybe_int with (calling loom.binary_search with xs, 3)
        calling show_maybe_int with (calling loom.binary_search with xs, 1)
        calling show_maybe_int with (calling loom.binary_search with xs, 5)
        var empty as list of int is list of int
        calling show_maybe_int with (calling loom.binary_search with empty, 1)
    ''', "2\nnone\n0\n3\nnone\n")


def test_count_if_even_and_positive():
    """`count_if_even` counts negatives too; `count_if_positive` is strictly `> 0`."""
    check('''
        var xs as list of int is [-2, 0, 3]
        var c1 as int is calling loom.count_if_even with xs
        var c2 as int is calling loom.count_if_positive with xs
        var empty as list of int is list of int
        var c3 as int is calling loom.count_if_even with empty
        calling spark.println with "{c1} {c2} {c3}"
    ''', "2 1 0\n")


def test_index_min_and_index_max():
    """`index_min`/`index_max` locate the first extreme, or `none` when empty."""
    check('''
        var xs as list of int is [3, 1, 4, 1]
        calling show_maybe_int with (calling loom.index_min with xs)
        calling show_maybe_int with (calling loom.index_max with xs)
        var empty as list of int is list of int
        calling show_maybe_int with (calling loom.index_min with empty)
        calling show_maybe_int with (calling loom.index_max with empty)
    ''', "1\n2\nnone\nnone\n")


# ---------------------------------------------------------------------------
# Pure structural editing
# ---------------------------------------------------------------------------

def test_insert_at():
    """`insert_at` clamps the position to `[0, len]`."""
    check('''
        var xs as list of int is [1, 2, 3]
        calling show_ints with (calling loom.insert_at with xs, 1, 9)
        calling show_ints with (calling loom.insert_at with xs, 9, 9)
        calling show_ints with (calling loom.insert_at with xs, -4, 9)
        calling show_ints with (calling loom.insert_at with xs, 0, 9)
    ''', "1,9,2,3,\n1,2,3,9,\n9,1,2,3,\n9,1,2,3,\n")


def test_remove_at_and_replace_at():
    """Out-of-range `remove_at`/`replace_at` return an untouched full copy."""
    check('''
        var xs as list of int is [1, 2, 3]
        calling show_ints with (calling loom.remove_at with xs, 1)
        calling show_ints with (calling loom.remove_at with xs, 5)
        calling show_ints with (calling loom.remove_at with xs, -1)
        calling show_ints with (calling loom.replace_at with xs, 1, 7)
        calling show_ints with (calling loom.replace_at with xs, 5, 7)
        calling show_ints with (calling loom.replace_at with xs, -1, 7)
    ''', "1,3,\n1,2,3,\n1,2,3,\n1,7,3,\n1,2,3,\n1,2,3,\n")


def test_swap_at():
    """`swap_at` swaps when both positions are in range and copies otherwise."""
    check('''
        var xs as list of int is [1, 2, 3]
        calling show_ints with (calling loom.swap_at with xs, 0, 2)
        calling show_ints with (calling loom.swap_at with xs, 0, 0)
        calling show_ints with (calling loom.swap_at with xs, 0, 9)
        calling show_ints with (calling loom.swap_at with xs, -1, 1)
    ''', "3,2,1,\n1,2,3,\n1,2,3,\n1,2,3,\n")


def test_pad_left_and_pad_right():
    """`pad_left`/`pad_right` grow to `target_len` and copy when it is smaller."""
    check('''
        var xs as list of int is [1, 2]
        calling show_ints with (calling loom.pad_left with xs, 4, -1)
        calling show_ints with (calling loom.pad_right with xs, 4, -1)
        calling show_ints with (calling loom.pad_left with xs, 1, -1)
        calling show_ints with (calling loom.pad_right with xs, 2)
        var empty as list of int is list of int
        calling show_ints with (calling loom.pad_left with empty, 3, 7)
    ''', "-1,-1,1,2,\n1,2,-1,-1,\n1,2,\n1,2,\n7,7,7,\n")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def test_median():
    """`median` sorts first, averages the middle pair and is `none` when empty."""
    check('''
        var odd as list of int is [3, 1, 2]
        calling show_maybe_float with (calling loom.median with odd)
        var even as list of int is [1, 2, 3, 4]
        calling show_maybe_float with (calling loom.median with even)
        var unsorted as list of int is [9, 1]
        calling show_maybe_float with (calling loom.median with unsorted)
        var empty as list of int is list of int
        calling show_maybe_float with (calling loom.median with empty)
    ''', "2\n2.5\n5\nnone\n")


def test_mode():
    """`mode` picks the most frequent value and keeps the first on a tie."""
    check('''
        var xs as list of int is [1, 2, 2, 3]
        calling show_maybe_int with (calling loom.mode with xs)
        var first as list of int is [3, 3, 1, 1]
        calling show_maybe_int with (calling loom.mode with first)
        var one as list of int is [9]
        calling show_maybe_int with (calling loom.mode with one)
        var empty as list of int is list of int
        calling show_maybe_int with (calling loom.mode with empty)
    ''', "2\n3\n9\nnone\n")


def test_variance_and_stddev():
    """Population variance and its square root, or `none` when empty."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        calling show_maybe_float with (calling loom.variance with xs)
        var d as maybe float is calling loom.stddev with xs
        var sq as float is d.value * d.value
        calling spark.println with "{sq}"
        var flat as list of int is [4, 4, 4]
        calling show_maybe_float with (calling loom.variance with flat)
        calling show_maybe_float with (calling loom.stddev with flat)
        var empty as list of int is list of int
        calling show_maybe_float with (calling loom.variance with empty)
        calling show_maybe_float with (calling loom.stddev with empty)
    ''', "1.25\n1.25\n0\n0\nnone\nnone\n")


def test_percentile():
    """`percentile` interpolates linearly and refuses `p` outside `[0, 100]`."""
    check('''
        var xs as list of int is [1, 2, 3, 4]
        calling show_maybe_float with (calling loom.percentile with xs, 50.0)
        calling show_maybe_float with (calling loom.percentile with xs, 0.0)
        calling show_maybe_float with (calling loom.percentile with xs, 100.0)
        calling show_maybe_float with (calling loom.percentile with xs, 25.0)
        calling show_maybe_float with (calling loom.percentile with xs, 150.0)
        calling show_maybe_float with (calling loom.percentile with xs, -1.0)
        var empty as list of int is list of int
        calling show_maybe_float with (calling loom.percentile with empty, 50.0)
    ''', "2.5\n1\n4\n1.75\nnone\nnone\nnone\n")


# ---------------------------------------------------------------------------
# Generic core helpers
# ---------------------------------------------------------------------------

def test_first_or():
    """`first_or` returns the first element or the default, for any `T`."""
    check('''
        var xs as list of int is [1, 2]
        var a as int is calling loom.first_or of int with xs, 0
        calling spark.println with "{a}"
        var empty as list of int is list of int
        var b as int is calling loom.first_or of int with empty, 5
        calling spark.println with "{b}"
        var words as list of string is ["a", "b"]
        var c as string is calling loom.first_or of string with words, "z"
        calling spark.println with c
        var blank as list of string is list of string
        calling spark.println with (calling loom.first_or of string with blank, "z")
    ''', "1\n5\na\nz\n")


def test_generic_take_and_take_last():
    """`generic_take`/`generic_take_last` slice string lists and clamp `n`."""
    check('''
        var words as list of string is ["a", "b", "c"]
        var head as list of string is calling loom.generic_take of string with words, 2
        for w in head:
            calling spark.println with w
        var tail as list of string is calling loom.generic_take_last of string with words, 2
        for w in tail:
            calling spark.println with w
        var all as list of string is calling loom.generic_take of string with words, 9
        var n1 as int is calling all.len
        calling spark.println with "{n1}"
        var none_head as list of string is calling loom.generic_take of string with words, -1
        var n2 as int is calling none_head.len
        calling spark.println with "{n2}"
        var none_tail as list of string is calling loom.generic_take_last of string with words, 0
        var n3 as int is calling none_tail.len
        calling spark.println with "{n3}"
    ''', "a\nb\nb\nc\n3\n0\n0\n")


def test_generic_reverse_and_chain():
    """`generic_reverse` and `generic_chain` work on a non-int element type."""
    check('''
        var words as list of string is ["a", "b"]
        var back as list of string is calling loom.generic_reverse of string with words
        for w in back:
            calling spark.println with w
        var joined as list of string is calling loom.generic_chain of string with back, words
        var n as int is calling joined.len
        calling spark.println with "{n}"
        calling spark.println with (joined at 0)
    ''', "b\na\n4\nb\n")


def test_generic_index_of():
    """`generic_index_of` finds the first match or returns `-1`."""
    check('''
        var words as list of string is ["a", "b", "c"]
        var i1 as int is calling loom.generic_index_of of string with words, "b"
        var i2 as int is calling loom.generic_index_of of string with words, "z"
        var i3 as int is calling loom.generic_index_of of string with words, "a"
        calling spark.println with "{i1} {i2} {i3}"
    ''', "1 -1 0\n")


# ---------------------------------------------------------------------------
# Module constant
# ---------------------------------------------------------------------------

def test_loom_version_constant():
    """`LOOM_VERSION` is the migrated 2.1.0 revision."""
    check('''
        calling spark.println with "version={loom.LOOM_VERSION}"
    ''', "version=2.1.0\n")
