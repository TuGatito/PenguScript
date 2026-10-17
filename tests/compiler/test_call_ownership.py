"""A `string` parameter is borrowed; the caller owns a temporary it creates.

`calling spark.println with "{a} {b}"` used to leak: the interpolation allocates
a `PenguString`, the parameter borrows it, and nobody freed it.  The code
generator now binds such a temporary to a local, makes the call and banishes it —
but only when that is *sound*:

* the result must not be able to carry the borrowed buffer (`void` or a scalar
  always; a `string` result only when it is a different buffer, since a callee
  may return its parameter — `weave id with s as string into string: return s`);
* a container/rune/reference result may have stored the pointer, so it is left
  alone (the documented manual-memory rule: the callee must not outlive the
  borrow, and the caller keeps ownership of what it passed).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _compile(emit_c, tmp_path, source: str) -> str:
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


def test_interpolation_argument_is_released(emit_c):
    c = emit_c("""
weave take with s as string into void:
    return

weave f with a as int into int:
    calling take with "value {a}"
    return 0
""")
    assert "pengu_banish_string(&_arg_" in c, c


def test_to_string_argument_is_released(emit_c):
    c = emit_c("""
weave take with s as string into void:
    return

weave f with a as int into int:
    calling take with (a to string)
    return 0
""")
    assert "pengu_banish_string(&_arg_" in c, c


def test_plain_variable_argument_is_not_released(emit_c):
    """The caller owns the variable; the callee only borrows it."""
    c = emit_c("""
weave take with s as string into void:
    return

weave f into int:
    var s as string is "hi"
    calling take with s
    banish s
    return 0
""")
    assert "pengu_banish_string(&_arg_" not in c, c


def test_literal_argument_is_not_released(emit_c):
    c = emit_c("""
weave take with s as string into void:
    return

weave f into int:
    calling take with "plain"
    return 0
""")
    assert "_arg_" not in c, c


def test_string_returning_call_guards_the_release(emit_c):
    """A callee may return its parameter: release only a different buffer."""
    c = emit_c("""
weave identity with s as string into string:
    return s

weave f with a as int into int:
    var out as string is calling identity with "value {a}"
    banish out
    return 0
""")
    assert ".data != " in c and "pengu_banish_string(&_arg_" in c, c


def test_container_returning_call_keeps_the_argument(emit_c):
    """The result could hold the borrowed pointer, so nothing is released."""
    c = emit_c("""
weave wrap with s as string into maybe string:
    return some s

weave f with a as int into int:
    var m as maybe string is calling wrap with "value {a}"
    return 0
""")
    assert "pengu_banish_string(&_arg_" not in c, c


def test_scalar_returning_call_releases(emit_c):
    c = emit_c("""
weave length_of with s as string into int:
    return s.length

weave f with a as int into int:
    return calling length_of with "value {a}"
""")
    assert "pengu_banish_string(&_arg_" in c, c


@pytest.mark.slow
def test_released_argument_compiles_without_warnings(emit_c, tmp_path):
    _compile(emit_c, tmp_path, """
weave take with s as string into void:
    return

weave length_of with s as string into int:
    return s.length

weave identity with s as string into string:
    return s

weave f with a as int into int:
    calling take with "value {a}"
    var n as int is calling length_of with "len {a}"
    var s as string is calling identity with "id {a}"
    banish s
    return n
""")


@pytest.mark.slow
def test_interpolation_temporary_is_freed_at_runtime(compile_and_run):
    """The behavioural proof: the program is leak-free while printing."""
    out = compile_and_run("""
import std.spark

weave bump with x as int into int:
    return x + 1

weave main into int:
    var a as int is 1
    var b as int is 2
    calling spark.println with "{calling bump with a} {calling bump with b}"
    calling spark.println_int with 41
    return 0
""", tag="arg_ownership")
    assert out.strip().splitlines() == ["2 3", "41"]


@pytest.mark.slow
def test_pass_through_argument_stays_alive(compile_and_run):
    """A callee returning its parameter must not hand back freed memory."""
    out = compile_and_run("""
import std.spark

weave identity with s as string into string:
    return s

weave main into int:
    var a as int is 7
    var msg as string is calling identity with "v={a}"
    calling spark.println with msg
    banish msg
    return 0
""", tag="arg_passthrough")
    assert out.strip() == "v=7"


def test_strict_c99_statement_call_releases_in_a_block(parse_and_check):
    """Strict mode has no statement expressions; a statement call uses a block."""
    from pengu_parser.pengu_codegen import PenguCodegen
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    source = """
weave take with s as string into void:
    return

weave f with a as int into int:
    calling take with "value {a}"
    return 0
"""
    ast = PenguParser().parse(source)
    checker = PenguChecker(base_dir=".")
    checker.check(ast, source=source, filename="t.pengu")
    codegen = PenguCodegen(checker.symbols, ["t.pengu"], ".", compile_env=checker.compile_env,
                           use_gnu_extensions=False)
    codegen.collect_declarations([("t.pengu", ast)])
    c = codegen.generate_bundle()
    assert "__extension__" not in c, c
    assert "pengu_banish_string(&_arg_" in c, c
