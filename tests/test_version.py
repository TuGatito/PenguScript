"""Roadmap Phase 7 / item 7.5 — one version, everywhere.

``pengu_version.py`` has always claimed that "a unit test asserts that the
fallback, the file and the places that spell the version out stay in sync".
Until this module existed that claim was **false**: there was no
``tests/test_version.py`` at all, and AUDIT_1.0.md §13.4 found version drift in
13 files (``0.14.x`` in the two guides, the two language references, the parser
docstring, ``docs/PENGU_BUILD.md``, and more).

Two gates here:

* every *current-version claim* — the header of each normative document, the
  ``pengu.yaml`` examples, the parser docstring — must equal ``VERSION``;
* every *stale version token* in the scanned set must be an explicitly
  justified historical mention.  A new ``0.14.x`` fails unless it is recorded in
  ``HISTORICAL`` with a reason, which is how the drift is kept from creeping
  back in.

Phase 10 / item 10.7 hardened the second gate: it used to key on a hardcoded
``0.10``-``0.15`` range, so the moment ``VERSION`` moved past ``0.16`` the detector
would have gone **blind to the version just left** — a ``0.16.0`` claim could
have appeared anywhere in the scanned set unnoticed.  It is now *relative to*
``VERSION``: any token that parses as a semver older than the current one is
stale, and a per-token allowlist (rather than a whole-file exemption) records the
few mentions that are legitimate history.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

import pytest

from pengu_semver import Version

# Fast, subprocess-free unit tests: part of the `smoke` tier that
# `pengu selftest --smoke` runs. Keep it that way -- a smoke test that
# compiles C is not a smoke test.
pytestmark = pytest.mark.smoke

REPO = Path(__file__).resolve().parent.parent

VERSION_FILE = REPO / "VERSION"
VERSION = VERSION_FILE.read_text(encoding="utf-8").strip()

#: Matches any semver, including a pre-release suffix (`1.0.0-rc1`).
SEMVER = r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.\-]+)?"


# ---------------------------------------------------------------------------
# 1. The version machinery itself
# ---------------------------------------------------------------------------

def test_version_file_is_a_plain_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?", VERSION), VERSION


def test_fallback_version_matches_the_version_file():
    """A stale FALLBACK_VERSION only shows up in frozen builds — so pin it."""
    from pengu_version import FALLBACK_VERSION

    assert FALLBACK_VERSION == VERSION, (
        f"pengu_version.FALLBACK_VERSION is {FALLBACK_VERSION!r} but VERSION is "
        f"{VERSION!r}; frozen builds would report the wrong version"
    )


def test_resolved_version_matches_the_file():
    import pengu_version

    assert pengu_version.__version__ == VERSION
    assert pengu_version.__version_tag__ == f"v{VERSION}"


def test_packages_expose_the_single_source_of_truth():
    """The LSP package re-exports the version instead of hardcoding it."""
    import pengu_lsp
    import pengu_version

    assert pengu_lsp.__version__ == pengu_version.__version__


def test_pengu_lsp_does_not_hardcode_a_version():
    """AUDIT §13.4 said ``pengu_lsp/__init__.py:1`` claimed ``v0.6`` — refuted."""
    text = (REPO / "pengu_lsp" / "__init__.py").read_text(encoding="utf-8")
    assert "0.6" not in text
    assert "from pengu_version import __version__" in text


def test_pengu_parser_names_the_current_version():
    """Regression guard for ``pengu_parser.py``'s old ``v0.14.x`` docstring."""
    text = (REPO / "pengu_parser" / "pengu_parser.py").read_text(encoding="utf-8")
    assert "v0.14.x" not in text
    assert f"v{VERSION}" in text, "pengu_parser.py should name the version it implements"


# ---------------------------------------------------------------------------
# 2. Every current-version claim in the documentation
# ---------------------------------------------------------------------------

#: ``(relative path, regex whose group 1 is the version the file claims)``.
#: These are the places that assert *which version this document describes*.
CURRENT_VERSION_CLAIMS: tuple[tuple[str, str], ...] = (
    ("LANGUAGE.md", r"\*\*Version covered:\*\* PenguScript \*\*([0-9][^*]*)\*\*"),
    ("LANGUAGE_Spanish.md", r"\*\*Versión cubierta:\*\* PenguScript \*\*([0-9][^*]*)\*\*"),
    ("LANGUAGE.md", rf"^version: ({SEMVER})$"),
    ("LANGUAGE_Spanish.md", rf"^version: ({SEMVER})$"),
    ("LANGUAGE.md", r"e\.g\. `PenguScript (v[0-9][^`]*)`"),
    ("LANGUAGE_Spanish.md", r"p\. ej\. `PenguScript (v[0-9][^`]*)`"),
    ("LANGUAGE.md", r"behavior at version ([0-9]+\.[0-9]+\.x)"),
    ("LANGUAGE_Spanish.md", r"comportamiento del compilador en la versión ([0-9]+\.[0-9]+\.x)"),
    ("PenguScriptGuideEnglish.md", r"\*\*Covered version:\*\* PenguScript \*\*([0-9][^*]*)\*\*"),
    ("PenguScriptGuideSpanish.md", r"\*\*Versión cubierta:\*\* PenguScript \*\*([0-9][^*]*)\*\*"),
    ("docs/PENGU_BUILD.md", r"^# PenguScript (v[0-9][^\s]*) Build System"),
    ("docs/README_RELEASE.md", rf"pengus-({SEMVER})\.vsix"),
    # Phase 11 / F11-N2: these two were *not* in the table and drifted for three
    # releases. `CONTRIBUTING.md` still claimed `0.16.0` and the README badge still
    # said `1.0.0-rc1` when 1.0.0 shipped; neither was covered by any gate.
    ("CONTRIBUTING.md", r"Current version: \*\*([0-9][^*]*)\*\*"),
    ("README.md", rf"badge/version-({SEMVER})-blue"),
)


def _claims_current(claim: str) -> bool:
    """Is ``claim`` the current version?

    ``0.16.x`` is accepted as a claim on the ``0.16`` series; a claim with a
    full patch level must match exactly.
    """
    claim = claim.lstrip("v")
    if claim.endswith(".x"):
        return VERSION.startswith(claim[:-2] + ".")
    return claim == VERSION


@pytest.mark.parametrize("relpath,pattern", CURRENT_VERSION_CLAIMS)
def test_current_version_claim_matches_version_file(relpath, pattern):
    """Every document that names *its* version must name the current one."""
    text = (REPO / relpath).read_text(encoding="utf-8")
    matches = re.findall(pattern, text, re.M)
    assert matches, f"{relpath}: pattern {pattern!r} matched nothing"
    wrong = [m for m in matches if not _claims_current(m)]
    assert not wrong, (
        f"{relpath} claims a version that is not {VERSION}: {sorted(set(wrong))}"
    )


def test_the_claim_table_covers_the_drifted_files():
    """The table above must cover the files AUDIT §13.4 found drifted.

    Measured at ``355d946``, the files claiming a version other than the current
    one were the two language references, the two style guides, the two
    ``pengu.yaml`` examples, the parser docstring, ``docs/PENGU_BUILD.md`` and
    ``docs/README_RELEASE.md``.  ``pengu_lsp/__init__.py`` was listed by the
    audit but is **refuted**: it re-exports ``pengu_version`` and hardcodes
    nothing (asserted above).
    """
    files = {relpath for relpath, _ in CURRENT_VERSION_CLAIMS}
    assert len(files) >= 6, f"only {len(files)} files are gated: {sorted(files)}"
    for expected in ("LANGUAGE.md", "LANGUAGE_Spanish.md",
                     "PenguScriptGuideEnglish.md", "PenguScriptGuideSpanish.md",
                     "docs/PENGU_BUILD.md", "docs/README_RELEASE.md"):
        assert expected in files, f"{expected} is not gated for version drift"


# ---------------------------------------------------------------------------
# 3. Stale tokens must be justified historical mentions (ratchet)
# ---------------------------------------------------------------------------

#: Version tokens older than the current release that ARE allowed, because they
#: describe history rather than the present.  The value is the reason.  Adding a
#: file here is the deliberate act of saying "this mention is history", which is
#: what stops silent drift from creeping back in.
HISTORICAL: dict[str, str] = {
    "CHANGELOG.md": "the release history itself",
    "ROADMAP_1.0.0.md": "the historical 1.0.0 roadmap",
    "ROADMAP_1.1.md": "the live roadmap; records which phase fixed or measured what",
    "CLEANUP_PLAN.md": "historical cleanup plan",
    "AUDIT_1.0.md": "the audit's own measurements name the versions it found",
    "AUDIT_1.0_FASE3.md": "phase audit, historical measurements",
    "AUDIT_1.0_FASE6.md": "phase audit, historical measurements",
    "docs/DEPRECATIONS.md": "each alias records the version that deprecated it",
    "docs/PERFORMANCE.md": "benchmark numbers are attributed to the tree measured",
    "README.md": "records which release completed each stdlib batch",
    "CHEATSHEET.md": "notes when a syntax form changed (e.g. 'since 0.10.0')",
    "LANGUAGE.md": "notes when a feature was introduced or removed",
    "LANGUAGE_Spanish.md": "notes when a feature was introduced or removed",
    "pengu_parser/pengu_parser.py":
        "parse-error hints name the release (0.10.0) that removed the 'and' separator",
    "pengu_parser/pengu_infer.py":
        "diagnostic hints name the release (0.10.0) that changed 'and'/'or'",
    "pengu_bind.py": "binding templates reference upstream versions",
    "tests/regression/test_audit_v0150_fixes.py": "the 0.15.0 audit regression suite",
    "tests/test_pengu_paths.py": "the 0.15.0 multi-layout tests",
    "tests/regression/test_regression_0_12_0.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_0.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_1.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_2.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_3.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_4.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_5.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_6.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_7.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_8.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_9.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_10.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_11.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_12.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_13.py": "regression suite for that release",
    "tests/regression/test_regression_0_13_14.py": "regression suite for that release",
}

#: Files scanned for stale tokens: the normative documents, the guides, the
#: release/security documents and the version-aware toolchain sources.
#: ``pengu_project.py`` is deliberately **not** scanned: it is full of numeric
#: literals (``time.sleep(0.15)``, cache durations) that are not versions, and a
#: gate that cries wolf is a gate people learn to ignore.  Its version surface is
#: the ``pengu.yaml`` template, which is a *project* version and legitimately not
#: the toolchain version.
SCAN = (
    "LANGUAGE.md", "LANGUAGE_Spanish.md", "CHEATSHEET.md", "README.md",
    "PenguScriptGuideEnglish.md", "PenguScriptGuideSpanish.md",
    "RELEASE_CHECKLIST.md", "SECURITY.md", "BENCHMARKS.md",
    "pengu_parser/pengu_parser.py", "pengu_parser/pengu_infer.py",
    "pengu_version.py", "pengu_lsp/__init__.py",
)

#: A token that really looks like a release version: a three-component version
#: (optionally with a pre-release suffix), an ``N.M.x`` series, or an ``N.x``
#: series.  Deliberately not "any ``0.NN``": bare ``0.15`` appears in the tree as
#: a ``time.sleep`` argument and ``0.85`` as a benchmark timing, and a gate that
#: cries wolf is a gate people learn to ignore.
_VERSION_TOKEN_RE = re.compile(
    r"\bv?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?|\d+\.\d+\.x|\d+\.x)\b"
)

#: Tokens that legitimately name an older release **in a file that is otherwise
#: current**, keyed by ``(file, token)``.  This is deliberately narrower than
#: ``HISTORICAL`` (which exempts a whole file): a release document that names the
#: series it still supports should not stop being checked for *other* drift.
JUSTIFIED_TOKENS: dict[tuple[str, str], str] = {
    ("SECURITY.md", "1.1.x"):
        "the supported-version table records the series that reached end of "
        "support when 2.0.0 shipped; a support matrix has to name the series it "
        "drops",
    ("SECURITY.md", "0.16.x"):
        "the supported-version table records the series that reached end of "
        "support when 1.0.0 shipped; a support matrix has to name the series it "
        "drops",
    ("RELEASE_CHECKLIST.md", "0.16.0"):
        "the measured `--strict-c99` gap is stated for the release it was "
        "measured on, which is history",
    ("BENCHMARKS.md", "1.0.0-rc1"):
        "the published numbers are attributed to the tree they were measured on "
        "(`c8e07d9`, `1.0.0-rc1`); re-labelling them `1.0.0` without re-running "
        "the harness would be exactly the edited-number failure the page exists "
        "to prevent",
    ("BENCHMARKS.md", "1.99.0"):
        "the measurement-environment table names the Rust compiler it ran "
        "(`rustc 1.99.0`), which is not a PenguScript release at all",
}


def _as_version(token: str) -> Optional[Version]:
    """Parses a token from `_VERSION_TOKEN_RE`, mapping an ``x`` series to 0."""
    token = token.lstrip("v")
    if token.endswith(".x"):
        token = token[:-2] + (".0.0" if token.count(".") == 1 else ".0")
    return Version.try_parse(token)


def _stale_tokens(relpath: str) -> List[str]:
    """Version tokens in ``relpath`` that are **older** than ``VERSION``.

    Relative rather than a hardcoded range, so the ratchet cannot go blind when
    ``VERSION`` moves into a new series (Phase 10 / item 10.7).
    """
    text = (REPO / relpath).read_text(encoding="utf-8")
    current = Version.parse(VERSION)
    stale = set()
    for raw in _VERSION_TOKEN_RE.findall(text):
        parsed = _as_version(raw)
        if parsed is not None and parsed < current:
            stale.add(raw)
    return sorted(stale)


@pytest.mark.parametrize("relpath", SCAN)
def test_no_unjustified_stale_version_tokens(relpath):
    """A stale token in a scanned file must be recorded in HISTORICAL.

    This is the ratchet: a new ``0.14.x`` anywhere in the scanned set fails the
    build until someone writes down why it is there.
    """
    if relpath in HISTORICAL:
        pytest.skip(f"justified history: {HISTORICAL[relpath]}")
    stale = [token for token in _stale_tokens(relpath)
             if (relpath, token) not in JUSTIFIED_TOKENS]
    assert stale == [], (
        f"{relpath} mentions stale version(s) {stale}; either fix them to "
        f"{VERSION} or add the file to HISTORICAL/JUSTIFIED_TOKENS with a reason"
    )


def test_the_stale_detector_is_relative_to_the_current_version():
    """The gate must be able to see the series we just left (Phase 10 / 10.7).

    The previous implementation keyed on a hardcoded ``0.10``-``0.15`` range; moving
    ``VERSION`` to ``1.0.0-rc1`` would have made ``0.16.0`` invisible to it.
    """
    probe = REPO / "tests" / "_version_probe.tmp"
    probe.write_text(
        "current {v}\nolder 0.16.0\nmuch older 0.14.x\nfuture 9.9.9\n".format(v=VERSION),
        encoding="utf-8",
    )
    try:
        stale = _stale_tokens(probe.relative_to(REPO).as_posix())
    finally:
        probe.unlink()
    assert stale == ["0.14.x", "0.16.0"], stale


def test_justified_tokens_have_no_dead_entries():
    """A per-token exemption must still point at a token that is really there."""
    dead = []
    for (relpath, token), reason in JUSTIFIED_TOKENS.items():
        if not (REPO / relpath).is_file():
            dead.append(f"{relpath}: file missing ({reason})")
        elif token not in _stale_tokens(relpath):
            dead.append(f"{relpath}: {token!r} is no longer a stale token ({reason})")
    assert dead == [], "JUSTIFIED_TOKENS entries that no longer apply:\n  " + "\n  ".join(dead)


def test_historical_allowlist_has_no_dead_entries():
    """Every justified file must still exist and still contain a stale token.

    Otherwise the allowlist rots into a blanket exemption.
    """
    dead = []
    for relpath in HISTORICAL:
        path = REPO / relpath
        if not path.exists():
            dead.append(f"{relpath} (missing)")
        elif not _stale_tokens(relpath):
            dead.append(f"{relpath} (no stale token left)")
    assert dead == [], f"HISTORICAL entries that no longer apply: {dead}"


def test_the_scanned_set_is_not_empty():
    assert len(SCAN) >= 10
    present = [p for p in SCAN if (REPO / p).exists()]
    assert len(present) == len(SCAN), (
        f"scanned files that do not exist: {sorted(set(SCAN) - set(present))}"
    )
