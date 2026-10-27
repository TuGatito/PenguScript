#!/usr/bin/env python3
"""Benchmark de `psc emit-c` para F4.

Mide tiempo de emisión y tamaño del bundle para los fixtures de aceptación.
No compila C: F4 es sólo codegen; F5 mide el pipeline completo.
"""
from __future__ import annotations

import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"
FIXTURES = ROOT / "tests" / "psc" / "fixtures" / "f4"


def bench(name: str, runs: int = 5) -> tuple[float, int]:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / f"{name}.c"
        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            res = subprocess.run(
                [str(PSC), "emit-c", str(FIXTURES / f"{name}.pengu"), f"--out={out}"],
                cwd=ROOT, capture_output=True, text=True,
            )
            if res.returncode != 0:
                raise SystemExit(res.stderr)
            times.append(time.perf_counter() - t0)
        return statistics.median(times), out.stat().st_size


def main() -> int:
    if not PSC.is_file():
        print("psc/build/psc no existe; construye PSC primero", file=sys.stderr)
        return 2
    print(f"{'fixture':20} {'median_ms':>10} {'bytes':>10}")
    for name in ("hello", "types", "control", "interp", "arena", "std_hello"):
        ms, size = bench(name)
        print(f"{name:20} {ms * 1000:10.2f} {size:10d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
