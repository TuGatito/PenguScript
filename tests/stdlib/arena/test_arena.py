"""``std.arena`` — bump allocation, reset and free.

The programs use a tiny C bridge only to *observe* absolute addresses for the
alignment assertions; the allocator itself is the module under test.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PREAMBLE = """
import std.spark
import std.arena

antiquus test_addr with p as ref to byte into usize:
    r\"\"\"
return (size_t)p;
\"\"\"

antiquus test_bytes with p as ref to frozen char into ref to byte:
    r\"\"\"
return (uint8_t *)p;
\"\"\"

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"
"""


def test_arena_alloc_str_cstr_and_alignment(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
rune Node:
    value as int
    next as ref to Node

weave main into int:
    var a as Arena is calling Arena.new
    defer banish a
    defer calling a.free

    calling eq_i with (calling a.block_count), 0, "fresh blocks"
    calling eq_i with (calling a.total_allocated to int), 0, "fresh total"
    calling eq_b with (calling a.block_size) == 4096, true, "default block size"

    var zero as ref to byte is calling a.alloc with 0
    if zero == null:
        calling spark.println with "FAIL alloc(0) returned null"
    calling eq_i with (calling a.total_allocated to int), 0, "alloc(0) total"

    var p as ref to byte is calling a.alloc with 16
    set p at 0 is 65
    set p at 15 is 66
    calling eq_i with ((p at 0) to int), 65, "alloc write"
    calling eq_i with ((p at 15) to int), 66, "alloc last"
    calling eq_i with (calling a.total_allocated to int), 16, "total 16"

    var s as ref to byte is calling a.alloc_str with "hola"
    calling eq_i with ((s at 0) to int), 104, "str h"
    calling eq_i with ((s at 3) to int), 97, "str a"
    var empty as ref to byte is calling a.alloc_str with ""
    if empty == null:
        calling spark.println with "FAIL alloc_str empty"

    var c as ref to frozen char is calling a.alloc_cstr with "abc"
    var cp as ref to byte is calling test_bytes with c
    calling eq_i with ((cp at 0) to int), 97, "cstr a"
    calling eq_i with ((cp at 2) to int), 99, "cstr c"
    calling eq_i with ((cp at 3) to int), 0, "cstr NUL"

    var big as ref to byte is calling a.alloc_aligned with 5000, 16
    set big at 4999 is 7
    calling eq_i with ((big at 4999) to int), 7, "oversized write"
    if (calling a.block_count) < 2:
        calling spark.println with "FAIL oversized needs a block"

    var page as ref to byte is calling a.alloc_aligned with 32, 4096
    var page_addr as usize is calling test_addr with page
    calling eq_b with (page_addr & 4095) == 0, true, "page aligned"
    var aligned as ref to byte is calling a.alloc_aligned with 64, 64
    var aligned_addr as usize is calling test_addr with aligned
    calling eq_b with (aligned_addr & 63) == 0, true, "64 aligned"
    var one_align as ref to byte is calling a.alloc_aligned with 3, 1
    if one_align == null:
        calling spark.println with "FAIL alignment 1"

    var n1 as ref to Node is calling arena_alloc_one of Node with (sigil of a)
    set n1->value is 11
    set n1->next is calling arena_alloc_one of Node with (sigil of a)
    set n1->next->value is 22
    calling eq_i with n1->value + n1->next->value, 33, "generic nodes"

    var arr as ref to int is calling arena_alloc of int with (sigil of a), 8
    set arr at 0 is 5
    set arr at 7 is 9
    calling eq_i with (arr at 0) + (arr at 7), 14, "generic int array"
    calling eq_i with (arr at 1), 0, "generic zeroed"

    calling spark.println with "DONE"
    return 0
""")


def test_arena_reset_free_and_reuse(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as Arena is calling Arena.with_block_size with 128
    defer banish a
    defer calling a.free

    var i as int is 0
    while i < 40:
        var q as ref to byte is calling a.alloc with 32
        set q at 0 is (i to byte)
        set i is i + 1
    if (calling a.block_count) < 2:
        calling spark.println with "FAIL expected several blocks"
    var total_before as usize is calling a.total_allocated
    if total_before < 1280:
        calling spark.println with "FAIL total_before={total_before}"

    calling a.reset
    calling eq_i with (calling a.block_count), 1, "reset keeps first block"
    calling eq_i with (calling a.total_allocated to int), 0, "reset total"
    var again as ref to byte is calling a.alloc with 100
    set again at 0 is 1
    calling eq_i with ((again at 0) to int), 1, "usable after reset"
    calling a.reset

    var huge as ref to byte is calling a.alloc_aligned with 9000, 16
    set huge at 8999 is 9
    if (calling a.block_count) < 2:
        calling spark.println with "FAIL oversized block"
    calling a.reset
    calling eq_i with (calling a.block_count), 1, "reset drops oversized"

    calling a.free
    calling eq_i with (calling a.block_count), 0, "free blocks"
    calling eq_i with (calling a.total_allocated to int), 0, "free total"
    var reuse as ref to byte is calling a.alloc with 8
    set reuse at 0 is 3
    calling eq_i with ((reuse at 0) to int), 3, "reuse after free"
    calling a.free
    calling spark.println with "DONE"
    return 0
""")


def test_arena_banish_after_free_is_safe(compile_and_run):
    out = compile_and_run(_PREAMBLE + """
weave main into int:
    var a as Arena is calling Arena.new
    var p as ref to byte is calling a.alloc with 32
    set p at 0 is 1
    calling a.free
    banish a
    var b as Arena is calling Arena.new
    defer banish b
    defer calling b.free
    calling b.reset
    calling spark.println with "DONE"
    return 0
""")


@pytest.mark.parametrize("body, expected", [
    ("var p as ref to byte is calling a.alloc_aligned with 8, 0", "alignment"),
    ("var p as ref to byte is calling a.alloc_aligned with 8, 3", "power of two"),
    ("var p as ref to Node is calling arena_alloc of Node with (sigil of a), -1", "negative count"),
])
def test_arena_panics_are_fatal(run_pengu, body, expected):
    res = run_pengu(f"""
import std.spark
import std.arena

rune Node:
    value as int

weave main into int:
    var a as Arena is calling Arena.new
    defer calling a.free
    defer banish a
    {body}
    calling spark.println with "SHOULD NOT REACH"
    return 0
""")
    assert res.returncode != 0
    assert expected in (res.stderr + res.stdout), (res.stdout, res.stderr)


def test_arena_rejects_zero_block_size(run_pengu):
    res = run_pengu("""
import std.arena

weave main into int:
    var a as Arena is calling Arena.with_block_size with 0
    banish a
    return 0
""")
    assert res.returncode != 0, res.stdout
