"""Tests for Bug 1.3 & Gap 4.1: with target: blocks on list and map collections."""

import pytest
from tests.conftest import (
    check_ok, gen_bundle, check_c_syntax, compile_run, requires_cc, requires_runtime
)


def test_with_list_push_codegen():
    """Verify Bug 1.3 fix: with list_var emits pengu_list_push instead of C++ dot call."""
    src = """
weave main into void:
    var lst as list of int is list of int
    with lst:
        calling .push with 42
        calling .push with 99
"""
    check_ok(src)
    c_code = gen_bundle(src)
    assert ".push(" not in c_code
    assert "pengu_list_push(&lst," in c_code
    check_c_syntax(c_code)


def test_with_map_put_codegen():
    """Verify with map_var emits pengu_map_put instead of C++ dot call."""
    src = """
weave main into void:
    var my_map as map of string to int is map of string to int
    with my_map:
        calling .put with "first", 10
        calling .put with "second", 20
"""
    check_ok(src)
    c_code = gen_bundle(src)
    assert ".put(" not in c_code
    assert "pengu_map_put(&my_map," in c_code
    check_c_syntax(c_code)


@requires_cc
@requires_runtime
def test_with_list_and_map_runtime():
    """Runtime execution of with blocks operating on list and map."""
    src = """
weave main into int:
    var lst as list of int is list of int
    with lst:
        calling .push with 10
        calling .push with 20
        calling .push with 30

    var reg as map of string to int is map of string to int
    with reg:
        calling .put with "alpha", 100
        calling .put with "beta", 200

    if lst.len == 3 and reg.len == 2:
        return 0
    return 1
"""
    proc = compile_run(src, tag="with_coll_rt")
    assert proc.returncode == 0
