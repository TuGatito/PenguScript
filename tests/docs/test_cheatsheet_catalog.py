"""Roadmap Phase 6 / item 6.13 — the CHEATSHEET must name real functions.

The module catalog drifted away from the code: it listed ``product``, ``max``
and ``min`` for ``loom`` (the real weaves are ``product_num``, ``max_int``,
``min_int``), ``compress``/``decompress`` for ``seal`` (really
``zlib_compress``/``zlib_decompress``), and claimed 25 modules while ``std/``
holds 27 hand-written ones (``celeris`` and ``xlsx`` were missing entirely).

Unlike a plain "did the text change" check, these tests cross the documented
names with the actual ``weave`` declarations, so the catalog cannot silently
diverge again.
"""

import re
from pathlib import Path

import pytest

from tests.conftest import REPO

CHEATSHEET = REPO / "CHEATSHEET.md"
STD = REPO / "std"

# Names that appear in the catalog's prose as illustrative C-library versions or
# upstream symbols, not as stdlib weaves.
_NOT_WEAVES = {
    "assert", "panic",  # re-exported/duplicated by design in ward/spark
}

_WEAVE_RE = re.compile(r"^(?:\s*)weave\s+([a-z_][A-Za-z0-9_]*)", re.M)
_ROW_RE = re.compile(r"^\|\s*\*\*([a-z_][a-z0-9_]*)\*\*\s*\|", re.M)


def _stdlib_weaves():
    """Every public ``weave`` name declared in the hand-written ``std/`` modules."""
    names = set()
    for path in STD.glob("*.pengu"):
        if path.name.endswith(".d.pengu"):
            continue
        for m in _WEAVE_RE.finditer(path.read_text(encoding="utf-8")):
            name = m.group(1)
            if not name.startswith("_"):
                names.add(name)
    return names


def _catalog_rows():
    text = CHEATSHEET.read_text(encoding="utf-8")
    start = text.index("### 15.2")
    end = text.index("### 15.3")
    section = text[start:end]
    rows = {}
    for line in section.splitlines():
        m = re.match(r"^\|\s*\*\*([a-z_][a-z0-9_]*)\*\*\s*\|", line)
        if m:
            rows[m.group(1)] = line
    return rows


def _hand_written_modules():
    return sorted(
        p.stem for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu")
    )


def test_catalog_count_matches_the_real_module_count():
    rows = _catalog_rows()
    modules = _hand_written_modules()
    assert len(rows) == len(modules), (
        f"catalog lists {len(rows)} modules, std/ has {len(modules)}: "
        f"missing={sorted(set(modules) - set(rows))} extra={sorted(set(rows) - set(modules))}"
    )


def test_catalog_header_states_the_real_count():
    text = CHEATSHEET.read_text(encoding="utf-8")
    m = re.search(r"### 15\.2 Core module catalog \((\d+) modules\)", text)
    assert m, "catalog header not found in the expected form"
    declared = int(m.group(1))
    assert declared == len(_hand_written_modules()), (
        f"header says {declared} modules, std/ has {len(_hand_written_modules())}"
    )


def test_catalog_covers_every_module():
    rows = set(_catalog_rows())
    modules = set(_hand_written_modules())
    missing = sorted(modules - rows)
    assert not missing, f"modules missing from the catalog: {missing}"


@pytest.mark.parametrize("module", sorted(_catalog_rows()))
def test_documented_backtick_names_exist_as_weaves(module):
    """Backticked identifiers in a catalog row must be real weaves somewhere.

    Names are only rejected when they look like function calls and match nothing
    in the stdlib; the row also contains type names, field names and link flags,
    so only ``snake_case`` identifiers are checked.
    """
    row = _catalog_rows()[module]
    weaves = _stdlib_weaves()
    # Only inspect the purpose cell (last column) to avoid the `import` column.
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    purpose = cells[-1]
    candidates = set(re.findall(r"`([a-z_][a-z0-9_]*)`", purpose))
    unknown = sorted(
        c for c in candidates
        if c not in weaves and c not in _NOT_WEAVES and "_" in c
    )
    assert not unknown, (
        f"{module}: catalog documents names that are not weaves: {unknown}"
    )


def test_known_previously_broken_names_are_fixed():
    """Direct regression pins for the three names the roadmap listed."""
    text = CHEATSHEET.read_text(encoding="utf-8")
    rows = _catalog_rows()
    loom_row = rows["loom"]
    assert "`product_num`" in loom_row
    assert "`max_int`" in loom_row and "`min_int`" in loom_row
    assert "`product`" not in loom_row, "loom row still documents `product`"
    assert "`max`/`min`" not in loom_row, "loom row still documents `max`/`min`"
    seal_row = rows["seal"]
    assert "`zlib_compress`" in seal_row and "`zlib_decompress`" in seal_row
    assert "zlib `compress`/`decompress`" not in seal_row
    assert "(27 modules)" in text
