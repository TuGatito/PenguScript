#!/usr/bin/env python3
"""Compute or check the SHA-256 digests of the external C library archives.

``extern_manifest.py`` pins one digest per dependency and refuses to extract an
archive whose stream does not hash to it (Roadmap 2.0 / Phase 9, item 9.1).  The
digests are *data*, not a build step: they are computed once, reviewed and
committed, so a normal build never re-downloads 300 MB to re-derive them.

Usage::

    python scripts/extern_digests.py --check     # CI/local gate, downloads nothing
    python scripts/extern_digests.py --download  # re-derive the table (network)
    python scripts/extern_digests.py --update    # rewrite SHA256 in extern_manifest.py

``--check`` verifies that every entry in ``MANIFEST`` has a well-formed digest
and that the pinned table has no orphan keys.  It deliberately does **not** hash
the extracted trees: the digest is of the *archive stream*, which is what the
release actually downloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from extern_manifest import EXPECTED_DIRS, MANIFEST  # noqa: E402

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_BLOCK_START = "SHA256: Dict[str, str] = {"
_BLOCK_END = "}"


def check() -> int:
    """Fail when the pinned table and the manifest disagree."""
    problems = []
    missing = [name for name, entry in MANIFEST.items() if not entry.get("sha256")]
    for name in missing:
        problems.append(f"{name}: no sha256 pinned")
    for name, entry in MANIFEST.items():
        digest = entry.get("sha256", "")
        if digest and not _HEX64.match(digest):
            problems.append(f"{name}: malformed sha256 {digest!r}")
    orphans = set(EXPECTED_DIRS) - set(MANIFEST)
    for name in sorted(orphans):
        problems.append(f"{name}: EXPECTED_DIRS entry with no MANIFEST entry")

    for name, entry in MANIFEST.items():
        print(f"  {name:<16} {entry.get('url', '?')}")
        print(f"  {'':<16} sha256={entry.get('sha256') or 'MISSING'}")

    if problems:
        print("\n[FAIL] extern manifest digests are incomplete:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"\n[OK] {len(MANIFEST)} dependencies with a pinned SHA-256")
    return 0


def download(json_path: Path | None = None) -> dict:
    """Download every archive once and return ``{name: sha256}``.

    Each digest is printed (and optionally appended to ``json_path``) as soon as
    it is known, so an interrupted run keeps the work it already did.
    """
    digests: dict = {}
    if json_path and json_path.is_file():
        digests = json.loads(json_path.read_text(encoding="utf-8"))
    for name, entry in MANIFEST.items():
        if name in digests:
            print(f"  {name:<16} {digests[name]} (cached)", flush=True)
            continue
        url = entry["url"]
        print(f"  [DOWNLOADING] {name} ...", flush=True)
        digest = hashlib.sha256()
        req = urllib.request.Request(
            url, headers={"User-Agent": "PenguScript-ExternDigests/1.0"}
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            while True:
                buf = resp.read(1024 * 1024)
                if not buf:
                    break
                digest.update(buf)
        digests[name] = digest.hexdigest()
        print(f"  {name:<16} {digests[name]}", flush=True)
        if json_path:
            json_path.write_text(
                json.dumps(digests, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    return digests


def update(digests: dict) -> int:
    """Rewrite the SHA256 values inside ``extern_manifest.py`` in place."""
    path = ROOT_DIR / "extern_manifest.py"
    text = path.read_text(encoding="utf-8")
    for name, digest in digests.items():
        pattern = re.compile(
            r'("%s":\s*\{\s*"url":\s*"[^"]+",\s*"sha256":\s*")[0-9a-f]*(")' % re.escape(name)
        )
        text, count = pattern.subn(lambda m: m.group(1) + digest + m.group(2), text)
        if count != 1:
            print(f"[FAIL] could not rewrite {name} ({count} matches)", file=sys.stderr)
            return 1
    path.write_text(text, encoding="utf-8")
    print(f"[OK] wrote {len(digests)} digests into {path}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="validate the pinned table")
    group.add_argument("--download", action="store_true", help="re-derive the digests")
    group.add_argument("--update", action="store_true", help="re-derive and rewrite the table")
    parser.add_argument(
        "--cache", type=Path, default=ROOT_DIR / "build" / "extern_digests.json",
        help="where to keep already-derived digests so an interrupted run resumes",
    )
    args = parser.parse_args(argv)

    if args.check:
        return check()
    digests = download(args.cache)
    if args.update:
        return update(digests)
    for name, digest in digests.items():
        print(f'{name}: "{digest}",')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
