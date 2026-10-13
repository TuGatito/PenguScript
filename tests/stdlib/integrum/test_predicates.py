"""`std.integrum` — the predicate family.

Two programs: the small integer predicates (`is_even`, `is_odd`,
`is_power_of_two`, `is_multiple_of`) and primality (`is_prime`).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.integrum

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_parity_and_multiples(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as int is 4
    var b as int is 5
    var c as int is -4
    var d as int is -7
    var z as int is 0
    var w as i64 is 100
    var n as u8 is 3
    calling eq_b with (calling a.is_even), true, "even positive"
    calling eq_b with (calling b.is_even), false, "odd positive"
    calling eq_b with (calling c.is_even), true, "even negative"
    calling eq_b with (calling z.is_even), true, "zero is even"
    calling eq_b with (calling w.is_even), true, "i64 even"
    calling eq_b with (calling n.is_even), false, "u8 odd"
    calling eq_b with (calling d.is_odd), true, "odd negative"
    calling eq_b with (calling a.is_odd), false, "even is not odd"
    var m as int is 12
    var five as int is 5
    calling eq_b with (calling m.is_multiple_of with 4), true, "exact multiple"
    calling eq_b with (calling m.is_multiple_of with five), false, "not a multiple"
    calling eq_b with (calling z.is_multiple_of with 7), true, "zero is a multiple"
    calling eq_b with (calling c.is_multiple_of with 4), true, "negative multiple"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_power_of_two_and_primality(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var one as int is 1
    var two as int is 2
    var four as int is 4
    var three as int is 3
    var six as int is 6
    var zero as int is 0
    var neg as int is -4
    calling eq_b with (calling one.is_power_of_two), true, "one is a power of two"
    calling eq_b with (calling two.is_power_of_two), true, "two"
    calling eq_b with (calling four.is_power_of_two), true, "four"
    calling eq_b with (calling three.is_power_of_two), false, "three"
    calling eq_b with (calling six.is_power_of_two), false, "six"
    calling eq_b with (calling zero.is_power_of_two), false, "zero"
    calling eq_b with (calling neg.is_power_of_two), false, "negative"
    var a as int is 0
    var b as int is 1
    var c as int is 2
    var d as int is 4
    var e as int is 17
    var f as int is 100
    var g as int is 7919
    var h as int is 7920
    calling eq_b with (calling a.is_prime), false, "0 not prime"
    calling eq_b with (calling b.is_prime), false, "1 not prime"
    calling eq_b with (calling c.is_prime), true, "2 prime"
    calling eq_b with (calling d.is_prime), false, "4 not prime"
    calling eq_b with (calling e.is_prime), true, "17 prime"
    calling eq_b with (calling f.is_prime), false, "100 not prime"
    calling eq_b with (calling g.is_prime), true, "7919 prime"
    calling eq_b with (calling h.is_prime), false, "7920 not prime"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
