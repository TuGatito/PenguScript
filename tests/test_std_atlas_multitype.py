"""Tests for multi-type std/atlas.pengu expansions (0.15.0 expansion).

Covers:
  - map of string to string (test_atlas_ss.pengu)
  - map of string to float  (test_atlas_sf.pengu)
  - map of int to int       (test_atlas_ii.pengu)
  - map of int to string    (test_atlas_is.pengu)
  - map of string to bool   (test_atlas_sb.pengu)
"""
from pathlib import Path
import pytest
from tests.conftest import compile_run, requires_runtime

STD_PROGRAMS = Path(__file__).resolve().parent / "std_programs"


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_string_string(profile):
    """Verify map of string to string enchanting, wrappers and generic ops."""
    source = (STD_PROGRAMS / "test_atlas_ss.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_ss_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas (String -> String) ===" in res.stdout
    assert "atlas_ss: OK" in res.stdout


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_string_float(profile):
    """Verify map of string to float enchanting, wrappers and generic ops."""
    source = (STD_PROGRAMS / "test_atlas_sf.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_sf_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas (String -> Float) ===" in res.stdout
    assert "atlas_sf: OK" in res.stdout


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_int_int(profile):
    """Verify map of int to int enchanting, wrappers and generic ops."""
    source = (STD_PROGRAMS / "test_atlas_ii.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_ii_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas (Int -> Int) ===" in res.stdout
    assert "atlas_ii: OK" in res.stdout


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_int_string(profile):
    """Verify map of int to string enchanting, wrappers and generic ops."""
    source = (STD_PROGRAMS / "test_atlas_is.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_is_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas (Int -> String) ===" in res.stdout
    assert "atlas_is: OK" in res.stdout


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_atlas_string_bool(profile):
    """Verify map of string to bool enchanting, wrappers and generic ops."""
    source = (STD_PROGRAMS / "test_atlas_sb.pengu").read_text(encoding="utf-8")
    res = compile_run(source, tag=f"atlas_sb_{profile}", profile=profile)
    assert res.returncode == 0
    assert "=== Test Atlas (String -> Bool) ===" in res.stdout
    assert "atlas_sb: OK" in res.stdout
