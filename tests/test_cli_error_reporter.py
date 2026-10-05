"""Phase 4 item 4.8 (A6): script paths report errors, never tracebacks.

The five script-oriented commands reached the compiler directly without an edge
handler, so a syntax error in the user's file escaped as a Python traceback
(measured: `pengu run roto.pengu` → 33 lines of stderr, `Traceback (most recent
call first)`). Roadmap C4 states no user input may produce a traceback.

Each command now routes user-input errors through `report_pengu_error()`, which
prints one `file:line:col [code] message` diagnostic (plus `help`/`note` when the
error carries them) and exits non-zero.
"""

import os
import subprocess
import sys

import pytest

from tests.conftest import REPO

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

BROKEN = "weave main into int:\n    var x as int is\n    return 0\n"


def _run(args, cwd=None, timeout=120):
    env = dict(os.environ, NO_COLOR="1")
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=timeout,
        cwd=str(cwd) if cwd else None, env=env,
    )


@pytest.fixture()
def broken(tmp_path):
    path = tmp_path / "roto.pengu"
    path.write_text(BROKEN, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The five script paths: a diagnostic, no traceback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", ["run", "expand", "time"])
def test_script_commands_report_instead_of_crashing(broken, command):
    res = _run([command, str(broken)])
    assert res.returncode != 0
    assert "Traceback" not in res.stderr, res.stderr
    assert "Traceback" not in res.stdout
    assert "E0000" in res.stderr, res.stderr
    assert "Syntax error" in res.stderr, res.stderr
    assert f"{broken.name}:3:5" in res.stderr or ":3:" in res.stderr, res.stderr


def test_watch_reports_instead_of_crashing(broken):
    res = _run(["watch", str(broken)], timeout=120)
    assert res.returncode != 0
    assert "Traceback" not in res.stderr, res.stderr
    assert "E0000" in res.stderr, res.stderr


def test_eval_reports_instead_of_crashing():
    res = _run(["eval", "1 +"])
    assert res.returncode != 0
    assert "Traceback" not in res.stderr, res.stderr
    assert "E0000" in res.stderr, res.stderr


def test_missing_script_reports_instead_of_crashing(tmp_path):
    """A missing file is not a `PenguError` but is still user input."""
    res = _run(["run", str(tmp_path / "noexiste.pengu")])
    assert res.returncode != 0
    assert "Traceback" not in res.stderr, res.stderr
    assert "not found" in res.stderr.lower(), res.stderr


# ---------------------------------------------------------------------------
# The happy paths still work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command,args_after", [
    ("run", []),
    ("expand", []),
    ("time", []),
])
def test_valid_script_still_works(tmp_path, command, args_after):
    script = tmp_path / "bueno.pengu"
    script.write_text('weave main into int:\n    calling print with "ok"\n    return 0\n',
                      encoding="utf-8")
    res = _run([command, str(script), *args_after])
    assert res.returncode == 0, res.stderr


def test_valid_eval_still_works():
    res = _run(["eval", "2 + 3"])
    assert res.returncode == 0, res.stderr
    assert "5" in res.stdout


# ---------------------------------------------------------------------------
# The reporter contract (unit level)
# ---------------------------------------------------------------------------


def test_report_pengu_error_formats_and_returns_nonzero(capsys):
    import pengu_project as pp

    class FakeError(Exception):
        code = "E0000"
        line = 7
        column = 3
        message = "Syntax error: boom"
        help = "check the docs"
        note = "indentation matters"

    rc = pp.report_pengu_error(FakeError(), source="x.pengu")
    assert rc == 1
    err = capsys.readouterr().err
    assert "x.pengu:7:3 [E0000] Syntax error: boom" in err
    assert "help: check the docs" in err
    assert "note: indentation matters" in err


def test_report_pengu_error_json_lines(capsys):
    import json as _json

    import pengu_project as pp

    class FakeError(Exception):
        code = "E0000"
        line = 2
        column = 1
        message = "Syntax error: boom"

    rc = pp.report_pengu_error(FakeError(), json_output=True, source="x.pengu")
    assert rc == 1
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 2
    diag = _json.loads(out[0])
    summary = _json.loads(out[1])
    assert diag["type"] == "diagnostic" and diag["file"] == "x.pengu"
    assert summary == {"type": "summary", "ok": False, "errors": 1, "warnings": 0}


def test_signal_termination_is_not_swallowed():
    """A process killed by a signal is 4.9's contract, not 4.8's.

    The reporter must not turn it into a generic user-input error: `eval "1/0"`
    still reports the crash and exits 136 (measured pre-4.8).
    """
    res = _run(["eval", "1/0"])
    assert res.returncode == 136, (res.returncode, res.stdout, res.stderr)
    assert "Traceback" not in res.stderr, res.stderr
