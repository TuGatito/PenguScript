import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import ParseError


def test_weave_inline_modifiers_both_orders():
    """Verify both 'weave inline' and 'inline weave' parse and compile cleanly."""
    code1 = (
        "weave inline helper into int:\n"
        "  return 42\n"
    )
    code2 = (
        "inline weave helper into int:\n"
        "  return 42\n"
    )
    parser = PenguParser()
    t1 = parser.parse(code1)
    assert t1 is not None
    t2 = parser.parse(code2)
    assert t2 is not None

    checker1 = PenguChecker()
    checker1.check(t1)
    assert len(checker1.errors) == 0

    checker2 = PenguChecker()
    checker2.check(t2)
    assert len(checker2.errors) == 0

    codegen1 = PenguCodegen(checker1.symbols)
    codegen1.collect_declarations([("test1.pengu", t1)])
    c1 = codegen1.generate_function_definitions()
    assert "static inline" in c1

    codegen2 = PenguCodegen(checker2.symbols)
    codegen2.collect_declarations([("test2.pengu", t2)])
    c2 = codegen2.generate_function_definitions()
    assert "static inline" in c2


def test_weave_ritual_modifier():
    """Verify 'weave ritual' parses and compiles cleanly."""
    code = (
        "weave ritual make into int:\n"
        "  return 100\n"
    )
    parser = PenguParser()
    tree = parser.parse(code)
    assert tree is not None
    checker = PenguChecker()
    checker.check(tree)
    assert len(checker.errors) == 0


def test_var_borrowed_modifier():
    """Verify 'var borrowed x is 5' compiles as a valid borrowed variable."""
    code = (
        "weave run into int:\n"
        "  var borrowed x is 5\n"
        "  return x\n"
    )
    parser = PenguParser()
    tree = parser.parse(code)
    assert tree is not None
    checker = PenguChecker()
    checker.check(tree)
    assert len(checker.errors) == 0


def test_borrowed_as_variable_name_rejected_by_grammar():
    """'var borrowed is 5' is rejected as ParseError because borrowed is semi-reserved after var/let."""
    parser = PenguParser()
    with pytest.raises(ParseError):
        parser.parse("var borrowed is 5\n")
