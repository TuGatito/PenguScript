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
    return sym.doc if sym.doc else fallback


class ModuleDoc:
    """Rendered documentation for one source module."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.module_name = os.path.splitext(os.path.basename(filepath))[0]
        if self.module_name.endswith(".d"):
            self.module_name = self.module_name[:-2]
        self.entries: List[Tuple[str, str]] = []  # (kind, rendered markdown)

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
        doc_pages.append((safe, page))

    # index
    index_lines = [
        "# PenguScript Documentation",
        "",
        f"> Generated by `pengu doc` for `{config.name}` v{config.version}",
        "",
        "## Modules",
        "",
    ]
    for safe, _ in doc_pages:
        name = safe[:-3] if safe.endswith(".md") else safe
        index_lines.append(f"- [{name}]({safe})")
    index_lines.append("")
    index_path = os.path.join(out_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    for safe, page in doc_pages:
        with open(os.path.join(out_dir, safe), "w", encoding="utf-8") as f:
            f.write(page)

    if all_errors:
        print(f"\033[1;33m     Warning\033[0m {all_errors} module(s) could not be documented.")
    print(f"\033[1;32m  Generated\033[0m {len(doc_pages)} module page(s) in {out_dir}")
    return index_path


if __name__ == "__main__":
    doc_project()
