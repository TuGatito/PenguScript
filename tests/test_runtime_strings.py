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
    /* 1. replace with to.len < from.len */
    {
        PenguString s = pengu_string_from_cstr("hello world");
        PenguString from = pengu_string_from_cstr("world");
        PenguString to = pengu_string_from_cstr("!");
        PenguString res = pengu_string_replace(s, from, to);
        CHECK(res.len == 7 && strcmp(res.data, "hello !") == 0, "replace('hello world', 'world', '!')");
        pengu_banish_string(&res);

        PenguString s2 = pengu_string_from_cstr("aaa");
        PenguString from2 = pengu_string_from_cstr("a");
        PenguString to2 = pengu_string_from_cstr("");
        PenguString res2 = pengu_string_replace(s2, from2, to2);
        CHECK(res2.len == 0 && strcmp(res2.data, "") == 0, "replace('aaa', 'a', '')");
        pengu_banish_string(&res2);

        PenguString s3 = pengu_string_from_cstr("abcabc");
        PenguString from3 = pengu_string_from_cstr("abc");
        PenguString to3 = pengu_string_from_cstr("x");
        PenguString res3 = pengu_string_replace(s3, from3, to3);
        CHECK(res3.len == 2 && strcmp(res3.data, "xx") == 0, "replace('abcabc', 'abc', 'x')");
        pengu_banish_string(&res3);
    }

    /* 2. replace with to.len >= from.len */
    {
        PenguString s = pengu_string_from_cstr("abc");
        PenguString from = pengu_string_from_cstr("abc");
        PenguString to = pengu_string_from_cstr("xyz");
        PenguString res = pengu_string_replace(s, from, to);
        CHECK(res.len == 3 && strcmp(res.data, "xyz") == 0, "replace('abc', 'abc', 'xyz')");
        pengu_banish_string(&res);

        PenguString s2 = pengu_string_from_cstr("a b");
        PenguString from2 = pengu_string_from_cstr(" ");
        PenguString to2 = pengu_string_from_cstr("---");
        PenguString res2 = pengu_string_replace(s2, from2, to2);
        CHECK(res2.len == 5 && strcmp(res2.data, "a---b") == 0, "replace('a b', ' ', '---')");
        pengu_banish_string(&res2);
    }

    /* 3. repeat with normal and overflow */
    {
        PenguString s = pengu_string_from_cstr("ab");
        PenguString res = pengu_string_repeat(s, 3);
        CHECK(res.len == 6 && strcmp(res.data, "ababab") == 0, "repeat('ab', 3)");
        pengu_banish_string(&res);

        /* repeat with SIZE_MAX / 2 should not overflow or crash */
        PenguString res_ovf = pengu_string_repeat(s, (int)(SIZE_MAX / 2));
        CHECK(res_ovf.len == 0 && res_ovf.data != NULL && res_ovf.data[0] == '\0', "repeat overflow");
        pengu_banish_string(&res_ovf);

        PenguString res_neg = pengu_string_repeat(s, -1);
        CHECK(res_neg.len == 0 && res_neg.data != NULL, "repeat negative");
        pengu_banish_string(&res_neg);
    }

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

    /* 5. parse_int / parse_float with range & simulated malloc failure */
    {
        /* In-range */
        PenguString ok_int = pengu_string_from_cstr("12345");
        PenguMaybe m_ok = pengu_parse_int(ok_int);
        CHECK(m_ok.is_present && m_ok.value != NULL && *(int32_t *)m_ok.value == 12345, "parse_int 12345");
        free(m_ok.value);

        /* Out-of-range (> INT32_MAX) */
        PenguString ovf_int = pengu_string_from_cstr("9999999999999999");
        PenguMaybe m_ovf = pengu_parse_int(ovf_int);
        CHECK(!m_ovf.is_present, "parse_int overflow returns none");

        /* Out-of-range (< INT32_MIN) */
        PenguString unf_int = pengu_string_from_cstr("-9999999999999999");
        PenguMaybe m_unf = pengu_parse_int(unf_int);
        CHECK(!m_unf.is_present, "parse_int underflow returns none");

        /* Simulated malloc failure for parse_int */
        g_fail_malloc = 1;
        PenguMaybe m_int_fail = pengu_parse_int(ok_int);
        CHECK(!m_int_fail.is_present, "parse_int malloc fail returns none");
        g_fail_malloc = 0;

        /* In-range float */
        PenguString ok_flt = pengu_string_from_cstr("3.1415");
        PenguMaybe m_flt = pengu_parse_float(ok_flt);
        CHECK(m_flt.is_present && m_flt.value != NULL, "parse_float ok");
        free(m_flt.value);

        /* Simulated malloc failure for parse_float */
        g_fail_malloc = 1;
        PenguMaybe m_flt_fail = pengu_parse_float(ok_flt);
        CHECK(!m_flt_fail.is_present, "parse_float malloc fail returns none");
        g_fail_malloc = 0;
    }

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

            PenguString src = pengu_string_from_cstr("abc");
            PenguString from = pengu_string_from_cstr("abc");
            PenguString to = pengu_string_from_cstr("");
            PenguString rep = pengu_string_replace(src, from, to);
            CHECK(rep.len == 0 && rep.data != NULL && rep.data[0] == '\0', "replace('abc','abc','') len 0");
            pengu_banish_string(&rep);
        }
    }

    /* 8. index_of with embedded NULs and edge cases */
    {
        char raw_a[4] = {'a', '\0', 'b', '\0'};
        PenguString a = {raw_a, 3};
        PenguString sub_b = pengu_string_from_cstr("b");
        int idx = pengu_string_index_of(a, sub_b);
        CHECK(idx == 2, "index_of({'a\\0b', 3}, 'b') == 2");

        PenguString s = pengu_string_from_cstr("abcabc");
        PenguString sub_bc = pengu_string_from_cstr("bc");
        CHECK(pengu_string_index_of(s, sub_bc) == 1, "index_of('abcabc', 'bc') == 1");

        PenguString hello = pengu_string_from_cstr("hello");
        PenguString empty = pengu_string_from_cstr("");
        PenguString z = pengu_string_from_cstr("z");
        CHECK(pengu_string_index_of(hello, empty) == 0, "index_of('hello', '') == 0");
        CHECK(pengu_string_index_of(hello, z) == -1, "index_of('hello', 'z') == -1");
    }

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
                CHECK(p0->len == 1 && strcmp(p0->data, "a") == 0, "part 0 is 'a'");
                CHECK(p1->len == 0 && p1->data[0] == '\0', "part 1 is empty");
                CHECK(p2->len == 1 && strcmp(p2->data, "b") == 2 || strcmp(p2->data, "b") == 0, "part 2 is 'b'");
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

    /* 11. replace preserves embedded NULs on no-match and no-op (B21) */
    {
        char raw_nul[4] = {'a', '\0', 'b', '\0'};
        PenguString s_bin = {raw_nul, 3};
        PenguString empty_from = pengu_string_from_cstr("");
        PenguString rep_to = pengu_string_from_cstr("x");
        PenguString res_noop = pengu_string_replace(s_bin, empty_from, rep_to);
        CHECK(res_noop.len == 3 && memcmp(res_noop.data, "a\0b", 3) == 0, "replace with empty from preserves NULs");
        pengu_banish_string(&res_noop);

        PenguString nomatch_from = pengu_string_from_cstr("z");
        PenguString res_nomatch = pengu_string_replace(s_bin, nomatch_from, rep_to);
        CHECK(res_nomatch.len == 3 && memcmp(res_nomatch.data, "a\0b", 3) == 0, "replace with no-match preserves NULs");
        pengu_banish_string(&res_nomatch);
    }

    /* 12. parse_float checks errno for ERANGE (B22) */
    {
        PenguString ovf = pengu_string_from_cstr("1e999");
        PenguMaybe m_ovf = pengu_parse_float(ovf);
        CHECK(!m_ovf.is_present, "parse_float('1e999') returns none due to ERANGE");
    }

    /* 13. parse_int / parse_float reject pure whitespace and accept valid surrounding whitespace (B23) */
    {
        PenguString ws1 = pengu_string_from_cstr("   ");
        PenguString ws2 = pengu_string_from_cstr("\t\n");
        CHECK(!pengu_parse_int(ws1).is_present, "parse_int('   ') is none");
        CHECK(!pengu_parse_int(ws2).is_present, "parse_int('\\t\\n') is none");
        CHECK(!pengu_parse_float(ws1).is_present, "parse_float('   ') is none");

        PenguString ok42 = pengu_string_from_cstr("42");
        PenguMaybe m42 = pengu_parse_int(ok42);
        CHECK(m42.is_present && m42.value && *(int32_t *)m42.value == 42, "parse_int('42') == 42");
        free(m42.value);

        PenguString ok_padded = pengu_string_from_cstr("  42  ");
        PenguMaybe m_padded = pengu_parse_int(ok_padded);
        CHECK(m_padded.is_present && m_padded.value && *(int32_t *)m_padded.value == 42, "parse_int('  42  ') == 42");
        free(m_padded.value);

        PenguString ok_flt_padded = pengu_string_from_cstr("  3.14  ");
        PenguMaybe m_flt = pengu_parse_float(ok_flt_padded);
        CHECK(m_flt.is_present && m_flt.value && *(double *)m_flt.value > 3.13 && *(double *)m_flt.value < 3.15, "parse_float('  3.14  ') == 3.14");
        free(m_flt.value);
    }

    /* 14. pengu_string_contains with embedded NULs (B24) */
    {
        char raw_bin[4] = {'a', '\0', 'b', '\0'};
        PenguString s_bin = {raw_bin, 3};
        PenguString sub_b = pengu_string_from_cstr("b");
        PenguString sub_z = pengu_string_from_cstr("z");
        PenguString sub_empty = pengu_string_from_cstr("");
        CHECK(pengu_string_contains(s_bin, sub_b), "contains('a\\0b', 'b') is true");
        CHECK(!pengu_string_contains(s_bin, sub_z), "contains('a\\0b', 'z') is false");
        CHECK(pengu_string_contains(s_bin, sub_empty), "contains('a\\0b', '') is true");
    }

    /* 15. pengu_string_starts_with with embedded NULs (B25) */
    {
        char raw_x[4] = {'a', '\0', 'X', '\0'};
        char raw_y[4] = {'a', '\0', 'Y', '\0'};
        PenguString s_x = {raw_x, 3};
        PenguString s_y = {raw_y, 3};
        CHECK(!pengu_string_starts_with(s_x, s_y), "starts_with('a\\0X', 'a\\0Y') is false");
        CHECK(pengu_string_starts_with(s_x, s_x), "starts_with('a\\0X', 'a\\0X') is true");

        PenguString s_abc = pengu_string_from_cstr("abc");
        PenguString s_ab = pengu_string_from_cstr("ab");
        CHECK(pengu_string_starts_with(s_abc, s_ab), "starts_with('abc', 'ab') is true");
    }

    /* 16. pengu_string_concat overflow guard (A14) */
    {
        char dummy[1] = {'x'};
        PenguString a = {dummy, INT_MAX / 2 + 10};
        PenguString b = {dummy, INT_MAX / 2 + 10};
        PenguString res = pengu_string_concat(a, b);
        CHECK(res.len == 0, "concat overflow returns empty string");
        pengu_banish_string(&res);
    }

    /* 17. pengu_string_repeat overflow guard (A15) */
    {
        char dummy[4] = "abc";
        PenguString s = {dummy, 3};
        PenguString res = pengu_string_repeat(s, (int)((size_t)INT_MAX / 2 + 10));
        CHECK(res.len == 0, "repeat overflow returns empty string");
        pengu_banish_string(&res);
    }

    /* 18. pengu_string_replace overflow guard (A16) */
    {
        char src[3] = "aa";
        PenguString s = {src, 2};
        PenguString from = pengu_string_from_cstr("a");
        PenguString to = {(char *)"x", INT_MAX};
        PenguString res = pengu_string_replace(s, from, to);
        CHECK(res.len == 0, "replace overflow returns empty string");
        pengu_banish_string(&res);
    }

    /* 19. pengu_string_replace with embedded NUL in from/s (B26) */
    {
        char raw_s[8] = {'x', ' ', 'a', '\0', 'b', ' ', 'y', '\0'};
        char raw_from[4] = {'a', '\0', 'b', '\0'};
        PenguString s = {raw_s, 7};
        PenguString from = {raw_from, 3};
        PenguString to = pengu_string_from_cstr("ZZZ");
        PenguString res = pengu_string_replace(s, from, to);
        CHECK(res.len == 7, "replace embedded NUL result len is 7");
        CHECK(res.data != NULL && memcmp(res.data, "x ZZZ y", 7) == 0, "replace embedded NUL replaced full 3 bytes");
        pengu_banish_string(&res);
    }

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

    /* 21. pengu_parse_int / pengu_parse_float reject embedded NUL / trailing bytes (B28) */
    {
        char raw_num[8] = {'4', '2', '\0', 'x', 'y', 'z', '\0'};
        PenguString s_num = {raw_num, 6};
        PenguMaybe mi = pengu_parse_int(s_num);
        CHECK(!mi.is_present, "parse_int rejects embedded NUL and trailing chars");

        char raw_flt[10] = {'4', '2', '.', '5', '\0', 'x', 'y', 'z', '\0'};
        PenguString s_flt = {raw_flt, 8};
        PenguMaybe mf = pengu_parse_float(s_flt);
        CHECK(!mf.is_present, "parse_float rejects embedded NUL and trailing chars");

        /* Valid cases still work */
        PenguString s_ok_int = pengu_string_from_cstr("  42  ");
        PenguMaybe mi_ok = pengu_parse_int(s_ok_int);
        CHECK(mi_ok.is_present && *(int32_t *)mi_ok.value == 42, "parse_int accepts valid whitespace-padded int");
        if (mi_ok.is_present) free(mi_ok.value);

        PenguString s_ok_flt = pengu_string_from_cstr("  3.14  ");
        PenguMaybe mf_ok = pengu_parse_float(s_ok_flt);
        CHECK(mf_ok.is_present && *(double *)mf_ok.value > 3.13 && *(double *)mf_ok.value < 3.15, "parse_float accepts valid float");
        if (mf_ok.is_present) free(mf_ok.value);
    }

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

    /* 15. pengu_string_replace overflow defense with int64 (A21) */
    {
        PenguString s = pengu_string_from_cstr("aa");
        PenguString from = pengu_string_from_cstr("a");
        PenguString to;
        to.data = "x";
        to.len = INT_MAX / 2 + 10;
        PenguString res = pengu_string_replace(s, from, to);
        CHECK(res.len == 0 && strcmp(res.data, "") == 0, "replace with count*delta exceeding INT_MAX returns empty string");
        pengu_banish_string(&res);
    }

    /* 16. pengu_parse_int and pengu_parse_float NUL-awareness and non-NUL views (N1a, N1b) */
    {
        /* Embedded NUL in integer string */
        char raw_int_nul[8] = "42\0xyz";
        PenguString s_int_nul = {raw_int_nul, 6};
        PenguMaybe m_int_nul = pengu_parse_int(s_int_nul);
        CHECK(!m_int_nul.is_present, "parse_int('42\\0xyz') returns none");

        /* Non-NUL-terminated view for integer */
        char raw_int_partial[8] = "42999";
        PenguString s_int_slice = {raw_int_partial, 2}; /* only "42" */
        PenguMaybe m_int = pengu_parse_int(s_int_slice);
        CHECK(m_int.is_present && m_int.value != NULL, "parse_int on partial slice is present");
        if (m_int.is_present && m_int.value) {
            CHECK(*(int32_t *)m_int.value == 42, "parse_int('42999', len=2) == 42");
            free(m_int.value);
        }

        /* Whitespace trimmed integer regression */
        PenguString s_int_ws = pengu_string_from_cstr(" 42 ");
        PenguMaybe m_int_ws = pengu_parse_int(s_int_ws);
        CHECK(m_int_ws.is_present && m_int_ws.value != NULL, "parse_int(' 42 ') is present");
        if (m_int_ws.is_present && m_int_ws.value) {
            CHECK(*(int32_t *)m_int_ws.value == 42, "parse_int(' 42 ') == 42");
            free(m_int_ws.value);
        }

        /* Embedded NUL in float string */
        char raw_flt_nul[9] = "3.14\0xyz";
        PenguString s_flt_nul = {raw_flt_nul, 8};
        PenguMaybe m_flt_nul = pengu_parse_float(s_flt_nul);
        CHECK(!m_flt_nul.is_present, "parse_float('3.14\\0xyz') returns none");

        /* Non-NUL-terminated view for float */
        char raw_flt_partial[8] = "3.1499";
        PenguString s_flt_slice = {raw_flt_partial, 4}; /* only "3.14" */
        PenguMaybe m_flt = pengu_parse_float(s_flt_slice);
        CHECK(m_flt.is_present && m_flt.value != NULL, "parse_float on partial slice is present");
        if (m_flt.is_present && m_flt.value) {
            double v = *(double *)m_flt.value;
            CHECK(v >= 3.139 && v <= 3.141, "parse_float('3.1499', len=4) == 3.14");
            free(m_flt.value);
        }

        /* Whitespace trimmed float regression */
        PenguString s_flt_ws = pengu_string_from_cstr(" 3.14 ");
        PenguMaybe m_flt_ws = pengu_parse_float(s_flt_ws);
        CHECK(m_flt_ws.is_present && m_flt_ws.value != NULL, "parse_float(' 3.14 ') is present");
        if (m_flt_ws.is_present && m_flt_ws.value) {
            double v = *(double *)m_flt_ws.value;
            CHECK(v >= 3.139 && v <= 3.141, "parse_float(' 3.14 ') == 3.14");
            free(m_flt_ws.value);
        }
    }

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
