#!/usr/bin/env python3
"""Tests for Phase 1 Task 3: pengu test --json and --watch flags."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from tests.conftest import (
    BUILD_DIR,
    REPO,
    requires_cc,
    requires_runtime,
)

PY = sys.executable
PROJECT_SCRIPT = str(REPO / "pengu_project.py")


def cli(args, cwd=None, timeout=120):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
    return subprocess.run(
        [PY, PROJECT_SCRIPT] + list(args),
        cwd=cwd or REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture()
def proj_dir():
    d = tempfile.mkdtemp(prefix="test_runner_proj_", dir=BUILD_DIR)
    try:
        # Create minimal pengu.yaml and src/main.pengu
        src = Path(d) / "src"
        src.mkdir(parents=True, exist_ok=True)
        (Path(d) / "pengu.yaml").write_text(
            "name: testrunner_app\nversion: 0.1.0\nentry: src/main.pengu\n",
            encoding="utf-8"
        )
        yield Path(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_test_watch_flag_parses():
    """pengu test --help must list --watch and --json flags without error."""
    res = cli(["test", "--help"])
    assert res.returncode == 0
    assert "--watch" in res.stdout
    assert "--json" in res.stdout


@requires_cc
@requires_runtime
def test_test_json_output_parses(proj_dir):
    """pengu test --json must emit valid JSON Lines events."""
    main_pengu = proj_dir / "src" / "main.pengu"
    main_pengu.write_text(
        """
weave main into int:
    return 0

test "arithmetic":
    var a as int is 1 + 2

test "strings":
    var s as string is "hello"
""",
        encoding="utf-8"
    )

    res = cli(["test", "--json"], cwd=proj_dir)
    assert res.returncode == 0, f"pengu test failed: {res.stderr}\n{res.stdout}"

    lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    types = [e["event"] for e in events]
    assert types == ["start", "test_start", "test_pass", "test_start", "test_pass", "end"]
    start_ev = events[0]
    assert start_ev["total"] == 2
    end_ev = events[-1]
    assert end_ev["total"] == 2
    assert end_ev["passed"] == 2
    assert end_ev["failed"] == 0


@requires_cc
@requires_runtime
def test_test_json_failure(proj_dir):
    """Crashing test under --json must emit test_start without test_pass and return non-zero exit."""
    main_pengu = proj_dir / "src" / "main.pengu"
    main_pengu.write_text(
        """
weave main into int:
    return 0

test "good":
    var a as int is 1

test "crashing":
    var xs as array of int with size 2 is [1, 2]
    var y as int is xs at 10
""",
        encoding="utf-8"
    )

    res = cli(["test", "--json"], cwd=proj_dir)
    assert res.returncode != 0

    lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    types = [e["event"] for e in events]

    assert "start" in types
    assert "test_start" in types
    # Last test_start was "crashing" and does not have a corresponding test_pass
    last_test_start = [e for e in events if e["event"] == "test_start"][-1]
    assert last_test_start["name"] == "crashing"
    passed_names = [e["name"] for e in events if e["event"] == "test_pass"]
    assert "crashing" not in passed_names


@requires_cc
@requires_runtime
def test_json_escapes_quotes(proj_dir):
    """Test names with quotes must produce valid escaped JSON lines."""
    main_pengu = proj_dir / "src" / "main.pengu"
    main_pengu.write_text(
        """
weave main into int:
    return 0

test "quote \\"test\\" check":
    var a as int is 42
""",
        encoding="utf-8"
    )

    res = cli(["test", "--json"], cwd=proj_dir)
    assert res.returncode == 0, f"pengu test failed: {res.stderr}\n{res.stdout}"

    lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    events = [json.loads(line) for line in lines]
    types = [e["event"] for e in events]
    assert "start" in types
    assert "test_start" in types
    assert "test_pass" in types
    assert "end" in types
    names = [e["name"] for e in events if "name" in e]
    assert any("test" in n for n in names)
