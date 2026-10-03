"""Roadmap Phase 2 / §2.1 — `--strict-c99` emits portable C99.

The GNU default wraps expression-level statements in `__extension__(({ ... }))`
and uses `__auto_type`.  Strict mode hoists those statements into the enclosing
statement and returns a concrete temporary, so the generated C compiles as
`-std=c99 -pedantic-errors`.
"""

import os
import subprocess

import pytest

from pengu_parser.pengu_codegen import CTypeMapper, set_restrict_keyword
from pengu_parser.pengu_types import INT_TYPE, RefType
from tests.conftest import (
    BUILD_DIR, BUILD_INCLUDE, BUILD_LIB, HAVE_CC, HAVE_RUNTIME, REPO, gen_bundle,
    have_tool, runtime_link_flags, runtime_tail_flags,
)

_PROG = """\
omen Color:
  Red
  Blue

weave maybe_pick with flag as bool into maybe int:
  var m as maybe int is some 5
  if flag:
    return m
  return maybe none

weave main into int:
  var xs as list of int is [1, 2, 3]
  var total as int is 0
  for x in xs:
    set total is total + x
  var evens is for x in xs when x % 2 == 0 then x
  var m as maybe int is some total
  var v as int is m or else 0
  var c as Color is Color.Red
  var n as int is judge c:
    when Color.Red -> 1
    when Color.Blue -> 2
  var d as map of string to int is {"a": 1}
  var has as bool is "a" in d
  var arr as array of int with size 3 is [4, 5, 6]
  var cond as bool is 2 in arr
  var s as string is "n={n}"
  var out as int is 0
  if has:
    set out is out + 1
  if cond:
    set out is out + 1
  if s length > 0:
    set out is out + 1
  if v + n + (evens.len) > 0:
    set out is out + 1
  return 0
"""


def test_strict_mode_has_no_gnu_extensions():
    c = gen_bundle(_PROG, strict_c99=True)
    assert "__extension__" not in c
    assert "__auto_type" not in c
    assert "({ " not in c


def test_gnu_mode_is_still_the_default():
    c = gen_bundle(_PROG)
    # Default output must keep using statement expressions (no behaviour change).
    assert "__extension__" in c


@pytest.mark.skipif(not HAVE_CC, reason="no C compiler available")
@pytest.mark.skipif(not HAVE_RUNTIME, reason="libpengu_runtime.a not built")
def test_strict_mode_compiles_as_pedantic_c99(tmp_path):
    cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
    c = gen_bundle(_PROG, strict_c99=True)
    src = tmp_path / "bundle.c"
    src.write_text(c, encoding="utf-8")
    exe = tmp_path / "prog"
    cmd = [
        cc, "-std=c99", *(["-pedantic-errors"] if os.name != "nt" else ["-pedantic"]),
        str(src), "-o", str(exe),
        f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}", f"-L{BUILD_LIB}",
        *runtime_link_flags(), *runtime_tail_flags(),
    ]
    compiled = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert compiled.returncode == 0, f"strict C99 compile failed:\n{compiled.stderr}"
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"program failed: rc={run.returncode}\n{run.stderr}"


def test_strict_mode_compiles_with_tcc(tmp_path):
    """TCC is bundled with the releases; it must accept the strict bundle."""
    try:
        from pengu_tcc import find_tcc
    except Exception:
        pytest.skip("pengu_tcc not importable")
    tcc = find_tcc()
    if not tcc:
        pytest.skip("TCC not available")
    c = gen_bundle(_PROG, strict_c99=True)
    src = tmp_path / "bundle.c"
    src.write_text(c, encoding="utf-8")
    obj = tmp_path / "bundle.o"
    cmd = [tcc, "-std=c11", "-c", str(src), "-o", str(obj),
           f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, f"TCC rejected the strict bundle:\n{res.stderr}"


def test_restrict_keyword_is_portable():
    set_restrict_keyword("msvc")
    assert "__restrict" in CTypeMapper.to_c_decl(RefType(INT_TYPE), "p", restrict=True)
    assert " restrict " not in CTypeMapper.to_c_decl(RefType(INT_TYPE), "p", restrict=True)
    set_restrict_keyword("gcc")
    decl = CTypeMapper.to_c_decl(RefType(INT_TYPE), "p", restrict=True)
    assert " restrict " in decl
    assert "__restrict" not in decl
