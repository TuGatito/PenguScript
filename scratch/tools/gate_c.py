#!/usr/bin/env python3
"""Gate C: checker, corpus, diagnostics and formatting evidence."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(args: list[str]) -> str:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"FAIL: {' '.join(args)}")
    return result.stdout + result.stderr


def main() -> int:
    run(["cargo", "test", "--workspace"])
    run(["cargo", "clippy", "--workspace", "--all-targets", "--", "-D", "warnings"])
    run(["cargo", "fmt", "--all", "--", "--check"])
    run(["python3", "scratch/tools/check_rewrite.py"])
    run(["python3", "scratch/tools/check_pengu_blocks.py"])
    coverage = run(["python3", "scratch/tools/check_diagnostics.py"])
    match = re.search(r"cobertura: (\d+)/(\d+)", coverage)
    covered = int(match.group(1)) if match else -1
    print(f"Gate C: {covered}/160 diagnósticos cubiertos (emitidos + justificados)")
    if covered != 160:
        print("Gate C: FAIL (cobertura de diagnósticos incompleta)")
        return 1
    print("Gate C: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
