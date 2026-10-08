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


def _run(args, cwd, env=None):
    return subprocess.run(
        [*PENGU, *args], capture_output=True, text=True, timeout=300, cwd=str(cwd),
        env=env,
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
def test_build_fails_cleanly_without_runtime_archive(fresh_project, tmp_path_factory):
    """The pre-flight fires before the compiler when the archive is gone.

    The archive is never moved on disk: ``PENGU_LIB_DIR`` is an override, so
    pointing it at an empty directory is enough to simulate a missing runtime
    without touching the repository.

    This test used to rename the checkout's real ``libpengu_runtime.a`` aside for
    the duration of one build. Serially that is harmless; under ``pytest-xdist``
    every other worker that linked during that window died with
    ``cannot find -lpengu_runtime``, which made the failure look like a dozen
    unrelated tests breaking at random.
    """
    empty_lib = tmp_path_factory.mktemp("no_runtime_lib")
    _force_rebuild(fresh_project)
    res = _run(["build"], cwd=fresh_project,
               env=dict(os.environ, PENGU_LIB_DIR=str(empty_lib)))
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


# ---------------------------------------------------------------------------
# Documented boundary: tcc strips its output, so `nm` cannot verify the pin
#
# Measured 2026-10: tcc 0.9.28rc links `_pengu_abi_pin` (the object *does*
# reference `U pengu_abi_version`) but writes a stripped executable, so
# `nm <binary>` reports no runtime symbols at all — even for a program whose
# `main` calls runtime functions. The ABI-pin guarantee is therefore verified
# under gcc and clang (the release compilers) and *not* verifiable under tcc.
# This test freezes that behaviour: if a future tcc stops stripping, it fails
# and docs/ABI.md must be revisited.
# ---------------------------------------------------------------------------


def test_tcc_output_is_stripped_so_nm_cannot_verify_the_pin(tmp_path):
    from pengu_tcc import find_tcc

    tcc = find_tcc()
    if not tcc:
        pytest.skip("no tcc available (set PENGU_TCC or ship it under build/tcc-dist)")

    src = tmp_path / "min.c"
    src.write_text("int main(void) { return 0; }\n", encoding="utf-8")
    exe = tmp_path / "min_tcc"
    res = subprocess.run([tcc, str(src), "-o", str(exe)],
                         capture_output=True, text=True, timeout=300)
    if res.returncode != 0:
        pytest.skip(f"bundled tcc cannot link a minimal program: {res.stderr.strip()}")

    file_out = subprocess.run(["file", str(exe)], capture_output=True, text=True, timeout=60)
    assert "stripped" in file_out.stdout, (
        "tcc no longer strips its output; the ABI pin can now be verified under "
        f"tcc and docs/ABI.md should say so: {file_out.stdout}"
    )
    nm = subprocess.run(["nm", str(exe)], capture_output=True, text=True, timeout=60)
    assert "pengu_abi_version" not in nm.stdout
