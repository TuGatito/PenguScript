#!/usr/bin/env python3
"""End-to-end tests for ``std.rites`` (Chunk 5 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.rites`` is the process-and-environment module: the environment accessors,
the command-line helpers, the shell escape/quote layer and the process-capture
family.  These tests pin the environment round-trip, ``shell_escape`` for
quote-bearing input, ``env_substitute``, argument forwarding, ``parse_flags``,
``which``, the ``run_capture*`` shapes, the POSIX credential getters and the
platform predicates.

The environment cases use a variable name unique to the case and unset it again,
and the capture cases tolerate a host without ``sh``: the generated program
consults ``rites.which`` first and prints the ``none`` shape when the tool is
missing, so the assertion holds either way.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

#: Whether the host the tests run on has ``sh`` on PATH.  The generated programs
#: probe it through ``rites.which``; the Python side uses it to pick the expected
#: output, so a host without a shell still passes instead of failing spuriously.
HAVE_SH = shutil.which("sh") is not None

pytestmark = [requires_cc, requires_runtime]


def run_pengu(source: str, *args: str, stdin_text: str = "",
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process."""
    with tempfile.TemporaryDirectory(prefix="pengu_rites_") as td:
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
# Program builders
# ---------------------------------------------------------------------------

#: Imports shared by every generated program; ``scrolls`` supplies the string
#: ``contains`` method the error-message assertion uses.
_PREAMBLE = """\
import std.spark
import std.rites
import std.scrolls
import std.oracle
"""


def _run_rites(body: str, *args: str) -> subprocess.CompletedProcess:
    """Runs ``body`` as the body of a ``main`` that imports spark and rites."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = [_PREAMBLE, "", "weave main into int:", body, "    return 0", ""]
    return run_pengu("\n".join(sections), *args)


def _print_int(expr: str) -> str:
    """One line of Pengu that prints the ``int`` expression ``expr``."""
    return f"calling spark.println with calling spark.str_int with ({expr})"


def _print_bool(expr: str) -> str:
    """One line of Pengu that prints the ``bool`` expression ``expr``."""
    return f"calling spark.println with calling spark.str_bool with ({expr})"


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``RITES_VERSION`` reports the migrated module version ``2.1.0``."""
    res = _run_rites('''
        calling spark.println with rites.RITES_VERSION
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "2.1.0\n"


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def test_setenv_getenv_has_env_unsetenv_round_trip():
    """A variable set with ``setenv`` is visible to ``getenv``/``has_env`` until unset."""
    res = _run_rites(f'''
        let n as string is "PENGU_RITES_EXT_ROUND"
        {_print_bool('calling rites.setenv with n, "v1", true')}
        {_print_bool("calling rites.has_env with n")}
        let got as maybe string is calling rites.getenv with n
        {_print_bool("got is present")}
        calling spark.println with got.value
        {_print_bool("calling rites.unsetenv with n")}
        {_print_bool("calling rites.has_env with n")}
        let gone as maybe string is calling rites.getenv with n
        {_print_bool("gone is present")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\nv1\ntrue\nfalse\nfalse\n"


def test_setenv_without_overwrite_keeps_the_first_value():
    """``setenv`` with ``overwrite`` false leaves an existing value untouched."""
    res = _run_rites(f'''
        let n as string is "PENGU_RITES_EXT_KEEP"
        {_print_bool('calling rites.setenv with n, "first", true')}
        {_print_bool('calling rites.setenv with n, "second", false')}
        let got as maybe string is calling rites.getenv with n
        calling spark.println with got.value
        {_print_bool('calling rites.setenv with n, "third", true')}
        let again as maybe string is calling rites.getenv with n
        calling spark.println with again.value
        {_print_bool("calling rites.unsetenv with n")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\nfirst\ntrue\nthird\ntrue\n"


def test_an_empty_environment_value_is_present():
    """A variable set to ``""`` is present with a zero-length value, not absent."""
    res = _run_rites(f'''
        let n as string is "PENGU_RITES_EXT_EMPTY"
        {_print_bool('calling rites.setenv with n, "", true')}
        let got as maybe string is calling rites.getenv with n
        {_print_bool("got is present")}
        {_print_bool("(got.value length) == 0")}
        {_print_bool("calling rites.unsetenv with n")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\n"


def test_getenv_or_returns_the_fallback_for_an_unset_name():
    """``getenv_or`` yields its default when the variable is not in the environment."""
    res = _run_rites('''
        calling spark.println with (calling rites.getenv_or with "PENGU_RITES_EXT_UNSET_X", "fallback")
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "fallback\n"


def test_get_env_keys_includes_a_freshly_set_variable():
    """``get_env_keys`` reports the process environment that ``setenv`` just changed."""
    res = _run_rites(f'''
        let n as string is "PENGU_RITES_EXT_KEYS"
        {_print_bool('calling rites.setenv with n, "x", true')}
        let keys as list of string is calling rites.get_env_keys
        var found as bool is false
        for k in keys:
            if k == n:
                set found is true
        {_print_bool("found")}
        {_print_bool("(calling keys.len) >= 1")}
        {_print_bool("calling rites.unsetenv with n")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\ntrue\n"


def test_env_substitute_expands_braced_percent_and_escaped_forms():
    """``env_substitute`` replaces ``${VAR}`` and ``%VAR%``, empties unknown names and unescapes ``$$``."""
    res = _run_rites('''
        let n as string is "PENGU_RITES_EXT_SUBST"
        calling rites.setenv with n, "alias", true
        let ob as string is "{"
        let cb as string is "}"
        let braced as string is "${ob}PENGU_RITES_EXT_SUBST{cb}"
        calling spark.println with (calling rites.env_substitute with braced)
        calling spark.println with (calling rites.env_substitute with "%PENGU_RITES_EXT_SUBST%")
        let unknown as string is calling rites.env_substitute with "x${ob}PENGU_RITES_EXT_UNSET{cb}y"
        calling spark.println with unknown
        calling spark.println with (calling rites.env_substitute with "$$HOME")
        calling rites.unsetenv with n
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "alias\nalias\nxy\n$HOME\n"


# ---------------------------------------------------------------------------
# shell_escape
# ---------------------------------------------------------------------------

def test_shell_escape_wraps_a_plain_argument():
    """A plain argument comes back wrapped in single quotes."""
    res = _run_rites('''
        calling spark.println with (calling rites.shell_escape with "plain")
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "'plain'\n"


def test_shell_escape_doubles_an_embedded_single_quote():
    """An embedded ``'`` is rewritten as ``'\\''`` before the closing quote."""
    res = _run_rites('''
        calling spark.println with (calling rites.shell_escape with "it's")
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "'it'\\''s'\n"


def test_shell_escape_of_the_empty_string_is_two_quotes():
    """The empty argument becomes the literal ``''`` so the shell still sees one word."""
    res = _run_rites('''
        calling spark.println with (calling rites.shell_escape with "")
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "''\n"


# ---------------------------------------------------------------------------
# Program arguments and flags
# ---------------------------------------------------------------------------

def test_get_args_and_get_argc_agree_on_forwarded_arguments():
    """Two forwarded arguments give ``argc == 3`` (index 0 is the program name)."""
    res = _run_rites(f'''
        let args as list of string is calling rites.get_args
        let argc as int is calling rites.get_argc
        {_print_int("argc")}
        {_print_bool("(calling args.len) == argc")}
        {_print_int("calling args.len")}
        {_print_bool("((calling rites.get_argv with 0) length) > 0")}
        calling spark.println with (calling rites.arg_at_or with 1, "")
        calling spark.println with (calling rites.arg_at_or with 99999, "fallback")
    ''', "alpha", "--beta=gamma")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\ntrue\n3\ntrue\nalpha\nfallback\n"


def test_parse_flags_has_flag_and_get_flag_value():
    """``parse_flags`` reads ``--key=value`` and bare ``--flag`` and ignores positionals."""
    res = _run_rites(f'''
        {_print_bool('calling rites.has_flag with "verbose"')}
        {_print_bool('calling rites.has_flag with "absent"')}
        let value as maybe string is calling rites.get_flag_value with "output"
        calling spark.println with value.value
        let bare as maybe string is calling rites.get_flag_value with "verbose"
        calling spark.println with bare.value
        let missing as maybe string is calling rites.get_flag_value with "absent"
        {_print_bool("missing is present")}
        let flags as map of string to string is calling rites.parse_flags
        {_print_bool('calling flags.contains with "positional"')}
    ''', "--verbose", "--output=out.txt", "positional")
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\nfalse\nout.txt\ntrue\nfalse\nfalse\n"


# ---------------------------------------------------------------------------
# which
# ---------------------------------------------------------------------------

def test_which_finds_sh_or_reports_none():
    """``which`` either names an existing ``sh`` or hands back ``none``."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        {_print_bool("sh is present")}
        var nonempty as bool is false
        if sh is present:
            set nonempty is (sh.value length) > 0
        {_print_bool("nonempty")}
        let missing as maybe string is calling rites.which with "pengu-rites-no-such-tool-xyzzy"
        {_print_bool("missing is present")}
    ''')
    assert res.returncode == 0, res.stderr
    expected_present = "true" if HAVE_SH else "false"
    assert res.stdout == f"{expected_present}\n{expected_present}\nfalse\n"


# ---------------------------------------------------------------------------
# run_capture and friends
# ---------------------------------------------------------------------------

def test_run_capture_returns_stdout_on_success():
    """``run_capture`` gives back the captured stdout for a zero exit."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        var text_ok as bool is false
        if sh is present:
            let args1 as list of string is ["-c", "echo hi"]
            let out as maybe string is calling rites.run_capture with "sh", args1
            set present is (out is present)
            if out is present:
                let want as string is "hi\\n"
                set text_ok is (out.value) == want
        {_print_bool("present")}
        {_print_bool("text_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\ntrue\n" if HAVE_SH else "false\nfalse\n")


def test_run_capture_returns_none_on_a_nonzero_exit():
    """A non-zero exit collapses to ``none``, never to partial output."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        if sh is present:
            let args2 as list of string is ["-c", "exit 3"]
            let out as maybe string is calling rites.run_capture with "sh", args2
            set present is (out is present)
        {_print_bool("present")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\n"


def test_run_capture_result_is_ok_on_success():
    """``run_capture_result`` carries the stdout in its ``ok`` payload."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var is_ok as bool is false
        var value_ok as bool is false
        if sh is present:
            let args3 as list of string is ["-c", "echo ok"]
            let r as result of string to string is calling rites.run_capture_result with "sh", args3
            set is_ok is r.is_ok
            if r.is_ok:
                let want as string is "ok\\n"
                set value_ok is (r.value) == want
        {_print_bool("is_ok")}
        {_print_bool("value_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\ntrue\n" if HAVE_SH else "false\nfalse\n")


def test_run_capture_result_is_err_and_mentions_the_exit_code():
    """A non-zero exit is an ``err`` whose message names the failing code."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var err_shape as bool is false
        var mentions_code as bool is false
        if sh is present:
            let args4 as list of string is ["-c", "exit 7"]
            let r as result of string to string is calling rites.run_capture_result with "sh", args4
            if calling r.is_err:
                let msg as string is r.error
                set err_shape is (msg length) > 0
                set mentions_code is calling msg.contains with "7"
        {_print_bool("err_shape")}
        {_print_bool("mentions_code")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\ntrue\n" if HAVE_SH else "false\nfalse\n")


def test_run_capture_lines_splits_stdout():
    """``run_capture_lines`` drops the trailing newline into separate lines."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        var count as int is 0
        if sh is present:
            let args5 as list of string is ["-c", "printf 'a\\nb\\n'"]
            let lines as maybe list of string is calling rites.run_capture_lines with "sh", args5
            set present is (lines is present)
            if lines is present:
                let ls as list of string is lines.value
                set count is calling ls.len
        {_print_bool("present")}
        {_print_int("count")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\n2\n" if HAVE_SH else "false\n0\n")


def test_run_capture_lines_of_empty_stdout_is_an_empty_list():
    """Empty output is ``some []`` -- present, but with nothing in it."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        var count as int is 0
        if sh is present:
            let args6 as list of string is ["-c", "true"]
            let lines as maybe list of string is calling rites.run_capture_lines with "sh", args6
            set present is (lines is present)
            if lines is present:
                let ls as list of string is lines.value
                set count is calling ls.len
        {_print_bool("present")}
        {_print_int("count")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\n0\n" if HAVE_SH else "false\n0\n")


def test_run_capture_stderr_captures_only_stderr():
    """``run_capture_stderr`` returns the error stream, not the standard one."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        var text_ok as bool is false
        if sh is present:
            let args7 as list of string is ["-c", "echo oops >&2"]
            let err as maybe string is calling rites.run_capture_stderr with "sh", args7
            set present is (err is present)
            if err is present:
                let want as string is "oops\\n"
                set text_ok is (err.value) == want
        {_print_bool("present")}
        {_print_bool("text_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\ntrue\n" if HAVE_SH else "false\nfalse\n")


def test_run_shell_capture_runs_a_pipeline():
    """``run_shell_capture`` hands the whole line to the shell, pipes included."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        var text_ok as bool is false
        if sh is present:
            let out as maybe string is calling rites.run_shell_capture with "echo ab | tr a-z A-Z"
            set present is (out is present)
            if out is present:
                let want as string is "AB\\n"
                set text_ok is (out.value) == want
        {_print_bool("present")}
        {_print_bool("text_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == ("true\ntrue\n" if HAVE_SH else "false\nfalse\n")


def test_run_shell_capture_returns_none_on_a_failing_line():
    """A shell line that exits non-zero collapses to ``none``."""
    res = _run_rites(f'''
        let sh as maybe string is calling rites.which with "sh"
        var present as bool is false
        if sh is present:
            let out as maybe string is calling rites.run_shell_capture with "exit 5"
            set present is (out is present)
        {_print_bool("present")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\n"


# ---------------------------------------------------------------------------
# Process identity and platform
# ---------------------------------------------------------------------------

def test_get_uid_and_get_gid_are_present_on_posix():
    """On POSIX both real ids are present and non-negative; elsewhere they are ``none``."""
    res = _run_rites(f'''
        var uid_ok as bool is false
        var gid_ok as bool is false
        if calling rites.is_unix:
            let uid as maybe int is calling rites.get_uid
            let gid as maybe int is calling rites.get_gid
            if uid is present:
                set uid_ok is (uid.value) >= 0
            if gid is present:
                set gid_ok is (gid.value) >= 0
        {_print_bool("uid_ok")}
        {_print_bool("gid_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    expected = "true\ntrue\n" if os.name == "posix" else "false\nfalse\n"
    assert res.stdout == expected


def test_get_euid_and_get_egid_shape_matches_the_platform():
    """The effective ids answer with the same ``maybe int`` shape as the real ids."""
    res = _run_rites(f'''
        var euid_ok as bool is false
        var egid_ok as bool is false
        if calling rites.is_unix:
            let euid as maybe int is calling rites.get_euid
            let egid as maybe int is calling rites.get_egid
            if euid is present:
                set euid_ok is (euid.value) >= 0
            if egid is present:
                set egid_ok is (egid.value) >= 0
        {_print_bool("euid_ok")}
        {_print_bool("egid_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    expected = "true\ntrue\n" if os.name == "posix" else "false\nfalse\n"
    assert res.stdout == expected


def test_is_windows_and_is_unix_are_exclusive_and_total():
    """Exactly one platform predicate is true, so the pair partitions the hosts."""
    res = _run_rites(f'''
        let win as bool is calling rites.is_windows
        let unix as bool is calling rites.is_unix
        {_print_bool("win != unix")}
        {_print_bool("win or unix")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\n"


def test_home_dir_and_temp_dir_are_non_empty():
    """``temp_dir`` always exists; ``home_dir`` is present exactly when ``HOME`` is set."""
    res = _run_rites(f'''
        let tmp as maybe string is calling rites.temp_dir
        {_print_bool("tmp is present")}
        {_print_bool("(tmp.value length) > 0")}
        let home as maybe string is calling rites.home_dir
        var home_ok as bool is false
        if home is present:
            set home_ok is (home.value length) > 0
        {_print_bool("home_ok")}
    ''')
    assert res.returncode == 0, res.stderr
    expected_home = "true" if os.environ.get("HOME") else "false"
    assert res.stdout == f"true\ntrue\n{expected_home}\n"


def test_os_family_os_arch_and_uname_are_non_empty_and_agree():
    """``os_family``/``os_arch`` describe the host and ``uname`` aliases the family."""
    res = _run_rites(f'''
        let family as string is calling rites.os_family
        let arch_name as string is calling rites.os_arch
        let un as string is calling rites.uname
        {_print_bool("(family length) > 0")}
        {_print_bool("(arch_name length) > 0")}
        {_print_bool("un == family")}
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "true\ntrue\ntrue\n"
