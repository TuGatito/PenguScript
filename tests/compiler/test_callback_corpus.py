"""Conformance corpus for thick functions and context-taking pipelines.

One program per shipped capability, each with an ``.expected`` stdout:

* ``fixtures/functor/`` — ``Fn0``..``Fn3``, a ``Fn`` stored in a rune, a ``Fn``
  parameter, a null context with ``call_or``, and the ``string``/``ref to rune``
  argument types.
* ``fixtures/loom_ctx/`` — one program per ``*_ctx`` function, including the
  empty-list edges and the truncating ``zip_with_ctx``.

Every case is checked at three levels: ``parse_and_check`` (fast, no C), the
real CLI run with exact stdout, and ``pengu check`` + ``pengu build`` with no
warning on the output.  The last one is what proves ``std.functor``'s
``transmute`` opt-out reaches a normal user build.
"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _cases(kind: str):
    return sorted((FIXTURES / kind).glob("*.pengu"))


def _read(case: Path) -> str:
    return case.read_text(encoding="utf-8")


def _expected(case: Path) -> str:
    return case.with_suffix(".expected").read_text(encoding="utf-8")


ALL_CASES = [(kind, case) for kind in ("functor", "loom_ctx") for case in _cases(kind)]
IDS = [f"{kind}/{case.stem}" for kind, case in ALL_CASES]


def test_the_corpus_is_not_empty():
    assert len(_cases("functor")) >= 8
    assert len(_cases("loom_ctx")) >= 9


@pytest.mark.parametrize("kind,case", ALL_CASES, ids=IDS)
def test_corpus_checks_clean(parse_and_check, kind, case):
    errors, _ast, _symbols = parse_and_check(_read(case), filename=str(case))
    assert errors == [], [f"{e.code}: {e}" for e in errors]


@pytest.mark.slow
@pytest.mark.parametrize("kind,case", ALL_CASES, ids=IDS)
def test_corpus_runs_with_expected_output(compile_and_run, kind, case):
    out = compile_and_run(_read(case), tag=case.stem)
    assert out.strip() == _expected(case).strip()


@pytest.mark.slow
@pytest.mark.parametrize("kind,case", ALL_CASES, ids=IDS)
def test_corpus_cli_check_and_build_without_warnings(pengu_cli, tmp_path, kind, case):
    local = tmp_path / case.name
    local.write_text(_read(case), encoding="utf-8")
    check = pengu_cli("check", str(local), cwd=tmp_path)
    assert check.returncode == 0, check.stdout + check.stderr
    assert "warning" not in (check.stdout + check.stderr).lower(), check.stdout + check.stderr
    build = pengu_cli("build", "--entry", str(local), cwd=tmp_path)
    assert build.returncode == 0, build.stdout + build.stderr
    assert "warning" not in (build.stdout + build.stderr).lower(), build.stdout + build.stderr
