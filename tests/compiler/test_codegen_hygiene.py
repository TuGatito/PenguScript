"""Generated-C hygiene: no warnings for code that does nothing, complete types.

C is the boundary, so the compiler's own output must compile under
``-Wall -Wextra -Werror`` even when the *program* ignores a binding.  This file
pins the three shapes that used to warn:

* a parameter the body never reads (`type of p` is the sharpest case: the
  operand is inspected, never emitted) gets a ``(void)name;``;
* a local binding the body never reads gets the same cast right after its
  declaration;
* a tuple-typed rune *field* needs its product struct defined before the rune,
  or C reports "field has incomplete type".
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _compile(emit_c, tmp_path, source: str) -> str:
    """Emits the bundle for ``source`` and compiles it with every C compiler."""
    bundle = tmp_path / "bundle.c"
    bundle.write_text(emit_c(source), encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    compilers = [c for c in (shutil.which("gcc"), shutil.which("clang")) if c]
    if not compilers:
        pytest.skip("no C compiler available")
    for cc in compilers:
        res = subprocess.run(
            [cc, "-c", str(bundle), "-o", str(tmp_path / f"{Path(cc).name}.o"),
             "-O0", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-Wno-unused-function",
             "-I", str(root), "-I", str(root / "build" / "include")],
            capture_output=True, text=True, timeout=600,
        )
        assert res.returncode == 0, (
            f"{cc} rejected the generated C:\n{res.stdout}\n{res.stderr}\n---\n"
            + bundle.read_text(encoding="utf-8")
        )
    return bundle.read_text(encoding="utf-8")


def test_unused_parameter_gets_a_void_cast(emit_c):
    c = emit_c("""
weave ignored with q as int into int:
    return 0
""")
    assert "(void)q;" in c, c


def test_used_parameter_gets_no_cast(emit_c):
    c = emit_c("""
weave used with q as int into int:
    return q + 1
""")
    assert "(void)q;" not in c, c


def test_parameter_read_only_by_type_of_is_unused_in_c(emit_c):
    """`type of p` inspects the operand; it never references it."""
    c = emit_c("""
weave describe shard T with x as T into string:
    return type of x

weave use into int:
    var a as string is calling describe with 42
    return 0
""")
    assert "int32_t x" in c, c
    assert "(void)x;" in c, c


def test_unused_receiver_gets_a_void_cast(emit_c):
    c = emit_c("""
rune Box:
    tag as string

enchanting Box:
    weave label into string:
        return "box"
""")
    assert "(void)self;" in c, c


def test_unused_local_gets_a_void_cast_after_its_declaration(emit_c):
    c = emit_c("""
weave f with q as int into int:
    var ignored as int is q + 1
    var unused_str as string is "hi"
    let also_unused as bool is true
    return q
""")
    assert "(void)ignored;" in c, c
    assert "(void)unused_str;" in c, c
    assert "(void)also_unused;" in c, c
    # The cast follows the declaration, not the function prologue.
    decl_line = next(i for i, line in enumerate(c.splitlines()) if "int32_t ignored" in line)
    cast_line = next(i for i, line in enumerate(c.splitlines()) if "(void)ignored;" in line)
    assert cast_line > decl_line, c


def test_used_local_gets_no_cast(emit_c):
    c = emit_c("""
weave f with q as int into int:
    var used as int is q + 1
    return used
""")
    assert "(void)used;" not in c, c


def test_local_read_only_by_type_of_is_unused_in_c(emit_c):
    c = emit_c("""
weave f with q as int into string:
    var only_typed as int is q
    return type of only_typed
""")
    assert "(void)only_typed;" in c, c


@pytest.mark.slow
def test_unused_bindings_compile_cleanly(emit_c, tmp_path):
    _compile(emit_c, tmp_path, """
weave ignored with q as int, p as string into int:
    var dropped as int is q * 2
    return 0

weave describe shard T with x as T into string:
    return type of x

weave use into int:
    var a as string is calling describe with 42
    return 0
""")


@pytest.mark.slow
def test_tuple_field_of_a_rune_compiles(emit_c, tmp_path):
    """A tuple *field* needs its product struct complete before the rune."""
    c = _compile(emit_c, tmp_path, """
rune Holder:
    pair as (int, bool)
    name as string

weave make into (int, bool):
    return 1, true

weave f into int:
    var h as Holder is with pair is calling make, name is "x"
    let (first, second) is h.pair
    return first
""")
    tuple_def = c.index("struct _pengu_tup_")
    rune_def = c.index("struct Holder {")
    assert tuple_def < rune_def, c
