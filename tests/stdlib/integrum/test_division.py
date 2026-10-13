"""`std.integrum` — Euclidean division.

Two programs: the tuple-returning `div_rem` and the flooring pair
(`div_floor`, `mod_floor`) across all four sign combinations.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.integrum

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_div_rem(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as int is 17
    var b as int is -17
    var five as int is 5
    let (q1, r1) is calling a.div_rem with five
    let (q2, r2) is calling b.div_rem with five
    calling eq_i with q1, 3, "17/5 quotient"
    calling eq_i with r1, 2, "17%5 remainder"
    calling eq_i with q2, -3, "-17/5 quotient (toward zero)"
    calling eq_i with r2, -2, "-17%5 remainder (sign of dividend)"
    calling eq_i with ((q1 * 5) + r1), 17, "identity positive"
    calling eq_i with ((q2 * 5) + r2), -17, "identity negative"
    var wide as i64 is 100
    let (q3, r3) is calling wide.div_rem with 7
    calling eq_i with (q3 to int), 14, "i64 quotient"
    calling eq_i with (r3 to int), 2, "i64 remainder"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_floor_division_and_modulo(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var p as int is 7
    var n as int is -7
    var two as int is 2
    var mtwo as int is -2
    var three as int is 3
    var mthree as int is -3
    calling eq_i with (calling p.div_floor with two), 3, "7 div_floor 2"
    calling eq_i with (calling n.div_floor with two), -4, "-7 div_floor 2"
    calling eq_i with (calling p.div_floor with mtwo), -4, "7 div_floor -2"
    calling eq_i with (calling n.div_floor with mtwo), 3, "-7 div_floor -2"
    calling eq_i with (calling p.mod_floor with three), 1, "7 mod_floor 3"
    calling eq_i with (calling n.mod_floor with three), 2, "-7 mod_floor 3"
    calling eq_i with (calling p.mod_floor with mthree), -2, "7 mod_floor -3"
    calling eq_i with (calling n.mod_floor with mthree), -1, "-7 mod_floor -3"
    var four as int is 12
    calling eq_i with (calling four.mod_floor with three), 0, "exact multiple"
    var u as u32 is 7
    calling eq_i with (calling u.div_floor with 2), 3, "unsigned div_floor"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
