"""Roadmap Phase 6 / item 6.15 — every ``@deprecated`` symbol is documented.

``docs/DEPRECATIONS.md`` lists each deprecated stdlib symbol with its
replacement and retirement status.  This test makes that list verifiable rather
than aspirational: it scrapes the ``@deprecated`` markers out of ``std/`` and
requires an exact match against the tables in the document, in both directions.

That catches the realistic failures:

* a new ``@deprecated`` marker is added and never documented;
* a symbol is removed from the sources but lingers in the table;
* a documented *replacement* does not exist (prose rot).
"""

import re
from pathlib import Path

import pytest

from tests.conftest import REPO

DOC = REPO / "docs" / "DEPRECATIONS.md"
STD = REPO / "std"

# No module is exempt: the oracle legacy types are listed individually too.
_SKIP_MODULES: set = set()

# Modules that may legitimately appear as `module.symbol` in a replacement cell.
_STDLIB_MODULES = {"tally", "scrolls", "loom", "oracle", "atlas", "spark", "seal"}
_MODULE_SYMBOLS_CACHE: dict = {}

# `## @deprecated Use `x` instead.` / `# @deprecated Use x instead.`
_REASON_RE = re.compile(r"@deprecated\s*(.*)")


def _deprecated_symbols():
    """module -> {symbol: reason} for every ``@deprecated`` in hand-written std/."""
    result = {}
    for path in sorted(STD.glob("*.pengu")):
        if path.name.endswith(".d.pengu"):
            continue
        module = path.name[: -len(".pengu")]
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "@deprecated" not in line:
                continue
            # The marker documents the *next* declaration in the block. For a
            # method that is the following `weave`; for a type it is the rune.
            decl = None
            for k in range(i + 1, min(i + 10, len(lines))):
                m = re.match(
                    r"^\s*(weave|rune|echo|omen|alias|seal)\s+([A-Za-z_]\w*)", lines[k]
                )
                if m:
                    decl = (m.group(1), m.group(2))
                    break
            if decl is None:
                continue  # prose mention in a module header
            reason = _REASON_RE.search(line).group(1).strip()
            result.setdefault(module, {})[decl[1]] = reason
    return result


def _documented_symbols():
    """module -> {symbol} taken from the DEPRECATIONS.md tables.

    A row looks like ``| `tally.average` | `tally.mean` | 0.14.0 | 1.x |``.
    """
    text = DOC.read_text(encoding="utf-8")
    current_module = None
    documented = {}
    for line in text.splitlines():
        heading = re.match(r"^##\s+\d+\.\s+`std\.([a-z_]+)`", line)
        if heading:
            current_module = heading.group(1)
            documented.setdefault(current_module, set())
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("Symbol", "---") or set(cells[0]) <= {"-"}:
            continue
        first = cells[0]
        m = re.match(r"^`([A-Za-z_][\w.]*)`$", first)
        if not m or current_module is None:
            continue
        ref = m.group(1)
        # `tally.average` -> `average`.  The scrolls table names methods as
        # `string.find` while the source marker sits on the `enchanting string`
        # method `find`, so take the last dotted segment.
        symbol = ref.rsplit(".", 1)[-1]
        documented[current_module].add(symbol)
    return documented


def test_doc_exists():
    assert DOC.is_file(), "docs/DEPRECATIONS.md is missing"


@pytest.mark.parametrize("module", sorted(_deprecated_symbols()))
def test_every_deprecated_symbol_is_documented(module):
    actual = set(_deprecated_symbols()[module])
    if module in _SKIP_MODULES:
        pytest.skip("oracle markers are grouped per legacy type in the doc")
    documented = _documented_symbols().get(module, set())
    missing = sorted(actual - documented)
    assert not missing, (
        f"std.{module}: deprecated symbols missing from docs/DEPRECATIONS.md: {missing}"
    )


@pytest.mark.parametrize("module", sorted(_documented_symbols()))
def test_documented_symbols_still_exist(module):
    """A table row must not outlive the marker it describes."""
    if module in _SKIP_MODULES:
        pytest.skip("oracle markers are grouped per legacy type in the doc")
    documented = _documented_symbols()[module]
    actual = set(_deprecated_symbols().get(module, {}))
    stale = sorted(documented - actual)
    assert not stale, (
        f"std.{module}: docs/DEPRECATIONS.md lists symbols that are no longer "
        f"deprecated: {stale}"
    )


def test_every_row_has_a_replacement_and_a_status():
    text = DOC.read_text(encoding="utf-8")
    bad = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in ("Symbol",):
            continue
        if set(cells[0]) <= {"-"}:
            continue
        if not re.match(r"^`[A-Za-z_][\w.]*`$", cells[0]):
            continue
        replacement, status = cells[1], cells[-1]
        if not replacement or replacement in ("", "-"):
            bad.append(f"no replacement: {cells[0]}")
        if status not in ("1.x", "blocked"):
            bad.append(f"bad status {status!r}: {cells[0]}")
        # A `module.symbol` reference in the replacement must resolve. Only
        # stdlib module names are checked, so field/expression prose such as
        # `m.value` is not mistaken for a symbol.
        for ref in re.findall(r"`([a-z_][\w]*)\.([a-z_]\w*)`", replacement):
            mod, sym = ref
            if mod not in _STDLIB_MODULES:
                continue
            if sym not in _module_symbols().get(mod, set()):
                bad.append(f"{cells[0]} -> {mod}.{sym} does not exist")
    assert not bad, "malformed deprecation rows:\n  " + "\n  ".join(bad)


def _module_symbols():
    """module -> set of declared symbol names (weaves, runes, methods, ...)."""
    if _MODULE_SYMBOLS_CACHE:
        return _MODULE_SYMBOLS_CACHE
    for path in STD.glob("*.pengu"):
        if path.name.endswith(".d.pengu"):
            continue
        module = path.stem
        names = _MODULE_SYMBOLS_CACHE.setdefault(module, set())
        for m in re.finditer(
            r"^\s*(?:weave|declare|rune|echo|omen|alias|seal|const)\s+([A-Za-z_]\w*)",
            path.read_text(encoding="utf-8"),
            re.M,
        ):
            names.add(m.group(1))
    return _MODULE_SYMBOLS_CACHE
