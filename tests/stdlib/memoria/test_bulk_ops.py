"""``std.memoria`` — the bulk operations: ``copy``, ``fill``, ``zero``, ``swap``
and ``compare``.

Three programs. ``copy`` is ``memmove``-based, so the overlap cases (forward and
backward) are the ones that would catch a ``memcpy`` regression. ``compare``
must return ``-1``/``0``/``1`` like ``memcmp``.
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

weave eq_f with got as float, want as float, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: float mismatch"
"""


def test_copy_and_overlap(compile_and_run):
    """Non-overlapping copy plus both overlap directions and ``n == 0``."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    # Non-overlapping.
    var src as ref to int is calling memoria.alloc_array of int with 3
    set src at 0 is 1
    set src at 1 is 2
    set src at 2 is 3
    var dst as ref to int is calling memoria.alloc_array of int with 3
    calling memoria.copy of int with dst, src, 3
    calling eq_i with (dst at 0), 1, "copy [0]"
    calling eq_i with (dst at 2), 3, "copy [2]"
    banish src
    banish dst

    # Overlap forward: shift 0..2 to 1..3 (memmove must copy right-to-left).
    var fwd as ref to int is calling memoria.alloc_array of int with 5
    set fwd at 0 is 1
    set fwd at 1 is 2
    set fwd at 2 is 3
    set fwd at 3 is 4
    set fwd at 4 is 5
    calling memoria.copy of int with (sigil of (fwd at 1)), (sigil of (fwd at 0)), 3
    calling eq_i with (fwd at 1), 1, "overlap fwd [1]"
    calling eq_i with (fwd at 2), 2, "overlap fwd [2]"
    calling eq_i with (fwd at 3), 3, "overlap fwd [3]"
    calling eq_i with (fwd at 4), 5, "overlap fwd untouched tail"
    banish fwd

    # Overlap backward: shift 1..3 to 0..2.
    var bwd as ref to int is calling memoria.alloc_array of int with 5
    set bwd at 0 is 1
    set bwd at 1 is 2
    set bwd at 2 is 3
    set bwd at 3 is 4
    set bwd at 4 is 5
    calling memoria.copy of int with (sigil of (bwd at 0)), (sigil of (bwd at 1)), 3
    calling eq_i with (bwd at 0), 2, "overlap bwd [0]"
    calling eq_i with (bwd at 1), 3, "overlap bwd [1]"
    calling eq_i with (bwd at 2), 4, "overlap bwd [2]"
    banish bwd

    # n == 0 touches nothing.
    var a as ref to int is calling memoria.alloc_array of int with 2
    var b as ref to int is calling memoria.alloc_array of int with 2
    set b at 0 is 5
    calling memoria.copy of int with a, b, 0
    calling eq_i with (a at 0), 0, "copy n=0 is a no-op"
    banish a
    banish b

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_fill_and_zero(compile_and_run):
    """``fill`` writes any byte pattern; ``zero`` writes zeros."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 4
    calling memoria.fill of int with buf, -1, 4
    calling eq_i with (buf at 0), 0 - 1, "fill -1 [0]"
    calling eq_i with (buf at 3), 0 - 1, "fill -1 [3]"
    calling memoria.fill of int with buf, 7, 4
    calling eq_i with (buf at 0), 7, "fill 7 [0]"
    calling memoria.fill of int with buf, 0, 4
    calling eq_i with (buf at 0), 0, "fill 0 [0]"
    banish buf

    var fb as ref to float is calling memoria.alloc_array of float with 3
    calling memoria.fill of float with fb, 1.5, 3
    calling eq_f with (fb at 0), 1.5, "fill float [0]"
    calling eq_f with (fb at 2), 1.5, "fill float [2]"
    banish fb

    var ob as ref to byte is calling memoria.alloc_array of byte with 1
    calling memoria.fill of byte with ob, 255, 1
    calling eq_i with ((ob at 0) to int), 255, "fill single byte"
    banish ob

    var zb as ref to int is calling memoria.alloc_array of int with 8
    var i as int is 0
    while i < 8:
        set zb at i is i + 1
        set i is i + 1
    calling memoria.zero of int with zb, 8
    calling eq_i with (zb at 0), 0, "zero [0]"
    calling eq_i with (zb at 7), 0, "zero [7]"
    banish zb

    var zf as ref to float is calling memoria.alloc_array of float with 2
    set zf at 0 is 2.5
    calling memoria.zero of float with zf, 2
    calling eq_f with (zf at 0), 0.0, "zero float"
    banish zf

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_swap_and_compare(compile_and_run):
    """``swap`` exchanges values; ``compare`` returns the memcmp sign."""
    out = compile_and_run(_PREAMBLE + """
rune MemoriaPair:
    x as int
    y as int

weave main into int:
    var a as int is 1
    var b as int is 2
    calling memoria.swap of int with (sigil of a), (sigil of b)
    calling eq_i with a, 2, "swap a"
    calling eq_i with b, 1, "swap b"

    var x as float is 1.5
    var y as float is 2.5
    calling memoria.swap of float with (sigil of x), (sigil of y)
    calling eq_f with x, 2.5, "swap float x"
    calling eq_f with y, 1.5, "swap float y"

    var p as MemoriaPair is with x is 1, y is 2
    var q as MemoriaPair is with x is 3, y is 4
    calling memoria.swap of MemoriaPair with (sigil of p), (sigil of q)
    calling eq_i with p.x, 3, "swap rune x"
    calling eq_i with q.y, 2, "swap rune y"

    var e1 as ref to int is calling memoria.alloc_array of int with 3
    var e2 as ref to int is calling memoria.alloc_array of int with 3
    set e1 at 0 is 5
    set e2 at 0 is 5
    calling eq_i with (calling memoria.compare of int with e1, e2, 3), 0, "compare equal"
    set e1 at 1 is 1
    set e2 at 1 is 2
    calling eq_i with (calling memoria.compare of int with e1, e2, 3), 0 - 1, "compare less"
    calling eq_i with (calling memoria.compare of int with e2, e1, 3), 1, "compare greater"
    calling eq_i with (calling memoria.compare of int with e1, e2, 0), 0, "compare n=0"
    banish e1
    banish e2

    var c1 as ref to byte is calling memoria.alloc_array of byte with 2
    var c2 as ref to byte is calling memoria.alloc_array of byte with 2
    set c1 at 0 is 10
    set c2 at 0 is 20
    calling eq_i with (calling memoria.compare of byte with c1, c2, 2), 0 - 1, "compare bytes"
    banish c1
    banish c2

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
