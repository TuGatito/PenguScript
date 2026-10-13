"""`std.numerus` — arithmetic transforms and conversions.

Three programs: the shape transforms (`twice`, `half`, `square`, `cube`), the
integer power (`pow_int`, including the truncating negative exponent), and the
chainable conversions (`to_f64`, `to_i64`).
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


def test_shape_transforms(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var pos as int is 21
    var neg as int is -4
    var zero as int is 0
    var odd as int is 5
    var f as f64 is 2.5
    calling eq_i with (calling pos.twice), 42, "twice positive"
    calling eq_i with (calling neg.twice), -8, "twice negative"
    calling eq_i with (calling zero.twice), 0, "twice zero"
    calling eq_i with (calling pos.half), 10, "half even"
    calling eq_i with (calling odd.half), 2, "half odd truncates"
    calling eq_i with (calling neg.half), -2, "half negative truncates"
    calling eq_f with (calling f.half), 1.25, "half f64"
    calling eq_i with (calling neg.square), 16, "square negative"
    calling eq_i with (calling zero.square), 0, "square zero"
    calling eq_i with (calling neg.cube), -64, "cube negative"
    calling eq_i with (calling zero.cube), 0, "cube zero"
    calling eq_i with (calling pos.square), 441, "square positive"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_pow_int(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var two as int is 2
    var f as f64 is 2.0
    var three as f64 is 3.0
    calling eq_i with (calling two.pow_int with 0), 1, "pow exp 0"
    calling eq_i with (calling two.pow_int with 1), 2, "pow exp 1"
    calling eq_i with (calling two.pow_int with 10), 1024, "pow exp 10"
    calling eq_i with (calling two.pow_int with -3), 0, "pow int neg truncates"
    calling eq_f with (calling f.pow_int with 10), 1024.0, "pow f64 exp 10"
    calling eq_f with (calling f.pow_int with -1), 0.5, "pow f64 neg fractional"
    calling eq_f with (calling three.pow_int with 3), 27.0, "pow f64 cube"
    calling eq_f with (calling three.pow_int with 0), 1.0, "pow f64 exp 0"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_conversions(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var i as int is 42
    var wide as i64 is -7
    var narrow as f32 is 2.5
    var frac as f64 is 2.9
    var neg as f64 is -2.9
    calling eq_f with (calling i.to_f64), 42.0, "to_f64 int"
    calling eq_f with (calling wide.to_f64), -7.0, "to_f64 i64"
    calling eq_f with (calling narrow.to_f64), 2.5, "to_f64 f32"
    calling eq_i with (calling frac.to_i64 to int), 2, "to_i64 truncates down"
    calling eq_i with (calling neg.to_i64 to int), -2, "to_i64 truncates up"
    calling eq_i with (calling i.to_i64 to int), 42, "to_i64 int"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
