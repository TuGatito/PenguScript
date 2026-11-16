#!/usr/bin/env python3
"""Structural checks for the 0.5.0 rewrite of docs/LANGUAGE.md."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "LANGUAGE.md"


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []

    ids = re.findall(r'<a id="([^"]+)"></a>', text)
    sections = [int(n) for n in re.findall(r'<a id="sec-(\d+)"></a>', text)]
    if sections != list(range(1, 29)):
        errors.append(f"secciones: {sections}")
    if len(ids) != len(set(ids)):
        errors.append("anchors duplicados")
    links = re.findall(r"\]\(#([^)]+)\)", text)
    missing = sorted(set(links) - set(ids))
    if missing:
        errors.append(f"links roto(s): {missing}")

    start = text.index("## 20. Diagnósticos")
    catalog = text[start:]
    codes = re.findall(r"\|\s*`(PGS-[EW]\d{4})`\s*\|", catalog)
    if len(codes) > 160:
        errors.append(f"catálogo: {len(codes)} > 160")
    if len(codes) != len(set(codes)):
        errors.append("catálogo con códigos duplicados")

    gstart = text.index("### 21.1")
    gend = text.index("### 21.2")
    grows = [
        line
        for line in text[gstart:gend].splitlines()
        if line.startswith("|") and "---" not in line and "Aspecto" not in line
    ]
    if len(grows) > 50:
        errors.append(f"garantías: {len(grows)} > 50")

    banned = [
        r"'static", r"for<'a>", r"\bwhere\b", r"\bGATs?\b", r"\bHRTB\b",
        r"\bRPITIT\b", r"\bPin\b", r"\bUnpin\b", r"\bFuture\b", r"\bdyn\b",
        r"impl Trait", r"macro_rules", r"incantation", r"rust block",
        r"transmute", r"MaybeUninit", r"ManuallyDrop", r"UnsafeCell",
        r"PhantomData", r"\bZST\b", r"\bDST\b", r"\brepr\b", r"\bcfg\b",
        r"\binline\b", r"must_use", r"\bSend\b", r"\bSync\b", r"\basync\b",
        r"\bawait\b", r"\bdream\b", r"\bawaken\b", r"\bchimera\b",
    ]
    current = 0
    for lineno, line in enumerate(lines, 1):
        m = re.match(r'<a id="sec-(\d+)"', line)
        if m:
            current = int(m.group(1))
        if current >= 22:
            continue
        if "PGS-E1010" in line or "palabras históricas" in line:
            continue
        for term in banned:
            if re.search(term, line):
                errors.append(f"término prohibido en §{current} línea {lineno}: {term}")
                break

    fence_lines = [line for line in lines if line.startswith("```")]
    if len(fence_lines) % 2:
        errors.append("bloques de código sin cerrar")
    if "\t" in text:
        errors.append("tabuladores")

    print(f"secciones: {len(sections)}")
    print(f"anchors: {len(ids)}")
    print(f"links: {len(links)}")
    print(f"diagnósticos: {len(codes)}")
    print(f"garantías: {len(grows)}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
