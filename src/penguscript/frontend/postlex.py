"""Postlex processing for indentation and token transformations."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from lark.indenter import DedentError, Indenter
from lark.lexer import Token


class PenguIndenter(Indenter):
    """Indenter configured for PenguScript indentation rules."""

    NL_type = "_NEWLINE"
    OPEN_PAREN_types = ["LPAR", "LBRACK", "LBRACE", "SET_LBRACE"]
    CLOSE_PAREN_types = ["RPAR", "RBRACK", "RBRACE"]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4

    def __init__(self, source_text: str = "") -> None:
        super().__init__()
        self.source_text = source_text
        self.last_token: Token | None = None
        self.angle_depth = 0

    def set_source(self, text: str) -> None:
        """Set source code text for lexical disambiguation."""
        self.source_text = text

    def process(self, stream: Any) -> Iterator[Token]:
        """Wrap Indenter.process to extract source text from the lexer stream if needed."""
        if not self.source_text and hasattr(stream, "gi_frame") and stream.gi_frame:
            ls = stream.gi_frame.f_locals.get("lexer_state")
            if ls and hasattr(ls, "text"):
                self.source_text = str(getattr(ls.text, "text", str(ls.text)))
        return super().process(stream)  # type: ignore[no-untyped-call,no-any-return]

    def _process(self, stream: Any) -> Iterator[Token]:
        for token in super()._process(stream):  # type: ignore[no-untyped-call]
            if token.type == "_NEWLINE":
                self.angle_depth = 0
            elif token.type in ("LT", "GENERIC_LT"):
                self.angle_depth += 1
            elif token.type == "GT":
                self.angle_depth = max(0, self.angle_depth - 1)
            elif token.type == "RSHIFT" and self.angle_depth > 0:
                t1 = Token.new_borrow_pos("GT", ">", token)
                t2 = Token.new_borrow_pos("GT", ">", token)
                self.angle_depth = max(0, self.angle_depth - 2)
                self.last_token = t2
                yield t1
                yield t2
                continue

            if token.type == "LT" and self.last_token and self.last_token.type == "IDENT":
                pos = token.start_pos
                if pos is not None and self.source_text:
                    sub = self.source_text[pos:]
                    depth = 0
                    found_gt = -1
                    for idx, ch in enumerate(sub):
                        if ch == "<":
                            depth += 1
                        elif ch == ">":
                            depth -= 1
                            if depth == 0:
                                found_gt = idx
                                break
                        elif ch in ("\n", ";", "="):
                            break
                    if found_gt != -1:
                        rest = sub[found_gt + 1 :].lstrip(" \t")
                        if rest.startswith("(") or rest.startswith("[") or rest.startswith("{"):
                            token = Token.new_borrow_pos("GENERIC_LT", "<", token)
            self.last_token = token
            yield token

    def handle_NL(self, token: Token):  # type: ignore[no-untyped-def] # noqa: N802
        if self.paren_level > 0:
            return

        indent_str = token.rsplit("\n", 1)[1]
        indent = indent_str.count(" ") + indent_str.count("\t") * self.tab_len

        if indent > self.indent_level[-1]:
            self.indent_level.append(indent)
            yield Token.new_borrow_pos(self.INDENT_type, indent_str, token)
        elif indent < self.indent_level[-1]:
            while indent < self.indent_level[-1]:
                self.indent_level.pop()
                yield Token.new_borrow_pos(self.DEDENT_type, indent_str, token)
            if indent != self.indent_level[-1]:
                expected = self.indent_level[-1]
                raise DedentError(
                    f"Unexpected dedent to column {indent}. Expected dedent to {expected}"
                )
        else:
            yield token
