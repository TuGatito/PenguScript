"""``std.memoria`` — allocation primitives.

Three programs cover the four allocating methods plus ``bytes_for``: the
zeroed-by-default contract of ``alloc``/``alloc_array``, the ``try_*``
variants that report OOM through ``maybe``, and the byte-size helper across
primitive and rune types.

The ``try_*`` cases banish twice on purpose: the payload (``banish p``) and the
``maybe`` box (``banish mp``). A ``maybe ref to T`` owns the *box*, not the
pointee, so one ``banish`` is not enough — see the module docstring.
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


def test_alloc_and_alloc_array(compile_and_run):
    """Zeroed by default, writable afterwards, for primitives and runes."""
    out = compile_and_run(_PREAMBLE + """
rune Player:
    hp as int
    level as int

weave main into int:
    # alloc: one zeroed value.
    var p as ref to int is calling memoria.alloc of int
    calling eq_i with (essence of p), 0, "alloc int zeroed"
    set essence of p is 42
    calling eq_i with (essence of p), 42, "alloc int write"
    banish p

    var f as ref to float is calling memoria.alloc of float
    if (essence of f) != 0.0:
        calling spark.println with "FAIL alloc float zeroed"
    banish f

    # alloc_array: N zeroed elements.
    var one as ref to int is calling memoria.alloc_array of int with 1
    calling eq_i with (one at 0), 0, "alloc_array n=1"
    banish one

    var buf as ref to int is calling memoria.alloc_array of int with 100
    var i as int is 0
    var all_zero as bool is true
    while i < 100:
        if (buf at i) != 0:
            set all_zero is false
        set buf at i is i * 2
        set i is i + 1
    if not all_zero:
        calling spark.println with "FAIL alloc_array not zeroed"
    calling eq_i with (buf at 50), 100, "alloc_array indexed write"
    banish buf

    # Runes: the whole struct starts at zero.
    var pl as ref to Player is calling memoria.alloc of Player
    calling eq_i with pl->hp, 0, "alloc rune hp"
    calling eq_i with pl->level, 0, "alloc rune level"
    set pl->hp is 7
    set pl->level is 9
    calling eq_i with pl->hp, 7, "alloc rune hp write"
    banish pl

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_try_alloc(compile_and_run):
    """``try_alloc``/``try_alloc_array`` return ``some`` and free cleanly."""
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var mp as maybe ref to int is calling memoria.try_alloc of int
    if p as ref to int is mp:
        calling eq_i with (essence of p), 0, "try_alloc zeroed"
        set essence of p is 11
        calling eq_i with (essence of p), 11, "try_alloc write"
        banish p
    else:
        calling spark.println with "FAIL try_alloc returned none"
    banish mp

    var ma as maybe ref to int is calling memoria.try_alloc_array of int with 5
    if a as ref to int is ma:
        calling eq_i with (a at 0), 0, "try_alloc_array zeroed"
        set a at 4 is 9
        calling eq_i with (a at 4), 9, "try_alloc_array write"
        banish a
    else:
        calling spark.println with "FAIL try_alloc_array returned none"
    banish ma

    var mb as maybe ref to byte is calling memoria.try_alloc_array of byte with 1
    if b as ref to byte is mb:
        set b at 0 is 200
        calling eq_i with ((b at 0) to int), 200, "try_alloc_array byte"
        banish b
    else:
        calling spark.println with "FAIL try_alloc_array byte returned none"
    banish mb

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_bytes_for(compile_and_run):
    """``bytes_for`` is ``n * (size of T)`` for primitives and runes."""
    out = compile_and_run(_PREAMBLE + """
rune MemoriaPair:
    a as int
    b as int

weave main into int:
    calling eq_i with (calling memoria.bytes_for of int with 4), 16, "int x4"
    calling eq_i with (calling memoria.bytes_for of byte with 7), 7, "byte x7"
    calling eq_i with (calling memoria.bytes_for of f64 with 3), 24, "f64 x3"
    calling eq_i with (calling memoria.bytes_for of MemoriaPair with 5), 40, "rune x5"
    calling eq_i with (calling memoria.bytes_for of int with 0), 0, "int x0"
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
