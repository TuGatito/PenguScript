"""`std.fractio` — the `libm` transcendentals on the 64-bit width.

Three programs mirroring the 32-bit file, but on `f64`/`double` with a tight
tolerance. Because `f64` is not the default float width, this also pins that the
literal precision fix really delivers double precision.
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


def test_roots_and_logs_f64(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-12
    var four as f64 is 4.0
    var two as f64 is 2.0
    var nine as double is 9.0
    var neg as f64 is -8.0
    var eight as f64 is 8.0
    var one as f64 is 1.0
    var e as f64 is 2.718281828459045
    var lo as f64 is 1024.0
    var hundred as f64 is 100.0
    calling eq_f with (calling four.sqrt), 2.0, eps, "sqrt 4"
    calling eq_f with (calling nine.sqrt), 3.0, eps, "sqrt 9 (double)"
    calling eq_f with (calling two.sqrt), 1.4142135623730951, eps, "sqrt 2 irrational"
    calling eq_f with (calling eight.cbrt), 2.0, eps, "cbrt 8"
    calling eq_f with (calling neg.cbrt), -2.0, eps, "cbrt -8"
    calling eq_f with (calling one.ln), 0.0, eps, "ln 1"
    calling eq_f with (calling e.ln), 1.0, eps, "ln e"
    calling eq_f with (calling eight.log2), 3.0, eps, "log2 8"
    calling eq_f with (calling lo.log2), 10.0, eps, "log2 1024"
    calling eq_f with (calling hundred.log10), 2.0, eps, "log10 100"
    var zero as f64 is 0.0
    var onef as f64 is 1.0
    calling eq_f with (calling zero.exp), 1.0, eps, "exp 0"
    calling eq_f with (calling onef.exp), 2.718281828459045, eps, "exp 1"
    var minus as f64 is -1.0
    var bad as f64 is calling minus.sqrt
    calling eq_b with (calling bad.is_nan), true, "sqrt(-1) is NaN"
    var badlog as f64 is calling minus.ln
    calling eq_b with (calling badlog.is_nan), true, "ln(-1) is NaN"
    var zero_log as f64 is calling zero.ln
    calling eq_b with (calling zero_log.is_negative_infinity), true, "ln(0) is -Inf"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_trigonometry_f64(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-12
    var zero as f64 is 0.0
    var one as f64 is 1.0
    var pi as f64 is 3.141592653589793
    var half as f64 is pi / 2.0
    var quarter as f64 is pi / 4.0
    calling eq_f with (calling zero.sin), 0.0, eps, "sin 0"
    calling eq_f with (calling half.sin), 1.0, eps, "sin pi/2"
    calling eq_f with (calling zero.cos), 1.0, eps, "cos 0"
    calling eq_f with (calling half.cos), 0.0, eps, "cos pi/2"
    calling eq_f with (calling zero.tan), 0.0, eps, "tan 0"
    calling eq_f with (calling quarter.tan), 1.0, eps, "tan pi/4"
    calling eq_f with (calling one.asin), 1.5707963267948966, eps, "asin 1"
    calling eq_f with (calling one.acos), 0.0, eps, "acos 1"
    calling eq_f with (calling one.atan), 0.7853981633974483, eps, "atan 1"
    var two as f64 is 2.0
    var bad as f64 is calling two.asin
    calling eq_b with (calling bad.is_nan), true, "asin 2 is NaN"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_two_argument_functions_f64(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var eps as f64 is 1e-12
    var one as f64 is 1.0
    var two as f64 is 2.0
    var three as f64 is 3.0
    var four as f64 is 4.0
    var zero as f64 is 0.0
    calling eq_f with (calling one.atan2 with one), 0.7853981633974483, eps, "atan2(1,1)"
    calling eq_f with (calling zero.atan2 with one), 0.0, eps, "atan2(0,1)"
    calling eq_f with (calling two.pow with 10.0), 1024.0, eps, "pow 2^10"
    calling eq_f with (calling two.pow with 0.0), 1.0, eps, "pow 2^0"
    calling eq_f with (calling two.pow with -1.0), 0.5, eps, "pow 2^-1"
    calling eq_f with (calling three.hypot with four), 5.0, eps, "hypot 3,4"
    calling eq_f with (calling zero.hypot with zero), 0.0, eps, "hypot 0,0"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
