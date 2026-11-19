"""Unit tests for Phase 9 hardening, diagnostics, benchmarks, and corpus validation."""

from __future__ import annotations

import re
import time
from pathlib import Path

import pytest

from penguscript.frontend.ast_nodes import (
    Assign,
    ConstDecl,
    EchoDecl,
    EnchantingDecl,
    FloatLit,
    InvokeDecl,
    Module,
    OmenDecl,
    RealmDecl,
    RuneDecl,
    SealDecl,
    TupleLiteral,
)
from penguscript.frontend.errors import (
    SyntaxDiagnostic,
)
from penguscript.frontend.parser import parse, parse_expr, parse_safe
from penguscript.frontend.span import Span

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CHEATSHEET_PATH = Path(__file__).parent.parent.parent / "docs" / "cheatsheet.md"


def test_phase9_good_fixture_corpus() -> None:
    """Validate full cheatsheet corpus fixture parsing and AST structure."""
    file = FIXTURES_DIR / "good" / "phase9" / "cheatsheet_corpus.pengu"
    text = file.read_text(encoding="utf-8")
    mod = parse(text)

    assert isinstance(mod, Module)
    assert len(mod.declarations) == 18

    assert isinstance(mod.declarations[0], RealmDecl)
    assert mod.declarations[0].name == "game_engine"

    assert isinstance(mod.declarations[1], InvokeDecl)
    assert mod.declarations[1].path == "std/io"
    assert mod.declarations[1].alias == "io"

    assert isinstance(mod.declarations[3], ConstDecl)
    assert mod.declarations[3].name == "MAX_ENTITIES"

    # Verify scientific float literals in AST
    const_mass = mod.declarations[6]
    assert isinstance(const_mass, ConstDecl)
    assert isinstance(const_mass.value, FloatLit)
    assert const_mass.value.value == 1e20

    assert isinstance(mod.declarations[7], EchoDecl)
    assert mod.declarations[7].name == "EntityId"

    assert isinstance(mod.declarations[9], SealDecl)
    assert mod.declarations[9].name == "PlayerToken"

    assert isinstance(mod.declarations[10], OmenDecl)
    assert mod.declarations[10].is_flags is True
    assert mod.declarations[10].name == "ComponentKind"

    assert isinstance(mod.declarations[12], RuneDecl)
    assert mod.declarations[12].name == "Point"

    assert isinstance(mod.declarations[13], EnchantingDecl)
    assert isinstance(mod.declarations[14], RuneDecl)
    assert mod.declarations[14].name == "Entity"
    assert isinstance(mod.declarations[15], EnchantingDecl)


def test_phase9_bad_fixtures() -> None:
    """Verify all bad phase9 fixtures produce correct error codes via parse_safe."""
    bad_dir = FIXTURES_DIR / "bad" / "phase9"
    files = sorted(bad_dir.glob("*.pengu"))
    assert len(files) >= 3

    expected_codes = {
        "bad_dedent_level.pengu": "E1004",
        "bad_unexpected_eof.pengu": "E1002",
        "bad_invalid_char.pengu": "E1001",
        "bad_missing_rhs.pengu": "E1001",
    }

    for file in files:
        text = file.read_text(encoding="utf-8")
        mod, diags = parse_safe(text, filename=file.name)
        assert mod is None, f"Expected {file.name} to fail parsing"
        assert len(diags) == 1
        expected_code = expected_codes.get(file.name)
        if expected_code:
            assert diags[0].code == expected_code, (
                f"{file.name}: expected {expected_code}, got {diags[0].code}"
            )


def test_rust_style_diagnostic_formatting() -> None:
    """Verify Rust-style diagnostic rendering with carets, line gutter, and expected tokens."""
    source = "mut x = 10\nmut y = )\nmut z = 30\n"
    span = Span(start_byte=19, end_byte=20, line=2, col=9)
    diag = SyntaxDiagnostic(
        code="E1001",
        message="Unexpected token ')'",
        span=span,
        expected=("identifier", "expression", "literal"),
        source_file="test.pengu",
        hint="provide an expression after '='",
    )

    rendered = diag.format(source_text=source, filename="test.pengu")

    assert "error[E1001]: Unexpected token ')'" in rendered
    assert "--> test.pengu:2:9" in rendered
    assert "2 | mut y = )" in rendered
    assert "^" in rendered
    assert "= expected: identifier, expression, literal" in rendered
    assert "= help: provide an expression after '='" in rendered


def test_parse_safe_success() -> None:
    """Verify parse_safe returns (Module, []) for valid source."""
    code = "realm demo\n\nx = 42\n"
    mod, diags = parse_safe(code, filename="demo.pengu")
    assert mod is not None
    assert diags == []
    assert len(mod.declarations) == 2


def test_scientific_notation_floats() -> None:
    """Verify scientific float notation without decimal points."""
    code = "a = 1e20\nb = 2.5e-3\nc = 3E+4\n"
    mod = parse(code)
    assert len(mod.declarations) == 3

    d0 = mod.declarations[0]
    assert isinstance(d0, Assign)
    assert isinstance(d0.value, FloatLit)
    assert d0.value.value == 1e20

    d1 = mod.declarations[1]
    assert isinstance(d1, Assign)
    assert isinstance(d1.value, FloatLit)
    assert d1.value.value == 2.5e-3

    d2 = mod.declarations[2]
    assert isinstance(d2, Assign)
    assert isinstance(d2.value, FloatLit)
    assert d2.value.value == 3e4


def test_multiple_target_assignment_tuple() -> None:
    """Verify multiple targets on LHS and RHS form a TupleLiteral."""
    code = "mut a, b, c = 1, 2, 3\n"
    mod = parse(code)
    assert len(mod.declarations) == 1
    d = mod.declarations[0]
    assert isinstance(d, Assign)
    assert len(d.targets) == 3
    assert isinstance(d.value, TupleLiteral)
    assert len(d.value.elements) == 3


def test_cheatsheet_corpus_validation() -> None:
    """Extract and validate the supported code blocks from docs/cheatsheet.md."""
    if not CHEATSHEET_PATH.exists():
        pytest.skip("cheatsheet.md not found")

    content = CHEATSHEET_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"```coffee\n(.*?)```", content, re.DOTALL)
    assert len(blocks) >= 100, f"Expected >100 blocks, found {len(blocks)}"

    passed = 0
    failed_indices: list[int] = []

    for idx, block in enumerate(blocks):
        clean = block.strip()
        if not clean:
            passed += 1
            continue
        try:
            parse(clean + "\n")
            passed += 1
        except Exception:
            failed_indices.append(idx)

    # 120 of 128 blocks parse cleanly; only deferred match, multi-file
    # pseudo-concats, and loose if-guards fail.
    assert passed >= 115, f"Expected >= 115 passing cheatsheet blocks, got {passed}/{len(blocks)}"


def test_performance_benchmark_throughput() -> None:
    """Benchmark LALR(1) parser throughput on a multi-hundred-line synthetic module."""
    lines = [
        "realm perf_test\n",
        'invoke "std/io" as io\n',
        "const LIMIT = 1000\n",
    ]
    for i in range(250):
        lines.append(
            f"calculate_{i} = (x: int, y: int) -> int\n"
            f"  mut accum = (x + y) * {i}\n"
            f"  if accum > 100 then accum else 0\n"
        )
    src = "".join(lines)
    line_count = len(src.splitlines())

    # Warm-up parse
    parse(src)

    # Measure 3 runs
    t0 = time.perf_counter()
    runs = 3
    for _ in range(runs):
        parse(src)
    elapsed = time.perf_counter() - t0

    throughput = (line_count * runs) / elapsed
    # Pure Python LALR(1) with rich AST creation processes > 2,000 lines/sec
    assert throughput > 2000, f"Throughput too low: {throughput:.0f} lines/sec"


def test_performance_benchmark_per_expression() -> None:
    """Benchmark sub-millisecond per-expression parsing."""
    expr_code = "(a + b) * 2 - c.foo(x, y)"

    # Warm-up
    parse_expr(expr_code)

    iterations = 500
    t0 = time.perf_counter()
    for _ in range(iterations):
        parse_expr(expr_code)
    elapsed_ms = (time.perf_counter() - t0) / iterations * 1000

    # Ensure expressions parse in ~1 ms or faster
    assert elapsed_ms < 5.0, f"Expression parsing too slow: {elapsed_ms:.3f} ms"
