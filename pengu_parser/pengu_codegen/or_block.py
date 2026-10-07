"""`or:`, `or else`, `or return` and the result constructors.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    Any,
    AnyType,
    FLOAT_TYPE,
    FnType,
    INT_TYPE,
    List,
    MaybeType,
    Optional,
    RefType,
    ResultType,
    STRING_TYPE,
    SemanticError,
    Tree,
    Type,
    VOID_TYPE,
)
from .ctype import (
    CTypeMapper,
)

class OrBlockMixin:
    """`or:`, `or else`, `or return` and the result constructors."""

    def _translate_or_block(
        self,
        left_op: Any,
        block_stmts: List[Tree],
        target_type: Optional[Type] = None,
        target_decl: Optional[str] = None,
        target_ident: Optional[str] = None,
    ) -> str:
        """Translates an 'or:' error-handling block into C99 statements or statement-expression."""
        ind = self.indent()
        tmp_res = self.get_temp_name("_res")
        left_c = self._translate_expr(left_op)

        left_op_t = None
        if hasattr(self, "symbols"):
            try:
                left_op_t = self._infer_node_type(left_op)
            except Exception:
                pass

        if left_op_t is None:
            raise SemanticError(
                "Compiler invariant violated: 'or:' reached codegen with an "
                "uninferable operand; the checker should have rejected this.",
                code="E0005",
                help="This is a compiler bug; please report the minimal case.",
            )
        if isinstance(left_op_t, AnyType):
            raise SemanticError(
                "'or:' reached codegen with 'any' operand type; the checker must "
                "resolve the operand type before this point",
                code="E0005",
                help="This is a compiler bug; annotate the operand with 'as maybe T' "
                     "or 'as result of T to E'.",
            )
        if not isinstance(left_op_t, (ResultType, MaybeType)):
            raise SemanticError(
                f"'or:' requires a 'maybe T' or 'result of T to E' operand, "
                f"got '{left_op_t}'",
                code="E0005",
                help="The checker guarantees the operand type; seeing this is an internal error.",
            )

        if target_type is None:
            if isinstance(left_op_t, ResultType):
                target_type = left_op_t.ok_type
            elif isinstance(left_op_t, MaybeType):
                target_type = left_op_t.element
            else:
                target_type = left_op_t

        is_maybe = isinstance(left_op_t, MaybeType)
        if is_maybe:
            err_t = STRING_TYPE
            err_decl = "PenguString error"
            err_expr = 'pengu_string_from_cstr("none")'
        else:
            err_t = left_op_t.err_type
            err_decl = CTypeMapper.to_c_decl(err_t, "error")
            err_ptr_cast = CTypeMapper.to_c_decl(err_t, "*")
            err_expr = f"(*(({err_ptr_cast}){tmp_res}.err_val))"

        saved_locals = dict(self.local_vars)
        self.local_vars["error"] = err_t
        try:
            self.indent_level += 1
            inner_body = [self._translate_stmt(bs) for bs in block_stmts]
            self.indent_level -= 1
        finally:
            self.local_vars = saved_locals

        block_c = "\n".join(inner_body)

        cast_t = CTypeMapper.to_c_type(target_type) if target_type is not None else "void*"
        if cast_t == "void":
            cast_t = "int32_t"

        ptr_cast = CTypeMapper.to_c_decl(target_type, "*") if target_type is not None else "void**"

        container_c = "PenguMaybe" if is_maybe else "PenguResult"
        is_fail = f"!pengu_maybe_is_present(&{tmp_res})" if is_maybe else f"!pengu_result_is_ok(&{tmp_res})"
        ok_read = f"(*(({ptr_cast}){tmp_res}.value))" if is_maybe else f"(*(({ptr_cast}){tmp_res}.ok_val))"

        # A 'maybe T' box built by 'some' (or handed over by a call) is owned by
        # this expression: the payload is *moved* into the result and only the
        # box allocation is released here.  A direct reference to a local must
        # not be freed (the local still owns its box); a result box may belong to
        # the C side, so it is left alone.  Look through grouping parentheses:
        # '(some s) or:' arrives as paren_expr(some_expr(...)) and used to keep
        # the box (and its payload) allocated forever.
        own_box_op = left_op
        while (isinstance(own_box_op, Tree)
               and own_box_op.data in ("paren_expr", "value_expr", "expr")
               and len(own_box_op.children) == 1):
            own_box_op = own_box_op.children[0]
        own_box = (is_maybe and isinstance(own_box_op, Tree)
                   and own_box_op.data in ("some_expr", "maybe_none", "calling_expr",
                                           "or_block", "or_else", "if_stmt", "do_expr"))
        if own_box:
            # The payload is *moved* into the result by the assignment above
            # ('x = *(PenguString*)box.value' shares the buffer), so only the
            # box allocation may be released here: releasing the payload would
            # free memory the result now owns.  The result's own auto-banish is
            # responsible for the moved value.
            ok_free = (f"  free({tmp_res}.value); {tmp_res}.value = NULL;\n"
                       f"  {tmp_res}.is_present = false;\n")
            fail_free = f"  pengu_banish_maybe(&{tmp_res});\n"
        else:
            ok_free = fail_free = ""

        if target_decl is not None:
            if target_ident is None:
                raise SemanticError(
                    "Compiler invariant violated: target_ident must be provided when target_decl is specified in _translate_or_block",
                    code="E0000"
                )
            ident = target_ident
            init_c = "NULL" if isinstance(target_type, (FnType, RefType)) else f"({cast_t}){{0}}"
            return (
                f"{ind}{container_c} {tmp_res} = {left_c};\n"
                f"{ind}{target_decl} = {init_c};\n"
                f"{ind}if ({is_fail}) {{\n"
                f"{ind}  {err_decl} = {err_expr};\n"
                f"{fail_free}"
                f"{block_c}\n"
                f"{ind}}} else {{\n"
                f"{ind}  {ident} = {ok_read};\n"
                f"{ok_free}"
                f"{ind}}}"
            )
        else:
            tmp_val = self.get_temp_name("_val")
            val_decl = CTypeMapper.to_c_decl(target_type, tmp_val) if target_type is not None else f"{cast_t} {tmp_val}"
            init_c = "NULL" if isinstance(target_type, (FnType, RefType)) else f"({cast_t}){{0}}"
            return (
                f"(__extension__(({{ {container_c} {tmp_res} = {left_c};\n"
                f"  {val_decl} = {init_c};\n"
                f"  if ({is_fail}) {{\n"
                f"    {err_decl} = {err_expr};\n"
                f"{fail_free}"
                f"{block_c}\n"
                f"  }} else {{\n"
                f"    {tmp_val} = {ok_read};\n"
                f"{ok_free}"
                f"  }}\n"
                f"  {tmp_val}; }}))"
            )
    def _translate_unwrap_expr(self, rule: str, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates 'try', 'or else' and 'or return' unwrapping expressions.

        The grammar accepts these operators on any expression, but they only
        make sense on a ``maybe T`` or ``result of T to E`` operand. Type
        checking already guarantees the operand type (and, for 'try', that the
        enclosing function returns a compatible maybe/result container); this
        method emits the C unwrap using a GNU statement-expression so the
        success value is produced lazily and the failure path can ``return``
        from the enclosing function.
        """
        left_node = node.children[0]
        left_c = self._translate_expr(left_node)
        left_t = self._infer_node_type(left_node)

        if isinstance(left_t, MaybeType):
            container_c = "PenguMaybe"
            ok_c = CTypeMapper.to_c_type(left_t.element)
        elif isinstance(left_t, ResultType):
            container_c = "PenguResult"
            ok_c = CTypeMapper.to_c_type(left_t.ok_type)
        else:
            got = str(left_t) if left_t is not None else "unknown"
            raise SemanticError(
                f"'{rule}' requires a maybe T or result of T to E operand, got '{got}'",
                code="E0005",
            )
        tmp = self.get_temp_name("_unwrap")

        if rule == "or_else":
            right_node = node.children[1]
            right_c = self._translate_expr(right_node)
            if isinstance(left_t, MaybeType):
                is_ok = f"pengu_maybe_is_present(&{tmp})"
                ok_read = f"(*(({ok_c}*){tmp}.value))"
            else:
                is_ok = f"pengu_result_is_ok(&{tmp})"
                ok_read = f"(*(({ok_c}*){tmp}.ok_val))"
            if not self.use_gnu_extensions:
                self._hoist(f"{container_c} {tmp} = {left_c};")
                return f"(({is_ok}) ? ({ok_read}) : (({ok_c})({right_c})))"
            return (
                f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
                f"({is_ok}) ? ({ok_read}) : (({ok_c})({right_c})); }})))"
            )

        if isinstance(left_t, ResultType):
            is_fail = f"!pengu_result_is_ok(&{tmp})"
            ok_read = f"(*(({ok_c}*){tmp}.ok_val))"
        else:
            is_fail = f"!pengu_maybe_is_present(&{tmp})"
            ok_read = f"(*(({ok_c}*){tmp}.value))"

        if rule == "or_return":
            right_node = node.children[1]
            right_c = self._translate_expr(right_node,
                                           expected_type=self.current_return_type)
            is_err_ret = False
            if isinstance(right_node, Tree) and right_node.data in ("err_expr", "error_lit"):
                is_err_ret = True
            cleanup_stmts = self._get_return_cleanup_lines(is_err_ret=is_err_ret)
            if cleanup_stmts:
                cleanup_code = " " + " ".join(cleanup_stmts)
                tmp_ret = self.get_temp_name("_ret")
                ret_decl = (
                    f"{CTypeMapper.to_c_decl(self.current_return_type, tmp_ret)} = ({right_c});"
                    if self.current_return_type is not None and self.current_return_type != VOID_TYPE and getattr(self.current_return_type, "name", "") != "void"
                    else f"__typeof__(({right_c})) {tmp_ret} = ({right_c});"
                )
                if not self.use_gnu_extensions:
                    self._hoist(f"{container_c} {tmp} = {left_c};")
                    self._hoist(f"if ({is_fail}) {{ {ret_decl}{cleanup_code} pengu_frame_pop(); return {tmp_ret}; }}")
                    return ok_read
                return (
                    f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
                    f"if ({is_fail}) {{ {ret_decl}{cleanup_code} pengu_frame_pop(); return {tmp_ret}; }} {ok_read}; }})))"
                )
            if not self.use_gnu_extensions:
                self._hoist(f"{container_c} {tmp} = {left_c};")
                self._hoist(f"if ({is_fail}) {{ pengu_frame_pop(); return ({right_c}); }}")
                return ok_read
            return (
                f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
                f"if ({is_fail}) {{ pengu_frame_pop(); return ({right_c}); }} {ok_read}; }})))"
            )

        # rule == "try_expr": on failure propagate to the enclosing function.
        fn_ret = self.current_return_type
        if isinstance(left_t, ResultType):
            err_ok = isinstance(fn_ret, AnyType) or (
                isinstance(fn_ret, ResultType)
                and left_t.err_type.is_compatible(fn_ret.err_type))
            if not err_ok:
                raise SemanticError(
                    f"'try' over 'result of T to E' requires the enclosing "
                    f"function to return a compatible result type (error type "
                    f"'{left_t.err_type}'), not "
                    f"'{fn_ret if fn_ret is not None else 'void'}'",
                    code="E0045",
                )
            cleanup_stmts = self._get_return_cleanup_lines(is_err_ret=True)
            cleanup_code = (" " + " ".join(cleanup_stmts)) if cleanup_stmts else ""
            fail_stmt = f"{{ {cleanup_code} pengu_frame_pop(); return {tmp}; }}"
        else:
            if not isinstance(fn_ret, (MaybeType, AnyType)):
                raise SemanticError(
                    f"'try' over 'maybe T' requires the enclosing function to "
                    f"return 'maybe T', not "
                    f"'{fn_ret if fn_ret is not None else 'void'}'",
                    code="E0045",
                )
            cleanup_stmts = self._get_return_cleanup_lines(is_err_ret=False)
            cleanup_code = (" " + " ".join(cleanup_stmts)) if cleanup_stmts else ""
            fail_stmt = f"{{ {cleanup_code} pengu_frame_pop(); return pengu_maybe_none(); }}"
        if not self.use_gnu_extensions:
            self._hoist(f"{container_c} {tmp} = {left_c};")
            self._hoist(f"if ({is_fail}) {fail_stmt}")
            return ok_read
        return (
            f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
            f"if ({is_fail}) {fail_stmt} {ok_read}; }})))"
        )
    def _result_ctor_name(self, target_node: Any) -> Optional[str]:
        """Returns ``'ok_of'``/``'err_of'`` when a call target is a result ctor.

        Accepted spellings: bare (``calling ok_of with v``) and qualified
        (``calling oracle.ok_of with v``) — the way ``std.oracle`` documents it.
        These are compiler intrinsics (no Pengu body to resolve), which is why
        the check runs before normal call resolution: ``ok``/``err`` cannot be
        grammar keywords without shadowing the many identifiers named ``ok`` in
        the wild.
        """
        if not isinstance(target_node, Tree) or target_node.data != "normal_target":
            return None
        if not target_node.children:
            return None
        last = target_node.children[-1]
        if isinstance(last, Tree) and last.data in ("dot_access", "arrow_access") and last.children:
            name = str(last.children[0])
            if name in ("ok_of", "err_of") and str(target_node.children[0]) == "oracle":
                return name
            return None
        if len(target_node.children) == 1:
            name = str(target_node.children[0])
            if name in ("ok_of", "err_of"):
                return name
        return None
    def _first_call_arg(self, node: Any) -> Optional[Any]:
        """First argument expression of a ``calling_expr`` node, or None."""
        for ch in node.children[1:]:
            if isinstance(ch, Tree) and ch.data == "arg_list":
                for arg in ch.children:
                    if isinstance(arg, Tree):
                        if arg.data == "pos_arg" and arg.children:
                            return arg.children[0]
                        if arg.data == "named_arg" and len(arg.children) >= 2:
                            return arg.children[1]
                    elif arg is not None:
                        return arg
        return None
    def _translate_result_ctor(self, arg_node: Any, is_ok: bool) -> str:
        """Lower ``ok_of v`` / ``err_of e`` to a heap-boxed ``PenguResult``.

        Mirrors the 'some' contract (LANGUAGE.md §6.6): the payload is copied into
        a ``pengu_sigil_alloc`` cell so the result owns it, using the deep-copy
        helper when the payload itself owns memory.
        """
        arg_c = self._translate_expr(arg_node)
        arg_t = self._infer_node_type(arg_node)
        if arg_t is None:
            if isinstance(arg_node, Tree) and arg_node.data in ("int_lit", "true_lit", "false_lit"):
                arg_t = INT_TYPE
            elif isinstance(arg_node, Tree) and arg_node.data == "string_lit":
                arg_t = STRING_TYPE
            elif isinstance(arg_node, Tree) and arg_node.data == "float_lit":
                arg_t = FLOAT_TYPE
            else:
                raise SemanticError(
                    f"Cannot determine the payload type of '{'ok_of' if is_ok else 'err_of'}'",
                    code="E0005",
                    help="Annotate the value or bind it to a typed variable first "
                         "('var v as T is ...' then 'calling ok_of with v').",
                    note="The constructor boxes a value of a statically known type."
                )
        side = "ok_val" if is_ok else "err_val"
        tmp = self.get_temp_name("_res_val")
        decl_tmp = CTypeMapper.to_c_decl(arg_t, tmp)
        res_tmp = self.get_temp_name("_result")
        stmts = [
            f"{decl_tmp} = {arg_c};",
            f"PenguResult {res_tmp};",
            f"{res_tmp}.is_ok = {'true' if is_ok else 'false'};",
            f"{res_tmp}.ok_val = NULL;",
            f"{res_tmp}.err_val = NULL;",
            f"{res_tmp}.{side} = pengu_sigil_alloc(sizeof({tmp}));",
            f"if (!{res_tmp}.{side}) {res_tmp}.is_ok = {'false' if is_ok else 'true'};",
            # The box stores the payload bytes; the source keeps whatever it owned.
            f"else memcpy({res_tmp}.{side}, &({tmp}), sizeof({tmp}));",
        ]
        return self._block_expr(stmts, res_tmp)
