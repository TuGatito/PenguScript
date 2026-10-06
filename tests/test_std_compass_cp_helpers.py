"""Roadmap Phase 6 / item 6.11 — ``compass.cp_*``: decision and measurement.

The roadmap asked to prefix `compass`'s 32 `cp_*` helpers with `_` so that "the
public surface is reduced to the documented API".  The Phase 6 audit called them
"internal helpers exposed alongside the public API".

Measurement taken before acting:

* **No external user exists in this repository.** Nothing outside
  `std/compass.pengu` references any `compass.cp_*` symbol (checked across
  `std/`, `tests/`, `benches/`, `docs/` and the root guides).
* **They are not undocumented.** All 32 carry their own doc comment, and they
  are catalogued as part of the module's `weave` surface.
* **Internal use is heavy.** ~169 reference sites inside `compass.pengu`, which
  means the rename is mechanical but touches a large fraction of the module.
* **They are load-bearing by design.** `CHANGELOG.md` records that the `cp_*`
  split exists deliberately ("clean internal `cp_*` architectural decoupling
  preventing method/weave symbol collision in codegen").

Decision: **deferred to 1.1 with this measurement**, not closed.  Unlike
`tally`/`scrolls` (whose aliases are marked deprecated), the `cp_*` names carry
no `@deprecated` marker and are already documented, so renaming them is a
**breaking change for any existing 0.16 user code** that calls them, with no
correctness benefit.  It belongs in a minor release that can state the break and
ship deprecation aliases, alongside the `tally`/`loom` unification (item 6.5),
which is the same class of change.

Reopening criterion: the 1.1 public-surface cleanup, where `cp_*` becomes
`_cp_*` (or stays, promoted to a documented low-level namespace) together with
alias shims and a CHANGELOG entry.

This file pins the measurement so the deferral stays honest: if someone later
starts importing `cp_*` from outside, the "no users" premise is gone and the
decision must be revisited.
"""

import re
from pathlib import Path

import pytest

from tests.conftest import REPO

STD = REPO / "std"
COMPASS = STD / "compass.pengu"

_CP_DECL = re.compile(r"^weave\s+(cp_[A-Za-z0-9_]*)", re.M)
_CP_ANY = re.compile(r"\bcp_[A-Za-z0-9_]*\b")


def _cp_helpers():
    return sorted(set(_CP_DECL.findall(COMPASS.read_text(encoding="utf-8"))))


def test_compass_still_has_the_cp_helpers():
    helpers = _cp_helpers()
    assert len(helpers) == 32, (
        f"expected the 32 catalogued cp_* helpers, found {len(helpers)}: {helpers}"
    )


def test_cp_helpers_have_no_user_outside_compass():
    """The deferral's key premise: renaming would break nobody in-repo."""
    offenders = []
    roots = [STD, REPO / "tests", REPO / "benches", REPO / "docs"]
    myself = Path(__file__).resolve()
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in (".pengu", ".py", ".md"):
                continue
            if path.resolve() in (COMPASS.resolve(), myself):
                continue  # compass itself, and this test's own pattern text
            text = path.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"compass\.(cp_[A-Za-z0-9_]*)", text):
                offenders.append(f"{path.relative_to(REPO)}: {m.group(0)}")
    assert not offenders, (
        "compass.cp_* now has external callers, so the 1.1 deferral premise is "
        "gone and item 6.11 must be revisited:\n  " + "\n  ".join(offenders)
    )


def test_cp_helpers_are_all_documented():
    """They are public-looking, not undocumented internals."""
    lines = COMPASS.read_text(encoding="utf-8").splitlines()
    undocumented = []
    for i, line in enumerate(lines):
        m = re.match(r"^weave\s+(cp_[A-Za-z0-9_]*)", line)
        if not m:
            continue
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        if not (j >= 0 and lines[j].strip().startswith("#")):
            undocumented.append(m.group(1))
    assert not undocumented, f"cp_* helpers without a doc comment: {undocumented}"


def test_cp_helpers_are_used_heavily_inside_compass():
    """Justifies treating the rename as a real change, not a one-liner."""
    text = COMPASS.read_text(encoding="utf-8")
    # Every declaration plus every call site.
    occurrences = len(_CP_ANY.findall(text))
    assert occurrences > 100, (
        f"expected heavy internal use of cp_* (found {occurrences} mentions); "
        "if this dropped, the deferral rationale needs re-measuring"
    )
