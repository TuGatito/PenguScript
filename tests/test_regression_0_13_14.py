"""Regression tests for PenguScript 0.13.14.

Covers:
- 1: Single evaluation of string interpolation expressions (no double evaluation of side effects)
- 2: Field access with . and -> and within with: blocks on frozen RuneType
- 3: No false positive E0020 on single-line return statements in if/else branches
- 4: Loop variable names that collide with C keywords are escaped with _c_ident
- 5: banish on alias of FrozenType is rejected with E0008
- 6: .d.pengu module name prefixing does not retain .d suffix
- 7: Bare array/map literals in single-line statements (simple_stmt) are rejected with E0005
- 8: Deep loop detection prevents functions with nested loops from being marked is_inline
- 9: Destructuring over FnType emits valid C function pointer declarations
- Bonus: Default values on variadic 'many' parameters are rejected with E0005
- Version: version sync across toolchain files to 0.13.14
"""

import pytest
from tests.conftest import (
    check, check_ok, check_error, gen_bundle, compile_run, requires_cc,
)
from pengu_parser.pengu_errors import (
    SemanticError, TypeMismatchError, InvalidMemoryOpError,
)
from pengu_parser.pengu_types import (
    RuneType, RefType, FrozenType, INT_TYPE, STRING_TYPE
)
from pengu_parser.pengu_codegen import PenguCodegen, PENGU_VERSION
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_parser import PenguParser
import pengu_version


def test_version_sync_0_13_14():
    """Verify that version 0.13.14+ is synced across toolchain."""
    assert tuple(map(int, pengu_version.__version__.split("."))) >= (0, 13, 14)
    assert pengu_version.FALLBACK_VERSION == pengu_version.__version__
    assert PENGU_VERSION == pengu_version.__version__
    assert pengu_version.read_version_file() == pengu_version.__version__


@requires_cc
def test_1_string_interpolation_single_eval():
    """1: String interpolation expressions evaluate side effects exactly once."""
    code = """rune Counter:
    val as int

weave inc with c as ref to Counter into string:
    set c->val is c->val + 1
    return "World"

weave main into int:
    var c as Counter with:
        set .val is 0
    var rc as ref to Counter is sigil of c
    let msg is "Hello, {calling inc with rc}!"
    if c.val != 1:
        return 1
    if msg.len != 13:
        return 2
    return 0
"""
    check_ok(code)
    res = compile_run(code, tag="test_interp_single_eval")
    assert res.returncode == 0


@requires_cc
def test_2_frozen_rune_field_and_arrow_read():
    """2: Field reading with . and -> on frozen RuneType is allowed."""
    code = """rune Point:
    x as int
    y as int

weave inspect_val with p as frozen Point into int:
    return p.x + p.y

weave inspect_ref with p as ref to frozen Point into int:
    let px is p->x
    let py is p->y
    return px + py

weave main into int:
    var pt as Point with:
        set .x is 10
        set .y is 20
    var rpt as ref to frozen Point is sigil of pt
    let v_res is calling inspect_val with pt
    let r_res is calling inspect_ref with rpt
    if (v_res == 30) and (r_res == 30):
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_frozen_read")
    assert res.returncode == 0


@requires_cc
def test_3_stmt_always_returns_single_line_alias():
    """3: _stmt_always_returns recognizes single-line return statements."""
    code = """weave classify with x as int into int:
    if x > 0: return 1
    else:
        return 2

weave main into int:
    if ((calling classify with 5) == 1) and ((calling classify with -3) == 2):
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_single_line_returns")
    assert res.returncode == 0


@requires_cc
def test_4_loop_variable_c_keyword_ident():
    """4: Loop variable names colliding with C keywords are escaped via _c_ident."""
    code = """weave main into int:
    var sum as int is 0
    for int from 0 to 5:
        set sum is sum + int
    for char in [10, 20, 30]:
        set sum is sum + char
    for i, short in [100, 200]:
        set sum is sum + i + short
    if sum == (10 + 60 + 0 + 100 + 1 + 200):
        return 0
    return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "for (int32_t _int = 0;" in c
    assert "_char" in c
    assert "_short" in c
    res = compile_run(code, tag="test_loop_c_keywords")
    assert res.returncode == 0


def test_5_banish_frozen_alias_rejected():
    """5: banish on an alias of FrozenType is rejected with E0008."""
    code = """alias FrozenInt as frozen int

weave main into int:
    var x as FrozenInt is 5
    banish x
    return 0
"""
    check_error(code, "E0008")


def test_6_d_pengu_const_prefix():
    """6: .d.pengu files extract module name without .d suffix."""
    from pengu_parser.pengu_codegen import PenguCodegen
    from pengu_parser.pengu_checker import PenguChecker
    from pengu_parser.pengu_parser import PenguParser

    header_code = """const FLAG_ACTIVE as int is 1
"""
    parser = PenguParser()
    tree = parser.parse(header_code)
    checker = PenguChecker(filename="std/raylib.d.pengu")
    checker.check(tree, source=header_code)
    cg = PenguCodegen(checker.symbols, ["std/raylib.d.pengu", "main.pengu"])
    cg.collect_declarations([("std/raylib.d.pengu", tree)])

    # Must be 'raylib_FLAG_ACTIVE', NOT 'raylib.d_FLAG_ACTIVE'
    assert "raylib_FLAG_ACTIVE" in cg.consts
    assert "raylib.d_FLAG_ACTIVE" not in cg.consts


def test_7_simple_stmt_bare_array_rejected():
    """7: Bare array/map literals in single-line statements are rejected with E0005."""
    code = """weave main into int:
    if true: [1, 2, 3]
    return 0
"""
    check_error(code, "E0005")


def test_8_nested_loop_not_inlined():
    """8: A function containing an inner loop within an if is not marked is_inline."""
    code = """weave process with n as int into int:
    var sum as int is 0
    if n > 0:
        for i from 0 to n:
            set sum is sum + i
    return sum
"""
    checker = check_ok(code)
    fn_sym = checker.symbols.lookup("process")
    assert fn_sym is not None
    assert getattr(fn_sym, "is_inline", False) is False


@requires_cc
def test_9_fntype_destructuring_valid_c():
    """9: Destructuring arrays of function pointers emits valid C99."""
    code = """weave f with x as int into int:
    return x + 1

weave g with x as int into int:
    return x * 2

weave main into int:
    var funcs as array of weave with x as int into int with size 2 is [f, g]
    let a, b is funcs
    if ((calling a with 10) == 11) and ((calling b with 10) == 20):
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_fn_destructure")
    assert res.returncode == 0


def test_bonus_many_default_rejected():
    """Bonus: Default value on variadic 'many' parameter is rejected with E0005."""
    code = """weave variadic with many items as int is [1, 2] into int:
    return 0
"""
    check_error(code, "E0005")
