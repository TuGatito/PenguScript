"""Parser interface for PenguScript."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from lark import Lark

from penguscript.frontend.ast_nodes import Expression, Module
from penguscript.frontend.errors import SyntaxDiagnostic, diagnostic_from_exception
from penguscript.frontend.postlex import PenguIndenter
from penguscript.frontend.transformer import PenguTransformer

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


@lru_cache(maxsize=1)
def get_parser() -> Lark:
    """Return cached Lark parser instance."""
    grammar_text = _GRAMMAR_PATH.read_text(encoding="utf-8")
    return Lark(
        grammar_text,
        parser="lalr",
        lexer="contextual",
        start=["start"],
        postlex=PenguIndenter(),
        propagate_positions=True,
    )


@lru_cache(maxsize=1)
def get_transformer() -> PenguTransformer:
    """Return cached transformer instance."""
    return PenguTransformer()


def parse(text: str) -> Module:
    """Parse PenguScript source code into a Module AST node."""
    parser = get_parser()
    if isinstance(parser.options.postlex, PenguIndenter):
        parser.options.postlex.set_source(text)
    tree = parser.parse(text, start="start")
    transformer = get_transformer()
    result = transformer.transform(tree)
    if isinstance(result, Module):
        return result
    raise TypeError(f"Expected Module AST node, got {type(result).__name__}")


def parse_expr(text: str) -> Expression:
    """Parse a single expression into an Expression AST node."""
    mod = parse(text)
    if not mod.declarations:
        raise ValueError("No expression found in input")
    first = mod.declarations[0]
    if hasattr(first, "expr") and isinstance(first.expr, Expression):
        return first.expr
    if isinstance(first, Expression):
        return first
    raise TypeError(f"Expected expression, got {type(first).__name__}")


def parse_safe(
    text: str, filename: str | None = None
) -> tuple[Module | None, list[SyntaxDiagnostic]]:
    """Safely parse PenguScript source code, returning AST and syntax diagnostics."""
    try:
        mod = parse(text)
        return mod, []
    except Exception as exc:
        diag = diagnostic_from_exception(exc, source_text=text, filename=filename)
        return None, [diag]
