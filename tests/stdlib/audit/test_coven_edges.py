"""``std.coven`` — set semantics, the legacy `SetInt` storage fix, leak churn.

`SetInt` used to stringify every element into its backing map, so each `add`,
`contains` and `remove` allocated a `string` the map never owned.  The audit
moved it to an `int`-keyed map; the first program pins the observable behaviour
that had to stay identical and the second burns the operations under ASan.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.coven

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_coven_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    # --- SetString with caller-owned elements ----------------------
    var a as SetString is calling coven.new_set_string
    var b as SetString is calling coven.new_set_string
    calling a.add with "x"
    calling a.add with "x"
    calling a.add with "y"
    calling b.add with "y"
    calling b.add with "z"
    calling eq_i with (calling a.len), 2, "set deduplicates"
    calling eq_b with (calling a.contains with "x"), true, "contains"
    calling eq_b with (calling a.contains with "q"), false, "contains missing"
    calling eq_b with (calling a.remove with "x"), true, "remove present"
    calling eq_b with (calling a.remove with "x"), false, "remove twice"
    calling a.add with "x"

    var u as SetString is calling a.union with b
    calling eq_i with (calling u.len), 3, "union"
    banish u.items
    var n as SetString is calling a.intersect with b
    calling eq_i with (calling n.len), 1, "intersect"
    banish n.items
    var d as SetString is calling a.difference with b
    calling eq_i with (calling d.len), 1, "difference"
    banish d.items
    var sd as SetString is calling a.symmetric_difference with b
    calling eq_i with (calling sd.len), 2, "symmetric_difference"
    banish sd.items
    var ab as SetString is calling a.union with b
    calling eq_b with (calling a.is_subset with ab), true, "is_subset"
    banish ab.items
    calling eq_b with (calling a.is_disjoint with b), false, "is_disjoint"
    calling eq_b with (calling a.equals with a), true, "equals self"

    var cl as SetString is calling a.clone
    calling cl.add with "clone-only"
    calling eq_i with (calling a.len), 2, "clone is independent"
    banish cl.items
    var tl as list of string is calling a.to_list
    calling eq_i with tl.len, 2, "to_list count"
    banish tl

    calling a.clear
    calling eq_i with (calling a.len), 0, "clear"
    banish a.items
    banish b.items

    # --- SetInt (int-keyed after the audit) -------------------------
    var si as SetInt is calling coven.new_set_int
    var k as int is 0
    while k < 100:
        calling si.add with k
        set k is k + 1
    calling si.add with 0
    calling eq_i with (calling si.len), 100, "SetInt deduplicates"
    calling eq_b with (calling si.contains with 42), true, "SetInt contains"
    calling eq_b with (calling si.contains with 1000), false, "SetInt contains missing"
    calling eq_b with (calling si.remove with 42), true, "SetInt remove"
    calling eq_b with (calling si.remove with 42), false, "SetInt remove twice"
    calling eq_i with (calling si.sum_ints), 4908, "SetInt sum_ints"
    calling eq_i with (calling si.min_int), 0, "SetInt min_int"
    calling eq_i with (calling si.max_int), 99, "SetInt max_int"
    var sl as list of int is calling si.to_list_int
    calling eq_i with sl.len, 99, "SetInt to_list_int"
    var si2 as SetInt is calling coven.from_list_int with sl
    banish si2.items
    banish sl
    banish si.items

    # --- generic Set of int ----------------------------------------
    var g as Set of int is calling coven.new_int_set
    calling g.add with 1
    calling g.add with 1
    calling g.add with 2
    calling eq_i with (calling g.len), 2, "generic set deduplicates"
    banish g.items

    calling spark.println with "DONE"
    return 0
""")


def test_coven_no_internal_leak(compile_and_run):
    out = compile_and_run(_PRE + """
weave churn with a as SetString, b as SetString into void:
    var u as SetString is calling a.union with b
    banish u.items
    var n as SetString is calling a.intersect with b
    banish n.items
    var d as SetString is calling a.difference with b
    banish d.items
    var sd as SetString is calling a.symmetric_difference with b
    banish sd.items
    var cl as SetString is calling a.clone
    banish cl.items
    var tl as list of string is calling a.to_list
    banish tl

weave main into int:
    var a as SetString is calling coven.new_set_string
    var b as SetString is calling coven.new_set_string
    var elems as list of string is list of string
    var i as int is 0
    while i < 50:
        var s as string is "item{i}"
        calling elems.push with s
        calling a.add with s
        if (i % 2) == 0:
            calling b.add with s
        set i is i + 1

    var iter as int is 0
    while iter < 60:
        calling churn with a, b
        set iter is iter + 1

    calling a.clear
    calling b.clear
    banish a.items
    banish b.items
    for s in elems:
        banish s
    banish elems

    # SetInt churn
    var si as SetInt is calling coven.new_set_int
    var j as int is 0
    while j < 200:
        calling si.add with j
        var present as bool is calling si.contains with j
        set j is j + 1
    var seed as list of int is [1, 2, 3]
    var siu as SetInt is calling coven.from_list_int with seed
    banish siu.items
    banish seed
    banish si.items

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
