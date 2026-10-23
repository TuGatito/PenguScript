"""Codegen and end-to-end regressions found while building ``std.functor``.

Three code-generation bugs were exposed by a rune that stores a function
pointer, and each one is pinned here at the level that can catch it:

* a struct/union field of function-pointer type emitted ``R (*)(A) name;``
  instead of ``R (*name)(A);`` (invalid C).  The test asserts the declarator
  shape and compiles it with every available C compiler under
  ``-Wall -Wextra -Werror``;
* a by-value field of a *monomorphized* generic rune was emitted before the
  generated struct existed ("field has incomplete type").  The topological
  ordering of rune definitions is asserted through the real CLI;
* a generic rune's method was registered as a monomorphization while its type
  argument was still a ``shard`` parameter (``Box_T_get``), emitting a C
  prototype whose type does not exist.  A concrete call must emit only
  ``Box_int_get`` and run.

The ``donum``/partial-initializer cases are here too: a rune with a ``list``
field used to zero that field (``elem_size == 0``), so the first ``push``
copied zero bytes.  They are compiler-level fixes that ``std.functor``'s
context runes and ``loom.for_each_ctx``'s accumulator rely on.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _compilers() -> list[str]:
    return [c for c in (shutil.which("gcc"), shutil.which("clang")) if c]


def _compile(emit_c, tmp_path, source: str, tag: str = "bundle") -> str:
    """Emits the C bundle for ``source`` and compiles it with every compiler."""
    bundle = tmp_path / f"{tag}.c"
    bundle.write_text(emit_c(source), encoding="utf-8")
    compilers = _compilers()
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        out = tmp_path / f"{tag}_{Path(cc).name}.o"
        res = subprocess.run(
            [cc, "-c", str(bundle), "-o", str(out),
             "-O0", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-I", str(ROOT), "-I", str(ROOT / "build" / "include")],
            capture_output=True, text=True, timeout=300,
        )
        assert res.returncode == 0, (
            f"{cc} rejected the generated C:\n{res.stdout}\n{res.stderr}\n---\n"
            + bundle.read_text(encoding="utf-8")
        )
    return bundle.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Function-pointer fields
# ---------------------------------------------------------------------------

_FN_FIELD = """
rune Handler:
    fn_ptr as ref to weave with ctx as ref to void, a as int into int
    ctx as ref to void

# A by-value use keeps the rune in the bundle under --prune-types; the test is
# about the declarator shape, not about an unreachable type.
weave takes_handler with h as Handler into int:
    return 0
"""


def test_rune_function_pointer_field_is_a_valid_declarator(emit_c, tmp_path):
    c = _compile(emit_c, tmp_path, _FN_FIELD, "rune_fn")
    # The name lives inside the declarator: `int32_t (*fn_ptr)(void*, int32_t)`.
    assert "(*fn_ptr)(void*, int32_t)" in c
    # The broken shape appended the name after the parenthesised type.
    assert "(*) fn_ptr" not in c


def test_echo_function_pointer_field_is_a_valid_declarator(emit_c, tmp_path):
    source = """
echo Value:
    as_int as int
    as_fn as ref to weave with ctx as ref to void into int

weave takes_value with v as Value into int:
    return 0
"""
    c = _compile(emit_c, tmp_path, source, "echo_fn")
    assert "(*as_fn)(void*)" in c
    assert "(*) as_fn" not in c


def test_omen_function_pointer_payload_is_a_valid_declarator(emit_c, tmp_path):
    source = """
omen Slot:
    Empty
    Callback with fn_ptr as ref to weave with ctx as ref to void into int

weave takes_slot with s as Slot into int:
    return 0
"""
    c = _compile(emit_c, tmp_path, source, "omen_fn")
    assert "(*fn_ptr)(void*)" in c
    assert "(*) fn_ptr" not in c


def test_function_pointer_field_can_be_read_and_called(compile_and_run):
    source = """
import std.spark

rune Ops:
    inc as ref to weave with x as int into int

weave plus_one with x as int into int:
    return x + 1

weave main into int:
    var o as Ops is with inc is plus_one
    let f as ref to weave with x as int into int is o.inc
    calling spark.println with "{calling f with 4}"
    return 0
"""
    assert compile_and_run(source, tag="fn_field_call").strip() == "5"


def test_array_of_function_pointers_is_a_valid_declarator(emit_c, tmp_path):
    source = """
rune Table:
    fns as array of weave with x as int into int with size 2

weave takes_table with t as Table into int:
    return 0
"""
    c = _compile(emit_c, tmp_path, source, "fn_array")
    assert "(*fns[2])(int32_t)" in c
    assert "(*) fns" not in c


# ---------------------------------------------------------------------------
# Monomorphized generic runes
# ---------------------------------------------------------------------------

_GENERIC_RUNE = """
import std.spark

rune Box shard T:
    value as T

enchanting Box shard T:
    weave get into T:
        return self->value

weave main into int:
    var b as Box of int is with value is 7
    calling spark.println with "{calling b.get}"
    return 0
"""


def test_concrete_generic_rune_method_emits_only_the_specialization(emit_c):
    c = emit_c(_GENERIC_RUNE)
    assert "Box_int_get" in c
    # The unspecialized template had an invalid `Box*` receiver type.
    assert "Box_T_get" not in c
    assert "Box_get_T" not in c


def test_concrete_generic_rune_method_runs(compile_and_run):
    assert compile_and_run(_GENERIC_RUNE, tag="generic_box").strip() == "7"


def test_a_rune_can_store_a_monomorphized_generic_rune(compile_and_run):
    """A by-value field of a generic instantiation must be defined first."""
    source = """
import std.spark

rune Box shard T:
    value as T

rune Holder:
    boxed as Box of int

weave main into int:
    var h as Holder is with boxed is with value is 9
    calling spark.println with "{h.boxed.value}"
    return 0
"""
    assert compile_and_run(source, tag="generic_field").strip() == "9"


_FN_VOID = """
import std.functor
import std.spark

rune Button:
    label as string
    on_click as functor.Fn1 of int, void

weave log_click with clicks as ref to int, button as int into void:
    set essence of clicks is (essence of clicks) + 1
    calling spark.println with "button {button} clicked {essence of clicks}"

weave main into int:
    var clicks as int is 0
    var f as functor.Fn1 of int, void is calling functor.make_fn1 with log_click, (sigil of clicks)
    var b as Button is with label is "Save", on_click is f
    calling b.on_click.call with 1
    return 0
"""


def test_a_generic_void_result_emits_a_bare_return(emit_c, compile_and_run):
    """`Fn1<A, void>` used to emit `void _ret = call; return _ret;`."""
    c = emit_c(_FN_VOID)
    assert "\n  void _ret_" not in c
    out = compile_and_run(_FN_VOID, tag="fn_void")
    assert out.strip().splitlines()[-1] == "button 1 clicked 1", out


# ---------------------------------------------------------------------------
# Semantic defaults for container fields
# ---------------------------------------------------------------------------

_PARTIAL_INIT = """
import std.spark

rune Collector:
    total as int
    items as list of int

weave main into int:
    var c as Collector is with total is 3
    calling c.items.push with 7
    calling c.items.push with 8
    calling spark.println with "total={c.total} len={calling c.items.len} first={c.items at 0}"
    banish c.items
    return 0
"""


def test_partial_struct_init_gives_a_container_field_an_empty_default(compile_and_run):
    out = compile_and_run(_PARTIAL_INIT, tag="partial_init").strip()
    assert out == "total=3 len=2 first=7", out


def test_donum_of_a_rune_with_a_list_field_is_a_usable_empty_list(compile_and_run):
    source = """
import std.spark

rune Collector:
    total as int
    items as list of int

weave main into int:
    var c as Collector is donum Collector
    calling c.items.push with 9
    calling spark.println with "len={calling c.items.len} first={c.items at 0}"
    banish c.items
    return 0
"""
    out = compile_and_run(source, tag="donum_list").strip()
    assert out == "len=1 first=9", out


def test_donum_of_a_nested_rune_with_a_list_field(compile_and_run):
    source = """
import std.spark

rune Inner:
    items as list of int

rune Outer:
    inner as Inner
    label as string

weave main into int:
    var o as Outer is donum Outer
    calling o.inner.items.push with 5
    calling spark.println with "{calling o.inner.items.len}"
    banish o.inner.items
    return 0
"""
    out = compile_and_run(source, tag="donum_nested").strip()
    assert out == "1", out
