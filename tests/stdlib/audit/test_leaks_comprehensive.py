"""Comprehensive leak gate for the audited surface.

Each program allocates and releases exactly what it owns, so when the suite is
run with a sanitizer the process must exit cleanly and LeakSanitizer must print
nothing:

    PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all" \\
    PENGU_LDFLAGS="-fsanitize=address,undefined" \\
    ASAN_OPTIONS="detect_leaks=1:halt_on_error=1:abort_on_error=1" \\
    python -m pytest tests/stdlib/audit/test_leaks_comprehensive.py -v -p no:cacheprovider

Without the sanitizer flags the programs still pass; they simply no longer
*prove* the absence of leaks.  The comment above each block names the ownership
rule it exercises.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.scrolls
import std.tally
import std.atlas
import std.coven
import std.oracle
import std.memoria
import std.ffi
"""


def test_leaks_primitives(compile_and_run):
    """string / list / map: allocate, use, banish — nothing implicit."""
    out = compile_and_run(_PRE + """
weave main into int:
    # 1000 owned interpolations, each released by name.
    var i as int is 0
    while i < 1000:
        var s as string is "hello {i}"
        banish s
        set i is i + 1

    # 1000 list pushes, then the list buffer.
    var xs as list of int is list of int
    set i is 0
    while i < 1000:
        calling xs.push with i
        set i is i + 1
    banish xs

    # A map with literal (non-owning) keys: only the entry cells are owned.
    var m as map of string to int is map of string to int
    calling m.put with "a", 1
    calling m.put with "b", 2
    banish m

    # A map with computed keys: the caller keeps them alive, then releases
    # them after the map (the map does not own the key buffers).
    var m2 as map of string to int is map of string to int
    var keys as list of string is list of string
    set i is 0
    while i < 200:
        var k as string is "k{i}"
        calling keys.push with k
        calling m2.put with k, i
        set i is i + 1
    banish m2
    for k in keys:
        banish k
    banish keys

    # maybe / result boxes own their box; release box and payload.
    set i is 0
    while i < 500:
        var mp as maybe int is calling oracle.some_int with i
        var v as int is calling mp.unwrap
        banish mp
        var r as result of int to string is calling ok_of with v
        var rv as int is calling r.unwrap
        banish r
        set i is i + 1

    # memoria: alloc + defer, and alloc_array + banish.
    set i is 0
    while i < 500:
        var p as ref to int is calling memoria.alloc of int
        set essence of p is i
        banish p
        set i is i + 1

    # a helper owns and releases its own block
    set i is 0
    while i < 300:
        calling owner with i
        set i is i + 1

    calling spark.println with "DONE"
    return 0

weave owner with n as int into void:
    var p as ref to int is calling memoria.alloc_array of int with 8
    defer banish p
    set p at 0 is n
"""
)
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_leaks_std_composition(compile_and_run):
    """scrolls / tally / atlas / coven / oracle / ffi working together."""
    out = compile_and_run(_PRE + """
weave main into int:
    var src as string is "  Hello, World  "
    var clean as string is calling src.trim
    var parts as list of string is calling clean.split with ", "
    # split returns a list of *views* into `clean`, so banishing the list is
    # the whole release; every element is a no-op.
    banish parts
    banish clean

    var xs as list of int is [5, 3, 9, 1]
    var sorted as list of int is calling tally.sort_asc with xs
    banish sorted
    var total as int is calling tally.sum with xs
    banish xs

    var m as map of string to int is map of string to int
    calling m.put with "a", 1
    var c as map of string to int is calling m.clone
    banish c
    banish m

    var st as SetString is calling coven.new_set_string
    calling st.add with clean
    var cl as SetString is calling st.clone
    banish cl.items
    banish st.items

    # ffi: owning copy + non-owning view
    var msg as string is "hi"
    var cp as ref to char is calling ffi.cstr_from_string with msg
    var copy as string is calling ffi.string_from_cstr with cp
    banish copy

    var buf as ref to int is calling memoria.alloc_array of int with 4
    set buf at 0 is 7
    var vp as ref to void is transmute buf to ref to void
    var sl as slice of int is calling ffi.slice_from_ptr of int with vp, 4
    var copied as list of int is calling ffi.list_from_ptr of int with vp, 4
    banish copied
    banish buf

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_leaks_documented_split_pattern(compile_and_run):
    """The documented release pattern for a `list of string` from `split`.

    `split` returns views, so `banish parts` releases everything.  A list whose
    elements *are* owned (here built from interpolations) must have each element
    released before the list buffer.
    """
    out = compile_and_run(_PRE + """
weave main into int:
    # views: one banish for the whole list
    var csv as string is "a,b,c"
    var parts as list of string is calling csv.split with ","
    banish parts

    # owned elements: one banish each, then the list
    var owned as list of string is list of string
    var i as int is 0
    while i < 50:
        var e as string is "e{i}"
        calling owned.push with e
        set i is i + 1
    for e in owned:
        banish e
    banish owned

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
