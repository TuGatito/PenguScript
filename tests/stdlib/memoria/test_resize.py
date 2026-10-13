"""``std.memoria`` — ``resize_array`` and ``try_resize_array``.

Three programs: the content-preserving grow/shrink contract, the edge cases
(equal sizes, ``null`` source, ``new_n == 0`` is deliberately untested because
``realloc(p, 0)`` is implementation-defined), and the ``maybe``-returning
variant.

The pattern under test is the documented one: after a successful resize the
*old* pointer is invalid and only the return value may be used. ``defer
banish`` reads the variable at scope exit, so it frees the current pointer —
never a snapshot of the original.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.memoria

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_resize_preserves_content(compile_and_run):
    """Grow preserves the prefix and zeroes the tail; shrink keeps the prefix."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    # Grow 4 -> 8: old content survives, new tail is zero.
    var buf as ref to int is calling memoria.alloc_array of int with 4
    set buf at 0 is 10
    set buf at 1 is 20
    set buf at 2 is 30
    set buf at 3 is 40
    set buf is calling memoria.resize_array of int with buf, 4, 8
    calling eq_i with (buf at 0), 10, "grow [0]"
    calling eq_i with (buf at 1), 20, "grow [1]"
    calling eq_i with (buf at 2), 30, "grow [2]"
    calling eq_i with (buf at 3), 40, "grow [3]"
    calling eq_i with (buf at 4), 0, "grow tail zeroed"
    calling eq_i with (buf at 7), 0, "grow last zeroed"
    set buf at 7 is 77
    calling eq_i with (buf at 7), 77, "grow tail writable"

    # Shrink 8 -> 2: only the prefix is guaranteed.
    set buf is calling memoria.resize_array of int with buf, 8, 2
    calling eq_i with (buf at 0), 10, "shrink [0]"
    calling eq_i with (buf at 1), 20, "shrink [1]"
    banish buf

    # A byte buffer grows the same way.
    var raw_bytes as ref to byte is calling memoria.alloc_array of byte with 2
    set raw_bytes at 0 is 9
    set raw_bytes is calling memoria.resize_array of byte with raw_bytes, 2, 5
    calling eq_i with ((raw_bytes at 0) to int), 9, "byte grow [0]"
    calling eq_i with ((raw_bytes at 4) to int), 0, "byte grow tail"
    banish raw_bytes

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_resize_edge_cases(compile_and_run):
    """Equal sizes is a no-op; a ``null`` source allocates zeroed memory."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    # new_n == old_n must not free the block.
    var buf as ref to int is calling memoria.alloc_array of int with 3
    set buf at 1 is 55
    set buf is calling memoria.resize_array of int with buf, 3, 3
    calling eq_i with (buf at 1), 55, "equal-size keeps content"
    banish buf

    # null source behaves like alloc_array.
    var empty as ref to int is null
    var fresh as ref to int is calling memoria.resize_array of int with empty, 0, 4
    calling eq_i with (fresh at 0), 0, "null source zeroed"
    set fresh at 3 is 3
    calling eq_i with (fresh at 3), 3, "null source writable"
    banish fresh

    # defer on the reassigned variable frees the live pointer exactly once.
    var loop as ref to int is calling memoria.alloc_array of int with 2
    defer banish loop
    set loop at 0 is 1
    set loop is calling memoria.resize_array of int with loop, 2, 64
    calling eq_i with (loop at 0), 1, "defer sees the resized pointer"

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_try_resize(compile_and_run):
    """``try_resize_array`` populates ``some`` and preserves content."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 3
    set buf at 0 is 8
    var mp as maybe ref to int is calling memoria.try_resize_array of int with buf, 3, 6
    if p as ref to int is mp:
        calling eq_i with (p at 0), 8, "try_resize preserves"
        calling eq_i with (p at 5), 0, "try_resize zeroes tail"
        banish p
    else:
        calling spark.println with "FAIL try_resize returned none"
        banish buf
    banish mp

    # Equal sizes returns the same live block.
    var same as ref to int is calling memoria.alloc_array of int with 2
    set same at 0 is 4
    var ms as maybe ref to int is calling memoria.try_resize_array of int with same, 2, 2
    if s as ref to int is ms:
        calling eq_i with (s at 0), 4, "try_resize equal keeps content"
        banish s
    else:
        calling spark.println with "FAIL try_resize equal returned none"
    banish ms

    # From null: a fresh zeroed block.
    var empty as ref to int is null
    var mn as maybe ref to int is calling memoria.try_resize_array of int with empty, 0, 3
    if n as ref to int is mn:
        calling eq_i with (n at 2), 0, "try_resize null zeroed"
        banish n
    else:
        calling spark.println with "FAIL try_resize null returned none"
    banish mn

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
