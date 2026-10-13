"""`std.integrum` — `to_hex`, `to_bin`, `to_oct`.

Two programs: the digit conversions (including the sign-and-magnitude rule for
negatives) and the ownership check (every returned `string` is `banish`ed).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.integrum

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_to_hex_bin_oct(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var one as int is 1
    var fifteen as int is 15
    var sixteen as int is 16
    var ff as int is 255
    var fff as int is 4095
    var h0 as string is calling zero.to_hex
    var h1 as string is calling one.to_hex
    var h15 as string is calling fifteen.to_hex
    var h16 as string is calling sixteen.to_hex
    var hff as string is calling ff.to_hex
    var hfff as string is calling fff.to_hex
    calling eq_s with h0, "0", "hex 0"
    calling eq_s with h1, "1", "hex 1"
    calling eq_s with h15, "f", "hex 15"
    calling eq_s with h16, "10", "hex 16"
    calling eq_s with hff, "ff", "hex 255"
    calling eq_s with hfff, "fff", "hex 4095"
    var five as int is 5
    var eight as int is 8
    var seven as int is 7
    var sixtythree as int is 63
    var b5 as string is calling five.to_bin
    var b0 as string is calling zero.to_bin
    var bff as string is calling ff.to_bin
    calling eq_s with b5, "101", "bin 5"
    calling eq_s with b0, "0", "bin 0"
    calling eq_s with bff, "11111111", "bin 255"
    var o8 as string is calling eight.to_oct
    var o7 as string is calling seven.to_oct
    var o63 as string is calling sixtythree.to_oct
    calling eq_s with o8, "10", "oct 8"
    calling eq_s with o7, "7", "oct 7"
    calling eq_s with o63, "77", "oct 63"
    banish h0
    banish h1
    banish h15
    banish h16
    banish hff
    banish hfff
    banish b5
    banish b0
    banish bff
    banish o8
    banish o7
    banish o63
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_negative_representations_are_sign_and_magnitude(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var n as int is -255
    var m as int is -5
    var h as string is calling n.to_hex
    var b as string is calling m.to_bin
    var o as string is calling m.to_oct
    calling eq_s with h, "-ff", "hex -255"
    calling eq_s with b, "-101", "bin -5"
    calling eq_s with o, "-5", "oct -5"
    banish h
    banish b
    banish o
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
