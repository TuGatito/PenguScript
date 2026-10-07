"""Phase 9, item 9.8 — archiving the same tree must produce the same bytes.

The trap this pins: the release workflows used to archive with `tar -czf` and
`Compress-Archive`, both of which embed the *current* time (gzip header mtime /
ZIP entry dates) and the directory walk order.  ``make_release.py`` now writes the
archive itself: sorted entries, a timestamp from ``SOURCE_DATE_EPOCH``, normalized
ownership and permissions.

Scope, measured in Phase 11 (F11-N9): what is gated here is that *the same tree*
archives byte-for-byte identically.  It is **not** a claim that two independent
builds of a commit produce an identical distribution tree — they do not: of the
229 files the 1.0.0 dry run hashes, 227 matched run to run and two did not
(`pengus-*.vsix`, written by ``vsce``, and ``pengu_runtime.h.gch``, written by
gcc).  Closing those is roadmap 1.1 candidate X.
"""

from __future__ import annotations

import gzip
import hashlib
import os
import struct
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from tests.conftest import REPO
from tests.test_ci_workflows import _raw

sys.path.insert(0, str(REPO))
import make_release  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path, *, mtime: float, order: tuple = ("z.txt", "a/b.txt", "m.txt")) -> Path:
    """Build the same content twice with a different clock and creation order."""
    for rel in order:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"content of {rel}\n", encoding="utf-8")
    for path in root.rglob("*"):
        os.utime(path, (mtime, mtime))
    return root


@pytest.mark.parametrize("suffix", [".tar.gz", ".zip"])
def test_the_same_tree_archives_to_the_same_bytes(tmp_path, suffix):
    """C2: revert to `tar -czf`/`Compress-Archive` and this fails."""
    first = _tree(tmp_path / "one", mtime=1_000_000_000, order=("z.txt", "a/b.txt", "m.txt"))
    second = _tree(tmp_path / "two", mtime=1_500_000_000, order=("m.txt", "a/b.txt", "z.txt"))

    out1 = make_release.make_archive(first, tmp_path / f"one{suffix}", epoch=1_700_000_000)
    out2 = make_release.make_archive(second, tmp_path / f"two{suffix}", epoch=1_700_000_000)
    assert _sha256(out1) == _sha256(out2), (
        "the archive depends on mtimes or walk order; it must not"
    )


def test_a_different_source_date_epoch_changes_the_archive(tmp_path):
    """The epoch is the *only* time input, so the gate is not vacuous."""
    tree = _tree(tmp_path / "t", mtime=1_000_000_000)
    a = make_release.make_archive(tree, tmp_path / "a.tar.gz", epoch=1_700_000_000)
    b = make_release.make_archive(tree, tmp_path / "b.tar.gz", epoch=1_700_000_001)
    assert _sha256(a) != _sha256(b)


def test_gzip_header_carries_no_build_time(tmp_path):
    """gzip stores an mtime field; `tar -z` filled it with 'now'."""
    tree = _tree(tmp_path / "t", mtime=1_000_000_000)
    archive = make_release.make_archive(tree, tmp_path / "a.tar.gz", epoch=1_700_000_000)
    raw = archive.read_bytes()
    assert raw[:2] == b"\x1f\x8b", "not a gzip stream"
    assert struct.unpack("<I", raw[4:8])[0] == 0, "the gzip header embeds a timestamp"


def test_tar_members_are_normalized(tmp_path):
    tree = _tree(tmp_path / "t", mtime=1_000_000_000)
    archive = make_release.make_archive(tree, tmp_path / "a.tar.gz", epoch=1_700_000_000)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
    names = [m.name for m in members]
    assert names == sorted(names), names
    for member in members:
        assert member.mtime == 1_700_000_000, member.name
        assert (member.uid, member.gid) == (0, 0), member.name
        assert member.uname == member.gname == "", member.name


def test_zip_members_are_sorted_and_use_the_epoch(tmp_path):
    import time

    tree = _tree(tmp_path / "t", mtime=1_000_000_000)
    archive = make_release.make_archive(tree, tmp_path / "a.zip", epoch=1_700_000_000)
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
    assert [i.filename for i in infos] == sorted(i.filename for i in infos)
    expected = time.gmtime(1_700_000_000)[:6]
    for info in infos:
        assert info.date_time == expected, info.filename


def test_source_date_epoch_env_wins(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1234567890")
    assert make_release.resolve_source_date_epoch() == 1234567890


def test_source_date_epoch_defaults_to_the_commit_time(monkeypatch):
    """Not the wall clock: two builds of the same commit must agree."""
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    epoch = make_release.resolve_source_date_epoch()
    commit = subprocess.run(
        ["git", "log", "-1", "--format=%ct"], cwd=str(REPO),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert epoch == int(commit)


def test_no_wall_clock_in_the_packaging_path():
    """A `datetime.now()`/`time.time()` in the archive path would break the gate."""
    text = (REPO / "make_release.py").read_text(encoding="utf-8")
    for forbidden in ("datetime.now", "time.time()", "date.today"):
        assert forbidden not in text, forbidden


def test_release_workflows_use_the_deterministic_archiver():
    """The workflows must not go back to `tar -czf`/`Compress-Archive`."""
    for workflow in ("ci.yml", "release.yml"):
        raw = _raw(workflow)
        # Comments may *mention* the old commands; commands may not use them.
        code = "\n".join(
            line for line in raw.splitlines() if not line.strip().startswith("#")
        )
        assert "make_release.py --archive-only" in code, workflow
        assert "tar -czf" not in code, f"{workflow} still uses a timestamped tar"
        assert "Compress-Archive" not in code, f"{workflow} still uses Compress-Archive"
        assert "--archive" in code


def test_release_workflow_rechecks_reproducibility():
    raw = _raw("release.yml")
    assert "Reproducibility check" in raw
    assert "is not reproducible" in raw


def test_print_hashes_reports_every_file(tmp_path):
    tree = _tree(tmp_path / "t", mtime=1_000_000_000)
    hashes = make_release.artifact_hashes(tree)
    assert [rel for rel, _ in hashes] == ["a/b.txt", "m.txt", "z.txt"]
    assert all(len(d) == 64 for _, d in hashes)


def test_archive_rejects_an_unknown_extension(tmp_path):
    tree = _tree(tmp_path / "t", mtime=1_000_000_000)
    with pytest.raises(SystemExit):
        make_release.make_archive(tree, tmp_path / "a.rar")


def test_archive_of_a_missing_directory_fails(tmp_path):
    with pytest.raises(SystemExit):
        make_release.make_archive(tmp_path / "nope", tmp_path / "a.tar.gz")


# ---------------------------------------------------------------------------
# Phase 11 (F11-N7 / F11-N8) — the dry run found two holes in the packager
# ---------------------------------------------------------------------------


def test_print_hashes_is_not_a_no_op_on_the_packaging_path(tmp_path, monkeypatch, capsys):
    """F11-N8: `--print-hashes` only worked with `--archive-only`.

    The documented command — `python make_release.py --layout portable
    --print-hashes` — passed the flag to the packaging path, which ignored it
    and printed no digest at all.  A "run it twice, same hashes" check could
    therefore pass by looking at an empty screen.

    C2: drop the `if args.print_hashes:` block after the SUCCESS banner and this
    fails (no 64-hex digest naming `VERSION`).
    """
    dist = tmp_path / "dist"

    def fake_assemble(dist_dir, layout="portable"):
        dist_dir.mkdir(parents=True, exist_ok=True)
        (dist_dir / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        return dist_dir

    monkeypatch.setattr(make_release, "get_venv_python", lambda: sys.executable)
    monkeypatch.setattr(make_release, "ensure_dependencies", lambda py_exe: None)
    monkeypatch.setattr(make_release, "build_runtime", lambda py_exe, rebuild=False: None)
    monkeypatch.setattr(make_release, "assemble_distribution", fake_assemble)
    monkeypatch.setattr(make_release, "build_vscode_extension", lambda dist_dir: None)
    monkeypatch.setattr(
        make_release, "package_with_pyinstaller",
        lambda py_exe, dist_dir, bin_subdir="": None,
    )
    monkeypatch.setattr(
        make_release, "generate_release_readme",
        lambda dist_dir, layout="portable": None,
    )

    monkeypatch.setattr(sys, "argv", [
        "make_release.py", "--layout", "portable", "--skip-tests",
        "--dist-dir", str(dist), "--print-hashes",
    ])
    make_release.main()

    out = capsys.readouterr().out
    digests = [
        line for line in out.splitlines()
        if len(line.split()) == 2 and len(line.split()[0]) == 64
    ]
    assert digests, f"the packaging path printed no hashes:\n{out}"
    assert any(line.endswith("VERSION") for line in digests), digests


def test_a_stale_vsix_is_not_shipped(tmp_path, monkeypatch):
    """F11-N7: a previous release's `.vsix` must not ride along.

    `*.vsix` is git-ignored and `vsce` writes it next to the sources, so a tree
    that has cut a release before keeps the old artifact.  Measured on the 1.0.0
    dry run: `pengucc_build/` contained both `pengus-1.0.0.vsix` and the stale
    `pengus-1.0.0-rc1.vsix`, because the packager copied every `*.vsix` it found.

    C2: revert `select_vsix_artifacts` to a plain `glob("*.vsix")` copy-all and
    this fails (the stale file lands in `dist_dir`).
    """
    root = tmp_path / "root"
    ext = root / "vscode-extension"
    ext.mkdir(parents=True)
    (root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (ext / "pengus-1.0.0.vsix").write_bytes(b"current release")
    (ext / "pengus-1.0.0-rc1.vsix").write_bytes(b"stale release")
    dist = tmp_path / "dist"
    dist.mkdir()

    monkeypatch.setattr(make_release, "ROOT_DIR", root)
    monkeypatch.setattr(make_release, "sync_extension_version", lambda: None)
    monkeypatch.setattr(make_release, "run_cmd", lambda *a, **k: None)

    make_release.build_vscode_extension(dist)

    shipped = sorted(p.name for p in dist.glob("*.vsix"))
    assert shipped == ["pengus-1.0.0.vsix"], shipped


def test_the_smoke_test_scratch_is_cleaned_up(tmp_path, monkeypatch):
    """F11-N11: the release command must not leave `scratch/` behind.

    `scratch/` is git-ignored, but
    `tests/test_audit_regressions.py::test_historical_cleanup_targets_are_gone`
    asserts it is **absent**, so "run `python make_release.py`, then run the test
    suite" failed with a leftover `scratch/smoke_release_test/`.  This drives
    `main()` end to end with the heavy steps mocked: the mocked
    `verify_executable` creates the scratch directory the real smoke tests use,
    and the run must remove it.

    C2: drop the `finally: cleanup_smoke_scratch()` in `main()` and this fails.
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    dist = tmp_path / "dist"
    scratch = root / "scratch" / "smoke_release_test"

    def fake_assemble(dist_dir, layout="portable"):
        dist_dir.mkdir(parents=True, exist_ok=True)
        return dist_dir

    def fake_verify(dist_dir, bin_subdir=""):
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "leftover.txt").write_text("x", encoding="utf-8")

    monkeypatch.setattr(make_release, "ROOT_DIR", root)
    monkeypatch.setattr(make_release, "get_venv_python", lambda: sys.executable)
    monkeypatch.setattr(make_release, "ensure_dependencies", lambda py_exe: None)
    monkeypatch.setattr(make_release, "build_runtime", lambda py_exe, rebuild=False: None)
    monkeypatch.setattr(make_release, "assemble_distribution", fake_assemble)
    monkeypatch.setattr(make_release, "build_vscode_extension", lambda dist_dir: None)
    monkeypatch.setattr(
        make_release, "package_with_pyinstaller",
        lambda py_exe, dist_dir, bin_subdir="": None,
    )
    monkeypatch.setattr(
        make_release, "generate_release_readme",
        lambda dist_dir, layout="portable": None,
    )
    monkeypatch.setattr(make_release, "verify_executable", fake_verify)
    monkeypatch.setattr(sys, "argv", [
        "make_release.py", "--layout", "portable", "--dist-dir", str(dist),
    ])

    make_release.main()

    assert not scratch.exists(), "the smoke-test scratch directory was left behind"
    assert not (root / "scratch").exists(), "an empty scratch/ was left behind"
