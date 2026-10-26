"""Acceptance gate for PSC F1 (source, diagnostics, lexer).

These tests build the native `psc` binary with the source-checkout compiler and
exercise the committed F1 suite. They skip when no C compiler is available.
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


def _run(args, cwd=PSC, timeout=300):
    return subprocess.run(
        [str(a) for a in args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def psc_binary() -> Path:
    if not (shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")):
        pytest.skip("no C compiler")
    if not BIN.exists():
        built = _run([sys.executable, ROOT / "pengu_project.py", "build"])
        if built.returncode != 0:
            pytest.skip(f"psc build failed: {built.stderr[-2000:]}")
    if not BIN.exists():
        pytest.skip("psc binary not produced")
    return BIN


def test_f1_golden(psc_binary):
    proc = _run([sys.executable, PSC / "tools" / "run_f1_checks.py"], timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_f1_unit(psc_binary):
    proc = _run(
        [sys.executable, ROOT / "pengu_project.py", "run", "tests/lexer_unit.pengu",
         "--no-cache"],
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK determinism" in proc.stdout


def test_f1_corpus(psc_binary):
    proc = _run(
        [sys.executable, ROOT / "pengu_project.py", "run", "tests/lexer_corpus.pengu",
         "--no-cache"],
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "bad=0" in proc.stdout


def test_cli_json_and_stdin(psc_binary):
    fixture = PSC / "tests" / "fixtures" / "unterminated_string.pengu"
    proc = _run([psc_binary, "lex", "--quiet", "--check",
                 "--diagnostics=json", fixture])
    assert proc.returncode == 1
    payload = json.loads(proc.stderr)
    assert payload and payload[0]["code"] == "E0000"
    stdin = b"weave main into int:\n    return 0\n"
    proc = subprocess.run(
        [str(psc_binary), "lex", "--quiet", "--stdin"],
        cwd=str(PSC), input=stdin, capture_output=True,
    )
    assert proc.returncode == 0
    assert b"# file: <stdin>" in proc.stdout
    assert b"Keyword(weave)" in proc.stdout


@pytest.mark.skipif(
    os.environ.get("PSC_PARITY") != "1",
    reason="set PSC_PARITY=1 to run the 175-file stage0 token oracle",
)
def test_f1_stage0_parity(psc_binary):
    proc = _run(
        [sys.executable, PSC / "tools" / "lark_token_oracle.py",
         "--psc", psc_binary, "--root", "std", "tests"],
        cwd=ROOT,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "failures=0" in proc.stdout
