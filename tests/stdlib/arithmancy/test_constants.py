"""`std.arithmancy` — the mathematical constants are untouched.

The constants stay in `arithmancy` (no other module owns them), so they are
checked bit for bit against their documented values. `float` is 32-bit, so the
comparison is done in `f64` with the single-precision tolerance.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.arithmancy

weave eq_f with got as f64, want as f64, eps as f64, name as string into void:
    var d as f64 is got - want
    if d < 0.0:
        set d is 0.0 - d
    if d > eps:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_constants(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-5
    calling eq_f with (arithmancy.PI to f64), 3.141592653589793, eps, "PI"
    calling eq_f with (arithmancy.TAU to f64), 6.283185307179586, eps, "TAU"
    calling eq_f with (arithmancy.E to f64), 2.718281828459045, eps, "E"
    calling eq_f with (arithmancy.HALF_PI to f64), 1.5707963267948966, eps, "HALF_PI"
    calling eq_f with (arithmancy.QUARTER_PI to f64), 0.7853981633974483, eps, "QUARTER_PI"
    calling eq_f with (arithmancy.TWO_PI to f64), 6.283185307179586, eps, "TWO_PI"
    calling eq_f with (arithmancy.INV_PI to f64), 0.3183098861837907, eps, "INV_PI"
    calling eq_f with (arithmancy.DEG2RAD to f64), 0.017453292519943295, eps, "DEG2RAD"
    calling eq_f with (arithmancy.RAD2DEG to f64), 57.29577951308232, eps, "RAD2DEG"
    calling eq_f with (arithmancy.SQRT2 to f64), 1.4142135623730951, eps, "SQRT2"
    calling eq_f with (arithmancy.SQRT3 to f64), 1.7320508075688772, eps, "SQRT3"
    calling eq_f with (arithmancy.EPSILON to f64), 0.000001, 1e-9, "EPSILON"
    var t as f64 is arithmancy.TWO_PI to f64
    var tau as f64 is arithmancy.TAU to f64
    calling eq_f with t, tau, 0.0, "TWO_PI == TAU"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
