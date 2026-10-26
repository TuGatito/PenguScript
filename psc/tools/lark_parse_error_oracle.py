#!/usr/bin/env python3
"""Oráculo de errores sintácticos: stage0 vs PSC.

Compara aceptación/rechazo y la línea/columna del primer error. No compara el
texto del mensaje (PSC tiene mensajes/help propios), solo código `E0000` y
posición.

Uso:
    python psc/tools/lark_parse_error_oracle.py --psc psc/build/psc
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_errors import ParseError  # noqa: E402
from pengu_parser.pengu_parser import PenguParser  # noqa: E402

CASES = {
    "multi_statement": "weave f into int:\n    var x is 1 var y is 2\n    return 0\n",
    "legacy_and": "weave f with a as int and b as int into int:\n    return a\n",
    "at_precedence": "weave f with xs as list of int, n as int into int:\n    set xs at n - 1 is 0\n",
    "missing_colon": "weave f into int\n    return 0\n",
    "unexpected_else": "weave f into int:\n    else:\n        return 0\n",
    "missing_expr": "weave f into int:\n    return\n    return 1 +\n",
    "empty_block": "weave f into int:\n    if true:\n    return 0\n",
    "unexpected_eof": "weave f into int:\n    return (1 +\n",
    "keyword_as_name": "weave f into int:\n    var if as int is 5\n    return if\n",
    "deep_parens": "weave f into int:\n    return " + "(" * 520 + "1" + ")" * 520 + "\n",
    "bad_with": "weave f into int:\n    var p as Point is with\n",
    "bad_judge": "weave f into int:\n    judge x:\n        return 0\n",
    "bad_when": "weave f into int:\n    when x\n        return 0\n",
    "bad_set": "weave f into int:\n    set is 1\n",
    "bad_type": "weave f into int:\n    var x as is 1\n",
}


def stage0_result(text: str):
    try:
        PenguParser().parse(text)
        return None
    except ParseError as exc:
        return ("E0000", exc.line, exc.column)
    except Exception as exc:  # noqa: BLE001
        return ("OTHER", None, None)


def psc_result(binary: Path, text: str):
    proc = subprocess.run(
        [str(binary), "parse", "--quiet", "--check", "--stop-after-first",
         "--diagnostics=json", "--stdin"],
        input=text,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=60,
    )
    if proc.returncode == 0:
        return None
    try:
        payload = json.loads(proc.stderr)
    except Exception:
        return ("NOJSON", None, None)
    if not payload:
        return ("EMPTY", None, None)
    first = payload[0]
    start = first.get("range", {}).get("start", {})
    return (first.get("code"), start.get("line", -2) + 1, start.get("character", -2) + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--psc", required=True)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--allowlist", default=str(Path(__file__).with_name("parse_error_allowlist.txt")))
    args = ap.parse_args()
    binary = Path(args.psc).resolve()
    allowed = set()
    allow_path = Path(args.allowlist)
    if allow_path.exists():
        for line in allow_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                allowed.add(line)
    allowed_hits = 0
    accepted = 0
    pos_ok = 0
    failures = 0
    for name, text in CASES.items():
        s0 = stage0_result(text)
        ps = psc_result(binary, text)
        if (s0 is None) != (ps is None):
            print(f"ACCEPT DIFF {name}: stage0={s0} psc={ps}")
            failures += 1
            continue
        if s0 is None:
            accepted += 1
            continue
        if s0[0] == ps[0] and s0[1] == ps[1] and s0[2] == ps[2]:
            pos_ok += 1
        elif name in allowed:
            allowed_hits += 1
        else:
            failures += 1
            print(f"POS DIFF {name}: stage0={s0} psc={ps}")
    print(f"cases={len(CASES)} accept_ok={accepted + pos_ok + allowed_hits} pos_ok={pos_ok} allowed={allowed_hits} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
