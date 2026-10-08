import pytest
from tests.conftest import check_ok, check_error


def test_h2_1_bare_c_function_without_declare_fails():
    # include without declare must fail with E0004
    src = """include "stdio.h"

weave main into int:
    calling printf with "%d", 5
    return 0
"""
    check_error(src, contains=["E0004", "Function 'printf' is not declared"])


def test_h2_1_c_function_with_declare_succeeds():
    # include with explicit declare must succeed
    src = """include "stdio.h"

declare printf with fmt as ref to frozen char, ... into int

weave main into int:
    calling printf with "%d", 5
    return 0
"""
    check_ok(src)


def test_h2_2_array_lit_as_direct_scalar_arg_fails():
    # passing array literal directly to non-array/slice/many/any param must fail with E0005
    src = """weave take with x as int into void:
    return

weave main into int:
    calling take with [1, 2, 3]
    return 0
"""
    check_error(src, contains=["E0005", "Array literal cannot be passed directly"])


def test_h2_2_array_lit_as_many_or_slice_succeeds():
    # passing array literal to many or slice remains allowed
    src = """weave take_many with vals as many int into void:
    return

weave main into int:
    calling take_many with [1, 2, 3]
    return 0
"""
    check_ok(src)


def test_h2_3_many_in_declare_fails():
    # declare with many T must fail with E0005
    src = """declare f with rest as many int into void
"""
    check_error(src, contains=["E0005", "'many' parameters are not allowed in 'declare' statements"])


def test_h2_3_varargs_ellipsis_in_declare_succeeds():
    # declare with ... must succeed
    src = """declare f with fmt as ref to frozen char, ... into int
"""
    check_ok(src)
