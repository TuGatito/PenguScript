#!/usr/bin/env python3
"""Tests for C runtime string functions (hardening against overflow, underflow, and leaks)."""

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

static void *test_malloc(size_t sz) {
    if (g_fail_malloc) return NULL;
    return malloc(sz);
}

#define malloc test_malloc
#include "pengu_runtime.h"
#undef malloc

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

int main(void) {
    /* 1-3. pengu_string_replace / pengu_string_repeat moved to std/scrolls.pengu
     * (Chunk 2 of the 2.0 migration): the header no longer defines them, so a
     * driver that only includes pengu_runtime.h cannot call them.  Their range,
     * overflow, embedded-NUL and malloc-failure behaviour is asserted
     * end-to-end by tests/test_scrolls.py. */

    /* 4. concat with normal and simulated malloc failure */
    {
        PenguString a = pengu_string_from_cstr("");
        PenguString b = pengu_string_from_cstr("");
        PenguString c = pengu_string_concat(a, b);
        CHECK(c.len == 0 && c.data != NULL && c.data[0] == '\0', "concat('', '')");
        pengu_banish_string(&c);

        PenguString a2 = pengu_string_from_cstr("abc");
        PenguString b2 = pengu_string_from_cstr("def");
        PenguString c2 = pengu_string_concat(a2, b2);
        CHECK(c2.len == 6 && strcmp(c2.data, "abcdef") == 0, "concat('abc', 'def')");
        pengu_banish_string(&c2);

        /* Simulated failure */
        g_fail_malloc = 1;
        PenguString c_fail = pengu_string_concat(a2, b2);
        CHECK(c_fail.len == 0 && c_fail.data != NULL && c_fail.data[0] == '\0',
              "concat failure returns {len=0, non-NULL data}");
        g_fail_malloc = 0;
    }

    /* 5. parse_int / parse_float moved to std/spark.pengu (Chunk 1 of the 2.0
     * migration): the header no longer defines them, so a driver that only
     * includes pengu_runtime.h cannot call them.  The range, malloc-failure,
     * ERANGE, whitespace and embedded-NUL cases they used to assert are covered
     * end-to-end by tests/test_spark.py (parse_int / parse_int_hex / parse_bin /
     * parse_oct / parse_float). */

    /* 6. copy preserves exact binary length including embedded NUL */
    {
        char raw[4] = {'a', '\0', 'b', '\0'};
        PenguString bin;
        bin.data = raw;
        bin.len = 3;
        PenguString copy = pengu_string_copy(bin);
        CHECK(copy.len == 3, "copy len 3 with embedded NUL");
        CHECK(copy.data != NULL && copy.data[0] == 'a' && copy.data[1] == '\0' && copy.data[2] == 'b',
              "copy binary content preserved");
        pengu_banish_string(&copy);
    }

    /* 7. format / concat / replace with empty results (len == 0, non-owning view, no leaks) */
    {
        for (int i = 0; i < 10000; ++i) {
            PenguString fmt = pengu_string_format("");
            CHECK(fmt.len == 0 && fmt.data != NULL && fmt.data[0] == '\0', "format('') len 0");
            pengu_banish_string(&fmt);

            PenguString a = pengu_string_from_cstr("");
            PenguString b = pengu_string_from_cstr("");
            PenguString cat = pengu_string_concat(a, b);
            CHECK(cat.len == 0 && cat.data != NULL && cat.data[0] == '\0', "concat('', '') len 0");
            pengu_banish_string(&cat);
        }
    }

    /* 8. index_of moved to std/scrolls.pengu (Chunk 2); see tests/test_scrolls.py. */

    /* 9. split with empty segments */
    {
        for (int iter = 0; iter < 10000; ++iter) {
            PenguString s = pengu_string_from_cstr("a,,b");
            PenguString delim = pengu_string_from_cstr(",");
            PenguList parts = pengu_string_split(s, delim);
            CHECK(parts.len == 3, "split('a,,b', ',') len 3");
            if (parts.len == 3) {
                PenguString *p0 = (PenguString *)pengu_list_at(&parts, 0);
                PenguString *p1 = (PenguString *)pengu_list_at(&parts, 1);
                PenguString *p2 = (PenguString *)pengu_list_at(&parts, 2);
                /* Each part is a length-carrying view into s (no clone on store),
                 * so compare with memcmp instead of assuming NUL termination. */
                CHECK(p0->len == 1 && memcmp(p0->data, "a", 1) == 0, "part 0 is 'a'");
                CHECK(p1->len == 0 && p1->data[0] == '\0', "part 1 is empty");
                CHECK(p2->len == 1 && memcmp(p2->data, "b", 1) == 0, "part 2 is 'b'");
            }
            pengu_banish_string_list(&parts);

            PenguString empty_s = pengu_string_from_cstr("");
            PenguList empty_parts = pengu_string_split(empty_s, delim);
            CHECK(empty_parts.len == 1, "split('', ',') len 1");
            if (empty_parts.len == 1) {
                PenguString *ep0 = (PenguString *)pengu_list_at(&empty_parts, 0);
                CHECK(ep0->len == 0 && ep0->data[0] == '\0', "empty split element has len 0");
            }
            pengu_banish_string_list(&empty_parts);
        }
    }

    /* 10. pengu_string_new("") and '\0' char_at / from_char leak safety (A13) */
    {
        for (int iter = 0; iter < 10000; ++iter) {
            PenguString s_empty = pengu_string_new("");
            CHECK(s_empty.len == 0 && s_empty.data != NULL && s_empty.data[0] == '\0', "new('') is len 0");
            pengu_banish_string(&s_empty);

            PenguString s_nullchar = pengu_string_from_char('\0');
            CHECK(s_nullchar.len == 1 && s_nullchar.data != NULL && s_nullchar.data[0] == '\0', "from_char('\\0') is len 1");
            pengu_banish_string(&s_nullchar);

            char raw_midnull[4] = {'a', '\0', 'b', '\0'};
            PenguString s_bin = {raw_midnull, 3};
            PenguString s_at_null = pengu_string_char_at(s_bin, 1);
            CHECK(s_at_null.len == 1 && s_at_null.data != NULL && s_at_null.data[0] == '\0', "char_at null byte is len 1");
            pengu_banish_string(&s_at_null);
        }
    }

    /* 11. pengu_string_replace embedded-NUL preservation (B21) moved to
     * std/scrolls.pengu; see tests/test_scrolls.py. */

    /* 12-13. parse_float ERANGE (B22) and parse_int/parse_float whitespace
     * trimming (B23) moved to std/spark.pengu with the functions themselves; see
     * tests/test_spark.py. */

    /* 14-15. pengu_string_contains (B24) and pengu_string_starts_with (B25)
     * moved to std/scrolls.pengu; see tests/test_scrolls.py. */

    /* 16. pengu_string_concat overflow guard (A14) */
    {
        char dummy[1] = {'x'};
        PenguString a = {dummy, INT_MAX / 2 + 10};
        PenguString b = {dummy, INT_MAX / 2 + 10};
        PenguString res = pengu_string_concat(a, b);
        CHECK(res.len == 0, "concat overflow returns empty string");
        pengu_banish_string(&res);
    }

    /* 17-19. pengu_string_repeat (A15) and pengu_string_replace (A16/B26)
     * overflow and embedded-NUL guards moved to std/scrolls.pengu; see
     * tests/test_scrolls.py. */

    /* 20. pengu_string_split with embedded NUL in delim (B27) */
    {
        char raw_s[9] = {'a', 'b', '\0', 'c', 'd', '\0', 'e', 'f', '\0'};
        char raw_delim[2] = {'\0', '\0'};
        PenguString s = {raw_s, 8};
        PenguString delim = {raw_delim, 1};
        PenguList parts = pengu_string_split(s, delim);
        CHECK(parts.len == 3, "split on NUL delim produces 3 parts");
        if (parts.len == 3) {
            PenguString *p0 = (PenguString *)pengu_list_at(&parts, 0);
            PenguString *p1 = (PenguString *)pengu_list_at(&parts, 1);
            PenguString *p2 = (PenguString *)pengu_list_at(&parts, 2);
            CHECK(p0->len == 2 && memcmp(p0->data, "ab", 2) == 0, "split part 0 is 'ab'");
            CHECK(p1->len == 2 && memcmp(p1->data, "cd", 2) == 0, "split part 1 is 'cd'");
            CHECK(p2->len == 2 && memcmp(p2->data, "ef", 2) == 0, "split part 2 is 'ef'");
        }
        pengu_banish_string_list(&parts);
    }

    /* 21. parse_int / parse_float embedded-NUL and trailing-byte rejection (B28)
     * moved to std/spark.pengu; see tests/test_spark.py. */

    /* 22. char_at and from_char with '\0' byte-level accuracy (S1) */
    {
        char raw[4] = {'a', '\0', 'b', '\0'};
        PenguString s = {raw, 3};

        PenguString c_null = pengu_string_char_at(s, 1);
        CHECK(c_null.len == 1 && c_null.data != NULL && c_null.data[0] == '\0', "char_at null byte returns len 1");

        PenguString fc_null = pengu_string_from_char('\0');
        CHECK(fc_null.len == 1 && fc_null.data != NULL && fc_null.data[0] == '\0', "from_char('\\0') returns len 1");

        /* Compare bytes with split */
        PenguString delim_empty = pengu_string_from_cstr("");
        PenguList parts = pengu_string_split(s, delim_empty);
        if (parts.len == 3) {
            PenguString *sp_null = (PenguString *)pengu_list_at(&parts, 1);
            CHECK(sp_null->len == 1 && sp_null->data[0] == '\0', "split on empty delim produces exact NUL part");
            CHECK(c_null.len == sp_null->len && c_null.data[0] == sp_null->data[0], "char_at matches split element at NUL index");
        }
        pengu_banish_string_list(&parts);

        /* Out of bounds regression */
        PenguString s_abc = pengu_string_from_cstr("abc");
        PenguString c_oob = pengu_string_char_at(s_abc, 3);
        CHECK(c_oob.len == 0, "char_at out of bounds returns empty");

        /* Normal char_at regression */
        PenguString c_a = pengu_string_char_at(s_abc, 0);
        CHECK(c_a.len == 1 && c_a.data[0] == 'a', "char_at(0) returns 'a'");
        pengu_banish_string(&c_a);

        pengu_banish_string(&c_null);
        pengu_banish_string(&fc_null);
    }

    /* 15. pengu_string_replace int64 overflow defense (A21) moved to
     * std/scrolls.pengu; see tests/test_scrolls.py. */

    /* 16. parse_int / parse_float NUL-awareness and non-NUL views (N1a, N1b)
     * moved to std/spark.pengu; see tests/test_spark.py. */

    /* 17. pengu_string_from_bool rodata view (N6) */
    {
        PenguString s_true = pengu_string_from_bool(true);
        CHECK(s_true.len == 4, "from_bool(true).len == 4");
        CHECK(s_true.data != NULL && s_true.data[0] == 't', "from_bool(true)[0] == 't'");
        CHECK(strcmp(s_true.data, "true") == 0, "from_bool(true) == 'true'");

        PenguString s_false = pengu_string_from_bool(false);
        CHECK(s_false.len == 5, "from_bool(false).len == 5");
        CHECK(s_false.data != NULL && s_false.data[0] == 'f', "from_bool(false)[0] == 'f'");
        CHECK(strcmp(s_false.data, "false") == 0, "from_bool(false) == 'false'");

        /* Nota: NO se ejecuta banish_string sobre s_true / s_false por ser vistas en rodata */
    }

    /* 40. pengu_string_format_ex: byte-exact '%.*s' and overflow-safe scalars */
    {
        /* Borrowed 3-byte view whose middle byte is NUL. */
        PenguString raw;
        raw.data = (char *)"a\0b";
        raw.len = 3;
        PenguString out = pengu_string_format_ex("<%.*s>", (int)raw.len, raw.data);
        CHECK(out.len == 5, "format_ex keeps embedded NUL (len)");
        CHECK(out.data[1] == 'a' && out.data[2] == '\0' && out.data[3] == 'b',
              "format_ex keeps embedded NUL (bytes)");
        pengu_banish_string(&out);

        /* Phase 3 item 3.9: the float branch renders with `%g`, so a huge float
         * is compact ("1e+300") instead of the ~310 characters `%f` produced.
         * Passing the extreme value still exercises the formatter's scratch
         * buffer, which must not be overrun. */
        PenguString big = pengu_string_format_ex("%f", 1.0e300);
        CHECK(big.len == 6 && strncmp(big.data, "1e+300", 6) == 0,
              "format_ex big float uses %g");
        pengu_banish_string(&big);

        PenguString scalars = pengu_string_format_ex("%d|%c|%s|%%", -7, 'Z', "ok");
        CHECK(scalars.len == 9 && strncmp(scalars.data, "-7|Z|ok|%", 9) == 0,
              "format_ex scalar specifiers");
        pengu_banish_string(&scalars);
    }

    /* 41. pengu_to_string also accepts raw C string pointers */
    {
        PenguString from_ptr = pengu_to_string((const char *)"hi");
        CHECK(from_ptr.len == 2 && strcmp(from_ptr.data, "hi") == 0,
              "pengu_to_string(const char*)");
        /* non-owning view: do not banish */
    }

    if (failures == 0) {
        printf("RUNTIME STRINGS OK\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
"""


@requires_cc
@requires_runtime
def test_runtime_strings_driver():
    """Verify string hardening fixes in C driver."""
    d = Path(tempfile.mkdtemp(prefix="test_str_", dir=BUILD_DIR))
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
        assert "RUNTIME STRINGS OK" in run.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
