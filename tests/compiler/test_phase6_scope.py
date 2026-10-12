"""Roadmap Phase 6 / §6.3 — scope decisions and the manual release checklist.

The two documents these tests gate (``ROADMAP_1.0.0.md`` and
``RELEASE_CHECKLIST.md``) were removed with the 2.0 documentation cleanup. The
tests stay guarded so restoring either document re-enables the gate instead of
silently losing it.
"""

import pytest

from tests.conftest import REPO

# TODO(phase-1): ROADMAP_1.0.0.md / RELEASE_CHECKLIST.md were deleted.
_HAS_ROADMAP = (REPO / "ROADMAP_1.0.0.md").is_file()
_HAS_CHECKLIST = (REPO / "RELEASE_CHECKLIST.md").is_file()


@pytest.mark.skipif(not _HAS_ROADMAP,
                    reason="ROADMAP_1.0.0.md was removed in the 2.0 doc cleanup")
def test_playground_is_explicitly_out_of_scope():
    roadmap = (REPO / "ROADMAP_1.0.0.md").read_text(encoding="utf-8")
    assert "Playground Web en WASM" in roadmap
    # The justification must name the concrete technical blockers.
    for needle in ("Pyodide", "clang-wasm", "no está compilado a WASM"):
        assert needle in roadmap, needle
    # And the deferred alternative must be described, not hand-waved.
    assert "POST /check" in roadmap
    assert "No ejecuta código" in roadmap or "no ejecuta código" in roadmap


@pytest.mark.skipif(not _HAS_CHECKLIST,
                    reason="RELEASE_CHECKLIST.md was removed in the 2.0 doc cleanup")
def test_release_checklist_separates_manual_from_automated():
    text = (REPO / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    assert "Automated" in text and "Manual" in text
    for needle in ("Discord", "GitHub Discussions", "Hacker News", "GPG"):
        assert needle in text, needle
    assert "not agent work" in text


@pytest.mark.skipif(not _HAS_CHECKLIST,
                    reason="RELEASE_CHECKLIST.md was removed in the 2.0 doc cleanup")
def test_release_checklist_states_known_limitations():
    text = (REPO / "RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    for needle in ("web playground", "Performance vs C", "Binary size",
                   "backtracking", "Known limitations"):
        assert needle.lower() in text.lower(), needle


@pytest.mark.skipif(not _HAS_CHECKLIST,
                    reason="RELEASE_CHECKLIST.md was removed in the 2.0 doc cleanup")
def test_readme_links_the_release_documents():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for doc in ("BENCHMARKS.md", "RELEASE_CHECKLIST.md", "SECURITY.md"):
        assert doc in readme, doc


@pytest.mark.skipif(not _HAS_ROADMAP,
                    reason="ROADMAP_1.0.0.md was removed in the 2.0 doc cleanup")
def test_roadmap_phase6_records_the_rewrite():
    roadmap = (REPO / "ROADMAP_1.0.0.md").read_text(encoding="utf-8")
    assert 'FASE 6 completada como "DX Verificable"' in roadmap
    # The unmet targets must be stated, not hidden.
    assert "NO cumplidos" in roadmap
