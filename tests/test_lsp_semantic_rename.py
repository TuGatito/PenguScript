"""Roadmap Phase 3 / §3.1 — semantic rename & document highlight.

rename/highlight used to run `\\bword\\b` over the raw text, rewriting homonyms
in other scopes, member accesses, comments and string literals.  They now resolve
the symbol at the cursor and scan real lexer tokens.
"""

from lsprotocol.types import (
    DocumentHighlightParams,
    Position,
    RenameParams,
    TextDocumentIdentifier,
)

from tests.test_lsp import checked_symbols

URI = "file:///sem.pengu"

_TWO_FUNCS = (
    "weave f with x as int into int:\n"
    "    var total as int is x + x\n"
    "    return total\n"
    "\n"
    "weave g with x as int into int:\n"
    "    var other as int is x * 2\n"
    "    return other\n"
)


def _register(source, uri=URI, filename="sem.pengu"):
    from pengu_lsp.server import server

    symbols = checked_symbols(source, filename=filename)
    server._symbols[uri] = symbols
    server._docs[uri] = source
    return symbols


def _rename_edits(source, line, character, new_name, uri=URI):
    from pengu_lsp.server import rename_symbol

    _register(source, uri=uri)
    params = RenameParams(
        text_document=TextDocumentIdentifier(uri=uri),
        position=Position(line=line, character=character),
        new_name=new_name,
    )
    result = rename_symbol(params)
    assert result is not None and result.changes
    return result.changes[uri]




def test_rename_local_does_not_touch_other_scope():
    # cursor on the `x` parameter of f (line 0, col 13)
    edits = _rename_edits(_TWO_FUNCS, 0, 13, "value")
    # f's parameter and its two uses inside the body, and nothing else.
    assert {(e.range.start.line, e.range.start.character) for e in edits} == {
        (0, 13), (1, 24), (1, 28),
    }
    assert all(e.new_text == "value" for e in edits)


def test_rename_skips_string_literals_but_updates_interpolation():
    src = (
        "weave f with x as int into int:\n"
        '    var s as string is "literal x here"\n'
        '    var t as string is "value={x}"\n'
        "    return x\n"
    )
    edits = _rename_edits(src, 0, 13, "count")
    assert len(edits) == 3  # param decl, interpolation, return
    touched_lines = {e.range.start.line for e in edits}
    assert touched_lines == {0, 2, 3}
    # The plain literal on line 1 must not be rewritten.
    assert 1 not in touched_lines


def test_rename_skips_comments_and_member_access():
    src = (
        "## x is the parameter name; do not touch x here\n"
        "rune Box:\n"
        "    x as int\n"
        "\n"
        "weave f with x as int into int:\n"
        "    var b as Box is with x is 5\n"
        "    return x + b.x\n"
    )
    edits = _rename_edits(src, 4, 13, "n")
    lines = {e.range.start.line for e in edits}
    assert 0 not in lines  # comment untouched
    # `b.x` (member access) is never rewritten.
    rendered = []
    for e in edits:
        rendered.append(e.range.start.line)
    assert 6 in rendered or 5 in rendered
    for e in edits:
        assert e.range.start.line != 6 or e.range.start.character == 11  # `x` in `x + b.x`


def test_rename_invalid_identifier_rejected():
    from pengu_lsp.server import rename_symbol

    _register(_TWO_FUNCS)
    params = RenameParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=0, character=13),
        new_name="not valid!",
    )
    assert rename_symbol(params) is None


def test_document_highlight_scope_aware():
    from pengu_lsp.server import document_highlight

    _register(_TWO_FUNCS)
    params = DocumentHighlightParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=0, character=13),
    )
    res = document_highlight(params)
    assert res
    assert {h.range.start.line for h in res} == {0, 1}


def test_document_highlight_ignores_strings_and_comments():
    from pengu_lsp.server import document_highlight

    src = (
        "## x in a comment\n"
        "weave f with x as int into int:\n"
        '    var s as string is "x x x"\n'
        "    return x\n"
    )
    _register(src)
    params = DocumentHighlightParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=1, character=13),
    )
    res = document_highlight(params)
    assert res
    assert {h.range.start.line for h in res} == {1, 3}


def test_references_skips_comments_and_string_literals():
    from lsprotocol.types import ReferenceContext, ReferenceParams
    from pengu_lsp.server import references

    src = (
        "## helper appears in this comment\n"
        "weave helper with n as int into int:\n"
        '    var s as string is "helper in a literal"\n'
        "    return n\n"
        "\n"
        "weave main into int:\n"
        "    return calling helper with 1\n"
    )
    _register(src)
    params = ReferenceParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=1, character=7),
        context=ReferenceContext(include_declaration=True),
    )
    res = references(params)
    assert res
    lines = {loc.range.start.line for loc in res}
    assert 0 not in lines  # comment
    assert 2 not in lines  # string literal
    assert {1, 6} <= lines


def test_references_local_symbol_stays_in_scope():
    from lsprotocol.types import ReferenceContext, ReferenceParams
    from pengu_lsp.server import references

    _register(_TWO_FUNCS)
    params = ReferenceParams(
        text_document=TextDocumentIdentifier(uri=URI),
        position=Position(line=0, character=13),
        context=ReferenceContext(include_declaration=True),
    )
    res = references(params)
    assert res
    assert {loc.range.start.line for loc in res} == {0, 1}
