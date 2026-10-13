"""Docs ↔ compiler sync for the machine-readable `bounds-ops` block.

`LANGUAGE.md` §10.9 carries a second, machine-readable copy of the concept →
operator table (`CONCEPT_OPERATORS` in `pengu_parser/pengu_types.py`) so a reader
can see the monotone chain without parsing prose. A copy that can drift is worse
than no copy, so this test parses the fenced block out of both language
references and fails when it disagrees with the compiler -- in either direction,
so a concept that is added to the code and forgotten in the docs (or the
reverse) is caught here.

The Spanish block is machine-readable too, which is why it must list exactly the
same concepts and operators as the English one: these are compiler identifiers,
not prose, and translating them would be a bug.

The block lives next to the prose table it mirrors. Keep the two in step:

* add the row to the §10.9 table (`| `Real` | *real* | ... |`);
* add the concept line here (both languages, identical);
* register the concept in `pengu_parser/pengu_types.py`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

#: Repository root: ``tests/compiler/test_docs_bounds_sync.py`` -> ``tests/compiler``
#: -> ``tests`` -> checkout.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_types import CONCEPT_OPERATORS  # noqa: E402

#: The bilingual pair that must both carry the block.
DOCS = ("LANGUAGE.md", "LANGUAGE_Spanish.md")

_BLOCK_RE = re.compile(r"^```text bounds-ops[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)
_ROW_RE = re.compile(r"^\|\s*`([A-Za-z_][A-Za-z0-9_]*)`\s*\|", re.M)


def _parse_block(name: str) -> dict[str, set[str]]:
    """``{concept: {operator, ...}}`` from the `bounds-ops` block of ``name``."""
    text = (ROOT / name).read_text(encoding="utf-8")
    match = _BLOCK_RE.search(text)
    assert match, f"{name} has no '```text bounds-ops' block"
    table: dict[str, set[str]] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line:
            continue
        concept, _, ops = line.partition(":")
        table[concept.strip()] = {op.strip() for op in ops.split(",") if op.strip()}
    return table


def _concept_row_names(name: str) -> set[str]:
    """Concept names that have a row in the §10.9 table of ``name``."""
    text = (ROOT / name).read_text(encoding="utf-8")
    section = text.split("### 10.9", 1)[1].split("### 10.10", 1)[0]
    return {m.group(1) for m in _ROW_RE.finditer(section)}


@pytest.mark.smoke
@pytest.mark.parametrize("name", DOCS)
def test_bounds_ops_block_matches_the_compiler(name):
    documented = _parse_block(name)
    compiled = {concept: set(ops) for concept, ops in CONCEPT_OPERATORS.items()}
    assert documented == compiled, (
        f"{name}'s bounds-ops block disagrees with CONCEPT_OPERATORS; "
        f"only in docs: {sorted(set(documented) - set(compiled))}, "
        f"only in compiler: {sorted(set(compiled) - set(documented))}, "
        f"operator drift: "
        f"{ {c: (sorted(documented.get(c, set())), sorted(compiled.get(c, set()))) for c in set(documented) | set(compiled) if documented.get(c) != compiled.get(c)} }"
    )


@pytest.mark.smoke
def test_both_languages_carry_the_same_machine_readable_block():
    assert _parse_block(DOCS[0]) == _parse_block(DOCS[1])


@pytest.mark.smoke
@pytest.mark.parametrize("name", DOCS)
def test_every_compiler_concept_has_a_row_in_the_concept_table(name):
    rows = _concept_row_names(name)
    assert set(CONCEPT_OPERATORS) <= rows, (
        f"{name} §10.9 is missing a row for "
        f"{sorted(set(CONCEPT_OPERATORS) - rows)}"
    )
