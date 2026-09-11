#!/usr/bin/env python3
"""Comprehensive test suite for PenguScript v0.9.0 features."""
import pytest
from tests.conftest import gen_bundle, compile_run, requires_runtime
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import (
    TypeMismatchError, ArraySizeMismatchError, InvalidRangeError,
    PrivateSymbolAccessError, NonExhaustiveJudgeError
)


# =========================================================================
# Feature 1: Multiline Arrays
# =========================================================================

def test_multiline_array_parsing():
    """P0 Feature 1: Multiline arrays with newlines inside brackets."""
    parser = PenguParser()
    code = """
weave main into int:
    var a is [
        1, 2, 3
    ]
    var b is [
        10,
        20,
        30
    ]
    return 0
"""
    tree = parser.parse(code)
    assert tree is not None


@requires_runtime
def test_multiline_array_runtime():
    """P0 Feature 1: Runtime execution of multiline arrays."""
    code = """
import std.spark

weave main into int:
    var arr is [
        10,
        20,
        30
    ]
    if (arr at 0) != 10:
        return 1
    if (arr at 1) != 20:
        return 1
    if (arr at 2) != 30:
        return 1
    calling spark.println with "multiline array ok"
    return 0
"""
    res = compile_run(code, tag="multi_arr")
    assert "multiline array ok" in res.stdout


# =========================================================================
# Feature 2: Strings, Dedent & Interpolation
# =========================================================================

def test_triple_and_raw_strings():
    """P0 Feature 2: Triple strings, dedent, raw strings, and expression interpolation."""
    code = '''
rune Point:
    x as float
    y as float

weave main into int:
    var p as Point is with x is 3.5, y is 4.5
    let msg is """
        Point coordinates:
        x: {p.x}
        y: {p.y}
    """
    let raw1 is r"hello\n{p.x}"
    let raw2 is r"""
        multiline raw {p.y}
    """
    return 0
'''
    c_out = gen_bundle(code)
    assert "pengu_string_format" in c_out
    assert "%f" in c_out
    assert 'r"hello' not in c_out
    assert "multiline raw {p.y}" in c_out


@requires_runtime
def test_triple_string_interpolation_runtime():
    """P0 Feature 2: Runtime interpolation and dedent."""
    code = '''
import std.spark

weave main into int:
    let name is "Pengu"
    let count is 42
    let text is """
        Hello {name}!
        Count is {count}.
    """
    calling spark.println with text
    return 0
'''
    res = compile_run(code, tag="interp")
    assert "Hello Pengu!" in res.stdout
    assert "Count is 42." in res.stdout


@requires_runtime
def test_raw_strings_runtime():
    """P0 Feature 2: Runtime raw strings without interpolation or escape processing."""
    code = '''
import std.spark

weave main into int:
    let raw_single is r"raw\\n{name}"
    let raw_triple is r"""
        first line\\t
        second line {val}
    """
    calling spark.println with raw_single
    calling spark.println with raw_triple
    return 0
'''
    res = compile_run(code, tag="raw_str")
    assert "raw\\n{name}" in res.stdout
    assert "second line {val}" in res.stdout


# =========================================================================
# Feature 4: Local Type & Array Size Inference
# =========================================================================

def test_type_and_size_inference():
    """P0 Feature 4: Full local type inference and array size inference."""
    code = """
weave main into int:
    let x is 5
    var y is 10
    var arr1 as array of i32 is [1, 2, 3]
    var arr2 is [10, 20, 30, 40]
    return x + y + (arr1 at 0) + (arr2 at 0)
"""
    c_out = gen_bundle(code)
    assert "x = 5" in c_out
    assert "y = 10" in c_out
    assert "arr1[3]" in c_out
    assert "arr2[4]" in c_out


def test_type_inference_null_error():
    """P0 Feature 4: Error E0014 when type cannot be inferred from null."""
    code = """
weave main into int:
    let x is null
    return 0
"""
    parser = PenguParser()
    tree = parser.parse(code)
    checker = PenguChecker()
    with pytest.raises(TypeMismatchError) as exc_info:
        checker.check(tree, source=code, filename="test.pengu")
    assert exc_info.value.code == "E0014"


# =========================================================================
# Feature 3: Indent Literals (2D / 1D Arrays, Runes, Maps)
# =========================================================================

@requires_runtime
def test_indent_array_2d_runtime():
    """P0 Feature 3: 2D array defined with indent literal."""
    code = """
import std.spark

weave main into int:
    var grid as array of array of i32 with size 2 with size 3 is
        1, 2, 3
        4, 5, 6

    if ((grid at 0) at 0) != 1:
        return 1
    if ((grid at 0) at 2) != 3:
        return 1
    if ((grid at 1) at 1) != 5:
        return 1
    calling spark.println with "grid ok"
    return 0
"""
    res = compile_run(code, tag="grid2d")
    assert "grid ok" in res.stdout


@requires_runtime
def test_indent_array_1d_runtime():
    """P0 Feature 3: 1D array defined with indent literal."""
    code = """
import std.spark

weave main into int:
    var my_arr as array of i32 with size 3 is
        100
        200
        300

    if (my_arr at 0) != 100:
        return 1
    if (my_arr at 2) != 300:
        return 1
    calling spark.println with "list ok"
    return 0
"""
    res = compile_run(code, tag="list1d")
    assert "list ok" in res.stdout


@requires_runtime
def test_indent_rune_and_map_runtime():
    """P0 Feature 3: Rune and Map defined with indent syntax."""
    code = """
import std.spark

rune Config:
    port as i32
    host as string

weave main into int:
    var cfg as Config is
        port: 8080
        host: "localhost"

    var dict is
        "alice": 10
        "bob": 20

    if cfg.port != 8080:
        return 1
    if cfg.host != "localhost":
        return 1
    calling spark.println with "cfg ok"
    return 0
"""
    res = compile_run(code, tag="ind_rune")
    assert "cfg ok" in res.stdout


# =========================================================================
# Feature 5: Ranges and `in` / `not in` Operators
# =========================================================================

@requires_runtime
def test_ranges_and_in_not_in_runtime():
    """P0 Feature 5: Range iteration and in/not in operator."""
    code = """
import std.spark

weave main into int:
    var total is 0
    for x in 0 to 5:
        set total is total + x

    var count is 0
    for y in 0..3:
        set count is count + 1

    let in_range is 3 in 0 to 5
    let not_in_range is 10 not in 0 to 5
    let str_in is "pengu" in "hello pengu world"
    let str_not_in is "xyz" not in "hello pengu world"

    if total != 10:
        return 1
    if count != 3:
        return 1
    if in_range == false:
        return 1
    if not_in_range == false:
        return 1
    if str_in == false:
        return 1
    if str_not_in == false:
        return 1
    calling spark.println with "ranges and in ok"
    return 0
"""
    res = compile_run(code, tag="ranges")
    assert "ranges and in ok" in res.stdout


# =========================================================================
# Feature 6: Checker Validations (E0041 - E0044)
# =========================================================================

def test_checker_e0041_array_size_mismatch():
    """P0 Feature 6: E0041 on array dimension mismatches in indent literal."""
    code_rows = """
weave main into int:
    var m as array of array of i32 with size 2 with size 2 is
        1, 2
        3, 4
        5, 6
    return 0
"""
    parser = PenguParser()
    checker = PenguChecker()
    with pytest.raises(ArraySizeMismatchError) as exc:
        checker.check(parser.parse(code_rows), source=code_rows, filename="test.pengu")
    assert exc.value.code == "E0041"
    assert "rows" in str(exc.value)

    code_cols = """
weave main into int:
    var m as array of array of i32 with size 2 with size 3 is
        1, 2, 3
        4, 5
    return 0
"""
    with pytest.raises(ArraySizeMismatchError) as exc2:
        checker.check(parser.parse(code_cols), source=code_cols, filename="test.pengu")
    assert exc2.value.code == "E0041"
    assert "elements" in str(exc2.value)


def test_checker_e0042_invalid_range():
    """P0 Feature 6: E0042 when range start > end at compile time."""
    code = """
weave main into int:
    var r is 5 to 2
    return 0
"""
    parser = PenguParser()
    checker = PenguChecker()
    with pytest.raises(InvalidRangeError) as exc:
        checker.check(parser.parse(code), source=code, filename="test.pengu")
    assert exc.value.code == "E0042"

    code2 = """
weave main into int:
    for i in 10..0:
        let x is i
    return 0
"""
    with pytest.raises(InvalidRangeError) as exc2:
        checker.check(parser.parse(code2), source=code2, filename="test.pengu")
    assert exc2.value.code == "E0042"


def test_checker_e0043_private_symbol_access():
    """P0 Feature 6: E0043 when accessing private symbol outside its owner."""
    code = """
rune Account:
    _secret as i32
    public_id as i32

weave main into int:
    var acc as Account is with _secret is 123, public_id is 1
    let s is acc._secret
    return 0
"""
    parser = PenguParser()
    checker = PenguChecker()
    with pytest.raises(PrivateSymbolAccessError) as exc:
        checker.check(parser.parse(code), source=code, filename="test.pengu")
    assert exc.value.code == "E0043"


def test_checker_e0044_non_exhaustive_judge():
    """P0 Feature 6: E0044 when judge on omen/bool is non-exhaustive without else."""
    code_omen = """
omen Status:
    Ok
    Err
    Pending

weave main into int:
    var s as Status is Status_Ok
    let code is judge s:
        when Status_Ok -> 0
        when Status_Err -> 1
    return code
"""
    parser = PenguParser()
    checker = PenguChecker()
    with pytest.raises(NonExhaustiveJudgeError) as exc:
        checker.check(parser.parse(code_omen), source=code_omen, filename="test.pengu")
    assert exc.value.code == "E0044"

    code_bool = """
weave main into int:
    var b is true
    let val is judge b:
        when true -> 1
    return val
"""
    with pytest.raises(NonExhaustiveJudgeError) as exc2:
        checker.check(parser.parse(code_bool), source=code_bool, filename="test.pengu")
    assert exc2.value.code == "E0044"


# =========================================================================
# Feature 7: Defer & Errdefer Blocks
# =========================================================================

@requires_runtime
def test_defer_and_errdefer_block_runtime():
    """P0 Feature 7: Multi-line block defer and errdefer."""
    code = """
import std.spark

weave cleanup_demo into int:
    var step is 0
    defer:
        calling spark.println with "defer block step 2"
        set step is step + 1
    defer:
        calling spark.println with "defer block step 1"
        set step is step + 1
    calling spark.println with "doing work"
    return 0

weave main into int:
    return calling cleanup_demo
"""
    res = compile_run(code, tag="defer_blk")
    assert "doing work" in res.stdout
    assert "defer block step 1" in res.stdout
    assert "defer block step 2" in res.stdout
    # Check execution order: doing work -> step 1 -> step 2
    idx_work = res.stdout.index("doing work")
    idx_s1 = res.stdout.index("defer block step 1")
    idx_s2 = res.stdout.index("defer block step 2")
    assert idx_work < idx_s1 < idx_s2
