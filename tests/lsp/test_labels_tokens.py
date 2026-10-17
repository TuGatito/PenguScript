"""Semantic tokens and document highlight for loop labels.

A loop label (``outer: for line in lines:``) and the label of a
``break outer`` / ``continue outer`` are compiler-defined jump targets, not
module symbols, so the lexer reports them as plain ``NAME`` tokens and the
symbol-based ``documentHighlight`` scan would treat them as an unresolved name.
These tests pin the two services that now resolve them from the parsed tree:

* semantic tokens type the declaration and every labeled jump as the legend's
  ``label`` token type, and leave every other token unchanged;
* document highlight returns the declaration plus the jumps enclosed by *that*
  loop — never a same-named label in another function.

Everything else keeps its previous behaviour: bare ``break`` / ``continue``
contribute no label token, a non-label position falls through to the ordinary
symbol highlighting, and a buffer that does not lex or parse yields nothing
instead of raising.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import (
    DocumentHighlightKind,
    DocumentHighlightParams,
    Position,
    SemanticTokensParams,
    TextDocumentIdentifier,
)

pytestmark = pytest.mark.smoke

#: Two functions, each with a label called ``outer`` (labels are unique *per
#: function*, so these are two different labels).  The first ``outer`` loop has
#: both a ``continue outer`` and a ``break outer``; the nested ``inner`` loop
#: proves the highlight stops at the loop that owns the label.
SOURCE = '''weave scan with lines as list of string into int:
    var hits as int is 0
    outer: for line in lines:
        inner: for ch in line:
            if ch == ";":
                continue outer
            if ch == "}":
                break outer
            if ch == "?":
                break inner
            set hits is hits + 1
    return hits

weave other with xs as list of int into int:
    outer: while true:
        break outer
    return 0
'''

#: A program with bare ``break`` / ``continue`` only: no label token at all.
BARE = '''weave f into int:
    while true:
        break
    return 0
'''

#: The lexer rejects the unterminated string, so the whole buffer yields nothing.
BROKEN_LEX = '''weave f into int:
    var x as string is "oops
    return 0
'''

#: Lexes fine but does not parse: the semantic-token handler must keep the
#: lexical tokens it always returned, only without any label classification.
PARSE_ONLY_BROKEN = "weave f into int:\n    outer: for x in :\n"

#: The LSP standard token types, in the order the legend has always sent them.
#: ``label`` is appended after these, so their indices must not move.
_STANDARD_TOKEN_TYPES = [
    "namespace", "type", "class", "enum", "interface", "struct",
    "typeParameter", "parameter", "variable", "property", "enumMember",
    "event", "function", "method", "macro", "keyword", "modifier",
    "comment", "string", "number", "regexp", "operator", "decorator",
]

#: ``(line, character, length)`` of every label token in ``SOURCE``, in LSP
#: (sorted) order: three declarations and four labeled jumps.
_LABEL_SPANS = [
    (2, 4, 5), (3, 8, 5), (5, 25, 5), (7, 22, 5),
    (9, 22, 5), (14, 4, 5), (15, 14, 5),
]

#: The label token text at each ``_LABEL_SPANS`` entry.
_LABEL_NAMES = ["outer", "inner", "outer", "outer", "inner", "outer", "outer"]


def _legend():
    """The SemanticTokensLegend the server registered for full tokens."""
    from pengu_lsp import server as lsp_server

    return lsp_server.server.protocol.fm.feature_options[
        "textDocument/semanticTokens/full"
    ]


def _decode(data):
    """Decodes LSP delta-encoded ``data`` into ``(line, char, length, type, mods)``."""
    assert len(data) % 5 == 0, data
    tokens = []
    line = 0
    char = 0
    for index in range(0, len(data), 5):
        delta_line, delta_char, length, type_index, modifiers = data[index:index + 5]
        line += delta_line
        char = delta_char if delta_line else char + delta_char
        tokens.append((line, char, length, type_index, modifiers))
    return tokens


def _semantic_tokens(lsp):
    """Runs the server's full semantic-token handler and decodes the result."""
    from pengu_lsp import server as lsp_server

    params = SemanticTokensParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri))
    result = lsp_server.semantic_tokens_full(params)
    assert result is not None
    return _decode(result.data)


def _label_tokens(tokens):
    """The subset of decoded ``tokens`` whose type is the legend's ``label``."""
    label_index = _legend().token_types.index("label")
    return [token for token in tokens if token[3] == label_index]


def _position(text, needle, occurrence=1, offset=1):
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


def _highlights(lsp, position):
    """Runs the server's documentHighlight handler at ``position``."""
    from pengu_lsp import server as lsp_server

    params = DocumentHighlightParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=position,
    )
    return lsp_server.document_highlight(params)


def _spans(highlights):
    """``(line, start, end)`` of each highlight, in the order returned."""
    return [(h.range.start.line, h.range.start.character, h.range.end.character)
            for h in highlights]


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------

def test_legend_registers_the_label_token_type():
    """``label`` is in the legend, appended so no existing index shifts."""
    from lsprotocol.types import SemanticTokensLegend
    from pengu_lsp import server as lsp_server

    legend = _legend()
    assert isinstance(legend, SemanticTokensLegend)
    assert legend.token_types == _STANDARD_TOKEN_TYPES + ["label"]
    assert lsp_server._TOKEN_TYPE_INDEX["label"] == len(_STANDARD_TOKEN_TYPES)
    assert lsp_server._TOKEN_TYPE_INDEX["variable"] == 8
    assert lsp_server._TOKEN_TYPE_INDEX["keyword"] == 15


# ---------------------------------------------------------------------------
# Semantic tokens
# ---------------------------------------------------------------------------

def test_semantic_tokens_type_the_declaration_and_every_jump(lsp):
    """Declaration and jumps carry ``label``, at the exact position and length."""
    lsp.open(SOURCE)
    labelled = _label_tokens(_semantic_tokens(lsp))

    assert len(labelled) == len(_LABEL_SPANS) == 7
    assert list(zip([t[0] for t in labelled],
                    [t[1] for t in labelled],
                    [t[2] for t in labelled])) == _LABEL_SPANS

    lines = SOURCE.splitlines()
    for (line, char, length), name in zip(_LABEL_SPANS, _LABEL_NAMES):
        assert lines[line][char:char + length] == name
        assert length == len(name)

    # A label declares no value, so no symbol-derived modifier leaks onto it.
    assert [token[4] for token in labelled] == [0] * len(_LABEL_SPANS)


def test_semantic_tokens_leave_the_other_token_types_unchanged(lsp):
    """Neighbouring keywords, names and numbers keep their old classification."""
    lsp.open(SOURCE)
    types = _legend().token_types
    by_position = {(line, char): (length, type_index)
                   for line, char, length, type_index, _mods
                   in _semantic_tokens(lsp)}

    # `for` on the labeled loop header, `continue` of a labeled jump, `hits`.
    assert by_position[(2, 11)] == (3, types.index("keyword"))
    assert by_position[(5, 16)] == (8, types.index("keyword"))
    assert by_position[(1, 8)] == (4, types.index("variable"))
    assert by_position[(1, 23)] == (1, types.index("number"))


def test_bare_break_and_continue_produce_no_label_token(lsp):
    """A bare jump adds no token; the keyword itself stays a keyword."""
    lsp.open(BARE)
    assert _label_tokens(_semantic_tokens(lsp)) == []

    by_position = {(line, char): (length, type_index)
                   for line, char, length, type_index, _mods
                   in _semantic_tokens(lsp)}
    assert by_position[(2, 8)] == (5, _legend().token_types.index("keyword"))


# ---------------------------------------------------------------------------
# Document highlight
# ---------------------------------------------------------------------------

def test_highlight_from_the_declaration_returns_declaration_and_jumps(lsp):
    """The label's whole extent: its declaration plus both of its jumps."""
    lsp.open(SOURCE)
    highlights = _highlights(lsp, _position(SOURCE, "outer", occurrence=1))

    assert highlights is not None
    assert _spans(highlights) == [(2, 4, 9), (5, 25, 30), (7, 22, 27)]
    # A label is never written at runtime; jumps only read it.
    assert {h.kind for h in highlights} == {DocumentHighlightKind.Read}


def test_highlight_from_a_jump_returns_the_same_set(lsp):
    """Highlighting ``continue outer`` or ``break outer`` finds the whole label."""
    lsp.open(SOURCE)
    expected = [(2, 4, 9), (5, 25, 30), (7, 22, 27)]
    # Occurrences 2 and 3 of `outer` are `continue outer` and `break outer`.
    for occurrence in (2, 3):
        highlights = _highlights(lsp, _position(SOURCE, "outer", occurrence=occurrence))
        assert highlights is not None, occurrence
        assert _spans(highlights) == expected, occurrence
        assert {h.kind for h in highlights} == {DocumentHighlightKind.Read}


def test_highlight_of_a_nested_label_does_not_include_outer_jumps(lsp):
    """The label is scoped to its own loop; enclosing jumps are not its own."""
    lsp.open(SOURCE)
    highlights = _highlights(lsp, _position(SOURCE, "inner", occurrence=1))

    assert highlights is not None
    assert _spans(highlights) == [(3, 8, 13), (9, 22, 27)]


def test_highlight_excludes_a_homonym_label_in_another_function(lsp):
    """Labels are function-local: the second function's ``outer`` is separate."""
    lsp.open(SOURCE)
    first = _highlights(lsp, _position(SOURCE, "outer", occurrence=1))
    assert first is not None
    assert (14, 4, 9) not in _spans(first)
    assert (15, 14, 19) not in _spans(first)

    second = _highlights(lsp, _position(SOURCE, "outer", occurrence=4))
    assert second is not None
    assert _spans(second) == [(14, 4, 9), (15, 14, 19)]


def test_highlight_on_a_non_label_position_keeps_the_symbol_highlights(lsp):
    """An ordinary identifier still gets the pre-existing symbol-based scan."""
    lsp.open(SOURCE)
    highlights = _highlights(lsp, _position(SOURCE, "hits", occurrence=1))

    assert highlights is not None
    assert _spans(highlights) == [
        (1, 8, 12),    # `var hits`
        (10, 16, 20),  # `set hits`
        (10, 24, 28),  # read in `hits + 1`
        (11, 11, 15),  # `return hits`
    ]
    label_spans = {(line, char, char + length)
                   for line, char, length in _LABEL_SPANS}
    assert not label_spans & set(_spans(highlights))


def test_highlight_on_a_keyword_is_not_a_label_highlight(lsp):
    """The ``break`` keyword itself is not the label token that follows it."""
    lsp.open(SOURCE)
    assert _highlights(lsp, Position(line=7, character=16)) is None


# ---------------------------------------------------------------------------
# Buffers that do not parse
# ---------------------------------------------------------------------------

def test_unlexable_buffer_yields_no_tokens_and_no_highlights(lsp):
    """A buffer the lexer rejects returns nothing instead of raising."""
    from pengu_lsp import server as lsp_server

    lsp.open(BROKEN_LEX)
    tokens = lsp_server.semantic_tokens_full(SemanticTokensParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri)))
    assert tokens is None

    assert _highlights(lsp, Position(line=1, character=8)) is None


def test_parse_only_broken_buffer_contributes_no_label_token(lsp):
    """Mid-edit highlighting survives: lexical tokens stay, labels do not."""
    from pengu_lsp import server as lsp_server

    lsp.open(PARSE_ONLY_BROKEN)
    tokens = lsp_server.semantic_tokens_full(SemanticTokensParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri)))
    assert tokens is not None
    decoded = _decode(tokens.data)
    assert decoded, decoded
    assert _label_tokens(decoded) == []

    # No parsed tree means no label resolution, so the old symbol scan answers;
    # it must simply not raise (the position is textually on a label).
    highlights = _highlights(lsp, Position(line=1, character=6))
    assert _spans(highlights) == [(1, 4, 9)]
