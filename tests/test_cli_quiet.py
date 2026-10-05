"""Phase 4 item 4.4: `--quiet` must suppress progress output.

`pengu --quiet build` printed the full banner before this item: the global
`-q/--quiet` flag was parsed but never read anywhere in the CLI. Progress lines
are now emitted with `level="progress"`, and `emit()` drops them when
`configure_output(quiet=True)` has been called. Errors and warnings always
print — `--quiet` reduces noise, it never hides a failure.

`--quiet` is accepted both as a global flag and after the subcommand.
"""

import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]


def _run(args, cwd=None):
    env = dict(os.environ, NO_COLOR="1")     # colour is item 4.5's contract
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=180,
        cwd=str(cwd) if cwd else None, env=env,
    )


@pytest.fixture()
def project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    return tmp_path / "ok"


@requires_cc
@requires_runtime
def test_quiet_build_prints_nothing_on_success(project):
    res = _run(["--quiet", "build"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "", res.stdout
    assert res.stderr == "", res.stderr


@requires_cc
@requires_runtime
def test_quiet_after_the_subcommand_too(project):
    res = _run(["build", "--quiet"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "", res.stdout
    res2 = _run(["-q", "build"], cwd=project)
    assert res2.stdout == "", res2.stdout


def test_quiet_check_success_prints_nothing(project):
    res = _run(["--quiet", "check"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert res.stdout == "", res.stdout


def test_quiet_does_not_hide_errors(project):
    broken = project / "broken.pengu"
    broken.write_text("weave main into int:\n    var x as int is\n", encoding="utf-8")
    res = _run(["--quiet", "check", str(broken)], cwd=project)
    assert res.returncode != 0
    combined = res.stdout + res.stderr
    assert "Syntax error" in combined, combined


def test_without_quiet_the_banner_is_printed(project):
    res = _run(["check"], cwd=project)
    assert res.returncode == 0, res.stderr
    assert "Checking" in res.stdout, res.stdout


def test_quiet_unit_contract(monkeypatch):
    """`emit(level="progress")` is dropped; errors and warnings are not."""
    import pengu_project as pp

    class _Sink:
        def __init__(self):
            self.chunks = []

        def write(self, text):
            self.chunks.append(text)

        def isatty(self):
            return False

    pp.configure_output(quiet=True)
    sink = _Sink()
    pp.emit("busy", level="progress", file=sink)
    pp.emit("boom", level="error", file=sink)
    pp.emit("careful", level="warning", file=sink)
    assert sink.chunks == ["boom\n", "careful\n"]

    pp.configure_output(quiet=False)
    sink2 = _Sink()
    pp.emit("busy", level="progress", file=sink2)
    assert sink2.chunks == ["busy\n"]

    pp.configure_output()   # restore process defaults
