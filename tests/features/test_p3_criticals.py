"""Tests for P3 criticals (C1 binding qualified bare variants, C2 interpolation diagnostics, C3 parameter restrict)."""

import pytest
from tests.conftest import (
    compile_run,
    gen_bundle,
    requires_cc,
    requires_runtime,
)


# ==========================================================================
# C1 — Module-qualified bare binding variants (module.VARIANT)
# ==========================================================================


class TestBindingOmenVariants:
    """Omen variants declared in PenguScript emit their prefixed C identifiers."""

    def test_pengu_declared_omen_keeps_prefixed_c_name(self):
        """Omens declared in PenguScript (non-binding) keep their prefixed C names."""
        src = (
            "omen Color:\n"
            "    Rojo\n"
            "    Verde\n\n"
            "weave main into int:\n"
            "    var c as Color is Color.Rojo\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "Color_Rojo" in c_code
        assert "Color c = Color_Rojo;" in c_code



# ==========================================================================
# C2 — Interpolation diagnostics ({...} inside string literals)
# ==========================================================================


class TestInterpolationDiagnostics:
    """Non-PenguScript content inside regular string braces reports clear diagnostics pointing to raw strings."""

    def test_glsl_string_with_braces_reports_helpful_error(self):
        """GLSL string with braces reports error pointing to literal's line and mentions raw strings."""
        from pengu_parser.pengu_errors import SemanticError
        from tests.conftest import check_ok

        src = (
            "weave main into int:\n"
            '    var vs as string is "#version 330\\nvoid main() { gl_Position = vec4(0.0); }"\n'
            "    return 0\n"
        )
        with pytest.raises(SemanticError) as exc_info:
            check_ok(src)
        err = exc_info.value
        assert err.line == 2
        assert err.code == "E0019"
        assert err.help is not None
        assert 'r"""' in err.help
        assert "raw string" in err.help

    @requires_cc
    @requires_runtime
    def test_glsl_in_raw_string_builds_and_runs(self):
        """r\"\"\"...{...}...\"\"\" with the same shader content compiles and executes."""
        src = (
            "weave main into int:\n"
            '    var vs as string is r"""#version 330\nvoid main() { gl_Position = vec4(0.0); }\n"""\n'
            "    return 0\n"
        )
        res = compile_run(src, tag="c2_glsl_raw")
        assert res.returncode == 0

    @requires_cc
    @requires_runtime
    def test_valid_string_interpolation_builds_and_runs(self):
        """Valid interpolation 'score: {x}' compiles and runs with expected value."""
        src = (
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var x as int is 42\n"
            '    var s as string is "score: {x}"\n'
            "    calling spark.print with s\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="c2_valid_interp")
        assert res.returncode == 0
        assert "score: 42" in res.stdout

    def test_invalid_syntax_interpolation_reports_error(self):
        """Interpolation with invalid expression like '{1 +}' reports E0019 with raw string hint."""
        from pengu_parser.pengu_errors import SemanticError
        from tests.conftest import check_ok

        src = (
            "weave main into int:\n"
            '    var s as string is "val: {1 +}"\n'
            "    return 0\n"
        )
        with pytest.raises(SemanticError) as exc_info:
            check_ok(src)
        err = exc_info.value
        assert err.line == 2
        assert err.code == "E0019"
        assert err.help is not None
        assert 'r"""' in err.help


# ==========================================================================
# C3 — Drop restrict qualifier on generated parameters
# ==========================================================================


class TestNoRestrictInGeneratedParams:
    """Generated function prototypes and definitions do not emit restrict qualifiers on ref parameters or self."""

    def test_weave_with_ref_params_has_no_restrict(self):
        """weave with two ref parameters generates pointer parameters without restrict."""
        src = (
            "rune Buffer:\n"
            "    len as int\n\n"
            "weave swap_bufs with a as ref to Buffer, b as ref to Buffer into void:\n"
            "    return\n\n"
            "weave main into int:\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "void swap_bufs(Buffer* a, Buffer* b);" in c_code
        assert "void swap_bufs(Buffer* a, Buffer* b) {" in c_code
        assert "restrict" not in c_code

    def test_enchanting_self_has_no_restrict(self):
        """enchanting generates self pointer parameter without restrict."""
        src = (
            "rune Point:\n"
            "    x as int\n"
            "    y as int\n\n"
            "enchanting Point:\n"
            "    weave move with dx as int, dy as int into void:\n"
            "        set self->x is self->x + dx\n"
            "        set self->y is self->y + dy\n"
            "        return\n\n"
            "weave main into int:\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "void Point_move(Point* self, int32_t dx, int32_t dy);" in c_code
        assert "void Point_move(Point* self, int32_t dx, int32_t dy) {" in c_code
        assert "restrict" not in c_code

    def test_ctype_mapper_still_supports_restrict_opt_in(self):
        """CTypeMapper.to_c_decl retains restrict=True opt-in capability."""
        from pengu_parser.pengu_codegen import CTypeMapper
        from pengu_parser.pengu_types import RefType, INT_TYPE

        t = RefType(INT_TYPE)
        decl_no_restrict = CTypeMapper.to_c_decl(t, "p", restrict=False)
        assert decl_no_restrict == "int32_t* p"

        decl_with_restrict = CTypeMapper.to_c_decl(t, "p", restrict=True)
        assert decl_with_restrict == "int32_t* restrict p"


