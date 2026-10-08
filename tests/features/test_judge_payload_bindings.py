"""Tests for judge payload bindings and guards (Item 1.5.1)."""

import pytest
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import SemanticError, TypeMismatchError
from tests.conftest import compile_run


def check_source(source: str):
    parser = PenguParser()
    tree = parser.parse(source)
    checker = PenguChecker()
    checker.check(tree)
    return checker


def test_judge_payload_binding_compiles_and_runs():
    source = """import std.spark

omen Status:
    Ok with value as int
    Err with code as int

weave inspect with s as Status into int:
    return judge s:
        when Status.Ok with value -> value + 10
        when Status.Err with code -> code
        else -> 0

weave main into int:
    var s as Status is with Ok is with value is 32
    var res as int is calling inspect with s
    calling spark.println with (res to string)
    return 0
"""
    checker = check_source(source)
    assert checker is not None
    res = compile_run(source, tag="test_judge_payload")
    assert res.returncode == 0
    assert "42" in res.stdout


def test_judge_guard_filters_by_condition():
    source = """import std.spark

omen Number:
    Val with n as int

weave describe with x as Number into string:
    return judge x:
        when Number.Val with n if n > 0 -> "positive"
        when Number.Val with n if n < 0 -> "negative"
        when Number.Val with n -> "zero"
        else -> "unknown"

weave main into int:
    var p as Number is with Val is with n is 5
    var z as Number is with Val is with n is 0
    var m as Number is with Val is with n is -3
    calling spark.println with (calling describe with p)
    calling spark.println with (calling describe with z)
    calling spark.println with (calling describe with m)
    return 0
"""
    checker = check_source(source)
    assert checker is not None
    res = compile_run(source, tag="test_judge_guard")
    assert res.returncode == 0
    lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    assert lines == ["positive", "zero", "negative"]


def test_missing_field_in_payload_fails():
    source = """omen Status:
    Ok with value as int

weave main into int:
    var s as Status is with Ok is with value is 10
    var r as int is judge s:
        when Status.Ok with nonexistent -> 1
        else -> 0
    return r
"""
    with pytest.raises(SemanticError) as exc_info:
        check_source(source)
    assert "nonexistent" in str(exc_info.value)
    assert exc_info.value.code == "E0005"


def test_payload_in_variant_without_payload_fails():
    source = """omen Flag:
    Active
    Inactive

weave main into int:
    var f as Flag is Flag.Active
    var r as int is judge f:
        when Flag.Active with x -> 1
        else -> 0
    return r
"""
    with pytest.raises(SemanticError) as exc_info:
        check_source(source)
    assert "no payload fields" in str(exc_info.value)
    assert exc_info.value.code == "E0005"


def test_guard_non_boolean_fails():
    source = """omen Status:
    Ok with value as int

weave main into int:
    var s as Status is with Ok is with value is 10
    var r as int is judge s:
        when Status.Ok with value if value + 1 -> 1
        else -> 0
    return r
"""
    with pytest.raises(TypeMismatchError) as exc_info:
        check_source(source)
    assert exc_info.value.code == "E0005"
