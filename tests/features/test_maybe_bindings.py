"""``if NAME as T is <maybe>:`` bindings: checker validation and C codegen.

The pattern used to emit ``if ((int32_t v = opt, pengu_maybe_is_present(&v)))``
— a ``PenguMaybe`` (or the presence ``bool``) assigned to the unwrapped type
inside a comma expression, which gcc rejects. It now lowers to a scoped block
that evaluates the maybe once, tests presence and declares the bound name from
``.value``.
"""

import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import gen_bundle, requires_runtime, compile_run


def compile_failure(source: str) -> PenguError:
    """Parses + type-checks ``source`` expecting a failure; returns the error."""
    tree = PenguParser().parse(source)
    with pytest.raises(PenguError) as info:
        PenguChecker(base_dir=".").check(tree, source=source, filename="t.pengu")
    return info.value


SOME_PROGRAM = """import std.spark

weave pick with opt as maybe int into int:
    if v as int is opt:
        return v + 1
    return 0

weave main into int:
    var a as maybe int is some 41
    var r as int is calling pick with a
    calling spark.println with (r to string)
    return 0
"""

NONE_PROGRAM = """import std.spark

weave pick with opt as maybe int into int:
    if v as int is opt:
        return v + 1
    else:
        return 7

weave main into int:
    var b as maybe int is maybe none
    var r as int is calling pick with b
    calling spark.println with (r to string)
    return 0
"""

PRESENT_PROGRAM = """import std.spark

weave pick with opt as maybe int into int:
    if v as int is opt is present:
        return v * 2
    return 0

weave main into int:
    var a as maybe int is some 21
    var r as int is calling pick with a
    calling spark.println with (r to string)
    return 0
"""

VALUE_PROGRAM = """import std.spark

weave pick with opt as maybe int into int:
    let r is if v as int is opt:
        v + 1
    else:
        0
    return r

weave main into int:
    var a as maybe int is some 41
    var r as int is calling pick with a
    calling spark.println with (r to string)
    return 0
"""

RUNE_PROGRAM = """import std.spark

rune Point:
    x as int
    y as int

weave sum_point with opt as maybe Point into int:
    if p as Point is opt:
        return p.x + p.y
    return 0

weave main into int:
    var a as maybe Point is some with x is 3, y is 4
    var r as int is calling sum_point with a
    calling spark.println with (r to string)
    return 0
"""


class TestMaybeBindingCodegen:
    """The emitted C evaluates the maybe once and unwraps it in the branch."""

    def test_emits_scoped_unwrap(self):
        code = gen_bundle(SOME_PROGRAM)
        assert "PenguMaybe _maybe_" in code
        assert "pengu_maybe_is_present(&_maybe_" in code
        # The invalid comma-expression shape is gone.
        assert ", pengu_maybe_is_present(" not in code
        assert "(*(" in code and ".value)" in code

    @requires_runtime
    def test_unwraps_present_value(self):
        res = compile_run(SOME_PROGRAM, tag="bind_some")
        assert "42" in res.stdout

    @requires_runtime
    def test_absent_value_takes_the_else_branch(self):
        res = compile_run(NONE_PROGRAM, tag="bind_none")
        assert "7" in res.stdout

    @requires_runtime
    def test_explicit_is_present_is_accepted(self):
        res = compile_run(PRESENT_PROGRAM, tag="bind_present")
        assert "42" in res.stdout

    @requires_runtime
    def test_value_position_binding(self):
        res = compile_run(VALUE_PROGRAM, tag="bind_value")
        assert "42" in res.stdout

    @requires_runtime
    def test_struct_value_binding(self):
        res = compile_run(RUNE_PROGRAM, tag="bind_rune")
        assert "7" in res.stdout


class TestMaybeBindingChecks:
    """The checker rejects bindings that codegen could not unwrap."""

    def test_non_maybe_operand_is_e0005(self):
        exc = compile_failure(
            "weave pick with n as int into int:\n"
            "    if v as int is n:\n"
            "        return v\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "'v' requires a maybe value, got 'int'" in str(exc)

    def test_mismatched_element_type_is_e0005(self):
        exc = compile_failure(
            "weave pick with opt as maybe int into int:\n"
            "    if v as string is opt:\n"
            "        return 1\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "'v' as 'string' from 'maybe int'" in str(exc)

    def test_is_not_present_cannot_bind(self):
        exc = compile_failure(
            "weave pick with opt as maybe int into int:\n"
            "    if v as int is opt is not present:\n"
            "        return v\n"
            "    return 0\n"
        )
        assert exc.code == "E0005"
        assert "cannot be combined with a binding" in str(exc)

    def test_binding_over_maybe_is_clean(self):
        code = gen_bundle(
            "weave pick with opt as maybe string into int:\n"
            "    if s as string is opt:\n"
            "        return 1\n"
            "    return 0\n"
        )
        assert "PenguMaybe" in code
