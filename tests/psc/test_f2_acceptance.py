"""Acceptance gate for PSC F2 (parser, AST, recovery).

Builds the native `psc` binary with the source-checkout compiler and runs the
committed F2 suite. Skips when no C compiler is available.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc"
BIN = PSC / "build" / ("psc.exe" if os.name == "nt" else "psc")


def _run(args, cwd=PSC, timeout=300, input_text=None):
    return subprocess.run(
        [str(a) for a in args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        input=input_text,
    )


@pytest.fixture(scope="module")
def psc_binary() -> Path:
    if not (shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")):
        pytest.skip("no C compiler")
    if not BIN.exists():
        built = _run([sys.executable, ROOT / "pengu_project.py", "build"])
        if built.returncode != 0:
            pytest.skip(f"psc build failed: {built.stderr[-2000:]}")
    return BIN


def test_f2_golden(psc_binary):
    proc = _run([sys.executable, PSC / "tools" / "run_f2_checks.py"], timeout=600)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_f2_unit(psc_binary):
    proc = _run(
        [sys.executable, ROOT / "pengu_project.py", "run", "tests/parser_unit.pengu",
         "--no-cache"],
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK parser_unit" in proc.stdout


def test_f2_corpus(psc_binary):
    proc = _run(
        [sys.executable, ROOT / "pengu_project.py", "run", "tests/parser_corpus.pengu",
         "--no-cache"],
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "bad=0" in proc.stdout


def test_cli_parse_stdin_and_json(psc_binary):
    proc = _run([psc_binary, "parse", "--quiet", "--stdin"], input_text="weave main into int:\n    return 0\n")
    assert proc.returncode == 0, proc.stderr
    assert "start" in proc.stdout
    assert "weave_decl" in proc.stdout
    bad = PSC / "tests" / "fixtures" / "parser_bad_multi.pengu"
    proc = _run([psc_binary, "parse", "--quiet", "--check", "--stop-after-first",
                 "--diagnostics=json", bad])
    assert proc.returncode == 1
    payload = json.loads(proc.stderr)
    assert payload and payload[0]["code"] == "E0000"
    aliased = _run([psc_binary, "ast", "--quiet", "--no-header", bad.parent / "basic.pengu"])
    assert aliased.returncode == 0
    assert "start" in aliased.stdout


def test_f2_depth_and_chain(psc_binary):
    deep = "weave f into int:\n    return " + "(" * 520 + "1" + ")" * 520 + "\n"
    proc = _run([psc_binary, "parse", "--quiet", "--check", "--diagnostics=json", "--stdin"],
                input_text=deep)
    assert proc.returncode == 1
    payload = json.loads(proc.stderr)
    assert payload and payload[0]["code"] == "E0000"
    assert "depth" in payload[0]["message"]
    chain = PSC / "tests" / "fixtures" / "chain_multiline.pengu"
    proc = _run([psc_binary, "parse", "--quiet", "--no-header", chain])
    assert proc.returncode == 0
    assert "dot_access" in proc.stdout


@pytest.mark.skipif(
    os.environ.get("PSC_PARITY") != "1",
    reason="set PSC_PARITY=1 to run the stage0 AST/error oracles",
)
def test_f2_stage0_ast_parity(psc_binary):
    proc = _run(
        [sys.executable, PSC / "tools" / "lark_ast_oracle.py",
         "--psc", psc_binary, "--root", "std", "tests", "psc/src"],
        cwd=ROOT,
        timeout=900,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "diverged=0" in proc.stdout


@pytest.mark.skipif(
    os.environ.get("PSC_PARITY") != "1",
    reason="set PSC_PARITY=1 to run the stage0 AST/error oracles",
)
def test_f2_stage0_error_parity(psc_binary):
    proc = _run(
        [sys.executable, PSC / "tools" / "lark_parse_error_oracle.py",
         "--psc", psc_binary],
        cwd=ROOT,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "failures=0" in proc.stdout
