"""`std.integrum` — the bit operations.

Two programs: the bit queries (`bit_count`, `bit_length`, `leading_zeros`,
`trailing_zeros`) and the power-of-two rounding pair.
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


def test_bit_queries(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var one as int is 1
    var eleven as int is 0b1011
    var ff as int is 255
    var big as int is 256
    var neg as int is -1
    var wide as i64 is 255
    calling eq_i with (calling zero.bit_count), 0, "bit_count 0"
    calling eq_i with (calling one.bit_count), 1, "bit_count 1"
    calling eq_i with (calling eleven.bit_count), 3, "bit_count 0b1011"
    calling eq_i with (calling ff.bit_count), 8, "bit_count 255"
    calling eq_i with (calling neg.bit_count), 32, "bit_count -1 (sign bits)"
    calling eq_i with (calling zero.bit_length), 0, "bit_length 0"
    calling eq_i with (calling one.bit_length), 1, "bit_length 1"
    calling eq_i with (calling ff.bit_length), 8, "bit_length 255"
    calling eq_i with (calling big.bit_length), 9, "bit_length 256"
    calling eq_i with (calling wide.bit_length), 8, "bit_length i64 255"
    calling eq_i with (calling zero.leading_zeros), 32, "leading_zeros 0"
    calling eq_i with (calling one.leading_zeros), 31, "leading_zeros 1"
    calling eq_i with (calling ff.leading_zeros), 24, "leading_zeros 255"
    var x as int is 7919
    calling eq_i with ((calling x.leading_zeros) + (calling x.bit_length)), 32, "lz + bl == width"
    calling eq_i with (calling zero.trailing_zeros), 32, "trailing_zeros 0"
    calling eq_i with (calling one.trailing_zeros), 0, "trailing_zeros 1"
    var eight as int is 8
    var twelve as int is 12
    calling eq_i with (calling eight.trailing_zeros), 3, "trailing_zeros 8"
    calling eq_i with (calling twelve.trailing_zeros), 2, "trailing_zeros 12"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out


def test_power_of_two_rounding(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var zero as int is 0
    var one as int is 1
    var four as int is 4
    var five as int is 5
    var big as int is 1023
    calling eq_i with (calling zero.get_next_power_of_two), 1, "next 0"
    calling eq_i with (calling one.get_next_power_of_two), 2, "next 1"
    calling eq_i with (calling four.get_next_power_of_two), 8, "next 4"
    calling eq_i with (calling five.get_next_power_of_two), 8, "next 5"
    calling eq_i with (calling big.get_next_power_of_two), 1024, "next 1023"
    calling eq_i with (calling zero.get_prev_power_of_two), 0, "prev 0"
    calling eq_i with (calling one.get_prev_power_of_two), 1, "prev 1"
    calling eq_i with (calling four.get_prev_power_of_two), 4, "prev 4"
    calling eq_i with (calling five.get_prev_power_of_two), 4, "prev 5"
    calling eq_i with (calling big.get_prev_power_of_two), 512, "prev 1023"
    var narrow as u8 is 100
    calling eq_i with (calling narrow.get_next_power_of_two), 128, "next u8"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out
