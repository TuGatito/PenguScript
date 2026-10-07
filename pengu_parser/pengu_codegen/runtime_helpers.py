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
    MapType,
    MaybeType,
    OmenType,
    Optional,
    RefType,
    ResultType,
    RuneType,
    SealType,
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

    def _release_payload_stmts(self, t: Optional[Type], ptr_expr: str, ind: str = "") -> str:
        """C statements releasing the *contents* of a value held at ``ptr_expr``.

        ``ptr_expr`` is a ``void*`` (the payload of a maybe/result box, a
        container element, …).  Returns an empty string for types that own
        nothing; never frees ``ptr_expr`` itself.
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
        if isinstance(u, ListType):
            return f"{ind}pengu_banish_list((PenguList *)({ptr_expr}));"
        if isinstance(u, MapType):
            return f"{ind}pengu_banish_map((PenguMap *)({ptr_expr}));"
        if isinstance(u, ArrayType) and u.size is not None:
            idx = self.get_temp_name("_ri")
            inner = self._release_payload_stmts(
                u.element, f"((char *)({ptr_expr})) + ({idx} * sizeof({CTypeMapper.to_c_type(u.element)}))", ind + "  ")
            if not inner.strip():
                return ""
            return (f"{ind}for (size_t {idx} = 0; {idx} < {u.size}; ++{idx}) {{\n"
                    f"{inner}\n{ind}}}")
        if isinstance(u, MaybeType):
            # The box expression must be materialised *before* recursing: the
            # old code built the inner statements from '{ptr_expr}_m->value',
            # which produced invalid C ('x.value_m->value') whenever ptr_expr
            box = self.get_temp_name("_mb")
            inner = self._release_payload_stmts(u.element, f"{box}->value", ind + "  ")
            body = f"{inner}\n" if inner.strip() else ""
            return (f"{ind}{{ PenguMaybe *{box} = (PenguMaybe *)({ptr_expr});\n"
                    f"{ind}  if ({box}->is_present && {box}->value) {{\n"
                    f"{body}"
                    f"{ind}    free({box}->value); {box}->value = NULL; }}\n"
                    f"{ind}  {box}->is_present = false; }}")
        if isinstance(u, ResultType):
            # Only the active side (ok_val xor err_val) owns a payload box.
            box = self.get_temp_name("_rb")
            ok_inner = self._release_payload_stmts(u.ok_type, f"{box}->ok_val", ind + "    ")
            err_inner = self._release_payload_stmts(u.err_type, f"{box}->err_val", ind + "    ")
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
