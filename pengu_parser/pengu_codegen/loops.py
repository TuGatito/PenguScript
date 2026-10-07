"""`while`, `for` and the collecting loop values.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AnyType,
    ArrayType,
    BaseType,
    I64_TYPE,
    INT_TYPE,
    ListType,
    ManyType,
    MapType,
    Optional,
    RangeType,
    RefType,
    STRING_TYPE,
    SemanticError,
    SliceType,
    Symbol,
    Tree,
    Type,
    TypeInferrer,
    TypeParam,
)
from .ctype import (
    CTypeMapper,
)

class LoopMixin:
    """`while`, `for` and the collecting loop values."""

    def _translate_while(self, node: Tree, append_ctx=None) -> str:
        """Translates a while loop; ``append_ctx`` collects the body value."""
        ind = self.indent()
        cond_node = node.children[0]
        block_node = node.children[1]
        cond_str = self._translate_expr(cond_node)

        self.indent_level += 1
        body_str = self._translate_loop_body(block_node, append_ctx)
        self.indent_level -= 1

        return f"{ind}while ({cond_str}) {{\n{body_str}\n{ind}}}"
    def _translate_loop_body(self, block_node: Tree, append_ctx=None) -> str:
        """Body C of a loop.

        With ``append_ctx`` = ``(list_tmp, elem_c, elem_t)`` the body's final
        statement is the iteration's *value*: it is pushed onto the collecting
        list instead of being emitted (so the push sits at the end of the body and
        ``continue`` naturally skips it while ``break`` ends the loop).
        """
        if append_ctx is None:
            return self._translate_nested_block(block_node)
        val_node_box: Optional[list] = None
        if len(append_ctx) == 4:
            list_tmp, elem_c, elem_t, val_node_box = append_ctx
        else:
            list_tmp, elem_c, elem_t = append_ctx
        saved_locals = dict(self.local_vars)
        try:
            stmts = [c for c in block_node.children if isinstance(c, Tree)]
            parts, val = self._value_branch(stmts, elem_t, val_node_out=val_node_box)
            if val is not None:
                parts.extend(self._emit_iteration_value(
                    list_tmp, elem_c, val, elem_t,
                    val_node_box[-1] if val_node_box else None))
            return "\n".join(parts)
        finally:
            self.local_vars = saved_locals
    def _translate_loop_value(self, node: Tree, expected_type: Optional[Type] = None) -> str:
        """GNU statement-expression for a loop used as a value.

        The loop collects its body's value on every iteration into a fresh list
        (``list of T``), e.g. ``for i from 0 to 3: i * 2`` yields three ints.
        """
        v_t = getattr(node, "_pengu_value_type", None) or expected_type
        if isinstance(v_t, ListType):
            elem_t = v_t.element
        else:
            elem_t = INT_TYPE if isinstance(v_t, (type(None), AnyType)) else v_t
        if isinstance(elem_t, AnyType):
            elem_t = INT_TYPE
        elem_c = CTypeMapper.to_c_type(elem_t)
        init_call = f"pengu_list_new(sizeof({elem_c}), 8)"
        list_tmp = self.get_temp_name("_loop_list")
        with_append = (list_tmp, elem_c, elem_t, [])
        if node.data == "while_stmt":
            loop_c = self._translate_while(node, with_append)
        elif node.data == "for_range_stmt":
            loop_c = self._translate_for_range(node, with_append)
        else:
            loop_c = self._translate_for_in(node, with_append)
        ind = self.indent()
        return (
            f"(__extension__({{\n"
            f"{ind}  PenguList {list_tmp} = {init_call};\n"
            f"{loop_c}\n"
            f"{ind}  {list_tmp};\n"
            f"{ind}}}))"
        )
    def _range_counter_ctype(self, node: Tree) -> str:
        """C type of a 'for i from a to b [step s]' counter.

        Roadmap 0.11: the counter follows the inferred type of the bounds.  An
        'int' range keeps 'int32_t'; a 64-bit bound (i64/u64/usize) promotes the
        counter to 'int64_t' so a large range is not truncated.
        """
        def _is_64bit(t: Optional[Type]) -> bool:
            u = self._unwrap_owned_type(t)
            return isinstance(u, BaseType) and u.name in (
                "i64", "u64", "usize", "isize", "int64", "uint64", "int64_t", "uint64_t")
        for idx in (1, 2, 3):
            if idx < len(node.children) and node.children[idx] is not None:
                if _is_64bit(self._infer_node_type(node.children[idx])):
                    return "int64_t"
        return "int32_t"
    def _translate_for_range(self, node: Tree, append_ctx=None) -> str:
        """Translates for i from start to end [step s] loop."""
        ind = self.indent()
        var_name = str(node.children[0])
        c_var_name = self._c_ident(var_name)
        start_str = self._translate_expr(node.children[1])
        end_str = self._translate_expr(node.children[2])
        step_node = node.children[3] if len(node.children) == 5 and node.children[3] is not None else None
        step_str = self._translate_expr(step_node) if step_node is not None else "1"
        block_node = node.children[-1]
        counter_t = self._range_counter_ctype(node)

        _MISSING = object()
        prev_var = self.local_vars.get(var_name, _MISSING)
        self.local_vars[var_name] = I64_TYPE if counter_t == "int64_t" else INT_TYPE
        self.indent_level += 1
        body_str = self._translate_loop_body(block_node, append_ctx)
        self.indent_level -= 1
        if prev_var is _MISSING:
            self.local_vars.pop(var_name, None)
        else:
            self.local_vars[var_name] = prev_var

        step_val = self.const_folder.fold(step_node) if step_node is not None else 1
        if isinstance(step_val, int):
            if step_val < 0:
                cond_c = f"{c_var_name} > {end_str}"
                step_c = f"{c_var_name}--" if step_val == -1 else f"{c_var_name} += {step_str}"
                loop_header = f"for ({counter_t} {c_var_name} = {start_str}; {cond_c}; {step_c})"
            else:
                cond_c = f"{c_var_name} < {end_str}"
                step_c = f"{c_var_name}++" if step_val == 1 else f"{c_var_name} += {step_str}"
                loop_header = f"for ({counter_t} {c_var_name} = {start_str}; {cond_c}; {step_c})"
        else:
            _step_tmp = self.get_temp_name("_step")
            cond_c = f"({_step_tmp} > 0 ? {c_var_name} < {end_str} : ({_step_tmp} < 0 ? {c_var_name} > {end_str} : false))"
            loop_header = f"for ({counter_t} {c_var_name} = {start_str}, {_step_tmp} = {step_str}; {cond_c}; {c_var_name} += {_step_tmp})"

        return f"{ind}{loop_header} {{\n{body_str}\n{ind}}}"
    def _translate_for_in(self, node: Tree, append_ctx=None) -> str:
        """Translates for [i,] item in collection loop.

        Supports the classic single-binding form ('for v in col') and the
        indexed form ('for i, v in col', 'for i, _ in col', 'for _, v in col').
        When an index binding is requested its identifier becomes the C99 loop
        counter so 'i' is visible inside the body; '_' bindings are skipped.
        ``append_ctx`` collects the body's value per iteration (loop as value).
        """
        ind = self.indent()
        if len(node.children) == 4:
            index_name = str(node.children[0])
            elem_name = str(node.children[1])
            col_expr = node.children[2]
            block_node = node.children[3]
        else:
            index_name = None
            elem_name = str(node.children[0])
            col_expr = node.children[1]
            block_node = node.children[2]

        col_str = self._translate_expr(col_expr)
        want_index = index_name is not None and index_name != "_"
        want_elem = elem_name != "_"
        c_index_name = self._c_ident(index_name) if want_index else None
        c_elem_name = self._c_ident(elem_name) if want_elem else None
        iter_idx = c_index_name if want_index else self.get_temp_name("_idx")

        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
        for lv_k, lv_v in self.local_vars.items():
            inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))

        col_t = None
        try:
            col_t = inferrer.infer(col_expr)
        except Exception:
            pass

        # A bare type parameter only becomes concrete after monomorphization.
        # If it is still abstract here the element type is unknowable, which
        # would emit invalid C; fail loudly instead (the checker reports the
        # same condition earlier with source coordinates).
        if isinstance(col_t, TypeParam):
            subst = getattr(self, "current_subst_map", None) or {}
            if col_t.name in subst:
                col_t = subst[col_t.name]
        if isinstance(col_t, TypeParam):
            raise SemanticError(
                f"Cannot iterate directly over generic type parameter '{col_t.name}'",
                line=self._node_line(node),
                code="E0005",
                help=f"Use 'list of {col_t.name}' or 'slice of {col_t.name}' as the "
                     f"parameter type; direct iteration over a bare '{col_t.name}' "
                     "requires associated types (future feature).",
                note="'for ... in' needs a concrete element type to generate C.",
            )

        # Check if Range loop
        is_range = False
        start_str = None
        end_str = None
        if isinstance(col_expr, Tree) and col_expr.data in ("to_expr", "range_dotdot"):
            is_range = True
            start_str = self._translate_expr(col_expr.children[0])
            end_str = self._translate_expr(col_expr.children[-1])
        elif isinstance(col_t, RangeType):
            is_range = True

        if is_range:
            loop_var = c_elem_name if want_elem else self.get_temp_name("_rv")
            _MISSING = object()
            prev_elem = self.local_vars.get(elem_name, _MISSING) if want_elem else _MISSING
            prev_index = self.local_vars.get(index_name, _MISSING) if want_index else _MISSING
            if want_elem:
                self.local_vars[elem_name] = INT_TYPE
            if want_index:
                self.local_vars[index_name] = INT_TYPE
            self.indent_level += 1
            body_str = self._translate_loop_body(block_node, append_ctx)
            self.indent_level -= 1
            if want_elem:
                if prev_elem is _MISSING:
                    self.local_vars.pop(elem_name, None)
                else:
                    self.local_vars[elem_name] = prev_elem
            if want_index:
                if prev_index is _MISSING:
                    self.local_vars.pop(index_name, None)
                else:
                    self.local_vars[index_name] = prev_index

            if start_str is not None and end_str is not None:
                if want_index:
                    return (
                        f"{ind}int32_t {c_index_name} = 0;\n"
                        f"{ind}for (int64_t {loop_var} = {start_str}; "
                        f"{loop_var} < {end_str}; {loop_var}++, {c_index_name}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )
                else:
                    return (
                        f"{ind}for (int64_t {loop_var} = {start_str}; "
                        f"{loop_var} < {end_str}; {loop_var}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )
            else:
                rng_tmp = self.get_temp_name("_rng")
                if want_index:
                    return (
                        f"{ind}PenguRange {rng_tmp} = {col_str};\n"
                        f"{ind}int32_t {c_index_name} = 0;\n"
                        f"{ind}for (int64_t {loop_var} = {rng_tmp}.start; "
                        f"{loop_var} < {rng_tmp}.end; {loop_var}++, {c_index_name}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )
                else:
                    return (
                        f"{ind}PenguRange {rng_tmp} = {col_str};\n"
                        f"{ind}for (int64_t {loop_var} = {rng_tmp}.start; "
                        f"{loop_var} < {rng_tmp}.end; {loop_var}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )

        # A receiver such as 'self' inside an enchanting method is a pointer
        # ('ref to map'/'ref to list').  Bind it to a temporary and iterate
        # through the dereference so the generated member accesses and
        # pengu_list_at(&x) calls are valid C.
        ref_prefix = ""
        if isinstance(col_t, RefType) and isinstance(col_t.target, (ListType, MapType, SliceType, ArrayType)):
            ref_tmp = self.get_temp_name("_col")
            ref_decl = CTypeMapper.to_c_decl(col_t, ref_tmp)
            ref_prefix = f"{ind}{ref_decl} = {col_str};\n"
            col_str = f"(*{ref_tmp})"
            col_t = col_t.target

        # A non-lvalue list ('for v in (calling make())') has no addressable
        # storage, so 'pengu_list_at(&(<expr>))' would be invalid C: bind it to a
        # temporary first.  Borrowed expressions keep using the original.
        iter_tmp = None
        if (isinstance(col_t, ListType) and not ref_prefix and isinstance(col_expr, Tree)
                and col_expr.data not in (
                    "var_ref", "field_access", "arrow_access", "at_expr",
                    "array_at_expr", "essence_of", "self_arrow", "self_ref",
                )):
            iter_tmp = self.get_temp_name("_iter")
            ref_prefix = f"{ind}{CTypeMapper.to_c_decl(col_t, iter_tmp)} = {col_str};\n"
            col_str = iter_tmp

        elem_t = col_t.element_type() if col_t and hasattr(col_t, "element_type") and col_t.element_type() else INT_TYPE
        is_string_iter = col_t is not None and col_t.is_string()
        if is_string_iter:
            elem_t = STRING_TYPE
        elem_c = CTypeMapper.to_c_type(elem_t)

        # An inline array literal ('for v in [1, 2]') has no storage of its own
        # (its C form is a brace initializer), so materialize it into a temporary
        # array the loop can index.
        lit_decl = ref_prefix
        if (isinstance(col_expr, Tree) and col_expr.data == "array_lit"
                and isinstance(col_t, ArrayType) and col_expr.children):
            lit_tmp = self.get_temp_name("_lit")
            elems = ", ".join(self._translate_expr(c) for c in col_expr.children)
            lit_type_decl = CTypeMapper.to_c_decl(elem_t, f"{lit_tmp}[]")
            lit_decl = ref_prefix + f"{ind}{lit_type_decl} = {{ {elems} }};\n"
            col_str = lit_tmp
            col_t = ArrayType(element=col_t.element, size=len(col_expr.children))

        _MISSING = object()
        prev_index = self.local_vars.get(index_name, _MISSING) if want_index else _MISSING
        prev_elem = self.local_vars.get(elem_name, _MISSING) if want_elem else _MISSING
        if want_index:
            self.local_vars[index_name] = INT_TYPE
        if want_elem:
            self.local_vars[elem_name] = elem_t
        self.indent_level += 1
        body_str = self._translate_loop_body(block_node, append_ctx)
        self.indent_level -= 1
        if want_index:
            if prev_index is _MISSING:
                self.local_vars.pop(index_name, None)
            else:
                self.local_vars[index_name] = prev_index
        if want_elem:
            if prev_elem is _MISSING:
                self.local_vars.pop(elem_name, None)
            else:
                self.local_vars[elem_name] = prev_elem

        c_elem_name = self._c_ident(elem_name)
        decl_elem = CTypeMapper.to_c_decl(elem_t, c_elem_name) if want_elem else "/* discard element */"
        elem_decl = f"{ind}  {decl_elem} = " if want_elem else f"{ind}  {decl_elem} "
        elem_cast = CTypeMapper.to_c_decl(elem_t, "*")
        if isinstance(col_t, ArrayType) and col_t.size is not None:
            if want_elem:
                body_prefix = f"{elem_decl}({col_str})[{iter_idx}];\n"
            else:
                body_prefix = f"{ind}  (void)({col_str})[{iter_idx}];\n"
            return (
                f"{lit_decl}"
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < {col_t.size}; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )
        elif isinstance(col_t, (SliceType, ManyType)):
            if want_elem:
                body_prefix = f"{elem_decl}((({elem_cast})({col_str}).data)[{iter_idx}]);\n"
            else:
                body_prefix = f"{ind}  (void)((({elem_cast})({col_str}).data)[{iter_idx}]);\n"
            return (
                f"{lit_decl}"
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < ({col_str}).len; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )
        elif isinstance(col_t, ListType):
            if want_elem:
                body_prefix = f"{elem_decl}(*({elem_cast})pengu_list_at(&({col_str}), {iter_idx}));\n"
            else:
                body_prefix = f"{ind}  (void)(*({elem_cast})pengu_list_at(&({col_str}), {iter_idx}));\n"
            # A materialized non-lvalue iterable ('for v in calling make()') owns
            # the list: release it once the loop ends (a 'break' still reaches
            # this line, an early 'return' does not, like every scope release).
            iter_suffix = (f"{ind}pengu_banish_list(&{iter_tmp});\n"
                           if iter_tmp is not None else "")
            return (
                f"{lit_decl}"
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < ({col_str}).len; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}\n"
                f"{iter_suffix}"
            )
        elif is_string_iter:
            # Iterating a PenguScript string yields each character as a
            # single-character PenguString (allocated via the char_at primitive).
            if want_elem:
                body_prefix = f"{elem_decl}pengu_string_char_at({col_str}, {iter_idx});\n"
                # The character is a fresh one-character buffer bound to the loop
                # variable.  Manual memory: it is released by whoever ends up
                # owning it (the body, or the list a comprehension collects into),
                # never automatically at the end of the iteration — that would
                # dangle anything the body stored.
                body_suffix = ""
            else:
                body_prefix = f"{ind}  (void)pengu_string_char_at({col_str}, {iter_idx});\n"
                body_suffix = ""
            return (
                f"{lit_decl}"
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < ({col_str}).len; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{body_suffix}{ind}}}"
            )
        elif isinstance(col_t, MapType):
            key_c = CTypeMapper.to_c_type(col_t.key)
            key_cast = CTypeMapper.to_c_decl(col_t.key, "*")
            decl_map_elem = CTypeMapper.to_c_decl(col_t.key, c_elem_name)
            slot_idx = self.get_temp_name("_slot")
            count_tmp = self.get_temp_name("_seen")
            if want_elem:
                body_prefix = f"{ind}  {decl_map_elem} = *(({key_cast})({col_str}).entries[{slot_idx}].key);\n"
            else:
                body_prefix = f"{ind}  /* discard element */\n"
            if want_index:
                return (
                    f"{lit_decl}"
                    f"{ind}int32_t {iter_idx} = -1;\n"
                    f"{ind}for (int32_t {slot_idx} = 0, {count_tmp} = 0; {count_tmp} < ({col_str}).len && {slot_idx} < ({col_str}).cap; {slot_idx}++) {{\n"
                    f"{ind}  if (!({col_str}).entries || !({col_str}).entries[{slot_idx}].occupied) continue;\n"
                    f"{ind}  {count_tmp}++;\n"
                    f"{ind}  {iter_idx}++;\n"
                    f"{body_prefix}"
                    f"{body_str}\n"
                    f"{ind}}}"
                )
            else:
                return (
                    f"{lit_decl}"
                    f"{ind}for (int32_t {slot_idx} = 0, {count_tmp} = 0; {count_tmp} < ({col_str}).len && {slot_idx} < ({col_str}).cap; {slot_idx}++) {{\n"
                    f"{ind}  if (!({col_str}).entries || !({col_str}).entries[{slot_idx}].occupied) continue;\n"
                    f"{ind}  {count_tmp}++;\n"
                    f"{body_prefix}"
                    f"{body_str}\n"
                    f"{ind}}}"
                )
        else:
            raise SemanticError(
                f"Cannot iterate over non-collection type '{col_t}' at codegen time",
                code="E0005",
                help="The checker should have caught this; if you see this error, it is a compiler bug.",
            )
