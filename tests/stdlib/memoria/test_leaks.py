"""``std.memoria`` — leak checks.

These programs are written so that a leak is a *test failure* under a
sanitizer:

* ``alloc``/``alloc_array``/``resize_array`` are always paired with ``banish``
  or ``defer banish``;
* every ``try_*`` result frees the payload **and** the ``maybe`` box;
* the ``errdefer`` path frees the block it allocated.

Run them with ASan to make the check real::

    PENGU_CFLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer" \\
    PENGU_LDFLAGS="-fsanitize=address,undefined" \\
    python -m pytest tests/stdlib/memoria/test_leaks.py -v -p no:cacheprovider

Without the sanitizer flags the programs still pass; they simply do not prove
the absence of leaks. ``valgrind`` is not wired into ``pengu_project.py`` in
this checkout, so there is no automatic valgrind run; the ASan run is the
equivalent gate.
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


def test_no_leak_alloc_banish(compile_and_run):
    """A thousand allocate/free cycles and an explicit ``defer banish``."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var i as int is 0
    while i < 1000:
        var p as ref to int is calling memoria.alloc of int
        set essence of p is i
        banish p
        set i is i + 1

    var buf as ref to int is calling memoria.alloc_array of int with 128
    defer banish buf
    calling memoria.fill of int with buf, 3, 128
    calling eq_i with (buf at 127), 3, "deferred buffer usable"

    var j as int is 0
    while j < 100:
        var b as ref to byte is calling memoria.alloc_array of byte with 32
        set b at 0 is 1
        banish b
        set j is j + 1

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_no_leak_resize_and_helpers(compile_and_run):
    """``resize_array`` under ``defer``, plus a helper that owns its block."""
    out = compile_and_run(_PREAMBLE + """
weave doubled with n as int into int:
    var p as ref to int is calling memoria.alloc of int
    defer banish p
    set essence of p is n
    return (essence of p) * 2

weave main into int:
    var k as int is 0
    while k < 200:
        calling eq_i with (calling doubled with k), k * 2, "helper"
        set k is k + 1

    # Grow and shrink in a loop; the defer frees the live pointer.
    var buf as ref to int is calling memoria.alloc_array of int with 4
    defer banish buf
    var i as int is 0
    while i < 50:
        set buf at 0 is i
        set buf is calling memoria.resize_array of int with buf, 4, 32
        set buf is calling memoria.resize_array of int with buf, 32, 4
        set i is i + 1
    calling eq_i with (buf at 0), 49, "resize loop keeps content"

    # swap / zero / compare own nothing.
    var x as int is 1
    var y as int is 2
    calling memoria.swap of int with (sigil of x), (sigil of y)
    calling eq_i with x, 2, "swap"
    calling memoria.zero of int with buf, 4
    calling eq_i with (calling memoria.compare of int with buf, buf, 4), 0, "compare"

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_no_leak_try_variants_and_errdefer(compile_and_run):
    """``try_*`` frees payload + box; ``errdefer`` frees on the error path."""
    out = compile_and_run(_PREAMBLE + """
weave checked with n as int into result of int to string:
    var p as ref to int is calling memoria.alloc of int
    errdefer banish p
    if n < 0:
        return calling err_of with "negative"
    set essence of p is n
    let v as int is essence of p
    banish p
    return calling ok_of with v

weave main into int:
    var i as int is 0
    while i < 100:
        var mp as maybe ref to int is calling memoria.try_alloc of int
        if p as ref to int is mp:
            set essence of p is i
            banish p
        banish mp

        var ma as maybe ref to int is calling memoria.try_alloc_array of int with 8
        if a as ref to int is ma:
            set a at 7 is i
            banish a
        banish ma
        set i is i + 1

    var k as int is 0
    while k < 100:
        var okr as result of int to string is calling checked with k
        if okr.is_ok:
            calling eq_i with okr.value, k, "checked ok"
        banish okr
        var errr as result of int to string is calling checked with 0 - 1
        if errr.is_ok == false:
            var message as string is errr.error
            if (message length) == 0:
                calling spark.println with "FAIL checked error message"
        banish errr
        set k is k + 1

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
