"""Roadmap Phase 7 / item 7.7 — document the exceptions, with measurements.

AUDIT_1.0.md §10.4 listed five guide rules as "the language cannot satisfy
these".  Re-measured in Phase 7, most of them turned out to be either already
satisfied or flatly mis-stated — only two needed an exception:

* the indentation rule was **never** broken (`pengu fmt` pins 4 spaces, not 2:
  measured in `AUDIT_1.0_FASE7.md` §F7-N2);
* `W0005` (shadowing) and `W0001` (unsafe conversion) are **0** across all 27
  hand-written `std/` modules, and `std/` contains **zero** `transmute` calls;
* the docstring rule is met 100 % for *public functions* — the single
  undocumented `weave` is a private helper;
* only "names and signatures are consistent across modules" needed a relaxed,
  named exception (`loom`/`tally`, deferred to 1.1).

Both guides carry the resulting table.  These tests keep its numbers honest: the
doc coverage figures are recomputed from the sources, the indentation claim is
checked against the formatter configuration, and the `transmute` claim is checked
with a grep.  The expensive end-to-end checks (`W0005`/`W0001` over 27 modules)
are not re-run here; the guide states the command to reproduce them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

EN = REPO / "PenguScriptGuideEnglish.md"
ES = REPO / "PenguScriptGuideSpanish.md"
STD = REPO / "std"

#: Every rule Phase 7 had to adjudicate, and the phrase that marks its row.
ROWS = (
    (EN, "Enforced", "public `weave` carries a `##` docstring"),
    (EN, "Scoped out", "`declare` / `const` / `alias` / `omen` is documented"),
    (EN, "Enforced", "Indent with 4 spaces, never tabs"),
    (EN, "Enforced", "may not shadow a global `weave`"),
    (EN, "Enforced", "No unsafe conversion"),
    (EN, "Relaxed", "consistent across modules"),
    (ES, "Exigida", "lleva docstring `##`"),
    (ES, "Acotada fuera", "está documentado"),
    (ES, "Exigida", "Indentar con 4 espacios"),
    (ES, "Exigida", "ensombrecer un `weave` global"),
    (ES, "Exigida", "Sin conversiones inseguras"),
    (ES, "Relajada", "consistentes entre módulos"),
)


@pytest.fixture(scope="module")
def english() -> str:
    return EN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spanish() -> str:
    return ES.read_text(encoding="utf-8")


@pytest.mark.parametrize("path,status,phrase", ROWS)
def test_every_adjudicated_rule_has_a_documented_row(path, status, phrase):
    text = path.read_text(encoding="utf-8")
    assert "## 15." in text, f"{path.name} has no exceptions section"
    section = text.split("## 15.", 1)[1]
    assert phrase in section, f"{path.name}: no row for {phrase!r}"
    # The status must appear on the same table row as the phrase.
    row = next((ln for ln in section.splitlines() if phrase in ln), "")
    assert status in row, (
        f"{path.name}: row for {phrase!r} is not marked {status!r}:\n  {row}"
    )


@pytest.mark.parametrize("path,fixture", [(EN, "english"), (ES, "spanish")])
def test_the_exceptions_section_has_a_toc_entry(request, path, fixture):
    text = request.getfixturevalue(fixture)
    assert re.search(r"^15\. \[", text, re.M), (
        f"{path.name}: section 15 is not in the table of contents"
    )


def test_doc_coverage_numbers_in_the_guide_match_the_sources(english, spanish):
    """The quoted `documented/total` figures must be the real ones.

    This is what stops the exception table from becoming a comfortable lie: if
    documentation improves, the guide's numbers must be updated, and if it
    regresses, the ratchet in `test_std_docs_completeness.py` fires first.
    """
    from tests.test_std_docs_completeness import _coverage

    cov = _coverage()
    for kind in ("weave", "declare", "const", "alias", "omen"):
        documented, total = cov[kind]
        needle = f"{documented}/{total}"
        assert needle in english, f"EN guide does not quote {kind} {needle}"
        assert needle in spanish, f"ES guide does not quote {kind} {needle}"


def test_the_only_undocumented_weave_is_private(english, spanish):
    """`weave` coverage is 100 % for public functions — assert the exception is private."""
    from tests.test_std_docs_completeness import _own_doc

    undocumented = []
    for module in sorted(STD.glob("*.pengu")):
        lines = module.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("weave "):
                continue
            if not _own_doc(lines, i):
                undocumented.append((f"{module.name}:{i + 1}", line.split()[1]))
    public = [where for where, name in undocumented if not name.startswith("_")]
    assert public == [], f"a PUBLIC weave lacks a docstring: {public}"
    assert "private" in english.split("## 15.", 1)[1]


def test_indentation_claim_matches_the_formatter_configuration():
    """The guide says 4 spaces because the config says 4 — check the config."""
    root = (REPO / ".pengufmt.toml").read_text(encoding="utf-8")
    std = (STD / ".pengufmt.toml").read_text(encoding="utf-8")
    for text, name in ((root, ".pengufmt.toml"), (std, "std/.pengufmt.toml")):
        assert re.search(r"^tab_size\s*=\s*4\s*$", text, re.M), (
            f"{name} no longer pins tab_size = 4"
        )
    from pengu_project import _resolve_indent

    assert _resolve_indent(None, None) == 4, "the formatter default is no longer 4"


def test_transmute_claim_matches_the_sources(english, spanish):
    """`std/` really contains zero `transmute` calls."""
    calls = []
    for module in sorted(STD.glob("*.pengu")):
        if module.name.endswith(".d.pengu"):
            continue
        for i, line in enumerate(module.read_text(encoding="utf-8").splitlines()):
            stripped = line.strip()
            if "transmute" in stripped and not stripped.startswith("#"):
                calls.append(f"{module.name}:{i + 1}")
    assert calls == [], (
        f"std/ now contains transmute calls, so the guide's claim is stale: {calls}"
    )
    assert "zero" in english.split("## 15.", 1)[1]
    assert "cero" in spanish.split("## 15.", 1)[1]


def test_the_guides_still_agree_on_block_count():
    """A pair that diverges is how the ranges section drifted (§7.3)."""
    en = len(re.findall(r"^```pengu\s*$", EN.read_text(encoding="utf-8"), re.M))
    es = len(re.findall(r"^```pengu\s*$", ES.read_text(encoding="utf-8"), re.M))
    assert en == es, f"the guides diverged: EN {en} pengu blocks, ES {es}"
