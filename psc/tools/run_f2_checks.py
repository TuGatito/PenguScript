#!/usr/bin/env python3
"""Golden tests de F2 (parser/AST). Dev-only.

Uso:
    python psc/tools/run_f2_checks.py
    python psc/tools/run_f2_checks.py --update-golden
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

AST_CASES = [
    ("fixtures/basic", "tests/fixtures/basic.pengu", []),
    ("fixtures/chain_multiline", "tests/fixtures/chain_multiline.pengu", []),
    ("fixtures/parser_decls", "tests/fixtures/parser_decls.pengu", []),
    ("fixtures/parser_expr", "tests/fixtures/parser_expr.pengu", []),
    ("fixtures/antiquus_ok", "tests/fixtures/antiquus_ok.pengu", []),
    ("corpus/arena_ast", "../tests/conformance/compliance/arena_ast.pengu", []),
    ("corpus/judge_over_guards", "../tests/compiler/fixtures/judge_over/03_guards.pengu", []),
    ("corpus/judge_patterns_state", "../tests/compiler/fixtures/judge_patterns/03_state_and_tuple.pengu", []),
    ("corpus/label_for_in", "../tests/compiler/fixtures/labels/05_label_on_for_in.pengu", []),
    ("corpus/type_of_nominal", "../tests/compiler/fixtures/type_of/03_nominal.pengu", []),
    ("std/arena", "../std/arena.pengu", []),
    ("std/json", "../std/json.pengu", []),
    ("std/compressus", "../std/compressus.pengu", []),
    ("std/rites", "../std/rites.pengu", []),
    ("src/parse_state", "src/psc/parse/state.pengu", []),
    ("src/stmt_core", "src/psc/parse/stmt/core.pengu", []),
    ("src/expr_ops", "src/psc/parse/expr/ops.pengu", []),
    ("src/expr_calls", "src/psc/parse/expr/calls.pengu", []),
    ("src/expr_util", "src/psc/parse/expr/util.pengu", []),
    ("src/decl_core", "src/psc/parse/decl/core.pengu", []),
]

DIAG_CASES = [
    ("bad_multi", "tests/fixtures/parser_bad_multi.pengu"),
    ("bad_and", "tests/fixtures/parser_bad_and.pengu"),
    ("bad_at", "tests/fixtures/parser_bad_at.pengu"),
    ("bad_colon", "tests/fixtures/parser_bad_colon.pengu"),
    ("bad_else", "tests/fixtures/parser_bad_else.pengu"),
    ("unterminated_string", "tests/fixtures/unterminated_string.pengu"),
    ("indent_bad", "tests/fixtures/indent_bad.pengu"),
    ("unclosed_bracket", "tests/fixtures/unclosed_bracket.pengu"),
]


def run_psc(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(BIN), *args],
        cwd=str(PSC_DIR),
        capture_output=True,
        text=True,
    )


def check_ast(update: bool) -> int:
    failures = 0
    golden_dir = PSC_DIR / "tests" / "golden" / "ast"
    golden_dir.mkdir(parents=True, exist_ok=True)
    for name, path, extra in AST_CASES:
        proc = run_psc(["parse", "--quiet", "--no-header", path, *extra])
        if proc.returncode not in (0, 1):
            print(f"FAIL ast {name}: psc rc={proc.returncode}")
            print(proc.stderr[:1000])
            failures += 1
            continue
        target = golden_dir / f"{name.replace('/', '_')}.txt"
        if update or not target.exists():
            target.write_text(proc.stdout, encoding="utf-8")
            print(f"updated {target.relative_to(ROOT)}")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != proc.stdout:
            print(f"FAIL ast {name}: {target.relative_to(ROOT)}")
            failures += 1
        else:
            print(f"ok   ast {name}")
    return failures


def check_diagnostics(update: bool) -> int:
    failures = 0
    golden_dir = PSC_DIR / "tests" / "golden" / "parse_diagnostics"
    golden_dir.mkdir(parents=True, exist_ok=True)
    for name, path in DIAG_CASES:
        proc = run_psc(["parse", "--quiet", "--no-color", "--check", path])
        target = golden_dir / f"{name}.txt"
        if update or not target.exists():
            target.write_text(proc.stderr, encoding="utf-8")
            print(f"updated {target.relative_to(ROOT)}")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != proc.stderr:
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
    failures = check_ast(args.update_golden)
    failures += check_diagnostics(args.update_golden)
    print(f"\ngolden failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
