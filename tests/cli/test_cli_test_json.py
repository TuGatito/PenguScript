"""Phase 4 item 4.6 (A5): `pengu test --json` must emit JSON Lines on failure.

The JSON branch of `test_project` lived *after* `builder.compile()`, and only
`EntryPointNotFoundError` was caught, so a compilation error escaped as a Python
traceback with **zero** JSON lines on stdout — breaking the CI contract the flag
advertises. Measured before the fix: rc=1, stdout 0 lines, stderr 33 lines of
traceback.

The failure path now reports through the same edge the script commands use
(item 4.8): one `{"type":"diagnostic",...}` line plus
`{"type":"summary","ok":false,...}`.
"""

import json
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

BROKEN_MAIN = "weave main into int:\n    var y as int is\n    return 0\n"
OK_WITH_TEST = ('weave main into int:\n    return 0\n\n'
                'test "suma":\n'
                '    var a as int is 1 + 1\n'
                '    if a == 2:\n'
                '        return\n')


def _run(args, cwd=None):
    env = dict(os.environ, NO_COLOR="1")
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300,
        cwd=str(cwd) if cwd else None, env=env,
    )


@pytest.fixture()
def project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    return tmp_path / "ok"


def _json_lines(stdout):
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines], lines


@requires_cc
@requires_runtime
def test_json_emits_diagnostic_and_summary_on_compile_error(project):
    (project / "src" / "main.pengu").write_text(BROKEN_MAIN, encoding="utf-8")
    res = _run(["test", "--json"], cwd=project)
    assert res.returncode != 0
    assert "Traceback" not in res.stderr, res.stderr

    objects, lines = _json_lines(res.stdout)
    types = [o.get("type") for o in objects]
    assert "diagnostic" in types, lines
    assert "summary" in types, lines

    diag = next(o for o in objects if o.get("type") == "diagnostic")
    assert diag["severity"] == "error"
    assert diag["file"].endswith("main.pengu")
    assert diag["line"] == 3
    assert "Syntax error" in diag["message"]

    summary = next(o for o in objects if o.get("type") == "summary")
    assert summary["ok"] is False
    assert summary["errors"] >= 1


@requires_cc
@requires_runtime
def test_json_success_still_emits_events(project):
    (project / "src" / "main.pengu").write_text(OK_WITH_TEST, encoding="utf-8")
    res = _run(["test", "--json"], cwd=project)
    assert res.returncode == 0, res.stderr
    objects, lines = _json_lines(res.stdout)
    events = [o for o in objects if "event" in o]
    assert events, lines
    assert events[0]["event"] == "start"
    assert any(e["event"] == "test_pass" for e in events), lines
    assert events[-1]["event"] == "end"


@requires_cc
@requires_runtime
def test_plain_test_output_is_unchanged(project):
    (project / "src" / "main.pengu").write_text(OK_WITH_TEST, encoding="utf-8")
    res = _run(["test"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert "PASS" in res.stdout, res.stdout


def test_json_failure_is_valid_json_lines_unit(tmp_path, capsys):
    """The reporter fills the JSON contract with no compiler involved."""
    import pengu_project as pp

    class FakeError(Exception):
        code = "E0000"
        line = 4
        column = 2
        message = "Syntax error: boom"

    rc = pp.report_pengu_error(FakeError(), json_output=True, source="src/main.pengu")
    assert rc == 1
    out = capsys.readouterr().out
    objects, lines = _json_lines(out)
    assert [o["type"] for o in objects] == ["diagnostic", "summary"]
    assert objects[1]["ok"] is False
