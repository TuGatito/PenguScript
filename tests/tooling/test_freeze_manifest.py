"""Phase 10, item 10.1 — the freeze manifest.

`docs/FREEZE.md` declares the public surface of PenguScript 1.0.  A declaration
that nothing checks is prose, so this module reads every `<!-- freeze:KEY -->`
block out of the document and compares it against **the thing it claims to
freeze** — never against a second copy of the same list:

===========================  =========================================================
freeze block                 measured from
===========================  =========================================================
`keywords`, `soft-keywords`  `LANGUAGE.md` §3.4 (the normative list)
`abi-version`                `#define PENGU_ABI_VERSION` in `pengu_runtime.h`
`global-flags`, `subcommands`  `create_cli_parser()` introspection
`rc-contract`                three real CLI invocations (0 / 1 / 2)
`stdlib-modules`, `stdlib-bindings`  the files in `std/`
`opt-in-modules`             the modules `tests/stdlib/test_std_orphan_modules.py` pins
`lsp-features`               the LSP server's own feature registry
`error-codes`, `warning-codes`  `docs/error_catalog.json`
===========================  =========================================================

Adding a subcommand, a keyword, an error code or a stdlib module without
updating the document fails here.  That is the whole point: the freeze cannot
rot into a description of a tree that no longer exists.

Rule C2 is covered by `test_the_comparison_detects_drift`, a negative control
that deletes an entry from a *copy* of the declaration and asserts the
comparison notices.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List

import pytest

from tests.conftest import REPO

FREEZE = REPO / "docs/FREEZE.md"
LANGUAGE = REPO / "LANGUAGE.md"
RUNTIME_HEADER = REPO / "pengu_runtime.h"
ERROR_CATALOG = REPO / "docs" / "error_catalog.json"
STD = REPO / "std"

#: `<!-- freeze:key -->` + one fenced block + `<!-- /freeze:key -->`.
_BLOCK_RE = re.compile(
    r"<!-- freeze:([A-Za-z0-9_-]+) -->\s*```[a-zA-Z]*\n(.*?)```\s*<!-- /freeze:\1 -->",
    re.DOTALL,
)


def _declared() -> Dict[str, List[str]]:
    """The manifest exactly as `docs/FREEZE.md` states it."""
    text = FREEZE.read_text(encoding="utf-8")
    blocks: Dict[str, List[str]] = {}
    for match in _BLOCK_RE.finditer(text):
        blocks[match.group(1)] = [
            line.strip() for line in match.group(2).splitlines() if line.strip()
        ]
    return blocks


# ---------------------------------------------------------------------------
# The real values, each read from its own source of truth
# ---------------------------------------------------------------------------


def _language_keywords() -> List[str]:
    text = LANGUAGE.read_text(encoding="utf-8")
    assert "### 3.4 Reserved words" in text, "LANGUAGE.md lost §3.4"
    body = text.split("### 3.4 Reserved words", 1)[1]
    fenced = body.split("```text", 1)[1].split("```", 1)[0]
    return sorted(set(fenced.split()))


def _soft_keywords() -> List[str]:
    text = LANGUAGE.read_text(encoding="utf-8")
    assert "**Soft Keywords:**" in text, "LANGUAGE.md lost the soft-keyword list"
    body = text.split("**Soft Keywords:**", 1)[1].split("**C Identifier Protection", 1)[0]
    # Only the *bullet heads* are the keyword list: the explanation backticks
    # ordinary identifiers too ("Active only immediately after `var` or `let`").
    found: List[str] = []
    for line in body.splitlines():
        head = re.match(r"^- ((?:`[a-z]+`(?:,\s*)?)+):", line)
        if head:
            found.extend(re.findall(r"`([a-z]+)`", head.group(1)))
    assert found, "no soft keyword parsed out of LANGUAGE.md §3.4"
    return sorted(set(found))


def _abi_version() -> List[str]:
    text = RUNTIME_HEADER.read_text(encoding="utf-8")
    match = re.search(r"#define\s+PENGU_ABI_VERSION\s+(\d+)", text)
    assert match, "pengu_runtime.h does not define PENGU_ABI_VERSION"
    return [f"PENGU_ABI_VERSION = {match.group(1)}"]


def _global_flags() -> List[str]:
    from pengu_project import create_cli_parser

    flags = set()
    for action in create_cli_parser()._actions:
        for option in action.option_strings:
            if option.startswith("--"):
                flags.add(option)
    return sorted(flags)


def _subcommands() -> List[str]:
    from pengu_project import create_cli_parser

    for action in create_cli_parser()._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            return sorted(action.choices)
    raise AssertionError("the CLI parser declares no subcommands")


def _stdlib_modules() -> List[str]:
    return sorted(p.name for p in STD.glob("*.pengu") if not p.name.endswith(".d.pengu"))


def _stdlib_bindings() -> List[str]:
    return sorted(p.name for p in STD.glob("*.d.pengu"))


def _opt_in_modules() -> List[str]:
    """The modules `tests/stdlib/test_std_orphan_modules.py` pins as opt-in.

    Reusing that table means the freeze cannot disagree with the test that
    owns the property.
    """
    from tests.stdlib.test_std_orphan_modules import _EXPECTED_IMPORTERS

    return sorted(f"{name}.pengu" for name in _EXPECTED_IMPORTERS)


def _lsp_features() -> List[str]:
    from pengu_lsp.server import server

    fm = server.protocol.fm
    return sorted(set(fm.features) - set(fm.builtin_features))


def _catalog() -> Dict[str, List[str]]:
    data = json.loads(ERROR_CATALOG.read_text(encoding="utf-8"))
    return {
        "error-codes": sorted(set(data["errors"]) | set(data["project"])),
        "warning-codes": sorted(data["warnings"]),
    }


ACTUAL_READERS: Dict[str, Callable[[], List[str]]] = {
    "keywords": _language_keywords,
    "soft-keywords": _soft_keywords,
    "abi-version": _abi_version,
    "global-flags": _global_flags,
    "subcommands": _subcommands,
    "stdlib-modules": _stdlib_modules,
    "stdlib-bindings": _stdlib_bindings,
    "opt-in-modules": _opt_in_modules,
    "lsp-features": _lsp_features,
    "error-codes": lambda: _catalog()["error-codes"],
    "warning-codes": lambda: _catalog()["warning-codes"],
}

#: The blocks the document must have.  Separate from `ACTUAL_READERS` only
#: because `rc-contract` is measured by running the CLI, not by reading a file.
REQUIRED_SURFACES = tuple(sorted(ACTUAL_READERS)) + ("rc-contract",)


def _diff(declared: List[str], actual: List[str]) -> str:
    """Human-readable difference between a declaration and the tree."""
    missing = sorted(set(actual) - set(declared))
    stale = sorted(set(declared) - set(actual))
    lines = []
    if missing:
        lines.append(f"  not declared in FREEZE.md: {missing}")
    if stale:
        lines.append(f"  declared but gone from the tree: {stale}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The manifest must be complete and well-formed
# ---------------------------------------------------------------------------


def test_the_document_exists_and_declares_every_surface():
    assert FREEZE.is_file(), "docs/FREEZE.md does not exist"
    declared = _declared()
    absent = [key for key in REQUIRED_SURFACES if key not in declared]
    assert absent == [], f"FREEZE.md is missing these `freeze:` blocks: {absent}"


def test_no_frozen_surface_is_declared_empty():
    empty = [key for key, items in _declared().items() if not items]
    assert empty == [], f"these freeze blocks declare nothing: {empty}"


def test_the_freeze_names_its_version():
    text = FREEZE.read_text(encoding="utf-8")
    assert re.search(r"Frozen at \*\*\d+\.\d+\.\d+", text), (
        "FREEZE.md must state which release froze the surface"
    )


# ---------------------------------------------------------------------------
# Every declared list against its real source
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", sorted(ACTUAL_READERS))
def test_frozen_list_matches_the_tree(key):
    declared = _declared().get(key)
    assert declared is not None, f"FREEZE.md has no `freeze:{key}` block"
    actual = ACTUAL_READERS[key]()
    assert actual, f"the tree reports no {key}; the reader is broken, not the document"
    assert not _diff(declared, actual), (
        f"`freeze:{key}` in docs/FREEZE.md differs from the tree:\n"
        f"{_diff(declared, actual)}"
    )


def test_the_cli_freeze_agrees_with_the_contract_suite():
    """The subcommand list is the one `tests/cli/test_cli_contract.py` gates.

    FREEZE.md's own reader uses parser introspection; the contract suite keeps a
    hand-written table so a *renamed* subcommand cannot pass unnoticed.  The two
    must agree, otherwise one of them is describing a CLI that does not exist.
    """
    from tests.cli.test_cli_contract import SUBCOMMANDS

    assert sorted(SUBCOMMANDS) == _subcommands()
    assert _declared()["subcommands"] == _subcommands()


# ---------------------------------------------------------------------------
# 10.1 / rc contract — measured, not quoted
# ---------------------------------------------------------------------------

_BROKEN_PROGRAM = 'weave main into void:\n  var a as int is "not an int"\n'


def test_the_declared_exit_codes_are_the_ones_the_cli_returns(tmp_path):
    """Run the three documented outcomes instead of trusting the table."""
    declared = _declared()["rc-contract"]
    documented = sorted({int(line.split()[0]) for line in declared})
    assert documented == [0, 1, 2], f"FREEZE.md declares rc={documented}"

    broken = tmp_path / "broken.pengu"
    broken.write_text(_BROKEN_PROGRAM, encoding="utf-8")

    observed = {}
    for label, argv in (
        ("success", ["--help"]),
        ("usage", ["check", "--definitely-not-a-flag"]),
        ("type error", ["check", "--entry", str(broken)]),
    ):
        proc = subprocess.run(
            [sys.executable, str(REPO / "pengu_project.py"), *argv],
            cwd=str(REPO), capture_output=True, text=True, timeout=300,
        )
        observed[label] = proc.returncode

    assert sorted(observed.values()) == documented, (
        f"FREEZE.md declares rc={documented} but the CLI returned {observed}"
    )


def test_every_rc_contract_line_carries_a_meaning():
    for line in _declared()["rc-contract"]:
        head, _, tail = line.partition(" ")
        assert head.isdigit(), f"rc-contract line has no code: {line!r}"
        assert tail.strip(), f"rc-contract line has no meaning: {line!r}"


# ---------------------------------------------------------------------------
# Rule C2 — the comparison has teeth
# ---------------------------------------------------------------------------


def test_the_comparison_detects_drift():
    """Negative control: drop an entry and the comparison must notice.

    Without this, `_diff` could be a function that always returns "" and every
    other test in this module would still pass.
    """
    for key, reader in sorted(ACTUAL_READERS.items()):
        actual = reader()
        assert actual, key
        truncated = _declared()[key][:-1]
        assert _diff(truncated, actual), (
            f"removing an entry from `freeze:{key}` would go unnoticed"
        )


def test_an_invented_entry_is_also_caught():
    """The other direction: a subcommand that does not exist must fail too."""
    declared = _declared()["subcommands"]
    inflated = declared + ["teleport"]
    assert _diff(inflated, _subcommands()), (
        "an invented subcommand in FREEZE.md would go unnoticed"
    )
