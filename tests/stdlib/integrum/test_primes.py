"""`std.integrum` — primes and factorial.

Two programs: `next_prime`/`prev_prime` and `factorial` (within the documented
safe limits; the debug profile traps signed overflow with `-ftrapv`, so the
tests never exceed them).
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


def test_next_and_prev_prime(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var one as int is 1
    var two as int is 2
    var three as int is 3
    var thirteen as int is 13
    var hundred as int is 100
    calling eq_i with (calling zero.next_prime), 2, "next_prime 0"
    calling eq_i with (calling one.next_prime), 2, "next_prime 1"
    calling eq_i with (calling two.next_prime), 3, "next_prime 2"
    calling eq_i with (calling thirteen.next_prime), 17, "next_prime 13"
    calling eq_i with (calling hundred.next_prime), 101, "next_prime 100"
    calling eq_i with (calling two.prev_prime), 0, "prev_prime 2"
    calling eq_i with (calling three.prev_prime), 2, "prev_prime 3"
    calling eq_i with (calling hundred.prev_prime), 97, "prev_prime 100"
    calling eq_i with (calling one.prev_prime), 0, "prev_prime 1"
    var wide as i64 is 100
    calling eq_i with (calling wide.next_prime to int), 101, "i64 next_prime"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_factorial(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var one as int is 1
    var five as int is 5
    var ten as int is 10
    var twelve as int is 12
    calling eq_i with (calling zero.factorial), 1, "0!"
    calling eq_i with (calling one.factorial), 1, "1!"
    calling eq_i with (calling five.factorial), 120, "5!"
    calling eq_i with (calling ten.factorial), 3628800, "10!"
    calling eq_i with (calling twelve.factorial), 479001600, "12! (largest safe in i32)"
    var wide as i64 is 12
    calling eq_i with (calling wide.factorial to int), 479001600, "i64 12!"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
