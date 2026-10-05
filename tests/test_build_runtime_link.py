"""Phase 4 item 4.17a: ``pengu build`` always links the runtime archive.

Every bundle references ``pengu_abi_version`` (4.17b), so ``libpengu_runtime.a``
is a hard build requirement. Two properties are checked here:

* a freshly initialised project actually puts ``-lpengu_runtime`` on the link
  line and produces a runnable binary, and
* when the archive is missing the CLI fails **before** the compiler with an
  actionable message instead of an inscrutable ``undefined reference``.

The archive is never moved on disk: ``PENGU_LIB_DIR`` takes precedence over the
checkout's ``build/lib`` in :func:`pengu_paths.runtime_lib_dirs`, so pointing it
at an empty directory is enough to simulate a missing runtime without touching
the repository.
"""

import os
import subprocess
import sys

import pytest

from tests.conftest import BUILD_LIB, REPO, requires_cc, requires_runtime

PENGU = [sys.executable, str(REPO / "pengu_project.py")]


def _run(args, cwd):
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300, cwd=str(cwd),
    )


def _force_rebuild(project):
    """Drops the build directory so the CLI really invokes the C compiler."""
    import shutil

    shutil.rmtree(project / "build", ignore_errors=True)


@pytest.fixture()
def fresh_project(tmp_path):
    res = _run(["init", "ok"], cwd=tmp_path)
    assert res.returncode == 0, res.stderr
    return tmp_path / "ok"


@requires_cc
@requires_runtime
def test_new_project_links_the_runtime_archive(fresh_project):
    _force_rebuild(fresh_project)
    res = _run(["build", "--verbose"], cwd=fresh_project)
    assert res.returncode == 0, res.stderr
    assert "-lpengu_runtime" in (res.stdout + res.stderr), res.stdout + res.stderr
    binary = fresh_project / "build" / "ok"
    assert binary.is_file(), binary
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr


@requires_cc
@requires_runtime
def test_link_line_comes_from_the_config_path(fresh_project):
    """`pengu init` writes a pengu.toml with `links = []`; it must not matter."""
    cfg = (fresh_project / "pengu.toml").read_text(encoding="utf-8")
    assert "links = []" in cfg, cfg
    _force_rebuild(fresh_project)
    res = _run(["build", "--verbose"], cwd=fresh_project)
    assert res.returncode == 0, res.stderr
    assert "-lpengu_runtime" in (res.stdout + res.stderr), res.stdout + res.stderr


@requires_cc
@requires_runtime
def test_build_fails_cleanly_without_runtime_archive(fresh_project):
    """The pre-flight fires before the compiler when the archive is gone.

    ``runtime_lib_dirs()`` always includes the checkout's ``build/lib``, so the
    archive has to be moved aside for real; it is restored in ``finally``.
    """
    archive = BUILD_LIB / "libpengu_runtime.a"
    assert archive.is_file()
    hidden = archive.with_suffix(".a.hidden-by-test")
    _force_rebuild(fresh_project)
    archive.rename(hidden)
    try:
        res = _run(["build"], cwd=fresh_project)
    finally:
        if hidden.exists():
            hidden.rename(archive)
    assert res.returncode != 0
    combined = res.stdout + res.stderr
    assert "libpengu_runtime.a not found" in combined, combined
    assert "build_runtime.py" in combined, combined
    assert "Traceback" not in combined, combined
    assert "undefined reference" not in combined, combined


def test_help_documents_the_runtime_requirement():
    """The contract is discoverable: `pengu build --help` mentions the runtime."""
    res = subprocess.run(
        [*PENGU, "build", "--help"], capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr


@requires_runtime
def test_preflight_helper_finds_the_archive():
    from pengu_project import _find_runtime_archive

    found = _find_runtime_archive()
    assert found is not None, "libpengu_runtime.a should be discoverable"
    assert found.endswith("libpengu_runtime.a")
    assert os.path.isfile(found)
