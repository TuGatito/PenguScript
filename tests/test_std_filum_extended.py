"""Tests for extended std/filum.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_filum_extended(profile):
    """Verify all extended filum helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_filum_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"filum_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Filum Extended ===" in res.stdout
    assert "version: OK" in res.stdout
    assert "mutex: OK" in res.stdout
    assert "waitgroup: OK" in res.stdout
    assert "once & cond: OK" in res.stdout
    assert "atomic_int: OK" in res.stdout
    assert "chan_int: OK" in res.stdout
    assert "chan_string: OK" in res.stdout
    assert "chan_float: OK" in res.stdout
    assert "chan_bool: OK" in res.stdout
    assert "system helpers: OK" in res.stdout
    assert "filum extended: OK" in res.stdout
