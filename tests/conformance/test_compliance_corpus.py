"""Conformance corpus: one realistic program per fundamental module.

The corpus is deliberately tiny and executable.  A program is accepted only
when ``pengu run`` checks it, compiles it and it prints ``OK <name>``.  The
script used to also invoke ``pengu check`` and ``pengu build`` separately, which
re-parsed and re-generated the whole corpus three times; ``pengu run`` performs
both steps internally, so one process proves the same contract.  The ``OK``
marker keeps a silently-empty program from passing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.conformance, pytest.mark.slow]

CORPUS = Path(__file__).parent / "compliance"
PROGRAMS = sorted(CORPUS.glob("*.pengu"))


def test_the_corpus_is_not_empty() -> None:
    assert len(PROGRAMS) == 66, [p.name for p in PROGRAMS]


@pytest.mark.parametrize("program", PROGRAMS, ids=[p.stem for p in PROGRAMS])
def test_program_checks_builds_and_runs(program: Path, compile_and_run):
    output = compile_and_run(program)
    assert f"OK {program.stem}" in output, output
    assert "FAIL" not in output, output
