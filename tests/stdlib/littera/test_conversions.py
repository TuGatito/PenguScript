"""`std.littera` — the conversions.

Two programs: `to_upper`/`to_lower` (including the non-letter pass-through and
the round trip) and the numeric pair `to_int`/`digit_value`.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.littera

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_case_conversion(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as char is 'a'
    var z as char is 'z'
    var big_a as char is 'A'
    var big_z as char is 'Z'
    var five as char is '5'
    var sp as char is ' '
    var bang as char is '!'
    calling eq_i with (ord (calling a.get_to_upper)), (ord 'A'), "a -> A"
    calling eq_i with (ord (calling z.get_to_upper)), (ord 'Z'), "z -> Z"
    calling eq_i with (ord (calling big_a.get_to_lower)), (ord 'a'), "A -> a"
    calling eq_i with (ord (calling big_z.get_to_lower)), (ord 'z'), "Z -> z"
    calling eq_i with (ord (calling big_a.get_to_upper)), (ord 'A'), "A -> A"
    calling eq_i with (ord (calling five.get_to_upper)), (ord '5'), "5 -> 5"
    calling eq_i with (ord (calling sp.get_to_lower)), (ord ' '), "space -> space"
    calling eq_i with (ord (calling bang.get_to_upper)), (ord '!'), "! -> !"
    var q as char is 'q'
    var up as char is calling q.get_to_upper
    var down as char is calling up.get_to_lower
    calling eq_i with (ord down), (ord 'q'), "round trip"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_numeric_conversions(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as char is '0'
    var nine as char is '9'
    var big_a as char is 'A'
    var a as char is 'a'
    var sp as char is ' '
    calling eq_i with (calling zero.to_int), 48, "to_int 0"
    calling eq_i with (calling big_a.to_int), 65, "to_int A"
    calling eq_i with (calling a.to_int), 97, "to_int a"
    calling eq_i with (calling sp.to_int), 32, "to_int space"
    calling eq_i with (calling zero.digit_value), 0, "digit 0"
    calling eq_i with (calling nine.digit_value), 9, "digit 9"
    var f as char is 'f'
    var big_f as char is 'F'
    calling eq_i with (calling a.digit_value), 10, "digit a"
    calling eq_i with (calling f.digit_value), 15, "digit f"
    calling eq_i with (calling big_a.digit_value), 10, "digit A"
    calling eq_i with (calling big_f.digit_value), 15, "digit F"
    var g as char is 'g'
    var z as char is 'z'
    calling eq_i with (calling g.digit_value), -1, "digit g"
    calling eq_i with (calling z.digit_value), -1, "digit z"
    calling eq_i with (calling sp.digit_value), -1, "digit space"
    var b as byte is 200
    var high as char is (b to char)
    calling eq_i with (calling high.to_int), 200, "to_int high byte is unsigned"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
