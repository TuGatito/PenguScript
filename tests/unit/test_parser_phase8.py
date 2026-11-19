"""Unit tests for Phase 8 advanced expressions."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput

from penguscript.frontend.ast_nodes import (
    Assign,
    Binary,
    Block,
    ForClause,
    Ident,
    IfBlockExpr,
    IfInline,
    IntLit,
    ListComp,
    ListLit,
    MapLit,
    NamedType,
    SelfField,
    SelfRef,
    SetLit,
    StringInterp,
    StringLit,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_string_interpolation_basic() -> None:
    """Verify #{expr} interpolation in standard strings."""
    code = 'msg = "Name: #{user}, Age: #{age}"\n'
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, Assign)
    interp = d.value
    assert isinstance(interp, StringInterp)
    assert len(interp.parts) == 4
    assert interp.parts[0] == "Name: "
    assert isinstance(interp.parts[1], Ident) and interp.parts[1].name == "user"
    assert interp.parts[2] == ", Age: "
    assert isinstance(interp.parts[3], Ident) and interp.parts[3].name == "age"


def test_fstring_interpolation() -> None:
    """Verify f"{expr}" format strings with expressions, fields, and self references."""
    code = 'msg1 = f"count = {@count}"\nmsg2 = f"{@} m"\nmsg3 = f"{i}:{x}"\n'
    mod = parse(code)
    assert len(mod.declarations) == 3

    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    assert isinstance(d1.value, StringInterp)
    assert len(d1.value.parts) == 2
    assert d1.value.parts[0] == "count = "
    assert isinstance(d1.value.parts[1], SelfField) and d1.value.parts[1].name == "count"

    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    assert isinstance(d2.value, StringInterp)
    assert len(d2.value.parts) == 2
    assert isinstance(d2.value.parts[0], SelfRef)
    assert d2.value.parts[1] == " m"

    d3 = mod.declarations[2]
    assert isinstance(d3, Assign)
    assert isinstance(d3.value, StringInterp)
    assert len(d3.value.parts) == 3
    assert isinstance(d3.value.parts[0], Ident) and d3.value.parts[0].name == "i"
    assert d3.value.parts[1] == ":"
    assert isinstance(d3.value.parts[2], Ident) and d3.value.parts[2].name == "x"


def test_regular_string_literal() -> None:
    """Strings without interpolation remain StringLit."""
    code = 'greeting = "Hello, world!"\n'
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, Assign)
    assert isinstance(d.value, StringLit)
    assert d.value.value == "Hello, world!"


def test_list_comprehension_filter_and_numeric() -> None:
    """Verify list comprehensions with filter if and numeric for."""
    code = (
        "squares = [x * x for x in items]\n"
        "evens = [x for x in items if x % 2 == 0]\n"
        "cubes = [i * i * i for i = 1, 10]\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 3

    # [x * x for x in items]
    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    c1 = d1.value
    assert isinstance(c1, ListComp)
    assert isinstance(c1.element, Binary) and c1.element.op == "*"
    assert len(c1.for_clauses) == 1
    clause1 = c1.for_clauses[0]
    assert isinstance(clause1, ForClause)
    assert clause1.target == "x"
    assert isinstance(clause1.iterable, Ident) and clause1.iterable.name == "items"
    assert clause1.condition is None

    # [x for x in items if x % 2 == 0]
    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    c2 = d2.value
    assert isinstance(c2, ListComp)
    assert isinstance(c2.element, Ident) and c2.element.name == "x"
    assert len(c2.for_clauses) == 1
    clause2 = c2.for_clauses[0]
    assert clause2.target == "x"
    assert clause2.condition is not None
    assert isinstance(clause2.condition, Binary) and clause2.condition.op == "=="

    # [i * i * i for i = 1, 10]
    d3 = mod.declarations[2]
    assert isinstance(d3, Assign)
    c3 = d3.value
    assert isinstance(c3, ListComp)
    clause3 = c3.for_clauses[0]
    assert clause3.target == "i"
    assert clause3.iterable is None
    assert isinstance(clause3.start, IntLit) and clause3.start.value == 1
    assert isinstance(clause3.end, IntLit) and clause3.end.value == 10


def test_list_comprehension_nested_and_index() -> None:
    """Verify multiple for clauses and index variable binding."""
    code = 'pairs = [[x, y] for x in xs for y in ys]\ntagged = [f"{i}:{x}" for i, x in items]\n'
    mod = parse(code)
    assert len(mod.declarations) == 2

    # pairs = [[x, y] for x in xs for y in ys]
    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    c1 = d1.value
    assert isinstance(c1, ListComp)
    assert len(c1.for_clauses) == 2
    assert c1.for_clauses[0].target == "x"
    assert isinstance(c1.for_clauses[0].iterable, Ident) and c1.for_clauses[0].iterable.name == "xs"
    assert c1.for_clauses[1].target == "y"
    assert isinstance(c1.for_clauses[1].iterable, Ident) and c1.for_clauses[1].iterable.name == "ys"

    # tagged = [f"{i}:{x}" for i, x in items]
    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    c2 = d2.value
    assert isinstance(c2, ListComp)
    assert len(c2.for_clauses) == 1
    assert c2.for_clauses[0].index_var == "i"
    assert c2.for_clauses[0].target == "x"


def test_typed_comprehension_and_collections() -> None:
    """Verify typed prefix on comprehensions and collection literals."""
    code = (
        "typed = vector<int>[x * 2 for x in items]\n"
        "explicit = vector<int>[1, 2, 3]\n"
        'm = map<string, int>{"alice": 30}\n'
        's = set{"red", "green"}\n'
    )
    mod = parse(code)
    assert len(mod.declarations) == 4

    # vector<int>[x * 2 for x in items]
    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    c1 = d1.value
    assert isinstance(c1, ListComp)
    assert c1.type_prefix is not None
    assert c1.type_prefix.name == "vector"
    assert len(c1.type_prefix.args) == 1
    assert isinstance(c1.type_prefix.args[0], NamedType)
    assert c1.type_prefix.args[0].name == "int"

    # vector<int>[1, 2, 3]
    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    assert isinstance(d2.value, ListLit)
    assert d2.value.type_prefix is not None
    assert isinstance(d2.value.type_prefix, NamedType)
    assert d2.value.type_prefix.name == "vector"

    # map<string, int>{"alice": 30}
    d3 = mod.declarations[2]
    assert isinstance(d3, Assign)
    assert isinstance(d3.value, MapLit)
    assert d3.value.type_prefix is not None
    assert isinstance(d3.value.type_prefix, NamedType)
    assert d3.value.type_prefix.name == "map"

    # set{"red", "green"}
    d4 = mod.declarations[3]
    assert isinstance(d4, Assign)
    assert isinstance(d4.value, SetLit)
    assert d4.value.prefix == "set"
    assert len(d4.value.elements) == 2


def test_inline_chained_if_expression() -> None:
    """Verify inline chained if...then...else if...else expressions."""
    code = 'sign = if x > 0 then "positive" else if x < 0 then "negative" else "zero"\n'
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, Assign)
    if_expr = d.value
    assert isinstance(if_expr, IfInline)
    assert isinstance(if_expr.condition, Binary) and if_expr.condition.op == ">"
    assert isinstance(if_expr.then_expr, StringLit) and if_expr.then_expr.value == "positive"
    # Nested else branch is another IfInline
    inner = if_expr.else_expr
    assert isinstance(inner, IfInline)
    assert isinstance(inner.condition, Binary) and inner.condition.op == "<"
    assert isinstance(inner.then_expr, StringLit) and inner.then_expr.value == "negative"
    assert isinstance(inner.else_expr, StringLit) and inner.else_expr.value == "zero"


def test_multiline_if_block_expression() -> None:
    """Verify multiline if expression returning a value with else if and else branches."""
    code = 'status = if count > 0\n  "ok"\nelse if count == 0\n  "empty"\nelse\n  "invalid"\n'
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, Assign)
    expr = d.value
    assert isinstance(expr, IfBlockExpr)
    assert isinstance(expr.condition, Binary) and expr.condition.op == ">"
    assert isinstance(expr.body, Block)
    assert len(expr.else_if_clauses) == 1
    elif_clause = expr.else_if_clauses[0]
    assert isinstance(elif_clause.condition, Binary) and elif_clause.condition.op == "=="
    assert isinstance(elif_clause.body, Block)
    assert expr.else_block is not None
    assert isinstance(expr.else_block, Block)


def test_good_fixtures_phase8() -> None:
    """All good phase8 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase8"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase8 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert result is not None, f"Failed to parse good fixture: {file.name}"


def test_bad_fixtures_phase8() -> None:
    """All bad phase8 fixtures must fail with a syntax error diagnostic."""
    bad_dir = FIXTURES_DIR / "bad" / "phase8"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase8 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises(UnexpectedInput) as exc_info:
            parse(content)
        diag = diagnostic_from_exception(exc_info.value)
        assert diag.code in ("E1001", "E1002"), (
            f"Expected E1xxx code for {file.name}, got {diag.code}"
        )
