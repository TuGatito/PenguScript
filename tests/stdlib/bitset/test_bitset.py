"""``std.bitset`` — fixed-length bit sets, set algebra and searches."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.bitset

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_bitset_constructors_bits_and_bulk(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var z as BitSet is calling BitSet.new with 0
    defer banish z
    calling eq_i with (calling z.bit_len), 0, "zero bits"
    calling eq_i with (calling z.count_ones), 0, "zero ones"
    calling eq_b with (calling z.is_empty), true, "zero empty"
    calling eq_b with (calling z.is_full), true, "zero full"
    calling eq_b with (calling z.any), false, "zero any"
    calling eq_b with (calling z.all), true, "zero all"

    var one as BitSet is calling BitSet.new with 1
    defer banish one
    calling eq_i with (calling one.count_zeros), 1, "one zeros"
    calling one.set with 0
    calling eq_b with (calling one.get with 0), true, "one set"
    calling one.clear with 0
    calling eq_b with (calling one.get with 0), false, "one clear"
    calling one.toggle with 0
    calling eq_b with (calling one.get with 0), true, "one toggle"
    calling one.set_to with 0, false
    calling eq_b with (calling one.get with 0), false, "one set_to false"

    var eight as BitSet is calling BitSet.new with 8
    defer banish eight
    calling eight.set_all
    calling eq_i with (calling eight.count_ones), 8, "eight all"
    calling eq_b with (calling eight.is_full), true, "eight full"
    calling eight.clear_all
    calling eq_i with (calling eight.count_ones), 0, "eight clear"
    calling eight.toggle_all
    calling eq_i with (calling eight.count_ones), 8, "eight toggle"

    var nine as BitSet is calling BitSet.filled with 9
    defer banish nine
    calling eq_i with (calling nine.count_ones), 9, "nine filled"
    calling eq_i with (calling nine.count_zeros), 0, "nine zeros"
    var nv as slice of byte is calling nine.to_bytes
    calling eq_i with nv.length, 2, "nine bytes len"
    calling eq_i with ((nv at 1) to int), 1, "nine padding masked"
    var nn as BitSet is calling nine.not
    defer banish nn
    calling eq_i with (calling nn.count_ones), 0, "nine not ones"
    calling eq_i with (calling nn.count_zeros), 9, "nine not zeros"
    var nb as slice of byte is calling nn.to_bytes
    calling eq_i with ((nb at 1) to int), 0, "nine not padding"
    calling nine.not_in_place
    calling eq_i with (calling nine.count_ones), 0, "nine not in place"
    calling eq_i with (calling nine.count_zeros), 9, "nine not in place zeros"
    var nbb as slice of byte is calling nine.to_bytes
    calling eq_i with ((nbb at 1) to int), 0, "nine not in place padding"
    calling spark.println with "DONE"
    return 0
""")


def test_bitset_set_algebra_in_place_and_search(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as BitSet is calling BitSet.new with 10
    defer banish a
    var b as BitSet is calling BitSet.new with 10
    defer banish b
    calling a.set with 0
    calling a.set with 2
    calling a.set with 9
    calling b.set with 2
    calling b.set with 3

    var anded as BitSet is calling a.and_with with (sigil of b)
    defer banish anded
    var ored as BitSet is calling a.or_with with (sigil of b)
    defer banish ored
    var xored as BitSet is calling a.xor_with with (sigil of b)
    defer banish xored
    var anot as BitSet is calling a.and_not_with with (sigil of b)
    defer banish anot
    calling eq_i with (calling anded.count_ones), 1, "and ones"
    calling eq_b with (calling anded.get with 2), true, "and bit2"
    calling eq_i with (calling ored.count_ones), 4, "or ones"
    calling eq_b with (calling ored.get with 3), true, "or bit3"
    calling eq_i with (calling xored.count_ones), 3, "xor ones"
    calling eq_i with (calling anot.count_ones), 2, "and_not ones"
    calling eq_b with (calling anot.get with 0), true, "and_not bit0"
    calling eq_b with (calling anot.get with 2), false, "and_not bit2"

    var cp as BitSet is calling a.copy
    defer banish cp
    calling eq_b with (calling a.equals with (sigil of cp)), true, "copy equals"
    calling cp.toggle with 0
    calling eq_b with (calling a.equals with (sigil of cp)), false, "copy differs"
    var small as BitSet is calling BitSet.new with 9
    defer banish small
    calling eq_b with (calling a.equals with (sigil of small)), false, "different len equals"

    var ip as BitSet is calling a.copy
    defer banish ip
    calling ip.and_in_place with (sigil of b)
    calling eq_i with (calling ip.count_ones), 1, "and in place"
    var ip2 as BitSet is calling a.copy
    defer banish ip2
    calling ip2.or_in_place with (sigil of b)
    calling eq_i with (calling ip2.count_ones), 4, "or in place"
    var ip3 as BitSet is calling a.copy
    defer banish ip3
    calling ip3.xor_in_place with (sigil of b)
    calling eq_i with (calling ip3.count_ones), 3, "xor in place"
    var ip4 as BitSet is calling a.copy
    defer banish ip4
    calling ip4.and_not_in_place with (sigil of b)
    calling eq_i with (calling ip4.count_ones), 2, "and_not in place"

    var f as BitSet is calling BitSet.new with 10
    defer banish f
    var none_i as maybe int is calling f.find_first_set
    calling eq_b with none_i.is_present, false, "find none"
    banish none_i
    calling f.set with 5
    var first as maybe int is calling f.find_first_set
    if v as int is first:
        calling eq_i with v, 5, "find first"
    else:
        calling spark.println with "FAIL find first none"
    banish first
    var next0 as maybe int is calling f.find_next_set with 0
    if v2 as int is next0:
        calling eq_i with v2, 5, "find next 0"
    else:
        calling spark.println with "FAIL find next 0"
    banish next0
    var next6 as maybe int is calling f.find_next_set with 6
    calling eq_b with next6.is_present, false, "find next 6 none"
    banish next6
    var firstclear as maybe int is calling f.find_first_clear
    if v3 as int is firstclear:
        calling eq_i with v3, 0, "find first clear"
    else:
        calling spark.println with "FAIL find first clear"
    banish firstclear
    var nclear as maybe int is calling f.find_next_clear with 5
    if v4 as int is nclear:
        calling eq_i with v4, 6, "find next clear"
    else:
        calling spark.println with "FAIL find next clear"
    banish nclear
    var fullset as BitSet is calling BitSet.filled with 10
    defer banish fullset
    var fc as maybe int is calling fullset.find_first_clear
    calling eq_b with fc.is_present, false, "full clear none"
    banish fc

    var it as list of int is calling a.iter_set
    defer banish it
    calling eq_i with it.len, 3, "iter len"
    calling eq_i with (it at 0), 0, "iter 0"
    calling eq_i with (it at 1), 2, "iter 2"
    calling eq_i with (it at 2), 9, "iter 9"
    calling spark.println with "DONE"
    return 0
""")


def test_bitset_from_bytes_and_large_popcount(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var raw as array of byte with size 2 is [255, 1]
    var view as slice of byte is raw at 0 to 2
    var fromb as BitSet is calling BitSet.from_bytes with view, 9
    defer banish fromb
    calling eq_i with (calling fromb.count_ones), 9, "from bytes ones"
    var fb as slice of byte is calling fromb.to_bytes
    calling eq_i with ((fb at 1) to int), 1, "from bytes masks padding"

    var big as BitSet is calling BitSet.new with 1000
    defer banish big
    var i as int is 0
    while i < 1000:
        if i % 3 == 0:
            calling big.set with i
        set i is i + 1
    var expected as int is 0
    set i is 0
    while i < 1000:
        if i % 3 == 0:
            set expected is expected + 1
        set i is i + 1
    calling eq_i with (calling big.count_ones), expected, "big popcount"
    var bigcopy as BitSet is calling big.copy
    defer banish bigcopy
    calling eq_b with (calling big.equals with (sigil of bigcopy)), true, "big copy equals"
    var iter as list of int is calling big.iter_set
    defer banish iter
    calling eq_i with iter.len, expected, "big iter len"
    calling eq_i with (iter at 0), 0, "big iter first"
    calling spark.println with "DONE"
    return 0
""")


@pytest.mark.parametrize("body, expected", [
    ("var b as BitSet is calling BitSet.new with -1", "negative bit length"),
    ("var b as BitSet is calling BitSet.new with 1\n    calling b.set with 1", "bit index out of bounds"),
    ("var b as BitSet is calling BitSet.new with 8\n    var c as BitSet is calling BitSet.new with 9\n    var d as BitSet is calling b.and_with with (sigil of c)", "bit lengths differ"),
    ("var b as BitSet is calling BitSet.new with 8\n    var m as maybe int is calling b.find_next_set with -1", "negative index"),
])
def test_bitset_panics_are_fatal(run_pengu, body, expected):
    res = run_pengu(f"""
import std.spark
import std.bitset

weave main into int:
    {body}
    calling spark.println with "SHOULD NOT REACH"
    return 0
""")
    assert res.returncode != 0
    assert expected in (res.stderr + res.stdout), (res.stdout, res.stderr)
