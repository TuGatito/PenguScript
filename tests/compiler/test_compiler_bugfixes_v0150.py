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


# ─── Bug 2 — Prefix heuristic hazards flatten ─────────────────────────
class TestBug2_PrefixHeuristicHazard:
    @requires_runtime
    def test_flatten_does_not_get_rewritten(self):
        """loom.flatten(...) must not be rewritten to oracle.flatten_maybe_*."""
        src = """
import std.spark
import std.loom
import std.oracle

weave main into int:
    var nested as list of list of int is [[1, 2], [3, 4], [5]]
    let flat is calling loom.flatten of int with nested
    calling spark.println with "{(calling flat.len to string)}"
    return 0
"""
        res = compile_run(src, tag="bug2_flatten_loom")
        assert res.stdout.strip() == "5"

    def test_imported_flatten_not_rewritten_to_oracle_monomorph(self):
        """A module importing oracle and another module with flatten must not rewrite the call."""
        import tempfile
        import shutil
        from pengu_project import PenguBuilder, ProjectConfig
        from tests.conftest import BUILD_DIR
        d = Path(tempfile.mkdtemp(prefix="bug2_test_", dir=BUILD_DIR))
        try:
            (d / "helper.pengu").write_text("weave flatten with x as int into int:\n    return x * 10\n", encoding="utf-8")
            (d / "main.pengu").write_text("""
import std.oracle
import helper

weave use_oracle with opt as maybe string into maybe string:
    return calling oracle.flatten_maybe with opt

weave main into int:
    return calling helper.flatten with 5
""", encoding="utf-8")
            cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(d), output="c")
            bundle_path, _ = PenguBuilder(cfg).bundle(output_file=str(d / "bundle.c"))
            content = Path(bundle_path).read_text(encoding="utf-8")
            assert "flatten_maybe_string(5)" not in content
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ─── Bug 3 — Weave-as-value in test loses prefix ──────────────────────
class TestBug3_WeaveAsValueInTest:
    def test_callback_in_test_block_uses_prefix(self):
        """Weave-as-value inside test blocks must carry the module prefix."""
        import tempfile
        import shutil
        from pengu_project import PenguBuilder, ProjectConfig
        from tests.conftest import BUILD_DIR
        d = Path(tempfile.mkdtemp(prefix="bug3_test_", dir=BUILD_DIR))
        try:
            std_d = d / "std"
            std_d.mkdir(parents=True, exist_ok=True)
            (std_d / "helper.pengu").write_text("""
weave my_callback with x as int into int:
    return x + 1

test "callback in std mod":
    var cb as ref to weave with x as int into int is my_callback
    let r is calling cb with 41
""", encoding="utf-8")
            (d / "main.pengu").write_text("""
import std.helper

test "callback in main from std mod":
    var cb as ref to weave with x as int into int is helper.my_callback
    let r is calling cb with 41
""", encoding="utf-8")
            cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(d), profile="debug", output="c")
            builder = PenguBuilder(cfg)
            builder.is_test_mode = True
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))
            content = Path(bundle_path).read_text(encoding="utf-8")
            # In generated code, all references to my_callback must carry the module prefix.
            import re
            matches = [m.group(0) for m in re.finditer(r"\b\w*my_callback\b", content)]
            assert len(matches) > 0
            assert all(m == "helper_my_callback" for m in matches)
            check_c_syntax(content)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_insignia_callback_in_test_block_preserves_prefix(self):
        """Insignia-prefixed weave as a value inside test block keeps prefix."""
        import tempfile
        import shutil
        from pengu_project import PenguBuilder, ProjectConfig
        from tests.conftest import BUILD_DIR
        d = Path(tempfile.mkdtemp(prefix="bug3_insignia_", dir=BUILD_DIR))
        try:
            (d / "main.pengu").write_text("""
insignia mylib_

weave step_fn with x as int into int:
    return x * 2

test "insignia callback in test":
    var cb as ref to weave with x as int into int is step_fn
    let r is calling cb with 10
""", encoding="utf-8")
            cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(d), profile="debug", output="c")
            builder = PenguBuilder(cfg)
            builder.is_test_mode = True
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))
            content = Path(bundle_path).read_text(encoding="utf-8")
            assert "mylib_step_fn" in content
            check_c_syntax(content)
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ─── Bug 4 — Unqualified symbols collide in tests ─────────────────────
class TestBug4_UnqualifiedInTest:
    def test_local_is_empty_wins_in_test(self):
        """Unqualified is_empty in test resolves to owning module without colliding with imported std.atlas."""
        import tempfile
        import shutil
        from pengu_project import PenguBuilder, ProjectConfig
        from tests.conftest import BUILD_DIR
        d = Path(tempfile.mkdtemp(prefix="bug4_test_", dir=BUILD_DIR))
        try:
            src = """
import std.spark
import std.atlas

weave is_empty with s as string into bool:
    return (s.length == 0)

test "local is_empty is used":
    let s is ""
    calling spark.println with "{(calling is_empty with s to string)}"
"""
            (d / "main.pengu").write_text(src, encoding="utf-8")
            cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(d), profile="debug", output="c")
            builder = PenguBuilder(cfg)
            builder.is_test_mode = True
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))
            content = Path(bundle_path).read_text(encoding="utf-8")
            check_c_syntax(content)
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ─── Bug 6 — pengu test bundles imported tests ────────────────────────
class TestBug6_TestBundling:
    def test_imported_std_tests_are_not_bundled(self):
        """Bundling a project that imports std modules excludes their internal tests."""
        import tempfile
        import shutil
        from pengu_project import PenguBuilder, ProjectConfig
        from tests.conftest import BUILD_DIR
        d = Path(tempfile.mkdtemp(prefix="bug6_user_", dir=BUILD_DIR))
        try:
            src = """
import std.atlas

test "my unique user test":
    let m is map of string to int
"""
            (d / "main.pengu").write_text(src, encoding="utf-8")
            cfg = ProjectConfig(entry=str(d / "main.pengu"), base_dir=str(d), profile="debug", output="c")
            builder = PenguBuilder(cfg)
            builder.is_test_mode = True
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))
            content = Path(bundle_path).read_text(encoding="utf-8")
            assert "my unique user test" in content
            assert "len cuenta bytes" not in content
            assert "pengu_test_names[1]" in content
            check_c_syntax(content)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_own_std_tests_are_bundled_when_entry(self):
        """Bundling a std module as entry retains all its own unit tests."""
        import tempfile
        import shutil
        from pengu_project import PenguBuilder, ProjectConfig
        from tests.conftest import BUILD_DIR
        d = Path(tempfile.mkdtemp(prefix="bug6_std_", dir=BUILD_DIR))
        try:
            cfg = ProjectConfig(entry="std/scrolls.pengu", base_dir=".", profile="debug", output="c")
            builder = PenguBuilder(cfg)
            builder.is_test_mode = True
            bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))
            content = Path(bundle_path).read_text(encoding="utf-8")
            assert "len cuenta bytes" in content
            assert "pengu_test_names[124]" in content
            check_c_syntax(content)
        finally:
            shutil.rmtree(d, ignore_errors=True)


# ─── Bug 5 — or/and boolean semantics & short-circuiting ───────────────
class TestBug5_OrAndBoolean:
    def test_or_requires_bool_operands(self):
        """Logical 'or' rejects non-boolean operands with E0005."""
        from tests.conftest import check_error
        code = """
weave main into int:
    let x is 1 or 2
    return 0
"""
        check_error(code, contains="E0005")

    def test_and_requires_bool_operands(self):
        """Logical 'and' rejects non-boolean operands with E0005."""
        from tests.conftest import check_error
        code = """
weave main into int:
    let x is 1 and 2
    return 0
"""
        check_error(code, contains="E0005")

    @requires_runtime
    def test_logical_short_circuit_runtime(self):
        """Logical 'or' and 'and' short-circuit and do not evaluate RHS when LHS determines result."""
        code = """
import std.spark

weave trigger into bool:
    static var called as int is 0
    set called is called + 1
    calling spark.println with "TRIGGERED"
    return true

weave main into int:
    let a is true or (calling trigger)
    let b is false and (calling trigger)
    calling spark.println with "SHORT_CIRCUIT_OK"
    return 0
"""
        res = compile_run(code, tag="bug5_short_circuit")
        assert "TRIGGERED" not in res.stdout
        assert "SHORT_CIRCUIT_OK" in res.stdout

    @requires_runtime
    def test_or_else_fallback_for_maybe(self):
        """Unwrapping with fallback semantics is properly achieved with 'or else'."""
        code = """
import std.spark

weave main into int:
    var m as maybe int is maybe none
    let v is m or else 42
    var s as maybe int is some 99
    let w is s or else 42
    calling spark.println with "{v} {w}"
    return 0
"""
        res = compile_run(code, tag="bug5_or_else")
        assert res.stdout.strip() == "42 99"




