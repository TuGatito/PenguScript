"""Track B10: generic functions used as values materialize from the expected type."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _check(pengu_cli, tmp_path: Path, source: str, tag: str) -> tuple[int, str]:
    script = tmp_path / f"{tag}.pengu"
    script.write_text(source, encoding="utf-8")
    res = pengu_cli("check", str(script))
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def _expand(pengu_cli, tmp_path: Path, source: str, tag: str,
            extra: tuple[str, ...] = ()) -> str:
    script = tmp_path / f"{tag}.pengu"
    script.write_text(source, encoding="utf-8")
    out = tmp_path / f"{tag}.c"
    res = pengu_cli("expand", str(script), "-o", str(out), *extra)
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    return out.read_text(encoding="utf-8")


def test_local_generic_function_value_runs(compile_and_run):
    out = compile_and_run("""
import std.spark

weave twice shard T with x as T into T:
    return x

weave main into int:
    var f as weave with int into int is twice
    calling spark.println_int with (calling f with 2)
    return 0
""", tag="gen_value")
    assert out.strip() == "2"


def test_generic_function_value_as_callback_argument(compile_and_run):
    out = compile_and_run("""
import std.spark

weave twice shard T with x as T into T:
    return x

weave apply with f as weave with int into int, x as int into int:
    return calling f with x

weave main into int:
    calling spark.println_int with (calling apply with twice, 3)
    return 0
""", tag="gen_callback")
    assert out.strip() == "3"


def test_generic_function_value_as_return(compile_and_run):
    out = compile_and_run("""
import std.spark

weave twice shard T with x as T into T:
    return x

weave pick into weave with int into int:
    return twice

weave main into int:
    var f as weave with int into int is calling pick
    calling spark.println_int with (calling f with 4)
    return 0
""", tag="gen_return")
    assert out.strip() == "4"


def test_multi_parameter_generic_function_value(compile_and_run):
    out = compile_and_run("""
import std.spark

weave first shard A, B with a as A, b as B into A:
    return a

weave main into int:
    var f as weave with int, string into int is first
    calling spark.println_int with (calling f with 7, "x")
    return 0
""", tag="gen_multi")
    assert out.strip() == "7"


def test_value_is_emitted_as_a_concrete_instance(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, """
weave twice shard T with x as T into T:
    return x

weave main into int:
    var f as weave with int into int is twice
    return calling f with 2
""", "gen_instance")
    assert "twice_int" in c
    assert "((int32_t (*)(int32_t))twice_int)" in c
    assert "((int32_t (*)(int32_t))twice)" not in c


def test_generic_value_needs_a_concrete_function_type(pengu_cli, tmp_path):
    rc, out = _check(pengu_cli, tmp_path, """
weave twice shard T with x as T into T:
    return x

weave main into int:
    var f as int is twice
    return 0
""", "gen_bad")
    assert rc != 0
    assert "E0005" in out
    assert "without a concrete function type" in out


def test_generic_value_accepts_a_concrete_string_type(pengu_cli, tmp_path):
    rc, out = _check(pengu_cli, tmp_path, """
weave ident shard T with x as T into T:
    return x

weave main into int:
    var f as weave with string into string is ident
    return 0
""", "gen_string")
    assert rc == 0, out


def test_generic_value_rejects_bound_violation(pengu_cli, tmp_path):
    rc, out = _check(pengu_cli, tmp_path, """
weave ident shard T where T: Num with x as T into T:
    return x

weave main into int:
    var f as weave with string into string is ident
    return 0
""", "gen_bound")
    assert rc != 0
    assert "E0032" in out
    assert "'Num'" in out


def test_generic_value_inside_generic_function_needs_concrete_type(pengu_cli, tmp_path):
    rc, out = _check(pengu_cli, tmp_path, """
weave twice shard T with x as T into T:
    return x

weave make shard T into weave with T into T:
    return twice

weave main into int:
    return 0
""", "gen_nested")
    assert rc != 0
    assert "E0005" in out


def test_imported_std_generic_function_value(compile_and_run):
    out = compile_and_run("""
import std.spark
import std.atlas

alias IntToStringMap as map of int to string

weave main into int:
    var f as weave with IntToStringMap into int is atlas.map_size
    var m as IntToStringMap is donum (IntToStringMap)
    calling spark.println_int with (calling f with m)
    return 0
""", tag="gen_imported")
    assert out.strip() == "0"


def test_generic_value_survives_type_pruning(pengu_cli, tmp_path):
    c = _expand(pengu_cli, tmp_path, """
weave twice shard T with x as T into T:
    return x

weave main into int:
    var f as weave with int into int is twice
    return calling f with 2
""", "gen_pruned", extra=("--prune-types",))
    assert "twice_int" in c


def test_imported_user_generic_function_value(pengu_cli, tmp_path):
    (tmp_path / "a.pengu").write_text(
        "weave twice shard T with x as T into T:\n    return x\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.pengu"
    main.write_text(
        "import a\n\n"
        "weave main into int:\n"
        "    var f as weave with int into int is a.twice\n"
        "    var x as int is calling f with 9\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = pengu_cli("run", "--keep", "--no-cache", str(main))
    assert res.returncode == 0, (res.stdout or "") + (res.stderr or "")
    bundle = (tmp_path / "build" / "main_run" / "bundle.c").read_text(encoding="utf-8")
    assert "a_twice_int" in bundle
    assert "((int32_t (*)(int32_t))a_twice_int)" in bundle
