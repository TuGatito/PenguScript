import pytest
import warnings
from pengu_parser.pengu_parser import PenguParser, BOM
from pengu_parser.pengu_errors import ParseError


def test_dedent_error_produces_clean_parse_error():
    """An inconsistent dedent raises a clean ParseError(E0000) with line/col and snippet."""
    code = (
        "weave foo into void:\n"
        "    var x is 1\n"
        "  var y is 2\n"
    )
    parser = PenguParser()
    with pytest.raises(ParseError) as exc_info:
        parser.parse(code)
    err = exc_info.value
    assert getattr(err, "code", None) == "E0000"
    assert err.line == 3
    assert err.col is not None
    assert err.snippet is not None
    assert "  var y is 2" in err.snippet


def test_bom_in_get_tokens():
    """get_tokens strips leading BOM characters cleanly."""
    parser = PenguParser()
    code = f"{BOM}var x is 42\n"
    tokens = parser.get_tokens(code)
    assert len(tokens) > 0
    # First token value must not start with \ufeff
    assert not tokens[0].value.startswith("\ufeff")
    assert tokens[0].type == "VAR"


def test_bom_in_parse_expr():
    """parse_expr handles expressions with leading BOM."""
    parser = PenguParser()
    expr = f"{BOM}1 + 2"
    tree = parser.parse_expr(expr)
    assert tree is not None
    assert tree.data in ("add", "expr", "bit_add")


def test_mixed_tabs_and_spaces_emits_warning():
    """Mixed tabs and spaces indentation emits [W0005] warning without failing parse."""
    code = (
        "weave test into void:\n"
        "\tvar a is 1\n"
        "  var b is 2\n"
    )
    parser = PenguParser()
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        tree = parser.parse(code)
        assert tree is not None
        # Check warning recorded in parser.warnings
        w0005_warnings = [w for w in parser.warnings if "[W0005]" in w]
        assert len(w0005_warnings) > 0
        assert "Inconsistent indentation" in w0005_warnings[0]
        assert "uses tabs" in w0005_warnings[0] and "uses spaces" in w0005_warnings[0]


def test_pure_crlf_compiles_without_warnings():
    """Pure CRLF (\r\n) line endings parse cleanly without indentation warnings."""
    code = "weave test into void:\r\n  var a is 1\r\n  var b is 2\r\n"
    parser = PenguParser()
    tree = parser.parse(code)
    assert tree is not None
    assert len(parser.warnings) == 0
