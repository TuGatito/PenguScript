"""Tests for extended std/arithmancy.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_arithmancy_extended(profile):
    """Verify all extended arithmancy linear algebra & math helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_arithmancy_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"arithmancy_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "arithmancy extended: OK" in res.stdout
