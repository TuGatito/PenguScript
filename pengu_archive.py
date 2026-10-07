"""Hardened helpers for reading archives that arrive from the network.

Used by ``pengu_tcc.py`` (the prebuilt TinyCC zip) and by ``build_runtime.py``
(the prebuilt WebUI release), both of which extract a downloaded archive into a
directory that also holds build output.  ``zipfile`` documents that it "attempts
to prevent" path traversal but gives no guarantee, so the check is explicit here
(ROADMAP 2.0 / Phase 9, item 9.4): absolute paths, ``..`` components, drive
letters and symlinks are refused before anything is written, and the resolved
destination of every member is verified to stay inside the target directory.
"""

from __future__ import annotations

import hashlib
import os
import tarfile
import zipfile


class UnsafeArchiveError(RuntimeError):
    """An archive member would be written outside the extraction directory."""


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """SHA-256 of a file on disk, streamed (never loads it whole in memory)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            buf = handle.read(chunk_size)
            if not buf:
                break
            digest.update(buf)
    return digest.hexdigest()


def safe_extract_zip(zf: zipfile.ZipFile, dest_dir: str) -> None:
    """Extract ``zf`` into ``dest_dir``, refusing any escaping member.

    Raises:
        UnsafeArchiveError: a member is absolute, contains ``..``, carries a
            drive letter or is a symlink, or resolves outside ``dest_dir``.
    """
    dest_real = os.path.realpath(dest_dir)
    for info in zf.infolist():
        name = info.filename
        if not name or name.endswith("/"):
            continue
        if name.startswith(("/", "\\")) or ":" in name.split("/")[0]:
            raise UnsafeArchiveError(f"archive member with an absolute path: {name!r}")
        if ".." in name.replace("\\", "/").split("/"):
            raise UnsafeArchiveError(f"archive member escapes the destination: {name!r}")
        mode = info.external_attr >> 16
        if mode and (mode & 0o170000) == 0o120000:
            raise UnsafeArchiveError(f"archive member is a symlink: {name!r}")
        target = os.path.realpath(os.path.join(dest_real, name))
        if target != dest_real and not target.startswith(dest_real + os.sep):
            raise UnsafeArchiveError(f"archive member escapes the destination: {name!r}")
    zf.extractall(dest_dir)


def safe_extract_tar(tar: tarfile.TarFile, dest_dir: str) -> None:
    """Extract ``tar`` into ``dest_dir`` with an explicit ``data`` filter.

    The members are pre-checked (absolute paths and ``..`` components) so a
    hostile archive is refused *before* the first file is written, and the
    extraction itself passes ``filter="data"`` explicitly instead of relying on
    whatever default the running Python happens to apply.
    """
    for member in tar.getmembers():
        name = member.name
        if not name:
            continue
        if name.startswith(("/", "\\")) or ":" in name.split("/")[0]:
            raise UnsafeArchiveError(f"archive member with an absolute path: {name!r}")
        if ".." in name.replace("\\", "/").split("/"):
            raise UnsafeArchiveError(f"archive member escapes the destination: {name!r}")
    tar.extractall(path=dest_dir, filter="data")
