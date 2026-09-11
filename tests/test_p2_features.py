"""Tests for P2 features (P2.2 2D arrays, P2.4 memory banish API, P2.3 module state, P2.1 rlgl, P2.5 strict pointers, P2.6 pengu bind)."""

from pathlib import Path
import pytest
from pengu_parser.pengu_errors import PenguError
from tests.conftest import (
    check,
    check_ok,
    check_error,
    gen_bundle,
    bundle_project,
    compile_run,
    requires_cc,
    requires_runtime,
    requires_lib,
    is_windows,
    REPO,
    HAVE_CC,
    HAVE_RUNTIME,
)
from pengu_bind import generate_bind_file, HeaderParseError
from pengu_project import create_cli_parser



# ==========================================================================
# P2.2 — Multidimensional / 2D Arrays
# ==========================================================================


class TestArray2D:
    """2D arrays: syntax, C code generation, element indexing/mutation, length and errors."""

    def test_array_2d_codegen_no_none(self):
        """Codegen emits 'float m[2][3]' without '[None]'."""
        src = (
            "weave main into int:\n"
            "    var m as array of array of f32 with size 2 is [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "[None]" not in c_code
        assert "float m[2][3]" in c_code

    @requires_cc
    @requires_runtime
    def test_array_2d_compile_run_and_inner_length(self):
        """Compile and run: initialization, reading, index mutation and ((m at 0) length)."""
        src = (
            "weave main into int:\n"
            "    var m as array of array of f32 with size 2 is [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]\n"
            "    var v01 as f32 is m at 0 at 1\n"
            "    set m at 1 at 0 is 9.5\n"
            "    var v10 as f32 is m at 1 at 0\n"
            "    var inner_len as int is ((m at 0) length)\n"
            "    if v01 > 1.9 and v01 < 2.1 and v10 > 9.4 and v10 < 9.6 and inner_len == 3:\n"
            "        return 0\n"
            "    return 1\n"
        )
        res = compile_run(src)
        assert res.returncode == 0

    def test_array_2d_dimension_orientation(self):
        """Both type spellings produce the correct outer-first orientation."""
        src1 = (
            "weave main into int:\n"
            "    var a as array of array of f32 with size 2 with size 3 is [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]\n"
            "    return 0\n"
        )
        c1 = gen_bundle(src1)
        assert "float a[2][3]" in c1

        src2 = (
            "weave main into int:\n"
            "    var b as array of array of f32 with size 3 with size 2 is [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]\n"
            "    return 0\n"
        )
        c2 = gen_bundle(src2)
        assert "float b[3][2]" in c2

    def test_array_2d_uninferable_inner_dimension_error(self):
        """Semantic error E0015 (not '[None]') when inner dimension cannot be inferred."""
        src = (
            "weave main into int:\n"
            "    var m as array of array of f32 with size 2 is []\n"
            "    return 0\n"
        )
        from pengu_parser.pengu_parser import PenguParser
        from pengu_parser.pengu_checker import PenguChecker
        from pengu_parser.pengu_errors import UnknownArrayDimensionError
        tree = PenguParser().parse(src)
        checker = PenguChecker()
        with pytest.raises(UnknownArrayDimensionError) as exc_info:
            checker.check(tree, source=src)
        err = exc_info.value
        assert err.code == "E0015"
        assert "Unknown array dimension" in str(err)
        assert err.help is not None and "dimensions" in err.help

    def test_array_2d_unequal_row_lengths_error(self):
        """Inconsistent row lengths in 2D array literal trigger an error."""
        src = (
            "weave main into int:\n"
            "    var m is [[1.0, 2.0], [3.0, 4.0, 5.0]]\n"
            "    return 0\n"
        )
        err = check_error(src)
        assert ("Inconsistent row length" in err) or ("E0041" in err)

    @requires_cc
    @requires_runtime
    def test_array_2d_interop_pass_to_c_parameter(self):
        """A 2D array passes to a function with parameter decayed to 'float (*m)[3]'."""
        src = (
            "weave sum_matrix with m as array of array of f32 with size 2 with size 3 into f32:\n"
            "    return m at 0 at 0 + m at 1 at 2\n"
            "weave sum_row with row as array of f32 with size 3 into f32:\n"
            "    return row at 0 + row at 1 + row at 2\n"
            "weave main into int:\n"
            "    var mat as array of array of f32 with size 2 with size 3 is [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]\n"
            "    var s_row as f32 is calling sum_row with (mat at 0)\n"
            "    var s_mat as f32 is calling sum_matrix with mat\n"
            "    if s_row > 5.9 and s_row < 6.1 and s_mat > 6.9 and s_mat < 7.1:\n"
            "        return 0\n"
            "    return 1\n"
        )
        c_code = gen_bundle(src)
        assert "float sum_matrix(float (* m)[3])" in c_code
        assert "restrict" not in c_code
        res = compile_run(src)
        assert res.returncode == 0


# ==========================================================================
# P2.4 — Memory banish API for string / list / map
# ==========================================================================


class TestBanishCollections:
    """banish statement supports strings, lists, maps, and defer cleanups."""

    @requires_cc
    @requires_runtime
    def test_banish_string_loop_compile_run(self):
        """Loop creating and banishing 1000 strings terminates cleanly and emits pengu_banish_string."""
        src = (
            "weave main into int:\n"
            "    for i from 0 to 1000:\n"
            "        var s as string is \"hello {i}\"\n"
            "        banish s\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "pengu_banish_string(" in c_code
        res = compile_run(src)
        assert res.returncode == 0

    @requires_cc
    @requires_runtime
    def test_banish_list_and_map_codegen_and_run(self):
        """banish on list and map emits pengu_banish_list and pengu_banish_map and runs cleanly."""
        src = (
            "weave main into int:\n"
            "    var l as list of string is list of string with capacity 4\n"
            "    banish l\n"
            "    var m as map of string to int is {\"key\": 42}\n"
            "    banish m\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "pengu_banish_list(" in c_code
        assert "pengu_banish_map(" in c_code
        res = compile_run(src)
        assert res.returncode == 0

    @requires_cc
    @requires_runtime
    def test_defer_banish_string_in_weave(self):
        """'defer banish s' inside a weave compiles and runs cleanly."""
        src = (
            "weave helper into int:\n"
            "    var s as string is \"cleanup {42}\"\n"
            "    defer banish s\n"
            "    return 42\n"
            "weave main into int:\n"
            "    var r as int is calling helper\n"
            "    if r == 42:\n"
            "        return 0\n"
            "    return 1\n"
        )
        c_code = gen_bundle(src)
        assert "pengu_banish_string(" in c_code
        res = compile_run(src)
        assert res.returncode == 0

    def test_banish_negatives(self):
        """banish rejects literals, const, frozen, and temporary expressions with E0008."""
        from pengu_parser.pengu_errors import InvalidMemoryOpError

        # 1. Literal
        with pytest.raises(InvalidMemoryOpError) as exc1:
            check(
                "weave main into int:\n"
                "    banish \"hello\"\n"
                "    return 0\n"
            )
        assert exc1.value.code == "E0008"
        assert "literal" in str(exc1.value).lower()

        # 2. Const
        with pytest.raises(InvalidMemoryOpError) as exc2:
            check(
                "const G_STR as string is \"immutable\"\n"
                "weave main into int:\n"
                "    banish G_STR\n"
                "    return 0\n"
            )
        assert exc2.value.code == "E0008"
        assert "const" in str(exc2.value).lower()

        # 3. Frozen
        with pytest.raises(InvalidMemoryOpError) as exc3:
            check(
                "weave f with s as frozen string into void:\n"
                "    banish s\n"
                "weave main into int:\n"
                "    return 0\n"
            )
        assert exc3.value.code == "E0008"
        assert "frozen" in str(exc3.value).lower()

        # 4. Temporary
        with pytest.raises(InvalidMemoryOpError) as exc4:
            check(
                "weave make_str into string:\n"
                "    return \"temp\"\n"
                "weave main into int:\n"
                "    banish calling make_str\n"
                "    return 0\n"
            )
        assert exc4.value.code == "E0008"
        assert "temporary" in str(exc4.value).lower()

    @requires_cc
    @requires_runtime
    def test_banish_ref_still_emits_pengu_banish(self):
        """banish on 'ref to T' continues to emit pengu_banish (no regression)."""
        src = (
            "declare malloc with size as usize into ref to int\n"
            "weave main into int:\n"
            "    var p as ref to int is calling malloc with 4\n"
            "    banish p\n"
            "    return 0\n"
        )
        c_code = gen_bundle(src)
        assert "pengu_banish((void*)" in c_code
        res = compile_run(src)
        assert res.returncode == 0


# ==========================================================================
# P2.3 — Module state idiom
# ==========================================================================


class TestModuleState:
    """Module state patterns: static var in accessors, context struct, and top-level var rejection."""

    @requires_cc
    @requires_runtime
    def test_two_module_encapsulated_state_persistence(self):
        """Cross-module state persistence using static var in accessor weaves."""
        from tests.test_compiler_features import _compile_run

        state_mod = (
            "weave add with delta as int into int:\n"
            "    static var total as int is 0\n"
            "    set total is total + delta\n"
            "    return total\n"
            "weave get_total into int:\n"
            "    return calling add with 0\n"
        )
        main_mod = (
            "import state_holder\n"
            "weave main into int:\n"
            "    calling state_holder.add with 10\n"
            "    calling state_holder.add with 25\n"
            "    var res as int is calling state_holder.get_total\n"
            "    if res == 35:\n"
            "        return 0\n"
            "    return 1\n"
        )
        res = _compile_run(main_mod, tag="p2_state", entry="main.pengu",
                           extra_files={"state_holder.pengu": state_mod})
        assert res.returncode == 0

    @requires_cc
    @requires_runtime
    def test_two_module_explicit_context_struct(self):
        """Cross-module state using an explicit context struct passed by reference."""
        from tests.test_compiler_features import _compile_run

        ctx_mod = (
            "rune Counter:\n"
            "    value as int\n"
            "weave init into Counter:\n"
            "    return with value is 0\n"
            "weave increment with c as ref to Counter, step as int into void:\n"
            "    set c->value is c->value + step\n"
        )
        main_mod = (
            "import counter_service\n"
            "weave main into int:\n"
            "    var c as counter_service.Counter is calling counter_service.init\n"
            "    calling counter_service.increment with sigil of c, 5\n"
            "    calling counter_service.increment with sigil of c, 15\n"
            "    if c.value == 20:\n"
            "        return 0\n"
            "    return 1\n"
        )
        res = _compile_run(main_mod, tag="p2_ctx", entry="main.pengu",
                           extra_files={"counter_service.pengu": ctx_mod})
        assert res.returncode == 0

    def test_top_level_var_rejected_with_e0002_and_idiom_suggestion(self):
        """Top-level var is rejected with E0002 and a help message explaining the idiom."""
        from pengu_parser.pengu_errors import VarLetTopLevelError

        with pytest.raises(VarLetTopLevelError) as exc:
            check(
                "var global_counter as int is 0\n"
                "weave main into int:\n"
                "    return 0\n"
            )
        assert exc.value.code == "E0002"
        help_msg = exc.value.help.lower()
        assert "static var" in help_msg or "context struct" in help_msg


# ==========================================================================
# P2.1 — rlgl binding
# ==========================================================================


class TestRlgl:
    """rlgl binding: raylib OpenGL backend, coexistence with raylib, matrix interop."""

    def test_rlgl_d_pengu_checks_ok(self):
        """std/rlgl.d.pengu type-checks cleanly."""
        src = Path("std/rlgl.d.pengu").read_text(encoding="utf-8")
        check_ok(src, filename="std/rlgl.d.pengu")

    @requires_cc
    @requires_runtime
    @requires_lib("raylib")
    def test_rlgl_coexistence_with_raylib(self):
        """A program importing both std.raylib and std.rlgl bundles, compiles, and shares Matrix without conflict."""
        src = (
            "import std.raylib as rl\n"
            "import std.rlgl as rlgl\n"
            "weave main into int:\n"
            "    calling rl.InitWindow with 100, 100, \"rlgl_test\"\n"
            "    if not calling rl.IsWindowReady:\n"
            "        return 0\n"
            "    calling rlgl.rlMatrixMode with rlgl.RL_MODELVIEW\n"
            "    calling rlgl.rlPushMatrix\n"
            "    var mat as rl.Matrix is calling rlgl.rlGetMatrixModelview\n"
            "    calling rlgl.rlSetMatrixModelview with mat\n"
            "    calling rlgl.rlBegin with rlgl.RL_TRIANGLES\n"
            "    calling rlgl.rlColor4ub with 255, 0, 0, 255\n"
            "    calling rlgl.rlVertex3f with 0.0, 1.0, 0.0\n"
            "    calling rlgl.rlVertex3f with -1.0, -1.0, 0.0\n"
            "    calling rlgl.rlVertex3f with 1.0, -1.0, 0.0\n"
            "    calling rlgl.rlEnd\n"
            "    calling rlgl.rlPopMatrix\n"
            "    calling rl.CloseWindow\n"
            "    if mat.m0 > 0.99 and mat.m0 < 1.01:\n"
            "        return 0\n"
            "    return 1\n"
        )
        libs = ["-lraylib", "-lopengl32", "-lgdi32", "-lwinmm"] if is_windows() else ["-lraylib", "-lm"]
        c_code = bundle_project(src, tag="rlgl_coexist")
        assert "rlgl.h" in c_code
        assert "raylib.h" in c_code
        assert "rlBegin(" in c_code
        assert "InitWindow(" in c_code
        res = compile_run(src, tag="rlgl_coexist", extra_libs=libs)
        assert res.returncode == 0


# ==========================================================================
# P2.5 — Strict Pointer Typing
# ==========================================================================


class TestStrictPointers:
    """Strict pointer typing (_same_pointee, char<->byte exception, rejection of mismatched pointees)."""

    def test_negative_ref_i32_to_ref_char(self):
        """Passing 'ref to i32' to 'ref to char' parameter raises E0005."""
        src = (
            "declare take with p as ref to char into void\n\n"
            "weave main into int:\n"
            "    var n as i32 is 42\n"
            "    calling take with sigil of n\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as exc:
            check(src)
        assert exc.value.code == "E0005"

    def test_negative_ref_i32_to_ref_byte(self):
        """Passing 'ref to i32' to 'ref to byte' parameter raises E0005."""
        src = (
            "declare take with p as ref to byte into void\n\n"
            "weave main into int:\n"
            "    var n as i32 is 42\n"
            "    calling take with sigil of n\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as exc:
            check(src)
        assert exc.value.code == "E0005"

    def test_negative_ref_u8_to_ref_char(self):
        """Passing 'ref to u8' to 'ref to char' parameter raises E0005 (u8 is not byte)."""
        src = (
            "declare take with p as ref to char into void\n\n"
            "weave main into int:\n"
            "    var n as u8 is 42\n"
            "    calling take with sigil of n\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as exc:
            check(src)
        assert exc.value.code == "E0005"

    def test_negative_array_i32_to_ref_char(self):
        """Passing 'array of i32' to 'ref to char' decay raises E0005."""
        src = (
            "declare take with p as ref to char into void\n\n"
            "weave main into int:\n"
            "    var xs as array of i32 with size 4 is [1, 2, 3, 4]\n"
            "    calling take with xs\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as exc:
            check(src)
        assert exc.value.code == "E0005"

    def test_negative_ref_f32_to_ref_f64(self):
        """Passing 'ref to f32' to 'ref to f64' parameter raises E0005."""
        src = (
            "declare take with p as ref to f64 into void\n\n"
            "weave main into int:\n"
            "    var x as f32 is 1.5\n"
            "    calling take with sigil of x\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as exc:
            check(src)
        assert exc.value.code == "E0005"

    def test_positive_ref_char_to_ref_frozen_char(self):
        """'ref to char' flows into 'ref to frozen char' cleanly."""
        src = (
            "declare take with p as ref to frozen char into void\n\n"
            "weave main into int:\n"
            "    var c as char is 'A'\n"
            "    calling take with sigil of c\n"
            "    return 0\n"
        )
        check_ok(src)

    def test_positive_ref_byte_to_ref_char(self):
        """'ref to byte' flows into 'ref to char' (raw C byte buffer interop exception)."""
        src = (
            "declare take with p as ref to char into void\n\n"
            "weave main into int:\n"
            "    var b as byte is 65\n"
            "    calling take with sigil of b\n"
            "    return 0\n"
        )
        check_ok(src)

    def test_positive_sigil_to_ref_void(self):
        """'sigil of x' flows into 'ref to void' (universal wildcard)."""
        src = (
            "declare take with p as ref to void into void\n\n"
            "weave main into int:\n"
            "    var x as int is 123\n"
            "    calling take with sigil of x\n"
            "    return 0\n"
        )
        check_ok(src)

    def test_positive_array_char_to_ref_frozen_char(self):
        """'array of char' decays to 'ref to frozen char' cleanly."""
        src = (
            "declare take with p as ref to frozen char into void\n\n"
            "weave main into int:\n"
            "    var xs as array of char with size 3 is ['a', 'b', 'c']\n"
            "    calling take with xs\n"
            "    return 0\n"
        )
        check_ok(src)

    def test_positive_bytes_of_s_to_ref_frozen_void(self):
        """'bytes of s' flows into 'ref to frozen void'."""
        src = (
            "declare take with p as ref to frozen void into void\n\n"
            "weave main into int:\n"
            "    var s as string is \"hello\"\n"
            "    calling take with bytes of s\n"
            "    return 0\n"
        )
        check_ok(src)

    def test_frozen_directionality_preserved(self):
        """'ref to frozen int' passed to 'ref to int' is rejected with E0005."""
        src = (
            "declare take with p as ref to int into void\n\n"
            "weave main with q as ref to frozen int into int:\n"
            "    calling take with q\n"
            "    return 0\n"
        )
        with pytest.raises(PenguError) as exc:
            check(src)
        assert exc.value.code == "E0005"

    def test_numeric_value_widening_int_to_i64_still_works(self):
        """Numeric value widening (int -> i64) remains intact for values."""
        src = (
            "weave main into int:\n"
            "    var n as int is 5\n"
            "    var m as i64 is n\n"
            "    return 0\n"
        )
        check_ok(src)


# ==========================================================================
# P2.6 — pengu bind with Real Headers
# ==========================================================================


class TestPenguBind:
    """Tests for P2.6: real C header binding generation and diagnostics."""

    def test_bind_sqlite3_regression(self, tmp_path):
        """sqlite3.h binds cleanly and passes check_ok (no invalid zero-param callback syntax)."""
        header = REPO / "build/include/sqlite3.h"
        if not header.exists():
            pytest.skip("build/include/sqlite3.h not found")
        out_file = tmp_path / "sqlite3.d.pengu"
        p = generate_bind_file(str(header), output=str(out_file))
        assert Path(p).is_file()
        content = out_file.read_text(encoding="utf-8")
        assert "declare sqlite3_open " in content
        assert "alias sqlite3_syscall_ptr as ref to weave into void" in content
        check_ok(content)

    def test_member_and_param_names_are_kept_verbatim(self, tmp_path):
        """Struct members and `declare` parameters keep their C name.

        Regression guard: sanitising them produced `_type`/`_size`, which broke
        regeneration of `std/nanosvg.d.pengu` and `std/typis.d.pengu` (they use
        those member names) and changed the generated API for no compile-time
        gain — no such name breaks a `declare` signature today. Only `self`/`type`
        are sanitised as parameters, and callback aliases (whose grammar is
        stricter) sanitise type-like names too.
        """
        header = tmp_path / "names.h"
        header.write_text(
            "typedef struct Item {\n"
            "    char type;\n"
            "    int size;\n"
            "    float data;\n"
            "} Item;\n"
            "\n"
            "int item_count(const Item *item, int size, char type);\n",
            encoding="utf-8",
        )
        out = tmp_path / "names.d.pengu"
        generate_bind_file(str(header), output=str(out))
        content = out.read_text(encoding="utf-8")
        assert "rune Item:" in content
        # Members keep their C name, even when it spells a keyword.
        assert "  type as char" in content
        assert "  size as int" in content
        assert "  _type" not in content
        assert "  _size" not in content
        # Parameters keep their name too, except 'self'/'type' (which cannot be
        # spelled in a signature).
        assert "declare item_count with item as ref to frozen Item, size as int, _type as char into int" in content
        assert "_size" not in content
        check_ok(content)

    def test_callback_alias_sanitizes_type_like_parameter_names(self, tmp_path):
        """Callback aliases rename parameters the alias grammar would reject.

        `alias Cb as ref to weave with opaque as voidpf` is a syntax error, so
        those names get an underscore *inside callback aliases only* (a `declare`
        with the same parameter name is fine and keeps it).
        """
        header = tmp_path / "cb.h"
        header.write_text(
            "typedef void *(*alloc_fn)(void *opaque, int items, int size);\n"
            "void set_alloc(alloc_fn fn);\n",
            encoding="utf-8",
        )
        out = tmp_path / "cb.d.pengu"
        generate_bind_file(str(header), output=str(out))
        content = out.read_text(encoding="utf-8")
        assert "alias alloc_fn as ref to weave with _opaque as ref to void, items as int, size as int into ref to void" in content
        check_ok(content)

    def test_bind_rlgl_regression(self, tmp_path):
        """rlgl.h binds cleanly with include_paths and passes check_ok."""
        header = REPO / "extern/raylib-6.0/src/rlgl.h"
        if not header.exists():
            pytest.skip("extern/raylib-6.0/src/rlgl.h not found")
        out_file = tmp_path / "rlgl.d.pengu"
        p = generate_bind_file(
            str(header),
            output=str(out_file),
            include_paths=[str(header.parent)],
        )
        assert Path(p).is_file()
        content = out_file.read_text(encoding="utf-8")
        assert "declare rlBegin " in content
        assert "declare rlEnd into void" in content
        check_ok(content)

    def test_bind_zlib_success_and_compile(self, tmp_path):
        """zlib.h binds cleanly with --define Z_SOLO and the binding compiles."""
        header = REPO / "extern/zlib-1.3.2/zlib.h"
        if not header.exists():
            pytest.skip("extern/zlib-1.3.2/zlib.h not found")
        out_file = tmp_path / "zlib.d.pengu"
        p = generate_bind_file(
            str(header),
            output=str(out_file),
            defines=["Z_SOLO"],
            links=["z"],
        )
        assert Path(p).is_file()
        content = out_file.read_text(encoding="utf-8")
        assert "declare zlibVersion into ref to frozen char" in content
        assert "declare adler32 " in content
        # Parameter names are kept verbatim in `declare` lines (only 'self'/'type'
        # are sanitized there); the callback aliases zlib declares DO sanitize
        # type-like names, because `with opaque as voidpf` would not parse.
        assert "alias alloc_func as ref to weave with _opaque as voidpf" in content
        check_ok(content)

        if HAVE_CC and HAVE_RUNTIME:
            # Compile and run a minimal program invoking zlibVersion()
            src = (
                "include \"zlib.h\"\n"
                "link \"z\"\n\n"
                "declare zlibVersion into ref to frozen char\n\n"
                "weave main into int:\n"
                "    var ver as ref to frozen char is calling zlibVersion\n"
                "    if ver != null:\n"
                "        return 0\n"
                "    return 1\n"
            )
            res = compile_run(src, extra_libs=["-lz"])
            assert res.returncode == 0

    def test_bind_actionable_diagnostics(self, tmp_path):
        """Unpreprocessed complex header failure raises HeaderParseError with line snippet and tips."""
        header = REPO / "std_c/xxhash.h"
        if not header.exists():
            pytest.skip("std_c/xxhash.h not found")
        out_file = tmp_path / "xxhash.d.pengu"
        with pytest.raises(HeaderParseError) as exc:
            generate_bind_file(str(header), output=str(out_file))
        msg = str(exc.value)
        assert ">>> " in msg
        assert "--define" in msg
        assert "--system-includes" in msg
        assert "--cpp-flags" in msg

    def test_bind_cli_flags(self):
        """pengu bind CLI flags are properly registered and parsed."""
        parser = create_cli_parser()
        args = parser.parse_args([
            "bind", "test.h",
            "-D", "FOO",
            "--define", "BAR=1",
            "--cpp-flags", "-O2 -Wall",
            "--system-includes",
            "--no-blank-extensions",
            "--preprocessed", "input.i",
        ])
        assert args.header == "test.h"
        assert args.defines == ["FOO", "BAR=1"]
        assert args.cpp_flags == "-O2 -Wall"
        assert args.system_includes is True
        # '--no-blank-extensions' is a store_false on 'blank_extensions'
        # (default True = GNU extensions are blanked before pycparser).
        assert args.blank_extensions is False
        assert args.preprocessed == "input.i"

    def test_bind_defaults_blank_extensions(self):
        """Without the flag, GNU-extension blanking stays enabled (the default)."""
        parser = create_cli_parser()
        args = parser.parse_args(["bind", "test.h"])
        assert args.blank_extensions is True
        assert args.system_includes is False
        assert args.defines == []




