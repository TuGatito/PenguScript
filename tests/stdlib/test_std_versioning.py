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

# Constants that intentionally carry an **upstream API** version rather than the
# toolchain release.  `std.spark` is the only pure module that does this: its
# SPARK_VERSION is the spark API revision ("0.7.0-spark") and STD_VERSION the
# legacy stdlib tag it was written against.  Everything else tracks VERSION.
_API_VERSION_ALLOWLIST = {"SPARK_VERSION", "STD_VERSION"}


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


def test_toolchain_tracking_versions_match_the_toolchain():
    mismatched = []
    for path in _hand_written_modules():
        text = path.read_text(encoding="utf-8")
        for name, value in _VERSION_RE.findall(text):
            if name in _API_VERSION_ALLOWLIST:
                continue
            if value != PENGU_VERSION:
                mismatched.append(f"{path.name}: {name} = {value} != {PENGU_VERSION}")
    assert not mismatched, "std module version drift:\n  " + "\n  ".join(mismatched)


def test_module_versions_are_valid_versions():
    from pengu_semver import Version

    for path in _hand_written_modules():
        for name, value in _VERSION_RE.findall(path.read_text(encoding="utf-8")):
            assert Version.try_parse(value) is not None, f"{path.name}: bad {name} = {value!r}"


# ---------------------------------------------------------------------------
# Phase 10 / F10-N13 — the in-language test programs pin the same constants
# ---------------------------------------------------------------------------

#: `calling spark.assert with (loom.LOOM_VERSION == "1.0.0-rc1")`
_PROGRAM_ASSERTION_RE = re.compile(r'(\w+_VERSION)\s*==\s*"([^"]*)"')

STD_PROGRAMS = REPO / "tests" / "std_programs"

#: The conformance corpus keeps a second copy of the same programs, and that is
#: the one `tests/test_conformance.py` actually executes.  The 1.1.0 bump updated
#: only `tests/std_programs/`, so the conformance copies stayed at "1.0.0" and
#: every one of them died with `[PANIC] Assertion failed` on all three platforms
#: (14 red tests that named nothing).  Scanning both directories makes the next
#: bump fail once, here, with the file and the constant.
PROGRAM_DIRS = (STD_PROGRAMS, REPO / "tests" / "conformance" / "std_programs")


def _program_assertions():
    """Yields ``(relative path, constant, value)`` for every program assertion."""
    for directory in PROGRAM_DIRS:
        for path in sorted(directory.glob("*.pengu")):
            for name, value in _PROGRAM_ASSERTION_RE.findall(path.read_text(encoding="utf-8")):
                yield path.relative_to(REPO), name, value


def test_the_in_language_std_programs_assert_the_current_version():
    """`tests/**/std_programs/test_<mod>_extended.pengu` asserts `<MOD>_VERSION`.

    Measured during Phase 10: bumping `VERSION` to `1.0.0-rc1` updated the 26
    modules but not the 14 programs that assert their constants, so **28**
    `test_std_*_extended` runs died with `[PANIC] Assertion failed` plus two more
    in `test_cli_strict_c99.py` — a version bump that reported 42 failures in
    five different suites, none of which named the real cause (F10-N13). This
    gate makes the next bump fail **once**, here, with the file and the constant.
    """
    mismatched = [
        f"{path}: {name} == {value!r} != {PENGU_VERSION!r}"
        for path, name, value in _program_assertions()
        if name not in _API_VERSION_ALLOWLIST and value != PENGU_VERSION
    ]
    assert not mismatched, (
        "std test programs pin a version that is not the toolchain's:\n  "
        + "\n  ".join(mismatched)
    )


def test_the_program_gate_is_not_vacuous():
    """At least one program must really assert a toolchain-tracking constant."""
    found = [
        str(path)
        for path, name, _value in _program_assertions()
        if name not in _API_VERSION_ALLOWLIST
    ]
    assert len(found) >= 10, (
        f"only {len(found)} program version assertions found; the gate would pass "
        "for the wrong reason"
    )
