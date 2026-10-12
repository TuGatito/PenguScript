#!/usr/bin/env python3
"""extern_manifest.py - Manifest and downloader for external C libraries.

The PenguScript **core runtime** has no external C dependencies: it needs only
libc, libm and pthreads / Win32 threads. ``MANIFEST`` and ``EXPECTED_DIRS`` are
therefore empty and ``build_runtime.py`` downloads nothing.

The infrastructure below (URL pinning, streamed SHA-256 verification, safe
extraction, verified-directory stamps) is deliberately kept: the satellite
binding repositories introduced by Phase 1 copy this module to fetch and verify
the upstream library they wrap. See docs/EXTERNAL_MODULES.md.

An entry is a ``name -> {"url", "sha256"}`` mapping; adding one makes
``build_runtime.py`` stage it into ``extern/`` again.

Every archive is **verified while it is streamed to disk**: the SHA-256 is
computed on the bytes that are written and compared with the digest pinned in
this file *before* anything is extracted.  A mismatch aborts with the offending
digest and leaves ``extern/`` untouched.

The pinned digests are data, not a build step: they were derived once by
``python scripts/extern_digests.py --download`` and are checked by
``python scripts/extern_digests.py --check`` (offline).  To re-pin after a
deliberate upstream change, run ``--update`` and review the diff.

Note on GitHub-generated tarballs (``/archive/refs/tags/...``): those are not
byte-stable by contract -- GitHub has changed the gzip wrapper before and can
re-generate an archive when a tag is re-pointed.  If one of those entries starts
failing the digest, the release is *supposed* to stop: verify the new archive by
hand, then re-pin with ``--update`` in its own commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from pengu_archive import UnsafeArchiveError, safe_extract_tar

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_EXTERN_DIR = ROOT_DIR / "extern"

#: Size of the chunks read from the HTTP response while hashing.
CHUNK_SIZE = 64 * 1024

#: Records which pinned digest produced which extracted directory, so a cached
#: directory is only trusted when the *verified* archive that created it is the
#: one currently pinned.  Without it, "the folder exists" would silently mean
#: "a digest was never checked".
STAMP_NAME = ".pengu_verified.json"

#: name -> {"url": ..., "sha256": ...}.  Empty for the core runtime; satellite
#: binding repositories populate their own copy.
MANIFEST: Dict[str, Dict[str, str]] = {}

#: name -> extracted directory name.  Empty for the core runtime.
EXPECTED_DIRS = {}

MANIFEST_URLS: Dict[str, str] = {name: entry["url"] for name, entry in MANIFEST.items()}


class DigestMismatchError(RuntimeError):
    """The downloaded stream does not hash to the pinned SHA-256."""


def _stamp_path(target_dir: Path) -> Path:
    return target_dir / STAMP_NAME


def _read_stamp(target_dir: Path) -> Dict[str, str]:
    try:
        data = json.loads(_stamp_path(target_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_stamp(target_dir: Path, stamp: Dict[str, str]) -> None:
    try:
        _stamp_path(target_dir).write_text(
            json.dumps(stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError:
        # A stamp is an optimisation, not a gate: if it cannot be written the
        # next run simply re-downloads (and re-verifies) the archive.
        pass


def _download_verified(
    name: str, url: str, expected: str, archive_path: Path
) -> str:
    """Stream ``url`` into ``archive_path``, hashing as it goes.

    Returns the computed digest.  Raises :class:`DigestMismatchError` before the
    caller is allowed to extract anything.
    """
    digest = hashlib.sha256()
    req = urllib.request.Request(
        url, headers={"User-Agent": "PenguScript-Release-Packager/0.6.0"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp, open(archive_path, "wb") as out_f:
        # `resp.headers` exists on both HTTPResponse and the file:// addinfourl
        # (tests drive this path with a local archive), unlike `getheader`.
        headers = getattr(resp, "headers", None)
        total_size = headers.get("Content-Length") if headers is not None else None
        total_bytes = int(total_size) if total_size and total_size.isdigit() else None
        downloaded = 0

        while True:
            buf = resp.read(CHUNK_SIZE)
            if not buf:
                break
            digest.update(buf)
            downloaded += len(buf)
            out_f.write(buf)
            if total_bytes:
                pct = (downloaded / total_bytes) * 100
                print(
                    f"\r    -> {downloaded / (1024 * 1024):.2f} MB / {total_bytes / (1024 * 1024):.2f} MB ({pct:.1f}%)",
                    end="",
                    flush=True,
                )

    actual = digest.hexdigest()
    if not expected:
        raise DigestMismatchError(
            f"{name}: no SHA-256 is pinned for {url}. "
            f"Run 'python scripts/extern_digests.py --download' and commit the table."
        )
    if actual != expected:
        raise DigestMismatchError(
            f"{name}: SHA-256 mismatch for {url}\n"
            f"  expected {expected}\n"
            f"  actual   {actual}\n"
            f"  Refusing to extract. If the upstream release genuinely changed, "
            f"verify it by hand and re-pin with 'python scripts/extern_digests.py --update'."
        )
    return actual


def _extract_archive(archive_path: Path, target_dir: Path) -> None:
    """Extract a tarball with Python's ``data`` filter (explicit, not by default).

    ``filter="data"`` rejects absolute paths, ``..`` traversals, links that
    escape the destination and special files, so a hostile or corrupted archive
    cannot write outside ``target_dir``.  ``safe_extract_tar`` pre-checks the
    members so nothing at all is written when one of them escapes.
    """
    with tarfile.open(archive_path) as tar:
        safe_extract_tar(tar, str(target_dir))


def _remove_tree(path: Path) -> None:
    """Removes a previous extraction, clearing Windows' read-only attributes.

    A forced re-extraction used to unpack *over* the existing tree.  An upstream
    tarball may contain relative symlinks, and Python's tar ``data`` filter calls
    ``os.path.realpath(..., strict=ALLOW_MISSING)`` on every member path; on
    Windows that raises ``PermissionError [WinError 5]`` when the member is a
    symlink that is already on disk, so the release build died re-extracting a
    tree it had created itself one step earlier.  Removing the destination first
    makes the forced extraction identical to the first.
    """
    if path.is_symlink() or not path.exists():
        try:
            path.unlink()
        except OSError:
            pass
        return

    def _clear_readonly(func, target, exc_info):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if os.name == "nt":
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_clear_readonly)
        else:  # pragma: no cover - Python 3.11 still supports `onerror`
            shutil.rmtree(path, onerror=_clear_readonly)
    else:
        shutil.rmtree(path)


def download_and_extract_externs(
    extern_dir: Optional[Path] = None,
    force: bool = False,
    verify_only: bool = False,
    manifest: Optional[Dict[str, Dict[str, str]]] = None,
    expected_dirs: Optional[Dict[str, str]] = None,
) -> None:
    """Downloads and extracts all external dependencies into the extern/ directory.

    Args:
        extern_dir: Target directory path for external libraries (defaults to ROOT/extern).
        force: If True, re-downloads and re-extracts even if folders already exist.
        verify_only: If True, downloads and hashes every archive but extracts nothing.
        manifest: Optional manifest override (used by tests with synthetic archives).
        expected_dirs: Optional extraction-dir override matching ``manifest``.

    Raises:
        DigestMismatchError: A downloaded stream does not hash to the pinned digest.
    """
    target_dir = (extern_dir or DEFAULT_EXTERN_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    entries = MANIFEST if manifest is None else manifest
    dirs = EXPECTED_DIRS if expected_dirs is None else expected_dirs
    stamp = _read_stamp(target_dir)

    print(f"=== Checking external C libraries in: {target_dir} ===")

    for name, entry in entries.items():
        url = entry["url"]
        expected = entry.get("sha256", "")
        expected_folder_name = dirs.get(name, name)
        extracted_path = target_dir / expected_folder_name

        if verify_only:
            # Verified downloads never touch extern/: a mismatch must leave the
            # tree exactly as it was.
            archive_path = Path(tempfile.gettempdir()) / f"pengu-verify-{name}.archive"
            try:
                actual = _download_verified(name, url, expected, archive_path)
                print(f"\n  [VERIFIED] {name} sha256={actual}")
            finally:
                archive_path.unlink(missing_ok=True)
            continue

        verified = stamp.get(name) == expected and expected
        if extracted_path.exists() and not force and verified:
            print(f"  [OK] {name} already present at {extracted_path.name} (digest verified)")
            continue
        if extracted_path.exists() and not force and not verified:
            print(
                f"  [RE-VERIFYING] {name}: cached copy has no verified digest for the pinned archive"
            )

        print(f"  [DOWNLOADING] {name} from {url}...")
        archive_name = url.split("/")[-1]
        archive_path = target_dir / archive_name

        try:
            actual = _download_verified(name, url, expected, archive_path)

            print(f"\n  [EXTRACTING] {archive_name}...")
            # Extract into a clean destination: a forced re-extraction over the
            # previous tree is what broke on Windows (see `_remove_tree`).
            _remove_tree(extracted_path)
            _extract_archive(archive_path, target_dir)

            # Only now is the extracted tree's provenance known.
            stamp[name] = actual
            _write_stamp(target_dir, stamp)

            print(f"  [SUCCESS] {name} installed to {extracted_path.name} (sha256 verified)")

        except (DigestMismatchError, UnsafeArchiveError):
            # Never reinterpret a rejected archive as a plain download failure.
            raise
        except Exception as e:
            print(
                f"\n[ERROR] Failed to download or extract {name} from {url}: {e}",
                file=sys.stderr,
            )
            raise
        finally:
            if archive_path.exists():
                try:
                    archive_path.unlink()
                except OSError:
                    pass

    if verify_only:
        print("=== All external C library digests verified (nothing extracted). ===\n")
    else:
        print("=== All external C libraries verified. ===\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="download every archive, check its SHA-256 and extract nothing",
    )
    parser.add_argument(
        "--force", action="store_true", help="re-download even if the folder exists"
    )
    parser.add_argument(
        "--extern-dir", type=Path, default=None, help="target directory (default: ./extern)"
    )
    args = parser.parse_args(argv)
    try:
        download_and_extract_externs(
            args.extern_dir, force=args.force, verify_only=args.verify
        )
    except (DigestMismatchError, UnsafeArchiveError) as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
