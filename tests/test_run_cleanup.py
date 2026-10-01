"""``pengu run`` must not litter the project tree or /tmp.

The default run builds in a throw-away directory and stores the binary in the
global cache; ``--keep`` restores the historical ``build/<name>_run/`` layout and
``--ephemeral`` promises to leave no trace at all.  These tests pin those three
promises down, including the temp-directory cleanup on the failure paths.
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
import tempfile

import pytest

from pengu_cache import script_binary_name
from tests.conftest import REPO, requires_cc, requires_runtime

pytestmark = [requires_cc, requires_runtime]

HELLO = '''import std.spark

weave main into int:
    calling spark.println with "cleanup hello"
    return 0
'''


def _cli(args, cwd, cache_dir, timeout=300, env_extra=None):
    env = dict(os.environ)
    env["PENGU_CACHE_DIR"] = str(cache_dir)
    env.pop("PENGU_CACHE", None)
    env.pop("PENGU_NO_DCE", None)
    env.pop("PENGU_DEV_CC", None)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(REPO / "pengu_project.py")] + args,
        cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env,
    )


@pytest.fixture(scope="module")
def cache_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("cleanup-cache")


@pytest.fixture()
def sandbox(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    script = work / "hello.pengu"
    script.write_text(HELLO, encoding="utf-8")
    return {"work": work, "script": script}


def _leftover_temp_dirs(tag: str = "pengu_run_") -> set:
    return set(glob.glob(os.path.join(tempfile.gettempdir(), tag + "*")))


def test_default_run_does_not_create_build_dir(sandbox, cache_dir):
    work, script = sandbox["work"], sandbox["script"]
    before = _leftover_temp_dirs()
    res = _cli(["run", str(script), "--quiet"], work, cache_dir)
    assert res.returncode == 0, res.stderr
    assert "cleanup hello" in res.stdout
    assert not (work / "build").exists(), "the default run must not write build/"
    assert _leftover_temp_dirs() == before, "the throw-away build directory must be removed"


def test_default_run_with_script_args_is_still_clean(sandbox, cache_dir):
    work, script = sandbox["work"], sandbox["script"]
    before = _leftover_temp_dirs()
    res = _cli(["run", str(script), "--quiet", "--", "one", "two"], work, cache_dir)
    assert res.returncode == 0, res.stderr
    assert not (work / "build").exists()
    assert _leftover_temp_dirs() == before


def test_keep_writes_bundle_c(sandbox, cache_dir):
    work, script = sandbox["work"], sandbox["script"]
    res = _cli(["run", "--keep", str(script), "--quiet"], work, cache_dir)
    assert res.returncode == 0, res.stderr

    build = work / "build" / "hello_run"
    bundle = build / "bundle.c"
    assert bundle.is_file(), "--keep must leave build/hello_run/bundle.c"
    assert bundle.read_text(encoding="utf-8").count("pengu_main") >= 1
    exe = build / ("hello.exe" if os.name == "nt" else "hello")
    assert exe.is_file(), "--keep must leave the linked binary next to bundle.c"

    # A second --keep run rebuilds in the same, already existing directory.
    res2 = _cli(["run", "--keep", str(script), "--quiet"], work, cache_dir)
    assert res2.returncode == 0, res2.stderr
    assert bundle.is_file()


def test_ephemeral_no_cache_no_build(sandbox, tmp_path):
    work, script = sandbox["work"], sandbox["script"]
    # A dedicated cache root: '--ephemeral' must not add a single entry to it.
    fresh_cache = tmp_path / "ephemeral-cache"
    before = _leftover_temp_dirs()
    res = _cli(["run", "--ephemeral", str(script), "--quiet"], work, fresh_cache)
    assert res.returncode == 0, res.stderr
    assert "cleanup hello" in res.stdout
    assert not (work / "build").exists()
    scripts = fresh_cache / "scripts"
    assert not scripts.exists() or not list(scripts.glob(f"*/{script_binary_name()}")), \
        "--ephemeral must not populate the binary cache"
    assert _leftover_temp_dirs() == before


def test_missing_dev_compiler_falls_back_to_the_configured_one(sandbox, cache_dir):
    """A non-existent PENGU_DEV_CC must not crash the CLI.

    Covers the Windows/macOS case where the 'broken compiler' cannot be a POSIX
    shell stub: the retry path is reached because executing the compiler fails
    with OSError (spawn error), not because it exits non-zero.
    """
    work, script = sandbox["work"], sandbox["script"]
    res = _cli(["run", "--no-cache", str(script)], work, cache_dir,
               env_extra={"PENGU_DEV_CC": "pengu-no-such-compiler-xyz"})
    assert res.returncode == 0, res.stderr
    assert "cleanup hello" in res.stdout
    assert "retrying with" in res.stderr, res.stderr


def test_verbose_run_reports_dce_metrics(sandbox, cache_dir):
    """--verbose must surface the DCE reduction (the PR's measurable claim)."""
    work, script = sandbox["work"], sandbox["script"]
    res = _cli(["run", "--keep", "--verbose", str(script)], work, cache_dir)
    assert res.returncode == 0, res.stderr
    combined = res.stdout + res.stderr
    assert "DCE" in combined
    assert "bundle.c" in combined
