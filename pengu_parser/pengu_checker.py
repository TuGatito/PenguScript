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
    implements_concept, check_generic_bounds,
    typeparam_accepts_value, resolve_concept_method, ast_to_type,
    get_type_base_name, extract_type_params_from_type, receiver_deep_copies_on_store,
    type_has_derived_nexus, type_owns_heap,
)
from .pengu_symbols import SymbolTable, Symbol, Scope, resolve_imports, find_module_path, decl_layout
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
    UnknownArrayDimensionError, AutoOwnedBanishError, BorrowedBanishError, InvalidBuilderStatementError,
    DuplicateConceptBindingError, InfiniteTypeSizeError, UnknownAttributeError,
    suggest_similar_identifier
)


def _has_borrowed_modifier(node: Tree) -> Tuple[bool, int]:
    """Return (is_borrowed, name_index).

    When optional modifiers are parsed, Lark may emit None as a placeholder
    for [BORROWED] at index 0, shifting the variable name to index 1.
    If children[0] is Token(BORROWED), is_borrowed is True and name is at index 1.
    If children[0] is None, is_borrowed is False and name is at index 1.
    Otherwise (e.g. compacted tree), children[0] is the variable name itself.
    """
    if not node.children:
        return False, 0
    first = node.children[0]
    if first is not None and getattr(first, "type", None) == "BORROWED":
        return True, 1
    if first is None:
        return False, 1
    return False, 0


# Public layout extractor is defined in pengu_symbols; keep local alias for internal checker use.
_decl_layout = decl_layout


C_RESERVED_WORDS = {
    "default", "case", "switch", "register", "goto", "volatile", "union", "enum", "struct", "auto",
    "long", "short", "int", "char", "float", "double", "signed", "unsigned", "void", "const",
    "static", "extern", "inline", "restrict", "return", "sizeof", "typedef",
    "if", "else", "while", "for", "do", "break", "continue", "asm",
    "NULL", "bool", "true", "false", "_Bool", "wchar_t", "FILE",
    "_Alignas", "_Alignof", "_Atomic", "_Generic", "_Noreturn", "_Static_assert", "_Thread_local",
    "printf", "fprintf", "sprintf", "snprintf", "malloc", "free", "realloc", "calloc", "exit", "abort",
}

C_RESERVED_TYPE_NAMES = {
    # C keywords
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while",
    "_Alignas", "_Alignof", "_Atomic", "_Bool", "_Complex", "_Generic",
    "_Imaginary", "_Noreturn", "_Static_assert", "_Thread_local", "asm",
    # Common standard library macros and typedefs
    "NULL", "bool", "true", "false", "wchar_t", "FILE", "size_t", "ptrdiff_t",
    "int8_t", "int16_t", "int32_t", "int64_t",
    "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "intptr_t", "uintptr_t", "stdin", "stdout", "stderr",
    # Pengu runtime typedefs
    "PenguString", "PenguList", "PenguMap", "PenguSlice",
    "PenguMaybe", "PenguResult", "PenguRange", "PenguFrame",
}

C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while",
    "_Alignas", "_Alignof", "_Atomic", "_Bool", "_Complex", "_Generic",
    "_Imaginary", "_Noreturn", "_Static_assert", "_Thread_local", "asm",
}

C_RESERVED_FN_NAMES = {
    "printf", "fprintf", "sprintf", "snprintf", "malloc", "free", "realloc", "calloc", "exit", "abort",
    "puts", "gets", "putchar", "getchar", "system", "FILE",
}


def _c_ident(name: str) -> str:
    if name in C_RESERVED_WORDS:
        return f"_{name}"
    return name


def _is_ref_char_type(t: Optional[Type]) -> bool:
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


def _is_statically_initializable_type(t: Type, seen: Optional[Set[str]] = None) -> bool:
    if seen is None:
        seen = set()
    curr = t
    while isinstance(curr, (AliasType, FrozenType)) and getattr(curr, "target", None):
        curr = curr.target
    if curr.is_numeric() or curr.is_bool():
        return True
    if isinstance(curr, BaseType) and curr.name in ("char", "byte", "void", "opaque"):
        return True
    if _is_ref_char_type(curr):
        return True
    if isinstance(curr, RefType):
        return True
    if isinstance(curr, ArrayType):
        return _is_statically_initializable_type(curr.element, seen)
    if isinstance(curr, OmenType):
        if not curr.is_algebraic:
            return True
        if curr.name in seen:
            return True
        seen.add(curr.name)
        if hasattr(curr, "variants") and curr.variants:
            for v_name, v_fields in curr.variants.items():
                if isinstance(v_fields, dict):
                    for f_name, f_type in v_fields.items():
                        if not _is_statically_initializable_type(f_type, seen):
                            return False
        return True
    if isinstance(curr, RuneType):
        if curr.name in seen:
            return True
        seen.add(curr.name)
        if hasattr(curr, "fields") and curr.fields:
            for f_name, f_type in curr.fields.items():
                if not _is_statically_initializable_type(f_type, seen):
                    return False
        return True
    if isinstance(curr, EchoType):
        if curr.name in seen:
            return True
        seen.add(curr.name)
        if hasattr(curr, "fields") and curr.fields:
            for f_name, f_type in curr.fields.items():
                if not _is_statically_initializable_type(f_type, seen):
                    return False
        return True
    return False



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


def _extract_attributes(children: List[Any], start_idx: int = 0) -> Tuple[Dict[str, List[Any]], int]:
    """Extracts attribute mappings from an attributes AST node.
    Returns (attrs_dict, next_idx).
    """
    attrs: Dict[str, List[Any]] = {}
    idx = start_idx
    if idx < len(children) and isinstance(children[idx], Tree) and children[idx].data == "attributes":
        for attr_tree in children[idx].children:
            if isinstance(attr_tree, Tree) and attr_tree.data == "attribute":
                attr_name = str(attr_tree.children[0])
                args: List[Any] = []
                for sub in attr_tree.children[1:]:
                    if isinstance(sub, Tree) and sub.data == "attribute_args":
                        for a in sub.children:
                            if isinstance(a, Token):
                                if a.type == "INT":
                                    args.append(int(str(a)))
                                elif a.type in ("STRING", "TRIPLE_STRING", "RAW_STRING", "RAW_TRIPLE_STRING"):
                                    s = str(a)
                                    args.append(s[1:-1] if s.startswith(('"', "'")) else s)
                                else:
                                    s = str(a)
                                    args.append(int(s) if s.isdigit() else s)
                            elif isinstance(a, Tree):
                                s = str(a.children[0]) if a.children else ""
                                args.append(s[1:-1] if s.startswith(('"', "'")) else s)
                attrs[attr_name] = args
        idx += 1
    return attrs, idx


def _extract_weave_modifiers(children: List[Any], start_idx: int = 0) -> Tuple[bool, bool, int]:
    """Extracts is_inline, is_ritual and returns (is_inline, is_ritual, next_idx)."""
    is_inline = False
    is_ritual = False
    idx = start_idx
    while idx < len(children) and isinstance(children[idx], Tree) and children[idx].data == "attributes":
        idx += 1
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


def extract_where_clause(where_node: Tree) -> Dict[str, List[str]]:
    """Extracts concept bounds dictionary from a where_clause AST node."""
    bounds: Dict[str, List[str]] = {}
    if not isinstance(where_node, Tree):
        return bounds
    for wb in where_node.children:
        if isinstance(wb, Tree) and wb.data == "where_bound":
            t_param_name = _node_to_name(wb.children[0])
            concept_name = _node_to_name(wb.children[1])
            bounds.setdefault(t_param_name, []).append(concept_name)
    return bounds


def extract_derive_clause(derive_node: Tree) -> List[str]:
    """Extracts list of derived concept names from a derive_clause AST node."""
    concepts: List[str] = []
    if not isinstance(derive_node, Tree):
        return concepts
    for ch in derive_node.children:
        c_name = _node_to_name(ch)
        if c_name:
            concepts.append(c_name)
    return concepts


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
            bounds.update(extract_where_clause(ch))
    return type_params, bounds


def check_infinite_size(t: Type, target_base_name: str, seen: Optional[Set[str]] = None) -> bool:
    """Checks whether type t contains target_base_name directly by value without indirection."""
    if t is None:
        return False
    if seen is None:
        seen = set()
    if isinstance(t, RefType):
        return False
    if isinstance(t, (ListType, MapType, SliceType, ManyType)):
        return False
    if isinstance(t, FrozenType):
        return check_infinite_size(t.target, target_base_name, seen)
    if isinstance(t, MaybeType):
        return check_infinite_size(t.element, target_base_name, seen)
    if isinstance(t, ResultType):
        return check_infinite_size(t.ok_type, target_base_name, seen) or check_infinite_size(t.err_type, target_base_name, seen)
    if isinstance(t, ArrayType):
        return check_infinite_size(t.element, target_base_name, seen)
    if isinstance(t, (RuneType, EchoType)):
        b_name = get_type_base_name(t)
        if b_name == target_base_name:
            return True
        if b_name in seen:
            return False
        seen.add(b_name)
        for ft in t.fields.values():
            if check_infinite_size(ft, target_base_name, seen):
                return True
    return False



# Loop rules that can also be used as values (collecting their body's value).
_LOOP_RULES = ("while_stmt", "for_range_stmt", "for_in_stmt")

# AST node types for compound data structures and container literals in escape analysis
_ESCAPE_COMPOUND_RULES = (
    "struct_init", "field_init", "struct_init_expr", "with_init_expr",
    "array_init_expr", "array_lit", "list_lit", "map_lit", "tuple_lit",
    "some_expr", "ok_expr", "err_expr",
    "indent_literal", "indent_entries", "indent_array",
    "indent_row", "field_entry", "map_entry",
)


# Imported modules are re-parsed every time a module imports them (the
# sub-checker below needs their top-level symbols).  Caching the parsed tree by
# (path, mtime, size) removes ~200 redundant parses per build for a program that
# pulls in several std modules.  Trees are read-only during collection, so
# sharing them is safe; the cache is bounded and self-invalidating.
_MODULE_TREE_CACHE: Dict[Any, Any] = {}
_MODULE_TREE_CACHE_MAX = 512


def _cached_module_tree(path: str, code: str, parser: Any) -> Any:
    """Parses a module once per (path, mtime, size) within the process."""
    try:
        st = os.stat(path)
        key = (os.path.abspath(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return parser.parse(code)
    hit = _MODULE_TREE_CACHE.get(key)
    if hit is not None:
        return hit
    tree = parser.parse(code)
    if len(_MODULE_TREE_CACHE) >= _MODULE_TREE_CACHE_MAX:
        _MODULE_TREE_CACHE.clear()
    _MODULE_TREE_CACHE[key] = tree
    return tree


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
        compile_env: Optional[CompileTimeEnv] = None,
        lib_dir: str = "lib"
    ):
        """Initializes semantic checker instance with source code and directory context.

        Args:
            source: Source code text.
            filename: Source file path.
            source_code: Optional explicit source code text override.
            base_dir: Base directory for module import resolution.
            compile_env: Optional compile-time environment for 'when' clauses.
            lib_dir: External bindings directory name (pengu.yaml 'lib_dir').
        """
        self.source_code = source_code if source_code is not None else source
        self.filename = filename
        self.lib_dir = lib_dir or "lib"
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
        self.block_stmts_stack: List[List[Tree]] = []
        self.const_definitions: Dict[str, List[Tuple[Any, Optional[str]]]] = {}
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
            self.source_code = source.replace("\r\n", "\n")

        self.errors = []
        self.warnings = []
        self.block_stmts_stack = []
        self.const_definitions = {}
        self._seen_main_file = None
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
        # Pass 1b: every top-level type is registered now, so declared type
        # nodes (params, returns, fields) can be validated.
        self._validate_declared_types(tree)

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

    def _validate_attributes(self, attrs: Dict[str, List[Any]], target: str, node: Any) -> None:
        """Validates attributes against target declaration kind ('weave', 'declare', 'rune', 'field')."""
        valid_attrs = {
            "weave": {"inline", "cold", "deprecated"},
            "declare": {"inline", "cold", "deprecated"},
            "rune": {"packed", "align", "deprecated"},
            "field": {"align", "deprecated"},
        }
        allowed = valid_attrs.get(target, set())
        for name, args in attrs.items():
            if name not in ("inline", "cold", "deprecated", "packed", "align"):
                err = self._make_error(
                    UnknownAttributeError,
                    f"Unknown attribute '@{name}'",
                    node,
                    code="E0056",
                    help="Supported attributes are @inline, @cold, @deprecated, @packed, and @align(N)."
                )
                self._record_error(err)
                continue
            if name not in allowed:
                err = self._make_error(
                    UnknownAttributeError,
                    f"Attribute '@{name}' is not supported on {target} declarations",
                    node,
                    code="E0056",
                    help=f"Allowed attributes on {target} are: {', '.join('@' + a for a in sorted(allowed))}."
                )
                self._record_error(err)
                continue
            if name in ("inline", "cold", "packed"):
                if len(args) != 0:
                    err = self._make_error(
                        UnknownAttributeError,
                        f"Attribute '@{name}' takes 0 arguments, got {len(args)}",
                        node,
                        code="E0056"
                    )
                    self._record_error(err)
            elif name == "align":
                if len(args) != 1 or not isinstance(args[0], int):
                    err = self._make_error(
                        UnknownAttributeError,
                        f"Attribute '@align' requires 1 integer argument, got {args}",
                        node,
                        code="E0056"
                    )
                    self._record_error(err)
            elif name == "deprecated":
                if len(args) > 1 or (len(args) == 1 and not isinstance(args[0], str)):
                    err = self._make_error(
                        UnknownAttributeError,
                        f"Attribute '@deprecated' takes at most 1 string argument, got {args}",
                        node,
                        code="E0056"
                    )
                    self._record_error(err)

    def _check_deprecated_symbol(self, sym: Any, name: Optional[str] = None) -> None:
        if sym is None:
            return
        attrs = getattr(sym, "attributes", None)
        if not attrs or "deprecated" not in attrs:
            return
        s_name = name or getattr(sym, "name", str(sym))
        reason = attrs["deprecated"][0] if attrs["deprecated"] else None
        if reason:
            msg = f"[W0006] Symbol '{s_name}' is deprecated: {reason}"
        else:
            msg = f"[W0006] Symbol '{s_name}' is deprecated"
        if msg not in self.warnings:
            self.warnings.append(msg)

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
            if stripped.startswith("#"):
                content = stripped
                while content.startswith("#") or content.endswith("#"):
                    content = content.strip("#").strip()
                if content and set(content) <= {"-", "=", "*", "_"}:
                    idx -= 1
                    continue
                if content:
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
    def _collect_top_level(self, tree: Tree, import_order: Optional[List[str]] = None, current_insignia: Optional[str] = None, file_imports: Optional[Set[str]] = None) -> Optional[str]:
        """Discovers and registers all module definitions, imports, and declarations.

        Args:
            tree: AST Tree root.
            import_order: Optional precomputed topological import order.
            current_insignia: Optional inherited insignia prefix.
        """
        if not hasattr(self, "_collected_files") or self._collected_files is None:
            self._collected_files = set()
        has_imports = False
        is_d_pengu = bool(self.filename and self.filename.endswith(".d.pengu"))
        is_std = bool(self.filename and ("std" in self.filename.replace("/", "\\").split("\\") or "std" in self.filename.replace("\\", "/").split("/")))

        if file_imports is None:
            file_imports = set()
        for child in tree.children:
            if not isinstance(child, Tree):
                continue
            if child.data == "file":
                current_insignia = self._collect_top_level(child, import_order=import_order,
                                                           current_insignia=current_insignia,
                                                           file_imports=file_imports)
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
                # 'file_imports' is per file, but 'symbols.imports' drives the
                # module scheduler: never append the same module twice (a module
                # legitimately imported by several files must be processed once).
                if dot_path not in self.symbols.imported_modules:
                    self.symbols.imports.append(dot_path)
                self.symbols.imported_modules.add(dot_path)
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
                        sub_tree = _cached_module_tree(mod_file, mod_code, sub_parser)
                        sub_checker = PenguChecker(base_dir=self.base_dir)
                        sub_checker.source_code = mod_code
                        sub_checker.filename = mod_file
                        sub_checker._collect_top_level(sub_tree, import_order=[])
                        mod_abs_file = os.path.abspath(mod_file)
                        for sname, sym in sub_checker.symbols.global_scope.symbols.items():
                            if sym.kind != "import":
                                sym_fp = getattr(sym, "file_path", None)
                                if sym_fp and os.path.abspath(sym_fp) != mod_abs_file:
                                    continue
                                mod_scope.define(sym)
                                eff_c_name = sym.get_c_name()
                                if sym.kind in ("weave", "function", "declare") and isinstance(sym.type, FnType):
                                    self.symbols.functions[f"{bind_name}_{sname}"] = sym.type
                                    self.symbols.functions[eff_c_name] = sym.type
                                if sym.kind == "rune" and isinstance(sym.type, RuneType):
                                    self.symbols.runes[f"{bind_name}_{sname}"] = sym.type
                                    self.symbols.runes[eff_c_name] = sym.type
                                if sym.kind == "const":
                                    cval = getattr(sym, "const_val", None)
                                    src_path = getattr(sym, "file_path", None) or mod_file
                                    self.symbols.consts[f"{bind_name}_{sname}"] = (sym.type, cval)
                                    self.symbols.consts[eff_c_name] = (sym.type, cval)
                                    self.const_definitions.setdefault(sname, []).append((cval, src_path))
                                if sym.kind == "alias" and isinstance(sym.type, AliasType):
                                    self.symbols.aliases[f"{bind_name}_{sname}"] = sym.type.target
                                    self.symbols.aliases[eff_c_name] = sym.type.target
                                    self.symbols.aliases[sname] = sym.type.target
                                    self.symbols.global_scope.define(sym)
                        for gname, ginfo in sub_checker.symbols.generic_functions.items():
                            self.symbols.generic_functions[gname] = ginfo
                            self.symbols.generic_functions[f"{bind_name}_{gname}"] = ginfo
                except PenguError as mod_err:
                    # Surface the imported module's own diagnostic instead of
                    # swallowing it and reporting a confusing 'undefined
                    # identifier' in the importing file.  Deduplicated because
                    # the builder also checks each module on its own.
                    mod_key = (getattr(mod_err, "code", None), getattr(mod_err, "line", None),
                               getattr(mod_err, "file", None) or getattr(mod_err, "filename", None))
                    known = {(getattr(e, "code", None), getattr(e, "line", None),
                              getattr(e, "file", None) or getattr(e, "filename", None))
                             for e in self.errors}
                    if mod_key not in known:
                        self._record_error(mod_err)
                except Exception:
                    pass

                mod_doc = self._extract_preceding_doc(line) or f"Module `{dot_path}`"
                self.symbols.global_scope.define(Symbol(
                    name=bind_name,
                    c_name=last_name,
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
                    saved_insignia = current_insignia
                    # Keep the precomputed import order: without it the recursive
                    # pass re-resolves and re-parses the whole import graph for
                    # every 'when' block (a large, repeated cost).
                    self._collect_top_level(Tree("file", chosen), import_order=import_order,
                                            current_insignia=current_insignia,
                                            file_imports=file_imports)
                    current_insignia = saved_insignia
                    self.symbols.insignia = saved_insignia

            elif rule == "rune_decl":
                r_attrs, r_idx = _extract_attributes(stmt.children)
                self._validate_attributes(r_attrs, "rune", stmt)
                r_name = str(stmt.children[r_idx])
                if not is_d_pengu and r_name in C_RESERVED_TYPE_NAMES:
                    err = self._make_error(
                        SemanticError,
                        f"Type name '{r_name}' is a reserved C keyword or standard identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this rune (e.g. 'My{r_name}' or '{r_name}Type').",
                        note="User type names cannot shadow C keywords or standard library identifiers to avoid emitting invalid C."
                    )
                    self._record_error(err)
                    continue
                c_r_name = f"{current_insignia}{r_name}" if current_insignia else r_name
                is_cyclus = False
                type_params = []
                bounds = {}
                derived_concepts: List[str] = []
                rem_children = [c for c in stmt.children[r_idx+1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "cyclus_kw":
                    is_cyclus = True
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "derive_clause":
                    derived_concepts = extract_derive_clause(rem_children[0])
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

                fields: Dict[str, Type] = {}
                field_attrs: Dict[str, Dict[str, List[Any]]] = {}
                rune_t = RuneType(name=r_name, fields=fields, type_params=type_params, base_name=r_name, c_name=c_r_name, derived_concepts=list(derived_concepts), bounds=bounds, attributes=r_attrs, field_attributes=field_attrs)
                if type_params:
                    self.symbols.generic_runes[r_name] = (type_params, stmt)
                self.symbols.runes[r_name] = rune_t
                if c_r_name != r_name:
                    self.symbols.runes[c_r_name] = rune_t

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    if tname == r_name:
                        return rune_t
                    return self.symbols.lookup_type(tname)

                seen_c_fields: Dict[str, str] = {}
                for f_decl in rem_children:
                    if isinstance(f_decl, Tree) and f_decl.data == "field_decl":
                        f_at, f_idx = _extract_attributes(f_decl.children)
                        self._validate_attributes(f_at, "field", f_decl)
                        f_name = str(f_decl.children[f_idx])
                        c_fid = _c_ident(f_name)
                        if c_fid in seen_c_fields:
                            err = self._make_error(
                                SemanticError,
                                f"Field '{f_name}' collides with field '{seen_c_fields[c_fid]}' in C code emission ('{c_fid}')",
                                f_decl,
                                code="E0035",
                                help=f"Rename '{f_name}' to avoid collision with C identifier '{c_fid}'.",
                                note="PenguScript escapes C keywords by prefixing an underscore, which may clash with existing identifiers."
                            )
                            self._record_error(err)
                        seen_c_fields[c_fid] = f_name
                        f_type = ast_to_type(f_decl.children[f_idx+1], lookup_tp)
                        fields[f_name] = f_type
                        field_attrs[f_name] = f_at

                        # Bug 9: Detect infinite type size (recursive value struct)
                        if check_infinite_size(f_type, r_name):
                            err = self._make_error(
                                InfiniteTypeSizeError,
                                f"Recursive type '{r_name}' has infinite size because field '{f_name}' contains '{r_name}' directly by value",
                                f_decl,
                                code="E0050",
                                help=f"Use 'ref to {r_name}' or 'maybe ref to {r_name}' to break the cycle with pointer indirection.",
                                note="A type cannot contain itself directly by value."
                            )
                            self._record_error(err)

                # Validate derive clause
                # Deep copy (Imago) and deep free (Nexus) always come as a pair:
                # a container that clones its elements must also be able to
                # release them, so deriving one implicitly derives the other.
                if "Imago" in derived_concepts and "Nexus" not in derived_concepts:
                    derived_concepts.append("Nexus")
                if "Nexus" in derived_concepts and "Imago" not in derived_concepts:
                    derived_concepts.append("Imago")
                for d_concept in derived_concepts:
                    if d_concept not in ("Par", "Ordo", "Vinculum", "Imago", "Nexus"):
                        err = self._make_error(
                            SemanticError,
                            f"Concept '{d_concept}' cannot be automatically derived for rune '{r_name}'",
                            stmt,
                            code="E0005",
                            help="Only 'Par', 'Ordo', 'Vinculum', 'Imago' and 'Nexus' can be derived.",
                            note="Built-in derivable concepts are Par, Ordo, Vinculum, Imago, Nexus."
                        )
                        self._record_error(err)
                        continue

                    for fn_k, ft_v in fields.items():
                        if isinstance(ft_v, TypeParam):
                            if d_concept not in ft_v.bounds:
                                ft_v.bounds.append(d_concept)
                            if ft_v.name in bounds and d_concept not in bounds[ft_v.name]:
                                bounds[ft_v.name].append(d_concept)
                        elif not implements_concept(ft_v, d_concept, self.symbols):
                            err = self._make_error(
                                SemanticError,
                                f"Cannot derive '{d_concept}' for rune '{r_name}' because field '{fn_k}' of type '{ft_v}' does not implement '{d_concept}'",
                                stmt,
                                code="E0032",
                                help=f"Ensure type '{ft_v}' implements '{d_concept}'.",
                                note=f"Deriving '{d_concept}' requires all fields to implement '{d_concept}'."
                            )
                            self._record_error(err)

                    self.symbols.concept_bindings[(r_name, d_concept)] = {}
                    if c_r_name != r_name:
                        self.symbols.concept_bindings[(c_r_name, d_concept)] = {}
                # 'rune_t' was built before validation appended the implied
                # Imago/Nexus pair, so refresh the record the checker and the
                # code generator read derived concepts from.
                rune_t.derived_concepts = list(derived_concepts)
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=r_name, type=rune_t, kind="rune", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_r_name
                ))

            elif rule == "echo_decl":
                e_attrs, e_idx = _extract_attributes(stmt.children)
                self._validate_attributes(e_attrs, "rune", stmt)
                e_name = str(stmt.children[e_idx])
                if not is_d_pengu and e_name in C_RESERVED_TYPE_NAMES:
                    err = self._make_error(
                        SemanticError,
                        f"Type name '{e_name}' is a reserved C keyword or standard identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this echo (e.g. 'My{e_name}' or '{e_name}Type').",
                        note="User type names cannot shadow C keywords or standard library identifiers to avoid emitting invalid C."
                    )
                    self._record_error(err)
                    continue
                c_e_name = f"{current_insignia}{e_name}" if current_insignia else e_name
                is_cyclus = False
                type_params = []
                bounds = {}
                derived_concepts: List[str] = []
                rem_children = [c for c in stmt.children[e_idx+1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "cyclus_kw":
                    is_cyclus = True
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "derive_clause":
                    derived_concepts = extract_derive_clause(rem_children[0])
                    rem_children = rem_children[1:]

                def lookup_tp(tname: str):
                    if tname in type_params:
                        return TypeParam(tname, bounds=bounds.get(tname, []))
                    return self.symbols.lookup_type(tname)

                seen_c_fields: Dict[str, str] = {}
                fields: Dict[str, Type] = {}
                for f_decl in rem_children:
                    if isinstance(f_decl, Tree) and f_decl.data == "field_decl":
                        f_at, f_idx = _extract_attributes(f_decl.children)
                        self._validate_attributes(f_at, "field", f_decl)
                        f_name = str(f_decl.children[f_idx])
                        c_fid = _c_ident(f_name)
                        if c_fid in seen_c_fields:
                            err = self._make_error(
                                SemanticError,
                                f"Field '{f_name}' collides with field '{seen_c_fields[c_fid]}' in C code emission ('{c_fid}')",
                                f_decl,
                                code="E0035",
                                help=f"Rename '{f_name}' to avoid collision with C identifier '{c_fid}'.",
                                note="PenguScript escapes C keywords by prefixing an underscore, which may clash with existing identifiers."
                            )
                            self._record_error(err)
                        seen_c_fields[c_fid] = f_name
                        f_type = ast_to_type(f_decl.children[f_idx+1], lookup_tp)
                        fields[f_name] = f_type

                # An 'echo' is an *untagged* C union: there is no discriminant,
                # so equality/ordering/hashing would read whichever member the
                # last write left behind. Deriving a concept on it is unsound.
                for d_concept in derived_concepts:
                    err = self._make_error(
                        SemanticError,
                        f"Concept '{d_concept}' cannot be derived for echo '{e_name}'",
                        stmt,
                        code="E0005",
                        help="Echos compile to untagged C unions, so the active member is "
                             "unknown at runtime; use an algebraic 'omen' (tagged) or "
                             "implement the concept explicitly with 'bind'.",
                        note="'derive' is supported for runes and algebraic omens only."
                    )
                    self._record_error(err)
                derived_concepts = []

                if type_params:
                    self.symbols.generic_echos[e_name] = (type_params, stmt)
                    echo_t = EchoType(name=e_name, fields=fields, type_params=type_params, c_name=c_e_name, derived_concepts=list(derived_concepts), bounds=bounds)
                else:
                    echo_t = EchoType(name=e_name, fields=fields, c_name=c_e_name, derived_concepts=list(derived_concepts))

                for d_concept in derived_concepts:
                    self.symbols.concept_bindings[(e_name, d_concept)] = {}
                    if c_e_name != e_name:
                        self.symbols.concept_bindings[(c_e_name, d_concept)] = {}

                self.symbols.echos[e_name] = echo_t
                if c_e_name != e_name:
                    self.symbols.echos[c_e_name] = echo_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=e_name, type=echo_t, kind="echo", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_e_name
                ))

            elif rule == "omen_decl":
                o_name = str(stmt.children[0])
                if not is_d_pengu and o_name in C_RESERVED_TYPE_NAMES:
                    err = self._make_error(
                        SemanticError,
                        f"Type name '{o_name}' is a reserved C keyword or standard identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this omen (e.g. 'My{o_name}' or '{o_name}Kind').",
                        note="User type names cannot shadow C keywords or standard library identifiers to avoid emitting invalid C."
                    )
                    self._record_error(err)
                    continue
                c_o_name = f"{current_insignia}{o_name}" if current_insignia else o_name
                is_cyclus = False
                type_params = []
                bounds = {}
                derived_concepts: List[str] = []
                rem_children = [c for c in stmt.children[1:] if c is not None]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "cyclus_kw":
                    is_cyclus = True
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                    type_params, bounds = extract_shard_params(rem_children[0])
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "omen_string_kind":
                    rem_children = rem_children[1:]
                if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "derive_clause":
                    derived_concepts = extract_derive_clause(rem_children[0])
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

                # Validate 'derive' for omens.  A simple (non-algebraic) omen is
                # a plain C enum, so equality/ordering/hash come for free; an
                # algebraic omen is a tagged struct and only the active variant's
                # payload may be inspected, which the generated code does.
                if is_string_mode and derived_concepts:
                    err = self._make_error(
                        SemanticError,
                        f"Concept(s) {', '.join(derived_concepts)} cannot be derived for string-valued omen '{o_name}'",
                        stmt,
                        code="E0005",
                        help="String-valued omens are constant macros, not a C type; "
                             "derive concepts only on numeric/algebraic omens.",
                        note="Remove the 'derive' clause or use an algebraic omen."
                    )
                    self._record_error(err)
                    derived_concepts = []
                # Imago/Nexus pairing (see the rune derive validation above).
                if "Imago" in derived_concepts and "Nexus" not in derived_concepts:
                    derived_concepts.append("Nexus")
                if "Nexus" in derived_concepts and "Imago" not in derived_concepts:
                    derived_concepts.append("Imago")
                for d_concept in derived_concepts:
                    if d_concept not in ("Par", "Ordo", "Vinculum", "Imago", "Nexus"):
                        err = self._make_error(
                            SemanticError,
                            f"Concept '{d_concept}' cannot be automatically derived for omen '{o_name}'",
                            stmt,
                            code="E0005",
                            help="Only 'Par', 'Ordo', 'Vinculum', 'Imago' and 'Nexus' can be derived.",
                            note="Built-in derivable concepts are Par, Ordo, Vinculum, Imago, Nexus."
                        )
                        self._record_error(err)
                        continue
                    if not is_string_mode and not has_any_payload:
                        # Simple enum: only the tag exists, nothing to validate.
                        self.symbols.concept_bindings[(o_name, d_concept)] = {}
                        if c_o_name != o_name:
                            self.symbols.concept_bindings[(c_o_name, d_concept)] = {}
                        continue
                    for v_name, v_fields in variants.items():
                        for fn_k, ft_v in v_fields.items():
                            if isinstance(ft_v, TypeParam):
                                if d_concept not in ft_v.bounds:
                                    ft_v.bounds.append(d_concept)
                                if ft_v.name in bounds and d_concept not in bounds[ft_v.name]:
                                    bounds[ft_v.name].append(d_concept)
                            elif not implements_concept(ft_v, d_concept, self.symbols):
                                err = self._make_error(
                                    SemanticError,
                                    f"Cannot derive '{d_concept}' for omen '{o_name}' because variant '{v_name}' field '{fn_k}' of type '{ft_v}' does not implement '{d_concept}'",
                                    stmt,
                                    code="E0032",
                                    help=f"Ensure type '{ft_v}' implements '{d_concept}'.",
                                    note=f"Deriving '{d_concept}' requires all payload fields to implement it."
                                )
                                self._record_error(err)
                    self.symbols.concept_bindings[(o_name, d_concept)] = {}
                    if c_o_name != o_name:
                        self.symbols.concept_bindings[(c_o_name, d_concept)] = {}

                if type_params:
                    self.symbols.generic_omens[o_name] = (type_params, stmt)
                    omen_t = OmenType(name=o_name, variants=variants, variant_values=variant_values, type_params=type_params, c_name=c_o_name, derived_concepts=list(derived_concepts), bounds=bounds)
                else:
                    omen_t = OmenType(name=o_name, variants=variants, variant_values=variant_values, c_name=c_o_name, derived_concepts=list(derived_concepts))

                for d_concept in derived_concepts:
                    self.symbols.concept_bindings.setdefault((o_name, d_concept), {})
                    if c_o_name != o_name:
                        self.symbols.concept_bindings.setdefault((c_o_name, d_concept), {})

                self.symbols.omens[o_name] = omen_t
                if c_o_name != o_name:
                    self.symbols.omens[c_o_name] = omen_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=o_name, type=omen_t, kind="omen", line=line, column=col, doc=doc, file_path=self.filename, c_name=c_o_name
                ))
                is_d_pengu = bool(self.filename and self.filename.endswith(".d.pengu"))
                for v_name in variants:
                    # For declaration files (.d.pengu), C enum constants follow the
                    # header's plain enumerator name (no insignia or omen prefix).
                    c_v_name = v_name if is_d_pengu else f"{c_o_name}_{v_name}"
                    self.symbols.global_scope.define(Symbol(
                        name=f"{o_name}_{v_name}", type=omen_t, kind="omen_variant", is_mutable=False, line=line, column=col, file_path=self.filename, c_name=c_v_name
                    ))
                    if self.symbols.global_scope.lookup(v_name) is None:
                        self.symbols.global_scope.define(Symbol(
                            name=v_name, type=omen_t, kind="omen_variant", is_mutable=False, line=line, column=col, file_path=self.filename, c_name=c_v_name
                        ))

            elif rule == "alias_decl":
                a_name = str(stmt.children[0])
                if not is_d_pengu and a_name in C_RESERVED_TYPE_NAMES:
                    err = self._make_error(
                        SemanticError,
                        f"Type name '{a_name}' is a reserved C keyword or standard identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this alias (e.g. 'My{a_name}' or '{a_name}Type').",
                        note="User type names cannot shadow C keywords or standard library identifiers to avoid emitting invalid C."
                    )
                    self._record_error(err)
                    continue
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
                alias_obj = AliasType(name=a_name, target=target_t, type_params=type_params, c_name=c_a_name)
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
                if not is_d_pengu and s_name in C_RESERVED_TYPE_NAMES:
                    err = self._make_error(
                        SemanticError,
                        f"Type name '{s_name}' is a reserved C keyword or standard identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this seal (e.g. 'My{s_name}' or '{s_name}Type').",
                        note="User type names cannot shadow C keywords or standard library identifiers to avoid emitting invalid C."
                    )
                    self._record_error(err)
                    continue
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
                if not is_d_pengu and concept_name in C_RESERVED_TYPE_NAMES:
                    err = self._make_error(
                        SemanticError,
                        f"Type name '{concept_name}' is a reserved C keyword or standard identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this concept (e.g. 'My{concept_name}' or '{concept_name}Concept').",
                        note="User type names cannot shadow C keywords or standard library identifiers to avoid emitting invalid C."
                    )
                    self._record_error(err)
                    continue
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
                base_tname = get_type_base_name(target_type)

                if (target_name, concept_name) in self.symbols.concept_bindings or (base_tname, concept_name) in self.symbols.concept_bindings:
                    err = self._make_error(
                        DuplicateConceptBindingError,
                        f"Duplicate concept binding: '{target_name}' already bound to '{concept_name}'",
                        stmt,
                        code="E0052",
                        help=f"Remove the duplicate 'bind {target_name} with {concept_name}:' declaration.",
                        note="A type can only bind a concept once."
                    )
                    self._record_error(err)

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

                        # Coherence (Phase 3): a type may bind several concepts,
                        # but the same method name cannot be provided by two
                        # different concepts — the call site could not choose.
                        owner_key = (base_tname, m_name)
                        prev_owner = self.symbols.bind_method_owner.get(owner_key)
                        if prev_owner is not None and prev_owner != concept_name:
                            err = self._make_error(
                                DuplicateConceptBindingError,
                                f"Method '{m_name}' of type '{base_tname}' is already provided by concept '{prev_owner}'",
                                m_decl,
                                code="E0052",
                                help=f"Rename the method in one of the 'bind' blocks, or merge "
                                     f"'{prev_owner}' and '{concept_name}'.",
                                note="A (type, method) pair can only be implemented once."
                            )
                            self._record_error(err)
                        else:
                            self.symbols.bind_method_owner[owner_key] = concept_name

                        self.symbols.methods[(target_name, m_name)] = impl_fn_t
                        if type_params or m_tparams:
                            self.symbols.methods[(base_tname, m_name)] = impl_fn_t
                            # (receiver_params, method_params, ast) — keeping the
                            # two param lists apart lets call sites split the
                            # receiver's type args from explicit 'of T' args.
                            self.symbols.generic_methods[(base_tname, m_name)] = (
                                list(type_params or []), list(m_tparams or []), m_decl,
                            )

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
                            if bool(getattr(impl_mfn, "is_ritual", False)) != bool(getattr(c_mfn, "is_ritual", False)):
                                err = self._make_error(
                                    ConceptMethodMismatchError,
                                    f"Method '{c_mname}' in bind block is "
                                    f"{'ritual' if getattr(impl_mfn, 'is_ritual', False) else 'not ritual'}, "
                                    f"but concept '{concept_name}' declares it "
                                    f"{'ritual' if getattr(c_mfn, 'is_ritual', False) else 'not ritual'}",
                                    stmt,
                                    code="E0030",
                                    help="Add or remove the 'ritual' modifier so the implementation "
                                         "matches the concept.",
                                    note="A ritual method has no 'self'; a normal method receives the instance."
                                )
                                self._record_error(err)
                            elif len(impl_mfn.params) != len(c_mfn.params) or not impl_mfn.return_type.is_compatible(c_mfn.return_type):
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
                self.const_definitions.setdefault(c_name, []).append((const_val, self.filename))
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
                base_tname = get_type_base_name(target_type)
                type_params = []
                enc_bounds: Dict[str, List[str]] = {}
                for ch in stmt.children[1:]:
                    if isinstance(ch, Tree) and ch.data == "shard_params":
                        sp_names, sp_bounds = extract_shard_params(ch)
                        if sp_names:
                            type_params = sp_names
                        enc_bounds.update(sp_bounds)
                    elif isinstance(ch, Tree) and ch.data == "where_clause":
                        enc_bounds.update(extract_where_clause(ch))

                if not type_params:
                    if base_tname in self.symbols.generic_runes:
                        type_params = self.symbols.generic_runes[base_tname][0]
                    elif isinstance(target_type, RuneType) and target_type.type_args:
                        type_params = [getattr(t, "name", str(t)) for t in target_type.type_args]
                    else:
                        type_params = extract_type_params_from_type(target_type)

                if isinstance(target_type, MapType):
                    k_name = getattr(target_type.key, "name", None)
                    if k_name and k_name in type_params:
                        k_b = enc_bounds.setdefault(k_name, [])
                        if "Par" not in k_b: k_b.append("Par")
                        if "Vinculum" not in k_b: k_b.append("Vinculum")

                target_type = target_type.substitute({tp: TypeParam(tp, bounds=enc_bounds.get(tp, [])) for tp in type_params})

                for m_decl in stmt.children[1:]:
                    if isinstance(m_decl, Tree) and m_decl.data == "weave_decl":
                        m_inline, m_ritual, m_idx = _extract_weave_modifiers(m_decl.children)
                        m_name = str(m_decl.children[m_idx])
                        m_rem = [c for c in m_decl.children[m_idx+1:] if c is not None]
                        m_tparams = []
                        m_bounds = {}
                        if m_rem and isinstance(m_rem[0], Tree) and m_rem[0].data == "shard_params":
                            m_tparams, m_bounds = extract_shard_params(m_rem[0])
                            m_rem = m_rem[1:]

                        all_bounds = dict(enc_bounds)
                        all_bounds.update(m_bounds)

                        def lookup_m_tp(tname: str):
                            if tname in m_tparams:
                                return TypeParam(tname, bounds=all_bounds.get(tname, []))
                            if tname in type_params:
                                return TypeParam(tname, bounds=all_bounds.get(tname, []))
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
                        if type_params or m_tparams:
                            self.symbols.methods[(base_tname, m_name)] = impl_fn_t
                            self.symbols.generic_methods[(base_tname, m_name)] = (type_params or [], m_tparams or [], m_decl)

            elif rule == "declare_stmt":
                d_attrs, d_idx = _extract_attributes(stmt.children)
                self._validate_attributes(d_attrs, "declare", stmt)
                is_inline, is_ritual, idx = _extract_weave_modifiers(stmt.children, start_idx=d_idx)
                if "inline" in d_attrs:
                    is_inline = True
                fn_name = str(stmt.children[idx])
                if fn_name in C_KEYWORDS:
                    err = self._make_error(
                        SemanticError,
                        f"Function name '{fn_name}' is a reserved C keyword",
                        stmt,
                        code="E0035",
                        help="Choose a different name for this declared function.",
                        note="Functions cannot be named after C keywords."
                    )
                    self._record_error(err)
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
                                if isinstance(pt, ManyType):
                                    err = self._make_error(
                                        SemanticError,
                                        f"'many' parameters are not allowed in 'declare' statements",
                                        p,
                                        code="E0005",
                                        help="Use '...' for C variadic functions: "
                                             "'declare printf with fmt as ref to frozen char, ... into int'. "
                                             "'many T' is only valid for 'weave' parameters.",
                                        note="'declare' binds an existing C function; C varargs are marked "
                                             "with '...', not 'many'."
                                    )
                                    self._record_error(err)
                                params.append((pn, pt))
                            elif (isinstance(p, Token) and (p.type in ("VARARGS", "_VARARGS") or str(p) == "...")) or (isinstance(p, Tree) and p.data in ("varargs", "_varargs")):
                                params.append(("_varargs", CVarArgsType()))
                    elif isinstance(child_n, Tree) and child_n.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                        ret_type = ast_to_type(child_n, lookup_tp)
                    elif isinstance(child_n, Token) and child_n.type == "NAME":
                        ret_type = ast_to_type(child_n, lookup_tp)
                fn_t = FnType(params=params, return_type=ret_type, is_ritual=is_ritual, type_params=type_params, attributes=d_attrs)
                self.symbols.functions[fn_name] = fn_t
                if c_fn_name != fn_name:
                    self.symbols.functions[c_fn_name] = fn_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=fn_name, type=fn_t, kind="declare", is_mutable=False, is_ritual=is_ritual, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_fn_name, attributes=d_attrs
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
                w_attrs, w_idx = _extract_attributes(stmt.children)
                self._validate_attributes(w_attrs, "weave", stmt)
                is_inline, is_ritual, idx = _extract_weave_modifiers(stmt.children, start_idx=w_idx)
                if "inline" in w_attrs:
                    is_inline = True
                fn_name = str(stmt.children[idx])
                if fn_name == "main":
                    if getattr(self, "_seen_main_file", None) is not None:
                        err = self._make_error(
                            SemanticError,
                            f"Multiple entry points 'main' defined: first in '{self._seen_main_file}', duplicate in '{self.filename}'",
                            stmt,
                            code="E0046",
                            help="A PenguScript program can only have a single 'weave main' entry point.",
                            note="Only one 'weave main' can be active in an executable."
                        )
                        self._record_error(err)
                    else:
                        self._seen_main_file = self.filename
                elif not is_d_pengu and not is_std and current_insignia is None and (fn_name in C_RESERVED_FN_NAMES or (fn_name in C_RESERVED_TYPE_NAMES and fn_name not in C_KEYWORDS)):
                    err = self._make_error(
                        SemanticError,
                        f"Function name '{fn_name}' is a reserved standard C function or identifier",
                        stmt,
                        code="E0035",
                        help=f"Choose a different name for this function (e.g. 'my_{fn_name}').",
                        note="Function names cannot shadow standard library functions like 'printf' or 'malloc'."
                    )
                    self._record_error(err)
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
                    fn_t = FnType(params=params, return_type=ret_type, default_count=default_count, is_ritual=is_ritual, type_params=type_params, attributes=w_attrs)
                else:
                    fn_t = FnType(params=params, return_type=ret_type, default_count=default_count, is_ritual=is_ritual, attributes=w_attrs)

                self.symbols.functions[fn_name] = fn_t
                if c_fn_name != fn_name:
                    self.symbols.functions[c_fn_name] = fn_t
                doc = self._extract_preceding_doc(line)
                self.symbols.global_scope.define(Symbol(
                    name=fn_name, type=fn_t, kind="weave", is_mutable=False, is_inline=is_inline, is_ritual=is_ritual, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_fn_name, attributes=w_attrs
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
                    order = resolve_imports(self.base_dir, target_file,
                                            parser=getattr(self, "parser", None),
                                            lib_dir=getattr(self, "lib_dir", "lib"))
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
                                prev_fn = self.filename
                                prev_insignia = getattr(self.symbols, "insignia", None)
                                try:
                                    self.filename = mod_abs
                                    self.symbols.insignia = None
                                    self._collect_top_level(m_tree, import_order=order, current_insignia=None)
                                finally:
                                    self.filename = prev_fn
                                    self.symbols.insignia = prev_insignia
                except SemanticError as e:
                    self._record_error(e)
        return current_insignia



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
                if getattr(node, "_pengu_with_init_checked_err", False):
                    return
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
                if getattr(node, "_pengu_with_init_checked_err", False):
                    return
            self._check_let_decl(node)
            return

        elif rule == "const_decl":
            self._check_const_decl(node)
            return

        # 2. Enchanting Blocks
        elif rule == "enchanting_decl":
            target_type_node = node.children[0]
            target_type = ast_to_type(target_type_node, self.symbols.lookup_type)
            base_tname = get_type_base_name(target_type)
            type_params = []
            bounds: Dict[str, List[str]] = {}

            for ch in node.children[1:]:
                if isinstance(ch, Tree) and ch.data == "shard_params":
                    sp_names, sp_bounds = extract_shard_params(ch)
                    if sp_names:
                        type_params = sp_names
                    bounds.update(sp_bounds)
                elif isinstance(ch, Tree) and ch.data == "where_clause":
                    bounds.update(extract_where_clause(ch))

            if not type_params:
                if base_tname in self.symbols.generic_runes:
                    type_params = self.symbols.generic_runes[base_tname][0]
                elif isinstance(target_type, RuneType) and target_type.type_args:
                    type_params = [getattr(t, "name", str(t)) for t in target_type.type_args]
                else:
                    type_params = extract_type_params_from_type(target_type)

            if isinstance(target_type, MapType):
                k_name = getattr(target_type.key, "name", None)
                if k_name and k_name in type_params:
                    k_b = bounds.setdefault(k_name, [])
                    if "Par" not in k_b: k_b.append("Par")
                    if "Vinculum" not in k_b: k_b.append("Vinculum")

            target_type = target_type.substitute({tp: TypeParam(tp, bounds=bounds.get(tp, [])) for tp in type_params})

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
                tp_b = list(bounds.get(tp, []))
                self.symbols.define(Symbol(name=tp, type=TypeParam(tp, bounds=tp_b), kind="type"))

            for child in node.children[1:]:
                if isinstance(child, Tree) and child.data == "weave_decl":
                    self._check_enchanting_method(child, target_type, type_params=type_params, type_bounds=bounds)
                else:
                    self._check_node(child)

            self.symbols.pop_scope(end_line=span_end)
            return

        elif rule == "bind_decl":
            target_type_node = node.children[0]
            concept_name_node = node.children[1]
            rem_children = [c for c in node.children[2:] if c is not None]
            type_params = []
            bind_bounds: Dict[str, List[str]] = {}
            if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
                type_params, bind_bounds = extract_shard_params(rem_children[0])
                rem_children = rem_children[1:]
            elif rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "where_clause":
                # 'bind Foo with Bar shard T:' may also carry a standalone
                # 'where T: ...' clause after the shard list.
                bind_bounds.update(extract_where_clause(rem_children[0]))
                rem_children = rem_children[1:]

            target_type = ast_to_type(target_type_node, self.symbols.lookup_type)
            if type_params:
                target_type = target_type.substitute(
                    {tp: TypeParam(tp, bounds=bind_bounds.get(tp, [])) for tp in type_params}
                )
            span_start, span_end = self._get_node_span(node)
            self.symbols.push_scope(kind="enchanting", enchanting_type=target_type, start_line=span_start, end_line=span_end)
            for tp in type_params:
                # The shard bounds ('where T: Par') must reach the method bodies:
                # the body of 'bind Box with Eq shard T where T: Par' compares
                # 'T' values, and that needs the bound at check time.
                self.symbols.define(Symbol(name=tp, type=TypeParam(tp, bounds=bind_bounds.get(tp, [])), kind="type"))

            for child in rem_children:
                if isinstance(child, Tree) and child.data == "weave_decl":
                    self._check_enchanting_method(child, target_type, type_params=type_params, type_bounds=bind_bounds)
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

        elif rule == "unsafe_stmt":
            self._check_unsafe_block(node)
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
                "string_lit", "int_lit", "float_lit", "char_lit",
                "true_lit", "false_lit", "null_lit", "array_lit", "map_lit"
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
                "calling_expr", "add", "sub", "mul", "div", "mod",
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
                    "arrow_access", "at_access", "essence_of"
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
                if sym is not None and sym.kind in ("var", "let"):
                    if getattr(sym, "is_auto_banished", False):
                        err = self._make_error(
                            AutoOwnedBanishError,
                            f"'banish' on auto-owned local '{sym_name}' would double-free",
                            target_expr,
                            code="E0047",
                            help="Remove 'banish' — the compiler frees this variable automatically at the end of its scope.",
                            note="Variables allocated locally with fresh ownership are scope-owned and cleaned up automatically."
                        )
                        self._record_error(err)
                        return
                    if getattr(sym, "is_borrowed", False):
                        err = self._make_error(
                            BorrowedBanishError,
                            f"'banish' on borrowed local '{sym_name}'",
                            target_expr,
                            code="E0048",
                            help="Remove 'banish' — borrowed references do not own the underlying memory.",
                            note="Only the owner of a resource is allowed to banish it."
                        )
                        self._record_error(err)
                        return
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
                if sym:
                    curr_t = sym.type
                    is_frozen = isinstance(curr_t, FrozenType)
                    while isinstance(curr_t, (AliasType, RefType)):
                        curr_t = getattr(curr_t, "target", None)
                        if isinstance(curr_t, FrozenType):
                            is_frozen = True
                            break
                    if is_frozen:
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
                    or (isinstance(curr, Tree) and curr.data == "essence_of")
                    # A value type with a derived Nexus owns its fields and has
                    # a generated destructor, so it can be released explicitly:
                    # 'banish doc' lowers to '_pengu_cleanup_Doc(&doc)'.
                    or type_has_derived_nexus(t, self.symbols)
                )
                if not is_valid_type:
                    err = self._make_error(
                        InvalidMemoryOpError,
                        f"'banish' requires a reference (ref to T), string, list, map, or a type with 'derive Nexus', got nominal seal type '{t}'" if isinstance(t, SealType) else f"'banish' requires a reference (ref to T), string, list, map, or a type with 'derive Nexus', got '{t}'",
                        target_expr,
                        code="E0008",
                        help="Pass a reference (ref to T), string, list, or map to 'banish', or add 'derive Nexus' to the type. Nominal seal types are also rejected; cast first: 'banish (v to string)'.",
                        note="'banish' deallocates memory behind references, strings, lists, maps, and 'derive Nexus' values."
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

        elif rule == "judge_expr":
            self._check_judge_expr(node)
            return

        elif rule == "when_stmt":
            self._check_when_stmt(node)
            return

        elif rule == "defined_expr":
            # 'defined(NAME)' is a compile-time predicate: 'when'/'when_expr'
            # evaluate it in pengu_comptime and never reach this dispatcher, so a
            # runtime occurrence would emit the bare identifier as C.
            name = str(node.children[0]) if node.children else "?"
            self._record_error(self._make_error(
                SemanticError,
                f"'defined({name})' can only be used in a compile-time 'when' condition",
                node,
                code="E0039",
                help="Move the check into 'when defined(NAME): …' or a 'when …' expression.",
                note="'defined' is resolved before code generation; it has no runtime value."
            ))
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

        elif rule == "char_lit":
            try:
                self.inferrer._validate_char_lit(node)
            except PenguError as err:
                self._record_error(err)
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
            self._check_node(Tree("expr_stmt", node.children, meta=node.meta))

    def _is_static_const_expr(self, node: Any) -> bool:
        """Determines if an expression is a valid compile-time constant expression for static/global constants."""
        if self.const_folder.fold(node) is not None:
            return True
        if isinstance(node, Token):
            if node.type in ("INT", "FLOAT", "CHAR_LIT", "STRING", "RAW_STRING", "TRIPLE_STRING", "RAW_TRIPLE_STRING"):
                return True
            if node.type == "NAME":
                sym = self.symbols.lookup(str(node))
                return sym is not None and (sym.kind in ("const", "omen_variant", "omen"))
            return False
        if not isinstance(node, Tree):
            return False
        rule = node.data
        if rule in ("null_lit", "maybe_none"):
            return True
        if rule == "var_ref":
            name = str(node.children[0])
            sym = self.symbols.lookup(name)
            return sym is not None and (sym.kind in ("const", "omen_variant", "omen"))
        if rule in ("field_access", "normal_target") and len(node.children) == 2:
            base = str(node.children[0])
            sym = self.symbols.lookup(base)
            if sym is not None and sym.kind == "omen":
                return True
        if rule == "array_lit":
            return all(self._is_static_const_expr(c) for c in node.children if isinstance(c, (Tree, Token)))
        if rule == "struct_init":
            field_inits = [c for c in node.children if isinstance(c, Tree) and c.data == "field_init"]
            return all(self._is_static_const_expr(fi.children[-1]) for fi in field_inits)
        return False

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
        if not self.filename.endswith(".d.pengu") and (c_name in C_RESERVED_TYPE_NAMES or c_name in C_RESERVED_WORDS):
            self._record_error(self._make_error(
                SemanticError,
                f"Constant name '{c_name}' is a reserved C keyword or standard identifier",
                node,
                code="E0035",
                help=f"Choose a different name for this constant (e.g. 'MY_{c_name.upper()}').",
                note="Constants emitted as C macros or definitions cannot shadow C keywords or standard library identifiers."
            ))
            return
        if not self.symbols.is_top_level():
            existing = self.symbols.lookup_local(c_name) if self.symbols else None
            if existing is not None:
                self._record_error(self._make_error(
                    SemanticError,
                    f"Redefinition of '{c_name}' in the same scope",
                    node,
                    code="E0053",
                    help="Use a distinct name for this constant.",
                    note=f"'{c_name}' was previously declared on line {existing.line}."
                ))
                return

        c_type = None
        c_expr = None

        if len(node.children) == 3:
            if node.children[1] is not None:
                self._validate_type_node(node.children[1])
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

                if isinstance(eff_type, (MapType, ListType)):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Constant '{c_name}' cannot be of type '{eff_type}' because it requires dynamic heap allocation",
                        node,
                        code="E0005",
                        help="Use a fixed array ('array of T') for compile-time collection constants, or initialize a local variable inside a function.",
                        note="Top-level constants must be statically initializable at compile time."
                    )

                if isinstance(eff_type, ArrayType):
                    base_elem = eff_type
                    while isinstance(base_elem, ArrayType):
                        base_elem = base_elem.element
                    if not _is_statically_initializable_type(base_elem):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Constant '{c_name}' of type '{eff_type}' cannot be statically initialized at compile time",
                            node,
                            code="E0005",
                            help="Constant arrays require statically initializable element types (numeric, bool, char, 'ref to char', or static runes/omens). For strings or heap objects, initialize a local variable inside a function.",
                            note="C requires compile-time constant expressions for static array initializers."
                        )

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
                is_static = self._is_static_const_expr(c_expr)
                if not self.symbols.is_top_level():
                    if folded_val is None and not is_static:
                        raise self._make_error(
                            ConstInsideWeaveError,
                            "'const' inside a weave must be compile-time evaluable; use 'let' for runtime-immutable bindings",
                            node,
                            code="E0001",
                            help="Use 'let' (immutable) or 'var' (mutable) inside functions instead of 'const'.",
                            note="'const' inside a weave is only allowed for compile-time constant expressions."
                        )
                elif not self.filename.endswith(".d.pengu") and not is_static and folded_val is None:
                    raise self._make_error(
                        SemanticError,
                        f"Constant '{c_name}' initializer is not a compile-time constant expression",
                        c_expr,
                        code="E0005",
                        help="Constants must evaluate to a compile-time constant (literal, constant folding, or another const). Use 'let' or 'var' for runtime expressions.",
                        note="Top-level constants are emitted as compile-time macros or static initializers in C."
                    )
                doc = self._extract_preceding_doc(line)
                existing_sym = self.symbols.lookup(c_name)
                c_c_name = existing_sym.c_name if existing_sym else None
                sym = Symbol(name=c_name, type=eff_type, kind="const", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename, c_name=c_c_name)
                if folded_val is not None:
                    sym.const_val = folded_val
                node._pengu_symbol = sym
                self.symbols.define(sym)
        except SemanticError as e:
            self._record_error(e)

    # ------------------------------------------------------------------
    # 'with:' block construction expressions
    # ------------------------------------------------------------------

    @staticmethod
    def _decl_type_and_expr(node: Tree):
        """Returns (type_node, expr_node) of a var/let/const declaration."""
        return _decl_layout(node)

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
            setattr(node, "_pengu_with_init_checked_err", True)
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
        result = self._check_with_builder(expr, expected)
        setattr(expr, "_pengu_value_type", result)

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
                is_valid = False
                if inner.data == "set_stmt":
                    is_valid = True
                elif inner.data == "expr_stmt" and inner.children:
                    expr_child = inner.children[0]
                    if isinstance(expr_child, Tree) and expr_child.data == "calling_expr" and expr_child.children:
                        tgt = expr_child.children[0]
                        if isinstance(tgt, Tree) and tgt.data in ("with_target", "normal_target"):
                            is_valid = True
                if not is_valid:
                    if inner.data == "expr_stmt" and inner.children:
                        first_child = inner.children[0]
                        inner_desc = first_child.data if isinstance(first_child, Tree) else (getattr(first_child, "type", None) or str(first_child))
                    else:
                        inner_desc = inner.data
                    err = self._make_error(
                        InvalidBuilderStatementError,
                        "'with:' block only allows 'set .field is ...' assignments and "
                        f"'calling .method' statements, not '{inner_desc}'",
                        inner,
                        code="E0014",
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

    def _check_value_block(self, stmts: List[Tree], expected: Optional[Type] = None,
                           copies_value: bool = False) -> Type:
        """Validates a value block in a fresh scope and returns its value type.

        Every statement is checked normally; the last one supplies the block's
        value (see :meth:`_check_block_value_stmt`).  ``copies_value`` is set for
        loop bodies: their value is deep-copied into the collected list, so a
        local that produces it does not escape and stays auto-banished.
        """
        if not stmts:
            return VOID_TYPE
        s_start, _ = self._get_node_span(stmts[0])
        _, e_end = self._get_node_span(stmts[-1])
        val = VOID_TYPE
        s_stmts = [s for s in stmts if isinstance(s, Tree)]
        self.block_stmts_stack.append(s_stmts)
        if not hasattr(self, "_value_block_stack"):
            self._value_block_stack = []
        # 'None' marks a block whose value is copied out (a loop body): the
        # producing local keeps ownership and must still be released.
        self._value_block_stack.append(None if copies_value else s_stmts)
        try:
            self.symbols.push_scope(kind="do", start_line=s_start, end_line=e_end)
            for ch in stmts[:-1]:
                self._check_node(ch)
            val = self._check_block_value_stmt(stmts[-1], expected)
        finally:
            self.symbols.pop_scope(end_line=e_end)
            self._value_block_stack.pop()
            self.block_stmts_stack.pop()
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

        if elem_t == VOID_TYPE or isinstance(elem_t, (NullType, AnyType)):
            if required:
                err = self._make_error(
                    TypeMismatchError,
                    "loop used as a value must produce a value on every iteration",
                    node,
                    code="E0005",
                    help="End the loop body with a concrete expression (the value collected "
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
        if rule == "or_block":
            self._check_or_block(node)
            return
        if rule == "judge_expr":
            self._check_judge_expr(node)
            return
        if rule == "struct_init":
            unwrapped_expected = expected
            while isinstance(unwrapped_expected, (AliasType, FrozenType)):
                unwrapped_expected = unwrapped_expected.target
            expected_fields: Dict[str, Type] = {}
            if isinstance(unwrapped_expected, (RuneType, EchoType)):
                expected_fields = unwrapped_expected.fields
                if not expected_fields and self.symbols:
                    sym_t = self.symbols.lookup_type(unwrapped_expected.name)
                    if isinstance(sym_t, (RuneType, EchoType)) and sym_t.fields:
                        expected_fields = sym_t.fields
            elif isinstance(unwrapped_expected, OmenType):
                variants = unwrapped_expected.variants
                if not variants and self.symbols:
                    sym_t = self.symbols.lookup_type(unwrapped_expected.name)
                    if isinstance(sym_t, OmenType) and sym_t.variants:
                        variants = sym_t.variants
                for v_name, v_fields in (variants or {}).items():
                    expected_fields[v_name] = RuneType(name=v_name, fields=v_fields)
            for child in node.children:
                if isinstance(child, Tree) and child.data == "field_init":
                    f_name = str(child.children[0])
                    f_exp = expected_fields.get(f_name)
                    if len(child.children) > 1 and child.children[1] is not None:
                        self._check_value_exprs(child.children[1], f_exp)
                else:
                    self._check_value_exprs(child)
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

    def _check_judge_expr(self, node: Tree) -> None:
        """Checks judge expression constraints."""
        subj_node = node.children[0]
        self._check_node(subj_node)
        try:
            subj_t = self.inferrer.infer(subj_node)
        except Exception:
            subj_t = None

        unwrapped_subj = subj_t
        while isinstance(unwrapped_subj, (AliasType, FrozenType)) and getattr(unwrapped_subj, "target", None):
            unwrapped_subj = unwrapped_subj.target
        if isinstance(unwrapped_subj, SealType):
            unwrapped_subj = unwrapped_subj.underlying

        for child in node.children[1:]:
            if isinstance(child, Tree) and child.data == "when_clause":
                pat_node = child.children[0]
                body_node = child.children[-1]
                payload_node = None
                guard_node = None
                for sub in child.children[1:-1]:
                    if isinstance(sub, Tree):
                        if sub.data == "when_payload":
                            payload_node = sub
                        elif sub.data == "when_guard":
                            guard_node = sub

                if unwrapped_subj is not None and len(child.children) >= 1:
                    self._check_when_pattern_type(pat_node, unwrapped_subj, subj_t)

                var_name = None
                variant_fields: Dict[str, Type] = {}
                if isinstance(unwrapped_subj, OmenType):
                    var_name, variant_fields = self._resolve_omen_variant(pat_node, unwrapped_subj)

                payload_fields = self._extract_payload_fields(payload_node) if payload_node else []
                if payload_fields:
                    if not isinstance(unwrapped_subj, OmenType):
                        self._record_error(self._make_error(
                            SemanticError,
                            "Payload bindings are only supported on omen variants",
                            payload_node,
                            code="E0005"
                        ))
                    elif not variant_fields:
                        self._record_error(self._make_error(
                            SemanticError,
                            f"Variant '{var_name}' has no payload fields",
                            payload_node,
                            code="E0005"
                        ))
                    else:
                        for f_name, f_node in payload_fields:
                            if f_name not in variant_fields:
                                self._record_error(self._make_error(
                                    SemanticError,
                                    f"Variant '{var_name}' has no field '{f_name}'",
                                    f_node,
                                    code="E0005"
                                ))

                # Register payload variables in when_clause scope
                self.symbols.push_scope(kind="when_clause")
                try:
                    for f_name, f_node in payload_fields:
                        if f_name in variant_fields:
                            sym = Symbol(
                                name=f_name,
                                type=variant_fields[f_name],
                                kind="let",
                                is_mutable=False,
                                line=getattr(f_node, "line", 1),
                                column=getattr(f_node, "column", 1)
                            )
                            self.symbols.define(sym)

                    if guard_node is not None:
                        guard_expr_node = guard_node.children[0]
                        self._check_node(guard_expr_node)
                        try:
                            guard_t = self.inferrer.infer(guard_expr_node)
                            if not (guard_t == BOOL_TYPE or guard_t.is_compatible(BOOL_TYPE)):
                                self._record_error(self._make_error(
                                    TypeMismatchError,
                                    f"Judge guard must be boolean, got '{guard_t}'",
                                    guard_node,
                                    code="E0005"
                                ))
                        except Exception as e:
                            self._record_error(e)

                    self._check_node(body_node)
                finally:
                    self.symbols.pop_scope()

            elif isinstance(child, Tree) and child.data == "else_clause":
                self._check_node(child)

    def _extract_payload_fields(self, payload_node: Tree) -> List[Tuple[str, Any]]:
        fields = []
        for c in payload_node.children:
            if isinstance(c, Tree) and c.data == "when_field":
                fields.append((str(c.children[0]), c))
            elif isinstance(c, Token) and c.type == "NAME":
                fields.append((str(c), c))
        return fields

    def _resolve_omen_variant(self, pat_node: Any, omen: OmenType) -> Tuple[Optional[str], Dict[str, Type]]:
        if not isinstance(pat_node, Tree) or pat_node.data != "when_pattern":
            return None, {}
        children = [c for c in pat_node.children if (isinstance(c, Token) and c.type == "NAME") or (isinstance(c, str))]
        if not children:
            return None, {}
        raw_name = str(children[-1])
        var_name = raw_name
        c_name = getattr(omen, "c_name", None) or omen.name
        for prefix in (f"{omen.name}_", f"{c_name}_"):
            if var_name.startswith(prefix):
                var_name = var_name[len(prefix):]
                break
        if var_name in omen.variants:
            return var_name, omen.variants[var_name]
        if raw_name in omen.variants:
            return raw_name, omen.variants[raw_name]
        return var_name, {}

    def _check_when_pattern_type(self, pat_node: Any, unwrapped_subj: Type, subj_t: Type) -> None:
        if not isinstance(pat_node, Tree) or pat_node.data != "when_pattern":
            return
        children = pat_node.children
        if not children:
            return
        if all(isinstance(c, Token) and c.type == "NAME" for c in children):
            if isinstance(unwrapped_subj, OmenType):
                raw_name = str(children[-1])
                var_name = raw_name
                c_name = getattr(unwrapped_subj, "c_name", None) or unwrapped_subj.name
                for prefix in (f"{unwrapped_subj.name}_", f"{c_name}_"):
                    if var_name.startswith(prefix):
                        var_name = var_name[len(prefix):]
                        break
                if var_name not in unwrapped_subj.variants and raw_name not in unwrapped_subj.variants:
                    self._record_error(self._make_error(
                        TypeMismatchError,
                        f"Pattern '{raw_name}' is not a variant of omen '{unwrapped_subj.name}'",
                        pat_node,
                        code="E0005"
                    ))
            elif unwrapped_subj.is_int():
                var_name = str(children[0])
                sym = self.symbols.lookup(var_name)
                if sym is not None and not sym.type.is_int():
                    self._record_error(self._make_error(
                        TypeMismatchError,
                        f"Pattern '{var_name}' of type '{sym.type}' cannot match integer subject",
                        pat_node,
                        code="E0005"
                    ))
            elif unwrapped_subj.is_string():
                var_name = str(children[0])
                sym = self.symbols.lookup(var_name)
                if sym is not None and not sym.type.is_string():
                    self._record_error(self._make_error(
                        TypeMismatchError,
                        f"Pattern '{var_name}' of type '{sym.type}' cannot match string subject",
                        pat_node,
                        code="E0005"
                    ))
            return

        first = children[0]
        pat_t = None
        if isinstance(first, Token):
            if first.type in ("INT", "CHAR_LIT"):
                pat_t = INT_TYPE
            elif first.type == "FLOAT":
                pat_t = FLOAT_TYPE
            elif first.type in ("STRING", "RAW_STRING", "TRIPLE_STRING", "RAW_TRIPLE_STRING"):
                pat_t = STRING_TYPE
        elif isinstance(first, Tree) and first.data in ("true_lit", "false_lit"):
            pat_t = BOOL_TYPE

        if pat_t is not None:
            if unwrapped_subj.is_int() and not pat_t.is_int():
                self._record_error(self._make_error(
                    TypeMismatchError,
                    f"Pattern of type '{pat_t}' cannot match integer subject",
                    pat_node,
                    code="E0005"
                ))
            elif unwrapped_subj.is_string() and not pat_t.is_string():
                self._record_error(self._make_error(
                    TypeMismatchError,
                    f"Pattern of type '{pat_t}' cannot match string subject",
                    pat_node,
                    code="E0005"
                ))
            elif (unwrapped_subj == BOOL_TYPE or unwrapped_subj.is_compatible(BOOL_TYPE)) and pat_t != BOOL_TYPE:
                self._record_error(self._make_error(
                    TypeMismatchError,
                    f"Pattern of type '{pat_t}' cannot match boolean subject",
                    pat_node,
                    code="E0005"
                ))
            elif isinstance(unwrapped_subj, OmenType):
                if not pat_t.is_int() and not pat_t.is_string():
                    self._record_error(self._make_error(
                        TypeMismatchError,
                        f"Pattern of type '{pat_t}' cannot match omen '{unwrapped_subj.name}'",
                        pat_node,
                        code="E0005"
                    ))

    def _validate_array_literal_size(self, declared_t: Type, lit_node: Any) -> None:
        """Validates array dimensions against array literals (indent_literal and array_lit)."""
        if not isinstance(declared_t, ArrayType) or not isinstance(lit_node, Tree):
            return

        if lit_node.data == "indent_literal":
            if not lit_node.children:
                return
            child = lit_node.children[0]
            if isinstance(child, Tree) and child.data == "indent_array":
                rows = child.children
                if isinstance(declared_t.element, ArrayType):
                    outer_sz = declared_t.size
                    inner_sz = declared_t.element.size
                    if outer_sz is not None and len(rows) != outer_sz:
                        raise self._make_error(
                            ArraySizeMismatchError,
                            f"Array has {len(rows)} rows but the declared size is {outer_sz}",
                            child,
                            code="E0041"
                        )
                    for r_idx, r in enumerate(rows):
                        r_elems = r.children if isinstance(r, Tree) else []
                        if inner_sz is not None and len(r_elems) != inner_sz:
                            raise self._make_error(
                                ArraySizeMismatchError,
                                f"Row {r_idx + 1} has {len(r_elems)} elements but the declared width is {inner_sz}",
                                r,
                                code="E0041"
                            )
                else:
                    sz = declared_t.size
                    all_elems = [e for r in rows if isinstance(r, Tree) for e in r.children]
                    if sz is not None and len(all_elems) != sz:
                        raise self._make_error(
                            ArraySizeMismatchError,
                            f"Array has {len(all_elems)} elements but the declared size is {sz}",
                            child,
                            code="E0041"
                        )

        elif lit_node.data == "array_lit":
            elems = lit_node.children
            sz = declared_t.size
            if sz is not None and len(elems) != sz:
                raise self._make_error(
                    ArraySizeMismatchError,
                    f"Array literal has {len(elems)} elements but declared size is {sz}",
                    lit_node,
                    code="E0041",
                    help=f"Expected {sz} elements to match declared array size.",
                )
            if isinstance(declared_t.element, ArrayType):
                for elem in elems:
                    if isinstance(elem, Tree) and elem.data == "array_lit":
                        self._validate_array_literal_size(declared_t.element, elem)

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

    def _is_direct_var_ref(self, node: Any, target_name: str) -> bool:
        if not isinstance(node, Tree):
            return isinstance(node, Token) and node.type == "NAME" and str(node) == target_name
        if node.data == "var_ref" and node.children:
            return str(node.children[0]) == target_name
        if node.data in ("paren_expr", "value_expr", "expr", "normal_target", "set_target") and len(node.children) == 1:
            return self._is_direct_var_ref(node.children[0], target_name)
        return False

    def _contains_var_ref(self, node: Any, target_name: str) -> bool:
        if not isinstance(node, Tree):
            return isinstance(node, Token) and node.type == "NAME" and str(node) == target_name
        if node.data == "var_ref" and node.children and str(node.children[0]) == target_name:
            return True
        return any(self._contains_var_ref(c, target_name) for c in node.children)

    def _string_cast_is_borrowed(self, node: Any) -> bool:
        """True when ``x to string`` reuses memory that ``x`` already owns.

        'string to string' is the identity (the result aliases x's buffer) and
        'bool to string' yields the static ``"true"``/``"false"`` rodata view;
        neither allocates a fresh buffer, so the result must not be auto-banished.
        Any other source (int, float, char, …) goes through
        ``pengu_string_from_*`` and produces an owned heap buffer.
        """
        if not isinstance(node, Tree) or not node.children:
            return False
        operand = node.children[0]
        op_t = getattr(operand, "_pengu_value_type", None)
        if op_t is None:
            try:
                op_t = self.inferrer.infer(operand)
            except Exception:
                op_t = None
        while isinstance(op_t, (AliasType, FrozenType, SealType)):
            nxt = getattr(op_t, "target", None) or getattr(op_t, "underlying", None)
            if nxt is None or nxt is op_t:
                break
            op_t = nxt
        return isinstance(op_t, BaseType) and op_t.name in ("string", "bool")

    def _is_fresh_heap_expr(self, expr_node: Any, eff_type: Type) -> bool:
        if not isinstance(expr_node, Tree):
            return False
        curr = expr_node
        while isinstance(curr, Tree) and curr.data in ("value_expr", "expr", "paren_expr") and len(curr.children) == 1:
            curr = curr.children[0]
        if not isinstance(curr, Tree):
            return False

        if isinstance(eff_type, (MaybeType, ResultType)) and curr.data in ("some_expr", "maybe_none", "calling_expr"):
            # A 'maybe T'/'result of T to E' box is heap-allocated by 'some'/
            # 'ok_of'/'err_of' (or handed over by a call), so the binding owns it
            # even though the expression is not a fresh string/container.
            return True

        if (isinstance(eff_type, OmenType) and eff_type.is_algebraic
                and curr.data == "struct_init"):
            # 'var e as Event is with Msg is ...' materialises the tagged struct
            # on the stack; the binding owns the payload of the active variant.
            # A fresh payload is moved in, an embedded owning local is disowned
            # by escape analysis (the documented compound-literal rule), and a
            # literal string stays a non-owning .rodata view that banish ignores.
            if not type_owns_heap(eff_type, symbols=self.symbols):
                return False
            return True

        if curr.data in ("var_ref", "field_access", "arrow_access", "at_expr", "array_at_expr", "null_lit", "none_lit", "try_expr", "or_else", "or_return", "or_block", "calling_expr"):
            # NOTE: an 'or_block' is deliberately not treated as fresh.  The ok
            # path of '(maybe T) or:' moves the payload out, so the fallback
            # decides the ownership of the result.
            return False

        if eff_type == STRING_TYPE or (isinstance(eff_type, BaseType) and eff_type.name == "string"):
            if curr.data in ("add", "binary_op"):
                return True
            if curr.data == "chr_expr":
                return True
            if curr.data in ("to_expr", "to_string_expr"):
                # 'x to string' is the identity when 'x' already is a string and
                # 'bool to string' returns the static "true"/"false" view, so
                # neither allocates.  Marking them fresh would auto-banish (and
                # free) a buffer owned elsewhere: for an owned source that is a
                # double free, for a literal it is the C1 free(.rodata) crash.
                if self._string_cast_is_borrowed(curr):
                    return False
                return True
            if curr.data == "string_lit" and curr.children:
                try:
                    from .pengu_parser import extract_string_parts
                    _, _, parts = extract_string_parts(curr.children[0])
                    if any(getattr(p, "is_expr", False) for p in parts):
                        return True
                except Exception:
                    pass
                return False
            return False

        if isinstance(eff_type, (ListType, MapType)):
            return True

        return False

    def _mentions_defer_banish(self, stmts: List[Tree], sym_name: str) -> bool:
        for s in stmts:
            if not isinstance(s, Tree):
                continue
            for d in s.iter_subtrees():
                if d.data in ("defer_stmt", "errdefer_stmt"):
                    for b in d.iter_subtrees():
                        if b.data in ("banish_expr", "banish_stmt"):
                            for vr in b.iter_subtrees():
                                if vr.data == "var_ref" and vr.children and str(vr.children[0]) == sym_name:
                                    return True
                                if isinstance(vr, Token) and vr.type == "NAME" and str(vr) == sym_name:
                                    return True
        return False

    def _mentions_set_target(self, stmts: List[Tree], sym_name: str,
                             sym_type: Type = None) -> bool:
        """True when a 'set' on ``sym_name`` stores a value the local does not own.

        Only a *borrowed* rvalue disables auto-banish.  When every assignment
        moves in a fresh value (literal, constructor, interpolation, or a call
        whose result owns memory) the local still owns its current value, so it
        may be released at scope exit; the code generator pairs that with a
        release-before-assign on each 'set', turning the old O(n) loop leak into
        O(1).  A 'set s is t' of an existing variable aliases t's buffer, so it
        must keep the local out of the auto-banish set.
        """
        for s in stmts:
            if not isinstance(s, Tree):
                continue
            for st in s.iter_subtrees():
                if st.data in ("set_stmt", "compound_set_stmt") and st.children:
                    target_node = st.children[0]
                    if not self._is_direct_var_ref(target_node, sym_name):
                        continue
                    rhs = self._set_stmt_rvalue(st)
                    # 'set s is s' is a no-op and keeps the current ownership.
                    if rhs is not None and self._is_direct_var_ref(rhs, sym_name):
                        continue
                    if rhs is None or not self._is_fresh_heap_expr(rhs, sym_type):
                        return True
        return False

    @staticmethod
    def _set_stmt_rvalue(st: Tree) -> Any:
        """Rvalue of a 'set'/'compound set' statement (None when unknown)."""
        if st.data == "set_stmt" and len(st.children) >= 2:
            return st.children[1]
        if st.data == "compound_set_stmt" and len(st.children) >= 3:
            return st.children[2]
        return None

    # Container members that are plain scalars, not views into the buffer: a
    # 'return s.len' must not keep 's' alive (that leaked the buffer).
    _SCALAR_MEMBER_NAMES = frozenset({
        "len", "length", "capacity", "cap", "size", "count", "is_present",
        "tag", "hash", "kind", "value_type",
    })

    def _is_scalar_member_access(self, node: Any) -> bool:
        """True for 'x.len'/'x.capacity'-style scalar member reads."""
        return (isinstance(node, Tree) and node.data in ("field_access", "arrow_access")
                and len(node.children) >= 2 and str(node.children[1]) in self._SCALAR_MEMBER_NAMES)

    def _block_value_node_of(self, stmts: List[Any]) -> Any:
        """Value expression of a value-position statement list (or None)."""
        if not stmts:
            return None
        last = stmts[-1]
        while (isinstance(last, Tree) and last.data in ("stmt", "simple_stmt", "block")
               and last.children):
            nxt = last.children[-1]
            if nxt is last:
                break
            last = nxt
        if not isinstance(last, Tree):
            return None
        if last.data == "expr_stmt" and last.children:
            return last.children[0]
        # A trailing value-position 'if'/'unless'/'do:'/loop *is* its own value.
        # The inferred type may not be recorded yet (a local earlier in the same
        # block is analysed before the trailing statement is checked), so the
        # rule name is enough.
        if getattr(last, "_pengu_value_type", None) is not None:
            return last
        if last.data in ("do_expr", "if_stmt", "unless_stmt",
                         "while_stmt", "for_range_stmt", "for_in_stmt"):
            return last
        return None

    def _compute_auto_banished(self, sym_name: str, eff_type: Type, expr_node: Any, is_borrowed: bool) -> bool:
        if is_borrowed:
            return False

        actual = eff_type
        while isinstance(actual, (AliasType, FrozenType)) and getattr(actual, "target", None):
            actual = actual.target

        is_banishable_type = (
            actual == STRING_TYPE or (isinstance(actual, BaseType) and actual.name == "string")
            or isinstance(actual, (ListType, MapType, MaybeType, ResultType))
            # An algebraic omen with a heap-owning variant payload has a
            # generated destructor and must be released at scope exit, exactly
            # like a list/map: without this every local 'omen Event' leaked.
            or (isinstance(actual, OmenType) and actual.is_algebraic
                and type_owns_heap(actual, symbols=self.symbols))
        )
        if not is_banishable_type:
            return False

        if not self._is_fresh_heap_expr(expr_node, actual):
            return False

        scope_stmts = self.block_stmts_stack[-1] if self.block_stmts_stack else []
        if self._mentions_defer_banish(scope_stmts, sym_name):
            return False
        if self._mentions_set_target(scope_stmts, sym_name, actual):
            return False
        prev_self_type = getattr(self, "_escape_self_type", None)
        self._escape_self_type = (sym_name, eff_type)
        try:
            if self._check_symbol_escape(sym_name, scope_stmts):
                return False
            # A local declared inside a value block ('do:'/'if:') escapes when
            # that block's own value borrows it ('var sl is do: … xs at 0 to 2'):
            # banishing it would leave the block value dangling.  The check
            # recurses through nested value blocks ('do: do: y').
            vb_stack = getattr(self, "_value_block_stack", None)
            if vb_stack and vb_stack[-1] is not None:
                if self._value_block_hands_out(vb_stack[-1], sym_name):
                    return False
        finally:
            self._escape_self_type = prev_self_type

        return True

    def _value_block_expressions(self, node: Any, _depth: int = 0) -> List[Any]:
        """Value expressions of a 'do:'/'if' block, nested blocks included."""
        if not isinstance(node, Tree) or _depth > 16:
            return []
        out: List[Any] = []
        if node.data == "do_expr":
            v = self._block_value_node_of([c for c in node.children if isinstance(c, Tree)])
            if v is not None:
                out.append(v)
        elif node.data in ("if_stmt", "unless_stmt"):
            # Value position is guaranteed by the caller (the expression would
            # not be translated otherwise); the recorded type may not exist yet.
            for branch in node.children[1:]:
                if not isinstance(branch, Tree):
                    continue
                if branch.data in ("block", "else_block", "when_else_plain", "when_else_when"):
                    v = self._block_value_node_of([c for c in branch.children if isinstance(c, Tree)])
                else:
                    v = self._block_value_node_of([branch])
                if v is not None:
                    out.append(v)
        else:
            return []
        for sub in list(out):
            if (isinstance(sub, Tree) and sub.data in ("do_expr", "if_stmt", "unless_stmt")
                    and getattr(sub, "_pengu_value_type", None) is not None):
                out.extend(self._value_block_expressions(sub, _depth + 1))
        return out

    def _value_block_hands_out(self, stmts_or_node: Any, sym_name: str) -> bool:
        """True when a value block hands ``sym_name``'s storage to its consumer."""
        if isinstance(stmts_or_node, list):
            value = self._block_value_node_of(stmts_or_node)
            nodes: List[Any] = [value] if value is not None else []
        else:
            nodes = [stmts_or_node]
        # Flatten nested value blocks ('do: do: y', value-'if' branches): their
        # value is what the enclosing expression finally consumes.
        candidates: List[Any] = []
        for n in nodes:
            candidates.append(n)
            if isinstance(n, Tree) and n.data in ("do_expr", "if_stmt", "unless_stmt"):
                candidates.extend(self._value_block_expressions(n))
        for sub in candidates:
            un = sub
            while (isinstance(un, Tree) and un.data in ("paren_expr", "value_expr", "expr")
                   and len(un.children) == 1):
                un = un.children[0]
            if self._is_direct_var_ref(un, sym_name):
                return True
            if (isinstance(un, Tree) and un.data in (
                    "at_expr", "array_at_expr", "slice_at_expr", "bytes_expr",
                    "field_access", "arrow_access", "self_arrow", "essence_of")
                    and not self._is_scalar_member_access(un)
                    and self._contains_var_ref(un, sym_name)):
                return True
        return False

    def _check_var_decl(self, node: Tree) -> None:
        """Checks local mutable variable declaration for type validity and folds constants.

        Args:
            node: AST Tree for var declaration.
        """
        line, col = self._get_loc(node)
        is_borrowed, name_idx = _has_borrowed_modifier(node)
        v_name = str(node.children[name_idx])
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
        if v_name != "_":
            existing = self.symbols.lookup_local(v_name) if self.symbols else None
            if existing is not None:
                self._record_error(self._make_error(
                    SemanticError,
                    f"Redefinition of '{v_name}' in the same scope",
                    node,
                    code="E0053",
                    help=f"Use 'set {v_name} is ...' to reassign, or use a distinct name.",
                    note=f"'{v_name}' was previously declared on line {existing.line}."
                ))
                return
            outer = self.symbols.lookup(v_name) if self.symbols else None
            if outer is not None and getattr(outer, "kind", "") in ("weave", "declare", "function"):
                self.warnings.append(f"[W0005] Variable '{v_name}' shadows global function '{v_name}' on line {line}")
        v_type = None
        type_node, v_expr = _decl_layout(node)
        if type_node is not None:
            self._validate_type_node(type_node)
            v_type = ast_to_type(type_node, self.symbols.lookup_type)

        # Block values nested in the initializer (call arguments, struct-literal
        # fields, …) are value-checked before inference.
        if not (isinstance(v_expr, Tree) and v_expr.data == "with_init_expr"):
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
            # A bare 'T: …' annotation only accepts bound-satisfying values
            # ('BaseType.is_compatible(TypeParam)' is a wildcard).
            if isinstance(v_type, TypeParam) and not self._typeparam_accepts_value(v_type, inferred):
                raise self._make_error(
                    TypeMismatchError,
                    f"Cannot initialize '{v_name}' of type '{v_type.name}' (bound: "
                    f"{', '.join(v_type.bounds)}) with a value of type '{inferred}'",
                    v_expr,
                    code="E0005",
                    help=f"Use a value satisfying 'where {v_type.name}: {', '.join(v_type.bounds)}'.",
                    note="A bounded type parameter only accepts values implementing its concepts."
                )
            eff_type = v_type or inferred

            if self._is_void_type_name(eff_type):
                raise self._make_error(
                    TypeMismatchError,
                    f"Variable '{v_name}' cannot be bound to a 'void' value",
                    node,
                    code="E0005",
                    help="A 'void' expression has no value; call it as a statement.",
                    note="Only expressions with a value can initialize a variable."
                )

            if self._has_unknown_array_dim(eff_type):
                raise self._make_error(
                    UnknownArrayDimensionError,
                    f"Unknown array dimension in '{eff_type}' for variable '{v_name}'",
                    node,
                    code="E0015",
                    help="Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.",
                    note="C requires fixed array sizes for all dimensions."
                )

            if isinstance(eff_type, ArrayType) and isinstance(v_expr, Tree):
                self._validate_array_literal_size(eff_type, v_expr)

            if (v_type is not None and not inferred.is_compatible(v_type)
                    and not self._accepts_string_omen_variant(inferred, v_type)):
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
            is_auto = self._compute_auto_banished(v_name, eff_type, v_expr, is_borrowed)
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
                file_path=self.filename,
                is_borrowed=is_borrowed,
                is_auto_banished=is_auto,
            )
            self.symbols.define(sym)
            node._pengu_symbol = sym
        except SemanticError as e:
            self._record_error(e)

    @staticmethod
    def _accepts_string_omen_variant(inferred: Type, declared: Type) -> bool:
        """True when a string-valued omen variant view initializes that omen type.

        Variants of an 'omen X with string' are typed as 'frozen string' because
        they are non-owning .rodata views that must not be banished (roadmap
        0.3 / C5), but an explicitly omen-typed binding still accepts one:
        'var m as HttpMethod is HttpMethod.Get' is a valid HttpMethod value.
        """
        def _unwrap(t: Any) -> Any:
            u = t
            while isinstance(u, (AliasType, FrozenType, SealType)):
                nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
                if nxt is None or nxt is u:
                    break
                u = nxt
            return u
        d = _unwrap(declared)
        if not (isinstance(d, OmenType) and getattr(d, "is_string_valued", False)):
            return False
        i = _unwrap(inferred)
        return isinstance(i, BaseType) and i.name == "string"

    @staticmethod
    def _is_void_type_name(t: Any) -> bool:
        """True when a resolved binding type is exactly 'void'."""
        if t is None or isinstance(t, AnyType):
            return False
        if t is VOID_TYPE:
            return True
        return str(getattr(t, "name", "")) == "void"

    @staticmethod
    def _clone_capable_type(t: Any) -> bool:
        """True when the value generator can deep-copy a value of this type.

        Mirrors the code generator's ``_element_clone_fn``: such a value may be
        copied into a 'some' box (or a container) without aliasing the source.
        """
        u = t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
            if nxt is None or nxt is u:
                break
            u = nxt
        if isinstance(u, BaseType) and u.name == "string":
            return True
        if isinstance(u, (ListType, MapType)):
            return True
        if isinstance(u, RuneType):
            return "Imago" in list(getattr(u, "derived_concepts", []) or [])
        return False

    def _some_payload_type(self, node: Any, parent: Any = None,
                           grandparent: Any = None) -> Optional[Type]:
        """Payload type of a 'some expr' node (inference, else its annotation).

        The escape analysis for a local may run before the binding that boxes it
        is declared, so the declared 'maybe T' of the enclosing declaration is
        used as a fallback.
        """
        if not (isinstance(node, Tree) and node.data == "some_expr" and node.children):
            return None
        payload_t: Optional[Type] = None
        try:
            payload_t = self.inferrer.infer(node.children[0])
        except Exception:
            payload_t = None
        if payload_t is None or isinstance(payload_t, AnyType):
            for anc in (parent, grandparent):
                if not (isinstance(anc, Tree) and anc.data in ("var_decl", "let_decl")):
                    continue
                try:
                    tnode, _v = _decl_layout(anc)
                    decl_t = (ast_to_type(tnode, self.symbols.lookup_type)
                              if tnode is not None else None)
                except Exception:
                    decl_t = None
                if isinstance(decl_t, MaybeType):
                    payload_t = decl_t.element
                break
        if payload_t is None or isinstance(payload_t, AnyType):
            # 'return some s' (or a value block): the enclosing signature carries
            # the box type, and the local being analysed may not be in the symbol
            # table yet (its own declaration is still being checked).
            try:
                ret_t = self.symbols.current_return_type()
            except Exception:
                ret_t = None
            if isinstance(ret_t, MaybeType):
                payload_t = ret_t.element
        return payload_t

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
        type_node, v_expr = decl_layout(node)
        if type_node is not None:
            self._validate_type_node(type_node)
            v_type = ast_to_type(type_node, self.symbols.lookup_type)

        # 'static var x is if/unless/for ...:' or block values nested in the
        # initializer (e.g. inside a struct literal) — positional value check.
        if not (isinstance(v_expr, Tree) and v_expr.data == "with_init_expr"):
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
            if self._is_void_type_name(eff_type):
                raise self._make_error(
                    TypeMismatchError,
                    f"Static variable '{v_name}' cannot be bound to a 'void' value",
                    node,
                    code="E0005",
                    help="A 'void' expression has no value.",
                    note="Only expressions with a value can initialize a variable."
                )
            if isinstance(eff_type, ArrayType):
                raise self._make_error(
                    SemanticError,
                    f"Static variable '{v_name}' cannot have an array type ('{eff_type}')",
                    node,
                    code="E0055",
                    help="Use a pointer, rune, list, or map type for function-static variables.",
                    note="C arrays cannot be assigned at runtime, so array statics are not supported."
                )
            if (v_type is not None and not inferred.is_compatible(v_type)
                    and not self._accepts_string_omen_variant(inferred, v_type)):
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
            # The enclosing weave pops its scope before code generation, so the
            # symbol must travel on the node (as 'var'/'let' already do).
            node._pengu_symbol = sym
        except SemanticError as e:
            self._record_error(e)

    def _check_let_decl(self, node: Tree) -> None:
        """Checks immutable let binding declaration, supports destructuring.

        Args:
            node: AST Tree for let declaration.
        """
        line, col = self._get_loc(node)
        is_borrowed, name_idx = _has_borrowed_modifier(node)
        names_node = node.children[name_idx]
        names: List[str] = [str(c) for c in names_node.children] if isinstance(names_node, Tree) else [str(names_node)]
        seen_in_decl = set()
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
            if nm != "_":
                if nm in seen_in_decl:
                    self._record_error(self._make_error(
                        SemanticError,
                        f"Duplicate binding name '{nm}' in destructuring",
                        node,
                        code="E0053",
                        help="Use distinct variable names for each destructured element."
                    ))
                    return
                seen_in_decl.add(nm)
                existing = self.symbols.lookup_local(nm) if self.symbols else None
                if existing is not None:
                    self._record_error(self._make_error(
                        SemanticError,
                        f"Redefinition of '{nm}' in the same scope",
                        node,
                        code="E0053",
                        help=f"Use a distinct name for this binding.",
                        note=f"'{nm}' was previously declared on line {existing.line}."
                    ))
                    return
                outer = self.symbols.lookup(nm) if self.symbols else None
                if outer is not None and getattr(outer, "kind", "") in ("weave", "declare", "function"):
                    self.warnings.append(f"[W0005] Variable '{nm}' shadows global function '{nm}' on line {line}")
        l_type = None
        type_node, l_expr = _decl_layout(node)
        if type_node is not None:
            self._validate_type_node(type_node)
            l_type = ast_to_type(type_node, self.symbols.lookup_type)

        if not (isinstance(l_expr, Tree) and l_expr.data == "with_init_expr"):
            self._check_value_exprs(l_expr, l_type)
        try:
            inferred = self.inferrer.infer(l_expr, expected_type=l_type)
            folded_val = self.const_folder.fold(l_expr)
            doc = self._extract_preceding_doc(line)

            if isinstance(l_type, TypeParam) and not self._typeparam_accepts_value(l_type, inferred):
                raise self._make_error(
                    TypeMismatchError,
                    f"Cannot initialize a binding of type '{l_type.name}' (bound: "
                    f"{', '.join(l_type.bounds)}) with a value of type '{inferred}'",
                    l_expr,
                    code="E0005",
                    help=f"Use a value satisfying 'where {l_type.name}: {', '.join(l_type.bounds)}'.",
                    note="A bounded type parameter only accepts values implementing its concepts."
                )

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

                if self._is_void_type_name(eff_type):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Binding '{v_name}' cannot be bound to a 'void' value",
                        node,
                        code="E0005",
                        help="A 'void' expression has no value; call it as a statement.",
                        note="Only expressions with a value can initialize a binding."
                    )

                if self._has_unknown_array_dim(eff_type):
                    raise self._make_error(
                        UnknownArrayDimensionError,
                        f"Unknown array dimension in '{eff_type}' for binding '{v_name}'",
                        node,
                        code="E0015",
                        help="Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.",
                        note="C requires fixed array sizes for all dimensions."
                    )

                if isinstance(eff_type, ArrayType) and isinstance(l_expr, Tree):
                    self._validate_array_literal_size(eff_type, l_expr)

                if (l_type is not None and not inferred.is_compatible(l_type)
                        and not self._accepts_string_omen_variant(inferred, l_type)):
                    err = self._make_type_mismatch_error(
                        expected_type=l_type,
                        found_type=inferred,
                        node=l_expr,
                        custom_message=f"Immutable binding '{v_name}' declared as '{l_type}', but initialized with '{inferred}'",
                        note="Immutable bindings must match their declared type."
                    )
                    self._record_error(err)
                is_auto = self._compute_auto_banished(v_name, eff_type, l_expr, is_borrowed)
                sym = Symbol(
                    name=v_name,
                    type=eff_type,
                    kind="let",
                    is_mutable=False,
                    is_stack_alloc=isinstance(eff_type, RuneType),
                    const_val=folded_val,
                    line=line,
                    column=col,
                    doc=doc,
                    file_path=self.filename,
                    is_borrowed=is_borrowed,
                    is_auto_banished=is_auto,
                )
                self.symbols.define(sym)
                node._pengu_symbol = sym
            else:
                # Destructuring: let x, y is my_vec or let a, b is arr
                destructured_syms = []
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
                        sym = Symbol(name=v_name, type=f_type, kind="let", is_mutable=False, line=line, column=col, doc=doc, file_path=self.filename, is_borrowed=is_borrowed)
                        self.symbols.define(sym)
                        destructured_syms.append(sym)
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
                        sym = Symbol(name=v_name, type=elem_t, kind="let", is_mutable=False, line=line, column=col, file_path=self.filename, is_borrowed=is_borrowed)
                        self.symbols.define(sym)
                        destructured_syms.append(sym)
                elif isinstance(inferred, (SliceType, ListType)):
                    elem_t = inferred.element
                    for v_name in names:
                        sym = Symbol(name=v_name, type=elem_t, kind="let", is_mutable=False, line=line, column=col, file_path=self.filename, is_borrowed=is_borrowed)
                        self.symbols.define(sym)
                        destructured_syms.append(sym)
                else:
                    raise self._make_error(
                        SemanticError,
                        f"Type '{inferred}' does not support destructuring",
                        node,
                        code="E0017",
                        help="Destructuring is only supported on runes, fixed arrays, slices, and lists.",
                        note="Destructuring unpacks fields or elements into individual bindings."
                    )
                node._pengu_symbols = destructured_syms
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
        through = len(node.children) > 1 or node.data == "with_target"
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

        curr = base_t
        while isinstance(curr, (AliasType, RefType)):
            curr = getattr(curr, "target", None)
            if isinstance(curr, FrozenType):
                return f"'{base_t}'"
        if isinstance(base_t, FrozenType):
            return f"'{base_t}'"
        return None

    def _typeparam_accepts_value(self, tp: TypeParam, val_t: Optional[Type]) -> bool:
        """True when ``val_t`` may be assigned to a bare type-parameter target.

        A ``TypeParam`` is a wildcard for the *value* direction
        (``BaseType.is_compatible(TypeParam)`` is always True), so the bounds
        have to be enforced explicitly here: nothing but a bound-satisfying value
        can flow into ``T: Num``.  Unbounded parameters stay fully permissive and
        ``any``/``null``/another parameter are accepted (they are resolved later).
        """
        return typeparam_accepts_value(tp, val_t, self.symbols)

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
                curr_frozen = with_t
                is_frozen_with = False
                while isinstance(curr_frozen, (AliasType, RefType)):
                    curr_frozen = getattr(curr_frozen, "target", None)
                    if isinstance(curr_frozen, FrozenType):
                        is_frozen_with = True
                        break
                if isinstance(with_t, FrozenType):
                    is_frozen_with = True
                if is_frozen_with:
                    raise self._make_error(
                        MutabilityError,
                        f"Cannot mutate field '.{field_name}' on frozen target '{with_t}' in 'with'",
                        target_node,
                        code="E0006",
                        help="The receiver passed to 'with' is frozen and cannot be modified.",
                        note="'frozen' values are read-only."
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
                while isinstance(with_t, (RefType, AliasType, FrozenType, SealType)):
                    with_t = getattr(with_t, "target", None) or getattr(with_t, "underlying", None)
                if isinstance(with_t, (RuneType, EchoType)):
                    if field_name.startswith("_"):
                        is_enchanting = (
                            self.symbols.is_in_enchanting()
                            and self.symbols.current_enchanting_type() == with_t
                        )
                        is_module_owner = (
                            hasattr(with_t, "module")
                            and with_t.module == getattr(self.symbols, "current_module", None)
                        )
                        if not (is_enchanting or is_module_owner):
                            raise self._make_error(
                                PrivateSymbolAccessError,
                                f"Field '{field_name}' is private to rune '{with_t.name}'",
                                target_node,
                                code="E0043",
                                help=f"Field '{field_name}' is private to rune '{with_t.name}'.",
                                note="Fields starting with '_' cannot be accessed from outside their rune."
                            )
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
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            sub_f = str(acc.children[0])
                            if acc.data == "dot_access" and isinstance(target_type, RefType):
                                raise self._make_error(
                                    SelfDotAccessError,
                                    "Reference must be accessed with '->', not '.'",
                                    acc,
                                    code="E0003",
                                    help="Change '.' to '->' when accessing fields on a reference.",
                                    note="References (ref to T) require arrow operator '->' for field access."
                                )
                            if acc.data == "arrow_access" and not isinstance(target_type, RefType):
                                raise self._make_error(
                                    SemanticError,
                                    "Cannot use '->' on non-reference",
                                    acc,
                                    code="E0003",
                                )
                            curr_t = target_type.target if isinstance(target_type, RefType) else target_type
                            while isinstance(curr_t, (RefType, AliasType, FrozenType, SealType)):
                                curr_t = getattr(curr_t, "target", None) or getattr(curr_t, "underlying", None)
                            if isinstance(curr_t, (RuneType, EchoType)):
                                if sub_f.startswith("_"):
                                    is_enchanting = (
                                        self.symbols.is_in_enchanting()
                                        and self.symbols.current_enchanting_type() == curr_t
                                    )
                                    is_module_owner = (
                                        hasattr(curr_t, "module")
                                        and curr_t.module == getattr(self.symbols, "current_module", None)
                                    )
                                    if not (is_enchanting or is_module_owner):
                                        raise self._make_error(
                                            PrivateSymbolAccessError,
                                            f"Field '{sub_f}' is private to rune '{curr_t.name}'",
                                            acc,
                                            code="E0043",
                                            help=f"Field '{sub_f}' is private to rune '{curr_t.name}'.",
                                            note="Fields starting with '_' cannot be accessed from outside their rune."
                                        )
                                if sub_f not in curr_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{curr_t.name}' has no field '{sub_f}'",
                                        acc,
                                        code="E0013",
                                    )
                                target_type = curr_t.fields[sub_f]
                            else:
                                raise self._make_error(
                                    SemanticError,
                                    f"Type '{curr_t}' has no field '{sub_f}'",
                                    acc,
                                    code="E0013",
                                )
                        elif isinstance(acc, Tree) and acc.data == "at_access":
                            if isinstance(target_type, RefType):
                                unwrapped_tgt = target_type.target
                                is_ptr_tgt_frozen = False
                                while isinstance(unwrapped_tgt, (AliasType, FrozenType)):
                                    if isinstance(unwrapped_tgt, FrozenType):
                                        is_ptr_tgt_frozen = True
                                    unwrapped_tgt = unwrapped_tgt.target
                                if is_ptr_tgt_frozen or isinstance(target_type, FrozenType):
                                    raise self._make_error(
                                        MutabilityError,
                                        f"Cannot mutate element through pointer to frozen type '{target_type}'",
                                        acc,
                                        code="E0006",
                                        help="Drop 'frozen' from the pointee type to allow mutation.",
                                        note="'ref to frozen T' guarantees pointee immutability."
                                    )
                                if isinstance(unwrapped_tgt, (ArrayType, SliceType, ManyType, ListType)):
                                    target_type = unwrapped_tgt.element
                                elif isinstance(unwrapped_tgt, MapType):
                                    target_type = unwrapped_tgt.value
                                else:
                                    target_type = unwrapped_tgt
                            else:
                                curr_t = target_type
                                is_coll_frozen = False
                                while isinstance(curr_t, (AliasType, FrozenType)):
                                    if isinstance(curr_t, FrozenType):
                                        is_coll_frozen = True
                                    curr_t = curr_t.target
                                if is_coll_frozen:
                                    raise self._make_error(
                                        MutabilityError,
                                        f"Cannot mutate element of frozen collection '{target_type}'",
                                        acc,
                                        code="E0006",
                                        help="Frozen collections cannot be modified.",
                                        note="'frozen' types guarantee const-correctness."
                                    )
                                if curr_t == STRING_TYPE or (isinstance(curr_t, BaseType) and curr_t.name == "string"):
                                    raise self._make_error(
                                        InvalidMemoryOpError,
                                        "Cannot modify characters in an immutable string directly",
                                        acc,
                                        code="E0006",
                                        help="Strings in PenguScript are immutable. Create a new string with string operations instead.",
                                        note="String characters cannot be assigned to directly."
                                    )
                                if isinstance(curr_t, AnyType):
                                    target_type = AnyType()
                                elif hasattr(curr_t, "element"):
                                    target_type = curr_t.element
                                elif hasattr(curr_t, "value"):
                                    target_type = curr_t.value
                                else:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Cannot index non-indexable type '{curr_t}'",
                                        acc,
                                        code="E0005",
                                    )
                else:
                    raise self._make_error(
                        SemanticError,
                        f"Type '{with_t}' has no field '{field_name}'",
                        target_node,
                        code="E0013",
                    )

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
                    ench_t = self.symbols.current_enchanting_type()
                    curr_chk_t = RefType(ench_t) if ench_t else AnyType()

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
                            curr_chk_t = with_t.fields[first_str]
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
                        curr_chk_t = sym.type
                        # Remember the binding for codegen: release-before-assign
                        # only fires for a local the checker proved auto-banished
                        # (never aliased/escaped).
                        node._pengu_set_var_symbol = sym
                    else:
                        first_acc = target_node.children[1]
                        if isinstance(first_acc, Tree) and first_acc.data in ("dot_access", "at_access"):
                            if not sym.is_mutable and not isinstance(sym.type, RefType):
                                what = "element" if first_acc.data == "at_access" else "field"
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate {what} of immutable 'let' variable '{first_str}'",
                                    target_node,
                                    code="E0006",
                                    help=f"Change 'let {first_str}' to 'var {first_str}' to allow {what} mutation.",
                                    note=f"{what.capitalize()}s of 'let' bindings cannot be modified."
                                )
                        curr_chk_t = sym.type

                if len(target_node.children) > 1:
                    for acc in target_node.children[1:]:
                        if isinstance(acc, Tree) and acc.data == "at_access":
                            if isinstance(curr_chk_t, RefType):
                                unwrapped_tgt = curr_chk_t.target
                                is_ptr_tgt_frozen = False
                                while isinstance(unwrapped_tgt, (AliasType, FrozenType)):
                                    if isinstance(unwrapped_tgt, FrozenType):
                                        is_ptr_tgt_frozen = True
                                    unwrapped_tgt = unwrapped_tgt.target
                                if is_ptr_tgt_frozen or isinstance(curr_chk_t, FrozenType):
                                    raise self._make_error(
                                        MutabilityError,
                                        f"Cannot mutate element through pointer to frozen type '{curr_chk_t}'",
                                        acc,
                                        code="E0006",
                                        help="Drop 'frozen' from the pointee type to allow mutation.",
                                        note="'ref to frozen T' guarantees pointee immutability."
                                    )
                                if isinstance(unwrapped_tgt, (ArrayType, SliceType, ManyType, ListType)):
                                    curr_chk_t = unwrapped_tgt.element
                                elif isinstance(unwrapped_tgt, MapType):
                                    curr_chk_t = unwrapped_tgt.value
                                else:
                                    curr_chk_t = unwrapped_tgt
                            else:
                                is_coll_frozen = False
                                unwrapped_t = curr_chk_t
                                while isinstance(unwrapped_t, (AliasType, FrozenType)):
                                    if isinstance(unwrapped_t, FrozenType):
                                        is_coll_frozen = True
                                    unwrapped_t = unwrapped_t.target
                                if is_coll_frozen:
                                    raise self._make_error(
                                        MutabilityError,
                                        f"Cannot mutate element of frozen collection '{curr_chk_t}'",
                                        acc,
                                        code="E0006",
                                        help="Frozen collections cannot be modified.",
                                        note="'frozen' types guarantee const-correctness."
                                    )
                                if unwrapped_t == STRING_TYPE or (isinstance(unwrapped_t, BaseType) and unwrapped_t.name == "string"):
                                    raise self._make_error(
                                        InvalidMemoryOpError,
                                        "Cannot modify characters in an immutable string directly",
                                        acc,
                                        code="E0006",
                                        help="Strings in PenguScript are immutable. Create a new string with string operations instead.",
                                        note="String characters cannot be assigned to directly."
                                    )
                                if isinstance(unwrapped_t, AnyType):
                                    curr_chk_t = AnyType()
                                elif hasattr(unwrapped_t, "element"):
                                    curr_chk_t = unwrapped_t.element
                                elif hasattr(unwrapped_t, "value"):
                                    curr_chk_t = unwrapped_t.value
                                else:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Cannot index non-indexable type '{unwrapped_t}'",
                                        acc,
                                        code="E0005",
                                    )
                        elif isinstance(acc, Tree) and acc.data in ("dot_access", "arrow_access") and acc.children:
                            fname = str(acc.children[0])
                            if acc.data == "dot_access" and isinstance(curr_chk_t, RefType):
                                raise self._make_error(
                                    SelfDotAccessError,
                                    "Reference must be accessed with '->', not '.'",
                                    acc,
                                    code="E0003",
                                    help="Change '.' to '->' when accessing fields on a reference.",
                                    note="References (ref to T) require arrow operator '->' for field access."
                                )
                            if acc.data == "arrow_access" and not isinstance(curr_chk_t, RefType):
                                raise self._make_error(
                                    SemanticError,
                                    "Cannot use '->' on non-reference",
                                    acc,
                                    code="E0003",
                                )
                            unwrapped_t = curr_chk_t.target if isinstance(curr_chk_t, RefType) else curr_chk_t
                            is_struct_frozen = isinstance(curr_chk_t, FrozenType)
                            while isinstance(unwrapped_t, (AliasType, FrozenType, SealType)):
                                if isinstance(unwrapped_t, FrozenType):
                                    is_struct_frozen = True
                                unwrapped_t = getattr(unwrapped_t, "target", None) or getattr(unwrapped_t, "underlying", None)
                            if is_struct_frozen:
                                raise self._make_error(
                                    MutabilityError,
                                    f"Cannot mutate field of frozen value '{curr_chk_t}'",
                                    acc,
                                    code="E0006",
                                    help="Drop 'frozen' from the declaration to allow field mutation.",
                                    note="'frozen' types guarantee const-correctness."
                                )
                            if isinstance(unwrapped_t, AnyType):
                                curr_chk_t = AnyType()
                            elif isinstance(unwrapped_t, (RuneType, EchoType)):
                                if fname.startswith("_"):
                                    is_enchanting = (
                                        self.symbols.is_in_enchanting()
                                        and self.symbols.current_enchanting_type() == unwrapped_t
                                    )
                                    is_module_owner = (
                                        hasattr(unwrapped_t, "module")
                                        and unwrapped_t.module == getattr(self.symbols, "current_module", None)
                                    )
                                    if not (is_enchanting or is_module_owner):
                                        raise self._make_error(
                                            PrivateSymbolAccessError,
                                            f"Field '{fname}' is private to rune '{unwrapped_t.name}'",
                                            acc,
                                            code="E0043",
                                            help=f"Field '{fname}' is private to rune '{unwrapped_t.name}'.",
                                            note="Fields starting with '_' cannot be accessed from outside their rune."
                                        )
                                if fname not in unwrapped_t.fields:
                                    raise self._make_error(
                                        SemanticError,
                                        f"Rune '{unwrapped_t.name}' has no field '{fname}'",
                                        acc,
                                        code="E0013",
                                        help=f"Check field spelling or verify the definition of rune '{unwrapped_t.name}'.",
                                        note=f"Rune '{unwrapped_t.name}' only exposes its declared fields."
                                    )
                                curr_chk_t = unwrapped_t.fields[fname]
                            else:
                                raise self._make_error(
                                    SemanticError,
                                    f"Type '{unwrapped_t}' has no field '{fname}'",
                                    acc,
                                    code="E0013",
                                )
                try:
                    target_type = self.inferrer.infer(target_node)
                except Exception:
                    target_type = curr_chk_t

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

            unwrapped_arr_t = target_type
            while isinstance(unwrapped_arr_t, (AliasType, FrozenType)) and getattr(unwrapped_arr_t, "target", None):
                unwrapped_arr_t = unwrapped_arr_t.target
            if isinstance(unwrapped_arr_t, ArrayType):
                raise self._make_error(
                    SemanticError,
                    f"Cannot assign directly to array type '{target_type}'",
                    node,
                    code="E0008",
                    help="Fixed-size arrays cannot be reassigned as a whole; use 'set arr at index is val' to update element-wise.",
                    note="Arrays have fixed storage and do not support whole-array reassignment."
                )

            # 'set x is if/unless/for ...:' and any block value nested in the
            # expression (e.g. inside a struct literal). The target type is the
            # expected type, so a nested 'with:' builder is typed from it.
            self._check_value_exprs(val_expr, target_type)

            val_type = self.inferrer.infer(val_expr, expected_type=target_type)

            if is_compound:
                # Operator-specific type rules for 'set TARGET OP VALUE'.
                if compound_op == "+=" and target_type.is_string() and not isinstance(target_type, SealType):
                    # String composition has exactly one spelling: '{expr}'
                    # interpolation.  '+=' is numeric-only (and '&='/'|='/'^='
                    # '/<<='/'>>=' are integer-only).
                    raise self._make_error(
                        TypeMismatchError,
                        "Cannot concatenate strings with '+='",
                        node,
                        code="E0005",
                        help='Rebind with interpolation: set s is "{s}{more}".',
                        note="PenguScript composes strings only via '{expr}' inside a "
                             "string literal; '+=' only accumulates numbers."
                    )
                elif compound_op == "%=":
                    # '%' is integer-only (same rule as the binary operator), so
                    # 'f %= 2.0' on a float must not reach the C compiler.
                    for t, side in ((target_type, "target"), (val_type, "value")):
                        if not t.is_int() and not isinstance(t, AnyType):
                            raise self._make_error(
                                TypeMismatchError,
                                f"Compound '%=' requires integers, got '{t}' for the {side}",
                                node,
                                code="E0005",
                                help="Use '%=' on integers; use '/' for floats.",
                                note="'%' (and '%=') only accept integer operands, as in C."
                            )
                elif compound_op in ("+=", "-=", "*=", "/="):
                    if not target_type.is_numeric() and not isinstance(target_type, AnyType):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Compound '{compound_op}' requires a numeric target, "
                            f"got '{target_type}'",
                            node,
                            code="E0005",
                            help="Use '+=' on numbers; for integers use '&='/'|='/'^='; "
                                 "build strings with interpolation.",
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

            # A bare type-parameter target must respect its own bounds: a
            # 'string' is not assignable to 'T: Num', even though
            # 'string.is_compatible(T)' returns True (TypeParam is a wildcard
            # for the value direction only).  Unbounded parameters keep the
            # permissive, backwards-compatible behaviour.
            unwrapped_tgt = target_type
            while isinstance(unwrapped_tgt, (AliasType, FrozenType, SealType)):
                unwrapped_tgt = getattr(unwrapped_tgt, "target", None) or getattr(unwrapped_tgt, "underlying", None)
            if isinstance(unwrapped_tgt, TypeParam) and not self._typeparam_accepts_value(unwrapped_tgt, val_type):
                offending = next(
                    (b for b in unwrapped_tgt.bounds if not implements_concept(val_type, b, self.symbols)),
                    unwrapped_tgt.bounds[0],
                )
                raise self._make_error(
                    TypeMismatchError,
                    f"Cannot assign value of type '{val_type}' to target of type "
                    f"'{unwrapped_tgt.name}' (bound: {', '.join(unwrapped_tgt.bounds)})",
                    node,
                    code="E0005",
                    help=f"'{val_type}' does not satisfy bound '{offending}'. "
                         f"Assign a value whose type implements all bounds.",
                    note="A type parameter accepts only values that implement its bounds."
                )

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

    # Type node rules that name a concrete/parameterised type.
    _TYPE_NODE_RULES = frozenset({
        "base_type", "custom_type", "ref_type", "array_type", "slice_type",
        "list_type", "map_type", "maybe_type", "result_type", "opaque_type",
        "fn_type", "frozen_type", "alias_type",
    })

    def _validate_declared_types(self, tree: Tree) -> None:
        """Validates type nodes in signatures and composite-type fields.

        ``_validate_type_node`` was only reached from var/let declarations, so a
        misspelled type in a parameter, return type, rune/echo field or declare
        signature reached the C compiler as an undeclared identifier.
        Generic declarations are skipped: their ``shard`` parameters are only in
        scope inside the declaration itself.
        """
        if self.filename and self.filename.endswith(".d.pengu"):
            return
        has_includes = bool(getattr(self.symbols, "includes", None))
        decl_rules = ("rune_decl", "echo_decl", "omen_decl", "declare_stmt", "weave_decl", "concept_decl")
        field_rules = ("field_decl", "param", "omen_field")
        generic_rules = decl_rules + ("enchanting_decl", "enchanting_stmt", "bind_decl")

        def walk(node: Any, generic_ctx: bool) -> None:
            if not isinstance(node, Tree):
                return
            if node.data in ("enchanting_decl", "enchanting_stmt"):
                # Only a *generic* enchanting block (shard params or a target
                # such as 'Box of T') brings implicit type parameters; a concrete
                # 'enchanting Player:' must still validate its signatures.
                if any(isinstance(c, Tree) and c.data == "shard_params" for c in node.children):
                    generic_ctx = True
                else:
                    target = node.children[0] if node.children else None
                    if isinstance(target, Tree):
                        # 'enchanting list of shard T:' inlines the parameter in
                        # the target type instead of a sibling 'shard_params'.
                        if any(sub.data in ("shard_param_ref", "shard_params")
                               for sub in target.iter_subtrees()):
                            generic_ctx = True
                        elif any(c is not None for c in target.children[1:]):
                            generic_ctx = True
                        else:
                            first = target.children[0]
                            base_n = (str(first.children[0]) if isinstance(first, Tree) and first.children
                                      else str(first))
                            if base_n in (self.symbols.generic_runes or {}) or \
                               base_n in (self.symbols.generic_echos or {}) or \
                               base_n in (self.symbols.generic_omens or {}) or \
                               base_n in (self.symbols.generic_aliases or {}):
                                generic_ctx = True
            elif node.data in generic_rules:
                if any(isinstance(c, Tree) and c.data == "shard_params" for c in node.children):
                    generic_ctx = True
            if node.data in decl_rules and not generic_ctx:
                for sub in node.iter_subtrees():
                    if isinstance(sub, Tree) and sub.data in field_rules:
                        for child in sub.children:
                            if isinstance(child, Tree) and child.data in self._TYPE_NODE_RULES:
                                if has_includes and self._type_node_looks_like_c(child):
                                    continue
                                self._validate_type_node(child)
                for child in node.children:
                    if isinstance(child, Tree) and child.data in self._TYPE_NODE_RULES:
                        if has_includes and self._type_node_looks_like_c(child):
                            continue
                        self._validate_type_node(child)
            for child in node.children:
                walk(child, generic_ctx)

        walk(tree, False)

    # C typedefs that hand-written bindings use in signatures but that the
    # PenguScript symbol table cannot know about.
    _C_TYPEDEF_NAMES = frozenset({
        "va_list", "jmp_buf", "sigjmp_buf", "fpos_t", "wint_t", "locale_t",
        "sigset_t", "stack_t", "ucontext_t", "pthread_t", "socklen_t",
        "off_t", "pid_t", "uid_t", "gid_t", "mode_t", "dev_t", "ino_t",
        "nlink_t", "blksize_t", "blkcnt_t", "clock_t", "time_t", "tm",
    })

    def _looks_like_c_type(self, name: str) -> bool:
        """Heuristic for names that come from an included C header."""
        if not name:
            return False
        if name in self._C_TYPEDEF_NAMES:
            return True
        if name.startswith("_") or name.isupper():
            return True
        if name.endswith("_t") or name.endswith("_T"):
            return True
        return False

    def _type_node_looks_like_c(self, type_node: Any) -> bool:
        """True when every name in a type node looks like a C header typedef.

        Files that ``include`` a header may name C-only types in signatures, so
        those are not validated; a PenguScript-looking typo still is.
        """
        if not isinstance(type_node, Tree):
            return False
        names = [str(tok) for tok in type_node.scan_values(
            lambda v: isinstance(v, Token) and v.type == "NAME")]
        if not names:
            return False
        return all(self._looks_like_c_type(n) for n in names)

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
                lookup_t = self.symbols.lookup_type(t_name) if hasattr(self.symbols, "lookup_type") else None
                is_generic = (t_name in self.symbols.generic_runes or 
                              t_name in self.symbols.generic_echos or 
                              t_name in self.symbols.generic_omens or 
                              t_name in self.symbols.generic_aliases or
                              (lookup_t is not None and getattr(lookup_t, "type_params", None)))
                if is_generic:
                    gen_entry = (self.symbols.generic_runes.get(t_name) or 
                                 self.symbols.generic_echos.get(t_name) or 
                                 self.symbols.generic_omens.get(t_name) or 
                                 self.symbols.generic_aliases.get(t_name))
                    params = gen_entry[0] if gen_entry else (getattr(lookup_t, "type_params", []) or [])
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
                    else:
                        arg_types = []
                        for c in rem_children:
                            try:
                                at = ast_to_type(c, self.symbols.lookup_type)
                                arg_types.append(at)
                            except Exception:
                                pass
                        if len(arg_types) == len(rem_children):
                            err_info = check_generic_bounds(t_name, arg_types, self.symbols)
                            if err_info:
                                arg_t_name, bound, tp_name, base_name = err_info
                                err = self._make_error(
                                    ConceptBoundNotSatisfiedError,
                                    f"Type '{arg_t_name}' does not implement concept '{bound}' required by generic parameter '{tp_name}' of '{base_name}'",
                                    type_node,
                                    code="E0032",
                                    help=f"Bind '{bound}' to '{arg_t_name}' using 'bind {arg_t_name} with {bound}:'.",
                                    note=f"Generic type '{base_name}' requires '{tp_name}: {bound}'."
                                )
                                self._record_error(err)
        for c in type_node.children:
            if isinstance(c, Tree):
                self._validate_type_node(c)

    def _stmt_always_returns(self, node: Any) -> bool:
        """Determines if a statement or block unconditionally returns or exits."""
        if not isinstance(node, Tree):
            return False
        inner = node
        while isinstance(inner, Tree) and inner.data in ("stmt", "simple_stmt") and inner.children:
            inner = inner.children[0]
        if not isinstance(inner, Tree):
            return False
        rule = SIMPLE_STMT_ALIASES.get(inner.data, inner.data)
        if rule == "return_stmt":
            return True
        if rule in ("if_stmt", "unless_stmt"):
            block_node = inner.children[1]
            else_node = inner.children[2] if len(inner.children) > 2 else None
            if not else_node:
                return False
            then_stmts = [c for c in block_node.children if isinstance(c, Tree)]
            if not then_stmts or not self._stmt_always_returns(then_stmts[-1]):
                return False
            if else_node.data in ("else_block", "block"):
                else_stmts = [c for c in else_node.children if isinstance(c, Tree)]
                return bool(else_stmts and self._stmt_always_returns(else_stmts[-1]))
            elif else_node.data in ("elif_stmt", "if_stmt", "unless_stmt"):
                return self._stmt_always_returns(else_node)
            else_children = [c for c in else_node.children if isinstance(c, Tree)]
            if else_children:
                return self._stmt_always_returns(else_children[-1])
        if rule == "when_stmt":
            val = self._eval_when_condition(inner.children[0], inner) if inner.children else None
            then_block = inner.children[1] if (len(inner.children) > 1 and isinstance(inner.children[1], Tree) and inner.children[1].data == "block") else None
            else_node = inner.children[2] if len(inner.children) > 2 and isinstance(inner.children[2], Tree) else None
            if val is True:
                if not then_block:
                    return False
                then_stmts = [c for c in then_block.children if isinstance(c, Tree)]
                return bool(then_stmts and self._stmt_always_returns(then_stmts[-1]))
            elif val is False:
                if not else_node:
                    return False
                if else_node.data == "when_else_when":
                    return bool(else_node.children and self._stmt_always_returns(else_node.children[0]))
                else_stmts = [c for c in else_node.children if isinstance(c, Tree)]
                return bool(else_stmts and self._stmt_always_returns(else_stmts[-1]))
            else:
                if not then_block or not else_node:
                    return False
                then_stmts = [c for c in then_block.children if isinstance(c, Tree)]
                if not then_stmts or not self._stmt_always_returns(then_stmts[-1]):
                    return False
                if else_node.data == "when_else_when":
                    return bool(else_node.children and self._stmt_always_returns(else_node.children[0]))
                else_stmts = [c for c in else_node.children if isinstance(c, Tree)]
                return bool(else_stmts and self._stmt_always_returns(else_stmts[-1]))
        return False

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
        w_attrs, _ = _extract_attributes(node.children)
        self._validate_attributes(w_attrs, "weave", node)
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

        seen_param_names: Dict[str, Any] = {}
        for child in rem_children:
            if isinstance(child, Tree) and child.data == "param_list":
                for p in child.children:
                    if isinstance(p, Tree) and p.data == "param":
                        pn = str(p.children[0])
                        pt = ast_to_type(p.children[1], lookup_tp) if len(p.children) >= 2 else AnyType()
                        has_default = len(p.children) >= 3 and p.children[2] is not None

                        if pn in seen_param_names:
                            err = self._make_error(
                                SemanticError,
                                f"Duplicate parameter name '{pn}' in function '{fn_name}'",
                                p,
                                code="E0005",
                                help=f"Rename one of the '{pn}' parameters.",
                                note="Each parameter of a weave must have a distinct name."
                            )
                            self._record_error(err)
                        else:
                            seen_param_names[pn] = p

                        if isinstance(pt, ManyType):
                            if has_default:
                                err = self._make_error(
                                    SemanticError,
                                    f"Variadic 'many' parameter '{pn}' in function '{fn_name}' cannot have a default value",
                                    p,
                                    code="E0005",
                                    help="Remove default value from 'many' parameter; it already defaults to an empty slice if omitted.",
                                    note="Variadic parameters collect trailing arguments into a slice."
                                )
                                self._record_error(err)
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
                                        f"Generic parameter '{pn}' of generic type '{pt}' cannot have a default value depending on type parameters",
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
            elif isinstance(child, Tree) and child.data not in ("param_list", "shard_params", "weave_modifier"):
                stmt_children.append(child)

        if fn_name == "main" and ret_type is not None:
            unwrapped_ret = ret_type
            while isinstance(unwrapped_ret, (AliasType, FrozenType)) and getattr(unwrapped_ret, "target", None):
                unwrapped_ret = unwrapped_ret.target
            if isinstance(unwrapped_ret, SealType):
                unwrapped_ret = unwrapped_ret.underlying

            if isinstance(unwrapped_ret, OmenType) or not (
                unwrapped_ret.is_int()
                or unwrapped_ret.is_bool()
                or unwrapped_ret == VOID_TYPE
                or (isinstance(unwrapped_ret, BaseType) and unwrapped_ret.name in ("void", "int", "i32", "i64", "bool"))
            ):
                err = self._make_error(
                    SemanticError,
                    f"Entry point 'main' must return an integer or 'void', got '{ret_type}'",
                    node,
                    code="E0020",
                    help="Declare 'main' as 'weave main into int' or 'weave main into void'.",
                    note="The program entry point must return an exit code (integer) or nothing (void)."
                )
                self._record_error(err)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="weave", return_type=ret_type, is_ritual=is_ritual, start_line=span_start, end_line=span_end)
        for tp in type_params:
            self.symbols.define(Symbol(name=tp, type=TypeParam(tp, bounds=bounds.get(tp, [])), kind="type"))

        for pn, pt in params:
            self.symbols.define(Symbol(name=pn, type=pt, kind="param", is_mutable=False, line=line, column=col))

        self.block_stmts_stack.append(stmt_children)
        try:
            for stmt in stmt_children:
                self._check_node(stmt)

            # Inlining and Small Weaves Analysis
            fn_sym = self.symbols.lookup(fn_name)
            if fn_sym:
                has_loop = any(True for _ in node.iter_subtrees() if isinstance(_, Tree) and _.data in ("while_stmt", "for_range_stmt", "for_in_stmt"))
                has_static = any(True for _ in node.iter_subtrees() if isinstance(_, Tree) and _.data == "static_var_decl")
                node_count = sum(1 for _ in node.iter_subtrees())
                if (len(stmt_children) <= 3 or node_count <= 25) and not has_loop and not has_static:
                    fn_sym.is_inline = True

            # Escape Analysis for local variables
            for s_name, sym in list(self.symbols.current_scope.symbols.items()):
                if sym.kind in ("var", "let") and not getattr(sym, "is_static", False):
                    escaped = self._check_symbol_escape(s_name, stmt_children)
                    sym.is_stack_alloc = not escaped
                    if escaped:
                        sym.is_auto_banished = False

            # Implicit return check for last expression
            if stmt_children:
                last_stmt = stmt_children[-1]
                last_inner = last_stmt
                while isinstance(last_inner, Tree) and last_inner.data in ("stmt", "simple_stmt") and last_inner.children:
                    last_inner = last_inner.children[0]

                if isinstance(last_inner, Tree) and last_inner.data == "expr_stmt":
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
                elif ret_type != VOID_TYPE and not isinstance(ret_type, AnyType):
                    if not self._stmt_always_returns(last_inner):
                        stmt_desc = last_inner.data.replace("_stmt", "").replace("_decl", "")
                        err = self._make_error(
                            TypeMismatchError,
                            f"Function '{fn_name}' declared into '{ret_type}' does not return a value (ends with '{stmt_desc}')",
                            last_inner,
                            code="E0020",
                            help=f"Add a 'return' statement or ensure the last statement is an expression evaluating to '{ret_type}'.",
                            note="Functions with non-void return types must return a value."
                        )
                        self._record_error(err)
        finally:
            self.block_stmts_stack.pop()

        self.symbols.pop_scope(end_line=span_end)

    def _lookup_field_type_on(self, base_t: Optional[Type], field_name: str) -> Optional[Type]:
        """Resolves the type of a field on ``base_t`` for the escape analysis.

        Mirrors the code generator's helper of the same name: references and
        aliases are looked through, and a primitive that names a user type is
        resolved through the symbol table (``BaseType('Bag')`` -> ``RuneType``).
        """
        u = base_t
        while isinstance(u, (RefType, AliasType, FrozenType, SealType)):
            nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
            if nxt is None or nxt is u:
                break
            u = nxt
        if isinstance(u, BaseType):
            sym_t = self.symbols.lookup_type(u.name)
            if sym_t is not None and sym_t is not u:
                u = sym_t
                while isinstance(u, (RefType, AliasType, FrozenType, SealType)):
                    nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
                    if nxt is None or nxt is u:
                        break
                    u = nxt
        if u is None:
            return None
        fields = getattr(u, "fields", None)
        if isinstance(u, (RuneType, EchoType)) and isinstance(fields, dict):
            return fields.get(field_name)
        return None

    def _resolve_chain_type(self, base_t: Optional[Type], accs: List[Any]) -> Optional[Type]:
        """Applies ``dot_access``/``arrow_access``/``at_access`` steps onto ``base_t``.

        Used by the escape analysis to find the *container* behind chains such as
        ``self->items`` or ``bag.inner.items`` instead of stopping at the first
        identifier.  Returns None as soon as a step cannot be resolved so the
        caller stays conservative.
        """
        curr = base_t
        for acc in accs:
            if not isinstance(acc, Tree):
                return None
            if acc.data in ("dot_access", "arrow_access") and acc.children:
                curr = self._lookup_field_type_on(curr, str(acc.children[0]))
            elif acc.data == "at_access":
                u = curr
                while isinstance(u, (RefType, AliasType, FrozenType, SealType)):
                    nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
                    if nxt is None or nxt is u:
                        break
                    u = nxt
                if isinstance(u, (ListType, ArrayType, SliceType, ManyType)):
                    curr = u.element
                elif isinstance(u, MapType):
                    curr = u.value
                elif isinstance(u, BaseType) and u.name == "string":
                    curr = STRING_TYPE  # indexing a string yields a character
                else:
                    return None
            else:
                return None
            if curr is None:
                return None
        return curr

    def _escape_receiver_type(self, target: Any,
                              with_types: Optional[List[Optional[Type]]] = None) -> Optional[Type]:
        """Best-effort type of the container a ``calling X.method`` targets.

        Returns None when it cannot be resolved statically (callers must then
        stay conservative and treat the store as an escape).
        """
        if not isinstance(target, Tree):
            return None
        if target.data == "with_target":
            if with_types:
                return with_types[-1]
            getter = getattr(self.symbols, "current_with_type", None)
            return getter() if callable(getter) else None
        if target.data == "normal_target" and target.children:
            first = target.children[0]
            # The last access operator *is* the method name; everything before
            # it is the receiver chain to resolve.
            rest = list(target.children[1:])
            if rest and isinstance(rest[-1], Tree) and rest[-1].data in ("dot_access", "arrow_access"):
                rest = rest[:-1]

            base_t: Optional[Type] = None
            if isinstance(first, Token) and str(first) == "self":
                getter = getattr(self.symbols, "current_enchanting_type", None)
                ench = getter() if callable(getter) else None
                # 'self' is always a pointer to the enchanted type.
                base_t = RefType(ench) if ench is not None else None
            elif isinstance(first, Token) and first.type == "NAME":
                sym = self.symbols.lookup(str(first))
                if sym is not None:
                    base_t = sym.type
                elif with_types and with_types[-1] is not None:
                    # Bare field name inside 'with x:' (e.g. 'calling items.push').
                    base_t = with_types[-1]
            if base_t is None:
                return None
            return self._resolve_chain_type(base_t, rest)
        return None

    def _slot_type_for_target(self, target: Any) -> Optional[Type]:
        """Type of the storage cell named by a `set` target (None when unknown).

        Mirrors the code generator's resolver so the escape analysis only relaxes
        when that storage really receives a deep copy.
        """
        if not isinstance(target, Tree):
            return None
        if target.data == "set_target" and target.children:
            return self._slot_type_for_target(target.children[0])
        if target.data == "with_target" and target.children:
            base = self.symbols.current_with_type() or getattr(self, "_escape_with_type", None)
            accs = [Tree("dot_access", [target.children[0]])]
            accs += [c for c in target.children[1:] if isinstance(c, Tree)]
            return self._resolve_chain_type(base, accs)
        if target.data == "normal_target" and target.children:
            first = target.children[0]
            base: Optional[Type] = None
            if isinstance(first, Token) and str(first) == "self":
                ench = self.symbols.current_enchanting_type()
                base = RefType(ench) if ench is not None else None
            elif isinstance(first, Token) and first.type == "NAME":
                sym = self.symbols.lookup(str(first))
                base = sym.type if sym is not None else None
            return self._resolve_chain_type(base, [c for c in target.children[1:] if isinstance(c, Tree)])
        if target.data == "essence_target" and target.children:
            try:
                return getattr(self.inferrer.infer(target.children[0]), "target", None)
            except SemanticError:
                return None
        return None

    def _slot_owns_string_copy(self, target: Any, val_node: Any) -> bool:
        """True when `target = val` deep-copies a string into its slot."""
        inner = target
        if isinstance(inner, Tree) and inner.data == "set_target" and inner.children:
            inner = inner.children[0]
        if not isinstance(inner, Tree):
            return False
        if not (inner.data == "with_target"
                or (inner.data == "normal_target" and len(inner.children) > 1)
                or inner.data == "essence_target"):
            return False
        slot_t = self._slot_type_for_target(inner)
        u = slot_t
        while isinstance(u, (AliasType, FrozenType, SealType)):
            u = getattr(u, "target", None) or getattr(u, "underlying", None)
        if not (isinstance(u, BaseType) and u.name == "string"):
            return False
        try:
            val_t = self.inferrer.infer(val_node)
        except SemanticError:
            # The value can be the very variable being declared ('var s is …'
            # is analysed before 's' exists in the scope): fall back to its
            # declared type when the escape pass provides it.
            info = getattr(self, "_escape_self_type", None)
            if info and self._is_direct_var_ref(val_node, info[0]):
                val_t = info[1]
            else:
                return False
        v = val_t
        while isinstance(v, (AliasType, FrozenType, SealType)):
            v = getattr(v, "target", None) or getattr(v, "underlying", None)
        if isinstance(v, BaseType) and v.name == "string":
            return True
        if isinstance(v, TypeParam):
            return "Forma" in v.bounds
        return isinstance(v, OmenType) and (v.is_string() or v.is_string_valued)

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
        # Type of the innermost 'with <expr>:' target, so that a '.push'/'.put'
        # inside the block can be classified without a live scope.
        with_types: List[Optional[Type]] = []

        def contains_sigil_of(node: Any) -> bool:
            if not isinstance(node, Tree):
                return False
            if node.data == "sigil_of" and node.children:
                target = node.children[0]
                # 'sigil of x' *and* addresses of a sub-object ('sigil of x.field',
                # 'sigil of x at 0', 'sigil of x.f.g') all keep x's storage alive:
                # every one of them is a pointer into x that would dangle once x
                # is released.  _contains_var_ref understands access chains.
                if self._contains_var_ref(target, sym_name):
                    return True
            return any(contains_sigil_of(c) for c in node.children if isinstance(c, Tree))

        def _struct_init_type(decl_or_field: Any) -> Optional[Type]:
            """Type of a struct literal from its enclosing declaration/field."""
            if not isinstance(decl_or_field, Tree):
                return None
            # 'var p as Player is with ...' -> the annotation child.
            if decl_or_field.data in ("var_decl", "let_decl"):
                for child in decl_or_field.children:
                    if isinstance(child, Tree) and child.data in (
                        "base_type", "custom_type", "ref_type", "alias_type",
                    ):
                        try:
                            return ast_to_type(child, self.symbols.lookup_type)
                        except Exception:
                            return None
                return None
            return None

        def _field_type_on(struct_t: Optional[Type], f_name: str) -> Optional[Type]:
            u = struct_t
            while isinstance(u, (AliasType, FrozenType, SealType, RefType)):
                nxt = (getattr(u, "target", None) or getattr(u, "underlying", None))
                if nxt is None or nxt is u:
                    break
                u = nxt
            fields = getattr(u, "fields", None)
            if isinstance(fields, dict):
                return fields.get(f_name)
            return None

        def _is_string_t(t: Optional[Type]) -> bool:
            u = t
            while isinstance(u, (AliasType, FrozenType, SealType)):
                nxt = (getattr(u, "target", None) or getattr(u, "underlying", None))
                if nxt is None or nxt is u:
                    break
                u = nxt
            return isinstance(u, BaseType) and u.name == "string"

        # Expressions that yield a *view* into an existing buffer instead of a
        # fresh/owned value: storing or returning one keeps the source alive.
        _VIEW_RULES = (
            "at_expr", "array_at_expr", "slice_at_expr", "bytes_expr",
            "field_access", "arrow_access", "self_arrow", "essence_of",
        )

        def _unwrap(node: Any) -> Any:
            un = node
            while (isinstance(un, Tree) and un.data in ("paren_expr", "value_expr", "expr")
                   and len(un.children) == 1):
                un = un.children[0]
            return un

        def _is_view_into(node: Any) -> bool:
            """True when ``node`` borrows into ``sym_name``'s storage."""
            un = _unwrap(node)
            if not isinstance(un, Tree):
                return False
            if un.data in _VIEW_RULES:
                if self._is_scalar_member_access(un):
                    return False
                return self._contains_var_ref(un, sym_name)
            return False

        def _last_value_expr(stmts: List[Any]) -> Any:
            """Value expression of a value-position statement list, if any."""
            if not stmts:
                return None
            last = _unwrap(stmts[-1])
            while (isinstance(last, Tree) and last.data in ("stmt", "simple_stmt", "block")
                   and last.children):
                nxt = _unwrap(last.children[-1])
                if nxt is last:
                    break
                last = nxt
            if not isinstance(last, Tree):
                return None
            if last.data == "expr_stmt" and last.children:
                return last.children[0]
            # A trailing value-position 'if'/'unless'/'do:'/loop *is* its own
            # value (the node carries the type the checker inferred).
            if getattr(last, "_pengu_value_type", None) is not None:
                return last
            return None

        def _block_value_exprs(node: Any, _depth: int = 0) -> List[Any]:
            """Value expressions produced by a 'do:' or a value-position 'if'.

            Nested value blocks are flattened recursively ('do: do: y'), so the
            escape analysis sees a local handed out through any depth.
            """
            un = _unwrap(node)
            if not isinstance(un, Tree) or _depth > 16:
                return []
            out: List[Any] = []
            if un.data == "do_expr":
                stmts = [c for c in un.children if isinstance(c, Tree)]
                v = _last_value_expr(stmts)
                if v is not None:
                    out.append(v)
            elif un.data in ("if_stmt", "unless_stmt") and getattr(un, "_pengu_value_type", None) is not None:
                for branch in un.children[1:]:
                    if not isinstance(branch, Tree):
                        continue
                    if branch.data in ("block", "else_block", "when_else_plain", "when_else_when"):
                        bstmts = [c for c in branch.children if isinstance(c, Tree)]
                    else:
                        bstmts = [branch]
                    v = _last_value_expr(bstmts)
                    if v is not None:
                        out.append(v)
            else:
                return []
            # Descend into nested *value blocks* (a loop value copies its
            # elements, so it never hands a local's storage out).
            for sub in list(out):
                su = _unwrap(sub)
                if (isinstance(su, Tree)
                        and su.data in ("do_expr", "if_stmt", "unless_stmt")
                        and getattr(su, "_pengu_value_type", None) is not None):
                    out.extend(_block_value_exprs(su, _depth + 1))
            return out

        def _hands_out_storage(node: Any) -> bool:
            """True when the expression *is* sym_name's value (or a sigil of it)."""
            if node is None:
                return False
            un = _unwrap(node)
            if isinstance(un, Tree) and un.data in ("do_expr", "if_stmt", "unless_stmt"):
                return _block_value_hands_out(node)
            return contains_sigil_of(node) or self._is_direct_var_ref(node, sym_name)

        def _block_value_hands_out(node: Any) -> bool:
            """True when a 'do:'/'if:' value is (or views into) sym_name.

            A block value is consumed by the enclosing expression *after* the
            block's own scope was released, so any borrowing value must keep the
            local alive; the code generator cannot defer that release.
            """
            for sub in _block_value_exprs(node):
                if (contains_sigil_of(sub) or self._is_direct_var_ref(sub, sym_name)
                        or _is_view_into(sub)):
                    return True
            return False

        def walk(n: Any, parent: Any = None, grandparent: Any = None):
            nonlocal escaped
            if escaped or not isinstance(n, Tree):
                return

            # 0. 'with <expr>:' — remember the target type for the nested calls.
            if n.data == "with_stmt" and n.children:
                wt: Optional[Type] = None
                try:
                    wt = self.inferrer.infer(n.children[0])
                except Exception:
                    wt = None
                with_types.append(wt)
                for child in n.children[1:]:
                    walk(child)
                with_types.pop()
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
                if self._is_direct_var_ref(ret_val, sym_name):
                    escaped = True
                    return
                if isinstance(ret_val, Tree):
                    if ret_val.data == "some_expr":
                        # 'return some s' deep-copies an owning payload into the
                        # box, so nothing of s's storage leaves the scope.
                        payload_t = self._some_payload_type(ret_val, parent, grandparent)
                        if payload_t is not None and self._clone_capable_type(payload_t):
                            return
                    for sub in ret_val.iter_subtrees():
                        if sub.data in _ESCAPE_COMPOUND_RULES:
                            if sub.data == "some_expr":
                                payload_t = self._some_payload_type(sub, n, parent)
                                if payload_t is not None and self._clone_capable_type(payload_t):
                                    continue
                            if self._contains_var_ref(sub, sym_name):
                                escaped = True
                                return
                    if ret_val.data in ("if_stmt", "unless_stmt", "do_expr",
                                        "while_stmt", "for_range_stmt", "for_in_stmt"):
                        if self._contains_var_ref(ret_val, sym_name):
                            escaped = True
                            return
                if contains_sigil_of(ret_val):
                    escaped = True
                    return
                # A view into the local ('return s at 0', 'return s.field',
                # 'return bytes of s') stays valid only while the local's buffer
                # lives: banishing the local would hand back a dangling pointer.
                if (_hands_out_storage(ret_val) or _is_view_into(ret_val)
                        or _block_value_hands_out(ret_val)):
                    escaped = True
                    return

            # 3. Set statements (assigning address to fields, struct members, globals)
            elif n.data == "set_stmt":
                val_node = n.children[-1]
                target_node = n.children[0]
                if contains_sigil_of(val_node):
                    escaped = True
                    return
                if self._contains_var_ref(val_node, sym_name):
                    if not self._is_direct_var_ref(target_node, sym_name):
                        # A string stored into an owned slot (struct field,
                        # element, pointee) is deep-copied by the code generator,
                        # so the local keeps ownership and stays auto-banished.
                        # The slot deep-copies a string value, so the source
                        # keeps ownership and stays auto-banished; only a
                        # non-copying slot (a view target) makes it escape.
                        if not self._slot_owns_string_copy(target_node, val_node):
                            escaped = True
                            return

            # 4. Function call arguments
            elif n.data == "calling_expr":
                if contains_sigil_of(n):
                    escaped = True
                    return
                target = n.children[0] if n.children else None
                method_name = None
                if isinstance(target, Tree):
                    if target.data == "with_target" and target.children:
                        method_name = str(target.children[0])
                    else:
                        for ch in reversed(target.children):
                            if isinstance(ch, Tree) and ch.data in ("dot_access", "arrow_access") and ch.children:
                                method_name = str(ch.children[0])
                                break
                if method_name in ("push", "append", "put", "insert", "set"):
                    arg_list = next((c for c in n.children if isinstance(c, Tree) and c.data == "arg_list"), None)
                    if arg_list and self._contains_var_ref(arg_list, sym_name):
                        # A list/map built with the owning constructors registers
                        # clone callbacks, so push/put deep-copies: the source
                        # keeps ownership of its own buffer and may still be
                        # auto-banished.  Only a shallow (aliasing) store makes
                        # the value escape.
                        recv_t = self._escape_receiver_type(target, with_types)
                        if receiver_deep_copies_on_store(recv_t, self.symbols):
                            pass
                        else:
                            escaped = True
                            return

            # 5. Compound data structures or container literals
            elif n.data in _ESCAPE_COMPOUND_RULES:
                if n.data in ("struct_init", "struct_init_expr", "with_init_expr"):
                    # Recurse: each field value is classified on its own, since a
                    # string stored into a string field is deep-copied.
                    prev_with = getattr(self, "_escape_with_type", None)
                    with_types.append(_struct_init_type(parent))
                    self._escape_with_type = _struct_init_type(parent)
                    try:
                        for child in n.children:
                            walk(child, n, parent)
                    finally:
                        with_types.pop()
                        self._escape_with_type = prev_with
                    return
                if n.data in ("field_init", "field_entry") and isinstance(parent, Tree) and parent.data == "struct_init":
                    # 'with name is s' stores a *copy* of a string into an owned
                    # rune field (see _string_slot_value), so the local keeps
                    # ownership and may still be auto-banished.
                    struct_t = _struct_init_type(grandparent)
                    f_name = str(n.children[0]) if n.children else ""
                    f_t = _field_type_on(struct_t, f_name)
                    val = n.children[-1] if len(n.children) > 1 else None
                    if _is_string_t(f_t):
                        if contains_sigil_of(val):
                            escaped = True
                            return
                        for child in n.children:
                            walk(child, n, parent)
                        return
                if n.data == "some_expr" and n.children:
                    # The code generator *deep-copies* an owning payload into the
                    # box ('some s' no longer shares s's buffer), so the source
                    # keeps ownership and may still be auto-banished.  A payload
                    # without a clone callback (slice/ref/POD) is still aliased.
                    payload_t = self._some_payload_type(n, parent, grandparent)
                    if payload_t is not None and self._clone_capable_type(payload_t):
                        for child in n.children:
                            walk(child, n, parent)
                        return
                if contains_sigil_of(n) or self._contains_var_ref(n, sym_name):
                    escaped = True
                    return


            # 6. Variable declarations (aliasing / transferring ownership)
            elif n.data in ("var_decl", "let_decl") and n.children:
                val_node = n.children[-1]
                # Binding a *view* is safe while every use precedes the
                # scope-end banish, so only an identity hand-off escapes here;
                # the view case is propagated below when the binding escapes.
                if _hands_out_storage(val_node) or _block_value_hands_out(val_node):
                    escaped = True
                    return


            for child in n.children:
                walk(child, n, parent)

        for stmt in stmts:
            walk(stmt)
        if escaped:
            return True

        # A local bound to a *view* of sym_name ('var v as string is xs at 0')
        # borrows sym_name's buffer: if that local escapes, so must the source.
        # Binding alone is safe (all uses precede the scope-end banish), so this
        # only fires when the view itself is returned or stored away.
        guard = getattr(self, "_escape_view_guard", None)
        if guard is None:
            guard = set()
            self._escape_view_guard = guard
        if sym_name in guard:
            return False
        guard.add(sym_name)
        try:
            for stmt in stmts:
                if not isinstance(stmt, Tree):
                    continue
                for decl in stmt.iter_subtrees():
                    if not (isinstance(decl, Tree) and decl.data in ("var_decl", "let_decl")):
                        continue
                    if len(decl.children) < 2:
                        continue
                    if not _is_view_into(decl.children[-1]):
                        continue
                    names = [str(t) for t in decl.children[1:]
                             if isinstance(t, Token) and t.type == "NAME"]
                    if not names or names[0] == sym_name:
                        continue
                    # A scalar element read ('lst at 0' of an int) is a copy, not
                    # a borrowed buffer, so its escape does not affect the source.
                    # The bound type comes from the declaration itself: this
                    # analysis runs while the *source* is being declared, so a
                    # later binding is not in the symbol table yet.
                    bound_t = None
                    for ch in decl.children[1:-1]:
                        if isinstance(ch, Tree) and ch.data in self._TYPE_NODE_RULES:
                            try:
                                bound_t = ast_to_type(ch, self.symbols.lookup_type)
                            except Exception:
                                bound_t = None
                            break
                    if bound_t is None:
                        bound_sym = self.symbols.lookup(names[0]) if self.symbols else None
                        bound_t = getattr(bound_sym, "type", None)
                    while isinstance(bound_t, (AliasType, FrozenType)) and getattr(bound_t, "target", None):
                        bound_t = bound_t.target
                    if isinstance(bound_t, BaseType) and bound_t.name in (
                            "int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
                            "float", "f32", "f64", "bool", "char", "byte"):
                        continue
                    if self._check_symbol_escape(names[0], stmts):
                        return True
        finally:
            guard.discard(sym_name)
        return False

    def _check_enchanting_method(self, node: Tree, self_type: Type, type_params: Optional[List[str]] = None, type_bounds: Optional[Dict[str, List[str]]] = None) -> None:
        """Checks method definition within an enchanting block.

        Args:
            node: AST Tree for enchanting weave method.
            self_type: Receiver Type being enchanted.
            type_params: Optional list of generic type parameters.
            type_bounds: Optional dictionary mapping type parameter names to concept bounds.
        """
        line, col = self._get_loc(node)
        w_attrs, _ = _extract_attributes(node.children)
        self._validate_attributes(w_attrs, "weave", node)
        is_inline, is_ritual, idx = _extract_weave_modifiers(node.children)
        fn_name = str(node.children[idx])
        rem_children = [c for c in node.children[idx+1:] if c is not None]

        m_tparams = []
        m_bounds = {}
        if rem_children and isinstance(rem_children[0], Tree) and rem_children[0].data == "shard_params":
            m_tparams, m_bounds = extract_shard_params(rem_children[0])
            rem_children = rem_children[1:]

        combined_bounds = dict(type_bounds or {})
        combined_bounds.update(m_bounds)
        tp_list = list(type_params or []) + m_tparams
        def lookup_m_tp(tname: str):
            if tname in tp_list:
                return TypeParam(tname, bounds=combined_bounds.get(tname, []))
            return self.symbols.lookup_type(tname)

        params: List[Tuple[str, Type]] = []
        ret_type: Type = VOID_TYPE
        stmt_children: List[Tree] = []
        default_count = 0
        has_seen_default = False
        many_param_seen = False
        many_count = 0

        seen_m_param_names: Dict[str, Any] = {}
        for child in rem_children:
            if isinstance(child, Tree) and child.data == "param_list":
                for p in child.children:
                    if isinstance(p, Tree) and p.data == "param":
                        pn = str(p.children[0])
                        pt = ast_to_type(p.children[1], lookup_m_tp) if len(p.children) >= 2 else AnyType()
                        has_default = len(p.children) >= 3 and p.children[2] is not None

                        if pn in seen_m_param_names:
                            err = self._make_error(
                                SemanticError,
                                f"Duplicate parameter name '{pn}' in method '{fn_name}'",
                                p,
                                code="E0005",
                                help=f"Rename one of the '{pn}' parameters.",
                                note="Each parameter of an enchanting method must have a distinct name."
                            )
                            self._record_error(err)
                        else:
                            seen_m_param_names[pn] = p

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
            self.symbols.define(Symbol(name=tp, type=TypeParam(tp, bounds=combined_bounds.get(tp, [])), kind="type"))

        for pn, pt in params:
            self.symbols.define(Symbol(name=pn, type=pt, kind="param", is_mutable=False, line=line, column=col))

        self.block_stmts_stack.append(stmt_children)
        try:
            for stmt in stmt_children:
                self._check_node(stmt)

            # Same implicit-return rules as a top-level weave: a method declared
            # 'into T' must either end in an expression of type T or always
            # return, otherwise the C function falls off the end (UB).
            if stmt_children and ret_type != VOID_TYPE:
                last_stmt = stmt_children[-1]
                last_inner = last_stmt
                while (isinstance(last_inner, Tree)
                       and last_inner.data in ("stmt", "simple_stmt") and last_inner.children):
                    last_inner = last_inner.children[0]
                if isinstance(last_inner, Tree) and last_inner.data == "expr_stmt":
                    expr_node = last_inner.children[0]
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
                elif not isinstance(ret_type, AnyType) and not self._stmt_always_returns(last_inner):
                    stmt_desc = last_inner.data.replace("_stmt", "").replace("_decl", "")
                    err = self._make_error(
                        TypeMismatchError,
                        f"Method '{fn_name}' declared into '{ret_type}' does not return a value (ends with '{stmt_desc}')",
                        last_inner,
                        code="E0020",
                        help=f"Add a 'return' statement or end with an expression evaluating to '{ret_type}'.",
                        note="Methods with non-void return types must return a value on every path."
                    )
                    self._record_error(err)
        finally:
            self.block_stmts_stack.pop()

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

        b_stmts = [c for c in block_node.children if isinstance(c, Tree)] if (isinstance(block_node, Tree) and block_node.data == "block") else ([block_node] if isinstance(block_node, Tree) else [])
        self.block_stmts_stack.append(b_stmts)
        try:
            if folded_cond is False:
                self.warnings.append("[W0004] Unreachable code in then branch")
            self._check_node(block_node)
        finally:
            self.block_stmts_stack.pop()
        self.symbols.pop_scope(end_line=span_end)

        if else_node is not None:
            if folded_cond is True:
                self.warnings.append("[W0004] Unreachable code in else branch")
            e_start, e_end = self._get_node_span(else_node)
            self.symbols.push_scope(kind="if", start_line=e_start, end_line=e_end)
            e_stmts = [c for c in else_node.children if isinstance(c, Tree)] if (isinstance(else_node, Tree) and else_node.data in ("block", "else_block")) else ([else_node] if isinstance(else_node, Tree) else [])
            self.block_stmts_stack.append(e_stmts)
            try:
                self._check_node(else_node)
            finally:
                self.block_stmts_stack.pop()
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

        folded_cond = self.const_folder.fold(cond_node)

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

        b_stmts = [c for c in block_node.children if isinstance(c, Tree)] if (isinstance(block_node, Tree) and block_node.data == "block") else ([block_node] if isinstance(block_node, Tree) else [])
        self.block_stmts_stack.append(b_stmts)
        try:
            if folded_cond is True:
                self.warnings.append("[W0004] Unreachable code in then branch")
            self._check_node(block_node)
        finally:
            self.block_stmts_stack.pop()
        self.symbols.pop_scope(end_line=span_end)

        if else_node is not None:
            if folded_cond is False:
                self.warnings.append("[W0004] Unreachable code in else branch")
            e_start, e_end = self._get_node_span(else_node)
            self.symbols.push_scope(kind="if", start_line=e_start, end_line=e_end)
            e_stmts = [c for c in else_node.children if isinstance(c, Tree)] if (isinstance(else_node, Tree) and else_node.data in ("block", "else_block")) else ([else_node] if isinstance(else_node, Tree) else [])
            self.block_stmts_stack.append(e_stmts)
            try:
                self._check_node(else_node)
            finally:
                self.block_stmts_stack.pop()
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
        b_stmts = [c for c in block_node.children if isinstance(c, Tree)] if (isinstance(block_node, Tree) and block_node.data == "block") else ([block_node] if isinstance(block_node, Tree) else [])
        self.block_stmts_stack.append(b_stmts)
        try:
            if collect:
                elem_t = self._check_value_block(list(block_node.children), expected_element,
                                                  copies_value=True)
            else:
                self._check_node(block_node)
        finally:
            self.block_stmts_stack.pop()
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
        step_node = node.children[3] if len(node.children) == 5 and node.children[3] is not None else None
        block_node = node.children[-1]

        start_val = self.const_folder.fold(start_node)
        end_val = self.const_folder.fold(end_node)
        step_val = self.const_folder.fold(step_node) if step_node is not None else 1

        if isinstance(step_val, int) and step_val == 0:
            err = self._make_error(
                InvalidRangeError,
                "Invalid range: step cannot be zero",
                step_node if step_node is not None else node,
                code="E0042",
                help="Range step must be a non-zero integer.",
                note="A step of 0 produces an infinite loop."
            )
            self._record_error(err)
        elif isinstance(step_val, int) and step_val < 0:
            if isinstance(start_val, int) and isinstance(end_val, int) and start_val < end_val:
                err = self._make_error(
                    InvalidRangeError,
                    "Invalid range: descending ranges require start >= end when both bounds are known at compile time",
                    node,
                    code="E0042",
                    help=f"Range start ({start_val}) must be >= end ({end_val}) for negative step ({step_val}).",
                    note="Descending ranges require start >= end."
                )
                self._record_error(err)
        else:
            if isinstance(start_val, int) and isinstance(end_val, int) and start_val > end_val:
                err = self._make_error(
                    InvalidRangeError,
                    "Invalid range: start must be less than or equal to end when both bounds are known at compile time",
                    node,
                    code="E0042",
                    help=f"Range start ({start_val}) must be <= end ({end_val}).",
                    note="Ascending ranges require start <= end."
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
        b_stmts = [c for c in block_node.children if isinstance(c, Tree)] if (isinstance(block_node, Tree) and block_node.data == "block") else ([block_node] if isinstance(block_node, Tree) else [])
        self.block_stmts_stack.append(b_stmts)
        try:
            if collect:
                elem_t = self._check_value_block(list(block_node.children), expected_element,
                                                  copies_value=True)
            else:
                self._check_node(block_node)
        finally:
            self.block_stmts_stack.pop()
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
            # 'for k in self' inside an enchanting method: the receiver is a
            # 'ref to map'/'ref to list' pointer, so look through the reference.
            probe = it
            while isinstance(probe, (RefType, AliasType, FrozenType)):
                probe = getattr(probe, "target", None) or probe
            if isinstance(probe, TypeParam):
                # A bare 'T' cannot be iterated: the element type is unknown
                # until monomorphization and generic code may be checked with
                # an abstract T.  Associated types ('T.Item') make this sound
                # in the future; until then require a concrete container.
                err = self._make_error(
                    SemanticError,
                    f"Cannot iterate directly over generic type parameter '{probe.name}'",
                    iter_node,
                    code="E0005",
                    help=f"Use 'list of {probe.name}' or 'slice of {probe.name}' as the parameter "
                         f"type. Direct iteration over a bare '{probe.name}' requires "
                         "associated types (future feature).",
                    note="'for ... in' needs to know the element type; a bare type "
                         "parameter does not provide one."
                )
                self._record_error(err)
            elif not probe.is_iterable() and not probe.is_string() and not isinstance(probe, AnyType):
                err = self._make_error(
                    SemanticError,
                    f"Cannot iterate over non-collection type '{it}'",
                    iter_node,
                    code="E0005",
                    help="Provide an iterable collection like an array, slice, or list.",
                    note="'for ... in' loops require iterable collections."
                )
                self._record_error(err)
            if probe.is_string():
                elem_type = STRING_TYPE  # iterating a string yields characters
            else:
                elem_type = probe.element_type() or AnyType()
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
        b_stmts = [c for c in block_node.children if isinstance(c, Tree)] if (isinstance(block_node, Tree) and block_node.data == "block") else ([block_node] if isinstance(block_node, Tree) else [])
        self.block_stmts_stack.append(b_stmts)
        try:
            if collect:
                body_t = self._check_value_block(list(block_node.children), expected_element,
                                                  copies_value=True)
            else:
                self._check_node(block_node)
        finally:
            self.block_stmts_stack.pop()
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
            if raw.startswith('r"""') and raw.endswith('"""'):
                test_name = raw[4:-3]
            elif raw.startswith('"""') and raw.endswith('"""'):
                test_name = raw[3:-3]
            elif raw.startswith('r"') and raw.endswith('"'):
                test_name = raw[2:-1]
            elif raw.startswith('"') and raw.endswith('"'):
                test_name = raw[1:-1]
            else:
                test_name = raw

        body_stmts: List[Tree] = []
        for c in node.children[1:]:
            if isinstance(c, Tree):
                body_stmts.append(c)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="weave", return_type=VOID_TYPE, start_line=span_start, end_line=span_end)
        # NOTE: global symbols stay reachable through the scope chain (lookup
        # walks parents), so they are deliberately *not* copied into the test
        # scope: copying them made a legitimate local shadowing a same-file
        # global ('var last' vs the 'last' weave) a false E0035 redefinition.
        self.block_stmts_stack.append(body_stmts)
        try:
            for stmt in body_stmts:
                self._check_node(stmt)
        finally:
            self.block_stmts_stack.pop()
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

    def _check_unsafe_block(self, node: Tree) -> None:
        """Checks an `unsafe:` block (roadmap 5.2/5.6).

        Unsafe blocks opt out of bounds and integer-overflow checks, so they are
        only allowed inside a function body and always warn `[W0007]`.
        """
        if self.symbols.current_return_type() is None:
            self._record_error(self._make_error(
                InvalidMemoryOpError,
                "'unsafe:' is only allowed inside function bodies (weave).",
                node,
                code="E0008",
                help="Move the 'unsafe:' block into a weave/enchanting/test body.",
                note="Unsafe blocks disable bounds and overflow checks for their statements.",
            ))
        line = getattr(node, "line", 0)
        self.warnings.append(
            f"[W0007] 'unsafe:' block disables bounds/overflow checks on line {line}"
        )
        body = node.children[0] if node.children else None
        if isinstance(body, Tree) and body.data == "block":
            for stmt in body.children:
                self._check_node(stmt)
        else:
            for stmt in node.children[1:]:
                self._check_node(stmt)

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
            is_frozen = False
            curr_f = target_type
            while isinstance(curr_f, (AliasType, RefType)):
                curr_f = getattr(curr_f, "target", None)
                if isinstance(curr_f, FrozenType):
                    is_frozen = True
                    break
            if isinstance(target_type, FrozenType):
                is_frozen = True

            if is_frozen:
                is_mut = False
            elif isinstance(target_expr, Tree) and target_expr.data == "var_ref":
                target_var_name = str(target_expr.children[0])
                sym = self.symbols.lookup(target_var_name)
                if sym:
                    sym_frozen = False
                    curr_s = sym.type
                    while isinstance(curr_s, (AliasType, RefType)):
                        curr_s = getattr(curr_s, "target", None)
                        if isinstance(curr_s, FrozenType):
                            sym_frozen = True
                            break
                    if isinstance(sym.type, FrozenType):
                        sym_frozen = True
                    is_mut = (not sym_frozen) and (sym.is_mutable or isinstance(sym.type, RefType))
            elif isinstance(target_type, RefType):
                is_mut = not is_frozen
        except SemanticError as e:
            self._record_error(e)

        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="with", with_type=target_type, with_is_mutable=is_mut, with_target_var_name=target_var_name, start_line=span_start, end_line=span_end)
        with_stmts = [b for b in block_node if isinstance(b, Tree)]
        self.block_stmts_stack.append(with_stmts)
        try:
            for b in block_node:
                self._check_node(b)
        finally:
            self.block_stmts_stack.pop()
        self.symbols.pop_scope(end_line=span_end)

    @staticmethod
    def _slice_base_var_name(node: Any) -> Optional[str]:
        """Base variable of a 'slice_at_expr' (through grouping wrappers)."""
        n = node
        while (isinstance(n, Tree) and n.data in ("paren_expr", "value_expr", "expr")
               and len(n.children) == 1):
            n = n.children[0]
        if not (isinstance(n, Tree) and n.data == "slice_at_expr" and n.children):
            return None
        target = n.children[0]
        while (isinstance(target, Tree) and target.data in ("paren_expr", "value_expr", "expr")
               and len(target.children) == 1):
            target = target.children[0]
        if isinstance(target, Tree) and target.data == "var_ref" and target.children:
            return str(target.children[0])
        return None

    def _check_slice_stack_return(self, expr_node: Any) -> None:
        """Rejects returning a slice ('arr at a to b') of a stack array.

        A slice is a non-owning view: its ``.data`` points into the array's
        storage, which is destroyed when the function returns, so the caller
        would receive a dangling fat pointer.  Heap-backed slices ('list',
        'slice' parameters, globals) are unaffected.
        """
        base = self._slice_base_var_name(expr_node)
        if base is None:
            return
        sym = self.symbols.lookup(base)
        if sym is None or not isinstance(sym.type, ArrayType):
            return
        if self.symbols.global_scope.symbols.get(base) is sym:
            return  # module-level array: static storage outlives the call
        if getattr(sym, "is_static", False):
            return
        self._record_error(self._make_error(
            SemanticError,
            f"Cannot return a slice ('{base} at ...') of the stack array "
            f"'{base}'; the slice would dangle once the weave returns",
            expr_node,
            code="E0051",
            help=f"Copy the array into a 'list of T' (heap) before slicing, or "
                 f"return the array by value.",
            note="A slice only borrows storage; a stack array's storage is "
                 "destroyed when the weave returns.",
        ))

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
        self._check_slice_stack_return(expr_node)
        self._check_value_exprs(expr_node, curr_ret)
        try:
            val_type = self.inferrer.infer(expr_node, expected_type=curr_ret)
            # 'T' is a wildcard in the value direction
            # (BaseType.is_compatible(TypeParam) is always true), so a bounded
            # parameter must be checked explicitly: 'into T' with 'T: Num' cannot
            # return a string.
            unwrapped_ret = curr_ret
            while isinstance(unwrapped_ret, (AliasType, FrozenType, SealType)):
                unwrapped_ret = getattr(unwrapped_ret, "target", None) or getattr(unwrapped_ret, "underlying", None)
            if isinstance(unwrapped_ret, TypeParam) and not self._typeparam_accepts_value(unwrapped_ret, val_type):
                err = self._make_error(
                    TypeMismatchError,
                    f"Cannot return value of type '{val_type}' from a function returning "
                    f"'{unwrapped_ret.name}' (bound: {', '.join(unwrapped_ret.bounds)})",
                    expr_node,
                    code="E0005",
                    help=f"Return a value satisfying 'where {unwrapped_ret.name}: {', '.join(unwrapped_ret.bounds)}'.",
                    note="A bounded type parameter only accepts values implementing its concepts."
                )
                self._record_error(err)
            elif curr_ret is not None and not val_type.is_compatible(curr_ret) and not isinstance(curr_ret, AnyType):
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
            if omen_t.name not in omens_seen:
                omens_seen[omen_t.name] = omen_t

        simple_owner: Dict[str, str] = {}
        full_names: Dict[str, Tuple[str, str]] = {}
        for o_logical, omen_t in omens_seen.items():
            o_cname = getattr(omen_t, "c_name", None) or o_logical
            # A 'pengu_bind' declaration emits its variants under the *simple*
            # name ('KEY_LEFT'), so the logical 'Omen_variant' name does not
            # exist in C and must not collide with a user symbol.
            o_sym = (self.symbols.global_scope.symbols.get(o_logical)
                     or self.symbols.global_scope.symbols.get(o_cname))
            from_declaration = str(getattr(o_sym, "file_path", "") or "").endswith(".d.pengu")
            for v_name in (omen_t.variants or {}):
                # Only the emitted C name (an 'insignia' prefix changes it) can
                # clash with a C symbol, so the logical name is not registered.
                if not from_declaration:
                    full_names[f"{o_cname}_{v_name}"] = (o_logical, v_name)
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
            names_to_check = [name]
            c_sym_name = getattr(sym, "c_name", None)
            if c_sym_name and c_sym_name != name:
                names_to_check.append(c_sym_name)
            for chk_name in names_to_check:
                if chk_name in simple_owner:
                    if self._const_matches_variant(sym, simple_owner[chk_name], chk_name):
                        continue
                    # A 'pengu_bind'-generated const re-declares the C enum
                    # member: same symbol as the variant, not a collision.
                    if (getattr(sym, "kind", "") == "const"
                            and getattr(sym, "const_val", None) is None
                            and str(getattr(sym, "file_path", "") or "").endswith(".d.pengu")):
                        continue
                    if getattr(sym, "kind", "") == "const":
                        clash_desc = f"top-level constant '{chk_name}'"
                        if getattr(sym, "const_val", None) is None:
                            note = ("Omen variants occupy both their simple and full names in the "
                                    f"global scope (constant '{chk_name}' value could not be folded at compile time for equality check).")
                        else:
                            note = ("Omen variants occupy both their simple and full names in the "
                                    "global scope.")
                    elif isinstance(sym.type, BaseType):
                        clash_desc = f"built-in type '{chk_name}'"
                        note = ("Built-in type names are reserved, so the variant cannot be "
                                "reached by its simple name.")
                    else:
                        clash_desc = f"top-level symbol '{chk_name}'"
                        note = ("Omen variants occupy both their simple and full names in the "
                                "global scope.")
                    err = self._make_error(
                        SemanticError,
                        f"Omen variant name '{chk_name}' of omen '{simple_owner[chk_name]}' collides "
                        f"with the {clash_desc}",
                        code="E0046",
                        help=f"Refer to the variant by its full "
                             f"'{simple_owner[chk_name]}_{chk_name}' name, or rename the conflicting "
                             "symbol.",
                        note=note,
                    )
                    self._record_error(err)
                    continue
                if chk_name in full_names:
                    o_logical, variant = full_names[chk_name]
                    if self._const_matches_variant(sym, o_logical, variant):
                        continue
                    note = "Omen variants occupy both their simple and full names in the global scope."
                    if getattr(sym, "kind", "") == "const" and getattr(sym, "const_val", None) is None:
                        note = (f"Omen variants occupy both their simple and full names in the global scope "
                                f"(constant '{chk_name}' value could not be folded at compile time for equality check).")
                    err = self._make_error(
                        SemanticError,
                        f"Top-level symbol '{chk_name}' collides with the full name of the "
                        f"'{o_logical}' omen variant",
                        code="E0046",
                        help="Rename the top-level symbol so it does not shadow the "
                             "full omen variant name.",
                        note=note
                    )
                    self._record_error(err)

        for cname, defs in getattr(self, "const_definitions", {}).items():
            if len(defs) > 1:
                first_val, first_path = defs[0]
                for other_val, other_path in defs[1:]:
                    if first_val is not None and other_val is not None and first_val != other_val:
                        if first_path == other_path:
                            err = self._make_error(
                                SemanticError,
                                f"Constant '{cname}' is redefined with conflicting values ({first_val} vs {other_val}) in '{first_path}'",
                                code="E0011",
                                help=f"Remove or rename the duplicate constant '{cname}'.",
                                note="Constants in the same module cannot be redefined with different values.",
                            )
                            self._record_error(err)
                            break
                        err = self._make_error(
                            SemanticError,
                            f"Constant '{cname}' is defined with conflicting values ({first_val} in '{first_path}' vs {other_val} in '{other_path}')",
                            code="E0046",
                            help="Ensure imported constants with the same name define identical values, or use qualified access.",
                            note="Conflicting constant values across modules cannot be resolved unambiguously.",
                        )
                        self._record_error(err)
                        break

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
        left_t: Type = AnyType()
        if node.children and isinstance(node.children[0], Tree):
            self._check_node(node.children[0])
            try:
                left_t = self.inferrer.infer(node.children[0])
            except SemanticError as e:
                self._record_error(e)
                left_t = AnyType()
            if isinstance(left_t, AnyType):
                # AnyType used to slip through and fail later, in codegen, with a
                # confusing "reached codegen with 'any' operand type".  Reject it
                # here with an actionable message instead.
                self._record_error(self._make_error(
                    SemanticError,
                    "'or:' cannot be applied to a value of unknown type 'any'",
                    node,
                    code="E0005",
                    help="Annotate the operand first (e.g. 'var m as maybe int is ...') "
                         "so the failure path has a known type.",
                    note="'or:' needs a concrete 'maybe T' / 'result of T to E' operand type.",
                ))
            elif not isinstance(left_t, (MaybeType, ResultType)):
                self._record_error(self._make_error(
                    TypeMismatchError,
                    f"'or:' requires a 'maybe T' or 'result of T to E' operand, got '{left_t}'",
                    node,
                    code="E0005",
                    help="Only maybe/result values can be unwrapped with 'or:'.",
                    note="'or:' handles the failure path of maybe/result values.",
                ))
                # Do not return early: continue checking the or: block body to accumulate all errors
        elif node.children and not isinstance(node.children[0], Tree):
            self._record_error(self._make_error(
                TypeMismatchError,
                f"'or:' requires a 'maybe T' or 'result of T to E' operand, got '{node.children[0]}'",
                node,
                code="E0005",
                help="Only maybe/result values can be unwrapped with 'or:'.",
                note="'or:' handles the failure path of maybe/result values.",
            ))
        span_start, span_end = self._get_node_span(node)
        self.symbols.push_scope(kind="or_block", in_or_block=True, start_line=span_start, end_line=span_end)
        err_t = left_t.err_type if isinstance(left_t, ResultType) else STRING_TYPE
        self.symbols.define(Symbol(name="error", type=err_t, kind="let", line=span_start, column=0, is_mutable=False))
        or_stmts = [child for child in node.children[1:] if isinstance(child, Tree)]
        self.block_stmts_stack.append(or_stmts)
        try:
            for child in or_stmts:
                self._check_node(child)

            # The fallback supplies the same value the success path produces:
            # 'maybe int or: "text"' used to be accepted and then emitted C that
            # read an int out of a string (and broke destructuring).
            ok_t = None
            if isinstance(left_t, MaybeType):
                ok_t = left_t.element
            elif isinstance(left_t, ResultType):
                ok_t = left_t.ok_type
            if ok_t is not None and not isinstance(ok_t, AnyType) and str(getattr(ok_t, "name", "")) != "void":
                v_node = self._or_block_fallback_value_node(or_stmts)
                if v_node is not None:
                    fb_t: Optional[Type] = None
                    try:
                        fb_t = self.inferrer.infer(v_node)
                    except SemanticError as e:
                        self._record_error(e)
                    if (fb_t is not None and not isinstance(fb_t, (AnyType, NullType))
                            and str(getattr(fb_t, "name", "")) != "void"
                            and not fb_t.is_compatible(ok_t)):
                        self._record_error(self._make_error(
                            TypeMismatchError,
                            f"'or:' fallback produces '{fb_t}', but the success value is '{ok_t}'",
                            v_node,
                            code="E0005",
                            help=f"The fallback must produce '{ok_t}' (or return/panic).",
                            note="Both branches of 'or:' must yield the same value type.",
                        ))
        finally:
            self.block_stmts_stack.pop()
            # Inside 'finally' so an internal failure cannot leave the scope on
            # the symbol-table stack (later diagnostics would then resolve names
            # in the wrong scope).
            self.symbols.pop_scope(end_line=span_end)

    def _or_block_fallback_value_node(self, or_stmts: List[Tree]) -> Optional[Any]:
        """AST node whose value an 'or:' fallback block produces, if any."""
        if not or_stmts:
            return None
        last = or_stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt") and last.children:
            last = last.children[0]
        if not isinstance(last, Tree):
            return None
        if last.data == "expr_stmt" and last.children:
            return last.children[0]
        if (last.data in ("if_stmt", "unless_stmt", "while_stmt", "for_range_stmt", "for_in_stmt")
                and getattr(last, "_pengu_value_type", None) is not None):
            return last
        return None
