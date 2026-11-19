"""Integration tests for the complete analysis pipeline and CLI check command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from penguscript.analysis import analyze_project, analyze_text
from penguscript.cli import app

runner = CliRunner()
FIXTURES_RESOLVE_DIR = Path(__file__).parent.parent / "fixtures" / "symbols" / "resolve"


def test_analyze_project_good_fixtures() -> None:
    """Verify that analyzing a valid multi-file project produces a clean AnnotatedProject."""
    good_dir = FIXTURES_RESOLVE_DIR / "good"
    annotated = analyze_project(good_dir)

    assert annotated.has_errors is False
    assert len(annotated.diagnostics) == 0, [str(d) for d in annotated.diagnostics]
    assert "geom" in annotated.realms
    assert "animals" in annotated.realms

    # Check references and reverse references
    assert len(annotated.references) > 0
    assert len(annotated.symbols_to_refs) > 0


def test_analyze_project_bad_fixtures() -> None:
    """Verify that analyzing invalid code accurately reports errors."""
    bad_dir = FIXTURES_RESOLVE_DIR / "bad"
    annotated = analyze_project(bad_dir)

    assert annotated.has_errors is True
    codes = [d.code for d in annotated.diagnostics]
    assert "E2306" in codes  # @ outside method
    assert "E2307" in codes  # field does not exist
    assert "E2308" in codes  # method does not exist
    assert "E2309" in codes  # parent() outside constructor
    assert "E2310" in codes  # parent() in constructor without heir
    assert "E2311" in codes  # parent() not first statement


def test_analyze_text_in_memory() -> None:
    """Verify in-memory snippet analysis."""
    code = """realm math_demo

square = (x: int) -> int
    x * x
"""
    annotated = analyze_text(code)
    assert annotated.has_errors is False
    assert "math_demo" in annotated.realms
    assert "square" in annotated.realms["math_demo"].symbols


def test_cli_check_good_directory() -> None:
    """Verify CLI `pengu check` exits with 0 on valid project."""
    good_dir = FIXTURES_RESOLVE_DIR / "good"
    result = runner.invoke(app, ["check", str(good_dir)])
    assert result.exit_code == 0
    assert "check passed: 0 errors" in result.stdout


def test_cli_check_bad_directory() -> None:
    """Verify CLI `pengu check` exits with 1 on invalid code and displays diagnostics."""
    bad_dir = FIXTURES_RESOLVE_DIR / "bad"
    result = runner.invoke(app, ["check", str(bad_dir)])
    assert result.exit_code == 1
    assert "error[E2306]" in result.stdout
    assert "error[E2310]" in result.stdout
    assert "check failed with" in result.stdout


def test_cli_check_quiet_flag() -> None:
    """Verify CLI `pengu check --quiet` suppresses warnings."""
    good_dir = FIXTURES_RESOLVE_DIR / "good"
    result = runner.invoke(app, ["check", str(good_dir), "--quiet"])
    assert result.exit_code == 0
