"""`std.littera` — end to end.

Three levels: the module's own embedded `test` blocks, a realistic hex parser
built on `digit_value`, and the emitted symbols (`char_*`, monomorphized by the
`enchanting char:` block and inherited by every alias-free use of the type).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

#: ``tests/stdlib/littera/test_end_to_end.py`` -> `littera` -> `stdlib` ->
#: `tests` -> the checkout.
ROOT = Path(__file__).resolve().parents[3]


def test_module_self_tests_pass():
    """``pengu test --entry std/littera.pengu``: all embedded blocks pass."""
    res = subprocess.run(
        [sys.executable, str(ROOT / "pengu_project.py"), "test",
         "--entry", str(ROOT / "std" / "littera.pengu")],
        capture_output=True, text=True, timeout=300,
        cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert res.returncode == 0, (
        f"module self-tests failed:\n--- stdout ---\n{res.stdout}\n"
        f"--- stderr ---\n{res.stderr}"
    )
    assert "All 26 test(s) passed." in res.stdout, res.stdout


def test_hex_parser(compile_and_run):
    """A hex parser written on `digit_value`, over a string's bytes.

    `for ch in s` yields a `string` (one character), not a `char`, so the parser
    walks `scrolls.bytes` and casts each `int` to `char` before asking for the
    digit value.
    """
    out = compile_and_run("""
import std.spark
import std.scrolls
import std.littera

weave parse_hex with s as string into int:
    var acc as int is 0
    let bs as list of int is calling scrolls.bytes with s
    for x in bs:
        var ch as char is (x to char)
        var d as int is calling ch.digit_value
        if d < 0:
            return 0 - 1
        set acc is acc * 16 + d
    return acc

weave main into int:
    var a as string is "ff"
    var b as string is "1a"
    var c as string is "FF"
    var d as string is "7"
    var bad as string is "zz"
    calling spark.println with "{calling parse_hex with a}"
    calling spark.println with "{calling parse_hex with b}"
    calling spark.println with "{calling parse_hex with c}"
    calling spark.println with "{calling parse_hex with d}"
    calling spark.println with "{calling parse_hex with bad}"
    return 0
""")
    assert "255" in out, out
    assert "26" in out, out
    assert out.count("255") == 2, out
    assert "-1" in out, out


def test_char_symbols_are_emitted(tmp_path):
    """Each method becomes one plain C `char_*` function."""
    source = tmp_path / "littera_symbols.pengu"
    source.write_text(
        "import std.littera\n"
        "weave main into int:\n"
        "    var c as char is 'a'\n"
        "    let a is calling c.is_digit\n"
        "    let b is calling c.to_upper\n"
        "    let d is calling c.digit_value\n"
        "    let e is calling c.is_whitespace\n"
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
    for symbol in ("char_is_digit", "char_to_upper", "char_digit_value",
                   "char_is_whitespace"):
        assert re.search(rf"\b{re.escape(symbol)}\b", bundle), f"{symbol} missing"
    assert "pengu_is_digit" not in bundle, "symbols must not carry a pengu_ prefix"
    # The module is pure PenguScript: no libc ctype symbol may leak in.
    assert "isdigit" not in bundle, "littera must not call <ctype.h>"
    assert "toupper" not in bundle, "littera must not call <ctype.h>"
