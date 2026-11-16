#!/usr/bin/env python3
"""Structural QA for PenguScript example sources.

This is not a parser. It checks the invariants that do not need semantics:
- no tabs and no trailing whitespace;
- indentation in multiples of 4 spaces;
- balanced (), [] and {} outside strings/comments;
- no retired spell/spirit/bind mut;
- no top-level bind/morph (global variables are forbidden).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "scratch" / "examples"
RETIRED = ("spell", "spirit", "bind mut")


def strip_strings_and_comments(line: str) -> str:
    out: list[str] = []
    i = 0
    quote: str | None = None
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == '"':
            quote = ch
            i += 1
            continue
        if ch == "-" and i + 1 < len(line) and line[i + 1] == "-":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def check(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text()
    if "\t" in text:
        errors.append("contains tabs")
    first = next((l.strip() for l in text.splitlines() if l.strip()), "")
    fragment = first.startswith("-- fragmento")
    stack: list[tuple[str, int]] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for lineno, raw in enumerate(text.splitlines(), 1):
        if raw.rstrip() != raw:
            errors.append(f"{lineno}: trailing whitespace")
        if not raw.strip():
            continue
        code = strip_strings_and_comments(raw)
        indent = len(code) - len(code.lstrip(" "))
        if indent % 4:
            errors.append(f"{lineno}: indentation {indent} is not a multiple of 4")
        stripped = code.strip()
        if not fragment and indent == 0 and (stripped.startswith("bind ") or stripped.startswith("morph ")):
            errors.append(f"{lineno}: top-level bind/morph (global variable)")
        for token in RETIRED:
            if token in stripped.split():
                errors.append(f"{lineno}: retired token {token!r}")
        for col, ch in enumerate(stripped, 1):
            if ch in "([{":
                stack.append((ch, lineno))
            elif ch in ")]}":
                if not stack or stack[-1][0] != pairs[ch]:
                    errors.append(f"{lineno}:{col}: unmatched {ch}")
                else:
                    stack.pop()
    for ch, lineno in stack:
        errors.append(f"{lineno}: unclosed {ch}")
    return errors


def main() -> int:
    files = sorted(EXAMPLES.glob("*.pengu"))
    if not files:
        print("no .pengu examples found", file=sys.stderr)
        return 1
    failures = 0
    for path in files:
        errors = check(path)
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT)}")
            for err in errors:
                print(f"  {err}")
    print(f"{len(files) - failures}/{len(files)} PenguScript examples pass structural checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
