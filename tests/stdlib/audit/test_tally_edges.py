"""``std.tally`` — edge cases and leak churn over ``list of int`` / ``list of string``.

The edge program pins the documented identities (empty reductions, even-length
median, first-wins mode) and every list-returning helper is banished, so under
ASan the program also proves the module allocates nothing it does not return.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.tally

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"
"""


def test_tally_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    var xs as list of int is [3, 1, 4, 1, 5, 9, 2, 6]
    var empty as list of int is list of int
    var dup as list of int is [2, 2, 3, 3]
    var even as list of int is [1, 2, 3, 4]
    var one as list of int is [7]

    # empty reductions use the identity element
    calling eq_i with (calling tally.sum with empty), 0, "sum empty"
    calling eq_i with (calling tally.product with empty), 1, "product empty"
    calling eq_i with (calling tally.max_val with empty), 0, "max_val empty sentinel"
    calling eq_i with (calling tally.min_val with empty), 0, "min_val empty sentinel"
    calling eq_i with (calling tally.median with empty), 0, "median empty"
    calling eq_i with (calling tally.mode with empty), 0, "mode empty"
    calling eq_i with (calling tally.max_index with empty), 0 - 1, "max_index empty is -1"

    # filled reductions
    calling eq_i with (calling tally.sum with xs), 31, "sum"
    calling eq_i with (calling tally.max_val with xs), 9, "max_val"
    calling eq_i with (calling tally.min_val with xs), 1, "min_val"
    calling eq_i with (calling tally.len with xs), 8, "len"
    calling eq_i with (calling tally.first with xs), 3, "first"
    calling eq_i with (calling tally.last with xs), 6, "last"
    calling eq_i with (calling tally.max_index with xs), 5, "max_index"
    calling eq_i with (calling tally.min_index with xs), 1, "min_index"
    calling eq_i with (calling tally.count_of with xs, 1), 2, "count_of"
    calling eq_i with (calling tally.index_of with xs, 1), 1, "index_of"
    calling eq_i with (calling tally.last_index_of with xs, 1), 3, "last_index_of"
    calling eq_i with (calling tally.sum with one), 7, "sum singleton"

    # even-length median averages the two middle elements (integer division)
    calling eq_i with (calling tally.median with even), 2, "median even"
    calling eq_i with (calling tally.median with one), 7, "median singleton"

    # mode: most frequent; the first value wins a tie
    calling eq_i with (calling tally.mode with dup), 2, "mode tie first wins"

    # at_or / at_safe bounds
    calling eq_i with (calling tally.at_or with xs, 99, 0 - 1), 0 - 1, "at_or out of range"
    calling eq_i with (calling tally.at_or with xs, 0, 0 - 1), 3, "at_or in range"
    var safe as maybe int is calling tally.at_safe with xs, 99
    calling eq_b with safe.is_present, false, "at_safe out of range is none"
    banish safe

    # sort / reverse / unique return new lists (the source is untouched)
    var sasc as list of int is calling tally.sort_asc with xs
    calling eq_i with (sasc at 0), 1, "sort_asc first"
    calling eq_i with (sasc at 7), 9, "sort_asc last"
    calling eq_i with (xs at 0), 3, "sort_asc does not mutate the source"
    banish sasc
    var sdesc as list of int is calling tally.sort_desc with xs
    calling eq_i with (sdesc at 0), 9, "sort_desc first"
    banish sdesc
    var srev as list of int is calling tally.reverse with xs
    calling eq_i with (srev at 0), 6, "reverse first"
    banish srev
    var suniq as list of int is calling tally.unique with dup
    calling eq_i with (suniq.len), 2, "unique removes duplicates"
    banish suniq
    var sdedup as list of int is calling tally.dedup with dup
    banish sdedup

    # filters allocate new lists
    var feven as list of int is calling tally.filter_even with xs
    calling eq_i with (feven.len), 3, "filter_even count"
    banish feven
    var fodd as list of int is calling tally.filter_odd with xs
    calling eq_i with (fodd.len), 5, "filter_odd count"
    banish fodd
    var fpos as list of int is calling tally.filter_positive with xs
    calling eq_i with (fpos.len), 8, "filter_positive count"
    banish fpos
    var fneg as list of int is calling tally.filter_negative with xs
    calling eq_i with (fneg.len), 0, "filter_negative empty"
    banish fneg
    var frange as list of int is calling tally.filter_range with xs, 2, 4
    calling eq_i with (frange.len), 3, "filter_range count"
    banish frange
    var ftake as list of int is calling tally.take with xs, 3
    calling eq_i with (ftake.len), 3, "take count"
    banish ftake
    var fdrop as list of int is calling tally.drop with xs, 3
    calling eq_i with (fdrop.len), 5, "drop count"
    banish fdrop

    # maps
    var mdbl as list of int is calling tally.map_double with xs
    calling eq_i with (mdbl at 0), 6, "map_double"
    banish mdbl
    var msq as list of int is calling tally.map_square with xs
    calling eq_i with (msq at 1), 1, "map_square"
    banish msq
    var mneg as list of int is calling tally.map_negate with xs
    calling eq_i with (mneg at 0), 0 - 3, "map_negate"
    banish mneg
    var madd as list of int is calling tally.map_add_scalar with xs, 10
    calling eq_i with (madd at 0), 13, "map_add_scalar"
    banish madd

    # combinations
    var ab as list of int is calling tally.concat with one, one
    calling eq_i with (ab.len), 2, "concat length"
    banish ab
    var zs as list of int is calling tally.zip_sum with one, one
    calling eq_i with (zs at 0), 14, "zip_sum"
    banish zs
    calling eq_i with (calling tally.dot with one, one), 49, "dot"
    var rp as list of int is calling tally.repeat with 5, 3
    calling eq_i with (rp.len), 3, "repeat length"
    banish rp

    # predicates
    calling eq_b with (calling tally.is_sorted_asc with xs), false, "is_sorted_asc false"
    calling eq_b with (calling tally.is_sorted_desc with xs), false, "is_sorted_desc false"
    var isasc as list of int is calling tally.sort_asc with xs
    calling eq_b with (calling tally.is_sorted_asc with isasc), true, "is_sorted_asc true"
    banish isasc
    banish empty
    banish dup
    banish even
    banish one
    banish xs

    # strings through the generic enchanting
    var ws as list of string is ["pear", "apple", "fig"]
    var wsort as list of string is calling tally.sort_asc with ws
    calling eq_s with (wsort at 0), "apple", "sort_asc strings"
    banish wsort
    var wrev as list of string is calling tally.reverse with ws
    calling eq_s with (wrev at 0), "fig", "reverse strings"
    banish wrev
    calling eq_s with (calling tally.min_val with ws), "apple", "min_val strings"
    calling eq_s with (calling tally.max_val with ws), "pear", "max_val strings"
    banish ws

    calling spark.println with "DONE"
    return 0
""")


def test_tally_no_internal_leak(compile_and_run):
    """Churn every list-returning helper in a loop; banish each result.

    A residual internal allocation shows up as an AddressSanitizer leak report
    (and therefore a non-zero exit) when the suite runs with ``PENGU_CFLAGS``.
    """
    out = compile_and_run(_PRE + """
weave churn with xs as list of int into void:
    var a as list of int is calling tally.sort_asc with xs
    banish a
    var b as list of int is calling tally.sort_desc with xs
    banish b
    var c as list of int is calling tally.reverse with xs
    banish c
    var d as list of int is calling tally.unique with xs
    banish d
    var e as list of int is calling tally.dedup with xs
    banish e
    var f as list of int is calling tally.filter_even with xs
    banish f
    var g as list of int is calling tally.filter_odd with xs
    banish g
    var h as list of int is calling tally.filter_positive with xs
    banish h
    var i as list of int is calling tally.filter_negative with xs
    banish i
    var j as list of int is calling tally.filter_range with xs, 2, 8
    banish j
    var k as list of int is calling tally.take with xs, 4
    banish k
    var l as list of int is calling tally.drop with xs, 4
    banish l
    var m as list of int is calling tally.map_double with xs
    banish m
    var n as list of int is calling tally.map_square with xs
    banish n
    var o as list of int is calling tally.map_negate with xs
    banish o
    var p as list of int is calling tally.map_add_scalar with xs, 3
    banish p
    var q as list of int is calling tally.concat with xs, xs
    banish q
    var r as list of int is calling tally.zip_sum with xs, xs
    banish r
    var s as list of int is calling tally.repeat with 1, 5
    banish s
    var t as list of int is calling tally.abs_all with xs
    banish t
    var u as list of int is calling tally.clamp_all with xs, 2, 6
    banish u
    var v as list of int is calling tally.slice_list with xs, 1, 5
    banish v
    var total as int is calling tally.sum with xs
    var med as int is calling tally.median with xs
    var mo as int is calling tally.mode with xs
    var prod as int is calling tally.product with xs
    var mx as int is calling tally.max_val with xs
    var mn as int is calling tally.min_val with xs

weave main into int:
    var xs as list of int is [3, 1, 4, 1, 5, 9, 2, 6]
    var i as int is 0
    while i < 100:
        calling churn with xs
        set i is i + 1
    banish xs
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
