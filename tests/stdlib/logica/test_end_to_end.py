"""`std.logica` — end to end.

Three levels: the module's own embedded `test` blocks, a realistic permission
check built out of `or_with`/`and_with`/`toggle`, and the emitted symbols
(`bool_to_int`, `bool_implies`, …).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/logica/test_end_to_end.py`` -> `logica` -> `stdlib` ->
#: `tests` -> the checkout.
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.xdist_group("pengu-module-tests")
def test_module_self_tests_pass():
    """``pengu test --entry std/logica.pengu``: all embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "logica.pengu")],
        capture_output=True, text=True, timeout=300,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 44 test(s) passed." in res.stdout, res.stdout


def test_permission_check(compile_and_run):
    """Access is granted to an admin, or to an owner of an unlocked resource."""
    out = compile_and_run("""
import std.spark
import std.logica

weave can_access with is_admin as bool, is_owner as bool, is_locked as bool into bool:
    var unlocked as bool is calling is_locked.get_toggle
    var owner_ok as bool is calling is_owner.get_and_with with unlocked
    return calling is_admin.get_or_with with owner_ok

weave main into int:
    var t as bool is true
    var f as bool is false
    calling spark.println with "{calling can_access with t, f, f}"
    calling spark.println with "{calling can_access with f, t, f}"
    calling spark.println with "{calling can_access with f, t, t}"
    calling spark.println with "{calling can_access with f, f, f}"
    return 0
""")
    assert out.count("true") == 2, out
    assert out.count("false") == 2, out


def test_flag_counter(compile_and_run):
    """`to_int` turns a predicate into a summable 0/1."""
    out = compile_and_run("""
import std.spark
import std.logica

weave main into int:
    var total as int is 0
    var a as bool is true
    var b as bool is false
    var c as bool is true
    set total is total + (calling a.to_int)
    set total is total + (calling b.to_int)
    set total is total + (calling c.to_int)
    calling spark.println with "{total}"
    return 0
""")
    assert "2" in out, out


def test_bool_symbols_are_emitted(tmp_path):
    """Each method becomes one plain C `bool_*` function."""
    source = tmp_path / "logica_symbols.pengu"
    source.write_text(
        "import std.logica\n"
        "weave main into int:\n"
        "    var a as bool is true\n"
        "    var b as bool is false\n"
        "    let n is calling a.to_int\n"
        "    let x is calling a.get_xor with b\n"
        "    let i is calling a.get_implies with b\n"
        "    let t is calling a.get_toggle\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "expand", str(source)],
        capture_output=True, text=True, timeout=180,
        cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, f"expand failed:\n{res.stdout}\n{res.stderr}"
    bundle = res.stdout
    for symbol in ("bool_to_int", "bool_xor", "bool_implies", "bool_toggle"):
        assert re.search(rf"\b{re.escape(symbol)}\b", bundle), f"{symbol} missing"
    assert "pengu_to_int" not in bundle, "symbols must not carry a pengu_ prefix"
