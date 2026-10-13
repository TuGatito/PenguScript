"""`std.arithmancy` — the scalar API delegates to the primitive modules.

Three programs, one per destination module. Each checks that the historical
`arithmancy.X` call and the method it now delegates to agree; where the two are
not bit-for-bit obligated to agree (the `libm` wrappers widen `float` to
`double`), the comparison uses a tolerance.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.arithmancy
import std.numerus

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_f with got as float, want as float, eps as float, name as string into void:
    var d as float is got - want
    if d < 0.0:
        set d is 0.0 - d
    if d > eps:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_numerus_delegations(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var i as int is -5
    calling eq_i with (calling arithmancy.abs_i with i), (calling i.abs), "abs_i"
    calling eq_i with (calling arithmancy.abs_i with 5), 5, "abs_i positive"
    calling eq_i with (calling arithmancy.sign_i with i), (calling i.signum), "sign_i"
    var a as int is 3
    var b as int is 7
    calling eq_i with (calling arithmancy.min_i with a, b), (calling a.min_with with b), "min_i"
    calling eq_i with (calling arithmancy.max_i with a, b), (calling a.max_with with b), "max_i"
    var hundred as int is 100
    calling eq_i with (calling arithmancy.clamp_i with hundred, 0, 50), (calling hundred.clamp with 0, 50), "clamp_i"
    var f as float is -2.5
    calling eq_f with (calling arithmancy.abs with f), (calling f.abs), 0.0, "abs"
    calling eq_f with (calling arithmancy.sign with f), (calling f.signum), 0.0, "sign"
    var p as float is 3.0
    var q as float is 7.0
    calling eq_f with (calling arithmancy.min with p, q), (calling p.min_with with q), 0.0, "min"
    calling eq_f with (calling arithmancy.max with p, q), (calling p.max_with with q), 0.0, "max"
    var hundred_f as float is 100.0
    calling eq_f with (calling arithmancy.clamp with hundred_f, 0.0, 50.0), (calling hundred_f.clamp with 0.0, 50.0), 0.0, "clamp"
    calling eq_f with (calling arithmancy.lerp with 0.0, 10.0, 0.5), 5.0, 0.0, "lerp"
    var r as float is 2.6
    calling eq_i with (calling arithmancy.to_int_round with r), (calling r.round to int), "to_int_round"
    calling eq_i with (calling arithmancy.to_int_floor with r), (calling r.floor to int), "to_int_floor"
    var s as float is 2.4
    calling eq_i with (calling arithmancy.to_int_ceil with s), (calling s.ceil to int), "to_int_ceil"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_integrum_delegations(compile_and_run):
    out = compile_and_run(_PREAMBLE.replace("import std.numerus", "import std.integrum") + """
weave main into int:
    var big as int is 7919
    var twelve as int is 12
    var eighteen as int is 18
    var four as int is 4
    var six as int is 6
    var eight as int is 8
    calling eq_i with (calling arithmancy.gcd with twelve, eighteen), (calling twelve.gcd with eighteen), "gcd"
    calling eq_i with (calling arithmancy.lcm with four, six), (calling four.lcm with six), "lcm"
    var g1 as bool is calling arithmancy.is_prime with big
    var g2 as bool is calling big.is_prime
    if g1 != g2:
        calling spark.println with "FAIL is_prime: {g1} != {g2}"
    calling eq_i with (calling arithmancy.gcd with twelve, eighteen), 6, "gcd value"
    calling eq_i with (calling arithmancy.lcm with four, six), 12, "lcm value"
    var p as bool is calling arithmancy.is_power_of_two with eight
    var q as bool is calling eight.is_power_of_two
    if p != q:
        calling spark.println with "FAIL is_power_of_two"
    var mersenne as int is 2147483647
    var m1 as bool is calling arithmancy.is_prime with mersenne
    var m2 as bool is calling mersenne.is_prime
    if m1 != m2:
        calling spark.println with "FAIL is_prime INT_MAX: {m1} != {m2}"
    if not m1:
        calling spark.println with "FAIL INT_MAX should be prime"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_fractio_delegations(compile_and_run):
    out = compile_and_run(_PREAMBLE.replace("import std.numerus", "import std.fractio") + """
weave main into int:
    calling eq_f with (calling arithmancy.sqrt with 4.0), 2.0, 0.0, "sqrt"
    calling eq_f with (calling arithmancy.pow with 2.0, 10.0), 1024.0, 0.0, "pow"
    calling eq_f with (calling arithmancy.sin with 0.0), 0.0, 0.0, "sin"
    calling eq_f with (calling arithmancy.cos with 0.0), 1.0, 0.0, "cos"
    calling eq_f with (calling arithmancy.tan with 0.0), 0.0, 0.0, "tan"
    calling eq_f with (calling arithmancy.asin with 1.0), 1.5707963267948966, 1e-6, "asin"
    calling eq_f with (calling arithmancy.acos with 1.0), 0.0, 0.0, "acos"
    calling eq_f with (calling arithmancy.atan with 1.0), 0.7853981633974483, 1e-6, "atan"
    calling eq_f with (calling arithmancy.atan2 with 1.0, 1.0), 0.7853981633974483, 1e-6, "atan2"
    calling eq_f with (calling arithmancy.exp with 0.0), 1.0, 0.0, "exp"
    calling eq_f with (calling arithmancy.log with 1.0), 0.0, 0.0, "log"
    calling eq_f with (calling arithmancy.log10 with 100.0), 2.0, 0.0, "log10"
    calling eq_f with (calling arithmancy.log2 with 8.0), 3.0, 0.0, "log2"
    calling eq_f with (calling arithmancy.hypot with 3.0, 4.0), 5.0, 0.0, "hypot"
    calling eq_f with (calling arithmancy.deg_to_rad with 180.0), 3.141592653589793, 1e-6, "deg_to_rad"
    calling eq_f with (calling arithmancy.rad_to_deg with 3.141592653589793), 180.0, 1e-3, "rad_to_deg"
    var x as float is 2.5
    calling eq_f with (calling arithmancy.sqrt with x), (calling x.sqrt), 1e-6, "sqrt matches method"
    var y as float is -1.0
    var bad1 as float is calling arithmancy.sqrt with y
    var bad2 as float is calling y.sqrt
    if (bad1 != bad1) != (bad2 != bad2):
        calling spark.println with "FAIL NaN agreement"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
