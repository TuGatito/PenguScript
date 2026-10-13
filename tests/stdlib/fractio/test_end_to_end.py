"""`std.fractio` — end to end.

Four levels: the module's own embedded `test` blocks, a realistic geometry
program, the two-block monomorphization (`float_*` vs `f64_*`), and the raw
`libm` symbols in the emitted bundle.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/fractio/test_end_to_end.py`` -> `fractio` -> `stdlib` ->
#: `tests` -> the checkout.
ROOT = Path(__file__).resolve().parents[3]


def test_module_self_tests_pass():
    """``pengu test --entry std/fractio.pengu``: all embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "fractio.pengu")],
        capture_output=True, text=True, timeout=300,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 37 test(s) passed." in res.stdout, res.stdout


def test_realistic_geometry(compile_and_run):
    """A 3-4-5 triangle, its angle, and a normalized vector."""
    out = compile_and_run("""
import std.spark
import std.fractio
import std.numerus

weave main into int:
    var x as f64 is 3.0
    var y as f64 is 4.0
    var length as f64 is calling x.hypot with y
    calling spark.println with "{length}"
    var angle as f64 is calling y.atan2 with x
    var degrees as f64 is calling angle.degrees
    calling spark.println with "{calling degrees.round to int}"
    var unit as f64 is x / length
    calling spark.println with "{calling unit.approx_eq with 0.6, 1e-12}"
    return 0
""")
    assert "5" in out, out
    assert "53" in out, out
    assert "true" in out, out


def test_two_blocks_emit_per_width_symbols(tmp_path):
    """`float` and `f64` get distinct C symbols, and the libm symbols are real."""
    source = tmp_path / "fractio_symbols.pengu"
    source.write_text(
        "import std.fractio\n"
        "weave main into int:\n"
        "    var a as f64 is 4.0\n"
        "    var b as float is 4.0\n"
        "    var c as f32 is 4.0\n"
        "    let s1 is calling a.sqrt\n"
        "    let s2 is calling b.sqrt\n"
        "    let s3 is calling c.sin\n"
        "    let n1 is calling a.is_nan\n"
        "    let e1 is calling a.exp\n"
        "    let h1 is calling a.hypot with 3.0\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "expand", str(source)],
        capture_output=True, text=True, timeout=180,
        cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, f"expand failed:\n{res.stdout}\n{res.stderr}"
    bundle = res.stdout
    # One monomorphized wrapper per concrete receiver ...
    for symbol in ("f64_sqrt", "float_sqrt", "f64_is_nan", "f64_exp", "f64_hypot"):
        assert re.search(rf"\b{re.escape(symbol)}\b", bundle), f"{symbol} missing"
    # ... each calling the real C99 symbol of the matching width.
    assert re.search(r"\bsqrtf\(", bundle), "sqrtf call missing"
    assert re.search(r"\bsqrt\(", bundle), "sqrt call missing"
    assert "pengu_sqrt" not in bundle, "symbols must not carry a pengu_ prefix"
