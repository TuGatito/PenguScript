"""``std.lingua`` vs Python's ``str`` code points.

CPython is the oracle: for 999 random Unicode strings (plus the empty one) the
PenguScript decoder must produce exactly ``[ord(c) for c in s]`` and the same
UTF-16 length as ``len(s.encode("utf-16-le")) // 2``. The strings deliberately
include combining marks, emoji, CJK and mixed scripts.
"""
from __future__ import annotations

import random

import pytest

pytestmark = pytest.mark.slow

_PROGRAM = r'''
import std.archivum
import std.spark
import std.lingua

weave main into int:
    var opt as maybe list of string is calling archivum.read_lines with "@@CASES@@"
    if lines as list of string is opt:
        var index as int is 0
        while index < lines.len:
            var s as string is lines at index
            var decoded as result of list of Codepoint to LinguaError is calling lingua.decode with s
            if not decoded.is_ok:
                calling spark.println with "FAIL decode {index}"
                return 1
            var cps as list of Codepoint is decoded.value
            var parts as string is "{index}:"
            var j as int is 0
            while j < cps.len:
                set parts is "{parts}{(cps at j) to u32} "
                set j is j + 1
            set parts is "{parts}|{(calling lingua.utf16_length with s)}"
            calling spark.println with parts
            banish parts
            banish decoded
            set index is index + 1
        calling spark.println with "OK"
    else:
        calling spark.println with "FAIL read"
        return 1
    return 0
'''


def _random_string(rng: random.Random) -> str:
    pools = [
        (0x20, 0x7E),      # printable ASCII
        (0xA0, 0x17F),     # Latin-1 + Latin Extended-A
        (0x300, 0x36F),    # combining marks
        (0x400, 0x4FF),    # Cyrillic
        (0x5D0, 0x5EA),    # Hebrew
        (0x620, 0x64A),    # Arabic
        (0x3040, 0x30FF),  # kana
        (0x4E00, 0x9FFF),  # CJK
        (0x1F300, 0x1FAFF),  # emoji
        (0x1D400, 0x1D7FF),  # mathematical alphanumerics
    ]
    length = rng.randrange(0, 24)
    out = []
    for _ in range(length):
        lo, hi = rng.choice(pools)
        out.append(chr(rng.randint(lo, hi)))
    return "".join(out)


def test_lingua_decode_matches_python(tmp_path, compile_and_run):
    rng = random.Random(2026110)
    cases = [_random_string(rng) for _ in range(999)]
    cases.append("")
    path = tmp_path / "cases.txt"
    # The last case is the empty string: joining (without an extra trailing
    # newline) writes exactly one empty final line for it.
    path.write_text("\n".join(cases), encoding="utf-8")

    source = _PROGRAM.replace("@@CASES@@", str(path))
    output = compile_and_run(source)
    lines = [line for line in output.splitlines() if line and not line.startswith("FAIL")]
    assert "OK" in output, output[-2000:]

    results = {}
    for line in lines:
        if line == "OK":
            continue
        head, tail = line.split("|", 1)
        index_s, *cps = head.split(":")
        results[int(index_s)] = ([int(cp) for cp in cps[0].split()] if cps[0] else [],
                                int(tail))

    assert len(results) == len(cases), (len(results), len(cases))
    for index, case in enumerate(cases):
        got_cps, got_utf16 = results[index]
        assert got_cps == [ord(ch) for ch in case], f"codepoints differ at {index}: {case!r}"
        assert got_utf16 == len(case.encode("utf-16-le")) // 2, (
            f"utf16 length differs at {index}: {case!r}"
        )
