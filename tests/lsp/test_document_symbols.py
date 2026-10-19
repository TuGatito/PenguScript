"""``textDocument/documentSymbol`` must always return a valid outline.

The VS Code client validates every ``DocumentSymbol`` it receives:

    selectionRange must be contained in fullRange

and rejects the *whole* reply when one symbol violates it.  The checker's global
scope also holds the declarations of every imported module (with line numbers
from *their* files), so the outline used to mix hundreds of std declarations
into a 20-line buffer and produce ranges past the end of the document.  These
tests pin both halves of the fix: only the document's own declarations are
listed, and every range/selection range is inside the buffer and inside its
parent.
"""
from __future__ import annotations

from lsprotocol.types import (
    DocumentSymbolParams,
    TextDocumentIdentifier,
)

from pengu_lsp import server as lsp_server
from pengu_parser.pengu_symbols import Symbol
from pengu_parser.pengu_types import INT_TYPE

SOURCE = """\
import std.spark
import std.loom

## Adds two integers.
weave add with a as int, b as int into int:
    return a + b

rune Pt:
    x as int
    y as int

omen Kind:
    A
    B with value as int

weave main into int:
    var p as Pt is with x is 1, y is 2
    calling spark.println with "{calling add with p.x, p.y}"
    return 0
"""


def _symbols(lsp):
    lsp.open(SOURCE)
    result = lsp_server.document_symbols(
        DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
        )
    )
    assert result is not None
    return result


def _assert_valid(symbol, lines, parent=None):
    """Raises AssertionError when a DocumentSymbol range is invalid."""
    full = symbol.range
    selection = symbol.selection_range
    assert 0 <= full.start.line < len(lines), (symbol.name, full)
    assert 0 <= full.end.line < len(lines), (symbol.name, full)
    assert 0 <= selection.start.line < len(lines), (symbol.name, selection)
    assert 0 <= selection.end.line < len(lines), (symbol.name, selection)
    assert (full.start.line, full.start.character) <= (
        selection.start.line,
        selection.start.character,
    ), (symbol.name, full, selection)
    assert (selection.end.line, selection.end.character) <= (
        full.end.line,
        full.end.character,
    ), (symbol.name, full, selection)
    if parent is not None:
        assert (parent.start.line, parent.start.character) <= (
            full.start.line,
            full.start.character,
        ), (symbol.name, parent, full)
        assert (full.end.line, full.end.character) <= (
            parent.end.line,
            parent.end.character,
        ), (symbol.name, parent, full)
    for child in symbol.children or []:
        _assert_valid(child, lines, full)


def test_outline_lists_the_documents_own_declarations(lsp):
    names = [symbol.name for symbol in _symbols(lsp)]
    for expected in ("spark", "loom", "add", "Pt", "Kind", "main"):
        assert expected in names, names
    # An imported module's members are not declarations of *this* file.  Before
    # the fix the outline contained every std function and type, which is also
    # what made the range validation fail.
    assert "println" not in names, names
    assert "Vec2" not in names, names
    assert len(names) < 40, names


def test_every_symbol_and_child_has_a_contained_range(lsp):
    lines = SOURCE.splitlines()
    for symbol in _symbols(lsp):
        _assert_valid(symbol, lines)


def test_rune_fields_and_omen_variants_are_children(lsp):
    by_name = {symbol.name: symbol for symbol in _symbols(lsp)}
    assert {child.name for child in by_name["Pt"].children} == {"x", "y"}
    assert {child.name for child in by_name["Kind"].children} == {"A", "B"}


def test_a_stale_symbol_outside_the_buffer_is_skipped(lsp):
    """A symbol table may describe the previous text for a moment."""
    symbols = _symbols(lsp)
    table = lsp_server.server._symbols[lsp.uri]
    table.global_scope.define(
        Symbol(
            name="ghost",
            type=INT_TYPE,
            kind="const",
            line=9999,
            column=9999,
            file_path=lsp.path,
        )
    )
    refreshed = lsp_server.document_symbols(
        DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
        )
    )
    assert refreshed is not None
    names = [symbol.name for symbol in refreshed]
    assert "ghost" not in names, names
    lines = SOURCE.splitlines()
    for symbol in refreshed:
        _assert_valid(symbol, lines)


def test_a_column_past_the_end_of_the_line_is_clamped(lsp):
    _symbols(lsp)
    table = lsp_server.server._symbols[lsp.uri]
    table.global_scope.define(
        Symbol(
            name="far_column",
            type=INT_TYPE,
            kind="const",
            line=5,
            column=500,
            file_path=lsp.path,
        )
    )
    refreshed = lsp_server.document_symbols(
        DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
        )
    )
    assert refreshed is not None
    lines = SOURCE.splitlines()
    for symbol in refreshed:
        _assert_valid(symbol, lines)


def test_crlf_sources_keep_valid_ranges(lsp, tmp_path):
    crlf = SOURCE.replace("\n", "\r\n")
    lsp.path.write_text(crlf, encoding="utf-8", newline="")
    lsp._validate(crlf)
    result = lsp_server.document_symbols(
        DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
        )
    )
    assert result is not None
    lines = crlf.splitlines()
    for symbol in result:
        _assert_valid(symbol, lines)


def test_no_symbols_returns_none_instead_of_an_empty_broken_reply(lsp):
    lsp.path.write_text("", encoding="utf-8")
    lsp._validate("")
    result = lsp_server.document_symbols(
        DocumentSymbolParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
        )
    )
    assert result is None
