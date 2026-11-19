"""Semantic and analysis diagnostics with Rust-style formatted output."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from penguscript.frontend.span import Span


class DiagnosticSeverity(Enum):
    """Severity levels for compiler diagnostics."""

    ERROR = auto()
    WARNING = auto()
    INFO = auto()
    HINT = auto()


@dataclass(frozen=True, slots=True)
class Label:
    """Secondary span and message for rich diagnostics."""

    span: Span
    message: str


@dataclass(frozen=True, slots=True)
class Suggestion:
    """Code replacement suggestion for quick-fixes."""

    span: Span
    replacement: str
    message: str = ""


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """Compiler diagnostic representing an error or warning."""

    code: str
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    span: Span | None = None
    source_file: Path | str | None = None
    secondary_labels: tuple[Label, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    hint: str | None = None
    suggestions: tuple[Suggestion, ...] = field(default_factory=tuple)

    @property
    def is_error(self) -> bool:
        """Return True if this diagnostic is an error."""
        return self.severity == DiagnosticSeverity.ERROR

    @property
    def is_warning(self) -> bool:
        """Return True if this diagnostic is a warning."""
        return self.severity == DiagnosticSeverity.WARNING

    def format(self, source_text: str | None = None, filename: str | None = None) -> str:
        """Format the diagnostic into a Rust-style compiler output."""
        return format_analysis_diagnostic(self, source_text=source_text, filename=filename)

    def __str__(self) -> str:
        prefix = "error" if self.is_error else "warning"
        return f"{prefix}[{self.code}]: {self.message}"


def format_analysis_diagnostic(
    diag: Diagnostic,
    source_text: str | None = None,
    filename: str | None = None,
) -> str:
    """Format an analysis diagnostic with primary and secondary spans and line snippets."""
    file_label = str(filename or diag.source_file or "<input>")
    prefix = "error" if diag.is_error else "warning"
    lines: list[str] = [f"{prefix}[{diag.code}]: {diag.message}"]

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

    for sec in diag.secondary_labels:
        if source_text is not None:
            source_lines = source_text.splitlines()
            sec_idx = sec.span.line - 1
            if 0 <= sec_idx < len(source_lines):
                sec_src = source_lines[sec_idx]
                sec_gutter = len(str(sec.span.line))
                sec_pad = " " * sec_gutter
                sec_col = max(1, sec.span.col)
                sec_len = (
                    max(1, sec.span.end_byte - sec.span.start_byte)
                    if sec.span.end_byte > sec.span.start_byte
                    else 1
                )
                sec_markers = "-" * sec_len
                sec_col_pad = " " * (sec_col - 1)

                lines.append(f"{sec_pad} ::: {file_label}:{sec.span.line}:{sec.span.col}")
                lines.append(f"{sec_pad} |")
                lines.append(f"{sec.span.line:>{sec_gutter}} | {sec_src}")
                lines.append(f"{sec_pad} | {sec_col_pad}{sec_markers} {sec.message}")

    for note in diag.notes:
        lines.append(f"  = note: {note}")

    if diag.hint:
        lines.append(f"  = help: {diag.hint}")

    for sug in diag.suggestions:
        if sug.message:
            lines.append(f"  = suggestion: {sug.message}: '{sug.replacement}'")
        else:
            lines.append(f"  = suggestion: replace with '{sug.replacement}'")

    return "\n".join(lines)


__all__ = [
    "Diagnostic",
    "DiagnosticSeverity",
    "Label",
    "Suggestion",
    "format_analysis_diagnostic",
]
