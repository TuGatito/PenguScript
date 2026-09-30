"""Tests for extended std/scrolls.pengu module additions (0.14.2 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_scrolls_extended(profile):
    """Verify all extended scrolls string methods in debug and release profiles."""
    source = (STD_PROGRAMS / "test_scrolls_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"scrolls_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Scrolls Extended ===" in res.stdout
    assert "case: OK" in res.stdout
    assert "search: OK" in res.stdout
    assert "whitespace: OK" in res.stdout
    assert "padding: OK" in res.stdout
    assert "modification: OK" in res.stdout
    assert "predicates: OK" in res.stdout
    assert "comparison: OK" in res.stdout
    assert "iteration: OK" in res.stdout
    assert "join: OK" in res.stdout
    assert "scrolls extended: OK" in res.stdout
