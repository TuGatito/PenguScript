import pytest
import warnings
from lark import Lark
from pengu_parser.pengu_grammar import GRAMMAR
from pengu_parser.pengu_parser import PenguParser, PenguIndenter
from pengu_parser.pengu_errors import ParseError


def test_grammar_lalr_builds_cleanly():
    """Verify that the LALR parser builds without warnings or reduce/reduce conflicts."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        parser = Lark(
            GRAMMAR,
            parser="lalr",
            postlex=PenguIndenter(),
            propagate_positions=True,
            start=["start", "expr"],
            cache=False,
        )
        assert parser is not None
        # Assert no unexpected grammar or lexer warnings were raised during build
        assert len(recorded) == 0


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
