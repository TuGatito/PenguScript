"""Tests for Bug 1.1: _translate_binding_if clean C emission without duplicate closing braces."""

import pytest
from tests.conftest import (
    check_ok, gen_bundle, check_c_syntax, compile_run, requires_cc, requires_runtime
)


def test_if_binding_statement_with_else():
    """Verify Bug 1.1 fix: if-binding with else block emits valid C without orphan closing braces."""
    src = """
weave find_val with x as maybe int into int:
    if v as int is x:
        return v
    else:
        return 0

weave main into int:
    let m as maybe int is some 42
    let n as maybe int is maybe none
    let r1 as int is calling find_val with m
    let r2 as int is calling find_val with n
    if r1 == 42 and r2 == 0:
        return 0
    return 1
"""
    check_ok(src)
    c_code = gen_bundle(src)
    # Ensure there is no separate orphaned } followed by }else {
    assert "}\n  }else {" not in c_code
    assert "} else {" in c_code
    check_c_syntax(c_code)


def test_if_binding_statement_without_else():
    """Verify if-binding without else block compiles cleanly to C."""
    src = """
weave inspect_maybe with x as maybe int into int:
    var res as int is -1
    if v as int is x:
        set res is v
    return res

weave main into int:
    let m as maybe int is some 99
    return calling inspect_maybe with m
"""
    check_ok(src)
    c_code = gen_bundle(src)
    check_c_syntax(c_code)


@requires_cc
@requires_runtime
def test_if_binding_statement_runtime():
    """Runtime execution test for if-binding with else branch."""
    src = """
weave check_opt with x as maybe int into int:
    if v as int is x:
        return v * 2
    else:
        return -5

weave main into int:
    let opt_some as maybe int is some 21
    let opt_none as maybe int is maybe none
    let a as int is calling check_opt with opt_some
    let b as int is calling check_opt with opt_none
    if a == 42 and b == -5:
        return 0
    return 1
"""
    proc = compile_run(src, tag="binding_if_rt")
    assert proc.returncode == 0
