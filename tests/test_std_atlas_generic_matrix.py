"""Tests for std/atlas.pengu generic matrix (Plan B expansion).

Exercises:
  - enchanting map of shard K to shard V
  - map of string to string
  - map of int to int
  - map of float to string (arbitrary unspecialized combination)
  - map of int to float   (arbitrary unspecialized combination)
  - Empty maps, clone, copy, remove_all, rename_key, find_key_by_value, is_equal, put_all
"""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_generic_matrix(profile):
    """Verify Plan B generic enchanting over arbitrary map combinations."""
    source = (STD_PROGRAMS / "test_atlas_generic_matrix.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_matrix_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas Generic Matrix ===" in res.stdout
    assert "atlas_generic_matrix: OK" in res.stdout
