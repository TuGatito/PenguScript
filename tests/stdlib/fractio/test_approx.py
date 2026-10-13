"""`std.fractio` — approximation and pure utilities.

Two programs: `approx_eq` (absolute tolerance) and the utility trio
(`reciprocal`, `lerp`, `copysign`).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.fractio

weave eq_f with got as f64, want as f64, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_approx_eq(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var one as f64 is 1.0
    var same as f64 is 1.0
    var close as f64 is 1.0000000001
    var far as f64 is 1.001
    var sum as f64 is 0.1 + 0.2
    var third as f64 is 0.3
    var neg as f64 is -2.5
    var neg_same as f64 is -2.5
    var neg_off as f64 is -2.6
    calling eq_b with (calling one.approx_eq with same, 1e-9), true, "exact"
    calling eq_b with (calling one.approx_eq with close, 1e-9), true, "within eps"
    calling eq_b with (calling one.approx_eq with far, 1e-9), false, "outside eps"
    calling eq_b with (calling one.approx_eq with far, 1e-2), true, "looser eps"
    calling eq_b with (calling sum.approx_eq with third, 1e-9), true, "0.1+0.2"
    calling eq_b with (calling neg.approx_eq with neg_same, 1e-9), true, "negative exact"
    calling eq_b with (calling neg.approx_eq with neg_off, 1e-9), false, "negative outside"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_reciprocal_lerp_copysign(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var two as f64 is 2.0
    var four as f64 is 4.0
    var neg as f64 is -1.0
    var zero as f64 is 0.0
    calling eq_f with (calling two.reciprocal), 0.5, "reciprocal 2"
    calling eq_f with (calling four.reciprocal), 0.25, "reciprocal 4"
    calling eq_f with (calling neg.reciprocal), -1.0, "reciprocal -1"
    var inf as f64 is calling zero.reciprocal
    calling eq_b with (calling inf.is_infinite), true, "reciprocal 0 -> Inf"
    var lo as f64 is 0.0
    var hi as f64 is 10.0
    calling eq_f with (calling lo.lerp with hi, 0.0), 0.0, "lerp t=0"
    calling eq_f with (calling lo.lerp with hi, 1.0), 10.0, "lerp t=1"
    calling eq_f with (calling lo.lerp with hi, 0.5), 5.0, "lerp t=0.5"
    calling eq_f with (calling lo.lerp with hi, 2.0), 20.0, "lerp extrapolates"
    var p as f64 is 3.0
    var n as f64 is -3.0
    var pos as f64 is 1.0
    calling eq_f with (calling p.copysign with neg), -3.0, "copysign + -"
    calling eq_f with (calling n.copysign with pos), 3.0, "copysign - +"
    calling eq_f with (calling p.copysign with pos), 3.0, "copysign + +"
    calling eq_f with (calling n.copysign with neg), -3.0, "copysign - -"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
