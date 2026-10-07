"""`#line` markers pointing back at the `.pengu` sources.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    Optional,
    Token,
    Tree,
    os,
)

class LineMarkerMixin:
    """`#line` markers pointing back at the `.pengu` sources."""

    @staticmethod
    def _node_line(node: Any) -> Optional[int]:
        """Returns the 1-based `.pengu` source line of an AST node, or None.

        Collected declarations are sometimes rebuilt by the collector and lose
        their ``meta`` block; the first descendant token or tree that still carries a
        line number is used as a fallback (tokens always keep theirs).
        """
        if node is None:
            return None
        direct_line = getattr(node, "line", None)
        if direct_line:
            try:
                return int(direct_line)
            except (TypeError, ValueError):
                pass
        meta = getattr(node, "meta", None)
        line = getattr(meta, "line", None) if meta is not None else None
        if line:
            try:
                return int(line)
            except (TypeError, ValueError):
                pass

        stack = [node]
        seen = 0
        while stack and seen < 64:
            current = stack.pop(0)
            seen += 1
            tok_line = getattr(current, "line", None)
            if tok_line:
                try:
                    return int(tok_line)
                except (TypeError, ValueError):
                    pass
            c_meta = getattr(current, "meta", None)
            if c_meta and getattr(c_meta, "line", None):
                try:
                    return int(c_meta.line)
                except (TypeError, ValueError):
                    pass
            children = getattr(current, "children", None)
            if children:
                stack.extend(c for c in children if isinstance(c, (Tree, Token)))
        return None
    def _display_path(self, filepath: Optional[str]) -> Optional[str]:
        """Returns the file name to spell in `#line`.

        Paths are made relative to the bundle directory (e.g.
        ``../src/main.pengu``), which keeps them short and machine-independent;
        the absolute path is only used when a relative one cannot be computed
        (different Windows drive).
        """
        if not filepath:
            return None
        path = os.path.abspath(filepath)
        if self.line_base_dir:
            try:
                path = os.path.relpath(path, self.line_base_dir)
            except ValueError:  # different drive on Windows
                path = os.path.abspath(filepath)
        return str(path).replace("\\", "/")
    def _line_marker(self, node: Any, filepath: Optional[str] = None) -> str:
        """Builds a `#line N "file.pengu"` directive for `node`.

        Args:
            node: AST node carrying Lark position metadata, or a raw line number.
            filepath: Optional explicit source file; defaults to the module
                currently being translated.

        Returns:
            The directive, or an empty string when the line is unknown or
            markers are disabled.
        """
        if not self.emit_line_markers:
            return ""
        line = node if isinstance(node, int) else self._node_line(node)
        if line is None:
            return ""
        shown = self._display_path(filepath or self.current_source_file)
        if not shown:
            return f"#line {line}"
        escaped = shown.replace("\\", "\\\\").replace('"', '\\"')
        return f'#line {line} "{escaped}"'
    def _generated_c_reset(self) -> str:
        """Returns a `#line` marker that restores attribution to the generated C.

        Emitted between compiler-generated sections and `#line`-marked user code
        so that a diagnostic about *generated* code (entry wrapper, test runner,
        lambda trampolines) is not blamed on a random `.pengu` line.
        """
        if not self.emit_line_markers:
            return ""
        if self.bundle_display_path:
            return f'#line 1 "{self.bundle_display_path}"'
        return "#line 1"
