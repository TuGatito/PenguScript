"""Roadmap Phase 4 / §4.9 — standard-library versioning policy.

The stdlib is coupled to the compiler in 1.x (decision D6), and every
hand-written module exports a ``<MODULE>_VERSION`` constant carrying the
toolchain version.  This test enforces that contract.
"""

import pathlib
import re

from pengu_version import __version__ as PENGU_VERSION
from tests.conftest import REPO

STD = REPO / "std"
_VERSION_RE = re.compile(r'^const\s+(\w+_VERSION)\s+as\s+string\s+is\s+"([^"]*)"', re.M)


def _hand_written_modules():
    return sorted(p for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu"))


def test_every_hand_written_module_exports_its_version():
    missing = []
    for path in _hand_written_modules():
        text = path.read_text(encoding="utf-8")
        expected = f"{path.stem.upper()}_VERSION"
        if not re.search(rf'^const\s+{re.escape(expected)}\s+as\s+string\b', text, re.M):
            missing.append(f"{path.name} (expected {expected})")
    assert not missing, "std modules without their version constant:\n  " + "\n  ".join(missing)


def test_module_versions_match_the_toolchain():
    mismatched = []
    for path in _hand_written_modules():
        text = path.read_text(encoding="utf-8")
        for _name, value in _VERSION_RE.findall(text):
            if value != PENGU_VERSION:
                mismatched.append(f"{path.name}: {value} != {PENGU_VERSION}")
    assert not mismatched, "std module version drift:\n  " + "\n  ".join(mismatched)


def test_module_versions_are_valid_versions():
    from pengu_semver import Version

    for path in _hand_written_modules():
        for _name, value in _VERSION_RE.findall(path.read_text(encoding="utf-8")):
            assert Version.try_parse(value) is not None, f"{path.name}: bad version {value!r}"
