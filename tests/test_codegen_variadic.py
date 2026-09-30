"""Tests for Bug 1.2: _build_call_args with ArrayType passed to variadic many parameter."""

import pytest
from tests.conftest import (
    check_ok, gen_bundle, check_c_syntax, compile_run, requires_cc, requires_runtime
)


def test_variadic_single_array_argument_codegen():
    """Verify Bug 1.2 fix: calling variadic function with array literal creates 1D array slice."""
    src = """
weave sum_all with xs as many int into int:
    var acc as int is 0
    for x in xs:
        set acc is acc + x
    return acc

weave main into int:
    return calling sum_all with [1, 2, 3]
"""
    check_ok(src)
    c_code = gen_bundle(src)
    # Must NOT contain nested brace array initialization: { { 1, 2, 3 } }
    assert "{ { 1, 2, 3 } }" not in c_code
    check_c_syntax(c_code)


def test_variadic_array_variable_codegen():
    """Verify calling variadic function with an existing array variable."""
    src = """
weave count_elements with items as many int into int:
    return items.len

weave main into int:
    var my_arr as array of int with size 4 is [10, 20, 30, 40]
    return calling count_elements with my_arr
"""
    check_ok(src)
    c_code = gen_bundle(src)
    check_c_syntax(c_code)


def test_variadic_single_scalar_argument_codegen():
    """Verify calling variadic function with a single scalar argument still wraps in 1-element slice."""
    src = """
weave single_elem with xs as many int into int:
    return xs.len

weave main into int:
    return calling single_elem with 42
"""
    check_ok(src)
    c_code = gen_bundle(src)
    check_c_syntax(c_code)


@requires_cc
@requires_runtime
def test_variadic_array_argument_runtime():
    """Verify runtime evaluation of variadic function called with array literal and array variable."""
    src = """
weave sum with xs as many int into int:
    var total as int is 0
    for v in xs:
        set total is total + v
    return total

weave main into int:
    let r1 as int is calling sum with [10, 20, 30]
    var numbers as array of int with size 3 is [1, 2, 3]
    let r2 as int is calling sum with numbers
    let r3 as int is calling sum with 5
    if r1 == 60 and r2 == 6 and r3 == 5:
        return 0
    return 1
"""
    proc = compile_run(src, tag="variadic_arr_rt")
    assert proc.returncode == 0
