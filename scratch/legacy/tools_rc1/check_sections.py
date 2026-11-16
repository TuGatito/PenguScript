#!/usr/bin/env python3
"""Compara el outline del plan con los encabezados de docs/LANGUAGE.md.

Uso:
    python3 scratch/tools/check_sections.py

Comprueba que las 71 secciones existan, estén numeradas 1..71 sin huecos y
que el orden y el título normalizado coincidan con `scratch/LANGUAGE_PLAN.md`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


PLAN = Path("scratch/LANGUAGE_PLAN.md")
DOC = Path("docs/LANGUAGE.md")
OUTLINE_START = "### 6.3 Outline completo"
OUTLINE_END = "### 6.4"


def normalize(title: str) -> str:
    title = title.strip().lower()
    title = title.replace("`", "")
    title = re.sub(r"[^\w\sáéíóúüñ]", " ", title, flags=re.UNICODE)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def plan_sections() -> list[tuple[int, str]]:
    lines = PLAN.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(OUTLINE_START)
    except ValueError:
        raise SystemExit(f"ERROR: no se encontró {OUTLINE_START!r} en {PLAN}")
    sections: list[tuple[int, str]] = []
    for line in lines[start + 1 :]:
        if line.startswith(OUTLINE_END):
            break
        match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if match:
            sections.append((int(match.group(1)), match.group(2)))
    return sections


def doc_sections() -> list[tuple[int, str]]:
    text = DOC.read_text(encoding="utf-8")
    sections: list[tuple[int, str]] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d+)\.\s+(.+?)\s*$", line)
        if match:
            sections.append((int(match.group(1)), match.group(2)))
    return sections


def main() -> int:
    if not PLAN.is_file() or not DOC.is_file():
        print("ERROR: faltan scratch/LANGUAGE_PLAN.md o docs/LANGUAGE.md", file=sys.stderr)
        return 2

    planned = plan_sections()
    actual = doc_sections()

    print(f"Plan: {len(planned)} secciones")
    print(f"Documento: {len(actual)} secciones")

    errors: list[str] = []
    expected_numbers = list(range(1, 72))
    planned_numbers = [n for n, _ in planned]
    actual_numbers = [n for n, _ in actual]

    if planned_numbers != expected_numbers:
        errors.append(f"el plan no numera 1..71: {planned_numbers}")
    if actual_numbers != expected_numbers:
        errors.append(f"el documento no numera 1..71: {actual_numbers}")

    planned_map = dict(planned)
    actual_map = dict(actual)
    for number in expected_numbers:
        if number not in planned_map:
            errors.append(f"falta la sección {number} en el plan")
            continue
        if number not in actual_map:
            errors.append(f"falta la sección {number} en el documento")
            continue
        if normalize(planned_map[number]) != normalize(actual_map[number]):
            errors.append(
                f"título distinto en §{number}: plan={planned_map[number]!r} "
                f"doc={actual_map[number]!r}"
            )

    if errors:
        print("\nErrores:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("OK: 71/71 secciones, orden y títulos coinciden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
