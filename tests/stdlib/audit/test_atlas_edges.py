"""``std.atlas`` — map semantics, ownership of string keys, and leak churn.

The second program is the important one for the raylib bindings: a map does not
own the buffer a `string` key points at (ABI v2), so the caller must keep every
interpolated key alive until the map is banished and then release it.  The
program demonstrates that pattern and, under ASan, proves it is leak-free.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.atlas

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_atlas_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    var m as map of string to int is map of string to int
    calling eq_i with (calling m.size), 0, "empty size"
    calling eq_b with (calling m.is_empty), true, "empty is_empty"

    # put / overwrite / get
    calling m.put with "a", 1
    calling m.put with "b", 2
    calling m.put with "a", 3
    calling eq_i with (calling m.size), 2, "put existing key overwrites"
    calling eq_i with (m at "a"), 3, "overwritten value"
    calling eq_b with (calling m.contains with "a"), true, "contains"
    calling eq_b with (calling m.contains with "zz"), false, "missing contains"
    calling eq_i with (calling m.get_or with "zz", 0 - 1), 0 - 1, "get_or fallback"
    calling eq_i with (calling m.get_or with "b", 0 - 1), 2, "get_or present"
    var gs as maybe int is calling m.get_safe with "zz"
    calling eq_b with gs.is_present, false, "get_safe missing"
    banish gs

    # update never inserts
    calling eq_b with (calling m.update with "b", 9), true, "update existing"
    calling eq_i with (m at "b"), 9, "updated value"
    calling eq_b with (calling m.update with "nope", 1), false, "update missing is false"
    calling eq_i with (calling m.size), 2, "update did not insert"

    # keys / values are new owned lists
    var ks as list of string is calling m.keys
    var vs as list of int is calling m.values
    calling eq_i with ks.len, 2, "keys count"
    calling eq_i with vs.len, 2, "values count"
    banish ks
    banish vs

    # clone is independent
    var c as map of string to int is calling m.clone
    calling c.put with "z", 100
    calling eq_i with (calling m.size), 2, "clone does not alias the source"
    calling eq_i with (calling c.size), 3, "clone takes its own put"
    banish c

    # remove / clear
    calling eq_b with (calling m.remove with "a"), true, "remove present"
    calling eq_b with (calling m.remove with "a"), false, "remove twice is false"
    calling eq_i with (calling m.size), 1, "remove decrements size"
    calling m.clear
    calling eq_i with (calling m.size), 0, "clear empties"
    banish m

    # from_lists truncates to the shorter list
    var kk as list of string is ["a", "b", "c"]
    var vv as list of int is [1, 2]
    var fl as map of string to int is calling atlas.from_lists with kk, vv
    calling eq_i with (calling fl.size), 2, "from_lists truncates"
    banish fl
    var fl2 as map of string to int is calling atlas.from_lists with kk, vv
    banish fl2
    banish kk
    banish vv

    # merge: the right map wins on collision
    var a as map of string to int is map of string to int
    var b as map of string to int is map of string to int
    calling a.put with "x", 1
    calling a.put with "y", 2
    calling b.put with "y", 20
    calling b.put with "z", 30
    var merged as map of string to int is calling atlas.merge with a, b
    calling eq_i with (merged at "y"), 20, "merge right wins"
    calling eq_i with (merged at "x"), 1, "merge keeps left-only keys"
    banish merged
    var kept as map of string to int is calling atlas.merge_keep_left with a, b
    calling eq_i with (kept at "y"), 2, "merge_keep_left keeps left"
    banish kept
    banish a
    banish b

    # int-keyed maps
    var ii as map of int to int is map of int to int
    var i as int is 0
    while i < 100:
        calling ii.put with i, i * 2
        set i is i + 1
    calling eq_i with (calling ii.size), 100, "int map size after rehashes"
    calling eq_i with (ii at 77), 154, "int map value after rehashes"
    banish ii

    calling spark.println with "DONE"
    return 0
""")


def test_atlas_owned_string_keys_are_leak_free(compile_and_run):
    """Own interpolated keys, keep them alive, free them after the map.

    This is the canonical pattern the raylib bindings must follow for any
    `map of string to ...` built from computed keys.
    """
    out = compile_and_run(_PRE + """
weave main into int:
    var m as map of string to int is map of string to int
    var keys as list of string is list of string
    var i as int is 0
    while i < 120:
        var k as string is "key-{i}"
        calling keys.push with k
        calling m.put with k, i
        set i is i + 1

    var total as int is 0
    for k in keys:
        if calling m.contains with k:
            set total is total + (m at k)
    calling eq_i with total, 7140, "sum over owned keys"

    # Rehash happened twice; every value is still reachable.
    calling eq_i with (m at "key-119"), 119, "value after rehashes"
    calling eq_i with (calling m.size), 120, "size after rehashes"

    # Release order: the map first (it only owns its entry cells), then the
    # key payloads the caller kept alive, then the list.
    banish m
    for k in keys:
        banish k
    banish keys

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
