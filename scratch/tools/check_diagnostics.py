#!/usr/bin/env python3
"""Valida el catálogo de diagnósticos contra el código y los tests."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "LANGUAGE.md"
CODE_RE = re.compile(r"PGS-[EW]\d{4}")

def codes_in(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    text = text.split("#[cfg(test)]", 1)[0]
    return set(CODE_RE.findall(text))

def main() -> int:
    doc_text = DOC.read_text(encoding="utf-8")
    documented = set(CODE_RE.findall(doc_text))
    if len(documented) != 160:
        print(f"catálogo: se esperaban 160 códigos, hay {len(documented)}")
        return 1

    sources: set[str] = set()
    tests: set[str] = set()
    for path in (ROOT / "crates").rglob("*.rs"):
        found = codes_in(path)
        if "/tests/" in path.as_posix():
            tests |= found
        else:
            sources |= found

    unknown = (sources | tests) - documented
    if unknown:
        print(f"códigos emitidos fuera del catálogo: {sorted(unknown)}")
        return 1

    emitted = sources | tests
    justification = ROOT / "scratch" / "DIAGNOSTIC_JUSTIFICATIONS.md"
    justified = set(CODE_RE.findall(justification.read_text(encoding="utf-8"))) if justification.exists() else set()
    unjustified = justified - documented
    if unjustified:
        print(f"códigos justificados fuera del catálogo: {sorted(unjustified)}")
        return 1
    covered = emitted | justified
    missing = sorted(documented - covered)
    print(f"catálogo: {len(documented)} códigos")
    print(f"emitidos en código/tests: {len(emitted)}")
    print(f"justificados: {len(justified)}")
    print(f"cobertura: {len(covered)}/{len(documented)}")
    if missing:
        print(f"sin uso ni justificación ({len(missing)}): {', '.join(missing)}")
    if not emitted:
        print("no se encontró ningún código emitido")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
