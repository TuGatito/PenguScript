#!/usr/bin/env python3
"""Generates the compiler diagnostic catalogue (``LANGUAGE.md`` §22.2/§22.3).

The problem this solves
-----------------------
``LANGUAGE.md`` §22.2 documented 59 error codes and, for five of them, named an
exception class that **does not exist** in the compiler
(``DuplicateConstantError``, ``AmbiguousStructInitError``, ``StaticArrayError``,
``ErrorLiteralContextError``, ``DanglingSliceError``); and it listed codes such
as ``E0051`` under a class while the code is really emitted as a bare
``SemanticError`` with an explicit ``code=`` keyword.  Nothing checked the
document against the compiler, so the drift was invisible for several releases.

What this tool does
-------------------
It builds the catalogue **from the sources**, by AST, and writes two artefacts:

* ``docs/error_catalog.json`` — the complete, machine-readable catalogue:
  every code, the exception class(es) that emit it, the human explanation taken
  from the class docstring, every distinct message *shape* it can carry, and the
  distinct ``help:``/``note:`` guidance pairs attached to it.
* the region of ``LANGUAGE.md`` between the two generator markers — the
  human-readable §22.2/§22.3 tables, rendered from that same JSON, plus the
  ``pengu``-free prose that introduces them.

``--check`` re-derives both and fails (exit 1) when either has drifted, so a
change to a diagnostic message, its class, or its help text is a *build*
failure until the document is regenerated.

Message *shapes*
----------------
Interpolated expressions are normalised to ``{}``.  That makes the catalogue
stable under local-variable renames and — more usefully — collapses diagnostics
that only differed because two call sites named their local differently, which
is how genuine duplicate conditions were found.

Usage
-----
    python tools/gen_error_catalog.py --check    # CI gate; non-zero on drift
    python tools/gen_error_catalog.py --write    # regenerate both artefacts
    python tools/gen_error_catalog.py --json     # print the catalogue
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Module that owns the diagnostic classes and the warning registry.
ERRORS_MODULE = REPO / "pengu_parser" / "pengu_errors.py"

#: Every module that may emit a diagnostic.
SOURCE_GLOBS = ("pengu_parser/*.py", "*.py", "pengu_lsp/*.py")

#: Generated artefacts.
CATALOG_JSON = REPO / "docs" / "error_catalog.json"
CATALOG_MARKDOWN = REPO / "LANGUAGE.md"

#: Region markers in ``LANGUAGE.md``.  ``--write`` replaces everything between
#: them, so the surrounding hand-written prose (§22.1, §22.4) is never touched.
MARK_BEGIN = "<!-- BEGIN GENERATED DIAGNOSTIC CATALOG — tools/gen_error_catalog.py -->"
MARK_END = "<!-- END GENERATED DIAGNOSTIC CATALOG -->"

#: Spanish sibling of ``LANGUAGE.md``; the generated region is duplicated there
#: with translated column headers, because two hand-maintained catalogues is
#: exactly the drift this tool exists to prevent.
CATALOG_MARKDOWN_ES = REPO / "LANGUAGE_Spanish.md"

_CODE_RE = re.compile(r"^[EW]\d{4}$")
_E_CODE_RE = re.compile(r"^E\d{4}$")
_W_CODE_RE = re.compile(r"^W\d{4}$")
_WARNING_TEXT_RE = re.compile(r"^\[(W\d{4})\]\s*(.*)$", re.S)


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _render(node: ast.AST | None, *, normalise: bool = True) -> str | None:
    """Renders a string expression as a stable template.

    With ``normalise`` every interpolated expression becomes ``{}`` so that a
    rename of a local variable does not change the catalogue.
    """
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        out: list[str] = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                out.append(str(part.value))
            elif isinstance(part, ast.FormattedValue):
                out.append("{}" if normalise else "{" + ast.unparse(part.value) + "}")
        return "".join(out)
    # Anything else (a variable holding a message, a concatenation…) cannot be
    # resolved statically.  Returning None keeps it out of the catalogue instead
    # of inventing a message.
    return None


def _is_error_class_ref(node: ast.AST) -> bool:
    """True for a bare ``FooError`` / ``mod.FooError`` reference."""
    if isinstance(node, ast.Name):
        return node.id.endswith("Error")
    if isinstance(node, ast.Attribute):
        return node.attr.endswith("Error")
    return False


def _source_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in SOURCE_GLOBS:
        files.update(REPO.glob(pattern))
    return sorted(p for p in files if p.is_file())


def _iter_string_nodes(tree: ast.AST):
    """Yields the *outermost* string nodes of ``tree``.

    ``ast.walk`` also visits the literal fragments *inside* an f-string, so
    ``f"[E0061] foo {x}"`` yields both the whole f-string and the constant
    ``"[E0061] foo "``.  Matching the fragment would register a truncated
    duplicate condition, so the interior nodes are skipped.
    """
    interior = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for part in node.values:
                interior.add(id(part))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Constant, ast.JoinedStr)) and id(node) not in interior:
            yield node


def _parse(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
        return None


# ---------------------------------------------------------------------------
# Catalogue extraction
# ---------------------------------------------------------------------------

def _literal_kwarg(call: ast.Call, name: str) -> str | None:
    """The literal string value of ``name=`` on ``call``, if it is a constant."""
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant):
            value = kw.value.value
            if isinstance(value, str):
                return value
    return None


def _template_kwarg(call: ast.Call, name: str) -> str | None:
    """The string *template* of ``name=`` on ``call`` (f-strings normalised)."""
    for kw in call.keywords:
        if kw.arg == name:
            return _render(kw.value)
    return None


def extract_project_diagnostics() -> dict[str, list[str]]:
    """Maps project/CLI-layer codes to the messages emitted for them.

    The project layer (`pengu.lock`, dependency resolution) does **not** use
    ``code=`` keywords: it prints ``"[E0061] …"`` strings and builds JSON
    diagnostics with ``{"code": "E0061", …}``.  Those codes share the ``Exxxx``
    namespace with the language diagnostics and, until this function existed,
    nothing prevented the two layers from colliding — ``E0061`` was very nearly
    reassigned to a language error while the lockfile already used it.

    Returns ``{code: [message shapes]}``.
    """
    conditions: dict[str, list[str]] = {}
    for path in _source_files():
        tree = _parse(path)
        if tree is None:
            continue
        # "[E0061] message ..." literals and f-strings.
        for node in _iter_string_nodes(tree):
            text = _render(node)
            if not text:
                continue
            match = re.match(r"^\[(E\d{4})\]\s*(.*)$", text, re.S)
            if match:
                _add(conditions, match.group(1), match.group(2))
        # {"code": "E0061", "message": "..."} JSON diagnostics.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            code = None
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "code"
                        and isinstance(value, ast.Constant) and isinstance(value.value, str)
                        and _E_CODE_RE.match(value.value)):
                    code = value.value
            if not code:
                continue
            message = None
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in ("message", "msg"):
                    message = _render(value)
            if message:
                _add(conditions, code, message)
    return conditions


def _add(bank: dict[str, list[str]], code: str, message: str) -> None:
    message = message.strip()
    if not message:
        return
    shapes = bank.setdefault(code, [])
    if message not in shapes:
        shapes.append(message)


def extract_error_classes() -> dict[str, dict]:
    """Maps every code with a dedicated exception class to that class's data.

    The code is read from ``kwargs.setdefault("code", "Exxxx")`` in the class
    body; the explanation is the class docstring with its leading ``Exxxx: ``
    stripped.  ``help``/``note`` come from the class's own ``setdefault`` calls,
    which are the defaults every emission inherits.
    """
    tree = _parse(ERRORS_MODULE)
    if tree is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot parse {ERRORS_MODULE}")

    found: dict[str, dict] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        code: str | None = None
        help_text: str | None = None
        note_text: str | None = None
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.Call):
                continue
            func = stmt.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "setdefault":
                continue
            if not stmt.args or not isinstance(stmt.args[0], ast.Constant):
                continue
            key = stmt.args[0].value
            value = stmt.args[1] if len(stmt.args) > 1 else None
            if key == "code" and isinstance(value, ast.Constant) and _E_CODE_RE.match(str(value.value)):
                code = str(value.value)
            elif key == "help":
                help_text = _render(value) or help_text
            elif key == "note":
                note_text = _render(value) or note_text
        if code is None:
            continue

        doc = ast.get_docstring(node) or ""
        explanation = doc.strip()
        explanation = re.sub(rf"^{re.escape(code)}\s*:\s*", "", explanation).strip()

        entry = found.setdefault(code, {"classes": [], "explanation": "", "guidance": []})
        entry["classes"].append(node.name)
        if explanation and not entry["explanation"]:
            entry["explanation"] = explanation
        if help_text or note_text:
            entry["guidance"].append({"help": help_text, "note": note_text})

    return found


def extract_error_emissions() -> dict[str, dict]:
    """Maps every error code to the message shapes and classes that emit it.

    Handles both call shapes used in this code base::

        raise TypeMismatchError("message", code="E0005")     # class carries it
        self._make_error(SemanticError, "message", code="E0005")

    Returns ``{code: {"conditions": [...], "classes": [...]}}``; the class list
    is what the code is *actually* raised as, which is how the document stopped
    naming exception classes that do not exist.
    """
    found: dict[str, dict] = {}
    for path in _source_files():
        tree = _parse(path)
        if tree is None:
            continue
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            code = _literal_kwarg(call, "code")
            if not code or not _E_CODE_RE.match(code):
                continue
            message: str | None = None
            fallback = "SemanticError"
            if call.args and _is_error_class_ref(call.args[0]):
                fallback = ast.unparse(call.args[0])
                if len(call.args) > 1:
                    message = _render(call.args[1])
            elif call.args:
                message = _render(call.args[0])
            entry = found.setdefault(code, {"conditions": [], "classes": []})
            if fallback not in entry["classes"]:
                entry["classes"].append(fallback)
            if message and message not in entry["conditions"]:
                entry["conditions"].append(message)
    return found


def extract_warnings() -> dict[str, list[str]]:
    """Maps every warning code to the distinct message shapes emitted for it.

    Two shapes exist in the sources::

        self._warn("W0001", "transmute is unsafe…")        # code as an argument
        self.warnings.append(f"[W0004] Unreachable …")     # code inside the text
    """
    conditions: dict[str, list[str]] = {}
    for path in _source_files():
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if name == "_warn" and len(node.args) > 1:
                    code = _render(node.args[0])
                    message = _render(node.args[1])
                    if code and _W_CODE_RE.match(code) and message:
                        bank = conditions.setdefault(code, [])
                        if message not in bank:
                            bank.append(message)
        for node in _iter_string_nodes(tree):
            text = _render(node)
            if not text:
                continue
            match = _WARNING_TEXT_RE.match(text)
            if not match:
                continue
            code, message = match.group(1), match.group(2)
            bank = conditions.setdefault(code, [])
            if message not in bank:
                bank.append(message)
    return conditions


def warning_registry() -> dict[str, dict]:
    """Reads ``WARNING_CATALOG`` from the diagnostic module."""
    tree = _parse(ERRORS_MODULE)
    if tree is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot parse {ERRORS_MODULE}")
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
            value = node.value
        else:
            continue
        if "WARNING_CATALOG" not in targets or value is None:
            continue
        table = ast.literal_eval(value)
        return {code: dict(entry) for code, entry in table.items()}
    raise SystemExit("WARNING_CATALOG not found in pengu_errors.py")


def build_catalog() -> dict:
    """The canonical catalogue, as serialised to ``docs/error_catalog.json``."""
    classes = extract_error_classes()
    emissions = extract_error_emissions()

    errors: dict[str, dict] = {}
    for code in sorted(set(classes) | set(emissions)):
        entry: dict = {}
        own = classes.get(code)
        emitters = emissions.get(code, {}).get("classes", [])
        dedicated = list(own["classes"]) if own else []
        entry["classes"] = sorted(set(emitters) | set(dedicated))
        if own and own["explanation"]:
            entry["explanation"] = own["explanation"]
        conditions = emissions.get(code, {}).get("conditions", [])
        if conditions:
            entry["conditions"] = sorted(conditions)
        guidance = list(own["guidance"]) if own else []
        if guidance:
            deduped: list[dict] = []
            for item in sorted(guidance, key=lambda d: json.dumps(d, sort_keys=True)):
                if item not in deduped:
                    deduped.append(item)
            entry["guidance"] = deduped
        errors[code] = entry

    registry = warning_registry()
    warnings_emitted = extract_warnings()
    warnings: dict[str, dict] = {}
    for code in sorted(set(registry) | set(warnings_emitted)):
        entry = {}
        meta = registry.get(code, {})
        if "name" in meta:
            entry["name"] = meta["name"]
        if "reserved" in meta:
            entry["reserved"] = True
        if "practice" in meta:
            entry["practice"] = meta["practice"]
        conditions = warnings_emitted.get(code, [])
        if conditions:
            entry["conditions"] = sorted(conditions)
        warnings[code] = entry

    # Project/CLI-layer codes live in the same Exxxx namespace but not in the
    # language catalogue: they are emitted by `pengu.lock` handling and version
    # resolution, not by the compiler proper.
    project_conditions = extract_project_diagnostics()
    project: dict[str, dict] = {}
    for code, shapes in sorted(project_conditions.items()):
        if code in errors:
            # A code cannot mean two things. `build_catalog` still returns it so
            # the caller can report it; the test suite fails on the overlap.
            project[code] = {"conditions": sorted(shapes), "conflict": True}
        else:
            project[code] = {"conditions": sorted(shapes)}

    return {"errors": errors, "warnings": warnings, "project": project}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _md_cell(text: str) -> str:
    """Escapes a value for a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _code_range(codes: list[str]) -> str:
    return f"`{codes[0]}`–`{codes[-1]}`" if codes else "—"


def render_english(catalog: dict) -> str:
    errors, warnings = catalog["errors"], catalog["warnings"]
    out: list[str] = [MARK_BEGIN, ""]
    out.append(f"### 22.2 Compiler Error Catalog ({_code_range(sorted(errors))})")
    out.append("")
    out.append(
        "Generated from the compiler sources by `tools/gen_error_catalog.py` "
        "(error classes and their `code=` defaults in "
        "[`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py), every "
        "`code=\"Exxxx\"` emission in `pengu_parser/`, `pengu_project.py` and "
        "`pengu_lsp/`).  The machine-readable form of this table is "
        "[`docs/error_catalog.json`](docs/error_catalog.json); "
        "`tests/test_error_catalog_sync.py` fails when the code and this table "
        "diverge, so **do not edit it by hand** — run "
        "`python tools/gen_error_catalog.py --write`.")
    out.append("")
    out.append(
        "`Conditions` is the number of distinct message shapes the code can carry "
        "(interpolated values are shown as `{}`).  `help:`/`note:` lists how many "
        "guidance pairs are attached to the code.")
    out.append("")
    out.append("| Code | Exception class | Conditions | Explanation | help: / note: |")
    out.append("|---|---|---|---|---|")
    for code, entry in errors.items():
        n = len(entry.get("conditions", []))
        explanation = _md_cell(entry.get("explanation", "")) or "—"
        guidance = entry.get("guidance", [])
        pairs = "—"
        if guidance:
            helps = sum(1 for g in guidance if g.get("help"))
            notes = sum(1 for g in guidance if g.get("note"))
            pairs = f"{helps} help / {notes} note"
        out.append(
            f"| `{code}` | {', '.join('`' + c + '`' for c in entry['classes'])} "
            f"| {n} | {explanation} | {pairs} |")
    out.append("")
    out.append(f"### 22.3 Compiler Warning Catalog ({_code_range(sorted(warnings))})")
    out.append("")
    out.append(
        "Warnings are emitted as `\"[Wxxxx] message\"` strings; the symbolic name "
        "and the recommended practice come from `WARNING_CATALOG` in "
        "[`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py), which is "
        "also generated into [`docs/error_catalog.json`](docs/error_catalog.json).")
    out.append("")
    out.append("| Code | Warning name | Conditions | Recommended practice |")
    out.append("|---|---|---|---|")
    for code, entry in warnings.items():
        name = entry.get("name", "—")
        if entry.get("reserved") and name != "(reserved)":
            name = f"{name} (reserved)"
        n = len(entry.get("conditions", []))
        practice = _md_cell(entry.get("practice", "—"))
        out.append(f"| `{code}` | {_md_cell(name)} | {n} | {practice} |")
    out += _render_project_table(catalog)
    out.append("")
    out.append(MARK_END)
    return "\n".join(out)


def _render_project_table(catalog: dict) -> list[str]:
    """The project/CLI-layer table, kept separate from the language catalogue.

    These codes are emitted as plain ``"[E0061] …"`` strings by the lockfile and
    dependency-resolution code, not by the compiler.  They share the ``Exxxx``
    namespace, so they are documented here and crossed with the language codes
    by the test suite: a code must not mean two things.
    """
    project = catalog.get("project", {})
    out: list[str] = [""]
    out.append(f"### 22.3.1 Project-layer diagnostics ({_code_range(sorted(project))})")
    out.append("")
    out.append(
        "Emitted by the project layer (`pengu.lock` under `--locked`/`--frozen`, "
        "and dependency resolution) as plain `[Exxxx]` strings — **not** by the "
        "language compiler, and not through a `code=` keyword.  They share the "
        "`Exxxx` namespace, so the numbering is kept disjoint from §22.2 by "
        "`tests/test_error_catalog_sync.py`.")
    out.append("")
    out.append("| Code | Conditions | Layer |")
    out.append("|---|---|---|")
    for code, entry in project.items():
        n = len(entry.get("conditions", []))
        layer = "project (conflict with §22.2!)" if entry.get("conflict") else "project"
        out.append(f"| `{code}` | {n} | {layer} |")
    return out


def render_spanish(catalog: dict) -> str:
    """The same generated catalogue with Spanish column headers.

    The *messages* stay in English: they are the literal compiler output, and
    translating them would produce a document that cannot be diffed against the
    diagnostics a user actually sees.
    """
    errors, warnings = catalog["errors"], catalog["warnings"]
    out: list[str] = [MARK_BEGIN, ""]
    out.append(f"### 22.2 Catálogo de errores del compilador ({_code_range(sorted(errors))})")
    out.append("")
    out.append(
        "Generado desde el código por `tools/gen_error_catalog.py`. La forma "
        "legible por máquina es [`docs/error_catalog.json`](docs/error_catalog.json); "
        "`tests/test_error_catalog_sync.py` falla si el código y esta tabla "
        "divergen, así que **no se edita a mano**: "
        "`python tools/gen_error_catalog.py --write`.")
    out.append("")
    out.append(
        "La columna `Conditions` es el número de formas de mensaje distintas que el "
        "código puede emitir (los valores interpolados se muestran como `{}`). Los "
        "mensajes se dejan en inglés porque son la salida literal del compilador.")
    out.append("")
    out.append("| Código | Clase de excepción | Condiciones | Explicación | help: / note: |")
    out.append("|---|---|---|---|---|")
    for code, entry in errors.items():
        n = len(entry.get("conditions", []))
        explanation = _md_cell(entry.get("explanation", "")) or "—"
        guidance = entry.get("guidance", [])
        pairs = "—"
        if guidance:
            helps = sum(1 for g in guidance if g.get("help"))
            notes = sum(1 for g in guidance if g.get("note"))
            pairs = f"{helps} help / {notes} note"
        out.append(
            f"| `{code}` | {', '.join('`' + c + '`' for c in entry['classes'])} "
            f"| {n} | {explanation} | {pairs} |")
    out.append("")
    out.append(f"### 22.3 Catálogo de advertencias del compilador ({_code_range(sorted(warnings))})")
    out.append("")
    out.append(
        "Las advertencias se emiten como cadenas `\"[Wxxxx] message\"`; el nombre "
        "simbólico y la práctica recomendada vienen de `WARNING_CATALOG` en "
        "[`pengu_parser/pengu_errors.py`](pengu_parser/pengu_errors.py).")
    out.append("")
    out.append("| Código | Nombre | Condiciones | Práctica recomendada |")
    out.append("|---|---|---|---|")
    for code, entry in warnings.items():
        name = entry.get("name", "—")
        if entry.get("reserved"):
            name = f"{name} (reservada)"
        n = len(entry.get("conditions", []))
        practice = _md_cell(entry.get("practice", "—"))
        out.append(f"| `{code}` | {_md_cell(name)} | {n} | {practice} |")
    out += _render_project_table(catalog)
    out.append("")
    out.append(MARK_END)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Markdown extraction (the round trip the tests rely on)
# ---------------------------------------------------------------------------

_TABLE_ROW_RE = re.compile(r"^\|\s*`([EW]\d{4})`\s*\|(.*)\|\s*$")


def extract_tables(markdown: str) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Parses the generated region back into ``(code → classes, code → count)``.

    This is deliberately a *strict* parse of the shape ``render_*`` produces, so
    a hand edit that changes a class list or a condition count is caught.
    """
    if MARK_BEGIN not in markdown or MARK_END not in markdown:
        raise ValueError("generated catalogue markers not found")
    region = markdown.split(MARK_BEGIN, 1)[1].split(MARK_END, 1)[0]

    classes: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    in_warnings = False
    for line in region.splitlines():
        if line.startswith("### 22.3"):
            in_warnings = True
            continue
        match = _TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        code, rest = match.group(1), match.group(2)
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", rest)]
        if code.startswith("W"):
            if len(cells) >= 2 and cells[1].isdigit():
                counts[code] = int(cells[1])
            continue
        if in_warnings:
            continue
        if len(cells) >= 3:
            class_cell = cells[0]
            classes[code] = re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", class_cell)
            if cells[1].isdigit():
                counts[code] = int(cells[1])
    return classes, counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _replace_region(markdown: str, rendered: str) -> str:
    if MARK_BEGIN in markdown and MARK_END in markdown:
        head, rest = markdown.split(MARK_BEGIN, 1)
        _, tail = rest.split(MARK_END, 1)
        return head + rendered + tail
    # First run: replace §22.2 and §22.3, i.e. everything from the §22.2 heading
    # up to (but not including) the §22.4 heading.
    start = markdown.find("### 22.2")
    end = markdown.find("### 22.4")
    if start == -1 or end == -1 or end < start:
        raise SystemExit("cannot find the §22.2 … §22.4 region to replace")
    return (markdown[:start].rstrip("\n") + "\n\n" + rendered + "\n\n"
            + markdown[end:])


def extract_project_table(markdown: str) -> dict[str, int]:
    """Parses the §22.3.1 project-layer table into ``{code: condition count}``."""
    if MARK_BEGIN not in markdown or MARK_END not in markdown:
        raise ValueError("generated catalogue markers not found")
    region = markdown.split(MARK_BEGIN, 1)[1].split(MARK_END, 1)[0]
    if "### 22.3.1" not in region:
        raise ValueError("§22.3.1 project-layer table not found")
    section = region.split("### 22.3.1", 1)[1]
    counts: dict[str, int] = {}
    for line in section.splitlines():
        match = _TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        code, rest = match.group(1), match.group(2)
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", rest)]
        # This table is `| Code | Conditions | Layer |`: the count is the first
        # cell, unlike §22.2 where the class list comes first.
        if cells and cells[0].isdigit():
            counts[code] = int(cells[0])
    return counts


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _compare(name: str, expected, actual) -> list[str]:
    if expected == actual:
        return []
    problems = [f"{name}: drift"]
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if expected.get(key) != actual.get(key):
                problems.append(f"  {key}:")
                problems.append(f"    expected: {json.dumps(expected.get(key), sort_keys=True)}")
                problems.append(f"    found:    {json.dumps(actual.get(key), sort_keys=True)}")
    else:
        problems.append(f"  expected: {expected!r}")
        problems.append(f"  found:    {actual!r}")
    return problems


def cmd_check() -> int:
    catalog = build_catalog()
    problems: list[str] = []

    overlap = sorted(set(catalog["errors"]) & set(catalog.get("project", {})))
    if overlap:
        problems.append(
            f"codes used by BOTH the language and the project layer: {overlap} "
            "(a code must mean exactly one thing)")

    on_disk = _load_json(CATALOG_JSON)
    if on_disk is None:
        problems.append(f"{CATALOG_JSON.relative_to(REPO)}: missing or unparseable")
    else:
        problems += _compare("docs/error_catalog.json", catalog, on_disk)

    for path, render in ((CATALOG_MARKDOWN, render_english),
                         (CATALOG_MARKDOWN_ES, render_spanish)):
        text = path.read_text(encoding="utf-8")
        expected = render(catalog)
        try:
            classes, counts = extract_tables(text)
            project_counts = extract_project_table(text)
        except ValueError as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        want_classes = {code: entry["classes"] for code, entry in catalog["errors"].items()}
        want_counts = {code: len(entry.get("conditions", []))
                       for code, entry in catalog["errors"].items()}
        want_counts.update({code: len(entry.get("conditions", []))
                            for code, entry in catalog["warnings"].items()})
        want_project = {code: len(entry.get("conditions", []))
                        for code, entry in catalog.get("project", {}).items()}
        problems += _compare(f"{path.name} table classes", want_classes, classes)
        problems += _compare(f"{path.name} table counts", want_counts, counts)
        problems += _compare(f"{path.name} project table", want_project, project_counts)
        if MARK_BEGIN not in text or MARK_END not in text:
            problems.append(f"{path.name}: generated markers missing")

    if problems:
        print("error catalog: OUT OF SYNC", file=sys.stderr)
        for line in problems:
            print(line, file=sys.stderr)
        print(f"\nrun: python tools/gen_error_catalog.py --write", file=sys.stderr)
        return 1

    n_err = len(catalog["errors"])
    n_cond = sum(len(e.get("conditions", [])) for e in catalog["errors"].values())
    n_warn = len(catalog["warnings"])
    n_proj = len(catalog.get("project", {}))
    print(f"error catalog: {n_err} codes, {n_cond} conditions, {n_warn} warnings, "
          f"{n_proj} project-layer codes, in sync")
    return 0


def cmd_write() -> int:
    catalog = build_catalog()
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_JSON.write_text(
        json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8")
    for path, render in ((CATALOG_MARKDOWN, render_english),
                         (CATALOG_MARKDOWN_ES, render_spanish)):
        text = path.read_text(encoding="utf-8")
        path.write_text(_replace_region(text, render(catalog)), encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    print(f"wrote {CATALOG_JSON.relative_to(REPO)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="fail when the catalogue and the document diverge")
    group.add_argument("--write", action="store_true",
                       help="regenerate docs/error_catalog.json and the LANGUAGE.md region")
    group.add_argument("--json", action="store_true", help="print the catalogue")
    args = parser.parse_args(argv)

    if args.check:
        return cmd_check()
    if args.write:
        return cmd_write()
    print(json.dumps(build_catalog(), indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
