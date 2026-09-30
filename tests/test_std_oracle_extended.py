"""Tests for extended std/oracle.pengu module additions (0.14.2 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_oracle_extended(profile):
    """Verify all extended oracle helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_oracle_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"oracle_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Oracle Extended ===" in res.stdout
    assert "native maybe int: OK" in res.stdout
    assert "native maybe string: OK" in res.stdout
    assert "native maybe float: OK" in res.stdout
    assert "native maybe bool: OK" in res.stdout
    assert "bridge: OK" in res.stdout
    assert "describe: OK" in res.stdout
    assert "result: OK" in res.stdout
    assert "judge reimplementations: OK" in res.stdout
    assert "oracle extended: OK" in res.stdout
