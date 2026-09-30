"""Tests for extended std/spark.pengu module additions (0.14.2 expansion)."""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_spark_extended(profile):
    """Verify all extended spark helpers in debug and release profiles."""
    source = (STD_PROGRAMS / "test_spark_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"spark_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Spark Extended ===" in res.stdout
    assert "versions: OK" in res.stdout
    assert "bool_to_string: OK" in res.stdout
    assert "scalar printing: OK" in res.stdout
    assert "ranges: OK" in res.stdout
    assert "math: OK" in res.stdout
    assert "spark extended: OK" in res.stdout
