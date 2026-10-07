"""Symbol, type and field lookups, and the small type predicates.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    AnyType,
    ArrayType,
    BaseType,
    EchoType,
    FrozenType,
    List,
    ListType,
    ManyType,
    MapType,
    OmenType,
    Optional,
    RefType,
    RuneType,
    SealType,
    SemanticError,
    SliceType,
    Symbol,
    Token,
    Tree,
    Type,
    TypeInferrer,
    VOID_TYPE,
    type_owns_heap,
)
from .ctype import (
    CTypeMapper,
)

class SymbolMixin:
    """Symbol, type and field lookups, and the small type predicates."""

    def _lookup_symbol(self, name: str) -> Optional[Symbol]:
        """Resolves symbol in active symbol table, falling back to un-escaped name if prefixed with _."""
        if not self.symbols:
            return None
        sym = self.symbols.lookup(name)
        if sym is None and name.startswith("_"):
            sym = self.symbols.lookup(name[1:])
        return sym
    def _lookup_var_type(self, name: str) -> Optional[Type]:
        """Looks up semantic type for identifier in local or symbol context."""
        if name in self.local_vars and self.local_vars[name] is not None:
            return self.local_vars[name]
        if name.startswith("_") and name[1:] in self.local_vars and self.local_vars[name[1:]] is not None:
            return self.local_vars[name[1:]]
        sym = self._lookup_symbol(name)
        if sym and sym.type:
            return sym.type
        if name in self.runes:
            return RuneType(name, self.runes[name])
        if name in self.seals:
            return SealType(name, self.seals[name])
        if name.startswith("_"):
            un_name = name[1:]
            if un_name in self.runes:
                return RuneType(un_name, self.runes[un_name])
            if un_name in self.seals:
                return SealType(un_name, self.seals[un_name])
        return None
    def _lookup_with_field_type(self, node: Tree) -> Optional[Type]:
        """Resolves the field type of a with_target against the active with chain.

        Used by 'set .field is ...' statements whose target is a leading-dot
        field: the inferrer has no with-context, so the codegen must look up the
        field type through the same stack it uses to resolve the target name.

        Args:
            node: A 'with_target' AST node ('.field').

        Returns:
            The field's Type, or None when it cannot be resolved.
        """
        if not self.with_stack:
            return None
        if not getattr(node, "children", None):
            return None
        field_name = str(node.children[0])
        base_target = self.with_stack[-1]
        base_t = self._get_current_with_target_type()
        # 'self' inside enchanting is a reference; the with-target itself may be
        # a 'ref to T'. Look through the pointer to the pointee's fields.
        while isinstance(base_t, (RefType, AliasType, FrozenType, SealType)):
            if isinstance(base_t, RefType):
                base_t = base_t.target
            elif isinstance(base_t, (AliasType, FrozenType)):
                base_t = base_t.target
            elif isinstance(base_t, SealType):
                base_t = base_t.underlying
        if isinstance(base_t, BaseType) and self.symbols:
            sym_t = self.symbols.lookup_type(getattr(base_t, "name", ""))
            if sym_t and sym_t is not base_t:
                base_t = sym_t
                while isinstance(base_t, (RefType, AliasType, FrozenType, SealType)):
                    if isinstance(base_t, RefType):
                        base_t = base_t.target
                    elif isinstance(base_t, (AliasType, FrozenType)):
                        base_t = base_t.target
                    elif isinstance(base_t, SealType):
                        base_t = base_t.underlying
        curr_t = None
        if isinstance(base_t, (RuneType, EchoType)):
            fields = base_t.fields
            if not fields:
                # The RuneType may carry only a name; fall back to the
                # codegen's own collected field map.
                base_name = getattr(base_t, "name", str(base_t))
                fields = self.runes.get(base_name) or self.echos.get(base_name, {})
            c_fn = self._c_ident(field_name)
            if field_name in fields:
                curr_t = fields[field_name]
            elif c_fn in fields:
                curr_t = fields[c_fn]
        elif isinstance(base_t, BaseType) and getattr(base_t, "name", "") in self.runes:
            fields = self.runes[base_t.name]
            c_fn = self._c_ident(field_name)
            if field_name in fields:
                curr_t = fields[field_name]
            elif c_fn in fields:
                curr_t = fields[c_fn]

        if curr_t is None:
            return None

        for acc in node.children[1:]:
            if isinstance(acc, Tree) and acc.data == "dot_access" and acc.children:
                sub_field = str(acc.children[0])
                while isinstance(curr_t, (RefType, AliasType, FrozenType, SealType)):
                    if isinstance(curr_t, RefType):
                        curr_t = curr_t.target
                    elif isinstance(curr_t, (AliasType, FrozenType)):
                        curr_t = curr_t.target
                    elif isinstance(curr_t, SealType):
                        curr_t = curr_t.underlying
                if isinstance(curr_t, BaseType) and self.symbols:
                    sym_t = self.symbols.lookup_type(getattr(curr_t, "name", ""))
                    if sym_t and sym_t is not curr_t:
                        curr_t = sym_t
                        while isinstance(curr_t, (RefType, AliasType, FrozenType, SealType)):
                            if isinstance(curr_t, RefType):
                                curr_t = curr_t.target
                            elif isinstance(curr_t, (AliasType, FrozenType)):
                                curr_t = curr_t.target
                            elif isinstance(curr_t, SealType):
                                curr_t = curr_t.underlying
                sub_fields = getattr(curr_t, "fields", None)
                if not sub_fields:
                    sub_name = getattr(curr_t, "name", str(curr_t))
                    sub_fields = self.runes.get(sub_name) or self.echos.get(sub_name, {})
                c_sf = self._c_ident(sub_field)
                if sub_field in sub_fields:
                    curr_t = sub_fields[sub_field]
                elif c_sf in sub_fields:
                    curr_t = sub_fields[c_sf]
                else:
                    return None
            else:
                break

        return curr_t
    def _infer_node_type(self, node: Any, expected_type: Optional[Type] = None) -> Optional[Type]:
        """Infers semantic type for AST node using active local variable context."""
        if not self.symbols:
            return None
        saved_scope = self.symbols.current_scope
        saved_all_scopes_len = len(self.symbols.all_scopes)
        try:
            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
            if self.current_enchanted_type is not None:
                inferrer.symbols.push_scope(kind="enchanting", enchanting_type=self.current_enchanted_type)
            else:
                inferrer.symbols.push_scope(kind="block")
            for var_name, var_type in self.local_vars.items():
                if var_type is not None:
                    inferrer.symbols.define(Symbol(name=var_name, type=var_type, kind="var", line=0, column=0, file_path="."))
            return inferrer.infer(node, expected_type=expected_type)
        except Exception:
            return None
        finally:
            self.symbols.current_scope = saved_scope
            if len(self.symbols.all_scopes) > saved_all_scopes_len:
                del self.symbols.all_scopes[saved_all_scopes_len:]
    def _lookup_type_fn(self, name: str) -> Optional[Type]:
        """Type lookup resolver for AST conversion during codegen."""
        if hasattr(self, "current_subst_map") and self.current_subst_map and name in self.current_subst_map:
            return self.current_subst_map[name]
        sym = self.symbols.lookup(name) if self.symbols else None
        if sym and sym.type:
            return sym.type
        if self.symbols is not None:
            resolved = self.symbols.lookup_type(name)
            if resolved is not None:
                return resolved
        if name in self.runes:
            return RuneType(name, self.runes[name])
        if name in self.echos:
            return EchoType(name, self.echos[name])
        if name in self.omens:
            v_vals = self.omen_values.get(name, {})
            omen_sym = self.symbols.lookup(name) if self.symbols else None
            real_c_name = getattr(omen_sym, "c_name", None) if omen_sym else None
            if not real_c_name and self.symbols and hasattr(self.symbols, "global_scope"):
                for sym_name, sym in self.symbols.global_scope.symbols.items():
                    if getattr(sym, "kind", "") == "omen" and getattr(sym.type, "name", "") == name:
                        real_c_name = getattr(sym, "c_name", None)
                        break
            return OmenType(name, self.omens[name], variant_values=v_vals, c_name=real_c_name or name)
        if name in self.aliases:
            return self.aliases[name]
        if name in self.seals:
            return SealType(name, self.seals[name])
        if name in self.concepts:
            return self.concepts[name]
        return None
    def _destructure_source_is_owned(self, node: Any) -> bool:
        """True when a destructured expression owns the storage it points at."""
        cur = node
        while (isinstance(cur, Tree) and cur.data in ("value_expr", "expr", "paren_expr")
               and len(cur.children) == 1):
            cur = cur.children[0]
        if not isinstance(cur, Tree):
            return False
        return cur.data not in self._VIEW_EXPR_RULES
    def _method_weave(self, t_name: str, m_name: str) -> Optional[dict]:
        """Collected weave entry for an 'enchanting' method, or None."""
        for w in self.weaves:
            et = w.get("enchanted_type")
            if et is None:
                continue
            if getattr(et, "name", str(et)) == t_name and w.get("name") == m_name:
                return w
        return None
    def _method_definition_c_name(self, t_name: str, m_name: str) -> Optional[str]:
        """C name recorded for an 'enchanting' method (insignia-aware).

        ``t_name``/``m_name`` are the logical type and method names used by the
        checker; the emitted C name may carry the defining module's insignia
        prefix, so it must be read back from the collected weave instead of
        being reconstructed from the logical name.
        """
        w = self._method_weave(t_name, m_name)
        return w.get("c_name") if w else None
    @staticmethod
    def _container_field_c_name(t: Optional[Type], raw_field: str) -> Optional[str]:
        """Maps the documented length/capacity aliases to the real C fields.

        ``string``/``slice`` expose ``len``; ``list``/``map`` expose ``len`` and
        ``cap``.  The inferrer accepts the long spellings, so the code generator
        has to translate them (``xs.length`` used to emit ``xs.length``).
        """
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
            if nxt is None or nxt is u:
                break
            u = nxt
        if isinstance(u, RefType):
            u = u.target
            while isinstance(u, (AliasType, FrozenType, SealType)):
                nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
                if nxt is None or nxt is u:
                    break
                u = nxt
        is_seq = isinstance(u, (ListType, SliceType, ManyType))
        is_str = isinstance(u, BaseType) and u.name == "string"
        if raw_field in ("length", "len") and (is_seq or is_str or isinstance(u, MapType)):
            return "len"
        if raw_field in ("capacity", "cap") and (isinstance(u, ListType) or isinstance(u, MapType)):
            return "cap"
        return None
    def _callee_params(self, target_node: Any) -> Optional[List[Any]]:
        """Declared parameters ``(name, type, default_node)`` for a call target."""
        if not isinstance(target_node, Tree):
            return None
        # obj.method(...) / self.field.method(...)
        if (target_node.data == "normal_target" and len(target_node.children) >= 2
                and isinstance(target_node.children[-1], Tree)
                and target_node.children[-1].data in ("dot_access", "arrow_access")):
            m_name = str(target_node.children[-1].children[0])
            base_parts = target_node.children[:-1]
            base0 = base_parts[0] if base_parts else None
            base_name = str(base0) if base0 is not None else None
            sym = self.symbols.lookup(base_name) if (self.symbols and base_name) else None
            if sym is not None and getattr(sym, "kind", None) == "import":
                mod_prefix = getattr(sym, "c_name", None) or base_name
                info = (self.fn_info.get(f"{mod_prefix}_{m_name}")
                        or self.fn_info.get(f"{base_name}_{m_name}"))
                if info:
                    return list(info.get("params", []))
                return None
            if base_name == "self":
                recv_t = self.current_enchanted_type
            else:
                recv_t = self._lookup_var_type(base_name)
            recv_t = recv_t.target if isinstance(recv_t, RefType) else recv_t
            t_name = getattr(recv_t, "name", None)
            if t_name is None:
                return None
            w = self._method_weave(t_name, m_name)
            if w is not None:
                return list(w.get("params", []))
            info = self.fn_info.get(f"{t_name}_{m_name}")
            if info:
                return list(info.get("params", []))
            return None
        # plain function / declare (parser wraps the name in a 1-child target)
        if target_node.data == "normal_target" and len(target_node.children) == 1:
            first = target_node.children[0]
            f_name = str(first.children[0]) if isinstance(first, Tree) and first.children else str(first)
            info = self.fn_info.get(f_name)
            if info:
                return list(info.get("params", []))
            return None
        if target_node.data == "var_ref" and target_node.children:
            f_name = str(target_node.children[0])
            info = self.fn_info.get(f_name)
            if info:
                return list(info.get("params", []))
        return None
    def _reorder_named_arg_nodes(self, arg_children: list, target_node: Any) -> Optional[list]:
        """Turns an all-named argument list into the callee's positional order.

        Named arguments used to be emitted in source order, so
        ``calling f with b is 2, a is 1`` produced ``f(2, 1)``.  The result must
        be *positional*: a parameter the user skipped is filled with its declared
        default (``calling greet with times is 5`` needs the ``name`` slot).
        Returns None (leave the source order untouched) when the callee's
        parameter list cannot be resolved with certainty, or when a parameter
        without a default is missing (the checker reports that).
        """
        named = [c for c in arg_children
                 if isinstance(c, Tree) and c.data == "named_arg"]
        if not named or len(named) != len(arg_children):
            return None
        params = self._callee_params(target_node)
        if not params:
            return None
        by_name = {str(c.children[0]): c for c in named}
        param_names = [p[0] for p in params]
        if any(n not in param_names for n in by_name):
            return None
        ordered: List[Any] = []
        for p_name, _p_type, p_default in params:
            if p_name in by_name:
                # Uniform positional shape: the value node of the named arg.
                ordered.append(Tree("pos_arg", [by_name[p_name].children[1]]))
            elif p_default is not None:
                ordered.append(Tree("pos_arg", [p_default]))
            else:
                raise SemanticError(
                    f"Missing required argument '{p_name}'",
                    code="E0005",
                    help=f"Provide a value for parameter '{p_name}'.",
                )
        return ordered
    def _expr_is_string(self, node: Any, known_type: Optional[Type] = None) -> bool:
        """Returns True when an expression resolves to the PenguScript string type."""
        t = known_type
        if t is None:
            t = self._infer_node_type(node)
        if t is None:
            return False
        if isinstance(t, RefType):
            t = t.target
        return t.is_string()
    def _expr_location(self, node: Any) -> str:
        """Returns 'file.pengu:line' for an AST node (best-effort)."""
        line = self._node_line(node) or 0
        shown = self._display_path(self.current_source_file) or "<unknown>"
        return f"{shown}:{line}"
    @staticmethod
    def _unwrap_owned_type(t: Optional[Type]) -> Optional[Type]:
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
            if nxt is None or nxt is u:
                break
            u = nxt
        return u
    def _derived_type_c_name(self, t: Type) -> str:
        """Best C name for a user type used as a derived-concept field."""
        c = getattr(t, "c_name", None)
        n = getattr(t, "name", None) or str(t)
        for cand in (c, n):
            if cand and (cand in self.runes or cand in self.omens or cand in self.echos):
                return cand
        base = n.split("_")[0] if "_" in n else n
        for reg in (self.runes, self.omens, self.echos):
            if base in reg:
                return base
        return c or n
    @staticmethod
    def _derived_unwrap(t: Type) -> Type:
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            u = getattr(u, "target", None) or getattr(u, "underlying", None)
        return u
    def _type_owns_heap(self, t: Optional[Type], _depth: int = 0) -> bool:
        """True when a value of this type owns memory that must be released.

        Delegates to ``pengu_types.type_owns_heap`` with symbol resolution,
        and falls back to codegen's local ``self.omens`` definitions if needed.
        """
        if type_owns_heap(t, _depth=_depth, symbols=self.symbols):
            return True
        if isinstance(t, OmenType) and t.name in self.omens:
            v_dict = self.omens[t.name]
            for v_fields in v_dict.values():
                if isinstance(v_fields, dict):
                    if any(self._type_owns_heap(f, _depth + 1) for f in v_fields.values()):
                        return True
                elif v_fields is not None:
                    if self._type_owns_heap(v_fields, _depth + 1):
                        return True
        return False
    @staticmethod
    def _c_ident(name: str) -> str:
        if name in (
            "default", "case", "switch", "register", "goto", "volatile", "union", "enum", "struct", "auto",
            "long", "short", "int", "char", "float", "double", "signed", "unsigned", "void", "const",
            "static", "extern", "inline", "restrict", "return", "sizeof", "typedef",
            "if", "else", "while", "for", "do", "break", "continue", "asm",
            "NULL", "bool", "true", "false", "_Bool", "wchar_t", "FILE",
            "_Alignas", "_Alignof", "_Atomic", "_Generic", "_Noreturn", "_Static_assert", "_Thread_local",
        ):
            return f"_{name}"
        return name
    def _get_omen_variant_c_name(self, omen_name: str, variant_name: str) -> str:
        """Returns the C name emitted for an omen variant.

        Omens declared in a ``.d.pengu`` declaration file mirror a C enum from
        an included header: their C header already defines the enum constants
        under the *simple* variant names (e.g. ``KEY_LEFT``), so the type name
        must NOT be prefixed. Omens defined in normal ``.pengu`` modules are
        compiler-generated and keep the ``Omen_variant`` prefix to avoid
        collisions between different enums.

        Args:
            omen_name: Logical name of the omen.
            variant_name: Simple variant name as written in PenguScript.

        Returns:
            The C identifier to emit for this variant.
        """
        if omen_name in self.declaration_types:
            return variant_name
        return f"{omen_name}_{variant_name}"
    def _target_local_name(self, target: Any) -> Optional[str]:
        """Name of a plain local-variable `set` target, else None."""
        if isinstance(target, Token):
            return str(target) if getattr(target, "type", None) == "NAME" else None
        if isinstance(target, Tree):
            if target.data == "var_ref" and target.children:
                return str(target.children[0])
            if (target.data == "normal_target" and len(target.children) == 1
                    and isinstance(target.children[0], Token)):
                return str(target.children[0])
        return None
    @staticmethod
    def _expr_is_plain_var_ref(expr_node: Any, name: str) -> bool:
        """True when the rvalue is exactly the variable ``name`` (self-assign)."""
        node = expr_node
        while (isinstance(node, Tree) and node.data in ("paren_expr", "value_expr", "expr")
               and len(node.children) == 1):
            node = node.children[0]
        if isinstance(node, Token):
            return str(node) == name
        return (isinstance(node, Tree) and node.data == "var_ref"
                and node.children and str(node.children[0]) == name)
    def _lookup_field_type_on(self, base_t: Optional[Type], field_name: str) -> Optional[Type]:
        """Resolves the type of a field on base_t."""
        while isinstance(base_t, (RefType, AliasType, FrozenType, SealType)):
            if isinstance(base_t, (RefType, AliasType, FrozenType)):
                base_t = base_t.target
            elif isinstance(base_t, SealType):
                base_t = base_t.underlying
        if isinstance(base_t, BaseType) and self.symbols:
            sym_t = self.symbols.lookup_type(getattr(base_t, "name", ""))
            if sym_t and sym_t is not base_t:
                base_t = sym_t
                while isinstance(base_t, (RefType, AliasType, FrozenType, SealType)):
                    if isinstance(base_t, (RefType, AliasType, FrozenType)):
                        base_t = base_t.target
                    elif isinstance(base_t, SealType):
                        base_t = base_t.underlying
        if isinstance(base_t, (RuneType, EchoType)):
            fields = base_t.fields or self.runes.get(getattr(base_t, "name", ""), {}) or self.echos.get(getattr(base_t, "name", ""), {})
            c_fn = self._c_ident(field_name)
            return fields.get(field_name) or fields.get(c_fn)
        if isinstance(base_t, BaseType) and getattr(base_t, "name", "") in self.runes:
            fields = self.runes[base_t.name]
            c_fn = self._c_ident(field_name)
            return fields.get(field_name) or fields.get(c_fn)
        return None
    def _main_is_void(self) -> bool:
        """True when `weave main` is declared `into void` (no value to return)."""
        ret_type = self.main_return_type
        if ret_type is None:
            return True
        try:
            return CTypeMapper.to_c_type(ret_type).strip() == "void"
        except Exception:  # noqa: BLE001 - unknown type: assume it has a value
            return False
    def _is_ref_char_type(self, t: Optional[Type]) -> bool:
        """Returns True if the type is a raw C byte pointer.

        That is ``char*``, ``const char*`` (what a ``.d.pengu`` binding emits
        for C's ``const char*``) and the ``void*`` / ``const void*``
        catch-alls, since a C string literal converts to all of them.

        A `frozen` qualification counts too: string literals must keep
        converting to C string pointers there.
        """
        if t is None:
            return False
        curr = t
        while isinstance(curr, (AliasType, FrozenType)) and getattr(curr, "target", None):
            curr = curr.target
        if isinstance(curr, RefType):
            target = curr.target
            while isinstance(target, (AliasType, FrozenType)) and getattr(target, "target", None):
                target = target.target
            if isinstance(target, BaseType) and target.name in ("char", "const char", "void", "byte"):
                return True
        return False
    @staticmethod
    def _is_void_type(t: Any) -> bool:
        """True for a declared 'void' value type (never a 'None'/'any' unknown)."""
        if t is None or isinstance(t, AnyType):
            return False
        if t is VOID_TYPE:
            return True
        return str(getattr(t, "name", "")) == "void"
    def _get_current_with_target_type(self) -> Optional[Type]:
        """Returns the Type of the current with-target, or None."""
        if self.with_type_stack and self.with_type_stack[-1] is not None:
            return self.with_type_stack[-1]
        if self.with_stack:
            base_target = self.with_stack[-1]
            return self._lookup_var_type(base_target)
        return None
    def _emit_bounds_check(self, idx_code: str, base_code: str, base_t: Optional[Type], node: Any) -> str:
        """Wraps idx_code in a statement-expression with a bounds check.

        Checks are emitted in every profile unless bounds checking was disabled
        (``--release-unsafe``) or the access sits inside an ``unsafe:`` block
        (roadmap 5.2).  Returns the (possibly wrapped) index expression.
        """
        if not getattr(self, "bounds_check_enabled", True):
            return idx_code
        if getattr(self, "_unsafe_depth", 0) > 0:
            return idx_code
        loc = self._expr_location(node)
        loc_escaped = loc.replace("\\", "\\\\").replace('"', '\\"')
        actual_t = base_t.target if isinstance(base_t, RefType) else base_t
        if isinstance(actual_t, ArrayType) and actual_t.size is not None:
            len_expr = str(actual_t.size)
        elif isinstance(actual_t, (SliceType, ManyType, ListType)):
            sep = "->" if isinstance(base_t, RefType) else "."
            len_expr = f"({base_code}){sep}len"
        elif isinstance(actual_t, BaseType) and getattr(actual_t, "name", "") == "string":
            sep = "->" if isinstance(base_t, RefType) else "."
            len_expr = f"({base_code}){sep}len"
        else:
            return idx_code
        tmp = self.get_temp_name("_p_idx")
        if self.use_gnu_extensions:
            return (
                f"(__extension__({{ __auto_type {tmp} = ({idx_code}); "
                f"pengu_assert_bounds((int64_t){tmp}, (int64_t)({len_expr}), \"{loc_escaped}\"); {tmp}; }}))"
            )
        # Strict C99: hoist the declaration and the check, index through the
        # temp.  Indices are integers, so int64_t is a safe concrete type.
        return self._block_expr(
            [
                f"int64_t {tmp} = (int64_t)({idx_code});",
                f"pengu_assert_bounds({tmp}, (int64_t)({len_expr}), \"{loc_escaped}\");",
            ],
            tmp,
        )
