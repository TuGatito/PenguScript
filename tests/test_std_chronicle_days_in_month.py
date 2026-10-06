"""Roadmap Phase 6 / item 6.12 — ``chronicle.days_in_month`` must validate its month.

The month was not range-checked: the function returned 31 through its fallback
branch for ``m = 0``, ``m = 13``, negative months and any other out-of-range
value, so a caller could not distinguish "December" from "garbage".

The roadmap described this as an out-of-bounds read of a ``feb_days[12]``
table.  That premise is wrong: the implementation is a plain if-chain with no
array and no indexing, so there was no memory-safety bug -- only a missing
range validation.  The test below pins the observable contract either way.
"""

import pytest

from tests.conftest import compile_run, requires_runtime

# (year, month) -> expected day count, 0 meaning "invalid month".
_CASES = [
    (2024, 1, 31),
    (2024, 2, 29),
    (2023, 2, 28),
    (2000, 2, 29),
    (1900, 2, 28),
    (2024, 3, 31),
    (2024, 4, 30),
    (2024, 5, 31),
    (2024, 6, 30),
    (2024, 7, 31),
    (2024, 8, 31),
    (2024, 9, 30),
    (2024, 10, 31),
    (2024, 11, 30),
    (2024, 12, 31),
    (2024, 0, 0),
    (2024, 13, 0),
    (2024, -1, 0),
    (2024, 100, 0),
    (2024, -2147483648, 0),
]


def _program() -> str:
    lines = []
    for i, (year, month, want) in enumerate(_CASES):
        lines.append(f"    var d{i} as int is calling chronicle.days_in_month with {year} , {month}")
        lines.append(
            f"    if d{i} != {want}:\n"
            f'        calling spark.println with "days_in_month({year}, {month}) = {{d{i}}}, want {want}"\n'
            f'        calling spark.panic with "days_in_month({year}, {month})"'
        )
    return (
        "import std.spark\n"
        "import std.chronicle\n"
        "\n"
        "weave main into void:\n" + "\n".join(lines) + "\n"
    )


@requires_runtime
def test_days_in_month_full_matrix():
    compile_run(_program(), tag="days_in_month")


@requires_runtime
def test_out_of_range_months_return_zero():
    """The specific regression: 0 and 13 used to come back as 31."""
    src = (
        "import std.spark\n"
        "import std.chronicle\n"
        "\n"
        "weave main into void:\n"
        "    var m0 as int is calling chronicle.days_in_month with 2024 , 0\n"
        "    var m13 as int is calling chronicle.days_in_month with 2024 , 13\n"
        "    var m12 as int is calling chronicle.days_in_month with 2024 , 12\n"
        "    calling spark.assert with (m0 == 0)\n"
        "    calling spark.assert with (m13 == 0)\n"
        "    calling spark.assert with (m12 == 31)\n"
    )
    compile_run(src, tag="days_in_month_range")


@requires_runtime
def test_leap_year_rules_still_apply():
    src = (
        "import std.spark\n"
        "import std.chronicle\n"
        "\n"
        "weave main into void:\n"
        "    var feb24 as int is calling chronicle.days_in_month with 2024 , 2\n"
        "    var feb23 as int is calling chronicle.days_in_month with 2023 , 2\n"
        "    calling spark.assert with (feb24 == 29)\n"
        "    calling spark.assert with (feb23 == 28)\n"
        "    calling spark.assert with (calling chronicle.is_leap_year with 2000)\n"
        "    calling spark.assert with (not (calling chronicle.is_leap_year with 1900))\n"
    )
    compile_run(src, tag="days_in_month_leap")
