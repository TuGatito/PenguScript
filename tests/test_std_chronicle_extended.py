"""Tests for extended std/chronicle.pengu module additions (0.14.1 system expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_chronicle_extended(profile):
    """Verify all extended chronicle helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_chronicle_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"chronicle_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Chronicle Extended ===" in res.stdout
    assert "utc getters: OK" in res.stdout
    assert "local getters: OK" in res.stdout
    assert "datetime rune: OK" in res.stdout
    assert "formatting and iso: OK" in res.stdout
    assert "day boundaries: OK" in res.stdout
    assert "arithmetic: OK" in res.stdout
    assert "calendar helpers: OK" in res.stdout
    assert "comparisons: OK" in res.stdout
    assert "durations: OK" in res.stdout
    assert "stopwatch: OK" in res.stdout
    assert "chronicle extended: OK" in res.stdout
