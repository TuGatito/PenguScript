#!/usr/bin/env python3
"""Detecta sintaxis retirada o prohibida fuera de bloques Rust.

Uso:
    python3 scratch/tools/check_terms.py [archivos.md ...]

Por defecto revisa `docs/LANGUAGE.md`. Los bloques cercados con lenguaje
`rust` se omiten porque pueden contener identificadores de Rust legítimos.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


FORBIDDEN = [
    (re.compile(r"\bspell\b"), "`spell` fue retirado; usa `name = (...) -> Tipo`"),
    (re.compile(r"\bspirit\b"), "`spirit` fue retirado; usa `@`, `@mut` o `@own`"),
    (re.compile(r"\bbind\s+mut\b"), "`bind mut` fue retirado; usa `morph`"),
    (re.compile(r"(?<!@)@!"), "`@!` fue retirado; los atributos internos usan `@@!`"),
]

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*([A-Za-z0-9_+-]*)")


def check(path: Path) -> list[str]:
    errors: list[str] = []
    in_fence = False
    in_rust = False
    fence: str | None = None

    def inspect(number: int, line: str) -> None:
        # Las menciones explícitas a la migración son intencionales.
        if re.search(r"retirad|retira|migraci[oó]n|PGS-E1010|changelog|\bADR\b", line, re.IGNORECASE):
            return
        for pattern, message in FORBIDDEN:
            if pattern.search(line):
                errors.append(f"{path}:{number}: {message}: {line.strip()}")

    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = FENCE_RE.match(line)
        if not in_fence:
            if match:
                in_fence = True
                in_rust = match.group(2).lower() == "rust"
                fence = match.group(1)[0] * 3
            else:
                inspect(number, line)
            continue

        if line.strip().startswith(fence or ""):
            in_fence = False
            in_rust = False
            fence = None
            continue

        if not in_rust:
            inspect(number, line)

    return errors


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]] or [Path("docs/LANGUAGE.md")]
    missing = [p for p in paths if not p.is_file()]
    if missing:
        for path in missing:
            print(f"ERROR: no existe {path}", file=sys.stderr)
        return 2

    errors: list[str] = []
    for path in paths:
        errors.extend(check(path))

    if errors:
        print("Términos prohibidos encontrados:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK: sin términos prohibidos fuera de bloques Rust ({len(paths)} archivo(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
