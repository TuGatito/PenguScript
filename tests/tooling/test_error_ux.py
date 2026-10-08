"""Diagnostics UX: the friendly ``E0000`` for the removed ``and`` separator and
the ``is present`` / ``is not present`` operand check (``E0005``).
"""

import pytest

from pengu_parser.pengu_errors import ParseError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import check_ok


def parse_failure(source: str) -> ParseError:
    """Parses ``source`` expecting a :class:`ParseError`; returns the error."""
    with pytest.raises(ParseError) as info:
        PenguParser().parse(source)
    return info.value


def compile_failure(source: str):
    """Parses + type-checks ``source`` expecting a failure; returns the error."""
    from pengu_parser.pengu_checker import PenguChecker

    tree = PenguParser().parse(source)
    with pytest.raises(Exception) as info:  # noqa: B017 - the error carries .code
        PenguChecker(base_dir=".").check(tree, source=source, filename="t.pengu")
    return info.value


class TestLegacyAndSeparatorParseError:
    """The pre-0.10.0 ``and`` separator produces an actionable ``E0000``."""

    def test_parameter_list_points_at_the_and(self):
        exc = parse_failure(
            "weave f with a as int and b as int into int:\n"
            "    return a\n"
        )
        assert exc.code == "E0000"
        message = str(exc)
        assert "'and' is no longer a separator" in message
        assert "use ','" in message
        assert "'and' at line 1, column 23" in message
        assert (exc.line, exc.col) == (1, 23)
        assert exc.help and "boolean operator" in exc.help
        assert exc.note and "CHANGELOG" in exc.note

    def test_struct_literal_field_list(self):
        exc = parse_failure(
            "weave main into int:\n"
            "    var v as Vec is with x is 1 and y is 2\n"
            "    return 0\n"
        )
        assert exc.code == "E0000"
        assert "'and' is no longer a separator" in str(exc)
        assert (exc.line, exc.col) == (2, 33)

    def test_map_of_reminds_about_to(self):
        exc = parse_failure(
            "weave main into int:\n"
            "    var m as map of int and string is null\n"
            "    return 0\n"
        )
        assert "'and' is no longer a separator" in str(exc)
        assert exc.help and "'to'" in exc.help

    def test_unrelated_error_on_the_same_line_is_not_blamed_on_and(self):
        # 'and' is still a legal separator between pure type parameters, and the
        # real problem is the missing initializer.
        exc = parse_failure(
            "weave main into int:\n"
            "    var cb as weave with x as int and y as int into int\n"
            "    return 0\n"
        )
        assert exc.code == "E0000"
        assert "no longer a separator" not in str(exc)
        assert "Syntax error" in str(exc)

    def test_and_inside_a_string_or_comment_is_ignored(self):
        exc = parse_failure(
            "weave main into int:\n"
            '    calling print with "a and b"   # a and b\n'
            "    var x as int is (\n"
            "    return 0\n"
        )
        assert "no longer a separator" not in str(exc)

    def test_boolean_and_still_parses(self):
        check_ok(
            "weave main into int:\n"
            "    if true and false:\n"
            "        return 1\n"
            "    return 0\n"
        )

    def test_lsp_diagnostic_carries_the_code_and_help(self):
        """The editor shows `[E0000]` + help instead of a Lark traceback."""
        from pengu_lsp.server import diagnostics_from_errors
        from pengu_parser.pengu_checker import PenguChecker

        source = (
            "weave main into int:\n"
            "    var v as Vec is with x is 1 and y is 2\n"
            "    return 0\n"
        )
        try:
            tree = PenguParser().parse(source)
            PenguChecker(base_dir=".").check(tree, source=source, filename="t.pengu")
        except Exception as exc:  # noqa: BLE001 - the LSP catches PenguError too
            error = exc
        else:
            raise AssertionError("expected a parse error")

        diags = diagnostics_from_errors([error], source)
        assert len(diags) == 1
        message = diags[0].message
        assert "[E0000]" in message
        assert "no longer a separator" in message
        assert "help:" in message

    def test_pure_name_list_separator_still_parses(self):
        PenguParser().parse(
            "weave f shard T and U where T: Printable and U: Printable "
            "with a as T, b as U into T:\n"
            "    return a\n"
        )


class TestIsPresentOperandCheck:
    """``is present`` only type-checks on ``maybe`` (and unresolved generics)."""

    def test_maybe_operands_are_accepted(self):
        check_ok(
            "weave main into int:\n"
            "    var m as maybe int is some 42\n"
            "    var n as maybe string is maybe none\n"
            "    if m is present and n is not present:\n"
            "        return 1\n"
            "    return 0\n"
        )

    def test_call_result_needs_parentheses(self):
        check_ok(
            "declare find with n as int into maybe int\n"
            "weave main into int:\n"
            "    if (calling find with 1) is present:\n"
            "        return 1\n"
            "    return 0\n"
        )

    def test_generic_operand_is_accepted(self):
        check_ok(
            "weave probe shard T with v as maybe T into bool:\n"
            "    return v is present\n"
        )

    @pytest.mark.parametrize("declared,value", [("int", "1"), ("string", '"x"'), ("bool", "true")])
    def test_non_maybe_operand_is_e0005(self, declared, value):
        exc = compile_failure(
            "weave main into int:\n"
            f"    var v as {declared} is {value}\n"
            "    var ok as bool is v is present\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        message = str(exc)
        assert "'is present' requires a maybe type" in message
        assert f"got '{declared}'" in message
        assert "maybe of T" in (exc.help or "")

    def test_is_not_present_reports_the_keyword(self):
        exc = compile_failure(
            "weave main into int:\n"
            "    var v as int is 0\n"
            "    var ok as bool is v is not present\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "'is not present' requires a maybe type" in str(exc)

    def test_bare_test_in_argument_position_is_rejected(self):
        # `calling find with "1" is present` applies the test to the *argument*;
        # the call-result reading needs parentheses, so both are spelled out.
        exc = compile_failure(
            "declare find with n as string into maybe int\n"
            "weave main into int:\n"
            '    if calling find with "1" is present:\n'
            "        return 1\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "Ambiguous 'is present' in the arguments of 'find'" in str(exc)
        assert "(calling find with x) is present" in (exc.help or "")
        assert "calling find with (x is present)" in (exc.help or "")


class TestWordTestsInArgumentPosition:
    """`calling f with x is true` must not silently test the last argument."""

    @pytest.mark.parametrize("keyword", ["true", "false"])
    def test_is_true_false_in_argument_position(self, keyword):
        exc = compile_failure(
            "declare find with n as int into bool\n"
            "weave main into int:\n"
            f"    if calling find with 1 is {keyword}:\n"
            "        return 1\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert f"Ambiguous 'is {keyword}' in the arguments of 'find'" in str(exc)

    def test_is_present_in_argument_position(self):
        exc = compile_failure(
            "declare find with n as int into maybe string\n"
            "weave main into int:\n"
            "    if calling find with 1 is present:\n"
            "        return 1\n"
            "    return 0\n"
        )
        assert "Ambiguous 'is present' in the arguments of 'find'" in str(exc)

    def test_parenthesised_argument_is_clean(self):
        check_ok(
            "declare find with n as int into bool\n"
            "declare print_bool with b as bool into void\n"
            "weave main into int:\n"
            "    calling print_bool with (calling find with 1)\n"
            "    calling print_bool with ((calling find with 1) is true)\n"
            "    return 0\n"
        )

    def test_call_without_arguments_is_clean(self):
        check_ok(
            "declare ready into bool\n"
            "weave main into int:\n"
            "    if calling ready is true:\n"
            "        return 1\n"
            "    return 0\n"
        )

    def test_plain_variable_is_clean(self):
        check_ok(
            "weave main with flag as bool, m as maybe int into int:\n"
            "    if flag is false and m is present:\n"
            "        return 1\n"
            "    return 0\n"
        )


class TestBareBooleanInListPositions:
    """'and'/'or' are not operands of the elements of a comma-separated list.

    The removed 0.10.0 separator must never be read silently as one boolean
    element: either it is a parse error (array/map/indented literals, parameter
    defaults) or the checker asks for an explicit parenthesis (a bare ``and``
    glued to a call with arguments or a struct literal).
    """

    def test_array_literal_requires_comma(self):
        exc = parse_failure(
            "weave main into int:\n"
            "    var a as array of int with size 2 is [1 and 2]\n"
            "    return 0\n"
        )
        assert exc.code == "E0000"
        assert "'and' is no longer a separator" in str(exc)

    def test_map_literal_requires_comma(self):
        exc = parse_failure(
            "weave main into int:\n"
            '    var m as map of string to bool is {"k": a and b}\n'
            "    return 0\n"
        )
        assert exc.code == "E0000"
        assert "'and' is no longer a separator" in str(exc)

    def test_indented_literal_requires_comma(self):
        exc = parse_failure(
            "weave main into int:\n"
            "    var a as array of int with size 2 is:\n"
            "        1 and 2\n"
            "    return 0\n"
        )
        assert exc.code == "E0000"
        assert "'and' is no longer a separator" in str(exc)

    def test_parameter_default_requires_comma(self):
        exc = parse_failure(
            "weave f with flag as bool is a and b into int:\n"
            "    return 0\n"
        )
        assert exc.code == "E0000"
        assert "'and' is no longer a separator" in str(exc)

    def test_list_literals_with_comma_or_parens_are_clean(self):
        check_ok(
            "weave main with a as bool, b as bool into int:\n"
            "    var xs as array of int with size 2 is [1, 2]\n"
            "    var ys as array of bool with size 1 is [(a and b)]\n"
            "    var m as map of string to bool is {\"both\": (a and b)}\n"
            "    return 0\n"
        )

    def test_bare_and_after_call_with_arguments_is_e0005(self):
        exc = compile_failure(
            "declare find with n as int into bool\n"
            "weave main into int:\n"
            "    var ok as bool is calling find with 1 and true\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "Ambiguous 'and' after a call with arguments" in str(exc)
        assert "'calling f with 1, 2'" in (exc.help or "")

    def test_parenthesised_call_keeps_the_boolean(self):
        check_ok(
            "declare find with n as int into bool\n"
            "weave main into int:\n"
            "    var ok as bool is (calling find with 1) and true\n"
            "    return 0\n"
        )

    def test_bare_and_after_struct_literal_is_e0005(self):
        exc = compile_failure(
            "rune Vec:\n"
            "    flag as bool\n"
            "    other as bool\n"
            "weave main with a as bool, b as bool into int:\n"
            "    var v as Vec is with flag is a and b\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "Ambiguous 'and' after a struct literal" in str(exc)

    def test_parenthesised_struct_field_keeps_the_boolean(self):
        check_ok(
            "rune Vec:\n"
            "    flag as bool\n"
            "weave main with a as bool, b as bool into int:\n"
            "    var v as Vec is with flag is (a and b)\n"
            "    return 0\n"
        )

    def test_or_is_covered_too(self):
        exc = compile_failure(
            "declare find with n as int into bool\n"
            "weave main into int:\n"
            "    var ok as bool is calling find with 1 or true\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "Ambiguous 'or' after a call with arguments" in str(exc)

    def test_conditions_and_initialisers_still_allow_bare_and(self):
        check_ok(
            "weave main with a as bool, b as bool into int:\n"
            "    var ok as bool is a and b\n"
            "    if ok or a and b:\n"
            "        return 1\n"
            "    return 0\n"
        )

