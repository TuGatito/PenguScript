"""Value-position blocks: `do:`, value `if`/`unless` and implicit returns.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    AnyType,
    EchoType,
    FnType,
    List,
    ListType,
    Optional,
    RefType,
    RuneType,
    SIMPLE_STMT_ALIASES,
    Symbol,
    Token,
    Tree,
    Tuple,
    Type,
    TypeInferrer,
    ast_to_type,
)
from .ctype import (
    CTypeMapper,
)

class ValueIfMixin:
    """Value-position blocks: `do:`, value `if`/`unless` and implicit returns."""

    def _value_branch(self, stmts: List[Tree], expected_type: Optional[Type] = None,
                      val_node_out: Optional[list] = None):
        """C code and value expression of a value-position statement list.

        Returns ``(statement_parts, value_expr)``. The last statement supplies
        the block value: an expression statement, a trailing value-position
        ``if``/``unless`` or a collecting loop, or nothing for a void branch.
        ``val_node_out`` (when given) receives the AST node of that expression so
        callers can reason about ownership.
        """
        parts: List[str] = []
        val: Optional[str] = None
        n = len(stmts)
        for i, st in enumerate(stmts):
            inner = st
            while isinstance(inner, Tree) and inner.data == "stmt" and inner.children:
                inner = inner.children[0]
            if i == n - 1 and isinstance(inner, Tree):
                inner_vt = getattr(inner, "_pengu_value_type", None)
                if (inner.data in ("if_stmt", "unless_stmt") and inner_vt is not None):
                    val = self._translate_expr(inner, expected_type)
                    if val_node_out is not None:
                        val_node_out.append(inner)
                    continue
                if inner.data in ("while_stmt", "for_range_stmt", "for_in_stmt") and isinstance(inner_vt, ListType):
                    val = self._translate_expr(inner, expected_type)
                    if val_node_out is not None:
                        val_node_out.append(inner)
                    continue
                if inner.data == "expr_stmt" and inner.children:
                    val = self._translate_expr(inner.children[0], expected_type)
                    if val_node_out is not None:
                        val_node_out.append(inner.children[0])
                    continue
                if (inner.data == "simple_stmt" and len(inner.children) == 1
                        and isinstance(inner.children[0], (Tree, Token))):
                    val = self._translate_expr(inner.children[0], expected_type)
                    if val_node_out is not None:
                        val_node_out.append(inner.children[0])
                    continue
            code = self._translate_stmt(st)
            if code:
                parts.append(code.rstrip())
        return parts, val
    def _translate_value_block(
        self, stmts: List[Any], expected_type: Optional[Type] = None
    ) -> Tuple[List[str], Optional[str]]:
        saved_locals = dict(self.local_vars)
        try:
            parts, val = self._value_branch(stmts, expected_type)
            if val is not None and self._is_void_type(expected_type):
                # A void block has no value: 'void _val_N = f();' is invalid C, so
                # the expression is emitted as a plain statement (side effects
                # only) and the block yields nothing.
                parts.append(f"{self.indent()}{val};")
                val = None
            elif val is not None:
                tmp_val = self.get_temp_name("_val")
                if expected_type is not None and not isinstance(expected_type, AnyType):
                    decl = CTypeMapper.to_c_decl(expected_type, tmp_val)
                else:
                    decl = f"__auto_type {tmp_val}"
                parts.append(f"{self.indent()}{decl} = {val};")
                val = tmp_val
            return parts, val
        finally:
            self.local_vars = saved_locals
    def _translate_value_if(self, node: Tree, expected_type: Optional[Type] = None,
                            negate: bool = False,
                            cond_c: Optional[str] = None,
                            then_prologue: Optional[str] = None) -> str:
        """GNU statement-expression for an 'if'/'unless' used as a value.

        Every branch's last statement supplies the branch value; a trailing
        value-position 'if'/'unless' nests recursively, so both
        ``else if <cond>:`` and an ``else:`` block containing a nested block
        work. ``negate`` renders the condition as ``unless`` semantics.
        ``cond_c`` overrides the rendered condition and ``then_prologue`` is
        emitted at the top of the then-branch (used to declare a bound name).
        """
        if cond_c is None:
            cond_c = self._translate_if_cond(node.children[0])
        if negate:
            cond_c = f"!({cond_c})"
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None
        v_t = getattr(node, "_pengu_value_type", None) or expected_type

        saved_locals = dict(self.local_vars)
        try:
            then_parts, then_val = self._translate_value_block(list(block_node.children), v_t)
            if then_prologue:
                then_parts.insert(0, f"{self.indent()}  {then_prologue}")
            then_body = "\n".join(then_parts)

            else_parts: List[str] = []
            else_val: Optional[str] = None
            nested_else: Optional[str] = None
            if isinstance(else_node, Tree) and else_node.children:
                ech = [c for c in else_node.children if isinstance(c, Tree)]
                if len(ech) == 1 and ech[0].data in ("if_stmt", "unless_stmt"):
                    # 'else if <cond>:' — nested value block.
                    nested_else = self._translate_expr(ech[0], v_t)
                else:
                    else_parts, else_val = self._translate_value_block(ech, v_t)
            else_body = "\n".join(else_parts)

            is_void = v_t is None or str(getattr(v_t, "name", "")) == "void"
            if is_void:
                # Side effects only: any branch value is evaluated and dropped.
                if not self.use_gnu_extensions:
                    stmts = [f"if ({cond_c}) {{"]
                    if then_body:
                        stmts.extend(then_body.splitlines())
                    if then_val:
                        stmts.append(f"{then_val};")
                    if nested_else is not None:
                        stmts += ["} else {", f"{nested_else};", "}"]
                    elif else_body or else_val:
                        stmts.append("} else {")
                        if else_body:
                            stmts.extend(else_body.splitlines())
                        if else_val:
                            stmts.append(f"{else_val};")
                        stmts.append("}")
                    else:
                        stmts.append("}")
                    for s in stmts:
                        self._hoist(s)
                    return "((void)0)"
                then_full = "\n".join(
                    p for p in (then_body, f"{then_val};" if then_val else "") if p
                )
                res = f"(__extension__(({{ if ({cond_c}) {{\n{then_full}\n}}"
                if nested_else is not None:
                    res += f" else {{\n{nested_else};\n}}"
                elif else_body or else_val:
                    else_full = "\n".join(
                        p for p in (else_body, f"{else_val};" if else_val else "") if p
                    )
                    res += f" else {{\n{else_full}\n}}"
                res += "\n})))"
                return res

            c_t = CTypeMapper.to_c_type(v_t)
            tmp = self.get_temp_name("_if")
            decl_tmp = CTypeMapper.to_c_decl(v_t, tmp)
            if not self.use_gnu_extensions:
                stmts = [f"{decl_tmp};", f"if ({cond_c}) {{"]
                if then_body:
                    stmts.extend(then_body.splitlines())
                if then_val:
                    stmts.append(f"  {tmp} = {then_val};")
                if nested_else is not None:
                    stmts += ["} else {", f"  {tmp} = {nested_else};", "}"]
                elif else_body or else_val:
                    stmts.append("} else {")
                    if else_body:
                        stmts.extend(else_body.splitlines())
                    if else_val:
                        stmts.append(f"  {tmp} = {else_val};")
                    stmts.append("}")
                else:
                    default = "NULL" if isinstance(v_t, (FnType, RefType)) else f"({c_t}){{0}}"
                    stmts.append(f"}} else {{ {tmp} = {default}; }}")
                return self._block_expr(stmts, tmp)
            res = (
                f"(__extension__(({{ {decl_tmp}; if ({cond_c}) {{\n{then_body}\n"
                + (f"  {tmp} = {then_val};\n" if then_val else "")
                + "}"
            )
            if nested_else is not None:
                res += f" else {{\n  {tmp} = {nested_else};\n}}"
            elif else_body or else_val:
                res += (
                    f" else {{\n{else_body}\n"
                    + (f"  {tmp} = {else_val};\n" if else_val else "")
                    + "}"
                )
            else:
                if isinstance(v_t, (FnType, RefType)):
                    res += f" else {{ {tmp} = NULL; }}"
                else:
                    res += f" else {{ {tmp} = ({c_t}){{0}}; }}"
            res += f" {tmp}; }})))"
            return res
        finally:
            self.local_vars = saved_locals
    @staticmethod
    def _block_last_value_node(stmts: List[Any]) -> Any:
        """Value expression of a value-position statement list, if any."""
        if not stmts:
            return None
        last = stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt", "block") and last.children:
            nxt = last.children[-1]
            if nxt is last:
                break
            last = nxt
        if not isinstance(last, Tree):
            return None
        if last.data == "expr_stmt" and last.children:
            return last.children[0]
        if (last.data in ("if_stmt", "unless_stmt", "do_expr")
                and getattr(last, "_pengu_value_type", None) is not None):
            return last
        return None
    @staticmethod
    def _block_ends_with_jump(node: Any) -> bool:
        if not isinstance(node, Tree):
            return False
        stmts = node.children if node.data == "block" else [node]
        if not stmts:
            return False
        last = stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt") and last.children:
            last = last.children[0]
        if isinstance(last, Tree):
            data = SIMPLE_STMT_ALIASES.get(last.data, last.data)
            if data in ("return_stmt", "break_stmt", "continue_stmt"):
                return True
        return False
    @staticmethod
    def _stmts_end_with_jump(stmts: List[Tree]) -> bool:
        if not stmts:
            return False
        last = stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt") and last.children:
            last = last.children[0]
        if isinstance(last, Tree):
            data = SIMPLE_STMT_ALIASES.get(last.data, last.data)
            if data in ("return_stmt", "break_stmt", "continue_stmt"):
                return True
        return False
    def _implicit_return_expr(self, stmts: List[Any],
                              return_type: Optional[Type]) -> Optional[Any]:
        """Tail expression of a weave body that becomes its implicit return.

        Implements the documented rule (guide §4.11): "if the last statement of
        the weave is an expression, do not write `return`".  Returns the
        expression node when the body ends in a value-position expression and the
        declared return type is non-void and compatible; ``None`` keeps the
        previous behaviour (the emitter then appends nothing extra).

        Returning the node (instead of post-processing the emitted C) lets the
        caller route it through the real ``return_stmt`` path, so ``defer``,
        ``errdefer`` and scope auto-banishes run exactly once and the returned
        value is excluded from the banish set.
        """
        if not stmts or return_type is None:
            return None
        try:
            if CTypeMapper.to_c_type(return_type) == "void":
                return None
        except Exception:
            return None
        last = stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt") and last.children:
            last = last.children[-1]
        if not (isinstance(last, Tree) and last.data == "expr_stmt" and last.children):
            return None
        expr = last.children[0]
        # A bare call statement may be void (`calling spark.println with …`):
        # leave it alone so the author keeps writing `return` when they want the
        # callee's value.  Every other expression form that can appear in an
        # `expr_stmt` yields a value, so it is the implicit result.
        inner = expr
        while (isinstance(inner, Tree) and inner.data in ("paren_expr", "value_expr", "expr")
               and len(inner.children) == 1):
            inner = inner.children[0]
        if isinstance(inner, Tree) and inner.data == "calling_expr":
            return None
        return expr
    def _is_string_expr(self, n: Any) -> bool:
        """Checks if an AST expression node evaluates to a PenguString."""
        if n is None:
            return False
        if isinstance(n, Token):
            return n.type in ("STRING", "TRIPLE_STRING", "RAW_STRING", "RAW_TRIPLE_STRING")
        if isinstance(n, Tree):
            rule = n.data
            if rule == "string_lit":
                return True
            if rule == "var_ref":
                vt = self._lookup_var_type(str(n.children[0]))
                return vt is not None and vt.is_string()
            if rule == "self_arrow":
                field_name = str(n.children[0])
                if self.current_enchanted_type and isinstance(self.current_enchanted_type, (RuneType, EchoType)):
                    ft = self.current_enchanted_type.fields.get(field_name)
                    return ft is not None and ft.is_string()
                return False
            if rule == "field_access":
                target_node = n.children[0]
                field_name = str(n.children[1])
                target_type = None
                if isinstance(target_node, Tree) and target_node.data == "var_ref":
                    target_type = self._lookup_var_type(str(target_node.children[0]))
                elif isinstance(target_node, Tree) and target_node.data == "self_ref":
                    target_type = self.current_enchanted_type
                if target_type and isinstance(target_type, (RuneType, EchoType)):
                    ft = target_type.fields.get(field_name)
                    return ft is not None and ft.is_string()
                return False
            if rule == "cast_expr":
                t = ast_to_type(n.children[1], lambda name: self.symbols.lookup(name).type if self.symbols and self.symbols.lookup(name) else None)
                return t is not None and t.is_string()
            if rule == "add":
                return self._is_string_expr(n.children[0]) or self._is_string_expr(n.children[1])
            if rule == "calling_expr":
                fn_node = n.children[0]
                fn_name = ""
                if isinstance(fn_node, Token):
                    fn_name = str(fn_node)
                elif isinstance(fn_node, Tree):
                    if fn_node.data == "var_ref":
                        fn_name = str(fn_node.children[0])
                    elif fn_node.data == "field_access":
                        obj_node = fn_node.children[0]
                        m_name = str(fn_node.children[1])
                        if isinstance(obj_node, Tree) and obj_node.data == "var_ref":
                            obj_type = self._lookup_var_type(str(obj_node.children[0]))
                            if obj_type and hasattr(obj_type, "name"):
                                fn_name = f"{obj_type.name}_{m_name}"
                        elif isinstance(obj_node, Tree) and obj_node.data == "self_ref":
                            if self.current_enchanted_type and hasattr(self.current_enchanted_type, "name"):
                                fn_name = f"{self.current_enchanted_type.name}_{m_name}"
                if fn_name:
                    sym = self.symbols.lookup(fn_name) if self.symbols else None
                    if sym and isinstance(sym.type, FnType) and sym.type.return_type:
                        return sym.type.return_type.is_string()
                    if fn_name in self.fn_info:
                        ret_t = self.fn_info[fn_name].get("return_type")
                        return ret_t is not None and ret_t.is_string()
            if rule == "if_expr":
                return self._is_string_expr(n.children[1]) or self._is_string_expr(n.children[2])

            try:
                inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                for lv_k, lv_v in self.local_vars.items():
                    inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                if self.current_enchanted_type is not None:
                    self_t = self.current_enchanted_type if isinstance(self.current_enchanted_type, RefType) else RefType(self.current_enchanted_type)
                    inferrer.symbols.define(Symbol(name="self", type=self_t, kind="var"))
                inferred_t = inferrer.infer(n)
                if inferred_t is not None and inferred_t.is_string():
                    return True
            except Exception:
                pass
        return False
