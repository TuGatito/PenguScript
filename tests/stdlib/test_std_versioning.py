"""Every ``std/`` module exports its ``<MODULE>_VERSION`` marker.

``LANGUAGE.md`` §19.0 promises that each hand-written module exports a
``<MODULE>_VERSION`` constant holding the release that last changed it.  This
test is the executable version of that promise: it scans the modules rather
than a hand-maintained list, so a new module without a marker fails here.

The toolchain version itself is checked in the same place: ``VERSION`` is the
single source of truth, ``pengu_version.__version__`` reads it, and the frozen
fallback must not drift.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
STD = ROOT / "std"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pengu_version  # noqa: E402

#: A release version, optionally with a semver prerelease suffix (spark uses
#: ``0.8.0-spark``).
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")

MODULES = sorted(STD.glob("*.pengu"))
MODULE_IDS = [p.stem for p in MODULES]


def _declared_version(path: Path) -> str | None:
    const = f"{path.stem.upper()}_VERSION"
    pattern = re.compile(
        rf'^const {re.escape(const)} as string is "([^"]+)"',
        re.M,
    )
    matches = pattern.findall(path.read_text(encoding="utf-8"))
    assert len(matches) <= 1, f"{path.name} declares {const} {len(matches)} times"
    return matches[0] if matches else None


def test_the_module_list_is_not_empty_and_includes_the_new_modules():
    assert len(MODULES) >= 29, MODULE_IDS
    assert "functor" in MODULE_IDS
    assert "loom" in MODULE_IDS


@pytest.mark.parametrize("path", MODULES, ids=MODULE_IDS)
def test_every_module_exports_a_version_marker(path):
    version = _declared_version(path)
    assert version is not None, (
        f"std/{path.name} does not export "
        f"{path.stem.upper()}_VERSION (LANGUAGE.md §19.0)"
    )
    assert _VERSION_RE.match(version), (
        f"std/{path.name} exports {path.stem.upper()}_VERSION = {version!r}, "
        "which is not a valid release version"
    )


def test_functor_and_loom_are_at_the_current_release():
    assert _declared_version(STD / "functor.pengu") == "2.8.0"
    assert _declared_version(STD / "loom.pengu") == "2.8.0"


def test_the_version_file_and_the_fallback_agree():
    file_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert file_version == pengu_version.__version__
    assert file_version == pengu_version.FALLBACK_VERSION
    assert _VERSION_RE.match(file_version)
