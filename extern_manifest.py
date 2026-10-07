#!/usr/bin/env python3
"""extern_manifest.py - Manifest and automated downloader for external C libraries.

Contains URLs, pinned SHA-256 digests and extraction logic for external
dependencies used in PenguScript's static C runtime.  Every entry here is
consumed by build_runtime.py (see the build_* functions there); libraries that
cannot be built are not listed.

  - zlib (1.3.2)            - libmicrohttpd (1.0.1)  - libxml2 (2.9.0)
  - mbedtls (4.2.0)         - curl (8.21.0)          - pcre2 (10.47)
  - raylib (6.0)            - webui (2.5.0-beta.3)   - sqlite3 (3.53.4)
  - libuv (1.52.1)          - xlsxio (0.2.36)        - libcyaml (1.4.2)
  - tomlc17 (R260821)       - libzip (1.11.3)        - libexpat (2.6.4)
  - libyaml (0.2.5)

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

#: name -> {"url": ..., "sha256": ...}
MANIFEST: Dict[str, Dict[str, str]] = {
    "curl": {
        "url": "https://github.com/curl/curl/releases/download/curl-8_21_0/curl-8.21.0.tar.xz",
        "sha256": "aa1b66a70eace83dc624508745646c08ae561de512ab403adffb93ac87fc72e6",
    },
    "libmicrohttpd": {
        "url": "https://github.com/Karlson2k/libmicrohttpd/releases/download/v1.0.1/libmicrohttpd-1.0.1.tar.gz",
        "sha256": "a89e09fc9b4de34dde19f4fcb4faaa1ce10299b9908db1132bbfa1de47882b94",
    },
    "libxml2": {
        "url": "https://download.gnome.org/sources/libxml2/2.9/libxml2-2.9.0.tar.xz",
        "sha256": "97d3d9abce2da0eda9b7a58b3fd6b4a6de012d322355151e7693b0d7ed98c634",
    },
    "mbedtls": {
        "url": "https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-4.2.0/mbedtls-4.2.0.tar.bz2",
        "sha256": "2bed9d713b4668f76553b097e72b8aa30bc8f112a940d7ae228d524bbde6ffea",
    },
    "pcre2": {
        "url": "https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.47/pcre2-10.47.tar.gz",
        "sha256": "c08ae2388ef333e8403e670ad70c0a11f1eed021fd88308d7e02f596fcd9dc16",
    },
    "zlib": {
        "url": "https://github.com/madler/zlib/releases/download/v1.3.2/zlib-1.3.2.tar.gz",
        "sha256": "bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16",
    },
    "raylib": {
        "url": "https://github.com/raysan5/raylib/archive/refs/tags/6.0.tar.gz",
        "sha256": "2b3ee1e2120c7a0796b33062c7e9a694dd8a8caa56a96319ac8c8ecf54a90d0b",
    },
    "webui": {
        "url": "https://github.com/webui-dev/webui/archive/refs/tags/2.5.0-beta.3.tar.gz",
        "sha256": "03a388ff0fa4b87ef15239f2b2a7308356fb5d2119f693c1dd61d68e38e91732",
    },
    "sqlite3": {
        "url": "https://sqlite.org/2026/sqlite-autoconf-3530400.tar.gz",
        "sha256": "0e9483900e92cd5de8fd48d16bf9200145a61f7fd5be542a5ac81d8a9516eb9c",
    },
    "libuv": {
        "url": "https://github.com/libuv/libuv/archive/refs/tags/v1.52.1.tar.gz",
        "sha256": "478baf2599bfbc882c355288c9cb6f92e0e7dda435fa04031fa5b607cf3f414c",
    },
    "xlsxio": {
        "url": "https://github.com/brechtsanders/xlsxio/archive/refs/tags/0.2.36.tar.gz",
        "sha256": "80d3df95a7a108a41f83f0ce4c6706873fd2afafd92424fcccea475a8acbd044",
    },
    "libcyaml": {
        "url": "https://github.com/tlsa/libcyaml/archive/refs/tags/v1.4.2.tar.gz",
        "sha256": "3211b2a0589ebfe02c563c96adce9246c0787be2af30353becbbd362998d16dc",
    },
    "tomlc17": {
        "url": "https://github.com/cktan/tomlc17/archive/refs/tags/R260821.tar.gz",
        "sha256": "c4958fe2664d596ba1cc22589f56f900429fac89ad0738c3468c6e1021e92c1a",
    },
    "libzip": {
        "url": "https://github.com/nih-at/libzip/releases/download/v1.11.3/libzip-1.11.3.tar.xz",
        "sha256": "9509d878ba788271c8b5abca9cfde1720f075335686237b7e9a9e7210fe67c1b",
    },
    "libexpat": {
        "url": "https://github.com/libexpat/libexpat/releases/download/R_2_6_4/expat-2.6.4.tar.xz",
        "sha256": "a695629dae047055b37d50a0ff4776d1d45d0a4c842cf4ccee158441f55ff7ee",
    },
    "libyaml": {
        "url": "https://pyyaml.org/download/libyaml/yaml-0.2.5.tar.gz",
        "sha256": "c642ae9b75fee120b2d96c712538bd2cf283228d2337df2cf2988e3c02678ef4",
    },
}

EXPECTED_DIRS = {
    "curl": "curl-8.21.0",
    "libmicrohttpd": "libmicrohttpd-1.0.1",
    "libxml2": "libxml2-2.9.0",
    "mbedtls": "mbedtls-4.2.0",
    "pcre2": "pcre2-10.47",
    "zlib": "zlib-1.3.2",
    "raylib": "raylib-6.0",
    "webui": "webui-2.5.0-beta.3",
    "sqlite3": "sqlite-autoconf-3530400",
    "libuv": "libuv-1.52.1",
    "xlsxio": "xlsxio-0.2.36",
    "libcyaml": "libcyaml-1.4.2",
    "tomlc17": "tomlc17-R260821",
    "libzip": "libzip-1.11.3",
    "libexpat": "expat-2.6.4",
    "libyaml": "yaml-0.2.5",
}

#: Backwards-compatible name -> URL view (older callers/tests used this shape).
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
