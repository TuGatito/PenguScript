"""Unit tests for Phase 3 statements, control flow and function literals."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput
from lark.indenter import DedentError

from penguscript.frontend.ast_nodes import (
    Assign,
    Binary,
    Block,
    Break,
    Continue,
    ExprStmt,
    ForIter,
    ForNumeric,
    FunctionLiteral,
    If,
    IfInline,
    IntLit,
    Module,
    NamedType,
    Parameter,
    Pass,
    Repeat,
    Unless,
    UnsafeBlock,
    Until,
    VarTarget,
    While,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_function_literal_multiline() -> None:
    """Verify multiline function literal with typed parameters and block body."""
    mod = parse("sum = (x: int, y: int) -> int\n  x + y\n")
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    assert stmt.targets == [VarTarget("sum", span=stmt.targets[0].span)]
    fn = stmt.value
    assert isinstance(fn, FunctionLiteral)
    assert len(fn.params) == 2
    assert fn.params[0] == Parameter(
        name="x",
        type_annotation=NamedType("int", span=fn.params[0].type_annotation.span),  # type: ignore[union-attr]
        span=fn.params[0].span,
    )
    assert fn.params[1] == Parameter(
        name="y",
        type_annotation=NamedType("int", span=fn.params[1].type_annotation.span),  # type: ignore[union-attr]
        span=fn.params[1].span,
    )
    assert fn.return_type == NamedType("int", span=fn.return_type.span)  # type: ignore[union-attr]
    assert isinstance(fn.body, Block)
    assert len(fn.body.statements) == 1
    expr_stmt = fn.body.statements[0]
    assert isinstance(expr_stmt, ExprStmt)
    assert isinstance(expr_stmt.expr, Binary)


def test_function_forward_declaration() -> None:
    """Verify function forward declaration (no body)."""
    mod = parse("my_function = -> void\n")
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    fn = stmt.value
    assert isinstance(fn, FunctionLiteral)
    assert fn.params == []
    assert fn.return_type == NamedType("void", span=fn.return_type.span)  # type: ignore[union-attr]
    assert fn.body is None


def test_function_inline_inferred() -> None:
    """Verify inline functions with inferred return type."""
    mod = parse('func_a = -> io::println("hello world")\n')
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    fn = stmt.value
    assert isinstance(fn, FunctionLiteral)
    assert fn.return_type is None
    assert fn.body is not None

    mod2 = parse("double = (x: int) -> x * 2\n")
    stmt2 = mod2.declarations[0]
    assert isinstance(stmt2, Assign)
    fn2 = stmt2.value
    assert isinstance(fn2, FunctionLiteral)
    assert len(fn2.params) == 1
    assert fn2.return_type is None
    assert isinstance(fn2.body, Binary)


def test_if_else_branches() -> None:
    """Verify multi-branch if-statement and unless statement."""
    code = "if x > 0\n  pass\nelse if x < 0\n  pass\nelse\n  pass\n"
    mod = parse(code)
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, If)
    assert len(stmt.else_if_clauses) == 1
    assert stmt.else_block is not None

    mod_unless = parse("unless x == 0\n  pass\n")
    assert len(mod_unless.declarations) == 1
    assert isinstance(mod_unless.declarations[0], Unless)


def test_if_inline() -> None:
    """Verify inline if expression."""
    mod = parse("sign = if x > 0 then 1 else -1\n")
    assert len(mod.declarations) == 1
    stmt = mod.declarations[0]
    assert isinstance(stmt, Assign)
    assert isinstance(stmt.value, IfInline)


def test_loops() -> None:
    """Verify while, until, repeat, numeric for, and iterable for."""
    code = (
        "while c < 10\n  c += 1\n"
        "until c >= 10\n  c += 1\n"
        "repeat\n  c += 1\nuntil c == 20\n"
        "for i = 1, 10\n  pass\n"
        "for x in items\n  pass\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 5
    assert isinstance(mod.declarations[0], While)
    assert isinstance(mod.declarations[1], Until)
    assert isinstance(mod.declarations[2], Repeat)
    assert isinstance(mod.declarations[3], ForNumeric)
    assert isinstance(mod.declarations[4], ForIter)


def test_control_flow_keywords() -> None:
    """Verify break, continue, pass, and unsafe block."""
    code = "break 42\ncontinue\npass\nunsafe\n  pass\n"
    mod = parse(code)
    assert len(mod.declarations) == 4
    b, c, p, u = mod.declarations
    assert isinstance(b, Break) and isinstance(b.value, IntLit)
    assert isinstance(c, Continue)
    assert isinstance(p, Pass)
    assert isinstance(u, UnsafeBlock)


def test_good_fixtures_phase3() -> None:
    """All good phase3 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase3"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase3 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert isinstance(result, Module), f"Failed for {file}"
        assert len(result.declarations) > 0, f"Expected statements in {file}"


def test_bad_fixtures_phase3() -> None:
    """All bad phase3 fixtures must raise syntax/parsing errors."""
    bad_dir = FIXTURES_DIR / "bad" / "phase3"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase3 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises((UnexpectedInput, DedentError)) as exc_info:
            parse(content)
        if isinstance(exc_info.value, UnexpectedInput):
            diag = diagnostic_from_exception(exc_info.value)
            assert diag.code in ("E1001", "E1002")
