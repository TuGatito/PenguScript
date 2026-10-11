#!/usr/bin/env python3
"""End-to-end tests for ``std.whisper`` (Chunk 6 of the Pengunic 2.0 migration).

Every case here compiles and runs a small PenguScript program through the real
pipeline (Pengu source -> C bundle -> C compiler -> executable) and asserts the
program's own stdout, stderr and exit code.  Nothing inspects the generated C:
the contract under test is behaviour, and the compiler is free to change how it
gets there.

``std.whisper`` is the leveled-logging module: six severities, ANSI colours, ISO
timestamps, JSON lines, file/stderr redirection, hierarchical child loggers and
a per-name singleton registry.  This suite pins both the global functional
surface (``whisper.info``, ``whisper.set_level``, ``whisper.log_json`` ...) and
the ``Logger`` value rune, and carries a named regression test for each of the
2.1.0 fixes the migration documents (B12-B24).

Two details of the environment shape the assertions:

* The module colours stdout by default, so any textual comparison strips the
  SGR escapes first (or the program disables colour).  File output is plain by
  contract, so file-based assertions compare the raw bytes.
* The CLI prints a one-line ``[pengu] ...`` notice on stderr when it falls back
  from its development compiler to the host C compiler.  That line belongs to
  the build, not to the program, so :func:`_cli_noise_free` removes it before
  any stderr assertion.

Each test writes its own throw-away program into a temporary directory and runs
it with the binary cache disabled, so no test can observe another test's state
and a failure names exactly one program.  The compiler is invoked through the
repository's own CLI (``pengu_project.py``): a source checkout has no installed
``pengu`` binary, and the CLI is what CI runs.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

from tests.conftest import requires_cc, requires_runtime

#: Three levels up: tests/stdlib/test_whisper.py -> tests/stdlib -> tests -> repo.
REPO = Path(__file__).resolve().parent.parent.parent

#: The CLI entry point, run with the same interpreter as the test session.
PENGU = [sys.executable, str(REPO / "pengu_project.py")]

pytestmark = [requires_cc, requires_runtime]

#: ANSI SGR sequences ``whisper`` wraps coloured lines in.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

#: The environment variables ``set_level_from_env`` consults, in priority order.
_LEVEL_ENV_VARS = ("LOG_LEVEL", "RUST_LOG", "PENGU_LOG", "RITES_LOG_LEVEL", "WHISPER_LOG")


def run_pengu(source: str, *args: str, stdin_text: str = "",
              env: dict | None = None,
              timeout: int = 300) -> subprocess.CompletedProcess:
    """Compiles and runs ``source`` as a throw-away script and returns the process.

    Args:
        source: the whole PenguScript program.  It is dedented, so tests can
            indent it to match their own block.
        args: forwarded to the program after ``--``.
        stdin_text: what the program reads from stdin.
        env: the complete environment for the child.  ``None`` inherits this
            process's environment; env-sensitive tests pass
            :func:`_env_without_levels` so a developer's shell cannot leak a
            level into the program.
        timeout: seconds allowed for compile + run.

    Returns:
        The ``CompletedProcess`` of the CLI invocation.  With ``-q`` the CLI's
        own stdout is empty, so ``stdout`` is the program's; ``stderr`` may also
        carry the CLI's build-fallback notice (see :func:`_cli_noise_free`).
    """
    with tempfile.TemporaryDirectory(prefix="pengu_whisper_") as td:
        src = Path(td) / "main.pengu"
        src.write_text(textwrap.dedent(source).lstrip("\n"), encoding="utf-8")
        cmd = [*PENGU, "-q", "run", str(src), "--no-cache"]
        if args:
            cmd += ["--", *args]
        return subprocess.run(
            cmd, capture_output=True, text=True, input=stdin_text,
            timeout=timeout, cwd=str(REPO), env=env,
        )


def strip_ansi(text: str) -> str:
    """Removes every ANSI SGR sequence so colours do not break text matching."""
    return _ANSI_RE.sub("", text)


def _cli_noise_free(stderr: str) -> str:
    """Drops the CLI's own ``[pengu] ...`` build notices from ``stderr``.

    The notices describe the compiler fallback, not the program, and would
    otherwise make every ``stderr == ""`` assertion depend on which C backend
    the host happened to use.
    """
    return "\n".join(line for line in stderr.splitlines() if not line.startswith("[pengu]"))


def _env_without_levels(**overrides: str) -> dict:
    """A copy of ``os.environ`` with every log-level variable removed.

    ``set_level_from_env`` consults ``LOG_LEVEL``, ``RUST_LOG``, ``PENGU_LOG``,
    ``RITES_LOG_LEVEL`` and ``WHISPER_LOG``.  A developer's shell (or CI) may
    export any of them, so every env-sensitive test starts from an environment
    where none is set and opts specific ones back in.
    """
    env = {k: v for k, v in os.environ.items() if k not in _LEVEL_ENV_VARS}
    env.update(overrides)
    return env


#: Print helpers spliced into every program, so a test body stays one statement
#: per assertion and an exact stdout comparison pins the value.
_PRELUDE = '''
weave w_int with v as int into void:
    calling spark.println with calling spark.str_int with v

weave w_bool with v as bool into void:
    calling spark.println with calling spark.str_bool with v

weave w_str with v as string into void:
    calling spark.println with v
'''


def _run_main(body: str, *args: str, env: dict | None = None,
              stdin_text: str = "") -> subprocess.CompletedProcess:
    """Runs ``body`` as the statements of a ``main`` that imports the module."""
    body = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    sections = ["import std.spark", "import std.whisper", "import std.rites", ""]
    sections.append(textwrap.dedent(_PRELUDE).strip("\n"))
    sections += ["", "weave main into int:", body, "    return 0", ""]
    return run_pengu("\n".join(sections), *args, env=env, stdin_text=stdin_text)


def _check(body: str, expected: str, *args: str, env: dict | None = None) -> None:
    """Runs ``body`` and asserts exit 0 and ``expected`` after stripping colour."""
    res = _run_main(body, *args, env=env)
    assert res.returncode == 0, res.stderr
    assert strip_ansi(res.stdout) == expected, res.stderr


# ---------------------------------------------------------------------------
# Version, constants and level names
# ---------------------------------------------------------------------------

def test_version_constant_is_2_1_0():
    """``WHISPER_VERSION`` reports the module revision ``2.1.0``."""
    _check('calling w_str with whisper.WHISPER_VERSION', "2.1.0\n")


def test_level_constants_are_ordered_0_to_5():
    """``LOG_TRACE``..``LOG_FATAL`` are ``0``..``5`` in increasing severity."""
    _check('''
        calling w_int with whisper.LOG_TRACE
        calling w_int with whisper.LOG_DEBUG
        calling w_int with whisper.LOG_INFO
        calling w_int with whisper.LOG_WARN
        calling w_int with whisper.LOG_ERROR
        calling w_int with whisper.LOG_FATAL
    ''', "0\n1\n2\n3\n4\n5\n")


def test_color_constants_are_the_documented_ansi_escapes():
    """The ``COLOR_*`` constants hold the documented ANSI SGR byte sequences.

    The values are printed and compared on the Python side rather than compared
    with ``==`` inside PenguScript: the compiler currently does not lower a
    string ``==``/``!=`` between two module-level ``string`` values and emits C
    that the host compiler rejects.
    """
    res = _run_main('''
        calling spark.println with whisper.COLOR_GRAY
        calling spark.println with whisper.COLOR_CYAN
        calling spark.println with whisper.COLOR_GREEN
        calling spark.println with whisper.COLOR_YELLOW
        calling spark.println with whisper.COLOR_RED
        calling spark.println with whisper.COLOR_BRIGHT_RED
        calling spark.println with whisper.COLOR_RESET
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "\x1b[90m\n\x1b[36m\n\x1b[32m\n\x1b[33m\n"
        "\x1b[31m\n\x1b[91m\n\x1b[0m\n"
    )


def test_get_level_name_maps_every_level():
    """``get_level_name`` returns the uppercase name, unknown ids becoming FATAL."""
    _check('''
        calling w_str with calling whisper.get_level_name with whisper.LOG_TRACE
        calling w_str with calling whisper.get_level_name with whisper.LOG_DEBUG
        calling w_str with calling whisper.get_level_name with whisper.LOG_INFO
        calling w_str with calling whisper.get_level_name with whisper.LOG_WARN
        calling w_str with calling whisper.get_level_name with whisper.LOG_ERROR
        calling w_str with calling whisper.get_level_name with whisper.LOG_FATAL
        calling w_str with calling whisper.get_level_name with 99
    ''', "TRACE\nDEBUG\nINFO\nWARN\nERROR\nFATAL\nFATAL\n")


def test_get_level_color_returns_the_matching_ansi_escape():
    """Each severity maps to its documented ANSI escape byte for byte."""
    res = _run_main('''
        calling spark.println with calling whisper.get_level_color with whisper.LOG_TRACE
        calling spark.println with calling whisper.get_level_color with whisper.LOG_DEBUG
        calling spark.println with calling whisper.get_level_color with whisper.LOG_INFO
        calling spark.println with calling whisper.get_level_color with whisper.LOG_WARN
        calling spark.println with calling whisper.get_level_color with whisper.LOG_ERROR
        calling spark.println with calling whisper.get_level_color with whisper.LOG_FATAL
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "\x1b[90m\n\x1b[36m\n\x1b[32m\n\x1b[33m\n\x1b[31m\n\x1b[91m\n"
    )


def test_get_level_color_unknown_level_falls_back_to_bright_red():
    """An out-of-range level id is coloured as FATAL / bright red."""
    res = _run_main(
        'calling spark.println with calling whisper.get_level_color with 99'
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout == "\x1b[91m\n"


def test_log_levels_are_named_in_severity_order():
    """``log_levels`` lists the six lowercase names in increasing severity."""
    _check('''
        var names as list of string is calling whisper.log_levels
        for n in names:
            calling w_str with n
        banish names
    ''', "trace\ndebug\ninfo\nwarn\nerror\nfatal\n")


# ---------------------------------------------------------------------------
# Global level configuration
# ---------------------------------------------------------------------------

def test_global_get_level_and_is_enabled():
    """``set_level`` drives both ``get_level`` and ``is_enabled``."""
    _check('''
        calling whisper.set_level with whisper.LOG_ERROR
        calling w_int with calling whisper.get_level
        calling w_bool with calling whisper.is_enabled with whisper.LOG_WARN
        calling w_bool with calling whisper.is_enabled with whisper.LOG_FATAL
    ''', "4\nfalse\ntrue\n")


def test_set_default_level_changes_the_env_fallback():
    """``set_default_level`` changes what ``get_default_level`` reports."""
    _check('''
        calling w_int with calling whisper.get_default_level
        calling whisper.set_default_level with whisper.LOG_WARN
        calling w_int with calling whisper.get_default_level
    ''', "2\n3\n")


def test_parse_level_string_is_case_insensitive():
    """``parse_level_string`` accepts names (and ``warning``) regardless of case."""
    _check('''
        var a as maybe int is calling whisper.parse_level_string with "WARNING"
        calling w_int with (a or else -1)
        var b as maybe int is calling whisper.parse_level_string with "FaTaL"
        calling w_int with (b or else -1)
        var c as maybe int is calling whisper.parse_level_string with "nope"
        calling w_int with (c or else -1)
    ''', "3\n5\n-1\n")


def test_set_level_from_string_applies_known_and_rejects_unknown():
    """A recognised name is applied and reported; an unknown one leaves the level."""
    _check('''
        calling w_bool with calling whisper.set_level_from_string with "error"
        calling w_int with calling whisper.get_level
        calling w_bool with calling whisper.set_level_from_string with "nope"
        calling w_int with calling whisper.get_level
    ''', "true\n4\nfalse\n4\n")


# ---------------------------------------------------------------------------
# Global functional logger
# ---------------------------------------------------------------------------

def test_global_helpers_emit_every_level():
    """``trace``..``fatal`` each emit one line named for their severity."""
    _check('''
        calling whisper.set_level with whisper.LOG_TRACE
        calling whisper.trace with "t"
        calling whisper.debug with "d"
        calling whisper.info with "i"
        calling whisper.warn with "w"
        calling whisper.error with "e"
        calling whisper.fatal with "f"
    ''', "[TRACE] t\n[DEBUG] d\n[INFO] i\n[WARN] w\n[ERROR] e\n[FATAL] f\n")


def test_global_set_level_suppresses_lower_levels():
    """Messages below the active minimum are dropped, not merely recoloured."""
    _check('''
        calling whisper.set_level with whisper.LOG_WARN
        calling whisper.info with "no"
        calling whisper.warn with "yes"
        calling whisper.error with "also"
    ''', "[WARN] yes\n[ERROR] also\n")


def test_global_log_emits_at_the_requested_level():
    """``log`` takes an explicit severity and emits above the minimum."""
    _check('''
        calling whisper.set_level with whisper.LOG_TRACE
        calling whisper.log with whisper.LOG_WARN, "explicit"
    ''', "[WARN] explicit\n")


def test_colorize_wraps_with_level_colour_and_reset():
    """``colorize`` brackets the message with the level colour and a reset."""
    res = _run_main(
        'calling spark.println with calling whisper.colorize with whisper.LOG_WARN, "msg"'
    )
    assert res.returncode == 0, res.stderr
    assert res.stdout == "\x1b[33mmsg\x1b[0m\n"


def test_global_helpers_colour_stdout():
    """A colourised global line carries real ANSI escapes and a trailing reset."""
    res = _run_main('''
        calling whisper.set_level with whisper.LOG_TRACE
        calling whisper.info with "hello"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "\x1b[32m[INFO] hello\x1b[0m\n"


def test_fatal_and_exit_uses_the_given_status():
    """``fatal_and_exit`` emits FATAL, flushes and terminates with ``code``."""
    res = _run_main('calling whisper.fatal_and_exit with "bang", 3')
    assert res.returncode == 3
    assert strip_ansi(res.stdout) == "[FATAL] bang\n"


def test_json_escape_public_escapes_quotes():
    """``json_escape_public`` escapes a double quote and leaves the rest intact."""
    # The quote is written as a source escape rather than ``(chr 34)``: the
    # compiler constant-folds ``chr 34`` into a raw ``"`` inside the generated C
    # string literal and the build fails before the program ever runs.
    res = _run_main('''
        var q as string is "a\\"b"
        calling spark.println with calling whisper.json_escape_public with q
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == 'a\\"b\n'


# ---------------------------------------------------------------------------
# Global JSON logging
# ---------------------------------------------------------------------------

def test_global_log_json_always_includes_a_timestamp():
    """The module-level ``log_json`` always adds an ISO ``"time"`` member."""
    res = _run_main('''
        var f as map of string to string is map of string to string
        calling whisper.log_json with whisper.LOG_INFO, "hi", f
    ''')
    assert res.returncode == 0, res.stderr
    doc = json.loads(res.stdout.strip())
    assert doc["level"] == "INFO" and doc["msg"] == "hi"
    assert "T" in doc["time"] and doc["time"].endswith("Z")


def test_global_log_json_sorts_field_keys():
    """Field keys are emitted in sorted order regardless of insertion order."""
    res = _run_main('''
        var f as map of string to string is map of string to string
        with f:
            calling .put with "zeta", "1"
            calling .put with "alpha", "2"
            calling .put with "mid", "3"
        calling whisper.log_json with whisper.LOG_INFO, "hi", f
    ''')
    assert res.returncode == 0, res.stderr
    line = res.stdout.strip()
    assert line.index('"alpha"') < line.index('"mid"') < line.index('"zeta"')
    doc = json.loads(line)
    assert doc["alpha"] == "2" and doc["mid"] == "3" and doc["zeta"] == "1"


# ---------------------------------------------------------------------------
# The Logger rune: construction and identity
# ---------------------------------------------------------------------------

def test_logger_new_starts_at_trace_and_carries_its_name():
    """``Logger.new`` starts at TRACE and keeps the given name."""
    _check('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling w_str with calling log.get_name
        calling w_int with calling log.get_level
        calling log.trace with "deep"
    ''', "app\n0\n[TRACE] [app] deep\n")


def test_logger_named_sets_its_minimum_level():
    """``Logger.named`` fixes the minimum level at construction time."""
    _check('''
        var log as whisper.Logger is calling Logger.named with "app", whisper.LOG_WARN
        calling log.debug with "no"
        calling log.warn with "yes"
    ''', "[WARN] [app] yes\n")


def test_default_and_named_logger_are_named_singletons():
    """``default_logger``/``named_logger`` return loggers with those names."""
    _check('''
        var d as whisper.Logger is calling default_logger
        calling w_str with calling d.get_name
        var n as whisper.Logger is calling named_logger with "svc"
        calling w_str with calling n.get_name
    ''', "default\nsvc\n")


def test_logger_from_env_uses_the_default_level_when_clean():
    """With no level variable set, ``Logger.from_env`` uses the default (INFO)."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.from_env
        calling w_str with calling log.get_name
        calling w_int with calling log.get_level
    ''', env=_env_without_levels())
    assert res.returncode == 0, res.stderr
    assert res.stdout == "default\n2\n"


def test_logger_from_env_reads_a_valid_level_variable():
    """A valid ``WHISPER_LOG`` value is honoured by ``Logger.from_env``."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.from_env
        calling w_int with calling log.get_level
    ''', env=_env_without_levels(WHISPER_LOG="warn"))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "3\n"


def test_logger_set_level_from_env_publishes_to_the_registry():
    """``Logger.set_level_from_env`` also updates the singleton registry entry."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.get_or_create with "app"
        calling log.set_level_from_env
        calling w_int with calling log.get_level
        var other as whisper.Logger is calling Logger.get_or_create with "app"
        calling w_int with calling other.get_level
    ''', env=_env_without_levels(LOG_LEVEL="error"))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "4\n4\n"


# ---------------------------------------------------------------------------
# The Logger rune: level, colour, timestamps, destination
# ---------------------------------------------------------------------------

def test_logger_set_level_changes_only_that_logger():
    """A logger's level is independent of both the global level and other loggers."""
    _check('''
        var a as whisper.Logger is calling Logger.new with "a"
        var b as whisper.Logger is calling Logger.new with "b"
        calling a.set_level with whisper.LOG_ERROR
        calling w_int with calling a.get_level
        calling w_int with calling b.get_level
        calling a.warn with "hidden"
        calling b.warn with "shown"
    ''', "4\n0\n[WARN] [b] shown\n")


def test_logger_is_enabled_respects_its_minimum():
    """``Logger.is_enabled`` compares against that logger's own minimum."""
    _check('''
        var log as whisper.Logger is calling Logger.named with "app", whisper.LOG_WARN
        calling w_bool with calling log.is_enabled with whisper.LOG_DEBUG
        calling w_bool with calling log.is_enabled with whisper.LOG_WARN
        calling w_bool with calling log.is_enabled with whisper.LOG_FATAL
    ''', "false\ntrue\ntrue\n")


def test_logger_level_helpers_cover_all_six():
    """``trace``..``fatal`` on a ``Logger`` name the logger and the severity."""
    _check('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.trace with "t"
        calling log.debug with "d"
        calling log.info with "i"
        calling log.warn with "w"
        calling log.error with "e"
        calling log.fatal with "f"
    ''', (
        "[TRACE] [app] t\n[DEBUG] [app] d\n[INFO] [app] i\n"
        "[WARN] [app] w\n[ERROR] [app] e\n[FATAL] [app] f\n"
    ))


def test_logger_log_emits_at_the_requested_level():
    """``Logger.log`` takes an explicit severity and formats it normally."""
    _check('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.log with whisper.LOG_ERROR, "boom"
    ''', "[ERROR] [app] boom\n")


def test_logger_color_can_be_toggled():
    """``disable_color`` emits plain text; ``enable_color`` restores the escapes."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.info with "plain"
        calling log.enable_color
        calling log.info with "colour"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == (
        "[INFO] [app] plain\n\x1b[32m[INFO] [app] colour\x1b[0m\n"
    )


def test_logger_timestamp_toggle():
    """``enable_timestamp``/``disable_timestamp`` add and remove the ISO prefix."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.info with "bare"
        calling log.enable_timestamp
        calling log.info with "stamped"
        calling log.disable_timestamp
        calling log.info with "bare2"
    ''')
    assert res.returncode == 0, res.stderr
    lines = res.stdout.splitlines()
    assert lines[0] == "[INFO] [app] bare"
    assert lines[1].endswith("] [INFO] [app] stamped") and "T" in lines[1]
    assert lines[2] == "[INFO] [app] bare2"


def test_logger_get_timestamp_is_iso8601_utc():
    """``Logger.get_timestamp`` returns an ISO-8601 UTC instant."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling spark.println with calling log.get_timestamp
    ''')
    assert res.returncode == 0, res.stderr
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                        res.stdout.strip())


def test_bug19_to_stderr_writes_to_stderr_not_stdout():
    """Regression B19: ``to_stderr`` redirects the logger to file descriptor 2."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.to_stderr
        calling log.info with "to-err"
    ''')
    assert res.returncode == 0, res.stderr
    assert "to-err" not in res.stdout
    assert "[INFO] [app] to-err" in res.stderr


def test_logger_to_stdout_restores_stdout():
    """``to_stdout`` moves a logger back from stderr, keeping the streams apart."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.to_stderr
        calling log.info with "err"
        calling log.to_stdout
        calling log.info with "out"
    ''')
    assert res.returncode == 0, res.stderr
    assert "out" in res.stdout and "err" not in res.stdout
    assert "err" in res.stderr and "out" not in res.stderr


def test_logger_destination_queries(tmp_path):
    """``is_file_mode``/``is_stderr_mode`` report the active destination."""
    # The path is never logged to, so the file is not created; only the query
    # is under test.
    res = _run_main('''
        var path as string is calling rites.arg_at_or with 1, ""
        var log as whisper.Logger is calling Logger.new with "app"
        calling w_bool with calling log.is_file_mode
        calling w_bool with calling log.is_stderr_mode
        calling log.to_stderr
        calling w_bool with calling log.is_stderr_mode
        calling log.to_file with path
        calling w_bool with calling log.is_file_mode
        calling w_bool with calling log.is_stderr_mode
    ''', str(tmp_path / "unused.log"))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "false\nfalse\ntrue\ntrue\nfalse\n"
    assert not (tmp_path / "unused.log").exists()


def test_logger_flush_keeps_output_order():
    """``flush`` passes buffered lines through without changing their stream."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.disable_color
        calling log.info with "before"
        calling log.flush
        calling log.to_stderr
        calling log.info with "after"
    ''')
    assert res.returncode == 0, res.stderr
    assert res.stdout == "[INFO] [app] before\n"
    assert "[INFO] [app] after" in res.stderr


# ---------------------------------------------------------------------------
# The Logger rune: files, formats and structured context
# ---------------------------------------------------------------------------

def test_bug13_file_output_is_plain_despite_colour(tmp_path):
    """Regression B13: a file never receives ANSI escapes, even with colour on."""
    out = tmp_path / "plain.log"
    res = _run_main('''
        var path as string is calling rites.arg_at_or with 1, ""
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.to_file with path
        calling log.info with "plain"
    ''', str(out))
    assert res.returncode == 0, res.stderr
    content = out.read_text(encoding="utf-8")
    assert content == "[INFO] [app] plain\n"
    assert "\x1b[" not in content
    assert "plain" not in res.stdout


def test_bug12_child_preserves_file_path(tmp_path):
    """Regression B12: a child logger keeps writing to the parent's file."""
    out = tmp_path / "child.log"
    res = _run_main('''
        var path as string is calling rites.arg_at_or with 1, ""
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.to_file with path
        var kid as whisper.Logger is calling log.child with "db"
        calling kid.info with "from-child"
    ''', str(out))
    assert res.returncode == 0, res.stderr
    content = out.read_text(encoding="utf-8")
    assert "from-child" in content
    assert "[app.db]" in content
    assert "from-child" not in res.stdout


def test_bug24_custom_format_is_used(tmp_path):
    """Regression B24: ``set_format`` controls the text layout, file included."""
    out = tmp_path / "fmt.log"
    res = _run_main('''
        var path as string is calling rites.arg_at_or with 1, ""
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.set_format with r"{level}|{msg}"
        calling log.to_file with path
        calling log.info with "hello"
    ''', str(out))
    assert res.returncode == 0, res.stderr
    assert out.read_text(encoding="utf-8") == "INFO|hello\n"
    assert res.stdout == ""


def test_bug21_file_failure_is_reported_and_does_not_abort(tmp_path):
    """Regression B21: an unwritable file is reported on stderr, exit stays 0."""
    bad = tmp_path / "no-such-dir" / "out.log"
    res = _run_main('''
        var path as string is calling rites.arg_at_or with 1, ""
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.to_file with path
        calling log.info with "nope"
        calling spark.println with "alive"
    ''', str(bad))
    assert res.returncode == 0
    assert "alive" in res.stdout
    assert "cannot append" in res.stderr
    assert not bad.exists()


def test_bug23_child_sanitises_names():
    """Regression B23: an empty segment keeps the parent name, bad bytes become ``_``."""
    _check('''
        var log as whisper.Logger is calling Logger.new with "app"
        var empty as whisper.Logger is calling log.child with ""
        calling w_str with calling empty.get_name
        var spaced as whisper.Logger is calling log.child with "a b"
        calling w_str with calling spaced.get_name
        var kept as whisper.Logger is calling log.child with "db-1.2"
        calling w_str with calling kept.get_name
    ''', "app\napp.a_b\napp.db-1.2\n")


def test_logger_with_field_and_context_merge_into_json():
    """``with_field``/``with_context`` members appear in a JSON line."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        var ctx as map of string to string is map of string to string
        with ctx:
            calling .put with "pid", "42"
        var withctx as whisper.Logger is calling log.with_context with ctx
        var withfield as whisper.Logger is calling withctx.with_field with "k", "v"
        var f as map of string to string is map of string to string
        calling withfield.log_json with whisper.LOG_INFO, "hi", f
    ''')
    assert res.returncode == 0, res.stderr
    doc = json.loads(res.stdout.strip())
    assert doc["logger"] == "app" and doc["msg"] == "hi"
    assert doc["pid"] == "42" and doc["k"] == "v"


def test_logger_log_json_ex_controls_the_timestamp():
    """``log_json_ex`` adds ``"time"`` only when asked, unlike ``log_json``."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        var f as map of string to string is map of string to string
        calling log.log_json_ex with whisper.LOG_INFO, "a", f, false
        calling log.log_json_ex with whisper.LOG_INFO, "b", f, true
    ''')
    assert res.returncode == 0, res.stderr
    lines = res.stdout.strip().splitlines()
    assert '"time"' not in lines[0]
    assert '"time"' in lines[1] and "T" in lines[1]


# ---------------------------------------------------------------------------
# Regressions B14-B18 (escaping, JSON timestamp/order, environment)
# ---------------------------------------------------------------------------

def test_bug14_json_escape_escapes_control_bytes():
    """Regression B14: ``\\b`` and ``\\f`` are escaped, no raw control byte leaks."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        var m as string is "a{(chr 8)}b{(chr 12)}c"
        var f as map of string to string is map of string to string
        calling log.log_json with whisper.LOG_INFO, m, f
    ''')
    assert res.returncode == 0, res.stderr
    assert "\\b" in res.stdout and "\\f" in res.stdout
    assert "\x08" not in res.stdout and "\x0c" not in res.stdout
    # The JSON is still valid and round-trips to the original message.
    assert json.loads(res.stdout.strip())["msg"] == "a\bb\fc"


def test_bug15_log_json_includes_a_timestamp():
    """Regression B15: ``enable_timestamp`` makes ``log_json`` carry ``"time"``."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        calling log.enable_timestamp
        var f as map of string to string is map of string to string
        calling log.log_json with whisper.LOG_INFO, "hi", f
    ''')
    assert res.returncode == 0, res.stderr
    assert '"time":"' in res.stdout
    doc = json.loads(res.stdout.strip())
    assert "T" in doc["time"] and doc["time"].endswith("Z")


def test_bug16_log_json_field_order_is_deterministic():
    """Regression B16: field keys are sorted, not left in hash-map order."""
    res = _run_main('''
        var log as whisper.Logger is calling Logger.new with "app"
        var f as map of string to string is map of string to string
        with f:
            calling .put with "zeta", "1"
            calling .put with "alpha", "2"
            calling .put with "mid", "3"
        calling log.log_json with whisper.LOG_INFO, "hi", f
    ''')
    assert res.returncode == 0, res.stderr
    line = res.stdout.strip()
    assert line.index('"alpha"') < line.index('"mid"') < line.index('"zeta"')
    doc = json.loads(line)
    fields = [k for k in doc if k not in ("level", "logger", "msg", "time")]
    assert fields == ["alpha", "mid", "zeta"]


def test_bug17_invalid_env_level_warns_and_falls_back():
    """Regression B17: an unknown level variable warns and falls back to the default."""
    res = _run_main('''
        calling whisper.set_level_from_env
        calling w_int with calling whisper.get_level
        calling whisper.debug with "hidden"
        calling whisper.info with "shown"
    ''', env=_env_without_levels(WHISPER_LOG="nonsense"))
    assert res.returncode == 0, res.stderr
    assert res.stdout.splitlines()[0].strip() == "2"
    assert "shown" in res.stdout and "hidden" not in res.stdout
    assert 'ignoring invalid WHISPER_LOG="nonsense"' in res.stderr


def test_bug18_set_level_from_env_defaults_to_info():
    """Regression B18: with no variable set, ``set_level_from_env`` selects INFO."""
    res = _run_main('''
        calling whisper.set_level_from_env
        calling w_int with calling whisper.get_level
        calling whisper.debug with "hidden"
        calling whisper.info with "shown"
    ''', env=_env_without_levels())
    assert res.returncode == 0, res.stderr
    assert res.stdout.splitlines()[0].strip() == "2"
    assert "shown" in res.stdout and "hidden" not in res.stdout
    assert "ignoring invalid" not in res.stderr


def test_bug20_get_or_create_shares_one_level():
    """Regression B20: two ``get_or_create`` values for one name are the same logger."""
    _check('''
        var first as whisper.Logger is calling Logger.get_or_create with "app"
        calling first.set_level with whisper.LOG_ERROR
        var second as whisper.Logger is calling Logger.get_or_create with "app"
        calling w_int with calling second.get_level
        calling w_str with calling second.get_name
    ''', "4\napp\n")


def test_valid_env_var_wins_over_invalid_one():
    """The first valid level variable wins even when an earlier one is invalid."""
    res = _run_main('''
        calling whisper.set_level_from_env
        calling w_int with calling whisper.get_level
    ''', env=_env_without_levels(LOG_LEVEL="bogus", RUST_LOG="debug"))
    assert res.returncode == 0, res.stderr
    assert res.stdout == "1\n"
    assert 'ignoring invalid LOG_LEVEL="bogus"' in res.stderr


def test_program_stderr_is_free_of_whisper_noise_on_clean_run():
    """A clean run adds nothing to stderr beyond the CLI's own build notice."""
    res = _run_main('''
        calling whisper.set_level with whisper.LOG_TRACE
        calling whisper.info with "quiet"
    ''')
    assert res.returncode == 0, res.stderr
    assert _cli_noise_free(res.stderr).strip() == ""
    assert strip_ansi(res.stdout) == "[INFO] quiet\n"
