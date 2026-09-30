#!/usr/bin/env python3
"""Tests for extended std.compass module in debug and release profiles."""

from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_compass_extended(profile):
    """Verify all extended compass functions and Path methods across profiles."""
    source = (STD_PROGRAMS / "test_compass_extended.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"compass_ext_{profile}", profile=profile)
    assert res.returncode == 0
    assert "compass extended: OK" in res.stdout
