#!/usr/bin/env python3
"""Verifies the ``pengu`` code blocks in the documentation against the compiler.

The problem this solves
-----------------------
AUDIT_1.0.md §12.3 measured that most examples in `LANGUAGE.md` did not survive
`pengu check`. Measured again for roadmap item 7.4: of **101** ```` ```pengu ````
blocks, **35 compiled and 66 did not**. Some of the failures were real bugs in the
documentation — an invalid string interpolation, a generic call the checker could
not infer, and `filum.free_mutex` being called with a value where it takes a
`ref to` — and the rest were snippets that were never programs (``1 to 10``,
``42 -7 0xFF``, directives, deliberately-wrong examples).

The marker protocol
-------------------
Every fenced block that is not a complete program must say so, using one of:

````
```pengu           an example that MUST compile
```pengu-fragment  a snippet: not a program (it must NOT compile on its own)
```pengu-invalid   a deliberately wrong example used to show a diagnostic
````

The check is deliberately two-sided:

* every ```` ```pengu ```` block compiles;
* every ```` ```pengu-fragment ```` and ```` ```pengu-invalid ```` block does
  **not** compile.

The second rule is what stops the markers from being abused as an escape hatch: a
fragment that starts compiling is mislabelled and has to be promoted back to
``pengu``.

Usage
-----
    python tools/check_doc_blocks.py --check        # CI gate
    python tools/check_doc_blocks.py --report       # classification, no failure
    python tools/check_doc_blocks.py --relabel      # rewrite fences by measurement
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Documents whose `pengu` blocks are gated. The style guides are excluded on
#: purpose: their blocks are ❌/✅ anti-pattern pairs, so half of them must not
#: compile by construction.
DOCUMENTS = ("LANGUAGE.md", "LANGUAGE_Spanish.md")

#: Directory the documents are read from. Kept separate from :data:`REPO`, which
#: locates the compiler used to check them, so the tests can point the checker at
#: a temporary document without breaking the compiler path.
DOC_DIR = REPO

MARKERS = ("pengu", "pengu-fragment", "pengu-invalid")

#: A block is treated as a deliberately-wrong example when it announces itself as
#: one. Used only by `--relabel`; `--check` trusts the marker.
_INVALID_HINTS = ("# Invalid", "# ❌", "# Anti-Pengunic", "# anti-pengunic", "# INVALID")


class Block:
    def __init__(self, path: Path, line: int, marker: str, code: str) -> None:
        self.path = path
        self.line = line          # 1-based line of the opening fence
        self.marker = marker
        self.code = code

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Block {self.path.name}:{self.line} {self.marker}>"


def extract_blocks(path: Path) -> list[Block]:
    """All fenced blocks with a `pengu*` marker, in document order."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        m = re.match(r"^```(\S+)\s*$", lines[i])
        if m and m.group(1) in MARKERS:
            marker = m.group(1)
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            blocks.append(Block(path, i + 1, marker, "\n".join(lines[i + 1:j])))
            i = j + 1
            continue
        i += 1
    return blocks


def check_block(block: Block, timeout: int = 120) -> tuple[bool, str]:
    """Returns ``(compiles, output)`` for one block, compiled in isolation."""
    with tempfile.TemporaryDirectory() as tmp:
        entry = Path(tmp) / "blk.pengu"
        entry.write_text(block.code + "\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(REPO / "pengu_project.py"), "check", "--entry", str(entry)],
            capture_output=True, text=True, timeout=timeout, cwd=str(REPO),
        )
        return proc.returncode == 0, proc.stdout + proc.stderr


def _looks_invalid(block: Block, text_lines: list[str]) -> bool:
    """True when the block announces itself as a counter-example."""
    if any(hint in block.code for hint in _INVALID_HINTS):
        return True
    # ...or when the line right before the fence says so (e.g. "**Anti-Pengunic:**").
    idx = block.line - 2
    for _ in range(3):
        if idx < 0:
            break
        stripped = text_lines[idx].strip()
        if stripped:
            return "nvalid" in stripped or "❌" in stripped or "Anti-Pengunic" in stripped
        idx -= 1
    return False


def relabel(verbose: bool = True) -> int:
    """Rewrites the fence markers of every document by measurement."""
    changed = 0
    for name in DOCUMENTS:
        path = REPO / name
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        out: list[str] = []
        i = 0
        while i < len(lines):
            m = re.match(r"^```(\S+)\s*$", lines[i])
            if m and m.group(1) in MARKERS:
                marker = m.group(1)
                j = i + 1
                while j < len(lines) and not lines[j].startswith("```"):
                    j += 1
                block = Block(path, i + 1, marker, "\n".join(lines[i + 1:j]))
                compiles, _ = check_block(block)
                if marker == "pengu" and not compiles:
                    new = "pengu-invalid" if _looks_invalid(block, lines) else "pengu-fragment"
                    if verbose:
                        print(f"  {name}:{block.line} pengu -> {new}")
                    changed += 1
                    out.append(f"```{new}")
                elif marker != "pengu" and compiles:
                    if verbose:
                        print(f"  {name}:{block.line} {marker} -> pengu (it compiles!)")
                    changed += 1
                    out.append("```pengu")
                else:
                    out.append(lines[i])
                out.extend(lines[i + 1:j])
                out.append(lines[j] if j < len(lines) else "```")
                i = j + 1
                continue
            out.append(lines[i])
            i += 1
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def cmd_check(timeout: int = 120) -> tuple[int, list[str]]:
    """Returns ``(exit_code, problems)``."""
    problems: list[str] = []
    for name in DOCUMENTS:
        for block in extract_blocks(DOC_DIR / name):
            compiles, output = check_block(block, timeout=timeout)
            if block.marker == "pengu" and not compiles:
                first = next((ln.strip() for ln in output.splitlines()
                              if re.search(r"\[[EW]\d{4}\]", ln)), "")
                problems.append(
                    f"{name}:{block.line}: a `pengu` block does not compile. {first}"
                )
            elif block.marker != "pengu" and compiles:
                problems.append(
                    f"{name}:{block.line}: marked `{block.marker}` but it compiles — "
                    f"promote it to `pengu`"
                )
    return (1 if problems else 0), problems


def cmd_report(timeout: int = 120) -> int:
    total = passes = 0
    for name in DOCUMENTS:
        for block in extract_blocks(DOC_DIR / name):
            compiles, _ = check_block(block, timeout=timeout)
            total += 1
            passes += 1 if compiles else 0
            print(f"{name}:{block.line:5d} {block.marker:15s} compiles={compiles}")
    print(f"\n{total} blocks, {passes} of them compile")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="fail when a block's marker does not match reality")
    group.add_argument("--report", action="store_true",
                       help="print the classification of every block")
    group.add_argument("--relabel", action="store_true",
                       help="rewrite markers by measurement")
    group.add_argument("--timeout", type=int, default=120, help="per-block timeout in seconds")
    args = parser.parse_args(argv)

    if args.relabel:
        changed = relabel()
        print(f"relabelled {changed} block(s)")
        return 0
    if args.report:
        return cmd_report(args.timeout)
    code, problems = cmd_check(args.timeout)
    if problems:
        print("documentation blocks: OUT OF SYNC", file=sys.stderr)
        for line in problems:
            print("  " + line, file=sys.stderr)
        print("\nrun: python tools/check_doc_blocks.py --relabel", file=sys.stderr)
        return code
    n = sum(len(extract_blocks(DOC_DIR / name)) for name in DOCUMENTS)
    print(f"documentation blocks: {n} blocks verified, every marker matches reality")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
