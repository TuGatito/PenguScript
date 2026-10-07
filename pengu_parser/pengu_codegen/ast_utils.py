"""Small AST utilities shared by the collection and translation passes.

Part of :mod:`pengu_parser.pengu_codegen`; see
:class:`~pengu_parser.pengu_codegen.main.PenguCodegen` for the assembled
generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    Dict,
    List,
    Optional,
    Token,
    Tree,
    Tuple,
)

def _normalize_banish_ident(val: str) -> str:
    """Unwraps balanced outer parens and whitespace from a C expression."""
    s = val.strip()
    while s.startswith("(") and s.endswith(")") and len(s) > 1:
        depth = 0
        balanced = True
        for i, c in enumerate(s):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0 and i != len(s) - 1:
                    balanced = False
                    break
        if not balanced:
            break
        s = s[1:-1].strip()
    return s
def _extract_attributes_from_node(children: List[Any], start_idx: int = 0) -> Tuple[Dict[str, List[Any]], int]:
    attrs: Dict[str, List[Any]] = {}
    idx = start_idx
    if idx < len(children) and isinstance(children[idx], Tree) and children[idx].data == "attributes":
        for attr_tree in children[idx].children:
            if isinstance(attr_tree, Tree) and attr_tree.data == "attribute":
                attr_name = str(attr_tree.children[0])
                args: List[Any] = []
                for sub in attr_tree.children[1:]:
                    if isinstance(sub, Tree) and sub.data == "attribute_args":
                        for a in sub.children:
                            if isinstance(a, Token):
                                if a.type == "INT":
                                    args.append(int(str(a)))
                                elif a.type in ("STRING", "TRIPLE_STRING", "RAW_STRING", "RAW_TRIPLE_STRING"):
                                    s = str(a)
                                    args.append(s[1:-1] if s.startswith(('"', "'")) else s)
                                else:
                                    s = str(a)
                                    args.append(int(s) if s.isdigit() else s)
                            elif isinstance(a, Tree):
                                s = str(a.children[0]) if a.children else ""
                                args.append(s[1:-1] if s.startswith(('"', "'")) else s)
                attrs[attr_name] = args
        idx += 1
    return attrs, idx
def skip_weave_modifiers(children, start: int = 0):
    """Parses leading ``inline``/``ritual`` weave modifiers from a weave/declare
    AST node. The grammar wraps each modifier in a ``weave_modifier`` Tree when
    present (``Tree('weave_modifier', [Token('RITUAL','ritual')])``), but older
    callers also tolerated bare ``Token`` modifiers directly in the child list;
    both shapes are handled here.

    Returns ``(is_inline, is_ritual, next_index)``.
    """
    is_inline = False
    is_ritual = False
    idx = start
    while idx < len(children) and isinstance(children[idx], Tree) and children[idx].data == "attributes":
        idx += 1
    while idx < len(children):
        child = children[idx]
        if isinstance(child, Tree) and child.data == "weave_modifier":
            for sub in child.children:
                if isinstance(sub, Token) and str(sub) == "inline":
                    is_inline = True
                elif isinstance(sub, Token) and str(sub) == "ritual":
                    is_ritual = True
            idx += 1
        elif isinstance(child, Token) and str(child) in ("inline", "ritual"):
            if str(child) == "inline":
                is_inline = True
            else:
                is_ritual = True
            idx += 1
        else:
            break
    return is_inline, is_ritual, idx
def get_generic_ast_name(node: Any) -> Optional[str]:
    """Extracts the declared function name from a weave_decl AST node."""
    if not isinstance(node, Tree) or node.data != "weave_decl":
        return None
    _, _, idx = skip_weave_modifiers(node.children)
    if idx < len(node.children):
        return str(node.children[idx])
    return None
def unwrap_top_level(node):
    """Descends through top_stmt wrappers to the real declaration."""
    while node is not None and isinstance(node, Tree) and node.data == "top_stmt" and node.children:
        node = node.children[0]
    return node
def flatten_at_chain(node: Any) -> List[Any]:
    """Flattens an 'at' chain into [base, idx1, idx2, ...] regardless of the
    association produced by the parser (left or right nested)."""
    if not (isinstance(node, Tree) and node.data == "at_expr"):
        return [node]
    left = node.children[0]
    right = node.children[1]
    if isinstance(left, Tree) and left.data == "at_expr":
        parts = flatten_at_chain(left)
        parts.append(right)
        return parts
    if isinstance(right, Tree) and right.data == "at_expr":
        return [left] + flatten_at_chain(right)
    return [left, right]
