"""Tests for codegen fix: enchanting methods must not shadow top-level functions."""

import pytest
from tests.conftest import (
    check_ok, gen_bundle, check_c_syntax, compile_run, requires_cc, requires_runtime
)


def test_codegen_enchanting_method_does_not_shadow_top_level_function():
    """Verify that an enchanting method (e.g. Logger.log) does not shadow a top-level function (e.g. log)."""
    src = """
rune Counter:
    val as int

enchanting Counter:
    weave add with amount as int into int:
        return self->val + amount

weave add with a as int , b as int into int:
    return a + b

weave main into int:
    var c as Counter is with val is 10
    var r1 as int is calling c.add with 5
    var r2 as int is calling add with 20, 30
    return 0
"""
    check_ok(src)
    c_code = gen_bundle(src)
    # The method call should call Counter_add
    assert "Counter_add(" in c_code
    # The standalone function call should call add(20, 30), not Counter_add
    assert "add(20, 30)" in c_code
    check_c_syntax(c_code)


@requires_cc
@requires_runtime
def test_codegen_method_shadowing_runtime():
    """Runtime execution confirming both the enchanting method and standalone function run correctly."""
    src = """
rune Worker:
    id as int

enchanting Worker:
    weave work with step as int into int:
        return self->id * 100 + step

weave work with step as int into int:
    return 1000 + step

weave main into int:
    var w as Worker is with id is 3
    var method_res as int is calling w.work with 5
    var func_res as int is calling work with 7

    if method_res == 305 and func_res == 1007:
        return 0
    return 1
"""
    res = compile_run(src, tag="test_shadowing")
    assert res.returncode == 0
