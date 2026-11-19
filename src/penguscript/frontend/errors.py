"""Diagnostic and error types for PenguScript frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lark.exceptions import (
    LarkError,
    UnexpectedCharacters,
    UnexpectedEOF,
    UnexpectedInput,
    UnexpectedToken,
)
from lark.indenter import DedentError

from penguscript.frontend.span import Span

_HUMAN_TOKENS: dict[str, str] = {
    "IDENT": "identifier",
    "TYPE_IDENT": "type identifier",
    "REALM_IDENT": "realm identifier",
    "INT": "integer",
    "FLOAT": "float",
    "HEX": "hexadecimal",
    "STRING": "string",
    "BOOL": "boolean",
    "NONE": "'none'",
    "NULLPTR": "'nullptr'",
    "PASS": "'pass'",
    "ELLIPSIS": "'...'",
    "MUT": "'mut'",
    "CONST": "'const'",
    "STATIC": "'static'",
    "REALM": "'realm'",
    "INVOKE": "'invoke'",
    "FROM": "'from'",
    "AS": "'as'",
    "RUNE": "'rune'",
    "ENCHANTING": "'enchanting'",
    "HEIR": "'heir'",
    "OMEN": "'omen'",
    "FLAGS": "'flags'",
    "ECHO": "'echo'",
    "SEAL": "'seal'",
    "CONSTRUCTOR": "'constructor'",
    "DESTRUCTOR": "'destructor'",
    "OPERATOR": "'operator'",
    "UNSAFE": "'unsafe'",
    "PARENT": "'parent'",
    "IF": "'if'",
    "ELSE": "'else'",
    "THEN": "'then'",
    "UNLESS": "'unless'",
    "WHILE": "'while'",
    "UNTIL": "'until'",
    "REPEAT": "'repeat'",
    "FOR": "'for'",
    "IN": "'in'",
    "BREAK": "'break'",
    "CONTINUE": "'continue'",
    "NOT": "'not'",
    "AND": "'and'",
    "OR": "'or'",
    "NEEDS": "'needs'",
    "FUNCTION": "'function'",
    "ASSIGN": "'='",
    "COLON": "':'",
    "COMMA": "','",
    "SEMICOLON": "';'",
    "LPAR": "'('",
    "RPAR": "')'",
    "LBRACK": "'['",
    "RBRACK": "']'",
    "LBRACE": "'{'",
    "RBRACE": "'}'",
    "PLUS": "'+'",
    "MINUS": "'-'",
    "STAR": "'*'",
    "SLASH": "'/'",
    "PERCENT": "'%'",
    "AMP": "'&'",
    "PIPE": "'|'",
    "CARET": "'^'",
    "TILDE": "'~'",
    "LT": "'<'",
    "GT": "'>'",
    "EQ": "'=='",
    "NEQ": "'!='",
    "LE": "'<='",
    "GE": "'>='",
    "SPACESHIP": "'<=>'",
    "RANGE_INC": "'..'",
    "RANGE_EXC": "'..<'",
    "ARROW": "'->'",
    "DOUBLE_COLON": "'::'",
    "AT": "'@'",
    "HASH": "'#'",
    "BANG": "'!'",
    "QUESTION": "'?'",
    "_INDENT": "indentation",
    "_DEDENT": "dedent",
    "_NEWLINE": "newline",
    "$END": "end of file",
}


@dataclass(frozen=True, slots=True)
class SyntaxDiagnostic:
    """Represents a syntax diagnostic with code, message, and formatting support."""

    code: str
    message: str
    span: Span | None = None
    expected: tuple[str, ...] = field(default_factory=tuple)
    source_file: str | None = None
    hint: str | None = None

    def format(self, source_text: str | None = None, filename: str | None = None) -> str:
        """Format the diagnostic into a Rust-style compiler error output."""
        return format_diagnostic(self, source_text=source_text, filename=filename)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def format_diagnostic(
    diag: SyntaxDiagnostic,
    source_text: str | None = None,
    filename: str | None = None,
) -> str:
    """Format a diagnostic with Rust-style source snippet, carets, and notes."""
    file_label = filename or diag.source_file or "<input>"
    lines: list[str] = [f"error[{diag.code}]: {diag.message}"]

    if diag.span is not None:
        lines.append(f" --> {file_label}:{diag.span.line}:{diag.span.col}")
        gutter_width = len(str(diag.span.line))
        pipe_pad = " " * gutter_width

        if source_text is not None:
            source_lines = source_text.splitlines()
            line_idx = diag.span.line - 1
            if 0 <= line_idx < len(source_lines):
                src_line = source_lines[line_idx]
                col = max(1, diag.span.col)
                tok_len = (
                    max(1, diag.span.end_byte - diag.span.start_byte)
                    if diag.span.end_byte > diag.span.start_byte
                    else 1
                )
                carets = "^" * tok_len
                caret_pad = " " * (col - 1)

                lines.append(f"{pipe_pad} |")
                lines.append(f"{diag.span.line:>{gutter_width}} | {src_line}")
                lines.append(f"{pipe_pad} | {caret_pad}{carets}")
            else:
                lines.append(f"{pipe_pad} |")
        else:
            lines.append(f"{pipe_pad} |")
    else:
        lines.append(f" --> {file_label}")

    if diag.expected:
        exp_str = ", ".join(diag.expected)
        lines.append(f"  = expected: {exp_str}")

    if diag.hint:
        lines.append(f"  = help: {diag.hint}")

    return "\n".join(lines)


class PenguSyntaxError(Exception):
    """Base exception for syntax errors in PenguScript."""

    def __init__(
        self,
        diagnostic: SyntaxDiagnostic,
        source_text: str | None = None,
        filename: str | None = None,
    ) -> None:
        self.diagnostic = diagnostic
        self.source_text = source_text
        self.filename = filename
        super().__init__(diagnostic.format(source_text=source_text, filename=filename))


def diagnostic_from_exception(
    exc: Exception,
    source_text: str | None = None,
    filename: str | None = None,
) -> SyntaxDiagnostic:
    """Convert a Lark parsing exception into a SyntaxDiagnostic."""
    span: Span | None = None
    line = getattr(exc, "line", None)
    col = getattr(exc, "column", None)
    if line is not None and col is not None:
        pos = getattr(exc, "pos_in_stream", 0) or 0
        end_pos = pos
        tok = getattr(exc, "token", None)
        if tok is not None and hasattr(tok, "value"):
            end_pos = pos + len(str(tok.value))
        span = Span(start_byte=pos, end_byte=end_pos, line=line, col=col)

    expected: tuple[str, ...] = ()
    raw_expected = getattr(exc, "expected", None)
    if raw_expected:
        mapped = [_HUMAN_TOKENS.get(tok, tok) for tok in sorted(raw_expected)]
        seen: set[str] = set()
        deduped: list[str] = []
        for item in mapped:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        expected = tuple(deduped)

    if isinstance(exc, DedentError):
        m = re.search(r"column (\d+)", str(exc))
        if m and span is None:
            col_num = int(m.group(1))
            span = Span(start_byte=0, end_byte=0, line=1, col=col_num)
        return SyntaxDiagnostic(
            code="E1004",
            message="Unindent does not match any outer indentation level",
            span=span,
            source_file=filename,
            hint="Ensure indentation matches the previous block level",
        )

    if isinstance(exc, UnexpectedEOF):
        return SyntaxDiagnostic(
            code="E1002",
            message="Unexpected end of file",
            span=span,
            expected=expected,
            source_file=filename,
            hint="Complete the unfinished statement or block before end of file",
        )

    if isinstance(exc, UnexpectedCharacters):
        char = exc.char if hasattr(exc, "char") else "?"
        return SyntaxDiagnostic(
            code="E1001",
            message=f"Unexpected character '{char}'",
            span=span,
            expected=expected,
            source_file=filename,
        )

    if isinstance(exc, UnexpectedToken):
        tok = getattr(exc, "token", None)
        tok_type = getattr(tok, "type", None)
        if tok_type == "$END":
            return SyntaxDiagnostic(
                code="E1002",
                message="Unexpected end of file",
                span=span,
                expected=expected,
                source_file=filename,
                hint="Complete the unfinished statement or block before end of file",
            )
        val = str(tok.value) if tok is not None and hasattr(tok, "value") else str(tok)
        return SyntaxDiagnostic(
            code="E1001",
            message=f"Unexpected token '{val}'",
            span=span,
            expected=expected,
            source_file=filename,
        )

    if isinstance(exc, IndentationError):
        return SyntaxDiagnostic(
            code="E1003",
            message=str(exc),
            span=span,
            source_file=filename,
        )

    return SyntaxDiagnostic(
        code="E1000",
        message=str(exc),
        span=span,
        source_file=filename,
    )


__all__ = [
    "DedentError",
    "LarkError",
    "PenguSyntaxError",
    "SyntaxDiagnostic",
    "UnexpectedCharacters",
    "UnexpectedEOF",
    "UnexpectedInput",
    "UnexpectedToken",
    "diagnostic_from_exception",
    "format_diagnostic",
]
