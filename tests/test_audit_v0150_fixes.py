"""Regression tests for PenguScript 0.15.0 compiler audit fixes (C1-C9, I1-I10, etc.)."""

import pytest
from pathlib import Path
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_types import BaseType
from tests.conftest import (
    check_ok,
    check_error,
    compile_run,
    check_c_syntax,
    requires_runtime,
)


# ─── C1: _int_interp_spec duplicate decorator ─────────────────────────
class TestC1_IntInterpSpecDecorator:
    def test_staticmethod_is_callable(self):
        """_int_interp_spec is a callable static method without duplicate decorator."""
        assert callable(PenguCodegen._int_interp_spec)
        spec, cast = PenguCodegen._int_interp_spec(BaseType("i64"))
        assert spec == "%lld"
        assert cast == "long long"

        spec_u, cast_u = PenguCodegen._int_interp_spec(BaseType("u64"))
        assert spec_u == "%llu"
        assert cast_u == "unsigned long long"


# ─── C2: field_access over maybe field emits payload cast ─────────────
class TestC2_FieldAccessMaybeCast:
    @requires_runtime
    def test_nested_rune_maybe_field_value_cast(self):
        """field_access on composite rune.maybe.value properly emits cast."""
        code = """
import std.spark

rune Inner:
    m as maybe int

rune Outer:
    inner as Inner

weave main into int:
    var inn as Inner with:
        set .m is some 123
    var o as Outer with:
        set .inner is inn
    if o.inner.m is present:
        var v as int is o.inner.m.value
        calling spark.println with "{v}"
    return 0
"""
        res = compile_run(code, tag="test_c2_nested")
        assert res.stdout.strip() == "123"


# ─── C3: list.push/contains/index_of evaluates argument only once ─────
class TestC3_ListArgSingleEvaluation:
    @requires_runtime
    def test_push_side_effects_once(self):
        """Calling push with an expression evaluates the expression exactly once."""
        code = """
import std.spark

weave gen into string:
    static var gen_count as int is 0
    set gen_count is gen_count + 1
    calling spark.println with "GEN CALLED"
    return "item"

weave main into int:
    var xs as list of string is list of string
    calling xs.push with (calling gen)
    return 0
"""
        res = compile_run(code, tag="test_c3_push")
        assert res.stdout.count("GEN CALLED") == 1

    @requires_runtime
    def test_contains_side_effects_once(self):
        """Calling contains with an expression evaluates the expression exactly once."""
        code = """
import std.spark

weave gen into string:
    static var gen_count as int is 0
    set gen_count is gen_count + 1
    calling spark.println with "GEN CALLED"
    return "item"

weave main into int:
    var xs as list of string is list of string
    calling xs.push with "item"
    let has is calling xs.contains with (calling gen)
    return 0
"""
        res = compile_run(code, tag="test_c3_contains")
        assert res.stdout.count("GEN CALLED") == 1


# ─── C4: Algebraic omens without derive Nexus emit cleanup helpers ────
class TestC4_AlgebraicOmenNexus:
    @requires_runtime
    def test_algebraic_omen_list_cleanup_and_clone(self):
        """Algebraic omens with heap payloads automatically emit cleanup/clone for lists."""
        code = """
import std.spark

omen Event:
    Msg with text as string

weave main into int:
    var l as list of Event is list of Event
    let ev as Event is with text is "hello"
    calling l.push with ev
    calling spark.println with "OK"
    return 0
"""
        res = compile_run(code, tag="test_c4_run")
        assert res.stdout.strip() == "OK"



