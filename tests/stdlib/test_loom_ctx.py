"""``std.loom.*_ctx`` — pipeline functions with an explicit context.

The ``_ctx`` family is the no-closure alternative to ``map(xs, lambda ...)``:
the callback takes the borrowed context as its first parameter.  These tests
drive every one of the ten shipped functions through the real CLI, including
the empty-list edges, the truncating ``zip_with_ctx`` and the mutable rune
context of ``for_each_ctx``.  The original (context-free) loom surface is
checked too, so adding the family cannot silently change it.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]


def test_module_self_tests_pass():
    """``pengu test --entry std/loom.pengu``: the 156 embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "loom.pengu")],
        capture_output=True, text=True, timeout=900,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 156 test(s) passed." in res.stdout, res.stdout


_CTX_PROGRAM = """
import std.loom
import std.spark

rune Scaler:
    factor as int
    limit as int

rune Acc:
    total as int

weave scale with s as ref to Scaler, x as int into int:
    return s->factor * x

weave above with s as ref to Scaler, x as int into bool:
    return x > s->limit

weave fold_add with s as ref to Scaler, acc as int, x as int into int:
    return acc + x + s->factor

weave accumulate with a as ref to Acc, x as int into void:
    set a->total is a->total + x

weave pair_add with s as ref to Scaler, x as int, y as int into int:
    return x + y + s->factor

weave maybe_double with s as ref to Scaler, x as int into maybe int:
    if (x % 2) == 0:
        return some (x * s->factor)
    return maybe none

weave main into int:
    var s as Scaler is with factor is 2, limit is 3
    var xs as list of int is [1, 2, 3, 4]
    var mapped as list of int is calling loom.map_ctx with xs, (sigil of s), scale
    var filtered as list of int is calling loom.filter_ctx with xs, (sigil of s), above
    var folded as int is calling loom.fold_ctx with xs, 0, (sigil of s), fold_add
    var acc as Acc is with total is 0
    calling loom.for_each_ctx with xs, (sigil of acc), accumulate
    var ys as list of int is [10, 20]
    var zipped as list of int is calling loom.zip_with_ctx with xs, ys, (sigil of s), pair_add
    var first as maybe int is calling loom.find_first_ctx with xs, (sigil of s), above
    var any_above as bool is calling loom.any_ctx with xs, (sigil of s), above
    var all_above as bool is calling loom.all_ctx with xs, (sigil of s), above
    let (yes, no) is calling loom.partition_ctx with xs, (sigil of s), above
    var fm as list of int is calling loom.filter_map_ctx with xs, (sigil of s), maybe_double

    calling spark.println with "mapped={mapped at 0},{mapped at 1},{mapped at 2},{mapped at 3}"
    calling spark.println with "filtered={filtered at 0} len={calling filtered.len}"
    calling spark.println with "folded={folded} acc={acc.total}"
    calling spark.println with "zip={zipped at 0},{zipped at 1} len={calling zipped.len}"
    if v as int is first:
        calling spark.println with "first={v}"
    calling spark.println with "any={any_above} all={all_above}"
    calling spark.println with "part={yes at 0} yes_len={calling yes.len} no0={no at 0} no_len={calling no.len}"
    calling spark.println with "fm={fm at 0},{fm at 1} len={calling fm.len}"

    var empty as list of int is list of int
    var none_first as maybe int is calling loom.find_first_ctx with empty, (sigil of s), above
    var empty_any as bool is calling loom.any_ctx with empty, (sigil of s), above
    var empty_all as bool is calling loom.all_ctx with empty, (sigil of s), above
    if v2 as int is none_first:
        calling spark.println with "unreachable {v2}"
    else:
        calling spark.println with "empty first=none any={empty_any} all={empty_all}"

    banish mapped
    banish filtered
    banish zipped
    banish yes
    banish no
    banish fm
    banish xs
    banish ys
    banish empty
    return 0
"""


def test_every_ctx_function_runs_end_to_end(compile_and_run):
    out = compile_and_run(_CTX_PROGRAM)
    lines = [line for line in out.strip().splitlines() if line and not line.startswith(" ")]
    assert lines == [
        "mapped=2,4,6,8",
        "filtered=4 len=1",
        "folded=18 acc=10",
        "zip=13,24 len=2",
        "first=4",
        "any=true all=false",
        "part=4 yes_len=1 no0=1 no_len=3",
        "fm=4,8 len=2",
        "empty first=none any=false all=true",
    ], out


def test_the_original_loom_surface_still_works(compile_and_run):
    out = compile_and_run(
        """
import std.loom
import std.spark

weave add with a as int, b as int into int:
    return a + b

weave main into int:
    var xs as list of int is calling loom.range with 1, 6, 1
    var total as int is calling loom.sum with xs
    var zipped as list of int is calling loom.zip_with_op with xs, xs, add
    calling spark.println with "{total} {zipped at 0} {zipped at 4}"
    return 0
"""
    )
    assert out.strip().splitlines()[-1] == "15 2 10", out
