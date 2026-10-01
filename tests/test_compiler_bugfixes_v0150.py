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


# ─── Bug 1 — _resolve_call_target splits at `_` ────────────────────────
class TestBug1_GenericModuleWeaveResolution:
    @requires_runtime
    def test_map_size_does_not_match_enchanted_size(self):
        """map_size does not collide with method size."""
        src = """
import std.spark
import std.atlas

weave main into int:
    var m as map of string to int is map of string to int
    calling m.put with "a", 1
    calling m.put with "b", 2
    let sz is calling atlas.map_size of string and int with m
    calling spark.println with "{sz}"
    return 0
"""
        res = compile_run(src, tag="bug1_map_size")
        assert res.stdout.strip() == "2"

    @requires_runtime
    def test_module_weave_and_method_coexist(self):
        """Method m.size and module weave atlas.map_size coexist without polluting monomorphized_methods."""
        src = """
import std.spark
import std.atlas

weave main into int:
    var m as map of string to int is map of string to int
    calling m.put with "x", 10
    let a is calling m.size
    let b is calling atlas.map_size of string and int with m
    calling spark.println with "{a} {b}"
    return 0
"""
        res = compile_run(src, tag="bug1_coexist")
        assert res.stdout.strip() == "1 1"

    def test_unqualified_map_size_c_syntax(self):
        src = """
import std.atlas
weave test_fn with m as map of string to int into int:
    return calling map_size with m
"""
        b = bundle_project(src, tag="bug1_unqual")
        check_c_syntax(b)

