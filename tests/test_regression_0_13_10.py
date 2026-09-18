"""Regression tests for PenguScript 0.13.10.

Covers:
- A1: with_stmt emits C block { ... } avoiding variable redefinition in C
- A2: struct_init on omen uses omen_cname for tags, compound literals, and 0-init under insignia
- M1: set_stmt rejects reassigning fixed-size array types with E0008
- M2: judge variant pattern validates omen prefix matching target omen
- M3: when_pattern retains true/false literals allowing exhaustive boolean matching
- m1: banish rejects non-lvalue expressions (such as casts) with E0008
- m2: non-void weaves ending in non-value statements (let/var/set) rejected with E0020
- m3: with_builder blocks reject arbitrary statement expressions with E0014
- m4: omen variant collisions check variant c_name under insignia with E0046
- Version: version sync across toolchain files to 0.13.10
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError
from pengu_parser.pengu_types import OmenType, STRING_TYPE, INT_TYPE, BaseType
from pengu_parser.pengu_codegen import PenguCodegen, PENGU_VERSION
import pengu_version


def test_version_sync_0_13_10():
    """Verify that version 0.13.10+ is synced across toolchain."""
    assert tuple(map(int, pengu_version.__version__.split("."))) >= (0, 13, 10)
    assert pengu_version.FALLBACK_VERSION == pengu_version.__version__
    assert PENGU_VERSION == pengu_version.__version__
    assert pengu_version.read_version_file() == pengu_version.__version__


@requires_cc
def test_a1_with_stmt_emits_c_block_no_redefinition():
    """A1: with target: emits C block { ... } allowing inner variables to shadow outer scope."""
    code = """rune Point:
    x as int
    y as int

weave main into int:
    let temp is 100
    var pt as Point with:
        set .x is 1
        set .y is 2
    with pt:
        let temp is 42
        set .x is temp
        set .y is temp * 2
    if pt.x == 42 and pt.y == 84 and temp == 100:
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    # The with block must be wrapped in { } in C
    assert "{\n" in c
    res = compile_run(code, tag="test_a1_with_block")
    assert res.returncode == 0


@requires_cc
def test_a2_struct_init_omen_with_insignia():
    """A2: struct_init on omens with insignia emits correct C type and variant names."""
    code = """insignia app_

omen Msg:
    Plain with code as int
    Data with id as int

weave main into int:
    let m1 as Msg is with Data is with id is 99
    let m2 as Msg is with code is 404
    return 0
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "app_Msg_Data" in c
    assert "(app_Msg)" in c
    res = compile_run(code, tag="test_a2_insignia_omen_init")
    assert res.returncode == 0


def test_m1_set_array_rejected():
    """M1: Reassigning an entire fixed-size array is rejected with E0008."""
    code = """weave main into int:
    var arr as int[3] is [1, 2, 3]
    set arr is [4, 5, 6]
    return 0
"""
    check_error(code, "E0008")


def test_m2_judge_qualified_pattern_rejects_unrelated_omen():
    """M2: judge variant pattern validates qualified prefix against matched omen."""
    code = """omen Color:
    Red
    Blue

omen Mood:
    Blue
    Sad

weave check_mood with m as Mood into int:
    return judge m:
        when Color.Blue -> 1
        when Mood.Sad -> 2
        else -> 0
"""
    # Color.Blue cannot be used when matching Mood
    check_error(code, "E0005")


@requires_cc
def test_m2_judge_qualified_pattern_valid():
    """M2: Valid qualified omen variant pattern compiles and runs."""
    code = """omen Mood:
    Blue
    Sad

weave check_mood with m as Mood into int:
    return judge m:
        when Mood.Blue -> 1
        when Mood.Sad -> 2
        else -> 0

weave main into int:
    let m as Mood is Mood.Blue
    let res is calling check_mood with m
    if res == 1:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_m2_valid_judge")
    assert res.returncode == 0


@requires_cc
def test_m3_when_pattern_true_false_literals():
    """M3: when_pattern supports true and false literals with full exhaustiveness."""
    code = """weave bool_to_int with b as bool into int:
    return judge b:
        when true -> 10
        when false -> 20

weave main into int:
    let r1 is calling bool_to_int with true
    let r2 is calling bool_to_int with false
    if r1 == 10 and r2 == 20:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_m3_bool_when")
    assert res.returncode == 0


def test_m1_banish_cast_rvalue_rejected():
    """m1: banish rejects non-lvalue expressions like casts with E0008."""
    code = """weave main into int:
    let s is "hello"
    banish (s to string)
    return 0
"""
    check_error(code, "E0008")


def test_m2_weave_ending_in_stmt_rejected():
    """m2: Non-void weaves ending in statement without return are rejected with E0020."""
    code = """weave calc with x as int into int:
    var y is x + 1
    set y is y * 2
"""
    check_error(code, "E0020")


def test_m3_with_builder_rejects_arbitrary_expr():
    """m3: with builder block rejects arbitrary expressions with E0014."""
    code = """rune Config:
    retries as int

weave main into int:
    var c as Config with:
        set .retries is 3
        1 + 2
    return 0
"""
    check_error(code, "E0014")


def test_m4_omen_variant_collision_with_insignia():
    """m4: Omen variant C-name collision under insignia is detected with E0046."""
    code = """insignia lib_

omen Status:
    Active
    Inactive

const lib_Status_Active as int is 1

weave main into int:
    return 0
"""
    check_error(code, "E0046")
