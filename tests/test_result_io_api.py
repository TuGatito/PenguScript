"""Roadmap Phase 4 / §4.4 (scoped) — Result-based I/O alongside maybe/bool.

Full stdlib migration to `Result` is a breaking change and is deferred (the
audit calls it the riskiest item of the phase).  What is implemented here is the
non-breaking foundation: `std.archivum` gains `read_file_result`,
`write_file_result` and `delete_file_result` returning
`result of T to IoError`, so a program can tell *why* an operation failed, while
the historical `maybe`/`bool` APIs keep working unchanged.
"""

import pytest

from tests.conftest import compile_run, requires_cc, requires_runtime

pytestmark = [requires_cc, requires_runtime]


def _run(body: str):
    src = "import std.archivum\n\nweave main into int:\n" + body
    return compile_run(src, tag="result_io")


def test_missing_file_reports_not_found():
    res = _run(
        '  var r as result of string to archivum.IoError is '
        'calling archivum.read_file_result with "/nonexistent/nope.txt"\n'
        "  if r.is_ok:\n"
        "    return 1\n"
        "  if r.error != archivum.IoError.NotFound:\n"
        "    return 2\n"
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_directory_reports_is_a_directory():
    res = _run(
        '  var r as result of string to archivum.IoError is '
        'calling archivum.read_file_result with "/tmp"\n'
        "  if r.is_ok:\n"
        "    return 1\n"
        "  if r.error != archivum.IoError.IsADirectory:\n"
        "    return 2\n"
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_write_then_read_round_trip():
    res = _run(
        '  var w as result of int to archivum.IoError is '
        'calling archivum.write_file_result with "/tmp/pengu_result_io.txt", "hello"\n'
        "  if not w.is_ok:\n"
        "    return 1\n"
        '  var r as result of string to archivum.IoError is '
        'calling archivum.read_file_result with "/tmp/pengu_result_io.txt"\n'
        "  if not r.is_ok:\n"
        "    return 2\n"
        '  if r.value != "hello":\n'
        "    return 3\n"
        '  var d as result of int to archivum.IoError is '
        'calling archivum.delete_file_result with "/tmp/pengu_result_io.txt"\n'
        "  if not d.is_ok:\n"
        "    return 4\n"
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_write_to_a_directory_fails_with_cause():
    res = _run(
        '  var w as result of int to archivum.IoError is '
        'calling archivum.write_file_result with "/tmp", "x"\n'
        "  if w.is_ok:\n"
        "    return 1\n"
        "  if w.error != archivum.IoError.IsADirectory:\n"
        "    return 2\n"
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_delete_missing_reports_not_found():
    res = _run(
        '  var d as result of int to archivum.IoError is '
        'calling archivum.delete_file_result with "/nonexistent/nope.txt"\n'
        "  if d.is_ok:\n"
        "    return 1\n"
        "  if d.error != archivum.IoError.NotFound:\n"
        "    return 2\n"
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_describe_error_is_human_readable():
    res = _run(
        '  var msg as string is calling archivum.describe_error with archivum.IoError.NotFound\n'
        '  if msg != "no such file or directory":\n'
        "    return 1\n"
        '  var p as string is calling archivum.describe_error with archivum.IoError.Permission\n'
        '  if p != "permission denied":\n'
        "    return 2\n"
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_legacy_maybe_api_is_unchanged():
    """Backward compatibility: the historical API still behaves the same."""
    res = _run(
        '  var legacy as maybe string is calling archivum.read_file with "/nonexistent/nope.txt"\n'
        "  if legacy.is_present:\n"
        "    return 1\n"
        '  var ok_legacy as bool is calling archivum.write_file with "/tmp/pengu_legacy_io.txt", "hi"\n'
        "  if not ok_legacy:\n"
        "    return 2\n"
        '  var back as maybe string is calling archivum.read_file with "/tmp/pengu_legacy_io.txt"\n'
        '  if (back or else "") != "hi":\n'
        "    return 3\n"
        '  calling archivum.delete_file with "/tmp/pengu_legacy_io.txt"\n'
        "  return 0\n"
    )
    assert res.returncode == 0, f"rc={res.returncode}\n{res.stderr}"


def test_result_api_is_documented_in_std():
    from tests.conftest import REPO

    text = (REPO / "std" / "archivum.pengu").read_text(encoding="utf-8")
    for symbol in ("omen IoError:", "read_file_result", "write_file_result",
                   "delete_file_result", "describe_error"):
        assert symbol in text
    # Decision D5 is spelled out next to the new API.
    assert "maybe" in text and "backwards compatibility" in text
