"""Acceptance gate for PSC F3 (semantic analysis).

Builds/reuses the native `psc` binary and exercises the public `psc check`
surface plus the internal smoke programs. The full corpus is represented by a
curated manifest so the default test run stays fast; ``PSC_F3_FULL=1`` runs the
whole `std`, `tests` and `psc/src` tree.
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

CURATED = [
    "psc/src/main.pengu",
    "psc/src/psc/sema/api.pengu",
    "psc/src/psc/sema/check/body.pengu",
    "psc/src/psc/sema/types/table.pengu",
    "psc/src/psc/sema/infer/core.pengu",
    "std/oracle.pengu",
    "std/atlas.pengu",
    "std/scrolls.pengu",
    "std/petitio.pengu",
    "tests/compiler/fixtures/judge_over/05_nested_judge.pengu",
    "tests/conformance/compliance/lingua_binding_raw.pengu",
    "tests/wasm/std_web_smoke.pengu",
]


def _run(args, cwd=PSC, timeout=600, input_text=None):
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
        built = _run([sys.executable, ROOT / "pengu_project.py", "build"], timeout=600)
        if built.returncode != 0:
            pytest.skip(f"psc build failed: {built.stderr[-2000:]}")
    return BIN


def _check(psc_binary: Path, rel: str):
    return _run([psc_binary, "check", "--no-color", str(ROOT / rel)], cwd=ROOT, timeout=600)


def test_f3_smoke_programs(psc_binary):
    for name, marker in [
        ("sema_smoke", "sema smoke ok"),
        ("sema_api_smoke", "api smoke ok"),
        ("sema_check_smoke", "collect smoke bad-return: errors=1"),
        ("flag", ""),
    ]:
        proc = _run(
            [sys.executable, ROOT / "pengu_project.py", "run", f"tests/{name}.pengu",
             "--no-cache"],
            timeout=600,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert marker in proc.stdout or marker == ""


@pytest.mark.parametrize("rel", CURATED)
def test_f3_curated_corpus(psc_binary, rel):
    proc = _check(psc_binary, rel)
    assert proc.returncode == 0, f"{rel}\n{proc.stdout}{proc.stderr}"


def test_f3_cli_stdin_json(psc_binary):
    ok = "weave main into int:\n    return 0\n"
    proc = _run([psc_binary, "check", "--no-color", "--stdin"], cwd=ROOT, input_text=ok)
    assert proc.returncode == 0, proc.stderr
    bad = "weave main into int:\n    return missing\n"
    proc = _run([psc_binary, "check", "--no-color", "--diagnostics=json", "--stdin"],
                cwd=ROOT, input_text=bad)
    assert proc.returncode == 1
    payload = json.loads(proc.stderr)
    assert payload and payload[0]["code"] == "E0004"


@pytest.mark.parametrize(
    "source,code",
    [
        ("weave main into int:\n    return missing\n", "E0004"),
        ('weave f into int:\n    return "x"\n', "E0005"),
        ("weave main into int:\n    let x as int is 1\n    set x is 2\n    return x\n", "E0006"),
    ],
)
def test_f3_error_codes(psc_binary, source, code):
    proc = _run([psc_binary, "check", "--no-color", "--diagnostics=json", "--stdin"],
                cwd=ROOT, input_text=source)
    assert proc.returncode == 1
    payload = json.loads(proc.stderr)
    assert any(d["code"] == code for d in payload), payload


@pytest.mark.skipif(
    os.environ.get("PSC_F3_FULL") != "1",
    reason="set PSC_F3_FULL=1 to check the whole corpus",
)
def test_f3_full_corpus(psc_binary):
    failures = []
    files = sorted(
        p for base in ("std", "tests", "psc/src") for p in (ROOT / base).rglob("*.pengu")
    )
    for path in files:
        proc = _run([psc_binary, "check", "--no-color", "--max-errors=1", str(path)],
                    timeout=600)
        if proc.returncode != 0:
            failures.append(f"{path.relative_to(ROOT)}: {proc.stderr.splitlines()[:1]}")
    assert not failures, "\n".join(failures)
