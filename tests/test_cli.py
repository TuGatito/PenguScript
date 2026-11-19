"""Tests for the PenguScript CLI."""

from typer.testing import CliRunner

import penguscript
from penguscript.cli import app

runner = CliRunner()


def test_version() -> None:
    """Verify that --version outputs the package version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert penguscript.__version__ in result.stdout
    assert f"PenguScript {penguscript.__version__}" in result.stdout


def test_help() -> None:
    """Verify that --help exits cleanly and displays help information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "PenguScript compiler" in result.stdout
    assert "check" in result.stdout


def test_check_help() -> None:
    """Verify that `check --help` displays command options."""
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "--quiet" in result.stdout
