"""UTF-16 position conversions for the Language Server Protocol.

LSP positions are expressed in **UTF-16 code units**, while Python strings are
indexed by Unicode code points and the PenguScript lexer reports byte columns.
For ASCII all three agree, which is why the first LSP tests missed this.  A
single non-BMP character (an emoji, U+1F600) occupies two UTF-16 units but one
Python index, so every diagnostic/hover/rename range after it drifted by one.

The helpers here are deliberately pure and dependency-free so they can be used
from every feature module without importing the server (which would create a
cycle).  Keep the conversion at the protocol boundary:

* incoming request: UTF-16 -> code points before indexing Python text;
* outgoing response: code points -> UTF-16 after the feature has computed its
  ordinary string indices.
"""
from __future__ import annotations

from typing import Optional


def utf16_units(text: str) -> int:
    """Number of UTF-16 code units needed by ``text``."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def cp_to_utf16(line: str, cp_col: int) -> int:
    """Converts a 0-based code-point column to UTF-16 code units.

    ``cp_col`` is clamped to the line so a diagnostic at EOF (or a stale
    position from an editor) can never produce an out-of-range LSP value.
    """
    if not line:
        return 0
    col = max(0, min(int(cp_col), len(line)))
    return utf16_units(line[:col])


def utf16_to_cp(line: str, u16_col: int) -> int:
    """Converts an LSP UTF-16 column to a Python code-point index."""
    if not line:
        return 0
    target = max(0, int(u16_col))
    units = 0
    for idx, ch in enumerate(line):
        width = 2 if ord(ch) > 0xFFFF else 1
        if units + width > target:
            return idx
        units += width
        if units == target:
            return idx + 1
    return len(line)


def position_to_cp(text: str, line0: int, u16_col: int) -> int:
    """Converts an LSP ``(line, character)`` pair against a document."""
    lines = text.splitlines()
    if line0 < 0 or line0 >= len(lines):
        return 0
    return utf16_to_cp(lines[line0], u16_col)


def range_to_utf16(lines: list[str], line0: int, start_cp: int, end_cp: int) -> tuple[int, int]:
    """Converts a code-point column range on ``line0`` to UTF-16 units."""
    line = lines[line0] if 0 <= line0 < len(lines) else ""
    return cp_to_utf16(line, start_cp), cp_to_utf16(line, end_cp)


def span_to_utf16(source: str, line0: int, start_cp: int, end_cp: int) -> tuple[int, int]:
    """Convenience wrapper that splits ``source`` on demand."""
    return range_to_utf16(source.splitlines(), line0, start_cp, end_cp)


def symbol_end(start_cp: int, name: str) -> int:
    """End column of ``name`` in code points, starting at ``start_cp``."""
    return start_cp + utf16_units(name)
