"""Release helpers (`banish`, payload release) and iteration values.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    ArrayType,
    BaseType,
    FrozenType,
    List,
    ListType,
    ManyType,
    MapType,
    MaybeType,
    OmenType,
    Optional,
    RefType,
    ResultType,
    RuneType,
    SealType,
    SliceType,
    Token,
    Tree,
    Type,
    type_has_derived_nexus,
)
from .ctype import (
    CTypeMapper,
)

class RuntimeMixin:
    """Release helpers (`banish`, payload release) and iteration values."""

    def _release_payload_stmts(self, t: Optional[Type], ptr_expr: str, ind: str = "",
                               deep: bool = False) -> str:
        """C statements releasing the *contents* of a value held at ``ptr_expr``.

        ``ptr_expr`` is a ``void*`` (the payload of a maybe/result box, a
        container element, …).  Returns an empty string for types that own
        nothing; never frees ``ptr_expr`` itself.

        ``deep`` is what a *derived Nexus* asks for: it recurses into the
        elements of a list/map so `banish json` releases the whole tree.  The
        default is shallow, the historical `banish` contract: a plain
        `banish list`/`banish maybe list` frees only the container, exactly as
        documented, because the caller may already have released the elements.
        """
        if t is None:
            return ""
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
            if nxt is None or nxt is u:
                break
            u = nxt
        if isinstance(u, BaseType) and u.name == "string":
            return f"{ind}pengu_banish_string((PenguString *)({ptr_expr}));"
        if isinstance(u, ListType) and not deep:
            # Shallow by default: the historical `banish list` contract.
            return f"{ind}pengu_banish_list((PenguList *)({ptr_expr}));"
        if isinstance(u, ListType):
            # A derived destructor is the one place where recursing is the
            # whole point: `banish json` must release the nested
            # strings/lists/runes of the tree, not just the outermost array.
            # Emit an element loop only when the element type actually owns
            # something, so a `list of int` stays a single free.
            elem_c = CTypeMapper.to_c_type(u.element)
            idx = self.get_temp_name("_li")
            lst = self.get_temp_name("_ll")
            inner = self._release_payload_stmts(
                u.element,
                f"((char *)({lst})->data + ((size_t){idx} * sizeof({elem_c})))",
                ind + "    ", deep=True)
            if not inner.strip():
                return f"{ind}pengu_banish_list((PenguList *)({ptr_expr}));"
            return (f"{ind}{{ PenguList *{lst} = (PenguList *)({ptr_expr});\n"
                    f"{ind}  for (int {idx} = 0; {idx} < {lst}->len; ++{idx}) {{\n"
                    f"{inner}\n"
                    f"{ind}  }}\n"
                    f"{ind}  pengu_banish_list({lst}); }}")
        if isinstance(u, MapType) and not deep:
            return f"{ind}pengu_banish_map((PenguMap *)({ptr_expr}));"
        if isinstance(u, MapType):
            # Same contract as a list: a derived destructor releases every key
            # and value payload the map references, then the map's own table.
            idx = self.get_temp_name("_mi")
            mp = self.get_temp_name("_mm")
            entry = self.get_temp_name("_me")
            key_inner = self._release_payload_stmts(
                u.key, f"{entry}->key", ind + "    ", deep=True)
            val_inner = self._release_payload_stmts(
                u.value, f"{entry}->val", ind + "    ", deep=True)
            if not key_inner.strip() and not val_inner.strip():
                return f"{ind}pengu_banish_map((PenguMap *)({ptr_expr}));"
            body = []
            if key_inner.strip():
                body.append(key_inner)
            if val_inner.strip():
                body.append(val_inner)
            inner = "\n".join(body)
            return (f"{ind}{{ PenguMap *{mp} = (PenguMap *)({ptr_expr});\n"
                    f"{ind}  for (int {idx} = 0; {idx} < {mp}->cap; ++{idx}) {{\n"
                    f"{ind}    PenguMapEntry *{entry} = &{mp}->entries[{idx}];\n"
                    f"{ind}    if (!{entry}->occupied) continue;\n"
                    f"{inner}\n"
                    f"{ind}  }}\n"
                    f"{ind}  pengu_banish_map({mp}); }}")
        if isinstance(u, ArrayType) and u.size is not None:
            idx = self.get_temp_name("_ri")
            inner = self._release_payload_stmts(
                u.element,
                f"((char *)({ptr_expr})) + ({idx} * sizeof({CTypeMapper.to_c_type(u.element)}))",
                ind + "  ", deep=deep)
            if not inner.strip():
                return ""
            return (f"{ind}for (size_t {idx} = 0; {idx} < {u.size}; ++{idx}) {{\n"
                    f"{inner}\n{ind}}}")
        if isinstance(u, MaybeType):
            # The box expression must be materialised *before* recursing: the
            # old code built the inner statements from '{ptr_expr}_m->value',
            # which produced invalid C ('x.value_m->value') whenever ptr_expr
            box = self.get_temp_name("_mb")
            inner = self._release_payload_stmts(u.element, f"{box}->value", ind + "  ", deep=deep)
            body = f"{inner}\n" if inner.strip() else ""
            return (f"{ind}{{ PenguMaybe *{box} = (PenguMaybe *)({ptr_expr});\n"
                    f"{ind}  if ({box}->is_present && {box}->value) {{\n"
                    f"{body}"
                    f"{ind}    free({box}->value); {box}->value = NULL; }}\n"
                    f"{ind}  {box}->is_present = false; }}")
        if isinstance(u, ResultType):
            # Only the active side (ok_val xor err_val) owns a payload box.
            box = self.get_temp_name("_rb")
            ok_inner = self._release_payload_stmts(u.ok_type, f"{box}->ok_val", ind + "    ", deep=deep)
            err_inner = self._release_payload_stmts(u.err_type, f"{box}->err_val", ind + "    ", deep=deep)
            ok_body = f"{ok_inner}\n" if ok_inner.strip() else ""
            err_body = f"{err_inner}\n" if err_inner.strip() else ""
            return (f"{ind}{{ PenguResult *{box} = (PenguResult *)({ptr_expr});\n"
                    f"{ind}  if ({box}->is_ok) {{\n"
                    f"{ind}    if ({box}->ok_val) {{\n"
                    f"{ok_body}"
                    f"{ind}      free({box}->ok_val); {box}->ok_val = NULL; }} }}\n"
                    f"{ind}  else {{\n"
                    f"{ind}    if ({box}->err_val) {{\n"
                    f"{err_body}"
                    f"{ind}      free({box}->err_val); {box}->err_val = NULL; }} }}\n"
                    f"{ind}  }}")
        if isinstance(u, RuneType):
            cleanup = self._element_cleanup_fn(u)
            if cleanup is not None:
                return f"{ind}{cleanup}((void *)({ptr_expr}));"
            return ""
        if isinstance(u, OmenType):
            # Algebraic omens own the payload of their active variant; the
            # user-declared destructor ('derive Nexus') releases it.  A simple
            # omen is a bare enum with nothing to release.
            if not u.is_algebraic:
                return ""
            cleanup = self._element_cleanup_fn(u)
            if cleanup is not None:
                return f"{ind}{cleanup}((void *)({ptr_expr}));"
            return ""
        return ""
    def _emit_iteration_value(self, list_tmp: str, elem_c: str, val: str,
                              elem_t: Optional[Type] = None, val_node: Any = None) -> List[str]:
        """Emits the push of a loop iteration value.

        ``pengu_list_push`` copies the element bytes with ``memcpy``; it never
        clones a heap payload.  Releasing a temporary that only the list
        references is therefore the programmer's job, not the compiler's.
        """
        ind = self.indent()
        tmp_val = self.get_temp_name("_lv")
        decl_c = CTypeMapper.to_c_decl(elem_t, tmp_val) if elem_t is not None else f"{elem_c} {tmp_val}"
        return [
            f"{ind}{decl_c} = {val};",
            f"{ind}pengu_list_push(&{list_tmp}, &{tmp_val});"
        ]
    def _banish_wrapper_stmts(self, t: Type, ptr: str) -> List[str]:
        """Statements releasing a maybe/result value held at ``ptr`` (a ``T *``).

        The wrapper owns its payload box, so an explicit ``banish m`` releases
        the payload first and the box after.  Nothing calls this implicitly: it
        is the lowering of a ``banish`` the programmer wrote.
        """
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
            if nxt is None or nxt is u:
                break
            u = nxt
        if isinstance(u, MaybeType):
            inner = self._release_payload_stmts(u.element, f"({ptr})->value", "  ")
            lines: List[str] = [f"if (({ptr})->is_present && ({ptr})->value) {{"]
            if inner.strip():
                lines.extend(inner.splitlines())
            lines.append(f"  free(({ptr})->value); ({ptr})->value = NULL;")
            lines.append("}")
            lines.append(f"({ptr})->is_present = false;")
            return lines
        if isinstance(u, ResultType):
            inner = self._release_payload_stmts(u, ptr, "")
            return inner.splitlines() if inner.strip() else []
        return []
    def _translate_banish_target(self, target_expr: Any, stmt_context: bool = False) -> str:
        """Translates banish target into appropriate runtime free call according to type.

        ``stmt_context`` selects real statements instead of a GNU statement
        expression when the lowering needs more than one line (banishing a
        maybe/result releases the payload and the box).
        """
        # Grouping parentheses are not part of the target: 'banish (xs at 0)'
        # names the same storage cell as 'banish xs at 0'.  Without this the
        # element path below would copy the element into a temporary and banish
        # the *copy*, leaving the real element untouched.
        bare_target = target_expr
        while (isinstance(bare_target, Tree)
               and bare_target.data in ("paren_expr", "value_expr", "expr", "primary")
               and len(bare_target.children) == 1):
            bare_target = bare_target.children[0]
        target_str = self._translate_expr(target_expr)
        t = self._infer_node_type(target_expr)
        if t is None:
            if isinstance(bare_target, Tree) and bare_target.data == "var_ref":
                t = self._lookup_var_type(str(bare_target.children[0]))
            elif isinstance(bare_target, Token):
                t = self._lookup_var_type(str(bare_target))
            elif isinstance(bare_target, Tree) and bare_target.data == "at_expr":
                # `banish xs at i` frees the *element*, and for a `list of ref
                # to T` that element is the pointer itself.  Inference on the
                # synthetic `pengu_list_at(...)` expression has no type, so
                # resolve the chain from the container instead: without this the
                # pointer branch below took the address of the list slot and
                # freed it (invalid free).
                t = self._resolve_at_chain_type(bare_target)
            elif isinstance(bare_target, Tree) and bare_target.data in ("field_access", "arrow_access"):
                # `banish a._blocks` releases the *field value*.  Inference has
                # no type for a field access either, and the old fall-through
                # took `&(a._blocks)` and passed it to `pengu_banish`, freeing a
                # stack address.  Resolve the field type explicitly.
                if bare_target.data == "arrow_access":
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        t = self.runes.get(t_name, {}).get(str(bare_target.children[1]))
                else:
                    b_node = bare_target.children[0]
                    b_name = str(b_node.children[0]) if isinstance(b_node, Tree) and b_node.data == "var_ref" else str(b_node)
                    b_type = self._lookup_var_type(b_name)
                    while isinstance(b_type, RefType):
                        b_type = b_type.target
                    if b_type is not None and hasattr(b_type, "name"):
                        t = self.runes.get(b_type.name, {}).get(str(bare_target.children[1]))

        actual_t = t
        while isinstance(actual_t, (FrozenType, AliasType, SealType)):
            if isinstance(actual_t, (FrozenType, AliasType)) and getattr(actual_t, "target", None):
                actual_t = actual_t.target
            elif isinstance(actual_t, SealType):
                actual_t = actual_t.underlying
            else:
                break
        is_str = isinstance(actual_t, BaseType) and actual_t.name == "string"
        is_lst = isinstance(actual_t, ListType)
        is_map = isinstance(actual_t, MapType)

        is_lvalue = (
            target_str.startswith("&")
            or isinstance(actual_t, RefType)
            or target_str.isidentifier()
            or (isinstance(bare_target, Tree) and bare_target.data in (
                "var_ref", "field_access", "dot_access", "arrow_access",
                "essence_of", "at_expr", "array_at_expr", "slice_at_expr",
                "normal_target", "at_access"))
        )
        if not is_lvalue and not (target_str.startswith("&") or isinstance(actual_t, RefType)):
            tmp_banish = self.get_temp_name("_btmp")
            c_decl = CTypeMapper.to_c_decl(actual_t, tmp_banish) if actual_t else f"__auto_type {tmp_banish}"
            if is_str:
                return f"(__extension__({{ {c_decl} = ({target_str}); pengu_banish_string(&{tmp_banish}); }}))"
            elif is_lst:
                return f"(__extension__({{ {c_decl} = ({target_str}); pengu_banish_list(&{tmp_banish}); }}))"
            elif is_map:
                return f"(__extension__({{ {c_decl} = ({target_str}); pengu_banish_map(&{tmp_banish}); }}))"
            return f"(__extension__({{ {c_decl} = ({target_str}); pengu_banish((void*){tmp_banish}); }}))"

        ptr = target_str if (target_str.startswith("&") or isinstance(actual_t, RefType)) else (f"&{target_str}" if target_str.isidentifier() else f"&({target_str})")

        if is_str:
            return f"pengu_banish_string({ptr})"
        elif is_lst:
            return f"pengu_banish_list({ptr})"
        elif is_map:
            return f"pengu_banish_map({ptr})"
        elif isinstance(actual_t, (MaybeType, ResultType)):
            lines = self._banish_wrapper_stmts(actual_t, ptr)
            if stmt_context:
                return "\n".join(lines)
            if not self.use_gnu_extensions:
                # Strict C99: hoist the statements and let the caller see the
                # (side-effect-only) expression result.
                for line in lines:
                    self._hoist(line)
                return "((void)0)"
            return "(__extension__(({ " + " ".join(lines) + " })))"
        elif type_has_derived_nexus(actual_t, self.symbols):
            # Try a UserType with 'derive Nexus' owns heap fields; its generated
            # destructor (idempotent: runtime banish helpers null the buffers)
            # releases them without freeing the stack value itself.
            return f"{self._rune_cleanup_helper(actual_t)}({ptr})"
        # 'ref to T' frees the pointed-to allocation; when T owns heap fields its
        # destructor must run first or every field leaks (the pointee struct is
        # freed below either way).
        if isinstance(actual_t, RefType):
            pointee = actual_t.target
            while isinstance(pointee, (FrozenType, AliasType, SealType)):
                nxt = getattr(pointee, "target", None) or getattr(pointee, "underlying", None)
                if nxt is None or nxt is pointee:
                    break
                pointee = nxt
            if type_has_derived_nexus(pointee, self.symbols):
                return (f"(__extension__(({{ {self._rune_cleanup_helper(pointee)}((void*)({ptr})); "
                        f"pengu_banish((void*)({ptr})); }})))")
        return f"pengu_banish((void*)({ptr}))"
    def _resolve_at_chain_type(self, node: Tree) -> Optional[Type]:
        """Element type of an ``at_expr`` chain, or ``None`` when unknown.

        Banish needs the element type to choose between ``pengu_banish`` (a
        pointer element), ``pengu_banish_string`` (a string element) and a rune
        destructor.  ``_infer_node_type`` cannot infer the lowered
        ``pengu_list_at`` expression, so walk the chain here.
        """
        from .ast_utils import flatten_at_chain

        parts = flatten_at_chain(node)
        if not parts:
            return None
        base_node = parts[0]
        t: Optional[Type] = None
        if isinstance(base_node, Tree) and base_node.data == "var_ref":
            t = self._lookup_var_type(str(base_node.children[0]))
        elif isinstance(base_node, Tree) and base_node.data in ("field_access", "arrow_access"):
            if base_node.data == "arrow_access":
                if self.current_enchanted_type is not None:
                    t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                    t = self.runes.get(t_name, {}).get(str(base_node.children[1]))
            else:
                b_node = base_node.children[0]
                b_name = str(b_node.children[0]) if isinstance(b_node, Tree) and b_node.data == "var_ref" else str(b_node)
                b_type = self._lookup_var_type(b_name)
                while isinstance(b_type, RefType):
                    b_type = b_type.target
                if b_type is not None and hasattr(b_type, "name"):
                    t = self.runes.get(b_type.name, {}).get(str(base_node.children[1]))
        if t is None:
            t = self._infer_node_type(base_node)
        for _ in parts[1:]:
            t = self._unwrap_container_alias(t)
            if isinstance(t, RefType):
                target = t.target
                t = target if isinstance(target, (ListType, SliceType, ManyType, ArrayType)) else target
            if isinstance(t, (ListType, SliceType, ManyType)):
                t = t.element
            elif isinstance(t, ArrayType):
                t = t.element
            elif isinstance(t, MapType):
                t = t.value
            elif isinstance(t, BaseType) and t.name == "string":
                t = BaseType("string")
            else:
                return None
        return t

    def _value_sizeof(self, t: Optional[Type]) -> str:
        """C ``sizeof`` expression for one value of ``t`` (arrays included).

        ``CTypeMapper.to_c_type`` decays a fixed array to a pointer, so
        ``sizeof`` of it would under-allocate a payload box; multiply the
        element size explicitly instead.
        """
        u = self._unwrap_owned_type(t)
        if isinstance(u, ArrayType) and u.size is not None:
            return f"(sizeof({CTypeMapper.to_c_type(u.element)}) * {u.size})"
        return f"sizeof({CTypeMapper.to_c_type(t)})"
    def _element_cleanup_fn(self, t: Optional[Type]) -> Optional[str]:
        """Name of the *user-declared* destructor for ``t``, or ``None``.

        PenguScript never derives ``Nexus`` implicitly: a rune or algebraic omen
        only has a destructor when it writes ``derive Nexus`` (or binds the
        concept explicitly).  Everything else is released field by field by
        :meth:`_release_payload_stmts`.
        """
        if t is None:
            return None
        unwrapped = t
        while isinstance(unwrapped, (AliasType, FrozenType, SealType)):
            nxt = getattr(unwrapped, "target", None) or getattr(unwrapped, "underlying", None)
            if nxt is None or nxt is unwrapped:
                break
            unwrapped = nxt
        if isinstance(unwrapped, (RuneType, OmenType)):
            is_omen = isinstance(unwrapped, OmenType)
            if is_omen and not unwrapped.is_algebraic:
                return None
            derived = list(getattr(unwrapped, "derived_concepts", []) or [])
            base_n = (unwrapped.get_base_name() if hasattr(unwrapped, "get_base_name")
                      else unwrapped.name.split("_")[0])
            if self.symbols:
                store = getattr(self.symbols, "omens" if is_omen else "runes", {})
                if base_n in store:
                    derived.extend(getattr(store[base_n], "derived_concepts", []) or [])
            # Runes/omens imported from another module carry no local
            # derived_concepts; fall back to the global concept bindings emitted
            # by an explicit 'derive Nexus'.
            if self.symbols is not None and hasattr(self.symbols, "concept_bindings"):
                for key in ((unwrapped.name, "Nexus"), (base_n, "Nexus")):
                    if key in self.symbols.concept_bindings:
                        derived.append("Nexus")
                        break
            if "Nexus" in derived or self._rune_derives_explicitly(unwrapped, "Nexus"):
                return self._rune_cleanup_helper(unwrapped)
        return None
