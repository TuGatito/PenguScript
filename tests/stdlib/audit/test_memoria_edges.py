"""``std.memoria`` — audit edge cases: resize + defer, zero-count bulk ops, OOM-free paths.

The existing ``tests/stdlib/memoria`` suite covers the happy paths; this file
targets the audit's specific worries: `resize_array` under a `defer banish`
(freed exactly once), `compare`/`copy`/`fill` with a zero element count, `swap`
of a block with itself, and the `try_*` failure contract.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.memoria

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_memoria_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    # alloc / alloc_array are zeroed
    var p as ref to int is calling memoria.alloc of int
    calling eq_i with (essence of p), 0, "alloc zeroed"
    banish p

    var buf as ref to int is calling memoria.alloc_array of int with 8
    calling eq_i with (buf at 7), 0, "alloc_array zeroed"
    set buf at 0 is 42

    # resize grows zeroed, shrinks keeping the prefix, equal is a no-op
    set buf is calling memoria.resize_array of int with buf, 8, 16
    calling eq_i with (buf at 0), 42, "resize preserves"
    calling eq_i with (buf at 15), 0, "resize zeroes tail"
    set buf is calling memoria.resize_array of int with buf, 16, 4
    calling eq_i with (buf at 0), 42, "shrink preserves prefix"
    set buf is calling memoria.resize_array of int with buf, 4, 4
    calling eq_i with (buf at 0), 42, "equal resize is a no-op"
    banish buf

    # resize from null behaves like alloc_array
    var nullbuf as ref to int is null
    var fresh as ref to int is calling memoria.resize_array of int with nullbuf, 0, 4
    calling eq_i with (fresh at 3), 0, "resize from null is zeroed"
    banish fresh

    # bulk ops with a zero element count must not touch the buffers
    var a as ref to int is calling memoria.alloc_array of int with 2
    var b as ref to int is calling memoria.alloc_array of int with 2
    set b at 0 is 5
    calling memoria.copy of int with a, b, 0
    calling eq_i with (a at 0), 0, "copy of 0 elements is a no-op"
    calling memoria.zero of int with a, 0
    calling eq_i with (a at 0), 0, "zero of 0 elements"
    calling memoria.fill of int with a, 9, 0
    calling eq_i with (a at 0), 0, "fill of 0 elements"
    calling eq_i with (calling memoria.compare of int with a, b, 0), 0, "compare of 0 elements"

    # swap of a block with itself is a no-op
    set a at 0 is 3
    calling memoria.swap of int with (sigil of (a at 0)), (sigil of (a at 0))
    calling eq_i with (a at 0), 3, "swap self"

    # compare sign convention is exactly -1/0/1
    set a at 0 is 1
    set b at 0 is 2
    calling eq_i with (calling memoria.compare of int with a, b, 2), 0 - 1, "compare lt"
    calling eq_i with (calling memoria.compare of int with b, a, 2), 1, "compare gt"
    calling eq_i with (calling memoria.compare of int with a, a, 2), 0, "compare eq"
    banish a
    banish b

    # try_alloc returns some with a zeroed block
    var mp as maybe ref to int is calling memoria.try_alloc of int
    calling eq_b with mp.is_present, true, "try_alloc present"
    if tp as ref to int is mp:
        calling eq_i with (essence of tp), 0, "try_alloc zeroed"
        banish tp
    banish mp

    var ma as maybe ref to int is calling memoria.try_alloc_array of int with 3
    calling eq_b with ma.is_present, true, "try_alloc_array present"
    if ta as ref to int is ma:
        calling eq_i with (ta at 2), 0, "try_alloc_array zeroed"
        banish ta
    banish ma

    # try_resize with an equal size returns the same live block
    var base as ref to int is calling memoria.alloc_array of int with 2
    set base at 0 is 7
    var mr as maybe ref to int is calling memoria.try_resize_array of int with base, 2, 2
    calling eq_b with mr.is_present, true, "try_resize present"
    if tr as ref to int is mr:
        calling eq_i with (tr at 0), 7, "try_resize preserves"
        banish tr
    else:
        banish base
    banish mr

    # bytes_for
    calling eq_i with (calling memoria.bytes_for of int with 4), 16, "bytes_for int"
    calling eq_i with (calling memoria.bytes_for of byte with 7), 7, "bytes_for byte"
    calling eq_i with (calling memoria.bytes_for of int with 0), 0, "bytes_for zero"

    calling spark.println with "DONE"
    return 0
""")


def test_memoria_resize_under_defer(compile_and_run):
    """`defer banish` must free the current pointer exactly once.

    Before the audit this was a double-free trap: if `resize_array` had freed
    the old block, the defer would free a stale pointer.  It does not; the defer
    reads the rebound variable.
    """
    out = compile_and_run(_PRE + """
weave helper with n as int into void:
    var q as ref to int is calling memoria.alloc_array of int with 4
    defer banish q
    set q at 0 is n
    if (q at 0) != n:
        calling spark.println with "FAIL helper roundtrip"

weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 8
    defer banish buf
    set buf at 0 is 11
    var i as int is 0
    while i < 200:
        set buf is calling memoria.resize_array of int with buf, 8, 64
        set buf is calling memoria.resize_array of int with buf, 64, 8
        set i is i + 1
    calling eq_i with (buf at 0), 11, "resize loop keeps the first element"

    # helper that owns and releases its own block
    var k as int is 0
    while k < 200:
        calling helper with k
        set k is k + 1

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
