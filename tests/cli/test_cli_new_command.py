"""Phase 4 item 4.14: `pengu new <template> <name>`.

The roadmap asked for `pengu new` and `pengu migrate`. `new` is the priority
(it is the first thing a user types); `migrate` is deferred with a measurement
(no migration corpus exists yet — see the roadmap and CHANGELOG).

`pengu new` is the template-first spelling of `pengu init`: it reuses the same
templates (`exe`, `cli`, `lib`, `game`), so a new template cannot drift between
two code paths.
"""

import os
import subprocess
import sys

import pytest

from tests.conftest import REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]
TEMPLATES = ("exe", "cli", "lib", "game")


def _run(args, cwd=None):
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300,
        cwd=str(cwd) if cwd else None, env=dict(os.environ, NO_COLOR="1"),
    )


@pytest.mark.parametrize("template", TEMPLATES)
def test_new_creates_each_template(tmp_path, template):
    res = _run(["new", template, f"app_{template}"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    project = tmp_path / f"app_{template}"
    assert (project / "pengu.toml").is_file()
    source = sorted((project / "src").glob("*.pengu"))
    assert source, sorted(os.listdir(project / "src"))
    assert f'name = "app_{template}"' in (project / "pengu.toml").read_text(encoding="utf-8")


def test_new_lib_is_a_static_library_with_a_smoke_test(tmp_path):
    res = _run(["new", "lib", "mylib"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    manifest = (tmp_path / "mylib" / "pengu.toml").read_text(encoding="utf-8")
    assert 'output = "static"' in manifest
    body = "\n".join(p.read_text(encoding="utf-8")
                     for p in (tmp_path / "mylib" / "src").glob("*.pengu"))
    assert "test " in body, body


def test_matches_init_output_for_the_same_template(tmp_path):
    """`new` and `init --template` must produce the same tree (one code path)."""
    a = _run(["new", "cli", "via_new"], cwd=tmp_path)
    b = _run(["init", "via_init", "--template", "cli"], cwd=tmp_path)
    assert a.returncode == 0 and b.returncode == 0, (a.stderr, b.stderr)

    def tree(root):
        """Relative file paths, with the project name (the only difference)
        stripped from the first segment."""
        out = []
        for p in sorted(root.rglob("*")):
            if not p.is_file() or "build" in p.parts:
                continue
            parts = p.relative_to(root).parts[1:]      # drop the project dir
            out.append("/".join(parts))
        return out

    assert tree(tmp_path / "via_new") == tree(tmp_path / "via_init")


def test_new_requires_a_known_template(tmp_path):
    res = _run(["new", "nonsense", "x"], cwd=tmp_path)
    assert res.returncode == 2          # argparse rejects the choice
    assert "invalid choice" in res.stderr, res.stderr


@requires_cc
@requires_runtime
def test_new_exe_builds_and_runs(tmp_path):
    assert _run(["new", "exe", "runnable"], cwd=tmp_path).returncode == 0
    project = tmp_path / "runnable"
    build = _run(["build"], cwd=project)
    assert build.returncode == 0, build.stderr
    artifact = project / "build" / ("runnable.exe" if os.name == "nt" else "runnable")
    assert artifact.is_file(), sorted(os.listdir(project / "build"))
    run = subprocess.run([str(artifact)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert "runnable" in run.stdout


def test_new_is_documented_in_help():
    res = _run(["new", "--help"])
    assert res.returncode == 0, res.stderr
    assert "Exit codes" in res.stdout and "Example" in res.stdout
    assert "pengu new lib my_lib" in res.stdout


def test_migrate_is_not_claimed():
    """`migrate` is deferred, not silently absent: `--help` must not list it."""
    res = _run(["--help"])
    assert res.returncode == 0, res.stderr
    assert "migrate" not in res.stdout
