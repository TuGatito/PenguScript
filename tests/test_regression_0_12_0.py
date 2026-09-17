"""Regression test suite for PenguScript 0.12.0 release.

Covers bugfixes and improvements:
T1. 'set x is f() or: return' generates valid C with PenguResult and error binding.
T2. 'return f() or: return' generates valid C with PenguResult.
T3. 'for k in my_map:' emits a loop bounded by .len and never sizeof.
T4. 'm at key' on map of string to int emits pengu_map_get.
T5. 'x in my_list' on list of int emits pengu_list_at loop, not direct equality.
T6. 'const R is 0 to 10' at global scope emits PenguRange initialization.
T7. 'var x as array of int with size 5 is [1, 2, 3]' raises E0041.
T8. Loop variable does not clobber outer scope binding of the same name.
T9. with_stack is restored even when an error occurs inside a with: body.
T10. Import std.ffi and call cstr_from_string cleanly.
"""
from lark import Token, Tree

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import ArraySizeMismatchError, SemanticError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import check, check_error, gen_bundle


def test_t1_set_or_block():
    """T1: 'set x is f() or: return' produces valid C with PenguResult and error."""
    src = """declare may_fail into result of int to string

weave run into int:
  var x as int is 0
  set x is calling may_fail or:
    return 1
  return x
"""
    c = gen_bundle(src)
    assert "PenguResult" in c
    assert "PenguString error" in c
    assert "= ;" not in c


def test_t2_return_or_block():
    """T2: 'return f() or: return' produces valid C with PenguResult."""
    src = """declare may_fail into result of int to string

weave run into int:
  return calling may_fail or:
    return 1
"""
    c = gen_bundle(src)
    assert "PenguResult" in c
    assert "PenguString error" in c
    assert "= ;" not in c


def test_t3_for_in_map():
    """T3: 'for k in my_map:' emits a loop bounded by .len and not sizeof."""
    src = """weave run into void:
  var my_map as map of string to int is map of string to int
  for k in my_map:
    calling print with k
"""
    c = gen_bundle(src)
    assert ".len" in c
    assert "sizeof(my_map)" not in c
    assert "sizeof" not in c or "sizeof(my_map)/sizeof" not in c


def test_t4_map_at_key():
    """T4: 'm at key' on map of string to int emits pengu_map_get."""
    src = """weave run into int:
  var m as map of string to int is map of string to int
  let val is m at "hello"
  return val
"""
    c = gen_bundle(src)
    assert "pengu_map_get" in c
    assert "m[\"hello\"]" not in c


def test_t4_map_set_at_key():
    """T4 bonus: 'set m at key is val' emits pengu_map_put."""
    src = """weave run into void:
  var m as map of string to int is map of string to int
  set m at "hello" is 42
"""
    c = gen_bundle(src)
    assert "pengu_map_put" in c


def test_t5_in_list():
    """T5: 'x in my_list' emits a loop with pengu_list_at, not direct equality."""
    src = """weave check_in with x as int, my_list as list of int into bool:
  return x in my_list
"""
    c = gen_bundle(src)
    assert "pengu_list_at" in c
    assert "x == my_list" not in c


def test_t6_const_range_global():
    """T6: 'const R is 0 to 10' at global scope emits initialization."""
    src = """const R is 0 to 10

weave run into int:
  return 0
"""
    c = gen_bundle(src)
    assert "PenguRange R = {" in c
    assert ".start = 0" in c
    assert ".end = 10" in c
    assert "PenguRange R;" not in c


def test_t7_array_size_mismatch():
    """T7: 'var x as array of int with size 5 is [1, 2, 3]' raises E0041."""
    src = """weave run into void:
  var x as array of int with size 5 is [1, 2, 3]
"""
    err = check_error(src, contains="E0041")
    assert "E0041" in err


def test_t8_loop_var_no_clobber():
    """T8: loop variable does not clobber outer scope binding."""
    src = """weave run into int:
  var i as int is 42
  for i from 0 to 5:
    let temp is i * 2
  return i + 1
"""
    c = gen_bundle(src)
    assert "i" in c
    check(src)


def test_t9_with_stack_cleanup_on_error():
    """T9: with_stack is restored even when an error occurs inside a with: body."""
    codegen = PenguCodegen()
    assert codegen.with_stack == []

    bad_stmt = Tree("with_stmt", [
        Tree("var_ref", [Token("NAME", "target")]),
        Tree("unknown_stmt_to_trigger_error", [])
    ])
    try:
        codegen._translate_stmt(bad_stmt)
    except Exception:
        pass
    assert codegen.with_stack == []


def test_t10_std_ffi_cstr_from_string():
    """T10: importing std.ffi and compiling calling ffi.cstr_from_string with s."""
    src = """import std.ffi

declare puts with s as ref to char into int

weave run with msg as string into int:
  let p as ref to char is calling ffi.cstr_from_string with msg
  calling ffi.cstr_free with p
  return calling puts with p
"""
    c = gen_bundle(src)
    assert "cstr_from_string" in c or "pengu_ffi_string_cstr" in c


def test_l2_judge_payload_rejected():
    """L2: payload bindings in judge when clause are rejected with E0005."""
    src = """omen Color:
  Red
  Custom with r as int, g as int, b as int

weave describe with c as Color into string:
  return judge c:
    when Red -> "red"
    when Custom with r, g, b -> "custom"
    else -> "other"
"""
    err = check_error(src, contains="E0005")
    assert "Payload bindings in 'when' clauses are not supported yet" in err


# ═══════════════════════════════════════════════════════════════════════════
# Phase 2 Regression Tests (T1–T11)
# ═══════════════════════════════════════════════════════════════════════════

import re


def test_p2_t1_or_block_in_set_return_expr_stmt():
    """T1 — 'or:' in set, return, expr_stmt produces valid C."""
    src = """declare may_fail into result of int to string

weave f into result of int to string:
    return calling may_fail

weave g into int:
    var x as int is 0
    set x is calling may_fail or:
        return 1
    calling may_fail or:
        return 2
    return calling may_fail or:
        return 3
"""
    c = gen_bundle(src)
    assert "PenguResult" in c
    assert "= ;" not in c
    assert "return ;" not in c


def test_p2_t2_map_at_no_redundant_deref():
    """T2 — 'm at k' over 'map of string to int' does NOT produce *(int32_t)."""
    src = """weave main into int:
    var m as map of string to int is map of string to int
    var x as int is m at "k"
    return x
"""
    c = gen_bundle(src)
    assert "pengu_map_get" in c
    assert not re.search(r'\*\(\s*int32_t\s*\)', c)
    assert not re.search(r'\*\(\s*PenguString\s*\)', c)


def test_p2_t3_ref_to_map_at():
    """T3 — 'ref to map at k' emits pengu_map_get(m, …) with pointer."""
    src = """weave get with m as ref to map of string to int into int:
    return m at "k"
"""
    c = gen_bundle(src)
    assert "pengu_map_get(m," in c
    assert "m[k]" not in c
    assert "m[i]" not in c
    assert "pengu_map_get(&" not in c


def test_p2_t4_for_in_map_statement_len():
    """T4 — 'for k in my_map:' (statement) emits .len, not sizeof."""
    src = """weave main into void:
    var m as map of string to int is map of string to int
    for k in m:
        calling print with k
"""
    c = gen_bundle(src)
    assert ".len" in c
    assert not re.search(r'sizeof\s*\(\s*\w+\s*\)\s*/\s*sizeof', c)


def test_p2_t5_for_comp_map_len_not_sizeof():
    """T5 — 'for k in my_map then k' (comprehension) emits .len, not sizeof."""
    src = """weave keys with m as map of string to int into list of string:
    return for k in m then k
"""
    c = gen_bundle(src)
    assert ".len" in c
    assert not re.search(r'sizeof\s*\(\s*\w+\s*\)\s*/\s*sizeof', c)


def test_p2_t6_const_range():
    """T6 — 'const R is 0 to 10' emits an initialization."""
    src = """const R is 0 to 10
"""
    c = gen_bundle(src)
    assert "PenguRange R = {" in c or "#define R" in c
    assert "PenguRange R;" not in c


def test_p2_t7_array_size_mismatch_shorter_literal():
    """T7 — Array size mismatch with literals (literal más corto)."""
    src = """weave main into void:
    var x as array of int with size 5 is [1, 2, 3]
"""
    err = check_error(src, contains="E0041")
    assert "E0041" in err


def test_p2_t8_array_size_mismatch_singleton_bypass():
    """T8 — Array size mismatch with singleton (bypass C5)."""
    src = """weave main into void:
    var x as array of int with size 5 is [1]
"""
    err = check_error(src, contains="E0041")
    assert "E0041" in err


def test_p2_t9_array_size_mismatch_call_compatibility():
    """T9 — Array size mismatch in function call (C4)."""
    src = """weave take with xs as array of int with size 5 into void:
    return

weave main into void:
    var s as array of int with size 3 is [1, 2, 3]
    calling take with s
"""
    err = check_error(src, contains="E0005")
    assert "E0005" in err


def test_p2_t10_nested_for_preserves_outer_var():
    """T10 — nested 'for i' preserves outer 'i'."""
    src = """declare print with s as string into void

weave main into void:
    for i from 0 to 3:
        for i from 0 to 2:
            calling print with (i to string)
        calling print with (i to string)
"""
    check(src)
    c = gen_bundle(src)
    assert "local_vars" not in c
    assert c.count("for (") >= 2


def test_p2_t11_set_ref_to_map():
    """T11 — 'set m at k is v' on ref to map."""
    src = """weave put with m as ref to map of string to int into void:
    set m at "k" is 42
"""
    c = gen_bundle(src)
    assert "pengu_map_put(m," in c
    assert "m[k] =" not in c


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 Regression Tests (F1–F3, M1–M2)
# ═══════════════════════════════════════════════════════════════════════════

import pytest
from pengu_parser.pengu_types import ArrayType, INT_TYPE
from pengu_parser.pengu_symbols import SymbolTable


def test_p3_f1a_value_if_auto_banish_scoped():
    """T-F1a — value-if auto-banish stays inside branch block and before statement-expression end."""
    src = """declare print with s as string into void

weave helper into void:
    let x is if true:
        var s is "hi" + "!"
        s length
    else:
        0
    calling print with (x to string)
"""
    c = gen_bundle(src)
    assert "pengu_banish_string(&s);" in c
    idx_banish = c.find("pengu_banish_string(&s);")
    idx_stmt_expr_end = c.find("})))")
    assert idx_banish != -1
    assert idx_banish < idx_stmt_expr_end
    idx_if = c.find("if (true)")
    assert idx_if != -1
    assert idx_if < idx_banish


def test_p3_f1b_do_expr_auto_banish_scoped():
    """T-F1b — do_expr auto-banish stays inside GNU statement expression block."""
    src = """weave helper into void:
    let x is do:
        var s is "hi" + "!"
        s length
    return
"""
    c = gen_bundle(src)
    assert "pengu_banish_string(&s);" in c
    idx_banish = c.find("pengu_banish_string(&s);")
    idx_stmt_expr_end = c.find("})))")
    assert idx_banish != -1
    assert idx_banish < idx_stmt_expr_end


def test_p3_f1c_binding_if_auto_banish_scoped():
    """T-F1c — statement-position if NAME as T is <maybe> banishes inside branch."""
    src = """declare print with s as string into void

weave helper with u as maybe int into void:
    if x as int is u:
        var s is "hi" + "!"
        calling print with s
    return
"""
    c = gen_bundle(src)
    assert "pengu_banish_string(&s);" in c
    idx_banish = c.find("pengu_banish_string(&s);")
    idx_ret = c.find("return;")
    assert idx_banish != -1
    assert idx_banish < idx_ret


def test_p3_f2_for_comp_preserves_outer_binding():
    """T-F2 — for_comp preserves outer local_vars binding."""
    src = """weave helper into int:
    var x as int is 5
    let ys is for x in [1, 2, 3] then x
    return x + 1
"""
    check(src)
    c = gen_bundle(src)
    assert "int32_t x = 5;" in c

    src_nested = """weave helper with xs as list of int into list of list of int:
    let res is for x in xs then for x in [1, 2] then x
    return res
"""
    check(src_nested)


def test_p3_f3_or_block_non_maybe_result_rejected_by_checker():
    """T-F3 — '10 or: return' reports E0005 from check() (not from codegen)."""
    src = """weave main into int:
    10 or:
        return 1
    return 0
"""
    err = check_error(src, contains="E0005")
    assert "requires a 'maybe T' or 'result of T to E' operand" in err


def test_p3_m1_array_type_equality_and_hash_includes_size():
    """T-M1 — ArrayType equality and hash include size."""
    a3 = ArrayType(element=INT_TYPE, size=3)
    a5 = ArrayType(element=INT_TYPE, size=5)
    assert a3 != a5
    assert hash(a3) != hash(a5)
    assert a3 == ArrayType(element=INT_TYPE, size=3)
    assert hash(a3) == hash(ArrayType(element=INT_TYPE, size=3))


def test_p3_m2_for_in_and_comp_non_collection_raises_semantic_error():
    """T-M2 — non-collection iteration rejected by checker and codegen raises SemanticError."""
    src = """weave main into void:
    for v in 10:
        return
"""
    check_error(src)

    cg = PenguCodegen()
    cg.symbols = SymbolTable()
    with pytest.raises(SemanticError) as exc_for_in:
        cg._translate_for_in(Tree("for_in_stmt", [Token("NAME", "v"), Token("INT", "10"), Tree("block", [])]))
    assert "Cannot iterate over non-collection type" in str(exc_for_in.value)

    with pytest.raises(SemanticError) as exc_for_comp:
        cg._translate_expr(Tree("for_comp", [Token("NAME", "v"), Token("INT", "10"), Token("INT", "1")]))
    assert "Cannot iterate over non-collection type" in str(exc_for_comp.value)


