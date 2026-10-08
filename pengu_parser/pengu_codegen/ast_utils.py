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
#: AST node kinds that carry a *failure* value out of a function.  `errdefer`
#: cleanup runs on these and only these, so a kind missing here silently
#: disables every `errdefer` on that path.
_FAILURE_RETURN_NODES = frozenset({
    "err_expr",    # error value produced by an `or:` block
    "error_lit",   # the `error` literal (only valid inside an `or:` block)
    "maybe_none",  # `return maybe none`
})
def is_failure_return_expr(node: Any) -> bool:
    """True when a return expression signals a failure return.

    A `maybe none` return is the `maybe` counterpart of `error` for
    `result`, but it was absent from the ad-hoc checks that used to live in
    :mod:`~pengu_parser.pengu_codegen.stmts` and
    :mod:`~pengu_parser.pengu_codegen.or_block`, so every ``errdefer`` in a
    ``maybe`` weave was skipped: the generated C emitted ``/* errdefer */``
    and then dropped the cleanup body entirely.  The ``err_of`` constructor
    was missing from those checks for the same reason.
    """
    if not isinstance(node, Tree):
        return False
    return node.data in _FAILURE_RETURN_NODES or _is_err_of_call(node)
def _is_err_of_call(node: Any) -> bool:
    """True for the `err_of` result constructor spelled as a call.

    ``calling err_of with e`` and ``calling oracle.err_of with e`` build a
    ``Result`` failure in one expression and never mention the ``error``
    literal, so returning one is a failure return.

    The accepted shapes deliberately mirror ``OrBlockMixin._result_ctor_name``
    -- the method that decides whether a call is really lowered as the
    intrinsic.  Recognising a spelling the lowering does not would run cleanup
    for an ordinary method call; missing one would drop it on a real failure.
    """
    if not (isinstance(node, Tree) and node.data == "calling_expr" and node.children):
        return False
    target = node.children[0]
    if not (isinstance(target, Tree) and target.data == "normal_target" and target.children):
        return False
    last = target.children[-1]
    if isinstance(last, Tree) and last.data in ("dot_access", "arrow_access") and last.children:
        return str(target.children[0]) == "oracle" and str(last.children[0]) == "err_of"
    if len(target.children) == 1:
        return str(target.children[0]) == "err_of"
    return False
