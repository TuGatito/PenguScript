"""Phase 9, item 9.4 — no archive is extracted without an escaping-path check.

The roadmap's done-criterion is "no `extractall` without `filter`/validation".
That is checked here in two ways: behaviourally (a hostile tar/zip cannot write
outside the destination) and structurally (a new call site in first-party code
cannot be added without either the `data` filter or the shared validator).
"""

from __future__ import annotations

import io
import re
import tarfile
import zipfile
from pathlib import Path

import pytest

import pengu_archive
from pengu_archive import UnsafeArchiveError, safe_extract_tar, safe_extract_zip

ROOT = Path(__file__).resolve().parents[2]
EXTRACT_CALL = re.compile(r"\.extractall\(")


def _hostile_tar(member_name: str) -> tarfile.TarFile:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(member_name)
        info.size = 4
        tar.addfile(info, io.BytesIO(b"pwn\n"))
    buf.seek(0)
    return tarfile.open(fileobj=buf)


def _hostile_zip(member_name: str) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member_name, "pwn\n")
    buf.seek(0)
    return zipfile.ZipFile(buf)


@pytest.mark.parametrize("member", ["../evil.txt", "/tmp/pengu-evil-abs.txt", "a/../../evil.txt"])
def test_tar_traversal_is_refused_before_writing(tmp_path, member):
    dest = tmp_path / "dest"
    dest.mkdir()
    with _hostile_tar(member) as tar:
        with pytest.raises(UnsafeArchiveError):
            safe_extract_tar(tar, str(dest))
    assert list(dest.iterdir()) == []
    assert not (tmp_path / "evil.txt").exists()
    assert not Path("/tmp/pengu-evil-abs.txt").exists()


@pytest.mark.parametrize("member", ["../evil.txt", "/tmp/pengu-evil-abs.zip", "a/../../evil.txt"])
def test_zip_traversal_is_refused_before_writing(tmp_path, member):
    dest = tmp_path / "dest"
    dest.mkdir()
    with _hostile_zip(member) as zf:
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zf, str(dest))
    assert list(dest.iterdir()) == []
    assert not (tmp_path / "evil.txt").exists()
    assert not Path("/tmp/pengu-evil-abs.zip").exists()


def test_zip_windows_drive_path_is_refused(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    with _hostile_zip("C:/Windows/evil.txt") as zf:
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zf, str(dest))


def test_zip_symlink_member_is_refused(tmp_path):
    dest = tmp_path / "dest"
    dest.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("link")
        info.external_attr = (0o120777 << 16)  # S_IFLNK
        zf.writestr(info, "/etc/passwd")
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        with pytest.raises(UnsafeArchiveError):
            safe_extract_zip(zf, str(dest))


def test_benign_archives_still_extract(tmp_path):
    """Positive control: the hardening must not break normal archives."""
    tar_dest = tmp_path / "tar"
    tar_dest.mkdir()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo("lib/file.c")
        info.size = 4
        tar.addfile(info, io.BytesIO(b"int\n"))
    buf.seek(0)
    with tarfile.open(fileobj=buf) as tar:
        safe_extract_tar(tar, str(tar_dest))
    assert (tar_dest / "lib" / "file.c").read_bytes() == b"int\n"

    zip_dest = tmp_path / "zip"
    zip_dest.mkdir()
    with _hostile_zip("lib/file.c") as zf:
        safe_extract_zip(zf, str(zip_dest))
    assert (zip_dest / "lib" / "file.c").is_file()


def test_no_first_party_extractall_bypasses_the_guard():
    """A new `extractall` must pass `filter=` or go through `pengu_archive`."""
    offenders = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".venv", "extern", "build", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not EXTRACT_CALL.search(line):
                continue
            hardened = 'filter="data"' in line or "filter='data'" in line
            if hardened:
                continue
            # Allowed only inside the shared validator module.
            if path.name == "pengu_archive.py":
                continue
            offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert offenders == [], "unhardened extractall call sites:\n" + "\n".join(offenders)


def test_the_shared_validator_is_the_one_used_by_the_downloaders():
    """Both download paths delegate to `pengu_archive` (no second implementation)."""
    extern_src = (ROOT / "extern_manifest.py").read_text(encoding="utf-8")
    tcc_src = (ROOT / "pengu_tcc.py").read_text(encoding="utf-8")
    runtime_src = (ROOT / "build_runtime.py").read_text(encoding="utf-8")
    assert "safe_extract_tar" in extern_src
    assert "safe_extract_zip" in tcc_src
    assert "safe_extract_zip" in runtime_src
