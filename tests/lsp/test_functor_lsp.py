"""LSP services for the ``std.functor`` namespace.

``functor.Fn1`` is a generic rune and ``make_fn1`` a generic weave, both
declared in a real ``std/`` module.  These tests pin the four requests an editor
uses on them: hover on the type, hover on the constructor (signature), go to
definition, and dot completion of the module's exported surface.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import (
    DefinitionParams,
    Position,
    TextDocumentIdentifier,
)

SOURCE = """\
import std.functor
import std.spark

rune Multiplier:
    factor as int

weave multiply with m as ref to Multiplier, x as int into int:
    return m->factor * x

weave main into int:
    var m as Multiplier is with factor is 3
    var f as functor.Fn1 of int, int is calling functor.make_fn1 with multiply, (sigil of m)
    calling spark.println with "{calling f.call with 5}"
    return 0
"""


def _position(text: str, needle: str, occurrence: int = 1, offset: int = 0) -> Position:
    """0-based ``Position`` on ``needle``'s ``offset``-th character."""
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


def test_hover_on_the_fn1_type_shows_the_type(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    pos = _position(SOURCE, "functor.Fn1 of int, int", offset=8)
    hover = get_hover(lsp.uri, pos, lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "Fn1" in value, value
    assert "functor" in value.lower() or "thick" in value.lower(), value


def test_hover_on_make_fn1_shows_the_signature(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    pos = _position(SOURCE, "functor.make_fn1", offset=8)
    hover = get_hover(lsp.uri, pos, lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "make_fn1" in value, value
    assert "fn_ptr" in value or "context" in value.lower() or "Fn1" in value, value


def test_go_to_definition_of_make_fn1_jumps_into_the_std_module(lsp, tmp_path):
    from pengu_lsp.server import definition

    lsp.open(SOURCE)
    pos = _position(SOURCE, "functor.make_fn1", offset=8)
    location = definition(
        DefinitionParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
            position=pos,
        )
    )
    assert location is not None
    assert "std" in location.uri and "functor.pengu" in location.uri, location.uri
    assert location.range.start.line >= 0


def test_completion_after_functor_dot_offers_the_public_surface(lsp):
    lsp.open(SOURCE)
    labels = lsp.complete_after("functor.")
    for expected in (
        "Fn0",
        "Fn1",
        "Fn2",
        "Fn3",
        "make_fn0",
        "make_fn1",
        "make_fn2",
        "make_fn3",
        "FUNCTOR_VERSION",
    ):
        assert expected in labels, (expected, labels)


def test_completion_after_functor_dot_does_not_offer_test_helpers(lsp):
    lsp.open(SOURCE)
    labels = lsp.complete_after("functor.")
    assert "_Multiplier" not in labels, labels
    assert "_Holder" not in labels, labels
