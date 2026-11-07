#!/usr/bin/env python3
"""Catálogo de diagnósticos y verificación de su documentación.

Hace tres comprobaciones:

  1. `docs/SEMA_ERRORS.md` está al día respecto de las constantes `CODE_*` /
     `WARN_*` declaradas en `src/psc/sema/diagnostics.pengu` y
     `src/psc/diagnostics.pengu`.
  2. Todo código citado en `docs/LANGUAGE.md` o `docs/LANGUAGE.es.md` existe en
     el compilador (evita citar `E00xx` inventados).
  3. Todo código del compilador aparece en la tabla §18 de `docs/LANGUAGE.md`.

Uso:
  tools/docs/check_codes.py --check   # gate de CI
  tools/docs/check_codes.py --write   # regenera docs/SEMA_ERRORS.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECL_FILES = [
    ROOT / "src" / "psc" / "sema" / "diagnostics.pengu",
    ROOT / "src" / "psc" / "parse" / "diagnostics.pengu",
    ROOT / "src" / "psc" / "diagnostics.pengu",
]
CATALOG = ROOT / "docs" / "SEMA_ERRORS.md"
LANGUAGE = ROOT / "docs" / "LANGUAGE.md"
LANGUAGE_ES = ROOT / "docs" / "LANGUAGE.es.md"

CONST_RE = re.compile(r'^const\s+(CODE|WARN|PSC)_(\w+)\s+as\s+string\s+is\s+"([EW]\d{4})"', re.M)
CODE_RE = re.compile(r"\b([EW]\d{4})\b")


def declarations() -> dict[str, list[str]]:
    """code -> constant names (a code may be declared once per layer)."""
    out: dict[str, list[str]] = {}
    for path in DECL_FILES:
        text = path.read_text(encoding="utf-8")
        for kind, name, code in CONST_RE.findall(text):
            const = f"{kind}_{name}"
            names = out.setdefault(code, [])
            if const not in names:
                names.append(const)
    return dict(sorted(out.items()))


def src_files() -> list[Path]:
    return [
        p
        for p in (ROOT / "src").rglob("*.pengu")
        if "test" not in p.name
    ]


def emit_counts(codes: dict[str, list[str]]) -> dict[str, int]:
    """Referencias a la constante menos su propia declaración."""
    counts = {code: 0 for code in codes}
    for path in src_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for code, consts in codes.items():
            for const in consts:
                counts[code] += len(re.findall(rf"\b{re.escape(const)}\b", text))
    for code, consts in codes.items():
        counts[code] = max(0, counts[code] - len(consts))
    return counts


def section18() -> str:
    text = LANGUAGE.read_text(encoding="utf-8")
    m = re.search(r"^## 18\..*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0) if m else ""


def render(codes: dict[str, list[str]], counts: dict[str, int], sec: str) -> str:
    rows = []
    for code, consts in codes.items():
        emitted = counts[code]
        state = "emitido" if emitted else "**sin emisor**"
        doc = "sí" if code in sec else "**falta**"
        rows.append(
            f"| `{code}` | {', '.join('`' + c + '`' for c in consts)} | "
            f"{emitted} | {state} | {doc} |"
        )
    return (
        "# Catálogo de diagnósticos\n\n"
        "Generado por `tools/docs/check_codes.py --write`; no editar a mano.\n\n"
        "Formato de un diagnóstico:\n\n"
        "```text\n"
        "error[E0005]: type mismatch: expected 'int', got 'string'\n"
        "  --> src/main.pengu:7:13\n"
        "   |\n"
        "   = help: Ensure the value type matches the expected type.\n"
        "```\n\n"
        "Los códigos `E****` son errores; `W****`, advertencias. La columna\n"
        "*emisores* cuenta las referencias a la constante en `src/psc` (sin contar\n"
        "las declaraciones); *§18* indica si el código está en la tabla de\n"
        "`docs/LANGUAGE.md`. Un código sin emisor es una promesa: o se implementa\n"
        "en una fase del plan, o se elimina de la documentación.\n\n"
        "| Código | Constante | Emisores | Estado | §18 |\n"
        "| --- | --- | ---: | --- | --- |\n"
        + "\n".join(rows)
        + "\n\n## Cómo agregar un código\n\n"
        "1. Declará la constante `CODE_*` en `src/psc/sema/diagnostics.pengu`\n"
        "   (o `PSC_*` en `src/psc/diagnostics.pengu` para el lexer).\n"
        "2. Emitilo desde el checker o el codegen; nunca escribas el literal.\n"
        "3. Agregá la fila en la tabla §18 de `docs/LANGUAGE.md` y su espejo en\n"
        "   `docs/LANGUAGE.es.md`.\n"
        "4. Corré `tools/docs/check_codes.py --write` y commiteá el catálogo.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if not (args.check or args.write):
        ap.error("usá --check o --write")

    codes = declarations()
    counts = emit_counts(codes)
    sec = section18()
    errs: list[str] = []

    if args.write:
        CATALOG.write_text(render(codes, counts, sec), encoding="utf-8")
        print(f"escrito {CATALOG.relative_to(ROOT)} ({len(codes)} códigos)")
        return 0

    expected = render(codes, counts, sec)
    if not CATALOG.exists():
        errs.append(f"{CATALOG.relative_to(ROOT)} no existe; corré --write")
    elif CATALOG.read_text(encoding="utf-8") != expected:
        errs.append(
            f"{CATALOG.relative_to(ROOT)} está desactualizado; corré --write"
        )

    for doc in (LANGUAGE, LANGUAGE_ES):
        text = doc.read_text(encoding="utf-8")
        cited = set(CODE_RE.findall(text))
        missing = sorted(c for c in cited if c not in codes)
        if missing:
            errs.append(
                f"{doc.relative_to(ROOT)}: códigos citados que no existen: {', '.join(missing)}"
            )

    undocumented = sorted(c for c in codes if c not in sec)
    if undocumented:
        errs.append(
            "códigos del compilador ausentes de §18 (docs/LANGUAGE.md): "
            + ", ".join(undocumented)
        )

    dead = sorted(c for c in codes if counts[c] == 0)
    if dead:
        print(
            f"aviso: {len(dead)} código(s) declarados sin emisor: " + ", ".join(dead),
            file=sys.stderr,
        )

    if errs:
        for e in errs:
            print(e)
        return 1
    print(f"ok: {len(codes)} códigos, catálogo y §18 consistentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
