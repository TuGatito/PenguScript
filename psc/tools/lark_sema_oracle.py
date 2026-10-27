#!/usr/bin/env python3
"""Compare F3 semantic acceptance/codes with stage0 on literal test cases.

Extracts every ``parse_and_check('''...''')``/``emit_c('''...''')`` source from
``tests/compiler``, runs the stage0 checker in-process and ``psc check --stdin``
in parallel. This is a development oracle, not a gate: PSC intentionally reports
some spans/messages differently, so only acceptance and the first code are
compared.

Usage::

    .venv/bin/python psc/tools/lark_sema_oracle.py --psc psc/build/psc
    .venv/bin/python psc/tools/lark_sema_oracle.py --json /tmp/sema.json --jobs 8
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_checker import PenguChecker  # noqa: E402
from pengu_parser.pengu_errors import PenguError  # noqa: E402
from pengu_parser.pengu_parser import PenguParser  # noqa: E402


def _literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dedent"
        and node.args
    ):
        return _literal(node.args[0])
    return None


def extract_cases(root: Path) -> dict[str, list[str]]:
    cases: dict[str, list[str]] = {}
    for path in sorted(root.glob("tests/compiler/**/test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"parse_and_check", "emit_c"}
                and node.args
            ):
                continue
            source = _literal(node.args[0])
            if source is not None:
                cases.setdefault(source, []).append(
                    f"{path.relative_to(root)}:{node.lineno}"
                )
    return cases


def stage0_codes(source: str) -> list[str]:
    try:
        ast0 = PenguParser().parse(source)
        checker = PenguChecker(base_dir=str(ROOT))
        checker.check(ast0, source=source, filename="t.pengu")
        return []
    except PenguError as exc:
        return [e.code for e in (getattr(exc, "all_errors", None) or [exc])]
    except Exception as exc:  # crash in stage0: keep it visible in the report
        return [f"CRASH:{type(exc).__name__}"]


def psc_codes(psc: Path, source: str, timeout: int) -> tuple[int, list[str]]:
    proc = subprocess.run(
        [str(psc), "check", "--diagnostics=json", "--stdin"],
        input=source,
        text=True,
        capture_output=True,
        cwd=ROOT,
        timeout=timeout,
    )
    try:
        payload = json.loads(proc.stderr)
        return proc.returncode, [d.get("code", "?") for d in payload]
    except json.JSONDecodeError:
        return proc.returncode, []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psc", type=Path, default=ROOT / "psc/build/psc")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--json", type=Path, help="write the full comparison report")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if not args.psc.is_file():
        parser.error(f"psc binary not found: {args.psc}")

    cases = extract_cases(args.root)
    items = list(cases.items())

    def run(item):
        source, locs = item
        expected = stage0_codes(source)
        rc, actual = psc_codes(args.psc, source, 120)
        return {
            "source": source,
            "locs": locs,
            "stage0": expected,
            "psc_rc": rc,
            "psc": actual,
        }

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        report = list(pool.map(run, items))

    valid = [r for r in report if not r["stage0"]]
    invalid = [r for r in report if r["stage0"]]
    valid_rejected = [r for r in valid if r["psc_rc"] != 0]
    invalid_accepted = [r for r in invalid if r["psc_rc"] == 0]
    same_code = [
        r for r in invalid if r["psc"] and r["psc"][0] == r["stage0"][0]
    ]
    print(
        f"cases={len(report)} valid={len(valid)} valid_rejected={len(valid_rejected)} "
        f"invalid={len(invalid)} invalid_accepted={len(invalid_accepted)} "
        f"same_code={len(same_code)}"
    )
    if args.verbose or valid_rejected:
        for r in valid_rejected:
            print(f"VALID_REJECTED {r['locs'][0]} stage0={r['stage0']} psc={r['psc']}")
    if args.verbose or invalid_accepted:
        for r in invalid_accepted:
            print(f"INVALID_ACCEPTED {r['locs'][0]} stage0={r['stage0']}")
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"report={args.json}")
    return 0 if not valid_rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
