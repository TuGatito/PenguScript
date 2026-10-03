#!/usr/bin/env python3
"""scripts/release_version.py — single source of truth for the release version.

Walks `CHANGELOG.md` and returns the **first released** version, skipping the
`[Unreleased]` sections.

Why this exists: the original CI snippet used

    re.search(r"^##\\s*\\[([^\\]]+)\\]", content, re.MULTILINE)

which matches the *first* `## [...]` heading.  Once the changelog gained several
`## [Unreleased] — FASE N` headers above the real release, that would have
created and pushed a **`vUnreleased`** tag on the next push to `main`.  Both
ci.yml (tagging) and release.yml (release notes) now call this script so they can
never disagree about the version.

Usage::

    python scripts/release_version.py                       # print the tag
    python scripts/release_version.py --github-output FILE   # write GH outputs
    python scripts/release_version.py --notes-file out.md    # write the section
    python scripts/release_version.py --json                 # machine readable

Exits non-zero with a clear message when there is no released version yet.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional

REPO = Path(__file__).resolve().parent.parent

# A version heading: "## [1.0.0] - 2026-10-02", "## [1.0.0-rc1]" or the
# "## [Unreleased] — FASE 6" style used by this repository.  The separator may be
# a hyphen, en dash or em dash, so all three are accepted (missing the em dash
# silently skipped the [Unreleased] headings entirely).
_HEADING_RE = re.compile(
    r"^##\s*\[(?P<version>[^\]]+)\]\s*(?:[\-\u2013\u2014]\s*(?P<suffix>.*))?$",
    re.MULTILINE,
)

# Anything that is not a real release.
_NON_RELEASE = {"unreleased", "tbd", "next", "wip"}


class VersionNotFound(RuntimeError):
    """No released version in the changelog."""


def parse_changelog(text: str) -> Dict[str, str]:
    """Returns the first released version's metadata.

    Keys: ``version``, ``tag_name``, ``title``, ``suffix``, ``body``.
    """
    headings = list(_HEADING_RE.finditer(text))
    if not headings:
        raise VersionNotFound(
            "no '## [version]' heading found in CHANGELOG.md"
        )

    chosen: Optional[re.Match] = None
    for match in headings:
        if match.group("version").strip().lower() not in _NON_RELEASE:
            chosen = match
            break
    if chosen is None:
        raise VersionNotFound(
            "CHANGELOG.md only contains [Unreleased] sections; "
            "promote the release before tagging"
        )

    version = chosen.group("version").strip()
    suffix = (chosen.group("suffix") or "").strip()

    # Section body runs until the next "## [" heading.
    nxt = next((h for h in headings if h.start() > chosen.start()), None)
    body = text[chosen.end(): nxt.start() if nxt else len(text)].strip()

    return {
        "version": version,
        "tag_name": f"v{version}",
        "title": f"PenguScript v{version}" + (f" - {suffix}" if suffix else ""),
        "suffix": suffix,
        "body": body + "\n" if body else "",
    }


def is_prerelease(version: str) -> bool:
    """`1.0.0-rc1`, `-beta`, `-alpha` and any other `-suffix` are prereleases."""
    return "-" in version.split("+")[0]


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Extract the release version from CHANGELOG.md")
    ap.add_argument("--changelog", default=str(REPO / "CHANGELOG.md"))
    ap.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT"),
                    help="File to append GitHub Actions outputs to")
    ap.add_argument("--notes-file", default=None, help="Write the section body here")
    ap.add_argument("--json", action="store_true", help="Print the metadata as JSON")
    args = ap.parse_args(argv)

    try:
        text = Path(args.changelog).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"::error::cannot read {args.changelog}: {exc}", file=sys.stderr)
        return 2

    try:
        info = parse_changelog(text)
    except VersionNotFound as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    info["prerelease"] = "true" if is_prerelease(info["version"]) else "false"

    if args.notes_file:
        Path(args.notes_file).write_text(info["body"], encoding="utf-8")

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as out:
            for key in ("version", "tag_name", "title", "prerelease"):
                out.write(f"{key}={info[key]}\n")

    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(info["tag_name"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
