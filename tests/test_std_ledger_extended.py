"""Tests for extended std/ledger.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_ledger_extended(profile):
    """Verify all extended ledger helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_ledger_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"ledger_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Ledger Extended ===" in res.stdout
    assert "constants: OK" in res.stdout
    assert "baseline: OK" in res.stdout
    assert "enhanced parsing: OK" in res.stdout
    assert "csv table: OK" in res.stdout
    assert "matrix enchantments: OK" in res.stdout
    assert "key-value conversions: OK" in res.stdout
    assert "generators & safe write: OK" in res.stdout
    assert "ledger extended: OK" in res.stdout
