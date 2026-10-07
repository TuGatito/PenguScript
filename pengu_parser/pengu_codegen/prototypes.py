"""Function prototypes, attributes and the function definitions.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    RefType,
    Tree,
)
from .ctype import (
    CTypeMapper,
)

class ProtoMixin:
    """Function prototypes, attributes and the function definitions."""

    def generate_function_prototypes(self) -> str:
        """Generates all forward function prototypes."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Prototypes",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            c_name = w["c_name"]
            ret_str = CTypeMapper.to_c_type(w["return_type"])
            param_strs = []

            # Self parameter for enchanting methods (only if not ritual)
            if w["enchanted_type"] is not None and not w.get("is_ritual", False):
                self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
                param_strs.append(f"{self_t_str}* self")

            for p_info in w["params"]:
                p_name, p_type = p_info[0], p_info[1]
                param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name)))

            params_formatted = ", ".join(param_strs) if param_strs else "void"
            inline_pfx = self._attributes_prefix(w)
            fn_actual_name = "pengu_main" if c_name == "main" else c_name
            decl = CTypeMapper.to_c_decl(w["return_type"], f"{fn_actual_name}({params_formatted})")
            lines.append(f"{inline_pfx}{decl};")

        lines.append("")
        return "\n".join(lines)
    def _attributes_prefix(self, w: dict) -> str:
        """C prefix and attribute modifiers for a weave, per target compiler.

        GNU/Clang/TCC use ``__attribute__``; MSVC uses ``__declspec`` (and
        ``__forceinline``), since it does not understand GNU attributes.
        """
        return self._format_attributes(w, self.target_compiler == "msvc")
    @staticmethod
    def _format_attributes(w: dict, is_msvc: bool = False) -> str:
        attrs = w.get("attributes", {})
        is_inline = w.get("is_inline", False) or ("inline" in attrs)
        auto_inline = w.get("auto_inline", False)

        parts = []
        c_attrs = []

        if is_inline:
            if is_msvc and not auto_inline:
                parts.append("static __forceinline")
            else:
                parts.append("static inline")
                if not auto_inline:
                    c_attrs.append("always_inline")

        if "cold" in attrs and not is_msvc:
            # MSVC has no direct equivalent of __attribute__((cold)).
            c_attrs.append("cold")
        if "deprecated" in attrs:
            reason = attrs["deprecated"][0] if attrs["deprecated"] else None
            if reason:
                clean_reason = str(reason).replace('"', '\\"')
                dep = f'deprecated("{clean_reason}")'
            else:
                dep = "deprecated"
            if is_msvc:
                parts.append(f"__declspec({dep})")
            else:
                c_attrs.append(dep)

        if c_attrs:
            parts.append(f"__attribute__(({', '.join(c_attrs)}))")

        if not parts:
            return ""
        return " ".join(parts) + " "
    @staticmethod
    def _inline_prefix(w: dict) -> str:
        """GNU attribute prefix for a weave (kept for backwards compatibility)."""
        # Local import: the mixin modules must not import the assembled class at
        # module level, or `main` would be imported while it is still building.
        from .main import PenguCodegen
        return PenguCodegen._format_attributes(w, is_msvc=False)
    def generate_function_definitions(self) -> str:
        """Generates function implementation bodies in topological module order."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Definitions",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            self._apply_main_flag(w.get("filepath"))
            self.current_source_file = w.get("filepath")
            c_name = w["c_name"]
            ret_str = CTypeMapper.to_c_type(w["return_type"])
            param_strs = []

            if w["enchanted_type"] is not None and not w.get("is_ritual", False):
                self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
                param_strs.append(f"{self_t_str}* self")

            for p_info in w["params"]:
                p_name, p_type = p_info[0], p_info[1]
                # restrict is opt-in: see CTypeMapper.to_c_decl
                param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name)))

            params_formatted = ", ".join(param_strs) if param_strs else "void"
            inline_pfx = self._attributes_prefix(w)
            fn_actual_name = "pengu_main" if c_name == "main" else c_name
            decl = CTypeMapper.to_c_decl(w["return_type"], f"{fn_actual_name}({params_formatted})")

            marker = self._line_marker(w.get("line"), w.get("filepath"))
            if marker:
                lines.append(marker)
            lines.append(f"{inline_pfx}{decl} {{")
            self.indent_level += 1
            push_path = self._display_path(w.get("filepath")) or ""
            push_line = w.get("line") or 0
            lines.append(f'{self.indent()}pengu_frame_push("{fn_actual_name}", "{push_path}", {push_line});')
            self.current_function = fn_actual_name
            self.current_return_type = w["return_type"]
            self.current_enchanted_type = w.get("enchanted_type")
            self.current_subst_map = w.get("subst_map", {})
            self.local_vars = {}
            if w["enchanted_type"] is not None and not w.get("is_ritual", False):
                self.local_vars["self"] = RefType(w["enchanted_type"])
            for p_info in w["params"]:
                self.local_vars[p_info[0]] = p_info[1]

            self.defer_stack.append([])
            self.errdefer_stack.append([])

            # Implicit return (guide §4.11): when the body's last statement is a
            # value expression and the weave returns a non-void type, that value
            # is the result.  Translating it as a real ``return_stmt`` gives the
            # same cleanup handling as an explicit ``return``.
            body_stmts = w["body_stmts"]
            tail_expr = self._implicit_return_expr(body_stmts, w.get("return_type"))
            if tail_expr is not None:
                body_code = self._translate_block(body_stmts[:-1])
                lines.append(body_code)
                lines.append(self._translate_stmt(Tree("return_stmt", [tail_expr],
                                                       meta=getattr(tail_expr, "meta", None))))
            else:
                body_code = self._translate_block(body_stmts)
                lines.append(body_code)

            # Emit any remaining top-level defers before function exit.
            active_defers = self.defer_stack.pop() if self.defer_stack else []
            if self.errdefer_stack:
                self.errdefer_stack.pop()
            # With a synthesized implicit return the deferred cleanup is already
            # emitted *inside* the return statement; emitting it again here would
            # double-free.
            if tail_expr is None and not self._stmts_end_with_jump(w["body_stmts"]):
                if active_defers:
                    lines.append(f"{self.indent()}/* Deferred cleanup */")
                    for d in reversed(active_defers):
                        lines.append(self._format_defer_cleanup(d, self.indent()))

            lines.append(f"{self.indent()}pengu_frame_pop();")
            self.indent_level -= 1
            lines.append("}")
            lines.append("")

        return "\n".join(lines)
