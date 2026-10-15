"""``@mutates`` end to end: real C compiler, real process.

Marked ``slow`` and skipped without a C compiler (or without a built runtime):
everything here shells out.  These are the cases that prove the *semantics* --
that the statement form really mutates, that ``get_<name>`` really does not, and
that chained mutations stay sequential instead of collapsing into one nested
expression (R1.6).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


PRELUDE = """
import std.spark

enchanting int:
    @mutates
    weave clamp with lo as int, hi as int into int:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

    @mutates
    weave twice into int:
        return self + self
"""


def test_statement_mutates_in_place(compile_and_run):
    out = compile_and_run(PRELUDE + """
weave main into int:
    var x as int is 50
    calling x.clamp with 0, 10
    calling spark.println with "{x}"
    return 0
""")
    assert out.strip() == "10"


def test_getter_returns_without_mutating(compile_and_run):
    out = compile_and_run(PRELUDE + """
weave main into int:
    var x as int is 50
    var y as int is calling x.get_clamp with 0, 3
    calling spark.println with "{y} {x}"
    return 0
""")
    assert out.strip() == "3 50"


def test_chained_mutations_are_sequential(compile_and_run):
    """Each statement sees the previous one's result (no temporary nesting)."""
    out = compile_and_run(PRELUDE + """
weave main into int:
    var x as int is -50
    calling x.clamp with -30, 30
    calling x.get_clamp with 0, 1
    calling x.twice
    calling spark.println with "{x}"
    return 0
""")
    assert out.strip() == "-60"


def test_mutation_is_visible_in_a_loop(compile_and_run):
    out = compile_and_run(PRELUDE + """
weave main into int:
    var x as int is 1
    var i as int is 0
    while i < 4:
        calling x.twice
        set i is i + 1
    calling spark.println with "{x}"
    return 0
""")
    assert out.strip() == "16"


def test_shard_mutates_covers_several_receivers(compile_and_run):
    """One `enchanting shard T` declaration serves int and float alike."""
    out = compile_and_run("""
import std.spark

enchanting shard T where T: Num and T: Ordo and T: Par:
    @mutates
    weave clamp with lo as T, hi as T into T:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

weave main into int:
    var i as int is 50
    calling i.clamp with 0, 10
    var f as float is 50.0
    calling f.clamp with 0.0, 2.5
    calling spark.println with "{i} {f}"
    return 0
""")
    assert out.strip() == "10 2.5"


def test_mutating_method_may_call_another_on_self(compile_and_run):
    """Inside a body `self` is still an immutable value, so a mutating method
    cannot recurse into itself in place -- it uses the pure form."""
    out = compile_and_run("""
import std.spark

enchanting int:
    @mutates
    weave halve into int:
        return self / 2

    @mutates
    weave quarter into int:
        return (calling self.get_halve) / 2

weave main into int:
    var x as int is 100
    calling x.quarter
    calling spark.println with "{x}"
    return 0
""")
    assert out.strip() == "25"


def test_mutates_on_a_rune_receiver(compile_and_run):
    """A reference receiver (`self` is `ref to T`) takes the same surface forms:
    the pure body returns a whole new value and the call site assigns it back."""
    out = compile_and_run("""
import std.spark

rune Counter:
    n as int

enchanting Counter:
    @mutates
    weave bumped into Counter:
        return with n is self->n + 1

weave main into int:
    var c as Counter with:
        set .n is 5
    calling c.bumped
    calling spark.println with "{c.n}"
    var d as Counter is calling c.get_bumped
    calling spark.println with "{d.n} {c.n}"
    return 0
""")
    assert out.strip().splitlines() == ["6", "7 6"]
