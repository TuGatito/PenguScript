"""Phase 2 item 2.2 — the documented bound table must match the code.

The audit's central complaint was that documentation and code drifted apart
silently (`AUDIT_1.0.md` §13). `LANGUAGE.md` and `LANGUAGE_Spanish.md` therefore
carry a machine-readable `text bounds-ops` block listing exactly which operators
each concept grants, and this test fails if it disagrees with
`CONCEPT_OPERATORS` in `pengu_parser/pengu_types.py`.

Rule C1 (ROADMAP_2.0 Anexo C): the comparison is structural -- the documented
operator sets are compared to the real table, and the documented sets are also
fed to `concept_grants()`, so a doc that lists an operator the checker does not
actually honour is caught too. No prose is matched.
"""

import re
from pathlib import Path

import pytest

from pengu_parser.pengu_types import (
    CONCEPT_OPERATORS,
    CONCEPT_REFINES,
    concept_grants,
)

REPO = Path(__file__).resolve().parent.parent
DOCS = ["LANGUAGE.md", "LANGUAGE_Spanish.md"]

_BLOCK_RE = re.compile(
    r"```text bounds-ops\n(?P<body>.*?)```",
    re.DOTALL,
)


def _parse_doc_block(path: Path) -> dict:
    """Extracts {concept: set(operators)} from the `bounds-ops` block of `path`."""
    text = path.read_text(encoding="utf-8")
    match = _BLOCK_RE.search(text)
    assert match, (
        f"{path.name} has no ```text bounds-ops block. Item 2.2 requires the "
        "documented bound table to be machine-readable so this test can check it."
    )
    documented = {}
    for line in match.group("body").strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        concept, _, ops = line.partition(":")
        concept = concept.strip()
        documented[concept] = {op.strip() for op in ops.split(",") if op.strip()}
    return documented


@pytest.mark.parametrize("doc", DOCS)
def test_documented_bounds_block_matches_the_code_table(doc):
    """The operator set documented for each concept equals the real one."""
    documented = _parse_doc_block(REPO / doc)

    assert set(documented) == set(CONCEPT_OPERATORS), (
        f"{doc} documents concepts {sorted(documented)} but the code table has "
        f"{sorted(CONCEPT_OPERATORS)}"
    )
    for concept, ops in documented.items():
        assert ops == set(CONCEPT_OPERATORS[concept]), (
            f"{doc}: concept {concept!r} is documented as granting {sorted(ops)} "
            f"but the code table grants {sorted(CONCEPT_OPERATORS[concept])}"
        )


@pytest.mark.parametrize("doc", DOCS)
def test_documented_bounds_block_is_honoured_by_the_checker(doc):
    """Every operator the docs promise must actually be granted by the table.

    This is the half that catches "the documentation lists an operator the
    checker does not honour". It goes through `concept_grants()`, so the
    refinement chain is exercised too.
    """
    documented = _parse_doc_block(REPO / doc)
    for concept, ops in documented.items():
        for op in ops:
            assert concept_grants(concept, op), (
                f"{doc}: {concept!r} is documented as granting {op!r} but "
                "concept_grants() says no"
            )


@pytest.mark.parametrize("doc", DOCS)
def test_documented_block_does_not_promise_operators_outside_the_table(doc):
    """The docs must not grant an operator that no concept in the table grants."""
    documented = _parse_doc_block(REPO / doc)
    known = set().union(*CONCEPT_OPERATORS.values())
    for concept, ops in documented.items():
        unknown = ops - known
        assert not unknown, f"{doc}: {concept!r} lists unknown operators {sorted(unknown)}"


def test_refinement_chain_is_documented_as_monotone():
    """`Integrum` refines `Num`, and the docs must say so.

    The prose block is checked for the concept names involved, which is enough
    to catch a wholesale removal of the explanation. The *semantics* of the
    chain are covered by test_concept_bounds_matrix.py, not here.
    """
    assert CONCEPT_REFINES == {"Integrum": "Num"}, CONCEPT_REFINES
    for doc in DOCS:
        text = (REPO / doc).read_text(encoding="utf-8")
        assert "Integrum" in text and "Num" in text
        # The chain claim: monotone / monótona, so the reader is told adding a
        # bound cannot remove a capability.
        assert re.search(r"monoton", text, re.IGNORECASE), (
            f"{doc} no longer states that the bound set is monotone"
        )
