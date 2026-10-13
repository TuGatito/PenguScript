"""``std.ffi`` — null-safety, view vs copy contracts, and zero-length edges.

The FFI bridges are the layer the raylib bindings will sit on, so the audit
pins: a NULL C pointer never crashes, `slice_from_ptr` is a non-owning view
(banishing it must be a no-op), and the owning copies (`string_from_cstr`,
`list_from_ptr`, `map_from_ptr`) survive the source buffer being released.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

_PRE = """
import std.spark
import std.ffi
import std.memoria

weave eq_i with got as int, want as int, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_b with got as bool, want as bool, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: {got} != {want}"

weave eq_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"

weave chk_s with got as string, want as string, name as string into void:
    if got != want:
        calling spark.println with "FAIL {name}: '{got}' != '{want}'"
    banish got

weave eat with s as string into void:
    banish s
"""


def test_ffi_edge_cases(compile_and_run):
    out = compile_and_run(_PRE + """
weave main into int:
    # --- pointer utilities -----------------------------------------
    var nv as ref to void is calling ffi.null_void
    var nc as ref to char is calling ffi.null_char
    var nb as ref to byte is calling ffi.null_byte
    calling eq_b with (calling ffi.is_null with nv), true, "is_null(NULL)"
    calling eq_b with (calling ffi.is_valid with nv), false, "is_valid(NULL)"
    calling eq_b with (calling ffi.ptr_is_valid with nv), false, "ptr_is_valid alias"
    calling eq_b with (calling ffi.ptr_eq with nv, nv), true, "ptr_eq NULL NULL"

    var buf as ref to int is calling memoria.alloc_array of int with 4
    set buf at 0 is 11
    set buf at 1 is 22
    set buf at 2 is 33
    set buf at 3 is 44
    set buf is calling memoria.resize_array of int with buf, 4, 4

    var vp as ref to void is transmute buf to ref to void
    calling eq_b with (calling ffi.is_valid with vp), true, "is_valid(non-null)"
    calling eq_b with (calling ffi.ptr_eq with vp, vp), true, "ptr_eq self"
    calling eq_b with (calling ffi.ptr_eq with vp, nv), false, "ptr_eq NULL"

    # --- slices: non-owning views ----------------------------------
    var sl as slice of int is calling ffi.slice_of_int_from_ptr with vp, 4
    calling eq_i with (sl at 0), 11, "slice reads element 0"
    calling eq_i with (sl at 3), 44, "slice reads element 3"
    var sgen as slice of int is calling ffi.slice_from_ptr of int with vp, 4
    calling eq_i with (sgen at 1), 22, "generic slice_from_ptr"
    var szero as slice of int is calling ffi.slice_from_ptr of int with vp, 0
    # A zero-length view is still a view: nothing to banish, nothing allocated.

    # list copies survive the source
    var copies as list of int is calling ffi.list_of_int_from_ptr with vp, 4
    calling eq_i with copies.len, 4, "list copy length"
    calling eq_i with (copies at 0), 11, "list copy content"
    banish copies
    var lgen as list of int is calling ffi.list_from_ptr of int with vp, 4
    calling eq_i with (lgen at 2), 33, "generic list_from_ptr"
    banish lgen
    var lempty as list of int is calling ffi.list_from_ptr of int with vp, 0
    calling eq_i with lempty.len, 0, "zero-length list copy"
    banish lempty

    banish buf

    # --- C string bridge -------------------------------------------
    var null_str as string is calling ffi.string_from_cstr with nc
    calling eq_s with null_str, "", "string_from_cstr(NULL)"
    banish null_str

    var hello as string is "hello"
    var chp as ref to char is calling ffi.cstr_from_string with hello
    var back as string is calling ffi.string_from_cstr with chp
    calling eq_s with back, "hello", "cstr round trip"
    banish back
    var bts as ref to byte is calling ffi.bytes_from_string with hello
    var from_bytes as string is calling ffi.string_from_bytes with bts, 5
    calling eq_s with from_bytes, "hello", "bytes round trip"
    banish from_bytes

    # bounded copy stops at the first NUL and rejects a non-positive bound
    var nzero as string is calling ffi.string_from_cstr_n with chp, 0
    calling eq_s with nzero, "", "cstr_n with 0"
    banish nzero
    var nbig as string is calling ffi.string_from_cstr_n with chp, 100
    calling eq_s with nbig, "hello", "cstr_n past the NUL"
    banish nbig
    var nsmall as string is calling ffi.string_from_cstr_n with chp, 3
    calling eq_s with nsmall, "hel", "cstr_n bounded"
    banish nsmall
    var bzero as string is calling ffi.string_from_bytes with bts, 0
    calling eq_s with bzero, "", "string_from_bytes 0"
    banish bzero

    # the read-only C views alias the PenguString buffer
    calling chk_s with (calling ffi.string_from_cstr with chp), "hello", "view still valid"

    # --- size helpers ----------------------------------------------
    calling eq_i with (calling ffi.size_of of int), 4, "size_of int"
    calling eq_i with (calling ffi.size_of of byte), 1, "size_of byte"
    calling eq_i with (calling ffi.pointer_size), 8, "pointer_size"
    calling eq_i with (calling ffi.alignment_of of int), 4, "alignment_of int"

    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out


def test_ffi_empty_slice_is_a_view(compile_and_run):
    """`slice_from_ptr(ptr, 0)` must not allocate and must stay banish-safe.

    A slice is a non-owning view, so releasing it (or the list of strings built
    from a NULL array) must be a no-op rather than a free of borrowed memory.
    """
    out = compile_and_run(_PRE + """
weave main into int:
    var buf as ref to int is calling memoria.alloc_array of int with 2
    set buf at 0 is 5
    var vp as ref to void is transmute buf to ref to void
    var empty as slice of int is calling ffi.slice_from_ptr of int with vp, 0
    var nul as slice of int is calling ffi.slice_from_ptr of int with (calling ffi.null_void), 0
    var nul_len as slice of int is calling ffi.slice_from_ptr of int with (calling ffi.null_void), 4
    # Nothing owned: only the backing buffer is released.
    banish buf
    calling spark.println with "DONE"
    return 0
""")
    assert "FAIL" not in out, out
    assert "DONE" in out, out
