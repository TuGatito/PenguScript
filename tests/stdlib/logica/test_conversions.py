"""`std.logica` — `to_int` and the algebraic identities.

Two programs: the `bool -> int` conversion (alone and used as a counter) and
the identities that tie the derived connectives to the basic ones
(`xor == not iff`, `nand == not and`, `nor == not or`, De Morgan, and the
`iff`/`implies` biconditional).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.logica

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_to_int(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var t as bool is true
    var f as bool is false
    calling eq_i with (calling t.to_int), 1, "true -> 1"
    calling eq_i with (calling f.to_int), 0, "false -> 0"
    var total as int is 0
    set total is total + (calling t.to_int)
    set total is total + (calling f.to_int)
    set total is total + (calling t.to_int)
    set total is total + (calling t.to_int)
    calling eq_i with total, 3, "counter"
    var negated as bool is calling f.get_toggle
    calling eq_i with (calling negated.to_int), 1, "toggled false -> 1"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_identities(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var t as bool is true
    var f as bool is false
    var x as bool is calling t.get_xor with f
    var i as bool is calling t.get_iff with f
    calling eq_b with (x == (not i)), true, "xor == not iff"
    var n as bool is calling t.get_nand with f
    var a as bool is calling t.get_and_with with f
    calling eq_b with (n == (not a)), true, "nand == not and"
    var no as bool is calling f.get_nor with f
    var o as bool is calling f.get_or_with with f
    calling eq_b with (no == (not o)), true, "nor == not or"
    var impl as bool is calling t.get_implies with f
    var expected as bool is (not t) or f
    calling eq_b with (impl == expected), true, "implies == not-or"
    var iff_res as bool is calling t.get_iff with f
    var forward as bool is calling t.get_implies with f
    var backward as bool is calling f.get_implies with t
    calling eq_b with (iff_res == (forward and backward)), true, "iff == both implies"
    var na as bool is calling t.get_toggle
    var nb as bool is calling f.get_toggle
    var or_result as bool is calling na.get_or_with with nb
    calling eq_b with (n == or_result), true, "de morgan"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
