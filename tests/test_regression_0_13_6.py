"""Regression test suite for PenguScript 0.13.6 release.

Covers:
- #1: const array with string elements is rejected with E0005 (runtime-init elements prohibited)
- #2: weave and lambda returning function pointers (FnType) generate valid C prototypes and declarators
- #3: Identifiers named NULL, bool, true, false, _Bool, wchar_t, FILE are escaped to avoid macro collisions
- #4: .value on maybe (FnType) generates valid double-pointer cast (to_c_decl(T, "*"))
- #5: judge_expr without resolved res_type emits valid C with __typeof__ and initialized _res
- #6: String interpolation on AliasType(string) and FrozenType(string) works correctly
- #7: compound set += on AliasType(string) passes checker and codegen
- #8: Duplicate const in same file does not report misleading cross-module E0046
- #9: estimate_size with None array size does not raise TypeError
- #10: String interpolation of unsupported types raises SemanticError
- #11: Consistent indentation in _translate_value_if then_prologue
- #12: ord expr evaluates argument with side-effects exactly once
"""
import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_types import ArrayType, INT_TYPE, estimate_size
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
)


def test_item1_const_string_array_rejected():
    """#1: const array of string is rejected with E0005 because it requires runtime init."""
    code = """const NAMES is ["alice", "bob"]

weave main into int:
  return 0
"""
    check_error(code, "E0005")


@requires_cc
def test_item1_const_numeric_array_accepted():
    """#1: const array of numeric/bool types remains accepted and compiles."""
    code = """const NUMS is [10, 20, 30]

weave main into int:
  if NUMS at 1 == 20:
    return 0
  return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_item1_const_num_arr")
    assert res.returncode == 0


@requires_cc
def test_item2_weave_returning_function_pointer():
    """#2: weave returning a function pointer emits valid C prototype and definition."""
    code = """weave add_one with x as int into int:
  return x + 1

weave get_adder into (weave with x as int into int):
  return add_one

weave main into int:
  let f as weave with x as int into int is calling get_adder
  if (calling f with 41) == 42:
    return 0
  return 1
"""
    c = gen_bundle(code)
    # Check that prototype has declarator inside parens, not `int32_t (*)(int32_t) get_adder`
    assert "int32_t (*)(int32_t) get_adder" not in c
    assert "(*get_adder(void))(int32_t);" in c or "(*get_adder())(int32_t);" in c
    res = compile_run(code, tag="test_item2_ret_fn_ptr")
    assert res.returncode == 0


@requires_cc
def test_item2_lambda_returning_function_pointer():
    """#2: Lambda returning a function pointer emits valid C declarator."""
    code = """weave add_one with x as int into int:
  return x + 1

weave main into int:
  let get_op as weave into (weave with x as int into int) is lambda into add_one
  let op as weave with x as int into int is calling get_op
  if (calling op with 5) == 6:
    return 0
  return 1
"""
    res = compile_run(code, tag="test_item2_lambda_ret_fn")
    assert res.returncode == 0


@requires_cc
def test_item3_protected_c_macro_identifiers():
    """#3: Variable names like NULL, bool, FILE, _Bool do not collide with C macros."""
    from pengu_parser.pengu_codegen import PenguCodegen
    assert PenguCodegen._c_ident("true") == "_true"
    assert PenguCodegen._c_ident("false") == "_false"
    assert PenguCodegen._c_ident("NULL") == "_NULL"
    assert PenguCodegen._c_ident("bool") == "_bool"
    assert PenguCodegen._c_ident("FILE") == "_FILE"

    code = """weave main into int:
  var NULL is 10
  var bool is 20
  var FILE is 50
  var _Bool is 60
  if NULL + bool + FILE + _Bool == 140:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "_NULL" in c
    assert "_bool" in c
    assert "_FILE" in c
    assert "__Bool" in c
    res = compile_run(code, tag="test_item3_macro_idents")
    assert res.returncode == 0


@requires_cc
def test_item4_maybe_fn_type_value_access():
    """#4: .value on maybe (FnType) generates valid double-pointer cast."""
    code = """weave square with x as int into int:
  return x * x

weave main into int:
  var opt as maybe (weave with x as int into int) is some square
  if opt is present:
    let fn as weave with x as int into int is opt.value
    if (calling fn with 6) == 36:
      return 0
  return 1
"""
    c = gen_bundle(code)
    # Cast must not be invalid syntax `(int32_t (*)(int32_t)*)`
    assert "(int32_t (*)(int32_t)*)" not in c
    res = compile_run(code, tag="test_item4_maybe_fn_val")
    assert res.returncode == 0


@requires_cc
def test_item5_judge_expr_untyped_res():
    """#5: judge expression with switchable cases initializes _res safely."""
    code = """weave main into int:
  var x is 2
  var res is judge x:
    when 1 -> 100
    when 2 -> 200
    else -> 0
  if res == 200:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "__auto_type _res_1;" not in c
    assert "default: break;" in c or "switch" in c
    res = compile_run(code, tag="test_item5_judge_init")
    assert res.returncode == 0


@requires_cc
def test_item6_string_interpolation_alias_and_frozen():
    """#6: String interpolation works on alias and frozen of string."""
    code = """alias MyText as string

weave main into int:
  var t as MyText is "Pengu"
  let msg is "Hello, {t}!"
  if msg == "Hello, Pengu!":
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "%.*s" in c
    assert "(int)(t).len, (t).data" in c
    res = compile_run(code, tag="test_item6_str_alias")
    assert res.returncode == 0


@requires_cc
def test_item7_compound_set_on_string_alias():
    """#7: compound set += on AliasType(string) passes checker and concatenates."""
    code = """alias MyText as string

weave main into int:
  var s as MyText is "hello"
  set s += " world"
  if s == "hello world":
    return 0
  return 1
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "pengu_string_concat" in c
    res = compile_run(code, tag="test_item7_compound_alias")
    assert res.returncode == 0


def test_item8_duplicate_const_intra_file_not_cross_module():
    """#8: Duplicate const in the same file reports E0011 redefinition, not E0046 cross-module."""
    code = """const FOO is 1
const FOO is 2

weave main into int:
  return 0
"""
    p = PenguParser()
    ast = p.parse(code)
    checker = PenguChecker(filename="test_intra.pengu")
    try:
        checker.check(ast)
        pytest.fail("Expected SemanticError")
    except Exception:
        pass
    codes = [getattr(e, "code", "") for e in checker.errors]
    assert "E0011" in codes
    assert "E0046" not in codes


def test_item9_estimate_size_none_array_size():
    """#9: estimate_size on ArrayType with size=None does not raise TypeError."""
    arr_t = ArrayType(INT_TYPE, size=None)
    sz = estimate_size(arr_t)
    assert sz == 4  # 1 * 4 bytes


def test_item10_unsupported_string_interpolation_raises():
    """#10: String interpolation of unsupported type (e.g. range or rune) raises SemanticError."""
    code = """rune Point:
  x as int
  y as int

weave main into int:
  var p as Point with:
    set .x is 1
    set .y is 2
  let s is "Point: {p}"
  return 0
"""
    with pytest.raises(Exception) as excinfo:
        gen_bundle(code)
    assert "cannot be interpolated into string" in str(excinfo.value)


@requires_cc
def test_item11_value_if_prologue_indentation():
    """#11: Value-if generates valid and readable C without broken line alignment."""
    code = """weave main into int:
  let m as maybe int is some 42
  let res is if val as int is m:
    val + 1
  else:
    0
  if res == 43:
    return 0
  return 1
"""
    res = compile_run(code, tag="test_item11_value_if_indent")
    assert res.returncode == 0


@requires_cc
def test_item12_ord_expr_evaluates_once():
    """#12: ord evaluates argument with function call side effects exactly once."""
    code = """rune Counter:
  calls as int

weave get_char with c as ref to Counter into string:
  set c->calls += 1
  return "A"

weave main into int:
  var cnt as Counter with:
    set .calls is 0
  let code is ord (calling get_char with sigil of cnt)
  if code == 65 and cnt.calls == 1:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "_ord_s" in c
    res = compile_run(code, tag="test_item12_ord_side_effects")
    assert res.returncode == 0
