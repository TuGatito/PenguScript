"""`std.fractio` — `degrees`, `radians` and `hypot`.

Two programs: the angle conversions (which exercise the `T: Real` literal cast
at both widths) and `hypot` as a distance helper.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.fractio

weave eq_f with got as f64, want as f64, eps as f64, name as string into void:
    var d as f64 is got - want
    if d < 0.0:
        set d is 0.0 - d
    if d > eps:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_degrees_and_radians(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var pi as f64 is 3.141592653589793
    var half as f64 is pi / 2.0
    var d180 as f64 is 180.0
    var d90 as f64 is 90.0
    var zero as f64 is 0.0
    calling eq_f with (calling pi.degrees), 180.0, 1e-12, "pi -> 180"
    calling eq_f with (calling half.degrees), 90.0, 1e-12, "pi/2 -> 90"
    calling eq_f with (calling zero.degrees), 0.0, 1e-12, "0 -> 0"
    calling eq_f with (calling d180.radians), pi, 1e-15, "180 -> pi"
    calling eq_f with (calling d90.radians), half, 1e-15, "90 -> pi/2"
    var pi32 as float is 3.141592653589793
    calling eq_f with ((calling pi32.degrees) to f64), 180.0, 1e-4, "pi f32 -> 180"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_hypot_as_distance(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave distance_2d with x1 as f64, y1 as f64, x2 as f64, y2 as f64 into f64:
    var dx as f64 is x2 - x1
    var dy as f64 is y2 - y1
    return calling dx.hypot with dy

weave main into int:
    calling eq_f with (calling distance_2d with 0.0, 0.0, 3.0, 4.0), 5.0, 1e-12, "3-4-5"
    calling eq_f with (calling distance_2d with 1.0, 1.0, 4.0, 5.0), 5.0, 1e-12, "offset 3-4-5"
    calling eq_f with (calling distance_2d with 2.0, 2.0, 2.0, 2.0), 0.0, 1e-12, "degenerate"
    var big as f64 is 1e200
    calling eq_f with (calling big.hypot with 0.0), 1e200, 1e190, "no overflow at 1e200"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
