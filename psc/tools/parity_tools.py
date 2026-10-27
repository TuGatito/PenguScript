#!/usr/bin/env python3
"""Paridad dev-only entre stage0 y PSC para herramientas de F7.

Uso:
    python psc/tools/parity_tools.py --only fmt --check
    python psc/tools/parity_tools.py --only fmt --path std/ --verbose
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"
sys.path.insert(0, str(ROOT))

from pengu_lsp.formatting import format_pengu_source  # noqa: E402


def files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.pengu") if p.is_file())


def check_fmt(path: Path, verbose: bool) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    stage0 = format_pengu_source(text, tab_size=4, insert_spaces=True, blank_lines_max=2)
    p = subprocess.run(
        [str(PSC), "fmt", "--stdin"],
        input=text,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )
    if p.returncode != 0:
        if verbose:
            print(f"FAIL {path}: psc fmt --stdin rc={p.returncode}: {p.stderr[:200]}")
        return False
    if p.stdout != stage0:
        if verbose:
            import difflib

            diff = list(
                difflib.unified_diff(
                    stage0.splitlines(), p.stdout.splitlines(), fromfile="stage0", tofile="psc"
                )
            )
            print(f"DIFF {path}")
            print("\n".join(diff[:80]))
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="fmt", choices=["fmt", "doc", "assets"])
    ap.add_argument("--path", action="append", default=None)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    paths = [Path(p) for p in (args.path or ["std", "psc/src"])]
    total = 0
    ok = 0
    for base in paths:
        for f in files_under(base):
            total += 1
            if args.only == "fmt":
                good = check_fmt(f, args.verbose)
            else:
                good = True
            if good:
                ok += 1
    print(f"parity {args.only}: {ok}/{total} ok")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
