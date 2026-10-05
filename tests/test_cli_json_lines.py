"""Phase 4 item 4.7: every `--json` command speaks JSON Lines.

`pengu tree --json` (and therefore `pengu metadata`) printed a **pretty-printed,
multi-line** object while `check`/`build`/`test` emit one object per line, so a
consumer could not parse stdout uniformly — the roadmap's contract is JSON Lines
for the five JSON commands.

These tests read the bytes each command writes and parse **every** line
independently: a pretty-printed object fails that, a JSON Lines stream passes.
"""

import json
import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]


def _run(args, cwd=None):
    env = dict(os.environ, NO_COLOR="1")
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300,
        cwd=str(cwd) if cwd else None, env=env,
    )


def _parse_lines(stdout):
    """Returns (objects, raw_lines); raises if any non-empty line is not JSON."""
    raw = [ln for ln in stdout.splitlines() if ln.strip()]
    return [json.loads(ln) for ln in raw], raw


@pytest.fixture()
def project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    return tmp_path / "ok"


@requires_cc
@requires_runtime
def test_tree_json_is_a_single_line(project):
    res = _run(["tree", "--json"], cwd=project)
    assert res.returncode == 0, res.stderr
    objects, raw = _parse_lines(res.stdout)
    assert len(raw) == 1, res.stdout
    assert objects[0]["type"] == "tree"
    assert objects[0]["project"] == "ok"
    assert "dependencies" in objects[0]
    assert "\n" not in res.stdout.strip()


@requires_cc
@requires_runtime
def test_metadata_is_a_single_json_line(project):
    """`pengu metadata` is JSON by definition, and one line of it."""
    res = _run(["metadata"], cwd=project)
    assert res.returncode == 0, res.stderr
    objects, raw = _parse_lines(res.stdout)
    assert len(raw) == 1, res.stdout
    assert objects[0]["project"] == "ok"


@requires_cc
@requires_runtime
def test_doctor_json_is_a_single_line(project):
    res = _run(["doctor", "--json"], cwd=project)
    objects, raw = _parse_lines(res.stdout)
    assert len(raw) == 1, res.stdout
    assert objects[0]["pengu"]


def test_gc_json_is_a_single_line(tmp_path):
    res = subprocess.run(
        [*PENGU, "gc", "--json"], capture_output=True, text=True, timeout=120,
        env=dict(os.environ, NO_COLOR="1", PENGU_CACHE=str(tmp_path / "cache")),
    )
    objects, raw = _parse_lines(res.stdout)
    assert len(raw) == 1, res.stdout
    assert "removed" in objects[0]


@requires_cc
@requires_runtime
def test_check_json_is_json_lines(project):
    res = _run(["check", "--json"], cwd=project)
    assert res.returncode == 0, res.stderr
    objects, _ = _parse_lines(res.stdout)
    assert any(o.get("type") == "summary" for o in objects), res.stdout


def test_build_json_is_json_lines(project):
    """`build --json` on a broken entry: diagnostics then a summary."""
    (project / "src" / "main.pengu").write_text(
        "weave main into int:\n    var y as int is\n    return 0\n", encoding="utf-8")
    res = _run(["build", "--json"], cwd=project)
    assert res.returncode != 0
    assert "Traceback" not in res.stderr, res.stderr
    objects, _ = _parse_lines(res.stdout)
    assert any(o.get("type") == "diagnostic" for o in objects), res.stdout
    assert any(o.get("type") == "summary" for o in objects), res.stdout
