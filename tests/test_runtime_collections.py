#!/usr/bin/env python3
"""Tests for C runtime collections (List and Map hardening, tombstones, and leak prevention)."""

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

static int g_fail_malloc = 0;
static int g_fail_realloc = 0;
static int g_fail_calloc = 0;
static int g_malloc_fail_after = -1;
static int g_malloc_count = 0;

static void *test_malloc(size_t sz) {
    if (g_fail_malloc) return NULL;
    if (g_malloc_fail_after >= 0) {
        if (g_malloc_count++ >= g_malloc_fail_after) return NULL;
    }
    return malloc(sz);
}

static void *test_realloc(void *ptr, size_t sz) {
    if (g_fail_realloc) return NULL;
    return realloc(ptr, sz);
}

static void *test_calloc(size_t n, size_t sz) {
    if (g_fail_calloc) return NULL;
    return calloc(n, sz);
}

#define malloc test_malloc
#define realloc test_realloc
#define calloc test_calloc
#include "pengu_runtime.h"
#undef malloc
#undef realloc
#undef calloc

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

int main(void) {
    /* 1. pengu_list_new when malloc fails */
    {
        g_fail_malloc = 1;
        PenguList l = pengu_list_new(sizeof(int), 16);
        CHECK(l.data == NULL && l.cap == 0 && l.len == 0, "list_new malloc failure sets {NULL, 0, 0}");
        g_fail_malloc = 0;
        pengu_banish_list(&l);
    }

    /* 2. pengu_list_push rollback when realloc fails */
    {
        PenguList l = pengu_list_new(sizeof(int), 2);
        int v1 = 10, v2 = 20, v3 = 30;
        pengu_list_push(&l, &v1);
        pengu_list_push(&l, &v2);
        CHECK(l.len == 2 && l.cap == 2, "list full at cap=2");

        /* Simulate realloc failure */
        g_fail_realloc = 1;
        void *orig_data = l.data;
        pengu_list_push(&l, &v3);
        CHECK(l.cap == 2 && l.data == orig_data && l.len == 2,
              "list_push realloc failure preserves cap and data");
        g_fail_realloc = 0;

        /* Now push with working realloc succeeds */
        pengu_list_push(&l, &v3);
        CHECK(l.len == 3 && l.cap >= 4, "subsequent push after failed realloc succeeds");
        CHECK(*(int *)pengu_list_at(&l, 0) == 10, "elem 0 intact");
        CHECK(*(int *)pengu_list_at(&l, 1) == 20, "elem 1 intact");
        CHECK(*(int *)pengu_list_at(&l, 2) == 30, "elem 2 intact");
        pengu_banish_list(&l);
    }

    /* 3. pengu_map_keys_string safety */
    {
        /* Called on int map */
        PenguMap int_map = pengu_map_new(sizeof(int), sizeof(int));
        int k = 1, v = 100;
        pengu_map_put(&int_map, &k, &v);
        PenguList keys = pengu_map_keys_string(&int_map);
        CHECK(keys.len == 0, "map_keys_string on int-map returns empty list");
        pengu_banish_list(&keys);
        pengu_banish_map(&int_map);

        /* Called on NULL */
        PenguList null_keys = pengu_map_keys_string(NULL);
        CHECK(null_keys.len == 0, "map_keys_string on NULL returns empty list");
        pengu_banish_list(&null_keys);
    }

    /* 4. pengu_map with embedded NUL in keys */
    {
        PenguMap map = pengu_map_new(sizeof(PenguString), sizeof(int));
        char raw1[4] = {'a', '\0', 'b', '\0'};
        PenguString k1 = {raw1, 3};
        int val1 = 42;
        pengu_map_put(&map, &k1, &val1);

        /* Query exact key */
        int *res1 = (int *)pengu_map_get(&map, &k1);
        CHECK(res1 != NULL && *res1 == 42, "map.get with embedded NUL finds value");

        /* Query truncated key with different len */
        char raw2[2] = {'a', '\0'};
        PenguString k2 = {raw2, 1};
        int *res2 = (int *)pengu_map_get(&map, &k2);
        CHECK(res2 == NULL, "map.get with different len returns NULL");

        pengu_banish_map(&map);
    }

    /* 5. Map collision chain & tombstone probe */
    {
        /* Use fixed capacity to test collision chain */
        PenguMap map = pengu_map_new(sizeof(int), sizeof(int));
        /* Modulo 16 collisions: 1, 17, 33 all hash or probe sequentially */
        int k1 = 1, v1 = 100;
        int k2 = 17, v2 = 200;
        int k3 = 33, v3 = 300;

        pengu_map_put(&map, &k1, &v1);
        pengu_map_put(&map, &k2, &v2);
        pengu_map_put(&map, &k3, &v3);

        CHECK(*(int *)pengu_map_get(&map, &k1) == 100, "find k1");
        CHECK(*(int *)pengu_map_get(&map, &k2) == 200, "find k2");
        CHECK(*(int *)pengu_map_get(&map, &k3) == 300, "find k3");

        /* Remove middle entry */
        bool rem = pengu_map_remove(&map, &k2);
        CHECK(rem, "remove k2 succeeded");
        CHECK(pengu_map_get(&map, &k2) == NULL, "k2 is removed");

        /* k3 must still be found even though k2 was removed (tombstone preserves chain) */
        int *res3 = (int *)pengu_map_get(&map, &k3);
        CHECK(res3 != NULL && *res3 == 300, "k3 still reachable across tombstone");

        /* Re-inserting k4 should reuse tombstone */
        int k4 = 49, v4 = 400;
        pengu_map_put(&map, &k4, &v4);
        CHECK(*(int *)pengu_map_get(&map, &k4) == 400, "find k4 in reused slot");
        CHECK(*(int *)pengu_map_get(&map, &k3) == 300, "k3 still reachable after reuse");

        pengu_banish_map(&map);
    }

    /* 6. Regression test: 1000 inserts, 500 removes, verify remaining 500 */
    {
        PenguMap map = pengu_map_new(sizeof(int), sizeof(int));
        for (int i = 0; i < 1000; ++i) {
            int val = i * 10;
            pengu_map_put(&map, &i, &val);
        }
        CHECK(map.len == 1000, "1000 entries inserted");

        /* Remove all even keys */
        for (int i = 0; i < 1000; i += 2) {
            bool ok = pengu_map_remove(&map, &i);
            if (!ok) {
                printf("FAIL: failed to remove even key %d\n", i);
                failures++;
            }
        }
        CHECK(map.len == 500, "500 entries remaining after remove");

        /* Verify all even keys are gone */
        for (int i = 0; i < 1000; i += 2) {
            if (pengu_map_get(&map, &i) != NULL) {
                printf("FAIL: removed key %d still found\n", i);
                failures++;
            }
        }

        /* Verify all odd keys are present and correct */
        for (int i = 1; i < 1000; i += 2) {
            int *v = (int *)pengu_map_get(&map, &i);
            if (!v || *v != i * 10) {
                printf("FAIL: odd key %d missing or wrong value\n", i);
                failures++;
                break;
            }
        }

        /* Re-insert 500 keys */
        for (int i = 0; i < 1000; i += 2) {
            int val = i * 100;
            pengu_map_put(&map, &i, &val);
        }
        CHECK(map.len == 1000, "1000 entries after re-insert");

        pengu_banish_map(&map);
    }

    /* 7. Map rehash with PenguString keys & values (leak test) */
    {
        PenguMap smap = pengu_map_new(sizeof(PenguString), sizeof(PenguString));
        for (int i = 0; i < 200; ++i) {
            char kbuf[32], vbuf[32];
            snprintf(kbuf, sizeof(kbuf), "key_%d", i);
            snprintf(vbuf, sizeof(vbuf), "value_%d", i);
            PenguString k = pengu_string_new(kbuf);
            PenguString v = pengu_string_new(vbuf);
            pengu_map_put(&smap, &k, &v);
            pengu_banish_string(&k);
            pengu_banish_string(&v);
        }
        CHECK(smap.len == 200, "200 string pairs inserted across rehashes");

        /* Verify all 200 keys */
        int verified = 0;
        for (int i = 0; i < 200; ++i) {
            char kbuf[32], vbuf[32];
            snprintf(kbuf, sizeof(kbuf), "key_%d", i);
            snprintf(vbuf, sizeof(vbuf), "value_%d", i);
            PenguString k = pengu_string_from_cstr(kbuf);
            PenguString *found = (PenguString *)pengu_map_get(&smap, &k);
            if (found && strcmp(found->data, vbuf) == 0) {
                verified++;
            }
        }
        CHECK(verified == 200, "all 200 string pairs verified");

        /* Test map_keys_string */
        PenguList klist = pengu_map_keys_string(&smap);
        CHECK(klist.len == 200, "map_keys_string returned 200 keys");
        pengu_banish_string_list(&klist);

        pengu_banish_map(&smap);
    }

    /* 8. pengu_map_new with calloc failure (A10) */
    {
        g_fail_calloc = 1;
        PenguMap m = pengu_map_new(sizeof(int), sizeof(int));
        CHECK(m.entries == NULL && m.cap == 0 && m.len == 0, "map_new calloc fail sets {NULL, 0, 0}");
        CHECK(pengu_map_get(&m, &failures) == NULL, "map_get on unallocated map returns NULL");
        g_fail_calloc = 0;

        int k = 42, v = 84;
        pengu_map_put(&m, &k, &v);
        CHECK(m.len == 1 && m.cap >= 16, "subsequent put reallocates map successfully");
        int *found = (int *)pengu_map_get(&m, &k);
        CHECK(found != NULL && *found == 84, "value found in recovered map");
        pengu_banish_map(&m);
    }

    /* 9. pengu_map_put with malloc failure per slot (A12) */
    {
        PenguMap m = pengu_map_new(sizeof(int), sizeof(int));
        int k1 = 1, v1 = 10;
        pengu_map_put(&m, &k1, &v1);
        CHECK(m.len == 1, "k1 inserted");

        /* Fail on next malloc (slot allocation) */
        g_malloc_count = 0;
        g_malloc_fail_after = 0;
        int k2 = 2, v2 = 20;
        pengu_map_put(&m, &k2, &v2);
        CHECK(m.len == 1, "k2 rejected without corrupting map or crashing");
        CHECK(pengu_map_get(&m, &k2) == NULL, "k2 not in map");
        g_malloc_fail_after = -1;

        /* Recover and insert */
        pengu_map_put(&m, &k2, &v2);
        CHECK(m.len == 2, "k2 inserted after malloc restored");
        CHECK(*(int *)pengu_map_get(&m, &k1) == 10, "k1 intact");
        CHECK(*(int *)pengu_map_get(&m, &k2) == 20, "k2 intact");
        pengu_banish_map(&m);
    }

    /* 10. pengu_map_clear resets tombstones (C6) */
    {
        PenguMap m = pengu_map_new(sizeof(int), sizeof(int));
        for (int i = 0; i < 50; ++i) {
            int val = i * 2;
            pengu_map_put(&m, &i, &val);
        }
        CHECK(m.len == 50, "50 entries inserted");
        for (int i = 0; i < 25; ++i) {
            pengu_map_remove(&m, &i);
        }
        CHECK(m.len == 25, "25 entries removed (tombstones left)");

        pengu_map_clear(&m);
        CHECK(m.len == 0, "map_clear resets len to 0");

        /* Insert 100 new entries into cleared map */
        for (int i = 1000; i < 1100; ++i) {
            int val = i * 3;
            pengu_map_put(&m, &i, &val);
        }
        CHECK(m.len == 100, "100 entries in cleared map");
        int verified = 0;
        for (int i = 1000; i < 1100; ++i) {
            int *v = (int *)pengu_map_get(&m, &i);
            if (v && *v == i * 3) verified++;
        }
        CHECK(verified == 100, "all 100 entries found in cleared map (tombstones reset)");
        pengu_banish_map(&m);
    }

    /* 11. string_int tombstones and intermixed operations (C5) */
    {
        PenguMap m = pengu_map_new(sizeof(PenguString), sizeof(int32_t));
        PenguString k1 = pengu_string_from_cstr("apple");
        PenguString k2 = pengu_string_from_cstr("banana");
        PenguString k3 = pengu_string_from_cstr("cherry");
        int32_t v1 = 10, v2 = 20, v3 = 30;

        pengu_map_put_string_int(&m, &k1, &v1);
        pengu_map_put_string_int(&m, &k2, &v2);
        pengu_map_put_string_int(&m, &k3, &v3);
        CHECK(m.len == 3, "3 string_int entries inserted");

        /* Remove middle entry via general remove */
        bool rem = pengu_map_remove(&m, &k2);
        CHECK(rem, "k2 removed via general pengu_map_remove");
        CHECK(m.len == 2, "len is 2 after remove");

        /* get_string_int must still find k3 across tombstone */
        int32_t *res3 = pengu_map_get_string_int(&m, &k3);
        CHECK(res3 != NULL && *res3 == 30, "get_string_int finds k3 across tombstone");

        /* Remove k1 via pengu_map_remove_string_int */
        bool rem1 = pengu_map_remove_string_int(&m, &k1);
        CHECK(rem1, "k1 removed via pengu_map_remove_string_int");
        CHECK(pengu_map_get_string_int(&m, &k1) == NULL, "k1 is gone");
        CHECK(pengu_map_get_string_int(&m, &k3) != NULL, "k3 still reachable");

        /* Insert new key k4 via put_string_int */
        PenguString k4 = pengu_string_from_cstr("date");
        int32_t v4 = 40;
        pengu_map_put_string_int(&m, &k4, &v4);
        CHECK(*(pengu_map_get_string_int(&m, &k4)) == 40, "k4 found");
        CHECK(*(pengu_map_get_string_int(&m, &k3)) == 30, "k3 still found");

        pengu_banish_map(&m);
    }

    /* 12. pengu_c_rand_range overflow safety (C9) */
    {
        int r = pengu_c_rand_range(-1000, 1000);
        CHECK(r >= -1000 && r <= 1000, "rand_range in [-1000, 1000]");
        int r_inv = pengu_c_rand_range(50, 10);
        CHECK(r_inv == 50, "rand_range min >= max returns min");
        int r_wide = pengu_c_rand_range(-2000000000, 2000000000);
        CHECK(r_wide >= -2000000000 && r_wide <= 2000000000, "rand_range wide range no overflow");
    }

    /* 13. pengu_c_strptime with malloc failure (C11) */
    {
        PenguString ts = pengu_string_from_cstr("2026-09-12T12:00:00");
        PenguString fmt = pengu_string_from_cstr("");
        PenguMaybe m_ok = pengu_c_strptime(ts, fmt);
        CHECK(m_ok.is_present && m_ok.value != NULL, "strptime parses ISO timestamp");
        if (m_ok.is_present && m_ok.value) free(m_ok.value);

        g_fail_malloc = 1;
        PenguMaybe m_fail = pengu_c_strptime(ts, fmt);
        CHECK(!m_fail.is_present, "strptime returns none when malloc fails");
        g_fail_malloc = 0;
    }

    /* 14. pengu_c_archivum_metadata with calloc failure (C12) */
    {
        FILE *tf = fopen("test_meta_c12.tmp", "wb");
        if (tf) { fputs("hello", tf); fclose(tf); }
        PenguString p = pengu_string_from_cstr("test_meta_c12.tmp");

        PenguMaybe m_meta = pengu_c_archivum_metadata(p);
        CHECK(m_meta.is_present && m_meta.value != NULL, "metadata succeeded");
        if (m_meta.is_present && m_meta.value) {
            PenguMap *map = (PenguMap *)m_meta.value;
            pengu_banish_map(map);
            free(map);
        }

        g_fail_calloc = 1;
        PenguMaybe m_fail = pengu_c_archivum_metadata(p);
        CHECK(!m_fail.is_present, "metadata returns none when calloc fails in map_new");
        g_fail_calloc = 0;

        remove("test_meta_c12.tmp");
    }

    /* 18. pengu_c_rand_range extreme bounds (A17) */
    {
        /* 10,000 calls with (INT_MIN, INT_MAX) */
        bool all_in_bounds = true;
        for (int i = 0; i < 10000; ++i) {
            int r = pengu_c_rand_range(INT_MIN, INT_MAX);
            if (r < INT_MIN || r > INT_MAX) {
                all_in_bounds = false;
                break;
            }
        }
        CHECK(all_in_bounds, "rand_range(INT_MIN, INT_MAX) within bounds across 10k calls");

        /* (INT_MIN, 0) */
        bool min_zero_ok = true;
        for (int i = 0; i < 1000; ++i) {
            int r = pengu_c_rand_range(INT_MIN, 0);
            if (r > 0) {
                min_zero_ok = false;
                break;
            }
        }
        CHECK(min_zero_ok, "rand_range(INT_MIN, 0) <= 0");

        /* (0, INT_MAX) */
        bool zero_max_ok = true;
        for (int i = 0; i < 1000; ++i) {
            int r = pengu_c_rand_range(0, INT_MAX);
            if (r < 0) {
                zero_max_ok = false;
                break;
            }
        }
        CHECK(zero_max_ok, "rand_range(0, INT_MAX) >= 0");

        /* (INT_MAX - 1, INT_MAX) */
        bool max_boundary_ok = true;
        for (int i = 0; i < 1000; ++i) {
            int r = pengu_c_rand_range(INT_MAX - 1, INT_MAX);
            if (r != INT_MAX - 1 && r != INT_MAX) {
                max_boundary_ok = false;
                break;
            }
        }
        CHECK(max_boundary_ok, "rand_range(INT_MAX-1, INT_MAX) in {INT_MAX-1, INT_MAX}");
    }

    /* 19. pengu__find_sub overflow defense (A18) */
    {
        char raw_hay[10] = "0123456789";
        char dummy[1] = {'x'};
        PenguString hay = {raw_hay, 10};
        PenguString needle_huge = {dummy, INT_MAX / 2 + 10};

        int idx = pengu__find_sub(hay, needle_huge, 5);
        CHECK(idx == -1, "find_sub with needle.len > hay.len - from_idx returns -1 without overflow");

        PenguString needle_empty = {raw_hay, 0};
        int idx_empty = pengu__find_sub(hay, needle_empty, 3);
        CHECK(idx_empty == 3, "find_sub with empty needle returns from_idx");
    }

    /* 20. pengu_map_put / put_string_int overflow defense on cap doubling (A19) */
    {
        PenguMap map = pengu_map_new(sizeof(int), sizeof(int));
        map.cap = (INT_MAX / 2) + 2;
        map.len = (INT_MAX / 4) + 2; /* len * 2 >= cap triggers resize branch */

        int k = 42, v = 100;
        pengu_map_put(&map, &k, &v);
        CHECK(map.cap == (INT_MAX / 2) + 2, "map_put rejects doubling when cap > INT_MAX / 2 without crash");

        PenguMap m_si = pengu_map_new(sizeof(PenguString), sizeof(int32_t));
        m_si.cap = (INT_MAX / 2) + 2;
        m_si.len = (INT_MAX / 4) + 2;
        PenguString pk = pengu_string_from_cstr("key");
        int32_t pv = 99;
        pengu_map_put_string_int(&m_si, &pk, &pv);
        CHECK(m_si.cap == (INT_MAX / 2) + 2, "map_put_string_int rejects doubling when cap > INT_MAX / 2 without crash");
    }

    /* 21. pengu_list_push overflow defense on SIZE_MAX / elem_size (A20) */
    {
        PenguList l;
        l.elem_size = (size_t)SIZE_MAX / 4 + 10;
        l.cap = 2;
        l.len = 2; /* forces doubling to new_cap = 4 */
        l.data = (void *)0x1234; /* dummy non-null */
        int dummy = 42;
        pengu_list_push(&l, &dummy);
        CHECK(l.cap == 2 && l.len == 2, "list_push rejects doubling when (size_t)new_cap > SIZE_MAX / elem_size");
    }

    if (failures == 0) {
        printf("RUNTIME COLLECTIONS OK\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
"""


@requires_cc
@requires_runtime
def test_runtime_collections_driver():
    """Verify list and map hardening fixes in C driver."""
    d = Path(tempfile.mkdtemp(prefix="test_col_", dir=BUILD_DIR))
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
        assert "RUNTIME COLLECTIONS OK" in run.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
