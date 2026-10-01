"""Regression tests for PenguScript 0.15.0 compiler audit fixes (C1-C9, I1-I10, etc.)."""

import pytest
from pathlib import Path
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_types import BaseType
from tests.conftest import (
    check_ok,
    check_error,
    compile_run,
    check_c_syntax,
    gen_bundle,
    requires_runtime,
)


# ─── C1: _int_interp_spec duplicate decorator ─────────────────────────
class TestC1_IntInterpSpecDecorator:
    def test_staticmethod_is_callable(self):
        """_int_interp_spec is a callable static method without duplicate decorator."""
        assert callable(PenguCodegen._int_interp_spec)
        spec, cast = PenguCodegen._int_interp_spec(BaseType("i64"))
        assert spec == "%lld"
        assert cast == "long long"

        spec_u, cast_u = PenguCodegen._int_interp_spec(BaseType("u64"))
        assert spec_u == "%llu"
        assert cast_u == "unsigned long long"


# ─── C2: field_access over maybe field emits payload cast ─────────────
class TestC2_FieldAccessMaybeCast:
    @requires_runtime
    def test_nested_rune_maybe_field_value_cast(self):
        """field_access on composite rune.maybe.value properly emits cast."""
        code = """
import std.spark

rune Inner:
    m as maybe int

rune Outer:
    inner as Inner

weave main into int:
    var inn as Inner with:
        set .m is some 123
    var o as Outer with:
        set .inner is inn
    if o.inner.m is present:
        var v as int is o.inner.m.value
        calling spark.println with "{v}"
    return 0
"""
        res = compile_run(code, tag="test_c2_nested")
        assert res.stdout.strip() == "123"


# ─── C3: list.push/contains/index_of evaluates argument only once ─────
class TestC3_ListArgSingleEvaluation:
    @requires_runtime
    def test_push_side_effects_once(self):
        """Calling push with an expression evaluates the expression exactly once."""
        code = """
import std.spark

weave gen into string:
    static var gen_count as int is 0
    set gen_count is gen_count + 1
    calling spark.println with "GEN CALLED"
    return "item"

weave main into int:
    var xs as list of string is list of string
    calling xs.push with (calling gen)
    return 0
"""
        res = compile_run(code, tag="test_c3_push")
        assert res.stdout.count("GEN CALLED") == 1

    @requires_runtime
    def test_contains_side_effects_once(self):
        """Calling contains with an expression evaluates the expression exactly once."""
        code = """
import std.spark

weave gen into string:
    static var gen_count as int is 0
    set gen_count is gen_count + 1
    calling spark.println with "GEN CALLED"
    return "item"

weave main into int:
    var xs as list of string is list of string
    calling xs.push with "item"
    let has is calling xs.contains with (calling gen)
    return 0
"""
        res = compile_run(code, tag="test_c3_contains")
        assert res.stdout.count("GEN CALLED") == 1


# ─── C4: Algebraic omens without derive Nexus emit cleanup helpers ────
class TestC4_AlgebraicOmenNexus:
    @requires_runtime
    def test_algebraic_omen_list_cleanup_and_clone(self):
        """Algebraic omens with heap payloads automatically emit cleanup/clone for lists."""
        code = """
import std.spark

omen Event:
    Msg with text as string

weave main into int:
    var l as list of Event is list of Event
    let ev as Event is with text is "hello"
    calling l.push with ev
    calling spark.println with "OK"
    return 0
"""
        res = compile_run(code, tag="test_c4_run")
        assert res.stdout.strip() == "OK"


# ─── C5: String-valued omen variants are typed as frozen string ───────
class TestC5_StringOmenFrozen:
    def test_banish_string_omen_variant_rejected(self):
        """String-valued omen variants cannot be banished directly or via variable."""
        from pengu_parser.pengu_errors import InvalidMemoryOpError, TypeMismatchError
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        code_banish_direct = """
omen Color with string:
    Red

weave main into void:
    banish Color.Red
"""
        p = PenguParser()
        checker = PenguChecker()
        with pytest.raises(InvalidMemoryOpError):
            checker.check(p.parse(code_banish_direct))

        code_banish_var = """
omen Color with string:
    Red

weave main into void:
    var c is Color.Red
    banish c
"""
        with pytest.raises(InvalidMemoryOpError):
            checker.check(p.parse(code_banish_var))

        code_assign_mutable = """
omen Color with string:
    Red

weave main into void:
    var s as string is Color.Red
"""
        with pytest.raises(TypeMismatchError):
            checker.check(p.parse(code_assign_mutable))

        code_valid_frozen = """
omen Color with string:
    Red

weave main into void:
    var s as frozen string is Color.Red
    var inf is Color.Red
"""
        assert checker.check(p.parse(code_valid_frozen)) == []


# ─── C6: Array passed to slice parameter wraps in PenguSlice ──────────
class TestC6_ArrayToSliceParam:
    @requires_runtime
    def test_array_variable_passed_to_slice_param(self):
        """Passing an array variable to a slice of T parameter compiles and runs."""
        code = """
weave sum with s as slice of int into int:
    let a, b, c is s
    return a + b + c

weave main into int:
    var arr as array of int with size 3 is [10, 20, 30]
    let total is calling sum with arr
    if total == 60:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_c6_var")
        assert res.returncode == 0

    @requires_runtime
    def test_array_literal_passed_to_slice_param(self):
        """Passing an array literal to a slice of T parameter compiles and runs."""
        code = """
weave sum with s as slice of int into int:
    let a, b, c is s
    return a + b + c

weave main into int:
    let total is calling sum with [5, 15, 25]
    if total == 45:
        return 0
    return 1
"""
        c = gen_bundle(code)
        check_c_syntax(c)
        res = compile_run(code, tag="test_c6_lit")
        assert res.returncode == 0


# ─── C7: for from to loops use int64_t for counter ────────────────────
class TestC7_ForRangeInt64:
    @requires_runtime
    def test_for_range_with_64bit_bounds(self):
        """for from to loop counter uses int64_t and does not overflow on 64-bit bounds."""
        code = """
weave main into int:
    var count as i64 is 0
    for i from 0 to 5000000000 step 1000000000:
        set count is count + 1
    if count == 5:
        return 0
    return 1
"""
        c = gen_bundle(code)
        assert "for (int64_t i = 0;" in c
        check_c_syntax(c)
        res = compile_run(code, tag="test_c7_run")
        assert res.returncode == 0


# ─── C8: Reject redeclaration in the same scope ───────────────────────
class TestC8_RedeclarationError:
    def test_redefinition_in_same_scope_rejected(self):
        """Redefining a variable or let in the same scope produces E0035."""
        from pengu_parser.pengu_errors import SemanticError
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        p = PenguParser()
        checker = PenguChecker()

        code_var = """
weave main into void:
    var x is 1
    var x is 2
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_var))
        assert exc_info.value.code == "E0035"

        code_let = """
weave main into void:
    let y is 1
    let y is 2
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_let))
        assert exc_info.value.code == "E0035"

        code_var_let = """
weave main into void:
    var z is 1
    let z is 2
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_var_let))
        assert exc_info.value.code == "E0035"

        code_destruct_dup = """
weave main into void:
    let a, a is [1, 2]
"""
        with pytest.raises(SemanticError) as exc_info:
            checker.check(p.parse(code_destruct_dup))
        assert exc_info.value.code == "E0035"

    def test_nested_scope_shadowing_allowed(self):
        """Shadowing in a distinct inner block scope is permitted."""
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        code = """
weave main into void:
    var x is 1
    if true:
        var x is 2
"""
        p = PenguParser()
        checker = PenguChecker()
        assert checker.check(p.parse(code)) == []

    def test_discard_identifier_multiple_allowed(self):
        """The discard identifier '_' can appear multiple times."""
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_parser import PenguParser

        code = """
weave main into void:
    var _ is 1
    var _ is 2
    let _ is 3
"""
        p = PenguParser()
        checker = PenguChecker()
        assert checker.check(p.parse(code)) == []
