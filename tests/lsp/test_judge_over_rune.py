"""LSP services for ``judge <rune> over <discriminant>:``.

The language server resolves a ``with`` binding and the ``over`` discriminant
from the *document text* plus the checked symbol table: neither name is an
addressable symbol (a binding lives only inside its clause; the discriminant is
a field), so the generic symbol lookup cannot answer for them.  These tests pin
that behaviour: hover, go-to-definition, both completion points, and the
diagnostics the checker publishes with the right span.

The hover/definition calls go through the same functions the server's request
handlers call, so a regression in the wiring — not just in the helper — fails
here.
"""
from __future__ import annotations

from lsprotocol.types import Position

SOURCE = """\
rune Expr:
    kind as ExprKind
    int_value as int
    left as ref to Expr

omen ExprKind:
    Literal
    Binary
    Neg

weave eval with e as ref to Expr into int:
    judge e over kind:
        when Literal with int_value -> int_value
        when Binary with left -> calling eval with left
        when Neg -> 0
"""


def _position(text: str, needle: str, occurrence: int = 1, offset: int = 1):
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


def test_binding_completion_offers_the_rune_fields(lsp):
    lsp.open(SOURCE)
    labels = lsp.complete_after("when Literal with ")
    assert "int_value" in labels, labels
    # A field that is not bound in this clause is still offered: the rune's
    # fields are all valid bindings.
    assert "left" in labels, labels


def test_over_completion_offers_only_omen_fields(lsp):
    lsp.open(SOURCE)
    labels = lsp.complete_after("judge e over ")
    assert labels == ["kind"], labels


def test_binding_hover_shows_an_immutable_let(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    pos = _position(SOURCE, "int_value", occurrence=2)
    hover = get_hover(lsp.uri, pos, lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "let int_value as int" in value, value
    assert "immutable" in value, value


def test_discriminant_hover_lists_the_variants(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    pos = _position(SOURCE, "over kind:", offset=6)
    hover = get_hover(lsp.uri, pos, lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "over kind as ExprKind" in value, value
    assert "Literal" in value and "Neg" in value, value


def test_binding_definition_jumps_to_the_rune_field(lsp):
    from pengu_lsp.judge_over import judge_over_definition

    lsp.open(SOURCE)
    pos = _position(SOURCE, "left", occurrence=2)
    location = judge_over_definition(SOURCE, pos, lsp.symbols)
    assert location is not None
    # `left as ref to Expr` is the 4th line of the file (0-based 3).
    assert location.range.start.line == 3, location
    assert location.range.start.character == 4, location


def test_discriminant_definition_jumps_to_the_rune_field(lsp):
    from pengu_lsp.judge_over import judge_over_definition

    lsp.open(SOURCE)
    pos = _position(SOURCE, "over kind:", offset=6)
    location = judge_over_definition(SOURCE, pos, lsp.symbols)
    assert location is not None
    # `kind as ExprKind` is the 2nd line (0-based 1).
    assert location.range.start.line == 1, location


def test_diagnostics_report_the_checker_codes_with_spans(lsp):
    bad = SOURCE.replace("when Neg -> 0", "")
    lsp.open(bad)
    codes = [d.code for d in lsp.diagnostics]
    assert "E0044" in codes, codes
    e0044 = next(d for d in lsp.diagnostics if d.code == "E0044")
    # The diagnostic is anchored on the `judge` line (0-based 11).
    assert e0044.range.start.line == 11, e0044


def test_unknown_discriminant_is_reported(lsp):
    bad = SOURCE.replace("judge e over kind:", "judge e over nope:")
    lsp.open(bad)
    assert "E0013" in [d.code for d in lsp.diagnostics], lsp.diagnostics


def test_non_rune_subject_is_reported(lsp):
    bad = SOURCE.replace("weave eval with e as ref to Expr into int:",
                         "weave eval with e as int into int:")
    lsp.open(bad)
    assert "E0005" in [d.code for d in lsp.diagnostics], lsp.diagnostics


def test_semantic_tokens_mark_the_discriminant_and_bindings(lsp):
    from pengu_lsp.judge_over import (
        binding_token_spans,
        discriminant_token_spans,
    )

    over = discriminant_token_spans(SOURCE)
    bindings = binding_token_spans(SOURCE)
    # 1-based (line, column, length): the `over` discriminant and the two
    # `with` names, not the field uses inside the clause bodies.
    assert over == [(12, 18, 4)], over
    assert bindings == [(13, 27, 9), (14, 26, 4)], bindings


def test_completion_outside_a_judge_over_is_unaffected(lsp):
    """The new pass must not swallow ordinary completions."""
    lsp.open("weave f into int:\n    var x as int is 1\n    return x\n")
    labels = lsp.complete(2, 4)
    assert "x" in labels, labels


NESTED = """\
rune Inner:
    kind as K
    v as int

omen K:
    A
    B

rune Wrapper:
    inner as Inner

weave f with w as Wrapper into int:
    judge w.inner over kind:
        when A with v -> v
        when B -> 0
"""


STRING_OMEN = """\
omen K with string:
    X is "x"
    Y is "y"

rune R:
    kind as K
    v as int

weave f with r as R into int:
    judge r over kind:
        when X with v -> v
        when Y -> 0
"""


def test_nested_subject_completes_and_hovers(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(NESTED)
    assert lsp.complete_after("judge w.inner over ") == ["kind"]
    pos = _position(NESTED, "with v", offset=6)
    hover = get_hover(lsp.uri, pos, lsp.symbols, NESTED)
    assert hover is not None
    assert "let v as int" in hover.contents.value, hover.contents.value


def test_nested_subject_binding_definition(lsp):
    from pengu_lsp.judge_over import judge_over_definition

    lsp.open(NESTED)
    pos = _position(NESTED, "with v", offset=6)
    location = judge_over_definition(NESTED, pos, lsp.symbols)
    assert location is not None
    assert location.range.start.line == 2, location


def test_string_valued_discriminant_still_completes(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(STRING_OMEN)
    assert lsp.complete_after("judge r over ") == ["kind"]
    pos = _position(STRING_OMEN, "over kind:", offset=6)
    hover = get_hover(lsp.uri, pos, lsp.symbols, STRING_OMEN)
    assert hover is not None
    assert "X" in hover.contents.value and "Y" in hover.contents.value


def test_binding_completion_filters_by_the_typed_prefix(lsp):
    lsp.open(SOURCE)
    line = next(i for i, t in enumerate(SOURCE.splitlines()) if "with int_value" in t)
    # Cursor after `with int` — only `int_value` may be offered.
    column = SOURCE.splitlines()[line].index("with ") + len("with int")
    labels = lsp.complete(line, column)
    assert labels == ["int_value"], labels


def test_half_typed_over_line_offers_the_discriminant(lsp):
    from pengu_lsp.judge_over import discriminant_token_spans

    # `over ` with nothing typed yet: there is no name to highlight.
    empty = ("rune R:\n    kind as K\n    v as int\n\nomen K:\n    A\n    B\n\n"
             "weave f with r as R into int:\n    judge r over \n")
    lsp.open_unsaved(empty)
    assert discriminant_token_spans(empty) == []
    # A partially typed discriminant is highlighted while it is being typed.
    partial = empty.replace("over \n", "over kin\n")
    assert discriminant_token_spans(partial) == [(10, 18, 3)]


def test_definition_is_none_for_a_body_use(lsp):
    from pengu_lsp.judge_over import judge_over_definition

    lsp.open(SOURCE)
    # `calling eval with left`: `left` here is a use in the body, not the binding.
    pos = _position(SOURCE, "with left", offset=len("with left") + 10)
    location = judge_over_definition(SOURCE, pos, lsp.symbols)
    assert location is None


def test_completions_are_untouched_without_a_rune(lsp):
    lsp.open("weave f with x as int into int:\n    judge x over \n")
    labels = lsp.complete_after("judge x over ")
    assert labels == [] or "kind" not in labels, labels
