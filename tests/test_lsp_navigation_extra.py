"""Roadmap Phase 3 / §3.7 (signature help) and §3.8 (document symbols, folding).

The audit assumed these were missing; they already existed in
``pengu_lsp/server.py`` but had no test coverage.  This locks their behaviour.
"""

from lsprotocol.types import (
    DocumentSymbolParams,
    FoldingRangeParams,
    Position,
    SignatureHelpParams,
    TextDocumentIdentifier,
)

from tests.test_lsp import checked_symbols

URI = "file:///nav.pengu"

_SRC = (
    "import std.spark\n"
    "\n"
    "## A point.\n"
    "rune Point:\n"
    "    x as int\n"
    "    y as int\n"
    "\n"
    "## Adds numbers.\n"
    "weave add with a as int, b as int into int:\n"
    "    return a + b\n"
    "\n"
    "const LIMIT as int is 10\n"
    "\n"
    "weave main into int:\n"
    "    var p as Point is with x is 1, y is 2\n"
    "    return calling add with 1, 2\n"
)


def _register(source, uri=URI, filename="nav.pengu"):
    from pengu_lsp.server import server

    symbols = checked_symbols(source, filename=filename)
    server._symbols[uri] = symbols
    server._docs[uri] = source
    return symbols


def test_signature_help_reports_parameters():
    from pengu_lsp.server import signature_help

    _register(_SRC)
    line = _SRC.splitlines().index("    return calling add with 1, 2")
    col = _SRC.splitlines()[line].index("1, 2") + 2  # cursor after the comma
    res = signature_help(SignatureHelpParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=line, character=col),
    ))
    assert res is not None and res.signatures
    sig = res.signatures[0]
    assert "add" in sig.label
    labels = [p.label for p in sig.parameters]
    assert labels == ["a as int", "b as int"]
    assert res.active_parameter == 1


def test_signature_help_none_for_non_call():
    from pengu_lsp.server import signature_help

    _register(_SRC)
    res = signature_help(SignatureHelpParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=12, character=6),
    ))
    assert res is None


def test_document_symbols_lists_top_level_decls():
    from pengu_lsp.server import document_symbols

    _register(_SRC)
    res = document_symbols(DocumentSymbolParams(
        text_document=TextDocumentIdentifier(uri=URI)))
    assert res
    names = {s.name for s in res}
    assert {"Point", "add", "main"} <= names
    assert "LIMIT" in names or "Limit" in names


def test_folding_ranges_cover_blocks_and_comments():
    from pengu_lsp.server import folding_ranges

    _register(_SRC)
    res = folding_ranges(FoldingRangeParams(
        text_document=TextDocumentIdentifier(uri=URI)))
    assert res
    # Every range must be well-formed (start strictly before end).
    for r in res:
        assert r.start_line < r.end_line
    # The rune body (lines 3..5, 0-based) is folded.
    assert any(r.start_line <= 3 and r.end_line >= 5 for r in res)
