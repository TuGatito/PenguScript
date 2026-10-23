"""`std.integrum` — end to end.

Four levels: the module's own embedded `test` blocks, a realistic prime-counting
program, every canonical integer spelling, and the emitted symbols
(monomorphization + delegation to `std.numerus`).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/integrum/test_end_to_end.py`` -> `integrum` -> `stdlib` ->
#: `tests` -> the checkout.
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.xdist_group("pengu-module-tests")
def test_module_self_tests_pass():
    """``pengu test --entry std/integrum.pengu``: all embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "integrum.pengu")],
        capture_output=True, text=True, timeout=300,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 57 test(s) passed." in res.stdout, res.stdout


def test_realistic_prime_count(compile_and_run):
    """Count the primes below 30 and factor a pair through gcd/lcm."""
    out = compile_and_run("""
import std.spark
import std.integrum

weave main into int:
    var count as int is 0
    for i from 2 to 30:
        if calling i.is_prime:
            set count is count + 1
    calling spark.println with "{count}"
    var a as int is 12
    var b as int is 18
    calling spark.println with "{calling a.get_gcd with b} {calling a.get_lcm with b}"
    var h as string is calling a.to_hex
    calling spark.println with h
    banish h
    return 0
""")
    assert "10" in out, out
    assert "6 36" in out, out
    assert "c" in out, out


def test_every_integer_spelling_gets_methods(compile_and_run):
    """All 11 canonical integer types, reached through 16 accepted spellings."""
    out = compile_and_run("""
import std.spark
import std.integrum

weave main into int:
    var a as int is 4
    var b as i8 is 4
    var c as i16 is 4
    var d as i32 is 4
    var e as i64 is 4
    var f as u8 is 4
    var g as u16 is 4
    var h as u32 is 4
    var i as u64 is 4
    var j as usize is 4
    var k as isize is 4
    var l as byte is 4
    var total as int is 0
    if calling a.is_even:
        set total is total + 1
    if calling b.is_even:
        set total is total + 1
    if calling c.is_even:
        set total is total + 1
    if calling d.is_even:
        set total is total + 1
    if calling e.is_even:
        set total is total + 1
    if calling f.is_even:
        set total is total + 1
    if calling g.is_even:
        set total is total + 1
    if calling h.is_even:
        set total is total + 1
    if calling i.is_even:
        set total is total + 1
    if calling j.is_even:
        set total is total + 1
    if calling k.is_even:
        set total is total + 1
    if calling l.is_even:
        set total is total + 1
    set total is total + (calling a.get_gcd with 6)
    set total is total + (calling f.get_gcd with 6)
    set total is total + (calling h.get_gcd with 6)
    calling spark.println with "{total}"
    return 0
""")
    # 12 parity hits + 2 + 2 + 2 gcds = 18
    assert "18" in out, out


def test_monomorphized_symbols_and_delegation(tmp_path):
    """One plain C function per receiver, and `abs` is delegated to numerus."""
    source = tmp_path / "integrum_symbols.pengu"
    source.write_text(
        "import std.integrum\n"
        "weave main into int:\n"
        "    var a as int is -12\n"
        "    var b as i64 is -12\n"
        "    var c as u32 is 12\n"
        "    let g1 is calling a.get_gcd with 18\n"
        "    let g2 is calling b.get_gcd with 18\n"
        "    let p is calling c.get_next_prime\n"
        "    var h as string is calling a.to_hex\n"
        "    banish h\n"
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
    for symbol in ("int_gcd", "i64_gcd", "u32_next_prime",
                   "u32__is_prime_impl", "int_to_hex"):
        assert re.search(rf"\b{re.escape(symbol)}\b", bundle), (
            f"{symbol} missing from the bundle"
        )
    # `int__is_prime_impl` is only reachable from `int.get_next_prime`; this
    # program calls `u32.get_next_prime`, so DCE correctly drops the int copy.
    assert not re.search(r"\bint__is_prime_impl\b", bundle), (
        "an unreachable int specialization is still in the bundle"
    )
    # `gcd` normalizes through `abs`, which lives in std.numerus.
    assert re.search(r"\bint_abs\b", bundle), "delegation to numerus.abs missing"
    assert "pengu_gcd" not in bundle, "symbols must not carry a pengu_ prefix"
