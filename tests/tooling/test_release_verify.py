"""Phase 9, items 9.7 and 9.12 — verify the *published* artifact by running it.

`release.yml`'s `verify` job is the last gate of a release: it downloads each
published artifact and executes `pengu -V`, `pengu build` and `pengu run` in both
the portable layout and a real FHS prefix.  Phase 12 folded the old
`release-verify.yml` into that job, so the ordering guarantee is now
`needs: [publish-release]` instead of an explicit `gh workflow run` dispatch.
The job cannot run here (no published release), so these tests pin the wiring and
execute the checking script itself against the local toolchain, which is the part
that can be run.
"""

from __future__ import annotations

import os
import shutil
import tarfile
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.conftest import REPO
from tests.test_ci_workflows import ALL_WORKFLOWS, _jobs, _raw, _triggers

#: The fake artifact's "binary" is `tests/fixtures/fake_pengu.py` written to a
#: file named `pengu` and executed through its `#!` shebang -- a POSIX mechanism.
#: Windows cannot run it (measured: `OSError [WinError 193]`), and release.yml
#: verifies the *real* `pengu.exe` in the portable layout, so the fake-binary
#: executions are POSIX-only.
_FAKE_BINARY_IS_POSIX = pytest.mark.skipif(
    os.name == "nt",
    reason="the fake artifact binary is a POSIX shebang script; Windows verifies "
           "the real pengu.exe in release.yml",
)

SCRIPT = REPO / "scripts" / "verify_release_artifact.py"
RUNTIME_ARCHIVE = REPO / "build" / "lib" / "libpengu_runtime.a"
VERSION = (REPO / "VERSION").read_text(encoding="utf-8").strip()

#: Assets release.yml publishes (`matrix.artifact_name`).
PUBLISHED_ASSETS = {"pengu-linux-x64.tar.gz", "pengu-macos.tar.gz", "pengu-windows-x64.zip"}


def _verify_doc() -> dict:
    """The workflow that owns verification: `release.yml`, job `verify`."""
    return yaml.safe_load(_raw("release.yml"))


def test_verification_is_a_job_of_the_release_workflow():
    doc = _verify_doc()
    triggers = _triggers(doc)
    assert "workflow_dispatch" in triggers, "ci.yml's auto-tag dispatches the release"
    assert triggers["workflow_dispatch"]["inputs"]["version"]["required"] is True
    assert "push" in triggers and "v*" in triggers["push"]["tags"], (
        "a hand-pushed tag must release — and therefore verify — too"
    )
    # The dispatch that used to start release-verify.yml is gone: ordering is a
    # `needs:` edge inside the workflow now, which cannot be forgotten.
    assert _jobs(doc)["verify"]["needs"] == ["publish-release"]


def test_every_published_asset_is_downloaded_and_executed():
    """No artifact may be published without being run (item 9.7)."""
    matrix = _jobs(_verify_doc())["verify"]["strategy"]["matrix"]["include"]
    covered = {entry["artifact"] for entry in matrix}
    assert covered == PUBLISHED_ASSETS, covered

    raw = _raw("release.yml")
    assert "gh release download" in raw
    assert '--pattern "${{ matrix.artifact }}"' in raw
    assert "scripts/verify_release_artifact.py" in raw
    assert '--artifact "dist/${{ matrix.artifact }}"' in raw


def test_both_layouts_are_exercised_and_fhs_is_not_claimed_on_windows():
    matrix = _jobs(_verify_doc())["verify"]["strategy"]["matrix"]["include"]
    layouts = {entry["layout"] for entry in matrix}
    assert layouts == {"portable", "fhs"}, layouts
    for entry in matrix:
        if entry["os"].startswith("windows"):
            assert entry["layout"] == "portable", "make_release.py rejects --layout fhs on Windows"
    # FHS runs on both POSIX platforms, one per artifact.
    posix_fhs = [e for e in matrix if e["layout"] == "fhs"]
    assert {e["os"] for e in posix_fhs} == {"ubuntu-latest", "macos-latest"}


def test_verification_runs_in_the_same_workflow_after_publishing():
    """`needs:` replaces the old dispatch, so the order cannot drift."""
    raw = _raw("release.yml")
    assert "gh workflow run release-verify.yml" not in raw, (
        "the separate verification workflow went away in Phase 12"
    )
    job = _jobs(yaml.safe_load(raw))["verify"]
    assert job["needs"] == ["publish-release"]
    assert "gh release create" in raw, "this workflow is the publisher"
    assert "gh release download" in raw, "and it verifies the *published* artifact"


def test_the_verify_job_cannot_write_to_the_repository():
    job = _jobs(_verify_doc())["verify"]
    assert job["permissions"] == {"contents": "read"}, job["permissions"]
    assert "gh release delete" not in _raw("release.yml"), (
        "the verifying job must not be able to unpublish by itself"
    )


def test_release_workflow_keeps_the_repo_invariants():
    """It is picked up by the generic invariants (timeout, concurrency, pins)."""
    assert "release.yml" in ALL_WORKFLOWS
    raw = _raw("release.yml")
    assert "concurrency:" in raw
    assert "cancel-in-progress: false" in raw
    assert "@11d5960a326750d5838078e36cf38b85af677262" in raw  # pinned checkout


# --------------------------------------------------------------------------- #
# The script itself, executed.
# --------------------------------------------------------------------------- #


def test_windows_pengu_command_keeps_backslash_paths():
    """Regression: Windows paths were shredded by ``shlex.split``.

    ``--pengu "C:\\...\\python.exe D:\\a\\...\\pengu_project.py"`` was split in
    POSIX mode, where ``\\`` escapes the next character, so the interpreter
    became ``C:...python.exe`` and every check died with ``WinError 2`` before
    it could run. ``_split_command(windows=True)`` is exercised from any host.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import verify_release_artifact as tool
    finally:
        sys.path.pop(0)

    cmd = (r"C:\hostedtoolcache\windows\Python\3.14.7\x64\python.exe "
           r"D:\a\PenguScript\PenguScript\pengu_project.py")
    assert tool._split_command(cmd, windows=True) == [
        r"C:\hostedtoolcache\windows\Python\3.14.7\x64\python.exe",
        r"D:\a\PenguScript\PenguScript\pengu_project.py",
    ]
    # A quoted interpreter path with spaces keeps both its spaces and its slashes.
    quoted = (r'"C:\Program Files\Python\python.exe" '
              r"D:\a\PenguScript\PenguScript\pengu_project.py")
    assert tool._split_command(quoted, windows=True) == [
        r"C:\Program Files\Python\python.exe",
        r"D:\a\PenguScript\PenguScript\pengu_project.py",
    ]


def _build_fake_artifact(tmp_path, *, name="pengu-linux-x64.tar.gz", version="1.2.3"):
    """A hermetic release artifact: the real portable layout, fake binary.

    The layout is the one `make_release.py` produces, including the detail that
    bit the first version of the FHS installer (F9-N7): the static archives live
    *directly* in `runtime/`, not in `runtime/lib/`.
    """
    fake = (REPO / "tests" / "fixtures" / "fake_pengu.py").read_text(encoding="utf-8")
    fake = fake.replace('VERSION = "1.2.3"', f'VERSION = "{version}"')

    unpacked = tmp_path / "payload"
    (unpacked / "runtime" / "include").mkdir(parents=True)
    (unpacked / "std").mkdir(parents=True)
    binary = unpacked / "pengu"
    binary.write_text(fake, encoding="utf-8")
    binary.chmod(0o755)
    (unpacked / "VERSION").write_text(version, encoding="utf-8")
    (unpacked / "runtime" / "libpengu_runtime.a").write_bytes(b"!<arch>\n")
    (unpacked / "runtime" / "pengu_runtime.h").write_text("/* */", encoding="utf-8")
    (unpacked / "runtime" / "include" / "zlib.h").write_text("/* */", encoding="utf-8")
    (unpacked / "std" / "spark.pengu").write_text("", encoding="utf-8")

    archive = tmp_path / name
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(unpacked.rglob("*")):
            tar.add(path, arcname=str(path.relative_to(unpacked)))
    return archive


def test_install_fhs_installs_the_real_portable_layout(tmp_path):
    """The published artifact is portable; the FHS layout is *installed* from it."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import verify_release_artifact as tool
    finally:
        sys.path.pop(0)

    artifact = _build_fake_artifact(tmp_path)
    unpacked = tmp_path / "unpacked"
    tool.unpack(artifact, unpacked)

    prefix = tmp_path / "prefix"
    binary = tool.install_fhs(unpacked, prefix)

    assert binary == prefix / "bin" / "pengu"
    # `runtime/*.a` (portable) -> `lib/pengu/*.a` (FHS): the exact mapping the
    # first version got wrong, which made every FHS run fail.
    assert (prefix / "lib" / "pengu" / "libpengu_runtime.a").is_file()
    assert (prefix / "include" / "pengu" / "pengu_runtime.h").is_file()
    assert (prefix / "include" / "pengu" / "zlib.h").is_file()
    assert (prefix / "share" / "pengu" / "std" / "spark.pengu").is_file()
    assert (prefix / "share" / "pengu" / "VERSION").read_text(encoding="utf-8") == "1.2.3"
    assert tool.artifact_version(unpacked, "portable") == "1.2.3"


@_FAKE_BINARY_IS_POSIX
@pytest.mark.parametrize("layout", ["portable", "fhs"])
def test_script_verifies_a_whole_artifact_end_to_end(tmp_path, layout):
    """The gate the workflow runs, with a real archive and a real extraction.

    This is the test that would have caught F9-N7: the scratch directory was
    never created, and the FHS installer looked for `runtime/lib/*.a`.
    """
    artifact = _build_fake_artifact(tmp_path)
    workdir = tmp_path / "work" / "does-not-exist-yet"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(artifact),
         "--layout", layout, "--expected-version", "1.2.3",
         "--workdir", str(workdir)],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Hello, world!" in output
    assert f"{layout} layout verified" in output
    if layout == "fhs":
        assert "hiding <prefix>/lib/pengu breaks the build" in output


@_FAKE_BINARY_IS_POSIX
def test_the_artifact_binary_is_execed_where_it_was_unpacked(tmp_path):
    artifact = _build_fake_artifact(tmp_path)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(artifact),
         "--layout", "portable", "--expected-version", "1.2.3"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "unpacked/pengu -V" in result.stdout


def test_script_fails_when_the_artifact_version_differs_from_the_tag(tmp_path):
    artifact = _build_fake_artifact(tmp_path, version="1.2.3")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(artifact),
         "--layout", "portable", "--expected-version", "9.9.9"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    assert result.returncode == 1
    assert "9.9.9" in result.stdout + result.stderr


def test_script_fails_when_the_binary_contradicts_the_version_file(tmp_path):
    """Without a tag, the artifact's own VERSION file is the expectation."""
    artifact = _build_fake_artifact(tmp_path, version="1.2.3")
    unpacked = tmp_path / "unpacked"
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import verify_release_artifact as tool
    finally:
        sys.path.pop(0)
    tool.unpack(artifact, unpacked)
    # Rewrite the file so it disagrees with what `pengu -V` prints.
    (unpacked / "VERSION").write_text("3.0.0", encoding="utf-8")
    repacked = tmp_path / "repacked.tar.gz"
    with tarfile.open(repacked, "w:gz") as tar:
        for path in sorted(unpacked.rglob("*")):
            tar.add(path, arcname=str(path.relative_to(unpacked)))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(repacked),
         "--layout", "portable"],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    assert result.returncode == 1
    assert "3.0.0" in result.stdout + result.stderr


def test_fhs_negative_control_runs_by_default(tmp_path):
    """The FHS gate must prove the prefix was used, without an extra flag."""
    raw = SCRIPT.read_text(encoding="utf-8")
    assert "prove_layout=not args.no_prove_layout" in raw
    assert "--no-prove-layout" in raw, "there must be a documented escape hatch"
    assert "is not what made it work" in raw


@pytest.mark.skipif(
    not RUNTIME_ARCHIVE.is_file(),
    reason="needs build/lib/libpengu_runtime.a (run build_runtime.py first)",
)
def test_script_executes_a_real_build_and_run(tmp_path):
    """End-to-end: `pengu -V`, `pengu build`, `pengu run hello.pengu`."""
    pengu = f"{sys.executable} {REPO / 'pengu_project.py'}"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--pengu", pengu,
         "--expected-version", VERSION, "--workdir", str(tmp_path / "w")],
        capture_output=True, text=True, cwd=str(REPO), timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Hello, world!" in result.stdout
    assert "[OK] pengu -V" in result.stdout
    assert "pengu build of a minimal project (rc=0)" in result.stdout


def test_script_fails_when_the_version_does_not_match(tmp_path):
    """C2: the version check is a gate, not a log line."""
    pengu = f"{sys.executable} {REPO / 'pengu_project.py'}"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--pengu", pengu,
         "--expected-version", "99.99.99", "--workdir", str(tmp_path / "w")],
        capture_output=True, text=True, cwd=str(REPO), timeout=300,
    )
    assert result.returncode == 1
    assert "99.99.99" in result.stdout + result.stderr


def test_script_rejects_an_unsupported_artifact_type(tmp_path):
    bad = tmp_path / "pengu.tar.bz2"
    bad.write_bytes(b"nope")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--artifact", str(bad), "--layout", "portable"],
        capture_output=True, text=True, cwd=str(REPO), timeout=120,
    )
    assert result.returncode == 1
    assert "unsupported artifact type" in result.stdout + result.stderr


def test_script_has_no_third_party_dependency():
    """It must run on a bare runner (and on the verification matrix)."""
    text = SCRIPT.read_text(encoding="utf-8")
    for import_line in ("import requests", "import yaml", "import pytest"):
        assert import_line not in text
    assert shutil.which("python") or True  # documentation-only guard


# --------------------------------------------------------------------------- #
# Item 9.12 — the layouts are verified on every push, not only at release time.
# --------------------------------------------------------------------------- #


def test_ci_verifies_the_packaged_artifact_in_both_layouts():
    raw = _raw("ci.yml")
    assert "scripts/verify_release_artifact.py" in raw, (
        "CI must run the packaged artifact, not only the source tree"
    )
    assert '--layout portable' in raw
    assert '--layout fhs' in raw
    # FHS does not exist on Windows (`make_release.py` rejects it there).
    fhs_step = raw.split("--layout fhs", 1)[0].rsplit("- name:", 1)[-1]
    assert "runner.os != 'Windows'" in fhs_step, fhs_step[:200]


def test_the_layout_check_runs_the_binary_and_not_a_unit_test():
    """The gate is an execution: it must invoke the unpacked `pengu`."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import verify_release_artifact as tool
    finally:
        sys.path.pop(0)

    source = (REPO / "scripts" / "verify_release_artifact.py").read_text(encoding="utf-8")
    for needle in ('"new", "exe"', '"build"', '"run"'):
        assert needle in source, needle
    # And the FHS run proves the prefix was used.
    assert "check_layout_is_actually_used" in source
    assert "libpengu_runtime.a" in source
    assert callable(tool.install_fhs)
