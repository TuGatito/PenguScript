#!/usr/bin/env python3
"""Compara dos bundles C ignorando rutas absolutas de `#line`."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LINE = re.compile(r'^\s*#line\s+\d+\s+".*"\s*$')


def normalize(path: Path) -> str:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if LINE.match(line):
            out.append(line.split('"')[0].strip())
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    args = ap.parse_args()
    na, nb = normalize(args.a), normalize(args.b)
    if na == nb:
        print("bundles: iguales (normalizados)")
        return 0
    import difflib

    diff = list(
        difflib.unified_diff(
            na.splitlines(), nb.splitlines(), fromfile=str(args.a), tofile=str(args.b)
        )
    )
    print("\n".join(diff[:200]), file=sys.stderr)
    print(f"bundles: DIFERENTES ({len(diff)} líneas de diff)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
