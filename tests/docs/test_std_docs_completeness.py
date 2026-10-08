"""Roadmap Phase 4 / §4.3 — standard-library documentation audit.

The roadmap asked to "convert every ``#`` comment in ``std/*.d.pengu`` to
``##``".  That premise is refuted: in 0.15.0 the hand-written bindings were
migrated ``##`` → ``#`` to match the ``pengu_bind`` generator, and both the
checker (``_extract_preceding_doc``) and the LSP hover read ``#`` and ``##`` as
doc text.  What this file enforces instead is:

1. every ``std/`` module carries a header doc block (100%);
2. the number of declarations with their own doc comment never regresses
   (a ratchet, so documentation can only improve);
3. generated bindings keep the ``#`` spelling (the ``##`` lines are only the
   two-line generator banner).
"""

import pathlib
import re
from typing import Dict, List, Tuple

import pytest

from tests.conftest import REPO

STD = REPO / "std"
_DECL_RE = re.compile(r"^(declare|weave|rune|echo|omen|alias|seal|const)\b")

# Ratchet: measured documented/total per declaration kind.  The test fails if a
# future change documents fewer declarations than today; it never demands a
# fixed 100% because generated bindings depend on the upstream header comments.
_BASELINE_DOCUMENTED: Dict[str, int] = {
    "declare": 630,
    # Fase 6 item 6.7 raised `atlas` (36 -> 151) and `scrolls` (23 -> 89) to
    # 100% of their public `weave`s; `arithmancy` was already at 100%. The
    # ratchet is raised to the measured value so the gain cannot be given back.
    "weave": 1314,
    "const": 118,
    "alias": 50,
    "rune": 91,
    "omen": 3,
}


def _modules() -> List[pathlib.Path]:
    return sorted(STD.glob("*.pengu"))


def _own_doc(lines: List[str], i: int) -> bool:
    j = i - 1
    while j >= 0 and lines[j].strip() == "":
        j -= 1
    return j >= 0 and lines[j].strip().startswith("#")


def _coverage() -> Dict[str, Tuple[int, int]]:
    """kind -> (documented, total) across every std module."""
    stats: Dict[str, List[int]] = {}
    for p in _modules():
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            m = _DECL_RE.match(ln)
            if not m:
                continue
            kind = m.group(1)
            entry = stats.setdefault(kind, [0, 0])
            entry[1] += 1
            if _own_doc(lines, i):
                entry[0] += 1
    return {k: (v[0], v[1]) for k, v in stats.items()}


def _has_header_doc(path: pathlib.Path) -> bool:
    for raw in path.read_text(encoding="utf-8").splitlines()[:60]:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            return True
        return False  # first real line is not a comment
    return False


def test_every_std_module_has_a_header_doc_block():
    missing = [p.name for p in _modules() if not _has_header_doc(p)]
    assert not missing, f"std modules without a header doc block: {missing}"


def test_std_doc_coverage_does_not_regress():
    cov = _coverage()
    regressions = []
    for kind, floor in _BASELINE_DOCUMENTED.items():
        documented, total = cov.get(kind, (0, 0))
        if documented < floor:
            regressions.append(f"{kind}: {documented}/{total} < baseline {floor}")
    assert not regressions, (
        "standard-library documentation regressed:\n  " + "\n  ".join(regressions)
    )


def test_doc_coverage_report_is_consistent():
    """Sanity: documented counts never exceed totals, and weave is well covered."""
    cov = _coverage()
    for kind, (documented, total) in cov.items():
        assert 0 <= documented <= total, f"{kind}: {documented}/{total}"
    weave_doc, weave_total = cov["weave"]
    assert weave_total > 0
    # The language-level API is the priority: functions stay above 80%.
    assert weave_doc / weave_total >= 0.80, f"weave coverage dropped to {weave_doc}/{weave_total}"


def test_generated_bindings_keep_hash_doc_convention():
    """``##`` is allowed for the banner/module header; declarations use ``#``."""
    offenders = []
    for path in sorted(STD.glob("*.d.pengu")):
        lines = path.read_text(encoding="utf-8").splitlines()
        first_decl = next(
            (i for i, ln in enumerate(lines) if _DECL_RE.match(ln)), len(lines)
        )
        for i, ln in enumerate(lines):
            if i >= first_decl and ln.startswith("##"):
                offenders.append(f"{path.name}:{i + 1}: {ln[:60]}")
    assert not offenders, (
        "`##` used on a declaration doc in .d.pengu "
        f"(use `#`): {offenders[:10]}"
    )
