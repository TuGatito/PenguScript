"""Roadmap Phase 7 / item 7.1 — the diagnostic catalogue is generated, not written.

`LANGUAGE.md` §22.2 used to name five exception classes that do not exist in the
compiler (``DuplicateConstantError``, ``AmbiguousStructInitError``,
``StaticArrayError``, ``ErrorLiteralContextError``, ``DanglingSliceError``) and
to attribute codes such as ``E0051`` to a class when the code is really emitted
as a bare ``SemanticError`` with an explicit ``code=`` keyword.  Nothing crossed
the document with the sources, so the drift survived several releases.

These tests are the crossing.  They fail if you revert any of:

* ``docs/error_catalog.json`` becomes stale with respect to the sources;
* the ``LANGUAGE.md`` / ``LANGUAGE_Spanish.md`` tables drift from the JSON;
* a diagnostic class or an emitted code is added without regenerating the docs;
* the phantom classes reappear in either document.

Regenerate with ``python tools/gen_error_catalog.py --write``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import gen_error_catalog as G  # noqa: E402

CATALOG_JSON = REPO / "docs" / "error_catalog.json"
LANGUAGE = REPO / "LANGUAGE.md"
LANGUAGE_ES = REPO / "LANGUAGE_Spanish.md"

#: Classes that were documented for years without existing in the compiler.
PHANTOM_CLASSES = (
    "DuplicateConstantError",
    "AmbiguousStructInitError",
    "StaticArrayError",
    "ErrorLiteralContextError",
    "DanglingSliceError",
)


@pytest.fixture(scope="module")
def catalog() -> dict:
    return G.build_catalog()


def test_checked_in_catalog_matches_the_sources(catalog):
    """`docs/error_catalog.json` is generated: regenerate it or the build breaks."""
    on_disk = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    assert on_disk == catalog, (
        "docs/error_catalog.json has drifted from the compiler sources; "
        "run `python tools/gen_error_catalog.py --write`"
    )


def test_catalog_is_not_empty(catalog):
    """Guards against an extractor that silently matches nothing."""
    assert len(catalog["errors"]) >= 59
    assert len(catalog["warnings"]) >= 7
    conditions = sum(len(e.get("conditions", [])) for e in catalog["errors"].values())
    assert conditions >= 300, f"only {conditions} conditions extracted"


@pytest.mark.parametrize("code", ["E0000", "E0035", "E0047", "E0051", "E0058"])
def test_known_codes_have_a_class_attribution(catalog, code):
    """Every documented code names the class(es) that really raise it."""
    assert code in catalog["errors"]
    assert catalog["errors"][code]["classes"], f"{code} has no emitting class"


def test_e0051_is_not_attributed_to_a_phantom_class(catalog):
    """E0051 is raised as a bare SemanticError; the document used to say otherwise."""
    assert catalog["errors"]["E0051"]["classes"] == ["SemanticError"]
    assert catalog["errors"]["E0053"]["classes"] == ["SemanticError"]
    assert catalog["errors"]["E0055"]["classes"] == ["SemanticError"]
    assert catalog["errors"]["E0058"]["classes"] == ["SemanticError"]


@pytest.mark.parametrize("path", [LANGUAGE, LANGUAGE_ES])
def test_document_carries_the_generated_markers(path):
    text = path.read_text(encoding="utf-8")
    assert G.MARK_BEGIN in text, f"{path.name} lost the generated-catalogue marker"
    assert G.MARK_END in text, f"{path.name} lost the generated-catalogue marker"
    start = text.index(G.MARK_BEGIN)
    end = text.index(G.MARK_END)
    assert start < end


@pytest.mark.parametrize("path", [LANGUAGE, LANGUAGE_ES])
def test_document_tables_match_the_catalog(catalog, path):
    """The human tables are derived from the same data as the JSON."""
    text = path.read_text(encoding="utf-8")
    classes, counts = G.extract_tables(text)

    want_classes = {code: entry["classes"] for code, entry in catalog["errors"].items()}
    assert classes == want_classes, (
        f"{path.name}: §22.2 class column drifted from the sources"
    )

    want_counts = {code: len(entry.get("conditions", []))
                   for code, entry in catalog["errors"].items()}
    want_counts.update({code: len(entry.get("conditions", []))
                        for code, entry in catalog["warnings"].items()})
    assert counts == want_counts, (
        f"{path.name}: condition counts drifted from the sources"
    )


@pytest.mark.parametrize("path", [LANGUAGE, LANGUAGE_ES])
def test_phantom_classes_are_gone(path):
    """The five invented classes must not come back in either document."""
    text = path.read_text(encoding="utf-8")
    present = [name for name in PHANTOM_CLASSES if name in text]
    assert not present, f"{path.name} still documents non-existent classes: {present}"


def test_every_emitted_code_is_in_the_catalog(catalog):
    """A code emitted by the compiler but absent from the catalogue is a bug."""
    emitted = set(G.extract_error_emissions())
    documented = set(catalog["errors"])
    assert emitted - documented == set(), (
        f"codes emitted but not catalogued: {sorted(emitted - documented)}"
    )


def test_every_documented_code_is_emitted(catalog):
    """A catalogued code that nothing emits is dead documentation."""
    emitted = set(G.extract_error_emissions())
    documented = set(catalog["errors"])
    assert documented - emitted == set(), (
        f"codes catalogued but never emitted: {sorted(documented - emitted)}"
    )


def test_every_emitted_warning_is_registered(catalog):
    """A warning emitted with an unregistered code must be added to WARNING_CATALOG."""
    emitted = set(G.extract_warnings())
    registered = {code for code, entry in catalog["warnings"].items()
                  if entry.get("name") != "(reserved)" and code != "W0000"}
    assert emitted - registered == set(), (
        f"warning codes emitted but not in WARNING_CATALOG: "
        f"{sorted(emitted - registered)}"
    )


def test_language_and_project_codes_are_disjoint(catalog):
    """A code must mean exactly one thing, across layers.

    The project layer (`pengu.lock` under `--locked`/`--frozen`, dependency
    resolution) prints plain `[Exxxx]` strings and shares the `Exxxx` namespace
    with the language diagnostics.  Item 7.2 nearly reassigned `E0061` -- already
    the lockfile code -- to a new language error, which is why this test exists.
    """
    language = set(catalog["errors"])
    project = set(catalog["project"])
    assert language & project == set(), (
        f"codes used by both the language and the project layer: "
        f"{sorted(language & project)}"
    )


def test_project_layer_codes_are_catalogued(catalog):
    """The project layer's codes are documented, not invisible."""
    assert {"E0061", "E0062"} <= set(catalog["project"]), (
        "the project-layer codes lost from the catalogue"
    )
    for code, entry in catalog["project"].items():
        assert entry.get("conditions"), f"{code} is catalogued with no condition"


@pytest.mark.parametrize("path", [LANGUAGE, LANGUAGE_ES])
def test_project_table_matches_the_catalog(catalog, path):
    """§22.3.1 is generated from the same data as the rest."""
    text = path.read_text(encoding="utf-8")
    counts = G.extract_project_table(text)
    want = {code: len(entry.get("conditions", []))
            for code, entry in catalog["project"].items()}
    assert counts == want, f"{path.name}: §22.3.1 drifted from the sources"


def test_check_mode_is_clean(capsys):
    """`--check` is the CI gate; it must exit 0 on the checked-in state."""
    assert G.cmd_check() == 0
    assert "in sync" in capsys.readouterr().out
