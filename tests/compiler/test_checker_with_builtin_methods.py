"""Tests for Bug 2.3: with target: on ref to list / ref to map collections."""

import pytest
from tests.conftest import (
    check_ok, gen_bundle, check_c_syntax, compile_run, requires_cc, requires_runtime
)


def test_with_ref_to_list_push():
    """Bug 2.3: with ref_to_list: calling .push with x must pass checker and codegen."""
    src = """
weave add_item with r_list as ref to list of int, val as int into void:
    with r_list:
        calling .push with val

weave main into void:
    var my_list as list of int is list of int
    calling add_item with sigil of my_list, 42
"""
    check_ok(src)
    c_code = gen_bundle(src)
    check_c_syntax(c_code)


def test_with_ref_to_map_put():
    """Bug 2.3: with ref_to_map: calling .put with k, v must pass checker and codegen."""
    src = """
weave set_entry with r_map as ref to map of string to int, k as string, v as int into void:
    with r_map:
        calling .put with k, v

weave main into void:
    var my_map as map of string to int is map of string to int
    calling set_entry with sigil of my_map, "score", 100
"""
    check_ok(src)
    c_code = gen_bundle(src)
    check_c_syntax(c_code)


@requires_cc
@requires_runtime
def test_with_ref_to_list_and_map_runtime():
    """Runtime execution of with blocks operating on ref to list and ref to map."""
    src = """
weave append_data with r_list as ref to list of int into void:
    with r_list:
        calling .push with 11
        calling .push with 22

weave main into int:
    var items as list of int is list of int
    calling append_data with sigil of items
    if items.len == 2:
        return 0
    return 1
"""
    proc = compile_run(src, tag="with_ref_rt")
    assert proc.returncode == 0
