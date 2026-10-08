"""Roadmap Phase 7 / item 7.4 — the `pengu` blocks in the docs are compiled.

AUDIT_1.0.md §12.3 measured that most examples in `LANGUAGE.md` did not survive
`pengu check`. Measured again for this item: of **101** ```` ```pengu ```` blocks,
**35** compiled and **66** did not. Four blocks were real documentation bugs and
are fixed here; the other 62 were never programs (``1 to 10``, ``42 -7 0xFF``,
directive lists, `...` elisions) or were deliberately-wrong examples.

The fix is not "make every snippet a program" — that would mean inventing 62
programs. It is to make the *classification explicit and machine-checked*:

* ```` ```pengu ```` — must compile;
* ```` ```pengu-fragment ```` — a snippet: must **not** compile on its own;
* ```` ```pengu-invalid ```` — a deliberately wrong example: must **not** compile.

The second and third rules are what keep the markers honest: a fragment that
starts compiling has to be promoted back to `pengu`, so the escape hatch cannot
be used to hide a broken example.

These tests wrap `tools/check_doc_blocks.py`; the tool is the single
implementation and the CI entry point. The full check compiles ~200 blocks, so it
is marked with the repo's `slow` convention and still runs by default — see the
module docstring of `tools/check_doc_blocks.py` for the standalone command.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import check_doc_blocks as C  # noqa: E402


@pytest.fixture(scope="module")
def blocks() -> dict[str, list[C.Block]]:
    return {name: C.extract_blocks(REPO / name) for name in C.DOCUMENTS}


def test_both_references_are_gated(blocks):
    assert set(blocks) == set(C.DOCUMENTS)
    for name, found in blocks.items():
        assert found, f"{name} has no pengu blocks at all"


def test_the_marker_protocol_is_used(blocks):
    """All three markers must appear, or the classification is not real."""
    for name, found in blocks.items():
        markers = {b.marker for b in found}
        assert "pengu" in markers, f"{name} has no `pengu` block"
        assert "pengu-fragment" in markers, f"{name} has no `pengu-fragment` block"
        assert "pengu-invalid" in markers, f"{name} has no `pengu-invalid` block"


def test_deliberately_invalid_blocks_say_so(blocks):
    """An `invalid` block must announce itself, so a reader is not misled.

    A block marked invalid that looks like ordinary advice would teach the wrong
    thing; the marker is only honest when the surrounding text or the block
    itself says "invalid".
    """
    for name, found in blocks.items():
        text_lines = (REPO / name).read_text(encoding="utf-8").splitlines()
        for block in found:
            if block.marker != "pengu-invalid":
                continue
            assert C._looks_invalid(block, text_lines), (
                f"{name}:{block.line}: marked `pengu-invalid` but nothing says it is "
                f"a counter-example"
            )


def test_the_documentation_bug_fixes_are_present(blocks):
    """The four real bugs this item fixed must not come back.

    Each was measured failing before the fix; each form below is the corrected
    one and is verified to compile by the full check.
    """
    text = (REPO / "LANGUAGE.md").read_text(encoding="utf-8")
    # 1. a `to` cast directly after a comparison inside {…} is not accepted
    assert "{(original.value == (payload to string))}" in text
    assert "{(original.value == payload to string)}" not in text
    # 2. `ffi.slice_from_ptr` needs explicit type arguments; the non-generic
    #    helper is the right call for a byte view
    assert "ffi.slice_of_bytes_from_ptr" in text
    # 3. `string_from_cstr` takes `ref to char`, not `ref to frozen char`
    assert "var c_str as ref to char is transmute c_buf to ref to char" in text
    # 4. `filum.free_mutex` / `free_wait_group` take `ref to`, so pass the sigil
    assert "calling filum.free_mutex with (sigil of m)" in text
    # 5. `regulus.compile` returns `maybe Regex`, and the API takes `ref to Regex`
    assert "var re as maybe regulus.Regex is calling regulus.compile" in text
    assert "calling regulus.search with (sigil of rx)" in text


def _document_blocks() -> list:
    """Every documented block, as ``(document, block)`` parameters.

    One test per block, not one test for all of them. The single-test version took
    ~141 s of *setup* and could not be split across pytest-xdist workers, which put
    a hard floor under the whole suite: no amount of ``-n auto`` makes a suite
    faster than its slowest single test. Compiling blocks is embarrassingly
    parallel, so the split turns 141 s of critical path into a few seconds of
    distributed work.

    Extraction happens at import time -- reading two Markdown files and scanning
    fences costs milliseconds, and every worker has to do it anyway.
    """
    return [
        pytest.param(name, block, id=f"{name}-L{block.line}")
        for name in C.DOCUMENTS
        for block in C.extract_blocks(REPO / name)
    ]


_DOCUMENT_BLOCKS = _document_blocks()


def test_the_block_split_covers_the_documents(blocks):
    """The parametrisation must see every block the documents actually have.

    A scanner that silently stopped finding blocks would turn ~200 gate tests into
    a handful of green no-ops, so the count is asserted rather than assumed.
    """
    assert len(_DOCUMENT_BLOCKS) == sum(len(found) for found in blocks.values())
    assert len(_DOCUMENT_BLOCKS) > 100, (
        f"the block scanner found only {len(_DOCUMENT_BLOCKS)} blocks"
    )


@pytest.mark.parametrize("document,block", _DOCUMENT_BLOCKS)
def test_every_marked_block_matches_reality(document, block):
    """The gate itself, one block at a time: every marker must match reality.

    `pengu` must compile; `pengu-fragment` and `pengu-invalid` must not. The rule
    is not restated here -- it is `tools.check_doc_blocks.classify_failure`, the
    same function the CLI walks with, so the two cannot drift apart.
    """
    compiles, output, diagnostics = C.check_block_detail(block)
    problem = C.classify_failure(document, block, compiles, output)
    assert problem is None, problem
    # A rejection must be a *language* rejection. An interpreter error swallowed by
    # the front end comes out with an empty code, and for a `pengu-fragment` block
    # that would masquerade as "correctly does not compile" -- the mirror image of
    # the vacuity fixed in tests/compiler/test_frontend_no_crash.py.
    uncoded = [d for d in diagnostics if not str(d.get("code") or "").strip()]
    assert not uncoded, (
        f"{document}:{block.line}: the compiler reported a diagnostic with no code, "
        f"which is how an interpreter error escapes: "
        + "; ".join(str(d.get("message", ""))[:120] for d in uncoded[:3])
    )


def test_the_cli_entry_point_reports_a_count(tmp_path, monkeypatch, capsys):
    """`check_doc_blocks.py --check` is the CI entry point.

    Exercised on a two-block document so that this test stays cheap; the real
    documents are covered by `check_result` above.
    """
    doc = tmp_path / "LANGUAGE.md"
    doc.write_text(
        "```pengu\nweave main into int:\n    return 0\n```\n"
        "```pengu-fragment\n1 to 10\n```\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(C, "DOCUMENTS", (doc.name,))
    monkeypatch.setattr(C, "DOC_DIR", tmp_path)
    assert C.main(["--check"]) == 0
    assert "every marker matches reality" in capsys.readouterr().out

    # ...and it fails when a marker lies.
    doc.write_text("```pengu\n1 to 10\n```\n", encoding="utf-8")
    assert C.main(["--check"]) == 1
    assert "does not compile" in capsys.readouterr().err
