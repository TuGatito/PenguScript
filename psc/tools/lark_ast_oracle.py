#!/usr/bin/env python3
"""Oráculo de AST de F2: compara stage0 (Lark) con PSC.

El dump canónico de PSC (`psc parse --no-header`) y el de este script usan el
mismo formato:

    start
      file
        top_stmt
          import_stmt
            dotted_path
              "std"
              "spark"
            _

- Nodo: `node.data`.
- Token: `"texto"` con escapes C y CRLF normalizado.
- `None` de Lark: `_`.
- Loop etiquetado: `for_in_stmt @label "outer"`.
- Sin posiciones.

Uso:
    python psc/tools/lark_ast_oracle.py --psc /tmp/psc_parse_tool/build/parse_tool \
        --root std tests psc/src
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lark import Token, Tree  # noqa: E402

from pengu_parser.pengu_parser import PenguParser  # noqa: E402


def escape_bytes(data: bytes) -> str:
    out = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == 13 and i + 1 < n and data[i + 1] == 10:
            i += 1
            b = 10
        if b == 34:
            out.append('\\"')
        elif b == 92:
            out.append("\\\\")
        elif b == 10:
            out.append("\\n")
        elif b == 9:
            out.append("\\t")
        elif b == 0:
            out.append("\\0")
        elif 32 <= b <= 126:
            out.append(chr(b))
        else:
            out.append(f"\\x{b:02x}")
        i += 1
    return "".join(out)


def quote(value) -> str:
    if isinstance(value, Token):
        value = str(value)
    if value is None:
        return "_"
    return '"' + escape_bytes(str(value).encode("utf-8")) + '"'


def dump_node(node, depth: int, lines: list[str]) -> None:
    pad = "  " * depth
    if isinstance(node, Tree):
        label = getattr(node, "loop_label", None)
        if label:
            lines.append(f'{pad}{node.data} @label "{escape_bytes(str(label).encode("utf-8"))}"')
        else:
            lines.append(f"{pad}{node.data}")
        for child in node.children:
            dump_node(child, depth + 1, lines)
    elif isinstance(node, Token):
        lines.append(f"{pad}{quote(node)}")
    elif node is None:
        lines.append(f"{pad}_")
    else:
        lines.append(f"{pad}{quote(node)}")


def stage0_dump(text: str) -> str:
    parser = PenguParser()
    tree = parser.parse(text)
    lines: list[str] = []
    dump_node(tree, 0, lines)
    return "\n".join(lines) + "\n"


def psc_dump(binary: Path, path: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [str(binary), "parse", "--quiet", "--no-header", str(path)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )
    return proc.returncode, proc.stdout, proc.stderr


def collect(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        base = ROOT / root
        if base.is_file():
            files.append(base)
        else:
            files.extend(sorted(base.rglob("*.pengu")))
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--psc", required=True)
    ap.add_argument("--root", nargs="+", default=["std", "tests", "psc/src"])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--allowlist", default=str(Path(__file__).with_name("ast_allowlist.txt")))
    args = ap.parse_args()
    binary = Path(args.psc).resolve()
    allowed = set()
    allow_path = Path(args.allowlist)
    if allow_path.exists():
        for line in allow_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                allowed.add(line)
    files = collect(args.root)
    ok = 0
    failed = 0
    allowed_hits = 0
    for path in files:
        rel = path.relative_to(ROOT)
        try:
            expected = stage0_dump(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"STAGE0 FAIL {rel}: {exc}")
            failed += 1
            continue
        rc, got, err = psc_dump(binary, path)
        if rc != 0:
            print(f"PSC FAIL {rel} rc={rc}: {err.splitlines()[:3]}")
            failed += 1
            continue
        if got != expected:
            if str(rel) in allowed:
                allowed_hits += 1
                print(f"ALLOW {rel}")
                continue
            failed += 1
            print(f"DIFF {rel}")
            if args.verbose:
                import difflib
                diff = list(difflib.unified_diff(expected.splitlines(), got.splitlines(), fromfile="stage0", tofile="psc", lineterm=""))
                print("\n".join(diff[:80]))
        else:
            ok += 1
    print(f"files={len(files)} exact={ok} allowed={allowed_hits} diverged={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
