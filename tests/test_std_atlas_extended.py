"""Tests for extended std/atlas.pengu module additions (0.14.1 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_extended(profile):
    """Verify all extended atlas helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_atlas_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas Extended ===" in res.stdout
    assert "length & predicates: OK" in res.stdout
    assert "access: OK" in res.stdout
    assert "mutation: OK" in res.stdout
    assert "bulk accessors: OK" in res.stdout
    assert "reductions: OK" in res.stdout
    assert "combination: OK" in res.stdout
    assert "filters: OK" in res.stdout
    assert "transformations: OK" in res.stdout
    assert "conversions: OK" in res.stdout
    assert "clear: OK" in res.stdout
    assert "direct enchanting methods: OK" in res.stdout
    assert "atlas extended: OK" in res.stdout
