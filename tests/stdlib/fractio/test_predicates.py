"""`std.fractio` — IEEE 754 classification.

Two programs: NaN detection and the infinity family (including `is_finite`).
NaN comes from `sqrt(-1)` and Inf from `reciprocal(0)`, so nothing relies on
undefined behaviour; floating-point division by zero is plain IEEE 754 and does
not abort in the debug profile.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.fractio

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_nan_classification(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var neg as f64 is -1.0
    var bad as f64 is calling neg.sqrt
    var also_bad as f64 is (0.0 / 0.0)
    var one as f64 is 1.0
    var zero as f64 is 0.0
    var inf as f64 is calling zero.reciprocal
    calling eq_b with (calling bad.is_nan), true, "sqrt(-1) is NaN"
    calling eq_b with (calling also_bad.is_nan), true, "0/0 is NaN"
    calling eq_b with (calling one.is_nan), false, "1 is not NaN"
    calling eq_b with (calling zero.is_nan), false, "0 is not NaN"
    calling eq_b with (calling inf.is_nan), false, "Inf is not NaN"
    calling eq_b with (calling bad.is_finite), false, "NaN is not finite"
    calling eq_b with (calling inf.is_finite), false, "Inf is not finite"
    calling eq_b with (calling one.is_finite), true, "1 is finite"
    calling eq_b with (calling bad.is_infinite), false, "NaN is not infinite"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_infinity_family(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as f64 is 0.0
    var pos as f64 is calling zero.reciprocal
    var ninf as f64 is (0.0 - 1.0) / zero
    var one as f64 is 1.0
    var neg as f64 is -1.0
    var bad as f64 is calling neg.sqrt
    calling eq_b with (calling pos.is_infinite), true, "+Inf is infinite"
    calling eq_b with (calling ninf.is_infinite), true, "-Inf is infinite"
    calling eq_b with (calling one.is_infinite), false, "1 is finite"
    calling eq_b with (calling bad.is_infinite), false, "NaN is not infinite"
    calling eq_b with (calling pos.is_positive_infinity), true, "+Inf"
    calling eq_b with (calling ninf.is_positive_infinity), false, "-Inf is not +Inf"
    calling eq_b with (calling one.is_positive_infinity), false, "1 is not +Inf"
    calling eq_b with (calling ninf.is_negative_infinity), true, "-Inf"
    calling eq_b with (calling pos.is_negative_infinity), false, "+Inf is not -Inf"
    calling eq_b with (calling bad.is_negative_infinity), false, "NaN is not -Inf"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
