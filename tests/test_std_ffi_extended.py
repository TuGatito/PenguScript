"""Tests for extended std/ffi.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_ffi_extended(profile):
    """Verify all extended ffi C interoperability helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_ffi_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"ffi_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "ffi extended: OK" in res.stdout
