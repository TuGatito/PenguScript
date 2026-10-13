"""`std.integrum` — `gcd` and `lcm`.

Two programs: the GCD (classic pair, zero identities, negatives, coprimes) and
the LCM (classic pair, zero, negatives, overflow-resistant formula).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.integrum

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_gcd(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as int is 12
    var b as int is 18
    calling eq_i with (calling a.gcd with b), 6, "gcd 12 18"
    calling eq_i with (calling b.gcd with a), 6, "gcd 18 12"
    var z as int is 0
    var n as int is 15
    calling eq_i with (calling z.gcd with n), 15, "gcd 0 n"
    calling eq_i with (calling n.gcd with z), 15, "gcd n 0"
    calling eq_i with (calling z.gcd with z), 0, "gcd 0 0"
    var c as int is 9
    var d as int is 28
    calling eq_i with (calling c.gcd with d), 1, "coprimes"
    var m as int is -12
    var p as int is 18
    var q as int is 12
    var r as int is -18
    calling eq_i with (calling m.gcd with p), 6, "gcd -12 18 is non-negative"
    calling eq_i with (calling q.gcd with r), 6, "gcd 12 -18 is non-negative"
    var wide as i64 is 48
    var gw as i64 is calling wide.gcd with 18
    calling eq_i with (gw to int), 6, "i64 gcd"
    var small as u8 is 12
    calling eq_i with (calling small.gcd with 18), 6, "u8 gcd"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_lcm(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as int is 4
    var b as int is 6
    calling eq_i with (calling a.lcm with b), 12, "lcm 4 6"
    calling eq_i with (calling b.lcm with a), 12, "lcm 6 4"
    var z as int is 0
    var n as int is 9
    calling eq_i with (calling z.lcm with n), 0, "lcm 0 n"
    calling eq_i with (calling n.lcm with z), 0, "lcm n 0"
    var m as int is -4
    var p as int is 6
    calling eq_i with (calling m.lcm with p), 12, "lcm -4 6 is non-negative"
    var e as int is 21
    var f as int is 6
    calling eq_i with (calling e.lcm with f), 42, "lcm 21 6"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
