"""Roadmap Phase 4 / §4.2 — SemVer parsing, constraints and selection."""

import pytest

from pengu_semver import (
    Constraint,
    SemVerError,
    Version,
    parse_constraint,
    satisfies,
    select_version,
)

# Fast, subprocess-free unit tests: part of the `smoke` tier that
# `pengu selftest --smoke` runs. Keep it that way -- a smoke test that
# compiles C is not a smoke test.
pytestmark = pytest.mark.smoke


def test_parse_version_forms():
    assert Version.parse("1.2.3") == Version(1, 2, 3)
    assert Version.parse("v1.2.3") == Version(1, 2, 3)
    assert Version.parse("1.2") == Version(1, 2, 0)
    assert Version.parse("1") == Version(1, 0, 0)
    assert Version.parse("1.2.3-rc1").prerelease == "rc1"
    assert Version.parse("1.2.3+build5") == Version(1, 2, 3)
    with pytest.raises(SemVerError):
        Version.parse("not-a-version")


def test_prerelease_outranks_lower_than_release():
    assert Version.parse("1.0.0-rc1") < Version.parse("1.0.0")
    assert Version.parse("1.0.0-alpha") < Version.parse("1.0.0-beta")
    assert version_lt("1.9.0", "1.10.0")


def version_lt(a, b):
    return Version.parse(a) < Version.parse(b)


def test_caret_constraint():
    c = parse_constraint("^1.2.0")
    assert satisfies(Version.parse("1.2.0"), c)
    assert satisfies(Version.parse("1.9.9"), c)
    assert not satisfies(Version.parse("2.0.0"), c)
    assert not satisfies(Version.parse("1.1.9"), c)
    # 0.x narrows.
    assert satisfies(Version.parse("0.2.5"), parse_constraint("^0.2.3"))
    assert not satisfies(Version.parse("0.3.0"), parse_constraint("^0.2.3"))


def test_tilde_constraint():
    c = parse_constraint("~1.2.3")
    assert satisfies(Version.parse("1.2.9"), c)
    assert not satisfies(Version.parse("1.3.0"), c)
    assert not satisfies(Version.parse("1.2.2"), c)


def test_range_constraint():
    c = parse_constraint(">=1.0.0, <2.0.0")
    assert satisfies(Version.parse("1.5.0"), c)
    assert not satisfies(Version.parse("2.0.0"), c)
    assert not satisfies(Version.parse("0.9.9"), c)


def test_exact_and_wildcard():
    assert satisfies(Version.parse("1.2.3"), parse_constraint("=1.2.3"))
    assert satisfies(Version.parse("1.2.3"), parse_constraint("1.2.3"))
    assert not satisfies(Version.parse("1.2.4"), parse_constraint("=1.2.3"))
    assert satisfies(Version.parse("9.9.9"), parse_constraint("*"))
    assert satisfies(Version.parse("9.9.9"), parse_constraint(""))


def test_invalid_constraint_raises():
    with pytest.raises(SemVerError):
        parse_constraint(">>1.0")


def test_select_version_picks_highest_match():
    tags = ["v1.0.0", "v1.2.0", "v1.10.0", "v2.0.0", "not-a-tag", "v1.3.0-rc1"]
    best = select_version(tags, "^1.0.0")
    assert best is not None
    tag, ver = best
    assert tag == "v1.10.0" and ver == Version(1, 10, 0)
    assert select_version(tags, "^3.0.0") is None
    assert select_version(tags, "*")[0] == "v2.0.0"


def test_select_version_ignores_prerelease_unless_asked():
    tags = ["v1.0.0", "v1.1.0-rc1"]
    assert select_version(tags, "^1.0.0")[0] == "v1.0.0"
    assert select_version(tags, ">=1.1.0-rc1")[0] == "v1.1.0-rc1"
