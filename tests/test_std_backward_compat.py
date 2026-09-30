"""Backward compatibility test verifying legacy std/tally, std/atlas, std/coven APIs."""
import pytest
from tests.conftest import compile_run, requires_runtime

SOURCE_LEGACY = """import std.tally
import std.atlas
import std.coven
import std.spark

weave main into int:
    # --- Legacy std.tally ---
    var xs as list of int is list of int
    calling spark.assert with calling tally.is_empty with xs
    calling xs.push with 5
    calling xs.push with 10
    calling spark.assert with (calling tally.sum with xs) == 15
    calling spark.assert with (calling tally.is_empty with xs) == false
    calling spark.assert with (calling tally.max_val with xs) == 10
    calling spark.assert with (calling tally.min_val with xs) == 5

    # --- Legacy std.atlas ---
    var m as map of string to int is map of string to int
    calling m.put with "a", 1
    calling spark.assert with (calling atlas.map_len_str_int with m) == 1

    # --- Legacy std.coven (SetString) ---
    var s as coven.SetString is calling coven.new_set_string
    calling spark.assert with calling s.is_empty
    calling spark.assert with (calling s.len) == 0
    calling s.add with "hi"
    calling spark.assert with calling s.contains with "hi"
    calling spark.assert with (calling s.len) == 1
    calling spark.assert with (calling s.is_empty) == false
    calling spark.assert with calling s.remove with "hi"
    calling spark.assert with (calling s.len) == 0
    calling s.add with "hello"
    calling s.clear
    calling spark.assert with calling s.is_empty

    # --- Legacy std.coven (SetInt) ---
    var si as coven.SetInt is calling coven.new_set_int
    calling spark.assert with calling si.is_empty
    calling spark.assert with (calling si.len) == 0
    calling si.add with 42
    calling spark.assert with calling si.contains with 42
    calling spark.assert with (calling si.len) == 1
    calling spark.assert with calling si.remove with 42
    calling spark.assert with (calling si.len) == 0

    calling spark.println with "backward compat: OK"
    return 0
"""


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_std_backward_compat(profile):
    """Ensure pre-expansion 0.14.x stdlib API continues to compile and execute."""
    res = compile_run(SOURCE_LEGACY, tag=f"backward_compat_{profile}", profile=profile)
    assert res.returncode == 0
    assert "backward compat: OK" in res.stdout
