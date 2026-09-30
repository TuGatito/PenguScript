"""Tests for extended std/loom.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_loom_extended(profile):
    """Verify all extended loom helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_loom_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"loom_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Loom Extended ===" in res.stdout
    assert "constants: OK" in res.stdout
    assert "baseline: OK" in res.stdout
    assert "reductions: OK" in res.stdout
    assert "predicates: OK" in res.stdout
    assert "transforms: OK" in res.stdout
    assert "set-like: OK" in res.stdout
    assert "search: OK" in res.stdout
    assert "structural: OK" in res.stdout
    assert "statistics: OK" in res.stdout
    assert "generics: OK" in res.stdout
    assert "loom extended: OK" in res.stdout
