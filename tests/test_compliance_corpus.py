#!/usr/bin/env python3
"""Compliance-corpus gate (Roadmap 2.0, item 8.4).

``tests/compliance/`` holds one canonical program per section of ``LANGUAGE.md``
(``NNN-slug.pengu``), a machine-readable ``corpus.json`` mapping each program to
its section and expected exit code, and ``run_all.py``, which drives every
program through the real toolchain (``pengu check`` -> ``pengu build`` -> execute).

These tests:

* validate the corpus against the files on disk and against the headings that
  actually exist in ``LANGUAGE.md``,
* assert the corpus is large enough (>= 25 programs) and that the sections it
  claims are distinct-ish,
* compile and execute every program through ``run_all.py`` and require the exit
  code it observes to equal the declared ``expects_rc``.

Nothing here inspects source text or generated C to decide whether a program is
correct: every gate compiles, executes or measures (Roadmap Annex C, rule C1).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from tests.conftest import SANITIZERS_ACTIVE, requires_cc, requires_runtime

COMPLIANCE_DIR = Path(__file__).resolve().parent / "compliance"
MIN_PROGRAMS = 25


def _load_runner():
    """Imports ``tests/compliance/run_all.py`` (not a package, so no plain import)."""
    path = COMPLIANCE_DIR / "run_all.py"
    spec = importlib.util.spec_from_file_location("compliance_run_all", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[cls.__module__], so the
    # module must be registered before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_all = _load_runner()
CORPUS = run_all.load_corpus()
PROGRAM_IDS = [entry["file"] for entry in CORPUS]


# --------------------------------------------------------------------------
# Corpus integrity (no toolchain needed)
# --------------------------------------------------------------------------


def test_corpus_json_matches_disk_and_language_md():
    """The corpus lists exactly the programs on disk, and every header agrees."""
    problems = run_all.verify_corpus(CORPUS)
    assert not problems, "corpus integrity problems:\n  " + "\n  ".join(problems)


def test_corpus_has_at_least_minimum_programs():
    assert len(CORPUS) >= MIN_PROGRAMS, (
        f"compliance corpus has {len(CORPUS)} programs, expected >= {MIN_PROGRAMS}")


def test_every_declared_section_exists_in_language_md():
    """Each section must be a real numbered heading of LANGUAGE.md, same title."""
    sections = run_all.language_sections()
    assert sections, "no numbered headings parsed out of LANGUAGE.md"
    missing = []
    mismatched = []
    for entry in CORPUS:
        section = str(entry["section"])
        if section not in sections:
            missing.append(f"{entry['file']}: §{section}")
        elif sections[section] != entry["title"]:
            mismatched.append(
                f"{entry['file']}: §{section} title {entry['title']!r} "
                f"!= LANGUAGE.md {sections[section]!r}")
    assert not missing, "corpus entries declare sections absent from LANGUAGE.md: " + \
        ", ".join(missing)
    assert not mismatched, "corpus titles disagree with LANGUAGE.md:\n  " + \
        "\n  ".join(mismatched)


def test_sections_are_distinct_ish():
    """Sections must not be re-used more than twice, and cover >= MIN distinct ones."""
    counts = {}
    for entry in CORPUS:
        section = str(entry["section"])
        counts[section] = counts.get(section, 0) + 1
    reused = {section: n for section, n in counts.items() if n > 2}
    assert not reused, f"sections pinned by more than two programs: {reused}"
    assert len(counts) >= MIN_PROGRAMS, (
        f"only {len(counts)} distinct LANGUAGE.md sections covered, "
        f"expected >= {MIN_PROGRAMS}")


def test_corpus_entries_declare_the_expected_fields():
    for entry in CORPUS:
        assert set(entry) >= {"file", "section", "title", "expects_rc"}, entry
        assert isinstance(entry["expects_rc"], int), entry
        assert entry["file"].endswith(".pengu"), entry
        assert entry["file"][:3].isdigit(), entry


def test_runner_self_check_exits_zero():
    """`run_all.py --check-corpus` must agree that the corpus is sound."""
    assert run_all.main(["--check-corpus"]) == 0


# --------------------------------------------------------------------------
# Real compile + execute
# --------------------------------------------------------------------------


@requires_cc
@requires_runtime
@pytest.mark.parametrize("entry", CORPUS, ids=PROGRAM_IDS)
def test_compliance_program_compiles_and_runs(entry):
    """check -> build -> execute; the observed exit code must equal ``expects_rc``."""
    if SANITIZERS_ACTIVE and entry["file"].startswith("020-"):
        pytest.skip(
            "finding F8-N10: this program passes an array to a variadic C "
            "function, which ASan reports as stack-use-after-scope"
        )
    path = COMPLIANCE_DIR / entry["file"]
    assert path.is_file(), f"{entry['file']} is listed in corpus.json but missing"

    result = run_all.run_program(path, expects_rc=int(entry["expects_rc"]))
    detail = "\n".join([
        f"program : {result.file} (LANGUAGE.md §{result.section} — {result.title})",
        f"stage   : {result.stage}",
        f"rc      : {result.rc} (expected {result.expects_rc})",
        f"command : {' '.join(result.commands[-1]) if result.commands else '<none>'}",
        "--- stdout ---", result.stdout.strip()[:4000],
        "--- stderr ---", result.stderr.strip()[:4000],
    ])
    assert result.ok, detail


# --------------------------------------------------------------------------
# Roadmap 10.3 — the corpus is also the compiler matrix's workload
# --------------------------------------------------------------------------

#: One program per language tier, so the matrix is not a hello-world only check.
_MATRIX_SAMPLE = ("001-hello.pengu", "016-judge.pengu", "040-auto-banish.pengu")


def test_the_runner_forwards_the_compiler_override():
    """`--cc` must reach the *build* stage, or the CI matrix would be a fiction.

    The full matrix (gcc and clang over all 54 programs) runs in
    `.github/workflows/compliance.yml`; rebuilding it inside the default suite
    would double a 5-minute job. What is pinned here is the mechanism plus one
    end-to-end run per compiler, measured — a `--cc` that is parsed and dropped
    would make the workflow green while compiling with the default compiler.
    """
    import shutil

    available = [cc for cc in ("gcc", "clang") if shutil.which(cc)]
    if not available:
        pytest.skip("neither gcc nor clang is installed")
    for compiler in available:
        for name in _MATRIX_SAMPLE:
            entry = next(e for e in CORPUS if e["file"] == name)
            result = run_all.run_program(
                COMPLIANCE_DIR / name, expects_rc=int(entry["expects_rc"]),
                timeout=600, cc=compiler)
            assert any("--cc" in cmd and compiler in cmd for cmd in result.commands), (
                f"--cc {compiler} never reached the build: {result.commands}")
            assert result.ok, (
                f"{compiler} failed {name}: {result.detail()}\n{result.stderr[:2000]}")
