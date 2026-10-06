"""Roadmap Phase 6 — the stdlib's deprecations are documented, not enforced.

Phase 6 item 6.15 asked for a deprecation list with retirement versions. While
building it, a more important fact surfaced: the toolchain has a **real**
`@deprecated("reason")` attribute that emits `W0006`, but the standard library
does not use it anywhere. Every one of the 90 markers in `std/` is a
`## @deprecated Use X instead.` doc comment, and the checker reads the parsed
attribute, not the docstring — so no stdlib alias currently warns.

This is a deliberate 1.0 decision, not an oversight (see `docs/DEPRECATIONS.md`
for the three blockers). These tests pin the decision so it stays measured
rather than accidental:

* the count of real attributes in `std/` is zero;
* the count of docstring markers is non-zero and unchanged in kind;
* the documentation states the "documented, not enforced" caveat, so a reader is
  not misled into expecting a compiler warning.
"""

import re
from pathlib import Path

import pytest

from tests.conftest import REPO

DOC = REPO / "docs" / "DEPRECATIONS.md"
STD = REPO / "std"

# `@deprecated("...")` as an actual declaration attribute (start of a line,
# optionally indented, NOT preceded by a comment marker).
_REAL_ATTR = re.compile(r"^\s*@deprecated\s*\(", re.M)
# `## @deprecated ...` / `# @deprecated ...` doc comment.
_DOC_MARKER = re.compile(r"^\s*#+\s*@deprecated\b", re.M)


def _modules():
    return [p for p in sorted(STD.glob("*.pengu")) if not p.name.endswith(".d.pengu")]


def _counts():
    real = doc = 0
    per_module = {}
    for path in _modules():
        text = path.read_text(encoding="utf-8")
        r = len(_REAL_ATTR.findall(text))
        d = len(_DOC_MARKER.findall(text))
        real += r
        doc += d
        if r or d:
            per_module[path.stem] = (r, d)
    return real, doc, per_module


def test_stdlib_has_no_real_deprecated_attributes():
    """If this fails, someone applied the attribute: update DEPRECATIONS.md,
    migrate the internal callers, and move the test-block coverage."""
    real, doc, per_module = _counts()
    assert real == 0, (
        f"std/ now declares {real} real @deprecated(...) attributes "
        f"{ {k: v for k, v in per_module.items() if v[0]} }; "
        "docs/DEPRECATIONS.md and the internal callers must be updated with it"
    )


def test_docstring_markers_are_still_present():
    """Guards against the opposite mistake: silently deleting the intent."""
    real, doc, per_module = _counts()
    assert doc >= 40, f"expected the docstring markers to remain, found {doc}"


def test_deprecations_doc_states_the_documented_not_enforced_caveat():
    text = DOC.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "not enforced" in lowered or "documented, not" in lowered, (
        "DEPRECATIONS.md no longer warns that the stdlib markers are "
        "documentation-only and emit no W0006"
    )
    assert "w0006" in lowered, "the doc must name the warning it does not emit"


def test_deprecations_doc_names_the_three_blockers():
    """The caveat must stay actionable; each blocker is checkable."""
    text = DOC.read_text(encoding="utf-8")
    for needle in ("std/invoke", "std/precis", "std/seal", "std/ward"):
        assert needle in text, f"DEPRECATIONS.md should name the internal user {needle}"
    assert "test" in text and "0:0" in text, (
        "the doc should mention the test-block and position blockers"
    )
