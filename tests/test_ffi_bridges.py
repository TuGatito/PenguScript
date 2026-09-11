#!/usr/bin/env python3
"""Tests for the C <-> Pengu conversion bridges.

Covers three levels:
* the new runtime bridge functions are exercised by a small C driver compiled
  against libpengu_runtime.a (null-safety, list/map/entry deep copies),
* std/ffi.pengu module wrappers run end-to-end through the std-program runner
  (see tests/std_programs/test_ffi.pengu registered in test_stdlib.py),
* the generated bundle.c contains the expected C calls for each wrapper.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from tests.conftest import (
    BUILD_DIR,
    BUILD_INCLUDE,
    BUILD_LIB,
    REPO,
    have_tool,
    runtime_link_flags,
    runtime_tail_flags,
)

_HAVE_CC = have_tool("gcc") or have_tool("clang") or have_tool("cc")
_HAVE_RUNTIME = (BUILD_LIB / "libpengu_runtime.a").is_file()

requires_cc = pytest.mark.skipif(not _HAVE_CC, reason="no C compiler available")
requires_runtime = pytest.mark.skipif(
    not _HAVE_RUNTIME, reason="libpengu_runtime.a not built (run build_runtime.py)"
)

DRIVER = r"""
#include "pengu_runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

int main(void) {
    /* Null-safe string views */
    CHECK(pengu_string_to_cstr(NULL) != NULL && pengu_string_to_cstr(NULL)[0] == '\0',
          "to_cstr(NULL) -> empty, never NULL");
    PenguString empty = {NULL, 0};
    CHECK(pengu_string_to_cstr(&empty)[0] == '\0', "to_cstr(empty) -> static empty");
    CHECK(pengu_string_bytes(NULL) != NULL, "string_bytes(NULL) never NULL");
    CHECK(pengu_slice_data(NULL) == NULL, "slice_data(NULL) -> NULL");
    CHECK(pengu_list_data(NULL) == NULL, "list_data(NULL) -> NULL");

    PenguString hi = pengu_string_new("hello");
    CHECK(strcmp(pengu_string_to_cstr(&hi), "hello") == 0, "to_cstr content");
    CHECK(pengu_string_bytes(&hi) == (const void *)hi.data, "string_bytes aliases data");

    PenguSlice vs = pengu_string_as_slice(hi);
    CHECK(vs.len == 5, "string_as_slice length");
    PenguString copy = pengu_string_copy(hi);
    CHECK(copy.len == 5 && strcmp(copy.data, "hello") == 0, "string_copy owns buffer");
    pengu_banish_string(&copy);
    pengu_banish_string(&hi);

    /* List bridge: NULL/count safety and content copy */
    PenguList l0 = pengu_list_from_data(NULL, 4, 3);
    CHECK(l0.len == 0, "list_from_data(NULL) empty");
    pengu_banish_list(&l0);
    int32_t src[3] = {10, 20, 30};
    PenguList l = pengu_list_from_data(src, sizeof(int32_t), 3);
    CHECK(l.len == 3 && l.elem_size == sizeof(int32_t), "list_from_data len/size");
    CHECK(((int32_t *)pengu_list_data(&l))[1] == 20, "list_from_data copied content");
    pengu_banish_list(&l);

    /* Map bridges: int keys */
    PenguMap m0 = pengu_map_from_entries(NULL, NULL, 4, 4, 5);
    CHECK(m0.len == 0, "map_from_entries(NULL) empty");
    pengu_banish_map(&m0);
    int32_t ks[2] = {7, 9};
    int32_t vals[2] = {70, 90};
    PenguMap m = pengu_map_from_entries(ks, vals, sizeof(int32_t), sizeof(int32_t), 2);
    CHECK(m.len == 2, "map_from_entries len");
    PenguEntryArray arr = pengu_map_to_entries(&m);
    CHECK(arr.count == 2, "map_to_entries count");
    int found = 0;
    for (int i = 0; i < arr.count; ++i) {
        if (((int32_t *)arr.keys)[i] == 7 && ((int32_t *)arr.values)[i] == 70)
            found = 1;
    }
    CHECK(found == 1, "map int round trip pair preserved");
    pengu_entry_array_free(&arr);
    pengu_banish_map(&m);

    /* Map bridges: deep-copied PenguString keys */
    PenguString ka[2] = {pengu_string_from_cstr("a"), pengu_string_from_cstr("b")};
    int32_t va[2] = {1, 2};
    PenguMap ms = pengu_map_from_entries(ka, va, sizeof(PenguString), sizeof(int32_t), 2);
    CHECK(ms.len == 2, "string map len");
    PenguEntryArray sa = pengu_map_to_entries(&ms);
    CHECK(sa.count == 2 && sa.key_size == sizeof(PenguString), "string map to_entries");
    found = 0;
    for (int i = 0; i < sa.count; ++i) {
        PenguString *k = (PenguString *)sa.keys + i;
        int32_t *v = (int32_t *)sa.values + i;
        if (strcmp(k->data, "a") == 0 && *v == 1)
            found++;
    }
    CHECK(found >= 1, "string map pair deep copied");
    pengu_entry_array_free(&sa);
    pengu_banish_map(&ms);

    if (failures == 0) {
        printf("FFI BRIDGES OK\n");
        return 0;
    }
    printf("FFI BRIDGES FAILURES: %d\n", failures);
    return 1;
}
"""


@requires_cc
@requires_runtime
def test_runtime_bridge_c_driver():
    """The new runtime bridge functions behave (null-safety + deep copies)."""
    d = Path(tempfile.mkdtemp(prefix="ffi_driver_", dir=BUILD_DIR))
    try:
        cfile = d / "driver.c"
        cfile.write_text(DRIVER, encoding="utf-8")
        cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
        exe = d / ("driver.exe" if os.name == "nt" else "driver")
        cmd = [cc, str(cfile), f"-I{REPO}", f"-I{BUILD_DIR}", f"-I{BUILD_INCLUDE}",
               f"-L{BUILD_LIB}"]
        cmd += ["-Wno-error=implicit-function-declaration",
                "-Wno-error=implicit-int",
                "-Wno-error=int-conversion"]
        cmd += runtime_link_flags()
        cmd += runtime_tail_flags()
        cmd += ["-o", str(exe)]
        comp = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        assert comp.returncode == 0, (
            f"C driver compilation failed:\n{comp.stderr}\n{comp.stdout}"
        )
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, f"driver failed:\n{run.stdout}\n{run.stderr}"
        assert "FFI BRIDGES OK" in run.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _bundle_text(source: str, tag: str = "ffi_bundle") -> str:
    from pengu_project import PenguBuilder, ProjectConfig

    d = Path(tempfile.mkdtemp(prefix=f"pengu_{tag}_", dir=BUILD_DIR))
    try:
        entry = d / f"{tag}.pengu"
        entry.write_text(source, encoding="utf-8")
        cfg = ProjectConfig(entry=str(entry), base_dir=str(REPO), output="c")
        builder = PenguBuilder(cfg)
        bundle_path, _ = builder.bundle(output_file=str(d / "bundle.c"))
        return Path(bundle_path).read_text(encoding="utf-8")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_std_ffi_module_bundle_emits_expected_c_calls():
    """The wrappers in std/ffi.pengu compile down to the expected C calls."""
    source = (
        "import std.ffi\n"
        "\n"
        "weave main into int:\n"
        '    var c as ref to char is calling ffi.cstr_from_string with "x"\n'
        "    return 0\n"
    )
    c = _bundle_text(source)
    expected_calls = [
        "pengu_ffi_cstr_string",   # string_from_cstr wrapper body
        "pengu_ffi_string_cstr",   # cstr_from_string wrapper body
        "pengu_ffi_string_bytes",  # bytes_from_string wrapper body
        "pengu_ffi_slice_u8",      # slice_of_bytes_from_ptr body
        "pengu_ffi_slice_i32",     # slice_of_int_from_ptr body
        "pengu_ffi_slice_f64",     # slice_of_float_from_ptr body
        "pengu_ffi_list_u8",       # list_of_bytes_from_ptr body
        "pengu_ffi_list_i32",      # list_of_int_from_ptr body
        "pengu_ffi_list_f64",      # list_of_float_from_ptr body
        "pengu_ffi_map_si",        # map_of_string_to_int_from_slices body
    ]
    missing = [name for name in expected_calls if name not in c]
    assert not missing, f"bundle.c missing expected bridge calls: {missing}"
