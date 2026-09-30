"""Regression test verifying generic type parameter substitution during AST conversion in pengu_codegen.py."""
import pytest
from tests.conftest import compile_run, requires_runtime

SOURCE_GENERIC_SUBST = """import std.spark

# Function with a generic parameter used in a local container constructor
weave wrap_in_list shard T with x as T into list of T:
    var r as list of T is list of T
    calling r.push with x
    return r

weave main into int:
    var xs as list of string is calling wrap_in_list of string with "hello"
    calling spark.assert with (xs.len == 1)
    calling spark.assert with ((xs at 0) == "hello")

    var ints as list of int is calling wrap_in_list of int with 42
    calling spark.assert with (ints.len == 1)
    calling spark.assert with ((ints at 0) == 42)

    calling spark.println with "generic subst: OK"
    return 0
"""


@requires_runtime
@pytest.mark.parametrize("profile", ["debug", "release"])
def test_codegen_generic_subst(profile):
    """Ensure generic type parameters resolve correctly in function bodies during monomorphization."""
    res = compile_run(SOURCE_GENERIC_SUBST, tag=f"gen_subst_{profile}", profile=profile)
    assert res.returncode == 0
    assert "generic subst: OK" in res.stdout
