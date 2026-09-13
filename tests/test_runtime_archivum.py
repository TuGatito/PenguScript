#!/usr/bin/env python3
"""Tests for Archivum filesystem runtime routines and leak-free directory traversals."""

import os
import shutil
import subprocess
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
_HAVE_VALGRIND = have_tool("valgrind")

requires_cc = pytest.mark.skipif(not _HAVE_CC, reason="no C compiler available")
requires_runtime = pytest.mark.skipif(
    not _HAVE_RUNTIME, reason="libpengu_runtime.a not built (run build_runtime.py)"
)
requires_valgrind = pytest.mark.skipif(
    not _HAVE_VALGRIND, reason="valgrind not installed"
)

DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "pengu_runtime.h"

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

int main(int argc, char **argv) {
    const char *base = (argc > 1) ? argv[1] : "test_archivum_sandbox";

    /* Create test directory hierarchy:
     * base/
     *   a/
     *     file1.txt
     *     file2.log
     *     sub_a/
     *       nested.txt
     *   b/
     *     data.bin
     *   root.txt
     */
    char p_base[512], p_a[512], p_sub_a[512], p_b[512];
    snprintf(p_base, sizeof(p_base), "%s", base);
    snprintf(p_a, sizeof(p_a), "%s/a", base);
    snprintf(p_sub_a, sizeof(p_sub_a), "%s/a/sub_a", base);
    snprintf(p_b, sizeof(p_b), "%s/b", base);

    pengu_c_archivum_create_dir(pengu_string_from_cstr(p_sub_a), true);
    pengu_c_archivum_create_dir(pengu_string_from_cstr(p_b), true);

    char f1[512], f2[512], f3[512], f4[512], f5[512];
    snprintf(f1, sizeof(f1), "%s/file1.txt", p_a);
    snprintf(f2, sizeof(f2), "%s/file2.log", p_a);
    snprintf(f3, sizeof(f3), "%s/nested.txt", p_sub_a);
    snprintf(f4, sizeof(f4), "%s/data.bin", p_b);
    snprintf(f5, sizeof(f5), "%s/root.txt", p_base);

    pengu_c_archivum_write_file(pengu_string_from_cstr(f1), pengu_string_from_cstr("hello"));
    pengu_c_archivum_write_file(pengu_string_from_cstr(f2), pengu_string_from_cstr("log data"));
    pengu_c_archivum_write_file(pengu_string_from_cstr(f3), pengu_string_from_cstr("nested content"));
    pengu_c_archivum_write_file(pengu_string_from_cstr(f4), pengu_string_from_cstr("binary"));
    pengu_c_archivum_write_file(pengu_string_from_cstr(f5), pengu_string_from_cstr("root content"));

    /* 1. Test read_dir and caller cleanup via pengu_banish_string_list */
    PenguMaybe m_entries = pengu_c_archivum_read_dir(pengu_string_from_cstr(p_a));
    CHECK(m_entries.is_present && m_entries.value != NULL, "read_dir p_a succeeded");
    if (m_entries.is_present && m_entries.value) {
        PenguList *l = (PenguList *)m_entries.value;
        CHECK(l->len >= 3, "p_a has at least 3 entries (file1.txt, file2.log, sub_a)");
        pengu_banish_string_list(l);
        free(l);
    }

    /* 2. Test walk on the directory hierarchy */
    PenguList walk_res = pengu_c_archivum_walk(pengu_string_from_cstr(p_base));
    CHECK(walk_res.len >= 1, "walk returned directory nodes");
    for (int i = 0; i < walk_res.len; ++i) {
        PenguList *node = (PenguList *)pengu_list_at(&walk_res, i);
        if (node) {
            pengu_banish_string_list(node);
        }
    }
    pengu_banish_list(&walk_res);

    /* 3. Test recursive remove_dir */
    bool rm_ok = pengu_c_archivum_remove_dir(pengu_string_from_cstr(p_base), true);
    CHECK(rm_ok, "remove_dir recursive succeeded");
    CHECK(!pengu_c_archivum_is_dir(pengu_string_from_cstr(p_base)), "base dir no longer exists");

    /* 4. Test read_file on empty file (B9 leak prevention) */
    {
        char empty_path[512];
        snprintf(empty_path, sizeof(empty_path), "%s_empty.txt", base);
        FILE *f_emp = fopen(empty_path, "wb");
        if (f_emp) fclose(f_emp);

        for (int iter = 0; iter < 10000; ++iter) {
            PenguMaybe m_emp = pengu_c_archivum_read_file(pengu_string_from_cstr(empty_path));
            CHECK(m_emp.is_present && m_emp.value != NULL, "read_file on empty file succeeded");
            if (m_emp.is_present && m_emp.value) {
                PenguString *s = (PenguString *)m_emp.value;
                CHECK(s->len == 0 && s->data != NULL, "empty file has len 0");
                pengu_banish_string(s);
                free(s);
            }
        }
        remove(empty_path);
    }

    /* 5. Test get_env_keys on POSIX (C8) */
#if !PENGU_WINDOWS
    {
        PenguList env_keys = pengu_c_get_env_keys();
        CHECK(env_keys.len > 0, "get_env_keys returns non-empty list on POSIX");
        bool found_path = false;
        for (int i = 0; i < env_keys.len; ++i) {
            PenguString *k = (PenguString *)pengu_list_at(&env_keys, i);
            if (k && k->data && strcmp(k->data, "PATH") == 0) {
                found_path = true;
                break;
            }
        }
        CHECK(found_path, "PATH found in get_env_keys on POSIX");
        pengu_banish_string_list(&env_keys);
    }
#endif

    if (failures == 0) {
        printf("RUNTIME ARCHIVUM OK\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
"""


def _compile_archivum_driver(work_dir: Path) -> Path:
    cfile = work_dir / "driver.c"
    cfile.write_text(DRIVER, encoding="utf-8")
    cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
    exe = work_dir / ("driver.exe" if os.name == "nt" else "driver")
    cmd = [
        cc,
        str(cfile),
        f"-I{REPO}",
        f"-I{BUILD_DIR}",
        f"-I{BUILD_INCLUDE}",
        f"-L{BUILD_LIB}",
    ]
    cmd += ["-Wno-error=implicit-function-declaration", "-Wno-error=unused-variable"]
    cmd += runtime_link_flags()
    cmd += runtime_tail_flags()
    cmd += ["-o", str(exe)]
    comp = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    assert comp.returncode == 0, f"Compilation failed:\n{comp.stderr}\n{comp.stdout}"
    return exe


@requires_cc
@requires_runtime
def test_runtime_archivum_driver():
    """Verify recursive directory operations, walk, and cleanup."""
    d = Path(tempfile.mkdtemp(prefix="test_arch_", dir=BUILD_DIR))
    try:
        exe = _compile_archivum_driver(d)
        sandbox = d / "sandbox"
        run = subprocess.run([str(exe), str(sandbox)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, f"Driver failed:\n{run.stdout}\n{run.stderr}"
        assert "RUNTIME ARCHIVUM OK" in run.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)


@requires_valgrind
@requires_cc
@requires_runtime
def test_runtime_archivum_valgrind():
    """Verify 0 leaks using Valgrind when available."""
    d = Path(tempfile.mkdtemp(prefix="test_valg_", dir=BUILD_DIR))
    try:
        exe = _compile_archivum_driver(d)
        sandbox = d / "sandbox"
        cmd = [
            "valgrind",
            "--leak-check=full",
            "--error-exitcode=1",
            str(exe),
            str(sandbox),
        ]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        assert run.returncode == 0, f"Valgrind reported leaks:\n{run.stderr}\n{run.stdout}"
    finally:
        shutil.rmtree(d, ignore_errors=True)
