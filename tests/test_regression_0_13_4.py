"""Regression test suite for PenguScript 0.13.4 release.

Covers:
- N10: Invalid C function-pointer declarators and casts in loop value collection, for-in, and for-comp
- N11: _check_or_block aborts error accumulation when inferrer throws SemanticError
- N12: in_expr / not_in_expr accepts (10 to float) as range
- N9: Local variables and functions named with C keywords (e.g. asm) escaped with _c_ident
- N13: Omen variant selection broken when variant or field is a C keyword
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
def test_n10_loop_as_value_function_pointers():
    """N10: Collecting function pointers via loop-as-value generates valid C declarators."""
    code = """weave double with x as int into int:
  return x * 2

weave main into int:
  var fs as list of (weave with x as int into int) is for i from 0 to 3:
    double
  var f as weave with x as int into int is fs at 0
  if (calling f with 5) == 10:
    return 0
  return 1
"""
    c = gen_bundle(code)
    # Must declare loop temporary with valid function-pointer syntax, not `int32_t (*)(int32_t) _lv`
    assert "int32_t (*)(int32_t) _lv" not in c
    res = compile_run(code, tag="test_n10_loop_val")
    assert res.returncode == 0


@requires_cc
def test_n10_for_in_over_array_of_function_pointers():
    """N10: for-in over array of function pointers produces valid C element declarators."""
    code = """weave double with x as int into int:
  return x * 2

weave main into int:
  var fs as array of (weave with x as int into int) with size 2 is [double, double]
  var total is 0
  for f in fs:
    set total += calling f with 3
  if total == 12:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "int32_t (*f)(int32_t)" in c
    assert "int32_t (*)(int32_t) f" not in c
    res = compile_run(code, tag="test_n10_for_in")
    assert res.returncode == 0


@requires_cc
def test_n10_for_comp_function_pointers():
    """N10: for-comprehension yielding function pointers generates valid C declarators."""
    code = """weave double with x as int into int:
  return x * 2

weave main into int:
  let fs is for x in [1, 2, 3] then double
  var f as weave with x as int into int is fs at 0
  if (calling f with 7) == 14:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "int32_t (*)(int32_t) _comp_val" not in c
    res = compile_run(code, tag="test_n10_for_comp")
    assert res.returncode == 0


def test_n11_or_block_error_accumulation():
    """N11: _check_or_block accumulates errors in body even if left operand fails inference."""
    code = """weave main into int:
  let x is undefined_thing or:
    let y is also_undefined
    return 0
  return 0
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    with pytest.raises(Exception) as exc_info:
        checker.check(tree, source=code)
    err = exc_info.value
    assert hasattr(err, "all_errors"), "Checker should attach all_errors on failure"
    msgs = [str(e) for e in err.all_errors]
    assert any("undefined_thing" in m for m in msgs), "Expected undefined_thing to be reported"
    assert any("also_undefined" in m for m in msgs), "Expected also_undefined to be reported"


def test_n12_in_expr_rejects_scalar_cast():
    """N12: in_expr / not_in_expr rejects scalar casts like (10 to float) as collections."""
    bad_code = """weave main into int:
  var x as float is 3.0
  if x in (10 to float):
    return 1
  return 0
"""
    check_error(bad_code, contains="E0005")

    # Valid range must still be accepted
    good_code = """weave main into int:
  var x is 5
  if x in 1 to 10:
    return 0
  return 1
"""
    check_ok(good_code)


@requires_cc
def test_n9_c_keyword_local_and_function_names():
    """N9: Functions and local variables named with C keywords (e.g. asm) compile and run."""
    code = """weave asm with x as int into int:
  return x * 3

weave main into int:
  var my_var is 10
  var res is calling asm with my_var
  var asm is 20
  if res + asm == 50:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "int32_t _asm(int32_t x)" in c or "int32_t _asm(" in c
    assert "int32_t _asm = 20;" in c
    res = compile_run(code, tag="test_n9_kw_ident")
    assert res.returncode == 0


@requires_cc
def test_n13_omen_variant_named_c_keyword():
    """N13: Omen variant named with a C keyword (e.g. asm) initializes and matches correctly."""
    code = """omen E:
  asm with x as int

weave main into int:
  var e as E is with asm is 5
  return 0
"""
    check_ok(code)
    c = gen_bundle(code)
    # Check that struct init produces valid union access
    assert ".tag = E_asm" in c
    assert ".data._asm" in c
    res = compile_run(code, tag="test_n13_omen_kw")
    assert res.returncode == 0


@requires_cc
def test_n13_omen_bare_payload_named_c_keyword():
    """N13: Omen bare payload with variant named with C keyword works without ambiguity."""
    code = """omen Status:
  asm with val as int

weave main into int:
  var s as Status is with val is 42
  return 0
"""
    check_ok(code)
    c = gen_bundle(code)
    assert ".tag = Status_asm" in c
    assert ".data._asm" in c
    res = compile_run(code, tag="test_n13_bare_omen")
    assert res.returncode == 0
