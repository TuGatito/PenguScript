"""Unit tests for Phase 7 omens, flags omen, unsafe operations, and pointer dereferences."""

from __future__ import annotations

from pathlib import Path

import pytest
from lark.exceptions import UnexpectedInput

from penguscript.frontend.ast_nodes import (
    Assign,
    Binary,
    Block,
    CompoundAssign,
    DerefTarget,
    EnchantingDecl,
    EnumVariant,
    ExprStmt,
    FunctionLiteral,
    Ident,
    IntLit,
    MethodDecl,
    NamedType,
    OmenDecl,
    OmenVariant,
    OperatorDecl,
    SelfField,
    SelfFieldTarget,
    SelfRef,
    Unary,
    UnsafeBlock,
    VarTarget,
)
from penguscript.frontend.errors import diagnostic_from_exception
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_basic_omen_declaration() -> None:
    """Verify single-line and multi-line basic omen declarations."""
    code_single = "omen Color\n  Red, Green, Blue\n"
    mod_single = parse(code_single)
    assert len(mod_single.declarations) == 1
    d_single = mod_single.declarations[0]
    assert isinstance(d_single, OmenDecl)
    assert d_single.name == "Color"
    assert not d_single.is_flags
    assert d_single.underlying_type is None
    assert len(d_single.variants) == 3
    assert all(isinstance(v, OmenVariant) for v in d_single.variants)
    assert [v.name for v in d_single.variants] == ["Red", "Green", "Blue"]
    assert all(v.value is None for v in d_single.variants)

    code_multi = "omen Direction\n  North\n  South\n  East\n  West\n"
    mod_multi = parse(code_multi)
    assert len(mod_multi.declarations) == 1
    d_multi = mod_multi.declarations[0]
    assert isinstance(d_multi, OmenDecl)
    assert d_multi.name == "Direction"
    assert len(d_multi.variants) == 4
    assert [v.name for v in d_multi.variants] == ["North", "South", "East", "West"]


def test_omen_with_underlying_type_and_values() -> None:
    """Verify omen with underlying integer type and explicit values."""
    code = (
        "omen HttpStatus: uint16_t\n"
        "  Ok = 200\n"
        "  Created = 201\n"
        "  NotFound = 404\n"
        "  ServerError = 500\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, OmenDecl)
    assert d.name == "HttpStatus"
    assert d.underlying_type is not None
    assert isinstance(d.underlying_type, NamedType)
    assert d.underlying_type.name == "uint16_t"
    assert len(d.variants) == 4

    ok, created, not_found, server_err = d.variants
    assert ok.name == "Ok" and isinstance(ok.value, IntLit) and ok.value.value == 200
    assert (
        created.name == "Created"
        and isinstance(created.value, IntLit)
        and created.value.value == 201
    )
    assert (
        not_found.name == "NotFound"
        and isinstance(not_found.value, IntLit)
        and not_found.value.value == 404
    )
    assert (
        server_err.name == "ServerError"
        and isinstance(server_err.value, IntLit)
        and server_err.value.value == 500
    )


def test_empty_omen_with_pass() -> None:
    """Verify empty omen declaration using pass."""
    code = "omen Empty\n  pass\n"
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, OmenDecl)
    assert d.name == "Empty"
    assert d.variants == []


def test_flags_omen() -> None:
    """Verify flags omen declaration with shift and bitwise or values."""
    code = (
        "flags omen Permission: uint8_t\n"
        "  None = 0\n"
        "  Read = 1 << 0\n"
        "  Write = 1 << 1\n"
        "  Execute = 1 << 2\n"
        "  All = Permission::Read | Permission::Write | Permission::Execute\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, OmenDecl)
    assert d.name == "Permission"
    assert d.is_flags
    assert d.underlying_type is not None
    assert isinstance(d.underlying_type, NamedType)
    assert d.underlying_type.name == "uint8_t"
    assert len(d.variants) == 5

    none_v, read_v, write_v, exec_v, all_v = d.variants
    assert none_v.name == "None" and isinstance(none_v.value, IntLit) and none_v.value.value == 0
    assert read_v.name == "Read" and isinstance(read_v.value, Binary) and read_v.value.op == "<<"
    assert (
        write_v.name == "Write" and isinstance(write_v.value, Binary) and write_v.value.op == "<<"
    )
    assert exec_v.name == "Execute" and isinstance(exec_v.value, Binary) and exec_v.value.op == "<<"
    assert all_v.name == "All" and isinstance(all_v.value, Binary) and all_v.value.op == "|"


def test_flags_bitwise_operations() -> None:
    """Verify bitwise operators and compound assignments used with flags."""
    code = (
        "perms = Permission::Read | Permission::Write\n"
        "perms |= Permission::Execute\n"
        "perms &= ~Permission::Write\n"
        "toggled = perms ^ Permission::Read\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 4

    # perms = Read | Write
    a1 = mod.declarations[0]
    assert isinstance(a1, Assign)
    assert isinstance(a1.value, Binary)
    assert a1.value.op == "|"
    assert isinstance(a1.value.left, EnumVariant)
    assert isinstance(a1.value.right, EnumVariant)

    # perms |= Execute
    ca1 = mod.declarations[1]
    assert isinstance(ca1, CompoundAssign)
    assert ca1.op == "|="
    assert isinstance(ca1.value, EnumVariant)

    # perms &= ~Write
    ca2 = mod.declarations[2]
    assert isinstance(ca2, CompoundAssign)
    assert ca2.op == "&="
    assert isinstance(ca2.value, Unary)
    assert ca2.value.op == "~"

    # toggled = perms ^ Read
    a2 = mod.declarations[3]
    assert isinstance(a2, Assign)
    assert isinstance(a2.value, Binary)
    assert a2.value.op == "^"


def test_unsafe_functions_and_blocks() -> None:
    """Verify unsafe function declarations, unsafe blocks, and pointer dereferences."""
    code = (
        "unsafe write_u8 = (p: raw<uint8_t>, v: uint8_t) -> void\n"
        "  *p = v\n"
        "\n"
        "set_flag = (p: raw<uint8_t>) -> void\n"
        "  unsafe\n"
        "    write_u8(p, 1)\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 2

    fn1 = mod.declarations[0]
    assert isinstance(fn1, Assign)
    assert fn1.is_unsafe
    assert isinstance(fn1.value, FunctionLiteral)
    assert fn1.value.body is not None
    assert isinstance(fn1.value.body, Block)
    deref_stmt = fn1.value.body.statements[0]
    assert isinstance(deref_stmt, Assign)
    assert len(deref_stmt.targets) == 1
    assert isinstance(deref_stmt.targets[0], DerefTarget)
    assert isinstance(deref_stmt.targets[0].target, VarTarget)
    assert deref_stmt.targets[0].target.name == "p"

    fn2 = mod.declarations[1]
    assert isinstance(fn2, Assign)
    assert not fn2.is_unsafe
    assert isinstance(fn2.value, FunctionLiteral)
    assert fn2.value.body is not None
    assert isinstance(fn2.value.body, Block)
    unsafe_block = fn2.value.body.statements[0]
    assert isinstance(unsafe_block, UnsafeBlock)
    assert len(unsafe_block.body.statements) == 1


def test_unsafe_methods_and_operators() -> None:
    """Verify unsafe modifier on enchanting methods and operators."""
    code = (
        "enchanting Buffer\n"
        "  unsafe mut write = (val: uint8_t) -> void\n"
        "    *@ptr = val\n"
        "\n"
        "  unsafe operator + = (offset: int) -> raw<uint8_t>\n"
        "    @ptr + offset\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 1
    enc = mod.declarations[0]
    assert isinstance(enc, EnchantingDecl)
    assert len(enc.members) == 2

    m = enc.members[0]
    assert isinstance(m, MethodDecl)
    assert m.name == "write"
    assert m.is_unsafe
    assert m.is_mut
    assert m.function.body is not None
    assert isinstance(m.function.body, Block)
    first_stmt = m.function.body.statements[0]
    assert isinstance(first_stmt, Assign)
    assert isinstance(first_stmt.targets[0], DerefTarget)
    assert isinstance(first_stmt.targets[0].target, SelfFieldTarget)
    assert first_stmt.targets[0].target.name == "ptr"

    op = enc.members[1]
    assert isinstance(op, OperatorDecl)
    assert op.op == "+"
    assert op.is_unsafe
    assert not op.is_mut
    assert isinstance(op.function.body, Block)
    op_stmt = op.function.body.statements[0]
    assert isinstance(op_stmt, ExprStmt)
    assert isinstance(op_stmt.expr, Binary)
    assert isinstance(op_stmt.expr.left, SelfField)


def test_pointer_dereference_expressions_and_targets() -> None:
    """Verify pointer dereferencing in expressions, assignments, and compound assignments."""
    code = "val = *p\n*p = 10\n*p += 5\n**ptr = 42\n"
    mod = parse(code)
    assert len(mod.declarations) == 4

    # val = *p
    s1 = mod.declarations[0]
    assert isinstance(s1, Assign)
    assert isinstance(s1.value, Unary)
    assert s1.value.op == "*"
    assert isinstance(s1.value.operand, Ident)
    assert s1.value.operand.name == "p"

    # *p = 10
    s2 = mod.declarations[1]
    assert isinstance(s2, Assign)
    assert isinstance(s2.targets[0], DerefTarget)
    assert isinstance(s2.targets[0].target, VarTarget)
    assert s2.targets[0].target.name == "p"
    assert isinstance(s2.value, IntLit)
    assert s2.value.value == 10

    # *p += 5
    s3 = mod.declarations[2]
    assert isinstance(s3, CompoundAssign)
    assert isinstance(s3.target, DerefTarget)
    assert isinstance(s3.target.target, VarTarget)
    assert s3.target.target.name == "p"
    assert s3.op == "+="
    assert isinstance(s3.value, IntLit)
    assert s3.value.value == 5

    # **ptr = 42
    s4 = mod.declarations[3]
    assert isinstance(s4, Assign)
    assert isinstance(s4.targets[0], DerefTarget)
    inner_deref = s4.targets[0].target
    assert isinstance(inner_deref, DerefTarget)
    assert isinstance(inner_deref.target, VarTarget)
    assert inner_deref.target.name == "ptr"


def test_omen_enchanting() -> None:
    """Verify enchanting block on an omen with @ referring to current variant."""
    code = (
        "omen Color\n"
        "  Red, Green, Blue\n"
        "\n"
        "enchanting Color\n"
        "  is_warm = -> bool\n"
        "    @ == Color::Red\n"
    )
    mod = parse(code)
    assert len(mod.declarations) == 2
    omen = mod.declarations[0]
    assert isinstance(omen, OmenDecl)
    assert omen.name == "Color"

    enc = mod.declarations[1]
    assert isinstance(enc, EnchantingDecl)
    assert isinstance(enc.target_type, NamedType)
    assert enc.target_type.name == "Color"
    assert len(enc.members) == 1
    m = enc.members[0]
    assert isinstance(m, MethodDecl)
    assert m.name == "is_warm"
    assert m.function.body is not None
    assert isinstance(m.function.body, Block)
    stmt = m.function.body.statements[0]
    assert isinstance(stmt, ExprStmt)
    assert isinstance(stmt.expr, Binary)
    assert stmt.expr.op == "=="
    assert isinstance(stmt.expr.left, SelfRef)
    assert isinstance(stmt.expr.right, EnumVariant)
    assert stmt.expr.right.enum_name == "Color"
    assert stmt.expr.right.variant_name == "Red"


def test_good_fixtures_phase7() -> None:
    """All good phase7 fixtures must parse successfully."""
    good_dir = FIXTURES_DIR / "good" / "phase7"
    files = list(good_dir.glob("*.pengu"))
    assert files, "No good phase7 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        result = parse(content)
        assert result is not None, f"Failed to parse good fixture: {file.name}"


def test_bad_fixtures_phase7() -> None:
    """All bad phase7 fixtures must fail with a syntax error diagnostic."""
    bad_dir = FIXTURES_DIR / "bad" / "phase7"
    files = list(bad_dir.glob("*.pengu"))
    assert files, "No bad phase7 fixtures found"
    for file in files:
        content = file.read_text(encoding="utf-8")
        with pytest.raises(UnexpectedInput) as exc_info:
            parse(content)
        diag = diagnostic_from_exception(exc_info.value)
        assert diag.code in ("E1001", "E1002"), (
            f"Expected E1xxx code for {file.name}, got {diag.code}"
        )
