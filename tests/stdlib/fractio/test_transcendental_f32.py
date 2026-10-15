"""`std.fractio` — the `libm` transcendentals on the 32-bit width.

Three programs, all exercising the `enchanting float:` block through `float`
and its alias `f32`: roots and exponentials/logarithms, trigonometry, and the
two-argument functions (`atan2`, `pow`, `hypot`). Results are widened to `f64`
for comparison, with a tolerance that matches single precision.
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

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_roots_and_logs_f32(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-5
    var four as float is 4.0
    var nine as f32 is 9.0
    var neg as float is -8.0
    var eight as float is 8.0
    var one as float is 1.0
    var e as float is 2.718281828459045
    var large as float is 1024.0
    var hundred as float is 100.0
    calling eq_f with ((calling four.get_sqrt) to f64), 2.0, eps, "sqrt 4"
    calling eq_f with ((calling nine.get_sqrt) to f64), 3.0, eps, "sqrt 9 (f32)"
    calling eq_f with ((calling eight.get_cbrt) to f64), 2.0, eps, "cbrt 8"
    calling eq_f with ((calling neg.get_cbrt) to f64), -2.0, eps, "cbrt -8"
    calling eq_f with ((calling one.get_ln) to f64), 0.0, eps, "ln 1"
    calling eq_f with ((calling e.get_ln) to f64), 1.0, eps, "ln e"
    calling eq_f with ((calling eight.get_log2) to f64), 3.0, eps, "log2 8"
    calling eq_f with ((calling large.get_log2) to f64), 10.0, eps, "log2 1024"
    calling eq_f with ((calling hundred.get_log10) to f64), 2.0, eps, "log10 100"
    var zero as float is 0.0
    var onef as float is 1.0
    calling eq_f with ((calling zero.get_exp) to f64), 1.0, eps, "exp 0"
    calling eq_f with ((calling onef.get_exp) to f64), 2.718281828459045, eps, "exp 1"
    var minus as float is -1.0
    var bad as float is calling minus.get_sqrt
    calling eq_b with (calling bad.is_nan), true, "sqrt(-1) is NaN"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_trigonometry_f32(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-5
    var zero as float is 0.0
    var one as float is 1.0
    var pi as float is 3.141592653589793
    var half as float is pi / 2.0
    var quarter as float is pi / 4.0
    calling eq_f with ((calling zero.get_sin) to f64), 0.0, eps, "sin 0"
    calling eq_f with ((calling half.get_sin) to f64), 1.0, eps, "sin pi/2"
    calling eq_f with ((calling zero.get_cos) to f64), 1.0, eps, "cos 0"
    calling eq_f with ((calling half.get_cos) to f64), 0.0, eps, "cos pi/2"
    calling eq_f with ((calling zero.get_tan) to f64), 0.0, eps, "tan 0"
    calling eq_f with ((calling quarter.get_tan) to f64), 1.0, eps, "tan pi/4"
    calling eq_f with ((calling one.get_asin) to f64), 1.5707963267948966, eps, "asin 1"
    calling eq_f with ((calling one.get_acos) to f64), 0.0, eps, "acos 1"
    calling eq_f with ((calling one.get_atan) to f64), 0.7853981633974483, eps, "atan 1"
    var two as float is 2.0
    var bad as float is calling two.get_asin
    calling eq_b with (calling bad.is_nan), true, "asin 2 is NaN"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_two_argument_functions_f32(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-5
    var one as float is 1.0
    var two as float is 2.0
    var three as float is 3.0
    var four as float is 4.0
    var zero as float is 0.0
    calling eq_f with ((calling one.get_atan2 with one) to f64), 0.7853981633974483, eps, "atan2(1,1)"
    calling eq_f with ((calling zero.get_atan2 with one) to f64), 0.0, eps, "atan2(0,1)"
    calling eq_f with ((calling two.get_pow with 10.0) to f64), 1024.0, eps, "pow 2^10"
    calling eq_f with ((calling two.get_pow with 0.0) to f64), 1.0, eps, "pow 2^0"
    calling eq_f with ((calling two.get_pow with -1.0) to f64), 0.5, eps, "pow 2^-1"
    calling eq_f with ((calling three.get_hypot with four) to f64), 5.0, eps, "hypot 3,4"
    calling eq_f with ((calling zero.get_hypot with zero) to f64), 0.0, eps, "hypot 0,0"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
