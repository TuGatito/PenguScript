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

