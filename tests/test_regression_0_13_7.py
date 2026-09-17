"""Regression test suite for PenguScript 0.13.7 release.

Covers:
- #1: User type names colliding with C reserved keywords/macros are rejected with E0035.
- #2: judge_expr on int/enum evaluates else_val lazily only if no when clause matches.
- #3: chr_expr is marked as fresh heap expr enabling auto-banish on scope exit.
- #4: SealType(string) += rejects string operand to enforce nominal typing.
- #5: _check_const_decl accepts static non-heap composite types (including algebraic omens).
- #6: _check_const_decl recognizes ref to frozen char and aliased char pointers.
- #7: String interpolation handles AliasType(ref to char), ref to byte, and SealType(char).
- #8: _is_string_expr uses .is_string() supporting AliasType(string).
- #9: _c_ident collision detection rejects fields with clashing C identifiers with E0035.
- #10: _check_weave_decl captures all statement types robustly.
- #11: weave main return type is validated to only allow integers or void (E0020).
- #12: Interpolated digit literals are cast to (int32_t).
- #13: Range loop index variable is typed as int32_t in C codegen.
"""
import pytest

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_types import ArrayType, INT_TYPE, STRING_TYPE
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
)


def test_item1_reserved_c_type_names_rejected():
    """#1: Types named after C reserved keywords or macros are rejected with E0035."""
    # Rune named 'int'
    code_rune = """rune int:
    x as i32

weave main into int:
    return 0
"""
    check_error(code_rune, "E0035")

    # Omen named 'NULL'
    code_omen = """omen NULL:
    A
    B

weave main into int:
    return 0
"""
    check_error(code_omen, "E0035")

    # Alias named 'FILE'
    code_alias = """alias FILE as i32

weave main into int:
    return 0
"""
    check_error(code_alias, "E0035")

    # Seal named 'bool'
    code_seal = """seal bool as i32

weave main into int:
    return 0
"""
    check_error(code_seal, "E0035")


@requires_cc
def test_item2_judge_lazy_else_evaluation():
    """#2: judge on int evaluates else_val lazily (not evaluated if a when matches)."""
    code = """weave side_effect_counter with inc as int into int:
    static var count as int is 0
    set count += inc
    return count

weave trigger_side_effect into int:
    return calling side_effect_counter with 1

weave evaluate_judge with x as int into int:
    return judge x:
        when 1 -> 10
        when 2 -> 20
        else -> calling trigger_side_effect

weave main into int:
    let r1 is calling evaluate_judge with 1
    let r2 is calling evaluate_judge with 2
    if r1 != 10 or r2 != 20:
        return 1
    # Side effects must still be 0 because both calls matched when branches!
    let current_effects is calling side_effect_counter with 0
    if current_effects != 0:
        return 2

    # Now call with unmatched value, triggering else
    let r3 is calling evaluate_judge with 99
    let after_effects is calling side_effect_counter with 0
    if r3 != 1 or after_effects != 1:
        return 3

    return 0
"""
    res = compile_run(code, tag="test_item2_judge_lazy_else")
    assert res.returncode == 0


def test_item3_chr_auto_banish_fresh_heap():
    """#3: chr_expr is marked as fresh heap expression so its variable is auto-banished."""
    code = """weave main into int:
    var s as string is chr 65
    return 0
"""
    tree = PenguParser().parse(code)
    checker = PenguChecker()
    errs = checker.check(tree)
    assert not errs
    main_scope = next(s for s in checker.symbols.all_scopes if s.kind == "weave")
    s_sym = main_scope.lookup("s")
    assert s_sym is not None
    assert s_sym.is_auto_banished is True


@requires_cc
def test_item3_chr_compilation_and_execution():
    """#3: Code using chr runs, properly compares, and manages heap memory via auto-banish."""
    code = """weave main into int:
    var s as string is chr 65
    if s == "A":
        return 0
    return 1
"""
    res = compile_run(code, tag="test_item3_chr_run")
    assert res.returncode == 0


def test_item4_seal_string_compound_assignment_rejected():
    """#4: Compound assignment '+=' on SealType(string) is rejected to enforce nominal typing."""
    code = """seal Handle as string

weave main into int:
    var h as Handle is "handle"
    set h += "extra"
    return 0
"""
    check_error(code, "E0005")


@requires_cc
def test_item5_const_array_algebraic_omen():
    """#5: const array of non-heap algebraic omen is accepted and compiles."""
    code = """omen Msg:
    Ping
    Pong with ts as i64

const MSGS as array of Msg with size 2 is [Ping, Ping]

weave main into int:
    let r is judge MSGS at 0:
        when Ping -> 0
        else -> 1
    return r
"""
    check_ok(code)
    res = compile_run(code, tag="test_item5_const_omen")
    assert res.returncode == 0


@requires_cc
def test_item6_const_array_ref_frozen_char():
    """#6: const array with 'ref to frozen char' element type is accepted and compiles."""
    code = """const WORDS as array of ref to frozen char with size 2 is ["hello", "world"]

weave main into int:
    let first as ref to frozen char is WORDS at 0
    return 0
"""
    check_ok(code)
    res = compile_run(code, tag="test_item6_const_ref_frozen_char")
    assert res.returncode == 0


@requires_cc
def test_item7_string_interpolation_alias_ref_char():
    """#7: String interpolation supports AliasType(ref to char) and byte."""
    code = """alias CStr as ref to char
alias Byte as byte

weave main into int:
    let p as CStr is "pengu"
    let b as Byte is 'Z'
    let s is "cstr: {p}, byte: {b}"
    if s == "cstr: pengu, byte: Z":
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_item7_str_interp_alias")
    assert res.returncode == 0


@requires_cc
def test_item8_is_string_expr_alias_support():
    """#8: _is_string_expr uses .is_string() to support AliasType(string)."""
    code = """alias MyStr as string

weave greet with name as MyStr into MyStr:
    return "Hello, " + name

weave main into int:
    let user as MyStr is "Pengu"
    let greeting is calling greet with user
    if greeting == "Hello, Pengu":
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_item8_alias_str_expr")
    assert res.returncode == 0


def test_item9_c_ident_collision_detection():
    """#9: Fields that collide after C identifier escaping are rejected with E0035."""
    code = """rune BadRune:
    FILE as i32
    _FILE as i32

weave main into int:
    return 0
"""
    check_error(code, "E0035")


@requires_cc
def test_item10_weave_statement_whitelist_robustness():
    """#10: Diverse statement types (banish, static var, loops) are captured cleanly in weave."""
    code = """weave compute with n as int into int:
    static var count as int is 0
    set count += 1
    var s as string is "temp" + ""
    defer banish s
    return count + n

weave main into int:
    let a is calling compute with 5
    let b is calling compute with 5
    if a == 6 and b == 7:
        return 0
    return 1
"""
    check_ok(code)
    res = compile_run(code, tag="test_item10_weave_stmts")
    assert res.returncode == 0


def test_item11_main_return_type_validation():
    """#11: weave main return type must be integer or void; other types rejected with E0020."""
    # Returning a function pointer
    code_fn = """weave main into (weave with x as int into int):
    return lambda with x as int into int -> x
"""
    check_error(code_fn, "E0020")

    # Returning string
    code_str = """weave main into string:
    return "hello"
"""
    check_error(code_str, "E0020")

    # Valid int / void forms
    check_ok("""weave main into int:\n    return 0\n""")
    check_ok("""weave main into void:\n    return\n""")
    check_ok("""weave main:\n    return\n""")


@requires_cc
def test_item12_string_interpolation_digit_cast():
    """#12: Interpolated digit literals are cast to (int32_t) in generated C."""
    code = """weave main into int:
    let s is "value: {42}"
    if s == "value: 42":
        return 0
    return 1
"""
    c = gen_bundle(code)
    assert "(int32_t)(42)" in c
    res = compile_run(code, tag="test_item12_digit_cast")
    assert res.returncode == 0


@requires_cc
def test_item13_for_in_range_index_int32():
    """#13: for i, v in range declares i as int32_t."""
    code = """weave main into int:
    var sum_idx as int is 0
    for i, v in 0 to 5:
        set sum_idx += i
    if sum_idx == 10:
        return 0
    return 1
"""
    c = gen_bundle(code)
    assert "int32_t i = 0;" in c
    res = compile_run(code, tag="test_item13_range_idx_i32")
    assert res.returncode == 0
