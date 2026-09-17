"""Regression test suite for PenguScript 0.13.2 release.

Covers:
- C1: Memory leak elimination on compound_set_stmt (set s += ...)
- C2: or: block fallthrough UB elimination on error path
- C3: Removal of named_stmt rule requiring explicit set/var/let
- H1: arrow_access and at_access support in with_target chains
- H2: Value-position if/unless with FnType generates valid C
- H3: some <array_lit> rejected with E0005
- H4: in / not in validates collection type with E0005
- M1: Unit test names with triple-quoted strings stripped cleanly
- M2: ref to maybe T / ref to result value access uses -> arrow in codegen
"""
import pytest
from lark import Tree

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import TypeMismatchError, SemanticError, ParseError
from pengu_parser.pengu_parser import PenguParser
from tests.conftest import (
    check,
    check_error,
    check_ok,
    compile_run,
    gen_bundle,
    requires_cc,
)


def test_c1_compound_set_string_no_auto_banish_leak():
    """C1: set s += ... marks variable as set target, preventing erroneous auto-banish."""
    code = """weave main into int:
  var s as string is "hello" + " world"
  set s += "!"
  return 0
"""
    checker = check_ok(code)
    # The variable 's' must not be auto-banished because it is mutated via compound_set_stmt
    c = gen_bundle(code)
    assert "pengu_banish_string(&s)" not in c


@requires_cc
def test_c2_or_block_fallthrough_safe():
    """C2: or: block fallthrough does not cause null dereference or UB in C."""
    code = """weave f into maybe int:
  return maybe none

weave main into int:
  var x as int is calling f or:
    calling print with "error handled"
  return x
"""
    res = compile_run(code, tag="test_c2_or_safe")
    assert res.returncode == 0
    assert "error handled" in res.stdout


def test_c3_named_stmt_syntax_error():
    """C3: bare 'x is 5' without set/var/let is rejected by the grammar."""
    code = """weave main into int:
  x is 5
  return x
"""
    parser = PenguParser()
    with pytest.raises(Exception):
        parser.parse(code)


@requires_cc
def test_h1_with_target_arrow_access():
    """H1: set .p->x is 5 within with: block is accepted and compiles cleanly."""
    code = """rune Point:
  x as int

rune Box:
  p as ref to Point

weave main into int:
  var pt as Point with:
    set .x is 0
  var b as Box with:
    set .p is sigil of pt
    set .p->x is 42
  if pt.x == 42:
    return 0
  return 1
"""
    checker = check_ok(code)
    res = compile_run(code, tag="test_h1_arrow")
    assert res.returncode == 0


@requires_cc
def test_h2_value_if_fn_type_compiles():
    """H2: Value-position if returning FnType emits valid C function pointer declaration."""
    code = """weave f1 with x as int into int:
  return x + 1

weave f2 with x as int into int:
  return x + 2

weave main into int:
  var cond as bool is true
  var f as weave with x as int into int is if cond:
    f1
  else:
    f2
  if (calling f with 5) == 6:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "int32_t (*" in c
    res = compile_run(code, tag="test_h2_fn_if")
    assert res.returncode == 0


def test_h3_some_array_lit_rejected():
    """H3: some [1, 2, 3] is rejected with E0005 because fixed C arrays cannot be boxed into maybe."""
    code = """weave main into int:
  var m as maybe (array of int with size 3) is some [1, 2, 3]
  return 0
"""
    check_error(code, contains="E0005")


def test_h4_in_expr_non_collection_rejected():
    """H4: 1 in r where r is a non-collection type is rejected with E0005."""
    code = """rune R:
  x as int

weave main into int:
  var r as R with:
    set .x is 1
  if 1 in r:
    calling print with "yes"
  return 0
"""
    check_error(code, contains="E0005")


def test_m1_test_triple_quoted_name():
    """M1: Test declaration with triple-quoted string has quotes stripped cleanly."""
    code = '''test """custom test title""":
  var ok as bool is true
'''
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    checker.check(tree)
    assert not checker.errors

    from pengu_parser.pengu_codegen import PenguCodegen
    codegen = PenguCodegen()
    codegen.collect_declarations([("test.pengu", tree)])
    assert len(codegen.tests) == 1
    assert codegen.tests[0]["name"] == "custom test title"


@requires_cc
def test_m2_ref_to_maybe_value_access():
    """M2: ref to maybe T accessing ->value uses -> arrow operator in C."""
    code = """weave unwrap with p as ref to maybe int into int:
  return p->value

weave main into int:
  var m as maybe int is some 42
  if (calling unwrap with sigil of m) == 42:
    return 0
  return 1
"""
    c = gen_bundle(code)
    assert "p->value" in c
    res = compile_run(code, tag="test_m2_ref_maybe")
    assert res.returncode == 0
