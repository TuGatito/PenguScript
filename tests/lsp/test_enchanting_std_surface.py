"""Exhaustive sweep: every `enchanting` block in `std/` resolves *and* is offered.

`test_enchanting_methods.py` proves the mechanism on a synthetic module and the
reported `std.numerus` case; this file walks the real 733-method surface.

It is marked ``slow`` on purpose. Each case parses and checks a document that
imports a real std module — `std.numerus` costs ~1.4 s and `std.tally` ~4.3 s
because the checker re-collects the whole transitive import graph — so the sweep
is ~3 minutes and has no business in the smoke tier. It still runs under
`pengu selftest` / `pytest tests`, which is where a change to `enchanting`,
`resolve_imports` or dot completion should be judged.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
from lsprotocol.types import DiagnosticSeverity

ROOT = Path(__file__).resolve().parents[2]
STD = ROOT / "std"

pytestmark = pytest.mark.slow

#: `enchanting` receiver spelling -> (probe type, default value or None).
#: The bound spelling here is the one the std modules use; a block whose
#: receiver is not listed is skipped (the owned types — `Vec2`, `DateTime`,
#: `Logger`, the channels — need a constructor, and `tests/stdlib/` drives those
#: end to end).
RECEIVERS: Dict[str, Tuple[str, str]] = {
    "shard T where T: Num and T: Ordo and T: Par": ("int", "0"),
    "shard T where T: Real": ("f32", "0.0"),
    "shard T where T: Integrum": ("int", "0"),
    "maybe shard T": ("maybe int", "maybe none"),
    "result of shard T to shard E": ("result of int to string", None),
    "list of shard T where T: Donum": ("list of int", "[]"),
    "list of shard T where T: Num": ("list of int", "[]"),
    "list of shard T where T: Donum and T: Ordered": ("list of int", "[]"),
    "list of shard T where T: Num and T: Ordo": ("list of int", "[]"),
    "list of shard T where T: Donum and T: Par": ("list of int", "[]"),
    "list of shard T where T: Integrum and T: Par": ("list of int", "[]"),
    "list of int": ("list of int", "[]"),
    "list of list of string": ("list of list of string", "[]"),
    "map of shard K to shard V where K: Par, V: Par": ("map of string to int", "{}"),
    "map of shard K to shard V where K: Par, V: Num and V: Ordo": ("map of string to int", "{}"),
    "map of shard K to shard V where K: Ordered, V: Par": ("map of string to int", "{}"),
    "map of shard K to shard V where K: Par, V: Ordered": ("map of string to int", "{}"),
    "map of shard K to bool shard K and V where K: Par, V: Par": ("map of string to bool", "{}"),
    "map of string to int": ("map of string to int", "{}"),
    "map of string to float": ("map of string to float", "{}"),
    "map of string to string": ("map of string to string", "{}"),
    "map of string to bool": ("map of string to bool", "{}"),
    "map of int to string": ("map of int to string", "{}"),
    "string": ("string", '"a"'),
    "char": ("char", "'a'"),
    "bool": ("bool", "false"),
    "float": ("f32", "0.0"),
    "f64": ("f64", "0.0"),
}


def _enchanting_blocks(path: Path) -> List[Tuple[str, List[str]]]:
    """``(receiver, [method names])`` for every ``enchanting`` block in a file."""
    out: List[Tuple[str, List[str]]] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^enchanting\s+(.+?)\s*:\s*$", lines[i])
        if not m:
            i += 1
            continue
        receiver, methods, j = m.group(1), [], i + 1
        while j < len(lines):
            line = lines[j]
            if line.strip() and not line.startswith((" ", "\t")):
                break
            w = re.match(r"^\s+weave\s+(?:ritual\s+)?([A-Za-z_][A-Za-z0-9_]*)", line)
            if w:
                methods.append(w.group(1))
            j += 1
        out.append((receiver, methods))
        i = j
    return out


def _cases() -> List[Tuple[str, str, str, List[str], str]]:
    cases = []
    for path in sorted(STD.glob("*.pengu")):
        for receiver, methods in _enchanting_blocks(path):
            probe = RECEIVERS.get(receiver)
            if not probe or not methods:
                continue
            probe_type, default = probe
            if default is None:
                body = f"weave probe with recv as {probe_type} into int:\n"
            else:
                body = f"weave probe into int:\n    var recv as {probe_type} is {default}\n"
            calls = "".join(f"    calling recv.{m}\n" for m in methods)
            source = f"import std.{path.stem}\n\n{body}{calls}    return 0\n"
            cases.append((path.stem, receiver, probe_type, methods, source))
    return cases


ALL_CASES = _cases()
ALL_IDS = [f"{module}-{probe_type.split()[0]}" for module, _, probe_type, _, _ in ALL_CASES]


def test_the_std_enchanting_corpus_is_complete():
    """Guards the sweep: a silent empty corpus would pass forever."""
    assert len(ALL_CASES) >= 20, len(ALL_CASES)
    assert sum(len(m) for _, _, _, m, _ in ALL_CASES) >= 300, "declared methods"


@pytest.mark.parametrize("module,receiver,probe_type,methods,source", ALL_CASES, ids=ALL_IDS)
def test_every_std_enchanting_method_resolves_and_is_offered(lsp, module, receiver, probe_type, methods, source):
    """A single check + completion per block, asserting all of its methods."""
    lsp.open(source)

    errors = [
        d.message for d in lsp.diagnostics
        if d.severity == DiagnosticSeverity.Error
    ]
    assert not any("has no method" in msg for msg in errors), errors

    labels = set(lsp.complete_after("recv."))
    missing = [m for m in methods if m not in labels]
    assert not missing, f"{module} / {probe_type}: {missing} were not offered"
