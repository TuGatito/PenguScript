import pytest
import warnings
from lark import Lark
from pengu_parser.pengu_grammar import GRAMMAR
from pengu_parser.pengu_parser import PenguParser, PenguIndenter
from pengu_parser.pengu_errors import ParseError


def test_grammar_lalr_builds_cleanly():
    """The LALR parser builds and the production options are the ones expected.

    NOTE (Phase 1, blocker B11): this test used to assert `len(recorded) == 0`
    over `warnings.catch_warnings()`, which is **vacuous** -- Lark resolves
    shift/reduce conflicts by an internal heuristic and only logs them through
    the `lark` logger at DEBUG level, so it never emits a Python warning and the
    assertion held no matter how many conflicts the grammar had. The grammar in
    fact has 188 shift/reduce conflicts across 79 terminals.

    The real check is `strict=True`, which turns each conflict into
    `GrammarError`. That is asserted explicitly by
    `test_grammar_strict_mode_conflict_budget` below, which records the current
    count so it can only go down.
    """
    parser = Lark(
        GRAMMAR,
        parser="lalr",
        postlex=PenguIndenter(),
        propagate_positions=True,
        start=["start", "expr"],
        cache=False,
    )
    assert parser is not None


#: Number of shift/reduce conflicts the grammar had when this budget was
#: recorded (Phase 1). Lark resolves every one of them as *shift*, which happens
#: to produce correct left-associativity and precedence for this expression
#: grammar -- but that is a property of the dependency's default heuristic, not
#: a guarantee of the language. The budget may only decrease.
_KNOWN_SHIFT_REDUCE_CONFLICTS = 188


def _count_shift_reduce_conflicts():
    """Counts the grammar's shift/reduce conflicts by rebuilding it in debug mode.

    Lark only reports conflicts through its logger, and only when `debug=True`;
    `strict=True` aborts on the first one, so it cannot be used to count them.
    """
    import io
    import logging
    import lark.parsers.lalr_analysis as analysis

    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setLevel(logging.WARNING)
    logger = analysis.logger
    previous_level, previous_disabled = logger.level, logger.disabled
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    logging.disable(logging.NOTSET)
    try:
        Lark(GRAMMAR, parser="lalr", propagate_positions=True, debug=True, cache=None)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled

    return sum(1 for line in buffer.getvalue().splitlines() if "conflict" in line.lower())


@pytest.mark.timeout(300)
def test_grammar_strict_mode_conflict_budget():
    """The grammar's ambiguity must not grow (blocker B11).

    This is the honest version of "the grammar is strict": the grammar is NOT
    LALR(1) today, and this test says so with a number instead of a vacuous
    `assert len(recorded) == 0`. Reducing the count is the Phase 2 goal; growing
    it is a regression.
    """
    count = _count_shift_reduce_conflicts()
    assert count <= _KNOWN_SHIFT_REDUCE_CONFLICTS, (
        f"the grammar grew to {count} shift/reduce conflicts "
        f"(budget {_KNOWN_SHIFT_REDUCE_CONFLICTS}); "
        "Lark resolves them by shift, so the language's operator precedence now "
        "depends on more heuristics than before"
    )


@pytest.mark.timeout(120)
def test_grammar_strict_mode_is_not_silently_enabled():
    """Pins the *reason* the conflict budget exists.

    If someone flips `strict=True` on the production parser, construction starts
    raising `GrammarError` instead of resolving by shift -- which would be a
    behaviour change to the language. This test documents the current state so
    that change is deliberate rather than accidental.
    """
    with pytest.raises(Exception) as excinfo:
        Lark(
            GRAMMAR,
            parser="lalr",
            postlex=PenguIndenter(),
            propagate_positions=True,
            start=["start", "expr"],
            cache=False,
            strict=True,
        )
    assert "conflict" in str(excinfo.value).lower()

    # And the production parser must NOT pass strict=True.
    source = (__import__("pathlib").Path(__file__).resolve().parent.parent
              / "pengu_parser" / "pengu_parser.py").read_text(encoding="utf-8")
    assert "strict=True" not in source, (
        "PenguParser builds Lark with strict=True; the conflict budget test above "
        "documents that this grammar is not LALR(1) yet"
    )


def test_mandatory_statement_delimiter_rejects_inline_statements():
    """Simple statement declarations require a mandatory newline delimiter.
    
    Two statements on the same line ('var x is 1 var y is 2') must fail with E0000 ParseError.
    """
    parser = PenguParser()
    with pytest.raises(ParseError) as exc_info:
        parser.parse("var x is 1 var y is 2")
    assert getattr(exc_info.value, "code", None) == "E0000"


def test_mandatory_statement_delimiter_accepts_multiline_statements():
    """Declarations separated by clean newlines parse without errors."""
    parser = PenguParser()
    tree = parser.parse("var x is 1\nvar y is 2\n")
    assert tree is not None
    assert tree.data == "start"


def test_let_and_set_require_mandatory_newline():
    """'let' and 'set' statements also require newlines and cannot be chained inline."""
    parser = PenguParser()
    with pytest.raises(ParseError) as exc_info:
        parser.parse("let a is 1 let b is 2")
    assert getattr(exc_info.value, "code", None) == "E0000"

    with pytest.raises(ParseError) as exc_info:
        parser.parse("set x is 1 set y is 2")
    assert getattr(exc_info.value, "code", None) == "E0000"
