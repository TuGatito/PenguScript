"""Tests for extended std/coven.pengu module additions (0.14.1 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_coven_extended(profile):
    """Verify all extended coven helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_coven_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"coven_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Coven Extended ===" in res.stdout
    assert "constructors & basic: OK" in res.stdout
    assert "string set algebra: OK" in res.stdout
    assert "string filters: OK" in res.stdout
    assert "int set basic: OK" in res.stdout
    assert "int set algebra: OK" in res.stdout
    assert "int reductions: OK" in res.stdout
    assert "coven extended: OK" in res.stdout
