#!/usr/bin/env python3
"""Structural checks for PenguScript code blocks in docs/LANGUAGE.md."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "LANGUAGE.md"
LEGACY = re.compile(r"\b(spell|spirit|bind\s+mut|class|this)\b")


def balanced(code: str) -> str | None:
    stack: list[str] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    in_str = False
    in_char = False
    escape = False
    in_line = False
    in_block = False
    for i, line in enumerate(code.splitlines(), 1):
        if in_block:
            if "]]" in line:
                in_block = False
            continue
        if in_line:
            in_line = False
            continue
        j = 0
        while j < len(line):
            c = line[j]
            if in_str:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    in_str = False
            elif in_char:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == "'":
                    in_char = False
            elif c == '"':
                in_str = True
            elif c == "'":
                in_char = True
            elif c == "-" and j + 1 < len(line) and line[j + 1] == "-":
                if j + 3 < len(line) and line[j + 2] == "[" and line[j + 3] == "[":
                    in_block = True
                else:
                    in_line = True
                break
            elif c in "([{":
                stack.append(c)
            elif c in ")]}":
                if not stack or stack.pop() != pairs[c]:
                    return f"delimitador desbalanceado en línea {i}"
            j += 1
    if stack:
        return "delimitadores sin cerrar"
    return None


def main() -> int:
    lines = DOC.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[int, list[str]]] = []
    cur: list[str] | None = None
    start = 0
    for i, line in enumerate(lines, 1):
        if line.startswith("```pengu"):
            cur, start = [], i
        elif line.startswith("```") and cur is not None:
            blocks.append((start, cur))
            cur = None
        elif cur is not None:
            cur.append(line)
    errors: list[str] = []
    for start, block in blocks:
        text = "\n".join(block)
        if "-- ERROR" in text:
            continue
        for j, line in enumerate(block, start + 1):
            if "\t" in line:
                errors.append(f"línea {j}: tabulador")
            if line.strip().startswith("--"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if line.strip() and indent % 4:
                errors.append(f"línea {j}: indentación {indent}")
        problem = balanced(text)
        if problem:
            errors.append(f"bloque desde línea {start}: {problem}")
        m = LEGACY.search(text)
        if m:
            errors.append(f"bloque desde línea {start}: término retirado {m.group(0)}")
    print(f"bloques pengu: {len(blocks)}")
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
