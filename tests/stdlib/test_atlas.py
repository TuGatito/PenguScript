#!/usr/bin/env python3
"""End-to-end tests for ``std.atlas`` (Chunk 4 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.atlas`` is the ``map of K to V`` module.  Its headline change in 2.1.0 is
that ``keys_sorted``/``values_sorted`` are **generic through a user-extensible
concept**: ``concept Ordered shard T`` declares ``cmp``, the module binds it for
``int``/``i32``/``i64``/``float``/``f32``/``f64``/``string``, and a user type
extends the order by importing atlas and binding the concept with the
*unqualified* ``bind MyType with Ordered:`` form (the qualified
``bind MyType with atlas.Ordered:`` does not compile).  These tests pin the
generic sorters, the numeric reductions, the concrete ``string`` filters, the
0.15.0 compatibility wrappers and a custom ``seal``/``rune`` key.

The compiler only registers a small set of primitive names for ``bind``, so
``u8``..``u64``, ``usize``, ``isize`` and ``char`` cannot implement ``Ordered``
(``E0004``); sorting for those key/value types is deliberately out of scope and
is not exercised here.

A ``map`` parameter is passed by value, so the module-level ``void`` mutators
(``map_put``, ``clear_ss``, ...) cannot change the caller's map.  The suite
therefore drives mutation through the method forms (``calling m.put``,
``calling m.clear``, ``calling m.update``) and documents the module-form
limitation in exactly one test instead of asserting the wrappers mutate.

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
    with tempfile.TemporaryDirectory(prefix="pengu_atlas_") as td:
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

#: Prints one ``int`` per line for a ``list of int``.
_DUMP_INTS = """
weave dump_ints with xs as list of int into void:
    for v in xs:
        calling spark.println with calling spark.str_int with v
"""

#: Prints one ``string`` per line for a ``list of string``.
_DUMP_STRINGS = """
weave dump_strings with xs as list of string into void:
    for v in xs:
        calling spark.println with v
"""

#: Prints one ``float`` per line with ``%g`` formatting.
_DUMP_FLOATS = """
weave dump_floats with xs as list of float into void:
    for v in xs:
        calling spark.println with calling spark.str_float with v
"""

#: Prints one ``i64`` per line, converted to ``int`` for formatting.
_DUMP_I64S = """
weave dump_i64s with xs as list of i64 into void:
    for v in xs:
        calling spark.println with calling spark.str_int with (v to int)
"""

#: Prints ``key=value`` for a ``map of string to int`` in sorted key order.
_DUMP_STR_INT = """
weave dump_str_int with mm as map of string to int into void:
    var ks as list of string is calling mm.keys_sorted
    for k in ks:
        calling spark.println with "{k}={mm at k}"
"""

#: A user ``seal`` implementing the ``Ordered`` concept through an unqualified bind.
_SEAL_USER = """
seal UserId as int

bind UserId with Ordered:
    weave cmp with other as UserId into int:
        var me as int is (essence of self) to int
        var you as int is other to int
        if me > you:
            return 1
        if me < you:
            return -1
        return 0
"""

#: A user ``rune`` implementing ``Ordered`` through an unqualified bind.
_RUNE_POINT = """
rune Point derive Par, Vinculum:
    id as int

bind Point with Ordered:
    weave cmp with other as Point into int:
        var me as int is (essence of self).id
        var you as int is other.id
        if me > you:
            return 1
        if me < you:
            return -1
        return 0
"""


def _run_main(body: str, helpers: str = "",
              imports: str = "") -> subprocess.CompletedProcess:
    """Runs ``body`` as the body of a ``main`` that imports spark and atlas."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = ["import std.spark", "import std.atlas"]
    if imports:
        sections.append(textwrap.dedent(imports).strip("\n"))
    if helpers:
        sections += ["", textwrap.dedent(helpers).strip("\n")]
    sections += ["", "weave main into int:", body, "    return 0", ""]
    return run_pengu("\n".join(sections))


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``atlas.ATLAS_VERSION`` reports the migrated module version ``2.1.0``."""
    res = _run_main("calling spark.println with atlas.ATLAS_VERSION")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.1.0\n"


# ---------------------------------------------------------------------------
# keys_sorted: generic through the Ordered concept
# ---------------------------------------------------------------------------

def test_keys_sorted_sorts_string_keys():
    """``keys_sorted`` orders ``string`` keys lexicographically."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "pear", 3
        calling m.put with "apple", 1
        calling m.put with "mango", 2
        var ks as list of string is calling m.keys_sorted
        calling dump_strings with ks
    ''', helpers=_DUMP_STRINGS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "apple\nmango\npear\n"


def test_keys_sorted_sorts_int_keys():
    """``keys_sorted`` orders ``int`` keys numerically, not lexicographically."""
    res = _run_main('''
        var m as map of int to string is map of int to string
        calling m.put with 30, "c"
        calling m.put with 10, "a"
        calling m.put with 20, "b"
        var ks as list of int is calling m.keys_sorted
        calling dump_ints with ks
    ''', helpers=_DUMP_INTS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\n20\n30\n"


def test_keys_sorted_sorts_i64_keys():
    """The ``i64`` bind makes ``keys_sorted`` available for 64-bit keys."""
    res = _run_main('''
        var m as map of i64 to string is map of i64 to string
        calling m.put with (30 to i64), "c"
        calling m.put with (10 to i64), "a"
        calling m.put with (20 to i64), "b"
        var ks as list of i64 is calling m.keys_sorted
        calling dump_i64s with ks
    ''', helpers=_DUMP_I64S)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\n20\n30\n"


def test_keys_sorted_sorts_float_keys():
    """The ``float`` bind orders fractional keys by numeric value."""
    res = _run_main('''
        var m as map of float to string is map of float to string
        calling m.put with 2.5, "b"
        calling m.put with 1.5, "a"
        calling m.put with 3.5, "c"
        var ks as list of float is calling m.keys_sorted
        calling dump_floats with ks
    ''', helpers=_DUMP_FLOATS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1.5\n2.5\n3.5\n"


def test_keys_sorted_of_module_function_sorts_string_keys():
    """``atlas.keys_sorted_of`` is the generic module form and also takes strings."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "pear", 3
        calling m.put with "apple", 1
        calling m.put with "mango", 2
        var ks as list of string is calling atlas.keys_sorted_of with m
        calling dump_strings with ks
    ''', helpers=_DUMP_STRINGS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "apple\nmango\npear\n"


def test_keys_sorted_of_empty_map_is_empty():
    """Sorting the keys of an empty map gives an empty list, never an error."""
    res = _run_main('''
        var e as map of string to int is map of string to int
        var ks as list of string is calling e.keys_sorted
        calling spark.println with calling spark.str_int with (calling ks.len)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_keys_sorted_does_not_mutate_the_receiver():
    """``keys_sorted`` builds a new list; the receiver keeps its entries."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "b", 2
        calling m.put with "a", 1
        var ks as list of string is calling m.keys_sorted
        var first as string is ks at 0
        var bval as int is m at "b"
        calling spark.println with first
        calling spark.println with calling spark.str_int with (calling m.size)
        calling spark.println with calling spark.str_int with bval
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a\n2\n2\n"


# ---------------------------------------------------------------------------
# values_sorted: generic through the Ordered concept
# ---------------------------------------------------------------------------

def test_values_sorted_sorts_int_values():
    """``values_sorted`` orders ``int`` values ascending."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 30
        calling m.put with "b", 10
        calling m.put with "c", 20
        var vs as list of int is calling m.values_sorted
        calling dump_ints with vs
    ''', helpers=_DUMP_INTS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\n20\n30\n"


def test_values_sorted_sorts_string_values():
    """``values_sorted`` orders ``string`` values lexicographically."""
    res = _run_main('''
        var m as map of string to string is map of string to string
        calling m.put with "k1", "pear"
        calling m.put with "k2", "apple"
        var vs as list of string is calling m.values_sorted
        calling dump_strings with vs
    ''', helpers=_DUMP_STRINGS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "apple\npear\n"


def test_values_sorted_sorts_float_values():
    """``values_sorted`` orders ``float`` values by numeric value."""
    res = _run_main('''
        var m as map of string to float is map of string to float
        calling m.put with "k1", 2.5
        calling m.put with "k2", 1.5
        var vs as list of float is calling m.values_sorted
        calling dump_floats with vs
    ''', helpers=_DUMP_FLOATS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1.5\n2.5\n"


def test_values_sorted_of_module_function_sorts_int_values():
    """``atlas.values_sorted_of`` is the generic module form of ``values_sorted``."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 30
        calling m.put with "b", 10
        calling m.put with "c", 20
        var vs as list of int is calling atlas.values_sorted_of with m
        calling dump_ints with vs
    ''', helpers=_DUMP_INTS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\n20\n30\n"


# ---------------------------------------------------------------------------
# Numeric reductions
# ---------------------------------------------------------------------------

def test_sum_values_adds_int_values():
    """``sum_values`` adds every value of an ``int``-valued map."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        calling spark.println with calling spark.str_int with (calling m.sum_values)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "45\n"


def test_sum_values_of_empty_map_is_zero():
    """``sum_values`` of an empty map is the additive identity ``0``."""
    res = _run_main('''
        var e as map of string to int is map of string to int
        calling spark.println with calling spark.str_int with (calling e.sum_values)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_sum_values_of_float_map_stays_float():
    """The numeric block keeps ``float`` values fractional, with no truncation."""
    res = _run_main('''
        var m as map of string to float is map of string to float
        calling m.put with "a", 1.5
        calling m.put with "b", 2.25
        var total as float is calling m.sum_values
        calling spark.println with calling spark.str_float with total
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3.75\n"


def test_sum_values_filtered_honours_the_closed_range():
    """``sum_values_filtered`` includes both bounds and ignores the rest."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        var inside as int is calling m.sum_values_filtered with 10, 25
        var outside as int is calling m.sum_values_filtered with 100, 200
        calling spark.println with calling spark.str_int with inside
        calling spark.println with calling spark.str_int with outside
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "40\n0\n"


def test_max_and_min_value():
    """``max_value``/``min_value`` return the extremes of the values."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        calling spark.println with calling spark.str_int with (calling m.max_value)
        calling spark.println with calling spark.str_int with (calling m.min_value)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "25\n5\n"


def test_max_and_min_value_of_empty_map_are_zero():
    """``max_value``/``min_value`` of an empty map collapse to ``0``."""
    res = _run_main('''
        var e as map of string to int is map of string to int
        calling spark.println with calling spark.str_int with (calling e.max_value)
        calling spark.println with calling spark.str_int with (calling e.min_value)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n0\n"


def test_values_in_range_accepts_and_rejects():
    """``values_in_range`` is inclusive and short-circuits on an outlier."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        var inside as bool is calling m.values_in_range with 5, 25
        var outside as bool is calling m.values_in_range with 10, 25
        calling spark.println with calling spark.str_bool with inside
        calling spark.println with calling spark.str_bool with outside
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\n"


def test_filter_values_range_keeps_only_the_range():
    """``filter_values_range`` returns the matching entries as a new map."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        var sub as map of string to int is calling m.filter_values_range with 10, 25
        calling dump_str_int with sub
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "b=15\nc=25\n"


def test_all_values_positive_and_any_value_negative():
    """The two value predicates read the sign of every value."""
    res = _run_main('''
        var pos as map of string to int is map of string to int
        calling pos.put with "a", 1
        calling pos.put with "b", 2
        var mixed as map of string to int is map of string to int
        calling mixed.put with "a", -1
        calling mixed.put with "b", 2
        calling spark.println with calling spark.str_bool with (calling pos.all_values_positive)
        calling spark.println with calling spark.str_bool with (calling mixed.all_values_positive)
        calling spark.println with calling spark.str_bool with (calling mixed.any_value_negative)
        calling spark.println with calling spark.str_bool with (calling pos.any_value_negative)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\ntrue\nfalse\n"


def test_count_if_value_positive_and_negative():
    """The two counting predicates split the values by sign."""
    res = _run_main('''
        var pos as map of string to int is map of string to int
        calling pos.put with "a", 5
        calling pos.put with "b", 15
        calling pos.put with "c", 25
        var mixed as map of string to int is map of string to int
        calling mixed.put with "a", -5
        calling mixed.put with "b", 3
        calling spark.println with calling spark.str_int with (calling pos.count_if_value_positive)
        calling spark.println with calling spark.str_int with (calling mixed.count_if_value_negative)
        calling spark.println with calling spark.str_int with (calling mixed.count_if_value_positive)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n1\n1\n"


def test_map_values_transformations():
    """``map_values_double``/``negate``/``scale`` build new transformed maps."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        var dbl as map of string to int is calling m.map_values_double
        var neg as map of string to int is calling m.map_values_negate
        var sca as map of string to int is calling m.map_values_scale with 2
        calling dump_str_int with dbl
        calling spark.println with "|"
        calling dump_str_int with neg
        calling spark.println with "|"
        calling dump_str_int with sca
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a=10\nb=30\nc=50\n|\na=-5\nb=-15\nc=-25\n|\na=10\nb=30\nc=50\n"


# ---------------------------------------------------------------------------
# String-key / string-value filters
# ---------------------------------------------------------------------------

def test_filter_keys_contains_keeps_matching_keys():
    """``filter_keys_contains`` keeps the keys holding the substring."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "apple", 10
        calling m.put with "apricot", 30
        calling m.put with "banana", 20
        var sub as map of string to int is calling m.filter_keys_contains with "ap"
        calling dump_str_int with sub
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "apple=10\napricot=30\n"


def test_filter_keys_startswith_and_no_match():
    """``filter_keys_startswith`` keeps prefixes and yields an empty map on a miss."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "apple", 10
        calling m.put with "apricot", 30
        calling m.put with "banana", 20
        var sub as map of string to int is calling m.filter_keys_startswith with "ban"
        var none as map of string to int is calling m.filter_keys_startswith with "zzz"
        calling dump_str_int with sub
        calling spark.println with calling spark.str_int with (calling none.size)
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "banana=20\n0\n"


def test_filter_values_contains_on_a_string_map():
    """``filter_values_contains`` keeps the entries whose value holds the substring."""
    res = _run_main('''
        var m as map of string to string is map of string to string
        calling m.put with "one", "uno"
        calling m.put with "two", "dos"
        calling m.put with "three", "tres"
        var f as map of string to string is calling m.filter_values_contains with "s"
        var ks as list of string is calling f.keys_sorted
        calling dump_strings with ks
    ''', helpers=_DUMP_STRINGS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "three\ntwo\n"


def test_filter_values_contains_with_int_keys():
    """The concrete ``map of int to string`` block backs value substring filtering."""
    res = _run_main('''
        var m as map of int to string is map of int to string
        calling m.put with 1, "uno"
        calling m.put with 2, "dos"
        var f as map of int to string is calling m.filter_values_contains with "os"
        var v as string is f at 2
        calling spark.println with calling spark.str_int with (calling f.size)
        calling spark.println with v
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\ndos\n"


def test_map_filter_values_contains_infers_the_key_type():
    """The generic module function infers ``K`` instead of needing a concrete block."""
    res = _run_main('''
        var m as map of int to string is map of int to string
        calling m.put with 1, "uno"
        calling m.put with 2, "dos"
        var f as map of int to string is calling atlas.map_filter_values_contains with m, "un"
        var v as string is f at 1
        calling spark.println with calling spark.str_int with (calling f.size)
        calling spark.println with v
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\nuno\n"


# ---------------------------------------------------------------------------
# count_true / count_false on non-string keys (the boolean block's second shard)
# ---------------------------------------------------------------------------

def test_count_true_and_false_on_an_int_keyed_map():
    """``count_true``/``count_false`` work on a ``map of int to bool``."""
    res = _run_main('''
        var m as map of int to bool is map of int to bool
        calling m.put with 1, true
        calling m.put with 2, false
        calling m.put with 3, true
        calling m.put with 4, false
        calling spark.println with calling spark.str_int with (calling m.count_true)
        calling spark.println with calling spark.str_int with (calling m.count_false)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n2\n"


def test_count_true_and_false_compat_wrappers():
    """The 0.15.0 ``count_true_sb``/``count_false_sb`` wrappers agree."""
    res = _run_main('''
        var m as map of string to bool is map of string to bool
        calling m.put with "a", true
        calling m.put with "b", false
        calling m.put with "c", true
        var t as int is calling atlas.count_true_sb with m
        var f as int is calling atlas.count_false_sb with m
        calling spark.println with calling spark.str_int with t
        calling spark.println with calling spark.str_int with f
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\n1\n"


# ---------------------------------------------------------------------------
# 0.15.0 compatibility wrappers
# ---------------------------------------------------------------------------

def test_size_and_is_empty_ss():
    """``size_ss``/``is_empty_ss`` forward to the generic methods."""
    res = _run_main('''
        var m as map of string to string is map of string to string
        calling m.put with "a", "x"
        calling m.put with "b", "y"
        var e as map of string to string is map of string to string
        var n as int is calling atlas.size_ss with m
        var not_empty as bool is calling atlas.is_empty_ss with m
        var empty as bool is calling atlas.is_empty_ss with e
        calling spark.println with calling spark.str_int with n
        calling spark.println with calling spark.str_bool with not_empty
        calling spark.println with calling spark.str_bool with empty
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\nfalse\ntrue\n"


def test_get_or_has_key_and_get_safe_ss():
    """``get_or_ss`` falls back, ``has_key_ss`` tests presence, ``get_safe_ss`` wraps."""
    res = _run_main('''
        var m as map of string to string is map of string to string
        calling m.put with "a", "x"
        var hit as string is calling atlas.get_or_ss with m, "a", "zz"
        var miss as string is calling atlas.get_or_ss with m, "q", "zz"
        var has as bool is calling atlas.has_key_ss with m, "a"
        var got as maybe string is calling atlas.get_safe_ss with m, "q"
        var got2 as maybe string is calling atlas.get_safe_ss with m, "a"
        calling spark.println with hit
        calling spark.println with miss
        calling spark.println with calling spark.str_bool with has
        calling spark.println with (got or else "none")
        calling spark.println with (got2 or else "none")
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x\nzz\ntrue\nnone\nx\n"


def test_merge_ii():
    """``merge_ii`` combines two int maps with the right map winning collisions."""
    res = _run_main('''
        var a as map of int to int is map of int to int
        calling a.put with 1, 10
        var b as map of int to int is map of int to int
        calling b.put with 1, 99
        calling b.put with 2, 20
        var m as map of int to int is calling atlas.merge_ii with a, b
        var v1 as int is m at 1
        var v2 as int is m at 2
        calling spark.println with calling spark.str_int with v1
        calling spark.println with calling spark.str_int with v2
        calling spark.println with calling spark.str_int with (calling m.size)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "99\n20\n2\n"


def test_merge_and_merge_keep_left():
    """``merge`` lets the right map win; ``merge_keep_left`` keeps the left value."""
    res = _run_main('''
        var a as map of string to int is map of string to int
        calling a.put with "x", 1
        calling a.put with "y", 2
        var b as map of string to int is map of string to int
        calling b.put with "y", 99
        calling b.put with "z", 3
        var mg as map of string to int is calling atlas.merge with a, b
        var ml as map of string to int is calling atlas.merge_keep_left with a, b
        calling dump_str_int with mg
        calling spark.println with "|"
        calling dump_str_int with ml
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x=1\ny=99\nz=3\n|\nx=1\ny=2\nz=3\n"


def test_from_lists_sf_and_get_or_sf():
    """``from_lists_sf`` zips keys and values; ``get_or_sf`` reads them back."""
    res = _run_main('''
        var ks as list of string is ["k1", "k2"]
        var vs as list of float is [1.5, 2.5]
        var m as map of string to float is calling atlas.from_lists_sf with ks, vs
        var got as float is calling atlas.get_or_sf with m, "k1", 0.0
        var miss as float is calling atlas.get_or_sf with m, "nope", -1.0
        calling spark.println with calling spark.str_float with got
        calling spark.println with calling spark.str_float with miss
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1.5\n-1\n"


def test_keys_sorted_ss():
    """``keys_sorted_ss`` sorts the keys of a ``map of string to string``."""
    res = _run_main('''
        var m as map of string to string is map of string to string
        calling m.put with "b", "y"
        calling m.put with "a", "x"
        var ks as list of string is calling atlas.keys_sorted_ss with m
        calling dump_strings with ks
    ''', helpers=_DUMP_STRINGS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a\nb\n"


def test_values_sorted_sf():
    """``values_sorted_sf`` sorts the float values of a string-keyed map."""
    res = _run_main('''
        var m as map of string to float is map of string to float
        calling m.put with "k1", 2.5
        calling m.put with "k2", 1.5
        var vs as list of float is calling atlas.values_sorted_sf with m
        calling dump_floats with vs
    ''', helpers=_DUMP_FLOATS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1.5\n2.5\n"


def test_keys_and_values_sorted_ii():
    """``keys_sorted_ii``/``values_sorted_ii`` sort both sides of an int map."""
    res = _run_main('''
        var m as map of int to int is map of int to int
        calling m.put with 30, 3
        calling m.put with 10, 1
        calling m.put with 20, 2
        var ks as list of int is calling atlas.keys_sorted_ii with m
        var vs as list of int is calling atlas.values_sorted_ii with m
        calling dump_ints with ks
        calling spark.println with "|"
        calling dump_ints with vs
    ''', helpers=_DUMP_INTS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\n20\n30\n|\n1\n2\n3\n"


def test_clone_ss():
    """``clone_ss`` copies the entries into an independent map."""
    res = _run_main('''
        var m as map of string to string is map of string to string
        calling m.put with "a", "x"
        var c as map of string to string is calling atlas.clone_ss with m
        var n as int is calling atlas.size_ss with c
        var v as string is c at "a"
        calling spark.println with calling spark.str_int with n
        calling spark.println with v
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\nx\n"


# ---------------------------------------------------------------------------
# Generic module functions
# ---------------------------------------------------------------------------

def test_generic_map_query_functions():
    """The generic module queries read any key/value combination."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 5
        calling m.put with "b", 15
        calling m.put with "c", 25
        var n as int is calling atlas.map_size with m
        var empty as bool is calling atlas.map_is_empty with m
        var has as bool is calling atlas.map_has_key with m, "a"
        var missing as int is calling atlas.map_get_or with m, "zz", -1
        var ks as list of string is calling atlas.map_keys with m
        var vs as list of int is calling atlas.map_values with m
        var kso as list of string is calling atlas.keys_sorted_of with m
        var vso as list of int is calling atlas.values_sorted_of with m
        calling spark.println with calling spark.str_int with n
        calling spark.println with calling spark.str_bool with empty
        calling spark.println with calling spark.str_bool with has
        calling spark.println with calling spark.str_int with missing
        calling spark.println with calling spark.str_int with (calling ks.len)
        calling spark.println with calling spark.str_int with (calling vs.len)
        calling spark.println with (kso at 0)
        calling spark.println with calling spark.str_int with (vso at 0)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\nfalse\ntrue\n-1\n3\n3\na\n5\n"


def test_map_from_lists_generic():
    """``map_from_lists`` infers ``K`` and ``V`` from the parallel lists."""
    res = _run_main('''
        var ks as list of string is ["a", "b"]
        var vs as list of int is [1, 2]
        var m as map of string to int is calling atlas.map_from_lists with ks, vs
        calling dump_str_int with m
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a=1\nb=2\n"


def test_map_merge_all():
    """``map_merge_all`` folds every map in order, so the last value wins."""
    res = _run_main('''
        var a as map of string to int is map of string to int
        calling a.put with "x", 1
        var b as map of string to int is map of string to int
        calling b.put with "y", 2
        var c as map of string to int is map of string to int
        calling c.put with "x", 9
        var maps as list of map of string to int is [a, b, c]
        var m as map of string to int is calling atlas.map_merge_all with maps
        calling dump_str_int with m
    ''', helpers=_DUMP_STR_INT)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x=9\ny=2\n"


def test_from_pairs_and_entries():
    """``from_pairs`` builds from ``oracle.Pair`` values and ``entries`` reverses it."""
    res = _run_main('''
        var p1 as oracle.Pair of string and int with:
            set .first is "a"
            set .second is 1
        var p2 as oracle.Pair of string and int with:
            set .first is "b"
            set .second is 2
        var ps as list of oracle.Pair of string and int is [p1, p2]
        var m as map of string to int is calling atlas.from_pairs with ps
        calling dump_str_int with m
        var es as list of oracle.Pair of string and int is calling m.entries
        calling spark.println with calling spark.str_int with (calling es.len)
    ''', helpers=_DUMP_STR_INT, imports="import std.oracle")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a=1\nb=2\n2\n"


# ---------------------------------------------------------------------------
# Generic query and mutation methods
# ---------------------------------------------------------------------------

def test_method_queries_has_any_all_find_get_safe():
    """The membership helpers agree on present, absent and partial key sets."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 1
        calling m.put with "b", 2
        var some_keys as list of string is ["a", "b", "zz"]
        var all_keys as list of string is ["a", "b"]
        var no_keys as list of string is ["zz"]
        var any as bool is calling m.has_any_key with some_keys
        var all as bool is calling m.has_all_keys with all_keys
        var partial as bool is calling m.has_all_keys with some_keys
        var found as maybe string is calling m.find_key_by_value with 2
        var hit as maybe int is calling m.get_safe with "a"
        var miss as maybe int is calling m.get_safe with "zz"
        calling spark.println with calling spark.str_bool with any
        calling spark.println with calling spark.str_bool with all
        calling spark.println with calling spark.str_bool with partial
        calling spark.println with (found or else "none")
        calling spark.println with calling spark.str_int with (hit or else -1)
        calling spark.println with calling spark.str_int with (miss or else -1)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nfalse\nb\n1\n-1\n"


def test_method_mutation_put_update_remove_rename_clear():
    """The method forms mutate the receiver in place; the receiver is a ``ref to``."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 1
        calling m.put with "b", 2
        var initial_size as int is calling m.size
        var upd as bool is calling m.update with "a", 10
        var no_upd as bool is calling m.update with "z", 99
        var a_val as int is m at "a"
        var rem as bool is calling m.remove with "b"
        var no_rem as bool is calling m.remove with "zz"
        var renamed as bool is calling m.rename_key with "a", "alpha"
        var alpha_val as int is m at "alpha"
        calling spark.println with calling spark.str_int with initial_size
        calling spark.println with calling spark.str_bool with upd
        calling spark.println with calling spark.str_bool with no_upd
        calling spark.println with calling spark.str_int with a_val
        calling spark.println with calling spark.str_bool with rem
        calling spark.println with calling spark.str_bool with no_rem
        calling spark.println with calling spark.str_bool with renamed
        calling spark.println with calling spark.str_int with alpha_val
        calling m.clear
        calling spark.println with calling spark.str_int with (calling m.size)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\ntrue\nfalse\n10\ntrue\nfalse\ntrue\n10\n0\n"


def test_clone_copy_and_is_equal():
    """``clone``/``copy`` are independent and ``is_equal`` compares by content."""
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling m.put with "a", 1
        var c as map of string to int is calling m.clone
        var d as map of string to int is calling m.copy
        calling m.put with "b", 2
        var same_as_clone as bool is calling m.is_equal with c
        var clone_eq_copy as bool is calling c.is_equal with d
        var clone_size as int is calling c.size
        calling spark.println with calling spark.str_bool with same_as_clone
        calling spark.println with calling spark.str_bool with clone_eq_copy
        calling spark.println with calling spark.str_int with clone_size
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\ntrue\n1\n"


# ---------------------------------------------------------------------------
# The custom-type generalisation (headline feature)
# ---------------------------------------------------------------------------

def test_custom_seal_type_sorts_through_ordered():
    """A user ``seal`` with an unqualified ``bind ... with Ordered`` sorts keys."""
    res = _run_main('''
        var m as map of UserId to string is map of UserId to string
        calling m.put with (7 to UserId), "seven"
        calling m.put with (3 to UserId), "three"
        calling m.put with (5 to UserId), "five"
        var ks as list of UserId is calling m.keys_sorted
        var k0 as UserId is ks at 0
        var k1 as UserId is ks at 1
        var k2 as UserId is ks at 2
        var first_val as string is m at k0
        calling spark.println with "{k0 to int}|{k1 to int}|{k2 to int}"
        calling spark.println with first_val
    ''', helpers=_SEAL_USER)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3|5|7\nthree\n"


def test_custom_rune_type_sorts_through_ordered():
    """A user ``rune`` with a ``cmp`` body sorts keys and string values."""
    res = _run_main('''
        var m as map of Point to string is map of Point to string
        var a as Point with:
            set .id is 20
        var b as Point with:
            set .id is 10
        calling m.put with a, "twenty"
        calling m.put with b, "ten"
        var ks as list of Point is calling m.keys_sorted
        var vs as list of string is calling m.values_sorted
        var first as Point is ks at 0
        calling spark.println with calling spark.str_int with first.id
        calling dump_strings with vs
    ''', helpers=_RUNE_POINT + _DUMP_STRINGS)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10\nten\ntwenty\n"


def test_other_primitive_binds_sort():
    """The ``i32``, ``f32`` and ``f64`` binds also drive ``keys_sorted``."""
    res = _run_main('''
        var mi as map of i32 to int is map of i32 to int
        calling mi.put with (2 to i32), 20
        calling mi.put with (1 to i32), 10
        var iks as list of i32 is calling mi.keys_sorted
        var ik0 as i32 is iks at 0

        var mf as map of f32 to int is map of f32 to int
        calling mf.put with (2.5 to f32), 20
        calling mf.put with (1.5 to f32), 10
        var fks as list of f32 is calling mf.keys_sorted
        var fk0 as f32 is fks at 0

        var md as map of f64 to int is map of f64 to int
        calling md.put with (2.5 to f64), 20
        calling md.put with (1.5 to f64), 10
        var dks as list of f64 is calling md.keys_sorted
        var dk0 as f64 is dks at 0

        calling spark.println with "{ik0 to int}"
        calling spark.println with "{fk0 to float}"
        calling spark.println with "{dk0 to float}"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n1.5\n1.5\n"


# ---------------------------------------------------------------------------
# Known limitation: module-level mutators receive the map by value
# ---------------------------------------------------------------------------

def test_module_form_map_put_cannot_mutate_the_callers_map():
    """Documents the known by-value limitation of the module mutators.

    A ``map`` **parameter** is passed as a C struct copy, so ``atlas.map_put``
    writes into the callee's copy: the caller's map keeps length ``0``.  This
    test pins the current behaviour (it is not a desirable contract); callers
    must use the method form ``calling m.put`` when they need real mutation.
    """
    res = _run_main('''
        var m as map of string to int is map of string to int
        calling atlas.map_put with m, "a", 1
        calling spark.println with calling spark.str_int with (calling m.size)
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"
