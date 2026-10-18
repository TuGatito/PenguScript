"""``std.regulus`` vs Python's ``re.search`` for the supported subset.

Every generated pattern stays inside tiny-regex-c's grammar: no groups, no
alternation, no ``{n,m}``, no lookaround. For that subset ``is_match`` and
``re.search`` agree, so CPython can act as the oracle over 200 pairs.
"""
from __future__ import annotations

import random
import re

import pytest

pytestmark = pytest.mark.slow

_PROGRAM = r'''
import std.archivum
import std.scrolls
import std.spark
import std.regulus

weave main into int:
    var opt as maybe list of string is calling archivum.read_lines with "@@CASES@@"
    if lines as list of string is opt:
        var index as int is 0
        while index < lines.len:
            var line as string is lines at index
            var fields as list of string is calling scrolls.split with line, "\t"
            if fields.len != 2:
                calling spark.println with "{index}:ERROR"
            else:
                var pattern as string is fields at 0
                var text as string is fields at 1
                var compiled as result of Regex to RegexError is calling Regex.compile with pattern
                if not compiled.is_ok:
                    calling spark.println with "{index}:ERROR"
                else:
                    var rx as Regex is compiled.value
                    var matched as bool is calling rx.is_match with text
                    if matched:
                        calling spark.println with "{index}:true"
                    else:
                        calling spark.println with "{index}:false"
                    banish compiled
            var f as int is 0
            while f < fields.len:
                banish (fields at f)
                set f is f + 1
            banish fields
            set index is index + 1
        calling spark.println with "OK"
    else:
        calling spark.println with "FAIL read"
        return 1
    return 0
'''

_FIXED = [
    "", "[0-9]+", "[a-z]+", "[A-Z]+", "[a-z0-9]+", "^abc", "abc$", "^abc$",
    "a.c", "a*b", "a+b", "ab?c", "abc", r"\d+", r"\w+", r"\s+", r"\.", "a$",
    "^a", ".", "x*", "[abc]+", "[a-z][0-9]", r"a\.b", r"\d\d", "[0-9]$",
    "^[a-z]+$", "ab*c", "[ _-]+",
]

_ATOMS = ["a", "b", "c", "x", "0", "1", "_", " ", r"\d", r"\w", r"\s", ".",
          "[a-z]", "[A-Z]", "[0-9]", "[abc]", r"\.", r"\-"]


def _random_pattern(rng: random.Random) -> str:
    parts = []
    if rng.random() < 0.3:
        parts.append("^")
    for _ in range(rng.randrange(1, 5)):
        atom = rng.choice(_ATOMS)
        quantifier = rng.choice(["", "", "", "*", "+", "?"])
        parts.append(atom + quantifier)
    if rng.random() < 0.3:
        parts.append("$")
    return "".join(parts)


def _random_text(rng: random.Random) -> str:
    alphabet = "abcxyzABC019 _-."
    return "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 21)))


def test_regulus_is_match_matches_python_search(tmp_path, compile_and_run):
    rng = random.Random(2026111)
    patterns = list(_FIXED)
    while len(patterns) < 200:
        patterns.append(_random_pattern(rng))
    patterns = patterns[:200]

    cases = []
    for pattern in patterns:
        text = _random_text(rng)
        cases.append((pattern, text))

    path = tmp_path / "cases.tsv"
    path.write_text("\n".join(f"{p}\t{t}" for p, t in cases), encoding="utf-8")
    source = _PROGRAM.replace("@@CASES@@", str(path))
    output = compile_and_run(source)
    assert "OK" in output, output[-2000:]

    results = {}
    for line in output.splitlines():
        if line == "OK" or not line:
            continue
        index_s, value = line.split(":", 1)
        results[int(index_s)] = value

    assert len(results) == len(cases), (len(results), len(cases))
    for index, (pattern, text) in enumerate(cases):
        expected = re.search(pattern, text) is not None
        got = results[index]
        assert got != "ERROR", f"pattern failed to compile at {index}: {pattern!r}"
        assert (got == "true") is expected, (
            f"mismatch at {index}: pattern={pattern!r} text={text!r} "
            f"python={expected} ours={got}"
        )
