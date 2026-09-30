"""Tests for extended std/parchment.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_parchment_extended(profile):
    """Verify all extended parchment XML/HTML DOM helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_parchment_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"parchment_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "parchment extended: OK" in res.stdout
