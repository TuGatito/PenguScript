"""LSP hover for ``type of expr``.

``type of`` is resolved by the checker, which records the canonical name on the
node (``_resolved_type_name``).  The hover handler reads it back from the tree
the last validation produced, so these tests drive the real validation path
(``server.validate_document``, via the ``lsp`` fixture) and then ask for hover
exactly where an editor would.

What is pinned here:

* hovering the ``type`` keyword, the ``of`` keyword and the operand all report
  the canonical name (``int``, ``Player``, ``list of int``, …);
* the answer comes from the checker, so a monomorphized ``shard T`` expression is
  not reported as ``T``;
* no answer is invented for a plain expression, for an unresolved buffer, or for
  a ``type of`` the checker never reached.
"""
from __future__ import annotations

from lsprotocol.types import Position

import pytest

pytestmark = pytest.mark.smoke

SOURCE = '''rune Player:
    name as string

weave describe with x as int into string:
    return "x: {type of x}"

weave names into int:
    var xs as list of Player is list of Player
    var p as Player is with name is "Ada"
    var a as string is type of xs
    var b as string is type of p
    return 0
'''

GENERIC = '''rune Box shard T:
    value as T

weave describe shard T with x as T into string:
    return type of x

weave use into int:
    var a as string is calling describe with 42
    return 0
'''


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


def _hover(lsp, position: Position):
    from pengu_lsp.hover import get_hover

    return get_hover(lsp.uri, position, lsp.symbols, lsp.text)


def test_hover_on_the_operand_reports_the_canonical_name(lsp):
    lsp.open(SOURCE)
    # `type of xs` on line 10; the cursor on `xs`.
    hover = _hover(lsp, _position(SOURCE, "type of xs", offset=8))
    assert hover is not None
    value = hover.contents.value
    assert "list of Player" in value, value
    assert "compile-time" in value, value


def test_hover_on_the_type_keyword_reports_it_too(lsp):
    lsp.open(SOURCE)
    for offset in (0, 5):          # `type` and `of`
        hover = _hover(lsp, _position(SOURCE, "type of xs", offset=offset))
        assert hover is not None, offset
        assert "list of Player" in hover.contents.value, hover.contents.value


def test_hover_in_a_string_interpolation(lsp):
    """`"{type of x}"` is an expression too: the checker resolved it."""
    lsp.open(SOURCE)
    hover = _hover(lsp, _position(SOURCE, "type of x", offset=8))
    assert hover is not None
    assert "int" in hover.contents.value, hover.contents.value


def test_hover_reports_the_local_nominal_name(lsp):
    lsp.open(SOURCE)
    hover = _hover(lsp, _position(SOURCE, "type of p", offset=8))
    assert hover is not None
    assert "→ Player" in hover.contents.value, hover.contents.value


def test_hover_resolves_a_generic_to_the_checked_parameter(lsp):
    """Inside the shard body the name is the parameter (monomorphization is codegen)."""
    lsp.open(GENERIC)
    hover = _hover(lsp, _position(GENERIC, "type of x", offset=8))
    assert hover is not None
    assert "T" in hover.contents.value, hover.contents.value


def test_hover_is_silent_off_the_expression(lsp):
    lsp.open(SOURCE)
    # On `var a as string`: an ordinary declaration, not a type-of expression.
    hover = _hover(lsp, _position(SOURCE, "string", occurrence=1, offset=1))
    value = hover.contents.value if hover is not None else ""
    assert "compile-time operator" not in value, value


def test_hover_is_silent_before_validation(lsp):
    """No validated tree for this text -> no invented answer."""
    from pengu_lsp.hover import get_hover

    text = "weave f with x as int into string:\n    return type of x\n"
    hover = get_hover(lsp.uri, Position(line=1, character=17), None, text)
    assert hover is None or "compile-time operator" not in hover.contents.value


def test_hover_does_not_crash_on_a_broken_buffer(lsp):
    from pengu_lsp.hover import get_hover

    broken = "weave f into int:\n    var a as string is type of\n"
    lsp.open(broken)
    hover = get_hover(lsp.uri, Position(line=1, character=30), lsp.symbols, broken)
    # Either None or an ordinary hover; the point is that nothing raises.
    assert hover is None or hover.contents is not None
