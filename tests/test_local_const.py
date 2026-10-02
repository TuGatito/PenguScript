"""Tests for local const declarations with compile-time evaluation (FASE 1.5.3)."""
import pytest
from tests.conftest import check, check_error, gen_bundle, compile_run, requires_runtime


def test_local_const_integer_compiles_and_emits_enum():
    src = """
weave main into int:
    const BUFFER_SIZE is 1024
    let x is BUFFER_SIZE + 1
    return 0
"""
    check(src)
    c_code = gen_bundle(src)
    assert "enum { BUFFER_SIZE = 1024 };" in c_code


@requires_runtime
def test_local_const_arithmetic_folding():
    src = """
weave main into int:
    const A is 10
    const B is A * 2 + 5
    if B == 25:
        return 0
    return 1
"""
    check(src)
    res = compile_run(src, tag="test_fold")
    assert res.returncode == 0, res.stderr


@requires_runtime
def test_local_const_used_in_array_size():
    src = """
weave main into int:
    const SIZE is 4
    var arr as array of int with size SIZE is [1, 2, 3, 4]
    if (arr at (SIZE - 1)) == 4:
        return 0
    return 1
"""
    check(src)
    res = compile_run(src, tag="test_arr_sz")
    assert res.returncode == 0, res.stderr


@requires_runtime
def test_local_const_types():
    src = """
weave main into int:
    const FLAG is true
    const PI is 3.14
    if FLAG and PI > 3.0:
        return 0
    return 1
"""
    check(src)
    res = compile_run(src, tag="test_types")
    assert res.returncode == 0, res.stderr


def test_local_const_runtime_expr_raises_e0001():
    src = """
weave test with a as int into int:
    const X is a + 1
    return X
"""
    err = check_error(src, contains="E0001")
    assert "must be compile-time evaluable" in err


def test_local_const_call_raises_e0001():
    src = """
weave helper into int:
    return 42

weave test into int:
    const X is calling helper
    return X
"""
    check_error(src, contains="E0001")


def test_local_const_redefinition_raises_e0053():
    src = """
weave test into int:
    const X is 10
    const X is 20
    return X
"""
    check_error(src, contains="E0053")


def test_local_const_mutation_raises_e0006():
    src = """
weave test into int:
    const X is 10
    set X is 20
    return X
"""
    check_error(src, contains="E0006")


@requires_runtime
def test_local_const_e2e_execution():
    src = """
weave compute with n as int into int:
    const MULTIPLIER is 3
    const OFFSET is 7
    return n * MULTIPLIER + OFFSET

weave main into int:
    let res is calling compute with 5
    if res == 22:
        return 0
    return 1
"""
    check(src)
    res = compile_run(src, tag="test_e2e")
    assert res.returncode == 0, res.stderr
