"""Tests for extended std/whisper.pengu module additions (0.15.0 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.timeout(30)
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_whisper_extended(profile):
    """Verify all extended whisper helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_whisper_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"whisper_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Whisper Extended ===" in res.stdout
    assert "constants: OK" in res.stdout
    assert "level parsing: OK" in res.stdout
    assert "global logger: OK" in res.stdout
    assert "instance logger: OK" in res.stdout
    assert "file target: OK" in res.stdout
    assert "whisper extended: OK" in res.stdout
