"""``std.json`` vs Python's ``json`` module.

The oracle is CPython itself: every generated document is dumped with
``json.dumps(value, ensure_ascii=False, separators=(",", ":"))`` and the
PenguScript program must produce exactly that text, re-parse it, and produce it
again unchanged. 1000 documents (including floats, Unicode and control
characters) plus every scalar shape are covered.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_PROGRAM = r'''
import std.archivum
import std.json
import std.spark

weave eat_maybe_list with ml as maybe list of string into void:
    if l as list of string is ml:
        for e in l:
            banish e
    banish ml

weave compare_lines with cases as list of string, expected as list of string into int:
    var ok as int is 0
    var count as int is cases.len
    if expected.len < count:
        set count is expected.len
    var i as int is 0
    while i < count:
        let line is cases at i
        let want is expected at i
        if (line length) > 0:
            var pr as result of JsonValue to json.JsonError is calling json.parse with line
            if not pr.is_ok:
                calling spark.println with "FAIL parse at {i}: {pr.error.message}"
                set ok is 1
            else:
                var v as JsonValue is pr.value
                var got as string is calling json.stringify with v
                if got != want:
                    calling spark.println with "MISMATCH at {i}"
                    calling spark.println with "  ours: {got}"
                    calling spark.println with "  python: {want}"
                    set ok is 1
                var pr2 as result of JsonValue to json.JsonError is calling json.parse with got
                if not pr2.is_ok:
                    calling spark.println with "FAIL reparse at {i}: {pr2.error.message}"
                    set ok is 1
                else:
                    var v2 as JsonValue is pr2.value
                    var got2 as string is calling json.stringify with v2
                    if got2 != got:
                        calling spark.println with "FAIL unstable at {i}"
                        set ok is 1
                    banish got2
                banish pr2
                banish got
            banish pr
        set i is i + 1
    return ok

weave main into int:
    var cases_opt as maybe list of string is calling archivum.read_lines with "@@CASES@@"
    var expected_opt as maybe list of string is calling archivum.read_lines with "@@EXPECTED@@"
    var failures as int is 0
    if cases as list of string is cases_opt:
        if expected as list of string is expected_opt:
            set failures is calling compare_lines with cases, expected
        else:
            calling spark.println with "FAIL: cannot read expected"
            set failures is 1
    else:
        calling spark.println with "FAIL: cannot read cases"
        set failures is 1
    calling eat_maybe_list with cases_opt
    calling eat_maybe_list with expected_opt
    if failures == 0:
        calling spark.println with "OK json_python_compat"
    return failures
'''


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _tricky_float(rng: random.Random) -> float:
    fixed = [
        0.0, -0.0, 1.0, -1.0, 0.1, -0.1, 1.5, 3.141592653589793,
        1e10, 1e-7, 1e16, 1e20, 1e-5, 1e-300, 1e300,
        1.2345678901234567, 123456789012345.0, 2.2250738585072014e-308,
    ]
    if rng.random() < 0.6:
        return rng.choice(fixed)
    return rng.uniform(-1e12, 1e12)


def _random_value(rng: random.Random, depth: int = 0):
    if depth >= 4:
        choice = rng.randrange(4)
    else:
        choice = rng.randrange(7)
    if choice == 0:
        return None
    if choice == 1:
        return rng.choice([True, False])
    if choice == 2:
        return rng.randint(-(2**63), 2**63 - 1)
    if choice == 3:
        return _tricky_float(rng)
    if choice == 4:
        alphabet = "abc ñáéíóú 中文 😀 \\\" / \n\t\r\b\f\x00\x01"
        return "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 12)))
    if choice == 5:
        return [_random_value(rng, depth + 1) for _ in range(rng.randrange(0, 5))]
    return {
        "".join(rng.choice("abcñ中😀") for _ in range(rng.randrange(0, 5))):
        _random_value(rng, depth + 1)
        for _ in range(rng.randrange(0, 5))
    }


def test_json_matches_python_and_round_trips(compile_and_run, tmp_path: Path):
    rng = random.Random(20261017)
    values = [_random_value(rng) for _ in range(1000)]
    cases = [_dump(v) for v in values]
    expected = [_dump(json.loads(c)) for c in cases]

    cases_path = tmp_path / "cases.jsonl"
    expected_path = tmp_path / "expected.jsonl"
    cases_path.write_text("\n".join(cases), encoding="utf-8")
    expected_path.write_text("\n".join(expected), encoding="utf-8")

    source = _PROGRAM.replace("@@CASES@@", str(cases_path)).replace(
        "@@EXPECTED@@", str(expected_path))
    out = compile_and_run(source)
    assert "OK json_python_compat" in out, out
    assert "FAIL" not in out, out
    assert "MISMATCH" not in out, out


def test_parse_accepts_what_python_accepts(compile_and_run, tmp_path: Path):
    """A small corpus of valid documents whose canonical forms are stable."""
    documents = [
        "null", "true", "false", "0", "-0", "1", "-1", "1.0", "0.1",
        "1e10", "1e-7", "1e16", "1e20", "[]", "{}", "[1,2,3]",
        '{"a":1,"b":2}', '{"a":[1,{"b":null}]}', '"ñ😀"',
        '"a\\nb"', '"\\u0041"', '"\\uD83D\\uDE00"',
        '{"a":1,"a":2}',
    ]
    cases = [json.dumps(json.loads(d), ensure_ascii=False, separators=(",", ":")) for d in documents]
    cases_path = tmp_path / "valid.jsonl"
    expected_path = tmp_path / "valid_expected.jsonl"
    cases_path.write_text("\n".join(cases), encoding="utf-8")
    expected_path.write_text("\n".join(cases), encoding="utf-8")
    source = _PROGRAM.replace("@@CASES@@", str(cases_path)).replace(
        "@@EXPECTED@@", str(expected_path))
    out = compile_and_run(source)
    assert "OK json_python_compat" in out, out
    assert "FAIL" not in out, out
    assert "MISMATCH" not in out, out
