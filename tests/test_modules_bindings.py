#!/usr/bin/env python3
"""Consolidated tests for the module system, declaration files, insignia,
and the ``pengu bind`` C-header -> ``.d.pengu`` binding generator.

Groups (ported from the historical suite):
  ImportsAndExports     - top-level import / include / link directives
  ModuleResolution      - resolve_imports topological order, cycles, __init__ packages
  DeclarationFiles      - .d.pengu semantics, include "header.h" emission, C suppression
  Insignia              - per-module C prefixing of declares/types/weaves
  ProjectBindings       - project layout (init_project), lib/ bindings, builder integration
  PenguBindGenerator    - pengu_bind.generate_bind_file output shapes

Module files are written into scratch directories under ``build/`` and the
checker / ``resolve_imports`` are pointed at them, mirroring the original
tests (which used bare ``tempfile`` directories).
"""
import contextlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from pengu_bind import generate_bind_file
from pengu_parser import PenguChecker, PenguParser, resolve_imports
from pengu_parser.pengu_codegen import PenguCodegen
from pengu_parser.pengu_errors import MultipleInsigniaError, SemanticError
from pengu_parser.pengu_symbols import find_module_path
from pengu_project import (
    OutputType,
    PenguBuilder,
    ProjectConfig,
    add_dependency,
    extract_lib_name,
    init_project,
)

from tests.conftest import BUILD_DIR, HAVE_CC, REPO

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def temp_project_dir(prefix: str = "pengu_mods_"):
    """A scratch project directory under build/ that is removed afterwards."""
    d = Path(tempfile.mkdtemp(prefix=prefix, dir=str(BUILD_DIR)))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def write_file(base_dir, rel_path: str, content: str) -> str:
    """Writes ``content`` to ``base_dir/rel_path`` (creating parents) and returns the path."""
    full = os.path.join(str(base_dir), rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return full


def check_all(base_dir, entry_rel: str):
    """resolve_imports + parse + check every module in topological order.

    Returns (order, [(filepath, tree), ...], checker) with a shared checker so
    cross-module symbols (imports / .d.pengu surfaces) are visible.
    """
    parser = PenguParser()
    order = resolve_imports(str(base_dir), str(entry_rel), parser)
    trees = []
    checker = PenguChecker(base_dir=str(base_dir))
    for i, filepath in enumerate(order):
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        tree = parser.parse(code)
        checker.check(
            tree, source=code, filename=filepath,
            reset_symbols=(i == 0), import_order=order,
        )
        trees.append((filepath, tree))
    return order, trees, checker


def _assert_semantic_errors(checker, msg: str = "unexpected semantic errors"):
    assert len(checker.errors) == 0, f"{msg}: {[str(e) for e in checker.errors]}"


def base_names(paths) -> list:
    return [os.path.basename(p) for p in paths]


# ---------------------------------------------------------------------------
# Import / export directives
# ---------------------------------------------------------------------------


class TestImportsAndExports:
    """Top-level ``import`` / ``include`` / ``link`` directives parse + check."""

    def test_import_dotted_path(self):
        code = """import src.components.Player
import src.math.Vec2
import my_module
"""
        parser = PenguParser()
        tree = parser.parse(code)
        assert tree is not None
        checker = PenguChecker()
        checker.check(tree, source=code, filename="t.pengu")
        _assert_semantic_errors(checker)

    def test_include_c_header(self):
        code = """include "raylib.h"
include "pengu_runtime.h"
"""
        parser = PenguParser()
        tree = parser.parse(code)
        assert tree is not None
        checker = PenguChecker()
        checker.check(tree, source=code, filename="t.pengu")
        _assert_semantic_errors(checker)

    def test_link_library(self):
        code = """link "raylib"
link "m"
"""
        parser = PenguParser()
        tree = parser.parse(code)
        assert tree is not None
        checker = PenguChecker()
        checker.check(tree, source=code, filename="t.pengu")
        _assert_semantic_errors(checker)

    def test_combined_imports(self):
        code = """import src.math.Vec2
include "raylib.h"
link "raylib"
link "m"
"""
        parser = PenguParser()
        tree = parser.parse(code)
        assert tree is not None
        checker = PenguChecker()
        checker.check(tree, source=code, filename="t.pengu")
        _assert_semantic_errors(checker)


# ---------------------------------------------------------------------------
# Module resolution
# ---------------------------------------------------------------------------


class TestModuleResolution:
    """resolve_imports: linear chains, topological order, cycles, packages."""

    def test_linear_module_resolution(self):
        with temp_project_dir("pengu_lin_") as d:
            write_file(d, "b.pengu", "rune B:\n  y as int\n")
            write_file(d, "a.pengu", "import b\nrune A:\n  x as int\n")

            order = resolve_imports(str(d), "a.pengu", PenguParser())
            assert len(order) == 2
            assert base_names(order) == ["b.pengu", "a.pengu"]

    def test_chain_module_resolution_topological_order(self):
        # a -> b -> c ; resolve_imports must emit dependencies first.
        with temp_project_dir("pengu_chain_") as d:
            write_file(d, "c.pengu", """rune Point:
  x as int
  y as int
""")
            write_file(d, "b.pengu", """import c

weave make_point into c.Point:
  with x is 1, y is 2
""")
            write_file(d, "a.pengu", """import b

weave main into void:
  let p is calling b.make_point
""")
            order = resolve_imports(str(d), "a.pengu", PenguParser())
            assert base_names(order) == ["c.pengu", "b.pengu", "a.pengu"]

    def test_circular_module_dependency_fails(self):
        with temp_project_dir("pengu_circ_") as d:
            write_file(d, "a.pengu", "import b\nweave a_fn into void:\n  return\n")
            write_file(d, "b.pengu", "import a\nweave b_fn into void:\n  return\n")

            with pytest.raises(SemanticError) as exc_info:
                resolve_imports(str(d), "a.pengu", PenguParser())
            err = exc_info.value
            assert err.code == "E0004"
            assert "circular" in str(err).lower()

    def test_package_init_module_resolution(self):
        with temp_project_dir("pengu_pkg_") as d:
            write_file(d, "math/vector.pengu", """rune Vec2:
  x as float
  y as float
""")
            write_file(d, "math/__init__.pengu", "import math.vector\n")
            write_file(d, "main.pengu", """import math
weave main into void:
  return
""")
            order = resolve_imports(str(d), "main.pengu", PenguParser())
            assert base_names(order) == ["vector.pengu", "__init__.pengu", "main.pengu"]


# ---------------------------------------------------------------------------
# Declaration files (.d.pengu)
# ---------------------------------------------------------------------------


class TestDeclarationFiles:
    """.d.pengu semantics: no bodies, types/consts stay declarative, includes/links."""

    def test_find_module_path_priority(self):
        with temp_project_dir("pengu_find_") as d:
            src_dir = os.path.join(str(d), "src")
            os.makedirs(src_dir, exist_ok=True)
            pengu_file = os.path.join(src_dir, "mylib.pengu")
            dpengu_file = os.path.join(src_dir, "mylib.d.pengu")

            # Case 1: only the .d.pengu exists -> it is resolved.
            with open(dpengu_file, "w", encoding="utf-8") as f:
                f.write("declare mylib_fn into int\n")
            found = find_module_path(str(d), "mylib")
            assert found is not None
            assert found.endswith("mylib.d.pengu")

            # Case 2: both exist -> the real .pengu takes priority.
            with open(pengu_file, "w", encoding="utf-8") as f:
                f.write("weave mylib_fn into int:\n    return 42\n")
            found_both = find_module_path(str(d), "mylib")
            assert found_both is not None
            assert found_both.endswith("mylib.pengu")

    def test_declaration_file_rejects_weave_body(self):
        code = """
weave calculate with x as int into int:
    return x * 2
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        with pytest.raises(SemanticError) as exc_info:
            checker.check(tree, source=code, filename="math_bindings.d.pengu")
        err = exc_info.value
        assert getattr(err, "code", "") == "E0025" or "E0025" in str(err)
        assert "Implementation body not allowed in declaration file (.d.pengu)" in str(err)

    def test_declaration_file_allows_declarations_and_types(self):
        code = """
include "custom_c_header.h"
link "custom_c_lib"

const LIB_VERSION as int is 1

rune CData:
    id as int
    flag as bool

alias CDataPtr as ref to CData

declare custom_init with id as int into int
declare custom_process with data as ref to CData into void
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="custom_c.d.pengu")
        _assert_semantic_errors(checker)

        assert "custom_init" in checker.symbols.functions
        assert "custom_process" in checker.symbols.functions
        assert "CData" in checker.symbols.runes
        assert "CDataPtr" in checker.symbols.aliases
        assert "LIB_VERSION" in checker.symbols.consts

    def test_codegen_with_declaration_file_import(self):
        with temp_project_dir("pengu_dcode_") as d:
            write_file(d, "mathlib.d.pengu", """
include "math_extern.h"
link "m"

rune MathVector:
    x as float
    y as float

declare compute_sum with a as int, b as int into int
""")
            write_file(d, "main.pengu", """
import mathlib

weave main into int:
    let res as int is calling compute_sum with 10, 20
    return res
""")
            order, trees, checker = check_all(d, "main.pengu")
            assert len(order) == 2
            assert any(p.endswith("mathlib.d.pengu") for p in order)
            _assert_semantic_errors(checker)

            codegen = PenguCodegen(checker.symbols, order, str(d))
            codegen.collect_declarations(trees)
            c_code = codegen.generate_bundle()

            # header include + recorded link flag
            assert '#include "math_extern.h"' in c_code
            assert "m" in codegen.links

            # runes declared by the .d.pengu are NOT emitted as C definitions
            assert "typedef struct MathVector MathVector;" not in c_code
            assert "struct MathVector {" not in c_code

            # the declared function is callable ...
            assert "compute_sum(10, 20)" in c_code
            # ... but no C definition body is generated for it
            assert "int32_t compute_sum(" not in c_code
            assert "int32_t mathlib_compute_sum(" not in c_code

    def test_declaration_files_suppress_all_c_definitions(self):
        with temp_project_dir("pengu_dsupp_") as d:
            write_file(d, "webui.d.pengu", """
include "webui.h"
link "webui-2-static"
insignia webui_

const MAX_CLIENTS as int is 128

rune Event:
    window as int
    event_type as int

echo Payload:
    int_val as int
    float_val as float

omen Browser:
    Chrome is 1
    Firefox is 2

alias WindowHandle as int
seal WindowId as int

declare new_window into WindowId
declare show with win as WindowId, content as string into void
declare wait into void
""")
            write_file(d, "main.pengu", """
import webui

weave main into int:
    var win as WindowId is calling webui.new_window
    var max_c as int is webui.MAX_CLIENTS
    calling webui.show with win, "Hello Pengu"
    calling webui.wait
    return 0
""")
            order, trees, checker = check_all(d, "main.pengu")
            _assert_semantic_errors(checker)

            codegen = PenguCodegen(checker.symbols, order, str(d))
            codegen.collect_declarations(trees)
            c_code = codegen.generate_bundle()

            # 1. includes and links from the .d.pengu MUST appear
            assert '#include "webui.h"' in c_code
            assert "webui-2-static" in codegen.links

            # 2. insignia-prefixed calls appear in the implementation
            assert "webui_new_window()" in c_code
            assert "webui_show(" in c_code
            assert "webui_wait()" in c_code
            assert "webui_MAX_CLIENTS" in c_code

            # 3. NONE of the types/consts from the .d.pengu may emit C
            #    definitions or forward declarations.
            assert "struct webui_Event;" not in c_code
            assert "typedef struct webui_Event webui_Event;" not in c_code
            assert "struct webui_Event {" not in c_code

            assert "union webui_Payload;" not in c_code
            assert "typedef union webui_Payload webui_Payload;" not in c_code
            assert "union webui_Payload {" not in c_code

            assert "typedef enum webui_Browser webui_Browser;" not in c_code
            assert "typedef enum webui_Browser {" not in c_code
            assert "webui_Browser_Chrome" not in c_code

            assert "typedef int32_t webui_WindowHandle;" not in c_code
            assert "typedef int32_t webui_WindowId;" not in c_code

            assert "#define webui_MAX_CLIENTS" not in c_code
            assert "#define MAX_CLIENTS" not in c_code

            # 4. no declare prototypes are emitted
            assert "WindowId webui_new_window(" not in c_code

    @pytest.mark.skipif(not HAVE_CC, reason="no C compiler available")
    def test_end_to_end_declaration_file_execution(self):
        with temp_project_dir("pengu_de2e_") as d:
            # 1. native C header + implementation
            write_file(d, "native_calc.h", """
#ifndef NATIVE_CALC_H
#define NATIVE_CALC_H
int native_multiply(int a, int b);
#endif
""")
            c_impl = write_file(d, "native_calc.c", """
#include "native_calc.h"
int native_multiply(int a, int b) {
    return a * b;
}
""")
            # 2. calc.d.pengu declaration file
            write_file(d, "calc.d.pengu", """
include "native_calc.h"

declare native_multiply with a as int, b as int into int
""")
            # 3. main.pengu
            write_file(d, "main.pengu", """
import calc

weave main into int:
    let result as int is calling native_multiply with 6, 7
    if result == 42:
        return 0
    return 1
""")
            order, trees, checker = check_all(d, "main.pengu")
            _assert_semantic_errors(checker)

            codegen = PenguCodegen(checker.symbols, order, str(d))
            codegen.collect_declarations(trees)
            bundle_c = codegen.generate_bundle()

            bundle_path = os.path.join(str(d), "bundle.c")
            with open(bundle_path, "w", encoding="utf-8") as f:
                f.write(bundle_c)

            exe_path = os.path.join(str(d), "test_app.exe")
            comp = subprocess.run(
                ["gcc", "-std=c99",
                 "-Wno-error=implicit-function-declaration",
                 "-Wno-error=implicit-int", "-Wno-error=int-conversion",
                 "-I", str(REPO), "-I", str(d), bundle_path, c_impl, "-o", exe_path],
                capture_output=True, text=True, timeout=240,
            )
            assert comp.returncode == 0, f"GCC Compilation failed: {comp.stderr}\nBundle:\n{bundle_c}"

            run_res = subprocess.run([exe_path], capture_output=True, text=True, timeout=120)
            assert run_res.returncode == 0, f"Run failed: {run_res.stderr}"


# ---------------------------------------------------------------------------
# Insignia (per-module C prefix)
# ---------------------------------------------------------------------------


class TestInsignia:
    """insignia prefixes declare/weave C names and type C names per module."""

    def test_insignia_declare_prefix(self):
        code = """
include "webui.h"
insignia webui_

declare new_window into int
declare show with win as int, content as string into void
declare wait into void
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="webui.d.pengu")
        _assert_semantic_errors(checker)

        assert checker.symbols.lookup("new_window").c_name == "webui_new_window"
        assert checker.symbols.lookup("show").c_name == "webui_show"
        assert checker.symbols.lookup("wait").c_name == "webui_wait"

        codegen = PenguCodegen(symbols=checker.symbols)
        codegen.collect_declarations([("webui.d.pengu", tree)])

        assert codegen.fn_info["new_window"]["c_name"] == "webui_new_window"
        assert codegen.fn_info["show"]["c_name"] == "webui_show"
        assert codegen.fn_info["wait"]["c_name"] == "webui_wait"

    def test_insignia_types_and_consts(self):
        code = """
insignia ray_

rune Vector2:
    x as float
    y as float

echo Payload:
    i as int
    f as float

omen Status:
    Ok
    Err with msg as string

alias Handle as int
const MAX_WINDOWS as int is 10
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="raylib.pengu")
        _assert_semantic_errors(checker)

        assert checker.symbols.lookup("Vector2").c_name == "ray_Vector2"
        assert checker.symbols.lookup("Payload").c_name == "ray_Payload"
        assert checker.symbols.lookup("Status").c_name == "ray_Status"
        assert checker.symbols.lookup("Handle").c_name == "ray_Handle"
        assert checker.symbols.lookup("MAX_WINDOWS").c_name == "ray_MAX_WINDOWS"

        codegen = PenguCodegen(symbols=checker.symbols)
        codegen.collect_declarations([("raylib.pengu", tree)])

        forward_decls = codegen.generate_forward_declarations()
        assert "struct ray_Vector2;" in forward_decls
        assert "union ray_Payload;" in forward_decls
        assert "struct ray_Status;" in forward_decls

        type_defs = codegen.generate_type_definitions()
        assert "struct ray_Vector2 {" in type_defs
        assert "union ray_Payload {" in type_defs
        assert "struct ray_Status {" in type_defs
        assert "typedef int32_t ray_Handle;" in type_defs

        const_defs = codegen.generate_constants()
        assert "#define ray_MAX_WINDOWS 10" in const_defs

    def test_multiple_insignia_error(self):
        code = """
insignia webui_
declare new_window into int
insignia raylib_
declare init_window into int
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        with pytest.raises(MultipleInsigniaError) as exc_info:
            checker.check(tree, source=code, filename="test.pengu")
        err = exc_info.value
        assert getattr(err, "code", "") == "E0026" or "E0026" in str(err)
        assert "Multiple 'insignia' directives not allowed" in str(err)

    def test_insignia_position_dependence(self):
        # only declarations AFTER the directive receive the prefix.
        code = """
declare local_fn into void

insignia my_

declare remote_fn into void
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="module.pengu")
        _assert_semantic_errors(checker)

        assert checker.symbols.lookup("local_fn").c_name == "local_fn"
        assert checker.symbols.lookup("remote_fn").c_name == "my_remote_fn"

        codegen = PenguCodegen(symbols=checker.symbols)
        codegen.collect_declarations([("module.pengu", tree)])
        assert codegen.fn_info["local_fn"]["c_name"] == "local_fn"
        assert codegen.fn_info["remote_fn"]["c_name"] == "my_remote_fn"

    def test_insignia_imported_module_call_and_constants(self):
        with temp_project_dir("pengu_insimp_") as d:
            webui_decl = """
include "webui.h"
insignia webui_

const TIMEOUT as int is 5000
declare new_window into int
declare show with win as int, content as string into void
declare wait into void
"""
            webui_path = write_file(d, "webui.d.pengu", webui_decl)

            main_code = """
import webui

weave main into void:
    var win as int is calling webui.new_window
    var t as int is webui.TIMEOUT
    calling webui.show with win, "Hello"
    calling webui.wait
"""
            main_path = write_file(d, "main.pengu", main_code)

            parser = PenguParser()
            webui_tree = parser.parse(webui_decl)
            main_tree = parser.parse(main_code)

            checker = PenguChecker(base_dir=str(d))
            checker.check(main_tree, source=main_code, filename=main_path)
            _assert_semantic_errors(checker)

            codegen = PenguCodegen(
                symbols=checker.symbols,
                import_order=[webui_path, main_path],
            )
            codegen.collect_declarations([(webui_path, webui_tree), (main_path, main_tree)])
            c_code = codegen.generate_bundle()

            assert "webui_new_window()" in c_code
            assert "webui_TIMEOUT" in c_code
            assert "webui_show(" in c_code
            assert "webui_wait()" in c_code
            assert '#include "webui.h"' in c_code

    def test_insignia_weave_with_body(self):
        code = """
insignia mod_

weave helper into int:
    return 42

weave main into void:
    var x as int is calling helper
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="main.pengu")
        _assert_semantic_errors(checker)

        assert checker.symbols.lookup("helper").c_name == "mod_helper"

        codegen = PenguCodegen(symbols=checker.symbols)
        codegen.collect_declarations([("main.pengu", tree)])
        c_code = codegen.generate_bundle()

        assert "int32_t mod_helper(void)" in c_code
        assert "mod_helper()" in c_code

    def test_insignia_at_end_of_file(self):
        # an insignia declared after all symbols has no effect on them.
        code = """
declare first_fn into void
insignia trailing_
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="test.pengu")
        _assert_semantic_errors(checker)
        assert checker.symbols.lookup("first_fn").c_name == "first_fn"

    def test_insignia_enchanting_methods(self):
        code = """
insignia gui_

rune Window:
    id as int

enchanting Window:
    weave show with self as Window into void:
        return
"""
        parser = PenguParser()
        tree = parser.parse(code)
        checker = PenguChecker()
        checker.check(tree, source=code, filename="gui.pengu")
        _assert_semantic_errors(checker)

        codegen = PenguCodegen(symbols=checker.symbols)
        codegen.collect_declarations([("gui.pengu", tree)])
        c_code = codegen.generate_bundle(is_library=True)

        assert "gui_Window_show" in c_code

    def test_insignia_cross_file_rune(self):
        with temp_project_dir("pengu_insx_") as d:
            write_file(d, "types_mod.d.pengu", """
insignia engine_

rune Color:
    r as int
    g as int
    b as int

declare create_color with r as int, g as int, b as int into Color
""")
            write_file(d, "main.pengu", """
import types_mod

weave main into void:
    var c as Color is calling types_mod.create_color with 255, 0, 0
""")
            order, trees, checker = check_all(d, "main.pengu")
            _assert_semantic_errors(checker)

            codegen = PenguCodegen(
                symbols=checker.symbols, import_order=order, base_dir=str(d),
            )
            codegen.collect_declarations(trees)
            c_code = codegen.generate_bundle()

            # runes declared by the .d.pengu must not be emitted in bundle.c
            assert "struct engine_Color;" not in c_code
            assert "struct engine_Color {" not in c_code
            assert "engine_create_color(255, 0, 0)" in c_code


# ---------------------------------------------------------------------------
# Project structure + bindings
# ---------------------------------------------------------------------------


class TestProjectBindings:
    """init_project layout, lib/<binding>/pengu resolution, builder integration."""

    def test_extract_lib_name(self):
        assert extract_lib_name("libwebui-2-static.a") == "webui-2-static"
        assert extract_lib_name("libraylib.a") == "raylib"
        assert extract_lib_name("webui.lib") == "webui"
        assert extract_lib_name("libfoo.so") == "foo"
        assert extract_lib_name("libbar.dylib") == "bar"
        assert extract_lib_name("foo.dll") == "foo"
        assert extract_lib_name("readme.txt") is None
        assert extract_lib_name("main.pengu") is None

    def test_init_project_creates_structure(self):
        with temp_project_dir("pengu_init_") as d:
            proj_dir = init_project("my_rpg", output_type="exe", target_dir=str(d))
            assert os.path.isdir(os.path.join(proj_dir, "src"))
            assert os.path.isdir(os.path.join(proj_dir, "lib"))
            assert os.path.isdir(os.path.join(proj_dir, "include"))
            assert os.path.isdir(os.path.join(proj_dir, "c"))
            assert os.path.isfile(os.path.join(proj_dir, "src", "main.pengu"))
            assert os.path.isfile(os.path.join(proj_dir, "pengu.yaml"))
            assert os.path.isfile(os.path.join(proj_dir, ".gitignore"))
            assert os.path.isfile(os.path.join(proj_dir, "README.md"))

            config = ProjectConfig.load(proj_dir)
            assert config.name == "my_rpg"
            assert config.src_dir == "src"
            assert config.lib_dir == "lib"
            assert config.include_dir == "include"
            assert config.c_dir == "c"
            assert config.resolve_entry() == os.path.abspath(
                os.path.join(proj_dir, "src", "main.pengu")
            )

    def test_find_module_path_in_src_and_lib(self):
        with temp_project_dir("pengu_path_") as d:
            proj_dir = os.path.join(str(d), "app")
            os.makedirs(os.path.join(proj_dir, "src", "math"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "lib", "webui", "pengu"), exist_ok=True)

            # internal src module
            vec_file = write_file(proj_dir, "src/math/vec.pengu",
                                  "rune Vec2:\n  x as float\n  y as float\n")
            # external binding module
            webui_file = write_file(
                proj_dir, "lib/webui/pengu/webui.pengu",
                'include "webui.h"\nlink "webui"\nweave new_window into int:\n  return 1\n',
            )

            res_vec = find_module_path(proj_dir, "math.vec")
            assert res_vec is not None
            assert os.path.abspath(res_vec) == os.path.abspath(vec_file)

            res_webui = find_module_path(proj_dir, "webui")
            assert res_webui is not None
            assert os.path.abspath(res_webui) == os.path.abspath(webui_file)

    def test_resolve_imports_with_binding(self):
        with temp_project_dir("pengu_rimp_") as d:
            proj_dir = os.path.join(str(d), "game")
            os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "lib", "raylib", "pengu"), exist_ok=True)

            write_file(
                proj_dir, "lib/raylib/pengu/raylib.pengu",
                'include "raylib.h"\nlink "raylib"\nweave init_window with w as int, h as int into void:\n  return\n',
            )
            write_file(
                proj_dir, "src/main.pengu",
                'import raylib\n\nweave main into void:\n  calling raylib.init_window with 800, 600\n',
            )

            order = resolve_imports(proj_dir, "src/main.pengu", PenguParser())
            assert len(order) == 2
            assert order[0].endswith("raylib.pengu")
            assert order[1].endswith("main.pengu")

    def test_bundle_with_binding_and_codegen(self):
        with temp_project_dir("pengu_bbind_") as d:
            proj_dir = os.path.join(str(d), "gui_app")
            os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "lib", "ui", "pengu"), exist_ok=True)

            write_file(
                proj_dir, "lib/ui/pengu/ui.pengu",
                'include "ui_native.h"\nlink "ui_native"\nweave show_dialog with msg as string into void:\n  calling print with msg\n',
            )
            write_file(
                proj_dir, "src/main.pengu",
                'import ui\n\nweave main into void:\n  var txt as string is "Hello UI"\n  calling ui.show_dialog with txt\n',
            )

            config = ProjectConfig(name="gui_app", base_dir=proj_dir, entry="src/main.pengu")
            builder = PenguBuilder(config)
            bundle_path, _is_cached = builder.bundle()
            assert os.path.isfile(bundle_path)

            with open(bundle_path, "r", encoding="utf-8") as f:
                c_code = f.read()

            assert '#include "ui_native.h"' in c_code
            assert "show_dialog" in c_code
            assert "pengu_main" in c_code

    def test_build_compile_commands_collects_c_and_lib_dirs(self):
        with temp_project_dir("pengu_cc_") as d:
            proj_dir = os.path.join(str(d), "multi_c_proj")
            os.makedirs(os.path.join(proj_dir, "src"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "include"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "c"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "lib", "mylib", "include"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "lib", "mylib", "c"), exist_ok=True)
            os.makedirs(os.path.join(proj_dir, "lib", "mylib", "lib"), exist_ok=True)

            # project C glue
            write_file(proj_dir, "c/helper.c", "void helper_fn() {}\n")
            # binding C glue
            write_file(proj_dir, "lib/mylib/c/mylib_glue.c", "void mylib_c_func() {}\n")
            # binding precompiled library (dummy file to test detection)
            write_file(proj_dir, "lib/mylib/lib/libmylib_native.a", "dummy archive")

            config = ProjectConfig(
                name="multi_c_app",
                base_dir=proj_dir,
                entry="src/main.pengu",
                output=OutputType.EXE,
            )
            builder = PenguBuilder(config)
            commands = builder.build_compile_commands("build/bundle.c", "build/app.exe")
            assert len(commands) == 1

            cmd_args = commands[0]
            cmd_str = " ".join(cmd_args)

            # project + binding C sources are compiled in
            assert any("helper.c" in arg for arg in cmd_args)
            assert any("mylib_glue.c" in arg for arg in cmd_args)

            # include dirs from the project and the binding
            assert any(arg.startswith("-I") and "include" in arg for arg in cmd_args)
            assert any(arg.startswith("-I") and "mylib" in arg for arg in cmd_args)

            # library search dir + link flag
            assert any(arg.startswith("-L") and "mylib" in arg for arg in cmd_args)
            assert "-lmylib_native" in cmd_str

    def test_add_dependency_local_folder(self):
        with temp_project_dir("pengu_adddep_") as d:
            # 1. fresh project
            proj_dir = init_project("main_app", output_type="exe", target_dir=str(d))

            # 2. external local binding folder
            ext_binding = os.path.join(str(d), "webui_repo")
            os.makedirs(os.path.join(ext_binding, "pengu"), exist_ok=True)
            os.makedirs(os.path.join(ext_binding, "include"), exist_ok=True)
            os.makedirs(os.path.join(ext_binding, "c"), exist_ok=True)
            os.makedirs(os.path.join(ext_binding, "lib"), exist_ok=True)
            write_file(ext_binding, "pengu/webui.pengu", "weave webui_init into int:\n  return 0\n")
            write_file(ext_binding, "include/webui.h", "int webui_init(void);\n")
            write_file(ext_binding, "build.py", 'print("Building webui...")\n')

            # 3. add the dependency
            added_dir = add_dependency(
                source=ext_binding,
                name="webui",
                config_path=proj_dir,
                run_build=True,
            )
            assert os.path.isdir(added_dir)
            assert os.path.isfile(os.path.join(added_dir, "pengu", "webui.pengu"))
            assert os.path.isfile(os.path.join(added_dir, "include", "webui.h"))

            # 4. pengu.yaml records the dependency
            with open(os.path.join(proj_dir, "pengu.yaml"), "r", encoding="utf-8") as f:
                yaml_txt = f.read()
            assert "webui" in yaml_txt

    def test_legacy_flat_project_compatibility(self):
        with temp_project_dir("pengu_legacy_") as d:
            legacy_dir = os.path.join(str(d), "legacy")
            os.makedirs(legacy_dir, exist_ok=True)
            write_file(legacy_dir, "main.pengu", "weave main into void:\n  calling print with 123\n")
            write_file(legacy_dir, "pengu.yaml", "project:\n  name: legacy\n  entry: main.pengu\n")

            config = ProjectConfig.load(legacy_dir)
            assert config.resolve_entry() == os.path.abspath(os.path.join(legacy_dir, "main.pengu"))

            builder = PenguBuilder(config)
            bundle_path, _ = builder.bundle()
            assert os.path.isfile(bundle_path)


# ---------------------------------------------------------------------------
# pengu bind (C header -> .d.pengu generator)
# ---------------------------------------------------------------------------

DEMO_HEADER = """\
/* Demo header used by the bind tests. */
#ifndef DEMO_H
#define DEMO_H

#include <stdbool.h>
#include <stddef.h>

#define DEMO_LIMIT 128
#define DEMO_NAME "demo"
#define DEMO_SKIP 1

typedef struct Point {
    int x;
    float y;
} Point;

enum color {
    RED = 3,
    GREEN,
    BLUE,
};

typedef void (*change_cb)(int value, const char* text);

int add(int a, int b);
bool set_path(const char* path, size_t n, Point* p, change_cb fn);
void* alloc_raw(unsigned long long n);

#endif
"""

# Minimal stand-in for the real webui.h (which lived under the removed
# CToPenguTest/ tree in the historical repo). Exercised through the full
# preprocess -> pycparser -> .d.pengu pipeline, and the result must pass the
# semantic checker standalone.
WEBUI_STUB_HEADER = """\
/* Minimal webui.h stand-in used by the bind tests. */
#ifndef WEBUI_STUB_H
#define WEBUI_STUB_H

#include <stddef.h>
#include <stdbool.h>

typedef struct webui_event_t {
    size_t size;
    unsigned char type;
    const char* name;
} webui_event_t;

typedef void (*webui_event_cb)(webui_event_t* e);

size_t webui_new_window(void);
void webui_show(size_t window, const char* content);
void webui_wait(void);

#endif
"""


@pytest.mark.skipif(not HAVE_CC, reason="pengu bind runs gcc -E; no C compiler available")
class TestPenguBindGenerator:
    """generate_bind_file: preprocesses a C header (gcc -E over c_bind_stubs/)
    and emits a .d.pengu declaration binding."""

    @staticmethod
    def _gen(header_text: str, name: str = "demo.h", **kw) -> str:
        with temp_project_dir("pengu_bind_") as d:
            hdr = write_file(d, name, header_text)
            out = os.path.join(str(d), Path(name).stem + ".d.pengu")
            kw.setdefault("output", out)
            kw.setdefault("prefix", "")
            generate_bind_file(hdr, **kw)
            with open(out, "r", encoding="utf-8") as f:
                return f.read()

    def test_header_and_links_lines(self):
        text = self._gen(DEMO_HEADER, links=["demo", "m"])
        assert 'include "demo.h"' in text
        assert 'link "demo"' in text
        assert 'link "m"' in text

    def test_const_macros(self):
        text = self._gen(DEMO_HEADER)
        assert "const DEMO_LIMIT as i64 is 128" in text
        assert 'const DEMO_NAME as string is "demo"' in text

    def test_struct_enum_callback_function(self):
        text = self._gen(DEMO_HEADER)
        assert "rune Point:" in text
        assert "  x as int" in text
        assert "  y as f32" in text
        assert "omen color:" in text
        assert "  RED is 3" in text
        assert "  GREEN is 4" in text
        assert "  BLUE is 5" in text
        assert "alias change_cb as ref to weave with value as int, text as ref to frozen char into void" in text
        assert "declare add with a as int, b as int into int" in text
        assert "declare set_path with path as ref to frozen char, n as size_t, p as ref to Point, fn as change_cb into bool" in text
        assert "declare alloc_raw with n as u64 into ref to void" in text

    def test_ignore_patterns(self):
        text = self._gen(DEMO_HEADER, ignore=[r"DEMO_.*", "add"])
        assert "DEMO_LIMIT" not in text
        assert "declare add" not in text
        assert "rune Point:" in text

    def test_insignia_prefix_added(self):
        text = self._gen(DEMO_HEADER, prefix="demo_")
        assert "insignia demo_" in text
        # fixture names are plain, so the declared name keeps no extra prefix
        assert "declare add with a as int, b as int into int" in text

    def test_no_comments(self):
        # a doc comment directly above a declaration becomes a single-line '#'
        # comment, unless no_comments is set.
        header = """\
/* Demo header used by the bind tests. */
#ifndef DEMO_H
#define DEMO_H

/* Returns the sum of a and b. */
int add(int a, int b);

#endif
"""
        text = self._gen(header)
        assert "# Returns the sum of a and b." in text

        text_no_c = self._gen(header, no_comments=True)
        assert "Returns the sum of a and b." not in text_no_c

    def test_webui_end_to_end(self):
        with temp_project_dir("pengu_bindwebui_") as d:
            hdr = write_file(d, "webui.h", WEBUI_STUB_HEADER)
            out = os.path.join(str(d), "webui.d.pengu")
            p = generate_bind_file(
                hdr, output=out, prefix="webui_",
                links=["webui-2-static", "ole32"],
            )
            with open(p, encoding="utf-8") as f:
                text = f.read()
            assert 'include "webui.h"' in text
            assert "insignia webui_" in text
            assert "declare new_window into size_t" in text
            assert "rune webui_event_t:" in text
            assert "alias " in text
            # The generated .d.pengu must pass the semantic checker standalone.
            checker = PenguChecker(base_dir=str(REPO))
            checker.check(PenguParser().parse(text), source=text, filename=p)
            _assert_semantic_errors(checker)


@pytest.mark.skipif(not HAVE_CC, reason="pengu bind runs gcc -E; no C compiler available")
class TestPenguBindCurrentLanguage:
    """The generator must emit what the current language accepts.

    Covers the 0.10.0 output rules (comma separators, single-line `#` comments)
    plus the features added later: `frozen` for `const` signatures, the
    `frozen`-aware C-string literal conversion, auto `import` of the bindings
    for included headers, callback aliases hoisted out of struct bodies and the
    dropping of enum aliases (PenguScript omens reject duplicate values).
    """

    @staticmethod
    def _gen(header_text: str, name: str = "demo.h", **kw) -> str:
        with temp_project_dir("pengu_bind_lang_") as d:
            hdr = write_file(d, name, header_text)
            out = os.path.join(str(d), Path(name).stem + ".d.pengu")
            kw.setdefault("output", out)
            generate_bind_file(hdr, **kw)
            with open(out, "r", encoding="utf-8") as f:
                return f.read()

    @staticmethod
    def _check(text: str, filename: str = "demo.d.pengu", base_dir=None):
        checker = PenguChecker(base_dir=str(base_dir or REPO))
        checker.check(PenguParser().parse(text), source=text, filename=filename)
        _assert_semantic_errors(checker)

    def test_multiline_comment_becomes_one_hash_line_each(self):
        text = self._gen(
            "/* Demo header.\n"
            " * Second line.\n"
            " * Third line.\n"
            " */\n"
            "int add(int a, int b);\n"
        )
        assert "# Demo header." in text
        assert "# Second line." in text
        assert "# Third line." in text
        assert "## Second line." not in text
        # Only the generated-file banner keeps the '##' doc marker.
        assert all(not line.startswith("##") or "pengu bind" in line or "Source header" in line
                   for line in text.splitlines())

    def test_const_parameters_become_frozen(self):
        text = self._gen(
            "void show(const char *text, const void *blob);\n"
            "const int LIMIT = 10;\n"
        )
        assert "declare show with text as ref to frozen char, blob as ref to frozen void into void" in text

    def test_const_pointer_qualifier_is_dropped(self):
        # 'char * const p' freezes the pointer, which is what 'let' expresses.
        text = self._gen("void poke(char * const p);\n")
        assert "declare poke with p as ref to char into void" in text
        assert "frozen" not in text

    def test_string_literal_flows_into_frozen_char(self):
        # The generated signature must stay callable with a plain literal.
        text = self._gen("void show(const char *text);\n")
        with temp_project_dir("pengu_bind_str_") as d:
            mod = write_file(d, "demo.d.pengu", text)
            entry = write_file(d, "main.pengu",
                               'import demo\n\nweave main into int:\n'
                               '    calling show with "hello"\n    return 0\n')
            parser = PenguParser()
            order = resolve_imports(str(d), entry, parser)
            checker = PenguChecker(base_dir=str(d))
            for i, path in enumerate(order):
                code = Path(path).read_text(encoding="utf-8")
                checker.check(parser.parse(code), source=code, filename=path,
                              reset_symbols=(i == 0), import_order=order)
            _assert_semantic_errors(checker)
            assert os.path.isfile(mod)

    def test_auto_import_of_included_headers(self):
        with temp_project_dir("pengu_bind_imp_") as d:
            write_file(d, "base.h", "typedef struct Base { int x; } Base;\n")
            write_file(d, "top.h", '#include "base.h"\ntypedef struct Top { Base b; } Top;\n')
            # Bind the dependency first so its banner records the header.
            generate_bind_file(str(d / "base.h"), output=str(d / "base.d.pengu"),
                               include_paths=[str(d)])
            text = Path(generate_bind_file(str(d / "top.h"), output=str(d / "top.d.pengu"),
                                           include_paths=[str(d)])).read_text(encoding="utf-8")
            assert "#   base.h" in text
            assert "import" in text and "base" in text
            # …and never imports itself.
            assert "import pen..top" not in text

    def test_callback_alias_is_hoisted_out_of_the_struct(self):
        text = self._gen(
            "typedef struct io {\n"
            "    int (*read)(void *user, char *data, int size);\n"
            "    void (*skip)(void *user, int n);\n"
            "} io;\n"
        )
        lines = [l for l in text.splitlines() if l.strip()]
        rune_at = next(i for i, l in enumerate(lines) if l.startswith("rune io:"))
        aliases = [i for i, l in enumerate(lines) if l.startswith("alias Callback")]
        assert aliases, "no callback alias emitted"
        assert max(aliases) < rune_at, "aliases must precede the rune"
        assert lines[rune_at + 1].startswith("  read as Callback")
        assert lines[rune_at + 2].startswith("  skip as Callback")
        self._check(text)

    def test_duplicate_enum_values_are_dropped(self):
        text = self._gen(
            "typedef enum mode {\n"
            "    MODE_A = 0,\n"
            "    MODE_B = 1,\n"
            "    MODE_ALIAS = 1,\n"
            "} mode;\n"
        )
        assert "  MODE_B is 1" in text
        assert "MODE_ALIAS" not in text
        self._check(text)

    def test_generated_binding_checks_clean(self):
        text = self._gen(
            "typedef enum level { LOG_OFF = 0, LOG_ON = 1 } level;\n"
            "typedef struct point { float x; float y; } point;\n"
            "const char *name_of(const point *p);\n"
            "void move(point *p, float dx, float dy);\n"
        )
        assert "rune point:" in text
        assert "omen level:" in text
        assert "declare name_of with p as ref to frozen point into ref to frozen char" in text
        assert "declare move with p as ref to point, dx as f32, dy as f32 into void" in text
        self._check(text)
