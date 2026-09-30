"""Tests for extended std/tally.pengu module additions (0.14.1 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_tally_extended(profile):
    """Verify all extended tally helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_tally_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"tally_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Tally Extended ===" in res.stdout
    assert "length & access: OK" in res.stdout
    assert "search: OK" in res.stdout
    assert "reductions: OK" in res.stdout
    assert "statistics: OK" in res.stdout
    assert "transformations: OK" in res.stdout
    assert "selection: OK" in res.stdout
    assert "combination: OK" in res.stdout
    assert "predicates: OK" in res.stdout
    assert "filters: OK" in res.stdout
    assert "mappings: OK" in res.stdout
    assert "tally extended: OK" in res.stdout
