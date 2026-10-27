#!/usr/bin/env python3
"""Bootstrap reproducible de PSC: stage1 -> stage2 -> stage3 -> stage4.

El criterio de punto fijo es que el C normalizado emitido por stage3 y stage4
sea idéntico. TCC se comprueba por defecto en Linux porque el driver `run` lo
usa como compilador rápido.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "psc"
BOOT = PSC / "build" / "bootstrap"
TCC_CANDIDATES = [
    ROOT / "build" / "tcc-dist" / "tcc-dist" / "bin" / "tcc",
    ROOT / "build" / "tcc-dev" / "tinycc-src" / "tcc",
]


def fail(msg: str) -> None:
    print(f"bootstrap: {msg}", file=sys.stderr)
    raise SystemExit(1)


def env() -> dict[str, str]:
    e = os.environ.copy()
    e.setdefault("PENGU_STD_DIR", str(ROOT / "std"))
    e.setdefault("PENGU_LIB_DIR", str(ROOT / "build" / "lib"))
    e.setdefault("PENGU_INCLUDE_DIR", str(ROOT / "build" / "include"))
    return e


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, env=env())
    if p.returncode != 0:
        fail(f"command failed ({p.returncode}): {' '.join(cmd)}")


def build_stage(compiler: Path, out: Path, cc: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    run([str(compiler), "build", ".", f"--out={out}", f"--cc={cc}"], PSC)
    if not out.is_file():
        fail(f"no se produjo {out}")
    return out


def emit_c(compiler: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    run([str(compiler), "emit-c", "psc/src/main.pengu", f"--out={out}"], ROOT)
    if not out.is_file():
        fail(f"no se produjo {out}")
    return out


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", type=Path, default=PSC / "build" / "psc")
    ap.add_argument("--cc", default="gcc")
    ap.add_argument("--tcc", type=Path, default=None)
    ap.add_argument("--no-tcc", action="store_true")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    stage1 = args.stage1.resolve()
    if not stage1.is_file():
        fail(f"falta stage1: {stage1} (compílalo con stage0 primero)")

    BOOT.mkdir(parents=True, exist_ok=True)
    work = BOOT / "check"
    if work.exists() and not args.keep:
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    stage2 = build_stage(stage1, work / "stage2" / "psc", args.cc)
    stage3 = build_stage(stage2, work / "stage3" / "psc", args.cc)
    stage4 = build_stage(stage3, work / "stage4" / "psc", args.cc)
    c3 = emit_c(stage3, work / "stage3.c")
    c4 = emit_c(stage4, work / "stage4.c")
    h3, h4 = digest(c3), digest(c4)
    print(f"stage3 C: {h3}")
    print(f"stage4 C: {h4}")
    if c3.read_bytes() != c4.read_bytes():
        fail("punto fijo NO alcanzado: stage3.c != stage4.c")
    print("punto fijo: OK")

    tcc = args.tcc
    if tcc is None:
        for cand in TCC_CANDIDATES:
            if cand.is_file():
                tcc = cand
                break
    if not args.no_tcc:
        if tcc is None or not tcc.is_file():
            fail("TCC es obligatorio en Linux (build/tcc-dist o --tcc)")
        run(
            [
                sys.executable,
                str(PSC / "tools" / "selfhost_preflight.py"),
                "--cc",
                str(tcc),
                "--smoke",
            ],
            ROOT,
        )
    print("bootstrap: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
