#!/usr/bin/env python3
"""
Regression tests for the 7 compiler bugs documented in CHANGELOG.md
under '## [0.15.0] - Unreleased -> Compiler bugs found (documented, not fixed)'.

Each test targets ONE bug and fails without the corresponding fix.
"""
from pathlib import Path
import pytest
from tests.conftest import (
    compile_run,
    bundle_project,
    check_c_syntax,
    REPO,
    requires_runtime,
    requires_cc,
)

STD_PROGRAMS = REPO / "tests" / "std_programs"


# ─── Bug 7 — Global symbol shadows local in `set` target ───────────────
class TestBug7_LocalShadowsGlobal:
    @requires_runtime
    def test_local_list_wins_over_global_int(self):
        # std.invoke exports a variable idx:int; here we declare a local
        # idx:list of int and execute set idx at 0 is 42.
        src = """
import std.spark
import std.invoke

weave main into int:
    var idx as list of int is [0, 0, 0]
    set idx at 0 is 42
    calling spark.println with "{idx at 0}"
    return 0
"""
        res = compile_run(src, tag="bug7_local_wins")
        assert res.stdout.strip() == "42"

    @requires_runtime
    def test_atlas_values_sorted_of_string_int_compiles(self):
        source = (STD_PROGRAMS / "test_invoke_extended.pengu").read_text(encoding="utf-8")
        res = compile_run(source, tag="bug7_invoke_ext")
        assert "invoke extended: OK" in res.stdout
