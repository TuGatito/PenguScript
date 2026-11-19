"""Unit tests for Phase 2 core expressions and variable operations."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput

from penguscript.frontend.ast_nodes import (
    Assign,
    Binary,
    Call,
    CompoundAssign,
    Ident,
    Index,
    IntLit,
    ListLit,
    MapLit,
    MethodCall,
    Module,
    NamedType,
    Paren,
    RealmAccess,
    SelfFieldTarget,
    SetLit,
    VarTarget,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_variable_arithmetic_assignment() -> None:
    """Verify variable creation with arithmetic expression: x = (y + 1) / 2."""
    mod = parse("x = (y + 1) / 2")
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    assert stmt.targets == [VarTarget("x", span=stmt.targets[0].span)]
    assert isinstance(stmt.value, Binary)
    assert stmt.value.op == "/"
    assert isinstance(stmt.value.left, Paren)
    inner = stmt.value.left.inner
    assert isinstance(inner, Binary)
    assert inner.op == "+"
    assert isinstance(inner.left, Ident) and inner.left.name == "y"
    assert isinstance(inner.right, IntLit) and inner.right.value == 1
    assert isinstance(stmt.value.right, IntLit) and stmt.value.right.value == 2


def test_variable_reassignment_and_compound() -> None:
    """Verify reassignment and compound operators: x += 3."""
    mod = parse("x = 5\nx += 3\n")
    assert len(mod.declarations) == 2
    first, second = mod.declarations
    assert isinstance(first, Assign)
    assert isinstance(second, CompoundAssign)
    assert second.target == VarTarget("x", span=second.target.span)
    assert second.op == "+="
    assert isinstance(second.value, IntLit) and second.value.value == 3


def test_variable_mut_and_typed() -> None:
    """Verify mut variable and type annotations: mut counter: int = 0."""
    mod = parse("mut counter: int = 0")
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    assert stmt.is_mut is True
    assert stmt.targets == [VarTarget("counter", span=stmt.targets[0].span)]
    assert stmt.type_annotation is not None
    assert stmt.type_annotation == NamedType("int", span=stmt.type_annotation.span)
    assert isinstance(stmt.value, IntLit) and stmt.value.value == 0


def test_self_field_assignment() -> None:
    """Verify self field assignment: @x = x."""
    mod = parse("@x = x")
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    assert stmt.targets == [SelfFieldTarget("x", span=stmt.targets[0].span)]
    assert isinstance(stmt.value, Ident) and stmt.value.name == "x"


def test_collections_ast() -> None:
    """Verify list, map and set parsing into AST."""
    mod = parse("l = [1, 2]\nm = {a: 1}\ns = set{1, 2}\n")
    assert len(mod.declarations) == 3
    l_stmt, m_stmt, s_stmt = mod.declarations
    assert isinstance(l_stmt, Assign) and isinstance(l_stmt.value, ListLit)
    assert isinstance(m_stmt, Assign) and isinstance(m_stmt.value, MapLit)
    assert isinstance(s_stmt, Assign) and isinstance(s_stmt.value, SetLit)


def test_calls_and_accesses() -> None:
    """Verify calls, method calls, indices and realm access."""
    mod = parse("x = math::sqrt(2.0)\ny = obj.method(42)\nz = arr[0]\n")
    assert len(mod.declarations) == 3
    s1, s2, s3 = mod.declarations
    assert isinstance(s1, Assign) and isinstance(s1.value, Call)
    assert isinstance(s1.value.callee, RealmAccess)
    assert isinstance(s2, Assign) and isinstance(s2.value, MethodCall)
    assert isinstance(s3, Assign) and isinstance(s3.value, Index)


def test_good_fixtures_phase2() -> None:
    """All good phase2 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase2"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase2 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert isinstance(result, Module), f"Failed for {file}"
        assert len(result.declarations) > 0, f"Expected statements in {file}"


def test_bad_fixtures_phase2() -> None:
    """All bad phase2 fixtures must raise syntax/parsing errors."""
    bad_dir = FIXTURES_DIR / "bad" / "phase2"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase2 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises(UnexpectedInput) as exc_info:
            parse(content)
        diag = diagnostic_from_exception(exc_info.value)
        assert diag.code in ("E1001", "E1002")
