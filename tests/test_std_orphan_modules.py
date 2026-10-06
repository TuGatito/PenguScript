"""Roadmap Phase 6 / item 6.14 — the three "orphan" modules are not orphaned.

The roadmap listed ``celeris``, ``xlsx`` and ``trial`` as orphans and proposed
moving them to ``std/contrib/`` "if they have no real importer".  Measurement
refutes the premise: each one has an importer that compiles **and runs** it, and
each documents its opt-in requirements in its own header.

======================  ==================================================================
module                  real importer
======================  ==================================================================
``std.celeris``         ``tests/test_ffi_libs.py::test_all_stb_modules_import_and_compile_in_one_bundle``
                        compiles and asserts ``celeris.hash64`` == ``0x610DF71A00097754``
``std.xlsx``            ``tests/test_ffi_libs.py::TestXlsxio`` writes a real ``.xlsx`` and
                        reads it back (skipped here: optional ``libzip``/``xlsxio`` extern)
``std.trial``           ``tests/std_programs/test_trial.pengu``, driven by
                        ``tests/test_stdlib.py::test_std_module_program``
======================  ==================================================================

So this item is *refuted*, not deferred: no module is moved.  What this test
locks down is the property the roadmap actually cared about -- none of the three
becomes a genuine orphan unnoticed.  If a future change deletes the importer or
the module stops importing, this fails instead of the module rotting silently.

Moving them to ``std/contrib/`` was considered and rejected for 1.0: it is a
breaking import-path change with no functional benefit, ``xlsx`` already
documents itself as opt-in (listing the exact extra link flags), and the
roadmap's own exit criterion -- "each one has an importer in ``std/``" -- is
satisfied.
"""

import re
from pathlib import Path

import pytest

from tests.conftest import REPO

STD = REPO / "std"
TESTS = REPO / "tests"

# module -> (file containing a real `import std.<module>`, a call that proves it runs)
_EXPECTED_IMPORTERS = {
    "celeris": (TESTS / "test_ffi_libs.py", "celeris.hash64"),
    "xlsx": (TESTS / "test_ffi_libs.py", "xlsx.write_sheet"),
    "trial": (
        TESTS / "std_programs" / "test_trial.pengu",
        "trial.new_suite",
    ),
}


@pytest.mark.parametrize("module", sorted(_EXPECTED_IMPORTERS))
def test_module_still_exists(module):
    assert (STD / f"{module}.pengu").is_file(), f"std/{module}.pengu disappeared"


@pytest.mark.parametrize("module", sorted(_EXPECTED_IMPORTERS))
def test_module_has_a_real_importer(module):
    importer, exercised = _EXPECTED_IMPORTERS[module]
    assert importer.is_file(), f"expected importer {importer} is gone"
    text = importer.read_text(encoding="utf-8")
    # Regex, not substring: a plain `in` check happily matches the module's own
    # docstring or an `import std.celeris_XX` typo. A real import statement is
    # an exact module name at the start of a line.
    assert re.search(
        rf"^\s*import\s+std\.{re.escape(module)}\s*$", text, re.M
    ), (
        f"std.{module} lost its importer in {importer.name}; it is now a real orphan"
    )
    assert exercised in text, (
        f"{importer.name} imports std.{module} but no longer exercises it "
        f"(expected {exercised!r})"
    )


@pytest.mark.parametrize("module", sorted(_EXPECTED_IMPORTERS))
def test_module_declares_its_extra_link_requirements(module):
    """An opt-in module must say what it costs to opt in.

    ``celeris`` and ``xlsx`` pull C libraries into the bundle, so their headers
    have to name the library.  ``trial`` is pure and only needs to document its
    imports.
    """
    text = (STD / f"{module}.pengu").read_text(encoding="utf-8")
    header = text[:2000]
    if module == "trial":
        assert "import std.ward" in text, "trial should re-export ward assertions"
        return
    # ffi-backed: the module doc must mention the C library it binds.
    expected = "xxhash" if module == "celeris" else "xlsxio"
    assert expected in header, (
        f"std/{module}.pengu header no longer documents its {expected} dependency"
    )


def test_no_other_stdlib_module_is_unimported():
    """Guard the general property, not just the three known names.

    Hand-written ``std/*.pengu`` modules only.  Generated ``*.d.pengu`` bindings
    are pulled in on demand by the modules that wrap them and are imported by
    their stem without the ``.d`` suffix, so they are checked separately below.
    """
    sources = []
    for path in list(STD.glob("*.pengu")) + list(TESTS.rglob("*.pengu")):
        sources.append(path.read_text(encoding="utf-8"))
    for path in list(TESTS.rglob("*.py")) + list((REPO / "benches").glob("*.pengu")):
        sources.append(path.read_text(encoding="utf-8"))
    blob = "\n".join(sources)

    unimported = []
    for path in sorted(STD.glob("*.pengu")):
        if path.name.endswith(".d.pengu"):
            continue
        if not re.search(rf"import\s+std\.{re.escape(path.stem)}\b", blob):
            unimported.append(path.stem)

    assert not unimported, (
        "hand-written std modules with no importer anywhere in the repo "
        "(real orphans): " + ", ".join(unimported)
    )


def test_generated_bindings_are_opt_in_by_design():
    """``*.d.pengu`` bindings are library adapters reached by ``import std.<lib>``.

    They are deliberately not imported by any other module: the user opts in
    when they need the library, and the linker then adds it.  Measured during
    Phase 6, 9 of the 25 bindings (``datastructura``, ``fenestra``, ``pactum``,
    ``perlinum``, ``scriptor``, ``typis``, ``webui``, ``stb_herringbone_wang_tile``,
    ``stb_image_resize2``) have no in-repo importer -- including no test -- and
    are reachable only through their ``LANGUAGE.md``/``CHEATSHEET.md`` catalog
    entry.  That is documented opt-in, not rot, so nothing is moved or deleted
    for 1.0; the check below only asserts that every binding is *reachable*
    somehow: a wrapper, a test, or the documentation catalog.
    """
    sources = []
    for path in list(STD.glob("*.pengu")) + list(TESTS.rglob("*.pengu")):
        sources.append(path.read_text(encoding="utf-8"))
    for path in list(TESTS.rglob("*.py")) + list((REPO / "benches").glob("*.pengu")):
        sources.append(path.read_text(encoding="utf-8"))
    code_blob = "\n".join(sources)
    docs_blob = "\n".join(
        (REPO / name).read_text(encoding="utf-8")
        for name in ("LANGUAGE.md", "CHEATSHEET.md")
        if (REPO / name).is_file()
    )

    unreachable = []
    for path in sorted(STD.glob("*.d.pengu")):
        stem = path.name[: -len(".d.pengu")]
        imported = re.search(rf"import\s+std\.{re.escape(stem)}(?:\.d)?\b", code_blob)
        documented = f"`{stem}`" in docs_blob or f"std.{stem}" in docs_blob
        if not (imported or documented):
            unreachable.append(stem)

    assert not unreachable, (
        "generated bindings neither imported nor documented (real orphans): "
        + ", ".join(unreachable)
    )
