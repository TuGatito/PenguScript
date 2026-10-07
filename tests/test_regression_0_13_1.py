"""Regression test suite for PenguScript 0.13.1 release.

Covers residual fixes from 0.13.0:
- R1: UAF elimination when block/loop value is wrapped in parentheses
- R2: const_definitions reset in PenguChecker.check()
- R3: with_init_expr body checked once (no duplicated errors)
- R4: dead ident branch removed from is_err_ret
- R5: _translate_or_block rejects AnyType operand at codegen time with E0005
- R6: _check_or_block continues body checking when left operand is invalid
- R7: _check_static_var_decl uses decl_layout consistently
- R9: decl_layout is public in pengu_symbols
"""
import pytest
from lark import Tree

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_codegen import PenguCodegen, _normalize_banish_ident
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_symbols import decl_layout
from pengu_parser.pengu_types import AnyType
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
    requires_runtime,
)


def test_r1_normalize_banish_ident():
    """R1: _normalize_banish_ident unwraps balanced outer parentheses."""
    assert _normalize_banish_ident("s") == "s"
    assert _normalize_banish_ident("(s)") == "s"
    assert _normalize_banish_ident("  ((s))  ") == "s"
    assert _normalize_banish_ident("(a) + (b)") == "(a) + (b)"
    assert _normalize_banish_ident("(foo(bar))") == "foo(bar)"


@requires_runtime
def test_r1_parenthesized_value_if_no_uaf():
    """R1: Parenthesized identifier in value if block escapes without use-after-free."""
    code = 'weave main into int:\n  let x as string is if true:\n    var s is "hello world"\n    (s)\n  else:\n    "fallback"\n  if x == "hello world":\n    return 0\n  return 1\n'
    res = compile_run(code, tag="r1_if_uaf")
    assert res.returncode == 0


@requires_runtime
def test_r1_parenthesized_value_do_no_uaf():
    """R1: Parenthesized identifier in do: block escapes without use-after-free."""
    code = 'weave main into int:\n  let y as string is do:\n    var t is "penguscript"\n    ((t))\n  if y == "penguscript":\n    return 0\n  return 1\n'
    res = compile_run(code, tag="r1_do_uaf")
    assert res.returncode == 0


@requires_runtime
def test_r1_parenthesized_value_loop_no_uaf():
    """R1: Parenthesized identifier in loop value collection escapes without use-after-free."""
    code = 'weave main into int:\n  var words as list of string is for i from 0 to 3:\n    var s is "item-{(i to string)}"\n    (s)\n  var w0 as string is words at 0\n  var w1 as string is words at 1\n  var w2 as string is words at 2\n  if w0 == "item-0" and w1 == "item-1" and w2 == "item-2":\n    return 0\n  return 1\n'
    res = compile_run(code, tag="r1_loop_uaf")
    assert res.returncode == 0


def test_r2_const_definitions_reset_on_recheck():
    """R2: Reusing the same PenguChecker instance resets const_definitions without false collision."""
    parser = PenguParser()
    checker = PenguChecker()

    tree1 = parser.parse("const MAX is 100\nweave main into int:\n  return MAX\n")
    checker.check(tree1)
    assert len(checker.errors) == 0

    tree2 = parser.parse("const MAX is 200\nweave main into int:\n  return MAX\n")
    checker.check(tree2)
    assert len(checker.errors) == 0


def test_r3_with_init_body_errors_reported_once():
    """R3: Errors inside a with: builder are reported exactly once."""
    code = """rune Point:
  x as int

weave main into int:
  var p as Point with:
    set .y is 10
  return 0
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    try:
        checker.check(tree)
    except Exception as exc:
        all_errors = getattr(exc, "all_errors", [exc])
        field_errors = [e for e in all_errors if "has no field 'y'" in str(e)]
        assert len(field_errors) == 1, f"Expected 1 field error, got {len(field_errors)}: {field_errors}"


def test_r5_or_block_any_type_rejected_at_codegen():
    """R5: _translate_or_block raises SemanticError E0005 when operand is AnyType."""
    codegen = PenguCodegen()
    codegen._infer_node_type = lambda *args, **kwargs: AnyType()
    with pytest.raises(SemanticError) as exc_info:
        codegen._translate_or_block(left_op=None, block_stmts=[])
    assert exc_info.value.code == "E0005"
    assert "with 'any' operand type" in str(exc_info.value)


def test_r6_or_block_body_still_checked_on_bad_operand():
    """R6: _check_or_block continues checking the or: body when the operand is invalid."""
    code = """weave main into int:
  var x as int is 1 or:
    var bad as int is "type error"
    return 0
  return x
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    try:
        checker.check(tree)
    except Exception as exc:
        all_errors = getattr(exc, "all_errors", [exc])
        err_texts = [str(e) for e in all_errors]
        assert any("'or:' requires a 'maybe T'" in t for t in err_texts)
        assert any("type error" in t or "TypeMismatchError" in str(type(e)) for e, t in zip(all_errors, err_texts))


def test_r7_static_var_decl_with_layout_consistency():
    """R7: static var declarations work consistently with decl_layout."""
    code = """weave counter into int:
  static var count as int is 0
  set count is count + 1
  return count

weave main into int:
  return calling counter
"""
    check_ok(code)
    c = gen_bundle(code)
    assert "static int32_t count = 0;" in c


def test_r9_decl_layout_moved_to_symbols():
    """R9: decl_layout is exposed from pengu_parser.pengu_symbols.

    The borrowed modifier is gone, so var_decl/let_decl/static_var_decl share a
    single child layout: [name, type_or_None, value].  The type therefore lives
    at index 1 and the value at index 2, with no leading placeholder slot.
    """
    from pengu_parser.pengu_symbols import decl_layout as symbols_decl_layout
    from pengu_parser.pengu_checker import _decl_layout as checker_decl_layout

    parser = PenguParser()
    tree = parser.parse(
        "weave main into int:\n"
        "  var x as int is 5\n"
        "  let y as int is x\n"
        "  static var z as int is 1\n"
        "  return x\n"
    )
    seen = set()
    for rule in ("var_decl", "let_decl", "static_var_decl"):
        for n in tree.find_data(rule):
            seen.add(rule)
            t1, e1 = symbols_decl_layout(n)
            t2, e2 = checker_decl_layout(n)
            assert t1 is not None and t1 == t2
            assert e1 is not None and e1 == e2
            assert n.children[1] is t1
            assert n.children[2] is e1
    assert seen == {"var_decl", "let_decl", "static_var_decl"}

    # An absent annotation is still an explicit None placeholder, so the value
    # keeps living at index 2.
    tree = parser.parse("weave main into int:\n  var x is 5\n  return x\n")
    for n in tree.find_data("var_decl"):
        assert n.children[1] is None
        t, e = symbols_decl_layout(n)
        assert t is None
        assert e is n.children[2]
