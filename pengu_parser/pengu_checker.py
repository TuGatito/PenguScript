from __future__ import annotations
import os
from typing import List, Set, Optional, Dict, Tuple, Any
from lark import Tree, Token

from .pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ManyType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, OPAQUE_TYPE, AliasType, AnyType, FrozenType,
    TypeParam, NullType, NULL_TYPE, INT_TYPE, I32_TYPE, I64_TYPE, U32_TYPE, U64_TYPE, CHAR_TYPE, BYTE_TYPE,
    U8_TYPE, I8_TYPE, U16_TYPE, I16_TYPE, USIZE_TYPE, ISIZE_TYPE, FLOAT_TYPE, F32_TYPE,
    F64_TYPE, DOUBLE_TYPE, BOOL_TYPE, STRING_TYPE, VOID_TYPE, ERROR_TYPE, ConceptType, SealType,
    CVarArgsType,
    implements_concept, resolve_concept_method, ast_to_type
)
from .pengu_symbols import SymbolTable, Symbol, Scope, resolve_imports, find_module_path
from .pengu_infer import TypeInferrer, ConstFolder
from .pengu_comptime import CompileTimeEnv, default_env, eval_comptime
from .pengu_grammar import SIMPLE_STMT_ALIASES
from .pengu_errors import (
    PenguError, ErrorReporter, SemanticError, ConstInsideWeaveError, VarLetTopLevelError,
    SelfDotAccessError, UndefinedIdentifierError, TypeMismatchError, MutabilityError,
    InvalidControlFlowError, InvalidMemoryOpError, InvalidWithTargetError,
    GenericTypeMissingArgsError, TypeParamOutsideGenericError, MultipleManyParamsError,
    ManyParamNotLastError, MultipleInsigniaError, DuplicateOmenValueError,
    InvalidOmenPayloadValueError, InvalidOmenConstantValueError,
    ConceptMethodMismatchError, UnimplementedConceptMethodError, ConceptBoundNotSatisfiedError,
    InvalidRitualSelfAccessError, InvalidRitualCallError,
    ArraySizeMismatchError, InvalidRangeError, PrivateSymbolAccessError, NonExhaustiveJudgeError,
    UnknownArrayDimensionError, suggest_similar_identifier
)



def _node_to_name(node: Any) -> str:
    """Extracts plain identifier / type name from Token or Tree (dotted_path, custom_type, etc.)."""
    if isinstance(node, Token):
        return str(node)
    if isinstance(node, Tree):
        if node.data == "dotted_path":
            return ".".join(str(c) for c in node.children if isinstance(c, (Token, str)))
        if node.data in ("custom_type", "type_param", "type", "where_bound", "base_type"):
            if node.children:
                return _node_to_name(node.children[0])
        if len(node.children) == 1:
            return _node_to_name(node.children[0])
        return ".".join(_node_to_name(c) for c in node.children if isinstance(c, (Token, Tree)))
    return str(node)


def _extract_weave_modifiers(children: List[Any], start_idx: int = 0) -> Tuple[bool, bool, int]:
    """Extracts is_inline, is_ritual and returns (is_inline, is_ritual, next_idx)."""
    is_inline = False
    is_ritual = False
    idx = start_idx
    while idx < len(children):
        ch = children[idx]
        if isinstance(ch, Tree) and ch.data == "weave_modifier":
            val = str(ch.children[0])
            if val == "inline": is_inline = True
            elif val == "ritual": is_ritual = True
            idx += 1
        elif isinstance(ch, Token) and (ch.type == "WEAVE_MODIFIER" or str(ch) in ("inline", "ritual")):
            if str(ch) == "inline": is_inline = True
            elif str(ch) == "ritual": is_ritual = True
            idx += 1
        else:
            break
    return is_inline, is_ritual, idx


def extract_shard_params(shard_node: Tree) -> Tuple[List[str], Dict[str, List[str]]]:
    """Extracts type parameter names and optional where concept bounds from a shard_params AST node."""
    type_params: List[str] = []
    bounds: Dict[str, List[str]] = {}
    if not isinstance(shard_node, Tree):
        return type_params, bounds
    for ch in shard_node.children:
        if isinstance(ch, Token) and ch.type == "NAME":
            type_params.append(str(ch))
        elif isinstance(ch, Tree) and ch.data == "where_clause":
            for wb in ch.children:
                if isinstance(wb, Tree) and wb.data == "where_bound":
                    t_param_name = _node_to_name(wb.children[0])
                    concept_name = _node_to_name(wb.children[1])
                    bounds.setdefault(t_param_name, []).append(concept_name)
    return type_params, bounds


# Loop rules that can also be used as values (collecting their body's value).
_LOOP_RULES = ("while_stmt", "for_range_stmt", "for_in_stmt")


class PenguChecker:
    """Performs comprehensive semantic analysis, type checking, and optimization tagging.

    Ensures V-safety rules, type soundness, ownership boundaries, and module integrity.
    """

    def __init__(
        self,
        source: str = "",
        filename: str = "main.pengu",
        source_code: Optional[str] = None,
        base_dir: Optional[str] = None,
        compile_env: Optional[CompileTimeEnv] = None
    ):
        """Initializes semantic checker instance with source code and directory context.

        Args:
            source: Source code text.
            filename: Source file path.
            source_code: Optional explicit source code text override.
            base_dir: Base directory for module import resolution.
            compile_env: Optional compile-time environment for 'when' clauses.
        """
        self.source_code = source_code if source_code is not None else source
        self.filename = filename
        if base_dir is not None:
            self.base_dir = os.path.abspath(base_dir)
        elif os.path.isabs(filename) or "/" in filename or "\\" in filename:
            self.base_dir = os.path.abspath(os.path.dirname(filename))
        else:
            self.base_dir = os.path.abspath(os.getcwd())
        self.compile_env = compile_env if compile_env is not None else default_env()

        self.errors: List[PenguError] = []
        self.warnings: List[str] = []
        self.symbols = SymbolTable()
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
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
        self.inferrer = TypeInferrer(self.symbols, source_code=self.source_code, filename=self.filename,
                                     compile_env=self.compile_env)
        self.const_folder = ConstFolder(self.symbols)
        if import_order is not None:
            self.symbols.import_order = import_order

        # Pass 1: Collect all top-level types, functions, declarations, includes, and modules
        self._collect_top_level(tree, import_order=import_order)
        self._check_omen_variant_collisions()

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
        if idx >= len(lines):
            return None
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

    def _eval_when_condition(self, cond_node: Any, node: Any) -> Optional[bool]:
        """Evaluates a 'when' condition against the compile-time environment.

        Returns True/False, or None (recording an error) when the condition is
        not a constant boolean expression.
        """
        val = eval_comptime(self.compile_env, cond_node)
        if val is None or not isinstance(val, bool):
            err = self._make_error(
                SemanticError,
                "'when' condition must evaluate to a compile-time boolean constant",
                node,
                code="E0039",
                help="Use expressions such as os == \"windows\", defined(NAME), or literal true/false.",
                note="Compile-time 'when' conditions must be constant and side-effect free."
            )
            self._record_error(err)
            return None
        return val

    def _active_when_top_items(self, node: Tree) -> List[Tree]:
        """Returns the top_stmt wrappers belonging to the active branch of a when_top_decl.

        Args:
            node: when_top_decl AST node.

        Returns:
            List of 'top_stmt' trees that should be processed for this platform.
        """
        chosen: List[Tree] = []
        if not node.children:
            return chosen
        val = self._eval_when_condition(node.children[0], node)
        if val is None:
            return chosen
        if val:
            for c in node.children[1:]:
                if isinstance(c, Tree) and c.data == "top_stmt":
                    chosen.append(c)
        else:
            for c in node.children[1:]:
                if not isinstance(c, Tree):
                    continue
                if c.data == "when_top_else_plain":
                    for ic in c.children:
                        if isinstance(ic, Tree) and ic.data == "top_stmt":
                            chosen.append(ic)
                elif c.data == "when_top_else_when":
                    for ic in c.children:
                        if isinstance(ic, Tree):
                            if ic.data == "top_stmt":
                                chosen.append(ic)
                            elif ic.data == "when_top_decl":
                                chosen.append(Tree("top_stmt", [ic]))
        return chosen

    def _active_when_stmt_items(self, node: Tree) -> Tuple[Optional[Tree], Optional[Tree]]:
        """Resolves the active branch of a statement-level when_stmt.

        Returns:
            (then_block_or_None, else_children_container_or_None). The caller
            decides how to traverse each based on its Lark rule ('block',
            'when_else_plain' or 'when_else_when').
        """
        if not node.children:
            return None, None
        val = self._eval_when_condition(node.children[0], node)
        if val is None:
            return None, None
        then_block = node.children[1] if (len(node.children) > 1 and isinstance(node.children[1], Tree) and node.children[1].data == "block") else None
        else_node = node.children[2] if len(node.children) > 2 and isinstance(node.children[2], Tree) else None
        if val:
            return then_block, None
        return None, else_node

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
        current_insignia: Optional[str] = None

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
            while isinstance(stmt, Tree) and stmt.data == "top_stmt" and stmt.children:
                stmt = stmt.children[0]
            if not isinstance(stmt, Tree):
                continue

            line, col = self._get_loc(stmt)
            rule = stmt.data

            if rule == "insignia_stmt":
                if current_insignia is not None:
                    err = self._make_error(
                        MultipleInsigniaError,
                        "Multiple 'insignia' directives not allowed",
                        stmt,
                        code="E0026",
                        help="Only one 'insignia' directive is allowed per module file.",
                        note="The 'insignia' directive sets the global C prefix for all subsequent declarations in this file."
                    )
                    self._record_error(err)
                else:
                    prefix_tok = stmt.children[0]
                    current_insignia = str(prefix_tok)
                    self.symbols.insignia = current_insignia

            elif rule == "include_stmt":
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
                alias = None
                if len(stmt.children) > 1 and stmt.children[1] is not None:
                    alias = str(stmt.children[1])
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
                bind_name = alias if alias is not None else last_name

                if alias is not None:
                    if alias == "_":
                        err = self._make_error(
                            SemanticError,
                            "Import alias cannot be '_' (discard)",
                            stmt,
                            code="E0036",
                            help="Use a meaningful identifier as the import alias.",
                            note="'_' is reserved as a discard placeholder and cannot alias a module."
                        )
                        self._record_error(err)
                    else:
                        # Conflicts are only reported against built-ins or names
                        # declared in THIS file; in a multi-module build every
                        # module is collected into one shared table, so symbols
                        # from other files must not trip the alias check.
                        def _same_file(fp):
                            if not fp:
                                return True  # built-in / global-scope symbol
                            try:
                                return os.path.abspath(fp) == os.path.abspath(self.filename)
                            except Exception:
                                return fp == self.filename
                        clash = self.symbols.lookup(alias)
                        if clash is not None and _same_file(clash.file_path):
                            err = self._make_error(
                                SemanticError,
                                f"Import alias '{alias}' for module '{dot_path}' conflicts with an existing symbol",
                                stmt,
                                code="E0036",
                                help=f"Choose a different alias for module '{dot_path}'.",
                                note="Import aliases must not collide with other visible names."
                            )
                            self._record_error(err)

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
                                eff_c_name = sym.get_c_name()
                                if sym.kind in ("weave", "function", "declare") and isinstance(sym.type, FnType):
                                    self.symbols.functions[f"{bind_name}_{sname}"] = sym.type
                                    self.symbols.functions[eff_c_name] = sym.type
                                if sym.kind == "rune" and isinstance(sym.type, RuneType):
                                    self.symbols.runes[f"{bind_name}_{sname}"] = sym.type
                                    self.symbols.runes[eff_c_name] = sym.type
                                if sym.kind == "const":
                                    self.symbols.consts[f"{bind_name}_{sname}"] = (sym.type, getattr(sym, "const_val", None))
                                    self.symbols.consts[eff_c_name] = (sym.type, getattr(sym, "const_val", None))
                                if sym.kind == "alias" and isinstance(sym.type, AliasType):
                                    self.symbols.aliases[f"{bind_name}_{sname}"] = sym.type.target
                                    self.symbols.aliases[eff_c_name] = sym.type.target
                                    self.symbols.aliases[sname] = sym.type.target
                                    self.symbols.global_scope.define(sym)
                        for gname, ginfo in sub_checker.symbols.generic_functions.items():
                            self.symbols.generic_functions[gname] = ginfo
                            self.symbols.generic_functions[f"{bind_name}_{gname}"] = ginfo
                except Exception:
                    pass

                mod_doc = self._extract_preceding_doc(line) or f"Module `{dot_path}`"
                self.symbols.global_scope.define(Symbol(
                    name=bind_name,
                    type=RuneType(name=bind_name),
                    kind="import",
                    line=line, column=col,
                    doc=mod_doc,
                    module_scope=mod_scope,
                    file_path=mod_file
                ))

            elif rule == "when_top_decl":
                chosen = self._active_when_top_items(stmt)
                if chosen:
                    self._collect_top_level(Tree("file", chosen))

            elif rule == "rune_decl":
                r_name = str(stmt.children[0])
                c_r_name = f"{current_insignia}{r_name}" if current_insignia else r_name
                type_params = []
                bounds = {}
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
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
                        return TypeParam(tname, bounds=bounds.get(tname, []))
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
                if c_r_name != r_name:
                    self.symbols.runes[c_r_name] = rune_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=r_name, type=rune_t, kind="rune", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_r_name
                ))

            elif rule == "echo_decl":
                e_name = str(stmt.children[0])
                c_e_name = f"{current_insignia}{e_name}" if current_insignia else e_name
                type_params = []
                bounds = {}
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
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
                if c_e_name != e_name:
                    self.symbols.echos[c_e_name] = echo_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=e_name, type=echo_t, kind="echo", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_e_name
                ))

            elif rule == "omen_decl":
                o_name = str(stmt.children[0])
                c_o_name = f"{current_insignia}{o_name}" if current_insignia else o_name
                type_params = []
                bounds = {}
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    return self.symbols.lookup_type(tname)

                variants: Dict[str, Dict[str, Type]] = {}
                variant_values: Dict[str, Any] = {}
                seen_values: Dict[Any, str] = {}
                current_value = 0
                has_any_payload = False
                is_string_mode = any(isinstance(c, Tree) and c.data == "omen_string_kind" for c in stmt.children[1:])
                value_kind: Optional[str] = None  # 'int' | 'str' | None

                def _record_value_kind(kind: str, v_name: str, node: Any) -> None:
                    nonlocal value_kind
                    if value_kind is None:
                        value_kind = kind
                    elif value_kind != kind:
                        err = self._make_error(
                            SemanticError,
                            f"Cannot mix integer and string values in omen '{o_name}' (variant '{v_name}' uses {kind} values)",
                            node,
                            code="E0029",
                            help="Use either integer values or string values for every variant, not both.",
                            note="Omen variant values must be homogenous (all ints or all strings)."
                        )
                        self._record_error(err)

                for var_node in rem_children:
                    if isinstance(var_node, Tree) and var_node.data == "omen_variant":
                        v_name = str(var_node.children[0])
                        v_fields: Dict[str, Type] = {}
                        has_payload = False
                        is_expr_node = None

                        for of_node in var_node.children[1:]:
                            if isinstance(of_node, Tree) and of_node.data == "omen_field":
                                has_payload = True
                                has_any_payload = True
                                fn = str(of_node.children[0])
                                ft = ast_to_type(of_node.children[1], lookup_tp)
                                v_fields[fn] = ft
                            elif isinstance(of_node, Tree):
                                is_expr_node = of_node

                        if has_payload and is_expr_node is not None:
                            err = self._make_error(
                                InvalidOmenPayloadValueError,
                                f"Value assignment is not allowed on algebraic omen variant '{v_name}' with payload ('with')",
                                is_expr_node,
                                code="E0028",
                                help="Remove 'is <value>' from algebraic variants with 'with'.",
                                note="Explicit variant values are only supported on simple enums without payload."
                            )
                            self._record_error(err)

                        if has_payload and is_string_mode:
                            err = self._make_error(
                                SemanticError,
                                f"String-valued omen '{o_name}' cannot define payload variants like '{v_name}' ('with' fields)",
                                var_node,
                                code="E0029",
                                help="Use 'with string' only for simple enums whose variants map to string constants.",
                                note="String-valued omens are simple constant enums and do not carry payloads."
                            )
                            self._record_error(err)

                        if not has_payload:
                            assigned_val = None
                            if is_string_mode:
                                # 'omen X with string:' auto-assigns each variant its own name.
                                assigned_val = v_name
                                _record_value_kind("str", v_name, var_node)
                            elif is_expr_node is not None:
                                folded = self.const_folder.fold(is_expr_node)
                                if folded is None or not (isinstance(folded, (int, str)) and not isinstance(folded, bool)):
                                    err = self._make_error(
                                        InvalidOmenConstantValueError,
                                        f"Omen variant '{v_name}' value must be a compile-time integer constant or string literal",
                                        is_expr_node,
                                        code="E0029",
                                        help="Use a compile-time integer literal, string literal, or constant expression.",
                                        note="Omen values must evaluate to an integer or a string at compile time."
                                    )
                                    self._record_error(err)
                                    assigned_val = current_value
                                    current_value += 1
                                    _record_value_kind("int", v_name, var_node)
                                else:
                                    assigned_val = folded
                                    if isinstance(folded, str):
                                        _record_value_kind("str", v_name, is_expr_node)
                                    else:
                                        _record_value_kind("int", v_name, is_expr_node)
                                        current_value = folded + 1
                            else:
                                # Implicit auto-increment requires integer values only.
                                _record_value_kind("int", v_name, var_node)
                                assigned_val = current_value
                                current_value += 1

                            if assigned_val in seen_values:
                                first_v = seen_values[assigned_val]
                                err = self._make_error(
                                    DuplicateOmenValueError,
                                    f"Duplicate value '{assigned_val}' in omen '{o_name}': variants '{first_v}' and '{v_name}' have the same value",
                                    var_node,
                                    code="E0027",
                                    help="Ensure all omen variant values are unique.",
                                    note="Omen variant values must be distinct."
                                )
                                self._record_error(err)
                            else:
                                seen_values[assigned_val] = v_name
                            variant_values[v_name] = assigned_val

                        variants[v_name] = v_fields

                if has_any_payload and not is_string_mode:
                    variant_values = {}

                if type_params:
                    self.symbols.generic_omens[o_name] = (type_params, stmt)
                    omen_t = OmenType(name=o_name, variants=variants, variant_values=variant_values, type_params=type_params, c_name=c_o_name)
                else:
                    omen_t = OmenType(name=o_name, variants=variants, variant_values=variant_values, c_name=c_o_name)

                self.symbols.omens[o_name] = omen_t
                if c_o_name != o_name:
                    self.symbols.omens[c_o_name] = omen_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=o_name, type=omen_t, kind="omen", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_o_name
                ))
                for v_name in variants:
                    c_v_name = f"{c_o_name}_{v_name}"
                    self.symbols.global_scope.define(Symbol(
                        name=f"{o_name}_{v_name}", type=omen_t, kind="omen_variant", is_mutable=False, line=line, column=col, file_path=self.filename, c_name=c_v_name
                    ))
                    if self.symbols.lookup(v_name) is None:
                        self.symbols.global_scope.define(Symbol(
                            name=v_name, type=omen_t, kind="omen_variant", is_mutable=False, line=line, column=col, file_path=self.filename, c_name=c_v_name
                        ))

            elif rule == "alias_decl":
                a_name = str(stmt.children[0])
                c_a_name = f"{current_insignia}{a_name}" if current_insignia else a_name
                type_params = []
                bounds = {}
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    return self.symbols.lookup_type(tname)

                target_t = ast_to_type(rem_children[0], lookup_tp)
                alias_obj = AliasType(name=a_name, target=target_t, type_params=type_params)
                if type_params:
                    self.symbols.generic_aliases[a_name] = (type_params, stmt)
                self.symbols.aliases[a_name] = alias_obj
                if c_a_name != a_name:
                    self.symbols.aliases[c_a_name] = alias_obj
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=a_name, type=alias_obj, kind="alias", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_a_name
                ))

            elif rule == "seal_decl":
                s_name = str(stmt.children[0])
                c_s_name = f"{current_insignia}{s_name}" if current_insignia else s_name
                underlying_t = ast_to_type(stmt.children[1], self.symbols.lookup_type)
                seal_obj = SealType(name=s_name, underlying=underlying_t, c_name=c_s_name)
                self.symbols.seals[s_name] = seal_obj
                if c_s_name != s_name:
                    self.symbols.seals[c_s_name] = seal_obj
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=s_name, type=seal_obj, kind="seal", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_s_name
                ))

            elif rule == "concept_decl":
                concept_name = str(stmt.children[0])
                c_concept_name = f"{current_insignia}{concept_name}" if current_insignia else concept_name
                rem_children = [c for c in stmt.children[1:] if c is not None]
                type_params = []
                bounds = {}
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    return self.symbols.lookup_type(tname)

                methods: Dict[str, FnType] = {}
                ritual_methods: Set[str] = set()
                for m_node in rem_children:
                    if isinstance(m_node, Tree) and m_node.data == "concept_method":
                        m_is_inline, m_is_ritual, m_idx = _extract_weave_modifiers(m_node.children)
                        m_name = str(m_node.children[m_idx])
                        m_rem = [c for c in m_node.children[m_idx+1:] if c is not None]
                        m_tparams = []
                        if m_rem and isinstance(m_rem[0], Tree) and m_rem[0].data == "shard_params":
                            m_tparams, _ = extract_shard_params(m_rem[0])
                            m_rem = m_rem[1:]

                        def lookup_m_tp(tname: str):
                            if tname in m_tparams:
                                return TypeParam(tname)
                            return lookup_tp(tname)

                        m_params: List[Tuple[Optional[str], Type]] = []
                        m_ret: Type = VOID_TYPE
                        for cn in m_rem:
                            if isinstance(cn, Tree) and cn.data == "param_list":
                                for p in cn.children:
                                    if isinstance(p, Tree) and p.data == "param":
                                        pn = str(p.children[0])
                                        pt = ast_to_type(p.children[1], lookup_m_tp) if len(p.children) >= 2 else AnyType()
                                        m_params.append((pn, pt))
                            elif isinstance(cn, Tree) and cn.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                                m_ret = ast_to_type(cn, lookup_m_tp)
                            elif isinstance(cn, Token) and cn.type == "NAME":
                                m_ret = ast_to_type(cn, lookup_m_tp)

                        m_fn_t = FnType(params=m_params, return_type=m_ret, is_ritual=m_is_ritual, type_params=m_tparams)
                        methods[m_name] = m_fn_t
                        if m_is_ritual:
                            ritual_methods.add(m_name)

                concept_obj = ConceptType(
                    name=concept_name,
                    methods=methods,
                    ritual_methods=ritual_methods,
                    type_params=type_params,
                    c_name=c_concept_name
                )
                self.symbols.concepts[concept_name] = concept_obj
                if c_concept_name != concept_name:
                    self.symbols.concepts[c_concept_name] = concept_obj
                if type_params:
                    self.symbols.generic_concepts[concept_name] = (type_params, stmt)
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=concept_name, type=concept_obj, kind="concept", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_concept_name
                ))

            elif rule == "bind_decl":
                target_type_node = stmt.children[0]
                concept_name_node = stmt.children[1]
                rem_children = [c for c in stmt.children[2:] if c is not None]
                type_params = []
                bounds = {}
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    return self.symbols.lookup_type(tname)

                target_type = ast_to_type(target_type_node, lookup_tp)
                concept_name = _node_to_name(concept_name_node)
                target_name = getattr(target_type, "name", str(target_type))
                base_tname = target_name.split("_")[0]

                if not self.symbols.has_includes:
                    target_exists = (
                        self.symbols.lookup_type(base_tname) is not None
                        or base_tname in self.symbols.generic_runes
                    )
                    if not target_exists:
                        err = self._make_error(
                            UndefinedIdentifierError,
                            f"Undefined type '{base_tname}' in bind declaration",
                            target_type_node,
                            code="E0004",
                            help=f"Define rune/echo '{base_tname}:' before binding a concept to it.",
                            note=f"Type '{base_tname}' has not been declared."
                        )
                        self._record_error(err)

                concept_obj = self.symbols.lookup_concept(concept_name)
                if concept_obj is None and not self.symbols.has_includes:
                    err = self._make_error(
                        UndefinedIdentifierError,
                        f"Undefined concept '{concept_name}' in bind declaration",
                        concept_name_node,
                        code="E0004",
                        help=f"Define 'concept {concept_name}:' before binding it.",
                        note=f"Concept '{concept_name}' has not been declared."
                    )
                    self._record_error(err)

                implemented_methods: Dict[str, FnType] = {}
                for m_decl in rem_children:
                    if isinstance(m_decl, Tree) and m_decl.data == "weave_decl":
                        m_is_inline, m_is_ritual, m_idx = _extract_weave_modifiers(m_decl.children)
                        m_name = str(m_decl.children[m_idx])
                        m_rem = [c for c in m_decl.children[m_idx+1:] if c is not None]
                        m_tparams = []
                        if m_rem and isinstance(m_rem[0], Tree) and m_rem[0].data == "shard_params":
                            m_tparams, _ = extract_shard_params(m_rem[0])
                            m_rem = m_rem[1:]

                        def lookup_m_tp(tname: str):
                            if tname in m_tparams:
                                return TypeParam(tname)
                            return lookup_tp(tname)

                        m_params: List[Tuple[Optional[str], Type]] = []
                        m_ret: Type = VOID_TYPE
                        default_count = 0
                        for cn in m_rem:
                            if isinstance(cn, Tree) and cn.data == "param_list":
                                for p in cn.children:
                                    if isinstance(p, Tree) and p.data == "param":
                                        pn = str(p.children[0])
                                        pt = ast_to_type(p.children[1], lookup_m_tp) if len(p.children) >= 2 else AnyType()
                                        if len(p.children) >= 3 and p.children[2] is not None:
                                            default_count += 1
                                        m_params.append((pn, pt))
                            elif isinstance(cn, Tree) and cn.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                                m_ret = ast_to_type(cn, lookup_m_tp)
                            elif isinstance(cn, Token) and cn.type == "NAME":
                                m_ret = ast_to_type(cn, lookup_m_tp)

                        impl_fn_t = FnType(params=m_params, return_type=m_ret, default_count=default_count, is_ritual=m_is_ritual, type_params=m_tparams)
                        implemented_methods[m_name] = impl_fn_t
                        self.symbols.methods[(target_name, m_name)] = impl_fn_t
                        self.symbols.methods[(base_tname, m_name)] = impl_fn_t
                        if type_params:
                            self.symbols.generic_methods[(base_tname, m_name)] = (type_params, m_decl)

                if concept_obj is not None:
                    for c_mname, c_mfn in concept_obj.methods.items():
                        if c_mname not in implemented_methods:
                            err = self._make_error(
                                UnimplementedConceptMethodError,
                                f"Type '{target_name}' does not implement method '{c_mname}' required by concept '{concept_name}'",
                                stmt,
                                code="E0031",
                                help=f"Add 'weave {c_mname} ...' implementation in the 'bind {target_name} with {concept_name}:' block.",
                                note=f"Concept '{concept_name}' requires method '{c_mname}'."
                            )
                            self._record_error(err)
                        else:
                            impl_mfn = implemented_methods[c_mname]
                            if len(impl_mfn.params) != len(c_mfn.params) or not impl_mfn.return_type.is_compatible(c_mfn.return_type):
                                err = self._make_error(
                                    ConceptMethodMismatchError,
                                    f"Signature of method '{c_mname}' in bind block does not match concept '{concept_name}' declaration (parameter count mismatch: expected {len(c_mfn.params)}, found {len(impl_mfn.params)})",
                                    stmt,
                                    code="E0030",
                                    help=f"Expected signature '{c_mfn}', found '{impl_mfn}'.",
                                    note=f"Method '{c_mname}' signature must match concept definition."
                                )
                                self._record_error(err)
                            else:
                                for (p1_n, p1_t), (p2_n, p2_t) in zip(impl_mfn.params, c_mfn.params):
                                    if not p1_t.is_compatible(p2_t):
                                        err = self._make_error(
                                            ConceptMethodMismatchError,
                                            f"Parameter '{p1_n}' of method '{c_mname}' in bind block has type '{p1_t}', expected '{p2_t}'",
                                            stmt,
                                            code="E0030",
                                            help=f"Change parameter '{p1_n}' type to '{p2_t}'.",
                                            note=f"Concept '{concept_name}' specifies '{p2_n} as {p2_t}'."
                                        )
                                        self._record_error(err)

                self.symbols.concept_bindings[(target_name, concept_name)] = implemented_methods
                self.symbols.concept_bindings[(base_tname, concept_name)] = implemented_methods

            elif rule == "const_decl":
                c_name = str(stmt.children[0])
                c_c_name = f"{current_insignia}{c_name}" if current_insignia else c_name
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
                if c_c_name != c_name:
                    self.symbols.consts[c_c_name] = (c_type, const_val)
                doc = self._extract_preceding_doc(line)
                sym = Symbol(name=c_name, type=c_type or AnyType(), kind="const", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_c_name)
                sym.const_val = const_val
                self.symbols.global_scope.define(sym)

            elif rule == "enchanting_decl":
                if self.filename and self.filename.endswith(".d.pengu"):
                    for m_decl in stmt.children[1:]:
                        if isinstance(m_decl, Tree) and m_decl.data == "weave_decl":
                            err = self._make_error(
                                SemanticError,
                                "Implementation body not allowed in declaration file (.d.pengu)",
                                m_decl,
                                code="E0025",
                                help="Use 'declare' or type declarations instead of 'weave' in declaration files (.d.pengu).",
                                note="Declaration files (.d.pengu) cannot contain function implementation bodies."
                            )
                            self._record_error(err)
                target_type_node = stmt.children[0]
                target_type = ast_to_type(target_type_node, self.symbols.lookup_type)
                target_name = getattr(target_type, "name", str(target_type))
                base_tname = target_name.split("_")[0]
                type_params = []
                if base_tname in self.symbols.generic_runes:
                    type_params = self.symbols.generic_runes[base_tname][0]
                elif isinstance(target_type, RuneType) and target_type.type_args:
                    type_params = [getattr(t, "name", str(t)) for t in target_type.type_args]

                for m_decl in stmt.children[1:]:
                    if isinstance(m_decl, Tree) and m_decl.data == "weave_decl":
                        m_inline, m_ritual, m_idx = _extract_weave_modifiers(m_decl.children)
                        m_name = str(m_decl.children[m_idx])
                        m_rem = [c for c in m_decl.children[m_idx+1:] if c is not None]
                        m_tparams = []
                        if m_rem and isinstance(m_rem[0], Tree) and m_rem[0].data == "shard_params":
                            m_tparams, _ = extract_shard_params(m_rem[0])
                            m_rem = m_rem[1:]

                        def lookup_m_tp(tname: str):
                            if tname in m_tparams:
                                return TypeParam(tname)
                            if tname in type_params:
                                return TypeParam(tname)
                            return self.symbols.lookup_type(tname)

                        m_params: List[Tuple[Optional[str], Type]] = []
                        m_ret: Type = VOID_TYPE
                        default_count = 0
                        for cn in m_rem:
                            if isinstance(cn, Tree) and cn.data == "param_list":
                                for p in cn.children:
                                    if isinstance(p, Tree) and p.data == "param":
                                        pn = str(p.children[0])
                                        pt = ast_to_type(p.children[1], lookup_m_tp) if len(p.children) >= 2 else AnyType()
                                        if len(p.children) >= 3 and p.children[2] is not None:
                                            default_count += 1
                                        m_params.append((pn, pt))
                            elif isinstance(cn, Tree) and cn.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                                m_ret = ast_to_type(cn, lookup_m_tp)
                            elif isinstance(cn, Token) and cn.type == "NAME":
                                m_ret = ast_to_type(cn, lookup_m_tp)

                        impl_fn_t = FnType(params=m_params, return_type=m_ret, default_count=default_count, is_ritual=m_ritual, type_params=m_tparams)
                        self.symbols.methods[(target_name, m_name)] = impl_fn_t
                        self.symbols.methods[(base_tname, m_name)] = impl_fn_t
                        if type_params:
                            self.symbols.generic_methods[(base_tname, m_name)] = (type_params, m_decl)

            elif rule == "declare_stmt":
                is_inline, is_ritual, idx = _extract_weave_modifiers(stmt.children)
                fn_name = str(stmt.children[idx])
                c_fn_name = f"{current_insignia}{fn_name}" if current_insignia else fn_name
                type_params = []
                bounds = {}
                rem_children = [c for c in stmt.children[idx+1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    return self.symbols.lookup_type(tname)

                params: List[Tuple[Optional[str], Type]] = []
                ret_type: Type = VOID_TYPE
                for child_n in rem_children:
                    if isinstance(child_n, Tree) and child_n.data in ("param_list", "declare_params"):
                        for p in child_n.children:
                            if isinstance(p, Tree) and p.data == "param":
                                pn = str(p.children[0])
                                pt = ast_to_type(p.children[1], lookup_tp) if len(p.children) >= 2 else AnyType()
                                params.append((pn, pt))
                            elif (isinstance(p, Token) and (p.type in ("VARARGS", "_VARARGS") or str(p) == "...")) or (isinstance(p, Tree) and p.data in ("varargs", "_varargs")):
                                params.append(("_varargs", CVarArgsType()))
                    elif isinstance(child_n, Tree) and child_n.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                        ret_type = ast_to_type(child_n, lookup_tp)
                    elif isinstance(child_n, Token) and child_n.type == "NAME":
                        ret_type = ast_to_type(child_n, lookup_tp)
                fn_t = FnType(params=params, return_type=ret_type, is_ritual=is_ritual, type_params=type_params)
                self.symbols.functions[fn_name] = fn_t
                if c_fn_name != fn_name:
                    self.symbols.functions[c_fn_name] = fn_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=fn_name, type=fn_t, kind="declare", is_mutable=False, is_ritual=is_ritual, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_fn_name
                ))

            elif rule == "weave_decl":
                if self.filename and self.filename.endswith(".d.pengu"):
                    err = self._make_error(
                        SemanticError,
                        "Implementation body not allowed in declaration file (.d.pengu)",
                        stmt,
                        code="E0025",
                        help="Use 'declare' instead of 'weave' in declaration files (.d.pengu).",
                        note="Declaration files (.d.pengu) cannot contain function implementation bodies."
                    )
                    self._record_error(err)
                is_inline, is_ritual, idx = _extract_weave_modifiers(stmt.children)
                fn_name = str(stmt.children[idx])
                c_fn_name = f"{current_insignia}{fn_name}" if current_insignia else fn_name
                type_params = []
                bounds = {}
                rem_children = [c for c in stmt.children[idx+1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
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
                    if c_fn_name != fn_name:
                        self.symbols.generic_functions[c_fn_name] = (type_params, stmt)
                    fn_t = FnType(params=params, return_type=ret_type, default_count=default_count, is_ritual=is_ritual, type_params=type_params)
                else:
                    fn_t = FnType(params=params, return_type=ret_type, default_count=default_count, is_ritual=is_ritual)

                self.symbols.functions[fn_name] = fn_t
                if c_fn_name != fn_name:
                    self.symbols.functions[c_fn_name] = fn_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=fn_name, type=fn_t, kind="weave", is_mutable=False, is_ritual=is_ritual, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_fn_name
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
                    help="Use 'const' for global constants, or move inside a function body. For stateful modules, use accessor weaves with 'static var' or an explicit context struct.",
                    note="PenguScript forbids mutable global state to guarantee V-safety."
                )
                self._record_error(err)
                return
            if self._decl_uses_with_init(node):
                self._check_with_init_body(node)
            self._check_var_decl(node)
            return

        elif rule == "static_var_decl":
            self._check_static_var_decl(node)
            return

        elif rule == "let_decl":
            if self.symbols.is_top_level():
                err = self._make_error(
                    VarLetTopLevelError,
                    "'let' is not allowed at top-level. Use 'const' or move inside a function.",
                    node,
                    code="E0002",
                    help="Use 'const' for global constants, or move inside a function body. For stateful modules, use accessor weaves with 'static var' or an explicit context struct.",
                    note="PenguScript forbids mutable global state to guarantee V-safety."
                )
                self._record_error(err)
                return
            if self._decl_uses_with_init(node):
                self._check_with_init_body(node)
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

        elif rule == "bind_decl":
            target_type_node = node.children[0]
            concept_name_node = node.children[1]
            rem_children = [c for c in node.children[2:] if c is not None]
            type_params = []
            if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                type_params, _ = extract_shard_params(rem_children[0])
                rem_children = rem_children[1:]

            target_type = ast_to_type(target_type_node, self.symbols.lookup_type)
            span_start, span_end = self._get_node_span(node)
            self.symbols.push_scope(kind="enchanting", enchanting_type=target_type, start_line=span_start, end_line=span_end)
            for tp in type_params:
                self.symbols.define(Symbol(name=tp, type=TypeParam(tp), kind="type"))

            for child in rem_children:
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
        elif rule in ("set_stmt", "compound_set_stmt"):
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
            if isinstance(expr_node, Tree) and expr_node.data == "block":
                for stmt in expr_node.children:
                    self._check_node(stmt)
                return
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
            curr = target_expr
            while isinstance(curr, Tree) and curr.data in ("primary", "expr_stmt") and len(curr.children) == 1:
                curr = curr.children[0]

            if isinstance(curr, Tree) and curr.data in (
                "str_lit", "string_lit", "raw_string_lit", "int_lit", "float_lit",
                "bool_lit", "char_lit", "array_lit", "list_lit", "map_lit"
            ):
                err = self._make_error(
                    InvalidMemoryOpError,
                    "Cannot banish a literal value. 'banish' requires a variable or field lvalue.",
                    target_expr,
                    code="E0008",
                    help="Assign the value to a variable first before banishing it.",
                    note="Literals cannot be banished."
                )
                self._record_error(err)
                return

            if isinstance(curr, Tree) and curr.data in (
                "calling_expr", "calling_stmt", "add", "sub", "mul", "div", "mod",
                "bitwise_or", "bitwise_and", "bitwise_xor", "shl", "shr", "concat",
                "logic_or", "logic_and", "range_expr", "try_expr", "or_else", "or_return"
            ):
                err = self._make_error(
                    InvalidMemoryOpError,
                    "Cannot banish a temporary expression. 'banish' requires a variable or field lvalue.",
                    target_expr,
                    code="E0008",
                    help="Assign the temporary expression to a variable before banishing it.",
                    note="Temporaries cannot be banished directly."
                )
                self._record_error(err)
                return

            is_lvalue = isinstance(curr, Token) or (
                isinstance(curr, Tree) and curr.data in (
                    "var_ref", "normal_target", "field_access", "dot_access",
                    "arrow_access", "at_access"
                )
            )
            if not is_lvalue:
                err = self._make_error(
                    InvalidMemoryOpError,
                    "Cannot banish a non-lvalue expression. 'banish' requires a variable or field.",
                    target_expr,
                    code="E0008",
                    help="Pass a variable name or field access to 'banish'.",
                    note="Only lvalues can be banished."
                )
                self._record_error(err)
                return

            if isinstance(curr, Tree) and curr.data == "var_ref":
                sym_name = str(curr.children[0])
                sym = self.symbols.lookup(sym_name)
                if sym and sym.kind == "const":
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"Cannot banish constant '{sym_name}'",
                        target_expr,
                        code="E0008",
                        help="Only dynamically allocated variables or references can be banished.",
                        note="Constants cannot be banished."
                    )
                    self._record_error(err)
                    return
                if sym and (
                    isinstance(sym.type, FrozenType)
                    or (isinstance(sym.type, RefType) and isinstance(sym.type.target, FrozenType))
                ):
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"Cannot banish frozen (read-only) variable '{sym_name}'",
                        target_expr,
                        code="E0008",
                        help="Remove the 'frozen' qualifier to allow banishing this variable.",
                        note="Frozen variables cannot be deallocated."
                    )
                    self._record_error(err)
                    return

            try:
                t = self.inferrer.infer(target_expr)
                if isinstance(t, FrozenType):
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"Cannot banish frozen (read-only) value of type '{t}'",
                        target_expr,
                        code="E0008",
                        help="Frozen values cannot be modified or deallocated.",
                        note="Only mutable references, strings, lists, or maps can be banished."
                    )
                    self._record_error(err)
                    return

                is_valid_type = (
                    isinstance(t, (RefType, ListType, MapType, AnyType))
                    or (isinstance(t, BaseType) and t.name == "string")
                )
                if not is_valid_type:
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"'banish' requires a reference (ref to T), string, list, or map, got '{t}'",
                        target_expr,
                        code="E0008",
                        help="Pass a reference (ref to T), string, list, or map to 'banish'.",
                        note="'banish' deallocates memory behind references, strings, lists, and maps."
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
            # A bare array/map literal is not a statement. 'x[0]' (C-style
            # indexing, which Pengu spells 'x at 0') parses as the variable
            # followed by a stray '[0]' statement, so this catches the typo
            # instead of emitting a useless '{ 0 };' and an unused value.
            if isinstance(expr_node, Tree) and expr_node.data in ("array_lit", "map_lit"):
                err = self._make_error(
                    SemanticError,
                    f"{'A map' if expr_node.data == 'map_lit' else 'An array'} literal "
                    f"is not a statement",
                    expr_node,
                    code="E0005",
                    help="Did you mean an element access? PenguScript indexes with "
                         "'x at i', not 'x[i]'.",
                    note="Bare literals have no effect; assign them or pass them to a call."
                )
                self._record_error(err)
                return
            self._check_value_exprs(expr_node)
            try:
                self.inferrer.infer(expr_node)
            except SemanticError as e:
                self._record_error(e)
            return

        elif rule == "or_block":
            self._check_or_block(node)
            return

        elif rule == "when_stmt":
            self._check_when_stmt(node)
            return

        elif rule == "test_decl":
            self._check_test_decl(node)
            return

        elif rule == "when_top_decl":
            for item in self._active_when_top_items(node):
                self._check_node(item)
            return

        # Single-line block statements ('if c: return 0'): each aliases the
        # canonical statement rule, and a bare 'simple_stmt' holds one
        # expression. Both are checked exactly like their indented spelling.
        elif rule in SIMPLE_STMT_ALIASES or rule == "simple_stmt":
            self._check_simple_stmt(node)
            return

        # Generic traversal for other nodes
        for child in node.children:
            if isinstance(child, Tree):
                self._check_node(child)

    # -------------------------------------------------------------------------
    # Specific Statement Checkers
    # -------------------------------------------------------------------------
    def _check_simple_stmt(self, node: Tree) -> None:
        """Checks a single-line block statement (``if c: return 0``).

        Those forms parse as aliased nodes (``return_simple`` …) or as a bare
        ``simple_stmt`` holding one expression. Re-dispatch onto the canonical
        statement checker so they are validated exactly like the indented
        spelling (mutability, return type, loop-control placement, …).
        """
        canonical = SIMPLE_STMT_ALIASES.get(node.data)
        if canonical is not None:
            self._check_node(Tree(canonical, node.children, meta=node.meta))
            return
        if node.children and isinstance(node.children[0], Tree):
            try:
                self.inferrer.infer(node.children[0])
            except SemanticError as e:
                self._record_error(e)

    def _check_const_decl(self, node: Tree) -> None:
        """Checks constant declaration for V-safety and compile-time type validity.

        Args:
            node: AST Tree for const declaration.
        """
        line, col = self._get_loc(node)
        c_name = str(node.children[0])
        if c_name == "main":
            self._record_error(self._make_error(
                SemanticError,
                "'main' is a reserved compile-time variable",
                node,
                code="E0040",
                help="Use a different name, or use 'when main:' for conditional execution.",
                note="'main' can only appear as the condition of a compile-time 'when'."
            ))
            return
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
            if c_type is None and isinstance(inferred, NullType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Constant '{c_name}' initialized with 'null' requires an explicit type annotation (e.g. 'as ref to T' or 'as opaque')",
                    node,
                    code="E0014",
                    help=f"Add an explicit type annotation: 'const {c_name} as ref to T is null'",
                    note="'null' requires explicit type context to determine target pointer type."
                )
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
                if c_type is not None and isinstance(c_type, ArrayType) and isinstance(inferred, ArrayType):
                    self._sync_array_sizes(c_type, inferred)
                eff_type = c_type or inferred

                if self._has_unknown_array_dim(eff_type):
                    raise self._make_error(
                        UnknownArrayDimensionError,
                        f"Unknown array dimension in '{eff_type}' for constant '{c_name}'",
                        node,
                        code="E0015",
                        help="Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.",
                        note="C requires fixed array sizes for all dimensions."
                    )

                folded_val = self.const_folder.fold(c_expr)
                doc = self._extract_preceding_doc(line)
                existing_sym = self.symbols.lookup(c_name)
                c_c_name = existing_sym.c_name if existing_sym else None
                sym = Symbol(name=c_name, type=eff_type, kind="const", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_c_name)
                if folded_val is not None:
                    sym.const_val = folded_val
                self.symbols.define(sym)
        except SemanticError as e:
            self._record_error(e)

    # ------------------------------------------------------------------
    # 'with:' block construction expressions
    # ------------------------------------------------------------------

    @staticmethod
    def _decl_type_and_expr(node: Tree):
        """Returns (type_node, expr_node) of a var/let/const declaration."""
        if len(node.children) >= 3 and node.children[1] is not None:
            return node.children[1], node.children[2]
        return None, node.children[-1]

    def _decl_uses_with_init(self, node: Tree) -> bool:
        """True when a declaration initializer needs block-body checking.

        Covers the ``with:`` builder, ``do:`` blocks and an ``if``/``unless`` used
        as a value (``let x is if c: ... else: ...``), which is positional: the
        same statement node is checked in value mode here.
        """
        _, expr = self._decl_type_and_expr(node)
        return isinstance(expr, Tree) and expr.data in (
            "with_init_expr", "do_expr", "if_stmt", "unless_stmt"
        )

    def _check_with_init_body(self, node: Tree) -> None:
        """Validates the body of a block-style expression initializer.

        * ``with:`` (construction) — behaves like a ``with target:`` scope over
          the annotated value under construction; only ``set .field is ...``
          and ``calling .method`` statements are allowed.
        * ``do:`` — general statement block (see :meth:`_check_value_block`).
        * ``if``/``unless`` used as a value (positional value semantics).

        Args:
            node: The enclosing var/let declaration node.
        """
        type_node, expr = self._decl_type_and_expr(node)
        if expr.data in ("if_stmt", "unless_stmt", "do_expr",
                         "while_stmt", "for_range_stmt", "for_in_stmt"):
            # Positional value forms: one walker handles them all (and any block
            # values nested deeper in the initializer). The declared type is the
            # expected type, so a nested 'with:' builder or a loop's element type
            # is known.
            expected = (ast_to_type(type_node, self.symbols.lookup_type)
                        if type_node is not None else None)
            self._check_value_exprs(expr, expected)
            return

        expected = None
        if type_node is not None:
            expected = ast_to_type(type_node, self.symbols.lookup_type)
        if type_node is None:
            err = self._make_error(
                TypeMismatchError,
                "'with:' block construction requires an explicit type annotation "
                "(e.g. 'var x as T with:')",
                node,
                code="E0014",
                help="Add an explicit type to the declaration: 'var x as SomeType with:'.",
                note="A 'with:' construction block cannot infer its target type."
            )
            self._record_error(err)
            return
        self._check_with_builder(expr, expected)

    def _check_with_builder(self, expr: Tree, expected: Optional[Type]) -> Type:
        """Checks a ``with:`` construction block against its target type.

        The block mutates the value under construction through an implicit
        temporary: only ``set .field is ...`` assignments and ``calling .method``
        statements are allowed. Returns the built value's type.
        """
        span_start, span_end = self._get_node_span(expr)
        self.symbols.push_scope(
            kind="with",
            with_type=expected,
            with_is_mutable=True,
            with_target_var_name="_with_builder",
            start_line=span_start,
            end_line=span_end,
        )

        try:
            for ch in expr.children:
                if not isinstance(ch, Tree):
                    continue
                inner = ch
                while inner.data == "stmt" and inner.children:
                    inner = inner.children[0]
                if inner.data not in ("set_stmt", "expr_stmt"):
                    err = self._make_error(
                        InvalidControlFlowError,
                        "'with:' block only allows 'set .field is ...' assignments and "
                        f"'calling .method' statements, not '{inner.data}'",
                        inner,
                        code="E0007",
                        help="Use field assignments and method calls inside the builder block.",
                        note="Construction blocks may not contain control flow or declarations."
                    )
                    self._record_error(err)
                    continue
                self._check_node(ch)
        finally:
            self.symbols.pop_scope(end_line=span_end)
        return expected if expected is not None else AnyType()

    @staticmethod
    def _unwrap_stmt(node: Tree) -> Tree:
        """Unwraps 'stmt' wrappers down to the concrete statement node."""
        inner = node
        while isinstance(inner, Tree) and inner.data == "stmt" and inner.children:
            inner = inner.children[0]
        return inner

    @staticmethod
    def _block_value_expr(inner: Tree):
        """Expression node that supplies a block's value, or None.

        Covers indented blocks (``expr_stmt``) and the single-line block form
        (``":" simple_stmt``), whose statement node wraps the expression.
        """
        if not isinstance(inner, Tree):
            return None
        if inner.data == "expr_stmt" and inner.children:
            return inner.children[0]
        if inner.data == "simple_stmt" and len(inner.children) == 1:
            return inner.children[0]
        return None

    def _check_block_value_stmt(self, stmt: Tree, expected: Optional[Type] = None) -> Type:
        """Checks the last statement of a value block; returns its value type.

        A trailing 'if'/'unless' or loop is checked in value position
        (recursively), so chains, nested blocks and collected loops work.
        """
        inner = self._unwrap_stmt(stmt)
        if isinstance(inner, Tree) and inner.data == "if_stmt":
            return self._check_if_value(inner, expected)
        if isinstance(inner, Tree) and inner.data == "unless_stmt":
            return self._check_unless_value(inner, expected)
        if isinstance(inner, Tree) and inner.data in _LOOP_RULES:
            # Best effort: a loop ending a value block yields its collected list,
            # but a value-less loop body is not an error here (the block is then
            # simply void, and the enclosing value slot reports any mismatch).
            return self._check_loop_value(
                inner, expected_element=expected.element if isinstance(expected, ListType) else None,
                required=False,
            )
        if isinstance(inner, Tree) and inner.data == "do_expr":
            return self._check_value_block(list(inner.children), expected)
        val_node = self._block_value_expr(inner)
        if (isinstance(val_node, Tree) and val_node.data == "with_init_expr"
                and expected is not None):
            # A trailing 'with:' builder is typed by the surrounding value slot
            # (e.g. the element type of a collecting loop).
            return self._check_with_builder(val_node, expected)
        if isinstance(val_node, Tree) and val_node.data == "do_expr":
            # A trailing nested 'do:' is itself a value block.
            return self._check_value_block(list(val_node.children), expected)
        if val_node is not None:
            try:
                return self.inferrer.infer(val_node)
            except SemanticError as e:
                self._record_error(e)
                return VOID_TYPE
        self._check_node(stmt)
        return VOID_TYPE

    def _check_value_block(self, stmts: List[Tree], expected: Optional[Type] = None) -> Type:
        """Validates a value block in a fresh scope and returns its value type.

        Every statement is checked normally; the last one supplies the block's
        value (see :meth:`_check_block_value_stmt`).
        """
        if not stmts:
            return VOID_TYPE
        s_start, _ = self._get_node_span(stmts[0])
        _, e_end = self._get_node_span(stmts[-1])
        val = VOID_TYPE
        try:
            self.symbols.push_scope(kind="do", start_line=s_start, end_line=e_end)
            for ch in stmts[:-1]:
                self._check_node(ch)
            val = self._check_block_value_stmt(stmts[-1], expected)
        finally:
            self.symbols.pop_scope(end_line=e_end)
        return val

    def _check_loop_value(self, node: Tree, expected_element: Optional[Type] = None,
                          required: bool = True) -> Type:
        """Checks a loop in value position: it collects each iteration's value.

        A loop used as a value evaluates to ``list of T``, where ``T`` is the type
        of the body's last statement (every iteration must produce one). With
        ``required`` a value-less body is reported as an error; otherwise the loop
        simply has no value (it behaves as a statement inside a value block).
        """
        if node.data == "while_stmt":
            elem_t = self._check_while_stmt(node, collect=True, expected_element=expected_element)
        elif node.data == "for_range_stmt":
            elem_t = self._check_for_range_stmt(node, collect=True, expected_element=expected_element)
        else:
            elem_t = self._check_for_in_stmt(node, collect=True, expected_element=expected_element)

        if elem_t == VOID_TYPE or isinstance(elem_t, NullType):
            if required:
                err = self._make_error(
                    TypeMismatchError,
                    "loop used as a value must produce a value on every iteration",
                    node,
                    code="E0005",
                    help="End the loop body with an expression (the value collected "
                         "for that iteration), or use the loop as a statement.",
                    note="A loop in a value position builds a list from the body's "
                         "value on each iteration."
                )
                self._record_error(err)
            setattr(node, "_pengu_value_type", VOID_TYPE)
            return VOID_TYPE

        list_t = ListType(element=elem_t)
        setattr(node, "_pengu_value_type", list_t)
        return list_t

    def _check_branch_condition(self, cond_node: Tree, keyword: str = "if") -> None:
        """Validates an 'if'/'unless' condition: bool expression, or (for 'if')
        a binding pattern.

        Binding patterns (``if x as T is expr [is present]:``) define the bound
        name in the current scope, so callers must push the branch scope first.
        """
        line, col = self._get_loc(cond_node)
        if isinstance(cond_node, Tree) and cond_node.data in (
            "if_cond_binding_present", "if_cond_binding"
        ):
            bind_name = str(cond_node.children[0])
            bind_type = ast_to_type(cond_node.children[1], self.symbols.lookup_type)
            init_expr = cond_node.children[2]
            # 'if v as T is opt is present:' parses as a binding whose operand
            # carries the presence test (the grammar's *_binding_present rule is
            # unreachable): the test is inherent to the binding, so unwrap it.
            if isinstance(init_expr, Tree) and init_expr.children:
                if init_expr.data == "is_present":
                    init_expr = init_expr.children[0]
                elif init_expr.data == "is_not_present":
                    self._record_error(self._make_error(
                        TypeMismatchError,
                        f"'is not present' cannot be combined with a binding "
                        f"('{bind_name}')",
                        cond_node,
                        code="E0005",
                        help=f"Write 'if {bind_name} as T is <maybe>:' — the branch "
                             f"already runs only when the value is present.",
                        note="Test absence on its own: 'if opt is not present:'.",
                    ))
                    return
            try:
                init_t = self.inferrer.infer(init_expr)
                if isinstance(init_t, MaybeType):
                    elem_t = init_t.element
                    if not (isinstance(elem_t, (AnyType, TypeParam))
                            or elem_t.is_compatible(bind_type)
                            or bind_type.is_compatible(elem_t)):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Binding '{bind_name}' as '{bind_type}' from '{init_t}'",
                            cond_node,
                            code="E0005",
                            help=f"Bind the present value with its own type: "
                                 f"'{bind_name} as {elem_t} is ...'.",
                            note="The bound name receives the value held by the maybe.",
                        )
                    # Codegen unwraps the maybe and declares the bound name
                    # inside the branch: remember both types on the node.
                    setattr(cond_node, "_pengu_bind_maybe_type", init_t)
                    setattr(cond_node, "_pengu_bind_elem_type", elem_t)
                    setattr(cond_node, "_pengu_bind_source", init_expr)
                elif not isinstance(init_t, (AnyType, TypeParam)):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Binding '{bind_name}' requires a maybe value, got '{init_t}'",
                        cond_node,
                        code="E0005",
                        help="Bind only over a 'maybe T' operand; the branch runs when "
                             "the value is present.",
                        note="For other optionals, test with 'is present' and read '.value'.",
                    )
                self.symbols.define(Symbol(name=bind_name, type=bind_type, kind="let",
                                           is_mutable=False, line=line, column=col))
            except SemanticError as e:
                self._record_error(e)
            return

        try:
            c_type = self.inferrer.infer(cond_node)
            if not c_type.is_compatible(BOOL_TYPE) and not isinstance(c_type, AnyType):
                err = self._make_error(
                    TypeMismatchError,
                    f"'{keyword}' condition must be bool, got '{c_type}'",
                    cond_node,
                    code="E0005",
                    help=f"Ensure '{keyword}' condition evaluates to a boolean (bool).",
                    note="Branch conditions must be boolean expressions."
                )
                self._record_error(err)
        except SemanticError as e:
            self._record_error(e)

    def _merge_branch_value_types(self, node: Tree, then_t: Type, else_t: Type,
                                  keyword: str = "if") -> Type:
        """Common value type of the branches of a value-position 'if'/'unless'.

        Records the result on the node (``_pengu_value_type``) so the inferrer and
        codegen treat the very same node as a value, and reports ``E0005`` when the
        branches disagree or when a value branch meets a value-less one.
        """
        if isinstance(then_t, AnyType) and isinstance(else_t, AnyType):
            common: Type = AnyType()
        elif then_t == VOID_TYPE and else_t == VOID_TYPE:
            common = VOID_TYPE
        elif then_t != VOID_TYPE and else_t != VOID_TYPE:
            common = then_t
            if not then_t.is_compatible(else_t) and not else_t.is_compatible(then_t):
                err = self._make_error(
                    TypeMismatchError,
                    f"'{keyword}' block branches have incompatible value types: "
                    f"'{then_t}' vs '{else_t}'",
                    node,
                    code="E0005",
                    help="Make every branch end with an expression of the same type.",
                    note=f"An {keyword} used as a value needs one common branch type."
                )
                self._record_error(err)
        else:
            val_t = then_t if then_t != VOID_TYPE else else_t
            err = self._make_error(
                TypeMismatchError,
                f"'{keyword}' block expression mixes a value branch ('{val_t}') with a "
                "branch that has no final expression",
                node,
                code="E0005",
                help=f"Every branch of an {keyword} used as a value must end with an "
                     "expression of the same type.",
                note="A block used as a value must produce a value on every branch."
            )
            self._record_error(err)
            common = val_t
        setattr(node, "_pengu_value_type", common)
        return common

    def _check_value_exprs(self, node: Any, expected: Optional[Type] = None) -> None:
        """Value-checks block constructs nested inside an expression.

        'if'/'unless'/'while'/'for' have a single grammar rule each, so anywhere
        inside an *expression* they are values: validate each in value mode (which
        records its type on the node) before the expression is inferred.
        ``expected`` is the type the enclosing slot requires; it is used to type
        the elements of a loop and a ``with:`` builder that is the slot's direct
        value. Block bodies are not walked into — a handled construct already
        checked its own statements.
        """
        if not isinstance(node, Tree):
            return
        rule = node.data
        if rule == "if_stmt":
            if getattr(node, "_pengu_value_type", None) is None:
                self._check_if_value(node, expected)
            return
        if rule == "unless_stmt":
            if getattr(node, "_pengu_value_type", None) is None:
                self._check_unless_value(node, expected)
            return
        if rule in _LOOP_RULES:
            if getattr(node, "_pengu_value_type", None) is None:
                self._check_loop_value(
                    node,
                    expected_element=expected.element if isinstance(expected, ListType) else None,
                )
            return
        if rule == "do_expr":
            if getattr(node, "_pengu_value_type", None) is None:
                setattr(node, "_pengu_value_type",
                        self._check_value_block(list(node.children), expected))
            return
        if rule == "with_init_expr":
            # A nested builder needs its target type from the surrounding slot;
            # without one the inferrer reports the usual "explicit type" error.
            if getattr(node, "_pengu_value_type", None) is None and expected is not None:
                setattr(node, "_pengu_value_type", self._check_with_builder(node, expected))
            return
        for child in node.children:
            self._check_value_exprs(child)

    def _check_if_value(self, node: Tree, expected: Optional[Type] = None) -> Type:
        """Checks an ``if`` used in value position and returns its value type.

        ``if`` has a single grammar rule (``if_stmt``), so statement-ness and
        value-ness are decided by *position*: in a value slot every branch must
        end with an expression and all branches must share one common type.
        """
        cond_node = node.children[0]
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None

        span_start, span_end = self._get_node_span(block_node)
        self.symbols.push_scope(kind="if", start_line=span_start, end_line=span_end)
        try:
            self._check_branch_condition(cond_node, "if")
            then_t = self._check_value_block(list(block_node.children), expected)
        finally:
            self.symbols.pop_scope(end_line=span_end)

        else_t = self._check_else_value(else_node, expected) if else_node is not None else VOID_TYPE
        return self._merge_branch_value_types(node, then_t, else_t, "if")

    def _check_unless_value(self, node: Tree, expected: Optional[Type] = None) -> Type:
        """Checks an ``unless`` used in value position; mirrors ``_check_if_value``.

        Semantics are the mirror image: the then-branch runs when the condition is
        false, so equal branch types are still required and the recorded type is
        the common branch type.
        """
        cond_node = node.children[0]
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None

        span_start, span_end = self._get_node_span(block_node)
        self.symbols.push_scope(kind="if", start_line=span_start, end_line=span_end)
        try:
            self._check_branch_condition(cond_node, "unless")
            then_t = self._check_value_block(list(block_node.children), expected)
        finally:
            self.symbols.pop_scope(end_line=span_end)

        else_t = self._check_else_value(else_node, expected) if else_node is not None else VOID_TYPE
        return self._merge_branch_value_types(node, then_t, else_t, "unless")

    def _check_else_value(self, else_node: Tree, expected: Optional[Type] = None) -> Type:
        """Value type of the ``else`` branch of a value-position 'if'/'unless'.

        Handles both spellings: ``else:`` with an indented block (a trailing
        nested 'if'/'unless'/loop is itself a value) and ``else if <cond>:``.
        """
        children = [c for c in else_node.children if isinstance(c, Tree)]
        if not children:
            return VOID_TYPE
        if len(children) == 1 and children[0].data == "if_stmt":
            # 'else if <cond>:' — the nested if supplies the value directly.
            return self._check_if_value(children[0], expected)
        if len(children) == 1 and children[0].data == "unless_stmt":
            return self._check_unless_value(children[0], expected)
        e_start, e_end = self._get_node_span(else_node)
        self.symbols.push_scope(kind="if", start_line=e_start, end_line=e_end)
        try:
            return self._check_value_block(children, expected)
        finally:
            self.symbols.pop_scope(end_line=e_end)

    @staticmethod
    def _sync_array_sizes(target_t: Any, source_t: Any) -> None:
        """Recursively propagates inferred array dimensions to declared array types."""
        if isinstance(target_t, ArrayType) and isinstance(source_t, ArrayType):
            if target_t.size is None and source_t.size is not None:
                target_t.size = source_t.size
            PenguChecker._sync_array_sizes(target_t.element, source_t.element)

    @staticmethod
    def _has_unknown_array_dim(t: Any) -> bool:
        """Returns True if an ArrayType has any dimension with size None."""
        curr = t
        while isinstance(curr, ArrayType):
            if curr.size is None:
                return True
            curr = curr.element
        return False

    def _check_var_decl(self, node: Tree) -> None:
        """Checks local mutable variable declaration for type validity and folds constants.

        Args:
            node: AST Tree for var declaration.
        """
        line, col = self._get_loc(node)
        v_name = str(node.children[0])
        if v_name == "main":
            self._record_error(self._make_error(
                SemanticError,
                "'main' is a reserved compile-time variable",
                node,
                code="E0040",
                help="Use a different name, or use 'when main:' for conditional execution.",
                note="'main' can only appear as the condition of a compile-time 'when'."
            ))
            return
        v_type = None
        v_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                self._validate_type_node(node.children[1])
                v_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            v_expr = node.children[2]
        else:
            v_expr = node.children[1]

        # Block values nested in the initializer (call arguments, struct-literal
        # fields, …) are value-checked before inference.
        self._check_value_exprs(v_expr, v_type)

        try:
            inferred = self.inferrer.infer(v_expr, expected_type=v_type)
            if v_type is None and (inferred is None or isinstance(inferred, NullType) or getattr(inferred, "name", "") == "unknown"):
                raise self._make_error(
                    TypeMismatchError,
                    f"Variable '{v_name}' initialized with 'null' or uninferable value requires an explicit type annotation (e.g. 'as ref to T' or 'as opaque')",
                    node,
                    code="E0014",
                    help=f"Add an explicit type annotation: 'var {v_name} as T is ...'",
                    note="Type inference requires sufficient context to determine concrete type."
                )

            if v_type is not None and isinstance(v_type, ArrayType) and isinstance(inferred, ArrayType):
                self._sync_array_sizes(v_type, inferred)
            eff_type = v_type or inferred

            if self._has_unknown_array_dim(eff_type):
                raise self._make_error(
                    UnknownArrayDimensionError,
                    f"Unknown array dimension in '{eff_type}' for variable '{v_name}'",
                    node,
                    code="E0015",
                    help="Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.",
                    note="C requires fixed array sizes for all dimensions."
                )

            if isinstance(eff_type, ArrayType) and isinstance(v_expr, Tree) and v_expr.data == "indent_literal":
                child = v_expr.children[0]
                if child.data == "indent_array":
                    rows = child.children
                    if isinstance(eff_type.element, ArrayType):
                        outer_sz = eff_type.size
                        inner_sz = eff_type.element.size
                        if outer_sz is not None and len(rows) != outer_sz:
                            raise self._make_error(
                                ArraySizeMismatchError,
                                f"Array has {len(rows)} rows but the declared size is {outer_sz}",
                                child,
                                code="E0041"
                            )
                        for r_idx, r in enumerate(rows):
                            r_elems = r.children
                            if inner_sz is not None and len(r_elems) != inner_sz:
                                raise self._make_error(
                                    ArraySizeMismatchError,
                                    f"Row {r_idx + 1} has {len(r_elems)} elements but the declared width is {inner_sz}",
                                    r,
                                    code="E0041"
                                )
                    else:
                        sz = eff_type.size
                        all_elems = [e for r in rows for e in r.children]
                        if sz is not None and len(all_elems) != sz:
                            raise self._make_error(
                                ArraySizeMismatchError,
                                f"Array has {len(all_elems)} elements but the declared size is {sz}",
                                child,
                                code="E0041"
                            )

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
                type=eff_type,
                kind="var",
                is_mutable=True,
                is_stack_alloc=isinstance(eff_type, RuneType),
                const_val=folded_val,
                line=line,
                column=col,
                doc=doc,
                file_path=self.filename
            )
            self.symbols.define(sym)
        except SemanticError as e:
            self._record_error(e)

    def _check_static_var_decl(self, node: Tree) -> None:
        """Checks 'static var' declarations that persist across function calls.

        Rules:
        - Only allowed directly inside a function body ('weave' scope), not at top-level
          and not nested in control-flow blocks.
        - The variable is a mutable local ('var' semantics) but is flagged is_static so
          codegen emits a C 'static' storage-class variable initialized once.
        - Array-typed static variables are rejected (C arrays are not assignable).
        """
        line, col = self._get_loc(node)
        if self.symbols.is_top_level():
            err = self._make_error(
                VarLetTopLevelError,
                "'static var' is not allowed at top-level. Use 'const' or move inside a function.",
                node,
                code="E0002",
                help="Use 'const' for global constants, or move 'static var' inside a function body.",
                note="PenguScript forbids mutable global state to guarantee V-safety."
            )
            self._record_error(err)
            return

        if self.symbols.current_scope.kind not in ("weave",):
            err = self._make_error(
                SemanticError,
                "'static var' is only allowed directly inside a function body (weave).",
                node,
                code="E0035",
                help="Move the 'static var' declaration to the top level of the function body.",
                note="Function-static variables must be direct children of the function body."
            )
            self._record_error(err)
            return

        v_name = str(node.children[0])
        if v_name == "main":
            self._record_error(self._make_error(
                SemanticError,
                "'main' is a reserved compile-time variable",
                node,
                code="E0040",
                help="Use a different name, or use 'when main:' for conditional execution.",
                note="'main' can only appear as the condition of a compile-time 'when'."
            ))
            return
        v_type = None
        v_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                self._validate_type_node(node.children[1])
                v_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            v_expr = node.children[2]
        else:
            v_expr = node.children[1]

        # 'static var x is if/unless/for ...:' or block values nested in the
        # initializer (e.g. inside a struct literal) — positional value check.
        self._check_value_exprs(v_expr, v_type)

        try:
            inferred = self.inferrer.infer(v_expr, expected_type=v_type)
            if v_type is None and isinstance(inferred, NullType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Static variable '{v_name}' initialized with 'null' requires an explicit type annotation (e.g. 'as ref to T' or 'as opaque')",
                    node,
                    code="E0014",
                    help=f"Add an explicit type annotation: 'static var {v_name} as ref to T is null'",
                    note="'null' requires explicit type context to determine target pointer type."
                )
            eff_type = v_type or inferred
            if isinstance(eff_type, ArrayType):
                raise self._make_error(
                    SemanticError,
                    f"Static variable '{v_name}' cannot have an array type ('{eff_type}')",
                    node,
                    code="E0035",
                    help="Use a pointer, rune, list, or map type for function-static variables.",
                    note="C arrays cannot be assigned at runtime, so array statics are not supported."
                )
            if v_type is not None and not inferred.is_compatible(v_type):
                err = self._make_type_mismatch_error(
                    expected_type=v_type,
                    found_type=inferred,
                    node=v_expr,
                    custom_message=f"Static variable '{v_name}' declared as '{v_type}', but initialized with '{inferred}'",
                    note="Variables must match their declared type."
                )
                self._record_error(err)

            folded_val = self.const_folder.fold(v_expr)
            doc = self._extract_preceding_doc(line)
            sym = Symbol(
                name=v_name,
                type=eff_type,
                kind="var",
                is_mutable=True,
                is_static=True,
                is_stack_alloc=False,
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
        for nm in names:
            if nm == "main":
                self._record_error(self._make_error(
                    SemanticError,
                    "'main' is a reserved compile-time variable",
                    node,
                    code="E0040",
                    help="Use a different name, or use 'when main:' for conditional execution.",
                    note="'main' can only appear as the condition of a compile-time 'when'."
                ))
                return
        l_type = None
        l_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                self._validate_type_node(node.children[1])
                l_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            l_expr = node.children[2]
        else:
            l_expr = node.children[1]

        self._check_value_exprs(l_expr, l_type)
        try:
            inferred = self.inferrer.infer(l_expr, expected_type=l_type)
            folded_val = self.const_folder.fold(l_expr)
            doc = self._extract_preceding_doc(line)

            if len(names) == 1:
                v_name = names[0]
                if l_type is None and (inferred is None or isinstance(inferred, NullType) or getattr(inferred, "name", "") == "unknown"):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Binding '{v_name}' initialized with 'null' or uninferable value requires an explicit type annotation (e.g. 'as ref to T' or 'as opaque')",
                        node,
                        code="E0014",
                        help=f"Add an explicit type annotation: 'let {v_name} as T is ...'",
                        note="Type inference requires sufficient context to determine concrete type."
                    )

                if l_type is not None and isinstance(l_type, ArrayType) and isinstance(inferred, ArrayType):
                    self._sync_array_sizes(l_type, inferred)
                eff_type = l_type or inferred

                if self._has_unknown_array_dim(eff_type):
                    raise self._make_error(
                        UnknownArrayDimensionError,
                        f"Unknown array dimension in '{eff_type}' for binding '{v_name}'",
                        node,
                        code="E0015",
                        help="Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.",
                        note="C requires fixed array sizes for all dimensions."
                    )

                if isinstance(eff_type, ArrayType) and isinstance(l_expr, Tree) and l_expr.data == "indent_literal":
                    child = l_expr.children[0]
                    if child.data == "indent_array":
                        rows = child.children
                        if isinstance(eff_type.element, ArrayType):
                            outer_sz = eff_type.size
                            inner_sz = eff_type.element.size
                            if outer_sz is not None and len(rows) != outer_sz:
                                raise self._make_error(
                                    ArraySizeMismatchError,
                                    f"Array has {len(rows)} rows but the declared size is {outer_sz}",
                                    child,
                                    code="E0041"
                                )
                            for r_idx, r in enumerate(rows):
                                r_elems = r.children
                                if inner_sz is not None and len(r_elems) != inner_sz:
                                    raise self._make_error(
                                        ArraySizeMismatchError,
                                        f"Row {r_idx + 1} has {len(r_elems)} elements but the declared width is {inner_sz}",
                                        r,
                                        code="E0041"
                                    )
                        else:
                            sz = eff_type.size
                            all_elems = [e for r in rows for e in r.children]
                            if sz is not None and len(all_elems) != sz:
                                raise self._make_error(
                                    ArraySizeMismatchError,
                                    f"Array has {len(all_elems)} elements but the declared size is {sz}",
                                    child,
                                    code="E0041"
                                )

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
                    type=eff_type,
                    kind="let",
                    is_mutable=False,
                    is_stack_alloc=isinstance(eff_type, RuneType),
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

    def _frozen_write_block(self, target_node: Any, target_type: Type) -> Optional[str]:
        """Describes why a `set` target is read-only, or None when it is writable.

        Two shapes are rejected, mirroring C's ``const``:

        * the target *is* a frozen value (`var y as frozen int` → `const int y`);
        * the target is reached **through** a frozen pointee
          (`p as ref to frozen T` → `const T* p`), i.e. `set p->field is …` or
          `set p at i is …`. Rebinding the pointer itself is still allowed,
          because `frozen` qualifies the pointee, not the pointer.

        Args:
            target_node: The resolved `set` target node.
            target_type: The type the assignment would write to.

        Returns:
            A short description of the frozen view, or None.
        """
        if isinstance(target_type, FrozenType):
            return f"value of type '{target_type}'"

        node = target_node
        if isinstance(node, Tree) and node.data == "set_target":
            node = node.children[0]
        if not isinstance(node, Tree):
            return None
        through = len(node.children) > 1
        if not through:
            return None

        base_t: Optional[Type] = None
        if node.data == "with_target":
            base_t = self.symbols.current_with_type()
        elif node.data == "normal_target" and node.children:
            first = node.children[0]
            if isinstance(first, (Token, str)):
                sym = self.symbols.lookup(str(first))
                if sym is not None:
                    base_t = sym.type
        elif node.data == "essence_target":
            base_t = self.inferrer.infer(node.children[0])

        if isinstance(base_t, RefType) and isinstance(base_t.target, FrozenType):
            return f"'{base_t}'"
        if isinstance(base_t, FrozenType):
            return f"'{base_t}'"
        return None

    def _check_set_stmt(self, node: Tree) -> None:
        """Checks reassignment statement for mutability and type soundness.

        Args:
            node: AST Tree for set assignment statement.
        """
        line, col = self._get_loc(node)
        target_node = node.children[0]
        if isinstance(target_node, Tree) and target_node.data == "set_target":
            target_node = target_node.children[0]
        # Compound assignment ('set x += 1'): children are [target, OP, value],
        # while a plain 'set x is v' has [target, value]. The target validation
        # below is identical (mutability, with_target, essence_target, private
        # fields, self->); only the operator's type rules differ.
        is_compound = node.data == "compound_set_stmt"
        compound_op = str(node.children[1]) if is_compound else None
        val_expr = node.children[2] if is_compound else node.children[1]

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
                    if self.symbols.is_in_ritual_context():
                        raise self._make_error(
                            InvalidRitualSelfAccessError,
                            "'self' cannot be used inside a 'ritual' method",
                            target_node,
                            code="E0033",
                            help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                            note="'ritual' methods are static functions and do not have a 'self' reference."
                        )
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

            # Writing through a read-only qualification is an error, exactly like
            # C's 'const': the target itself may be 'frozen T', or it may be
            # reached through a pointer whose pointee is frozen ('ref to frozen T').
            frozen_desc = self._frozen_write_block(target_node, target_type)
            if frozen_desc is not None:
                raise self._make_error(
                    MutabilityError,
                    f"Cannot assign through read-only 'frozen' {frozen_desc}",
                    target_node,
                    code="E0006",
                    help="Drop 'frozen' from the declaration, or copy the value into "
                         "a mutable local first.",
                    note="'frozen T' is C's 'const T': it cannot be written through."
                )

            # 'set x is if/unless/for ...:' and any block value nested in the
            # expression (e.g. inside a struct literal). The target type is the
            # expected type, so a nested 'with:' builder is typed from it.
            self._check_value_exprs(val_expr, target_type)

            val_type = self.inferrer.infer(val_expr, expected_type=target_type)

            if is_compound:
                # Operator-specific type rules for 'set TARGET OP VALUE'.
                if compound_op == "+=" and getattr(target_type, "name", "") == "string":
                    if not val_type.is_compatible(STRING_TYPE) and not isinstance(val_type, AnyType):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Compound '+=' on a string requires a string value, got '{val_type}'",
                            node,
                            code="E0005",
                            help="Concatenate only strings: 'set s += \"more\"'. "
                                 "Convert numbers with 'to string' first.",
                            note="String '+=' concatenates, so both sides must be strings."
                        )
                elif compound_op in ("+=", "-=", "*=", "/=", "%="):
                    if not target_type.is_numeric() and not isinstance(target_type, AnyType):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Compound '{compound_op}' requires a numeric target, "
                            f"got '{target_type}'",
                            node,
                            code="E0005",
                            help="Use '+=' on numbers (or on strings for concatenation); "
                                 "use '&='/'|='/'^=' for integers.",
                            note="Arithmetic compound assignment needs numeric operands."
                        )
                    if not val_type.is_numeric() and not isinstance(val_type, AnyType):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Compound '{compound_op}' requires a numeric value, "
                            f"got '{val_type}'",
                            node,
                            code="E0005",
                            help=f"The right-hand side of '{compound_op}' must be a number.",
                            note="Arithmetic compound assignment needs numeric operands."
                        )
                elif compound_op in ("&=", "|=", "^=", "<<=", ">>="):
                    for t, side in ((target_type, "target"), (val_type, "value")):
                        if not t.is_int() and not isinstance(t, AnyType):
                            raise self._make_error(
                                TypeMismatchError,
                                f"Compound '{compound_op}' requires integers, "
                                f"got '{t}' for the {side}",
                                node,
                                code="E0005",
                                help="Bitwise/shift compound assignment only accepts "
                                     "integer operands (int, i32, i64, ...).",
                                note="Use 'and'/'or' for booleans instead of '&='/'|='."
                            )
                return

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
        if self.filename and self.filename.endswith(".d.pengu"):
            err = self._make_error(
                SemanticError,
                "Implementation body not allowed in declaration file (.d.pengu)",
                node,
                code="E0025",
                help="Use 'declare' instead of 'weave' in declaration files (.d.pengu).",
                note="Declaration files (.d.pengu) cannot contain function implementation bodies."
            )
            self._record_error(err)
            return

        line, col = self._get_loc(node)
        is_inline, is_ritual, idx = _extract_weave_modifiers(node.children)
        fn_name = str(node.children[idx])

        type_params = []
        bounds = {}
        rem_children = [c for c in node.children[idx+1:] if c is not None]
        if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
            type_params, bounds = extract_shard_params(rem_children[0])
            rem_children = rem_children[1:]

        def lookup_tp(tname: str):
            if tname in type_params:
                return TypeParam(tname, bounds=bounds.get(tname, []))
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
                                    if isinstance(t, FrozenType):
                                        return type_depends_on_tp(t.target)
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
        self.symbols.push_scope(kind="weave", return_type=ret_type, is_ritual=is_ritual, start_line=span_start, end_line=span_end)
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
            has_static = any(True for _ in node.iter_subtrees() if isinstance(_, Tree) and _.data == "static_var_decl")
            node_count = sum(1 for _ in node.iter_subtrees())
            if (len(stmt_children) <= 3 or node_count <= 25) and not has_loop and not has_static:
                fn_sym.is_inline = True

        # Escape Analysis for local variables
        for s_name, sym in list(self.symbols.current_scope.symbols.items()):
            if sym.kind in ("var", "let") and not getattr(sym, "is_static", False):
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
        is_inline, is_ritual, idx = _extract_weave_modifiers(node.children)
        fn_name = str(node.children[idx])
        rem_children = [c for c in node.children[idx+1:] if c is not None]

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

        for child in rem_children:
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

        method_fn_type = FnType(params=params, return_type=ret_type, default_count=default_count, is_ritual=is_ritual, type_params=tp_list)
        self_t_name = getattr(self_type, "name", str(self_type))
        self.symbols.methods[(self_t_name, fn_name)] = method_fn_type
        if isinstance(self_type, RuneType):
            self_type.methods[fn_name] = method_fn_type

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="weave", return_type=ret_type, enchanting_type=self_type, is_ritual=is_ritual, start_line=span_start, end_line=span_end)
        if not is_ritual:
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

        self._check_branch_condition(cond_node, "if")

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

    def _check_while_stmt(self, node: Tree, collect: bool = False,
                          expected_element: Optional[Type] = None) -> Type:
        """Checks while-loop condition and body statements.

        With ``collect`` the body is checked as a *value block* and the type of
        the value produced on each iteration is returned (the loop is used as an
        expression, see :meth:`_check_loop_value`).

        Args:
            node: AST Tree for while statement.
            collect: True when the loop is used as a value.
            expected_element: Element type required by the enclosing value slot.
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
        elem_t: Type = VOID_TYPE
        if collect:
            elem_t = self._check_value_block(list(block_node.children), expected_element)
        else:
            self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)
        return elem_t

    def _check_for_range_stmt(self, node: Tree, collect: bool = False,
                              expected_element: Optional[Type] = None) -> Type:
        """Checks numeric range for-loop bounds and step expressions.

        With ``collect`` the body is checked as a value block and the per-iteration
        value type is returned (loop used as an expression).

        Args:
            node: AST Tree for for-range statement.
            collect: True when the loop is used as a value.
            expected_element: Element type required by the enclosing value slot.
        """
        line, col = self._get_loc(node)
        var_name = str(node.children[0])
        start_node = node.children[1]
        end_node = node.children[2]
        step_node = node.children[3] if len(node.children) == 5 else None
        block_node = node.children[-1]

        start_val = self.const_folder.fold(start_node)
        end_val = self.const_folder.fold(end_node)
        if isinstance(start_val, int) and isinstance(end_val, int) and start_val > end_val:
            err = self._make_error(
                InvalidRangeError,
                "Invalid range: start must be less than or equal to end when both bounds are known at compile time",
                node,
                code="E0042",
                help=f"Range start ({start_val}) must be <= end ({end_val}).",
                note="Descending ranges are not supported."
            )
            self._record_error(err)


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
        elem_t: Type = VOID_TYPE
        if collect:
            elem_t = self._check_value_block(list(block_node.children), expected_element)
        else:
            self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)
        return elem_t

    def _check_for_in_stmt(self, node: Tree, collect: bool = False,
                           expected_element: Optional[Type] = None) -> Type:
        """Checks collection iterator for-loop and element binding.

        Supports both the classic single-binding form ('for v in col') and the
        indexed form ('for i, v in col', 'for i, _ in col', 'for _, v in col').
        A '_' binding is a discard and never creates a scope symbol.

        With ``collect`` the body is checked as a value block and the
        per-iteration value type is returned (loop used as an expression).

        Args:
            node: AST Tree for for-in statement.
            collect: True when the loop is used as a value.
            expected_element: Element type required by the enclosing value slot.
        """
        line, col = self._get_loc(node)
        if len(node.children) == 4:
            index_name = str(node.children[0])
            elem_name = str(node.children[1])
            iter_node = node.children[2]
            block_node = node.children[3]
        else:
            index_name = None
            elem_name = str(node.children[0])
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
            if it == STRING_TYPE:
                elem_type = STRING_TYPE  # iterating a string yields characters
            else:
                elem_type = it.element_type() or AnyType()
        except SemanticError as e:
            self._record_error(e)

        if index_name is not None and index_name != "_" and elem_name != "_" and index_name == elem_name:
            err = self._make_error(
                SemanticError,
                f"Loop index and element bindings cannot both be named '{index_name}'",
                node,
                code="E0037",
                help="Rename one of the two loop bindings in 'for i, v in collection'.",
                note="The index and element bindings must use distinct identifiers."
            )
            self._record_error(err)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="for", in_loop=True, start_line=span_start, end_line=span_end)
        if index_name is not None and index_name != "_":
            self.symbols.define(Symbol(name=index_name, type=INT_TYPE, kind="var", is_mutable=False, line=line, column=col))
        if elem_name != "_":
            self.symbols.define(Symbol(name=elem_name, type=elem_type, kind="var", is_mutable=False, line=line, column=col))
        body_t: Type = VOID_TYPE
        if collect:
            body_t = self._check_value_block(list(block_node.children), expected_element)
        else:
            self._check_node(block_node)
        self.symbols.pop_scope(end_line=span_end)
        return body_t

    def _check_test_decl(self, node: Tree) -> None:
        """Type-checks an integrated unit test body as a void function.

        Test bodies are semantically validated in every compilation mode so
        errors surface early; code generation only emits them in --test mode.
        """
        if self.filename and self.filename.endswith(".d.pengu"):
            err = self._make_error(
                SemanticError,
                "'test' blocks are not allowed in declaration files (.d.pengu)",
                node,
                code="E0025",
                help="Remove the test block from the declaration file.",
                note="Declaration files (.d.pengu) cannot contain implementation code."
            )
            self._record_error(err)
            return

        name_tok = node.children[0]
        if isinstance(name_tok, Tree):
            test_name = _node_to_name(name_tok)
        else:
            raw = str(name_tok)
            test_name = raw[1:-1] if (raw.startswith('"') and raw.endswith('"')) else raw

        body_stmts: List[Tree] = []
        for c in node.children[1:]:
            if isinstance(c, Tree):
                body_stmts.append(c)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="weave", return_type=VOID_TYPE, start_line=span_start, end_line=span_end)
        for stmt in body_stmts:
            self._check_node(stmt)
        self.symbols.pop_scope(end_line=span_end)

        if not test_name or test_name == "_":
            err = self._make_error(
                SemanticError,
                "Test name must be a non-empty string or identifier",
                node,
                code="E0035",
                help="Give the test a descriptive name: 'test \"does something\"' or 'test does_something'.",
                note="Unit tests need a name for reporting."
            )
            self._record_error(err)

    def _check_when_stmt(self, node: Tree) -> None:
        """Checks a compile-time 'when' statement by validating only its active branch.

        'when' behaves like a textual preprocessor substitution: the active
        branch is checked directly in the enclosing scope (variables declared in
        the active branch remain visible afterwards, exactly as if the code had
        been written inline). The discarded branch is not semantically checked.
        """
        then_block, else_node = self._active_when_stmt_items(node)
        if then_block is None and else_node is None:
            return  # invalid / non-constant condition already reported
        if then_block is not None:
            self._check_node(then_block)
        elif else_node is not None:
            if else_node.data == "when_else_plain":
                for c in else_node.children:
                    if isinstance(c, Tree):
                        self._check_node(c)
            elif else_node.data == "when_else_when":
                for c in else_node.children:
                    if isinstance(c, Tree):
                        self._check_node(c)

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
        self._check_value_exprs(expr_node, curr_ret)
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

    def _check_omen_variant_collisions(self) -> None:
        """Reports collisions between omen variant names and global symbols.

        Every non-generic omen variant is registered in the global scope under
        both its full name (``Omen_variant``) and, when free, its simple name
        (``variant``) so Pengu code can refer to it ergonomically.  Both names
        must stay unique: a weave, constant, alias or second omen reusing a
        variant name would silently shadow one of the two registrations (the
        symbol table overwrites without complaining), producing confusing
        resolution.  This pass raises E0046 for such collisions.
        """
        omens_seen: Dict[str, OmenType] = {}
        for o_name, omen_t in self.symbols.omens.items():
            if not isinstance(omen_t, OmenType):
                continue
            # insignia-registered duplicates map the same object twice.
            if omen_t.name not in omens_seen and omen_t.name in self.symbols.omens:
                omens_seen[omen_t.name] = omen_t
            elif omen_t.name not in omens_seen:
                omens_seen[omen_t.name] = omen_t

        simple_owner: Dict[str, str] = {}
        full_names: Dict[str, str] = {}
        for o_logical, omen_t in omens_seen.items():
            for v_name in (omen_t.variants or {}):
                full = f"{o_logical}_{v_name}"
                full_names[full] = o_logical
                if v_name in simple_owner and simple_owner[v_name] != o_logical:
                    err = self._make_error(
                        SemanticError,
                        f"Omen variant name '{v_name}' is used by both omen "
                        f"'{simple_owner[v_name]}' and omen '{o_logical}'",
                        code="E0046",
                        help="Use distinct variant names, or refer to one of them by "
                             "its full 'Omen_variant' name.",
                        note="Simple variant names must be unique across all omens in the module."
                    )
                    self._record_error(err)
                else:
                    simple_owner[v_name] = o_logical

        for name, sym in list(self.symbols.global_scope.symbols.items()):
            if sym.kind in ("omen", "omen_variant"):
                continue
            if name in simple_owner:
                if self._const_matches_variant(sym, simple_owner[name], name):
                    # Same name and same value denote the same number, so the
                    # variant's simple name is merely shadowed by an equal
                    # constant. Generated bindings are self-contained per
                    # header, so a '#define' transcribed as a const legitimately
                    # repeats a variant of the header it includes (raygui.h
                    # includes raylib.h, hence its KEY_* consts).
                    continue
                if getattr(sym, "kind", "") == "const":
                    clash_desc = f"top-level constant '{name}'"
                    note = ("Omen variants occupy both their simple and full names in the "
                            "global scope.")
                elif isinstance(sym.type, BaseType):
                    clash_desc = f"built-in type '{name}'"
                    note = ("Built-in type names are reserved, so the variant cannot be "
                            "reached by its simple name.")
                else:
                    clash_desc = f"top-level symbol '{name}'"
                    note = ("Omen variants occupy both their simple and full names in the "
                            "global scope.")
                err = self._make_error(
                    SemanticError,
                    f"Omen variant name '{name}' of omen '{simple_owner[name]}' collides "
                    f"with the {clash_desc}",
                    code="E0046",
                    help=f"Refer to the variant by its full "
                         f"'{simple_owner[name]}_{name}' name, or rename the conflicting "
                         "symbol.",
                    note=note,
                )
                self._record_error(err)
                continue
            if name in full_names:
                o_logical = full_names[name]
                variant = name[len(o_logical) + 1:]
                if self._const_matches_variant(sym, o_logical, variant):
                    continue
                err = self._make_error(
                    SemanticError,
                    f"Top-level symbol '{name}' collides with the full name of the "
                    f"'{full_names[name]}' omen variant",
                    code="E0046",
                    help="Rename the top-level symbol so it does not shadow the "
                         "full omen variant name.",
                    note="Omen variants occupy both their simple and full names in the global scope."
                )
                self._record_error(err)

    def _const_matches_variant(self, sym: Symbol, omen_name: str, variant: str) -> bool:
        """True when ``sym`` is a constant holding the variant's exact value.

        Cross-module bindings may declare the same C symbol twice (a ``#define``
        as a ``const``, an ``enum`` member as an omen variant). When both agree
        on the value there is nothing ambiguous to report; when they differ the
        collision is a real one and stays an :class:`E0046`.
        """
        if getattr(sym, "kind", "") != "const":
            return False
        const_val = getattr(sym, "const_val", None)
        if const_val is None:
            return False
        omen_t = self.symbols.omens.get(omen_name)
        if not isinstance(omen_t, OmenType):
            return False
        value = (omen_t.variant_values or {}).get(variant)
        if value is None:
            return False
        if isinstance(value, (bool, int)) and isinstance(const_val, (bool, int)):
            return int(value) == int(const_val)
        if isinstance(value, str) and isinstance(const_val, str):
            return value == const_val
        return False

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
