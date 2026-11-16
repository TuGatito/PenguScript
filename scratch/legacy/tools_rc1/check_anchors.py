#!/usr/bin/env python3
"""Valida anclas explícitas y enlaces internos de docs/LANGUAGE.md.

Uso:
    python3 scratch/tools/check_anchors.py [archivo.md]

Comprueba:
- anclas `<a id="..."></a>` duplicadas;
- enlaces `[texto](#ancla)` que no apunten a un ancla existente;
- enlaces internos vacíos (`](#)`).

Los encabezados sin ancla explícita también cuentan, porque GitHub genera
slugs automáticos para ellos (por ejemplo `#indice`).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
EXPLICIT_ANCHOR_RE = re.compile(r'<a\s+id="([^"]+)"\s*>\s*</a>')
LINK_RE = re.compile(r"\[[^\]]*\]\(#([^)]*)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def strip_fenced_blocks(text: str) -> str:
    """Sustituye el contenido de bloques cercados por líneas vacías."""
    lines = text.splitlines()
    result: list[str] = []
    fence: str | None = None
    for line in lines:
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)[0] * 3
                result.append("")
            else:
                result.append(line)
        else:
            if line.strip().startswith(fence):
                fence = None
            result.append("")
    return "\n".join(result)


def github_slug(text: str) -> str:
    """Aproximación al slug de GitHub para encabezados sin ancla explícita."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    return text


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/LANGUAGE.md")
    if not path.is_file():
        print(f"ERROR: no existe {path}", file=sys.stderr)
        return 2

    raw = path.read_text(encoding="utf-8")
    text = strip_fenced_blocks(raw)
    # Los enlaces dentro de código en línea no cuentan.
    text = re.sub(r"`[^`\n]*`", "", text)

    explicit: list[str] = EXPLICIT_ANCHOR_RE.findall(text)
    duplicates = sorted({a for a in explicit if explicit.count(a) > 1})

    auto: set[str] = set()
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            auto.add(github_slug(match.group(2)))

    anchors = set(explicit) | auto
    links = LINK_RE.findall(text)
    broken: list[str] = []
    empty: list[str] = []
    for target in links:
        target = unquote(target.split()[0]) if target.split() else ""
        if not target:
            empty.append(target)
        elif target not in anchors:
            broken.append(target)

    print(f"Archivo: {path}")
    print(f"Anclas explícitas: {len(explicit)} ({len(set(explicit))} únicas)")
    print(f"Anclas de encabezado: {len(auto)}")
    print(f"Enlaces internos: {len(links)}")
    print(f"Anclas duplicadas: {len(duplicates)}")
    print(f"Enlaces rotos: {len(broken)}")
    print(f"Enlaces vacíos: {len(empty)}")

    if duplicates:
        print("\nAnclas duplicadas:")
        for anchor in duplicates:
            print(f"  - {anchor}")
    if broken:
        print("\nEnlaces rotos:")
        for target in sorted(set(broken)):
            print(f"  - #{target}")
    if empty:
        print("\nEnlaces vacíos: #")

    return 1 if duplicates or broken or empty else 0


if __name__ == "__main__":
    raise SystemExit(main())
