#!/usr/bin/env python3
"""PenguScript Documentation Generator ('pengu doc').

Walks a project's source modules, extracts `##` doc comments captured by the
semantic checker (Symbol.doc), and renders a Markdown reference site combining
the doc text with inferred signatures (parameters, return types, struct fields,
constants, variant values).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_symbols import resolve_imports, Symbol
from pengu_parser.pengu_comptime import parse_cli_defines
from pengu_parser.pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, AliasType, SealType,
    ConceptType, OPAQUE_TYPE, INT_TYPE, STRING_TYPE, VOID_TYPE
)
from pengu_parser.pengu_errors import PenguError


def _type_name(t: Optional[Type]) -> str:
    if t is None:
        return "void"
    if isinstance(t, FnType):
        params = ", ".join(f"{n or '_'}: {_type_name(pt)}" for n, pt in t.params)
        return f"weave with {params} into {_type_name(t.return_type)}"
    return str(t)


def _render_signature(sym: Symbol) -> str:
    t = sym.type
    if isinstance(t, FnType):
        params = ", ".join(f"{n}: {_type_name(pt)}" for n, pt in t.params)
        return f"**{sym.get_c_name()}**({params}) -> {_type_name(t.return_type)}"
    return f"**{sym.name}** : {_type_name(t)}"


def _doc_or(sym: Symbol, fallback: str) -> str:
    """Renders a symbol's doc comment: summary + Doxygen tags + deprecation badge.

    Doxygen-style lines (``@param``, ``@return``, ``@see``, ``@deprecated``, …)
    are pulled out of the prose into a structured bullet list, and a symbol
    marked ``@deprecated`` (attribute or tag) gets a visible badge.
    """
    doc = sym.doc or ""
    summary_lines: List[str] = []
    tag_lines: List[str] = []
    in_tags = False
    for raw in doc.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("@"):
            in_tags = True
        if in_tags:
            tag_lines.append(line.strip())
        else:
            summary_lines.append(line)

    summary = "\n".join(summary_lines).strip()
    parts: List[str] = [summary or fallback]

    attrs = getattr(sym, "attributes", None) or {}
    dep_reason = None
    if "deprecated" in attrs:
        vals = attrs.get("deprecated") or []
        dep_reason = vals[0] if vals else ""
    if dep_reason is None:
        for tag in tag_lines:
            if tag.lower().startswith("@deprecated"):
                dep_reason = tag[len("@deprecated"):].strip()
                break
    if dep_reason is not None:
        parts.append("> ⚠️ **Deprecated**" + (f" — {dep_reason}" if dep_reason else ""))

    if tag_lines:
        parts.append("\n".join(f"- `{_escape_code(t)}`" for t in tag_lines))
    return "\n\n".join(p for p in parts if p)


def _doc_summary(sym: Symbol) -> str:
    """First prose line of a symbol's doc, for the search index."""
    doc = sym.doc or ""
    for raw in doc.splitlines():
        line = raw.strip()
        if line and not line.startswith("@"):
            return line
    return ""


class ModuleDoc:
    """Rendered documentation for one source module."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.module_name = os.path.splitext(os.path.basename(filepath))[0]
        if self.module_name.endswith(".d"):
            self.module_name = self.module_name[:-2]
        self.entries: List[Tuple[str, str]] = []  # (kind, rendered markdown)
        self.index_entries: List[Dict[str, Any]] = []  # search-index rows

    def add(self, kind: str, markdown: str) -> None:
        self.entries.append((kind, markdown))


def _escape_code(text: str) -> str:
    return text.replace("`", "\\`")


def render_module_doc(
    module_path: str,
    checker: PenguChecker,
    order: List[str],
) -> ModuleDoc:
    """Collects the documented symbols that belong to one module file."""
    doc = ModuleDoc(module_path)
    mod_abs = os.path.abspath(module_path)
    syms = checker.symbols.global_scope.symbols
    seen: set = set()

    def record(sym: Symbol) -> None:
        key = (sym.name, sym.line)
        if key in seen:
            return
        seen.add(key)
        t = sym.type
        kind = sym.kind
        if kind in ("weave", "declare", "function", "const", "rune", "echo",
                    "omen", "alias", "seal", "concept", "import"):
            attrs = getattr(sym, "attributes", None) or {}
            doc_tags = (sym.doc or "").lower()
            doc.index_entries.append({
                "name": sym.name,
                "kind": kind,
                "module": doc.module_name,
                "signature": _render_signature(sym),
                "summary": _doc_summary(sym),
                "deprecated": ("deprecated" in attrs) or ("@deprecated" in doc_tags),
            })
        if kind == "weave" or kind == "declare" or kind == "function":
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> {_render_signature(sym)}\n\n"
                f"{_doc_or(sym, '_Undocumented function._')}\n"
            )
            doc.add("function", rendered)
        elif kind == "const":
            val = getattr(sym, "const_val", None)
            val_str = f"` = {val}`" if val is not None else ""
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> const {_type_name(t)}{val_str}\n\n"
                f"{_doc_or(sym, '_Undocumented constant._')}\n"
            )
            doc.add("const", rendered)
        elif kind == "rune":
            fields = "\n".join(f"- `{f}` : {_type_name(ft)}" for f, ft in (t.fields.items() if isinstance(t, RuneType) else []))
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> **rune** struct\n\n"
                f"{_doc_or(sym, '_Undocumented struct._')}\n\n"
                f"**Fields:**\n\n{fields or '_none_'}\n"
            )
            doc.add("rune", rendered)
        elif kind == "echo":
            fields = "\n".join(f"- `{f}` : {_type_name(ft)}" for f, ft in (t.fields.items() if isinstance(t, EchoType) else []))
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> **echo** tagged union\n\n"
                f"{_doc_or(sym, '_Undocumented union._')}\n\n"
                f"**Fields:**\n\n{fields or '_none_'}\n"
            )
            doc.add("echo", rendered)
        elif kind == "omen":
            if isinstance(t, OmenType):
                vals = "\n".join(
                    f"- `{v}` = `{val}`" for v, val in t.variant_values.items()
                ) or "- *(implicit values)*"
                rendered = (
                    f"### `{_escape_code(sym.name)}`\n\n"
                    f"> **omen** ({'string' if t.is_string_valued else 'integer'} values"
                    f"{', algebraic payload' if t.is_algebraic else ''})\n\n"
                    f"{_doc_or(sym, '_Undocumented omen._')}\n\n"
                    f"**Variants:**\n\n{vals}\n"
                )
            else:
                rendered = f"### `{_escape_code(sym.name)}`\n\n>{_doc_or(sym, '_Undocumented omen._')}\n"
            doc.add("omen", rendered)
        elif kind == "alias":
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> alias of {_type_name(t)}\n\n"
                f"{_doc_or(sym, '_Undocumented alias._')}\n"
            )
            doc.add("alias", rendered)
        elif kind == "seal":
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> sealed newtype over {_type_name(t)}\n\n"
                f"{_doc_or(sym, '_Undocumented seal._')}\n"
            )
            doc.add("seal", rendered)
        elif kind == "concept":
            rendered = (
                f"### `{_escape_code(sym.name)}`\n\n"
                f"> **concept**\n\n{_doc_or(sym, '_Undocumented concept._')}\n"
            )
            doc.add("concept", rendered)
        elif kind == "import":
            rendered = (
                f"### Module `{_escape_code(sym.name)}`\n\n"
                f"{_doc_or(sym, '_No module docs._')}\n"
            )
            doc.add("import", rendered)
        else:
            # var/let locals are not module-level documentation targets.
            return

    for sname, sym in syms.items():
        fp = sym.file_path
        if not fp:
            continue  # built-in/global symbols are not module documentation targets.
        try:
            same = os.path.abspath(fp) == mod_abs
        except Exception:
            same = False
        if same:
            record(sym)

    if not doc.entries:
        doc.add("module", f"_No documented symbols in `{os.path.basename(module_path)}`._")
    return doc


def _render_search_html(project_name: str, version: str,
                        entries: List[Dict[str, Any]]) -> str:
    """Self-contained HTML page with a client-side symbol search."""
    import json

    payload = json.dumps(entries, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{project_name} — PenguScript docs</title>
<style>
 body {{ font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; padding: 0 1rem; }}
 input#q {{ width: 100%; padding: .6rem .8rem; font-size: 1rem; box-sizing: border-box; }}
 .entry {{ padding: .5rem .2rem; border-bottom: 1px solid #eee; }}
 .name {{ font-weight: 600; }}
 .kind {{ color: #666; font-size: .85rem; margin-left: .5rem; }}
 .sig {{ font-family: ui-monospace, monospace; color: #333; font-size: .9rem; }}
 .dep {{ color: #b45309; font-size: .8rem; margin-left: .5rem; }}
 .summary {{ color: #444; font-size: .9rem; }}
</style>
</head>
<body>
<h1>{project_name} — symbol search</h1>
<p>Generated by <code>pengu doc</code> for v{version}.</p>
<input id="q" placeholder="Search by name, kind, module or signature…" autofocus>
<p id="count"></p>
<div id="results"></div>
<script>
const DATA = {payload};
const q = document.getElementById('q');
const results = document.getElementById('results');
const count = document.getElementById('count');
function render(items) {{
  results.innerHTML = items.slice(0, 300).map(e =>
    `<div class="entry"><a class="name" href="${{e.page}}">${{e.name}}</a>` +
    `<span class="kind">${{e.kind}} · ${{e.module}}</span>` +
    (e.deprecated ? '<span class="dep">[deprecated]</span>' : '') +
    `<div class="sig">${{e.signature}}</div>` +
    (e.summary ? `<div class="summary">${{e.summary}}</div>` : '') + '</div>').join('');
  count.textContent = items.length + ' symbol(s)';
}}
function search() {{
  const term = q.value.trim().toLowerCase();
  if (!term) {{ render(DATA); return; }}
  render(DATA.filter(e =>
    (e.name + ' ' + e.kind + ' ' + e.module + ' ' + e.signature + ' ' + e.summary)
      .toLowerCase().includes(term)));
}}
q.addEventListener('input', search);
render(DATA);
</script>
</body>
</html>
"""


def doc_project(
    config_path: Optional[str] = None,
    output: Optional[str] = None,
    entry: Optional[str] = None,
) -> str:
    """Generates a Markdown documentation site for a PenguScript project.

    Args:
        config_path: Optional path to config file or project root.
        output: Optional output directory (default: <project>/docs).
        entry: Optional entry file override (relative to project root).

    Returns:
        Path to the generated index file.
    """
    try:
        from pengu_project import ProjectConfig
    except Exception:
        from pengu_project import ProjectConfig  # noqa: F811

    config = ProjectConfig.load(config_path)
    if entry:
        config.entry = entry

    base_dir = config.base_dir
    out_dir = os.path.abspath(output) if output else os.path.join(base_dir, "docs")
    os.makedirs(out_dir, exist_ok=True)

    parser = PenguParser()
    compile_env = parse_cli_defines(config.defines)

    entry_abs = config.resolve_entry()
    if not os.path.isfile(entry_abs):
        print(f"\033[1;31m      Error\033[0m entry file not found: {entry_abs}", file=sys.stderr)
        return ""
    order = resolve_imports(base_dir, entry_abs, parser)

    # Parse + check each module once so doc comments and signatures are resolved.
    doc_pages: List[Tuple[str, str]] = []  # (relative output filename, content)
    all_index: List[Dict[str, Any]] = []
    all_errors = 0
    for mod_path in order:
        try:
            with open(mod_path, "r", encoding="utf-8") as f:
                code = f.read()
        except OSError as e:
            print(f"\033[1;33m     Warning\033[0m cannot read {mod_path}: {e}", file=sys.stderr)
            continue
        try:
            tree = parser.parse(code)
            checker = PenguChecker(base_dir=base_dir, filename=mod_path, compile_env=compile_env)
            checker.check(tree, source=code, filename=mod_path)
        except PenguError as e:
            msg = str(e).splitlines()
            print(f"\033[1;33m     Warning\033[0m {mod_path}: {msg[0] if msg else e}", file=sys.stderr)
            all_errors += 1
            continue
        except Exception as e:
            print(f"\033[1;33m     Warning\033[0m {mod_path}: {e}", file=sys.stderr)
            all_errors += 1
            continue

        mdoc = render_module_doc(mod_path, checker, order)

        rel = os.path.relpath(mod_path, base_dir)
        safe = rel.replace(os.sep, "_").replace("/", "_").replace("\\", "_")
        if safe.endswith(".pengu"):
            safe = safe[: -len(".pengu")]
        safe = f"{safe}.md"
        body = "\n\n".join(rendered for _, rendered in mdoc.entries)
        page = (
            f"# {mdoc.module_name}\n\n"
            f"> Source: `{rel}`\n\n---\n\n{body}\n"
        )
        for entry in mdoc.index_entries:
            entry["page"] = safe
        all_index.extend(mdoc.index_entries)
        doc_pages.append((safe, page))

    # index
    index_lines = [
        "# PenguScript Documentation",
        "",
        f"> Generated by `pengu doc` for `{config.name}` v{config.version}",
        "",
        f"> 🔎 **[Symbol search (HTML)](index.html)** — {len(all_index)} indexed symbol(s).",
        "",
        "## Modules",
        "",
    ]
    for safe, _ in doc_pages:
        name = safe[:-3] if safe.endswith(".md") else safe
        index_lines.append(f"- [{name}]({safe})")

    kind_labels = {
        "concept": "Concepts",
        "rune": "Runes (structs)",
        "echo": "Echoes (unions)",
        "omen": "Omens (enums / sum types)",
        "seal": "Seals (newtypes)",
        "alias": "Aliases",
        "const": "Constants",
        "weave": "Functions",
        "declare": "External C declarations",
        "function": "Functions",
        "import": "Modules",
    }
    by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for entry in all_index:
        by_kind.setdefault(entry["kind"], []).append(entry)
    if by_kind:
        index_lines += ["", "## Symbol index", ""]
        for kind in sorted(by_kind, key=lambda k: kind_labels.get(k, k)):
            index_lines.append(f"### {kind_labels.get(kind, kind)}")
            index_lines.append("")
            for entry in sorted(by_kind[kind], key=lambda e: e["name"]):
                dep = " `[deprecated]`" if entry.get("deprecated") else ""
                index_lines.append(
                    f"- [`{entry['name']}`]({entry['page']}) — {entry['signature']}{dep}"
                )
            index_lines.append("")
    index_lines.append("")
    index_path = os.path.join(out_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    for safe, page in doc_pages:
        with open(os.path.join(out_dir, safe), "w", encoding="utf-8") as f:
            f.write(page)

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(_render_search_html(config.name, config.version, all_index))

    if all_errors:
        print(f"\033[1;33m     Warning\033[0m {all_errors} module(s) could not be documented.")
    print(f"\033[1;32m  Generated\033[0m {len(doc_pages)} module page(s) in {out_dir}")
    return index_path


if __name__ == "__main__":
    doc_project()
