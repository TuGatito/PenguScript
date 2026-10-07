"""Global constants.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    AnyType,
    ArrayType,
    Optional,
    RangeConst,
    Token,
    Tree,
    Type,
)
from .ctype import (
    CTypeMapper,
    get_array_base_type,
    get_array_dims_and_base,
)

class ConstMixin:
    """Global constants."""

    def _format_const_val(self, val: Any, expected_type: Optional[Type] = None) -> str:
        """Formats evaluated constant Python value into C literal."""
        if isinstance(val, bool):
            return "true" if val else "false"
        elif isinstance(val, RangeConst):
            return f"((PenguRange){{ .start = {val.start}, .end = {val.end} }})"
        elif isinstance(val, int):
            return str(val)
        elif isinstance(val, float):
            return f"{val}f" if abs(val) < 1e7 else str(val)
        elif isinstance(val, str):
            if val.startswith("'") and val.endswith("'"):
                return val
            if val.startswith('"') and val.endswith('"'):
                cstr = val
            else:
                cstr = self._translate_string_lit(val, as_c_literal=True)
            if self._is_ref_char_type(expected_type):
                return cstr
            return f'pengu_string_from_cstr({cstr})'
        return str(val)
    def generate_global_constants(self) -> str:
        """Generates #define or const statements for global module constants."""
        if not self.consts:
            return ""

        emitted_lines = []
        for name, (c_type, val) in self.consts.items():
            if name in self.declaration_consts:
                continue
            c_name = self._c_ident(name)
            if val is not None:
                if isinstance(val, RangeConst):
                    emitted_lines.append(f"static const PenguRange {c_name} = {{ .start = {val.start}, .end = {val.end} }};")
                elif isinstance(val, str):
                    expr_node = self.const_nodes.get(name)
                    if expr_node is not None and isinstance(expr_node, Tree) and expr_node.data == "string_lit" and expr_node.children:
                        cstr = self._translate_string_lit(str(expr_node.children[0]), as_c_literal=True)
                    elif expr_node is not None and isinstance(expr_node, Token):
                        cstr = self._translate_string_lit(str(expr_node), as_c_literal=True)
                    else:
                        cstr = self._translate_string_lit(val, as_c_literal=True)
                    if self._is_ref_char_type(c_type):
                        emitted_lines.append(f'#define {c_name} {cstr}')
                    else:
                        emitted_lines.append(f'#define {c_name} pengu_string_from_cstr({cstr})')
                elif isinstance(val, bool):
                    emitted_lines.append(f'#define {c_name} {"true" if val else "false"}')
                else:
                    emitted_lines.append(f"#define {c_name} {val}")
            else:
                expr_node = self.const_nodes.get(name)
                if (c_type is None or isinstance(c_type, AnyType)) and self.symbols:
                    sym = self.symbols.lookup(name)
                    if sym and sym.type and not isinstance(sym.type, AnyType):
                        c_type = sym.type
                if c_type is not None and isinstance(c_type, ArrayType) and expr_node is not None:
                    expr_code = self._translate_expr(expr_node, expected_type=c_type)
                    dims, _ = get_array_dims_and_base(c_type)
                    dims_str = "".join(f"[{d}]" for d in dims)
                    base_t = get_array_base_type(c_type)
                    decl_arr = CTypeMapper.to_c_decl(base_t, f"{c_name}{dims_str}", const=True)
                    emitted_lines.append(f"static {decl_arr} = {expr_code};")
                elif c_type is not None and expr_node is not None:
                    expr_code = self._translate_expr(expr_node, expected_type=c_type)
                    decl_const = CTypeMapper.to_c_decl(c_type, c_name, const=True)
                    emitted_lines.append(f"static {decl_const} = {expr_code};")
                else:
                    t_str = CTypeMapper.to_c_type(c_type, const=True)
                    emitted_lines.append(f"{t_str} {c_name};")

        if not emitted_lines:
            return ""

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Global Constants",
            " * ------------------------------------------------------------------------- */",
        ] + emitted_lines + [""]
        return "\n".join(lines)
    def generate_constants(self) -> str:
        """Alias for generate_global_constants."""
        return self.generate_global_constants()
