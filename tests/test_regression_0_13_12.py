"""Regression tests for PenguScript 0.13.12.

Covers:
- C3: with self->node: emits -> operator in enchanting methods
- C4: destructuring on AnyType rejected with E0017 in checker
- H3: set x is calling make_big on large rune does not take & of rvalue
- M6: .ref_field.sub in with_target rejected with E0003
- M7: insignia declared in when_top_decl is scoped and does not leak outside
- m8: struct_init value expression checks propagate field-specific expected type
- m9: when_pattern bool_lit aliases true_lit and false_lit
- m11: _lookup_type_fn preserves omen variant_values and c_name
- Version: version sync across toolchain files to 0.13.12
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import (
    SemanticError, TypeMismatchError, SelfDotAccessError
)
from pengu_parser.pengu_types import (
    OmenType, STRING_TYPE, INT_TYPE, BaseType, RuneType, RefType
)
from pengu_parser.pengu_codegen import PenguCodegen, PENGU_VERSION
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_parser import PenguParser
import pengu_version


def test_version_sync_0_13_12():
    """Verify that version 0.13.12 is synced across toolchain."""
    assert pengu_version.__version__ == "0.13.12"
    assert pengu_version.FALLBACK_VERSION == "0.13.12"
    assert PENGU_VERSION == "0.13.12"
    assert pengu_version.read_version_file() == "0.13.12"


@requires_cc
def test_c3_with_self_arrow_field():
    """C3: with self->node: emits self->node->val = 42 in enchanting methods."""
    code = """rune Node:
    val as int

rune Holder:
    node as ref to Node

enchanting Holder:
    weave bump into void:
        with self->node:
            set .val is 42

weave main into int:
    var n as Node with:
        set .val is 10
    var h as Holder with:
        set .node is sigil of n
    calling h.bump
    if n.val == 42:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "self->node->val = 42;" in c
    res = compile_run(code, tag="test_c3_with_self_arrow")
    assert res.returncode == 0


def test_c4_reject_destructuring_any():
    """C4: Destructuring any type is rejected with E0017."""
    code = """weave test with x as any into void:
    let a, b is x
"""
    check_error(code, "E0017")


@requires_cc
def test_h3_set_large_rune_from_calling_expr():
    """H3: Reassignment of large rune from calling_expr does not emit &calling(...)."""
    code = """rune Big:
    a as int
    b as int
    c as int

weave make_big into Big:
    return with:
        set .a is 10
        set .b is 20
        set .c is 30

weave main into int:
    var x as Big with:
        set .a is 0
        set .b is 0
        set .c is 0
    set x is calling make_big
    if x.a == 10 and x.b == 20 and x.c == 30:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    # Must NOT take address of temporary calling expression
    assert "memcpy(&(x), &(make_big" not in c
    res = compile_run(code, tag="test_h3_large_rune_call")
    assert res.returncode == 0


def test_m6_with_target_rejects_dot_on_ref():
    """M6: .ref_field.sub in with_target is rejected with E0003."""
    code = """rune Inner:
    x as int

rune Outer:
    p as ref to Inner

weave main into int:
    var i as Inner with:
        set .x is 1
    var o as Outer with:
        set .p is sigil of i
    with o:
        set .p.x is 2
    return 0
"""
    check_error(code, "E0003")


def test_m7_insignia_does_not_leak_from_when_top_decl():
    """M7: insignia inside when_top_decl does not leak to subsequent outer declarations."""
    code = """when 1 == 1:
    insignia lnx_
    weave foo into int:
        return 1

weave bar into int:
    return 2
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker(filename="test.pengu")
    checker.check(tree, source=code)
    foo_sym = checker.symbols.lookup("foo")
    bar_sym = checker.symbols.lookup("bar")
    assert foo_sym is not None
    assert getattr(foo_sym, "c_name", "") == "lnx_foo"
    assert bar_sym is not None
    assert getattr(bar_sym, "c_name", "") in ("", "bar")


@requires_cc
def test_m8_struct_init_value_exprs_expected():
    """m8: struct_init value expressions resolve field-specific expected type."""
    code = """rune Inner:
    val as int

rune Outer:
    inner as Inner

weave main into int:
    var o as Outer with:
        set .inner is with:
            set .val is 100
    if o.inner.val == 100:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_m8_struct_init_nested")
    assert res.returncode == 0


@requires_cc
def test_m9_when_pattern_bool_lit_alias():
    """m9: judge with true/false patterns produces true_lit/false_lit and matches cleanly."""
    code = """weave judge_flag with flag as bool into int:
    return judge flag:
        when true -> 10
        when false -> 20

weave main into int:
    let r1 is calling judge_flag with true
    let r2 is calling judge_flag with false
    if r1 == 10 and r2 == 20:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_m9_judge_bool")
    assert res.returncode == 0


def test_m11_lookup_type_fn_omen():
    """m11: _lookup_type_fn on omen preserves variant_values and c_name."""
    codegen = PenguCodegen()
    codegen.omens["State"] = {"Active": {}, "Inactive": {}}
    codegen.omen_values["State"] = {"Active": 1, "Inactive": 0}
    t = codegen._lookup_type_fn("State")
    assert isinstance(t, OmenType)
    assert t.name == "State"
    assert t.c_name == "State"
    assert t.variant_values == {"Active": 1, "Inactive": 0}
