#!/usr/bin/env python3
"""Tests for concept bounds enforcement on generic type instantiation (Item 1.4 / B1)."""

import pytest
from tests.conftest import check_error, check_ok


def test_generic_box_with_par_satisfied_int():
    """Box of int satisfies T: Par."""
    src = """
rune Box shard T where T: Par:
    val as T

weave main into void:
    var b as Box of int with:
        set .val is 42
"""
    check_ok(src)


def test_generic_box_with_par_unsatisfied_non_par():
    """Box of NonPar raises E0032 because NonPar does not implement Par."""
    src = """
rune NonPar:
    x as int

rune Box shard T where T: Par:
    val as T

weave main into void:
    var np as NonPar with:
        set .x is 1
    var b as Box of NonPar with:
        set .val is np
"""
    check_error(src, contains="E0032")


def test_generic_box_with_par_satisfied_string():
    """Box of string satisfies T: Par."""
    src = """
rune Box shard T where T: Par:
    val as T

weave main into void:
    var b as Box of string with:
        set .val is "hello"
"""
    check_ok(src)


def test_generic_pair_multiple_bounds_satisfied():
    """Pair of int and float satisfies A: Num, B: Par."""
    src = """
rune Pair shard A, B where A: Num and B: Par:
    first as A
    second as B

weave main into void:
    var p as Pair of int and float with:
        set .first is 1
        set .second is 2.5
"""
    check_ok(src)


def test_generic_pair_first_bound_unsatisfied():
    """Pair of string and int fails because string does not implement Num."""
    src = """
rune Pair shard A, B where A: Num and B: Par:
    first as A
    second as B

weave main into void:
    var p as Pair of string and int with:
        set .first is "bad"
        set .second is 2
"""
    check_error(src, contains="E0032")


def test_generic_box_with_explicit_concept_binding():
    """Box of Custom succeeds once Custom binds Par."""
    src = """
rune Custom:
    x as int

bind Custom with Par:
    weave is_equal with other as Custom into bool:
        return self->x == other.x

rune Box shard T where T: Par:
    val as T

weave main into void:
    var c as Custom with:
        set .x is 5
    var b as Box of Custom with:
        set .val is c
"""
    check_ok(src)
