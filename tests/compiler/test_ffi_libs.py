#!/usr/bin/env python3
"""tests/compiler/test_ffi_libs.py - C-FFI / external-library integration tests.

Phase 1 moved every external C binding out of `std/` (PCRE2, libxml2, sqlite3,
raylib, stb, xlsxio, tomlc17, yaml, ...).  What remains here is the coverage of
things that still exist in-tree:

  * the C runtime header API contract;
  * ``std.filum`` concurrency primitives, compiled and run against the runtime;
  * ``std.archivum`` recursive tree helpers (pure PenguScript).

Everything is guarded with ``requires_runtime`` so the suite stays green on a
machine where ``build_runtime.py`` has not produced the archive.
"""

import shutil

from tests.conftest import (
    REPO,
    compile_run,
    requires_runtime,
)


def _expect_stdout(res, *markers: str):
    for marker in markers:
        assert marker in res.stdout, f"missing {marker!r} in output:\n{res.stdout}"


# ---------------------------------------------------------------------------
# 1. C runtime header API contract
# ---------------------------------------------------------------------------


class TestRuntimeHeader:
    """pengu_runtime.h must keep the documented C surface."""

    HEADER = REPO / "pengu_runtime.h"

    def test_core_types_and_string_primitives_present(self):
        content = TestRuntimeHeader.HEADER.read_text(encoding="utf-8")
        for token in (
            "PenguList", "PenguMap", "PenguSlice", "PenguMaybe",
            "PenguResult", "PenguString", "pengu_banish",
            # Core string primitives retained in C (compiler lowering + byte access)
            "pengu_string_substring", "pengu_string_char_at",
            "pengu_string_concat", "pengu_string_equal", "pengu_string_from_cstr",
        ):
            assert token in content, f"pengu_runtime.h no longer defines {token}"

    def test_list_and_map_helpers_present(self):
        content = TestRuntimeHeader.HEADER.read_text(encoding="utf-8")
        for token in (
            "pengu_list_push_int", "pengu_list_push_string", "pengu_list_pop_int",
            "pengu_list_contains_int", "pengu_list_index_of_int",
            "pengu_map_put_string_int", "pengu_map_get_string_int",
            "pengu_map_contains_string_int", "pengu_map_remove_string_int",
        ):
            assert token in content, f"pengu_runtime.h no longer defines {token}"

    def test_migrated_utilities_removed_from_header(self):
        # String utilities moved to std/scrolls.pengu ...
        content = TestRuntimeHeader.HEADER.read_text(encoding="utf-8")
        for token in ("static inline int scrolls_len", "pengu_string_upper"):
            assert token not in content, f"{token} should live in std, not the C header"
        # ... and path handling moved to std/compass.pengu.
        for token in ("pengu_c_path_is_sep", "pengu_c_path_normalize",
                      "pengu_c_path_join", "pengu_c_path_relative_to"):
            assert token not in content, f"{token} should live in std, not the C header"


# ---------------------------------------------------------------------------
# 2. Runtime + filum concurrency
# ---------------------------------------------------------------------------


class TestRuntimeDeps:
    """Compile+run against the runtime's remaining (internal) subsystem."""

    @requires_runtime
    def test_real_concurrency_execution(self):
        """Filum concurrency primitives: AtomicInt, Mutex, WaitGroup, sleep."""
        src = '\nimport std.spark\nimport std.oracle\nimport std.filum\n\nweave main into void:\n    calling spark.println with "=== Testing Real Filum Concurrency ==="\n\n    # 1. AtomicInt\n    var counter as AtomicInt is calling filum.atomic_int with 10\n    var cur_val as int is calling counter.load\n    calling spark.println with "atomic load: {cur_val}"\n\n    var added as int is calling counter.add with 5\n    var new_val as int is calling counter.load\n    calling spark.println with "atomic new: {new_val}"\n\n    # 2. Mutex\n    var mtx as Mutex is calling filum.mutex\n    calling mtx.lock\n    calling spark.println with "mutex locked"\n    calling mtx.unlock\n    calling spark.println with "mutex unlocked"\n\n    # 3. WaitGroup\n    var wg as WaitGroup is calling filum.wait_group\n    calling wg.add with 1\n    calling spark.println with "wg added 1"\n    calling wg.done\n    calling spark.println with "wg done"\n    calling wg.wait\n    calling spark.println with "wg wait ok"\n\n    # 4. Sleep\n    calling filum.sleep with 10\n    calling spark.println with "sleep ok"\n\n    calling spark.println with "=== Filum OK ==="\n'
        res = compile_run(src, tag="real_filum")
        _expect_stdout(res,
                       "=== Testing Real Filum Concurrency ===",
                       "atomic load: 10", "atomic new: 15",
                       "mutex locked", "mutex unlocked",
                       "wg added 1", "wg done", "wg wait ok",
                       "sleep ok", "=== Filum OK ===")

    @requires_runtime
    def test_filum_resource_cleanup(self):
        """Every filum primitive can be disposed through its new free API."""
        src = r"""
import std.spark
import std.filum

weave main into void:
    calling spark.println with "=== Filum Cleanup ==="

    var mtx as Mutex is calling filum.mutex
    calling mtx.lock
    calling mtx.unlock
    calling mtx.free

    var wg as WaitGroup is calling filum.wait_group
    calling wg.free

    var o as Once is calling filum.once
    calling o.free

    var cv as Cond is calling filum.cond
    calling cv.free

    var atom as AtomicInt is calling filum.atomic_int with 7
    calling atom.free

    # functional wrappers (ref-taking) resolve to the same C cleanup
    var mtx2 as Mutex is calling filum.mutex
    calling filum.free_mutex with sigil of mtx2
    var wg2 as WaitGroup is calling filum.wait_group
    calling filum.free_wait_group with sigil of wg2
    var o2 as Once is calling filum.once
    calling filum.free_once with sigil of o2
    var cv2 as Cond is calling filum.cond
    calling filum.free_cond with sigil of cv2
    var atom2 as AtomicInt is calling filum.atomic_int with 1
    calling filum.free_atomic_int with sigil of atom2

    calling spark.println with "=== Filum Cleanup OK ==="
"""
        res = compile_run(src, tag="filum_free")
        _expect_stdout(res,
                       "=== Filum Cleanup ===",
                       "=== Filum Cleanup OK ===")


# ---------------------------------------------------------------------------
# 3. std.archivum recursive tree helpers  (pure PenguScript)
# ---------------------------------------------------------------------------


class TestArchivumTree:
    """copy_tree / list_files_recursive - pure Pengu, gated on the runtime."""

    REL_SRC = "build/pengu_ffi_arch_src"
    REL_DST = "build/pengu_ffi_arch_dst"

    @requires_runtime
    def test_copy_tree_and_list_files_recursive(self):
        src_dir = REPO / "build" / "pengu_ffi_arch_src"
        dst_dir = REPO / "build" / "pengu_ffi_arch_dst"
        for d in (src_dir, dst_dir):
            shutil.rmtree(d, ignore_errors=True)
        try:
            demo = r"""import std.spark
import std.archivum

weave main into int:
    var ok_root as bool is calling archivum.create_dir with "{src}", true
    if ok_root == false:
        calling spark.println with "mkdir failed"
        return 1
    var ok_a as bool is calling archivum.write_file with "{src}/a.txt", "alpha"
    if ok_a == false:
        return 1
    var ok_sub as bool is calling archivum.create_dir with "{src}/sub", true
    if ok_sub == false:
        return 1
    var ok_b as bool is calling archivum.write_file with "{src}/sub/b.txt", "beta"
    if ok_b == false:
        return 1
    var copied as bool is calling archivum.copy_tree with "{src}", "{dst}"
    if copied == false:
        calling spark.println with "copy failed"
        return 1
    var files as list of string is calling archivum.list_files_recursive with "{dst}"
    if files.len == 2:
        calling spark.println with "list ok"
    var a_ok as bool is calling archivum.is_file with "{dst}/a.txt"
    var b_ok as bool is calling archivum.is_file with "{dst}/sub/b.txt"
    if a_ok:
        if b_ok:
            calling spark.println with "copy_tree ok"
    return 0
""".format(src=TestArchivumTree.REL_SRC, dst=TestArchivumTree.REL_DST)
            res = compile_run(demo, tag="archivum")
            _expect_stdout(res, "list ok", "copy_tree ok")
            assert (dst_dir / "a.txt").is_file()
            assert (dst_dir / "sub" / "b.txt").is_file()
        finally:
            for d in (src_dir, dst_dir):
                shutil.rmtree(d, ignore_errors=True)
