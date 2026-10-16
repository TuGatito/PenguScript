"""Language-server support for ``judge <rune> over <discriminant>:``.

The compiler treats ``judge over`` as a normal checker construct, so its
diagnostics reach the editor through the regular publish path.  The editor
services that need *structure* rather than diagnostics — hover on a ``with``
binding, go-to-definition of a binding or of the ``over`` field, and the two
completion points — are computed here from the document text plus the checked
symbol table.

Everything is deliberately text-driven: a ``judge over`` clause is a handful of
lines, and parsing them here keeps the feature working while the document is
half-typed (the checker only sees a complete, well-formed clause).  The rune's
*types* still come from the symbol table, so a stale text match cannot invent a
field.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    Hover,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
)

from pengu_parser.pengu_types import (
    AliasType,
    FrozenType,
    OmenType,
    RefType,
    RuneType,
    SealType,
    Type,
)

#: ``judge <subject> over <field>:`` opening line.
_JUDGE_OVER_RE = re.compile(
    r"^(?P<indent>[ \t]*)judge[ \t]+(?P<subject>.+?)[ \t]+over[ \t]+"
    r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)[ \t]*:[ \t]*$"
)

#: A ``judge <subject> over <field-so-far>`` line, with the field still being typed.
_JUDGE_OVER_TYPING_RE = re.compile(
    r"^(?P<indent>[ \t]*)judge[ \t]+(?P<subject>.+?)[ \t]+over[ \t]+"
    r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)?[ \t]*$"
)

#: ``when <Variant> with <bindings>`` clause line.
_WHEN_WITH_RE = re.compile(
    r"^(?P<indent>[ \t]*)when[ \t]+"
    r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?(?P<variant>[A-Za-z_][A-Za-z0-9_]*)"
    r"[ \t]+with[ \t]+(?P<bindings>.*)$"
)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _strip_comment(line: str) -> str:
    """Drops a trailing ``#`` comment, ignoring ``#`` inside a string literal."""
    in_string = False
    escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_string:
            escaped = True
        elif ch == '"':
            in_string = not in_string
        elif ch == "#" and not in_string:
            return line[:i]
    return line


def _unwrap(t: Any) -> Any:
    """Peels ``ref to`` / ``frozen`` / ``alias`` / ``seal`` wrappers."""
    seen = 0
    while t is not None and seen < 32:
        if isinstance(t, (RefType, AliasType, FrozenType)):
            nxt = getattr(t, "target", None)
        elif isinstance(t, SealType):
            nxt = getattr(t, "underlying", None)
        else:
            break
        if nxt is None or nxt is t:
            break
        t = nxt
        seen += 1
    return t


def _resolve_nominal(symbols: Any, t: Any) -> Any:
    """Resolves a nominal placeholder through the symbol table when possible."""
    u = _unwrap(t)
    if isinstance(u, (RuneType, OmenType)) and not getattr(u, "fields", None) \
            and not getattr(u, "variants", None):
        name = getattr(u, "name", None)
        lookup_type = getattr(symbols, "lookup_type", None)
        if name and lookup_type is not None:
            try:
                resolved = lookup_type(name)
            except Exception:
                resolved = None
            if isinstance(resolved, (RuneType, OmenType)):
                return _unwrap(resolved)
    return u


def _fields_for(symbols: Any, type_name: str) -> Dict[str, Type]:
    """``{field: Type}`` for a rune type name, or an empty dict."""
    if not symbols or not type_name:
        return {}
    fields = {}
    runes = getattr(symbols, "runes", {}) or {}
    if type_name in runes and isinstance(runes[type_name], dict):
        fields = dict(runes[type_name])
    if not fields:
        resolved = _resolve_nominal(symbols, _rune_type_of(symbols, type_name))
        if isinstance(resolved, RuneType):
            fields = dict(resolved.fields or {})
    return fields


def _rune_type_of(symbols: Any, name: str) -> Any:
    lookup_type = getattr(symbols, "lookup_type", None)
    if lookup_type is not None:
        try:
            t = lookup_type(name)
        except Exception:
            t = None
        if t is not None:
            return t
    sym = None
    try:
        sym = symbols.lookup(name)
    except Exception:
        sym = None
    return getattr(sym, "type", None) if sym is not None else None


def _subject_rune(symbols: Any, subject: str, line: int) -> Tuple[Optional[str], Dict[str, Type]]:
    """Resolves the rune behind a ``judge <subject> over`` expression.

    Supports a plain name (``e``), and one level of field access on a name
    (``w.inner`` / ``p->inner``), which is what the compiler's own subject
    materialization treats as a cheap lvalue.
    """
    subject = subject.strip()
    if not symbols or not subject:
        return None, {}
    base_name = subject
    member = None
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:->|\.)\s*([A-Za-z_][A-Za-z0-9_]*)$", subject)
    if m:
        base_name, member = m.group(1), m.group(2)
    sym = None
    lookup_at = getattr(symbols, "lookup_at", None)
    if lookup_at is not None:
        try:
            sym = lookup_at(base_name, line + 1)
        except Exception:
            sym = None
    if sym is None:
        try:
            sym = symbols.lookup(base_name)
        except Exception:
            sym = None
    if sym is None or getattr(sym, "type", None) is None:
        return None, {}
    base_t = _resolve_nominal(symbols, sym.type)
    if member:
        if not isinstance(base_t, RuneType):
            return None, {}
        field_t = (base_t.fields or {}).get(member)
        base_t = _resolve_nominal(symbols, field_t) if field_t is not None else None
    if not isinstance(base_t, RuneType):
        return None, {}
    name = getattr(base_t, "name", None)
    fields = _fields_for(symbols, name)
    return name, fields


def _find_enclosing_judge_over(lines: List[str], position: Position) -> Optional[Dict[str, Any]]:
    """Finds the innermost ``judge <subject> over <field>:`` around the cursor."""
    if not lines or position.line < 0 or position.line >= len(lines):
        return None
    current = _strip_comment(lines[position.line])
    # 1. Cursor on the judge line itself (the ``over`` field). The completed
    # spelling carries a trailing ``:``; the half-typed one does not.
    m = _JUDGE_OVER_RE.match(current) or _JUDGE_OVER_TYPING_RE.match(current)
    if m:
        return {
            "line": position.line,
            "indent": _indent_of(current),
            "subject": m.group("subject"),
            "field": m.group("field") or "",
            "clause_line": None,
            "clause": None,
        }
    cursor_indent = _indent_of(current)
    # 2. Walk upward for the nearest opener with a smaller indent.
    for i in range(position.line - 1, max(-1, position.line - 200), -1):
        raw = _strip_comment(lines[i])
        if not raw.strip():
            continue
        indent = _indent_of(raw)
        if indent >= cursor_indent:
            continue
        m = _JUDGE_OVER_RE.match(raw)
        if m:
            clause = None
            wm = _WHEN_WITH_RE.match(current)
            if wm and _indent_of(current) > indent:
                clause = {
                    "line": position.line,
                    "variant": wm.group("variant"),
                    "bindings": wm.group("bindings"),
                }
            return {
                "line": i,
                "indent": indent,
                "subject": m.group("subject"),
                "field": m.group("field"),
                "clause_line": position.line if clause else None,
                "clause": clause,
            }
    return None


def _binding_names(bindings_text: str) -> List[str]:
    """Names in a ``with a, b if …`` / ``with a, b -> …`` binding list."""
    cut = bindings_text
    for terminator in ("->", " if ", "\tif "):
        idx = cut.find(terminator)
        if idx != -1:
            cut = cut[:idx]
    return [n for n in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", cut)]


def _field_declaration_location(symbols: Any, rune_name: str, field_name: str) -> Optional[Location]:
    """Source location of ``field_name`` inside ``rune_name``'s declaration."""
    if not symbols or not rune_name or not field_name:
        return None
    try:
        sym = symbols.lookup(rune_name)
    except Exception:
        sym = None
    if sym is None:
        return None
    file_path = getattr(sym, "file_path", None)
    start_line = getattr(sym, "line", None)
    if file_path and start_line:
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                src_lines = handle.read().splitlines()
        except Exception:
            src_lines = []
        field_re = re.compile(
            r"^[ \t]*" + re.escape(field_name) + r"[ \t]+as[ \t]+"
        )
        for i in range(max(0, start_line - 1), min(len(src_lines), start_line + 400)):
            if field_re.match(src_lines[i]):
                col = len(src_lines[i]) - len(src_lines[i].lstrip(" \t"))
                return Location(
                    uri=_path_to_uri(file_path),
                    range=Range(
                        start=Position(line=i, character=col),
                        end=Position(line=i, character=col + len(field_name)),
                    ),
                )
    if start_line:
        return Location(
            uri=_path_to_uri(file_path) if file_path else None,
            range=Range(
                start=Position(line=max(0, start_line - 1), character=0),
                end=Position(line=max(0, start_line - 1), character=len(rune_name) + 5),
            ),
        ) if file_path else None
    return None


def _path_to_uri(path: str) -> str:
    try:
        from .server import path_to_uri  # local import: server imports this module
        return path_to_uri(path)
    except Exception:
        p = os.path.abspath(path).replace(os.sep, "/")
        if not p.startswith("/"):
            p = "/" + p
        return "file://" + p


# ---------------------------------------------------------------------------
# Completions
# ---------------------------------------------------------------------------

def judge_over_completions(
    doc_text: Optional[str],
    position: Position,
    symbols: Any,
) -> Optional[List[CompletionItem]]:
    """Completions for ``judge … over `` (omen fields) and ``when … with ``.

    Returns None when the cursor is not in either position, so the caller can
    fall through to the other completion passes.
    """
    if not doc_text or symbols is None:
        return None
    lines = doc_text.splitlines()
    if not (0 <= position.line < len(lines)):
        return None
    prefix = _strip_comment(lines[position.line])[: position.character]

    # `judge <subject> over <prefix>` → fields whose type is an omen.
    m = re.match(
        r"^[ \t]*judge[ \t]+(.+?)[ \t]+over[ \t]+([A-Za-z_][A-Za-z0-9_]*)?$",
        prefix,
    )
    if m:
        subject, typed = m.group(1), m.group(2) or ""
        _rune, fields = _subject_rune(symbols, subject, position.line)
        if not fields:
            return None
        items: List[CompletionItem] = []
        for f_name, f_type in fields.items():
            if f_name.startswith("_"):
                continue
            if typed and not f_name.startswith(typed):
                continue
            if not isinstance(_resolve_nominal(symbols, f_type), OmenType):
                continue
            items.append(CompletionItem(
                label=f_name,
                kind=CompletionItemKind.Field,
                detail=f"omen discriminant ({f_type})",
                insert_text=f"{f_name}:\n\t",
            ))
        return items

    # `when <Variant> with <prefix>` → every field of the rune.
    m = _WHEN_WITH_RE.match(prefix)
    if m:
        context = _find_enclosing_judge_over(lines, position)
        if not context:
            return None
        _rune, fields = _subject_rune(symbols, context["subject"], context["line"])
        if not fields:
            return None
        typed = (m.group("bindings") or "").strip()
        typed = typed.rsplit(",", 1)[-1].strip()
        items = []
        for f_name, f_type in fields.items():
            if f_name.startswith("_"):
                continue
            if typed and not f_name.startswith(typed):
                continue
            items.append(CompletionItem(
                label=f_name,
                kind=CompletionItemKind.Field,
                detail=str(f_type),
                insert_text=f_name,
            ))
        return items
    return None


# ---------------------------------------------------------------------------
# Hover
# ---------------------------------------------------------------------------

def judge_over_hover(
    doc_text: Optional[str],
    position: Position,
    symbols: Any,
) -> Optional[Hover]:
    """Hover for a ``with`` binding (``let <field> as <T>``) or ``over`` field."""
    if not doc_text or symbols is None:
        return None
    lines = doc_text.splitlines()
    if not (0 <= position.line < len(lines)):
        return None
    line = _strip_comment(lines[position.line])
    word = _word_at(line, position.character)
    if not word:
        return None

    context = _find_enclosing_judge_over(lines, position)
    if not context:
        return None
    rune_name, fields = _subject_rune(symbols, context["subject"], context["line"])

    # The discriminant after `over`.
    if context["line"] == position.line and word == context["field"]:
        field_t = fields.get(word)
        if field_t is None:
            return None
        omen = _resolve_nominal(symbols, field_t)
        variants = ", ".join(getattr(omen, "variants", {}) or {}) or "(none)"
        return Hover(contents=MarkupContent(
            kind=MarkupKind.Markdown,
            value=(f"```pengus\nover {word} as {field_t}\n```\n"
                   f"**Discriminant field** of rune `{rune_name}`.\n\n"
                   f"Variants: {variants}"),
        ))

    # A `with` binding.
    clause = context.get("clause")
    if not clause or clause["line"] != position.line:
        return None
    if word not in _binding_names(clause["bindings"]):
        return None
    bindings_prefix = clause["bindings"]
    cut = bindings_prefix.find(word)
    if cut == -1:
        return None
    # Only a binding *name* hovers; a field used inside a guard does not.
    names = _binding_names(bindings_prefix[: cut + len(word)])
    if not names or names[-1] != word:
        return None
    field_t = fields.get(word)
    if field_t is None:
        return None
    return Hover(contents=MarkupContent(
        kind=MarkupKind.Markdown,
        value=(f"```pengus\nlet {word} as {field_t}\n```\n"
               f"**Binding** of field `{word}` on rune `{rune_name}` "
               f"(immutable `let`)."),
    ))


# ---------------------------------------------------------------------------
# Go to definition
# ---------------------------------------------------------------------------

def judge_over_definition(
    doc_text: Optional[str],
    position: Position,
    symbols: Any,
) -> Optional[Location]:
    """Definition of a ``with`` binding or of the ``over`` discriminant field."""
    if not doc_text or symbols is None:
        return None
    lines = doc_text.splitlines()
    if not (0 <= position.line < len(lines)):
        return None
    line = _strip_comment(lines[position.line])
    word = _word_at(line, position.character)
    if not word:
        return None

    context = _find_enclosing_judge_over(lines, position)
    if not context:
        return None
    rune_name, fields = _subject_rune(symbols, context["subject"], context["line"])
    if word not in fields:
        return None

    if context["line"] == position.line and word == context["field"]:
        return _field_declaration_location(symbols, rune_name, word)
    clause = context.get("clause")
    if clause and clause["line"] == position.line:
        names = _binding_names(clause["bindings"])
        cut = clause["bindings"].find(word)
        if cut == -1:
            return None
        if names and names[-1] == word and word in _binding_names(
                clause["bindings"][: cut + len(word)]):
            return _field_declaration_location(symbols, rune_name, word)
    return None


def _word_at(line: str, character: int) -> Optional[str]:
    """Identifier under ``character`` in ``line`` (LSP columns are UTF-16)."""
    if character < 0 or character > len(line):
        return None
    left = character
    while left > 0 and (line[left - 1].isalnum() or line[left - 1] == "_"):
        left -= 1
    right = character
    while right < len(line) and (line[right].isalnum() or line[right] == "_"):
        right += 1
    word = line[left:right]
    return word or None


def discriminant_token_spans(doc_text: Optional[str]) -> List[Tuple[int, int, int]]:
    """1-based ``(line, column, length)`` of every ``over`` discriminant name.

    Used by the semantic-token pass so the discriminant highlights as a field
    (``property``) rather than as a bare variable.
    """
    if not doc_text:
        return []
    spans: List[Tuple[int, int, int]] = []
    for i, raw in enumerate(doc_text.splitlines(), start=1):
        line = _strip_comment(raw)
        m = _JUDGE_OVER_RE.match(line) or _JUDGE_OVER_TYPING_RE.match(line)
        if not m:
            continue
        field = m.group("field")
        if not field:
            continue
        col = line.rfind(field, 0, m.end("field"))
        if col < 0:
            continue
        spans.append((i, col + 1, len(field)))
    return spans


def binding_token_spans(doc_text: Optional[str]) -> List[Tuple[int, int, int]]:
    """1-based ``(line, column, length)`` of every ``with`` binding name."""
    if not doc_text:
        return []
    spans: List[Tuple[int, int, int]] = []
    for i, raw in enumerate(doc_text.splitlines(), start=1):
        line = _strip_comment(raw)
        m = _WHEN_WITH_RE.match(line)
        if not m:
            continue
        bindings = m.group("bindings")
        start = m.start("bindings")
        for name_match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", bindings):
            # Stop at the guard/arrow: everything after is an expression.
            tail = bindings[: name_match.start()]
            if re.search(r"->|\bif\b", tail):
                break
            spans.append((i, start + name_match.start() + 1, len(name_match.group(0))))
    return spans
