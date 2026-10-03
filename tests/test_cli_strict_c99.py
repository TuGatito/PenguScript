"""Roadmap Phase 2 / §2.1.h — `pengu build --strict-c99` and `--target-compiler`."""

import subprocess
import sys

import pytest

from tests.conftest import REPO


def _write_project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.pengu").write_text(
        "weave main into int:\n"
        "  var xs as list of int is [1, 2, 3]\n"
        "  var m as maybe int is some 7\n"
        "  var v as int is m or else 0\n"
        "  return v\n",
        encoding="utf-8",
    )
    (tmp_path / "pengu.yaml").write_text(
        "project:\n"
        "  name: strict_demo\n"
        "  entry: src/main.pengu\n"
        "build:\n"
        "  output: c\n",
        encoding="utf-8",
    )


def _run_build(tmp_path, *extra):
    cmd = [
        sys.executable, str(REPO / "pengu_project.py"), "build",
        "--config", str(tmp_path),
        "--output", str(tmp_path / "build" / "bundle.c"),
        *extra,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(tmp_path))


def test_cli_help_lists_phase2_flags():
    res = subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py"), "build", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert "--strict-c99" in res.stdout
    assert "--target-compiler" in res.stdout


def test_cli_strict_c99_emits_portable_c(tmp_path):
    _write_project(tmp_path)
    res = _run_build(tmp_path, "--strict-c99")
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"
    bundle = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    assert "__extension__" not in bundle
    assert "__auto_type" not in bundle


def test_cli_default_keeps_gnu_extensions(tmp_path):
    _write_project(tmp_path)
    res = _run_build(tmp_path)
    assert res.returncode == 0, f"build failed:\n{res.stdout}\n{res.stderr}"
    bundle = (tmp_path / "build" / "bundle.c").read_text(encoding="utf-8")
    # `or else` lowers to a statement expression by default.
    assert "__extension__" in bundle
