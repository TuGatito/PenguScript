"""Language-server support for ``type of expr``.

``type of`` is a compile-time operator, so hovering it is the one place where an
editor can show the *resolved* name before running the program.  The canonical
name is computed by the checker (``pengu_infer`` records it on the node as
``_resolved_type_name`` when it infers the operator), which means the hover needs
the tree the checker ran on, not a fresh parse.

:func:`remember` is called by ``server._compute_diagnostics`` right after the
parse — before the check, which fills the attribute on the very same tree — and
keys the tree by a hash of the document text.  A later hover therefore reuses
exactly the tree the last validation produced, for the exact text it validated,
and a stale buffer can never answer for a newer one.  The cache is bounded: an
editor sends a hover for one buffer at a time.
"""
from __future__ import annotations

import bisect
import hashlib
from typing import Dict, List, Optional

from lark import Tree

from lsprotocol.types import Hover, MarkupContent, MarkupKind, Position

#: Text hash -> the tree that was checked for it.  Bounded, newest last.
_TREES: Dict[str, Tree] = {}
_ORDER: List[str] = []
_MAX_TREES = 4


def _key(source: str) -> str:
    """Stable cache key for a document's text."""
    return hashlib.sha1(source.encode("utf-8", "replace")).hexdigest()


def remember(source: str, tree: Optional[Tree]) -> None:
    """Records the tree the checker is about to fill in for ``source``.

    Args:
        source: The document text that produced ``tree``.
        tree: The parsed tree, or None when parsing failed.
    """
    if tree is None or not source:
        return
    key = _key(source)
    if key not in _TREES:
        _ORDER.append(key)
    _TREES[key] = tree
    while len(_ORDER) > _MAX_TREES:
        _TREES.pop(_ORDER.pop(0), None)


def remembered_tree(source: str) -> Optional[Tree]:
    """The tree the last validation parsed for ``source``, if still cached.

    Other request handlers (loop labels, ``judge`` completion) need the same
    syntax tree.  Re-parsing a 2 000-line buffer inside a hover request added a
    full parse to the first hover after every edit; sharing the checker's tree
    keeps those requests at microsecond cost.
    """
    if not source:
        return None
    return _TREES.get(_key(source))


def _line_starts(source: str) -> List[int]:
    """Character offset of the first character of every line."""
    starts = [0]
    for index, char in enumerate(source):
        if char == "\n":
            starts.append(index + 1)
    return starts


def _offset_of(position: Position, starts: List[int]) -> Optional[int]:
    """Character offset of an LSP ``position``, or None when out of range."""
    if position.line < 0 or position.line >= len(starts):
        return None
    return starts[position.line] + max(0, position.character)


def _type_of_at(tree: Tree, position: Position, starts: List[int]) -> Optional[Tree]:
    """The innermost ``type_of`` node whose span covers ``position``, if any."""
    target = _offset_of(position, starts)
    if target is None:
        return None
    best: Optional[Tree] = None
    best_width = None
    for node in tree.iter_subtrees():
        if not isinstance(node, Tree) or node.data != "type_of":
            continue
        meta = getattr(node, "meta", None)
        if meta is None or getattr(meta, "empty", True):
            continue
        start_pos = getattr(meta, "start_pos", None)
        end_pos = getattr(meta, "end_pos", None)
        if start_pos is None or end_pos is None:
            continue
        if not (start_pos <= target <= end_pos):
            continue
        width = end_pos - start_pos
        if best_width is None or width < best_width:
            best, best_width = node, width
    return best


def type_of_hover(source: str, position: Position) -> Optional[Hover]:
    """Hover for ``type of expr``: the canonical name of the operand's type.

    Returns None when the cursor is not on a ``type of`` expression, when the
    buffer has not been validated yet, or when the operand's type could not be
    resolved (the checker records nothing it could not infer).
    """
    if not source:
        return None
    tree = _TREES.get(_key(source))
    if tree is None:
        return None
    starts = _line_starts(source)
    node = _type_of_at(tree, position, starts)
    if node is None:
        return None
    resolved = getattr(node, "_resolved_type_name", None)
    if not resolved:
        return None
    meta = node.meta
    operand = ""
    try:
        operand = source[meta.start_pos:meta.end_pos]
    except (TypeError, AttributeError):
        operand = ""
    operand = " ".join(operand.split())
    if len(operand) > 60:
        operand = operand[:57] + "…"
    shown = operand or "expr"
    return Hover(
        contents=MarkupContent(
            kind=MarkupKind.Markdown,
            value=(
                "```pengus\n"
                f"{shown} → {resolved}\n"
                "```\n"
                "`type of` is a compile-time operator: it reads the static type of "
                "the expression and yields its canonical name as a borrowed "
                "`string`. The operand is never evaluated, so the generated C is a "
                f"string literal — `pengu_string_from_cstr(\"{resolved}\")`."
            ),
        )
    )
