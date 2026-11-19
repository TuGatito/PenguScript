"""Unit tests for Phase 6 types, sigils, needs constraints, references, and optionals."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput

from penguscript.frontend.ast_nodes import (
    Assign,
    Block,
    Call,
    ConstructorCall,
    EchoDecl,
    FunctionLiteral,
    LiteralType,
    NamedType,
    RuneDecl,
    SealDecl,
    TupleLiteral,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_generic_functions_sigils() -> None:
    """Verify generic functions with single and multiple sigils."""
    code = "identity = <T>(x: T) -> T\n  x\npair = <A, B>(a: A, b: B) -> tuple<A, B>\n  (a, b)\n"
    mod = parse(code)
    assert len(mod.declarations) == 2

    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    fn1 = d1.value
    assert isinstance(fn1, FunctionLiteral)
    assert len(fn1.sigils) == 1
    assert fn1.sigils[0].name == "T"
    assert fn1.sigils[0].constraints == []

    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    fn2 = d2.value
    assert isinstance(fn2, FunctionLiteral)
    assert len(fn2.sigils) == 2
    assert fn2.sigils[0].name == "A"
    assert fn2.sigils[1].name == "B"
    assert fn2.body is not None
    assert isinstance(fn2.body, Block)
    first_stmt = fn2.body.statements[0]
    assert hasattr(first_stmt, "expr")
    assert isinstance(first_stmt.expr, TupleLiteral)
    assert len(first_stmt.expr.elements) == 2


def test_sigils_with_needs_constraints() -> None:
    """Verify sigils with single, multiple, and parameterized needs constraints."""
    code = (
        "find_min = <T needs Ord>(items: ref<vector<T>>) -> T?\n"
        "  pass\n"
        'describe = <T needs Ord, Display>(x: T) -> string\n  "ok"\n'
        "convert = <T needs Into<U>>(x: T) -> U\n  x as U\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 3

    # find_min
    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    fn1 = d1.value
    assert isinstance(fn1, FunctionLiteral)
    assert len(fn1.sigils) == 1
    s1 = fn1.sigils[0]
    assert s1.name == "T"
    assert len(s1.constraints) == 1
    assert s1.constraints[0].name == "Ord"
    assert s1.constraints[0].args == []

    # return type T?
    assert fn1.return_type is not None
    assert isinstance(fn1.return_type, NamedType)
    assert fn1.return_type.name == "T"
    assert fn1.return_type.is_optional is True

    # describe with multiple constraints
    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    fn2 = d2.value
    assert isinstance(fn2, FunctionLiteral)
    assert len(fn2.sigils) == 1
    s2 = fn2.sigils[0]
    assert s2.name == "T"
    assert len(s2.constraints) == 2
    assert [c.name for c in s2.constraints] == ["Ord", "Display"]

    # convert with parameterized constraint Into<U>
    d3 = mod.declarations[2]
    assert isinstance(d3, Assign)
    fn3 = d3.value
    assert isinstance(fn3, FunctionLiteral)
    assert len(fn3.sigils) == 1
    s3 = fn3.sigils[0]
    assert s3.name == "T"
    assert len(s3.constraints) == 1
    assert s3.constraints[0].name == "Into"
    assert len(s3.constraints[0].args) == 1
    assert isinstance(s3.constraints[0].args[0], NamedType)
    assert s3.constraints[0].args[0].name == "U"


def test_generic_runes_echoes_seals() -> None:
    """Verify generic runes, echoes, and seals with sigils."""
    code = "echo Pair<T> = tuple<T, T>\nseal Wrapper<T> = T\nrune Box<T>\n  value: T\n"
    mod = parse(code)
    assert len(mod.declarations) == 3

    e = mod.declarations[0]
    assert isinstance(e, EchoDecl)
    assert e.name == "Pair"
    assert e.type_params == ["T"]
    assert len(e.sigils) == 1
    assert e.sigils[0].name == "T"

    s = mod.declarations[1]
    assert isinstance(s, SealDecl)
    assert s.name == "Wrapper"
    assert s.type_params == ["T"]
    assert len(s.sigils) == 1
    assert s.sigils[0].name == "T"

    r = mod.declarations[2]
    assert isinstance(r, RuneDecl)
    assert r.name == "Box"
    assert r.type_params == ["T"]
    assert len(r.sigils) == 1
    assert r.sigils[0].name == "T"
    assert len(r.fields) == 1
    assert r.fields[0].name == "value"
    assert isinstance(r.fields[0].type_annotation, NamedType)
    assert r.fields[0].type_annotation.name == "T"


def test_references_and_optionals() -> None:
    """Verify ref<T>, mut ref<T>, T?, and optional<T>."""
    code = (
        "p = (name: ref<string>) -> void\n"
        "  pass\n"
        "m = (buf: mut ref<int>) -> void\n"
        "  pass\n"
        "x: int? = none\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 3

    # ref<string>
    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    fn1 = d1.value
    assert isinstance(fn1, FunctionLiteral)
    param1_type = fn1.params[0].type_annotation
    assert isinstance(param1_type, NamedType)
    assert param1_type.name == "ref"
    assert param1_type.is_mut is False
    assert len(param1_type.args) == 1
    assert isinstance(param1_type.args[0], NamedType)
    assert param1_type.args[0].name == "string"

    # mut ref<int>
    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    fn2 = d2.value
    assert isinstance(fn2, FunctionLiteral)
    param2_type = fn2.params[0].type_annotation
    assert isinstance(param2_type, NamedType)
    assert param2_type.name == "ref"
    assert param2_type.is_mut is True
    assert len(param2_type.args) == 1
    assert isinstance(param2_type.args[0], NamedType)
    assert param2_type.args[0].name == "int"

    # int?
    d3 = mod.declarations[2]
    assert isinstance(d3, Assign)
    assert d3.type_annotation is not None
    assert isinstance(d3.type_annotation, NamedType)
    assert d3.type_annotation.name == "int"
    assert d3.type_annotation.is_optional is True


def test_explicit_generic_calls() -> None:
    """Verify explicit generic instantiations like make_vector<int>() and Box<int>(42)."""
    code = 'v = make_vector<int>()\ns = identity<string>("hi")\nb = Box<int>(42)\n'
    mod = parse(code)
    assert len(mod.declarations) == 3

    # make_vector<int>()
    d1 = mod.declarations[0]
    assert isinstance(d1, Assign)
    assert isinstance(d1.value, Call)
    assert len(d1.value.type_args) == 1
    assert isinstance(d1.value.type_args[0], NamedType)
    assert d1.value.type_args[0].name == "int"
    assert d1.value.args == []

    # identity<string>("hi")
    d2 = mod.declarations[1]
    assert isinstance(d2, Assign)
    assert isinstance(d2.value, Call)
    assert len(d2.value.type_args) == 1
    assert isinstance(d2.value.type_args[0], NamedType)
    assert d2.value.type_args[0].name == "string"
    assert len(d2.value.args) == 1

    # Box<int>(42) - ConstructorCall
    d3 = mod.declarations[2]
    assert isinstance(d3, Assign)
    assert isinstance(d3.value, ConstructorCall)
    assert d3.value.target_type.name == "Box"
    assert len(d3.value.target_type.args) == 1
    assert isinstance(d3.value.target_type.args[0], NamedType)
    assert d3.value.target_type.args[0].name == "int"


def test_literal_types() -> None:
    """Verify literal values in type arguments, e.g. array<int, 4>."""
    code = "fixed: array<int, 4> = [1, 2, 3, 4]\n"
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, Assign)
    assert d.type_annotation is not None
    assert isinstance(d.type_annotation, NamedType)
    assert d.type_annotation.name == "array"
    assert len(d.type_annotation.args) == 2
    assert isinstance(d.type_annotation.args[0], NamedType)
    assert d.type_annotation.args[0].name == "int"
    assert isinstance(d.type_annotation.args[1], LiteralType)
    assert d.type_annotation.args[1].value == 4


def test_good_fixtures_phase6() -> None:
    """All good phase6 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase6"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase6 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert result is not None, f"Failed to parse good fixture: {file.name}"


def test_bad_fixtures_phase6() -> None:
    """All bad phase6 fixtures must fail with a syntax error diagnostic."""
    bad_dir = FIXTURES_DIR / "bad" / "phase6"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase6 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises(UnexpectedInput) as exc_info:
            parse(content)
        diag = diagnostic_from_exception(exc_info.value)
        assert diag.code in ("E1001", "E1002"), (
            f"Expected E1xxx code for {file.name}, got {diag.code}"
        )
