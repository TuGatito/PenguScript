#!/usr/bin/env python3
"""Ejecuta el corpus de conformidad F4 (66 fixtures) con las librerías nativas.

No forma parte del build: F4 es codegen. Este runner compila y ejecuta cada
fixture contra `build/lib` y exige la línea `OK <stem>`.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc" / "build" / "psc"
FIXTURES = ROOT / "tests" / "conformance" / "compliance"
LIBS = [
    "libpengu_runtime.a", "libpetitio.a", "libre.a", "libminiz.a",
    "libcyaml.a", "libyaml.a", "libsqlite3.a", "libzip.a", "libz.a",
    "libpcre2-8.a", "libexpat.a", "libmbedcrypto.a", "libuv.a",
    "libtomlc17.a",
]


def main() -> int:
    if not PSC.is_file():
        print("falta psc/build/psc", file=sys.stderr)
        return 2
    libs = [str(ROOT / "build" / "lib" / p) for p in LIBS
            if (ROOT / "build" / "lib" / p).is_file()]
    files = sorted(FIXTURES.glob("*.pengu"))
    passed, failed = 0, []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for f in files:
            c = tmp / f"{f.stem}.c"
            exe = tmp / f.stem
            r = subprocess.run([str(PSC), "emit-c", str(f), f"--out={c}"],
                               cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0:
                failed.append((f.stem, "emit", r.stderr[:200]))
                continue
            g = subprocess.run(["gcc", "-std=c11", "-w", "-I", str(ROOT),
                                "-I", str(ROOT / "build" / "include"),
                                "-I", str(ROOT / "std_c"), str(c), *libs,
                                "-lm", "-lpthread", "-lcurl", "-o", str(exe)],
                               capture_output=True, text=True)
            if g.returncode != 0:
                failed.append((f.stem, "gcc", g.stderr[:200]))
                continue
            try:
                rr = subprocess.run([str(exe)], capture_output=True, text=True,
                                    timeout=10)
            except subprocess.TimeoutExpired:
                failed.append((f.stem, "timeout", ""))
                continue
            if rr.returncode != 0 or f"OK {f.stem}" not in rr.stdout:
                failed.append((f.stem, "run", (rr.stdout + rr.stderr)[:200]))
            else:
                passed += 1
    print(f"F4 conformance: {passed}/{len(files)}")
    for name, kind, msg in failed:
        print(f"  FAIL {name} [{kind}] {msg.splitlines()[0] if msg else ''}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
