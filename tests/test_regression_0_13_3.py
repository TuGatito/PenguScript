"""Regression test suite for PenguScript 0.13.3 release.

Covers:
- N1: break and continue within loops flush loop-scoped auto-banished variables
- N2: or: block with FnType or RefType generates valid C declarators and casts
- N3: some <FnType> generates valid C temporary declarator and heap allocation
- N4: Scoped binding with FnType (if f as weave ... is opt:) generates valid C
- N5: _c_ident protects additional C keywords (if, else, while, for, do, break, continue, asm)
- N6: set let_arr at i is v raises MutabilityError (E0006) on immutable let arrays
- N7: in_expr uses syntactic range check only as fallback when col_t is None
"""
import pytest

from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import MutabilityError, TypeMismatchError
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
)


def test_n1_break_continue_flushes_loop_auto_banish():
    """N1: break and continue flush auto-banished variables declared directly in the loop body."""
    code = """weave main into int:
  for i from 0 to 5:
    var s is "hello " + (i to string)
    if i == 2:
      continue
    if i == 4:
      break
    calling print with s
  return 0
"""
    c = gen_bundle(code)
    # Both break and continue must be preceded by pengu_banish_string(&s);
    # Verify s is cleaned up at least 3 times (continue path, break path, normal end of loop)
    assert c.count("pengu_banish_string(&s);") >= 3
    # Check that continue is directly preceded by pengu_banish_string(&s);
    idx_cont = c.find("continue;")
    assert idx_cont != -1
    assert "pengu_banish_string(&s);" in c[max(0, idx_cont - 80):idx_cont]
    # Check that break is directly preceded by pengu_banish_string(&s);
    idx_brk = c.find("break;")
    assert idx_brk != -1
    assert "pengu_banish_string(&s);" in c[max(0, idx_brk - 80):idx_brk]


@requires_cc
def test_n1_break_continue_executes_cleanly():
    """N1: Loop with continue and break executes without memory leaks or crashes."""
    code = """weave main into int:
  var count is 0
  for i from 0 to 5:
    var s is "item " + (i to string)
    if i == 1:
      continue
    if i == 3:
      break
    set count += 1
  if count == 2:
    return 0
  return 1
"""
    res = compile_run(code, tag="test_n1_loop")
    assert res.returncode == 0


@requires_cc
def test_n2_or_block_with_fn_type():
    """N2: var f as weave with ... is calling maybe_fn or: produces valid C."""
    code = """weave maybe_fn with succeed as bool into maybe (weave with x as int into int):
  if succeed:
    return some (lambda x as int into x + 1)
  return maybe none

weave main into int:
  var f as weave with x as int into int is (calling maybe_fn with true) or:
    return 1
  if (calling f with 41) == 42:
    return 0
  return 2
"""
    c = gen_bundle(code)
    assert "int32_t (*f)(int32_t)" in c
    assert "int32_t (*)(int32_t) f" not in c
    res = compile_run(code, tag="test_n2_or_fn")
    assert res.returncode == 0


@requires_cc
def test_n3_some_with_fn_type():
    """N3: some <FnType> generates valid C declaration for temporary."""
    code = """weave main into int:
  var m as maybe (weave with x as int into int) is some (lambda x as int into x + 10)
  var f as weave with x as int into int is m or:
    return 1
  if (calling f with 42) == 52:
    return 0
  return 2
"""
    c = gen_bundle(code)
    assert "(*_some" in c
    res = compile_run(code, tag="test_n3_some_fn")
    assert res.returncode == 0


@requires_cc
def test_n4_binding_if_with_fn_type():
    """N4: if f as weave ... is opt: generates valid function pointer binding."""
    code = """weave main into int:
  var opt as maybe (weave with x as int into int) is some (lambda x as int into x + 100)
  if f as weave with x as int into int is opt:
    if (calling f with 23) == 123:
      return 0
  return 1
"""
    c = gen_bundle(code)
    # The binding declaration must be valid C function pointer syntax
    assert "int32_t (*f)(int32_t) = (*(int32_t (**)(int32_t))" in c
    res = compile_run(code, tag="test_n4_binding_fn")
    assert res.returncode == 0


def test_n5_c_ident_keywords():
    """N5: _c_ident escapes C keywords including if, else, while, for, do, break, continue, asm."""
    keywords = ["if", "else", "while", "for", "do", "break", "continue", "asm"]
    for kw in keywords:
        escaped = PenguCodegen._c_ident(kw)
        assert escaped == f"_{kw}", f"Expected {kw} to be escaped to _{kw}, got {escaped}"
    assert PenguCodegen._c_ident("my_var") == "my_var"


def test_n6_mutability_let_array_at_access_rejected():
    """N6: set let_arr at i is v raises MutabilityError E0006 on immutable let bindings."""
    bad_code = """weave main into int:
  let arr as array of int with size 3 is [1, 2, 3]
  set arr at 0 is 99
  return 0
"""
    exc = check_error(bad_code, contains="E0006")
    assert "Cannot mutate element of immutable 'let' variable 'arr'" in str(exc)

    good_code = """weave main into int:
  var arr as array of int with size 3 is [1, 2, 3]
  set arr at 0 is 99
  return 0
"""
    check_ok(good_code)


def test_n7_in_expr_with_cast_not_treated_as_range():
    """N7: in_expr does not treat cast expression (10 to float) as a range."""
    # 10 to float is of type float, which is not an iterable collection or range.
    bad_code = """weave main into int:
  var x is 10.0
  if x in (10 to float):
    return 1
  return 0
"""
    check_error(bad_code, contains="E0005")
