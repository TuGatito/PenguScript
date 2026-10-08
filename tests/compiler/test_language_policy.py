"""Roadmap Phase 7 / item 7.14 — language policy and pair sync.

The repository documents itself twice: English (canonical, normative) and Spanish
(a translation). Roadmap item 7.14 requires each bilingual document to *declare*
its status, and CI to verify that the pairs stay in step. The audit found the
declarations missing from every document, and a real structural divergence: the
Spanish language reference had **five `pengu` blocks fewer** than the English
one, because four sections had never been translated at all.

What this file enforces:

1. every bilingual document declares the policy (English canonical, Spanish
   non-normative);
2. the Spanish declaration itemises what is still untranslated;
3. the pairs' `pengu` block counts match, **modulo an explicit, itemised lag** —
   the ratchet is exact in both directions, so the lag can neither grow silently
   nor rot into a stale exemption;
4. the lag list and the measured lag agree.

The translation itself (roughly 200 lines of normative prose across §5.0, §19.0,
§19.1.1 and §23) is tracked as roadmap item 7.14b: it is prose volume, not
structure, and it is deliberately not guessed at here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

#: Bilingual pairs: (English, Spanish).
PAIRS = (
    ("LANGUAGE.md", "LANGUAGE_Spanish.md"),
    ("PenguScriptGuideEnglish.md", "PenguScriptGuideSpanish.md"),
)

#: Sections present in the English reference and not yet translated.
#: ``{spanish_path: {section number: pengu blocks still missing}}``.
#: A section listed here must still be missing, and must still contribute exactly
#: this many blocks; that two-way check is what stops the list from rotting.
UNTRANSLATED: dict[str, dict[str, int]] = {
    "LANGUAGE_Spanish.md": {
        "5.0": 1,       # Safety guarantees and their opt-outs
        "19.0": 1,      # Standard-library versioning policy
        "19.1.1": 1,    # Choosing between std.loom and std.tally
        "23.2": 0,      # Deprecating a symbol (the whole of §23 is untranslated;
                        #          its only example is a `pengu-fragment`)
    },
}

_BLOCK_RE = re.compile(r"^```pengu\s*$", re.M)
_HEADING_RE = re.compile(r"^(#{1,4}) ([0-9]+(?:\.[0-9]+)*)\.? ", re.M)


def _blocks(text: str) -> int:
    return len(_BLOCK_RE.findall(text))


def _sections(text: str) -> dict[str, int]:
    """``section number -> pengu blocks inside it``."""
    heads = [(m.start(), m.group(2)) for m in _HEADING_RE.finditer(text)]
    out: dict[str, int] = {}
    for i, (pos, num) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        out[num] = _blocks(text[pos:end])
    return out


@pytest.mark.parametrize("english,spanish", PAIRS)
def test_both_documents_declare_the_language_policy(english, spanish):
    en = (REPO / english).read_text(encoding="utf-8")[:2500]
    es = (REPO / spanish).read_text(encoding="utf-8")[:2500]
    assert "Language policy" in en or "Política de idioma" in en, (
        f"{english} does not declare the language policy"
    )
    assert "Política de idioma" in es or "Language policy" in es, (
        f"{spanish} does not declare the language policy"
    )
    assert "non-normative" in en.lower() or "no normativ" in en.lower() or "normative" in en.lower()
    assert "no normativ" in es.lower() or "non-normative" in es.lower()


@pytest.mark.parametrize("english,spanish", PAIRS)
def test_english_is_named_as_canonical(english, spanish):
    en = (REPO / english).read_text(encoding="utf-8")[:2500]
    es = (REPO / spanish).read_text(encoding="utf-8")[:2500]
    assert "canonical" in en.lower(), f"{english} does not name English as canonical"
    assert "canónico" in es.lower(), f"{spanish} does not name English as canonical"
    # The non-normative document must point at the normative one.
    assert (REPO / english).name in es or "LANGUAGE.md" in es


def test_readme_declares_the_policy():
    """README.md is bilingual inside one file, so it needs its own note."""
    head = (REPO / "README.md").read_text(encoding="utf-8")[:3000]
    assert "Language policy" in head and "Política de idioma" in head


@pytest.mark.parametrize("english,spanish", PAIRS)
def test_pair_block_counts_match_modulo_the_itemised_lag(english, spanish):
    """Same number of `pengu` blocks, except the sections named in UNTRANSLATED."""
    en_text = (REPO / english).read_text(encoding="utf-8")
    es_text = (REPO / spanish).read_text(encoding="utf-8")
    expected_lag = sum(UNTRANSLATED.get(spanish, {}).values())
    assert _blocks(en_text) == _blocks(es_text) + expected_lag, (
        f"{english} has {_blocks(en_text)} pengu blocks and {spanish} has "
        f"{_blocks(es_text)}; the itemised lag is {expected_lag}. Update "
        f"UNTRANSLATED only after translating the named sections."
    )


def test_the_untranslated_list_is_exact():
    """Every listed section must still be missing, with exactly the listed block count.

    This is the two-way ratchet: a section that gets translated must be removed
    from the list (otherwise the block-count test would start failing *and* the
    exemption would be a lie), and the count must not drift.
    """
    en_sections = _sections((REPO / "LANGUAGE.md").read_text(encoding="utf-8"))
    problems = []
    for spanish, sections in UNTRANSLATED.items():
        es_sections = _sections((REPO / spanish).read_text(encoding="utf-8"))
        for number, blocks in sections.items():
            if number in es_sections:
                problems.append(
                    f"§{number} is now present in {spanish}; remove it from UNTRANSLATED"
                )
                continue
            if en_sections.get(number, 0) != blocks:
                problems.append(
                    f"§{number} has {en_sections.get(number, 0)} blocks in "
                    f"LANGUAGE.md but UNTRANSLATED claims {blocks}"
                )
    assert problems == [], "\n  ".join(problems)


def test_the_spanish_declaration_itemises_the_lag():
    """The reader of the translation must be told what is missing."""
    es = (REPO / "LANGUAGE_Spanish.md").read_text(encoding="utf-8")[:2500]
    for number in UNTRANSLATED["LANGUAGE_Spanish.md"]:
        assert f"§{number}" in es, (
            f"LANGUAGE_Spanish.md does not mention untranslated §{number}"
        )


def test_the_guides_are_fully_in_step():
    """The style guides have no untranslated sections and must stay that way."""
    en = _blocks((REPO / "PenguScriptGuideEnglish.md").read_text(encoding="utf-8"))
    es = _blocks((REPO / "PenguScriptGuideSpanish.md").read_text(encoding="utf-8"))
    assert en == es, f"the style guides diverged: EN {en} blocks, ES {es}"


def test_untranslated_has_no_entries_for_in_sync_pairs():
    assert "PenguScriptGuideSpanish.md" not in UNTRANSLATED
