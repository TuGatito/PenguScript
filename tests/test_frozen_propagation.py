"""Tests for FrozenType propagation through collections, pointers, and structs (Item 1.6)."""

import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import MutabilityError, TypeMismatchError


def check_source(source: str):
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    checker.check(tree)
    return checker


def test_frozen_array_read_succeeds():
    source = """weave main into int:
    var arr as frozen array of int with size 3 is [1, 2, 3]
    var x as frozen int is arr at 0
    return 0
"""
    checker = check_source(source)
    assert checker is not None


def test_frozen_array_mutation_fails():
    source = """weave main into int:
    var arr as frozen array of int with size 3 is [1, 2, 3]
    set arr at 0 is 10
    return 0
"""
    with pytest.raises(MutabilityError) as exc_info:
        check_source(source)
    assert exc_info.value.code == "E0006"


def test_ref_to_frozen_mutation_fails():
    source = """weave main into int:
    var val as int is 42
    var p as ref to frozen int is sigil of val
    set p at 0 is 100
    return 0
"""
    with pytest.raises(MutabilityError) as exc_info:
        check_source(source)
    assert exc_info.value.code == "E0006"


def test_ref_to_frozen_to_ref_to_void_fails():
    source = """weave main into int:
    var val as int is 42
    var p as ref to frozen int is sigil of val
    var vp as ref to void is p
    return 0
"""
    with pytest.raises(TypeMismatchError) as exc_info:
        check_source(source)
    assert exc_info.value.code == "E0005"


def test_ref_to_frozen_to_ref_to_frozen_void_succeeds():
    source = """weave main into int:
    var val as int is 42
    var p as ref to frozen int is sigil of val
    var fvp as ref to frozen void is p
    return 0
"""
    checker = check_source(source)
    assert checker is not None


def test_frozen_struct_chained_field_mutation_fails():
    source = """rune Inner:
    val as int

rune Outer:
    inner as frozen Inner

weave main into int:
    var o as Outer is with inner is with val is 42
    set o.inner.val is 99
    return 0
"""
    with pytest.raises(MutabilityError) as exc_info:
        check_source(source)
    assert exc_info.value.code == "E0006"
