#!/usr/bin/env python3
"""Validate the hand-written docs under docs/.

Checks, per file:
  * code fences are balanced;
  * GFM tables have a consistent number of columns;
  * the TOC matches the headings (via tools/docs/toc.py --check);
  * every ```pengu block compiles with `psc check` (unless --no-compile).

Usage:
  tools/docs/validate_docs.py docs/LANGUAGE.md [docs/...]
  tools/docs/validate_docs.py --no-compile docs/LANGUAGE.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PSC = ROOT / "build" / "psc"


def read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def check_fences(path: Path, lines: list[str]) -> list[str]:
    errs = []
    open_at = 0
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            open_at = i if open_at == 0 else 0
    if open_at:
        errs.append(f"{path}:{open_at}: unclosed code fence")
    return errs


def check_tables(path: Path, lines: list[str]) -> list[str]:
    errs = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if "|" in line and re.match(r"^\s*\|?[\s:-]+\|[\s:|-]*$", nxt):
            cols = count_cols(line)
            j = i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                if count_cols(lines[j]) != cols:
                    errs.append(
                        f"{path}:{j + 1}: table row has {count_cols(lines[j])} "
                        f"columns, header has {cols}"
                    )
                j += 1
            i = j
            continue
        i += 1
    return errs


def count_cols(line: str) -> int:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return len(re.split(r"(?<!\\)\|", s))


def blocks(lines: list[str]) -> list[tuple[str, int, str]]:
    out = []
    cur = None
    start = 0
    buf: list[str] = []
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            if cur is None:
                cur = line[3:].strip()
                start = i
                buf = []
            else:
                out.append((cur, start, "\n".join(buf)))
                cur = None
        elif cur is not None:
            buf.append(line)
    return out


def check_compile(path: Path, lines: list[str]) -> list[str]:
    errs = []
    if not PSC.exists():
        return [f"{path}: {PSC} not built; skipping compile check"]
    for lang, start, src in blocks(lines):
        if lang != "pengu":
            continue
        with tempfile.NamedTemporaryFile(
            "w", suffix=".pengu", delete=False, dir="/tmp"
        ) as fh:
            fh.write(src + "\n")
            tmp = fh.name
        try:
            proc = subprocess.run(
                [str(PSC), "check", tmp],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
        finally:
            Path(tmp).unlink(missing_ok=True)
        if proc.returncode != 0:
            first = (proc.stderr or proc.stdout).strip().splitlines()
            detail = next((l for l in first if "error[" in l), first[0] if first else "?")
            errs.append(f"{path}:{start}: pengu block does not compile: {detail}")
    return errs


def check_toc(path: Path) -> list[str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "docs" / "toc.py"), str(path), "--check"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return [(proc.stdout + proc.stderr).strip()]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--no-compile", action="store_true")
    args = ap.parse_args()

    errs: list[str] = []
    for name in args.files:
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        lines = read(path)
        errs += check_fences(path, lines)
        errs += check_tables(path, lines)
        errs += check_toc(path)
        if not args.no_compile:
            errs += check_compile(path, lines)

    if errs:
        for e in errs:
            print(e)
        return 1
    print(f"ok: {len(args.files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
