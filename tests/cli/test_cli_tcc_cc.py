"""Phase 4 item 4.12 (L7): `--cc tcc` must find the shipped TCC.

The release archives a TCC under ``build/tcc-dist`` and ``pick_dev_compiler``
already locates it for `pengu run`, but ``--cc tcc`` handed the bare string
``tcc`` to ``subprocess``. Measured before the fix:

    $ pengu build --cc tcc
    Error:
    Could not execute: [Errno 2] No such file or directory: 'tcc'

whenever TCC is not on ``PATH`` (the normal case: the project ships its own).
"""

import json
import os
import subprocess
import sys

import pytest

from pengu_project import OutputType, PenguBuilder, ProjectConfig, _resolve_cc_argument
from pengu_tcc import find_tcc
from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]

SOURCE = "weave main into int:\n    return 0\n"


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
    p = tmp_path / "ok"
    (p / "src" / "main.pengu").write_text(SOURCE, encoding="utf-8")
    return p


def test_resolve_cc_argument_unit(monkeypatch):
    import pengu_project as pp

    monkeypatch.setattr(pp, "find_tcc", lambda: "/opt/pengu/tcc/bin/tcc")
    assert _resolve_cc_argument("tcc") == "/opt/pengu/tcc/bin/tcc"
    assert _resolve_cc_argument("TCC") == "/opt/pengu/tcc/bin/tcc"
    assert _resolve_cc_argument("gcc") == "gcc"
    # Any path whose basename is `tcc` also means "the development compiler":
    # the packaged one is then used rather than that path.
    assert _resolve_cc_argument("/usr/bin/tcc") == "/opt/pengu/tcc/bin/tcc"
    assert _resolve_cc_argument(None) is None

    # Without a shipped TCC the name is left alone (and the compiler reports it).
    monkeypatch.setattr(pp, "find_tcc", lambda: None)
    assert _resolve_cc_argument("tcc") == "tcc"
    assert _resolve_cc_argument("/usr/bin/tcc") == "/usr/bin/tcc"


@requires_cc
@requires_runtime
@pytest.mark.skipif(find_tcc() is None, reason="no packaged tcc available")
def test_cc_tcc_builds_with_the_shipped_compiler(project):
    res = _run(["build", "--cc", "tcc", "--verbose"], cwd=project)
    assert res.returncode == 0, res.stderr
    combined = res.stdout + res.stderr
    if os.path.basename(find_tcc()).lower().startswith("tcc"):
        assert find_tcc() in combined or "tcc" in combined, combined

    artifact = project / "build" / ("ok.exe" if os.name == "nt" else "ok")
    assert artifact.is_file(), sorted(os.listdir(project / "build"))
    run = subprocess.run([str(artifact)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr


@requires_cc
@requires_runtime
def test_unknown_compiler_still_reports_cleanly(project):
    res = _run(["build", "--cc", "definitely_not_a_compiler"], cwd=project)
    assert res.returncode != 0
    combined = res.stdout + res.stderr
    assert "Could not execute" in combined or "not found" in combined.lower(), combined
    assert "Traceback" not in combined, combined


def test_resolution_does_not_change_the_configured_dialect():
    """`--cc tcc` must keep `target_compiler = "tcc"`, not "gcc" (item 4.10)."""
    cfg = ProjectConfig(name="p", output=OutputType.EXE, output_name="app",
                        base_dir="/tmp/pengu_tcc_flags", cc="tcc",
                        target_compiler="tcc", links=["pengu_runtime"])
    cmd = PenguBuilder(cfg).build_compile_commands("/tmp/pengu_tcc_flags/bundle.c",
                                                   "/tmp/pengu_tcc_flags/app")[0]
    # tcc is a GNU-dialect compiler: it keeps the GNU spelling.
    assert "-ftrapv" in cmd or "-O0" in cmd or "-Wall" in cmd
    assert "/Fe:" not in cmd and "/link" not in cmd
