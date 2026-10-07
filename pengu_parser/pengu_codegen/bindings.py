"""`if v as T is m` binding conditions and binding `if` statements.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    MaybeType,
    Optional,
    Tree,
    Type,
    ast_to_type,
)
from .ctype import (
    CTypeMapper,
)

class BindingMixin:
    """`if v as T is m` binding conditions and binding `if` statements."""

    def _binding_cond(self, node: Any) -> Optional[tuple]:
        """Returns the parts of a binding condition, or None.

        The tuple is ``(bind_name, decl_c, elem_c, expr_c, maybe_c, bind_type)``:
        the bound name, its C type, the C type used to cast the unwrapped value,
        the translated maybe expression, the C type of the maybe value and the
        declared :class:`Type`.
        """
        if not (isinstance(node, Tree)
                and node.data in ("if_cond_binding", "if_cond_binding_present")):
            return None

        bind_name = str(node.children[0])
        c_bind_name = self._c_ident(bind_name)
        # Inside a monomorphized generic weave/method the bound types are still
        # spelled with their type parameters: substitute the active map, or the
        # unwrapping cast would be emitted as 'void*' instead of the concrete
        # element type ('int32_t v = *(void* *)m.value' → wrong C).
        subst = getattr(self, "current_subst_map", None) or {}

        def _resolve(t: Optional[Type]) -> Optional[Type]:
            if t is None or not subst:
                return t
            try:
                return t.substitute(subst)
            except Exception:
                return t

        bind_type = _resolve(ast_to_type(
            node.children[1],
            self._lookup_type_fn,
        ))
        expr_node = getattr(node, "_pengu_bind_source", None) or node.children[2]
        if isinstance(expr_node, Tree) and expr_node.data == "is_present" and expr_node.children:
            # Redundant presence test: the binding implies it.
            expr_node = expr_node.children[0]
        elem_t = _resolve(getattr(node, "_pengu_bind_elem_type", None) or bind_type)
        maybe_t = _resolve(getattr(node, "_pengu_bind_maybe_type", None) or MaybeType(element=elem_t))
        decl_c = CTypeMapper.to_c_decl(bind_type, c_bind_name)
        elem_cast = CTypeMapper.to_c_decl(elem_t, "*")
        return (
            bind_name,
            decl_c,
            elem_cast,
            self._translate_expr(expr_node),
            CTypeMapper.to_c_type(maybe_t),
            bind_type,
        )
    def _translate_binding_if(self, node: Tree, binding: tuple) -> str:
        """Emits ``if name as T is <maybe>:`` as a scoped C block.

        The maybe value is evaluated once into a temporary; the branch body runs
        only when the value is present, and the bound name is declared inside it::

            {
                PenguMaybe _maybe_1 = (expr);
                if (pengu_maybe_is_present(&_maybe_1)) {
                    T name = (*(T*)_maybe_1.value);
                    <body>
                } else { <else> }
            }
        """
        bind_name, decl_c, elem_c, expr_c, maybe_c, bind_type = binding
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None

        ind = self.indent()
        inner = ind + "  "
        inner2 = inner + "  "
        tmp = self.get_temp_name("_maybe")

        saved_locals = dict(self.local_vars)
        self.local_vars[bind_name] = bind_type
        self.local_vars[self._c_ident(bind_name)] = bind_type
        self.indent_level += 2
        try:
            body_str = self._translate_nested_block(block_node)
            else_str = None
            if else_node is not None:
                else_str = self._translate_else_block(else_node)
        finally:
            self.indent_level -= 2
            self.local_vars = saved_locals

        parts = [
            f"{ind}{{",
            f"{inner}{maybe_c} {tmp} = {expr_c};",
            f"{inner}if (pengu_maybe_is_present(&{tmp})) {{",
            f"{inner2}{decl_c} = (*({elem_c}){tmp}.value);",
        ]
        if body_str:
            parts.append(body_str)
        if else_str is not None:
            parts.append(f"{inner}}} else {{")
            if else_str:
                parts.append(else_str)
            parts.append(f"{inner}}}")
        else:
            parts.append(f"{inner}}}")
        parts.append(f"{ind}}}")
        return "\n".join(parts)
    def _translate_binding_value_if(self, node: Tree, binding: tuple,
                                    expected_type: Optional[Type] = None) -> str:
        """Value-position ``if`` with a binding condition.

        The maybe value is evaluated once in the enclosing statement-expression,
        the branch body declares the bound name and the inner value-``if`` is
        guarded by the presence test::

            (__extension__(({
                PenguMaybe _maybe_1 = (expr);
                (__extension__(({ T _if_1; if (pengu_maybe_is_present(&_maybe_1)) {
                    T name = (*(T*)_maybe_1.value); ... _if_1 = <then>; } ...
                } _if_1; })));
            })))
        """
        bind_name, decl_c, elem_c, expr_c, maybe_c, bind_type = binding
        tmp = self.get_temp_name("_maybe")

        saved_locals = dict(self.local_vars)
        self.local_vars[bind_name] = bind_type
        self.local_vars[self._c_ident(bind_name)] = bind_type
        try:
            inner = self._translate_value_if(
                node,
                expected_type,
                cond_c=f"pengu_maybe_is_present(&{tmp})",
                then_prologue=f"{decl_c} = (*({elem_c}){tmp}.value);",
            )
        finally:
            self.local_vars = saved_locals

        return f"(__extension__(({{ {maybe_c} {tmp} = {expr_c}; {inner}; }})))"
