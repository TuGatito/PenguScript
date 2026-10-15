"""`std.arithmancy` — end to end, plus the kept (non-delegated) semantics.

Two levels: a realistic pipeline that mixes the historical API with the new
modules, and the regressions that pin the six functions which deliberately do
**not** delegate (`floor`/`ceil`/`round`/`trunc` keep the full C domain,
`approx_eq` keeps `<=`, `next_power_of_two` keeps "at least n").
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.arithmancy
import std.numerus
import std.fractio

weave eq_f with got as float, want as float, eps as float, name as string into void:
    var d as float is got - want
    if d < 0.0:
        set d is 0.0 - d
    if d > eps:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_kept_full_domain_rounding(compile_and_run):
    """`floor`/`ceil`/`round`/`trunc` cover the whole `float` range.

    `numerus`'s versions round through `int`; these are the C functions, so a
    magnitude beyond `int` must survive untouched. Delegating them would have
    silently broken this.
    """
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var big as float is 2.7e20
    calling eq_f with (calling arithmancy.floor with big), big, 0.0, "floor 2.7e20"
    calling eq_f with (calling arithmancy.ceil with big), big, 0.0, "ceil 2.7e20"
    calling eq_f with (calling arithmancy.round with big), big, 0.0, "round 2.7e20"
    calling eq_f with (calling arithmancy.trunc with big), big, 0.0, "trunc 2.7e20"
    var neg as float is -2.5
    calling eq_f with (calling arithmancy.floor with neg), -3.0, 0.0, "floor -2.5"
    calling eq_f with (calling arithmancy.ceil with neg), -2.0, 0.0, "ceil -2.5"
    calling eq_f with (calling arithmancy.round with neg), -3.0, 0.0, "round -2.5"
    calling eq_f with (calling arithmancy.trunc with neg), -2.0, 0.0, "trunc -2.5"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_kept_boundary_and_integer_semantics(compile_and_run):
    """`approx_eq` is `<=`, `next_power_of_two` is `>=`, `fmod` is C `fmod`."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as float is 0.0
    var eps as float is 0.000001
    calling eq_b with (calling arithmancy.approx_eq with zero, eps, eps), true, "approx_eq boundary is inclusive"
    var four as int is 4
    calling eq_i with (calling arithmancy.next_power_of_two with four), 4, "next_power_of_two(4) is 4"
    var five as int is 5
    calling eq_i with (calling arithmancy.next_power_of_two with five), 8, "next_power_of_two(5) is 8"
    calling eq_f with (calling arithmancy.fmod with 7.0, 3.0), 1.0, 0.0, "fmod"
    calling eq_f with (calling arithmancy.fmod with -7.0, 3.0), -1.0, 0.0, "fmod negative"
    calling eq_f with (calling arithmancy.inv_sq with 2.0), 0.25, 0.0, "inv_sq"
    calling eq_f with (calling arithmancy.inv_sq with 0.0), 0.0, 0.0, "inv_sq zero"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_realistic_pipeline(compile_and_run):
    """A game-math pipeline mixing the old API and the new modules."""
    out = compile_and_run(_PREAMBLE + """
weave normalize_vec with x as float, y as float into arithmancy.Vec2:
    var len as float is calling arithmancy.hypot with x, y
    if len == 0.0:
        return with x is 0.0, y is 0.0
    return with x is x / len, y is y / len

weave main into int:
    var u as arithmancy.Vec2 is calling normalize_vec with 3.0, 4.0
    calling eq_f with u.x, 0.6, 1e-6, "normalized x"
    calling eq_f with u.y, 0.8, 1e-6, "normalized y"
    var raw as float is 145.7
    var clamped as float is calling arithmancy.clamp with raw, 0.0, 100.0
    var rounded as float is calling raw.get_round
    calling eq_f with clamped, 100.0, 1e-6, "clamp delegated"
    calling eq_f with rounded, 146.0, 1e-6, "round method"
    var angle as float is calling arithmancy.rad_to_deg with arithmancy.PI
    calling eq_f with angle, 180.0, 1e-3, "rad_to_deg"
    var g as int is calling arithmancy.gcd with 48, 18
    calling eq_i with g, 6, "gcd delegated"
    calling spark.println with "{rounded to int}"
    return 0
""")
    assert "FAIL" not in out, out
    assert "146" in out, out
