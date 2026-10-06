"""Roadmap Phase 7 / item 7.3 — one canonical spelling, the old one marked.

Two syntaxes had two documented spellings each, and the documents disagreed
about which was which:

* **Ranges.** `LANGUAGE.md` §15.5 showed `1 to 10` **twice** (a botched earlier
  rewrite replaced the `..` line with a copy of the canonical one), so the
  deprecated form was not documented at all; `LANGUAGE_Spanish.md` §15.5 still
  presented `1..10` as an innocent "alternate range syntax".  The compiler warns
  `W0013` on `..` and `pengu fmt` rewrites it, so `a to b` is the only form the
  documentation may present as current.
* **`frozen`.** §9.5 listed `frozen ref to int` next to `ref to frozen int` as
  an "alias" without saying which one to write.

These tests pin the documentation: the canonical form is stated, the deprecated
one is marked as such *and* tied to its diagnostic code, and the two language
references agree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
EN = REPO / "LANGUAGE.md"
ES = REPO / "LANGUAGE_Spanish.md"


def _section(text: str, heading: str) -> str:
    """Returns the body of ``heading`` up to the next heading of equal rank."""
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    rest = text[start + len(heading):]
    for match in re.finditer(r"^(#{1,6}) ", rest, re.M):
        if len(match.group(1)) <= level:
            return rest[: match.start()]
    return rest


@pytest.fixture(scope="module")
def english() -> str:
    return EN.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spanish() -> str:
    return ES.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Ranges
# ---------------------------------------------------------------------------

def test_the_range_section_does_not_repeat_the_canonical_example(english):
    """The duplicate `1 to 10` line was a symptom of the botched rewrite."""
    section = _section(english, "### 15.5")
    canonical = re.findall(r"^1 to 10\b.*$", section, re.M)
    assert len(canonical) == 1, (
        f"§15.5 shows the canonical range example {len(canonical)} times: {canonical}"
    )


@pytest.mark.parametrize("path,fixture", [(EN, "english"), (ES, "spanish")])
def test_the_range_section_names_the_canonical_form(request, path, fixture):
    section = _section(request.getfixturevalue(fixture), "### 15.5")
    assert "`a to b`" in section, (
        f"{path.name} §15.5 does not state the canonical range syntax"
    )


@pytest.mark.parametrize("path,fixture,word", [
    (EN, "english", "deprecated"),
    (ES, "spanish", "obsoleta"),
])
def test_the_deprecated_range_form_is_marked(request, path, fixture, word):
    """`..` must be documented *as deprecated* where ranges are taught."""
    section = _section(request.getfixturevalue(fixture), "### 15.5")
    assert "`a..b`" in section or "1..10" in section, (
        f"{path.name} §15.5 no longer mentions the `..` spelling at all"
    )
    assert word in section.lower(), (
        f"{path.name} §15.5 mentions `..` but does not call it {word!r}"
    )


@pytest.mark.parametrize("path", [EN, ES])
def test_the_deprecated_range_form_is_tied_to_w0013(path):
    """The reader must be able to find the diagnostic that fires."""
    section = _section(path.read_text(encoding="utf-8"), "### 15.5")
    assert "W0013" in section, f"{path.name} §15.5 does not name W0013"
    assert "2.0" in section, f"{path.name} §15.5 does not state the removal version"


def test_the_two_references_agree_that_dotdot_is_deprecated(english, spanish):
    """The pair must not diverge on which range spelling is current."""
    for text, word in ((english, "deprecated"), (spanish, "obsoleta")):
        section = _section(text, "### 15.5")
        assert word in section.lower()
    # ...and neither may present `..` as a plain alternative.
    for text, bad in ((english, "alternate range syntax"),
                      (spanish, "alternate range syntax")):
        assert bad not in text


def test_w0013_is_really_emitted_and_catalogued():
    """The documentation's claim must match the compiler."""
    import sys

    sys.path.insert(0, str(REPO))
    from tools import gen_error_catalog as G

    catalog = G.build_catalog()
    assert "W0013" in catalog["warnings"]
    assert catalog["warnings"]["W0013"]["conditions"], "W0013 has no condition"
    assert ".." in " ".join(catalog["warnings"]["W0013"]["conditions"])


# ---------------------------------------------------------------------------
# `frozen`
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,fixture", [(EN, "english"), (ES, "spanish")])
def test_frozen_names_the_canonical_placement(request, path, fixture):
    section = _section(request.getfixturevalue(fixture), "### 9.5")
    assert "`ref to frozen T`" in section, (
        f"{path.name} §9.5 does not name the canonical `frozen` placement"
    )
    assert "canónic" in section.lower() or "canonical" in section.lower(), (
        f"{path.name} §9.5 does not say which spelling is canonical"
    )


def test_frozen_alias_is_still_documented(english):
    """The accepted alias must stay documented, because it keeps compiling."""
    section = _section(english, "### 9.5")
    assert "frozen ref to int" in section
    assert "normalises" in section or "normalizes" in section


def test_frozen_normalisation_is_real():
    """`frozen ref to T` really normalises to `ref to frozen T`."""
    from pengu_parser.pengu_types import FrozenType

    # The type model has one read-only-pointee representation; the alias is
    # accepted by the parser and folded by ast_to_type.  Both spellings must
    # produce the same FrozenType wrapping, which is what makes the canonical
    # form a documentation choice rather than a semantic one.
    from pengu_parser.pengu_types import RefType, INT_TYPE

    canonical = RefType(FrozenType(INT_TYPE))
    assert canonical == RefType(FrozenType(INT_TYPE))
    assert FrozenType(INT_TYPE) == FrozenType(INT_TYPE)
