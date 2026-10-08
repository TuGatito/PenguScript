#!/usr/bin/env python3
"""Tests for C runtime time functions (hardening against invalid timestamps and libc NULL returns)."""

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

#include "pengu_runtime.h"

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } } while (0)

#define HUGE_DOUBLE 1e30

int main(void) {
    /* 1. UTC component getters with out-of-range timestamp return 0 / false (C16) */
    {
        CHECK(pengu_c_get_utc_year(HUGE_DOUBLE) == 0, "get_utc_year(HUGE) is 0");
        CHECK(pengu_c_get_utc_month(HUGE_DOUBLE) == 0, "get_utc_month(HUGE) is 0");
        CHECK(pengu_c_get_utc_day(HUGE_DOUBLE) == 0, "get_utc_day(HUGE) is 0");
        CHECK(pengu_c_get_utc_hour(HUGE_DOUBLE) == 0, "get_utc_hour(HUGE) is 0");
        CHECK(pengu_c_get_utc_minute(HUGE_DOUBLE) == 0, "get_utc_minute(HUGE) is 0");
        CHECK(pengu_c_get_utc_second(HUGE_DOUBLE) == 0, "get_utc_second(HUGE) is 0");
        CHECK(pengu_c_get_utc_weekday(HUGE_DOUBLE) == 0, "get_utc_weekday(HUGE) is 0");
        CHECK(pengu_c_get_utc_yearday(HUGE_DOUBLE) == 0, "get_utc_yearday(HUGE) is 0");
        CHECK(!pengu_c_get_utc_is_dst(HUGE_DOUBLE), "get_utc_is_dst(HUGE) is false");
    }

    /* 2. Local component getters with out-of-range timestamp return 0 / false (C16) */
    {
        CHECK(pengu_c_get_local_year(HUGE_DOUBLE) == 0, "get_local_year(HUGE) is 0");
        CHECK(pengu_c_get_local_month(HUGE_DOUBLE) == 0, "get_local_month(HUGE) is 0");
        CHECK(pengu_c_get_local_day(HUGE_DOUBLE) == 0, "get_local_day(HUGE) is 0");
        CHECK(pengu_c_get_local_hour(HUGE_DOUBLE) == 0, "get_local_hour(HUGE) is 0");
        CHECK(pengu_c_get_local_minute(HUGE_DOUBLE) == 0, "get_local_minute(HUGE) is 0");
        CHECK(pengu_c_get_local_second(HUGE_DOUBLE) == 0, "get_local_second(HUGE) is 0");
        CHECK(pengu_c_get_local_weekday(HUGE_DOUBLE) == 0, "get_local_weekday(HUGE) is 0");
        CHECK(pengu_c_get_local_yearday(HUGE_DOUBLE) == 0, "get_local_yearday(HUGE) is 0");
        CHECK(!pengu_c_get_local_is_dst(HUGE_DOUBLE), "get_local_is_dst(HUGE) is false");
    }

    /* 3. strftime with out-of-range timestamp returns empty string (C16) */
    {
        PenguString fmt = pengu_string_from_cstr("%Y");
        PenguString res = pengu_c_strftime(fmt, HUGE_DOUBLE);
        CHECK(res.len == 0, "strftime(fmt, HUGE) returns empty string");
        pengu_banish_string(&res);
    }

    /* 4. Normal timestamp regressions */
    {
        CHECK(pengu_c_get_utc_year(0.0) == 1970, "get_utc_year(0) is 1970");
        CHECK(pengu_c_get_utc_month(0.0) == 1, "get_utc_month(0) is 1");
        CHECK(pengu_c_get_utc_day(0.0) == 1, "get_utc_day(0) is 1");
        CHECK(pengu_c_get_utc_hour(0.0) == 0, "get_utc_hour(0) is 0");
        CHECK(pengu_c_get_utc_minute(0.0) == 0, "get_utc_minute(0) is 0");
        CHECK(pengu_c_get_utc_second(0.0) == 0, "get_utc_second(0) is 0");

        PenguString fmt = pengu_string_from_cstr("%Y");
        PenguString res = pengu_c_strftime(fmt, 0.0);
        CHECK(res.len == 4 && strcmp(res.data, "1970") == 0, "strftime('%Y', 0) is '1970'");
        pengu_banish_string(&res);
    }

    /* 5. strptime NUL-awareness and non-NUL view support (N1c) */
    {
        /* Non-NUL-terminated view */
        char raw_dt[30] = "2026-09-12T12:00:00GARBAGE";
        PenguString s_slice = {raw_dt, 19}; /* "2026-09-12T12:00:00" */
        PenguString dummy_fmt = pengu_string_from_cstr("");
        PenguMaybe m_res = pengu_c_strptime(s_slice, dummy_fmt);
        CHECK(m_res.is_present && m_res.value != NULL, "strptime on non-NUL slice is present");
        if (m_res.is_present && m_res.value) {
            double ts = *(double *)m_res.value;
            CHECK(ts > 0.0, "strptime on slice returns valid timestamp");
            free(m_res.value);
        }

        /* Standard date string regression */
        PenguString s_date = pengu_string_from_cstr("2026-09-12");
        PenguMaybe m_date = pengu_c_strptime(s_date, dummy_fmt);
        CHECK(m_date.is_present && m_date.value != NULL, "strptime on date is present");
        if (m_date.is_present && m_date.value) {
            double ts = *(double *)m_date.value;
            CHECK(ts > 0.0, "strptime on date returns valid timestamp");
            free(m_date.value);
        }
    }

    if (failures == 0) {
        printf("RUNTIME TIME OK\n");
        return 0;
    }
    printf("FAILURES: %d\n", failures);
    return 1;
}
"""


@requires_cc
@requires_runtime
def test_runtime_time_driver():
    """Verify time libc return check hardening in C driver."""
    d = Path(tempfile.mkdtemp(prefix="test_time_", dir=BUILD_DIR))
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
        assert "RUNTIME TIME OK" in run.stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
