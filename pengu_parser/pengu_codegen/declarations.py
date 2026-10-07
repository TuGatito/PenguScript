"""Collection of the top-level declarations of every module.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    AnyType,
    BaseType,
    CVarArgsType,
    ConceptType,
    Dict,
    EchoType,
    List,
    ListType,
    MapType,
    MaybeType,
    OmenType,
    Optional,
    ResultType,
    RuneType,
    SliceType,
    Token,
    Tree,
    Tuple,
    Type,
    TypeParam,
    VOID_TYPE,
    _dce_collect_refs,
    ast_to_type,
    eval_comptime,
    get_type_base_name,
    os,
)
from .ast_utils import (
    _extract_attributes_from_node,
    skip_weave_modifiers,
    unwrap_top_level,
)

class CollectMixin:
    """Collection of the top-level declarations of every module."""

    def collect_declarations(self, trees: List[Tuple[str, Tree]]) -> None:
        """Two-pass declarations collection to resolve forward and circular references.

        Pass 1: Registers all type and function names.
        Pass 2: Populates complete field definitions and signatures.

        Args:
            trees: List of (module_filepath, AST_tree) tuples in topological order.
        """
        if self.compile_env is not None:
            self.debug_mode = bool(getattr(self.compile_env, "is_debug", False))
            if not hasattr(self, "_unsafe_depth"):
                self._unsafe_depth = 0
        top_stmts: List[Tuple[Tree, str]] = []
        for filepath, tree in trees:
            for node in tree.children:
                if not isinstance(node, Tree):
                    continue
                if node.data == "file":
                    for top_node in node.children:
                        if isinstance(top_node, Tree):
                            top_stmts.append((top_node, filepath))
                elif node.data == "top_stmt":
                    top_stmts.append((node, filepath))

        # Resolve top-level compile-time 'when' blocks before collection.
        top_stmts = self._expand_when_top_stmts(top_stmts)

        # Split integrated unit tests out of the declaration pipeline: tests are
        # only emitted when generate_bundle() is called in test mode.
        kept_stmts: List[Tuple[Tree, str]] = []
        for tnode, tfile in top_stmts:
            inner = unwrap_top_level(tnode)
            if isinstance(inner, Tree) and inner.data == "test_decl":
                # Exclude internal unit tests from imported stdlib modules unless
                # the std module itself is the entry file being tested directly.
                norm_tf = os.path.normcase(os.path.abspath(tfile)) if tfile else ""
                entry_f = getattr(self, "entry_file", None)
                if not entry_f and self.import_order:
                    entry_f = self.import_order[-1]
                is_entry = False
                if entry_f and norm_tf:
                    try:
                        is_entry = (norm_tf == os.path.normcase(os.path.abspath(entry_f)))
                    except Exception:
                        is_entry = False

                is_std = False
                if norm_tf:
                    parts = norm_tf.replace("/", "\\").split("\\")
                    if "std" in parts and "tests" not in parts and "std_programs" not in parts:
                        is_std = True

                if is_std and not is_entry:
                    continue

                name_tok = inner.children[0]
                raw_name = str(name_tok)
                if raw_name.startswith('r"""') and raw_name.endswith('"""'):
                    display_name = raw_name[4:-3]
                elif raw_name.startswith('"""') and raw_name.endswith('"""'):
                    display_name = raw_name[3:-3]
                elif raw_name.startswith('r"') and raw_name.endswith('"'):
                    display_name = raw_name[2:-1]
                elif raw_name.startswith('"') and raw_name.endswith('"'):
                    display_name = raw_name[1:-1]
                else:
                    display_name = raw_name
                body_nodes = [c for c in inner.children[1:] if isinstance(c, Tree)]
                self.tests.append({
                    "name": display_name,
                    "name_token": name_tok,
                    "body_stmts": body_nodes,
                    "filepath": tfile,
                    "line": self._node_line(inner),
                })
            else:
                kept_stmts.append((tnode, tfile))
        top_stmts = kept_stmts

        # Pass 1: Register names (skipping generic templates)
        cur_file = None
        cur_insignia = None
        for top_node, filepath in top_stmts:
            if filepath != cur_file:
                cur_file = filepath
                cur_insignia = None
            stmt = unwrap_top_level(top_node)
            if not isinstance(stmt, Tree):
                continue
            rule = stmt.data
            if rule == "insignia_stmt":
                cur_insignia = str(stmt.children[0])
                continue
            has_shards = any(isinstance(c, Tree) and c.data == "shard_params" for c in stmt.children)
            if has_shards:
                continue
            if rule == "rune_decl":
                r_attrs, r_idx = _extract_attributes_from_node(stmt.children)
                name = str(stmt.children[r_idx])
                c_name = f"{cur_insignia}{name}" if cur_insignia else name
                self.runes[c_name] = {}
                self.rune_attributes[c_name] = r_attrs
            elif rule == "echo_decl":
                e_attrs, e_idx = _extract_attributes_from_node(stmt.children)
                name = str(stmt.children[e_idx])
                c_name = f"{cur_insignia}{name}" if cur_insignia else name
                self.echos[c_name] = {}
                self.rune_attributes[c_name] = e_attrs
            elif rule == "omen_decl":
                name = str(stmt.children[0])
                c_name = f"{cur_insignia}{name}" if cur_insignia else name
                self.omens[c_name] = {}
            elif rule == "alias_decl":
                name = str(stmt.children[0])
                c_name = f"{cur_insignia}{name}" if cur_insignia else name
                self.aliases[c_name] = VOID_TYPE

        # Pass 2: Populate definitions
        cur_file = None
        cur_insignia = None
        for top_node, filepath in top_stmts:
            if filepath != cur_file:
                cur_file = filepath
                cur_insignia = None
            stmt = unwrap_top_level(top_node)
            if isinstance(stmt, Tree) and stmt.data == "insignia_stmt":
                cur_insignia = str(stmt.children[0])
                continue
            self._collect_top_stmt(top_node, filepath, prefix=cur_insignia)

        # Pass 3: Collect monomorphized types and functions from symbol table
        if self.symbols:
            for m_name, m_type in self.symbols.monomorphized_types.items():
                if m_name in self.symbols._generated_instances:
                    continue
                self.symbols._generated_instances.add(m_name)
                if isinstance(m_type, RuneType) and m_name not in self.runes:
                    self.runes[m_name] = m_type.fields
                elif isinstance(m_type, EchoType) and m_name not in self.echos:
                    self.echos[m_name] = m_type.fields
                elif isinstance(m_type, OmenType) and m_name not in self.omens:
                    self.omens[m_name] = m_type.variants
                elif isinstance(m_type, AliasType) and m_name not in self.aliases:
                    self.aliases[m_name] = m_type.target

            while True:
                added = False
                for m_fn_name, (fn_ast, subst_map) in list(self.symbols.monomorphized_functions.items()):
                    if m_fn_name in self.symbols._generated_instances:
                        continue
                    self.symbols._generated_instances.add(m_fn_name)
                    if not any(w["c_name"] == m_fn_name for w in self.weaves):
                        self._collect_monomorphized_weave(m_fn_name, fn_ast, subst_map, None, filepath=".")
                        added = True

                for m_m_name, entry in list(self.symbols.monomorphized_methods.items()):
                    if m_m_name in self.symbols._generated_instances:
                        continue
                    self.symbols._generated_instances.add(m_m_name)
                    if len(entry) == 3:
                        m_ast, subst_map, rec_type = entry
                    else:
                        m_ast, subst_map = entry
                        parts = m_m_name.rsplit("_", 1)
                        rec_tname = parts[0]
                        rec_type = self.symbols.lookup_type(rec_tname) or RuneType(name=rec_tname)
                    if not any(w["c_name"] == m_m_name for w in self.weaves):
                        self._collect_monomorphized_weave(m_m_name, m_ast, subst_map, rec_type, filepath=".")
                        added = True
                if not added:
                    break

        # Pass 4: register lambda expressions found in weave/test bodies. They
        # become top-level 'static' C functions, so they must be collected before
        # any body is translated.
        for w in self.weaves:
            for st in w.get("body_stmts", []):
                self._register_lambdas_in(st, src_file=w.get("filepath"))
        for t in self.tests:
            for st in t.get("body_stmts", []):
                self._register_lambdas_in(st, src_file=t.get("filepath"))
    def _collect_top_stmt(self, top_node: Tree, filepath: str, prefix: Optional[str] = None) -> None:
        """Dispatches top-level statement collection."""
        stmt = unwrap_top_level(top_node)
        if not isinstance(stmt, Tree):
            return

        rule = stmt.data
        has_shards = any(isinstance(c, Tree) and c.data == "shard_params" for c in stmt.children)

        if rule == "rune_decl":
            if has_shards:
                return
            r_attrs, r_idx = _extract_attributes_from_node(stmt.children)
            name = str(stmt.children[r_idx])
            c_name = f"{prefix}{name}" if prefix else name
            self.rune_attributes[c_name] = r_attrs
            fields = {}
            field_attrs = {}
            for f in stmt.children[r_idx+1:]:
                if isinstance(f, Tree) and f.data == "field_decl":
                    f_attrs, f_idx = _extract_attributes_from_node(f.children)
                    f_name = str(f.children[f_idx])
                    f_type = ast_to_type(f.children[f_idx+1], self._lookup_type_fn)
                    fields[f_name] = f_type
                    field_attrs[f_name] = f_attrs
            self.runes[c_name] = fields
            self.rune_field_attributes[c_name] = field_attrs
            self._rune_file_paths[c_name] = filepath or ""
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_types.add(c_name)

        elif rule == "echo_decl":
            if has_shards:
                return
            e_attrs, e_idx = _extract_attributes_from_node(stmt.children)
            name = str(stmt.children[e_idx])
            c_name = f"{prefix}{name}" if prefix else name
            self.rune_attributes[c_name] = e_attrs
            fields = {}
            field_attrs = {}
            for f in stmt.children[e_idx+1:]:
                if isinstance(f, Tree) and f.data == "field_decl":
                    f_attrs, f_idx = _extract_attributes_from_node(f.children)
                    f_name = str(f.children[f_idx])
                    f_type = ast_to_type(f.children[f_idx+1], self._lookup_type_fn)
                    fields[f_name] = f_type
                    field_attrs[f_name] = f_attrs
            self.echos[c_name] = fields
            self.rune_field_attributes[c_name] = field_attrs
            self._rune_file_paths[c_name] = filepath or ""
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_types.add(c_name)

        elif rule == "omen_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            variants = {}
            for v in stmt.children[1:]:
                if isinstance(v, Tree) and v.data == "omen_variant":
                    v_name = str(v.children[0])
                    v_fields = {}
                    for f in v.children[1:]:
                        if isinstance(f, Tree) and f.data == "omen_field":
                            f_name = str(f.children[0])
                            f_type = ast_to_type(f.children[1], self._lookup_type_fn)
                            v_fields[f_name] = f_type
                    variants[v_name] = v_fields
            self.omens[c_name] = variants
            self._rune_file_paths[c_name] = filepath or ""
            omen_t = (self.symbols.omens.get(name) or self.symbols.omens.get(c_name)) if self.symbols else None
            if omen_t and hasattr(omen_t, "variant_values") and omen_t.variant_values:
                self.omen_values[c_name] = dict(omen_t.variant_values)
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_types.add(c_name)

        elif rule == "alias_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            rem_children = [c for c in stmt.children[1:] if c is not None]
            target_t = ast_to_type(rem_children[0], self._lookup_type_fn)
            self.aliases[c_name] = target_t
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_types.add(c_name)

        elif rule == "seal_decl":
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            underlying_t = ast_to_type(stmt.children[1], self._lookup_type_fn)
            self.seals[c_name] = underlying_t
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_types.add(c_name)

        elif rule == "concept_decl":
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            self.concepts[c_name] = ConceptType(name=c_name)

        elif rule == "bind_decl":
            bound_type = ast_to_type(stmt.children[0], self._lookup_type_fn)
            for w in stmt.children[2:]:
                if isinstance(w, Tree) and w.data == "weave_decl":
                    self._collect_weave(w, filepath, bound_type, prefix=prefix)

        elif rule == "const_decl":
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            c_type = None
            expr_idx = 1
            if len(stmt.children) == 3:
                if stmt.children[1] is not None:
                    c_type = ast_to_type(stmt.children[1], self._lookup_type_fn)
                expr_idx = 2
            expr_node = stmt.children[expr_idx]
            val = self.const_folder.fold(expr_node)
            if (c_type is None or isinstance(c_type, AnyType)) and self.symbols:
                sym = self.symbols.lookup(name)
                if sym and sym.type and not isinstance(sym.type, AnyType):
                    c_type = sym.type
            self.consts[c_name] = (c_type, val)
            self.const_nodes[c_name] = expr_node
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_consts.add(c_name)
            if filepath:
                norm_fp = os.path.abspath(filepath)
                norm_order = [os.path.abspath(p) for p in self.import_order]
                if len(norm_order) > 1 and norm_fp != norm_order[-1]:
                    is_std = "std" in norm_fp.replace("/", "\\").split("\\")
                    if is_std:
                        bname = os.path.basename(norm_fp)
                        if bname.endswith(".d.pengu"):
                            mod_name = bname[:-8]
                        elif bname.endswith(".pengu"):
                            mod_name = bname[:-6]
                        else:
                            mod_name = os.path.splitext(bname)[0]
                        if mod_name and not name.startswith(f"{mod_name}_"):
                            self.consts[f"{mod_name}_{name}"] = (c_type, val)
                            self.const_nodes[f"{mod_name}_{name}"] = expr_node
                            if filepath.endswith(".d.pengu"):
                                self.declaration_consts.add(f"{mod_name}_{name}")

        elif rule == "declare_stmt":
            if any(isinstance(c, Tree) and c.data == "shard_params" for c in stmt.children):
                return
            _, is_ritual, idx = skip_weave_modifiers(stmt.children)
            fn_name = str(stmt.children[idx])
            idx += 1
            c_fn_name = f"{prefix}{fn_name}" if prefix else fn_name
            rem_children = [c for c in stmt.children[idx:] if c is not None]
            params = []
            ret_type = VOID_TYPE
            for child_n in rem_children:
                if isinstance(child_n, Tree) and child_n.data in ("param_list", "declare_params"):
                    for p in child_n.children:
                        if isinstance(p, Tree) and p.data == "param":
                            pn = str(p.children[0])
                            pt = ast_to_type(p.children[1], self._lookup_type_fn) if len(p.children) >= 2 else AnyType()
                            pd = p.children[2] if len(p.children) >= 3 else None
                            params.append((pn, pt, pd))
                        elif (isinstance(p, Token) and (p.type in ("VARARGS", "_VARARGS") or str(p) == "...")) or (isinstance(p, Tree) and p.data in ("varargs", "_varargs")):
                            params.append(("_varargs", CVarArgsType(), None))
                elif isinstance(child_n, Tree) and child_n.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type"):
                    ret_type = ast_to_type(child_n, self._lookup_type_fn)
                elif isinstance(child_n, Token) and child_n.type == "NAME":
                    ret_type = ast_to_type(child_n, self._lookup_type_fn)
            self.fn_info[fn_name] = {"c_name": c_fn_name, "params": params, "return_type": ret_type, "is_ritual": is_ritual}
            self.fn_info[c_fn_name] = {"c_name": c_fn_name, "params": params, "return_type": ret_type, "is_ritual": is_ritual}

        elif rule == "include_stmt":
            inc_val = str(stmt.children[0]).strip('"')
            if inc_val not in self.includes:
                self.includes.append(inc_val)

        elif rule == "link_stmt":
            link_val = str(stmt.children[0]).strip('"')
            if link_val not in self.links:
                self.links.append(link_val)

        elif rule == "weave_decl":
            if any(isinstance(c, Tree) and c.data == "shard_params" for c in stmt.children):
                return
            self._collect_weave(stmt, filepath, None, prefix=prefix)

        elif rule == "enchanting_decl":
            type_node = stmt.children[0]
            enchanted_type = ast_to_type(type_node, self._lookup_type_fn)
            base_tname = get_type_base_name(enchanted_type)
            type_params_of_receiver = []
            if self.symbols and base_tname in self.symbols.generic_runes:
                type_params_of_receiver = list(self.symbols.generic_runes[base_tname][0])
            elif getattr(enchanted_type, "type_params", None):
                type_params_of_receiver = list(enchanted_type.type_params)
            elif any(isinstance(t, TypeParam) for t in getattr(enchanted_type, "type_args", [])):
                type_params_of_receiver = [t.name for t in enchanted_type.type_args if isinstance(t, TypeParam)]

            if type_params_of_receiver:
                for w in stmt.children[1:]:
                    if isinstance(w, Tree) and w.data == "weave_decl":
                        if self.symbols:
                            _, _, m_idx = skip_weave_modifiers(w.children)
                            m_name = str(w.children[m_idx])
                            m_tparams = []
                            for c in w.children:
                                if isinstance(c, Tree) and c.data == "shard_params":
                                    m_tparams.extend([str(x) for x in c.children if isinstance(x, Token) and x.type == "NAME"])
                                    break
                            self.symbols.generic_methods[(base_tname, m_name)] = (list(type_params_of_receiver), m_tparams, w)
                return
            for w in stmt.children[1:]:
                if isinstance(w, Tree) and w.data == "weave_decl":
                    has_method_shards = any(
                        isinstance(c, Tree) and c.data == "shard_params" for c in w.children
                    )
                    if has_method_shards:
                        if self.symbols:
                            _, _, m_idx = skip_weave_modifiers(w.children)
                            m_name = str(w.children[m_idx])
                            m_tparams = []
                            for c in w.children:
                                if isinstance(c, Tree) and c.data == "shard_params":
                                    m_tparams = [str(x) for x in c.children if isinstance(x, Token) and x.type == "NAME"]
                                    break
                            self.symbols.generic_methods[(base_tname, m_name)] = ([], m_tparams, w)
                        continue
                    self._collect_weave(w, filepath, enchanted_type, prefix=prefix)
    def _collect_monomorphized_weave(self, specialized_name: str, node: Tree, subst_map: Dict[str, Type], enchanted_type: Optional[Type], filepath: str = ".") -> None:
        """Collects specialized monomorphized function details."""
        attrs, a_idx = _extract_attributes_from_node(node.children)
        is_inline, is_ritual, idx = skip_weave_modifiers(node.children, start=a_idx)
        if "inline" in attrs:
            is_inline = True

        raw_name = str(node.children[idx])
        idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "shard_params":
            idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        def lookup_subst_tp(tname: str):
            if tname in subst_map:
                return subst_map[tname]
            return self._lookup_type_fn(tname)

        params = []
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data == "param_list":
                param_list_node = node.children[idx]
                for p in param_list_node.children:
                    if isinstance(p, Tree) and p.data == "param":
                        p_name = str(p.children[0])
                        p_type = ast_to_type(p.children[1], lookup_subst_tp) if len(p.children) > 1 else AnyType()
                        p_type = p_type.substitute(subst_map)
                        p_default = p.children[2] if len(p.children) >= 3 else None
                        params.append((p_name, p_type, p_default))
                idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        ret_type = VOID_TYPE
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data not in ("stmt", "block", "file"):
                ret_type = ast_to_type(node.children[idx], lookup_subst_tp)
                ret_type = ret_type.substitute(subst_map)
                idx += 1
            elif isinstance(node.children[idx], Token) and node.children[idx].type == "NAME":
                ret_type = ast_to_type(node.children[idx], lookup_subst_tp)
                ret_type = ret_type.substitute(subst_map)
                idx += 1

        body_stmts = []
        for s in node.children[idx:]:
            if isinstance(s, Tree):
                body_stmts.append(s)

        c_name = specialized_name

        self.fn_info[specialized_name] = {"c_name": c_name, "params": params, "return_type": ret_type, "is_ritual": is_ritual}
        self.fn_info[c_name] = {"c_name": c_name, "params": params, "return_type": ret_type, "is_ritual": is_ritual}

        if filepath and filepath.endswith(".d.pengu"):
            return

        if not any(w["c_name"] == c_name for w in self.weaves):
            self.weaves.append({
                "name": specialized_name,
                "c_name": c_name,
                "enchanted_type": enchanted_type,
                "params": params,
                "return_type": ret_type,
                "is_inline": is_inline,
                "is_ritual": is_ritual,
                "attributes": attrs,
                "body_stmts": body_stmts,
                "refs": _dce_collect_refs(body_stmts),
                "subst_map": subst_map,
                "filepath": filepath,
                # Declaration line of the weave in its .pengu source, used for the
                # '#line' marker emitted before the C definition.
                "line": self._node_line(node),
            })

        # Scan body statements for generic method calls on self to ensure transitive dependencies are monomorphized
        if enchanted_type is not None and hasattr(self, "symbols") and hasattr(self.symbols, "generic_methods"):
            base_tname = get_type_base_name(enchanted_type)
            t_args = getattr(enchanted_type, "type_args", [])
            for st in body_stmts:
                if not isinstance(st, Tree):
                    continue
                for sub in st.iter_subtrees():
                    if sub.data == "calling_expr" and sub.children:
                        target_node = sub.children[0]
                        if isinstance(target_node, Tree) and target_node.children:
                            is_self = str(target_node.children[0]) == "self"
                            if is_self and len(target_node.children) >= 2:
                                acc = target_node.children[1]
                                m_name = None
                                if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                                    m_name = str(acc.children[0])
                                elif isinstance(acc, (Token, str)):
                                    m_name = str(acc)
                                if m_name and (base_tname, m_name) in self.symbols.generic_methods:
                                    entry = self.symbols.generic_methods[(base_tname, m_name)]
                                    recv_p, m_p, method_ast = (entry[0], entry[1], entry[2]) if len(entry) == 3 else (entry[0], [], entry[1])
                                    type_params = list(recv_p) + list(m_p)
                                    if t_args and len(t_args) == len(type_params):
                                        c_m = self._c_ident(m_name)
                                        rec_mangled = enchanted_type.get_mangled_name() if hasattr(enchanted_type, "get_mangled_name") else str(enchanted_type).replace(" ", "_")
                                        cand = f"{rec_mangled}_{c_m}"
                                        sub_map = dict(zip(type_params, t_args))
                                        self.symbols.monomorphized_methods[cand] = (method_ast, sub_map, enchanted_type)
    def _collect_weave(self, node: Tree, filepath: str, enchanted_type: Optional[Type], prefix: Optional[str] = None) -> None:
        """Collects function declaration details."""
        attrs, a_idx = _extract_attributes_from_node(node.children)
        is_inline, is_ritual, idx = skip_weave_modifiers(node.children, start=a_idx)
        if "inline" in attrs:
            is_inline = True
        has_shard_params = any(isinstance(c, Tree) and c.data == "shard_params"
                               for c in node.children)

        name = str(node.children[idx])
        idx += 1

        auto_inline = False
        if not is_inline and "cold" not in attrs and self.symbols:
            # The checker flags small non-recursive weaves as inline candidates.
            # Automatic heuristic inlining uses advisory 'static inline' (giving the C
            # compiler discretion to decline), whereas explicit user 'inline weave'
            # specifies '__attribute__((always_inline))'.
            try:
                _inline_sym = self.symbols.lookup(name)
            except Exception:
                _inline_sym = None
            if _inline_sym is not None and getattr(_inline_sym, "is_inline", False):
                is_inline = True
                auto_inline = True

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        if idx < len(node.children) and isinstance(node.children[idx], Tree) and node.children[idx].data == "shard_params":
            idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        params = []
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data == "param_list":
                param_list_node = node.children[idx]
                for p in param_list_node.children:
                    if isinstance(p, Tree) and p.data == "param":
                        p_name = str(p.children[0])
                        p_type = ast_to_type(p.children[1], self._lookup_type_fn) if len(p.children) > 1 else AnyType()
                        p_default = p.children[2] if len(p.children) >= 3 else None
                        params.append((p_name, p_type, p_default))
                idx += 1

        while idx < len(node.children) and node.children[idx] is None:
            idx += 1

        ret_type = VOID_TYPE
        if idx < len(node.children):
            if isinstance(node.children[idx], Tree) and node.children[idx].data not in ("stmt", "block", "file"):
                ret_type = ast_to_type(node.children[idx], self._lookup_type_fn)
                idx += 1
            elif isinstance(node.children[idx], Token) and node.children[idx].type == "NAME":
                ret_type = ast_to_type(node.children[idx], self._lookup_type_fn)
                idx += 1

        body_stmts = []
        for s in node.children[idx:]:
            if isinstance(s, Tree):
                body_stmts.append(s)

        c_name = self._c_ident(name)
        if enchanted_type is not None:
            t_name = getattr(enchanted_type, "name", str(enchanted_type)).replace(" ", "_")
            t_name = self._c_ident(t_name)
            m_name = self._c_ident(name)
            # 'insignia' prefixes module-level weaves/declares but NOT methods
            # enchanting primitive/collection types (string, list, map, slice,
            # maybe, result): those keep their plain names (string_len, ...)
            # so they can never collide with the runtime pengu_string_* /
            # pengu_list_* / pengu_map_* primitive families.
            is_primitive_receiver = isinstance(enchanted_type, BaseType) or isinstance(
                enchanted_type, (ListType, MapType, SliceType, MaybeType, ResultType)
            )
            c_name = f"{t_name}_{m_name}" if is_primitive_receiver else (f"{prefix}{t_name}_{m_name}" if prefix else f"{t_name}_{m_name}")
        elif prefix:
            c_name = f"{prefix}{self._c_ident(name)}"
        elif filepath:
            norm_fp = os.path.abspath(filepath)
            norm_order = [os.path.abspath(p) for p in self.import_order]
            if len(norm_order) > 1 and norm_fp != norm_order[-1]:
                bname = os.path.basename(norm_fp)
                if bname.endswith(".d.pengu"):
                    mod_name = bname[:-8]
                elif bname.endswith(".pengu"):
                    mod_name = bname[:-6]
                else:
                    mod_name = os.path.splitext(bname)[0]
                mod_ident = self._c_ident(mod_name)
                if mod_ident and not name.startswith(f"{mod_ident}_"):
                    c_name = f"{mod_ident}_{self._c_ident(name)}"

        if name == "main" and enchanted_type is None:
            self.has_main = True
            # Remembered so the entry wrapper can forward it as the exit status.
            self.main_return_type = ret_type
            self.main_c_name = "pengu_main" if c_name == "main" else c_name

        if enchanted_type is None:
            self.fn_info[name] = {"c_name": c_name, "params": params, "return_type": ret_type, "is_ritual": is_ritual}
        self.fn_info[c_name] = {"c_name": c_name, "params": params, "return_type": ret_type, "is_ritual": is_ritual}

        if filepath and filepath.endswith(".d.pengu"):
            return

        self.weaves.append({
            "name": name,
            "c_name": c_name,
            "enchanted_type": enchanted_type,
            "params": params,
            "return_type": ret_type,
            "is_inline": is_inline,
            "auto_inline": auto_inline,
            "is_ritual": is_ritual,
            "attributes": attrs,
            "body_stmts": body_stmts,
            "refs": _dce_collect_refs(body_stmts),
            # Generic templates are never emitted on their own (their bodies
            # need concrete substitutions), so DCE must leave them alone.
            "is_generic": has_shard_params,
            "filepath": filepath,
            # Declaration line of the weave in its .pengu source, used for the
            # '#line' marker emitted before the C definition.
            "line": self._node_line(node),
        })
    def _expand_when_top_stmts(self, top_stmts: List[Tuple[Tree, str]]) -> List[Tuple[Tree, str]]:
        """Filters compile-time 'when' blocks down to their active branch at top level.

        Only declarations belonging to the branch selected by the compile-time
        environment are kept; everything else is dropped before collection.
        """
        out: List[Tuple[Tree, str]] = []

        def inner_stmt(node: Tree) -> Any:
            if node.data == "top_stmt" and node.children:
                return node.children[0]
            return node

        def is_when(node: Tree) -> bool:
            s = inner_stmt(node)
            return isinstance(s, Tree) and s.data == "when_top_decl"

        def active_items(node: Tree) -> List[Tree]:
            s = inner_stmt(node)
            if not isinstance(s, Tree) or not s.children:
                return []
            val = eval_comptime(self.compile_env, s.children[0])
            if val is True:
                return [c for c in s.children[1:] if isinstance(c, Tree) and c.data == "top_stmt"]
            if val is False:
                items: List[Tree] = []
                for c in s.children[1:]:
                    if not isinstance(c, Tree):
                        continue
                    if c.data == "when_top_else_plain":
                        items.extend(ic for ic in c.children if isinstance(ic, Tree) and ic.data == "top_stmt")
                    elif c.data == "when_top_else_when":
                        for ic in c.children:
                            if isinstance(ic, Tree):
                                if ic.data == "top_stmt":
                                    items.append(ic)
                                elif ic.data == "when_top_decl":
                                    items.append(Tree("top_stmt", [ic]))
                return items
            return []

        def process(node: Tree, fp: str) -> None:
            if is_when(node):
                for it in active_items(node):
                    process(it, fp)
            else:
                out.append((node, fp))

        for top_node, filepath in top_stmts:
            self._apply_main_flag(filepath)
            process(top_node, filepath)
        return out
    def _file_is_main(self, filepath: Optional[str]) -> bool:
        """Returns True when the given source file is compiled as the main entry.

        Entry-as-main mode must be enabled (pengu run <file> / -D main) and the
        filepath must match the recorded entry file; imported modules always
        compile with 'main' false.
        """
        if not getattr(self, "entry_main_mode", False) or not filepath:
            return False
        entry = getattr(self, "entry_file", None)
        if not entry:
            return False
        try:
            a = os.path.normcase(os.path.abspath(os.path.normpath(str(filepath))))
            b = os.path.normcase(os.path.abspath(os.path.normpath(str(entry))))
            return a == b
        except Exception:
            return False
    def _apply_main_flag(self, filepath: Optional[str]) -> None:
        """Sets compile_env.is_main to match the module being processed."""
        if self.compile_env is not None:
            self.compile_env.is_main = self._file_is_main(filepath)
