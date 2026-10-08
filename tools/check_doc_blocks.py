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


def block_diagnostics(block: Block) -> tuple[bool, list[dict]]:
    """Returns ``(ok, diagnostics)`` for one block, checked in isolation.

    The isolation that matters is that each block is its own *file* -- a block is
    not a program and must not see its neighbours -- not that it is its own
    process. This used to spawn ``python pengu_project.py check --entry`` per
    block; across ~200 blocks that cost ~0.36 s of interpreter start-up and
    compiler import each, which was the second largest item in the test suite.
    The diagnostics are returned rather than printed so that a caller can tell a
    real rejection from a swallowed interpreter error: the latter reaches
    `_diagnostic_message` without a ``code`` and comes out with an empty one, while
    every language diagnostic carries a code (calibrated over all 286 documented
    blocks in `tests/compiler/test_frontend_no_crash.py`).
    """
    from dataclasses import replace

    # This module is both imported (as `tools.check_doc_blocks`) and run as a
    # script. As a script the repository root is not on `sys.path` -- the previous
    # subprocess implementation got it from `cwd=REPO` -- so it is added here.
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    from pengu_project import PenguBuilder, ProjectConfig

    with tempfile.TemporaryDirectory() as tmp:
        entry = Path(tmp) / "blk.pengu"
        entry.write_text(block.code + "\n", encoding="utf-8")
        absolute = entry.resolve()
        config = replace(
            ProjectConfig.load(None),
            base_dir=str(absolute.parent),
            entry=absolute.name,
            name=absolute.stem,
        )
        builder = PenguBuilder(config)
        builder.verbose = False
        ok, diagnostics = builder.check_sources_diagnostics()
        return bool(ok), [dict(d) for d in diagnostics]


def _format_diagnostics(diagnostics: list[dict]) -> str:
    """The textual form of the diagnostics, shaped like the CLI's output."""
    return "".join(
        f"{d.get('file', '')}:{d.get('line', 0)}:{d.get('col', 0)} "
        f"{('[' + str(d['code']) + '] ') if d.get('code') else ''}"
        f"{d.get('message', '')}\n"
        for d in diagnostics
    )


def check_block_detail(block: Block) -> tuple[bool, str, list[dict]]:
    """``(compiles, output, diagnostics)`` for one block, from a single check.

    Callers that need both the verdict and the structured diagnostics use this
    rather than calling :func:`check_block` and :func:`block_diagnostics` in turn,
    which would check the block twice.
    """
    ok, diagnostics = block_diagnostics(block)
    return ok, _format_diagnostics(diagnostics), diagnostics


def check_block(block: Block, timeout: int = 120) -> tuple[bool, str]:
    """Returns ``(compiles, output)`` for one block, checked in isolation.

    ``timeout`` is accepted for compatibility with the previous subprocess
    implementation and is no longer enforced: there is no child process to kill.
    """
    ok, output, _diagnostics = check_block_detail(block)
    return ok, output


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


def classify_failure(document: str, block: Block, compiles: bool,
                     output: str) -> str | None:
    """The problem this block represents, or None when its marker matches reality.

    The single implementation of the two-sided rule, shared by :func:`cmd_check`
    and by the tests. It lives here rather than in the tests because there are two
    callers now: the CLI, which walks every block, and the pytest suite, which
    checks **one block per test** so ``pytest-xdist`` can spread the work. Some 200
    blocks take ~2.5 minutes serially and every block is independent, so the
    per-test split is what keeps that off the suite's critical path -- whereas
    duplicating the rule in the test would let the two drift apart.
    """
    if block.marker == "pengu" and not compiles:
        first = next((ln.strip() for ln in output.splitlines()
                      if re.search(r"\[[EW]\d{4}\]", ln)), "")
        return f"{document}:{block.line}: a `pengu` block does not compile. {first}"
    if block.marker != "pengu" and compiles:
        return (f"{document}:{block.line}: marked `{block.marker}` but it compiles — "
                f"promote it to `pengu`")
    return None


def cmd_check(timeout: int = 120) -> tuple[int, list[str]]:
    """Returns ``(exit_code, problems)``."""
    problems: list[str] = []
    for name in DOCUMENTS:
        for block in extract_blocks(DOC_DIR / name):
            compiles, output = check_block(block, timeout=timeout)
            problem = classify_failure(name, block, compiles, output)
            if problem:
                problems.append(problem)
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
