"""Statement dispatch, blocks and assignment targets.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    ArrayType,
    BOOL_TYPE,
    BaseType,
    EchoType,
    FLOAT_TYPE,
    FnType,
    FrozenType,
    INT_TYPE,
    List,
    ListType,
    ManyType,
    MapType,
    Optional,
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
    VOID_TYPE,
    _decl_layout,
    ast_to_type,
    eval_comptime,
)
from .ctype import (
    CTypeMapper,
    get_array_base_type,
    get_array_dims_and_base,
    sync_array_sizes,
)

class StmtMixin:
    """Statement dispatch, blocks and assignment targets."""

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
                        # These names are brand-new locals, so their type is the
                        # rune's field type at this position. A global name lookup
                        # must NOT take precedence over it: `n` is a common name, and
                        # when another module happens to declare one (`var n as int`
                        # inside a generic `weave`), the lookup won and emitted
                        # `const int32_t n = _destruct.name;` for a *string* field --
                        # C that does not compile. Reproducible with `pengu test` on a
                        # three-module project; see tests/_inventory.md §15.
                        field_t = f_dict.get(fields[i]) if i < len(fields) else None
                        sym = self.symbols.lookup(name) if self.symbols else None
                        var_t = field_t if field_t is not None else (sym.type if sym else None)
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
