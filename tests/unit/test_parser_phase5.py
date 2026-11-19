"""Unit tests for Phase 5 enchanting, constructors, destructors, operators, and parent."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput
from lark.indenter import DedentError

from penguscript.frontend.ast_nodes import (
    Assign,
    ConstructorCall,
    ConstructorDecl,
    DestructorDecl,
    EnchantingDecl,
    MethodDecl,
    Module,
    NamedType,
    OperatorDecl,
    ParentCall,
    RuneDecl,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_constructor_and_destructor() -> None:
    """Verify constructor with parameters and destructor inside rune."""
    code = (
        "rune Point\n"
        "  x: double\n"
        "  y: double\n"
        "  constructor(x: double, y: double)\n"
        "    @x = x\n"
        "    @y = y\n"
        "  destructor\n"
        '    io::println("Point destroyed")\n'
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    r = mod.declarations[0]
    assert isinstance(r, RuneDecl)
    assert r.name == "Point"
    assert len(r.fields) == 2
    assert r.constructor is not None
    assert isinstance(r.constructor, ConstructorDecl)
    assert len(r.constructor.params) == 2
    assert len(r.constructor.body.statements) == 2

    assert r.destructor is not None
    assert isinstance(r.destructor, DestructorDecl)
    assert len(r.destructor.body.statements) == 1


def test_constructor_no_args() -> None:
    """Verify parameterless constructor."""
    code = "rune Counter\n  count: int\n  constructor\n    @count = 0\n"
    mod = parse(code)
    assert len(mod.declarations) == 1
    r = mod.declarations[0]
    assert isinstance(r, RuneDecl)
    assert r.constructor is not None
    assert r.constructor.params == []
    assert len(r.constructor.body.statements) == 1


def test_constructor_parent_call() -> None:
    """Verify parent(...) constructor call in derived rune."""
    code = (
        "rune Dog heir Animal\n"
        "  breed: string\n"
        "  constructor(name: string, breed: string, legs: int = 4)\n"
        "    parent(name, legs)\n"
        "    @breed = breed\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    r = mod.declarations[0]
    assert isinstance(r, RuneDecl)
    assert r.parent is not None
    assert r.constructor is not None
    assert len(r.constructor.body.statements) == 2
    first_stmt = r.constructor.body.statements[0]
    assert isinstance(first_stmt, ParentCall)
    assert len(first_stmt.args) == 2


def test_enchanting_methods() -> None:
    """Verify const and mut methods inside enchanting blocks."""
    code = (
        "enchanting Point\n"
        "  len = -> double\n"
        "    (@x * @x + @y * @y).sqrt()\n"
        "  mut translate = (dx: double, dy: double) -> void\n"
        "    @x += dx\n"
        "    @y += dy\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    enc = mod.declarations[0]
    assert isinstance(enc, EnchantingDecl)
    assert enc.target_type == NamedType("Point", span=enc.target_type.span)
    assert len(enc.members) == 2

    m1, m2 = enc.members
    assert isinstance(m1, MethodDecl)
    assert m1.name == "len"
    assert not m1.is_mut

    assert isinstance(m2, MethodDecl)
    assert m2.name == "translate"
    assert m2.is_mut


def test_enchanting_operators() -> None:
    """Verify overloaded operators (+, -, +=, [], ()) inside enchanting."""
    code = (
        "enchanting Point\n"
        "  operator + = (other: Point) -> Point\n"
        "    Point(@x + other.x, @y + other.y)\n"
        "  operator - = -> Point\n"
        "    Point(-@x, -@y)\n"
        "  mut operator += = (other: Point) -> void\n"
        "    @x += other.x\n"
        "    @y += other.y\n"
        "  operator [] = (i: int) -> double\n"
        "    @x\n"
        "  operator () = (n: int) -> int\n"
        "    n * 2\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    enc = mod.declarations[0]
    assert isinstance(enc, EnchantingDecl)
    assert len(enc.members) == 5

    op_plus, op_neg, op_plus_eq, op_idx, op_call = enc.members
    assert isinstance(op_plus, OperatorDecl) and op_plus.op == "+" and not op_plus.is_mut
    assert isinstance(op_neg, OperatorDecl) and op_neg.op == "-" and not op_neg.is_mut
    assert isinstance(op_plus_eq, OperatorDecl) and op_plus_eq.op == "+=" and op_plus_eq.is_mut
    assert isinstance(op_idx, OperatorDecl) and op_idx.op == "[]" and not op_idx.is_mut
    assert isinstance(op_call, OperatorDecl) and op_call.op == "()" and not op_call.is_mut


def test_free_operator() -> None:
    """Verify free operator declaration at file scope."""
    code = (
        "operator + = (a: int, b: Point) -> Point\n"
        "  Point(a + b.x, a + b.y)\n"
        "operator * = (a: double, b: Point) -> Point\n"
        "  Point(a * b.x, a * b.y)\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 2
    op1, op2 = mod.declarations
    assert isinstance(op1, OperatorDecl) and op1.op == "+"
    assert isinstance(op2, OperatorDecl) and op2.op == "*"


def test_constructor_call_expression() -> None:
    """Verify constructor invocation expressions."""
    code = "p = Point(1.0, 2.0)\nb = Box<int>(42)\n"
    mod = parse(code)
    assert len(mod.declarations) == 2

    s1, s2 = mod.declarations
    assert isinstance(s1, Assign)
    assert isinstance(s1.value, ConstructorCall)
    assert s1.value.target_type == NamedType("Point", span=s1.value.target_type.span)
    assert len(s1.value.args) == 2

    assert isinstance(s2, Assign)
    assert isinstance(s2.value, ConstructorCall)
    assert s2.value.target_type.name == "Box"
    assert len(s2.value.target_type.args) == 1
    assert len(s2.value.args) == 1


def test_good_fixtures_phase5() -> None:
    """All good phase5 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase5"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase5 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert isinstance(result, Module), f"Failed for {file}"
        assert len(result.declarations) > 0, f"Expected statements in {file}"


def test_bad_fixtures_phase5() -> None:
    """All bad phase5 fixtures must raise syntax/parsing errors."""
    bad_dir = FIXTURES_DIR / "bad" / "phase5"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase5 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises((UnexpectedInput, DedentError)) as exc_info:
            parse(content)
        if isinstance(exc_info.value, UnexpectedInput):
            diag = diagnostic_from_exception(exc_info.value)
            assert diag.code in ("E1001", "E1002")
