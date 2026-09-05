#!/usr/bin/env python3
"""extern_manifest.py - Manifest and automated downloader for external C libraries.

Contains URLs and extraction logic for external dependencies used in PenguScript's
static C runtime. Every entry here is consumed by build_runtime.py (see the
build_* functions there); libraries that cannot be built are not listed.

  - zlib (1.3.2)            - libmicrohttpd (1.0.1)  - libxml2 (2.9.0)
  - mbedtls (4.2.0)         - curl (8.21.0)          - pcre2 (10.47)
  - raylib (6.0)            - webui (2.5.0-beta.3)   - sqlite3 (3.53.4)
  - libuv (1.52.1)          - xlsxio (0.2.36)        - libcyaml (1.4.2)
  - tomlc17 (R260821)       - libzip (1.11.3)        - libexpat (2.6.4)
  - libyaml (0.2.5)
"""

import os
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_EXTERN_DIR = ROOT_DIR / "extern"

MANIFEST: Dict[str, str] = {
    "curl": "https://github.com/curl/curl/releases/download/curl-8_21_0/curl-8.21.0.tar.xz",
    "libmicrohttpd": "https://github.com/Karlson2k/libmicrohttpd/releases/download/v1.0.1/libmicrohttpd-1.0.1.tar.gz",
    "libxml2": "https://download.gnome.org/sources/libxml2/2.9/libxml2-2.9.0.tar.xz",
    "mbedtls": "https://github.com/Mbed-TLS/mbedtls/releases/download/mbedtls-4.2.0/mbedtls-4.2.0.tar.bz2",
    "pcre2": "https://github.com/PCRE2Project/pcre2/releases/download/pcre2-10.47/pcre2-10.47.tar.gz",
    "zlib": "https://github.com/madler/zlib/releases/download/v1.3.2/zlib-1.3.2.tar.gz",
    "raylib": "https://github.com/raysan5/raylib/archive/refs/tags/6.0.tar.gz",
    "webui": "https://github.com/webui-dev/webui/archive/refs/tags/2.5.0-beta.3.tar.gz",
    "sqlite3": "https://sqlite.org/2026/sqlite-autoconf-3530400.tar.gz",
    "libuv": "https://github.com/libuv/libuv/archive/refs/tags/v1.52.1.tar.gz",
    "xlsxio": "https://github.com/brechtsanders/xlsxio/archive/refs/tags/0.2.36.tar.gz",
    "libcyaml": "https://github.com/tlsa/libcyaml/archive/refs/tags/v1.4.2.tar.gz",
    "tomlc17": "https://github.com/cktan/tomlc17/archive/refs/tags/R260821.tar.gz",
    "libzip": "https://github.com/nih-at/libzip/releases/download/v1.11.3/libzip-1.11.3.tar.xz",
    "libexpat": "https://github.com/libexpat/libexpat/releases/download/R_2_6_4/expat-2.6.4.tar.xz",
    "libyaml": "https://pyyaml.org/download/libyaml/yaml-0.2.5.tar.gz",
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


def download_and_extract_externs(
    extern_dir: Optional[Path] = None, force: bool = False
) -> None:
    """Downloads and extracts all external dependencies into the extern/ directory.

    Args:
        extern_dir: Target directory path for external libraries (defaults to ROOT/extern).
        force: If True, re-downloads and re-extracts even if folders already exist.
    """
    target_dir = (extern_dir or DEFAULT_EXTERN_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Checking external C libraries in: {target_dir} ===")

    for name, url in MANIFEST.items():
        expected_folder_name = EXPECTED_DIRS.get(name, name)
        extracted_path = target_dir / expected_folder_name

        if extracted_path.exists() and not force:
            print(f"  [OK] {name} already present at {extracted_path.name}")
            continue

        print(f"  [DOWNLOADING] {name} from {url}...")
        archive_name = url.split("/")[-1]
        archive_path = target_dir / archive_name

        # Download with custom User-Agent
        req = urllib.request.Request(
            url, headers={"User-Agent": "PenguScript-Release-Packager/0.6.0"}
        )

        try:
            with (
                urllib.request.urlopen(req, timeout=60) as resp,
                open(archive_path, "wb") as out_f,
            ):
                total_size = resp.getheader("Content-Length")
                total_bytes = (
                    int(total_size) if total_size and total_size.isdigit() else None
                )
                downloaded = 0
                block_sz = 64 * 1024

                while True:
                    buf = resp.read(block_sz)
                    if not buf:
                        break
                    downloaded += len(buf)
                    out_f.write(buf)
                    if total_bytes:
                        pct = (downloaded / total_bytes) * 100
                        print(
                            f"\r    -> {downloaded / (1024 * 1024):.2f} MB / {total_bytes / (1024 * 1024):.2f} MB ({pct:.1f}%)",
                            end="",
                            flush=True,
                        )

            print(f"\n  [EXTRACTING] {archive_name}...")
            with tarfile.open(archive_path) as tar:
                tar.extractall(path=target_dir)

            print(f"  [SUCCESS] {name} installed to {extracted_path.name}")

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

    print("=== All external C libraries verified. ===\n")


if __name__ == "__main__":
    download_and_extract_externs()
