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
