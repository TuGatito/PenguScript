"""Statement translation: blocks, loops, control flow and value blocks.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    AnyType,
    ArrayType,
    BOOL_TYPE,
    BaseType,
    EchoType,
    FLOAT_TYPE,
    FnType,
    FrozenType,
    I64_TYPE,
    INT_TYPE,
    List,
    ListType,
    ManyType,
    MapType,
    Optional,
    RangeType,
    RefType,
    RuneType,
    SIMPLE_STMT_ALIASES,
    STRING_TYPE,
    SealType,
    SemanticError,
    SliceType,
    Symbol,
    Token,
    Tree,
    Tuple,
    Type,
    TypeInferrer,
    TypeParam,
    VOID_TYPE,
    _decl_layout,
    ast_to_type,
    eval_comptime,
)
from .ast_utils import (
    flatten_at_chain,
)
from .ctype import (
    CTypeMapper,
    get_array_base_type,
    get_array_dims_and_base,
    sync_array_sizes,
)

class StmtMixin:
    """Statement translation: blocks, loops, control flow and value blocks."""

    def _translate_block(self, stmts: List[Tree]) -> str:
        """Translates a list of statements in a block.

        Each statement is preceded by a `#line` marker (statement context only)
        so compiler diagnostics point at the `.pengu` line that produced the C.
        """
        lines = []
        markers = self.emit_line_markers and self._expr_depth == 0
        for stmt in stmts:
            s_code = self._translate_stmt(stmt)
            if s_code:
                if markers:
                    marker = self._line_marker(stmt)
                    if marker:
                        lines.append(marker)
                lines.append(s_code)
        return "\n".join(lines)
    def _format_defer_cleanup(self, d: str, ind: str) -> str:
        """Formats a deferred cleanup statement or block with appropriate indentation."""
        if d.startswith("{\n") and d.endswith("}"):
            return "\n".join(f"{ind}{line}" if line else "" for line in d.splitlines())
        if d.endswith("}"):
            return f"{ind}{d}"
        return f"{ind}{d};"
    def _get_return_cleanup_lines(self, is_err_ret: bool = False, ind: str = "") -> List[str]:
        cleanup_lines = []
        if is_err_ret and self.errdefer_stack:
            for d in reversed(self.errdefer_stack[-1]):
                cleanup_lines.append(self._format_defer_cleanup(d, ind))

        if self.defer_stack:
            for d in reversed(self.defer_stack[-1]):
                cleanup_lines.append(self._format_defer_cleanup(d, ind))

        return cleanup_lines
    def _translate_stmt(self, node: Tree) -> str:
        """Wraps `_translate_stmt_impl` with statement-hoisting prelude flushing.

        In strict C99 mode (`use_gnu_extensions=False`) an expression may have
        queued statements in `self.expr_prelude` (see `_hoist`); they must be
        emitted *before* the statement that owns the expression.  In GNU mode
        (the default) this is a pass-through, so the generated C is unchanged.
        """
        if self.use_gnu_extensions:
            return self._translate_stmt_impl(node)
        saved = self.expr_prelude
        self.expr_prelude = []
        try:
            stmt_c = self._translate_stmt_impl(node)
            if self.expr_prelude:
                return "\n".join(self.expr_prelude + ([stmt_c] if stmt_c else []))
            return stmt_c
        finally:
            self.expr_prelude = saved
    def _hoist(self, stmt: str) -> None:
        """Queues a statement to be emitted before the current statement."""
        if stmt:
            self.expr_prelude.append(stmt)
    def _block_expr(self, stmts: List[str], value_expr: str) -> str:
        """Block-as-expression whose value is an already-declared name.

        ``stmts`` must declare ``value_expr`` (typically a temporary).  GNU mode
        wraps them in a statement expression; strict mode hoists them into the
        enclosing statement's prelude, which keeps the name in scope.
        """
        if self.use_gnu_extensions:
            body = "\n".join(list(stmts) + [f"  {value_expr};"])
            return f"(__extension__(({{\n{body}\n}})))"
        for s in stmts:
            self._hoist(s)
        return value_expr
    def _emit_block_expr(self, stmts: List[str], value_expr: str, c_decl: str) -> str:
        """Emits a block-as-expression.

        GNU mode keeps the historical statement-expression; strict mode hoists
        the statements to the current statement's prelude and returns the
        temporary holding the value.
        """
        if self.use_gnu_extensions:
            body = "\n".join(list(stmts) + [f"  {value_expr};"])
            return f"(__extension__(({{\n{body}\n}})))"
        tmp = self.get_temp_name("_bx")
        self._hoist(f"{c_decl} {tmp};")
        for s in stmts:
            self._hoist(s)
        self._hoist(f"{tmp} = {value_expr};")
        return tmp
    def _translate_stmt_impl(self, node: Tree) -> str:
        """Translates single statement node to C99."""
        if not isinstance(node, Tree):
            return ""

        if node.data == "stmt" and node.children:
            return self._translate_stmt(node.children[0])

        # Single-line block statements ('if c: return 0') parse as aliased
        # nodes (or a bare 'simple_stmt' holding one expression); normalize them
        # onto the canonical statement rules so they emit the same C as the
        # indented spelling.
        canonical = SIMPLE_STMT_ALIASES.get(node.data)
        if canonical is not None:
            node = Tree(canonical, node.children, meta=node.meta)
        elif node.data == "simple_stmt":
            if len(node.children) != 1:
                return ""
            node = Tree("expr_stmt", [node.children[0]], meta=node.meta)

        rule = node.data
        ind = self.indent()

        if rule == "var_decl":
            name = str(node.children[0])
            c_name = self._c_ident(name)
            type_node, expr_node = _decl_layout(node)

            t = None
            sym = getattr(node, "_pengu_symbol", None)
            if sym is None and self.symbols:
                sym = self.symbols.lookup(name)
            if type_node is not None:
                t = ast_to_type(type_node, self._lookup_type_fn)
                if isinstance(t, ArrayType) and sym and isinstance(sym.type, ArrayType):
                    sync_array_sizes(t, sym.type)
                if isinstance(t, ArrayType) and expr_node is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        inf_t = inferrer.infer(expr_node)
                        if isinstance(inf_t, ArrayType):
                            sync_array_sizes(t, inf_t)
                    except Exception:
                        pass
            else:
                if sym:
                    t = sym.type
                if t is None and expr_node is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        t = inferrer.infer(expr_node)
                    except Exception:
                        pass

            if t is not None:
                self.local_vars[name] = t
                self.local_vars[c_name] = t

            t_str = CTypeMapper.to_c_type(t) if t is not None else "int32_t"
            if t_str == "void":
                t_str = "int32_t"

            if isinstance(expr_node, Tree) and expr_node.data == "or_block":
                left_op = expr_node.children[0]
                block_stmts = [c for c in expr_node.children[1:] if isinstance(c, Tree)]
                decl = CTypeMapper.to_c_decl(t, c_name) if t is not None else f"{t_str} {c_name}"
                return self._translate_or_block(left_op, block_stmts, target_type=t, target_decl=decl, target_ident=c_name)

            alloc_comment = " /* stack */" if isinstance(t, (RuneType, ArrayType)) else ""
            if isinstance(t, ArrayType) and t.size is not None:
                dims, _ = get_array_dims_and_base(t)
                dims_str = "".join(f"[{d}]" for d in dims)
                base_t = get_array_base_type(t)
                decl_arr = CTypeMapper.to_c_decl(base_t, f"{c_name}{dims_str}")
                if isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                    return f"{ind}{decl_arr} = {{0}};{alloc_comment}"
                expr_code = self._translate_expr(expr_node, expected_type=t)
                return f"{ind}{decl_arr} = {expr_code};{alloc_comment}"
            if isinstance(t, ArrayType) and t.size is None and isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                array_size = self._translate_expr(expr_node.children[1])
                elem_str = CTypeMapper.to_c_type(t.element)
                return f"{ind}{elem_str} {c_name}[{array_size}] = {{0}};{alloc_comment}"
            expr_code = self._translate_expr(expr_node, expected_type=t)
            if isinstance(t, FnType) or (isinstance(t, RefType) and isinstance(t.target, FnType)):
                # Function-pointer values (lambdas, weave refs, C callbacks)
                # need a proper declarator: 'ret (*name)(params) = value;'
                return f"{ind}{CTypeMapper.to_c_decl(t, c_name)} = {expr_code};{alloc_comment}"
            return f"{ind}{t_str} {c_name} = {expr_code};{alloc_comment}"

        elif rule == "static_var_decl":
            name = str(node.children[0])
            c_name = self._c_ident(name)
            type_node, expr_node = _decl_layout(node)

            t = None
            sym = getattr(node, "_pengu_symbol", None)
            if sym is None and self.symbols:
                sym = self.symbols.lookup(name)
            if type_node is not None:
                t = ast_to_type(type_node, self._lookup_type_fn)
            else:
                if sym:
                    t = sym.type
                if t is None and expr_node is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        t = inferrer.infer(expr_node)
                    except Exception:
                        pass
            if t is not None:
                self.local_vars[name] = t
                self.local_vars[c_name] = t
            t_str = CTypeMapper.to_c_type(t) if t is not None else "int32_t"
            if t_str == "void":
                t_str = "int32_t"

            folded = None
            if expr_node is not None:
                try:
                    folded = self.const_folder.fold(expr_node)
                except Exception:
                    folded = None

            # Scalar compile-time constants can initialize a C static directly.
            if folded is not None and not isinstance(folded, str):
                val_str = self._format_const_val(folded, expected_type=t)
                return f"{ind}static {t_str} {c_name} = {val_str};"

            # Non-constant (e.g. strings, structs) statics are zero-initialized and
            # lazily assigned on first execution (once per process).
            init_c = self._translate_expr(expr_node, expected_type=t) if expr_node is not None else "0"
            guard = f"{c_name}_initialized"
            static_decl = (CTypeMapper.to_c_decl(t, c_name)
                           if (isinstance(t, FnType)
                               or (isinstance(t, RefType) and isinstance(t.target, FnType)))
                           else f"{t_str} {c_name}")
            return (
                f"{ind}static {static_decl};\n"
                f"{ind}static bool {guard} = false;\n"
                f"{ind}if (!{guard}) {{\n"
                f"{ind}  {c_name} = {init_c};\n"
                f"{ind}  {guard} = true;\n"
                f"{ind}}}"
            )


        elif rule == "let_decl":
            var_names_node = node.children[0]
            names = []
            if isinstance(var_names_node, Tree) and var_names_node.data == "var_name_list":
                names = [str(tok) for tok in var_names_node.children]
            else:
                names = [str(var_names_node)]

            type_node, expr_node = _decl_layout(node)

            if len(names) == 1:
                name = names[0]
                c_name = self._c_ident(name)
                t = None
                sym = getattr(node, "_pengu_symbol", None)
                if sym is None and self.symbols:
                    sym = self.symbols.lookup(name)
                if type_node is not None:
                    t = ast_to_type(type_node, self._lookup_type_fn)
                    if isinstance(t, ArrayType) and sym and isinstance(sym.type, ArrayType):
                        sync_array_sizes(t, sym.type)
                    if isinstance(t, ArrayType) and expr_node is not None:
                        try:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_name, lv_t in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                            inf_t = inferrer.infer(expr_node)
                            if isinstance(inf_t, ArrayType):
                                sync_array_sizes(t, inf_t)
                        except Exception:
                            pass
                else:
                    if sym:
                        t = sym.type
                    if t is None and expr_node is not None:
                        try:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_name, lv_t in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                            t = inferrer.infer(expr_node)
                        except Exception:
                            pass
                if t is not None:
                    self.local_vars[name] = t
                    self.local_vars[c_name] = t
                # A 'let' binding whose value owns a heap buffer is emitted as
                # non-const C storage: 'banish'/'defer banish' must be able to
                # null the buffer out.  Immutability is still enforced by the
                # checker ('set' on a 'let' is E0006), exactly as before.
                owned = self._type_owns_heap(t)
                t_str = CTypeMapper.to_c_type(t, const=not owned)
                if t_str == "void":
                    t_str = "const int32_t" if not owned else "int32_t"

                if isinstance(expr_node, Tree) and expr_node.data == "or_block":
                    left_op = expr_node.children[0]
                    block_stmts = [c for c in expr_node.children[1:] if isinstance(c, Tree)]
                    # 'or:' assigns the binding inside its else branch, so the
                    # declaration can never be 'const' (even for a non-owned
                    # 'let'): the C compiler rejects the assignment otherwise.
                    decl = CTypeMapper.to_c_decl(t, c_name) if t is not None else f"{t_str} {c_name}"
                    return self._translate_or_block(left_op, block_stmts, target_type=t, target_decl=decl, target_ident=c_name)

                alloc_comment = " /* stack */" if isinstance(t, (RuneType, ArrayType)) else ""
                if isinstance(t, ArrayType) and t.size is not None:
                    dims, _ = get_array_dims_and_base(t)
                    dims_str = "".join(f"[{d}]" for d in dims)
                    base_t = get_array_base_type(t)
                    decl_arr = CTypeMapper.to_c_decl(base_t, f"{c_name}{dims_str}", const=not owned)
                    if isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                        return f"{ind}{decl_arr} = {{0}};{alloc_comment}"
                    expr_code = self._translate_expr(expr_node, expected_type=t)
                    return f"{ind}{decl_arr} = {expr_code};{alloc_comment}"
                expr_code = self._translate_expr(expr_node, expected_type=t)
                if isinstance(t, FnType) or (isinstance(t, RefType) and isinstance(t.target, FnType)):
                    # Function-pointer binding: 'ret (*name)(params) = value;'
                    return f"{ind}{CTypeMapper.to_c_decl(t, c_name)} = {expr_code};{alloc_comment}"
                return f"{ind}{t_str} {c_name} = {expr_code};{alloc_comment}"
            else:
                # Destructuring: let a, b is expr
                tmp = self.get_temp_name("_destruct")
                expr_type = self._infer_node_type(expr_node)
                expr_code = self._translate_expr(expr_node)

                actual_expr_type = expr_type
                while isinstance(actual_expr_type, (FrozenType, AliasType, SealType)):
                    if isinstance(actual_expr_type, (FrozenType, AliasType)) and getattr(actual_expr_type, "target", None):
                        actual_expr_type = actual_expr_type.target
                    elif isinstance(actual_expr_type, SealType):
                        actual_expr_type = actual_expr_type.underlying
                    else:
                        break

                if isinstance(actual_expr_type, (RuneType, EchoType)) or (isinstance(actual_expr_type, BaseType) and (actual_expr_type.name in self.runes or actual_expr_type.name in self.echos)):
                    r_name = actual_expr_type.name
                    sym_r = self.symbols.lookup_type(r_name) if self.symbols else None
                    c_type_name = getattr(actual_expr_type, "c_name", None) or getattr(sym_r, "c_name", None) or self._c_ident(r_name)
                    # 'self.runes'/'self.echos' are keyed by the *C* name (an
                    # 'insignia' prefixed one), so look the fields up by that.
                    if c_type_name in self.runes:
                        f_dict = self.runes[c_type_name]
                    elif c_type_name in self.echos:
                        f_dict = self.echos[c_type_name]
                    elif r_name in self.runes:
                        f_dict = self.runes[r_name]
                    elif r_name in self.echos:
                        f_dict = self.echos[r_name]
                    else:
                        f_dict = {}
                    lines = [f"{ind}{c_type_name} {tmp} = {expr_code};"]
                    fields = list(f_dict.keys())
                    for i, name in enumerate(names):
                        c_name = self._c_ident(name)
                        sym = self.symbols.lookup(name) if self.symbols else None
                        var_t = sym.type if sym else None
                        if var_t is None and i < len(fields):
                            var_t = f_dict.get(fields[i])
                        if var_t is not None:
                            self.local_vars[name] = var_t
                            self.local_vars[c_name] = var_t
                        owned = self._type_owns_heap(var_t)
                        if var_t and var_t != VOID_TYPE:
                            decl = CTypeMapper.to_c_decl(var_t, c_name, const=not owned)
                        else:
                            decl = f"{'const int32_t' if not owned else 'int32_t'} {c_name}"
                        f_field_c = self._c_ident(fields[i]) if i < len(fields) else self._c_ident(name)
                        f_access = f"{tmp}.{f_field_c}"
                        lines.append(f"{ind}{decl} = {f_access};")
                    return "\n".join(lines)

                elif isinstance(actual_expr_type, ArrayType):
                    elem_t = actual_expr_type.element
                    if expr_code.strip().startswith("{"):
                        dims, base_c = get_array_dims_and_base(actual_expr_type)
                        dims_str = "".join(f"[{d}]" for d in dims)
                        lines = [f"{ind}const {base_c} {tmp}{dims_str} = {expr_code};"]
                    else:
                        lines = [f"{ind}const __auto_type {tmp} = {expr_code};"]
                    for i, name in enumerate(names):
                        c_name = self._c_ident(name)
                        sym = self.symbols.lookup(name) if self.symbols else None
                        var_t = sym.type if sym else elem_t
                        if var_t is not None:
                            self.local_vars[name] = var_t
                            self.local_vars[c_name] = var_t
                        owned = self._type_owns_heap(var_t)
                        if isinstance(elem_t, ArrayType):
                            decl = CTypeMapper.to_c_decl(elem_t, c_name, const=not owned)
                            lines.append(f"{ind}{decl} = {tmp}[{i}];")
                        else:
                            if var_t and var_t != VOID_TYPE:
                                decl = CTypeMapper.to_c_decl(var_t, c_name, const=not owned)
                            else:
                                decl = f"{'const int32_t' if not owned else 'int32_t'} {c_name}"
                            lines.append(f"{ind}{decl} = {tmp}[{i}];")
                    return "\n".join(lines)

                elif isinstance(actual_expr_type, (SliceType, ManyType)):
                    elem_t = actual_expr_type.element
                    elem_cast = CTypeMapper.to_c_decl(elem_t, "*")
                    lines = [f"{ind}PenguSlice {tmp} = {expr_code};"]
                    for i, name in enumerate(names):
                        c_name = self._c_ident(name)
                        sym = self.symbols.lookup(name) if self.symbols else None
                        var_t = sym.type if sym else elem_t
                        if var_t is not None:
                            self.local_vars[name] = var_t
                            self.local_vars[c_name] = var_t
                        owned = self._type_owns_heap(var_t)
                        if var_t and var_t != VOID_TYPE:
                            decl = CTypeMapper.to_c_decl(var_t, c_name, const=not owned)
                        else:
                            decl = f"{'const int32_t' if not owned else 'int32_t'} {c_name}"
                        lines.append(f"{ind}{decl} = (({elem_cast}){tmp}.data)[{i}];")
                    return "\n".join(lines)

                elif isinstance(actual_expr_type, ListType):
                    elem_t = actual_expr_type.element
                    elem_cast = CTypeMapper.to_c_decl(elem_t, "*")
                    lines = [f"{ind}PenguList {tmp} = {expr_code};"]
                    for i, name in enumerate(names):
                        c_name = self._c_ident(name)
                        sym = self.symbols.lookup(name) if self.symbols else None
                        var_t = sym.type if sym else elem_t
                        if var_t is not None:
                            self.local_vars[name] = var_t
                            self.local_vars[c_name] = var_t
                        owned = self._type_owns_heap(var_t)
                        if var_t and var_t != VOID_TYPE:
                            decl = CTypeMapper.to_c_decl(var_t, c_name, const=not owned)
                        else:
                            decl = f"{'const int32_t' if not owned else 'int32_t'} {c_name}"
                        lines.append(f"{ind}{decl} = (*({elem_cast})pengu_list_at(&{tmp}, {i}));")
                    # The helper list is a temporary copy of the PenguList header
                    # pointing at the same storage.  It is only released when the
                    # source expression owns that storage (rvalue) and the
                    # elements own nothing themselves: with a viewed source the
                    # buffer belongs to the original list, and with owning
                    # elements the extracted locals are views into it.
                    if (not self._type_owns_heap(elem_t)
                            and self._destructure_source_is_owned(expr_node)):
                        lines.append(f"{ind}pengu_banish_list(&{tmp});")
                    return "\n".join(lines)

                else:
                    raise SemanticError(
                        f"Cannot destructure expression of type '{expr_type}'",
                        code="E0017",
                        help="Destructuring is only supported on runes, fixed arrays, slices, and lists."
                    )

        elif rule == "const_decl":
            name = str(node.children[0])
            c_name = self._c_ident(name)
            type_node, expr_node = _decl_layout(node)

            t = None
            sym = getattr(node, "_pengu_symbol", None)
            if sym is None and self.symbols:
                sym = self.symbols.lookup(name)
            if type_node is not None:
                t = ast_to_type(type_node, self._lookup_type_fn)
            elif sym and sym.type:
                t = sym.type

            val = self.const_folder.fold(expr_node)
            if t is None:
                if isinstance(val, bool):
                    t = BOOL_TYPE
                elif isinstance(val, int):
                    t = INT_TYPE
                elif isinstance(val, float):
                    t = FLOAT_TYPE
                elif isinstance(val, str):
                    t = STRING_TYPE
                elif sym and sym.type:
                    t = sym.type

            if t is not None:
                self.local_vars[name] = t
                self.local_vars[c_name] = t

            if isinstance(val, bool):
                int_v = 1 if val else 0
                return f"{ind}enum {{ {c_name} = {int_v} }};"
            elif isinstance(val, int) and -2147483648 <= val <= 2147483647:
                return f"{ind}enum {{ {c_name} = {val} }};"
            elif isinstance(val, int):
                return f"{ind}static const int64_t {c_name} = {val}LL;"
            elif isinstance(val, float):
                return f"{ind}static const double {c_name} = {val};"
            elif isinstance(val, str):
                cstr = self._translate_string_lit(val, as_c_literal=True)
                if self._is_ref_char_type(t):
                    return f"{ind}static const char* const {c_name} = {cstr};"
                else:
                    return f"{ind}const PenguString {c_name} = pengu_string_from_cstr({cstr});"
            else:
                expr_code = self._translate_expr(expr_node, expected_type=t)
                t_str = CTypeMapper.to_c_decl(t, c_name, const=True) if t else f"const int32_t {c_name}"
                return f"{ind}static {t_str} = {expr_code};"

        elif rule == "set_stmt":
            target_node = node.children[0]
            expr_node = node.children[1]

            inner_target = target_node.children[0] if (isinstance(target_node, Tree) and target_node.data == "set_target" and target_node.children) else target_node

            # Check if setting a map element: `set m at k is v`
            if isinstance(inner_target, Tree) and inner_target.data in ("normal_target", "with_target") and len(inner_target.children) >= 2:
                last_acc = inner_target.children[-1]
                if isinstance(last_acc, Tree) and last_acc.data == "at_access":
                    base_parts = list(inner_target.children[:-1])
                    if inner_target.data == "normal_target":
                        base_str = str(base_parts[0])
                        sym = self.symbols.lookup(base_str) if self.symbols else None
                        if self.with_stack and (not sym or sym.kind == "field") and base_str not in self.local_vars:
                            base_target = self.with_stack[-1]
                            base_type = self._get_current_with_target_type()
                            sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                            base_str = f"{base_target}{sep}{base_str}"
                            curr_t = self._lookup_field_type_on(base_type, base_str)
                        else:
                            if base_str in self.local_vars and self.local_vars[base_str] is not None:
                                curr_t = self.local_vars[base_str]
                            elif base_str.startswith("_") and base_str[1:] in self.local_vars and self.local_vars[base_str[1:]] is not None:
                                curr_t = self.local_vars[base_str[1:]]
                            elif sym is not None and sym.type:
                                curr_t = sym.type
                            else:
                                curr_t = self._lookup_var_type(base_str)
                        for acc in base_parts[1:]:
                            base_str, curr_t = self._translate_access_op_step(base_str, acc, curr_t)
                        map_t = curr_t or self._lookup_var_type(base_str) or self._lookup_var_type(str(base_parts[0]))
                    else:
                        field_name = str(base_parts[0])
                        base_target = self.with_stack[-1] if self.with_stack else "self"
                        base_type = self._get_current_with_target_type()
                        sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                        base_str = f"{base_target}{sep}{field_name}"
                        curr_t = self._lookup_field_type_on(base_type, field_name)
                        for acc in base_parts[1:]:
                            base_str, curr_t = self._translate_access_op_step(base_str, acc, curr_t)
                        map_t = curr_t or self._lookup_var_type(base_str) or self._lookup_with_field_type(inner_target)

                    if isinstance(map_t, (MapType, RefType)) and (isinstance(map_t, MapType) or isinstance(map_t.target, MapType)):
                        actual_map = map_t.target if isinstance(map_t, RefType) else map_t
                        k_expr = self._translate_expr(last_acc.children[0], expected_type=actual_map.key)
                        v_expr = self._translate_expr(expr_node, expected_type=actual_map.value)
                        key_c = CTypeMapper.to_c_type(actual_map.key)
                        val_c = CTypeMapper.to_c_type(actual_map.value)
                        map_ptr = base_str if isinstance(map_t, RefType) else f"&({base_str})"
                        tmp_k = self.get_temp_name("_k")
                        tmp_v = self.get_temp_name("_v")
                        return (
                            f"{ind}{{\n"
                            f"{ind}  {key_c} {tmp_k} = {k_expr};\n"
                            f"{ind}  {val_c} {tmp_v} = {v_expr};\n"
                            f"{ind}  pengu_map_put({map_ptr}, &{tmp_k}, &{tmp_v});\n"
                            f"{ind}}}"
                        )

            target_str = self._translate_set_target(target_node)

            inner_target = target_node.children[0] if (isinstance(target_node, Tree) and target_node.data == "set_target" and target_node.children) else target_node
            target_type = self._infer_node_type(inner_target)
            if target_type is None:
                if isinstance(inner_target, Tree) and inner_target.data == "with_target":
                    # '.field' inside a 'with:' / 'with x:' block: the inferrer has no
                    # with-context, so resolve the field type from the codegen's stack.
                    target_type = self._lookup_with_field_type(inner_target)
                elif isinstance(inner_target, Tree) and inner_target.data == "normal_target":
                    obj_name = str(inner_target.children[0])
                    target_type = self._lookup_var_type(obj_name)
                elif isinstance(inner_target, Token):
                    target_type = self._lookup_var_type(str(inner_target))

            expr_str = self._translate_expr(expr_node, expected_type=target_type)

            rune_name = None
            if target_type is not None:
                if isinstance(target_type, RuneType):
                    rune_name = target_type.name
                elif isinstance(target_type, BaseType) and target_type.name in self.runes:
                    rune_name = target_type.name

            is_lvalue = (
                (isinstance(expr_node, Tree) and expr_node.data in ("var_ref", "field_access", "arrow_access", "at_expr"))
                or isinstance(expr_node, Token)
            )

            if is_lvalue and rune_name and rune_name in self.runes and len(self.runes[rune_name]) >= 3:
                return f"{ind}memcpy(&({target_str}), &({expr_str}), sizeof({rune_name}));"

            return f"{ind}{target_str} = {expr_str};"

        elif rule == "compound_set_stmt":
            # 'set target OP value' -> C compound assignment (strings concatenate).
            target_node = node.children[0]
            op = str(node.children[1])
            expr_node = node.children[2]
            target_str = self._translate_set_target(target_node)

            inner_target = target_node.children[0] if (isinstance(target_node, Tree) and target_node.data == "set_target" and target_node.children) else target_node
            target_type = None
            if isinstance(inner_target, Tree) and inner_target.data == "with_target":
                target_type = self._lookup_with_field_type(inner_target)
            elif isinstance(inner_target, Tree) and inner_target.data == "normal_target" and inner_target.children:
                target_type = self._lookup_var_type(str(inner_target.children[0]))
            elif isinstance(inner_target, Token):
                target_type = self._lookup_var_type(str(inner_target))

            expr_str = self._translate_expr(expr_node, expected_type=target_type)

            # 'string += ...' is rejected by the checker: string composition has
            # a single spelling ('{expr}' interpolation), so only numeric
            # compound operators reach this point.
            return f"{ind}{target_str} {op} {expr_str};"

        elif rule == "if_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            else_node = node.children[2] if len(node.children) > 2 else None

            binding = self._binding_cond(cond_node)
            if binding is not None:
                # 'if name as T is <maybe>:' — a scoped unwrap, never folded.
                return self._translate_binding_if(node, binding)

            # Dead code elimination for constant condition
            folded = self.const_folder.fold(cond_node)
            if folded is not None:
                if bool(folded) is True:
                    body_str = self._translate_nested_block(block_node)
                    return f"{ind}/* dead code eliminated (branch always true) */\n{body_str}"
                else:
                    if else_node:
                        self.indent_level += 1
                        else_str = self._translate_else_block(else_node)
                        self.indent_level -= 1
                        return f"{ind}/* dead code eliminated (branch always false) */\n{else_str}"
                    return f"{ind}/* dead code eliminated (branch always false) */"

            cond_str = self._translate_if_cond(cond_node)
            self.indent_level += 1
            body_str = self._translate_nested_block(block_node)
            self.indent_level -= 1

            res = f"{ind}if ({cond_str}) {{\n{body_str}\n{ind}}}"
            if else_node:
                self.indent_level += 1
                else_str = self._translate_else_block(else_node)
                self.indent_level -= 1
                res += f" else {{\n{else_str}\n{ind}}}"
            return res

        elif rule == "unless_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            else_node = node.children[2] if len(node.children) > 2 else None

            folded = self.const_folder.fold(cond_node)
            if folded is not None:
                if bool(folded) is False:
                    body_str = self._translate_nested_block(block_node)
                    return f"{ind}/* dead code eliminated (unless always true) */\n{body_str}"
                else:
                    if else_node:
                        self.indent_level += 1
                        else_str = self._translate_else_block(else_node)
                        self.indent_level -= 1
                        return f"{ind}/* dead code eliminated (unless always false) */\n{else_str}"
                    return f"{ind}/* dead code eliminated (unless always false) */"

            cond_str = self._translate_expr(cond_node)
            self.indent_level += 1
            body_str = self._translate_nested_block(block_node)
            self.indent_level -= 1

            res = f"{ind}if (!({cond_str})) {{\n{body_str}\n{ind}}}"
            if else_node:
                self.indent_level += 1
                else_str = self._translate_else_block(else_node)
                self.indent_level -= 1
                res += f" else {{\n{else_str}\n{ind}}}"
            return res

        elif rule == "when_stmt":
            # Compile-time conditional statement: emit only the active branch.
            cond_node = node.children[0]
            block_node = node.children[1] if (len(node.children) > 1 and isinstance(node.children[1], Tree) and node.children[1].data == "block") else None
            else_node = node.children[2] if (len(node.children) > 2 and isinstance(node.children[2], Tree)) else None
            val = eval_comptime(self.compile_env, cond_node)
            if val is None or not isinstance(val, bool):
                raise SemanticError(
                    "'when' condition must evaluate to a compile-time boolean constant",
                    code="E0039",
                )
            if val is True and block_node is not None:
                return self._translate_nested_block(block_node)
            if val is False and else_node is not None:
                if else_node.data == "when_else_plain":
                    stmt_nodes = [c for c in else_node.children if isinstance(c, Tree)]
                    return self._translate_block(stmt_nodes)
                if else_node.data == "when_else_when":
                    parts = [self._translate_stmt(c) for c in else_node.children if isinstance(c, Tree)]
                    return "\n".join(p for p in parts if p)
            return ""

        elif rule == "while_stmt":
            return self._translate_while(node)

        elif rule in ("for_stmt", "for_range_stmt", "for_in_stmt"):
            if rule == "for_range_stmt":
                return self._translate_for_range(node)
            elif rule == "for_in_stmt":
                return self._translate_for_in(node)
            first_child = node.children[0]
            if isinstance(first_child, Tree) and first_child.data == "for_range_stmt":
                return self._translate_for_range(first_child)
            elif isinstance(first_child, Tree) and first_child.data == "for_in_stmt":
                return self._translate_for_in(first_child)
            return ""

        elif rule == "unsafe_stmt":
            body = node.children[0] if node.children else None
            stmts = body.children if isinstance(body, Tree) and body.data == "block" else list(node.children[1:])
            saved_locals = dict(self.local_vars)
            self._unsafe_depth += 1
            try:
                body_lines = []
                for s_stmt in stmts:
                    code = self._translate_stmt(s_stmt)
                    if code:
                        body_lines.append(code)
            finally:
                self._unsafe_depth -= 1
                self.local_vars = saved_locals
            if not body_lines:
                return ""
            ind = "  " * self.indent_level
            return f"{ind}{{\n" + "\n".join(body_lines) + f"\n{ind}}}"

        elif rule == "with_stmt":
            target_expr = node.children[0]
            stmts = node.children[1:]
            target_str = self._translate_expr(target_expr)
            target_type = self._infer_node_type(target_expr)

            self.with_stack.append(target_str)
            self.with_type_stack.append(target_type)
            saved_locals = dict(self.local_vars)
            self.indent_level += 1
            try:
                body_lines = []
                for s in stmts:
                    code = self._translate_stmt(s)
                    if code:
                        body_lines.append(code)
            finally:
                self.indent_level -= 1
                self.local_vars = saved_locals
                self.with_type_stack.pop()
                self.with_stack.pop()

            if not body_lines:
                return ""
            return f"{ind}{{\n" + "\n".join(body_lines) + f"\n{ind}}}"

        elif rule == "defer_stmt":
            child = node.children[0]
            if isinstance(child, Tree) and child.data == "block":
                saved_level = self.indent_level
                self.indent_level = 1
                inner_stmts = [self._translate_stmt(s) for s in child.children]
                self.indent_level = saved_level
                block_c = "\n".join(s for s in inner_stmts if s)
                defer_str = f"{{\n{block_c}\n}}"
            elif isinstance(child, Tree) and (child.data.endswith("_stmt") or child.data == "stmt"):
                stmt_c = self._translate_stmt(child).strip()
                if stmt_c.endswith(";"):
                    stmt_c = stmt_c[:-1]
                defer_str = stmt_c
            else:
                defer_str = self._translate_expr(child)
            if self.defer_stack:
                self.defer_stack[-1].append(defer_str)
            return f"{ind}/* defer */"

        elif rule == "errdefer_stmt":
            child = node.children[0]
            if isinstance(child, Tree) and child.data == "block":
                saved_level = self.indent_level
                self.indent_level = 1
                inner_stmts = [self._translate_stmt(s) for s in child.children]
                self.indent_level = saved_level
                block_c = "\n".join(s for s in inner_stmts if s)
                errdefer_str = f"{{\n{block_c}\n}}"
            elif isinstance(child, Tree) and (child.data.endswith("_stmt") or child.data == "stmt"):
                stmt_c = self._translate_stmt(child).strip()
                if stmt_c.endswith(";"):
                    stmt_c = stmt_c[:-1]
                errdefer_str = stmt_c
            else:
                errdefer_str = self._translate_expr(child)
            if self.errdefer_stack:
                self.errdefer_stack[-1].append(errdefer_str)
            return f"{ind}/* errdefer */"

        elif rule == "banish_stmt":
            b_code = self._translate_banish_target(node.children[0], stmt_context=True)
            if "\n" in b_code:
                # Multi-line lowering (a maybe/result release): already complete
                # statements carrying their own indentation.
                return b_code if b_code.rstrip().endswith((";", "}")) else f"{b_code};"
            return f"{ind}{b_code};"

        elif rule == "return_stmt":
            ret_expr = node.children[0] if node.children else None
            ret_val_str = self._translate_expr(ret_expr, expected_type=self.current_return_type) if ret_expr is not None else ""

            is_err_ret = False
            if isinstance(ret_expr, Tree):
                if ret_expr.data in ("err_expr", "error_lit"):
                    is_err_ret = True
                elif ret_expr.data == "or_block" and len(ret_expr.children) > 1:
                    is_err_ret = True

            cleanup_lines = self._get_return_cleanup_lines(is_err_ret=is_err_ret, ind=ind)
            cleanup_str = "\n".join(cleanup_lines) + ("\n" if cleanup_lines else "")
            pop_stmt = f"{ind}pengu_frame_pop();"
            if ret_expr is not None:
                # Phase 3 item 3.7: always evaluate the return expression into a
                # temporary *before* popping the frame. This used to be done only
                # when there was deferred cleanup, so the common
                #     return calling f
                # emitted `pengu_frame_pop(); return f();` -- the caller's frame
                # was already off the stack when `f` pushed its own, and the crash
                # dump (which walks that stack) reported only the innermost
                # function instead of the real call chain.
                tmp = self.get_temp_name("_ret")
                ret_decl = CTypeMapper.to_c_decl(self.current_return_type, tmp)
                return f"{ind}{ret_decl} = {ret_val_str};\n{cleanup_str}{pop_stmt}\n{ind}return {tmp};"
            return f"{cleanup_str}{pop_stmt}\n{ind}return;"

        elif rule == "break_stmt":
            return f"{ind}break;"

        elif rule == "continue_stmt":
            return f"{ind}continue;"

        elif rule == "expr_stmt":
            expr_code = self._translate_expr(node.children[0])
            return f"{ind}{expr_code};"

        return ""
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
    def _translate_nested_block(self, node: Tree) -> str:
        """Translates a block node."""
        if not isinstance(node, Tree):
            return ""
        if node.data == "block":
            if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "simple_stmt":
                return self._translate_stmt(node.children[0])
            return self._translate_block(node.children)
        return self._translate_stmt(node)
    def _translate_else_block(self, node: Tree) -> str:
        """Translates an else block or else if statement."""
        if isinstance(node, Tree) and node.data == "else_block":
            if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "if_stmt":
                return self._translate_stmt(node.children[0])
            saved_locals = dict(self.local_vars)
            try:
                return self._translate_block(node.children)
            finally:
                self.local_vars = saved_locals
        elif isinstance(node, Tree) and node.data == "if_stmt":
            return self._translate_stmt(node)
        return ""
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
    def _translate_set_target(self, node: Any) -> str:
        """Translates the left-hand side target of a set statement."""
        if not isinstance(node, Tree):
            name = str(node)
            c_name = self._c_ident(name)
            sym = self.symbols.lookup(name) if self.symbols else None
            if self.with_stack and (not sym or sym.kind == "field") and name not in self.local_vars:
                base_target = self.with_stack[-1]
                base_type = self._get_current_with_target_type()
                sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                return f"{base_target}{sep}{c_name}"
            return c_name

        if node.data == "set_target":
            return self._translate_set_target(node.children[0])

        if node.data == "with_target":
            field_name = str(node.children[0])
            c_field_name = self._c_ident(field_name)
            base_target = self.with_stack[-1] if self.with_stack else "self"
            base_type = self._get_current_with_target_type()
            sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
            target_str = f"{base_target}{sep}{c_field_name}"
            current_t = self._lookup_field_type_on(base_type, field_name)
            for acc in node.children[1:]:
                target_str, current_t = self._translate_access_op_step(target_str, acc, current_t)
            return target_str

        elif node.data == "normal_target":
            base_name = str(node.children[0])
            c_base_name = self._c_ident(base_name)
            sym = self.symbols.lookup(base_name) if self.symbols else None
            if self.with_stack and (not sym or sym.kind == "field") and base_name not in self.local_vars:
                base_target = self.with_stack[-1]
                base_type = self._get_current_with_target_type()
                sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                target_str = f"{base_target}{sep}{c_base_name}"
                current_t = self._lookup_field_type_on(base_type, base_name)
            else:
                target_str = c_base_name
                if base_name in self.local_vars and self.local_vars[base_name] is not None:
                    current_t = self.local_vars[base_name]
                elif base_name.startswith("_") and base_name[1:] in self.local_vars and self.local_vars[base_name[1:]] is not None:
                    current_t = self.local_vars[base_name[1:]]
                elif sym is not None and sym.type:
                    current_t = sym.type
                else:
                    current_t = self._lookup_var_type(base_name)
            for acc in node.children[1:]:
                target_str, current_t = self._translate_access_op_step(target_str, acc, current_t)
            return target_str

        elif node.data == "essence_target":
            inner_str = self._translate_expr(node.children[0])
            return f"(*{inner_str})"

        return str(node)
    def _translate_access_op_step(self, base_str: str, acc_node: Tree, current_t: Optional[Type] = None) -> Tuple[str, Optional[Type]]:
        """Translates member and index access operators, returning (code, next_type)."""
        if acc_node.data == "dot_access":
            raw_field = str(acc_node.children[0])
            field_str = self._c_ident(raw_field)
            var_t = current_t if current_t is not None else self._lookup_var_type(base_str)
            alias_c = self._container_field_c_name(var_t, raw_field)
            if alias_c is not None:
                sep_a = "->" if (base_str == "self" or isinstance(var_t, RefType)) else "."
                return f"{base_str}{sep_a}{alias_c}", INT_TYPE
            sep = "->" if (base_str == "self" or isinstance(var_t, RefType)) else "."
            next_t = self._lookup_field_type_on(var_t, raw_field)
            return f"{base_str}{sep}{field_str}", next_t
        elif acc_node.data == "arrow_access":
            raw_field = str(acc_node.children[0])
            field_str = self._c_ident(raw_field)
            var_t = current_t if current_t is not None else self._lookup_var_type(base_str)
            target_t = var_t.target if isinstance(var_t, RefType) else var_t
            next_t = self._lookup_field_type_on(target_t, raw_field)
            return f"{base_str}->{field_str}", next_t
        elif acc_node.data == "at_access":
            idx = self._translate_expr(acc_node.children[0])
            var_t = current_t if current_t is not None else self._lookup_var_type(base_str)
            idx = self._emit_bounds_check(idx, base_str, var_t, acc_node.children[0])
            if isinstance(var_t, RefType):
                inner = var_t.target
                while isinstance(inner, (AliasType, FrozenType)) and getattr(inner, "target", None):
                    inner = inner.target
                if isinstance(inner, (SliceType, ManyType)):
                    elem_cast = CTypeMapper.to_c_decl(inner.element, "*")
                    return f"((({elem_cast})({base_str})->data)[{idx}])", inner.element
                if isinstance(inner, ListType):
                    elem_cast = CTypeMapper.to_c_decl(inner.element, "*")
                    return f"(*({elem_cast})pengu_list_at({base_str}, {idx}))", inner.element
                if isinstance(inner, ArrayType):
                    return f"{base_str}[{idx}]", inner.element
            if isinstance(var_t, (SliceType, ManyType)):
                elem_cast = CTypeMapper.to_c_decl(var_t.element, "*")
                return f"((({elem_cast})({base_str}).data)[{idx}])", var_t.element
            elif isinstance(var_t, ListType):
                elem_cast = CTypeMapper.to_c_decl(var_t.element, "*")
                return f"(*({elem_cast})pengu_list_at(&({base_str}), {idx}))", var_t.element
            elif isinstance(var_t, ArrayType):
                return f"{base_str}[{idx}]", var_t.element
            elif isinstance(var_t, (MapType, RefType)) and (isinstance(var_t, MapType) or isinstance(var_t.target, MapType)):
                actual_map = var_t.target if isinstance(var_t, RefType) else var_t
                key_c = CTypeMapper.to_c_type(actual_map.key)
                val_c = CTypeMapper.to_c_type(actual_map.value)
                ptr = base_str if isinstance(var_t, RefType) else f"&({base_str})"
                tmp_k = self.get_temp_name("_k")
                tmp_p = self.get_temp_name("_p")
                val_cast = CTypeMapper.to_c_decl(actual_map.value, "*")
                val_zero = "NULL" if isinstance(actual_map.value, (FnType, RefType)) else f"({val_c}){{0}}"
                code = (f"({{ {key_c} {tmp_k} = ({idx}); "
                        f"void* {tmp_p} = pengu_map_get({ptr}, &{tmp_k}); "
                        f"{tmp_p} ? (*(({val_cast}){tmp_p})) : {val_zero}; }})")
                return code, actual_map.value
            return f"{base_str}[{idx}]", (getattr(var_t, "element", None) if var_t else None)
        return base_str, current_t
    def _translate_access_op(self, base_str: str, acc_node: Tree, current_t: Optional[Type] = None) -> str:
        """Translates member and index access operators."""
        code, _ = self._translate_access_op_step(base_str, acc_node, current_t)
        return code
    def _translate_if_cond(self, node: Any) -> str:
        """Translates a branch condition.

        Binding patterns (``if name as T is <maybe>:``) are not conditions on
        their own — they need a scope for the bound name and are handled by
        :meth:`_translate_binding_if` / :meth:`_translate_binding_value_if`.
        """
        return self._translate_expr(node)
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
    def _make_elem_eq(self, elem_t: Optional[Type], left_expr: str, right_expr: str) -> str:
        """Emits appropriate C equality comparison for elements in collection checks."""
        unwrapped = elem_t
        while isinstance(unwrapped, (AliasType, FrozenType)):
            unwrapped = getattr(unwrapped, "target", None)
        if unwrapped == STRING_TYPE or (isinstance(unwrapped, BaseType) and unwrapped.name == "string"):
            return f"pengu_string_equal({left_expr}, {right_expr})"
        if isinstance(unwrapped, (RuneType, EchoType)):
            c_type = unwrapped.name
            return f"(memcmp(&({left_expr}), &({right_expr}), sizeof({c_type})) == 0)"
        if isinstance(unwrapped, BaseType) and unwrapped.name in self.runes:
            c_type = unwrapped.name
            return f"(memcmp(&({left_expr}), &({right_expr}), sizeof({c_type})) == 0)"
        return f"({left_expr} == {right_expr})"
    def _dotdot_as_slice_shape(self, node):
        """Re-shapes a `range_dotdot` that is really a slice into `slice_at_expr`.

        Returns None for a genuine range. Mirrors `TypeInferrer._range_as_slice`
        so the checker and the generator agree on which `..` nodes are slices.
        """
        children = [c for c in node.children if isinstance(c, Tree)]
        if len(children) != 2:
            return None
        left, right = children[0], children[-1]
        if not (isinstance(left, Tree) and left.data == "at_expr"):
            return None
        chain = flatten_at_chain(left)
        if len(chain) != 2:
            return None
        # slice_at_expr expects (base, slice_range(start, end)).
        slice_range = Tree("slice_range", [chain[1], right])
        return Tree("slice_at_expr", [chain[0], slice_range])
    def _emit_slice_at(self, node):
        """Emits the slice for a node shaped like `slice_at_expr`."""
        base_node = node.children[0]
        slice_range = node.children[1]
        start_c = self._translate_expr(slice_range.children[0])
        end_c = self._translate_expr(slice_range.children[1])
        base_c = self._translate_expr(base_node)
        base_t = self._infer_node_type(base_node)
        unwrapped_t = base_t.target if isinstance(base_t, RefType) else base_t
        while isinstance(unwrapped_t, (AliasType, FrozenType)) and getattr(unwrapped_t, "target", None):
            unwrapped_t = unwrapped_t.target

        if self._expr_is_string(base_node) or (base_t is not None and base_t.is_string()):
            return f"pengu_string_substring({base_c}, {start_c}, {end_c})"
        if isinstance(unwrapped_t, (SliceType, ManyType)):
            if not self.use_gnu_extensions:
                sl = self.get_temp_name("_sl")
                return self._block_expr(
                    [f"PenguSlice {sl} = ({base_c});"],
                    f"pengu_slice_new((char*){sl}.data + ((size_t)({start_c}) * {sl}.elem_size), {sl}.elem_size, (({end_c}) - ({start_c})))")
            return f"(__extension__({{ PenguSlice _sl = ({base_c}); pengu_slice_new((char*)_sl.data + ((size_t)({start_c}) * _sl.elem_size), _sl.elem_size, (({end_c}) - ({start_c}))); }}))"
        if isinstance(unwrapped_t, ListType):
            if not self.use_gnu_extensions:
                li = self.get_temp_name("_l")
                return self._block_expr(
                    [f"PenguList {li} = ({base_c});"],
                    f"pengu_slice_new((char*){li}.data + ((size_t)({start_c}) * {li}.elem_size), {li}.elem_size, (({end_c}) - ({start_c})))")
            return f"(__extension__({{ PenguList _l = ({base_c}); pengu_slice_new((char*)_l.data + ((size_t)({start_c}) * _l.elem_size), _l.elem_size, (({end_c}) - ({start_c}))); }}))"
        return f"pengu_slice_new(&(({base_c})[{start_c}]), sizeof(({base_c})[0]), (({end_c}) - ({start_c})))"
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
        ``errdefer`` and every scheduled release run exactly once and the returned
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
