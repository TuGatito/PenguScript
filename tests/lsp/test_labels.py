"""LSP services for labels on ``break`` / ``continue``.

A loop label (``outer: for line in lines:``) is *not* a module symbol: the
checker keeps labels in a per-function namespace, they cannot be imported and
they never appear in the symbol table.  These tests pin the editor services that
therefore resolve them from the parsed tree: hover on the declaration and on
``break outer`` / ``continue outer``, go-to-definition, completion after
``break `` / ``continue ``, and rename within the loop's function.  Bare
``break`` / ``continue`` keep their old behaviour.

The request calls go through the same entry points the server's handlers call
(``get_hover``, ``get_completions``, ``server.definition``,
``server.prepare_rename``, ``server.rename_symbol``), so a regression in the
wiring — not only in ``pengu_lsp.labels`` — fails here.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import (
    DefinitionParams,
    Position,
    PrepareRenameParams,
    RenameParams,
    TextDocumentIdentifier,
)

pytestmark = pytest.mark.smoke

#: Two functions, each with a labeled loop.  ``outer`` deliberately appears in
#: both: labels are unique *per function*, so the rename tests prove the two are
#: different labels.  ``inner`` is a nested labeled loop, so a jump inside it has
#: two enclosing labels to choose from.
SOURCE = '''weave scan with lines as list of string into int:
    var hits as int is 0
    outer: for line in lines:
        inner: for ch in line:
            if ch == ";":
                continue outer
            if ch == "}":
                break inner
            set hits is hits + 1
    return hits

weave other with xs as list of int into int:
    outer: while true:
        break outer
    return 0
'''

#: A program with bare ``break`` / ``continue`` only.
BARE = '''weave f into int:
    while true:
        break
    return 0
'''

#: An ordinary local variable, used to prove rename is otherwise untouched.
ORDINARY = '''weave f into int:
    var counter as int is 0
    set counter is counter + 1
    return counter
'''

#: One-line `if c: break outer` / `if c: continue outer` produce the grammar's
#: `break_simple` / `continue_simple` alias nodes instead of `break_stmt` /
#: `continue_stmt`; the label must resolve exactly the same.
ONE_LINE = '''weave f with xs as list of int into int:
    outer: for x in xs:
        if x > 0: break outer
        if x < 0: continue outer
    return 0
'''


def _position(text: str, needle: str, occurrence: int = 1, offset: int = 1) -> Position:
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


def _rename(lsp, position: Position, new_name: str):
    """Runs the server's rename handler at ``position``."""
    from pengu_lsp import server as lsp_server

    params = RenameParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=position,
        new_name=new_name,
    )
    return lsp_server.rename_symbol(params)


def _edit_spans(edit, uri: str):
    """Sorted ``(line, column, new_text)`` of an edit's changes for ``uri``."""
    return sorted(
        (e.range.start.line, e.range.start.character, e.new_text)
        for e in edit.changes.get(uri, [])
    )


# ---------------------------------------------------------------------------
# Hover
# ---------------------------------------------------------------------------

def test_hover_on_the_label_declaration_describes_the_loop(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    # `outer:` on the outer `for` loop (0-based line 2).
    pos = _position(SOURCE, "outer", occurrence=1)
    hover = get_hover(lsp.uri, pos, lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "label outer: for" in value, value
    assert "Loop label" in value, value
    assert "break outer" in value and "continue outer" in value, value


def test_hover_on_the_label_of_a_continue_describes_the_target(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    # `continue outer` (0-based line 5).
    pos = _position(SOURCE, "outer", occurrence=2)
    hover = get_hover(lsp.uri, pos, lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "label outer: for" in value, value
    assert "continue outer" in value, value


def test_hover_on_the_label_of_a_break_reports_its_loop_kind(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    # `break inner` (0-based line 7) targets the nested `for`.
    hover = get_hover(lsp.uri, _position(SOURCE, "inner", occurrence=2),
                      lsp.symbols, SOURCE)
    assert hover is not None
    assert "label inner: for" in hover.contents.value, hover.contents.value

    # `break outer` in the second function targets a `while` loop (line 13).
    hover = get_hover(lsp.uri, _position(SOURCE, "outer", occurrence=4),
                      lsp.symbols, SOURCE)
    assert hover is not None
    assert "label outer: while" in hover.contents.value, hover.contents.value


def test_hover_on_a_bare_break_or_continue_is_not_a_label(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(BARE)
    for column in (8, 9, 14):
        hover = get_hover(lsp.uri, Position(line=2, character=column),
                          lsp.symbols, BARE)
        value = hover.contents.value if hover is not None else ""
        assert "Loop label" not in value, value


def test_hover_needs_no_symbol_table(lsp):
    """Labels are not symbols, so a buffer without a table still hovers."""
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    hover = get_hover(lsp.uri, _position(SOURCE, "outer", occurrence=1), None, SOURCE)
    assert hover is not None
    assert "label outer: for" in hover.contents.value, hover.contents.value


# ---------------------------------------------------------------------------
# Go to definition
# ---------------------------------------------------------------------------

def test_definition_from_continue_outer_jumps_to_the_label(lsp):
    from pengu_lsp import server as lsp_server

    lsp.open(SOURCE)
    params = DefinitionParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=_position(SOURCE, "outer", occurrence=2),
    )
    location = lsp_server.definition(params)
    assert location is not None
    assert location.uri == lsp.uri, location
    assert location.range.start.line == 2, location
    assert location.range.start.character == 4, location
    assert location.range.end.character == 4 + len("outer"), location


def test_definition_from_break_inner_jumps_to_the_nested_label(lsp):
    from pengu_lsp import server as lsp_server

    lsp.open(SOURCE)
    params = DefinitionParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=_position(SOURCE, "inner", occurrence=2),
    )
    location = lsp_server.definition(params)
    assert location is not None
    assert location.range.start.line == 3, location
    assert location.range.start.character == 8, location


def test_definition_of_a_label_survives_a_missing_symbol_table(lsp):
    from pengu_lsp import server as lsp_server

    lsp.open(SOURCE)
    with lsp_server.server._validation_lock:
        lsp_server.server._symbols.pop(lsp.uri, None)
    params = DefinitionParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=_position(SOURCE, "outer", occurrence=4),
    )
    location = lsp_server.definition(params)
    assert location is not None
    assert location.range.start.line == 12, location


# ---------------------------------------------------------------------------
# Completions
# ---------------------------------------------------------------------------

def test_completion_after_continue_offers_enclosing_labels(lsp):
    lsp.open(SOURCE)
    # `continue outer` sits inside both the `outer` and the `inner` loop.
    assert lsp.complete_after("continue ") == ["inner", "outer"]


def test_completion_after_break_offers_and_filters_labels(lsp):
    lsp.open(SOURCE)
    assert lsp.complete_after("break ") == ["inner", "outer"]
    # A typed prefix filters, like every other completion point.
    assert lsp.complete_after("break i") == ["inner"]


def test_completion_offers_only_loops_that_enclosing_the_cursor(lsp):
    lsp.open(SOURCE)
    # The second `break ` is inside the second function's `while`; the `inner`
    # label of the first function must not leak into its suggestions.
    assert lsp.complete_after("break ", occurrence=2) == ["outer"]


def test_bare_break_and_continue_keep_the_keyword_completion(lsp):
    lsp.open(SOURCE)
    # Cursor right after `break` with no space: 16 indent + len("break").
    labels = lsp.complete(7, 16 + len("break"))
    assert "break" in labels, labels
    assert "continue" in labels, labels


def test_label_completion_returns_none_outside_a_jump(lsp):
    from pengu_lsp.labels import loop_label_completions

    lsp.open(SOURCE)
    # After `set ` there is no label position at all.
    assert loop_label_completions(SOURCE, Position(line=8, character=12)) is None


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------

def test_rename_from_the_declaration_rewrites_the_loop(lsp):
    lsp.open(SOURCE)
    edit = _rename(lsp, _position(SOURCE, "outer", occurrence=1), "lineLoop")
    assert edit is not None
    assert _edit_spans(edit, lsp.uri) == [
        (2, 4, "lineLoop"),
        (5, 25, "lineLoop"),
    ]


def test_rename_from_a_reference_rewrites_the_same_loop(lsp):
    lsp.open(SOURCE)
    edit = _rename(lsp, _position(SOURCE, "outer", occurrence=2), "lineLoop")
    assert edit is not None
    assert _edit_spans(edit, lsp.uri) == [
        (2, 4, "lineLoop"),
        (5, 25, "lineLoop"),
    ]


def test_rename_of_an_inner_label_keeps_the_outer_loop(lsp):
    lsp.open(SOURCE)
    edit = _rename(lsp, _position(SOURCE, "inner", occurrence=1), "chLoop")
    assert edit is not None
    assert _edit_spans(edit, lsp.uri) == [
        (3, 8, "chLoop"),
        (7, 22, "chLoop"),
    ]


def test_rename_does_not_touch_a_homonym_label_in_another_function(lsp):
    lsp.open(SOURCE)
    # The second function's `outer` is a different label: only its loop changes.
    edit = _rename(lsp, _position(SOURCE, "outer", occurrence=3), "lineLoop")
    assert edit is not None
    assert _edit_spans(edit, lsp.uri) == [
        (12, 4, "lineLoop"),
        (13, 14, "lineLoop"),
    ]


def test_rename_rejects_an_invalid_label_name(lsp):
    lsp.open(SOURCE)
    assert _rename(lsp, _position(SOURCE, "outer", occurrence=1), "1bad") is None


def test_prepare_rename_accepts_a_label_and_rejects_a_bare_keyword(lsp):
    from pengu_lsp import server as lsp_server

    lsp.open(SOURCE)
    params = PrepareRenameParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=_position(SOURCE, "outer", occurrence=4),
    )
    selected = lsp_server.prepare_rename(params)
    assert selected is not None
    assert selected.start.line == 13 and selected.start.character == 14, selected
    assert selected.end.character == 14 + len("outer"), selected

    lsp.open(BARE)
    params = PrepareRenameParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=Position(line=2, character=9),
    )
    assert lsp_server.prepare_rename(params) is None


def test_rename_of_an_ordinary_identifier_is_untouched(lsp):
    lsp.open(ORDINARY)
    edit = _rename(lsp, _position(ORDINARY, "counter", occurrence=1), "total")
    assert edit is not None
    assert _edit_spans(edit, lsp.uri) == [
        (1, 8, "total"),
        (2, 8, "total"),
        (2, 19, "total"),
        (3, 11, "total"),
    ]


# ---------------------------------------------------------------------------
# One-line `break` / `continue` aliases
# ---------------------------------------------------------------------------

def test_one_line_break_and_continue_aliases_are_resolved(lsp):
    from pengu_lsp import server as lsp_server
    from pengu_lsp.hover import get_hover

    lsp.open(ONE_LINE)
    # `break outer` and `continue outer` both jump to the label on line 1.
    for occurrence in (2, 3):
        params = DefinitionParams(
            text_document=TextDocumentIdentifier(uri=lsp.uri),
            position=_position(ONE_LINE, "outer", occurrence=occurrence),
        )
        location = lsp_server.definition(params)
        assert location is not None, occurrence
        assert location.range.start.line == 1, location
        assert location.range.start.character == 4, location

    hover = get_hover(lsp.uri, _position(ONE_LINE, "outer", occurrence=2),
                      lsp.symbols, ONE_LINE)
    assert hover is not None
    assert "break outer" in hover.contents.value, hover.contents.value

    assert lsp.complete_after("break ") == ["outer"]

    edit = _rename(lsp, _position(ONE_LINE, "outer", occurrence=1), "loopX")
    assert edit is not None
    assert _edit_spans(edit, lsp.uri) == [
        (1, 4, "loopX"),
        (2, 24, "loopX"),
        (3, 27, "loopX"),
    ]


# ---------------------------------------------------------------------------
# A document that does not parse
# ---------------------------------------------------------------------------

def test_labels_degrade_to_nothing_on_a_broken_document():
    """A buffer mid-edit parses nowhere: every service returns empty, not raise."""
    from pengu_lsp.labels import (
        loop_label_completions,
        loop_label_definition,
        loop_label_hover,
        loop_label_prepare_rename,
        loop_label_rename,
    )

    broken = "weave f into int:\n    outer: for x in :\n"
    position = Position(line=1, character=6)
    assert loop_label_hover(broken, position) is None
    assert loop_label_definition(broken, position, "file:///broken.pengu") is None
    assert loop_label_prepare_rename(broken, position) is None
    assert loop_label_rename(broken, position, "renamed", "file:///broken.pengu") is None
    assert loop_label_completions(broken, Position(line=1, character=15)) is None
