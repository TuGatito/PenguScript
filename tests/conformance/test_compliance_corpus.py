"""Conformance corpus: one realistic program per fundamental module.

The corpus is deliberately tiny and executable.  A program is accepted only
when it passes ``pengu check``, compiles with ``pengu build`` and prints
``OK <name>`` when run; the last rule keeps a silently-empty program from
passing.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.conformance, pytest.mark.slow]

CORPUS = Path(__file__).parent / "compliance"
PROGRAMS = sorted(CORPUS.glob("*.pengu"))


def test_the_corpus_is_not_empty() -> None:
    assert len(PROGRAMS) == 52, [p.name for p in PROGRAMS]


@pytest.mark.parametrize("program", PROGRAMS, ids=[p.stem for p in PROGRAMS])
def test_program_checks_builds_and_runs(program: Path, pengu_cli, tmp_path, compile_and_run):
    check = pengu_cli("check", str(program))
    assert check.returncode == 0, (
        f"check failed for {program.name}:\n{check.stdout}\n{check.stderr}"
    )

    bundle = tmp_path / f"{program.stem}.c"
    build = pengu_cli("build", "--entry", str(program), "--output", str(bundle))
    assert build.returncode == 0, (
        f"build failed for {program.name}:\n{build.stdout}\n{build.stderr}"
    )
    assert bundle.is_file(), f"build produced no C bundle for {program.name}"

    output = compile_and_run(program)
    assert f"OK {program.stem}" in output, output
    assert "FAIL" not in output, output
