#!/usr/bin/env python3
"""Golden tests y comprobaciones de F1 (dev-only).

Uso:
    python psc/tools/run_f1_checks.py
    python psc/tools/run_f1_checks.py --update-golden

Los golden viven en `psc/tests/golden/`. Las rutas se pasan relativas a `psc/`
para que el dump sea reproducible.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PSC_DIR = Path(__file__).resolve().parents[1]
ROOT = PSC_DIR.parent
BIN = PSC_DIR / "build" / ("psc.exe" if os.name == "nt" else "psc")

TOKEN_CASES = [
    ("fixtures/basic", "tests/fixtures/basic.pengu", ["--comments"]),
    ("fixtures/strings", "tests/fixtures/strings.pengu", []),
    ("fixtures/comments", "tests/fixtures/comments.pengu", ["--comments"]),
    ("fixtures/antiquus_ok", "tests/fixtures/antiquus_ok.pengu", []),
    ("fixtures/crlf", "tests/fixtures/crlf.pengu", []),
    ("fixtures/bom", "tests/fixtures/bom.pengu", []),
    ("fixtures/operators", "tests/fixtures/operators.pengu", []),
    ("fixtures/triple_interp", "tests/fixtures/triple_interp.pengu", []),
    ("fixtures/raw_triple", "tests/fixtures/raw_triple.pengu", []),
    ("src/source", "src/psc/source.pengu", []),
    ("src/decode", "src/psc/lexer_decode.pengu", []),
    ("src/lexer", "src/psc/lexer.pengu", []),
    ("corpus/arena_ast", "../tests/conformance/compliance/arena_ast.pengu", []),
    ("std/arena", "../std/arena.pengu", []),
]

DIAG_CASES = [
    ("unterminated_string", "tests/fixtures/unterminated_string.pengu"),
    ("unterminated_triple", "tests/fixtures/unterminated_triple.pengu"),
    ("invalid_char", "tests/fixtures/invalid_char.pengu"),
    ("indent_bad", "tests/fixtures/indent_bad.pengu"),
    ("mixed_indent", "tests/fixtures/mixed_indent.pengu"),
    ("unclosed_bracket", "tests/fixtures/unclosed_bracket.pengu"),
    ("unmatched_bracket", "tests/fixtures/unmatched_bracket.pengu"),
    ("unknown_char", "tests/fixtures/unknown_char.pengu"),
    ("antiquus_missing", "tests/fixtures/antiquus_missing.pengu"),
    ("antiquus_empty", "tests/fixtures/antiquus_empty.pengu"),
]


def run_psc(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(BIN), *args],
        cwd=str(PSC_DIR),
        capture_output=True,
        text=True,
    )


def check_tokens(update: bool) -> int:
    failures = 0
    golden_dir = PSC_DIR / "tests" / "golden" / "tokens"
    golden_dir.mkdir(parents=True, exist_ok=True)
    for name, path, extra in TOKEN_CASES:
        proc = run_psc(["lex", "--quiet", "--no-color", path, *extra])
        if proc.returncode not in (0, 1):
            print(f"FAIL token {name}: psc rc={proc.returncode}")
            print(proc.stderr[:1000])
            failures += 1
            continue
        target = golden_dir / f"{name.replace('/', '_')}.txt"
        expected = proc.stdout
        if update or not target.exists():
            target.write_text(expected, encoding="utf-8")
            print(f"updated {target.relative_to(ROOT)}")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != expected:
            print(f"FAIL token {name}: {target.relative_to(ROOT)}")
            failures += 1
        else:
            print(f"ok   token {name}")
    return failures


def check_diagnostics(update: bool) -> int:
    failures = 0
    golden_dir = PSC_DIR / "tests" / "golden" / "diagnostics"
    golden_dir.mkdir(parents=True, exist_ok=True)
    for name, path in DIAG_CASES:
        proc = run_psc(["lex", "--quiet", "--no-color", "--check", path])
        target = golden_dir / f"{name}.txt"
        expected = proc.stderr
        if update or not target.exists():
            target.write_text(expected, encoding="utf-8")
            print(f"updated {target.relative_to(ROOT)}")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != expected:
            print(f"FAIL diag {name}: {target.relative_to(ROOT)}")
            failures += 1
        else:
            print(f"ok   diag {name}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-golden", action="store_true")
    args = ap.parse_args()
    if not BIN.exists():
        print(f"missing {BIN}; run `python pengu_project.py build` in psc/", file=sys.stderr)
        return 2
    failures = check_tokens(args.update_golden)
    failures += check_diagnostics(args.update_golden)
    print(f"\ngolden failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
