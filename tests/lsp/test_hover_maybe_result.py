"""Hover for the optional/result vocabulary.

`maybe`, `result`, `some`, `maybe none`, `ok_of` and `err_of` are the words a
reader lands on first, but they are not ordinary symbols in the document scope.
These tests pin the contextual documentation and, just as importantly, that a
variable literally named `result` still hovers as a variable.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import Position

pytestmark = pytest.mark.smoke

SOURCE = '''weave make into maybe string:
    return some "x"

weave parse into result of int to string:
    return calling ok_of with 1

weave fail into result of int to string:
    return calling err_of with "e"

weave empty into maybe string:
    return maybe none

weave main into int:
    var m as maybe string is calling make
    var r as result of int to string is calling parse
    var result as int is 1
    return result
'''


def _position(text: str, needle: str, occurrence: int = 1, offset: int = 0) -> Position:
    seen = 0
    for line_no, line in enumerate(text.splitlines()):
        start = 0
        while True:
            found = line.find(needle, start)
            if found < 0:
                break
            seen += 1
            if seen == occurrence:
                return Position(line=line_no, character=found + offset)
            start = found + len(needle)
    raise AssertionError(f"{needle!r} (occurrence {occurrence}) not found")


def _hover(lsp, needle: str, occurrence: int = 1, offset: int = 0):
    from pengu_lsp.hover import get_hover

    return get_hover(
        lsp.uri,
        _position(SOURCE, needle, occurrence=occurrence, offset=offset),
        lsp.symbols,
        SOURCE,
    )


def test_maybe_is_documented(lsp):
    lsp.open(SOURCE)
    hover = _hover(lsp, "maybe")
    assert hover is not None
    assert "maybe T" in hover.contents.value


def test_result_type_is_documented(lsp):
    lsp.open(SOURCE)
    hover = _hover(lsp, "result")
    assert hover is not None
    assert "result of T to E" in hover.contents.value
    assert "ok_of" in hover.contents.value and "err_of" in hover.contents.value


def test_some_is_documented(lsp):
    lsp.open(SOURCE)
    hover = _hover(lsp, "some")
    assert hover is not None
    assert "some x" in hover.contents.value


def test_maybe_none_is_documented(lsp):
    lsp.open(SOURCE)
    hover = _hover(lsp, "maybe none")
    assert hover is not None
    assert "maybe none" in hover.contents.value


def test_ok_of_and_err_of_are_documented(lsp):
    lsp.open(SOURCE)
    ok = _hover(lsp, "ok_of")
    err = _hover(lsp, "err_of")
    assert ok is not None and "calling ok_of" in ok.contents.value
    assert err is not None and "calling err_of" in err.contents.value


def test_a_variable_named_result_still_hovers_as_a_variable(lsp):
    lsp.open(SOURCE)
    hover = _hover(lsp, "result", occurrence=4)
    assert hover is not None
    assert "result of T to E" not in hover.contents.value
    assert "result as int" in hover.contents.value
