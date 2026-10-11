#!/usr/bin/env python3
"""End-to-end tests for ``std.coven`` (Chunk 4 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the emitted C: the
contract under test is behaviour, and the compiler is free to change how it gets
there.

``coven`` is the set module.  Revision 2.2.0 keeps the two legacy concrete runes
``SetString`` and ``SetInt`` (both backed by a ``map of string to int``) and adds
a generic ``rune Set shard T`` backed by ``map of T to int``.  The generic rune
deliberately has no ``Set.empty`` ritual -- a type-qualified generic ritual
miscompiles -- so generic sets are built with the module constructors
``coven.make_set of T`` / ``coven.from_items_set of T with xs`` or with the
concrete ``new_int_set`` / ``new_string_set`` / ``new_float_set`` /
``new_bool_set`` / ``new_char_set`` constructors.  The ``of T`` is mandatory:
the element type is never inferred (``E0005``).  The legacy static rituals
(``SetString.empty``, ``SetString.from_items``, ``SetInt.empty``,
``SetInt.from_items``) and the module-level ``empty_set_*`` / ``from_list_*``
helpers stay.

A set owns its backing map, so each program releases it with ``banish s.items``
(never ``banish s``): the runtime has no cleanup hook for user runes.  Sets
received as parameters are borrowed and are never released by these methods.

The suite is deliberately self-contained.  Each test writes its own throw-away
program into a temporary directory and runs it with the binary cache disabled, so
no test can observe another test's state and a failure names exactly one program.

The compiler is invoked through the repository's own CLI (``pengu_project.py``):
a source checkout has no installed ``pengu`` binary, and the CLI is what CI runs.
``-q`` suppresses the build progress lines so the assertions can compare the
program's output byte for byte.  A generic ``Set of T`` can make the development
TCC build fall back to the configured C compiler; that prints a note on stderr
and is harmless, which is why no test asserts an empty stderr.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: Three levels up: tests/stdlib/test_coven.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script; returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_coven_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(cmd, capture_output=True, text=True,
                              input=stdin_text, timeout=timeout, cwd=str(REPO))


def coven_program(body: str, prelude: str = "") -> str:
    """Wraps ``body`` as the statements of a ``main`` that imports ``std.coven``.

    The body is dedented, so each test can indent it to match its own block.  An
    optional ``prelude`` is emitted before ``main`` (a custom ``rune`` needs to be
    declared at module scope, not inside a function).
    """
    statements = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    head = textwrap.dedent(prelude).strip("\n")
    if head:
        head += "\n\n"
    return (
        "import std.spark\n"
        "import std.coven\n"
        "\n"
        f"{head}"
        "weave main into int:\n"
        f"{statements}\n"
        "    return 0\n"
    )


def run_coven(body: str, prelude: str = "") -> subprocess.CompletedProcess:
    """Compiles and runs a ``coven`` program built from ``body``."""
    return run_pengu(coven_program(body, prelude))


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_coven_version_is_2_2_0():
    """The migrated module reports COVEN_VERSION 2.2.0."""
    res = run_coven('calling spark.println with coven.COVEN_VERSION')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.2.0\n"


# ---------------------------------------------------------------------------
# Legacy SetString
# ---------------------------------------------------------------------------


def test_set_string_add_deduplicates_and_reports_membership():
    """A new SetString is empty and stores a repeated element once."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        let start_empty as bool is calling s.is_empty
        calling s.add with "ada"
        calling s.add with "ada"
        let n as int is calling s.len
        let has as bool is calling s.contains with "ada"
        let missing as bool is calling s.contains with "grace"
        let start_s as string is calling spark.str_bool with start_empty
        let has_s as string is calling spark.str_bool with has
        let missing_s as string is calling spark.str_bool with missing
        calling spark.println with "{start_s}|{n}|{has_s}|{missing_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|1|true|false\n"


def test_set_string_remove_reports_membership_and_len():
    """remove returns true once, then false, and shrinks the set."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        calling s.add with "a"
        calling s.add with "b"
        let first as bool is calling s.remove with "a"
        let again as bool is calling s.remove with "a"
        let after as int is calling s.len
        let last as bool is calling s.remove with "b"
        let empty as bool is calling s.is_empty
        let first_s as string is calling spark.str_bool with first
        let again_s as string is calling spark.str_bool with again
        let last_s as string is calling spark.str_bool with last
        let empty_s as string is calling spark.str_bool with empty
        calling spark.println with "{first_s}|{again_s}|{after}|{last_s}|{empty_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|false|1|true|true\n"


def test_set_string_clear_drops_every_element():
    """clear leaves the set empty while keeping the receiver usable."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        calling s.add with "x"
        calling s.add with "y"
        let before as int is calling s.len
        calling s.clear
        let after as int is calling s.len
        let empty as bool is calling s.is_empty
        let empty_s as string is calling spark.str_bool with empty
        calling spark.println with "{before}|{after}|{empty_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|0|true\n"


def test_set_string_union_merges_and_intersect_keeps_common():
    """union merges both operands and intersect keeps only shared members."""
    res = run_coven('''
        var a as SetString is calling coven.new_set_string
        var b as SetString is calling coven.new_set_string
        calling a.add with "x"
        calling a.add with "y"
        calling b.add with "y"
        calling b.add with "z"
        var u as SetString is calling a.union with b
        var i as SetString is calling a.intersect with b
        let ulen as int is calling u.len
        let ux as bool is calling u.contains with "x"
        let uz as bool is calling u.contains with "z"
        let ilen as int is calling i.len
        let iy as bool is calling i.contains with "y"
        let ix as bool is calling i.contains with "x"
        let ux_s as string is calling spark.str_bool with ux
        let uz_s as string is calling spark.str_bool with uz
        let iy_s as string is calling spark.str_bool with iy
        let ix_s as string is calling spark.str_bool with ix
        calling spark.println with "{ulen}|{ux_s}|{uz_s}|{ilen}|{iy_s}|{ix_s}"
        banish u.items
        banish i.items
        banish a.items
        banish b.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3|true|true|1|true|false\n"


def test_set_string_difference_and_symmetric_difference():
    """difference keeps the left side only; symmetric_difference keeps the xor."""
    res = run_coven('''
        var a as SetString is calling coven.new_set_string
        var b as SetString is calling coven.new_set_string
        calling a.add with "x"
        calling a.add with "y"
        calling b.add with "y"
        calling b.add with "z"
        var d as SetString is calling a.difference with b
        var x as SetString is calling a.symmetric_difference with b
        let dlen as int is calling d.len
        let dx as bool is calling d.contains with "x"
        let dy as bool is calling d.contains with "y"
        let xlen as int is calling x.len
        let xx as bool is calling x.contains with "x"
        let xz as bool is calling x.contains with "z"
        let xy as bool is calling x.contains with "y"
        let dx_s as string is calling spark.str_bool with dx
        let dy_s as string is calling spark.str_bool with dy
        let xx_s as string is calling spark.str_bool with xx
        let xz_s as string is calling spark.str_bool with xz
        let xy_s as string is calling spark.str_bool with xy
        calling spark.println with "{dlen}|{dx_s}|{dy_s}|{xlen}|{xx_s}|{xz_s}|{xy_s}"
        banish d.items
        banish x.items
        banish a.items
        banish b.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1|true|false|2|true|true|false\n"


def test_set_string_subset_superset_and_disjoint():
    """The subset/superset/disjoint predicates classify shared membership."""
    res = run_coven('''
        var a as SetString is calling coven.new_set_string
        var b as SetString is calling coven.new_set_string
        var c as SetString is calling coven.new_set_string
        var e as SetString is calling SetString.empty
        calling a.add with "x"
        calling b.add with "x"
        calling b.add with "y"
        calling c.add with "z"
        let sub as bool is calling a.is_subset with b
        let sup as bool is calling b.is_superset with a
        let rev as bool is calling b.is_subset with a
        let esub as bool is calling e.is_subset with a
        let shared as bool is calling a.is_disjoint with b
        let apart as bool is calling a.is_disjoint with c
        let sub_s as string is calling spark.str_bool with sub
        let sup_s as string is calling spark.str_bool with sup
        let rev_s as string is calling spark.str_bool with rev
        let esub_s as string is calling spark.str_bool with esub
        let shared_s as string is calling spark.str_bool with shared
        let apart_s as string is calling spark.str_bool with apart
        calling spark.println with "{sub_s}|{sup_s}|{rev_s}|{esub_s}|{shared_s}|{apart_s}"
        banish a.items
        banish b.items
        banish c.items
        banish e.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|false|true|false|true\n"


def test_set_string_equals_ignores_insertion_order():
    """equals compares membership, so insertion order does not matter."""
    res = run_coven('''
        var a as SetString is calling coven.new_set_string
        var b as SetString is calling coven.new_set_string
        var c as SetString is calling coven.new_set_string
        var e1 as SetString is calling SetString.empty
        var e2 as SetString is calling SetString.empty
        calling a.add with "x"
        calling a.add with "y"
        calling b.add with "y"
        calling b.add with "x"
        calling c.add with "x"
        let same as bool is calling a.equals with b
        let diff as bool is calling a.equals with c
        let empties as bool is calling e1.equals with e2
        let same_s as string is calling spark.str_bool with same
        let diff_s as string is calling spark.str_bool with diff
        let empties_s as string is calling spark.str_bool with empties
        calling spark.println with "{same_s}|{diff_s}|{empties_s}"
        banish a.items
        banish b.items
        banish c.items
        banish e1.items
        banish e2.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|false|true\n"


def test_set_string_clone_is_independent():
    """Adding to a clone leaves the original set untouched."""
    res = run_coven('''
        var a as SetString is calling coven.new_set_string
        calling a.add with "a"
        var c as SetString is calling a.clone
        calling c.add with "b"
        let alen as int is calling a.len
        let clen as int is calling c.len
        let a_has_b as bool is calling a.contains with "b"
        let a_has_b_s as string is calling spark.str_bool with a_has_b
        calling spark.println with "{alen}|{clen}|{a_has_b_s}"
        banish a.items
        banish c.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1|2|false\n"


def test_set_string_to_list_round_trips_through_from_list():
    """to_list yields every distinct element, in any order."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        calling s.add with "a"
        calling s.add with "b"
        calling s.add with "c"
        var xs as list of string is calling s.to_list
        let n as int is calling xs.len
        var back as SetString is calling from_list_string with xs
        let same as bool is calling back.equals with s
        let same_s as string is calling spark.str_bool with same
        calling spark.println with "{n}|{same_s}"
        banish xs
        banish back.items
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3|true\n"


def test_set_string_to_set_int_parses_numbers_and_skips_text():
    """to_set_int keeps parseable elements (including negatives) and drops text."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        calling s.add with "1"
        calling s.add with "2"
        calling s.add with "x"
        calling s.add with "-3"
        var ints as SetInt is calling s.to_set_int
        let n as int is calling ints.len
        let one as bool is calling ints.contains with 1
        let neg as bool is calling ints.contains with -3
        let one_s as string is calling spark.str_bool with one
        let neg_s as string is calling spark.str_bool with neg
        calling spark.println with "{n}|{one_s}|{neg_s}"
        banish ints.items
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3|true|true\n"


def test_set_string_filter_starts_with_keeps_only_the_prefix():
    """filter_starts_with keeps matches, and the empty prefix keeps everything."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        calling s.add with "alpha"
        calling s.add with "alps"
        calling s.add with "beta"
        var r as SetString is calling s.filter_starts_with with "al"
        var all as SetString is calling s.filter_starts_with with ""
        let rlen as int is calling r.len
        let has_alpha as bool is calling r.contains with "alpha"
        let has_beta as bool is calling r.contains with "beta"
        let all_len as int is calling all.len
        let has_alpha_s as string is calling spark.str_bool with has_alpha
        let has_beta_s as string is calling spark.str_bool with has_beta
        calling spark.println with "{rlen}|{has_alpha_s}|{has_beta_s}|{all_len}"
        banish r.items
        banish all.items
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|false|3\n"


def test_set_string_filter_length_ge_keeps_long_elements():
    """filter_length_ge applies an inclusive minimum and copes with extreme n."""
    res = run_coven('''
        var s as SetString is calling coven.new_set_string
        calling s.add with "a"
        calling s.add with "abc"
        calling s.add with "abcde"
        var r as SetString is calling s.filter_length_ge with 3
        var all as SetString is calling s.filter_length_ge with 0
        var none as SetString is calling s.filter_length_ge with 9
        let rlen as int is calling r.len
        let has_abc as bool is calling r.contains with "abc"
        let all_len as int is calling all.len
        let none_empty as bool is calling none.is_empty
        let has_abc_s as string is calling spark.str_bool with has_abc
        let none_s as string is calling spark.str_bool with none_empty
        calling spark.println with "{rlen}|{has_abc_s}|{all_len}|{none_s}"
        banish r.items
        banish all.items
        banish none.items
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|3|true\n"


def test_set_string_empty_and_from_list_constructors():
    """The SetString rituals and module helpers all build deduplicated sets."""
    res = run_coven('''
        var e as SetString is calling coven.empty_set_string
        let e_empty as bool is calling e.is_empty
        var fresh as SetString is calling coven.new_set_string
        let fresh_empty as bool is calling fresh.is_empty
        var xs as list of string is list of string
        calling xs.push with "a"
        calling xs.push with "a"
        calling xs.push with "b"
        var s as SetString is calling from_list_string with xs
        let n as int is calling s.len
        var ys as list of string is list of string
        calling ys.push with "p"
        calling ys.push with "q"
        var t as SetString is calling SetString.from_items with ys
        let tn as int is calling t.len
        let tq as bool is calling t.contains with "q"
        var z as SetString is calling SetString.empty
        let z_empty as bool is calling z.is_empty
        let e_s as string is calling spark.str_bool with e_empty
        let fresh_s as string is calling spark.str_bool with fresh_empty
        let tq_s as string is calling spark.str_bool with tq
        let z_s as string is calling spark.str_bool with z_empty
        calling spark.println with "{e_s}|{fresh_s}|{n}|{tn}|{tq_s}|{z_s}"
        banish e.items
        banish fresh.items
        banish s.items
        banish t.items
        banish z.items
        banish xs
        banish ys
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|2|2|true|true\n"


# ---------------------------------------------------------------------------
# Legacy SetInt
# ---------------------------------------------------------------------------


def test_set_int_add_deduplicates_and_remove_reports():
    """A SetInt deduplicates values and remove reports present then absent."""
    res = run_coven('''
        var s as SetInt is calling coven.new_set_int
        calling s.add with 7
        calling s.add with 7
        let n as int is calling s.len
        let has as bool is calling s.contains with 7
        let first as bool is calling s.remove with 7
        let again as bool is calling s.remove with 7
        let empty as bool is calling s.is_empty
        let has_s as string is calling spark.str_bool with has
        let first_s as string is calling spark.str_bool with first
        let again_s as string is calling spark.str_bool with again
        let empty_s as string is calling spark.str_bool with empty
        calling spark.println with "{n}|{has_s}|{first_s}|{again_s}|{empty_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1|true|true|false|true\n"


def test_set_int_algebra():
    """The four SetInt set operations agree with the SetString ones."""
    res = run_coven('''
        var a as SetInt is calling coven.new_set_int
        var b as SetInt is calling coven.new_set_int
        calling a.add with 1
        calling a.add with 2
        calling b.add with 2
        calling b.add with 3
        var u as SetInt is calling a.union with b
        var i as SetInt is calling a.intersect with b
        var d as SetInt is calling a.difference with b
        var x as SetInt is calling a.symmetric_difference with b
        let ulen as int is calling u.len
        let u3 as bool is calling u.contains with 3
        let ilen as int is calling i.len
        let i2 as bool is calling i.contains with 2
        let dlen as int is calling d.len
        let d1 as bool is calling d.contains with 1
        let xlen as int is calling x.len
        let x1 as bool is calling x.contains with 1
        let x3 as bool is calling x.contains with 3
        let u3_s as string is calling spark.str_bool with u3
        let i2_s as string is calling spark.str_bool with i2
        let d1_s as string is calling spark.str_bool with d1
        let x1_s as string is calling spark.str_bool with x1
        let x3_s as string is calling spark.str_bool with x3
        calling spark.println with "{ulen}|{u3_s}|{ilen}|{i2_s}|{dlen}|{d1_s}|{xlen}|{x1_s}|{x3_s}"
        banish u.items
        banish i.items
        banish d.items
        banish x.items
        banish a.items
        banish b.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3|true|1|true|1|true|2|true|true\n"


def test_set_int_predicates_and_clone():
    """SetInt classifies subset/superset/disjoint and clones independently."""
    res = run_coven('''
        var a as SetInt is calling coven.new_set_int
        var b as SetInt is calling coven.new_set_int
        var c as SetInt is calling coven.new_set_int
        calling a.add with 1
        calling b.add with 1
        calling b.add with 2
        calling c.add with 9
        let sub as bool is calling a.is_subset with b
        let sup as bool is calling b.is_superset with a
        let shared as bool is calling a.is_disjoint with b
        let apart as bool is calling a.is_disjoint with c
        var copy as SetInt is calling b.clone
        let same as bool is calling b.equals with copy
        let other as bool is calling b.equals with a
        let sub_s as string is calling spark.str_bool with sub
        let sup_s as string is calling spark.str_bool with sup
        let shared_s as string is calling spark.str_bool with shared
        let apart_s as string is calling spark.str_bool with apart
        let same_s as string is calling spark.str_bool with same
        let other_s as string is calling spark.str_bool with other
        calling spark.println with "{sub_s}|{sup_s}|{shared_s}|{apart_s}|{same_s}|{other_s}"
        banish a.items
        banish b.items
        banish c.items
        banish copy.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|false|true|true|false\n"


def test_set_int_reductions_and_to_list():
    """sum_ints/min_int/max_int reduce a set, and the empty set collapses to 0."""
    res = run_coven('''
        var s as SetInt is calling coven.new_set_int
        calling s.add with 2
        calling s.add with 3
        calling s.add with 5
        var e as SetInt is calling SetInt.empty
        let total as int is calling s.sum_ints
        let lo as int is calling s.min_int
        let hi as int is calling s.max_int
        var xs as list of int is calling s.to_list_int
        let n as int is calling xs.len
        let e_total as int is calling e.sum_ints
        let e_lo as int is calling e.min_int
        let e_hi as int is calling e.max_int
        calling spark.println with "{total}|{lo}|{hi}|{n}|{e_total}|{e_lo}|{e_hi}"
        banish xs
        banish s.items
        banish e.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "10|2|5|3|0|0|0\n"


def test_set_int_to_set_string_round_trips_decimal_keys():
    """to_set_string stringifies every key, including negative values."""
    res = run_coven('''
        var s as SetInt is calling coven.new_set_int
        calling s.add with 7
        calling s.add with -2
        var t as SetString is calling s.to_set_string
        let n as int is calling t.len
        let seven as bool is calling t.contains with "7"
        let neg as bool is calling t.contains with "-2"
        let missing as bool is calling t.contains with "9"
        let seven_s as string is calling spark.str_bool with seven
        let neg_s as string is calling spark.str_bool with neg
        let missing_s as string is calling spark.str_bool with missing
        calling spark.println with "{n}|{seven_s}|{neg_s}|{missing_s}"
        banish t.items
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|true|false\n"


def test_set_int_empty_and_from_list_constructors():
    """The SetInt rituals and module helpers all build deduplicated sets."""
    res = run_coven('''
        var e as SetInt is calling coven.empty_set_int
        let e_empty as bool is calling e.is_empty
        var xs as list of int is list of int
        calling xs.push with 4
        calling xs.push with 4
        calling xs.push with 5
        var s as SetInt is calling from_list_int with xs
        let n as int is calling s.len
        var ys as list of int is list of int
        calling ys.push with 8
        calling ys.push with 9
        var t as SetInt is calling SetInt.from_items with ys
        let tn as int is calling t.len
        let t9 as bool is calling t.contains with 9
        var z as SetInt is calling SetInt.empty
        let z_empty as bool is calling z.is_empty
        let e_s as string is calling spark.str_bool with e_empty
        let t9_s as string is calling spark.str_bool with t9
        let z_s as string is calling spark.str_bool with z_empty
        calling spark.println with "{e_s}|{n}|{tn}|{t9_s}|{z_s}"
        banish e.items
        banish s.items
        banish t.items
        banish z.items
        banish xs
        banish ys
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|2|2|true|true\n"


# ---------------------------------------------------------------------------
# Generic Set of int
# ---------------------------------------------------------------------------


def test_generic_make_set_of_int_deduplicates_and_removes():
    """calling make_set of int builds an empty set that deduplicates."""
    res = run_coven('''
        var s as Set of int is calling coven.make_set of int
        let start_empty as bool is calling s.is_empty
        calling s.add with 7
        calling s.add with 7
        let n as int is calling s.len
        let has as bool is calling s.contains with 7
        let removed as bool is calling s.remove with 7
        let empty as bool is calling s.is_empty
        let start_s as string is calling spark.str_bool with start_empty
        let has_s as string is calling spark.str_bool with has
        let removed_s as string is calling spark.str_bool with removed
        let empty_s as string is calling spark.str_bool with empty
        calling spark.println with "{start_s}|{n}|{has_s}|{removed_s}|{empty_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|1|true|true|true\n"


def test_generic_set_of_int_algebra():
    """The generic set operations work on Set of int via new_int_set."""
    res = run_coven('''
        var a as Set of int is calling coven.new_int_set
        var b as Set of int is calling coven.new_int_set
        calling a.add with 1
        calling a.add with 2
        calling b.add with 2
        calling b.add with 3
        var u as Set of int is calling a.union with b
        var i as Set of int is calling a.intersect with b
        var d as Set of int is calling a.difference with b
        var x as Set of int is calling a.symmetric_difference with b
        let ulen as int is calling u.len
        let u3 as bool is calling u.contains with 3
        let ilen as int is calling i.len
        let i2 as bool is calling i.contains with 2
        let dlen as int is calling d.len
        let d1 as bool is calling d.contains with 1
        let xlen as int is calling x.len
        let x1 as bool is calling x.contains with 1
        let x3 as bool is calling x.contains with 3
        let u3_s as string is calling spark.str_bool with u3
        let i2_s as string is calling spark.str_bool with i2
        let d1_s as string is calling spark.str_bool with d1
        let x1_s as string is calling spark.str_bool with x1
        let x3_s as string is calling spark.str_bool with x3
        calling spark.println with "{ulen}|{u3_s}|{ilen}|{i2_s}|{dlen}|{d1_s}|{xlen}|{x1_s}|{x3_s}"
        banish u.items
        banish i.items
        banish d.items
        banish x.items
        banish a.items
        banish b.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3|true|1|true|1|true|2|true|true\n"


def test_generic_set_of_int_predicates_and_clone():
    """The generic set classifies membership and clones independently."""
    res = run_coven('''
        var a as Set of int is calling coven.new_int_set
        var b as Set of int is calling coven.new_int_set
        calling a.add with 1
        calling b.add with 1
        calling b.add with 2
        let sub as bool is calling a.is_subset with b
        let sup as bool is calling b.is_superset with a
        let shared as bool is calling a.is_disjoint with b
        var copy as Set of int is calling b.clone
        let same as bool is calling b.equals with copy
        let other as bool is calling b.equals with a
        let sub_s as string is calling spark.str_bool with sub
        let sup_s as string is calling spark.str_bool with sup
        let shared_s as string is calling spark.str_bool with shared
        let same_s as string is calling spark.str_bool with same
        let other_s as string is calling spark.str_bool with other
        calling spark.println with "{sub_s}|{sup_s}|{shared_s}|{same_s}|{other_s}"
        banish a.items
        banish b.items
        banish copy.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|true|false|true|false\n"


def test_generic_from_items_set_of_int_round_trips():
    """from_items_set of int deduplicates and to_list round-trips the members."""
    res = run_coven('''
        var xs as list of int is list of int
        calling xs.push with 4
        calling xs.push with 4
        calling xs.push with 5
        var s as Set of int is calling coven.from_items_set of int with xs
        let n as int is calling s.len
        var out as list of int is calling s.to_list
        let out_len as int is calling out.len
        var back as Set of int is calling coven.from_items_set of int with out
        let same as bool is calling back.equals with s
        let same_s as string is calling spark.str_bool with same
        calling spark.println with "{n}|{out_len}|{same_s}"
        banish out
        banish back.items
        banish s.items
        banish xs
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|2|true\n"


# ---------------------------------------------------------------------------
# Generic Set of string, float, bool and char
# ---------------------------------------------------------------------------


def test_generic_set_of_string_add_contains_to_list_and_clear():
    """A Set of string stores one copy, lists it, then clears."""
    res = run_coven('''
        var s as Set of string is calling coven.new_string_set
        calling s.add with "alpha"
        calling s.add with "alpha"
        let n as int is calling s.len
        let has as bool is calling s.contains with "alpha"
        let out as list of string is calling s.to_list
        let out_len as int is calling out.len
        let first as string is (out at 0)
        calling s.clear
        let empty as bool is calling s.is_empty
        let after as int is calling s.len
        let has_s as string is calling spark.str_bool with has
        let empty_s as string is calling spark.str_bool with empty
        calling spark.println with "{n}|{has_s}|{out_len}|{first}|{empty_s}|{after}"
        banish out
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1|true|1|alpha|true|0\n"


def test_generic_make_set_of_string_and_float():
    """make_set of string and make_set of float both build empty deduplicating sets."""
    res = run_coven('''
        var s as Set of string is calling coven.make_set of string
        let start_empty as bool is calling s.is_empty
        calling s.add with "x"
        calling s.add with "x"
        let n as int is calling s.len
        var f as Set of float is calling coven.make_set of float
        let f_start_empty as bool is calling f.is_empty
        calling f.add with 1.5
        let fn as int is calling f.len
        let start_s as string is calling spark.str_bool with start_empty
        let f_start_s as string is calling spark.str_bool with f_start_empty
        calling spark.println with "{start_s}|{n}|{f_start_s}|{fn}"
        banish s.items
        banish f.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true|1|true|1\n"


def test_generic_set_of_float_deduplicates_and_removes():
    """A Set of float deduplicates by value and remove reports membership."""
    res = run_coven('''
        var s as Set of float is calling coven.new_float_set
        calling s.add with 1.5
        calling s.add with 1.5
        calling s.add with 2.5
        let n as int is calling s.len
        let has as bool is calling s.contains with 1.5
        let missing as bool is calling s.contains with 3.5
        let removed as bool is calling s.remove with 1.5
        let after as int is calling s.len
        let has_s as string is calling spark.str_bool with has
        let missing_s as string is calling spark.str_bool with missing
        let removed_s as string is calling spark.str_bool with removed
        calling spark.println with "{n}|{has_s}|{missing_s}|{removed_s}|{after}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|false|true|1\n"


def test_generic_bool_and_char_sets():
    """The bool and char constructors build working generic sets."""
    res = run_coven('''
        var b as Set of bool is calling coven.new_bool_set
        calling b.add with true
        calling b.add with true
        let bn as int is calling b.len
        let bt as bool is calling b.contains with true
        let bf as bool is calling b.contains with false
        var c as Set of char is calling coven.new_char_set
        calling c.add with (65 to char)
        let ca as bool is calling c.contains with (65 to char)
        let cb as bool is calling c.contains with (66 to char)
        let bt_s as string is calling spark.str_bool with bt
        let bf_s as string is calling spark.str_bool with bf
        let ca_s as string is calling spark.str_bool with ca
        let cb_s as string is calling spark.str_bool with cb
        calling spark.println with "{bn}|{bt_s}|{bf_s}|{ca_s}|{cb_s}"
        banish b.items
        banish c.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1|true|false|true|false\n"


def test_generic_from_items_set_of_string():
    """from_items_set of string deduplicates a list of strings."""
    res = run_coven('''
        var xs as list of string is list of string
        calling xs.push with "a"
        calling xs.push with "a"
        calling xs.push with "b"
        var s as Set of string is calling coven.from_items_set of string with xs
        let n as int is calling s.len
        let has_b as bool is calling s.contains with "b"
        let has_c as bool is calling s.contains with "c"
        let has_b_s as string is calling spark.str_bool with has_b
        let has_c_s as string is calling spark.str_bool with has_c
        calling spark.println with "{n}|{has_b_s}|{has_c_s}"
        banish s.items
        banish xs
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|false\n"


def test_generic_set_of_custom_rune():
    """A user rune deriving Par, Vinculum works as a Set element type."""
    res = run_coven('''
        var s as Set of Player is calling coven.make_set of Player
        var p as Player with:
            set .id is 7
        var q as Player with:
            set .id is 7
        var r as Player with:
            set .id is 9
        calling s.add with p
        calling s.add with q
        calling s.add with r
        let n as int is calling s.len
        let has_p as bool is calling s.contains with p
        let has_r as bool is calling s.contains with r
        let removed as bool is calling s.remove with r
        let after as int is calling s.len
        let has_r_after as bool is calling s.contains with r
        let has_p_s as string is calling spark.str_bool with has_p
        let has_r_s as string is calling spark.str_bool with has_r
        let removed_s as string is calling spark.str_bool with removed
        let has_r_after_s as string is calling spark.str_bool with has_r_after
        calling spark.println with "{n}|{has_p_s}|{has_r_s}|{removed_s}|{after}|{has_r_after_s}"
        banish s.items
    ''', prelude='''
        rune Player derive Par, Vinculum:
            id as int
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|true|true|1|false\n"


# ---------------------------------------------------------------------------
# Widened element types: the 2.2.0 generic Set accepts wide integers and floats
# ---------------------------------------------------------------------------

def test_generic_make_set_of_i64_keys_on_64_bit_values():
    """``make_set of i64`` keys 5000000000 and -5000000000, not their int32 tails."""
    res = run_coven('''
        var s as Set of i64 is calling coven.make_set of i64
        calling s.add with 5000000000
        calling s.add with -5000000000
        calling s.add with 5000000000
        let n as int is calling s.len
        let has_pos as bool is calling s.contains with 5000000000
        let has_neg as bool is calling s.contains with -5000000000
        let has_tail as bool is calling s.contains with 705032704
        let has_pos_s as string is calling spark.str_bool with has_pos
        let has_neg_s as string is calling spark.str_bool with has_neg
        let has_tail_s as string is calling spark.str_bool with has_tail
        calling spark.println with "{n}|{has_pos_s}|{has_neg_s}|{has_tail_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|true|false\n"


def test_generic_new_i64_and_u64_sets():
    """``new_i64_set`` and ``new_u64_set`` build working wide-integer sets."""
    res = run_coven('''
        var a as Set of i64 is calling coven.new_i64_set
        var b as Set of u64 is calling coven.new_u64_set
        calling a.add with 12000000000
        calling b.add with 12000000000
        calling b.add with 12000000000
        let alen as int is calling a.len
        let blen as int is calling b.len
        let ahas as bool is calling a.contains with 12000000000
        let bhas as bool is calling b.contains with 12000000000
        let ahas_s as string is calling spark.str_bool with ahas
        let bhas_s as string is calling spark.str_bool with bhas
        calling spark.println with "{alen}|{blen}|{ahas_s}|{bhas_s}"
        banish a.items
        banish b.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1|1|true|true\n"


def test_generic_make_set_of_isize_with_a_negative_key():
    """``make_set of isize`` keeps a negative key distinct from its magnitude."""
    res = run_coven('''
        var s as Set of isize is calling coven.make_set of isize
        calling s.add with -9000000000
        calling s.add with -9000000000
        calling s.add with 9000000000
        let n as int is calling s.len
        let has_neg as bool is calling s.contains with -9000000000
        let has_pos as bool is calling s.contains with 9000000000
        let has_off as bool is calling s.contains with -9000000001
        let has_neg_s as string is calling spark.str_bool with has_neg
        let has_pos_s as string is calling spark.str_bool with has_pos
        let has_off_s as string is calling spark.str_bool with has_off
        calling spark.println with "{n}|{has_neg_s}|{has_pos_s}|{has_off_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|true|false\n"


def test_generic_set_of_float_keeps_signed_zero_keys_distinct():
    """``0.0`` and ``-0.0`` hash to different keys of a ``Set of float``."""
    res = run_coven('''
        var s as Set of float is calling coven.make_set of float
        calling s.add with 0.0
        calling s.add with -0.0
        calling s.add with 0.0
        let n as int is calling s.len
        let has_pos as bool is calling s.contains with 0.0
        let has_neg as bool is calling s.contains with -0.0
        let has_pos_s as string is calling spark.str_bool with has_pos
        let has_neg_s as string is calling spark.str_bool with has_neg
        calling spark.println with "{n}|{has_pos_s}|{has_neg_s}"
        banish s.items
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2|true|true\n"
