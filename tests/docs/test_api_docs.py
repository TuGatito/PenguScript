"""Roadmap Phase 7 / item 7.13 — a generated per-module API reference.

Roadmap item 7.13 asked for a reference covering "the 1463 public names" with the
undocumented share dropping below 10 %. Measured, the scoped surface is different:
across the **27 hand-written** `std/*.pengu` modules there are **1576** public
declarations, of which **1483 (94.1 %)** carry a doc summary — already above the
90 % the roadmap asks for. (Counting the generated `*.d.pengu` bindings as well
gives 4014 declarations; their documentation text is the upstream C header
comment, so grading it here would be grading somebody else's headers. They are
covered by `docs/DEPRECATIONS.md` and `LANGUAGE.md` §19 instead.)

Rather than hand-write 1576 entries, `docs/api/` is generated from the compiler's
own symbol table by `tools/gen_api_docs.py`, reusing `pengu_doc.render_module_doc`
— the renderer the `pengu doc` command already uses — so there is exactly one
implementation.

These tests make the reference trustworthy rather than merely present:

* regenerating must reproduce `docs/api/` byte for byte (no drift from the code);
* every public declaration of every module appears in that module's page;
* the documented share does not regress below the recorded floor.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import gen_api_docs as G  # noqa: E402

API_DIR = REPO / "docs" / "api"


@pytest.fixture(scope="module")
def generated() -> dict[str, str]:
    """The generated reference for all 27 modules.

    Rendered in a small process pool. Each module is an independent, CPU-bound
    render with its own import graph, and doing it serially made this fixture the
    single longest thing in the suite -- longer than the entire budget the suite is
    allowed to take -- because every test below needs the whole mapping
    (``index.json`` and ``README.md`` are aggregates over every module), so no
    amount of ``pytest-xdist`` could divide it.

    The pool is deliberately small: the suite already runs a worker per core, and
    only the workers that land one of these tests spawn it. Override with
    ``PENGU_API_DOC_WORKERS`` (0 or 1 renders serially).
    """
    workers = int(os.environ.get("PENGU_API_DOC_WORKERS", "4"))
    return G.build(workers=max(1, workers))


def test_the_reference_exists_and_covers_every_module(generated):
    modules = {p.stem for p in G._modules()}
    assert len(modules) >= 27, f"only {len(modules)} modules found"
    for name in modules:
        assert f"{name}.md" in generated, f"no page generated for std.{name}"
    assert "README.md" in generated
    assert "index.json" in generated


def test_the_checked_in_reference_matches_the_compiler(generated):
    """`docs/api/` is generated: edit the template, not the output."""
    on_disk = {p.name: p.read_text(encoding="utf-8") for p in sorted(API_DIR.iterdir())
               if p.is_file()}
    missing = sorted(set(generated) - set(on_disk))
    assert missing == [], f"missing generated pages: {missing}; run --write"
    drifted = sorted(name for name in generated if on_disk.get(name) != generated[name])
    assert drifted == [], (
        f"these pages drifted from the compiler: {drifted}; "
        f"run `python tools/gen_api_docs.py --write`"
    )


def test_every_public_declaration_appears_in_its_page(generated):
    """The index is the contract: it must list what the page shows."""
    index = json.loads(generated["index.json"])
    by_module: dict[str, list[dict]] = {}
    for entry in index["symbols"]:
        by_module.setdefault(entry["module"], []).append(entry)

    problems = []
    for name, entries in by_module.items():
        page = generated[f"{name}.md"]
        for entry in entries:
            if entry["name"] not in page:
                problems.append(f"{name}.md does not mention {entry['name']}")
    assert problems == [], "\n  ".join(problems[:20])


def test_private_symbols_are_excluded(generated):
    """`_`-prefixed helpers are not part of the public reference."""
    index = json.loads(generated["index.json"])
    private = [e["name"] for e in index["symbols"] if e["name"].startswith("_")]
    assert private == [], f"private symbols leaked into the reference: {private[:10]}"


def test_the_documented_share_meets_the_floor(generated):
    """The roadmap asks for >= 90 %; the ratchet records the measured 94.1 %."""
    index = json.loads(generated["index.json"])
    symbols = index["symbols"]
    documented = sum(1 for e in symbols if e["documented"])
    share = documented / len(symbols)
    assert share >= G.COVERAGE_FLOOR, (
        f"documented share {share * 100:.1f} % is below the floor "
        f"{G.COVERAGE_FLOOR * 100:.0f} % ({documented}/{len(symbols)})"
    )
    assert share >= 0.90, "the roadmap's own 90 % target is no longer met"
    # The README must state the same numbers it was generated with.
    assert f"**{len(symbols)}** public declarations" in generated["README.md"]
    assert f"**{documented}** of them carry a doc summary" in generated["README.md"]


def test_deprecated_symbols_are_flagged(generated):
    """`@deprecated` symbols must be visible in the index, not silently published."""
    index = json.loads(generated["index.json"])
    deprecated = [e for e in index["symbols"] if e["deprecated"]]
    assert deprecated, (
        "no deprecated symbol is flagged; docs/DEPRECATIONS.md records many"
    )
    for entry in deprecated[:5]:
        assert entry["name"] in generated[f"{entry['module']}.md"]


def test_check_mode_is_clean(generated, monkeypatch, capsys):
    """`--check` exits 0 on the checked-in state, without regenerating it."""
    monkeypatch.setattr(G, "build", lambda: generated)
    assert G.cmd_check() == 0
    assert "in sync" in capsys.readouterr().out


def test_check_mode_fails_when_a_page_is_tampered_with(generated, tmp_path, monkeypatch, capsys):
    """The gate must fail on drift, not merely report it."""
    for name, content in generated.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    monkeypatch.setattr(G, "OUT_DIR", tmp_path)
    monkeypatch.setattr(G, "build", lambda: generated)
    assert G.cmd_check() == 0
    capsys.readouterr()
    target = sorted(tmp_path.iterdir())[0]
    target.write_text("tampered\n", encoding="utf-8")
    assert G.cmd_check() == 1
    assert "OUT OF SYNC" in capsys.readouterr().err
