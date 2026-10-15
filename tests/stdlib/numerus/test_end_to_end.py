"""`std.numerus` — end to end: the module's own tests, a realistic pipeline and
the monomorphization guarantee.

Three levels:

* the embedded ``test`` blocks, run through ``pengu test`` (the same command a
  contributor runs by hand);
* a **realistic** program that chains `abs`, `clamp` and `round` the way a game
  or report would;
* every canonical primitive spelling, proving one `enchanting shard` declaration
  really covers all of them (the emitted C symbols are then asserted on the
  generated bundle, without a C compiler in the loop).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/numerus/test_end_to_end.py`` -> `numerus` -> `stdlib` ->
#: `tests` -> the checkout.
ROOT = Path(__file__).resolve().parents[3]


def test_module_self_tests_pass():
    """``pengu test --entry std/numerus.pengu``: all embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "numerus.pengu")],
        capture_output=True, text=True, timeout=300,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 69 test(s) passed." in res.stdout, res.stdout


def test_realistic_pipeline(compile_and_run):
    """Normalize a raw score into ``[0, 100]`` and round it."""
    out = compile_and_run("""
import std.spark
import std.numerus

weave main into int:
    var raw as f64 is 145.7
    var clamped as f64 is calling raw.get_clamp with 0.0, 100.0
    var rounded as f64 is calling clamped.get_round
    calling spark.println with "{rounded to int}"
    var bonus as f64 is -12.5
    var magnitude as f64 is calling bonus.get_abs
    var normalized as int is calling magnitude.get_round to int
    calling spark.println with "{normalized}"
    return 0
""")
    assert "100" in out, out
    assert "13" in out, out


def test_every_primitive_spelling_gets_a_method(compile_and_run):
    """All 11 canonical types, reached through 15 accepted spellings."""
    out = compile_and_run("""
import std.spark
import std.numerus

weave main into int:
    var a as int is -1
    var b as i8 is -2
    var c as i16 is -3
    var d as i32 is -4
    var e as i64 is -5
    var f as u8 is 6
    var g as u16 is 7
    var h as u32 is 8
    var i as u64 is 9
    var j as usize is 10
    var k as isize is -11
    var l as byte is 12
    var m as float is -1.5
    var n as f32 is -2.5
    var o as f64 is -3.5
    var p as double is -4.5
    var total as int is 0
    set total is total + (calling a.get_abs)
    set total is total + (calling b.get_abs)
    set total is total + (calling c.get_abs)
    set total is total + (calling d.get_abs)
    set total is total + (calling e.get_abs to int)
    set total is total + (calling f.get_abs)
    set total is total + (calling g.get_abs)
    set total is total + (calling h.get_abs)
    set total is total + (calling i.get_abs)
    set total is total + (calling j.get_abs)
    set total is total + (calling k.get_abs to int)
    set total is total + (calling l.get_abs)
    set total is total + (calling m.get_abs to int)
    set total is total + (calling n.get_abs to int)
    set total is total + (calling o.get_abs to int)
    set total is total + (calling p.get_abs to int)
    calling spark.println with "{total}"
    return 0
""")
    # 1+2+3+4+5+6+7+8+9+10+11+12 + truncations 1+2+3+4 = 78 + 10 = 88
    assert "88" in out, out


def test_monomorphized_symbols_are_emitted(tmp_path):
    """The bundle contains one plain C function per concrete receiver."""
    source = tmp_path / "monomorphize_probe.pengu"
    source.write_text(
        "import std.numerus\n"
        "weave main into int:\n"
        "    var a as int is -5\n"
        "    var b as f64 is -2.5\n"
        "    var c as u32 is 7\n"
        "    let x is calling a.get_abs\n"
        "    let y is calling b.get_clamp with 0.0, 1.0\n"
        "    let z is calling c.get_signum\n"
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
    for symbol in ("int_abs", "f64_clamp", "u32_signum"):
        assert re.search(rf"\b{re.escape(symbol)}\b", bundle), (
            f"{symbol} missing from the bundle"
        )
    assert "pengu_abs" not in bundle, "symbols must not carry a pengu_ prefix"
