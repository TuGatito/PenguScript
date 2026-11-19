"""Sub-fase 7: Hardening, full error catalog coverage, determinism, and performance benchmarks."""

from __future__ import annotations

import time
from pathlib import Path

from penguscript.analysis import analyze_project
from penguscript.analysis.collector import collect
from penguscript.analysis.realms import compute_visibility, merge_realms
from penguscript.analysis.resolver import resolve_project
from penguscript.frontend.ast_nodes import Module
from penguscript.frontend.parser import parse

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "symbols"


def _check_snippet_codes(code: str, file_name: str = "snippet.pengu") -> list[str]:
    """Helper to parse, resolve, and extract diagnostic codes for a snippet."""
    path = Path("/workspace") / file_name
    mod: Module = parse(code)
    raw = collect(mod, path)
    realms, merge_diags = merge_realms({path: raw})
    annotated, vis_diags = compute_visibility({path: raw}, realms, None)

    proj_res = resolve_project({path: mod}, annotated, realms)
    all_diags = list(raw.diagnostics) + merge_diags + vis_diags + proj_res.diagnostics
    return [d.code for d in all_diags]


def test_diag_e2209_free_operator_collision() -> None:
    """Test E2209: free operator collides with enchanting operator on same first parameter type."""
    code = """realm geom

rune Point
    x: double

enchanting Point
    operator + = (other: Point) -> Point
        Point(@x + other.x)

operator + = (a: Point, b: Point) -> Point
    Point(a.x + b.x)
"""
    codes = _check_snippet_codes(code)
    assert "E2209" in codes


def test_diag_e2213_heir_target_not_a_rune() -> None:
    """Test E2213: inheritance target is not a rune (e.g. is an omen)."""
    code = """realm test

omen Status
    Active,
    Inactive

rune BadDerivation heir Status
    count: int
"""
    codes = _check_snippet_codes(code)
    assert "E2213" in codes


def test_diag_e2214_generic_rune_inherited_without_args() -> None:
    """Test E2214: generic rune inherited without type arguments."""
    code = """realm test

rune Container<T>
    val: T

rune IntBox heir Container
    extra: int
"""
    codes = _check_snippet_codes(code)
    assert "E2214" in codes


def test_diag_e2218_enchanting_generic_sigil_mismatch() -> None:
    """Test E2218: enchanting of generic rune has mismatched sigils."""
    code = """realm test

rune Box<T>
    val: T

enchanting Box<U>
    get_val = () -> int
        0
"""
    codes = _check_snippet_codes(code)
    assert "E2218" in codes


def test_diag_e2220_echo_alias_cycle() -> None:
    """Test E2220: cycle detected in type aliases."""
    code = """realm test

echo TypeA = TypeB
echo TypeB = TypeA
"""
    codes = _check_snippet_codes(code)
    assert "E2220" in codes


def test_diag_e2221_inheritance_cycle() -> None:
    """Test E2221: cycle detected in rune inheritance."""
    code = """realm test

rune NodeA heir NodeB
    a: int

rune NodeB heir NodeA
    b: int
"""
    codes = _check_snippet_codes(code)
    assert "E2221" in codes


def test_diagnostics_determinism() -> None:
    """Verify that analyzing a project yields identical and deterministic diagnostics."""
    bad_dir = FIXTURES_DIR / "resolve" / "bad"

    run1 = analyze_project(bad_dir)
    run2 = analyze_project(bad_dir)
    run3 = analyze_project(bad_dir)

    diags1 = [(d.code, str(d.source_file), d.span.line if d.span else 0) for d in run1.diagnostics]
    diags2 = [(d.code, str(d.source_file), d.span.line if d.span else 0) for d in run2.diagnostics]
    diags3 = [(d.code, str(d.source_file), d.span.line if d.span else 0) for d in run3.diagnostics]

    assert diags1 == diags2 == diags3
    assert len(diags1) > 0


def test_performance_benchmark_large_project(tmp_path: Path) -> None:
    """Benchmark: analyzing 30 synthetic modules takes well under 500 ms."""
    project_dir = tmp_path / "bench_project"
    project_dir.mkdir()

    # Generate 30 interrelated modules
    for i in range(30):
        mod_file = project_dir / f"mod_{i:02d}.pengu"
        dep = f"mod_{i - 1:02d}" if i > 0 else ""
        invoke_stmt = f'invoke "{dep}" as prev\n' if dep else ""
        code = f"""realm realm_{i:02d}

{invoke_stmt}
rune Data_{i:02d}
    id: int
    val: double

process_{i:02d} = (d: Data_{i:02d}) -> double
    d.val * 2.0
"""
        mod_file.write_text(code, encoding="utf-8")

    t0 = time.perf_counter()
    annotated = analyze_project(project_dir)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert annotated.has_errors is False
    assert len(annotated.modules) == 30
    assert elapsed_ms < 500.0, f"Analysis took {elapsed_ms:.2f} ms (expected < 500 ms)"


def test_all_catalog_codes_defined() -> None:
    """Verify catalog codes formatting convention (E2xxx errors and W2xxx warnings)."""
    import inspect

    import penguscript.analysis.collector
    import penguscript.analysis.imports
    import penguscript.analysis.realms
    import penguscript.analysis.resolver
    import penguscript.analysis.scope_checks

    modules = [
        penguscript.analysis.collector,
        penguscript.analysis.imports,
        penguscript.analysis.realms,
        penguscript.analysis.resolver,
        penguscript.analysis.scope_checks,
    ]

    import re

    pattern = re.compile(r'code=["\']([EW]2\d{3})["\']')
    found_codes: set[str] = set()

    for mod in modules:
        src = inspect.getsource(mod)
        for match in pattern.finditer(src):
            found_codes.add(match.group(1))

    # Verify standard groupings
    errors = {c for c in found_codes if c.startswith("E")}
    warnings = {c for c in found_codes if c.startswith("W")}

    assert len(errors) >= 30, f"Expected at least 30 error codes, found {len(errors)}"
    assert len(warnings) >= 8, f"Expected at least 8 warning codes, found {len(warnings)}"
    assert "E2001" in errors
    assert "E2301" in errors
    assert "W2301" in warnings
    assert "W2308" in warnings
