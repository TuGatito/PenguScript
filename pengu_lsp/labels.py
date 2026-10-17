"""Language-server support for labels on ``break`` / ``continue``.

A label is an identifier immediately followed by ``:`` on a ``while`` or
``for`` line (``outer: for line in lines:``).  Labels are *not* module symbols:
they never enter the symbol table, cannot be imported and are invisible to every
symbol-based service, so hover, go-to-definition, completion and rename are
computed here from the parsed tree:

* :meth:`PenguParser.parse` flattens the grammar's ``labeled_loop`` wrapper, so
  a labeled loop is the plain ``while_stmt`` / ``for_range_stmt`` /
  ``for_in_stmt`` node carrying a ``loop_label`` attribute;
* a labeled ``break`` / ``continue`` carries its label as the statement's first
  ``NAME`` token, and a bare one has no label child (the one-line aliases
  ``break_simple`` / ``continue_simple`` behave identically).

A label is unique per function (the checker reports ``E0069`` on reuse) and a
labeled jump may only target an enclosing loop (``E0007``), so the set of
statements a rename must rewrite falls out of the loop's *indentation block*:
every reference inside that block is in the same function and enclosed by the
same loop.  No symbol table is consulted at all, which also means these
services keep working on a document whose check failed.

Parsing is best-effort: a buffer that is mid-edit (or otherwise does not parse)
yields no labels instead of raising.  The parse is memoized by content hash
because completion runs on every keystroke.
"""
from __future__ import annotations

import hashlib
import itertools
import re
from typing import Dict, Iterator, List, NamedTuple, Optional, Tuple

from lark import Token, Tree

from lsprotocol.types import (
    CompletionItem,
    CompletionItemKind,
    DocumentHighlight,
    DocumentHighlightKind,
    Hover,
    Location,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    TextEdit,
    WorkspaceEdit,
)

from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser

#: Loop rules that may carry a flattened ``loop_label`` attribute.
_LOOP_RULES = ("while_stmt", "for_range_stmt", "for_in_stmt")

#: Statement rules (canonical plus the one-line alias) that may carry a label.
_BREAK_RULES = ("break_stmt", "break_simple")
_CONTINUE_RULES = ("continue_stmt", "continue_simple")

#: ``break `` / ``continue `` followed by the label being typed (or nothing yet).
#: The keyword may start the line or follow the ``:`` of a one-line block
#: (``if x > 0: break outer``).
_LABELED_CONTROL_RE = re.compile(
    r"(?:^|:)[ \t]*(?P<keyword>break|continue)[ \t]+"
    r"(?P<typed>[A-Za-z_][A-Za-z0-9_]*)?[ \t]*$"
)

#: A valid PenguScript identifier, used to validate a rename target.
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

#: Cheap pre-check for the semantic-token handler, which runs on every
#: keystroke: a label declaration (``outer: for ...``) or a labeled jump
#: (``break outer`` / ``continue outer``).  A buffer with neither shape cannot
#: contain a label token, so it is not parsed at all.
_MAYBE_LABEL_RE = re.compile(
    r"^[ \t]*[A-Za-z_][A-Za-z0-9_]*[ \t]*:"
    r"|\b(?:break|continue)[ \t]+[A-Za-z_]",
    re.MULTILINE,
)

#: Content hash -> parsed tree (or None when the text does not parse).  Bounded
#: because completion parses on every keystroke: keeping the last few buffers is
#: enough to make hover/definition after a completion free.
_PARSE_CACHE: Dict[str, Optional[Tree]] = {}
_PARSE_CACHE_ORDER: List[str] = []
_PARSE_CACHE_MAX = 4


class LabelDecl(NamedTuple):
    """A ``label:`` declaration on a loop, located in 0-based coordinates."""

    label: str
    loop_kind: str  # "for" | "while"
    line: int
    column: int
    indent: int
    end_line: int  # last 0-based line of the loop body (inclusive)


class LabelRef(NamedTuple):
    """A ``break label`` / ``continue label`` reference, 0-based."""

    label: str
    keyword: str  # "break" | "continue"
    line: int
    column: int


def _parse(doc_text: Optional[str]) -> Optional[Tree]:
    """Parses ``doc_text``, returning None when it does not parse.

    The result is memoized by content hash so the repeated requests an editor
    sends for one buffer share a single parse.

    Args:
        doc_text: Full document text, or None.

    Returns:
        The parsed tree, or None when the text is empty or invalid.
    """
    if not doc_text:
        return None
    key = hashlib.sha1(doc_text.encode("utf-8", "replace")).hexdigest()
    if key in _PARSE_CACHE:
        return _PARSE_CACHE[key]
    try:
        tree: Optional[Tree] = PenguParser().parse(doc_text)
    except PenguError:
        tree = None
    except Exception:
        tree = None
    _PARSE_CACHE[key] = tree
    _PARSE_CACHE_ORDER.append(key)
    while len(_PARSE_CACHE_ORDER) > _PARSE_CACHE_MAX:
        _PARSE_CACHE.pop(_PARSE_CACHE_ORDER.pop(0), None)
    return tree


def _iter_trees(node) -> Iterator[Tree]:
    """Yields ``node`` and every :class:`Tree` below it, depth-first."""
    if not isinstance(node, Tree):
        return
    yield node
    for child in node.children:
        yield from _iter_trees(child)


def _indent_of(line: str) -> int:
    """Number of leading space/tab characters in ``line``."""
    return len(line) - len(line.lstrip(" \t"))


def _region_end(lines: List[str], decl_line: int, indent: int) -> int:
    """Last line of the indented block that starts at ``decl_line``.

    Blank lines are skipped (they may sit between body statements) and the
    block ends at the first non-blank line indented at or below the loop's own
    indentation.  That is exactly the block the checker sees as the loop body,
    so it is also the set of statements the loop encloses.
    """
    end = decl_line
    index = decl_line + 1
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            index += 1
            continue
        if _indent_of(raw) <= indent:
            break
        end = index
        index += 1
    return end


def _decl_position(node: Tree, label: str, lines: List[str]) -> Optional[Tuple[int, int]]:
    """0-based ``(line, column)`` of a loop's ``label:`` token.

    The loop node's own position points at the ``for`` / ``while`` keyword, so
    the label is recovered from the header line, in front of the keyword.  The
    node's line is preferred (a label is unique per function, but the same name
    may label a loop in another function) and a full scan is only a fallback.
    """
    meta = getattr(node, "meta", None)
    first_choices: List[int] = []
    if meta is not None and not getattr(meta, "empty", True):
        meta_line = getattr(meta, "line", None)
        if meta_line:
            first_choices.append(meta_line - 1)

    pattern = re.compile(r"^[ \t]*(" + re.escape(label) + r")[ \t]*:")
    seen = set()
    for line0 in itertools.chain(first_choices, range(len(lines))):
        if line0 in seen or not (0 <= line0 < len(lines)):
            continue
        seen.add(line0)
        match = pattern.match(lines[line0])
        if match:
            return line0, match.start(1)
    return None


def _label_decls(tree: Tree, lines: List[str]) -> List[LabelDecl]:
    """Collects every ``label:`` declaration in ``tree``."""
    decls: List[LabelDecl] = []
    for node in _iter_trees(tree):
        if node.data not in _LOOP_RULES:
            continue
        label = getattr(node, "loop_label", None)
        if not label:
            continue
        found = _decl_position(node, str(label), lines)
        if found is None:
            continue
        line0, column = found
        indent = _indent_of(lines[line0]) if 0 <= line0 < len(lines) else column
        kind = "while" if node.data == "while_stmt" else "for"
        decls.append(LabelDecl(str(label), kind, line0, column, indent,
                               _region_end(lines, line0, indent)))
    return decls


def _label_refs(tree: Tree) -> List[LabelRef]:
    """Collects every labeled ``break`` / ``continue`` reference in ``tree``."""
    refs: List[LabelRef] = []
    for node in _iter_trees(tree):
        if node.data in _BREAK_RULES:
            keyword = "break"
        elif node.data in _CONTINUE_RULES:
            keyword = "continue"
        else:
            continue
        if not node.children:
            continue
        token = node.children[0]
        if not isinstance(token, Token) or token.type != "NAME":
            continue
        line = getattr(token, "line", None)
        column = getattr(token, "column", None)
        if line is None or column is None:
            continue
        refs.append(LabelRef(str(token), keyword, line - 1, column - 1))
    return refs


def loop_label_token_spans(doc_text: Optional[str]) -> List[Tuple[int, int, int]]:
    """Every loop-label token as 1-based ``(line, column, length)``.

    A label produces two kinds of token: the declaration (``outer:`` on a
    ``while`` / ``for`` line) and the label of every labeled ``break`` /
    ``continue``.  Both are returned so the semantic-token handler can give them
    their own type instead of the lexer's generic ``NAME`` classification.

    The coordinates are 1-based to match the lexer tokens the handler already
    works with (and the other ``*_token_spans`` helpers in this package).

    Args:
        doc_text: Full document text, or None.

    Returns:
        One ``(line, column, length)`` tuple per label token, in tree order;
        empty when the text has no labels or does not parse.
    """
    if not doc_text or not _MAYBE_LABEL_RE.search(doc_text):
        return []
    tree = _parse(doc_text)
    if tree is None:
        return []
    lines = str(doc_text).splitlines()
    spans = [(decl.line + 1, decl.column + 1, len(decl.label))
             for decl in _label_decls(tree, lines)]
    spans.extend((ref.line + 1, ref.column + 1, len(ref.label))
                 for ref in _label_refs(tree))
    return spans


def _encloses(decl: LabelDecl, line0: int, column: int) -> bool:
    """True when 0-based ``(line0, column)`` sits inside ``decl``'s loop body."""
    if line0 < decl.line or line0 > decl.end_line:
        return False
    if line0 == decl.line:
        # A one-line loop (`outer: for i in xs: break outer`): the statement is
        # on the header line, after the label.
        return column > decl.column
    return True


def _covers(position: Position, line0: int, column: int, text: str) -> bool:
    """True when ``position`` is inside the token at ``(line0, column)``."""
    return (position.line == line0
            and column <= position.character <= column + len(text))


def _decl_at(decls: List[LabelDecl], position: Position) -> Optional[LabelDecl]:
    """The declaration whose label token covers ``position``, if any."""
    for decl in decls:
        if _covers(position, decl.line, decl.column, decl.label):
            return decl
    return None


def _ref_at(refs: List[LabelRef], position: Position) -> Optional[LabelRef]:
    """The labeled jump whose label token covers ``position``, if any."""
    for ref in refs:
        if _covers(position, ref.line, ref.column, ref.label):
            return ref
    return None


def _decl_for_ref(decls: List[LabelDecl], ref: LabelRef) -> Optional[LabelDecl]:
    """The innermost loop labeled ``ref.label`` that encloses ``ref``.

    Falls back to a *unique* declaration with that name when indentation cannot
    prove enclosure (for example a body that does not follow the header), so a
    valid program still resolves while a genuinely ambiguous one returns None.
    """
    matches = [d for d in decls
               if d.label == ref.label and _encloses(d, ref.line, ref.column)]
    if matches:
        return max(matches, key=lambda d: d.line)
    same_label = [d for d in decls if d.label == ref.label]
    if len(same_label) == 1:
        return same_label[0]
    return None


def _describe(decl: LabelDecl, keyword: Optional[str] = None) -> str:
    """Markdown hover body for ``decl``, optionally seen from a jump."""
    code = f"label {decl.label}: {decl.loop_kind}"
    if keyword:
        note = (f"**Loop label** on an enclosing `{decl.loop_kind}` loop. "
                f"This `{keyword} {decl.label}` targets that loop.")
    else:
        note = (f"**Loop label** on a `{decl.loop_kind}` loop. "
                f"Reachable from inside the loop with `break {decl.label}` or "
                f"`continue {decl.label}`.")
    return f"```pengus\n{code}\n```\n\n{note}"


def loop_label_hover(doc_text: Optional[str], position: Position) -> Optional[Hover]:
    """Hover for a loop label, on its declaration or on a ``break``/``continue``.

    Args:
        doc_text: Full document text.
        position: Cursor position.

    Returns:
        A Hover describing the label, or None when the cursor is not on one.
    """
    tree = _parse(doc_text)
    if tree is None:
        return None
    lines = str(doc_text).splitlines()
    decls = _label_decls(tree, lines)

    decl = _decl_at(decls, position)
    if decl is not None:
        return Hover(contents=MarkupContent(
            kind=MarkupKind.Markdown, value=_describe(decl)))

    ref = _ref_at(_label_refs(tree), position)
    if ref is not None:
        target = _decl_for_ref(decls, ref)
        if target is not None:
            return Hover(contents=MarkupContent(
                kind=MarkupKind.Markdown, value=_describe(target, ref.keyword)))
    return None


def loop_label_definition(
    doc_text: Optional[str],
    position: Position,
    uri: str,
) -> Optional[Location]:
    """Go-to-definition from ``break outer`` / ``continue outer`` to ``outer:``.

    Args:
        doc_text: Full document text.
        position: Cursor position.
        uri: URI of the document (the label lives in the same file).

    Returns:
        The Location of the label declaration, or None.
    """
    tree = _parse(doc_text)
    if tree is None:
        return None
    lines = str(doc_text).splitlines()
    decls = _label_decls(tree, lines)
    ref = _ref_at(_label_refs(tree), position)
    if ref is None:
        return None
    target = _decl_for_ref(decls, ref)
    if target is None:
        return None
    return Location(
        uri=uri,
        range=Range(
            start=Position(line=target.line, character=target.column),
            end=Position(line=target.line,
                         character=target.column + len(target.label)),
        ),
    )


def loop_label_highlights(
    doc_text: Optional[str],
    position: Position,
) -> Optional[List[DocumentHighlight]]:
    """Document highlights for the loop label under the cursor.

    The label is the declaration plus every ``break`` / ``continue`` enclosed by
    that loop (a labeled jump can only target an enclosing loop).  A homonym in
    another function is a different label and is left out: enclosure is decided
    from the loop's indentation block, exactly like rename.

    Every occurrence is reported as :attr:`DocumentHighlightKind.Read`.  A label
    is never assigned at runtime — ``break outer`` / ``continue outer`` only read
    the jump target resolved at compile time — so marking the declaration
    ``Write`` would describe a mutation that does not exist.

    Args:
        doc_text: Full document text.
        position: Cursor position.

    Returns:
        The highlights (declaration and jumps in source order), or None when the
        cursor is not on a loop label; the caller then keeps its ordinary
        symbol-based highlighting unchanged.
    """
    tree = _parse(doc_text)
    if tree is None:
        return None
    lines = str(doc_text).splitlines()
    decls = _label_decls(tree, lines)
    refs = _label_refs(tree)

    target_ref: Optional[LabelRef] = None
    decl = _decl_at(decls, position)
    if decl is None:
        target_ref = _ref_at(refs, position)
        if target_ref is None:
            return None
        decl = _decl_for_ref(decls, target_ref)
        if decl is None:
            return None

    spans = [(decl.line, decl.column, decl.label)]
    for ref in refs:
        if ref.label != decl.label:
            continue
        # `_decl_for_ref` falls back to a unique declaration when indentation
        # cannot prove enclosure; the jump under the cursor still belongs to it.
        if ref is target_ref or _encloses(decl, ref.line, ref.column):
            spans.append((ref.line, ref.column, ref.label))
    spans.sort(key=lambda span: (span[0], span[1]))

    return [
        DocumentHighlight(
            range=Range(
                start=Position(line=line0, character=column),
                end=Position(line=line0, character=column + len(label)),
            ),
            kind=DocumentHighlightKind.Read,
        )
        for line0, column, label in spans
    ]


def loop_label_completions(
    doc_text: Optional[str],
    position: Position,
) -> Optional[List[CompletionItem]]:
    """Labels offered after ``break `` / ``continue `` at the cursor.

    Only the labels of loops that actually enclose the cursor are offered,
    innermost first.  Returns None when the cursor is not right after a bare
    ``break`` / ``continue`` keyword, so the caller falls through to the
    ordinary keyword completions (a bare ``break`` still completes to the
    keyword list).

    Args:
        doc_text: Full document text.
        position: Cursor position.

    Returns:
        Completion items, or None when this is not a label position.
    """
    tree = _parse(doc_text)
    if tree is None:
        return None
    lines = str(doc_text).splitlines()
    if not (0 <= position.line < len(lines)):
        return None
    prefix = lines[position.line][:position.character]
    match = _LABELED_CONTROL_RE.search(prefix)
    if not match:
        return None
    typed = match.group("typed") or ""

    decls = _label_decls(tree, lines)
    enclosing = [d for d in decls if _encloses(d, position.line, position.character)]
    enclosing.sort(key=lambda d: d.line, reverse=True)
    items: List[CompletionItem] = []
    for decl in enclosing:
        if typed and not decl.label.startswith(typed):
            continue
        items.append(CompletionItem(
            label=decl.label,
            kind=CompletionItemKind.Reference,
            detail=f"loop label ({decl.loop_kind} loop)",
            insert_text=decl.label,
        ))
    return items


def _text_edit(line0: int, column: int, old: str, new: str) -> TextEdit:
    """A single-document replacement of ``old`` at 0-based ``(line0, column)``."""
    return TextEdit(
        range=Range(
            start=Position(line=line0, character=column),
            end=Position(line=line0, character=column + len(old)),
        ),
        new_text=new,
    )


def loop_label_rename(
    doc_text: Optional[str],
    position: Position,
    new_name: str,
    uri: str,
) -> Optional[WorkspaceEdit]:
    """Renames the loop label under the cursor within its function.

    The declaration and every ``break`` / ``continue`` enclosed by that loop are
    rewritten.  A homonym in another function is a different label (labels are
    unique per function), so its loops are left alone.

    Args:
        doc_text: Full document text.
        position: Cursor position.
        new_name: Requested new label.
        uri: URI of the document.

    Returns:
        A WorkspaceEdit, or None when the cursor is not on a label (the caller
        then continues with the ordinary symbol rename).
    """
    tree = _parse(doc_text)
    if tree is None:
        return None
    clean_new = (new_name or "").strip()
    if not _IDENTIFIER_RE.fullmatch(clean_new):
        return None

    lines = str(doc_text).splitlines()
    decls = _label_decls(tree, lines)
    refs = _label_refs(tree)

    decl = _decl_at(decls, position)
    if decl is None:
        ref = _ref_at(refs, position)
        if ref is None:
            return None
        decl = _decl_for_ref(decls, ref)
        if decl is None:
            return None
    if decl.label == clean_new:
        return None

    edits = [_text_edit(decl.line, decl.column, decl.label, clean_new)]
    for ref in refs:
        if ref.label != decl.label:
            continue
        if not _encloses(decl, ref.line, ref.column):
            continue
        edits.append(_text_edit(ref.line, ref.column, ref.label, clean_new))
    return WorkspaceEdit(changes={uri: edits})


def loop_label_prepare_rename(
    doc_text: Optional[str],
    position: Position,
) -> Optional[Range]:
    """The range of the loop label under the cursor, when it is renameable.

    Args:
        doc_text: Full document text.
        position: Cursor position.

    Returns:
        The label token's range, or None when the cursor is not on a label.
    """
    tree = _parse(doc_text)
    if tree is None:
        return None
    lines = str(doc_text).splitlines()
    decls = _label_decls(tree, lines)

    decl = _decl_at(decls, position)
    if decl is not None:
        return Range(start=Position(line=decl.line, character=decl.column),
                     end=Position(line=decl.line,
                                  character=decl.column + len(decl.label)))

    ref = _ref_at(_label_refs(tree), position)
    if ref is not None and _decl_for_ref(decls, ref) is not None:
        return Range(start=Position(line=ref.line, character=ref.column),
                     end=Position(line=ref.line,
                                  character=ref.column + len(ref.label)))
    return None
