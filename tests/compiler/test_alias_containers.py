"""`alias` is transparent: an alias of a container *is* that container.

`alias Numbers as list of int` names the same owning value as `list of int`, so
indexing, length, iteration, `banish` and assignability must all see through it.
Before 2.7.0 four separate sites compared the nominal wrapper instead of the
target, which made an aliased container unusable in four different ways.

The tests use ``emit_c`` (the C shape) and the real CLI (behaviour), because the
bugs lived in different layers: the checker rejected `banish`/assignment, and the
code generator emitted `numbers[0]` for a `PenguList`.
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


def test_alias_of_a_list_indexes_like_a_list(emit_c):
    c = emit_c("""
alias Numbers as list of int

weave f into int:
    var xs as Numbers is donum Numbers
    calling xs.push with 3
    return xs at 0
""")
    assert "pengu_list_at" in c, c


def test_alias_of_a_list_iterates(emit_c):
    c = emit_c("""
alias Numbers as list of int

weave total with xs as Numbers into int:
    var sum as int is 0
    for x in xs:
        set sum += x
    return sum
""")
    assert "pengu_list_at" in c, c


def test_alias_of_a_list_can_be_banished(emit_c):
    c = emit_c("""
alias Numbers as list of int

weave f into int:
    var xs as Numbers is donum Numbers
    calling xs.push with 3
    banish xs
    return 0
""")
    assert "pengu_banish_list" in c, c


def test_alias_of_a_slice_accepts_a_slice_value(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
alias Window as slice of int

weave f into int:
    var base as list of int is [1, 2, 3]
    var win as Window is base at 0 to 2
    return win at 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_alias_of_a_map_indexes_like_a_map(emit_c):
    c = emit_c("""
alias Registry as map of string to int

weave f into int:
    var m as Registry is donum Registry
    calling m.put with "a", 1
    return m at "a"
""")
    assert "pengu_map_get" in c, c


@pytest.mark.slow
def test_aliased_containers_behave_at_runtime(compile_and_run):
    out = compile_and_run("""
import std.spark

alias Numbers as list of int
alias Registry as map of string to int
alias Window as slice of int

weave total with xs as Numbers into int:
    var sum as int is 0
    for x in xs:
        set sum += x
    return sum

weave main into int:
    var xs as Numbers is donum Numbers
    calling xs.push with 1
    calling xs.push with 2
    calling spark.println with "len={xs.length} first={xs at 0} total={calling total with xs}"
    banish xs

    var reg as Registry is donum Registry
    calling reg.put with "k", 9
    calling spark.println with "m={reg at "k"}"

    var base as list of int is [5, 6, 7]
    var win as Window is base at 0 to 2
    calling spark.println with "w0={win at 0} wlen={win.length}"
    banish base
    return 0
""", tag="alias_containers")
    assert out.strip().splitlines() == [
        "len=2 first=1 total=3",
        "m=9",
        "w0=5 wlen=2",
    ]


@pytest.mark.slow
def test_aliased_container_compiles_without_warnings(emit_c, tmp_path):
    _compile(emit_c, tmp_path, """
alias Numbers as list of int
alias Registry as map of string to int

weave total with xs as Numbers into int:
    var sum as int is 0
    for x in xs:
        set sum += x
    return sum

weave f into int:
    var xs as Numbers is donum Numbers
    calling xs.push with 1
    var n as int is calling total with xs
    var m as Registry is donum Registry
    calling m.put with "a", n
    var v as int is m at "a"
    banish xs
    banish m
    return v
""")
