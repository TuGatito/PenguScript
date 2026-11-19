"""Tests for operator precedence and associativity."""

from __future__ import annotations

from penguscript.frontend.ast_nodes import Binary, IntLit, Paren, Unary
from penguscript.frontend.parser import parse_expr


def _strip_span(node: object) -> object:
    """Helper to compare AST trees ignoring spans."""
    if isinstance(node, Binary):
        return (node.op, _strip_span(node.left), _strip_span(node.right))
    if isinstance(node, Unary):
        return (node.op, _strip_span(node.operand))
    if isinstance(node, Paren):
        return ("paren", _strip_span(node.inner))
    if isinstance(node, IntLit):
        return node.value
    return node


def test_mul_over_add_precedence() -> None:
    """Multiplication binds tighter than addition."""
    expr = parse_expr("1 + 2 * 3")
    assert _strip_span(expr) == ("+", 1, ("*", 2, 3))


def test_paren_overrides_precedence() -> None:
    """Parentheses override natural precedence."""
    expr = parse_expr("(1 + 2) * 3")
    assert _strip_span(expr) == ("*", ("paren", ("+", 1, 2)), 3)


def test_unary_over_binary_precedence() -> None:
    """Unary operations bind tighter than binary addition."""
    expr = parse_expr("-1 + 2")
    assert _strip_span(expr) == ("+", ("-", 1), 2)


def test_comparison_lower_than_add() -> None:
    """Comparison binds looser than arithmetic."""
    expr = parse_expr("1 + 2 < 3 * 4")
    assert _strip_span(expr) == ("<", ("+", 1, 2), ("*", 3, 4))


def test_and_over_or_precedence() -> None:
    """'and' binds tighter than 'or'."""
    expr = parse_expr("a or b and c")
    assert isinstance(expr, Binary)
    assert expr.op == "or"
    assert isinstance(expr.right, Binary)
    assert expr.right.op == "and"
