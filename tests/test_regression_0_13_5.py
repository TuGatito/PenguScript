"""Regression test suite for PenguScript 0.13.5 release.

Covers:
- #1: _translate_for_range step_node detection unified with checker
- #2: Descending for-range loops (negative step) supported and zero-step rejected (E0042)
- #3: judge_expr returning function pointers (FnType) generates valid C declarators
- #5: with_stack reading/setting fields on ref to Rune emits pointer arrow (->)
- #7: string_lit interpolation emits %.*s with explicit length specifier
- #8: const with array literal generates static const array and const map is rejected (E0005)
- #10: No duplicate E0014 on var/let with_init_expr without type annotation
- #14: map indexed access with FnType value generates valid C declarators
"""
import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
)


@requires_cc
def test_item1_for_range_step_ast_consistency():
    """#1: for-range loop without step and with step both compile and execute correctly."""
    code = """weave main into int:
  var sum1 is 0
  for i from 0 to 5:
    set sum1 += i
  var sum2 is 0
  for j from 0 to 6 step 2:
    set sum2 += j
  if sum1 == 10 and sum2 == 6:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "for (int32_t i = 0; i < 5; i++)" in c
    assert "for (int32_t j = 0; j < 6; j += 2)" in c
    res = compile_run(code, tag="test_item1_for_step")
    assert res.returncode == 0


@requires_cc
def test_item2_descending_for_range_executes():
    """#2: Descending for-range with negative step compiles and executes correctly."""
    code = """weave main into int:
  var acc is 0
  for i from 5 to 0 step -1:
    set acc += i
  var acc2 is 0
  for j from 10 to 0 step -2:
    set acc2 += j
  if acc == 15 and acc2 == 30:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "for (int32_t i = 5; i > 0; i--)" in c
    assert "for (int32_t j = 10; j > 0; j += -2)" in c
    res = compile_run(code, tag="test_item2_desc_loop")
    assert res.returncode == 0


def test_item2_for_range_zero_step_rejected():
    """#2: for-range with step 0 is rejected with E0042."""
    code = """weave main into int:
  for i from 0 to 5 step 0:
    calling print with i
  return 0
"""
    check_error(code, "E0042")


def test_item2_descending_inverted_bounds_rejected():
    """#2: for-range with start < end and negative step is rejected with E0042."""
    code = """weave main into int:
  for i from 0 to 5 step -1:
    calling print with i
  return 0
"""
    check_error(code, "E0042")


@requires_cc
def test_item3_judge_expr_fn_type_result():
    """#3: judge expression returning function pointer generates valid C declarators."""
    code = """weave double with x as int into int:
  return x * 2

weave triple with x as int into int:
  return x * 3

weave main into int:
  let mode is 1
  let f as weave with x as int into int is judge mode:
    when 1 -> double
    when 2 -> triple
    else -> double
  if (calling f with 4) == 8:
    return 0
  return 1
"""
    c = gen_bundle(code)
    # Must NOT emit invalid C like `int32_t (*)(int32_t) _res;`
    assert "int32_t (*)(int32_t) _res" not in c
    assert "(*_res_" in c
    res = compile_run(code, tag="test_item3_judge_fn")
    assert res.returncode == 0


@requires_cc
def test_item5_with_stack_ref_type_arrow_access():
    """#5: Accessing fields on ref to Rune inside with-block emits arrow (->)."""
    code = """rune Point:
  x as int
  y as int

weave main into int:
  var p as Point with:
    set .x is 10
    set .y is 20
  var rp as ref to Point is sigil of p
  with rp:
    set .x is 42
  if p.x == 42:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "rp->x = 42;" in c
    assert "rp.x = 42;" not in c
    res = compile_run(code, tag="test_item5_with_ref")
    assert res.returncode == 0


@requires_cc
def test_item7_string_interpolation_length_specifier():
    """#7: String interpolation emits %.*s with length and data pointer."""
    code = """weave main into int:
  let name as string is "Pengu"
  let greeting is "Hello, {name}!"
  if greeting == "Hello, Pengu!":
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "%.*s" in c
    assert "(int)(name).len, (name).data" in c
    res = compile_run(code, tag="test_item7_str_fmt")
    assert res.returncode == 0


@requires_cc
def test_item8_const_array_literal_codegen():
    """#8: const with array literal emits static const array and works at runtime."""
    code = """const PRIMES is [2, 3, 5, 7, 11]

weave main into int:
  if PRIMES at 0 == 2 and PRIMES at 4 == 11:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "static const int32_t PRIMES[5] = { 2, 3, 5, 7, 11 };" in c
    assert "void PRIMES;" not in c
    res = compile_run(code, tag="test_item8_const_arr")
    assert res.returncode == 0


def test_item8_const_map_rejected():
    """#8: const with map literal is rejected with E0005 (requires dynamic allocation)."""
    code = """const CONFIG as map of string to int is:
  "port": 8080

weave main into int:
  return 0
"""
    check_error(code, "E0005")


def test_item10_no_duplicate_e0014_on_with_init():
    """#10: Missing type annotation on with: builder emits exactly one E0014 error."""
    code = """weave main into int:
  var p with:
    set .x is 10
  return 0
"""
    p = PenguParser()
    ast = p.parse(code)
    checker = PenguChecker(filename="test.pengu")
    try:
        checker.check(ast)
        pytest.fail("Expected SemanticError")
    except Exception:
        pass
    e0014_errors = [e for e in checker.errors if getattr(e, "code", "") == "E0014"]
    assert len(e0014_errors) == 1, f"Expected 1 E0014 error, got {len(e0014_errors)}"


@requires_cc
def test_item14_map_fn_type_value_access():
    """#14: Map containing function pointer values generates valid C on indexed access."""
    code = """weave double with x as int into int:
  return x * 2

weave main into int:
  var ops as map of string to (weave with x as int into int) is:
    "dbl": double
  let f as weave with x as int into int is ops at "dbl"
  if (calling f with 7) == 14:
    return 0
  return 1
"""
    c = gen_bundle(code)
    # Must emit valid cast and declarator, not `int32_t (*)(int32_t)* _p`
    assert "int32_t (*)(int32_t)*" not in c
    res = compile_run(code, tag="test_item14_map_fn")
    assert res.returncode == 0
