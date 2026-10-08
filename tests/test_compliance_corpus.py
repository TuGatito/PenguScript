#!/usr/bin/env python3
"""The compliance corpus, after its migration into ``tests/conformance/``.

The 53 ``NNN-slug.pengu`` programs that used to live in ``tests/compliance/`` are
now conformance cases under ``tests/conformance/compliance/``, driven by the batch
runner. Compiling and executing them is ``tests/test_conformance.py``'s job: one
bundle per collision-free group, instead of 53 separate check+build+run cycles.

What is kept here is the guarantee that made the corpus worth having in the first
place: **every case pins a real, numbered section of ``LANGUAGE.md``, with the
title that document actually uses.** That is a documentation-coverage gate, not a
runtime one, and losing it would let the corpus drift away from the language it
claims to pin, silently.

Roadmap 10.3 ("the corpus is also the compiler matrix's workload") survives as
``test_the_compiler_override_reaches_the_runner``: the matrix itself runs in
``.github/workflows/compliance.yml`` by setting ``PENGU_TEST_CC``.

Nothing here inspects source text or generated C to decide whether a program is
correct: every gate compiles, executes or measures (Roadmap Annex C, rule C1).
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest

from tests.conftest import REPO
from tests.test_conformance import CONFORMANCE_DIR, discover_cases

MANIFEST_PATH = CONFORMANCE_DIR / "_manifest.json"
LANGUAGE_MD = REPO / "LANGUAGE.md"

#: The corpus was 25 programs before the migration and 53 after, so this floor
#: only ratchets up in practice.
MIN_PROGRAMS = 25

#: ``## 12. Optionals & errors`` / ``### 7.4 `judge` — pattern matching``
_HEADING_RE = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")


def _manifest() -> dict:
    assert MANIFEST_PATH.is_file(), (
        f"{MANIFEST_PATH.relative_to(REPO)} is missing; "
        f"run: python tools/gen_conformance_deps.py"
    )
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _pinned_cases() -> dict:
    """Manifest entries for the migrated compliance corpus, keyed by case id."""
    return {
        case_id: meta
        for case_id, meta in _manifest().items()
        if isinstance(meta, dict) and meta.get("feature") == "compliance"
    }


def language_sections() -> dict:
    """``{section number: heading title}`` for every numbered heading.

    This parser used to live in ``tests/compliance/run_all.py``; it moved here when
    that directory did, because this gate is now the only thing that needs it. It
    keeps that parser's behaviour exactly: trailing ``#`` decorations are stripped
    from the title, and the *first* heading wins when a number repeats.
    """
    sections: dict = {}
    for line in LANGUAGE_MD.read_text(encoding="utf-8").splitlines():
        match = _HEADING_RE.match(line)
        if match:
            title = re.sub(r"\s+#+\s*$", "", match.group(3)).strip()
            sections.setdefault(match.group(2), title)
    return sections


# --------------------------------------------------------------------------
# The documentation-coverage gate
# --------------------------------------------------------------------------


def test_the_pinned_corpus_is_big_enough():
    pinned = _pinned_cases()
    assert len(pinned) >= MIN_PROGRAMS, (
        f"only {len(pinned)} migrated compliance case(s), expected >= {MIN_PROGRAMS}"
    )


def test_every_case_pins_a_real_language_md_section():
    """Each pinned section must exist in LANGUAGE.md, with the same title."""
    sections = language_sections()
    assert sections, "no numbered headings parsed out of LANGUAGE.md"

    missing, mismatched = [], []
    for case_id, meta in sorted(_pinned_cases().items()):
        section = str(meta.get("section", ""))
        title = meta.get("title", "")
        if not section:
            missing.append(f"{case_id}: no section recorded")
        elif section not in sections:
            missing.append(f"{case_id}: section {section}")
        elif sections[section] != title:
            mismatched.append(
                f"{case_id}: section {section} title {title!r} != LANGUAGE.md "
                f"{sections[section]!r}"
            )
    assert not missing, (
        "cases pin sections that LANGUAGE.md does not have: " + ", ".join(missing)
    )
    assert not mismatched, (
        "case titles disagree with LANGUAGE.md:\n  " + "\n  ".join(mismatched)
    )


def test_pinned_sections_are_distinct_ish():
    """No section may be pinned by more than two cases, and most must be covered."""
    counts: dict = {}
    for meta in _pinned_cases().values():
        section = str(meta.get("section", ""))
        counts[section] = counts.get(section, 0) + 1
    reused = {section: n for section, n in counts.items() if n > 2}
    assert not reused, f"sections pinned by more than two cases: {reused}"
    assert len(counts) >= MIN_PROGRAMS, (
        f"only {len(counts)} distinct LANGUAGE.md sections covered, "
        f"expected >= {MIN_PROGRAMS}"
    )


def test_every_pinned_case_exists_and_says_what_it_pins():
    """A manifest entry with no case, or no recorded pin, is a lie about coverage."""
    on_disk = {case.case_id for case in discover_cases()}
    problems = []
    for case_id, meta in sorted(_pinned_cases().items()):
        if case_id not in on_disk:
            problems.append(f"{case_id}: in _manifest.json but not a case on disk")
        if not str(meta.get("pins", "")).strip():
            problems.append(f"{case_id}: does not record what it pins")
        if not str(meta.get("migrated-from", "")).strip():
            problems.append(f"{case_id}: does not record where it came from")
    assert not problems, "\n  ".join(["compliance manifest problems:"] + problems)


def test_the_corpus_still_covers_the_compiler_matrix_workload():
    """The old corpus was also the gcc/clang matrix's workload (roadmap 10.3).

    The matrix now runs the batch runner with ``PENGU_TEST_CC``, so what has to
    keep working is that the override reaches the compiler selection. A `--cc`
    that is parsed and dropped would leave the workflow green while compiling with
    the default compiler — which is exactly the failure this pins.
    """
    available = [cc for cc in ("gcc", "clang") if shutil.which(cc)]
    if not available:
        pytest.skip("neither gcc nor clang is installed")

    import tests.test_conformance as runner

    requested = available[0]
    original = os.environ.get("PENGU_TEST_CC")
    os.environ["PENGU_TEST_CC"] = requested
    try:
        chosen = runner._pick_cc()
    finally:
        if original is None:
            os.environ.pop("PENGU_TEST_CC", None)
        else:
            os.environ["PENGU_TEST_CC"] = original

    assert chosen, f"PENGU_TEST_CC={requested} selected no compiler"
    assert requested in chosen, f"PENGU_TEST_CC={requested} selected {chosen}"
