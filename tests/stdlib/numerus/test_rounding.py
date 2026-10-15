"""`std.numerus` — rounding: `truncate`, `floor`, `ceil`, `round`.

Two programs split the family: the two downward operations and the two upward
ones. Every method is checked on a positive fraction, a negative fraction and a
whole number (where the integer result must be the identity), and `round` is
pinned to the half-away-from-zero convention on both signs.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.numerus

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_truncate_and_floor(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var pos as f64 is 2.7
    var neg as f64 is -2.7
    var whole as f64 is 2.0
    var ints as int is 42
    var negint as int is -42
    calling eq_i with (calling pos.get_truncate to int), 2, "truncate positive"
    calling eq_i with (calling neg.get_truncate to int), -2, "truncate negative"
    calling eq_i with (calling whole.get_truncate to int), 2, "truncate whole"
    calling eq_i with (calling ints.get_truncate), 42, "truncate int identity"
    calling eq_i with (calling pos.get_floor to int), 2, "floor positive"
    calling eq_i with (calling neg.get_floor to int), -3, "floor negative"
    calling eq_i with (calling whole.get_floor to int), 2, "floor whole"
    calling eq_i with (calling negint.get_floor), -42, "floor int identity"
    var half as f64 is 2.5
    calling eq_i with (calling half.get_floor to int), 2, "floor .5 down"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_ceil_and_round(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var pos as f64 is 2.3
    var neg as f64 is -2.3
    var whole as f64 is 2.0
    var ints as int is 5
    var negint as int is -5
    calling eq_i with (calling pos.get_ceil to int), 3, "ceil positive"
    calling eq_i with (calling neg.get_ceil to int), -2, "ceil negative"
    calling eq_i with (calling whole.get_ceil to int), 2, "ceil whole"
    calling eq_i with (calling ints.get_ceil), 5, "ceil int identity"
    var low as f64 is 2.4
    var mid as f64 is 2.5
    var high as f64 is 2.6
    calling eq_i with (calling low.get_round to int), 2, "round .4"
    calling eq_i with (calling mid.get_round to int), 3, "round .5 away from zero"
    calling eq_i with (calling high.get_round to int), 3, "round .6"
    var nlow as f64 is -2.4
    var nmid as f64 is -2.5
    var nhigh as f64 is -2.6
    calling eq_i with (calling nlow.get_round to int), -2, "round -2.4"
    calling eq_i with (calling nmid.get_round to int), -3, "round -2.5 away from zero"
    calling eq_i with (calling nhigh.get_round to int), -3, "round -2.6"
    calling eq_i with (calling negint.get_round), -5, "round int identity"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
