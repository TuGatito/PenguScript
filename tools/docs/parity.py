#!/usr/bin/env python3
"""Paridad estructural entre la documentación en inglés y en español.

No compara prosa (es imposible), sino la *forma*: cantidad de secciones de
cada nivel, lenguajes de los bloques de código y códigos de diagnóstico
citados. Si una traducción pierde una sección o un ejemplo, esto lo detecta.

Uso:
  tools/docs/parity.py            # chequea los pares conocidos
  tools/docs/parity.py a.md b.md  # chequea un par puntual
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAIRS = [
    ("docs/LANGUAGE.md", "docs/LANGUAGE.es.md"),
    ("docs/PENGUNIC.md", "docs/PENGUNIC.es.md"),
    ("docs/STDLIB.md", "docs/STDLIB.es.md"),
    ("docs/LIBRARIES.md", "docs/LIBRARIES.es.md"),
]
CODE_RE = re.compile(r"\b([EW]\d{4})\b")
FENCE_RE = re.compile(r"^```(\w[\w-]*)?", re.M)


def shape(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    return {
        "h1": len(re.findall(r"^# ", text, re.M)),
        "h2": len(re.findall(r"^## ", text, re.M)),
        "h3": len(re.findall(r"^### ", text, re.M)),
        "fences": sorted(m.group(1) or "" for m in FENCE_RE.finditer(text)),
        "codes": sorted(set(CODE_RE.findall(text))),
    }


def compare(a: Path, b: Path) -> list[str]:
    errs: list[str] = []
    sa, sb = shape(a), shape(b)
    for key in ("h1", "h2", "h3"):
        if sa[key] != sb[key]:
            errs.append(
                f"{a.name} tiene {sa[key]} encabezados {key.upper()}, "
                f"{b.name} tiene {sb[key]}"
            )
    if sa["fences"] != sb["fences"]:
        from collections import Counter

        ca, cb = Counter(sa["fences"]), Counter(sb["fences"])
        detalle = []
        for lang in sorted(set(ca) | set(cb)):
            if ca[lang] != cb[lang]:
                detalle.append(f"```{lang or '(sin lenguaje)'}: {ca[lang]} vs {cb[lang]}")
        errs.append(f"{a.name} y {b.name} difieren en bloques: " + "; ".join(detalle))
    if sa["codes"] != sb["codes"]:
        solo_a = sorted(set(sa["codes"]) - set(sb["codes"]))
        solo_b = sorted(set(sb["codes"]) - set(sa["codes"]))
        errs.append(
            f"{a.name}/{b.name}: códigos solo en uno: {solo_a or '-'} / {solo_b or '-'}"
        )
    return errs


def main() -> int:
    if len(sys.argv) == 3:
        pairs = [(sys.argv[1], sys.argv[2])]
    else:
        pairs = PAIRS
    errs: list[str] = []
    for a, b in pairs:
        pa, pb = ROOT / a, ROOT / b
        if not pa.exists() or not pb.exists():
            errs.append(f"falta {a if not pa.exists() else b}")
            continue
        errs += compare(pa, pb)
    if errs:
        for e in errs:
            print(e)
        return 1
    print(f"ok: {len(pairs)} par(es) con la misma estructura")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
