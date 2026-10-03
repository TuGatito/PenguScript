#!/usr/bin/env python3
"""Fuzz the SemVer parser and constraint matcher (roadmap 5.5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuzz_common import run_harness  # noqa: E402


def target(data: bytes) -> None:
    from pengu_semver import Version, parse_constraint, satisfies, select_version

    text = data.decode("utf-8", errors="replace")[:256]
    parse_constraint(text)
    v = Version.try_parse(text)
    if v is not None:
        satisfies(v, parse_constraint("^1.0.0"))
    select_version(["v1.0.0", "v2.3.4", text], text or "*")


if __name__ == "__main__":
    seeds = [b"^1.2.3", b"~0.1.0", b">=1.0.0, <2.0.0", b"*", b"1.2.3-rc1", b""]
    sys.exit(run_harness("semver", target, seeds, iterations=1500))
