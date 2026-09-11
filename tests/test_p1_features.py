"""Tests for P1 features (P1.3 array length, P1.2 struct arrays, P1.1 C varargs, P1.5 pointers, P1.4 raymath)."""

import pytest
from tests.conftest import (
    check_ok,
    check_error,
    gen_bundle,
    compile_run,
    requires_cc,
    requires_runtime,
    requires_lib,
    is_windows,
)


# ==========================================================================
# P1.3 — (xs length) for fixed-size arrays and collections
# ==========================================================================


class TestArrayLength:
    """Fixed-size arrays emit their compile-time size for (xs length)."""

    def test_array_param_codegen_literal(self):
        """Codegen emits integer literal for array length in parameter position."""
        src = (
            "weave f with xs as array of int with size 3 into int:\n"
            "    return (xs length)\n"
            "weave main into int:\n"
            "    var a as array of int with size 3 is [1, 2, 3]\n"
            "    return calling f with a\n"
        )
        c_code = gen_bundle(src)
        assert ("return (3);" in c_code) or ("return 3;" in c_code)

    @requires_cc
    @requires_runtime
    def test_array_length_local_and_param_runtime(self):
        """Length of local array and passed-in array evaluate to correct declared sizes."""
        src = (
            "import std.spark\n\n"
            "weave helper with xs as array of int with size 5 into int:\n"
            "    return (xs length)\n\n"
            "weave main into int:\n"
            "    var local_arr as array of int with size 4 is [10, 20, 30, 40]\n"
            "    var param_arr as array of int with size 5 is [1, 2, 3, 4, 5]\n"
            "    var len_local as int is (local_arr length)\n"
            "    var len_param as int is calling helper with param_arr\n"
            "    calling spark.println with \"local={len_local} param={len_param}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_arr_len")
        assert "local=4 param=5" in res.stdout

    @requires_cc
    @requires_runtime
    def test_slice_list_string_map_length(self):
        """Slice, list, string, and map continue returning their dynamic length."""
        src = (
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var s as string is \"hello\"\n"
            "    var arr as array of int with size 4 is [10, 20, 30, 40]\n"
            "    var sl as slice of int is arr at 0 to 2\n"
            "    var lst as list of int is list of int with capacity 10\n"
            "    calling lst.push with 1\n"
            "    calling lst.push with 2\n"
            "    calling lst.push with 3\n"
            "    var m as map of string to int is {\"a\": 1, \"b\": 2}\n"
            "    var s_len as int is (s length)\n"
            "    var sl_len as int is (sl length)\n"
            "    var lst_len as int is (lst length)\n"
            "    var m_len as int is (m length)\n"
            "    calling spark.println with \"s={s_len} sl={sl_len} lst={lst_len} m={m_len}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_col_len")
        assert "s=5 sl=2 lst=3 m=2" in res.stdout


# ==========================================================================
# P1.2 — E0011 struct arrays and index assignment
# ==========================================================================


class TestStructArrays:
    """Struct literals in array initializers and index assignments without spurious E0011."""

    @requires_cc
    @requires_runtime
    def test_struct_array_literal_init(self):
        """Array of raylib.Vector2 initialized with struct literals compiles and runs."""
        src = (
            "import std.raylib\n"
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var cs as array of raylib.Vector2 with size 2 is [(with x is 1.0, y is 2.0), (with x is 2.0, y is 3.0)]\n"
            "    var x0 as float is (cs at 0) . x\n"
            "    var y1 as float is (cs at 1) . y\n"
            "    calling spark.println with \"x0={x0} y1={y1}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_vec_arr")
        assert "x0=1" in res.stdout
        assert "y1=3" in res.stdout

    @requires_cc
    @requires_runtime
    def test_struct_array_index_assignment(self):
        """Reassigning struct array elements by index and field access works properly."""
        src = (
            "import std.raylib\n"
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var v as raylib.Vector2 is with x is 0.0, y is 0.0\n"
            "    var cs as array of raylib.Vector2 with size 4 is [v]\n"
            "    set cs at 0 is with x is 9.0, y is 9.0\n"
            "    set cs at 1 . x is 5.0\n"
            "    var x0 as float is (cs at 0) . x\n"
            "    var y0 as float is (cs at 0) . y\n"
            "    var x1 as float is (cs at 1) . x\n"
            "    calling spark.println with \"x0={x0} y0={y0} x1={x1}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_vec_assign")
        assert "x0=9" in res.stdout
        assert "y0=9" in res.stdout
        assert "x1=5" in res.stdout

    @requires_cc
    @requires_runtime
    def test_color_array_no_regression(self):
        """Array of raylib.Color continues working without regressions."""
        src = (
            "import std.raylib\n"
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var colors as array of raylib.Color with size 2 is [raylib.RED, raylib.BLUE]\n"
            "    calling spark.println with \"colors={colors length}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_color_arr")
        assert "colors=2" in res.stdout

    def test_real_ambiguity_e0011(self):
        """Truly ambiguous struct initialization with multiple distinct runes triggers E0011 without duplicates."""
        src = (
            "rune PointA:\n"
            "    x as float\n"
            "    y as float\n\n"
            "rune PointB:\n"
            "    x as float\n"
            "    y as float\n\n"
            "weave main into int:\n"
            "    var p is with x is 1.0, y is 2.0\n"
            "    return 0\n"
        )
        err = check_error(src, contains="Ambiguous struct init")
        assert "PointA" in err
        assert "PointB" in err
        # Verify no duplicate mentions
        assert "PointA, PointA" not in err
        assert "PointB, PointB" not in err


# ==========================================================================
# P1.1 — C Varargs: ... in declare + codegen + pengu_bind
# ==========================================================================


class TestCVarArgs:
    """C variadic functions with '...' in declare statements."""

    def test_varargs_codegen_no_slice(self):
        """Calling C varargs passes extra arguments directly without PenguSlice wrapping."""
        src = (
            "declare log_fmt with fmt as ref to frozen char, ... into void\n"
            "weave main into int:\n"
            "    calling log_fmt with \"a=%d b=%d\", 10, 20\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert 'log_fmt("a=%d b=%d", 10, 20)' in c_code
        assert "PenguSlice" not in c_code

    @requires_cc
    def test_varargs_compile_run_printf(self):
        """Compile and run C varargs function (printf from stdio.h)."""
        src = (
            'include "stdio.h"\n'
            "declare printf with fmt as ref to frozen char, ... into int\n"
            "weave main into int:\n"
            '    calling printf with "%d-%d\\n", 4, 2\n'
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_varargs_printf")
        assert "4-2" in res.stdout

    def test_varargs_min_arity_error(self):
        """Calling C varargs function with fewer arguments than fixed params triggers E0005."""
        from pengu_parser.pengu_errors import PenguError
        from pengu_parser import PenguChecker, PenguParser
        src = (
            "declare f with a as int, ... into void\n"
            "weave main into int:\n"
            "    calling f\n"
            "    return 0\n"
        )
        try:
            tree = PenguParser().parse(src)
            PenguChecker().check(tree, source=src)
            assert False, "expected compile error"
        except PenguError as exc:
            assert exc.code == "E0005"
            assert "Function expects at least 1 arguments" in str(exc)

    @requires_cc
    def test_pengu_bind_varargs(self, tmp_path):
        """pengu_bind emits '...' for C functions with ellipsis parameters."""
        from pengu_bind import generate_bind_file
        hdr = tmp_path / "test_varargs.h"
        hdr.write_text("int my_printf(const char *fmt, ...);\n", encoding="utf-8")
        out = tmp_path / "test_varargs.d.pengu"
        generate_bind_file(str(hdr), output=str(out), prefix="")
        content = out.read_text(encoding="utf-8")
        assert "declare my_printf with fmt as ref to frozen char, ... into int" in content


# ==========================================================================
# P1.5 — Pointer indexing (p at i) and generic slice bridge
# ==========================================================================


class TestPointerIndexing:
    """Pointer indexing and generic slice view construction."""

    def test_pointer_index_read_and_write_codegen(self):
        """p at i and set p at i is v emit base[idx] access."""
        src = (
            "weave test_ptr with p as ref to int, i as int into int:\n"
            "    set p at i is 99\n"
            "    return p at i\n"
        )
        c_code = gen_bundle(src)
        assert "p[i] = 99;" in c_code
        assert "p[i]" in c_code

    @requires_cc
    @requires_runtime
    def test_pointer_indexing_runtime(self):
        """Indexing through a pointer mutates and reads memory correctly."""
        src = (
            "import std.spark\n\n"
            "weave fill_and_sum with p as ref to int, count as int into int:\n"
            "    for i in 0 to count:\n"
            "        set p at i is (i * 10)\n"
            "    var total as int is 0\n"
            "    for j in 0 to count:\n"
            "        set total += p at j\n"
            "    return total\n\n"
            "weave main into int:\n"
            "    var arr as array of int with size 4 is [0, 0, 0, 0]\n"
            "    var s as int is calling fill_and_sum with arr, 4\n"
            "    calling spark.println with \"sum={s} a0={arr at 0} a3={arr at 3}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_ptr_idx")
        assert "sum=60 a0=0 a3=30" in res.stdout

    def test_pointer_frozen_mutation_rejected(self):
        """set p at i is v fails with E0006 when p is ref to frozen T."""
        from pengu_parser.pengu_errors import PenguError
        from pengu_parser import PenguChecker, PenguParser
        src = (
            "weave bad with p as ref to frozen int into void:\n"
            "    set p at 0 is 10\n"
        )
        try:
            tree = PenguParser().parse(src)
            PenguChecker().check(tree, source=src)
            assert False, "expected E0006 error"
        except PenguError as exc:
            assert exc.code == "E0006"

    def test_pointer_void_indexing_rejected(self):
        """p at i fails with E0005 when p is ref to void."""
        from pengu_parser.pengu_errors import PenguError
        from pengu_parser import PenguChecker, PenguParser
        src = (
            "weave bad with p as ref to void into int:\n"
            "    return p at 0\n"
        )
        try:
            tree = PenguParser().parse(src)
            PenguChecker().check(tree, source=src)
            assert False, "expected E0005 error"
        except PenguError as exc:
            assert exc.code == "E0005"
            assert "slice_from_ptr" in (getattr(exc, "help", "") or "") or "slice_from_ptr" in str(exc)

    @requires_cc
    @requires_runtime
    def test_generic_slice_from_ptr_runtime(self):
        """ffi.slice_from_ptr creates a slice from a pointer with correct length and iteration."""
        src = (
            "import std.ffi\n"
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var arr as array of int with size 4 is [10, 20, 30, 40]\n"
            "    var sl as slice of int is calling ffi.slice_from_ptr of int with (sigil of arr), 4\n"
            "    var total as int is 0\n"
            "    for x in sl:\n"
            "        set total += x\n"
            "    calling spark.println with \"len={(sl length)} sum={total}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_slice_bridge")
        assert "len=4 sum=100" in res.stdout


# ==========================================================================
# P1.4 — raymath C shim and binding
# ==========================================================================


class TestRaymath:
    """Tests for raymath non-inline C shim and std/raymath bindings."""

    def test_raymath_check_clean(self):
        """std/raymath declarations and usage check cleanly."""
        src = (
            "import std.raylib\n"
            "import std.raymath\n\n"
            "weave main into int:\n"
            "    var v1 as raylib.Vector2 is with x is 1.0, y is 2.0\n"
            "    var v2 as raylib.Vector2 is with x is 3.0, y is 4.0\n"
            "    var v3 as raylib.Vector2 is calling raymath.Vector2Add with v1, v2\n"
            "    var z as raylib.Vector2 is calling raymath.Vector2Zero\n"
            "    var m as raylib.Matrix is calling raymath.MatrixIdentity\n"
            "    return 0\n"
        )
        check_ok(src)

    @requires_cc
    @requires_runtime
    @requires_lib("pengu_raymath")
    @requires_lib("raylib")
    def test_raymath_runtime_vectors_and_matrices(self):
        """Calling raymath functions calculates accurate results at runtime."""
        src = (
            "import std.raylib\n"
            "import std.raymath\n"
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var v1 as raylib.Vector2 is with x is 3.0, y is 0.0\n"
            "    var v2 as raylib.Vector2 is with x is 0.0, y is 4.0\n"
            "    var sum_v as raylib.Vector2 is calling raymath.Vector2Add with v1, v2\n"
            "    var len as f32 is calling raymath.Vector2Length with sum_v\n"
            "    var zero_v as raylib.Vector2 is calling raymath.Vector2Zero\n"
            "    var m1 as raylib.Matrix is calling raymath.MatrixIdentity\n"
            "    var m2 as raylib.Matrix is calling raymath.MatrixMultiply with m1, m1\n"
            "    var q as raylib.Quaternion is with x is 0.0, y is 0.0, z is 0.0, w is 1.0\n"
            "    var qm as raylib.Matrix is calling raymath.QuaternionToMatrix with q\n"
            "    calling spark.println with \"len={len} zx={zero_v.x} m0={m2.m0} qm0={qm.m0}\"\n"
            "    return 0\n"
        )
        libs = ["-lpengu_raymath", "-lraylib", "-lopengl32", "-lgdi32", "-lwinmm"] if is_windows() else ["-lpengu_raymath", "-lraylib", "-lm"]
        res = compile_run(src, tag="p1_raymath", extra_libs=libs)
        assert "len=5" in res.stdout
        assert "zx=0" in res.stdout
        assert "m0=1" in res.stdout
        assert "qm0=1" in res.stdout


# ==========================================================================
# `at` index expressions — pinned semantics
# ==========================================================================


class TestAtIndexSemantics:
    """`at` is a postfix operator: it takes one atom as its index.

    `xs at i + 1` is therefore `(xs at i) + 1` (CHEATSHEET §6.1 precedence lists
    `at` below the additive operators), and a computed index must be
    parenthesised. These tests exist because the semantics are easy to change by
    accident: an earlier grammar revision made reads and writes disagree about
    `at i + 1`, which silently turned in-bounds indexing into arithmetic on the
    element (and could read out of bounds).
    """

    @requires_cc
    @requires_runtime
    def test_index_binds_tighter_than_addition(self):
        src = (
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var xs as array of int with size 3 is [10, 20, 30]\n"
            "    var i as int is 1\n"
            "    var plain as int is xs at i + 1\n"
            "    var grouped as int is xs at (i + 1)\n"
            "    calling spark.println with \"plain={plain} grouped={grouped}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_at_prec")
        # 20 + 1 vs the element at index 2
        assert "plain=21 grouped=30" in res.stdout

    @requires_cc
    @requires_runtime
    def test_computed_index_write_needs_parentheses(self):
        src = (
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var xs as array of int with size 3 is [10, 20, 30]\n"
            "    var n as int is 3\n"
            "    set xs at (n - 1) is 77\n"
            "    calling spark.println with \"last={xs at 2}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_at_write")
        assert "last=77" in res.stdout

    def test_unparenthesised_target_index_gets_a_helpful_error(self):
        from pengu_parser.pengu_errors import PenguError
        from pengu_parser.pengu_parser import PenguParser

        src = (
            "weave main into int:\n"
            "    var xs as array of int with size 3 is [1, 2, 3]\n"
            "    var n as int is 3\n"
            "    set xs at n - 1 is 9\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as info:
            PenguParser().parse(src)
        err = info.value
        assert err.code == "E0000"
        assert "binds tighter" in str(err)
        assert "at (n - 1)" in (getattr(err, "help", "") or "")

    def test_reads_are_the_documented_reading(self):
        # Reading is valid (postfix): `xs at n - 1` is `(xs at n) - 1`.
        from pengu_parser.pengu_parser import PenguParser

        PenguParser().parse(
            "weave main into int:\n"
            "    var xs as array of int with size 3 is [1, 2, 3]\n"
            "    var n as int is 2\n"
            "    var v as int is xs at n - 1\n"
            "    return v\n"
        )

    @requires_cc
    @requires_runtime
    def test_multiplicative_index_also_binds_tighter(self):
        src = (
            "import std.spark\n\n"
            "weave main into int:\n"
            "    var xs as array of int with size 3 is [10, 20, 30]\n"
            "    var i as int is 1\n"
            "    var plain as int is xs at i * 2\n"
            "    var grouped as int is xs at (i * 2)\n"
            "    calling spark.println with \"plain={plain} grouped={grouped}\"\n"
            "    return 0\n"
        )
        res = compile_run(src, tag="p1_at_mul")
        assert "plain=40 grouped=30" in res.stdout

