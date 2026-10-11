#!/usr/bin/env python3
"""End-to-end tests for ``std.tally`` (Chunk 3 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.tally`` is the *sentinel* family of list algorithms, deliberately distinct
from the safe ``loom`` family: an empty list collapses to a natural identity
(``sum`` -> 0, ``product`` -> 1, ``max_val`` -> 0, ``mode`` -> 0, ``min_max`` ->
``[]``) and fractional statistics truncate to ``int`` (``mean([1, 2]) == 1``).
These tests pin that contract, the compatibility module functions, every
deprecated alias and the newer shard API.  The safe family is never imported here.

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled, so no test can observe another test's state
and a failure names exactly one program.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
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

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_tally_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


# ---------------------------------------------------------------------------
# Program builders
# ---------------------------------------------------------------------------

#: Prints one int per line for a ``list of int``.
_DUMP_INT_LIST = """
weave dump with l as list of int into void:
    for v in l:
        calling spark.println with calling spark.str_int with v
"""

#: Prints each inner ``list of int`` of a ``list of list of int`` then a ``|``.
_DUMP_INT_ROWS = """
weave dump_rows with rows as list of list of int into void:
    for row in rows:
        for v in row:
            calling spark.println with calling spark.str_int with v
        calling spark.println with "|"
"""

#: A named binary weave, because bare lambdas cannot be reused across calls.
_ADD_INTS = """
weave add with a as int, b as int into int:
    return a + b
"""


def _run_main(body: str, helpers: str = "") -> subprocess.CompletedProcess:
    """Runs ``body`` as the body of a ``main`` that imports spark and tally."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = ["import std.spark", "import std.tally"]
    if helpers:
        sections += ["", textwrap.dedent(helpers).strip("\n")]
    sections += ["", "weave main into int:", body, "    return 0", ""]
    return run_pengu("\n".join(sections))


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``TALLY_VERSION`` reports the migrated module version ``2.2.0``."""
    res = _run_main("calling spark.println with tally.TALLY_VERSION")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.2.0\n"


# ---------------------------------------------------------------------------
# The sentinel contract: an empty list collapses to a natural identity
# ---------------------------------------------------------------------------

def test_sum_and_product_of_empty_list_are_identities():
    """``tally.sum([])`` is 0 and ``tally.product([])`` is 1, never an error."""
    res = _run_main('''
        var e as list of int is list of int
        calling spark.println with calling spark.str_int with (calling tally.sum with e)
        calling spark.println with calling spark.str_int with (calling tally.product with e)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n1\n"


def test_empty_list_statistics_collapse_to_sentinels():
    """``max_val``/``min_val``/``mode``/``median``/``mean`` of ``[]`` are all 0."""
    res = _run_main('''
        var e as list of int is list of int
        calling spark.println with calling spark.str_int with (calling tally.max_val with e)
        calling spark.println with calling spark.str_int with (calling tally.min_val with e)
        calling spark.println with calling spark.str_int with (calling tally.mode with e)
        calling spark.println with calling spark.str_int with (calling tally.median with e)
        calling spark.println with calling spark.str_int with (calling tally.mean with e)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n0\n0\n0\n0\n"


def test_min_max_of_empty_list_is_empty():
    """``tally.min_max([])`` is the empty list, not a two-element pair."""
    res = _run_main('''
        var e as list of int is list of int
        let mm as list of int is calling tally.min_max with e
        calling spark.println with calling spark.str_int with (calling mm.len)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_empty_receiver_methods_return_sentinels():
    """The dot-receiver forms on ``[]`` give 0, 1, 0 and 0 as well."""
    res = _run_main('''
        var e as list of int is list of int
        calling spark.println with calling spark.str_int with (calling e.sum)
        calling spark.println with calling spark.str_int with (calling e.product)
        calling spark.println with calling spark.str_int with (calling e.max_val)
        calling spark.println with calling spark.str_int with (calling e.mode)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n1\n0\n0\n"


def test_index_reductions_of_empty_list_are_minus_one():
    """``argmin``/``argmax``/``min_index``/``max_index`` of ``[]`` are -1."""
    res = _run_main('''
        var e as list of int is list of int
        calling spark.println with calling spark.str_int with (calling tally.argmin with e)
        calling spark.println with calling spark.str_int with (calling tally.argmax with e)
        calling spark.println with calling spark.str_int with (calling tally.min_index with e)
        calling spark.println with calling spark.str_int with (calling tally.max_index with e)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n-1\n-1\n-1\n"


def test_search_lookups_of_empty_list_are_minus_one():
    """Absent searches give -1 and an absent first-match gives ``none``."""
    res = _run_main('''
        var e as list of int is list of int
        calling spark.println with calling spark.str_int with (calling tally.index_of with e, 0)
        calling spark.println with calling spark.str_int with (calling tally.last_index_of with e, 0)
        let a as maybe int is calling tally.find_first_gt with e, 0
        let b as maybe int is calling tally.find_first_lt with e, 0
        calling spark.println with calling spark.str_int with (a or else -1)
        calling spark.println with calling spark.str_int with (b or else -1)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n-1\n-1\n-1\n"


# ---------------------------------------------------------------------------
# Fractional statistics truncate to int
# ---------------------------------------------------------------------------

def test_mean_truncates_towards_zero_module_form():
    """``tally.mean([1, 2])`` is 1 and ``tally.mean([-1, -2])`` is -1."""
    res = _run_main('''
        var xs as list of int is [1, 2]
        var neg as list of int is [-1, -2]
        calling spark.println with calling spark.str_int with (calling tally.mean with xs)
        calling spark.println with calling spark.str_int with (calling tally.mean with neg)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n-1\n"


def test_mean_truncates_towards_zero_with_dot_receiver():
    """``calling xs.mean`` on ``[1, 2]`` is the ``int`` 1, not 1.5."""
    res = _run_main('''
        var xs as list of int is [1, 2]
        calling spark.println with calling spark.str_int with (calling xs.mean)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n"


def test_average_alias_matches_mean_in_both_forms():
    """The deprecated ``average`` gives the same truncated 1 as ``mean``."""
    res = _run_main('''
        var xs as list of int is [1, 2]
        calling spark.println with calling spark.str_int with (calling tally.average with xs)
        calling spark.println with calling spark.str_int with (calling xs.average)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n1\n"


# ---------------------------------------------------------------------------
# Module functions and enchanting methods agree
# ---------------------------------------------------------------------------

def test_module_functions_and_methods_agree_on_reductions():
    """``tally.sum``/``max_val``/``min_val`` equal the dot-receiver results."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        calling spark.println with calling spark.str_int with (calling tally.sum with xs)
        calling spark.println with calling spark.str_int with (calling xs.sum)
        calling spark.println with calling spark.str_int with (calling tally.max_val with xs)
        calling spark.println with calling spark.str_int with (calling xs.max_val)
        calling spark.println with calling spark.str_int with (calling tally.min_val with xs)
        calling spark.println with calling spark.str_int with (calling xs.min_val)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "8\n8\n4\n4\n1\n1\n"


def test_filter_even_module_and_method_agree():
    """``tally.filter_even`` and ``calling xs.filter_even`` produce ``[4, 6]``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4, 1, 6]
        let a as list of int is calling tally.filter_even with xs
        let b as list of int is calling xs.filter_even
        calling dump with a
        calling spark.println with "|"
        calling dump with b
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n6\n|\n4\n6\n"


# ---------------------------------------------------------------------------
# Deprecated aliases
# ---------------------------------------------------------------------------

def test_argmin_and_argmax_aliases_match_min_and_max_index():
    """``argmin``/``argmax`` agree with ``min_index``/``max_index`` in both forms."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        calling spark.println with calling spark.str_int with (calling tally.argmin with xs)
        calling spark.println with calling spark.str_int with (calling xs.argmin)
        calling spark.println with calling spark.str_int with (calling tally.argmax with xs)
        calling spark.println with calling spark.str_int with (calling xs.argmax)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n1\n2\n2\n"


def test_dedup_alias_matches_unique():
    """``dedup`` keeps first-appearance order exactly like ``unique``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 3, 2]
        let u as list of int is calling tally.unique with xs
        let d as list of int is calling tally.dedup with xs
        calling dump with u
        calling spark.println with "|"
        calling dump with d
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n2\n|\n3\n1\n2\n"


def test_filter_range_alias_matches_filter_in_range():
    """``filter_range`` keeps the closed ``[lo, hi]`` span like ``filter_in_range``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4, 1, 5]
        var lo as int is 2
        var hi as int is 4
        let a as list of int is calling tally.filter_in_range with xs, lo, hi
        let b as list of int is calling tally.filter_range with xs, lo, hi
        calling dump with a
        calling spark.println with "|"
        calling dump with b
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n4\n|\n3\n4\n"


def test_group_count_alias_matches_frequencies():
    """``group_count`` returns the same value -> count map as ``frequencies``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 3]
        let f as map of int to int is calling tally.frequencies with xs
        let g as map of int to int is calling tally.group_count with xs
        calling spark.println with calling spark.str_int with (calling f.get with 3)
        calling spark.println with calling spark.str_int with (calling g.get with 1)
        calling spark.println with calling spark.str_int with (calling g.get with 9)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n0\n"


# ---------------------------------------------------------------------------
# The newer shard API
# ---------------------------------------------------------------------------

def test_zip_with_applies_the_function_pairwise():
    """``tally.zip_with`` pairs ``[3, 1]`` and ``[2, 5]`` into ``[5, 6]``."""
    res = _run_main('''
        var xs as list of int is [3, 1]
        var ys as list of int is [2, 5]
        let z as list of int is calling tally.zip_with with xs, ys, add
        calling dump with z
    ''', helpers=_DUMP_INT_LIST + _ADD_INTS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n6\n"


def test_zip_with_stops_at_the_shorter_list():
    """``tally.zip_with`` yields one element per position of the shorter input."""
    res = _run_main('''
        var xs as list of int is [1, 2, 3]
        var ys as list of int is [10, 20]
        let z as list of int is calling tally.zip_with with xs, ys, add
        calling dump with z
    ''', helpers=_DUMP_INT_LIST + _ADD_INTS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "11\n22\n"


def test_chunk_splits_into_consecutive_runs():
    """``tally.chunk`` splits ``[3, 1, 4, 1, 5]`` with span 2 into three runs."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4, 1, 5]
        let rows as list of list of int is calling tally.chunk with xs, 2
        calling dump_rows with rows
    ''', helpers=_DUMP_INT_ROWS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n|\n4\n1\n|\n5\n|\n"


def test_chunk_span_above_length_is_a_single_run():
    """A span larger than the input gives one run holding the whole list."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let rows as list of list of int is calling tally.chunk with xs, 10
        calling spark.println with calling spark.str_int with (calling rows.len)
        calling dump_rows with rows
    ''', helpers=_DUMP_INT_ROWS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n3\n1\n4\n|\n"


def test_chunk_nonpositive_span_is_empty():
    """A span of 0 gives an empty list, never an infinite loop."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let rows as list of list of int is calling tally.chunk with xs, 0
        calling spark.println with calling spark.str_int with (calling rows.len)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_windowed_slides_by_one():
    """``tally.windowed`` with width 2 yields ``[[3, 1], [1, 4]]``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let rows as list of list of int is calling tally.windowed with xs, 2
        calling dump_rows with rows
    ''', helpers=_DUMP_INT_ROWS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n|\n1\n4\n|\n"


def test_windowed_width_above_length_or_zero_is_empty():
    """A width above the length, or 0, gives an empty window list."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let wide as list of list of int is calling tally.windowed with xs, 4
        let zero as list of list of int is calling tally.windowed with xs, 0
        calling spark.println with calling spark.str_int with (calling wide.len)
        calling spark.println with calling spark.str_int with (calling zero.len)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n0\n"


def test_scan_left_accumulates_prefixes():
    """``tally.scan_left`` with ``+`` on ``[1, 2, 3]`` gives ``[1, 3, 6]``."""
    res = _run_main('''
        var xs as list of int is [1, 2, 3]
        let out as list of int is calling tally.scan_left with xs, (lambda acc as int, x as int into acc + x)
        calling dump with out
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n3\n6\n"


def test_scan_left_of_empty_list_is_empty():
    """``tally.scan_left`` over ``[]`` returns an empty list."""
    res = _run_main('''
        var e as list of int is list of int
        let out as list of int is calling tally.scan_left with e, (lambda acc as int, x as int into acc + x)
        calling spark.println with calling spark.str_int with (calling out.len)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_running_sum_accumulates_prefixes():
    """``tally.running_sum`` of ``[3, 1, 2]`` is ``[3, 4, 6]``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 2]
        let out as list of int is calling tally.running_sum with xs
        calling dump with out
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n4\n6\n"


def test_running_sum_of_empty_list_is_empty():
    """``tally.running_sum`` over ``[]`` returns an empty list."""
    res = _run_main('''
        var e as list of int is list of int
        let out as list of int is calling tally.running_sum with e
        calling spark.println with calling spark.str_int with (calling out.len)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_min_max_returns_min_then_max():
    """``tally.min_max([3, 1, 4])`` is the two-element list ``[1, 4]``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let mm as list of int is calling tally.min_max with xs
        calling spark.println with calling spark.str_int with (calling mm.len)
        calling dump with mm
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n4\n"


def test_enumerate_pairs_index_and_value():
    """``tally.enumerate_pairs`` turns ``[3, 1]`` into ``[[0, 3], [1, 1]]``."""
    res = _run_main('''
        var xs as list of int is [3, 1]
        let pairs as list of list of int is calling tally.enumerate_pairs with xs
        calling dump_rows with pairs
    ''', helpers=_DUMP_INT_ROWS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n3\n|\n1\n1\n|\n"


def test_partition_by_splits_matching_then_rest():
    """``tally.partition_by`` returns ``[matching, non_matching]`` in that order."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let parts as list of list of int is calling tally.partition_by with xs, (lambda x as int into (x % 2) == 0)
        calling dump_rows with parts
    ''', helpers=_DUMP_INT_ROWS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n|\n3\n1\n|\n"


def test_partition_by_all_matching_leaves_second_empty():
    """When every element matches, the second partition is empty but present."""
    res = _run_main('''
        var xs as list of int is [2, 4]
        let parts as list of list of int is calling tally.partition_by with xs, (lambda x as int into (x % 2) == 0)
        calling spark.println with calling spark.str_int with (calling parts.len)
        calling dump_rows with parts
    ''', helpers=_DUMP_INT_ROWS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n2\n4\n|\n|\n"


def test_frequencies_counts_each_value():
    """``tally.frequencies`` maps each value to its count; absent keys give 0."""
    res = _run_main('''
        var xs as list of int is [3, 1, 3]
        let f as map of int to int is calling tally.frequencies with xs
        calling spark.println with calling spark.str_int with (calling f.get with 3)
        calling spark.println with calling spark.str_int with (calling f.get with 1)
        calling spark.println with calling spark.str_int with (calling f.get with 9)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n0\n"


def test_frequencies_of_empty_list_is_empty():
    """``tally.frequencies([])`` is an empty map, so every lookup is 0."""
    res = _run_main('''
        var e as list of int is list of int
        let f as map of int to int is calling tally.frequencies with e
        calling spark.println with calling spark.str_int with (calling f.get with 0)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


# ---------------------------------------------------------------------------
# Edge cases: n larger than the list, negative n, duplicates, negatives
# ---------------------------------------------------------------------------

def test_take_clips_to_length_and_rejects_negative_n():
    """``take`` clips n above the length and treats a negative n as zero."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let big as list of int is calling tally.take with xs, 5
        let neg as list of int is calling tally.take with xs, -2
        calling dump with big
        calling spark.println with "|"
        calling spark.println with calling spark.str_int with (calling neg.len)
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n4\n|\n0\n"


def test_drop_clamps_negative_n_and_stops_at_length():
    """``drop`` clamps a negative n to 0 and an over-long n to an empty list."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let over as list of int is calling tally.drop with xs, 5
        let neg as list of int is calling tally.drop with xs, -2
        calling spark.println with calling spark.str_int with (calling over.len)
        calling dump with neg
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n3\n1\n4\n"


def test_slice_list_clamps_both_bounds():
    """``slice_list`` clamps a negative start and an over-long end."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let tail as list of int is calling tally.slice_list with xs, 1, 99
        let front as list of int is calling tally.slice_list with xs, -3, 2
        let empty_slice as list of int is calling tally.slice_list with xs, 2, 1
        calling dump with tail
        calling spark.println with "|"
        calling dump with front
        calling spark.println with "|"
        calling spark.println with calling spark.str_int with (calling empty_slice.len)
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n4\n|\n3\n1\n|\n0\n"


def test_take_and_drop_default_to_one_element():
    """``take`` defaults to the first element and ``drop`` to the rest."""
    res = _run_main('''
        var xs as list of int is [3, 1, 4]
        let head as list of int is calling xs.take
        let rest as list of int is calling xs.drop
        calling dump with head
        calling spark.println with "|"
        calling dump with rest
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n|\n1\n4\n"


def test_negative_values_sum_and_abs_all():
    """Negatives reduce normally and ``abs_all`` maps them to their distance to 0."""
    res = _run_main('''
        var xs as list of int is [-3, 1, -2]
        let positives as list of int is calling tally.abs_all with xs
        calling spark.println with calling spark.str_int with (calling tally.sum with xs)
        calling dump with positives
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-4\n3\n1\n2\n"


def test_unique_keeps_first_appearance_order():
    """Duplicates collapse to their first occurrence: ``[3, 1, 3, 2, 1]`` -> ``[3, 1, 2]``."""
    res = _run_main('''
        var xs as list of int is [3, 1, 3, 2, 1]
        let u as list of int is calling tally.unique with xs
        calling dump with u
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n2\n"


def test_sort_asc_and_sort_desc_do_not_mutate_input():
    """``sort_asc`` and ``sort_desc`` copy; the input keeps its original order."""
    res = _run_main('''
        var xs as list of int is [2, 2, 1, 3]
        let asc as list of int is calling tally.sort_asc with xs
        let desc as list of int is calling tally.sort_desc with xs
        calling dump with asc
        calling spark.println with "|"
        calling dump with desc
        calling spark.println with "|"
        calling dump with xs
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n2\n2\n3\n|\n3\n2\n2\n1\n|\n2\n2\n1\n3\n"


def test_clamp_all_uses_given_bounds_and_defaults():
    """``clamp_all`` defaults to ``[0, 100]`` and honours explicit bounds."""
    res = _run_main('''
        var xs as list of int is [-5, 3, 150]
        let default_clamped as list of int is calling tally.clamp_all with xs
        var lo as int is 0
        var hi as int is 9
        let explicit as list of int is calling tally.clamp_all with xs, lo, hi
        calling dump with default_clamped
        calling spark.println with "|"
        calling dump with explicit
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n3\n100\n|\n0\n3\n9\n"


def test_at_or_and_at_safe_handle_out_of_range():
    """``at_or`` returns its default and ``at_safe`` returns ``none`` out of range."""
    res = _run_main('''
        var xs as list of int is [7, 8]
        calling spark.println with calling spark.str_int with (calling tally.at_or with xs, 1, -1)
        calling spark.println with calling spark.str_int with (calling tally.at_or with xs, 9, -1)
        let a as maybe int is calling tally.at_safe with xs, 5
        let b as maybe int is calling tally.at_safe with xs, 1
        calling spark.println with calling spark.str_int with (a or else -1)
        calling spark.println with calling spark.str_int with (b or else -1)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "8\n-1\n-1\n8\n"


def test_repeat_nonpositive_times_is_empty():
    """``tally.repeat`` gives an empty list for ``times <= 0`` and repeats otherwise."""
    res = _run_main('''
        let zero_copies as list of int is calling tally.repeat with 7, 0
        let three_copies as list of int is calling tally.repeat with 7, 3
        calling spark.println with calling spark.str_int with (calling zero_copies.len)
        calling dump with three_copies
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n7\n7\n7\n"


def test_concat_zip_sum_and_dot():
    """``concat``, ``zip_sum`` and ``dot`` all stop or combine as documented."""
    res = _run_main('''
        var a as list of int is [1]
        var b as list of int is [2, 3]
        var c as list of int is [1, 2, 3]
        var d as list of int is [10, 20]
        var f as list of int is [4, 5]
        let cat as list of int is calling tally.concat with a, b
        let zs as list of int is calling tally.zip_sum with c, d
        let dp as int is calling tally.dot with c, f
        calling dump with cat
        calling spark.println with "|"
        calling dump with zs
        calling spark.println with "|"
        calling spark.println with calling spark.str_int with dp
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n2\n3\n|\n11\n22\n|\n14\n"


def test_generic_float_reductions_stay_float():
    """The generic enchanting blocks reduce ``list of float`` without truncation."""
    res = _run_main('''
        var fs as list of float is [1.5, 0.5]
        calling spark.println with calling spark.str_float with (calling fs.sum)
        calling spark.println with calling spark.str_float with (calling fs.mean)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n"


def test_contains_and_count_of_are_exact():
    """``contains`` and ``count_of`` use equality, never approximations."""
    res = _run_main('''
        var xs as list of int is [2, 2, 1, 1, 3]
        calling spark.println with calling spark.str_bool with (calling tally.contains with xs, 3)
        calling spark.println with calling spark.str_bool with (calling tally.contains with xs, 99)
        calling spark.println with calling spark.str_int with (calling tally.count_of with xs, 2)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\n2\n"


def test_median_truncates_on_even_length():
    """``median`` averages the two central values with integer division."""
    res = _run_main('''
        var odd as list of int is [1, 2, 3]
        var even as list of int is [1, 2]
        calling spark.println with calling spark.str_int with (calling tally.median with odd)
        calling spark.println with calling spark.str_int with (calling tally.median with even)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n"


def test_mode_breaks_ties_by_first_appearance():
    """``mode`` on a two-way tie returns the value seen first."""
    res = _run_main('''
        var xs as list of int is [2, 2, 1, 1, 3]
        calling spark.println with calling spark.str_int with (calling tally.mode with xs)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n"


def test_boolean_predicates_over_lists():
    """``all_zero``/``all_positive``/``any_negative``/``is_empty`` read the list."""
    res = _run_main('''
        var zeros as list of int is [0, 0]
        var mixed as list of int is [1, -2]
        var e as list of int is list of int
        calling spark.println with calling spark.str_bool with (calling zeros.all_zero)
        calling spark.println with calling spark.str_bool with (calling mixed.all_positive)
        calling spark.println with calling spark.str_bool with (calling mixed.any_negative)
        calling spark.println with calling spark.str_bool with (calling tally.is_empty with e)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\ntrue\ntrue\n"


def test_sortedness_and_map_helpers():
    """``is_sorted_asc``/``is_sorted_desc``/``map_double``/``sum_of_squares``."""
    res = _run_main('''
        var asc as list of int is [1, 2, 2, 3]
        var desc as list of int is [3, 2, 1]
        var xs as list of int is [3, 1, 2]
        let doubled as list of int is calling tally.map_double with xs
        calling spark.println with calling spark.str_bool with (calling asc.is_sorted_asc)
        calling spark.println with calling spark.str_bool with (calling desc.is_sorted_desc)
        calling spark.println with calling spark.str_int with (calling tally.sum_of_squares with xs)
        calling dump with doubled
    ''', helpers=_DUMP_INT_LIST)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\n14\n6\n2\n4\n"


# ---------------------------------------------------------------------------
# Widened element types: the 2.2.0 signatures accept float, i64 and string lists
# ---------------------------------------------------------------------------

#: Printers for the element types the widened signatures accept.
_WIDENED_DUMP = """
weave dump_float with xs as list of float into void:
    for x in xs:
        calling spark.println with calling spark.str_float with x

weave dump_i64 with xs as list of i64 into void:
    for x in xs:
        calling spark.println with "{x}"

weave dump_words with xs as list of string into void:
    for x in xs:
        calling spark.println with x
"""


def test_widened_float_sum_and_mean_keep_the_fraction():
    """``tally.sum``/``tally.mean`` over ``list of float`` do not truncate."""
    res = _run_main('''
        var xs as list of float is [1.0, 2.0]
        calling spark.println with calling spark.str_float with (calling tally.sum with xs)
        calling spark.println with calling spark.str_float with (calling xs.sum)
        calling spark.println with calling spark.str_float with (calling tally.mean with xs)
        calling spark.println with calling spark.str_float with (calling xs.mean)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n3\n1.5\n1.5\n"


def test_widened_i64_reductions_keep_64_bit_values():
    """``tally.sum``/``max_val``/``min_val`` on ``list of i64`` exceed 32 bits."""
    res = _run_main('''
        var xs as list of i64 is [5000000000, 1, -5000000000]
        let module_sum as i64 is calling tally.sum with xs
        let method_sum as i64 is calling xs.sum
        let module_max as i64 is calling tally.max_val with xs
        let method_max as i64 is calling xs.max_val
        let module_min as i64 is calling tally.min_val with xs
        let method_min as i64 is calling xs.min_val
        calling spark.println with "{module_sum}"
        calling spark.println with "{method_sum}"
        calling spark.println with "{module_max}"
        calling spark.println with "{method_max}"
        calling spark.println with "{module_min}"
        calling spark.println with "{method_min}"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n1\n5000000000\n5000000000\n-5000000000\n-5000000000\n"


def test_widened_float_product_and_bounds():
    """``product``, ``max_val`` and ``min_val`` widen to ``list of float``."""
    res = _run_main('''
        var xs as list of float is [3.5, 1.25, 2.0]
        calling spark.println with calling spark.str_float with (calling tally.product with xs)
        calling spark.println with calling spark.str_float with (calling tally.max_val with xs)
        calling spark.println with calling spark.str_float with (calling xs.max_val)
        calling spark.println with calling spark.str_float with (calling tally.min_val with xs)
        calling spark.println with calling spark.str_float with (calling xs.min_val)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "8.75\n3.5\n3.5\n1.25\n1.25\n"


def test_widened_string_sort_asc_and_sort_desc():
    """``tally.sort_asc``/``sort_desc`` order ``list of string`` lexicographically."""
    res = _run_main('''
        var words as list of string is ["pear", "apple", "fig"]
        let asc as list of string is calling tally.sort_asc with words
        calling dump_words with asc
        calling spark.println with "|"
        let desc as list of string is calling tally.sort_desc with words
        calling dump_words with desc
        calling spark.println with "|"
        let method_asc as list of string is calling words.sort_asc
        calling dump_words with method_asc
    ''', helpers=_WIDENED_DUMP)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "apple\nfig\npear\n|\npear\nfig\napple\n|\napple\nfig\npear\n"


def test_widened_string_unique_and_contains():
    """``tally.unique`` (module and method) and ``tally.contains`` work on text."""
    res = _run_main('''
        var words as list of string is ["b", "a", "b", "c"]
        let module_unique as list of string is calling tally.unique with words
        calling dump_words with module_unique
        calling spark.println with "|"
        let method_unique as list of string is calling words.unique
        calling dump_words with method_unique
        calling spark.println with "|"
        calling spark.println with calling spark.str_bool with (calling tally.contains with words, "a")
        calling spark.println with calling spark.str_bool with (calling tally.contains with words, "z")
    ''', helpers=_WIDENED_DUMP)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "b\na\nc\n|\nb\na\nc\n|\ntrue\nfalse\n"


def test_widened_string_bounds_via_method_and_module():
    """``max_val``/``min_val`` order strings through the same ``Ordered`` path."""
    res = _run_main('''
        var words as list of string is ["pear", "apple", "fig"]
        calling spark.println with (calling words.max_val)
        calling spark.println with (calling words.min_val)
        calling spark.println with (calling tally.max_val with words)
        calling spark.println with (calling tally.min_val with words)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "pear\napple\npear\napple\n"
