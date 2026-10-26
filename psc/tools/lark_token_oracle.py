#!/usr/bin/env python3
"""Oracle de tokens de F1: compara PSC contra el lexer contextual de stage0.

Dev-only. No forma parte del binario `psc`.

El truco importante: `PenguParser.get_tokens()` no sirve (no quita comentarios
y su chequeo de statements da falsos positivos). Este script monkeypatchea
`lark.lexer.LexerThread.lex` para capturar exactamente los tokens que consume un
`parse` real, con el estado contextual de Lark.

Uso:
    python psc/tools/lark_token_oracle.py --psc psc/build/psc
    python psc/tools/lark_token_oracle.py --psc psc/build/psc --verbose
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pengu_parser.pengu_parser import PenguParser  # noqa: E402
import lark.lexer as lark_lexer  # noqa: E402

WORD_TYPES = {
    "NAME", "_AND_SEP", "_BOOL_AND", "_BOOL_OR",
}
LITERAL_FAMILIES = {
    "INT": "INT",
    "FLOAT": "FLOAT",
    "STRING": "STRING",
    "TRIPLE_STRING": "STRING",
    "RAW_STRING": "STRING",
    "RAW_TRIPLE_STRING": "STRING",
    "CHAR_LIT": "CHAR",
}
STRUCTURAL = {"_NEWLINE", "_INDENT", "_DEDENT"}
SKIP_POSITION = {"INDENT", "DEDENT", "ANTIQUUS", "NEWLINE", "EOF"}


def logical_files(roots: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        for dirpath, _dirnames, filenames in os.walk(base):
            for name in sorted(filenames):
                if name.endswith(".pengu"):
                    out.append(Path(dirpath) / name)
    return sorted(out)


def preprocess(parser: PenguParser, source: str):
    code, bodies = parser._extract_antiquus_bodies(source)
    code = parser._strip_comments(code).rstrip() + "\n"
    merged = parser._merge_chain_continuations(code)
    expanded = parser._expand_short_struct_inits(merged)
    return code, merged, expanded, bodies


def capture_stage0(parser: PenguParser, code: str) -> Tuple[List[Tuple], bool]:
    captured: List[Tuple] = []
    original = lark_lexer.LexerThread.lex

    def tee(self, parser_state):
        for token in original(self, parser_state):
            captured.append(token)
            yield token

    lark_lexer.LexerThread.lex = tee
    try:
        parser.parser.parse(code, start="start")
        ok = True
    except Exception:
        ok = False
    finally:
        lark_lexer.LexerThread.lex = original

    records: List[Tuple] = []
    for token in captured:
        rec = stage0_record(token)
        # Lark columns count Unicode code points; PSC uses byte columns.
        rec = (rec[0], rec[1], rec[2], byte_col(code, rec[2], rec[3]))
        records.append(rec)
    # Lark's parser consumes EOF implicitly; add it explicitly.
    eof_line = code.count("\n") + 1
    eof_col = 1
    if code and not code.endswith("\n"):
        last = code.rsplit("\n", 1)[-1]
        eof_col = len(last) + 1
    records.append(("EOF", "", eof_line, eof_col))
    return records, ok


def indent_width(value: str) -> int:
    value = value.rsplit("\n", 1)[-1]
    return value.count(" ") + value.count("\t") * 2


def stage0_record(token) -> Tuple:
    typ = token.type
    lexeme = str(token)
    line = getattr(token, "line", 0) or 0
    col = getattr(token, "column", 0) or 0
    if typ == "_NEWLINE":
        return ("NEWLINE", str(indent_width(lexeme)), line, col)
    if typ == "_INDENT":
        return ("INDENT", str(indent_width(lexeme)), line, col)
    if typ == "_DEDENT":
        return ("DEDENT", "", line, col)
    if typ == "ANTIQUUS_BODY_PLACEHOLDER":
        return ("ANTIQUUS", "", line, col)
    if typ == "_TYPE_OF":
        return ("WORD", "type of", line, col)
    if typ == "_SIZE_OF":
        return ("WORD", "size of", line, col)
    if typ in LITERAL_FAMILIES:
        return (LITERAL_FAMILIES[typ], lexeme, line, col)
    if typ in WORD_TYPES:
        return ("WORD", lexeme, line, col)
    if typ.startswith("__ANON_"):
        # Primitive type keywords (`int`, `bool`, ...) are __ANON_n; operators
        # (`==`, `!=`, ...) are too. The lexeme decides.
        if lexeme and (lexeme[0].isalpha() or lexeme[0] == "_"):
            return ("WORD", lexeme, line, col)
        return ("OP", lexeme, line, col)
    if typ.isupper() and lexeme and (lexeme[0].isalpha() or lexeme[0] == "_"):
        # Keyword literal type (IMPORT, RUNE, ...). Punctuation types are also
        # uppercase (DOT, COLON, ...), so the lexeme decides.
        return ("WORD", lexeme, line, col)
    if typ == "PAT_OR":
        return ("OP", lexeme, line, col)
    if typ == "COMPOUND_OP":
        return ("OP", lexeme, line, col)
    return ("OP", lexeme, line, col)


def unescape_field(text: str) -> str:
    r"""Decodes the TSV escape form back to a UTF-8 Python string.

    The PSC dump escapes every byte >= 0x7F as ``\xNN`` so a lexeme is always
    one physical line. Rebuild the byte sequence and decode it as UTF-8.
    """
    data = bytearray()
    i = 0
    while i < len(text):
        ch = text[i]
        if ch != "\\":
            data.extend(ch.encode("utf-8"))
            i += 1
            continue
        if i + 1 >= len(text):
            data.append(0x5C)
            break
        nxt = text[i + 1]
        mapping = {"n": 10, "t": 9, "r": 13, "0": 0, "\\": 0x5C}
        if nxt in mapping:
            data.append(mapping[nxt])
            i += 2
            continue
        if nxt == "x" and i + 3 < len(text):
            try:
                data.append(int(text[i + 2:i + 4], 16))
                i += 4
                continue
            except ValueError:
                pass
        data.extend(nxt.encode("utf-8"))
        i += 2
    return data.decode("utf-8", errors="replace")


def byte_col(code: str, line: int, col: int) -> int:
    """Converts Lark's 1-indexed codepoint column to a 1-indexed byte column."""
    lines = code.splitlines()
    if line < 1 or line > len(lines):
        return col
    prefix = lines[line - 1][: max(col - 1, 0)]
    return len(prefix.encode("utf-8")) + 1


def parse_dump(text: str) -> List[Tuple]:
    records: List[Tuple] = []
    in_comments = False
    for line in text.splitlines():
        if line.startswith("# comments"):
            in_comments = True
            continue
        if line.startswith("#") or not line:
            continue
        if in_comments:
            continue
        parts = line.split("\t")
        if len(parts) < 10:
            continue
        _index, kind, lexeme, start, end, line_no, col, end_line, end_col, aux = parts[:10]
        lexeme = unescape_field(lexeme)
        if kind.startswith("Keyword("):
            records.append(("WORD", lexeme, int(line_no), int(col)))
            continue
        if kind == "Newline":
            records.append(("NEWLINE", str(int(aux)), int(line_no), int(col)))
        elif kind == "Indent":
            records.append(("INDENT", str(int(aux)), int(line_no), int(col)))
        elif kind == "Dedent":
            records.append(("DEDENT", "", int(line_no), int(col)))
        elif kind == "Eof":
            records.append(("EOF", "", int(line_no), int(col)))
        elif kind == "AntiquusBody":
            records.append(("ANTIQUUS", "", int(line_no), int(col)))
        elif kind in ("IntLit",):
            records.append(("INT", lexeme, int(line_no), int(col)))
        elif kind in ("FloatLit",):
            records.append(("FLOAT", lexeme, int(line_no), int(col)))
        elif kind in ("StringLit",):
            if re.fullmatch(r'"  __PENGU_ANTIQUUS_BODY_[0-9]+__  "', lexeme):
                records.append(("ANTIQUUS", "", int(line_no), int(col)))
            else:
                records.append(("STRING", lexeme, int(line_no), int(col)))
        elif kind in ("CharLit",):
            records.append(("CHAR", lexeme, int(line_no), int(col)))
        elif kind == "Identifier":
            records.append(("WORD", lexeme, int(line_no), int(col)))
        else:
            records.append(("OP", lexeme, int(line_no), int(col)))
    return records


def classify(source: str, parser: PenguParser) -> Tuple[str, dict]:
    _a, merged, expanded, bodies = preprocess(parser, source)
    _code, _bodies = parser._extract_antiquus_bodies(source)
    stripped = parser._strip_comments(_code).rstrip() + "\n"
    has_chain = merged != stripped
    has_struct = expanded != merged
    if has_chain:
        return "seq", {"antiquus": bool(bodies)}
    if has_struct:
        return "struct", {"antiquus": bool(bodies)}
    if bodies:
        return "antiquus", {"antiquus": True}
    return "exact", {"antiquus": False}


def compare(stage0: List[Tuple], psc: List[Tuple], level: str) -> List[str]:
    problems: List[str] = []
    if len(stage0) != len(psc):
        problems.append(f"count: stage0={len(stage0)} psc={len(psc)}")
    limit = min(len(stage0), len(psc))
    for i in range(limit):
        a = stage0[i]
        b = psc[i]
        if a[0] != b[0] or a[1] != b[1]:
            problems.append(f"#{i}: expected {a} got {b}")
            if len(problems) >= 12:
                return problems
            continue
        if a[0] in SKIP_POSITION:
            continue
        # struct/seq are lexed from the same rewritten buffer stage0 parses.
        if level == "antiquus" and a[0] == "ANTIQUUS":
            continue
        if a[2] != b[2] or a[3] != b[3]:
            problems.append(f"#{i}: position expected ({a[2]},{a[3]}) got ({b[2]},{b[3]}) {a[0]} {a[1]!r}")
            if len(problems) >= 12:
                return problems
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--psc", default=str(ROOT / "psc" / "build" / "psc"))
    ap.add_argument("--root", nargs="*", default=["std", "tests"])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    psc_bin = Path(args.psc)
    if not psc_bin.exists():
        print(f"missing psc binary: {psc_bin}", file=sys.stderr)
        return 2
    parser = PenguParser()
    files = logical_files(args.root)
    if args.limit:
        files = files[: args.limit]
    failures = 0
    skipped = 0
    level_counts: Counter = Counter()
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped += 1
            continue
        level, meta = classify(source, parser)
        level_counts[level] += 1
        _stripped, merged, expanded, _bodies = preprocess(parser, source)
        stage0, ok = capture_stage0(parser, expanded)
        if not ok:
            print(f"SKIP stage0 parse failed: {path.relative_to(ROOT)}")
            skipped += 1
            continue
        # stage0 does not parse the original text for chain continuations and
        # short struct inits: it parses a rewritten buffer. Compare against the
        # same buffer so the inserted `is` tokens are not counted as a lexer
        # difference. The original file is still checked for crashes by the
        # `psc --check` corpus run.
        lex_path = path
        temp_path: Optional[str] = None
        if level in ("struct", "seq"):
            rewritten = expanded if level == "struct" else merged
            handle = tempfile.NamedTemporaryFile(
                "w", suffix=".pengu", delete=False, encoding="utf-8"
            )
            handle.write(rewritten)
            handle.close()
            temp_path = handle.name
            lex_path = Path(temp_path)
        try:
            proc = subprocess.run(
                [str(psc_bin), "lex", "--quiet", str(lex_path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
        finally:
            if temp_path:
                os.unlink(temp_path)
        if proc.returncode not in (0, 1):
            print(f"FAIL psc crashed ({proc.returncode}): {path.relative_to(ROOT)}")
            print(proc.stderr[:1000])
            failures += 1
            continue
        psc_tokens = parse_dump(proc.stdout)
        problems = compare(stage0, psc_tokens, level)
        if problems:
            failures += 1
            print(f"FAIL [{level}] {path.relative_to(ROOT)}")
            for problem in problems:
                print("  " + problem)
        elif args.verbose:
            print(f"ok   [{level}] {path.relative_to(ROOT)} ({len(stage0)} tokens)")

    print()
    print(f"files={len(files)} skipped={skipped} failures={failures}")
    print("levels=" + ", ".join(f"{k}:{v}" for k, v in sorted(level_counts.items())))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
