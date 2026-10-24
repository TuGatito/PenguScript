"""``std.functor`` — thick functions end to end.

``Fn0``..``Fn3`` are a function pointer plus a borrowed context.  These tests
drive the shipped module the way a program does:

* the embedded ``test`` blocks run through ``pengu test`` (contexts of rune,
  ``int``, ``string`` and ``ref to rune`` type, a stored ``Fn``, a ``Fn``
  parameter, a null context, ``is_null`` and ``call_or``);
* a realistic program builds one of each arity and calls it, so the C-level
  function-pointer path is exercised by the real compiler;
* a generated-C assertion proves construction does not allocate and that the
  emitted struct is exactly the two pointer fields the module promises.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/test_functor.py`` -> ``stdlib`` -> ``tests`` -> checkout.
ROOT = Path(__file__).resolve().parents[2]

_FUNCTOR_VERSION = "3.0.1"


@pytest.mark.xdist_group("pengu-module-tests")
def test_module_self_tests_pass():
    """``pengu test --entry std/functor.pengu``: every embedded block passes."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "functor.pengu")],
        capture_output=True, text=True, timeout=600,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 14 test(s) passed." in res.stdout, res.stdout


def test_every_arity_runs_end_to_end(compile_and_run):
    out = compile_and_run(
        """
import std.functor
import std.spark

rune Multiplier:
    factor as int

rune Marker:
    value as int

weave mul with m as ref to Multiplier, x as int into int:
    return m->factor * x

weave mul_sum with m as ref to Multiplier, x as int, y as int into int:
    return m->factor * (x + y)

weave mul_sum3 with m as ref to Multiplier, x as int, y as int, z as int into int:
    return m->factor * (x + y + z)

weave marker_value with z as ref to Marker into int:
    return z->value

weave main into int:
    var m as Multiplier is with factor is 3
    var mk as Marker is with value is 7
    var f0 as functor.Fn0 of int is calling functor.make_fn0 with marker_value, (sigil of mk)
    var f1 as functor.Fn1 of int, int is calling functor.make_fn1 with mul, (sigil of m)
    var f2 as functor.Fn2 of int, int, int is calling functor.make_fn2 with mul_sum, (sigil of m)
    var f3 as functor.Fn3 of int, int, int, int is calling functor.make_fn3 with mul_sum3, (sigil of m)
    calling spark.println with "{calling f0.call} {calling f1.call with 5} {calling f2.call with 2, 3} {calling f3.call with 1, 2, 3}"
    return 0
""",
    )
    assert out.strip().splitlines()[-1] == "7 15 15 18", out


def test_null_and_call_or(compile_and_run):
    out = compile_and_run(
        """
import std.functor
import std.spark

rune Multiplier:
    factor as int

weave mul with m as ref to Multiplier, x as int into int:
    return m->factor * x

weave main into int:
    var m as Multiplier is with factor is 4
    var real as functor.Fn1 of int, int is calling functor.make_fn1 with mul, (sigil of m)
    var empty as functor.Fn1 of int, int is donum (functor.Fn1 of int, int)
    calling spark.println with "real null={calling real.is_null} value={calling real.call_or with 5, -1}"
    calling spark.println with "empty null={calling empty.is_null} value={calling empty.call_or with 5, -1}"
    return 0
""",
    )
    lines = [l for l in out.strip().splitlines() if l.startswith(("real ", "empty "))]
    assert lines == [
        "real null=false value=20",
        "empty null=true value=-1",
    ], out


def test_construction_is_two_pointers_and_allocates_nothing(tmp_path):
    """The generated struct is the promised pair of pointers; no malloc."""
    source = tmp_path / "functor_probe.pengu"
    source.write_text(
        "import std.functor\n"
        "import std.spark\n"
        "\n"
        "rune Multiplier:\n"
        "    factor as int\n"
        "\n"
        "weave mul with m as ref to Multiplier, x as int into int:\n"
        "    return m->factor * x\n"
        "\n"
        "weave main into int:\n"
        "    var m as Multiplier is with factor is 2\n"
        "    var f as functor.Fn1 of int, int is calling functor.make_fn1 with mul, (sigil of m)\n"
        '    calling spark.println with "{calling f.call with 3}"\n'
        "    return 0\n",
        encoding="utf-8",
    )
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "expand", str(source)],
        capture_output=True, text=True, timeout=300,
        cwd=str(tmp_path),
        # This test asserts the emitted `#define` of a constant the program
        # does not otherwise need; `--prune-types` would correctly drop it.
        env={**os.environ, "PYTHONPATH": str(ROOT), "PENGU_PRUNE_TYPES": "0"},
    )
    assert res.returncode == 0, res.stderr
    c = res.stdout
    assert f'#define functor_FUNCTOR_VERSION pengu_string_from_cstr("{_FUNCTOR_VERSION}")' in c
    assert "struct Fn1_int_int {" in c
    assert "int32_t (*fn_ptr)(void*, int32_t);" in c
    assert "void* ctx;" in c
    # `make_fn1` is the constructor; its body must not allocate.  The exact
    # mangled spelling is an implementation detail (and DCE now drops the
    # duplicate alias specialization), so locate the constructor by the shape
    # of its emitted definition instead of hard-coding one specialization.
    ctor = re.search(r"^Fn1_int_int (\w*make_fn1\w*)\([^;]*\)\s*\{", c, re.M)
    assert ctor, "no make_fn1 constructor definition in the bundle"
    start = ctor.start()
    body = c[start:c.index("\n}", start)]
    assert "malloc" not in body
    assert "pengu_alloc" not in body
    assert "pengu_list_new" not in body
