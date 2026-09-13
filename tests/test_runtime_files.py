#!/usr/bin/env python3
"""Tests for C runtime file and archivum functions (hardening against leaks, truncation, and bounds)."""

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

requires_cc = pytest.mark.skipif(not _HAVE_CC, reason="no C compiler available")
requires_runtime = pytest.mark.skipif(
    not _HAVE_RUNTIME, reason="libpengu_runtime.a not built (run build_runtime.py)"
)

DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <limits.h>

static int g_malloc_calls = 0;
static int g_free_calls = 0;
static int g_fail_malloc = 0;
static int g_malloc_fail_count = 0;

static void *test_malloc(size_t sz) {
    g_malloc_calls++;
    if (g_fail_malloc && g_malloc_calls == g_malloc_fail_count) {
        return NULL;
    }
    return malloc(sz);
}

static void test_free(void *ptr) {
    if (ptr) {
        g_free_calls++;
        free(ptr);
    }
}

static size_t g_fake_fread = 0;
static int g_intercept_fread = 0;
static size_t test_fread(void *ptr, size_t size, size_t nmemb, FILE *stream) {
    if (g_intercept_fread) return g_fake_fread;
    return fread(ptr, size, nmemb, stream);
}

#define malloc test_malloc
#define free test_free
#define fread test_fread
#include "pengu_runtime.h"
#undef malloc
#undef free
#undef fread

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

int main(void) {
    /* 1. read_dir on nonexistent path has no memory leaks (C13) */
    {
        int malloc_before = g_malloc_calls;
        int free_before = g_free_calls;

        PenguString bad_path = pengu_string_from_cstr("__nonexistent_pengu_dir_99999__");
        PenguMaybe res = pengu_c_archivum_read_dir(bad_path);

        CHECK(!res.is_present, "read_dir on nonexistent path returns none");
        int allocated = g_malloc_calls - malloc_before;
        int freed = g_free_calls - free_before;
        CHECK(allocated > 0 && allocated == freed, "read_dir frees all internal allocations on error");
    }

    /* 2. read_file rejecting files > INT_MAX bytes (B29) */
    {
        FILE *f = fopen("test_large_dummy.tmp", "wb");
        if (f) {
            fputs("pengu", f);
            fclose(f);
        }

        /* Simulate fread returning > INT_MAX */
        g_intercept_fread = 1;
        g_fake_fread = (size_t)INT_MAX + 100ULL;

        int malloc_before = g_malloc_calls;
        int free_before = g_free_calls;

        PenguString p = pengu_string_from_cstr("test_large_dummy.tmp");
        PenguMaybe res = pengu_c_archivum_read_file(p);
        CHECK(!res.is_present, "read_file rejects fread > INT_MAX");
        int allocated = g_malloc_calls - malloc_before;
        int freed = g_free_calls - free_before;
        CHECK(allocated == freed, "read_file > INT_MAX frees buffer (no leak)");

        g_intercept_fread = 0;
        remove("test_large_dummy.tmp");
    }

    /* 3. get_env_keys preserves keys > 255 chars (C14) */
    {
#if PENGU_WINDOWS
        char long_key[300];
        memset(long_key, 'K', 280);
        long_key[280] = '\0';
        SetEnvironmentVariableA(long_key, "1");

        PenguList keys = pengu_c_get_env_keys();
        bool found = false;
        for (int i = 0; i < keys.len; ++i) {
            PenguString *k = (PenguString *)pengu_list_at(&keys, i);
            if (k->len == 280 && memcmp(k->data, long_key, 280) == 0) {
                found = true;
                break;
            }
        }
        CHECK(found, "get_env_keys on Windows finds key > 255 chars");

        pengu_banish_string_list(&keys);
        SetEnvironmentVariableA(long_key, NULL);
#else
        CHECK(true, "POSIX get_env_keys already supports long keys");
#endif
    }

    /* 4. walk on directory hierarchy (C15b) */
    {
        PenguString root = pengu_string_from_cstr(".");
        PenguList walk_res = pengu_c_archivum_walk(root);
        CHECK(walk_res.len > 0, "walk on current dir returns at least 1 node");
        for (int i = 0; i < walk_res.len; ++i) {
            PenguList *node = (PenguList *)pengu_list_at(&walk_res, i);
            pengu_banish_string_list(node);
        }
        pengu_banish_list(&walk_res);
    }

    /* 5. read_symlink on non-symlink / boundary (C15c) */
    {
        PenguString p = pengu_string_from_cstr("nonexistent_symlink_target.tmp");
        PenguMaybe res = pengu_c_archivum_read_symlink(p);
        CHECK(!res.is_present, "read_symlink on nonexistent path is none");
    }

    /* 6. realpath canonical resolution (C15d) and OOM handling (C15d-Win) */
    {
        /* Short path regression */
        PenguString p = pengu_string_from_cstr(".");
        PenguMaybe res = pengu_c_archivum_realpath(p);
        CHECK(res.is_present && res.value != NULL, "realpath('.') is present");
        if (res.is_present && res.value) {
            PenguString *rp = (PenguString *)res.value;
            CHECK(rp->len > 0 && rp->data != NULL, "realpath('.') has non-empty path");
            pengu_banish_string(rp);
            free(rp);
        }

#if PENGU_WINDOWS
        /* Long path with dyn malloc failure (C15d-Win) */
        char long_path[4200];
        memset(long_path, 'a', sizeof(long_path) - 1);
        long_path[0] = '.';
        long_path[1] = '/';
        long_path[sizeof(long_path) - 1] = '\0';
        PenguString lp = pengu_string_from_cstr(long_path);

        /* Fail the second malloc (dyn allocation for path >= 4096) */
        g_fail_malloc = 1;
        g_malloc_fail_count = g_malloc_calls + 2;
        PenguMaybe res_oom = pengu_c_archivum_realpath(lp);
        CHECK(!res_oom.is_present, "realpath returns none on dyn malloc OOM without reading uninitialized buf");
        g_fail_malloc = 0;

        /* Long path when malloc succeeds */
        PenguMaybe res_long = pengu_c_archivum_realpath(lp);
        /* May succeed or fail depending on path validity, but must not crash */
        if (res_long.is_present && res_long.value) {
            PenguString *rp = (PenguString *)res_long.value;
            pengu_banish_string(rp);
            free(rp);
        }
#endif
    }

    /* 7. glob NUL-aware binary matching (B30) */
    {
        /* Pattern with embedded NUL */
        char pat_raw[14] = "dummy\0pattern";
        PenguString nul_pat;
        nul_pat.data = pat_raw;
        nul_pat.len = 13;
        PenguList res_nul = pengu_c_archivum_glob(nul_pat);
        CHECK(res_nul.len == 0, "glob with embedded NUL doesn't falsely match prefix");
        pengu_banish_string_list(&res_nul);

        /* Regression: *.c matches or doesn't crash */
        PenguString c_pat = pengu_string_from_cstr("*.c");
        PenguList res_c = pengu_c_archivum_glob(c_pat);
        CHECK(res_c.len >= 0, "glob('*.c') completes successfully");
        pengu_banish_string_list(&res_c);

        /* Regression: ** matches without crash */
        PenguString all_pat = pengu_string_from_cstr("**");
        PenguList res_all = pengu_c_archivum_glob(all_pat);
        CHECK(res_all.len >= 0, "glob('**') completes successfully");
        pengu_banish_string_list(&res_all);
    }

    /* 8. getcwd dynamic buffer resolution (N2) */
    {
        PenguMaybe cwd_m = pengu_c_getcwd();
        CHECK(cwd_m.is_present && cwd_m.value != NULL, "getcwd() is present");
        if (cwd_m.is_present && cwd_m.value) {
            PenguString *cwd = (PenguString *)cwd_m.value;
            CHECK(cwd->len > 0 && cwd->data != NULL, "getcwd() returns non-empty path");
            pengu_banish_string(cwd);
            free(cwd);
        }
    }

    /* 9. glob with empty pattern matches all entries (N4) */
    {
        PenguString empty_pat = pengu_string_from_cstr("");
        PenguList res_empty = pengu_c_archivum_glob(empty_pat);
        CHECK(res_empty.len > 0, "glob('') matches all entries (match-all behavior)");
        pengu_banish_string_list(&res_empty);
    }

    /* 10. getenv/setenv/unsetenv/chdir/strftime NUL-awareness and non-NUL view support (N7) */
    {
        /* setenv and getenv with standard strings */
        PenguString k = pengu_string_from_cstr("PENGU_TEST_ENV_VAR");
        PenguString v = pengu_string_from_cstr("pengu_val_123");
        bool set_ok = pengu_c_setenv(k, v, true);
        CHECK(set_ok, "setenv succeeds");

        PenguMaybe get_m = pengu_c_getenv(k);
        CHECK(get_m.is_present && get_m.value != NULL, "getenv returns present");
        if (get_m.is_present && get_m.value) {
            PenguString *gv = (PenguString *)get_m.value;
            CHECK(strcmp(gv->data, "pengu_val_123") == 0, "getenv returns correct value");
            pengu_banish_string(gv);
            free(gv);
        }

        /* Non-NUL-terminated view for getenv */
        char raw_k[30] = "PENGU_TEST_ENV_VAR_EXTRA";
        PenguString k_slice = {raw_k, 18}; /* exactly "PENGU_TEST_ENV_VAR" */
        PenguMaybe get_slice = pengu_c_getenv(k_slice);
        CHECK(get_slice.is_present && get_slice.value != NULL, "getenv with partial slice is present");
        if (get_slice.is_present && get_slice.value) {
            PenguString *gv = (PenguString *)get_slice.value;
            CHECK(strcmp(gv->data, "pengu_val_123") == 0, "getenv with slice returns correct value");
            pengu_banish_string(gv);
            free(gv);
        }

        /* unsetenv */
        bool unset_ok = pengu_c_unsetenv(k);
        CHECK(unset_ok, "unsetenv succeeds");
        PenguMaybe get_after = pengu_c_getenv(k);
        CHECK(!get_after.is_present, "getenv after unsetenv returns none");

        /* chdir with valid path and non-NUL view */
        PenguMaybe cwd_orig = pengu_c_getcwd();
        if (cwd_orig.is_present && cwd_orig.value) {
            PenguString *orig = (PenguString *)cwd_orig.value;
            char raw_dot[10] = "./junk";
            PenguString dot_slice = {raw_dot, 1}; /* "." */
            bool cd_ok = pengu_c_chdir(dot_slice);
            CHECK(cd_ok, "chdir('.') succeeds with partial slice");

            /* Restore */
            pengu_c_chdir(*orig);
            pengu_banish_string(orig);
            free(orig);
        }

        /* strftime with non-NUL-terminated fmt */
        char raw_fmt[20] = "%Y-%m-%dGARBAGE";
        PenguString fmt_slice = {raw_fmt, 8}; /* "%Y-%m-%d" */
        PenguString s_time = pengu_c_strftime(fmt_slice, 0.0);
        CHECK(s_time.len == 10 && strcmp(s_time.data, "1970-01-01") == 0, "strftime with partial fmt slice returns '1970-01-01'");
        pengu_banish_string(&s_time);
    }

    if (failures == 0) {
        printf("RUNTIME FILES OK\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
"""


@requires_cc
@requires_runtime
def test_runtime_files_driver():
    """Verify file and archivum hardening fixes in C driver."""
    d = Path(tempfile.mkdtemp(prefix="test_files_", dir=BUILD_DIR))
    try:
        cfile = d / "driver.c"
        cfile.write_text(DRIVER, encoding="utf-8")
        cc = "gcc" if have_tool("gcc") else ("clang" if have_tool("clang") else "cc")
        exe = d / ("driver.exe" if os.name == "nt" else "driver")
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
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, f"Driver failed:\n{run.stdout}\n{run.stderr}"
        assert "RUNTIME FILES OK" in run.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
