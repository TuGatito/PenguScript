"""`enchanting` — the methods a type gains from an imported module.

Reported as: ``import std.numerus`` followed by
``calling float_var.clamp with 20, -20`` was rejected with

    [E0004] Type 'f32' has no method 'clamp'
    help: Declare 'weave clamp' inside 'enchanting f32:'.

`clamp` *is* declared — by ``enchanting shard T where T: Num and T: Ordo and
T: Par:`` in `std/numerus.pengu`. Two separate defects hid it:

* the checker resolved the import graph by re-reading the file on disk, so a
  buffer that had just gained ``import std.numerus`` was checked against a file
  that did not have it yet; the module was never collected and none of its
  methods were registered (see `test_unsaved_import.py` for that half, which is
  about *diagnostics*);
* dot completion only understood ``rune`` / ``echo`` / ``omen`` receivers, so
  even with the methods registered, ``x.`` on a primitive or a container offered
  nothing at all.

This module checks the mechanism on a **synthetic module** (milliseconds, no
stdlib import) and then the reported case verbatim against `std.numerus`. The
exhaustive sweep over every std `enchanting` block lives in
`test_enchanting_std_surface.py`, which is marked ``slow`` because each case
costs a full check of a real std module's import graph.
"""
from __future__ import annotations

from typing import List

import pytest
from lsprotocol.types import DiagnosticSeverity

pytestmark = pytest.mark.smoke

#: A project-local module exercising all four ways a type gains a method:
#: a bounded shard block, a concrete primitive block, a generic container block,
#: and a rune with an `enchanting` block. No stdlib import, so a check costs
#: about a millisecond.
MODULE = '''enchanting shard T where T: Num and T: Ordo and T: Par:
    ## Local stand-in for `numerus.clamp`.
    weave clamp_local with lo as T, hi as T into T:
        if self < lo:
            return lo
        if self > hi:
            return hi
        return self

enchanting int:
    weave twice_local into int:
        return self + self

enchanting list of shard T where T: Par:
    weave first_or_local with fallback as T into T:
        if calling self.is_empty:
            return fallback
        return calling self.at with 0

rune Box:
    v as int

enchanting Box:
    weave get_local into int:
        return self.v
'''

PROBE = '''import boxmod

weave probe with a as int, b as f32, l as list of int, box as Box into int:
{body}
    return 0
'''

#: The state the editor is in while typing `<receiver>.`: the line does not
#: parse, so this also exercises the symbol-recovery pass.
TYPING = '''import boxmod

weave probe with a as int, b as f32, l as list of int, box as Box into int:
    var sink as int is 0
    set sink is {receiver}.
    return 0
'''

CALLS = [
    ("shard block on an int", "calling a.clamp_local with 0, 10"),
    ("shard block on an f32", "calling b.clamp_local with 0.0, 10.0"),
    ("concrete primitive block", "calling a.twice_local"),
    ("generic container block", "calling l.first_or_local with 0"),
    ("rune method block", "calling box.get_local"),
]

OFFERED = [
    ("shard block on an int", "a", "clamp_local"),
    ("shard block on an f32", "b", "clamp_local"),
    ("concrete primitive block", "a", "twice_local"),
    ("generic container block", "l", "first_or_local"),
    ("rune method block", "box", "get_local"),
]


def _program(call: str) -> str:
    return PROBE.format(body=f"    {call}")


def _typing(receiver: str) -> str:
    return TYPING.format(receiver=receiver)


def _errors(lsp, source: str) -> List[str]:
    lsp.open(source)
    return [
        d.message for d in lsp.diagnostics
        if d.severity == DiagnosticSeverity.Error
    ]


@pytest.fixture
def project(lsp):
    """Writes the synthetic module next to the document under test."""
    (lsp.directory / "boxmod.pengu").write_text(MODULE, encoding="utf-8")
    return lsp


@pytest.mark.parametrize("label,call", CALLS, ids=[c[0] for c in CALLS])
def test_a_method_from_an_imported_enchanting_block_type_checks(project, label, call):
    assert _errors(project, _program(call)) == []


@pytest.mark.parametrize("label,receiver,method", OFFERED, ids=[c[0] for c in OFFERED])
def test_a_method_from_an_imported_enchanting_block_is_offered(project, label, receiver, method):
    project.open(_typing(receiver))

    labels = project.complete_after(f"{receiver}.")

    assert method in labels, f"{label}: {method} missing; offered={sorted(labels)}"


@pytest.mark.parametrize("label,receiver,method", OFFERED, ids=[c[0] for c in OFFERED])
def test_a_half_typed_receiver_still_offers_the_method(project, label, receiver, method):
    project.open(_typing(receiver))

    labels = project.complete_after(f"{receiver}.")

    assert method in labels, f"{label}: {method} missing; offered={sorted(labels)}"


def test_container_methods_are_offered_next_to_the_enchanting_ones(project):
    """A `list` receiver also gets the builtin methods the inferrer hardcodes."""
    project.open(_typing("l"))

    labels = set(project.complete_after("l."))

    assert "first_or_local" in labels
    assert {"len", "is_empty", "at", "push"} <= labels, sorted(labels)


def test_a_rune_keeps_its_fields_next_to_its_methods(project):
    project.open(_typing("box"))

    labels = set(project.complete_after("box."))

    assert {"v", "get_local"} <= labels, sorted(labels)


def test_a_bounded_shard_method_is_not_offered_on_a_non_member(project):
    """`Num and Ordo and Par` excludes `Box`, so `clamp_local` must not appear."""
    project.open(_typing("box"))

    labels = set(project.complete_after("box."))

    assert "clamp_local" not in labels
    assert "twice_local" not in labels


# ---------------------------------------------------------------------------
# The reported case, verbatim, against the real stdlib
# ---------------------------------------------------------------------------

CLAMP_PROGRAM = '''import std.numerus

weave main into int:
    var variable_flotante as f32 is 20.0
    let resultado as f32 is calling variable_flotante.clamp with 20.0, -20.0
    return 0
'''


def test_the_reported_std_numerus_clamp_case_type_checks(lsp):
    assert _errors(lsp, CLAMP_PROGRAM) == []


def test_the_reported_std_numerus_clamp_is_offered(lsp):
    lsp.open(CLAMP_PROGRAM)

    labels = lsp.complete_after("variable_flotante.")

    assert "clamp" in labels, labels
    # …and the rest of the universal numeric surface, from the same block.
    assert {"abs", "signum", "min_with", "max_with"} <= set(labels), labels


def test_an_incomplete_std_method_call_still_offers_the_method(lsp):
    """The state the editor is in while typing: `variable_flotante.cla`."""
    lsp.open(CLAMP_PROGRAM.replace("clamp with 20.0, -20.0", "cla"))

    labels = lsp.complete_after("variable_flotante.")

    assert "clamp" in labels, labels
