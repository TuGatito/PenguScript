"""A lambda body is its own function: no outer loop, no outer label.

Lambdas lower to top-level ``static`` C functions (no capture), so a
``break``/``continue`` or a loop label inside one must not resolve to a loop of
the enclosing weave — the emitted C would contain a ``break`` or ``goto`` in a
function where that loop does not exist.
"""
from __future__ import annotations

import pytest


def test_bare_break_inside_a_lambda_is_rejected(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave main into int:
    var i as int is 0
    while i < 2:
        set i += 1
        var f as weave into int is lambda into do:
            break
        var ignored as int is calling f
    return 0
""")
    assert "E0007" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_labeled_jump_inside_a_lambda_is_rejected(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave main into int:
    outer: for i from 0 to 3:
        var f as weave into int is lambda into do:
            break outer
        var ignored as int is calling f
    return 0
""")
    assert "E0004" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_continue_inside_a_lambda_is_rejected(parse_and_check):
    errors, _ast, _symbols = parse_and_check("""
weave main into int:
    outer: for i from 0 to 3:
        var f as weave into int is lambda into do:
            continue outer
        var ignored as int is calling f
    return 0
""")
    assert "E0004" in [e.code for e in errors], [f"{e.code}: {e}" for e in errors]


def test_a_loop_inside_a_lambda_is_fine(parse_and_check):
    """The lambda's own loops work, and their labels belong to the lambda."""
    errors, _ast, _symbols = parse_and_check("""
weave main into int:
    var outer as int is 3
    outer_loop: for i from 0 to 3:
        var f as weave into int is lambda into do:
            var acc as int is 0
            inner: for a from 0 to 3:
                if a == 2:
                    break inner
                set acc += a
            acc
        var ignored as int is calling f
    return outer
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


def test_same_label_in_a_lambda_and_its_enclosing_weave_is_allowed(parse_and_check):
    """Labels are function-local, and a lambda is a function of its own."""
    errors, _ast, _symbols = parse_and_check("""
weave main into int:
    outer: for i from 0 to 3:
        var f as weave into int is lambda into do:
            var acc as int is 0
            outer: for a from 0 to 3:
                if a == 1:
                    break outer
                set acc += a
            acc
        var ignored as int is calling f
    return 0
""")
    assert errors == [], [f"{e.code}: {e}" for e in errors]


@pytest.mark.slow
def test_lambda_with_its_own_loop_runs(compile_and_run):
    out = compile_and_run("""
import std.spark

weave run into int:
    var total as int is 0
    outer: for i from 0 to 3:
        var f as weave into int is lambda into do:
            var acc as int is 0
            lab: for a from 0 to 3:
                if a == 2:
                    break lab
                set acc += a
            acc
        set total += calling f
        if i == 1:
            break outer
    return total

weave main into int:
    calling spark.println with "{calling run}"
    return 0
""", tag="lambda_scope")
    assert out.strip() == "2"
