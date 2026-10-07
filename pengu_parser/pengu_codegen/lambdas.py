"""Registration and emission of the compiler-generated lambdas.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    List,
    Optional,
    Symbol,
    Tree,
    Type,
    TypeInferrer,
    ast_to_type,
)
from .ctype import (
    CTypeMapper,
)

class LambdaMixin:
    """Registration and emission of the compiler-generated lambdas."""

    def _register_lambdas_in(self, node: Any, src_file: Optional[str] = None) -> None:
        """Pre-scans a statement subtree and registers every lambda inside it.

        Nested lambdas are registered first (inner bodies may mention outer
        parameter names, but registration order only affects naming).
        """
        if not isinstance(node, Tree):
            return
        if node.data in ("lambda_expr", "lambda_no_params"):
            for c in node.children:
                self._register_lambdas_in(c, src_file=src_file)
            self._register_one_lambda(node, src_file=src_file)
            return
        for c in node.children:
            self._register_lambdas_in(c, src_file=src_file)
    def _register_one_lambda(self, node: Tree, src_file: Optional[str] = None) -> None:
        """Emits one top-level 'static' C function for a lambda expression.

        The body is translated in an isolated scope containing only the
        parameters (lambdas have no capture), which is why a plain C function is
        enough — no GCC nested functions are required.
        """
        self._lambda_counter += 1
        name = f"_pengu_lambda_{self._lambda_counter}"
        try:
            setattr(node, "_lambda_name", name)
        except Exception:
            pass

        if node.data == "lambda_no_params":
            pnames: List[str] = []
            ptypes: List[Type] = []
            body = node.children[0]
        else:
            plist = node.children[0]
            body = node.children[1]
            pnames, ptypes = [], []
            for p in plist.children:
                if not isinstance(p, Tree) or len(p.children) < 2:
                    continue
                pnames.append(str(p.children[0]))
                ptypes.append(ast_to_type(p.children[1], self._lookup_type_fn))

        # Return type: infer inside a scope holding only the parameters.  The
        # scope must be pushed/popped: defining them in the *current* scope (the
        # global one during code generation) leaked lambda parameter names into
        # every later lookup.
        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
        inferrer.symbols.push_scope(kind="lambda")
        try:
            for pn, pt in zip(pnames, ptypes):
                inferrer.symbols.define(Symbol(name=pn, type=pt, kind="param"))
            ret_t = inferrer.infer(body)
        finally:
            inferrer.symbols.pop_scope()

        # Translate the body in the same isolated scope.
        saved_locals = dict(self.local_vars)
        saved_ind = self.indent_level
        self.local_vars = dict(zip(pnames, ptypes))
        self.indent_level = 1
        try:
            body_c = self._translate_expr(body, expected_type=ret_t)
        finally:
            self.local_vars = saved_locals
            self.indent_level = saved_ind

        ret_c = CTypeMapper.to_c_type(ret_t)
        decl = ", ".join(CTypeMapper.to_c_decl(pt, pn) for pn, pt in zip(pnames, ptypes)) or "void"
        l_line = self._node_line(node) or 0
        l_file = self._display_path(src_file) or ""
        push_call = f'pengu_frame_push("{name}", "{l_file}", {l_line});'
        pop_call = "pengu_frame_pop();"
        if ret_c == "void":
            self.lambdas.append(f"static void {name}({decl}) {{ {push_call} {body_c}; {pop_call} }}")
        else:
            fn_sig = CTypeMapper.to_c_decl(ret_t, f"{name}({decl})")
            lret_decl = CTypeMapper.to_c_decl(ret_t, "_lret")
            self.lambdas.append(f"static {fn_sig} {{ {push_call} {lret_decl} = {body_c}; {pop_call} return _lret; }}")
    def generate_lambdas(self) -> str:
        """Emits the top-level 'static' functions generated for lambdas."""
        if not self.lambdas:
            return ""
        lines = ["/* --- Lambdas --- */"]
        lines.extend(self.lambdas)
        lines.append("")
        return "\n".join(lines)
