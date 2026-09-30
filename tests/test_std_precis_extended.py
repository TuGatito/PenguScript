"""Tests for extended std/precis.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_precis_extended(profile):
    """Verify all extended precis HTTP client/server helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_precis_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"precis_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "precis extended: OK" in res.stdout
