"""`antiquus` — semantic checks (checker).

The C body is opaque, but everything *around* it is an ordinary PenguScript
signature: it registers a callable, takes part in overload resolution and DCE,
and obeys the same attribute rules as a weave.  These tests pin the rejections
the construct owes the user and the parts of the symbol table it must populate.
"""
import pytest

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from tests.conftest import REPO, check_error, check_ok

BODY = '    """\n    return 0;\n    """\n'


def _params(body: str) -> str:
    return f'antiquus f with {body} into int:\n    """\n    return 0;\n    """\n'


def test_signature_is_registered_as_a_callable():
    checker = check_ok(
        'antiquus add with a as int, b as int into int:\n'
        + BODY
        + '\nweave main into int:\n    return calling add with 1, 2\n'
    )
    fn = checker.symbols.functions["add"]
    assert [p[0] for p in fn.params] == ["a", "b"]
    assert fn.return_type.name == "int"
    sym = checker.symbols.lookup("add")
    assert sym is not None and sym.kind == "weave"


def test_generic_antiquus_registers_a_template():
    checker = check_ok(
        'antiquus ident shard T with v as T into T:\n'
        + BODY
        + '\nweave main into int:\n    return calling ident with 3\n'
    )
    assert "ident" in checker.symbols.generic_functions


def test_default_parameters_are_counted():
    checker = check_ok(
        'antiquus f with a as int, b as int is 4 into int:\n'
        + BODY
        + '\nweave main into int:\n    return calling f with 1\n'
    )
    assert checker.symbols.functions["f"].default_count == 1


def test_export_pins_the_c_symbol():
    checker = check_ok(
        '@export("pengu_custom_name")\nantiquus f into int:\n'
        + BODY
        + '\nweave main into int:\n    return 0\n'
    )
    sym = checker.symbols.lookup("f")
    assert sym is not None and sym.c_name == "pengu_custom_name"


def test_rejected_in_a_declaration_file():
    check_error(
        'antiquus f into int:\n' + BODY,
        filename="binding.d.pengu",
        contains="E0025",
    )


def test_rejects_c_keyword_parameter_name():
    """The C body sees the parameter verbatim; `_c_ident` must not be applied."""
    check_error(_params("if as int"), contains="E0035")


def test_rejects_many_parameter():
    check_error(_params("xs as many int"), contains="E0005")


def test_rejects_default_before_required():
    check_error(_params("a as int is 1, b as int"), contains="E0005")


def test_rejects_duplicate_parameter():
    check_error(_params("a as int, a as int"), contains="E0005")


def test_rejects_main():
    check_error(
        'antiquus main into int:\n' + BODY,
        contains="E0040",
    )


def test_rejects_noreturn_with_a_return_value():
    check_error(
        '@noreturn\nantiquus f into int:\n' + BODY,
        contains="E0056",
    )


def test_rejects_an_unknown_attribute():
    check_error(
        '@packed\nantiquus f into int:\n' + BODY,
        contains="E0056",
    )


def test_accepts_the_documented_attributes():
    check_ok(
        '@inline\n@cold\n@deprecated("use g")\n@noreturn\n'
        'antiquus f into void:\n'
        '    """\n    return;\n    """\n'
        '\nweave main into int:\n    calling f\n    return 0\n'
    )


def test_rejects_an_empty_body():
    """`""""""` is a body token with no C in it: that is a mistake, not a no-op."""
    check_error(
        'antiquus f into int:\n    """"""\n\nweave main into int:\n    return 0\n',
        contains="E0059",
    )


def test_rejects_a_plain_string_body():
    """Only triple-quoted bodies survive extraction; `"..."` must not parse away."""
    with pytest.raises(Exception) as exc_info:
        parser = PenguParser()
        tree = parser.parse('antiquus f into int:\n    "return 0;"\n')
        checker = PenguChecker(base_dir=str(REPO))
        checker.check(tree, source='antiquus f into int:\n    "return 0;"\n', filename="t.pengu")
    assert "E0059" in str(exc_info.value) or "Syntax error" in str(exc_info.value)


def test_body_is_kept_on_the_ast_node():
    source = 'antiquus f into int:\n' + BODY
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker(base_dir=str(REPO))
    checker.check(tree, source=source, filename="t.pengu")
    from lark import Tree
    node = next(st for st in tree.iter_subtrees() if st.data == "antiquus_decl")
    assert isinstance(node, Tree)
    assert node._pengu_c_body == "return 0;"
