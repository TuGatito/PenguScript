"""Roadmap Phase 3 / §3.6 — `pengu check --json` and `pengu build --json`.

CI needs machine-readable diagnostics: one JSON object per line with
``{file, line, col, code, severity, message, help, note}`` plus a final summary.
"""

import json
import subprocess
import sys

import pytest

from pengu_project import build_project, check_project
from tests.conftest import REPO

_CLEAN = "weave main into int:\n  return 0\n"
_BROKEN = (
    "weave main into int:\n"
    '  var x as int is "not an int"\n'
    "  return undefined_thing\n"
)


def _project(tmp_path, source):
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "main.pengu").write_text(source, encoding="utf-8")
    (tmp_path / "pengu.yaml").write_text(
        "project:\n  name: jsondemo\n  entry: src/main.pengu\n", encoding="utf-8"
    )
    return str(tmp_path)


def _json_lines(out: str):
    return [json.loads(ln) for ln in out.splitlines() if ln.strip().startswith("{")]


def test_check_json_clean(tmp_path, capsys):
    cfg = _project(tmp_path, _CLEAN)
    assert check_project(config_path=cfg, json_output=True) is True
    objs = _json_lines(capsys.readouterr().out)
    assert len(objs) == 1
    assert objs[0]["type"] == "summary"
    assert objs[0]["ok"] is True
    assert objs[0]["errors"] == 0


def test_check_json_broken(tmp_path, capsys):
    cfg = _project(tmp_path, _BROKEN)
    assert check_project(config_path=cfg, json_output=True) is False
    objs = _json_lines(capsys.readouterr().out)
    diags = [o for o in objs if o["type"] == "diagnostic"]
    assert diags, "expected at least one diagnostic"
    for d in diags:
        assert set(d) >= {"file", "line", "col", "code", "severity", "message", "help", "note"}
        assert d["severity"] == "error"
        assert d["code"].startswith("E")
        assert isinstance(d["line"], int) and isinstance(d["col"], int)
    assert diags[0]["code"] == "E0005"
    summary = [o for o in objs if o["type"] == "summary"][0]
    assert summary["ok"] is False and summary["errors"] == len(diags)


def test_check_json_stdout_is_pure_json(tmp_path, capsys):
    """No banner text must pollute stdout when --json is active."""
    cfg = _project(tmp_path, _CLEAN)
    check_project(config_path=cfg, json_output=True)
    out = capsys.readouterr().out
    for line in out.splitlines():
        if line.strip():
            json.loads(line)  # raises if any non-JSON line leaked


def test_build_json_clean(tmp_path, capsys):
    cfg = _project(tmp_path, _CLEAN)
    artifact = build_project(config_path=cfg, output=str(tmp_path / "b.c"), json_output=True)
    assert artifact.endswith("b.c")
    objs = _json_lines(capsys.readouterr().out)
    assert objs[-1]["type"] == "summary"
    assert objs[-1]["ok"] is True


def test_build_json_failure_exits_nonzero(tmp_path, capsys):
    cfg = _project(tmp_path, _BROKEN)
    with pytest.raises(SystemExit) as exc:
        build_project(config_path=cfg, json_output=True)
    assert exc.value.code == 1
    objs = _json_lines(capsys.readouterr().out)
    assert any(o["type"] == "diagnostic" and o["code"] == "E0005" for o in objs)
    assert any(o["type"] == "summary" and o["ok"] is False for o in objs)


def test_cli_exposes_json_flag():
    for cmd in ("check", "build"):
        res = subprocess.run(
            [sys.executable, str(REPO / "pengu_project.py"), cmd, "--help"],
            capture_output=True, text=True, timeout=60,
        )
        assert "--json" in res.stdout, f"{cmd} --help lacks --json"
