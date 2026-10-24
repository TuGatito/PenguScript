"""LSP positions are UTF-16 code units (B6).

Python indexes code points; the lexer reports columns in code points.  An emoji
(U+1F600) is one Python character but *two* UTF-16 code units, so without the
conversion every range after it was off by one.  These tests pin both
directions: incoming editor positions are decoded before indexing Python text,
and outgoing diagnostics/ranges are encoded after the feature computes them.
"""
from __future__ import annotations

from lsprotocol.types import Position

from pengu_lsp.hover import get_word_at_position
from pengu_lsp.positions import cp_to_utf16, utf16_to_cp, utf16_units
from pengu_lsp.server import diagnostics_from_errors
from pengu_parser.pengu_errors import ParseError


def test_utf16_units_counts_astral_chars_as_two():
    assert utf16_units("abc") == 3
    assert utf16_units("ñ") == 1
    assert utf16_units("日本語") == 3
    assert utf16_units("😀") == 2


def test_cp_and_utf16_columns_roundtrip():
    line = 'var s as string is "😀" + x'
    for cp_col in range(len(line) + 1):
        encoded = cp_to_utf16(line, cp_col)
        assert utf16_to_cp(line, encoded) == cp_col


def test_incoming_position_after_emoji_finds_identifier():
    line = '    x 😀 value'
    line0 = 1
    text = f"weave main into int:\n{line}\n    return 0\n"
    cp = line.index("value")
    u16 = cp_to_utf16(line, cp)
    word = get_word_at_position(text, Position(line=line0, character=u16))
    assert word == "value"


def test_diagnostics_range_is_utf16_after_emoji():
    line = '    var s as string is "😀" bad_token'
    source = "weave main into int:\n" + line + "\n"
    cp_col = line.index("bad_token") + 1  # ParseError columns are 1-based
    err = ParseError("bad token", line=2, column=cp_col)
    diags = diagnostics_from_errors([err], source)
    assert len(diags) == 1
    start = diags[0].range.start
    assert start.line == 1
    expected = cp_to_utf16(line, cp_col - 1)
    assert start.character == expected
    # The emoji contributes two units, so the raw code-point column would have
    # been wrong by exactly one.
    assert expected == cp_col - 1 + 1
