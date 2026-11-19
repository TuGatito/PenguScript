"""Unit tests for Phase 4 top-level declarations and modules."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput
from lark.indenter import DedentError

from penguscript.frontend.ast_nodes import (
    ConstDecl,
    EchoDecl,
    EnchantingDecl,
    FnType,
    ImportSymbol,
    IntLit,
    InvokeDecl,
    Module,
    NamedType,
    RealmDecl,
    RuneDecl,
    RuneField,
    SealDecl,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_realm_declaration() -> None:
    """Verify realm namespace declaration."""
    mod = parse("realm geometry\n")
    assert len(mod.declarations) == 1
    assert mod.realm is not None
    assert mod.realm == RealmDecl(name="geometry", span=mod.realm.span)
    assert mod.declarations[0] == mod.realm


def test_invoke_declarations() -> None:
    """Verify module and selective import forms."""
    code = 'invoke "math"\ninvoke "utils/strings" as str\ninvoke {sqrt, pow as power} from "math"\n'
    mod = parse(code)
    assert len(mod.declarations) == 3
    assert len(mod.imports) == 3

    imp1, imp2, imp3 = mod.imports
    assert imp1 == InvokeDecl(path="math", alias=None, symbols=[], span=imp1.span)
    assert imp2 == InvokeDecl(path="utils/strings", alias="str", symbols=[], span=imp2.span)
    assert imp3.path == "math"
    assert imp3.symbols == [
        ImportSymbol(name="sqrt", alias=None, span=imp3.symbols[0].span),
        ImportSymbol(name="pow", alias="power", span=imp3.symbols[1].span),
    ]


def test_const_declaration() -> None:
    """Verify constant declarations with and without explicit type."""
    code = "const GLOBAL_CONSTANT = 100\nconst PI: double = 3.14159\n"
    mod = parse(code)
    assert len(mod.declarations) == 2

    c1, c2 = mod.declarations
    assert isinstance(c1, ConstDecl)
    assert c1.name == "GLOBAL_CONSTANT"
    assert c1.type_annotation is None
    assert isinstance(c1.value, IntLit) and c1.value.value == 100

    assert isinstance(c2, ConstDecl)
    assert c2.name == "PI"
    assert c2.type_annotation == NamedType("double", span=c2.type_annotation.span)  # type: ignore[union-attr]


def test_echo_declaration() -> None:
    """Verify transparent type aliases."""
    code = (
        "echo Entity = int\necho Callback = function<(int) -> void>\necho Pair<T> = tuple<T, T>\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 3

    e1, e2, e3 = mod.declarations
    assert isinstance(e1, EchoDecl)
    assert e1.name == "Entity"
    assert e1.type_params == []
    assert e1.target_type == NamedType("int", span=e1.target_type.span)

    assert isinstance(e2, EchoDecl)
    assert e2.name == "Callback"
    assert isinstance(e2.target_type, FnType)
    assert len(e2.target_type.param_types) == 1
    assert e2.target_type.return_type == NamedType("void", span=e2.target_type.return_type.span)  # type: ignore[union-attr]

    assert isinstance(e3, EchoDecl)
    assert e3.name == "Pair"
    assert e3.type_params == ["T"]


def test_seal_declaration() -> None:
    """Verify opaque newtypes."""
    code = "seal UserId = int\nseal Wrapper<T> = T\n"
    mod = parse(code)
    assert len(mod.declarations) == 2

    s1, s2 = mod.declarations
    assert isinstance(s1, SealDecl)
    assert s1.name == "UserId"
    assert s1.type_params == []

    assert isinstance(s2, SealDecl)
    assert s2.name == "Wrapper"
    assert s2.type_params == ["T"]


def test_rune_declaration() -> None:
    """Verify runes with fields, defaults, inheritance, and generics."""
    code = (
        "rune Point\n"
        "  x: double\n"
        "  y: double = 0.0\n"
        "rune Dog heir Animal\n"
        "  breed: string\n"
        "rune Container<T> heir Animal<T>\n"
        "  payload: T\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 3

    r1, r2, r3 = mod.declarations
    assert isinstance(r1, RuneDecl)
    assert r1.name == "Point"
    assert r1.parent is None
    assert len(r1.fields) == 2
    assert r1.fields[0] == RuneField(
        name="x",
        type_annotation=NamedType("double", span=r1.fields[0].type_annotation.span),
        default_value=None,
        span=r1.fields[0].span,
    )
    assert r1.fields[1].default_value is not None

    assert isinstance(r2, RuneDecl)
    assert r2.name == "Dog"
    assert r2.parent == NamedType("Animal", span=r2.parent.span)  # type: ignore[union-attr]
    assert len(r2.fields) == 1

    assert isinstance(r3, RuneDecl)
    assert r3.name == "Container"
    assert r3.type_params == ["T"]
    assert isinstance(r3.parent, NamedType)
    assert r3.parent.name == "Animal"


def test_enchanting_declaration() -> None:
    """Verify empty enchanting block."""
    code = "enchanting Point\n  pass\n"
    mod = parse(code)
    assert len(mod.declarations) == 1
    enc = mod.declarations[0]
    assert isinstance(enc, EnchantingDecl)
    assert enc.target_type == NamedType("Point", span=enc.target_type.span)
    assert enc.body is not None


def test_good_fixtures_phase4() -> None:
    """All good phase4 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase4"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase4 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert isinstance(result, Module), f"Failed for {file}"
        assert len(result.declarations) > 0, f"Expected statements in {file}"


def test_bad_fixtures_phase4() -> None:
    """All bad phase4 fixtures must raise syntax/parsing errors."""
    bad_dir = FIXTURES_DIR / "bad" / "phase4"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase4 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises((UnexpectedInput, DedentError)) as exc_info:
            parse(content)
        if isinstance(exc_info.value, UnexpectedInput):
            diag = diagnostic_from_exception(exc_info.value)
            assert diag.code in ("E1001", "E1002")
