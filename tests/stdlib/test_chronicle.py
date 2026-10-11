#!/usr/bin/env python3
"""End-to-end tests for ``std.chronicle`` (Chunk 5 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.chronicle`` is the clock family: wall-clock and monotonic readings, Unix
timestamps, a decomposed ``DateTime`` value rune, UTC calendar boundaries,
formatting/parsing and a ``Stopwatch``.  The suite is deliberately deterministic:
every assertion is anchored on a fixed timestamp (``0.0``, ``86400.0``,
``1700000000.0`` or an early-1970 value); the only tests that touch the live
clocks assert invariants (``time > 0``, ``monotonic >= 0``, a monotonic reading
never decreases), never a concrete reading.

Timestamps are printed by truncating to ``int`` rather than by interpolating the
``float`` (``%g`` renders large values as ``1.7e+09``), so stdout comparisons stay
byte-for-byte stable.  Where a documented boundary lands on a value a 32-bit
``float`` cannot represent, the test pins the documented second within a
one-second tolerance instead of the rounded bit pattern; those spots are called
out in the test docstrings and were reported as a module finding.

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled, so no test can observe another test's state
and a failure names exactly one program.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: Three levels up: tests/stdlib/test_chronicle.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_chronicle_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


#: One-line printers spliced into every program, so an exact stdout comparison
#: pins the value without any Python-side formatting.  ``chr_ts`` truncates a
#: timestamp to ``int`` because ``%g`` would render large floats in exponent form.
_PRELUDE = '''
weave chr_int with v as int into void:
    calling spark.println with calling spark.str_int with v

weave chr_bool with v as bool into void:
    calling spark.println with calling spark.str_bool with v

weave chr_ts with v as float into void:
    calling spark.println with calling spark.str_int with (v to int)

weave chr_str with v as string into void:
    calling spark.println with v
'''


def _run_main(body: str, helpers: str = "") -> subprocess.CompletedProcess:
    """Runs ``body`` as the statements of a ``main`` that imports chronicle."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = ["import std.spark", "import std.chronicle", "import std.oracle", ""]
    sections.append(textwrap.dedent(_PRELUDE).strip("\n"))
    if helpers:
        sections += ["", textwrap.dedent(helpers).strip("\n")]
    sections += ["", "weave main into int:", body, "    return 0", ""]
    return run_pengu("\n".join(sections))


def _check(body: str, expected: str, helpers: str = "") -> None:
    """Runs ``body`` and asserts its exit code and exact stdout."""
    res = _run_main(body, helpers)
    assert res.returncode == 0, res.stderr
    assert res.stdout == expected, res.stderr


# ---------------------------------------------------------------------------
# Version and the two clocks
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``CHRONICLE_VERSION`` reports the module revision ``2.1.0``."""
    res = _run_main("calling spark.println with chronicle.CHRONICLE_VERSION")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.1.0\n"


def test_time_and_monotonic_are_sane():
    """``time`` is a positive epoch reading and ``monotonic`` is non-negative."""
    _check('''
        calling chr_bool with ((calling chronicle.time) > 0.0)
        calling chr_bool with ((calling chronicle.monotonic) >= 0.0)
    ''', "true\ntrue\n")


def test_now_ms_and_time_ms_are_callable_aliases():
    """``now_ms`` and ``time_ms`` compute the same millisecond reading.

    The reading is returned as an ``int`` (32-bit) and overflows for any
    post-1970 wall-clock time, so this test pins the alias relationship and the
    non-negative ``monotonic_ms``; the overflow was reported as a module finding.
    """
    _check('''
        calling chr_bool with ((calling chronicle.monotonic_ms) >= 0)
        let first as int is calling chronicle.now_ms
        let second as int is calling chronicle.time_ms
        let delta as int is if first >= second then (first - second) else (second - first)
        calling chr_bool with (delta <= 1000)
    ''', "true\ntrue\n")


def test_monotonic_never_moves_backwards():
    """Two consecutive ``monotonic`` readings are non-decreasing."""
    _check('''
        let first as float is calling chronicle.monotonic
        let second as float is calling chronicle.monotonic
        calling chr_bool with (second >= first)
    ''', "true\n")


def test_sleep_of_zero_or_less_returns_immediately():
    """``sleep_ms``/``sleep`` with a non-positive delay return normally."""
    _check('''
        calling chronicle.sleep_ms with 0
        calling chronicle.sleep_ms with -5
        calling chronicle.sleep with 0.0
        calling chr_str with "slept"
    ''', "slept\n")


# ---------------------------------------------------------------------------
# datetime_utc fields for fixed timestamps
# ---------------------------------------------------------------------------

def test_datetime_utc_epoch_fields():
    """``datetime_utc(0.0)`` is 1970-01-01 00:00:00 Thursday, day 0, no DST."""
    _check('''
        var dt as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        calling chr_int with dt.year
        calling chr_int with dt.month
        calling chr_int with dt.day
        calling chr_int with dt.hour
        calling chr_int with dt.minute
        calling chr_int with dt.second
        calling chr_int with dt.weekday
        calling chr_int with dt.yearday
        calling chr_bool with dt.is_dst
    ''', "1970\n1\n1\n0\n0\n0\n4\n0\nfalse\n")


def test_datetime_utc_second_day_fields():
    """``datetime_utc(86400.0)`` is 1970-01-02 00:00:00 Friday, day 1."""
    _check('''
        var dt as chronicle.DateTime is calling chronicle.datetime_utc with 86400.0
        calling chr_int with dt.year
        calling chr_int with dt.month
        calling chr_int with dt.day
        calling chr_int with dt.hour
        calling chr_int with dt.weekday
        calling chr_int with dt.yearday
    ''', "1970\n1\n2\n0\n5\n1\n")


def test_datetime_utc_famous_timestamp_fields():
    """``datetime_utc(1700000000.0)`` is 2023-11-14 22:13:20 Tuesday, day 317."""
    _check('''
        var dt as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        calling chr_int with dt.year
        calling chr_int with dt.month
        calling chr_int with dt.day
        calling chr_int with dt.hour
        calling chr_int with dt.minute
        calling chr_int with dt.second
        calling chr_int with dt.weekday
        calling chr_int with dt.yearday
        calling chr_bool with dt.is_dst
    ''', "2023\n11\n14\n22\n13\n20\n2\n317\nfalse\n")


def test_utc_getters_read_fixed_fields():
    """Every ``utc_*`` getter agrees with ``datetime_utc`` on a fixed timestamp."""
    _check('''
        calling chr_int with (calling chronicle.utc_year with 1700000000.0)
        calling chr_int with (calling chronicle.utc_month with 1700000000.0)
        calling chr_int with (calling chronicle.utc_day with 1700000000.0)
        calling chr_int with (calling chronicle.utc_hour with 1700000000.0)
        calling chr_int with (calling chronicle.utc_minute with 1700000000.0)
        calling chr_int with (calling chronicle.utc_second with 1700000000.0)
        calling chr_int with (calling chronicle.utc_weekday with 1700000000.0)
        calling chr_int with (calling chronicle.utc_yearday with 1700000000.0)
        calling chr_bool with (calling chronicle.utc_is_dst with 1700000000.0)
    ''', "2023\n11\n14\n22\n13\n20\n2\n317\nfalse\n")


def test_datetime_local_mirrors_local_getters():
    """``datetime_local`` fills its fields from the ``local_*`` getters."""
    _check('''
        let ts as float is 1700000000.0
        var dt as chronicle.DateTime is calling chronicle.datetime_local with ts
        calling chr_bool with (dt.year == (calling chronicle.local_year with ts))
        calling chr_bool with (dt.month == (calling chronicle.local_month with ts))
        calling chr_bool with (dt.day == (calling chronicle.local_day with ts))
        calling chr_bool with (dt.hour == (calling chronicle.local_hour with ts))
        calling chr_bool with (dt.minute == (calling chronicle.local_minute with ts))
        calling chr_bool with (dt.second == (calling chronicle.local_second with ts))
        calling chr_bool with (dt.weekday == (calling chronicle.local_weekday with ts))
        calling chr_bool with (dt.yearday == (calling chronicle.local_yearday with ts))
        calling chr_bool with (dt.is_dst == (calling chronicle.local_is_dst with ts))
    ''', "true\n" * 9)


# ---------------------------------------------------------------------------
# to_timestamp, to_iso and from_iso
# ---------------------------------------------------------------------------

def test_to_timestamp_inverts_datetime_utc():
    """``to_timestamp`` round-trips the three pinned timestamps exactly."""
    _check('''
        var epoch as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        calling chr_ts with (calling epoch.to_timestamp)
        var day as chronicle.DateTime is calling chronicle.datetime_utc with 86400.0
        calling chr_ts with (calling day.to_timestamp)
        var famous as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        calling chr_ts with (calling famous.to_timestamp)
    ''', "0\n86400\n1700000000\n")


def test_to_iso_formats_fixed_timestamps():
    """``to_iso`` renders the pinned timestamps in ISO 8601 UTC form."""
    _check('''
        calling chr_str with (calling chronicle.to_iso with 0.0)
        calling chr_str with (calling chronicle.to_iso with 86400.0)
        calling chr_str with (calling chronicle.to_iso with 1700000000.0)
    ''', "1970-01-01T00:00:00Z\n1970-01-02T00:00:00Z\n2023-11-14T22:13:20Z\n")


def test_datetime_to_iso_method_matches_the_module():
    """``DateTime.to_iso`` and ``chronicle.to_iso`` render the same record."""
    _check('''
        var famous as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        calling chr_str with (calling famous.to_iso)
        var epoch as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        calling chr_str with (calling epoch.to_iso)
    ''', "2023-11-14T22:13:20Z\n1970-01-01T00:00:00Z\n")


def test_from_iso_accepts_iso_date_only_and_space_forms():
    """``from_iso`` parses Z, space-separated, date-only and padded text."""
    _check('''
        let a as maybe float is calling chronicle.from_iso with "1970-01-01T00:00:00Z"
        calling chr_ts with (a.value)
        let b as maybe float is calling chronicle.from_iso with "2023-11-14T22:13:20Z"
        calling chr_ts with (b.value)
        let c as maybe float is calling chronicle.from_iso with "2023-11-14"
        calling chr_ts with (c.value)
        let d as maybe float is calling chronicle.from_iso with "2023-11-14 22:13:20"
        calling chr_ts with (d.value)
        let e as maybe float is calling chronicle.from_iso with "  1970-01-02T00:00:00Z  "
        calling chr_ts with (e.value)
    ''', "0\n1700000000\n1699920000\n1700000000\n86400\n")


def test_from_iso_round_trips_to_iso():
    """``from_iso(to_iso(ts))`` returns the original second."""
    _check('''
        let a as maybe float is calling chronicle.from_iso with (calling chronicle.to_iso with 0.0)
        calling chr_ts with (a.value)
        let b as maybe float is calling chronicle.from_iso with (calling chronicle.to_iso with 86400.0)
        calling chr_ts with (b.value)
        let c as maybe float is calling chronicle.from_iso with (calling chronicle.to_iso with 1700000000.0)
        calling chr_ts with (c.value)
    ''', "0\n86400\n1700000000\n")


def test_from_iso_rejects_malformed_input():
    """A short string, wrong separator, bad month/day/hour or pre-1970 is none."""
    _check('''
        let a as maybe float is calling chronicle.from_iso with "abc"
        calling chr_bool with a.is_present
        let b as maybe float is calling chronicle.from_iso with "2024/01/01"
        calling chr_bool with b.is_present
        let c as maybe float is calling chronicle.from_iso with "2024-13-01"
        calling chr_bool with c.is_present
        let d as maybe float is calling chronicle.from_iso with "2024-02-30"
        calling chr_bool with d.is_present
        let e as maybe float is calling chronicle.from_iso with "2024-01-01T99:00:00"
        calling chr_bool with e.is_present
        let f as maybe float is calling chronicle.from_iso with "1969-12-31"
        calling chr_bool with f.is_present
    ''', "false\n" * 6)


# ---------------------------------------------------------------------------
# DateTime arithmetic and comparisons
# ---------------------------------------------------------------------------

def test_plus_seconds_and_plus_minutes():
    """``plus_seconds``/``plus_minutes`` use their unit and accept negatives."""
    _check('''
        var base as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var by_sec as chronicle.DateTime is calling base.plus_seconds with 90
        calling chr_ts with (calling by_sec.to_timestamp)
        var by_min as chronicle.DateTime is calling base.plus_minutes with 2
        calling chr_ts with (calling by_min.to_timestamp)
        var back as chronicle.DateTime is calling by_min.plus_minutes with -1
        calling chr_ts with (calling back.to_timestamp)
    ''', "90\n120\n60\n")


def test_plus_hours_uses_3600_second_steps():
    """``plus_hours`` adds whole hours on both sides of a fixed timestamp."""
    _check('''
        var base as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var forward as chronicle.DateTime is calling base.plus_hours with 2
        calling chr_ts with (calling forward.to_timestamp)
        var day as chronicle.DateTime is calling chronicle.datetime_utc with 86400.0
        var backward as chronicle.DateTime is calling day.plus_hours with -1
        calling chr_ts with (calling backward.to_timestamp)
    ''', "7200\n82800\n")


def test_plus_days_and_plus_weeks():
    """``plus_days``/``plus_weeks`` add 86400 and 604800 seconds per unit."""
    _check('''
        var base as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var day as chronicle.DateTime is calling base.plus_days with 1
        calling chr_ts with (calling day.to_timestamp)
        var week as chronicle.DateTime is calling base.plus_weeks with 1
        calling chr_ts with (calling week.to_timestamp)
        var famous as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        var prev_day as chronicle.DateTime is calling famous.plus_days with -1
        calling chr_ts with (calling prev_day.to_timestamp)
        var next_day as chronicle.DateTime is calling famous.plus_days with 1
        calling chr_ts with (calling next_day.to_timestamp)
        var next_week as chronicle.DateTime is calling famous.plus_weeks with 1
        calling chr_ts with (calling next_week.to_timestamp)
    ''', "86400\n604800\n1699913600\n1700086400\n1700604800\n")


def test_plus_days_moves_the_calendar_fields():
    """The record returned by ``plus_days`` is rebuilt from the new timestamp."""
    _check('''
        var base as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var next as chronicle.DateTime is calling base.plus_days with 1
        calling chr_str with (calling next.to_date)
        calling chr_str with (calling next.to_time)
        calling chr_int with next.weekday
    ''', "1970-01-02\n00:00:00\n5\n")


def test_datetime_is_before_and_is_after():
    """The comparison methods are strict and order-sensitive."""
    _check('''
        var early as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var late as chronicle.DateTime is calling chronicle.datetime_utc with 86400.0
        calling chr_bool with (calling early.is_before with late)
        calling chr_bool with (calling early.is_after with late)
        calling chr_bool with (calling late.is_after with early)
        calling chr_bool with (calling late.is_before with early)
        calling chr_bool with (calling early.is_before with early)
    ''', "true\nfalse\ntrue\nfalse\nfalse\n")


def test_datetime_is_same_day_ignores_the_time_of_day():
    """``is_same_day`` compares the UTC day, not the second."""
    _check('''
        var with_time as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        var midnight as chronicle.DateTime is calling chronicle.datetime_utc with 1699920000.0
        var previous as chronicle.DateTime is calling chronicle.datetime_utc with 1699833600.0
        calling chr_bool with (calling with_time.is_same_day with midnight)
        calling chr_bool with (calling midnight.is_same_day with with_time)
        calling chr_bool with (calling with_time.is_same_day with previous)
    ''', "true\ntrue\nfalse\n")


# ---------------------------------------------------------------------------
# Calendar labels
# ---------------------------------------------------------------------------

def test_datetime_weekday_name_method():
    """``DateTime.weekday_name`` labels Thursday, Friday and Tuesday."""
    _check('''
        var thursday as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var friday as chronicle.DateTime is calling chronicle.datetime_utc with 86400.0
        var tuesday as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        calling chr_str with (calling thursday.weekday_name)
        calling chr_str with (calling friday.weekday_name)
        calling chr_str with (calling tuesday.weekday_name)
    ''', "Thursday\nFriday\nTuesday\n")


def test_datetime_month_name_method():
    """``DateTime.month_name`` labels January, November and February."""
    _check('''
        var january as chronicle.DateTime is calling chronicle.datetime_utc with 0.0
        var november as chronicle.DateTime is calling chronicle.datetime_utc with 1700000000.0
        var leap as chronicle.DateTime is calling chronicle.datetime_utc with 1709164800.0
        calling chr_str with (calling january.month_name)
        calling chr_str with (calling november.month_name)
        calling chr_str with (calling leap.month_name)
    ''', "January\nNovember\nFebruary\n")


def test_module_weekday_name_and_month_name():
    """The module functions map a timestamp to the same labels as the methods."""
    _check('''
        calling chr_str with (calling chronicle.weekday_name with 0.0)
        calling chr_str with (calling chronicle.weekday_name with 86400.0)
        calling chr_str with (calling chronicle.weekday_name with 1700000000.0)
        calling chr_str with (calling chronicle.month_name with 0.0)
        calling chr_str with (calling chronicle.month_name with 1700000000.0)
    ''', "Thursday\nFriday\nTuesday\nJanuary\nNovember\n")


def test_datetime_is_weekend():
    """Saturday and Sunday are weekend days; Monday is not."""
    _check('''
        var saturday as chronicle.DateTime is calling chronicle.datetime_utc with 172800.0
        var sunday as chronicle.DateTime is calling chronicle.datetime_utc with 259200.0
        var monday as chronicle.DateTime is calling chronicle.datetime_utc with 345600.0
        calling chr_bool with (calling saturday.is_weekend)
        calling chr_bool with (calling sunday.is_weekend)
        calling chr_bool with (calling monday.is_weekend)
    ''', "true\ntrue\nfalse\n")


# ---------------------------------------------------------------------------
# Leap years and month/year lengths
# ---------------------------------------------------------------------------

def test_module_is_leap_year():
    """The module rule: 2000 and 2024 are leap, 1900 and 2023 are not."""
    _check('''
        calling chr_bool with (calling chronicle.is_leap_year with 2000)
        calling chr_bool with (calling chronicle.is_leap_year with 1900)
        calling chr_bool with (calling chronicle.is_leap_year with 2024)
        calling chr_bool with (calling chronicle.is_leap_year with 2023)
        calling chr_bool with (calling chronicle.is_leap_year with 202400)
    ''', "true\nfalse\ntrue\nfalse\ntrue\n")


def test_datetime_is_leap_year_method():
    """``DateTime.is_leap_year`` reads the record's own year."""
    _check('''
        var leap as chronicle.DateTime is calling chronicle.datetime_utc with 1704067200.0
        var plain as chronicle.DateTime is calling chronicle.datetime_utc with 1672531200.0
        calling chr_bool with (calling leap.is_leap_year)
        calling chr_bool with (calling plain.is_leap_year)
    ''', "true\nfalse\n")


def test_days_in_month():
    """``days_in_month`` honours leap Februaries, the 30-day months and 31s."""
    _check('''
        calling chr_int with (calling chronicle.days_in_month with 2024, 2)
        calling chr_int with (calling chronicle.days_in_month with 2023, 2)
        calling chr_int with (calling chronicle.days_in_month with 2000, 2)
        calling chr_int with (calling chronicle.days_in_month with 1900, 2)
        calling chr_int with (calling chronicle.days_in_month with 2024, 4)
        calling chr_int with (calling chronicle.days_in_month with 2024, 6)
        calling chr_int with (calling chronicle.days_in_month with 2024, 12)
    ''', "29\n28\n29\n28\n30\n30\n31\n")


def test_days_in_month_rejects_out_of_range_months():
    """Month 0 and month 13 return 0 so callers can validate input."""
    _check('''
        calling chr_int with (calling chronicle.days_in_month with 2024, 0)
        calling chr_int with (calling chronicle.days_in_month with 2024, 13)
        calling chr_int with (calling chronicle.days_in_month with 2024, -1)
    ''', "0\n0\n0\n")


def test_days_in_year():
    """``days_in_year`` is 366 only for Gregorian leap years."""
    _check('''
        calling chr_int with (calling chronicle.days_in_year with 2024)
        calling chr_int with (calling chronicle.days_in_year with 2023)
        calling chr_int with (calling chronicle.days_in_year with 2000)
        calling chr_int with (calling chronicle.days_in_year with 1900)
    ''', "366\n365\n366\n365\n")


# ---------------------------------------------------------------------------
# Calendar boundaries
# ---------------------------------------------------------------------------

def test_start_of_day():
    """``start_of_day`` floors to 00:00:00 UTC, including the epoch."""
    _check('''
        calling chr_ts with (calling chronicle.start_of_day with 1700000000.0)
        calling chr_ts with (calling chronicle.start_of_day with 1699920000.0)
        calling chr_ts with (calling chronicle.start_of_day with 0.0)
    ''', "1699920000\n1699920000\n0\n")


def test_start_of_day_normalises_negative_timestamps():
    """A pre-epoch second floors onto the correct previous UTC day."""
    _check('''
        calling chr_ts with (calling chronicle.start_of_day with -1.0)
        calling chr_ts with (calling chronicle.start_of_day with -86400.0)
        calling chr_ts with (calling chronicle.start_of_day with -86401.0)
    ''', "-86400\n-86400\n-172800\n")


def test_end_of_day():
    """``end_of_day`` is 23:59:59 UTC at magnitudes a 32-bit float holds exactly."""
    _check('''
        calling chr_ts with (calling chronicle.end_of_day with 0.0)
        calling chr_ts with (calling chronicle.end_of_day with 86400.0)
        calling chr_ts with (calling chronicle.end_of_day with 3600.0)
    ''', "86399\n172799\n86399\n")


def test_start_of_month_and_start_of_year():
    """``start_of_month`` and ``start_of_year`` truncate a fixed timestamp."""
    _check('''
        calling chr_ts with (calling chronicle.start_of_month with 1700000000.0)
        calling chr_ts with (calling chronicle.start_of_year with 1700000000.0)
        calling chr_ts with (calling chronicle.start_of_year with 0.0)
    ''', "1698796800\n1672531200\n0\n")


def test_start_of_week_is_monday_midnight():
    """Weeks start on Monday, so a Tuesday floors to the previous Monday."""
    _check('''
        calling chr_ts with (calling chronicle.start_of_week with 1700000000.0)
        calling chr_ts with (calling chronicle.start_of_week with 1699833600.0)
        calling chr_int with (calling chronicle.utc_weekday with 1699833600.0)
    ''', "1699833600\n1699833600\n1\n")


def test_start_of_quarter():
    """``start_of_quarter`` floors to January, April, July or October."""
    _check('''
        calling chr_ts with (calling chronicle.start_of_quarter with 1700000000.0)
        calling chr_ts with (calling chronicle.start_of_quarter with 1672531200.0)
        calling chr_ts with (calling chronicle.start_of_quarter with 1709164800.0)
    ''', "1696118400\n1672531200\n1704067200\n")


def test_end_of_month():
    """``end_of_month`` honours the month length (Jan 31 days, Feb 28)."""
    _check('''
        calling chr_ts with (calling chronicle.end_of_month with 0.0)
        calling chr_ts with (calling chronicle.end_of_month with 86400.0)
        calling chr_ts with (calling chronicle.end_of_month with 2678400.0)
    ''', "2678399\n2678399\n5097599\n")


def test_end_of_month_of_a_leap_february_stays_within_one_second():
    """The documented Feb-2024 end (1709251199) is honoured within 1 second.

    ``chronicle`` stores timestamps in a 32-bit ``float``; at 2024 magnitudes the
    least significant bit is 128 seconds, so 23:59:59 is not representable and the
    stored value rounds.  This test pins the documented second within a
    one-second tolerance rather than the rounded bit pattern.
    """
    _check('''
        let got as float is calling chronicle.end_of_month with 1706745600.0
        let delta as float is calling chronicle.diff_seconds with got, 1709251199.0
        calling chr_bool with (delta >= -1.0 and delta <= 1.0)
    ''', "true\n")


# ---------------------------------------------------------------------------
# Distances and arithmetic on raw timestamps
# ---------------------------------------------------------------------------

def test_days_between_and_hours_between_are_non_negative():
    """The two distances do not depend on the argument order."""
    _check('''
        calling chr_int with (calling chronicle.days_between with 0.0, 259200.0)
        calling chr_int with (calling chronicle.days_between with 259200.0, 0.0)
        calling chr_int with (calling chronicle.days_between with 0.0, 0.0)
        calling chr_int with (calling chronicle.hours_between with 0.0, 7200.0)
        calling chr_int with (calling chronicle.hours_between with 7200.0, 0.0)
    ''', "3\n3\n0\n2\n2\n")


def test_diff_seconds_and_diff_days_are_signed():
    """``diff_seconds``/``diff_days`` are ``a - b`` and keep the sign."""
    _check('''
        calling chr_ts with (calling chronicle.diff_seconds with 10.0, 4.0)
        calling chr_ts with (calling chronicle.diff_seconds with 4.0, 10.0)
        calling chr_int with (calling chronicle.diff_days with 259200.0, 0.0)
        calling chr_int with (calling chronicle.diff_days with 0.0, 259200.0)
    ''', "6\n-6\n3\n-3\n")


def test_add_seconds_through_add_weeks():
    """``add_seconds`` through ``add_weeks`` use their unit and default of one."""
    _check('''
        calling chr_ts with (calling chronicle.add_seconds with 100.0)
        calling chr_ts with (calling chronicle.add_seconds with 100.0, 5)
        calling chr_ts with (calling chronicle.add_seconds with 100.0, -200)
        calling chr_ts with (calling chronicle.add_minutes with 0.0, 2)
        calling chr_ts with (calling chronicle.add_hours with 0.0, 1)
        calling chr_ts with (calling chronicle.add_days with 0.0, 1)
        calling chr_ts with (calling chronicle.add_weeks with 0.0, 1)
        calling chr_ts with (calling chronicle.add_weeks with 0.0, -1)
    ''', "101\n105\n-100\n120\n3600\n86400\n604800\n-604800\n")


def test_is_before_is_after_and_is_between():
    """The raw-timestamp comparisons are strict and ``is_between`` is inclusive."""
    _check('''
        calling chr_bool with (calling chronicle.is_before with 1.0, 2.0)
        calling chr_bool with (calling chronicle.is_before with 2.0, 2.0)
        calling chr_bool with (calling chronicle.is_after with 2.0, 1.0)
        calling chr_bool with (calling chronicle.is_after with 2.0, 2.0)
        calling chr_bool with (calling chronicle.is_between with 5.0, 5.0, 5.0)
        calling chr_bool with (calling chronicle.is_between with 4.0, 5.0, 6.0)
        calling chr_bool with (calling chronicle.is_between with 7.0, 5.0, 6.0)
    ''', "true\nfalse\ntrue\nfalse\ntrue\nfalse\nfalse\n")


def test_modern_timestamp_second_is_lost():
    """A one-second bump at 2023 magnitudes is lost in the 32-bit clock value.

    ``chronicle`` declares its timestamps as ``float``; at 1.7e9 the least
    significant bit is 128 seconds, so ``add_seconds(1700000000.0, 1)`` cannot
    change the value.  This documents the module's current precision, reported as
    a finding rather than treated as a contract to preserve.
    """
    _check('''
        let base as float is 1700000000.0
        let bumped as float is calling chronicle.add_seconds with base, 1
        calling chr_bool with (bumped == base)
    ''', "true\n")


# ---------------------------------------------------------------------------
# seconds_to_hms
# ---------------------------------------------------------------------------

def test_seconds_to_hms_splits_into_hours_minutes_seconds():
    """``seconds_to_hms`` fills an outer hour and an inner minute/second pair."""
    _check('''
        let a as oracle.Pair of int and oracle.Pair of int and int is calling chronicle.seconds_to_hms with 3661
        calling chr_int with a.first
        calling chr_int with a.second.first
        calling chr_int with a.second.second
        let b as oracle.Pair of int and oracle.Pair of int and int is calling chronicle.seconds_to_hms with 3600
        calling chr_int with b.first
        calling chr_int with b.second.first
        calling chr_int with b.second.second
    ''', "1\n1\n1\n1\n0\n0\n")


def test_seconds_to_hms_uses_the_absolute_value():
    """A negative or zero input still yields non-negative components."""
    _check('''
        let a as oracle.Pair of int and oracle.Pair of int and int is calling chronicle.seconds_to_hms with -61
        calling chr_int with a.first
        calling chr_int with a.second.first
        calling chr_int with a.second.second
        let b as oracle.Pair of int and oracle.Pair of int and int is calling chronicle.seconds_to_hms with 0
        calling chr_int with b.first
        calling chr_int with b.second.first
        calling chr_int with b.second.second
    ''', "0\n1\n1\n0\n0\n0\n")


# ---------------------------------------------------------------------------
# Formatting and parsing
# ---------------------------------------------------------------------------

def test_format_patterns():
    """``format`` renders the pinned timestamps with a strftime pattern in UTC."""
    _check('''
        calling chr_str with (calling chronicle.format with "%Y-%m-%d", 0.0)
        calling chr_str with (calling chronicle.format with "%H:%M:%S", 3661.0)
        calling chr_str with (calling chronicle.format with "%Y-%m-%dT%H:%M:%SZ", 1700000000.0)
        calling chr_str with (calling chronicle.format with "%Y", 1700000000.0)
    ''', "1970-01-01\n01:01:01\n2023-11-14T22:13:20Z\n2023\n")


def test_format_with_an_empty_pattern_uses_the_default():
    """An empty ``fmt`` falls back to ``%Y-%m-%d %H:%M:%S``."""
    _check('''
        calling chr_str with (calling chronicle.format with "", 0.0)
        calling chr_str with (calling chronicle.format with "", 1700000000.0)
    ''', "1970-01-01 00:00:00\n2023-11-14 22:13:20\n")


def test_to_date_time_and_datetime_strings():
    """The ``to_*_string`` helpers agree with the equivalent ``format`` call."""
    _check('''
        calling chr_str with (calling chronicle.to_date_string with 0.0)
        calling chr_str with (calling chronicle.to_time_string with 3661.0)
        calling chr_str with (calling chronicle.to_datetime_string with 0.0)
        calling chr_str with (calling chronicle.to_datetime_string with 1700000000.0)
    ''', "1970-01-01\n01:01:01\n1970-01-01 00:00:00\n2023-11-14 22:13:20\n")


def test_parse_reports_presence_for_supported_text():
    """``parse`` returns a present maybe for date and date-time text.

    Only presence is asserted: the value carried by a ``parse`` result is
    presently wrong (the C bridge stores a ``double`` payload that the 32-bit
    ``float`` accessor misreads), which was reported as a module finding.
    """
    _check('''
        let a as maybe float is calling chronicle.parse with "2023-11-14T22:13:20", "%Y-%m-%dT%H:%M:%S"
        calling chr_bool with a.is_present
        let b as maybe float is calling chronicle.parse with "1970-01-01", "%Y-%m-%d"
        calling chr_bool with b.is_present
    ''', "true\ntrue\n")


def test_parse_rejects_unparsable_text():
    """``parse`` returns ``none`` for empty, short or wrongly shaped text."""
    _check('''
        let a as maybe float is calling chronicle.parse with "", "%Y-%m-%d"
        calling chr_bool with a.is_present
        let b as maybe float is calling chronicle.parse with "abc", "%Y-%m-%d"
        calling chr_bool with b.is_present
        let c as maybe float is calling chronicle.parse with "2023/11/14", "%Y-%m-%d"
        calling chr_bool with c.is_present
    ''', "false\nfalse\nfalse\n")


def test_format_duration_renders_hours_minutes_and_seconds():
    """``format_duration`` drops leading zero units and renders 0 for ``<= 0``."""
    _check('''
        calling chr_str with (calling chronicle.format_duration with 0.0)
        calling chr_str with (calling chronicle.format_duration with -5.0)
        calling chr_str with (calling chronicle.format_duration with 45.0)
        calling chr_str with (calling chronicle.format_duration with 59.0)
        calling chr_str with (calling chronicle.format_duration with 60.0)
        calling chr_str with (calling chronicle.format_duration with 930.0)
        calling chr_str with (calling chronicle.format_duration with 9045.0)
    ''', "0s\n0s\n45s\n59s\n1m 0s\n15m 30s\n2h 30m 45s\n")


def test_parse_duration_accepts_suffixes_and_raw_seconds():
    """``parse_duration`` maps a trailing s/m/h/d to its unit; bare ints are s."""
    _check('''
        let raw as maybe float is calling chronicle.parse_duration with "45"
        calling chr_ts with (raw.value)
        let sec as maybe float is calling chronicle.parse_duration with "10s"
        calling chr_ts with (sec.value)
        let minutes as maybe float is calling chronicle.parse_duration with "30m"
        calling chr_ts with (minutes.value)
        let hours as maybe float is calling chronicle.parse_duration with "2h"
        calling chr_ts with (hours.value)
        let days as maybe float is calling chronicle.parse_duration with "7d"
        calling chr_ts with (days.value)
        let spaced as maybe float is calling chronicle.parse_duration with " 15m "
        calling chr_ts with (spaced.value)
    ''', "45\n10\n1800\n7200\n604800\n900\n")


def test_parse_duration_rejects_unsupported_text():
    """An empty string, a lone letter or an unknown suffix is ``none``."""
    _check('''
        let a as maybe float is calling chronicle.parse_duration with ""
        calling chr_bool with a.is_present
        let b as maybe float is calling chronicle.parse_duration with "x"
        calling chr_bool with b.is_present
        let c as maybe float is calling chronicle.parse_duration with "5x"
        calling chr_bool with c.is_present
        let d as maybe float is calling chronicle.parse_duration with "abc"
        calling chr_bool with d.is_present
    ''', "false\nfalse\nfalse\nfalse\n")


# ---------------------------------------------------------------------------
# Stopwatch
# ---------------------------------------------------------------------------

def test_stopwatch_reports_non_negative_elapsed_and_resets():
    """``elapsed_sec``/``elapsed_ms`` never go negative and ``reset`` restarts."""
    _check('''
        var sw as chronicle.Stopwatch is calling chronicle.new_stopwatch
        calling chr_bool with ((calling sw.elapsed_sec) >= 0.0)
        calling chr_bool with ((calling sw.elapsed_ms) >= 0)
        calling sw.reset
        calling chr_bool with ((calling sw.elapsed_sec) >= 0.0)
        calling chr_bool with ((calling sw.elapsed_ms) >= 0)
    ''', "true\ntrue\ntrue\ntrue\n")


def test_stopwatch_started_at_is_a_monotonic_reading():
    """A fresh ``Stopwatch`` records a non-negative monotonic start."""
    _check('''
        var sw as chronicle.Stopwatch is calling chronicle.new_stopwatch
        calling chr_bool with (sw.started_at >= 0.0)
        calling chr_bool with (sw.started_at <= (calling chronicle.monotonic))
    ''', "true\ntrue\n")


# ---------------------------------------------------------------------------
# Module boundary helpers that return strings
# ---------------------------------------------------------------------------

def test_to_iso_of_epoch_and_second_day():
    """``to_iso`` zero-pads every field of the very first UTC days."""
    _check('''
        calling chr_str with (calling chronicle.to_iso with 1.0)
        calling chr_str with (calling chronicle.to_iso with 90061.0)
    ''', "1970-01-01T00:00:01Z\n1970-01-02T01:01:01Z\n")


def test_datetime_to_date_and_to_time_pad_single_digits():
    """``to_date``/``to_time`` zero-pad month, day, hour, minute and second."""
    _check('''
        var dt as chronicle.DateTime is calling chronicle.datetime_utc with 90061.0
        calling chr_str with (calling dt.to_date)
        calling chr_str with (calling dt.to_time)
        calling chr_int with dt.year
        calling chr_int with dt.month
        calling chr_int with dt.day
    ''', "1970-01-02\n01:01:01\n1970\n1\n2\n")
