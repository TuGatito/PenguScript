"""Tests for nested with: blocks (both construction and editing forms).

Validates that 'set .field is with:' and 'with x:' with nested builders properly
infer the target type from the enclosing with-chain, allocate distinct C
temporaries (_with_N) without collisions, preserve semantic type safety, and
correctly lower compound assignment inside nested scopes.
"""
import pytest
from lark import Token, Tree

from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_symbols import SymbolTable
from pengu_parser.pengu_types import INT_TYPE, STRING_TYPE, RuneType
from tests.conftest import check_error, compile_run, gen_bundle, requires_runtime


@requires_runtime
def test_nested_with_creation():
    """2-level nested with: construction correctly allocates distinct temporaries and runs."""
    src = """rune Address:
  street as string
  city as string
  zip as string

rune Person:
  name as string
  age as int
  address as Address

weave main into int:
  var a as Person with:
    set .name is "John"
    set .age is 30
    set .address is with:
      set .street is "123 Main St"
      set .city is "New York"
      set .zip is "12345"

  calling print with a.address.city
  return 0
"""
    bundle = gen_bundle(src, filename="test_creation.pengu")
    assert "_with_1" in bundle
    assert "_with_2" in bundle

    res = compile_run(src, tag="nested_create")
    assert "New York" in res.stdout


@requires_runtime
def test_nested_with_editing():
    """In-place editing with 'with a:' and nested 'set .address is with:' builder."""
    src = """rune Address:
  street as string
  city as string
  zip as string

rune Person:
  name as string
  age as int
  address as Address

weave main into int:
  var a as Person with:
    set .name is "John"
    set .age is 30
    set .address is with:
      set .street is "123 Main St"
      set .city is "New York"
      set .zip is "12345"

  with a:
    set .name is "Jane"
    set .age is 31
    set .address is with:
      set .street is "456 Elm St"
      set .city is "Los Angeles"
      set .zip is "67890"

  calling print with a.name
  calling print with a.address.city
  return 0
"""
    res = compile_run(src, tag="nested_edit")
    assert "Jane" in res.stdout
    assert "Los Angeles" in res.stdout
    # Verify order
    jane_idx = res.stdout.index("Jane")
    la_idx = res.stdout.index("Los Angeles")
    assert jane_idx < la_idx

    bundle = gen_bundle(src, filename="test_editing.pengu")
    # In 'with a:', 'a' is the target; the nested builder creates a fresh _with_3 (or distinct temporary)
    assert "_with_1" in bundle
    assert "_with_2" in bundle
    assert "_with_3" in bundle


@requires_runtime
def test_triple_nested_with():
    """Three levels of nested with: builders infer their types correctly."""
    src = """rune Coord:
  lat as int
  lon as int

rune Address:
  street as string
  location as Coord

rune Person:
  name as string
  address as Address

weave main into int:
  var p as Person with:
    set .name is "Ana"
    set .address is with:
      set .street is "Calle 1"
      set .location is with:
        set .lat is 10
        set .lon is 20
  calling print with p.address.location.lat
  return 0
"""
    res = compile_run(src, tag="triple_nested")
    assert "10" in res.stdout


@requires_runtime
def test_nested_with_in_loop_collect():
    """Nested with: blocks inside loop-as-expression collect values properly."""
    src = """rune Inner:
  v as int

rune Outer:
  id as int
  inner as Inner

weave main into int:
  var xs as list of Outer is for i from 0 to 4:
    var o as Outer with:
      set .id is i
      set .inner is with:
        set .v is i * 10
    o
  var total as int is 0
  for x in xs:
    set total += x.inner.v
  calling print with total
  return 0
"""
    res = compile_run(src, tag="loop_nested")
    assert "60" in res.stdout


def test_nested_with_field_type_mismatch():
    """Semantic checker must reject type mismatch inside nested with: builder."""
    src = """rune Inner:
  v as int
rune Outer:
  inner as Inner

weave main into int:
  var o as Outer with:
    set .inner is with:
      set .v is "not an int"
  return 0
"""
    err = check_error(src, contains="E0005")
    assert "Cannot assign value of type" in err or "E0005" in err


@requires_runtime
def test_compound_set_inside_nested_with():
    """Compound assignment on nested struct field inside 'with target:'."""
    src = """rune Counter:
  n as int

rune Wrapper:
  c as Counter

weave main into int:
  var w as Wrapper with:
    set .c is with:
      set .n is 5
  with w:
    set .c.n += 10
  calling print with w.c.n
  return 0
"""
    res = compile_run(src, tag="compound_nested")
    assert "15" in res.stdout


def test_nested_with_regression_existing_tests_still_pass():
    """Verifies generated bundle temporaries and clean with_stack lifecycle."""
    src = """rune Address:
  street as string
  city as string
  zip as string

rune Person:
  name as string
  age as int
  address as Address

weave main into int:
  var a as Person with:
    set .name is "John"
    set .age is 30
    set .address is with:
      set .street is "123 Main St"
      set .city is "New York"
      set .zip is "12345"

  calling print with a.address.city
  return 0
"""
    bundle = gen_bundle(src, filename="test_regress.pengu")
    assert "_with_1" in bundle
    assert "_with_2" in bundle
    # Verify both temporaries are defined and used
    assert "Person _with_1 = {0};" in bundle
    assert "Address _with_2 = {0};" in bundle


def test_lookup_with_field_type_resolves_rune_field():
    """Unit test for PenguCodegen._lookup_with_field_type with RuneType."""
    symbols = SymbolTable()
    cg = PenguCodegen(symbols, ["test.pengu"], ".")
    addr_type = RuneType("Address", {"street": STRING_TYPE, "city": STRING_TYPE, "zip": STRING_TYPE})
    person_type = RuneType("Person", {"name": STRING_TYPE, "age": INT_TYPE, "address": addr_type})
    cg.local_vars["_with_1"] = person_type
    cg.with_stack.append("_with_1")

    node = Tree("with_target", [Token("NAME", "address")])
    resolved = cg._lookup_with_field_type(node)
    assert resolved == addr_type


def test_lookup_with_field_type_empty_stack():
    """Unit test: empty with_stack yields None."""
    symbols = SymbolTable()
    cg = PenguCodegen(symbols, ["test.pengu"], ".")
    node = Tree("with_target", [Token("NAME", "address")])
    assert cg._lookup_with_field_type(node) is None


def test_lookup_with_field_type_unknown_field():
    """Unit test: unknown field on base rune yields None."""
    symbols = SymbolTable()
    cg = PenguCodegen(symbols, ["test.pengu"], ".")
    person_type = RuneType("Person", {"name": STRING_TYPE, "age": INT_TYPE})
    cg.local_vars["_with_1"] = person_type
    cg.with_stack.append("_with_1")

    node = Tree("with_target", [Token("NAME", "nonexistent")])
    assert cg._lookup_with_field_type(node) is None
