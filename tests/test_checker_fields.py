"""Tests for Bugs 2.1, 2.2, and Gap 4.2: Semantic field validation in _check_set_stmt."""

import pytest
from tests.conftest import check_error, check_ok


def test_set_unknown_field_rejected():
    """Bug 2.1: set p.unknown_field is v must fail checker with E0013."""
    src = """
rune Player:
    hp as int

weave main into void:
    var p as Player with:
        set .hp is 100
    set p.unknown_field is 50
"""
    check_error(src, contains="E0013")


def test_nested_field_on_primitive_rejected():
    """Bug 2.2: set p.hp.sub is v where hp is int must fail with E0013."""
    src = """
rune Player:
    hp as int

weave main into void:
    var p as Player with:
        set .hp is 100
    set p.hp.sub is 50
"""
    check_error(src, contains="E0013")


def test_with_target_nested_field_on_primitive_rejected():
    """Bug 2.2: with p: set .hp.sub is v where hp is int must fail with E0013."""
    src = """
rune Player:
    hp as int

weave main into void:
    var p as Player with:
        set .hp is 100
    with p:
        set .hp.sub is 50
"""
    check_error(src, contains="E0013")


def test_arrow_access_unknown_field_rejected():
    """Gap 4.2: set ptr->unknown_field is v on ref to Rune must fail with E0013."""
    src = """
rune Player:
    hp as int

weave modify with ptr as ref to Player into void:
    set ptr->unknown_field is 99
"""
    check_error(src, contains="E0013")


def test_arrow_access_on_non_reference_rejected():
    """Gap 4.2: set p->field on non-reference value must fail with E0003."""
    src = """
rune Player:
    hp as int

weave main into void:
    var p as Player with:
        set .hp is 100
    set p->hp is 80
"""
    check_error(src, contains="E0003")


def test_dot_access_on_reference_rejected():
    """Accessing reference via dot in set must fail with E0003."""
    src = """
rune Player:
    hp as int

weave modify with ptr as ref to Player into void:
    set ptr.hp is 80
"""
    check_error(src, contains="E0003")


def test_valid_field_assignments_pass():
    """Verify valid struct field assignments (dot and arrow) pass checker cleanly."""
    src = """
rune Vec2:
    x as int
    y as int

rune Entity:
    pos as Vec2
    hp as int

weave update with e as ref to Entity into void:
    set e->hp is 100
    set e->pos.x is 10
    set e->pos.y is 20

weave main into void:
    var ent as Entity with:
        set .hp is 50
        set .pos is with:
            set .x is 0
            set .y is 0
    set ent.hp is 75
    set ent.pos.x is 5
    calling update with sigil of ent
"""
    check_ok(src)
