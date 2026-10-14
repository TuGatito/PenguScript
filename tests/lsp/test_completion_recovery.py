"""Completions while the buffer is mid-edit (the ``player.`` regression).

The parser is all-or-nothing: a half-typed line (`set player.x is player.`)
makes it reject the whole buffer. The check never ran, so the symbol table the
completion handler read was the one the checker's constructor leaves behind —
the primitive types, ``print`` and the built-in concepts, and nothing else.

The user-visible symptoms were:

* `player.` and `r->` offered the keyword list instead of the rune's fields,
  because nothing could resolve ``player`` to its ``Player`` type;
* the local variable itself was missing from plain identifier completion;
* imported modules kept working (``spark.`` offered its members) because the
  server-wide module cache is filled by *other* documents that did parse — which
  is exactly what made the bug look variable-specific.

`pengu_lsp.server._recover_symbols` blanks the line the parser choked on and
re-checks, so every declaration that is not on the line being edited survives.
Diagnostics are still computed from the real text.

Seven of the tests below fail with the recovery disabled
(``_MAX_SYMBOL_REPAIR_ATTEMPTS = 0``); the rest pin down that the fix leaves the
paths that already worked — a clean buffer, a semantic error, a document that
cannot be repaired at all — exactly as they were.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import DiagnosticSeverity

pytestmark = pytest.mark.smoke

#: A rune with four fields, an attached method and a `main` that builds two
#: ``Player`` values. Every regression test starts from this shape.
PLAYER_PROGRAM = '''rune Player:
    x as int
    y as int
    width as int
    height as int

enchanting Player:
    weave move into int:
        return self->x + 1

weave main into int:
    var player as Player is with x is 1, y is 2, width is 3, height is 4
    var alice as Player is with x is 0, y is 0, width is 0, height is 0
    {statement}
    return 0
'''

PLAYER_FIELDS = {"x", "y", "width", "height"}


def _program(statement: str) -> str:
    return PLAYER_PROGRAM.format(statement=statement)


# ---------------------------------------------------------------------------
# The reported bug: member completion after a dot / arrow
# ---------------------------------------------------------------------------

def test_dot_completion_works_while_the_member_is_half_typed(lsp):
    """`set player.x is player.` must offer the rune's fields, not keywords."""
    lsp.open(_program("set player.x is player."))

    labels = lsp.complete_after("is player.")

    assert PLAYER_FIELDS <= set(labels), labels
    assert "move" in labels, "the enchanting method is missing: " + repr(labels)
    # The pre-fix behaviour was the keyword/snippet list.
    assert "rune" not in labels


def test_arrow_completion_works_through_a_reference(lsp):
    """`r->` on a `ref to Player` offers the same members as `player.`."""
    source = _program(
        "var r as ref to Player is sigil of player\n    set player.x is r->"
    )
    lsp.open(source)

    labels = lsp.complete_after("is r->")

    assert PLAYER_FIELDS <= set(labels), labels
    assert "move" in labels


def test_nested_field_access_completes(lsp):
    """`player.pos.` resolves the nested rune, not just the first hop."""
    source = '''rune Vec2:
    x as float
    y as float

rune Player:
    pos as Vec2
    hp as int

weave main into int:
    var player as Player with:
        set .pos is with:
            set .x is 1.0
            set .y is 2.0
        set .hp is 3
    set player.pos.x is player.pos.
    return 0
'''
    lsp.open(source)

    labels = lsp.complete_after("is player.pos.")

    assert {"x", "y"} <= set(labels), labels


# ---------------------------------------------------------------------------
# The other half of the report: the identifier itself
# ---------------------------------------------------------------------------

def test_identifier_completion_offers_locals_while_typing(lsp):
    """Typing `pla` on a fresh line still offers the local `player`."""
    lsp.open(_program("pla"))

    labels = lsp.complete_after("pla")

    assert "player" in labels, labels
    assert "alice" in labels, labels


def test_identifier_completion_offers_params_and_siblings(lsp):
    """A half-typed line inside a nested block keeps the whole scope chain."""
    source = '''rune Player:
    x as int
    width as int

weave touch with p as ref to Player into void:
    var copy as Player is with x is p->x, width is p->width
    if p->width > 0:
        cop
    return
'''
    lsp.open(source)

    labels = lsp.complete_after("        cop")

    assert "copy" in labels, labels
    assert "p" in labels, labels


def test_an_incomplete_line_elsewhere_does_not_blank_the_symbol_table(lsp):
    """A dangling block far above the cursor must not cost the local symbols.

    This is the common shape of the user's report: the identifier being typed is
    perfectly well formed, but some *other* line is mid-edit, so the whole
    buffer failed to parse and every local vanished from the suggestions.
    """
    source = '''rune Player:
    x as int
    width as int

weave broken into int:
    var player as Player is with x is 1, width is 2
    if player.x > 0:
    return 0

weave helper into int:
    var local_thing as int is 2
    loc
    return 0
'''
    lsp.open(source)

    labels = lsp.complete_after("    loc")

    assert "local_thing" in labels, labels
    assert "helper" in labels, "top-level declarations survive too: " + repr(labels)


# ---------------------------------------------------------------------------
# Recovery must not disturb what already worked
# ---------------------------------------------------------------------------

def test_a_clean_document_is_unchanged(lsp):
    lsp.open(_program("set player.x is player.x"))

    errors = [d for d in lsp.diagnostics if d.severity == DiagnosticSeverity.Error]
    assert errors == []
    labels = lsp.complete_after("is player.")
    assert PLAYER_FIELDS <= set(labels)


def test_diagnostics_still_describe_the_real_text(lsp):
    """Recovery feeds the symbol table only; the published error is untouched."""
    lsp.open(_program("set player.x is player."))

    assert lsp.diagnostics, "the syntax error must still be reported"
    diag = lsp.diagnostics[0]
    assert diag.severity is not None
    # The error is on the half-typed line, which is where the user is looking.
    assert diag.range.start.line >= 10


def test_declarations_below_the_broken_line_are_recovered(lsp):
    """A rune declared *after* the cursor line must still be known."""
    source = '''weave main into int:
    var player as Player is with x is 1, y is 2, width is 3, height is 4
    set player.x is player.
    return 0

rune Player:
    x as int
    y as int
    width as int
    height as int
'''
    lsp.open(source)

    labels = lsp.complete_after("is player.")

    assert PLAYER_FIELDS <= set(labels), labels


def test_a_hopeless_document_degrades_to_the_old_behaviour(lsp):
    """Recovery is bounded: a document that cannot be repaired must not hang."""
    # Every line is broken, so blanking them all cannot leave a valid program.
    broken = "weave :\n::: :::\n  ??? :\n" * 40
    lsp.open(broken)

    labels = lsp.complete_after("??? :")

    assert "rune" in labels, "the keyword fallback must still answer"


def test_unsaved_buffer_path_is_not_required(lsp):
    """Symbol recovery works for a buffer that only exists in the editor."""
    from pengu_lsp import server as lsp_server

    uri = "file:///definitely/not/on/disk/main.pengu"
    with lsp_server.server._validation_lock:
        lsp_server.server._symbols.pop(uri, None)
    lsp_server.validate_document(uri, _program("set player.x is player."))

    symbols = lsp_server.server._symbols.get(uri)
    assert "Player" in getattr(symbols, "runes", {})


# ---------------------------------------------------------------------------
# The unit behind the recovery
# ---------------------------------------------------------------------------

def test_has_no_user_symbols_separates_a_bare_table_from_a_checked_one(lsp):
    from pengu_parser.pengu_symbols import SymbolTable
    from pengu_lsp.server import _has_no_user_symbols

    assert _has_no_user_symbols(None) is True
    # The constructor pre-loads primitives, `print` and the built-in concepts.
    assert _has_no_user_symbols(SymbolTable()) is True

    lsp.open(_program("set player.x is player.x"))
    assert _has_no_user_symbols(lsp.symbols) is False


def test_recover_symbols_returns_none_when_repair_is_impossible(lsp):
    from pengu_lsp.server import _recover_symbols

    recovered = _recover_symbols(
        "weave :\n::: :::\n  ??? :\n",
        str(lsp.path),
        str(lsp.directory),
        "lib",
        "src",
        1,
    )
    assert recovered is None


def test_the_semantic_error_path_does_not_pay_for_a_recovery(lsp, monkeypatch):
    """A document that parses keeps its partially-filled table as-is.

    Recovery is a repair for a *parse* failure. Running it after a type error
    would throw away a perfectly good partial table and waste a parse+check.
    """
    from pengu_lsp import server as lsp_server

    calls = []
    original = lsp_server._recover_symbols

    def counting(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(lsp_server, "_recover_symbols", counting)

    # Parses, but the checker rejects the initialiser: symbols are partial.
    lsp.open(_program('var broken as int is "not an int"'))
    assert calls == [], "a semantic error must not trigger the repair pass"
    assert lsp.symbols is not None
    assert "Player" in getattr(lsp.symbols, "runes", {})

    # Now a parse failure: the repair pass runs.
    lsp.open(_program("set player.x is player."))
    assert len(calls) == 1
    assert PLAYER_FIELDS <= set(lsp.complete_after("is player."))
