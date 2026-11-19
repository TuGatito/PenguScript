"""Generic AST visitor for PenguScript frozen dataclass nodes."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import fields
from typing import Any

from penguscript.frontend.ast_nodes import Node

_CAMEL_TO_SNAKE_RE = re.compile(r"(?<!^)(?=[A-Z])")


def _to_snake_case(name: str) -> str:
    return _CAMEL_TO_SNAKE_RE.sub("_", name).lower()


class ASTVisitor:
    """Base visitor for PenguScript AST nodes.

    Dispatches to visit_<snake_case_node_name>(node) (e.g. visit_rune_decl)
    if implemented, otherwise falls back to generic_visit(node).
    """

    def visit(self, node: Node | None) -> Any:
        """Visit a single AST node, returning the method result or None."""
        if node is None:
            return None

        cls_name = type(node).__name__
        snake_name = _to_snake_case(cls_name)

        # Try visit_<snake_name> first (e.g. visit_const_decl)
        method = getattr(self, f"visit_{snake_name}", None)
        if method is not None:
            return method(node)

        # Try visit_<ClassName> fallback
        method = getattr(self, f"visit_{cls_name}", None)
        if method is not None:
            return method(node)

        # Fallback to generic visit
        return self.generic_visit(node)

    def generic_visit(self, node: Node) -> None:
        """Visit all child Node instances and collections of Node instances in fields."""
        for f in fields(node):
            val = getattr(node, f.name, None)
            if val is None:
                continue

            if isinstance(val, Node):
                self.visit(val)
            elif isinstance(val, (list, tuple)):
                self._visit_sequence(val)
            elif isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(k, Node):
                        self.visit(k)
                    if isinstance(v, Node):
                        self.visit(v)

    def _visit_sequence(self, items: Iterable[Any]) -> None:
        """Visit all Node elements within a sequence."""
        for item in items:
            if isinstance(item, Node):
                self.visit(item)
            elif isinstance(item, (list, tuple)):
                self._visit_sequence(item)


__all__ = ["ASTVisitor"]
