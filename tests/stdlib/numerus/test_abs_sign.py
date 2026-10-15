"""`std.numerus` — `abs`, `signum` and `negated` across every numeric width.

Batched: two programs, one for the magnitude family and one for the sign family.
Each program prints ``FAIL …`` for a mismatch and ``DONE`` when it finishes, so a
single build validates the whole matrix.
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

weave eq_f with got as f64, want as f64, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_abs_across_every_width(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var neg as int is -5
    var pos as int is 5
    var zero as int is 0
    var wide as i64 is -9000000
    var small as i8 is -7
    var half as f32 is -2.5
    var real as f64 is -3.5
    var un as u32 is 7
    var byt as byte is 9
    var sz as usize is 11
    var iz as isize is -13
    calling eq_i with (calling neg.get_abs), 5, "int negative"
    calling eq_i with (calling pos.get_abs), 5, "int positive identity"
    calling eq_i with (calling zero.get_abs), 0, "int zero"
    calling eq_i with (calling wide.get_abs to int), 9000000, "i64 negative"
    calling eq_i with (calling small.get_abs), 7, "i8 negative"
    calling eq_f with (calling half.get_abs to f64), 2.5, "f32 negative"
    calling eq_f with (calling real.get_abs), 3.5, "f64 negative"
    calling eq_i with (calling un.get_abs), 7, "u32 identity"
    calling eq_i with (calling byt.get_abs), 9, "byte identity"
    calling eq_i with (calling sz.get_abs), 11, "usize identity"
    calling eq_i with (calling iz.get_abs to int), 13, "isize negative"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_signum_and_negated(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var neg as int is -42
    var zero as int is 0
    var pos as int is 7
    var fpos as f64 is 7.5
    var fneg as f64 is -0.5
    var un as u32 is 9
    calling eq_i with (calling neg.get_signum), -1, "signum int negative"
    calling eq_i with (calling zero.get_signum), 0, "signum int zero"
    calling eq_i with (calling pos.get_signum), 1, "signum int positive"
    calling eq_f with (calling fpos.get_signum), 1.0, "signum f64 positive"
    calling eq_f with (calling fneg.get_signum), -1.0, "signum f64 negative"
    calling eq_i with (calling un.get_signum), 1, "signum unsigned positive"
    calling eq_i with (calling neg.get_negated), 42, "negated int negative"
    calling eq_i with (calling zero.get_negated), 0, "negated int zero"
    calling eq_i with (calling pos.get_negated), -7, "negated int positive"
    calling eq_f with (calling fpos.get_negated), -7.5, "negated f64 positive"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
