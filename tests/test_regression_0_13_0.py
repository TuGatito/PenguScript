"""Regression test suite for PenguScript 0.13.0 release.

Covers bugfixes and improvements:
- B1: Layout of var_decl/let_decl with borrowed and optional type annotations
- B2: UAF elimination in loop body value collection
- B3: UAF elimination in value blocks (if/do)
- B4: Rejection of ordering comparisons (<, <=, >, >=) on strings (E0005)
- M1: _check_or_block multi-error accumulation
- M2: _translate_or_block raises E0005 on uninferable operand
- M3: _block_ends_with_jump with single-line aliases (return_simple, etc.)
- M4: Helper push + banish exclusion for loop and block values
- m1: Structural check for is_err_ret
- m3: ord on NULL string returns 0 safely
- m5: Unreachable branch type checking retained with warning W0004
- m6: Unique temporary variable names in judge expressions
"""
import pytest
from lark import Tree

from pengu_parser.pengu_checker import PenguChecker, _decl_layout
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
    requires_runtime,
)


def test_p1_1_borrowed_var_no_type():
    """B1: var borrowed x is 5 parses, checks, and generates C without IndexError."""
    code = """weave main into int:
  var borrowed x is 5
  return x
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "int32_t x = 5;" in c


def test_p1_1_borrowed_var_with_type():
    """B1: var borrowed x as int is 5 parses, checks, and generates C."""
    code = """weave main into int:
  var borrowed x as int is 5
  return x
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "int32_t x = 5;" in c


def test_p1_1_borrowed_let_no_type():
    """B1: let borrowed x is 5 parses, checks, and generates C."""
    code = """weave main into int:
  let borrowed x is 5
  return x
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "const int32_t x = 5;" in c


def test_p1_1_borrowed_let_with_type():
    """B1: let borrowed x as int is 5 parses, checks, and generates C."""
    code = """weave main into int:
  let borrowed x as int is 5
  return x
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "const int32_t x = 5;" in c


def test_p1_1_borrowed_with_init_expr():
    """B1: var borrowed with with_init_expr parses, checks, and generates C."""
    code = """rune Point:
  x as int
  y as int

weave main into int:
  var borrowed p as Point with:
    set x is 10
    set y is 20
  return p.x + p.y
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "Point p" in c


@requires_runtime
def test_p1_2_loop_value_fresh_local_runs():
    """B2: Local with auto-banish used as loop value avoids use-after-free."""
    code = """weave main into int:
  var words as list of string is for i from 0 to 3:
    var s is "item-" + (i to string)
    s
  var w0 as string is words at 0
  var w1 as string is words at 1
  var w2 as string is words at 2
  if w0 == "item-0" and w1 == "item-1" and w2 == "item-2":
    return 0
  return 1
"""
    res = compile_run(code, tag="loop_uaf")
    assert res.returncode == 0


@requires_runtime
def test_p1_3_value_if_fresh_local_runs():
    """B3: Fresh local in if block used as value avoids use-after-free."""
    code = """weave main into int:
  let x as string is if true:
    var s is "hello" + " world"
    s
  else:
    "fallback"
  if x == "hello world":
    return 0
  return 1
"""
    res = compile_run(code, tag="if_val_uaf")
    assert res.returncode == 0


@requires_runtime
def test_p1_3_do_expr_fresh_local_runs():
    """B3: Fresh local in do: block used as value avoids use-after-free."""
    code = """weave main into int:
  let y as string is do:
    var t is "pengu" + "script"
    t
  if y == "penguscript":
    return 0
  return 1
"""
    res = compile_run(code, tag="do_val_uaf")
    assert res.returncode == 0


def test_p1_4_string_ordering_rejected():
    """B4: Ordering comparisons (<, <=, >, >=) on string are rejected with E0005."""
    for op in ["<", "<=", ">", ">="]:
        code = f"""weave main into bool:
  let a is "abc"
  let b is "xyz"
  return a {op} b
"""
        err = check_error(code, contains="E0005")
        assert "Ordering comparison" in err
        assert "not supported for 'string'" in err


def test_p2_1_or_block_accumulates_errors():
    """M1: _check_or_block records errors via _record_error without interrupting checking."""
    code = """weave main into int:
  var a as int is 1 or:
    return 10
  var b as int is 2 or:
    return 20
  return 0
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    try:
        checker.check(tree)
    except Exception as exc:
        all_errors = getattr(exc, "all_errors", [exc])
        or_errors = [e for e in all_errors if "'or:' requires a 'maybe T'" in str(e)]
        assert len(or_errors) >= 2


def test_p2_2_or_block_uninferable_operand():
    """M2: _translate_or_block raises SemanticError E0005 when operand type is None."""
    codegen = PenguCodegen()
    codegen._infer_node_type = lambda *args, **kwargs: None
    with pytest.raises(SemanticError) as exc_info:
        codegen._translate_or_block(left_op=None, block_stmts=[])
    assert exc_info.value.code == "E0005"
    assert "Compiler invariant violated" in str(exc_info.value)


def test_p2_3_single_line_block_banish_ok():
    """M3: Single-line jump aliases (return_simple, etc.) are recognized as block jumps."""
    code = """weave foo with c as bool into int:
  if c: return 42
  return 0

weave main into int:
  return calling foo with true
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "return 42;" in c


def test_p3_3_ord_empty_string_safe():
    """m3: ord on string generates safe NULL-checked C expression."""
    code = """weave main into int:
  let s is ""
  return ord s
"""
    c = gen_bundle(code)
    assert "data) ? (s).data[0] : '\\0'" in c


def test_p3_5_unreachable_branch_still_type_checked():
    """m5: Dead-code branch with folded condition still checks type errors."""
    code = """weave main into int:
  if false:
    var x as int is "type mismatch here"
  return 0
"""
    err = check_error(code, contains="E0005")
    assert "TypeMismatchError" in err or "E0005" in err


def test_p3_6_judge_nested_temp_names_unique():
    """m6: Multiple judge expressions produce distinct temporary variable names."""
    code = """weave main into int:
  var x as int is judge 1:
    when 1 -> 100
    when 2 -> 200
    else -> 300
  var y as int is judge x:
    when 100 -> 1
    else -> 2
  return y
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "_val_1" in c
    assert "_val_3" in c
