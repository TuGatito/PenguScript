"""Tests for extended std/rites.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_rites_extended(profile):
    """Verify all extended rites helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_rites_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"rites_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Rites Extended ===" in res.stdout
    assert "version: OK" in res.stdout
    assert "env accessors: OK" in res.stdout
    assert "bulk env: OK" in res.stdout
    assert "expand env: OK" in res.stdout
    assert "arguments: OK" in res.stdout
    assert "process & directories: OK" in res.stdout
    assert "platform info: OK" in res.stdout
    assert "which search: OK" in res.stdout
    assert "rites extended: OK" in res.stdout
