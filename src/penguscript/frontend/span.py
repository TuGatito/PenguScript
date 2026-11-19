"""Source code span representation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Span:
    """Represents a range in source code."""

    start_byte: int
    end_byte: int
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None

    @classmethod
    def from_meta(cls, meta: Any) -> Span | None:
        """Create a Span from Lark Meta or token if line and column exist."""
        if meta is None:
            return None
        line = getattr(meta, "line", None)
        col = getattr(meta, "column", None)
        if line is None or col is None:
            return None
        start_byte = getattr(meta, "start_pos", 0) or 0
        end_byte = getattr(meta, "end_pos", 0) or 0
        end_line = getattr(meta, "end_line", None)
        end_col = getattr(meta, "end_column", None)
        return cls(
            start_byte=start_byte,
            end_byte=end_byte,
            line=line,
            col=col,
            end_line=end_line,
            end_col=end_col,
        )
