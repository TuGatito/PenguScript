"""Roadmap Phase 7 / item 7.12 — `MIGRATION.md`, and the anti-divergence gate.

`pengu migrate` is deferred to 1.1 (roadmap item 4.14b) because the only candidate
rewrite — `and` as a list separator — cannot be resolved safely without type
information, and there is no corpus to validate a rewriter against
(`tests/migration/` does not exist).

So this item delivers the *document* that item needs, and makes its central claims
executable: the table of breaking changes is cross-checked against the changelog,
and every before/after pair in the `and` → `,` section is **compiled** to prove
that the documented before-form really fails and the after-form really works.

That is what stops the guide from becoming the kind of comfortable lie this phase
exists to remove: a migration guide that tells you to change something the
compiler accepts, or that omits a break the changelog records, fails the build.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.conftest import check_error, check_ok

REPO = Path(__file__).resolve().parent.parent
MIGRATION = REPO / "MIGRATION.md"
CHANGELOG = REPO / "CHANGELOG.md"


@pytest.fixture(scope="module")
def guide() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _changelog_breaking_versions() -> list[str]:
    """Versions whose changelog section contains a ``BREAKING`` marker.

    A version heading is ``## [x.y.z]``; the section runs to the next heading of
    the same rank.
    """
    text = CHANGELOG.read_text(encoding="utf-8")
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^## \[([^\]]+)\]", text, re.M)]
    found = []
    for i, (pos, version) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        if "BREAKING" in text[pos:end]:
            found.append(version)
    return found


def test_the_guide_exists_and_names_the_current_version(guide):
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert f"Current version: {version}" in guide, (
        f"MIGRATION.md does not declare the current version ({version})"
    )


def test_every_changelog_breaking_version_is_in_the_table(guide):
    """A break recorded in the changelog must appear in the migration table."""
    breaking = [v for v in _changelog_breaking_versions() if not v.startswith("Unreleased")]
    assert breaking, "the changelog no longer records any breaking change"
    table = guide.split("## 2. Breaking changes by version", 1)[1].split("## 3.", 1)[0]
    missing = [v for v in breaking if f"`{v}`" not in table]
    assert missing == [], (
        f"MIGRATION.md omits breaking releases that the changelog records: {missing}"
    )


def test_the_guide_claims_no_break_between_the_known_one_and_now(guide):
    """The "0.11.0 – 0.16.0: none" row must still be true."""
    breaking = [v for v in _changelog_breaking_versions() if not v.startswith("Unreleased")]
    assert breaking == ["0.10.0"], (
        f"a new breaking release appeared: {breaking}; update MIGRATION.md §2 and §3"
    )
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    assert f"`0.11.0` – `{version}`" in guide


# ---------------------------------------------------------------------------
# The documented before/after pairs, compiled
# ---------------------------------------------------------------------------

_WITH_TWO_PARAMS = (
    "weave f with a as int, b as int into void:\n    return\n"
)
_MAIN = "weave main into int:\n"


def test_documented_before_forms_really_fail():
    """Each 'Before' cell must be rejected, or the guide is telling you to fix nothing."""
    # `calling f with 1 and 2` -> E0005 ambiguous
    check_error(_WITH_TWO_PARAMS + _MAIN + "    calling f with 1 and 2\n    return 0\n",
                contains="Ambiguous 'and'")
    # `weave g with x as int and y as int` -> E0000 hint
    check_error("weave g with x as int and y as int into void:\n    return\n",
                contains="'and' is no longer a separator")
    # `declare d with a as int and b as int`
    check_error("declare d with a as int and b as int into void\n",
                contains="'and' is no longer a separator")
    # indented array row
    check_error(_MAIN + "    var xs as array of int with size 2 is [1 and 2]\n    return 0\n",
                contains="'and' is no longer a separator")


def test_documented_after_forms_really_work():
    check_ok(_WITH_TWO_PARAMS + _MAIN + "    calling f with 1, 2\n    return 0\n")
    check_ok("weave g with x as int, y as int into void:\n    return\n")


def test_the_two_surviving_and_forms_really_work():
    """`and` as a boolean operator and in pure name/type lists must keep working.

    This is the part an automated rewriter would get wrong, so it is pinned: if
    the compiler ever stopped accepting `shard T and U`, the guide's advice
    ("do not rewrite this") would become actively harmful.
    """
    check_ok(_MAIN + "    var a as bool is true\n    var b as bool is false\n"
                     "    var ok as bool is a and b\n    return 0\n")
    check_ok("rune Box shard T and U:\n    first as T\n    second as U\n")


def test_the_guide_documents_the_two_diagnostic_codes(guide):
    """The reader must be able to tell the ambiguous case from the plain one."""
    assert "E0000" in guide and "E0005" in guide
    assert "no longer a separator" in guide
    assert "Ambiguous 'and' after a call with arguments" in guide


# ---------------------------------------------------------------------------
# Links and the deferred rewriter
# ---------------------------------------------------------------------------

def test_the_guide_links_the_normative_documents():
    for target in ("CHANGELOG.md", "LANGUAGE.md", "docs/DEPRECATIONS.md", "VERSION"):
        assert (REPO / target).exists(), f"{target} is linked but missing"
        assert target in MIGRATION.read_text(encoding="utf-8")


def test_the_deferred_rewriter_is_stated(guide):
    """`pengu migrate` must be described as unavailable, not implied to exist."""
    assert "pengu migrate" in guide
    assert "not yet available" in guide.lower() or "not** part of" in guide
    assert "4.14b" in guide


def test_pengu_migrate_really_is_absent():
    """The guide's claim must match the CLI."""
    import subprocess
    import sys

    out = subprocess.run([sys.executable, str(REPO / "pengu_project.py"), "--help"],
                         capture_output=True, text=True, timeout=120).stdout
    assert "migrate" not in out, (
        "`pengu migrate` now exists; MIGRATION.md §5 and roadmap 7.12/4.14b must be updated"
    )
