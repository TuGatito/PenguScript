#!/usr/bin/env python3
"""End-to-end tests for ``std.scrolls`` (Chunk 2 of the Pengunic 2.0 migration).

Every test here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout.  Nothing inspects the generated C: the contract under test
is behaviour, and the compiler is free to change how it gets there.

The suite is deliberately self-contained.  Each test writes its own throw-away
program into a temporary directory and runs it with the binary cache disabled, so
no test can observe another test's state and a failure names exactly one program.

The compiler is invoked through the repository's own CLI (``pengu_project.py``):
a source checkout has no installed ``pengu`` binary, and the CLI is what CI runs.
``-q`` suppresses the build progress lines so the assertions can compare the
program's output byte for byte.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

REPO = Path(__file__).resolve().parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process.

    Args:
        source: the whole PenguScript program.  It is dedented, so tests can
            indent it to match their own block.
        args: forwarded to the program after ``--``.
        stdin_text: what the program reads from stdin.
        timeout: seconds allowed for compile + run.

    Returns:
        The ``CompletedProcess`` of the CLI invocation.  With ``-q`` the CLI's
        own stdout/stderr are empty, so ``stdout``/``stderr`` are the program's.
    """
    with tempfile.TemporaryDirectory(prefix="pengu_scrolls_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO),
        )


# ---------------------------------------------------------------------------
# Bytes, not code points
# ---------------------------------------------------------------------------

def test_len_counts_bytes_not_code_points():
    """`len` counts bytes: the UTF-8 string `café` is five bytes long."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "café"
            calling spark.println_int with (calling s.len)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n"


def test_chars_returns_single_byte_strings():
    """`chars` splits a multi-byte string into one-byte elements."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "café"
            var letters as list of string is calling s.chars
            calling spark.println_int with (letters length)
            calling spark.println_int with (calling scrolls.len with (letters at 3))
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "5\n1\n"


# ---------------------------------------------------------------------------
# Trimming and case
# ---------------------------------------------------------------------------

def test_trim_removes_both_ends():
    """`trim` removes ASCII whitespace from both ends."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var raw as string is "  x  "
            calling spark.println with (calling raw.trim)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x\n"


def test_strip_is_an_alias_of_trim():
    """`strip` behaves exactly like `trim` on the receiver."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var raw as string is "\\t x \\n"
            calling spark.println with (calling raw.strip)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x\n"


def test_lower_and_upper():
    """`lower`/`upper` change the case of ASCII letters only."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "AbC"
            calling spark.println with (calling scrolls.lower with s)
            calling spark.println with (calling scrolls.upper with s)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "abc\nABC\n"


# ---------------------------------------------------------------------------
# Splitting and joining
# ---------------------------------------------------------------------------

def test_split_keeps_empty_pieces():
    """`split` keeps the empty pieces between adjacent delimiters."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "a,,b"
            var parts as list of string is calling s.split with ","
            calling spark.println with (calling scrolls.join with parts, "|")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "a||b\n"


def test_split_accepts_multi_char_delimiter():
    """`split` matches the whole delimiter, not just its first byte."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "a::b::c"
            var parts as list of string is calling s.split with "::"
            calling spark.println_int with (parts length)
            calling spark.println with (parts at 1)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\nb\n"


def test_join_of_empty_list_is_empty():
    """`join` over an empty list produces an empty string."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var parts as list of string is list of string
            var joined as string is calling scrolls.join with parts, ","
            calling spark.println_int with (calling scrolls.len with joined)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "0\n"


def test_splitn_keeps_the_remainder():
    """`splitn` stops after `n` parts and keeps the rest in the last one."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "a,b,c,d"
            var parts as list of string is calling s.splitn with ",", 2
            calling spark.println_int with (parts length)
            calling spark.println with (parts at 1)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\nb,c,d\n"


def test_rsplit_preserves_order():
    """`rsplit` scans from the right but returns left-to-right pieces."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "x:y:z"
            var parts as list of string is calling s.rsplit with ":"
            calling spark.println with (calling scrolls.join with parts, "/")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "x/y/z\n"


# ---------------------------------------------------------------------------
# Replacement
# ---------------------------------------------------------------------------

def test_replace_only_first_occurrence():
    """`replace` rewrites the first match and leaves the rest alone."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "cat, cat"
            calling spark.println with (calling s.replace with "cat", "dog")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "dog, cat\n"


def test_replace_all_every_occurrence():
    """`replace_all` rewrites every non-overlapping match."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "cat, cat"
            calling spark.println with (calling s.replace_all with "cat", "dog")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "dog, dog\n"


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def test_starts_with_empty_prefix():
    """An empty prefix always matches `starts_with`."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "abc"
            calling spark.println with (calling spark.str_bool with (calling s.starts_with with ""))
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\n"


def test_index_of_not_found_is_minus_one():
    """`index_of` returns -1 when the needle is absent."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "abc"
            calling spark.println_int with (calling s.index_of with "z")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n"


def test_starts_with_any_and_ends_with_any():
    """The any-prefix/any-suffix predicates short-circuit on the first match."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "abc"
            var prefixes as list of string is ["x", "ab"]
            var suffixes as list of string is ["x", "bc"]
            var empty_list as list of string is list of string
            calling spark.println with (calling spark.str_bool with (calling s.starts_with_any with prefixes))
            calling spark.println with (calling spark.str_bool with (calling s.ends_with_any with suffixes))
            calling spark.println with (calling spark.str_bool with (calling s.starts_with_any with empty_list))
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nfalse\n"


# ---------------------------------------------------------------------------
# Slicing
# ---------------------------------------------------------------------------

def test_substring_clamps_out_of_range_end():
    """`substring` clamps an end past the length instead of failing."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "abcdef"
            var piece as string is calling scrolls.substring with s, 2, 99
            calling spark.println with piece
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "cdef\n"


# ---------------------------------------------------------------------------
# Classification and case conversion
# ---------------------------------------------------------------------------

def test_is_palindrome():
    """`is_palindrome` compares the string with its reverse."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var ok as string is "racecar"
            var bad as string is "ab"
            calling spark.println with (calling spark.str_bool with (calling ok.is_palindrome))
            calling spark.println with (calling spark.str_bool with (calling bad.is_palindrome))
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\n"


def test_to_snake_case_splits_camel_case():
    """`to_snake_case` separates camelCase and acronym runs."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "HTTPServer"
            calling spark.println with (calling s.to_snake_case)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "http_server\n"


def test_to_kebab_case_uses_dashes():
    """`to_kebab_case` is `to_snake_case` with dashes."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "HelloWorld"
            calling spark.println with (calling s.to_kebab_case)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "hello-world\n"


def test_pascal_case_capitalises_every_word():
    """`pascal_case` capitalises each `snake_case` word."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "hello_world"
            calling spark.println with (calling s.pascal_case)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "HelloWorld\n"


def test_words_ignores_extra_spaces():
    """`words` splits on runs of whitespace and drops the edges."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "  a  b "
            var parts as list of string is calling s.words
            calling spark.println_int with (parts length)
            calling spark.println with (calling scrolls.join with parts, "|")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2\na|b\n"


def test_lines_strips_carriage_returns():
    """`lines` drops the trailing CR of CRLF input."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "a\\r\\nb\\r\\n"
            var parts as list of string is calling s.lines
            calling spark.println_int with (parts length)
            calling spark.println with (parts at 0)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\na\n"


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def test_compare_is_lexicographic():
    """`compare` returns -1/0/1 in byte order."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var a as string is "apple"
            var b as string is "banana"
            calling spark.println_int with (calling scrolls.compare with a, b)
            calling spark.println_int with (calling b.compare with a)
            calling spark.println_int with (calling a.compare with a)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-1\n1\n0\n"


# ---------------------------------------------------------------------------
# Padding and truncation
# ---------------------------------------------------------------------------

def test_zfill_preserves_the_sign():
    """`zfill` keeps a leading `-`/`+` in front of the zeros."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var negative as string is "-42"
            var positive as string is "+42"
            calling spark.println with (calling negative.zfill with 6)
            calling spark.println with (calling positive.zfill with 5)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-00042\n+0042\n"


def test_center_odd_padding_goes_right():
    """With odd padding `center` gives the smaller half to the left."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "ab"
            calling spark.println with (calling s.center with 5, "-")
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "-ab--\n"


def test_truncate_adds_ellipsis():
    """`ellipsis` cuts the string and appends `...`."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is "Hello, world"
            calling spark.println with (calling s.ellipsis with 8)
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "Hello...\n"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def test_parse_int_accepts_whitespace():
    """`parse_int` tolerates surrounding whitespace."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var s as string is " 42 "
            var m as maybe int is calling s.parse_int
            calling spark.println with (calling spark.str_int with (m or else -1))
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "42\n"


def test_parse_float_rejects_exponents():
    """`parse_float` accepts decimals but rejects exponents."""
    res = run_pengu('''
        import std.scrolls
        import std.spark

        weave main into int:
            var decimal as string is "3.5"
            var exponent as string is "1e3"
            var good as maybe float is calling decimal.parse_float
            var bad as maybe float is calling exponent.parse_float
            calling spark.println with (calling spark.str_bool with (good.is_present))
            calling spark.println with (calling spark.str_bool with (bad.is_present))
            return 0
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\n"
