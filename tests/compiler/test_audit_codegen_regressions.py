"""Regression tests for the 2.0.1 audit's code-generator fixes.

Two front-end / back-end mismatches were found while running the stdlib under
ASan and were fixed in the compiler:

* the epilogue of every weave appended an unconditional ``pengu_frame_pop();``
  after the body, so a body ending in ``return`` emitted an *unreachable call*.
  Under ``gcc -O0 -fsanitize=address`` that made the whole bundle report 155
  spurious ``-Wreturn-type: control reaches end of non-void function`` warnings;
* ``type_has_derived_nexus`` treated any heap-owning rune as if it had derived
  ``Nexus``, so ``banish`` on a rune without an explicit ``derive Nexus``
  (``SetString``, ``SetInt``, ``ResultInt``, a user rune with a ``string``
  field) was accepted and lowered to ``_pengu_cleanup_<T>`` -- a function the
  generator never emits.  The bundle then failed to compile with "implicit
  declaration of function '_pengu_cleanup_<T>'".
"""
from __future__ import annotations

import re
import shutil
import subprocess

import pytest


# --------------------------------------------------------------------------
# Unreachable frame-pop after a return
# --------------------------------------------------------------------------

def test_no_unreachable_frame_pop_after_return(emit_c):
    """A body ending in `return` must not emit a call after the return."""
    c = emit_c("""
weave give with i as int into int:
    if i > 0:
        return i
    return 0
""")
    assert not re.search(r"return [^;]+;\s*\n\s*pengu_frame_pop\(\);", c), (
        "unreachable pengu_frame_pop() emitted after a return:\n" + c
    )


def test_void_fall_through_still_pops(emit_c):
    """The fall-through exit of a void weave keeps its frame pop."""
    c = emit_c("""
import std.spark

weave talk with x as int into void:
    if x > 0:
        return
    calling spark.println with "neg"
""")
    assert "pengu_frame_pop();" in c


def test_sanitizer_build_has_no_return_type_warning(pengu_root, has_cc, tmp_path):
    """Compile a bundle ending in `return` at -O0 with ASan and -Werror.

    This is the exact combination that used to produce the spurious
    ``-Wreturn-type`` diagnostics; before the fix the compile below failed.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_codegen import PenguCodegen, set_release_unsafe
    from pengu_parser.pengu_parser import PenguParser

    source = """
weave give with i as int into int:
    if i > 0:
        return i
    return 0 - i

weave main into int:
    var i as int is 0
    while i < 3:
        var v as int is calling give with i
        set i is i + 1
    return 0
"""
    ast = PenguParser().parse(source)
    checker = PenguChecker(base_dir=str(pengu_root))
    checker.check(ast, source=source, filename="t.pengu")
    set_release_unsafe(False)
    codegen = PenguCodegen(checker.symbols, ["t.pengu"], str(pengu_root),
                           compile_env=checker.compile_env)
    codegen.collect_declarations([("t.pengu", ast)])
    bundle = tmp_path / "bundle.c"
    bundle.write_text(codegen.generate_bundle(), encoding="utf-8")

    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    res = subprocess.run(
        [cc, "-c", str(bundle), "-o", str(tmp_path / "bundle.o"),
         "-O0", "-Wall", "-std=c11", "-fsanitize=address",
         "-Werror=return-type",
         "-I", str(pengu_root), "-I", str(pengu_root / "build" / "include")],
        capture_output=True, text=True, timeout=600,
    )
    assert res.returncode == 0, (
        f"-Wreturn-type build failed:\n{res.stdout}\n{res.stderr}"
    )


# --------------------------------------------------------------------------
# Map indexing must not emit a bare statement expression
# --------------------------------------------------------------------------

def test_map_index_is_extension_wrapped(emit_c):
    """A map `at` read must be `__extension__(({ ... }))`, not `({ ... })`."""
    c = emit_c("""
weave peek_map with m as map of string to int, k as string into int:
    return m at k
""")
    assert "(__extension__(({ PenguString _k_" in c, c
    assert "= ({ PenguString _k_" not in c, c


def test_map_program_is_pedantic_clean(pengu_root, has_cc, tmp_path):
    """The whole bundle compiles with `-Wall -Wextra -Wpedantic -Werror`.

    Before the audit the map-index statement expression was emitted without
    `__extension__`, so one `map of string to int` access produced hundreds of
    `ISO C forbids braced-groups within expressions` diagnostics.
    """
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_codegen import PenguCodegen, set_release_unsafe
    from pengu_parser.pengu_parser import PenguParser

    source = """
weave peek_map with m as map of string to int, k as string into int:
    return m at k

weave store_map with m as map of string to int, k as string, v as int into void:
    calling m.put with k, v

weave main into int:
    var m as map of string to int is map of string to int
    calling store_map with m, "a", 1
    var v as int is calling peek_map with m, "a"
    banish m
    return v
"""
    ast = PenguParser().parse(source)
    checker = PenguChecker(base_dir=str(pengu_root))
    checker.check(ast, source=source, filename="t.pengu")
    set_release_unsafe(False)
    codegen = PenguCodegen(checker.symbols, ["t.pengu"], str(pengu_root),
                           compile_env=checker.compile_env)
    codegen.collect_declarations([("t.pengu", ast)])
    bundle = tmp_path / "bundle.c"
    bundle.write_text(codegen.generate_bundle(), encoding="utf-8")

    cc = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    res = subprocess.run(
        [cc, "-c", str(bundle), "-o", str(tmp_path / "bundle.o"),
         "-O0", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
         "-I", str(pengu_root), "-I", str(pengu_root / "build" / "include")],
        capture_output=True, text=True, timeout=600,
    )
    assert res.returncode == 0, (
        f"pedantic build failed:\n{res.stdout}\n{res.stderr}"
    )


# --------------------------------------------------------------------------
# `banish` on a rune requires an explicit `derive Nexus`
# --------------------------------------------------------------------------

def test_banish_rejects_rune_without_nexus(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Plain:
    x as int
    label as string

weave drop with p as Plain into void:
    banish p
""")
    assert any(e.code == "E0008" for e in errors), [e.code for e in errors]


def test_banish_accepts_rune_with_explicit_nexus(parse_and_check):
    errors, _, _ = parse_and_check("""
rune Owned derive Nexus:
    label as string

weave drop with p as Owned into void:
    banish p
""")
    assert errors == [], [str(e) for e in errors]


def test_banish_accepts_legacy_container_types(parse_and_check):
    """string / list / map / maybe / result stay banishable."""
    errors, _, _ = parse_and_check("""
weave drop with s as string, l as list of int, m as map of string to int, mb as maybe int into void:
    banish s
    banish l
    banish m
    banish mb
""")
    assert errors == [], [str(e) for e in errors]
