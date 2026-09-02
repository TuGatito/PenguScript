from __future__ import annotations
import os
from typing import List, Set, Optional, Dict, Tuple, Any
from lark import Tree, Token

from .pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ManyType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, OPAQUE_TYPE, AliasType, AnyType,
    TypeParam, INT_TYPE, I32_TYPE, I64_TYPE, U32_TYPE, U64_TYPE, CHAR_TYPE, BYTE_TYPE,
    U8_TYPE, I8_TYPE, U16_TYPE, I16_TYPE, USIZE_TYPE, ISIZE_TYPE, FLOAT_TYPE, F32_TYPE,
    F64_TYPE, DOUBLE_TYPE, BOOL_TYPE, STRING_TYPE, VOID_TYPE, ERROR_TYPE, ast_to_type
)
from .pengu_symbols import SymbolTable, Symbol, Scope, resolve_imports, find_module_path
from .pengu_infer import TypeInferrer, ConstFolder
from .pengu_errors import (
    PenguError, ErrorReporter, SemanticError, ConstInsideWeaveError, VarLetTopLevelError,
    SelfDotAccessError, UndefinedIdentifierError, TypeMismatchError, MutabilityError,
    InvalidControlFlowError, InvalidMemoryOpError, InvalidWithTargetError,
    GenericTypeMissingArgsError, TypeParamOutsideGenericError, MultipleManyParamsError,
    ManyParamNotLastError, suggest_similar_identifier
)


class PenguChecker:
    """Performs comprehensive semantic analysis, type checking, and optimization tagging.

    Ensures V-safety rules, type soundness, ownership boundaries, and module integrity.
    """

    def __init__(
        self,
        source: str = "",
        filename: str = "main.pengu",
        source_code: Optional[str] = None,
        base_dir: Optional[str] = None
    ):
        """Initializes semantic checker instance with source code and directory context.

        Args:
            source: Source code text.
            filename: Source file path.
            source_code: Optional explicit source code text override.
            base_dir: Base directory for module import resolution.
        """
        self.source_code = source_code if source_code is not None else source
        self.filename = filename
        if base_dir is not None:
            self.base_dir = os.path.abspath(base_dir)
        elif os.path.isabs(filename) or "/" in filename or "\\" in filename:
            self.base_dir = os.path.abspath(os.path.dirname(filename))
        else:
            self.base_dir = os.path.abspath(os.getcwd())

        self.errors: List[PenguError] = []
        self.warnings: List[str] = []
        self.symbols = SymbolTable()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename)
        self.const_folder = ConstFolder(self.symbols)

    def check(
        self,
        tree: Tree,
        source: Optional[str] = None,
        filename: Optional[str] = None,
        symbols: Optional[SymbolTable] = None,
        reset_symbols: bool = True,
        import_order: Optional[List[str]] = None
    ) -> List[PenguError]:
        """Validates AST semantic correctness using two-pass analysis.

        Pass 1: Collects all top-level types, runes, echos, omens, functions, and imports.
        Pass 2: Validates statements, mutability, type consistency, and control flow.

        Args:
            tree: Lark parsed AST root.
            source: Optional source text override.
            filename: Optional filename override.
            symbols: Optional existing SymbolTable to reuse.
            reset_symbols: Whether to reset symbol table on check (default True).
            import_order: Optional precomputed topological import order to avoid redundant DFS.

        Returns:
            List of detected semantic errors (empty if check succeeds).

        Raises:
            PenguError: The first error found with all_errors and rendered_all attached if validation fails.
        """
        if filename is not None:
            self.filename = filename
        if source is not None:
            self.source_code = source

        self.errors = []
        self.warnings = []
        if symbols is not None:
            self.symbols = symbols
        elif reset_symbols or not hasattr(self, "symbols") or self.symbols is None:
            self.symbols = SymbolTable()
            self._collected_files = set()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)

        # Pass 2: Validate semantic rules and type check
        self.symbols.has_includes = bool(self.symbols.includes) and reset_symbols is False
        self._check_node(tree)

        # Append inferrer warnings
        self.warnings.extend(self.inferrer.warnings)

        if self.errors:
            reporter = ErrorReporter(source=self.source_code, filename=self.filename)
            rendered_all = "\n\n".join([reporter.report(e, use_color=True) for e in self.errors])
            first_err = self.errors[0]
            first_err.all_errors = self.errors
            first_err.rendered_all = rendered_all
            raise first_err
        return self.errors

    def _get_loc(self, node: Any) -> Tuple[Optional[int], Optional[int]]:
        """Retrieves 1-indexed line and column numbers from AST node.

        Args:
            node: AST node or Token.

        Returns:
            Tuple of (line, column) or (None, None).
        """
        if isinstance(node, Token):
            return getattr(node, "line", None), getattr(node, "column", None)
        if isinstance(node, Tree):
            if hasattr(node, "meta") and node.meta:
                l = getattr(node.meta, 'line', None)
                c = getattr(node.meta, 'column', None)
                if l is not None:
                    return l, c
            for child in node.children:
                if isinstance(child, Token) and getattr(child, "line", None) is not None:
                    return child.line, child.column
                if isinstance(child, Tree):
                    cl, cc = self._get_loc(child)
                    if cl is not None:
                        return cl, cc
        return None, None

    def _get_node_span(self, node: Any) -> Tuple[int, int]:
        """Extracts (start_line, end_line) from an AST node."""
        if isinstance(node, Token):
            l = getattr(node, "line", 0) or 0
            el = getattr(node, "end_line", l) or l
            return l, el
        if isinstance(node, Tree):
            start_l = 0
            end_l = 0
            if hasattr(node, "meta") and node.meta:
                start_l = getattr(node.meta, "line", 0) or 0
                end_l = getattr(node.meta, "end_line", 0) or 0
            lines = []
            for t in node.scan_values(lambda v: isinstance(v, Token)):
                if getattr(t, "line", None):
                    lines.append(t.line)
                if getattr(t, "end_line", None):
                    lines.append(t.end_line)
            if lines:
                start_l = start_l or min(lines)
                end_l = max(lines) if not end_l else max(end_l, max(lines))
            return start_l, max(start_l, end_l)
        return 0, 0

    def _make_error(self, err_cls, message: str, node: Any = None, **kwargs) -> PenguError:
        """Creates a specialized semantic error with line, snippet, and span context.

        Args:
            err_cls: Exception class subclassing PenguError.
            message: Descriptive error message.
            node: AST node associated with the error.
            **kwargs: Additional error metadata (code, help, note, line, col).

        Returns:
            Instantiated PenguError.
        """
        line, col = self._get_loc(node) if node is not None else (None, None)
        if "line" in kwargs and kwargs["line"] is not None:
            line = kwargs.pop("line")
        if "col" in kwargs and kwargs["col"] is not None:
            col = kwargs.pop("col")

        if "span_start" not in kwargs and col is not None:
            kwargs["span_start"] = col
        if "span_end" not in kwargs and col is not None:
            if isinstance(node, Token):
                kwargs["span_end"] = col + len(str(node.value))
            elif isinstance(node, Tree) and hasattr(node, "meta") and getattr(node.meta, "end_column", None):
                kwargs["span_end"] = getattr(node.meta, "end_column")
            elif isinstance(node, Tree) and len(node.children) > 0 and isinstance(node.children[0], Token):
                kwargs["span_end"] = col + len(str(node.children[0].value))

        snippet = None
        if self.source_code and line is not None:
            lines = self.source_code.splitlines()
            if 1 <= line <= len(lines):
                snippet = lines[line - 1]

        kwargs.setdefault("file", self.filename)
        kwargs.setdefault("snippet", snippet)
        return err_cls(message, line=line, col=col, **kwargs)

    def _make_undefined_error(
        self,
        name: str,
        node: Any = None,
        code: str = "E0004",
        candidates: Optional[List[str]] = None,
        entity_kind: str = "identifier"
    ) -> UndefinedIdentifierError:
        """Constructs an UndefinedIdentifierError with fuzzy name suggestions."""
        if candidates is None:
            candidates = self.symbols.get_all_visible_names() if hasattr(self.symbols, "get_all_visible_names") else []
        suggestions = suggest_similar_identifier(name, candidates)
        if suggestions:
            suggested = suggestions[0]
            help_msg = f"A similar name exists in scope: '{suggested}'. Did you mean '{suggested}'?"
        else:
            help_msg = f"Check if '{name}' is misspelled or declare it before use."

        return self._make_error(
            UndefinedIdentifierError,
            f"Undefined {entity_kind} '{name}'",
            node,
            code=code,
            help=help_msg,
            note=f"All {entity_kind}s must be defined before use.",
            label="not found in this scope"
        )

    def _make_type_mismatch_error(
        self,
        expected_type: Any,
        found_type: Any,
        node: Any = None,
        expr_str: Optional[str] = None,
        custom_message: Optional[str] = None,
        code: str = "E0005",
        note: Optional[str] = None,
    ) -> TypeMismatchError:
        """Constructs a TypeMismatchError with expected/found format and conversion help."""
        msg = custom_message or f"Mismatched types: expected '{expected_type}', found '{found_type}'"
        expr_repr = expr_str or "value"
        is_num_src = str(found_type) in ("int", "i32", "i64", "float", "f32", "f64", "u8", "i8", "u16", "i16", "u32", "u64", "usize", "isize")
        is_num_tgt = str(expected_type) in ("int", "i32", "i64", "float", "f32", "f64", "u8", "i8", "u16", "i16", "u32", "u64", "usize", "isize")

        if is_num_src and is_num_tgt:
            help_msg = f"Consider converting the value explicitly using '{expr_repr} to {expected_type}'"
        else:
            help_msg = f"Ensure the value type matches the expected type '{expected_type}' or use explicit conversion 'to {expected_type}'."

        return self._make_error(
            TypeMismatchError,
            msg,
            node,
            code=code,
            help=help_msg,
            note=note or "PenguScript requires type safety and explicit conversions.",
            label=f"expected '{expected_type}'"
        )

    def _record_error(self, err: PenguError) -> None:
        """Records a semantic error in the error accumulator.

        Args:
            err: PenguError instance to register.
        """
        self.errors.append(err)

    def _extract_preceding_doc(self, line: Optional[int]) -> Optional[str]:
        """Extracts doc comments (# or ##) immediately preceding a declaration.

        Args:
            line: 1-indexed source line number of declaration.

        Returns:
            Extracted markdown docstring or None.
        """
        if not self.source_code or line is None or line <= 1:
            return None
        lines = self.source_code.splitlines()
        idx = line - 2  # 0-indexed line above declaration
        collected: List[str] = []

        while idx >= 0:
            raw_line = lines[idx]
            stripped = raw_line.strip()
            if not stripped:
                break
            if stripped.startswith("##") and stripped.endswith("##") and len(stripped) > 4:
                content = stripped[2:-2].strip()
                collected.append(content)
            elif stripped.startswith("##"):
                content = stripped[2:].strip()
                if content.endswith("##"):
                    content = content[:-2].strip()
                collected.append(content)
            elif stripped.startswith("#"):
                content = stripped[1:].strip()
                if content and set(content) <= {"-", "=", "*", "_"}:
                    idx -= 1
                    continue
                collected.append(content)
            else:
                break
            idx -= 1

        if not collected:
            return None
        collected.reverse()
        return "\n".join(collected).strip()

    # -------------------------------------------------------------------------
    # Pass 1: Collect Top-Level Declarations
    # -------------------------------------------------------------------------
    def _collect_top_level(self, tree: Tree, import_order: Optional[List[str]] = None) -> None:
        """Discovers and registers all module definitions, imports, and declarations.

        Args:
            tree: AST Tree root.
            import_order: Optional precomputed topological import order.
        """
        has_imports = False

        file_imports: Set[str] = set()
        for child in tree.children:
            if not isinstance(child, Tree):
                continue
            if child.data == "file":
                self._collect_top_level(child, import_order=import_order)
                continue
            if child.data != "top_stmt" or not child.children:
                continue

            stmt = child.children[0]
            if not isinstance(stmt, Tree):
                continue

            line, col = self._get_loc(stmt)
            rule = stmt.data

            if rule == "include_stmt":
                inc = str(stmt.children[0]).strip('"')
                self.symbols.has_includes = True
                self.symbols.includes.append(inc)

            elif rule == "link_stmt":
                lib = str(stmt.children[0]).strip('"')
                self.symbols.links.append(lib)

            elif rule == "import_stmt":
                has_imports = True
                path_tree = stmt.children[0]
                dot_path = ".".join(str(t) for t in path_tree.children)
                if dot_path in file_imports:
                    err = self._make_error(
                        SemanticError,
                        f"Duplicate import of module '{dot_path}'",
                        stmt,
                        code="E0004",
                        help=f"Remove duplicate import of module '{dot_path}'.",
                        note="Modules only need to be imported once."
                    )
                    self._record_error(err)
                file_imports.add(dot_path)
                self.symbols.imported_modules.add(dot_path)
                self.symbols.imports.append(dot_path)
                last_name = str(path_tree.children[-1])

                mod_scope = Scope(kind="module")
                mod_file = None
                try:
                    from_d = os.path.dirname(os.path.abspath(self.filename)) if self.filename else None
                    mod_file = find_module_path(self.base_dir, dot_path, from_dir=from_d)
                    if mod_file and os.path.isfile(mod_file):
                        with open(mod_file, "r", encoding="utf-8") as mf:
                            mod_code = mf.read()
                        from .pengu_parser import PenguParser
                        sub_parser = PenguParser()
                        sub_tree = sub_parser.parse(mod_code)
                        sub_checker = PenguChecker(base_dir=self.base_dir)
                        sub_checker.source_code = mod_code
                        sub_checker.filename = mod_file
                        sub_checker._collect_top_level(sub_tree)
                        for sname, sym in sub_checker.symbols.global_scope.symbols.items():
                            if sym.kind != "import":
                                mod_scope.define(sym)
                                if sym.kind in ("weave", "function", "declare") and isinstance(sym.type, FnType):
                                    self.symbols.functions[f"{last_name}_{sname}"] = sym.type
                                if sym.kind == "rune" and isinstance(sym.type, RuneType):
                                    self.symbols.runes[f"{last_name}_{sname}"] = sym.type
                except Exception:
                    pass

                mod_doc = self._extract_preceding_doc(line) or f"Module `{dot_path}`"
                self.symbols.global_scope.define(Symbol(
                    name=last_name,
                    type=RuneType(name=last_name),
                    kind="import",
                    line=line, column=col,
                    doc=mod_doc,
                    module_scope=mod_scope,
                    file_path=mod_file
                ))

            elif rule == "rune_decl":
                r_name = str(stmt.children[0])
                type_params = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
                    rem_children = rem_children[1:]

                if len(type_params) != len(set(type_params)):
                    err = self._make_error(
                        SemanticError,
                        f"Duplicate type parameter in generic declaration '{r_name}'",
                        stmt,
                        code="E0005",
                        help="Ensure all type parameter names are unique."
                    )
                    self._record_error(err)

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname)
                    return self.symbols.lookup_type(tname)

                fields: Dict[str, Type] = {}
                for f_decl in rem_children:
                    if isinstance(f_decl, Tree) and f_decl.data == "field_decl":
                        f_name = str(f_decl.children[0])
                        f_type = ast_to_type(f_decl.children[1], lookup_tp)
                        fields[f_name] = f_type

                if type_params:
                    self.symbols.generic_runes[r_name] = (type_params, stmt)
                    rune_t = RuneType(name=r_name, fields=fields, type_params=type_params)
                else:
                    rune_t = RuneType(name=r_name, fields=fields)

                self.symbols.runes[r_name] = rune_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=r_name, type=rune_t, kind="rune", line=line, column=col, doc=doc, file_path=self.filename
                ))

            elif rule == "echo_decl":
                e_name = str(stmt.children[0])
                type_params = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname)
                    return self.symbols.lookup_type(tname)

                fields: Dict[str, Type] = {}
                for f_decl in rem_children:
                    if isinstance(f_decl, Tree) and f_decl.data == "field_decl":
                        f_name = str(f_decl.children[0])
                        f_type = ast_to_type(f_decl.children[1], lookup_tp)
                        fields[f_name] = f_type

                if type_params:
                    self.symbols.generic_echos[e_name] = (type_params, stmt)
                    echo_t = EchoType(name=e_name, fields=fields, type_params=type_params)
                else:
                    echo_t = EchoType(name=e_name, fields=fields)

                self.symbols.echos[e_name] = echo_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=e_name, type=echo_t, kind="echo", line=line, column=col, doc=doc, file_path=self.filename
                ))

            elif rule == "omen_decl":
                o_name = str(stmt.children[0])
                type_params = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname)
                    return self.symbols.lookup_type(tname)

                variants: Dict[str, Dict[str, Type]] = {}
                for var_node in rem_children:
                    if isinstance(var_node, Tree) and var_node.data == "omen_variant":
                        v_name = str(var_node.children[0])
                        v_fields: Dict[str, Type] = {}
                        for of_node in var_node.children[1:]:
                            if isinstance(of_node, Tree) and of_node.data == "omen_field":
                                fn = str(of_node.children[0])
                                ft = ast_to_type(of_node.children[1], lookup_tp)
                                v_fields[fn] = ft
                        variants[v_name] = v_fields

                if type_params:
                    self.symbols.generic_omens[o_name] = (type_params, stmt)
                    omen_t = OmenType(name=o_name, variants=variants, type_params=type_params)
                else:
                    omen_t = OmenType(name=o_name, variants=variants)

                self.symbols.omens[o_name] = omen_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=o_name, type=omen_t, kind="omen", line=line, column=col, doc=doc, file_path=self.filename
                ))
                for v_name in variants:
                    self.symbols.global_scope.define(Symbol(
                        name=f"{o_name}_{v_name}", type=omen_t, kind="omen_variant", is_mutable=False, line=line, column=col, file_path=self.filename
                    ))
                    if self.symbols.lookup(v_name) is None:
                        self.symbols.global_scope.define(Symbol(
                            name=v_name, type=omen_t, kind="omen_variant", is_mutable=False, line=line, column=col, file_path=self.filename
                        ))

            elif rule == "alias_decl":
                a_name = str(stmt.children[0])
                type_params = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname)
                    return self.symbols.lookup_type(tname)

                target_t = ast_to_type(rem_children[0], lookup_tp)
                alias_obj = AliasType(name=a_name, target=target_t, type_params=type_params)
                if type_params:
                    self.symbols.generic_aliases[a_name] = (type_params, stmt)
                self.symbols.aliases[a_name] = alias_obj
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=a_name, type=alias_obj, kind="alias", line=line, column=col, doc=doc, file_path=self.filename
                ))

            elif rule == "const_decl":
                c_name = str(stmt.children[0])
                c_type = None
                c_expr = None
                if len(stmt.children) == 3:
                    if stmt.children[1] is not None:
                        c_type = ast_to_type(stmt.children[1], self.symbols.lookup_type)
                    c_expr = stmt.children[2]
                else:
                    c_expr = stmt.children[1]
                const_val = self.const_folder.fold(c_expr)
                if c_type is None and const_val is not None:
                    if isinstance(const_val, bool): c_type = BOOL_TYPE
                    elif isinstance(const_val, int): c_type = INT_TYPE
                    elif isinstance(const_val, float): c_type = FLOAT_TYPE
                    elif isinstance(const_val, str): c_type = STRING_TYPE
                self.symbols.consts[c_name] = (c_type, const_val)
                doc = self._extract_preceding_doc(line)
                sym = Symbol(name=c_name, type=c_type or AnyType(), kind="const", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename)
                sym.const_val = const_val
                self.symbols.global_scope.define(sym)

            elif rule == "enchanting_decl":
                target_type_node = stmt.children[0]
                target_type = ast_to_type(target_type_node, self.symbols.lookup_type)
                base_tname = target_type.name.split("_")[0]
                type_params = []
                if base_tname in self.symbols.generic_runes:
                    type_params = self.symbols.generic_runes[base_tname][0]
                elif isinstance(target_type, RuneType) and target_type.type_args:
                    type_params = [getattr(t, "name", str(t)) for t in target_type.type_args]

                for m_decl in stmt.children[1:]:
                    if isinstance(m_decl, Tree) and m_decl.data == "weave_decl":
                        m_name = str(m_decl.children[0])
                        if type_params:
                            self.symbols.generic_methods[(base_tname, m_name)] = (type_params, m_decl)

            elif rule == "declare_stmt":
                fn_name = str(stmt.children[0])
                type_params = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname)
                    return self.symbols.lookup_type(tname)

                params: List[Tuple[Optional[str], Type]] = []
                ret_type: Type = VOID_TYPE
                for child_n in rem_children:
                    if isinstance(child_n, Tree) and child_n.data == "param_list":
                        for p in child_n.children:
                            if isinstance(p, Tree) and p.data == "param":
                                pn = str(p.children[0])
                                pt = ast_to_type(p.children[1], lookup_tp) if len(p.children) >= 2 else AnyType()
                                params.append((pn, pt))
                    elif isinstance(child_n, Tree) and child_n.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                        ret_type = ast_to_type(child_n, lookup_tp)
                    elif isinstance(child_n, Token) and child_n.type == "NAME":
                        ret_type = ast_to_type(child_n, lookup_tp)
                fn_t = FnType(params=params, return_type=ret_type, type_params=type_params)
                self.symbols.functions[fn_name] = fn_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=fn_name, type=fn_t, kind="declare", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename
                ))

            elif rule == "weave_decl":
                fn_name = str(stmt.children[0])
                type_params = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname)
                    return self.symbols.lookup_type(tname)

                params: List[Tuple[Optional[str], Type]] = []
                ret_type: Type = VOID_TYPE
                default_count = 0
                has_seen_default = False
                for child_n in rem_children:
                    if isinstance(child_n, Tree) and child_n.data == "param_list":
                        for p in child_n.children:
                            if isinstance(p, Tree) and p.data == "param":
                                pn = str(p.children[0])
                                pt = ast_to_type(p.children[1], lookup_tp) if len(p.children) >= 2 else AnyType()
                                has_default = len(p.children) >= 3 and p.children[2] is not None
                                if has_default:
                                    has_seen_default = True
                                    default_count += 1
                                elif has_seen_default:
                                    err = self._make_error(
                                        SemanticError,
                                        f"Non-default parameter '{pn}' follows default parameter in function '{fn_name}'",
                                        p,
                                        code="E0005",
                                        help="Parameters with default values must appear at the end of parameter list.",
                                        note="Default arguments must follow all non-default arguments."
                                    )
                                    self._record_error(err)
                                params.append((pn, pt))
                    elif isinstance(child_n, Tree) and child_n.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                        ret_type = ast_to_type(child_n, lookup_tp)
                    elif isinstance(child_n, Token) and child_n.type == "NAME":
                        ret_type = ast_to_type(child_n, lookup_tp)

                if type_params:
                    self.symbols.generic_functions[fn_name] = (type_params, stmt)
                    fn_t = FnType(params=params, return_type=ret_type, default_count=default_count, type_params=type_params)
                else:
                    fn_t = FnType(params=params, return_type=ret_type, default_count=default_count)

                self.symbols.functions[fn_name] = fn_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=fn_name, type=fn_t, kind="weave", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename
                ))

        if not hasattr(self, "_collected_files") or self._collected_files is None:
            self._collected_files = set()

        target_file = self.filename
        if target_file:
            if not os.path.isabs(target_file):
                target_file = os.path.abspath(os.path.join(self.base_dir, target_file))
            self._collected_files.add(os.path.abspath(target_file))

        if has_imports and target_file and os.path.exists(target_file):
            if import_order is not None:
                self.symbols.import_order = import_order
            else:
                try:
                    order = resolve_imports(self.base_dir, target_file, parser=getattr(self, "parser", None))
                    self.symbols.import_order = order
                    from .pengu_parser import PenguParser
                    mod_parser = getattr(self, "parser", None) or PenguParser()
                    for mod_file in order:
                        mod_abs = os.path.abspath(mod_file)
                        if mod_abs not in self._collected_files:
                            self._collected_files.add(mod_abs)
                            if os.path.isfile(mod_abs):
                                with open(mod_abs, "r", encoding="utf-8") as mf:
                                    m_code = mf.read()
                                m_tree = mod_parser.parse(m_code)
                                self._collect_top_level(m_tree, import_order=order)
                except SemanticError as e:
                    self._record_error(e)



    # -------------------------------------------------------------------------
    # Pass 2: Traverse and Validate AST
    # -------------------------------------------------------------------------
    def _check_node(self, node: Any) -> None:
        """Walks AST node to enforce type safety, scope, and mutability constraints.

        Args:
            node: Lark Tree or Token AST node.
        """
        if not isinstance(node, Tree):
            return

        line, col = self._get_loc(node)
        rule = node.data

        # 1. Top-Level Safety Checks
        if rule == "include_stmt":
            self.symbols.has_includes = True
            return

        elif rule == "var_decl":
            if self.symbols.is_top_level():
                err = self._make_error(
                    VarLetTopLevelError,
                    "'var' is not allowed at top-level. Use 'const' or move inside a function.",
                    node,
                    code="E0002",
                    help="Use 'const' for global constants, or move 'var' inside a function body.",
                    note="PenguScript forbids mutable global state to guarantee V-safety."
                )
                self._record_error(err)
                return
            self._check_var_decl(node)
            return

        elif rule == "let_decl":
            if self.symbols.is_top_level():
                err = self._make_error(
                    VarLetTopLevelError,
                    "'let' is not allowed at top-level. Use 'const' or move inside a function.",
                    node,
                    code="E0002",
                    help="Use 'const' for global constants, or move 'let' inside a function body.",
                    note="PenguScript forbids mutable global state to guarantee V-safety."
                )
                self._record_error(err)
                return
            self._check_let_decl(node)
            return

        elif rule == "const_decl":
            if not self.symbols.is_top_level():
                err = self._make_error(
                    ConstInsideWeaveError,
                    "'const' is only allowed at top-level (global).",
                    node,
                    code="E0001",
                    help="Use 'let' (immutable) or 'var' (mutable) inside functions instead of 'const'.",
                    note="Constants in PenguScript are top-level compile-time definitions."
                )
                self._record_error(err)
                return
            self._check_const_decl(node)
            return

        # 2. Enchanting Blocks
        elif rule == "enchanting_decl":
            target_type_node = node.children[0]
            target_type = ast_to_type(target_type_node, self.symbols.lookup_type)
            base_tname = target_type.name.split("_")[0]
            type_params = []
            if base_tname in self.symbols.generic_runes:
                type_params = self.symbols.generic_runes[base_tname][0]
            elif isinstance(target_type, RuneType) and target_type.type_args:
                type_params = [getattr(t, "name", str(t)) for t in target_type.type_args]

            if isinstance(target_type, RuneType) and base_tname not in self.symbols.runes:
                err = self._make_error(
                    SemanticError,
                    f"Cannot enchant undefined Rune '{target_type.name}'",
                    node,
                    code="E0004",
                    help=f"Declare 'rune {target_type.name}:' before enchanting it.",
                    note="Enchanting blocks can only extend defined types."
                )
                self._record_error(err)

            span_start, span_end = self._get_node_span(node)
            self.symbols.push_scope(kind="enchanting", enchanting_type=target_type, start_line=span_start, end_line=span_end)
            for tp in type_params:
                self.symbols.define(Symbol(name=tp, type=TypeParam(tp), kind="type"))

            for child in node.children[1:]:
                if isinstance(child, Tree) and child.data == "weave_decl":
                    self._check_enchanting_method(child, target_type, type_params=type_params)
                else:
                    self._check_node(child)

            self.symbols.pop_scope(end_line=span_end)
            return

        # 3. Weave Function Bodies
        elif rule == "weave_decl":
            self._check_weave_decl(node)
            return

        # 4. Set Statements and Mutability
        elif rule == "set_stmt":
            self._check_set_stmt(node)
            return

        # 5. Calling Statements
        elif rule == "calling_stmt":
            target_node = node.children[0]
            args_node = node.children[1] if len(node.children) > 1 else None
            try:
                call_tree = Tree("calling_expr", [target_node] + ([args_node] if args_node else []))
                self.inferrer.infer(call_tree)
            except SemanticError as e:
                self._record_error(e)
            return

        # 6. Control Flow Statements
        elif rule == "if_stmt":
            self._check_if_stmt(node)
            return

        elif rule == "unless_stmt":
            self._check_unless_stmt(node)
            return

        elif rule == "while_stmt":
            self._check_while_stmt(node)
            return

        elif rule == "for_range_stmt":
            self._check_for_range_stmt(node)
            return

        elif rule == "for_in_stmt":
            self._check_for_in_stmt(node)
            return

        elif rule == "with_stmt":
            self._check_with_stmt(node)
            return

        # 7. Memory and Scope Statements
        elif rule in ("defer_stmt", "errdefer_stmt"):
            if self.symbols.current_return_type() is None:
                err = self._make_error(
                    InvalidMemoryOpError,
                    f"'{rule.split('_')[0]}' is only allowed inside function bodies (weave).",
                    node,
                    code="E0008",
                    help="Place defer / errdefer inside a function body.",
                    note="Deferred statements run upon function return."
                )
                self._record_error(err)
            expr_node = node.children[0]
            if isinstance(expr_node, Tree) and expr_node.data not in ("calling_expr", "banish_expr", "var_ref"):
                err = self._make_error(
                    InvalidMemoryOpError,
                    f"'{rule.split('_')[0]}' statement expects function call or banish expression",
                    expr_node,
                    code="E0008",
                    help="Use 'defer calling func(...)' or 'defer banish ptr'.",
                    note="Deferred statements must perform cleanup actions."
                )
                self._record_error(err)
            try:
                self.inferrer.infer(expr_node)
            except SemanticError as e:
                self._record_error(e)
            return

        elif rule == "banish_stmt":
            target_expr = node.children[0]
            if isinstance(target_expr, Tree) and target_expr.data == "var_ref":
                sym_name = str(target_expr.children[0])
                sym = self.symbols.lookup(sym_name)
                if sym and sym.kind == "const":
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"Cannot banish constant '{sym_name}'",
                        target_expr,
                        code="E0008",
                        help="Only dynamically allocated references can be banished.",
                        note="Constants cannot be banished."
                    )
                    self._record_error(err)
            try:
                t = self.inferrer.infer(target_expr)
                if not isinstance(t, RefType) and not isinstance(t, AnyType):
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"'banish' requires a reference type (ref to T), got '{t}'",
                        target_expr,
                        code="E0008",
                        help="Pass a reference (ref to T) to 'banish'.",
                        note="'banish' deallocates memory behind a reference."
                    )
                    self._record_error(err)
            except SemanticError as e:
                self._record_error(e)
            return

        elif rule == "return_stmt":
            self._check_return_stmt(node)
            return

        elif rule in ("break_stmt", "continue_stmt"):
            if not self.symbols.is_in_loop():
                err = self._make_error(
                    InvalidControlFlowError,
                    f"'{rule.split('_')[0]}' is only allowed inside loops (for / while).",
                    node,
                    code="E0007",
                    help=f"Remove '{rule.split('_')[0]}' or place it inside a 'for' or 'while' loop.",
                    note="Loop control statements are only valid within an active loop."
                )
                self._record_error(err)
            return

        elif rule == "expr_stmt":
            expr_node = node.children[0]
            try:
                self.inferrer.infer(expr_node)
            except SemanticError as e:
                self._record_error(e)
            return

        elif rule == "or_block":
            self._check_or_block(node)
            return

        # Generic traversal for other nodes
        for child in node.children:
            if isinstance(child, Tree):
                self._check_node(child)

    # -------------------------------------------------------------------------
    # Specific Statement Checkers
    # -------------------------------------------------------------------------
    def _check_const_decl(self, node: Tree) -> None:
        """Checks constant declaration for V-safety and compile-time type validity.

        Args:
            node: AST Tree for const declaration.
        """
        line, col = self._get_loc(node)
        c_name = str(node.children[0])
        c_type = None
        c_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                c_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            c_expr = node.children[2]
        else:
            c_expr = node.children[1]

        try:
            inferred = self.inferrer.infer(c_expr, expected_type=c_type)
            if c_type is not None and not inferred.is_compatible(c_type):
                err = self._make_type_mismatch_error(
                    expected_type=c_type,
                    found_type=inferred,
                    node=c_expr,
                    custom_message=f"Constant '{c_name}' declared as '{c_type}', but initialized with '{inferred}'",
                    note="Constants must match their declared type."
                )
                self._record_error(err)
            else:
                folded_val = self.const_folder.fold(c_expr)
                doc = self._extract_preceding_doc(line)
                sym = Symbol(name=c_name, type=c_type or inferred, kind="const", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename)
                if folded_val is not None:
                    sym.const_val = folded_val
                self.symbols.define(sym)
        except SemanticError as e:
            self._record_error(e)

    def _check_var_decl(self, node: Tree) -> None:
        """Checks local mutable variable declaration for type validity and folds constants.

        Args:
            node: AST Tree for var declaration.
        """
        line, col = self._get_loc(node)
        v_name = str(node.children[0])
        v_type = None
        v_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                self._validate_type_node(node.children[1])
                v_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            v_expr = node.children[2]
        else:
            v_expr = node.children[1]

        try:
            inferred = self.inferrer.infer(v_expr, expected_type=v_type)
            if v_type is not None and not inferred.is_compatible(v_type):
                err = self._make_type_mismatch_error(
                    expected_type=v_type,
                    found_type=inferred,
                    node=v_expr,
                    custom_message=f"Variable '{v_name}' declared as '{v_type}', but initialized with '{inferred}'",
                    note="Variables must match their declared type."
                )
                self._record_error(err)

            folded_val = self.const_folder.fold(v_expr)
            doc = self._extract_preceding_doc(line)
            sym = Symbol(
                name=v_name,
                type=v_type or inferred,
                kind="var",
                is_mutable=True,
                is_stack_alloc=isinstance(v_type or inferred, RuneType),
                const_val=folded_val,
                line=line,
                column=col,
                doc=doc,
                file_path=self.filename
            )
            self.symbols.define(sym)
        except SemanticError as e:
            self._record_error(e)

    def _check_let_decl(self, node: Tree) -> None:
        """Checks immutable let binding declaration, supports destructuring.

        Args:
            node: AST Tree for let declaration.
        """
        line, col = self._get_loc(node)
        names_node = node.children[0]
        names: List[str] = [str(c) for c in names_node.children] if isinstance(names_node, Tree) else [str(names_node)]
        l_type = None
        l_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                self._validate_type_node(node.children[1])
                l_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            l_expr = node.children[2]
        else:
            l_expr = node.children[1]

        try:
            inferred = self.inferrer.infer(l_expr, expected_type=l_type)
            folded_val = self.const_folder.fold(l_expr)
            doc = self._extract_preceding_doc(line)

            if len(names) == 1:
                v_name = names[0]
                if l_type is not None and not inferred.is_compatible(l_type):
                    err = self._make_type_mismatch_error(
                        expected_type=l_type,
                        found_type=inferred,
                        node=l_expr,
                        custom_message=f"Immutable binding '{v_name}' declared as '{l_type}', but initialized with '{inferred}'",
                        note="Immutable bindings must match their declared type."
                    )
                    self._record_error(err)
                self.symbols.define(Symbol(
                    name=v_name,
                    type=l_type or inferred,
                    kind="let",
                    is_mutable=False,
                    is_stack_alloc=isinstance(l_type or inferred, RuneType),
                    const_val=folded_val,
                    line=line,
                    column=col,
                    doc=doc,
                    file_path=self.filename
                ))
            else:
                # Destructuring: let x, y is my_vec or let a, b is arr
                if isinstance(inferred, RuneType):
                    fields_list = list(inferred.fields.items())
                    if len(names) != len(fields_list):
                        raise self._make_error(
                            SemanticError,
                            f"Destructuring mismatch: Rune '{inferred.name}' has {len(fields_list)} fields, but {len(names)} variables were provided",
                            node,
                            code="E0017",
                            help=f"Provide exactly {len(fields_list)} variable names for destructuring '{inferred.name}'.",
                            note="Destructuring requires an exact match in the number of targets."
                        )
                    for (v_name, (f_name, f_type)) in zip(names, fields_list):
                        self.symbols.define(Symbol(name=v_name, type=f_type, kind="let", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename))
                elif isinstance(inferred, ArrayType):
                    elem_t = inferred.element
                    if inferred.size is not None and isinstance(inferred.size, int) and len(names) != inferred.size:
                        raise self._make_error(
                            SemanticError,
                            f"Destructuring mismatch: Array has size {inferred.size}, but {len(names)} variables were provided",
                            node,
                            code="E0017",
                            help=f"Provide exactly {inferred.size} variable names for destructuring.",
                            note="Destructuring requires an exact match in the number of targets."
                        )
                    for v_name in names:
                        self.symbols.define(Symbol(name=v_name, type=elem_t, kind="let", is_mutable=False, line=line, column=col))
                elif isinstance(inferred, (SliceType, ListType)):
                    elem_t = inferred.element
                    for v_name in names:
                        self.symbols.define(Symbol(name=v_name, type=elem_t, kind="let", is_mutable=False, line=line, column=col))
                else:
                    for v_name in names:
                        self.symbols.define(Symbol(name=v_name, type=AnyType(), kind="let", is_mutable=False, line=line, column=col))
        except SemanticError as e:
            self._record_error(e)

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        val_expr = node.children[1]

        rule = target_node.data
        target_type: Type = AnyType()

        try:
            if rule == "with_target":
                field_name = str(target_node.children[0])
                with_t = self.symbols.current_with_type()
                if with_t is None:
                    raise self._make_error(
                        InvalidWithTargetError,
                        f"Field assignment '.{field_name}' used outside 'with' statement",
                        target_node,
                        code="E0009",
                        help="Wrap in a 'with' block (e.g. 'with player:') or assign directly to an object.",
                        note="Leading dot field assignments require an active 'with' context."
                    )
                if not self.symbols.current_with_is_mutable():
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on immutable 'let' struct in 'with'",
                        target_node,
                        code="E0006",
                        help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                        note="'with' blocks on immutable bindings do not allow field mutations."
                    )
                if isinstance(with_t, RuneType):
                    if field_name not in with_t.fields:
                        raise self._make_error(
                            SemanticError,
                            f"Rune '{with_t.name}' has no field '{field_name}'",
                            target_node,
                            code="E0013",
                            help=f"Check field spelling or verify the definition of rune '{with_t.name}'.",
                            note=f"Rune '{with_t.name}' only exposes its declared fields."
                        )
                    target_type = with_t.fields[field_name]

            elif rule == "normal_target":
                first = target_node.children[0]
                first_str = str(first)

                if first_str == "self":
                    if not self.symbols.is_in_enchanting():
                        raise self._make_error(
                            SemanticError,
                            "'self' is only valid inside 'enchanting' blocks",
                            target_node,
                            code="E0003",
                            help="Use 'self' only inside methods within an 'enchanting' block.",
                            note="'self' represents the instance reference in enchanting methods."
                        )
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "dot_access":
                            raise self._make_error(
                                SelfDotAccessError,
                                "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                                target_node,
                                code="E0003",
                                help="Change 'self.' to 'self->'.",
                                note="'self' in enchanting is always a reference (ref to SelfType)."
                            )
                    target_type = self.inferrer.infer(target_node)

                else:
                    sym = self.symbols.lookup(first_str)
                    if sym is None:
                        with_t = self.symbols.current_with_type()
                        if with_t is not None and isinstance(with_t, RuneType) and first_str in with_t.fields:
                            if not self.symbols.current_with_is_mutable():
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field '{first_str}' on immutable 'let' struct in 'with'",
                                    target_node,
                                    code="E0006",
                                    help="Ensure the target passed to 'with' is a 'var' or a reference (ref to T).",
                                    note="'with' blocks on immutable bindings do not allow field mutations."
                                )
                            target_type = with_t.fields[first_str]
                        else:
                            raise self._make_undefined_error(first_str, target_node, entity_kind="variable")

                    elif len(target_node.children) == 1:

                        if not sym.is_mutable:
                            if sym.kind == "const":
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot assign to constant '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help="Constants cannot be modified after definition.",
                                    note="'const' definitions are compile-time immutable."
                                )
                            raise self._make_error(
                                MutabilityError,
                                f"Cannot assign to immutable 'let' variable '{first_str}'",
                                target_node,
                                code="E0006",
                                help=f"Change 'let {first_str}' to 'var {first_str}' to allow reassignment.",
                                note="'let' bindings are immutable in PenguScript."
                            )
                        target_type = sym.type
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data == "dot_access":
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow field mutation.",
                                    note="Fields of 'let' bindings cannot be modified."
                                )
                        target_type = self.inferrer.infer(target_node)

            elif rule == "essence_target":
                ref_node = target_node.children[0]
                ref_type = self.inferrer.infer(ref_node)
                if not isinstance(ref_type, RefType) and not isinstance(ref_type, AnyType):
                    raise self._make_error(
                        TypeMismatchError,
                        f"'essence of' requires reference type (ref to T), got '{ref_type}'",
                        target_node,
                        code="E0008",
                        help="Pass a reference type (ref to T) to 'essence of'.",
                        note="'essence of' dereferences a pointer/reference."
                    )
                if isinstance(ref_type, RefType):
                    target_type = ref_type.target

            val_type = self.inferrer.infer(val_expr, expected_type=target_type)
            if not val_type.is_compatible(target_type) and not (val_type.is_numeric() and target_type.is_numeric()) and not isinstance(target_type, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Cannot assign value of type '{val_type}' to target of type '{target_type}'",
                    node,
                    code="E0005",
                    help=f"Ensure value type '{val_type}' is compatible with target type '{target_type}'.",
                    note="Assignment requires compatible types."
                )
        except SemanticError as e:
            self._record_error(e)

    def _validate_type_node(self, type_node: Any) -> None:
        """Validates that type nodes properly instantiate generic types and don't use raw type params."""
        if not isinstance(type_node, Tree):
            return
        if type_node.data in ("base_type", "custom_type"):
            first = type_node.children[0]
            t_name = ".".join(str(t) for t in first.children) if isinstance(first, Tree) and first.data == "dotted_path" else str(first)
            rem_children = [c for c in type_node.children[1:] if c is not None]
            has_of = len(rem_children) > 0
            if not has_of:
                if (t_name in self.symbols.generic_runes or 
                    t_name in self.symbols.generic_echos or 
                    t_name in self.symbols.generic_omens or 
                    t_name in self.symbols.generic_aliases):
                    gen_entry = (self.symbols.generic_runes.get(t_name) or 
                                 self.symbols.generic_echos.get(t_name) or 
                                 self.symbols.generic_omens.get(t_name) or 
                                 self.symbols.generic_aliases.get(t_name))
                    params = gen_entry[0] if gen_entry else []
                    params_str = " and ".join(params) if params else "..."
                    err = self._make_error(
                        GenericTypeMissingArgsError,
                        f"Generic type '{t_name}' requires type arguments. Use '{t_name} of {params_str}'.",
                        type_node,
                        code="E0021",
                        help=f"Instantiate the generic type using '{t_name} of {params_str}'.",
                        note="All generic types must be instantiated with 'of' before use."
                    )
                    self._record_error(err)
                elif t_name not in (
                    "int", "i32", "i64", "float", "f32", "f64", "bool", "string", "void", "opaque", "any",
                    "char", "byte", "u8", "i8", "u16", "i16", "u32", "u64", "int8", "uint8",
                    "int16", "uint16", "int32", "uint32", "int64", "uint64", "usize", "isize",
                    "size_t", "short", "ushort", "long", "ulong", "double", "int8_t", "uint8_t",
                    "int16_t", "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t", "uint"
                ) and self.symbols.lookup(t_name) is None and self.symbols.lookup_type(t_name) is None and not (t_name.isupper() and self.symbols.has_includes):
                    err = self._make_error(
                        TypeParamOutsideGenericError,
                        f"Type parameter '{t_name}' can only be used within a generic declaration (shard).",
                        type_node,
                        code="E0022",
                        help="Declare type parameter with 'shard' or use a defined concrete type.",
                        note="Type parameters are only valid inside generic declarations."
                    )
                    self._record_error(err)
            else:
                if (t_name in self.symbols.generic_runes or 
                    t_name in self.symbols.generic_echos or 
                    t_name in self.symbols.generic_omens or 
                    t_name in self.symbols.generic_aliases):
                    gen_entry = (self.symbols.generic_runes.get(t_name) or 
                                 self.symbols.generic_echos.get(t_name) or 
                                 self.symbols.generic_omens.get(t_name) or 
                                 self.symbols.generic_aliases.get(t_name))
                    params = gen_entry[0] if gen_entry else []
                    if len(rem_children) != len(params):
                        err = self._make_error(
                            SemanticError,
                            f"Generic type '{t_name}' expects {len(params)} type argument(s), got {len(rem_children)}",
                            type_node,
                            code="E0005",
                            help=f"Pass {len(params)} type argument(s): '{t_name} of {' and '.join(params)}'.",
                            note="Type parameter count must match generic declaration."
                        )
                        self._record_error(err)
        for c in type_node.children:
            if isinstance(c, Tree):
                self._validate_type_node(c)

    def _check_weave_decl(self, node: Tree) -> None:
        """Type checks weave declaration, parameters, and contained statements.

        Args:
            node: AST Tree for weave definition.
        """
        line, col = self._get_loc(node)
        fn_name = str(node.children[0])

        type_params = []
        rem_children = [c for c in node.children[1:] if c is not None]
        if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
            type_params = [str(c) for c in rem_children[0].children if isinstance(c, Token)]
            rem_children = rem_children[1:]

        def lookup_tp(tname: str):
            if tname in type_params:
                return TypeParam(tname)
            return self.symbols.lookup_type(tname)

        params: List[Tuple[str, Type]] = []
        ret_type: Type = VOID_TYPE
        stmt_children: List[Tree] = []
        has_seen_default = False
        many_param_seen = False
        many_count = 0

        for child in rem_children:
            if isinstance(child, Tree) and child.data == "param_list":
                for p in child.children:
                    if isinstance(p, Tree) and p.data == "param":
                        pn = str(p.children[0])
                        pt = ast_to_type(p.children[1], lookup_tp) if len(p.children) >= 2 else AnyType()
                        has_default = len(p.children) >= 3 and p.children[2] is not None

                        if isinstance(pt, ManyType):
                            many_count += 1
                            if many_count > 1:
                                err = self._make_error(
                                    MultipleManyParamsError,
                                    f"Only one 'many' parameter is allowed in function '{fn_name}'",
                                    p,
                                    code="E0023",
                                    help="A function can only have one 'many' parameter.",
                                    note="PenguScript allows at most one variadic parameter per function."
                                )
                                self._record_error(err)
                            many_param_seen = True
                        elif many_param_seen:
                            err = self._make_error(
                                ManyParamNotLastError,
                                f"The 'many' parameter must be the last parameter in function '{fn_name}'",
                                p,
                                code="E0024",
                                help="Move the 'many' parameter to the end of the parameter list.",
                                note="The variadic parameter 'many' must be the final parameter."
                            )
                            self._record_error(err)

                        if has_default:
                            has_seen_default = True
                            if type_params:
                                def type_depends_on_tp(t: Type) -> bool:
                                    if isinstance(t, TypeParam) or (isinstance(t, BaseType) and t.name in type_params):
                                        return True
                                    if isinstance(t, (RefType, ArrayType, SliceType, ManyType, ListType, MaybeType)):
                                        return type_depends_on_tp(getattr(t, "element", getattr(t, "target", None)))
                                    if isinstance(t, MapType):
                                        return type_depends_on_tp(t.key) or type_depends_on_tp(t.value)
                                    if isinstance(t, ResultType):
                                        return type_depends_on_tp(t.ok_type) or type_depends_on_tp(t.err_type)
                                    if isinstance(t, (RuneType, EchoType, OmenType, AliasType)):
                                        return any(type_depends_on_tp(a) for a in getattr(t, "type_args", []))
                                    return False

                                if type_depends_on_tp(pt):
                                    err = self._make_error(
                                        SemanticError,
                                        f"Generic parameter '{pn}' of type '{pt}' cannot have a default value depending on type parameters",
                                        p,
                                        code="E0005",
                                        help="Remove default value or ensure parameter type is a concrete non-generic type.",
                                        note="Default values in generic functions cannot depend on generic type parameters."
                                    )
                                    self._record_error(err)
                        elif has_seen_default and not isinstance(pt, ManyType):
                            err = self._make_error(
                                SemanticError,
                                f"Non-default parameter '{pn}' follows default parameter in function '{fn_name}'",
                                p,
                                code="E0005",
                                help="Parameters with default values must appear at the end of parameter list.",
                                note="Default arguments must follow all non-default arguments."
                            )
                            self._record_error(err)
                        params.append((pn, pt))
            elif isinstance(child, Tree) and child.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                ret_type = ast_to_type(child, lookup_tp)
            elif isinstance(child, Token) and child.type == "NAME":
                ret_type = ast_to_type(child, lookup_tp)
            elif isinstance(child, Tree) and child.data in ("stmt", "var_decl", "let_decl", "set_stmt", "return_stmt", "if_stmt", "while_stmt", "for_range_stmt", "for_in_stmt", "with_stmt", "expr_stmt"):
                stmt_children.append(child)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="weave", return_type=ret_type, start_line=span_start, end_line=span_end)
        for tp in type_params:
            self.symbols.define(Symbol(name=tp, type=TypeParam(tp), kind="type"))

        for pn, pt in params:
            self.symbols.define(Symbol(name=pn, type=pt, kind="param", is_mutable=False, line=line, column=col))

        for stmt in stmt_children:
            self._check_node(stmt)

        # Inlining and Small Weaves Analysis
        fn_sym = self.symbols.lookup(fn_name)
        if fn_sym:
            has_loop = any(s.data in ("while_stmt", "for_range_stmt", "for_in_stmt") for s in stmt_children)
            node_count = sum(1 for _ in node.iter_subtrees())
            if (len(stmt_children) <= 3 or node_count <= 25) and not has_loop:
                fn_sym.is_inline = True

        # Escape Analysis for local variables
        for s_name, sym in list(self.symbols.current_scope.symbols.items()):
            if sym.kind in ("var", "let"):
                escaped = self._check_symbol_escape(s_name, stmt_children)
                sym.is_stack_alloc = not escaped

        # Implicit return check for last expression
        if stmt_children:
            last_stmt = stmt_children[-1]
            if last_stmt.data == "stmt" and last_stmt.children:
                last_inner = last_stmt.children[0]
                if last_inner.data == "expr_stmt":
                    expr_node = last_inner.children[0]
                    try:
                        last_type = self.inferrer.infer(expr_node, expected_type=ret_type)
                        if ret_type != VOID_TYPE and not last_type.is_compatible(ret_type):
                            err = self._make_error(
                                TypeMismatchError,
                                f"Implicit return type '{last_type}' does not match weave return type '{ret_type}'",
                                expr_node,
                                code="E0020",
                                help=f"Ensure the last expression evaluates to '{ret_type}' or return void.",
                                note="The last expression in a weave function is used as its implicit return value."
                            )
                            self._record_error(err)
                    except SemanticError as e:
                        self._record_error(e)
            elif last_stmt.data == "expr_stmt":
                expr_node = last_stmt.children[0]
                try:
                    last_type = self.inferrer.infer(expr_node, expected_type=ret_type)
                    if ret_type != VOID_TYPE and not last_type.is_compatible(ret_type):
                        err = self._make_error(
                            TypeMismatchError,
                            f"Implicit return type '{last_type}' does not match weave return type '{ret_type}'",
                            expr_node,
                            code="E0020",
                            help=f"Ensure the last expression evaluates to '{ret_type}' or return void.",
                            note="The last expression in a weave function is used as its implicit return value."
                        )
                        self._record_error(err)
                except SemanticError as e:
                    self._record_error(e)

        self.symbols.pop_scope(end_line=span_end)

    def _check_symbol_escape(self, sym_name: str, stmts: List[Tree]) -> bool:
        """Determines if a local variable escapes its function scope via pointer, return, or assignment.

        Uses conservative escape analysis:
        - Escapes if returned directly or via pointer (sigil of x).
        - Escapes if its address (sigil of x) is assigned to a struct field or outer/global variable.
        - Escapes if its address is passed into a function call.
        - Escapes if stored in a container or data structure.

        Args:
            sym_name: Identifier name to analyze.
            stmts: List of function body statements.

        Returns:
            True if symbol escapes stack frame (requires heap allocation), False otherwise.
        """
        escaped = False

        def contains_sigil_of(node: Any) -> bool:
            if not isinstance(node, Tree):
                return False
            if node.data == "sigil_of" and node.children:
                target = node.children[0]
                if isinstance(target, Tree) and target.data == "var_ref" and str(target.children[0]) == sym_name:
                    return True
                if isinstance(target, Token) and str(target) == sym_name:
                    return True
            return any(contains_sigil_of(c) for c in node.children if isinstance(c, Tree))

        def walk(n: Any):
            nonlocal escaped
            if escaped or not isinstance(n, Tree):
                return

            # 1. Direct sigil_of taken on sym_name
            if n.data == "sigil_of":
                target = n.children[0]
                if (isinstance(target, Tree) and target.data == "var_ref" and str(target.children[0]) == sym_name) or (isinstance(target, Token) and str(target) == sym_name):
                    escaped = True
                    return

            # 2. Return statements
            elif n.data == "return_stmt" and n.children:
                ret_val = n.children[0]
                if isinstance(ret_val, Tree):
                    if ret_val.data == "var_ref" and str(ret_val.children[0]) == sym_name:
                        sym = self.symbols.lookup(sym_name)
                        if sym and isinstance(sym.type, RefType):
                            escaped = True
                            return
                    if contains_sigil_of(ret_val):
                        escaped = True
                        return

            # 3. Set statements (assigning address to fields, struct members, globals)
            elif n.data == "set_stmt":
                val_node = n.children[-1]
                if contains_sigil_of(val_node):
                    escaped = True
                    return

            # 4. Function call arguments
            elif n.data in ("calling_expr", "calling_stmt"):
                if contains_sigil_of(n):
                    escaped = True
                    return

            # 5. Rune / struct initialization with sigil
            elif n.data in ("struct_init_expr", "with_init_expr", "array_init_expr"):
                if contains_sigil_of(n):
                    escaped = True
                    return

            for child in n.children:
                walk(child)

        for stmt in stmts:
            walk(stmt)
        return escaped

    def _check_enchanting_method(self, node: Tree, self_type: Type, type_params: Optional[List[str]] = None) -> None:
        """Checks method definition within an enchanting block.

        Args:
            node: AST Tree for enchanting weave method.
            self_type: Receiver Type being enchanted.
            type_params: Optional list of generic type parameters.
        """
        line, col = self._get_loc(node)
        fn_name = str(node.children[0])

        tp_list = type_params or []
        def lookup_m_tp(tname: str):
            if tname in tp_list:
                return TypeParam(tname)
            return self.symbols.lookup_type(tname)

        params: List[Tuple[str, Type]] = []
        ret_type: Type = VOID_TYPE
        stmt_children: List[Tree] = []
        default_count = 0
        has_seen_default = False
        many_param_seen = False
        many_count = 0

        for child in node.children[1:]:
            if isinstance(child, Tree) and child.data == "param_list":
                for p in child.children:
                    if isinstance(p, Tree) and p.data == "param":
                        pn = str(p.children[0])
                        pt = ast_to_type(p.children[1], lookup_m_tp) if len(p.children) >= 2 else AnyType()
                        has_default = len(p.children) >= 3 and p.children[2] is not None

                        if isinstance(pt, ManyType):
                            many_count += 1
                            if many_count > 1:
                                err = self._make_error(
                                    MultipleManyParamsError,
                                    f"Only one 'many' parameter is allowed in method '{fn_name}'",
                                    p,
                                    code="E0023",
                                    help="A function can only have one 'many' parameter.",
                                    note="PenguScript allows at most one variadic parameter per function."
                                )
                                self._record_error(err)
                            many_param_seen = True
                        elif many_param_seen:
                            err = self._make_error(
                                ManyParamNotLastError,
                                f"The 'many' parameter must be the last parameter in method '{fn_name}'",
                                p,
                                code="E0024",
                                help="Move the 'many' parameter to the end of the parameter list.",
                                note="The variadic parameter 'many' must be the final parameter."
                            )
                            self._record_error(err)

                        if has_default:
                            has_seen_default = True
                            default_count += 1
                        elif has_seen_default and not isinstance(pt, ManyType):
                            err = self._make_error(
                                SemanticError,
                                f"Non-default parameter '{pn}' follows default parameter in method '{fn_name}'",
                                p,
                                code="E0005",
                                help="Parameters with default values must appear at the end of parameter list.",
                                note="Default arguments must follow all non-default arguments."
                            )
                            self._record_error(err)
                        params.append((pn, pt))
            elif isinstance(child, Tree) and child.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                ret_type = ast_to_type(child, lookup_m_tp)
            elif isinstance(child, Token) and child.type == "NAME":
                ret_type = ast_to_type(child, lookup_m_tp)
            elif isinstance(child, Tree) and child.data in ("stmt", "var_decl", "let_decl", "set_stmt", "return_stmt", "if_stmt", "while_stmt", "for_range_stmt", "for_in_stmt", "with_stmt", "expr_stmt"):
                stmt_children.append(child)

        method_fn_type = FnType(params=params, return_type=ret_type, default_count=default_count, type_params=tp_list)
        self_t_name = getattr(self_type, "name", str(self_type))
        self.symbols.methods[(self_t_name, fn_name)] = method_fn_type
        if isinstance(self_type, RuneType):
            self_type.methods[fn_name] = method_fn_type

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="weave", return_type=ret_type, enchanting_type=self_type, start_line=span_start, end_line=span_end)
        self.symbols.define(Symbol(name="self", type=RefType(target=self_type), kind="param", is_mutable=False, line=line, column=col))
        for tp in tp_list:
            self.symbols.define(Symbol(name=tp, type=TypeParam(tp), kind="type"))

        for pn, pt in params:
            self.symbols.define(Symbol(name=pn, type=pt, kind="param", is_mutable=False, line=line, column=col))

        for stmt in stmt_children:
            self._check_node(stmt)

        if stmt_children and ret_type != VOID_TYPE:
            last_stmt = stmt_children[-1]
            if last_stmt.data == "expr_stmt":
                expr_node = last_stmt.children[0]
                try:
                    last_type = self.inferrer.infer(expr_node, expected_type=ret_type)
                    if not last_type.is_compatible(ret_type):
                        err = self._make_error(
                            TypeMismatchError,
                            f"Implicit return type '{last_type}' does not match weave return type '{ret_type}'",
                            expr_node,
                            code="E0020",
                            help=f"Ensure the last expression evaluates to '{ret_type}' or return void.",
                            note="The last expression in a weave function is used as its implicit return value."
                        )
                        self._record_error(err)
                except SemanticError as e:
                    self._record_error(e)

        self.symbols.pop_scope(end_line=span_end)

    def _check_if_stmt(self, node: Tree) -> None:
        """Checks if-statement branches and detects unreachable dead code branches.

        Args:
            node: AST Tree for if statement.
        """
        line, col = self._get_loc(node)
        cond_node = node.children[0]
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None

        folded_cond = self.const_folder.fold(cond_node)

        span_start, span_end = self._get_node_span(block_node)
        self.symbols.push_scope(kind="if", start_line=span_start, end_line=span_end)

        if isinstance(cond_node, Tree) and cond_node.data == "if_cond_binding_present":
            bind_name = str(cond_node.children[0])
            bind_type = ast_to_type(cond_node.children[1], self.symbols.lookup_type)
            init_expr = cond_node.children[2]
            try:
                inferred = self.inferrer.infer(init_expr)
                self.symbols.define(Symbol(name=bind_name, type=bind_type, kind="let", is_mutable=False, line=line, column=col))
            except SemanticError as e:
                self._record_error(e)

        elif isinstance(cond_node, Tree) and cond_node.data == "if_cond_binding":
            bind_name = str(cond_node.children[0])
            bind_type = ast_to_type(cond_node.children[1], self.symbols.lookup_type)
            init_expr = cond_node.children[2]
            try:
                inferred = self.inferrer.infer(init_expr)
                self.symbols.define(Symbol(name=bind_name, type=bind_type, kind="let", is_mutable=False, line=line, column=col))
            except SemanticError as e:
                self._record_error(e)

        else:
            try:
                c_type = self.inferrer.infer(cond_node)
                if not c_type.is_compatible(BOOL_TYPE) and not isinstance(c_type, AnyType):
                    err = self._make_error(
                        TypeMismatchError,
                        f"'if' condition must be bool, got '{c_type}'",
                        cond_node,
                        code="E0005",
                        help="Ensure 'if' condition evaluates to a boolean (bool).",
                        note="Branch conditions must be boolean expressions."
                    )
                    self._record_error(err)
            except SemanticError as e:
                self._record_error(e)

        if folded_cond is False:
            self.warnings.append("[W0004] Unreachable code in then branch")
        else:
            self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)

        if else_node is not None:
            if folded_cond is True:
                self.warnings.append("[W0004] Unreachable code in else branch")
            else:
                e_start, e_end = self._get_node_span(else_node)
                self.symbols.push_scope(kind="if", start_line=e_start, end_line=e_end)
                self._check_node(else_node)
                self.symbols.pop_scope(end_line=e_end)

    def _check_unless_stmt(self, node: Tree) -> None:
        """Checks unless-statement condition and blocks.

        Args:
            node: AST Tree for unless statement.
        """
        line, col = self._get_loc(node)
        cond_node = node.children[0]
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None

        span_start, span_end = self._get_node_span(block_node)
        self.symbols.push_scope(kind="if", start_line=span_start, end_line=span_end)
        try:
            c_type = self.inferrer.infer(cond_node)
            if not c_type.is_compatible(BOOL_TYPE) and not isinstance(c_type, AnyType):
                err = self._make_error(
                    TypeMismatchError,
                    f"'unless' condition must be bool, got '{c_type}'",
                    cond_node,
                    code="E0005",
                    help="Ensure 'unless' condition evaluates to a boolean (bool).",
                    note="Branch conditions must be boolean expressions."
                )
                self._record_error(err)
        except SemanticError as e:
            self._record_error(e)

        self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)

        if else_node is not None:
            e_start, e_end = self._get_node_span(else_node)
            self.symbols.push_scope(kind="if", start_line=e_start, end_line=e_end)
            self._check_node(else_node)
            self.symbols.pop_scope(end_line=e_end)

    def _check_while_stmt(self, node: Tree) -> None:
        """Checks while-loop condition and body statements.

        Args:
            node: AST Tree for while statement.
        """
        line, col = self._get_loc(node)
        cond_node = node.children[0]
        block_node = node.children[1]

        try:
            c_type = self.inferrer.infer(cond_node)
            if not c_type.is_compatible(BOOL_TYPE) and not isinstance(c_type, AnyType):
                err = self._make_error(
                    TypeMismatchError,
                    f"'while' condition must be bool, got '{c_type}'",
                    cond_node,
                    code="E0005",
                    help="Ensure 'while' condition evaluates to a boolean (bool).",
                    note="Loop conditions must be boolean expressions."
                )
                self._record_error(err)
        except SemanticError as e:
            self._record_error(e)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="while", in_loop=True, start_line=span_start, end_line=span_end)
        self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)

    def _check_for_range_stmt(self, node: Tree) -> None:
        """Checks numeric range for-loop bounds and step expressions.

        Args:
            node: AST Tree for for-range statement.
        """
        line, col = self._get_loc(node)
        var_name = str(node.children[0])
        start_node = node.children[1]
        end_node = node.children[2]
        step_node = node.children[3] if len(node.children) == 5 else None
        block_node = node.children[-1]

        try:
            st = self.inferrer.infer(start_node)
            et = self.inferrer.infer(end_node)
            if not st.is_int():
                err = self._make_error(
                    TypeMismatchError,
                    f"'for from' start bound must be integer, got '{st}'",
                    start_node,
                    code="E0005",
                    help="Use an integer value for loop range start.",
                    note="Range bounds must be integer values."
                )
                self._record_error(err)
            if not et.is_int():
                err = self._make_error(
                    TypeMismatchError,
                    f"'for to' end bound must be integer, got '{et}'",
                    end_node,
                    code="E0005",
                    help="Use an integer value for loop range end.",
                    note="Range bounds must be integer values."
                )
                self._record_error(err)
            if step_node is not None:
                step_t = self.inferrer.infer(step_node)
                if not step_t.is_int():
                    err = self._make_error(
                        TypeMismatchError,
                        f"'for step' must be integer, got '{step_t}'",
                        step_node,
                        code="E0005",
                        help="Use an integer value for loop step.",
                        note="Loop step must be an integer value."
                    )
                    self._record_error(err)
        except SemanticError as e:
            self._record_error(e)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="for", in_loop=True, start_line=span_start, end_line=span_end)
        self.symbols.define(Symbol(name=var_name, type=INT_TYPE, kind="var", is_mutable=False, line=line, column=col))
        self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)

    def _check_for_in_stmt(self, node: Tree) -> None:
        """Checks collection iterator for-loop and element binding.

        Args:
            node: AST Tree for for-in statement.
        """
        line, col = self._get_loc(node)
        var_name = str(node.children[0])
        iter_node = node.children[1]
        block_node = node.children[2]

        elem_type: Type = AnyType()
        try:
            it = self.inferrer.infer(iter_node)
            if not it.is_iterable() and it != STRING_TYPE and not isinstance(it, AnyType):
                err = self._make_error(
                    SemanticError,
                    f"Cannot iterate over non-collection type '{it}'",
                    iter_node,
                    code="E0005",
                    help="Provide an iterable collection like an array, slice, or list.",
                    note="'for ... in' loops require iterable collections."
                )
                self._record_error(err)
            elem_type = it.element_type() or AnyType()
        except SemanticError as e:
            self._record_error(e)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="for", in_loop=True, start_line=span_start, end_line=span_end)
        self.symbols.define(Symbol(name=var_name, type=elem_type, kind="var", is_mutable=False, line=line, column=col))
        self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)

    def _check_with_stmt(self, node: Tree) -> None:
        """Checks with-statement binding and sets desugar annotations.

        Args:
            node: AST Tree for with statement.
        """
        line, col = self._get_loc(node)
        target_expr = node.children[0]
        block_node = node.children[1:]

        target_type: Type = AnyType()
        is_mut = False
        target_var_name = None

        try:
            target_type = self.inferrer.infer(target_expr)
            if isinstance(target_expr, Tree) and target_expr.data == "var_ref":
                target_var_name = str(target_expr.children[0])
                sym = self.symbols.lookup(target_var_name)
                if sym:
                    is_mut = sym.is_mutable or isinstance(sym.type, RefType)
            elif isinstance(target_type, RefType):
                is_mut = True
        except SemanticError as e:
            self._record_error(e)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="with", with_type=target_type, with_is_mutable=is_mut, with_target_var_name=target_var_name, start_line=span_start, end_line=span_end)
        for b in block_node:
            self._check_node(b)
        self.symbols.pop_scope(end_line=span_end)

    def _check_return_stmt(self, node: Tree) -> None:
        """Checks return statement value against enclosing function return type.

        Args:
            node: AST Tree for return statement.
        """
        line, col = self._get_loc(node)
        curr_ret = self.symbols.current_return_type()

        if len(node.children) == 0:
            if curr_ret is not None and curr_ret != VOID_TYPE and not isinstance(curr_ret, AnyType):
                err = self._make_error(
                    TypeMismatchError,
                    f"Return statement with no value in function returning '{curr_ret}'",
                    node,
                    code="E0020",
                    help=f"Return an expression of type '{curr_ret}'.",
                    note="Functions with non-void return types must return a value."
                )
                self._record_error(err)
            return

        expr_node = node.children[0]
        try:
            val_type = self.inferrer.infer(expr_node, expected_type=curr_ret)
            if curr_ret is not None and not val_type.is_compatible(curr_ret) and not isinstance(curr_ret, AnyType):
                err = self._make_error(
                    TypeMismatchError,
                    f"Returned value of type '{val_type}' does not match weave return type '{curr_ret}'",
                    expr_node,
                    code="E0020",
                    help=f"Return an expression of type '{curr_ret}' or change function signature 'into {val_type}'.",
                    note="Return values must match the declared function return type."
                )
                self._record_error(err)
        except SemanticError as e:
            self._record_error(e)

    def _check_or_block(self, node: Tree) -> None:
        """Checks error handling 'or:' block.

        Args:
            node: AST Tree for or-block statement.
        """
        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="or_block", in_or_block=True, start_line=span_start, end_line=span_end)
        for child in node.children:
            if isinstance(child, Tree):
                self._check_node(child)
        self.symbols.pop_scope(end_line=span_end)
