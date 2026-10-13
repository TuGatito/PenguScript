"""Phase 2.5 — `Real` end to end: Pengu source, real C compiler, real process.

Marked ``slow`` and skipped without a C compiler (or without a built runtime):
this is the only case in the `Real` feature that shells out, and it is kept in
its own file so `pengu selftest --smoke` — which selects whole files by the
``smoke`` marker — can never pick it up. A file that carries *both* markers
would look fast and compile C.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


def test_real_method_end_to_end(compile_and_run):
    """Float-only methods run for both widths and print the right values."""
    out = compile_and_run("""
import std.spark

enchanting shard T where T: Real:
    weave is_zero_f into bool:
        return self == donum T
    weave double_f into T:
        return self + self

weave main into int:
    var x as f64 is 0.0
    var y as f32 is 21.0
    if calling x.is_zero_f:
        calling spark.println with "x es cero"
    calling spark.println with "y*2 = {calling y.double_f}"
    return 0
""", tag="real")
    assert "x es cero" in out and "y*2 = 42" in out, out
