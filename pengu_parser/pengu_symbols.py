from __future__ import annotations
import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from lark import Tree

from .pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, OPAQUE_TYPE, AliasType, AnyType,
    INT_TYPE, FLOAT_TYPE, BOOL_TYPE, STRING_TYPE, VOID_TYPE
)

from .pengu_errors import SemanticError, UndefinedIdentifierError


@dataclass
class Symbol:
    """Represents a named identifier in a scope.

    Attributes:
        name: Name of identifier.
        type: Resolved type of identifier.
        kind: Classification ('var', 'let', 'const', 'param', 'function', 'weave', 'rune', 'echo', 'omen', 'alias', 'import', 'c_define', 'declare').
        is_mutable: True if variable can be modified with set.
        is_defined_in_c: True if symbol is provided by C include headers.
        is_inline: True if function should be inlined in codegen.
        is_stack_alloc: True if struct can be allocated on stack without heap escape.
        const_val: Constant evaluated value if known at compile-time.
        line: Source line of declaration.
        column: Source column of declaration.
        doc: Optional documentation string extracted from preceding comments.
        module_scope: Optional Scope containing exported symbols if this symbol represents an imported module.
        file_path: Optional source file path where the symbol is declared.
    """
    name: str
    type: Type
    kind: str = "var"
    is_mutable: bool = False
    is_defined_in_c: bool = False
    is_inline: bool = False
    is_stack_alloc: bool = False
    const_val: Optional[Any] = None
    line: Optional[int] = None
    column: Optional[int] = None
    doc: Optional[str] = None
    module_scope: Optional[Scope] = None
    file_path: Optional[str] = None


class Scope:
    """Lexical scope holding local symbol definitions and contextual state."""

    def __init__(
        self,
        kind: str = "global",
        parent: Optional[Scope] = None,
        with_type: Optional[Type] = None,
        with_is_mutable: bool = False,
        with_target_var_name: Optional[str] = None,
        enchanting_type: Optional[Type] = None,
        return_type: Optional[Type] = None,
        in_loop: bool = False,
        in_or_block: bool = False,
        start_line: int = 0,
        end_line: int = 0,
    ):
        """Initializes a new lexical scope.

        Args:
            kind: Kind of scope ('global', 'weave', 'enchanting', 'with', 'if', 'while', 'for', 'or_block').
            parent: Parent Scope if nested, None if global.
            with_type: Active target type of enclosing with block.
            with_is_mutable: True if with target is mutable.
            with_target_var_name: Variable name of with target if addressable.
            enchanting_type: Active type being enchanted.
            return_type: Expected return type of enclosing weave.
            in_loop: True if scope is inside a loop.
            in_or_block: True if scope is inside an or: error block.
            start_line: Starting 1-indexed source line of the scope.
            end_line: Ending 1-indexed source line of the scope.
        """
        self.kind = kind
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.with_type = with_type
        self.with_is_mutable = with_is_mutable
        self.with_target_var_name = with_target_var_name
        self.enchanting_type = enchanting_type
        self.return_type = return_type
        self.in_loop = in_loop
        self.in_or_block = in_or_block
        self.start_line = start_line
        self.end_line = end_line

    def define(self, symbol: Symbol) -> None:
        """Defines a symbol in this local scope.

        Args:
            symbol: Symbol definition to add.
        """
        self.symbols[symbol.name] = symbol

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Looks up symbol strictly in this local scope.

        Args:
            name: Identifier name to search.

        Returns:
            Matching Symbol or None.
        """
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Looks up symbol in this scope and recursively in parent scopes.

        Args:
            name: Identifier name to search.

        Returns:
            Matching Symbol or None.
        """
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None


class SymbolTable:
    """Manages the full hierarchy of lexical scopes and top-level definitions."""

    def __init__(self):
        """Initializes global scope, builtins, and symbol registries."""
        self.global_scope = Scope(kind="global", start_line=0, end_line=9999999)
        self.current_scope = self.global_scope
        self.all_scopes: List[Scope] = [self.global_scope]
        self.runes: Dict[str, RuneType] = {}
        self.echos: Dict[str, EchoType] = {}
        self.omens: Dict[str, OmenType] = {}
        self.aliases: Dict[str, AliasType] = {}
        self.functions: Dict[str, FnType] = {}
        self.methods: Dict[Tuple[str, str], FnType] = {}
        self.consts: Dict[str, Tuple[Optional[Type], Any]] = {}

        # Generic templates: name -> (type_params, AST node)
        self.generic_runes: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_echos: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_omens: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_aliases: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_functions: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_methods: Dict[Tuple[str, str], Tuple[List[str], Any]] = {}

        # Monomorphized instances: mangled_name -> instance
        self.monomorphized_types: Dict[str, Type] = {}
        self.monomorphized_functions: Dict[str, Tuple[Any, Dict[str, Type]]] = {}
        self.monomorphized_methods: Dict[str, Tuple[Any, Dict[str, Type]]] = {}
        self._generated_instances: Set[str] = set()

        self.has_includes: bool = False
        self.includes: List[str] = []
        self.links: List[str] = []
        self.imports: List[str] = []
        self.imported_modules: Set[str] = set()
        self.import_graph: Dict[str, List[str]] = {}
        self.import_order: List[str] = []

        self._init_builtins()

    def _init_builtins(self) -> None:
        """Initializes built-in primitive type symbols in global scope."""
        builtins: List[Tuple[str, Type]] = [
            ("int", BaseType("int")),
            ("i32", BaseType("i32")),
            ("i64", BaseType("i64")),
            ("float", BaseType("float")),
            ("f32", BaseType("f32")),
            ("f64", BaseType("f64")),
            ("bool", BaseType("bool")),
            ("string", BaseType("string")),
            ("void", BaseType("void")),
            ("opaque", OPAQUE_TYPE),
        ]
        for name, t in builtins:
            self.global_scope.define(Symbol(name=name, type=t, kind="type"))
        self.global_scope.define(Symbol(
            name="print",
            type=FnType(params=[("val", AnyType())], return_type=VOID_TYPE),
            kind="function"
        ))


    def push_scope(self, kind: str, **kwargs) -> Scope:
        """Creates and pushes a new child lexical scope.

        Handles context inheritance for loops, enchanting, return types, and 'with' bindings.

        Args:
            kind: Type of scope ('weave', 'enchanting', 'with', 'if', 'while', 'for', 'or_block').
            **kwargs: Overriding parameters (return_type, enchanting_type, with_type, with_target_var_name, in_loop, start_line, end_line, etc.).

        Returns:
            The newly created and entered Scope.
        """
        in_loop = kwargs.get("in_loop", self.current_scope.in_loop or (kind in ("while", "for")))
        in_or_block = kwargs.get("in_or_block", self.current_scope.in_or_block or (kind == "or_block"))
        return_type = kwargs.get("return_type", self.current_scope.return_type)
        enchanting_type = kwargs.get("enchanting_type", self.current_scope.enchanting_type)
        start_line = kwargs.get("start_line", 0)
        end_line = kwargs.get("end_line", 0)

        if kind == "with":
            with_type = kwargs.get("with_type", None)
            with_is_mutable = kwargs.get("with_is_mutable", False)
            with_target_var_name = kwargs.get("with_target_var_name", None)
        elif kind in ("weave", "enchanting"):
            with_type = None
            with_is_mutable = False
            with_target_var_name = None
        else:
            with_type = kwargs.get("with_type", self.current_scope.with_type)
            with_is_mutable = kwargs.get("with_is_mutable", self.current_scope.with_is_mutable)
            with_target_var_name = kwargs.get("with_target_var_name", self.current_scope.with_target_var_name)

        new_scope = Scope(
            kind=kind,
            parent=self.current_scope,
            with_type=with_type,
            with_is_mutable=with_is_mutable,
            with_target_var_name=with_target_var_name,
            enchanting_type=enchanting_type,
            return_type=return_type,
            in_loop=in_loop,
            in_or_block=in_or_block,
            start_line=start_line,
            end_line=end_line,
        )
        self.current_scope = new_scope
        if new_scope not in self.all_scopes:
            self.all_scopes.append(new_scope)

        if enchanting_type is not None and kind == "enchanting":
            self.current_scope.define(Symbol(
                name="self",
                type=RefType(target=enchanting_type),
                kind="param",
                is_mutable=False,
            ))
        return new_scope

    def pop_scope(self, end_line: Optional[int] = None) -> Scope:
        """Exits the current scope and restores parent scope.

        Args:
            end_line: Optional ending source line for the scope block.

        Returns:
            The popped Scope.
        """
        if self.current_scope.parent is not None:
            old = self.current_scope
            if end_line is not None and end_line > 0:
                old.end_line = end_line
            if old not in self.all_scopes:
                self.all_scopes.append(old)
            self.current_scope = self.current_scope.parent
            return old
        return self.current_scope

    def lookup_at(self, name: str, line: int) -> Optional[Symbol]:
        """Looks up a symbol at a specific source line by checking matching scopes.

        Args:
            name: Identifier name to search.
            line: Source line number (1-indexed).

        Returns:
            Matching Symbol or None.
        """
        # Find all scopes that contain the line, sorted by most specific (narrowest span) first
        matching_scopes = []
        for scope in self.all_scopes:
            if scope.start_line <= line <= scope.end_line:
                span = (scope.end_line - scope.start_line) if (scope.end_line >= scope.start_line and scope.start_line > 0) else 999999
                matching_scopes.append((span, scope))

        # Sort by narrowest span first
        matching_scopes.sort(key=lambda s: s[0])

        for _, scope in matching_scopes:
            if name in scope.symbols:
                return scope.symbols[name]

        # Fallback to global symbol table lookup
        return self.lookup(name)

    def define(self, symbol: Symbol) -> None:
        """Defines a symbol in the current scope.

        Args:
            symbol: Symbol to define.
        """
        self.current_scope.define(symbol)

    def get_all_visible_names(self) -> List[str]:
        """Returns all identifier names accessible from current scope and global tables."""
        names = set()
        sc = self.current_scope
        while sc is not None:
            names.update(sc.symbols.keys())
            sc = sc.parent
        names.update(self.global_scope.symbols.keys())
        names.update(self.functions.keys())
        names.update(self.runes.keys())
        names.update(self.echos.keys())
        names.update(self.omens.keys())
        names.update(self.aliases.keys())
        names.update(self.consts.keys())
        return list(names)

    def lookup(self, name: str) -> Optional[Symbol]:
        """Looks up symbol in current and enclosing scopes or uppercase C defines.

        Args:
            name: Identifier name to search.

        Returns:
            Matching Symbol or None.
        """
        sym = self.current_scope.lookup(name)
        if sym is not None:
            return sym

        if name.isupper() and self.has_includes:
            return Symbol(name=name, type=INT_TYPE, kind="c_define", is_defined_in_c=True)
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Looks up symbol strictly in the current scope.

        Args:
            name: Identifier name to search.

        Returns:
            Matching local Symbol or None.
        """
        return self.current_scope.lookup_local(name)

    def lookup_type(self, name: str) -> Optional[Type]:
        """Resolves type name across aliases, runes, echos, and omens.

        Args:
            name: Name of custom type.

        Returns:
            Resolved Type object or None.
        """
        if name in self.monomorphized_types:
            return self.monomorphized_types[name]
        if name in self.aliases:
            return self.aliases[name]
        if name in self.runes:
            return self.runes[name]
        if name in self.echos:
            return self.echos[name]
        if name in self.omens:
            return self.omens[name]
        sym = self.lookup(name)
        if sym and sym.kind in ("type", "rune", "echo", "omen", "alias"):
            return sym.type
        if name.isupper() and self.has_includes:
            return BaseType(name=name)
        return None

    def is_top_level(self) -> bool:
        """Returns True if current scope is the global top-level scope."""
        return self.current_scope == self.global_scope

    def is_in_loop(self) -> bool:
        """Returns True if current execution context is inside a loop."""
        return self.current_scope.in_loop

    def is_in_or_block(self) -> bool:
        """Returns True if current context is inside an 'or:' block."""
        return self.current_scope.in_or_block

    def is_in_enchanting(self) -> bool:
        """Returns True if currently within an enchanting block."""
        return self.current_scope.enchanting_type is not None

    def current_enchanting_type(self) -> Optional[Type]:
        """Returns the type being enchanted in the current context."""
        return self.current_scope.enchanting_type

    def current_with_type(self) -> Optional[Type]:
        """Returns the active target type of the enclosing 'with' statement."""
        return self.current_scope.with_type

    def current_with_is_mutable(self) -> bool:
        """Returns True if active 'with' target is mutable."""
        return self.current_scope.with_is_mutable

    def current_with_target_var_name(self) -> Optional[str]:
        """Returns variable name of active 'with' target if known."""
        return self.current_scope.with_target_var_name

    def current_return_type(self) -> Optional[Type]:
        """Returns the expected return type of the enclosing weave function."""
        return self.current_scope.return_type


def get_stdlib_dirs(base_abs: str) -> List[str]:
    """Returns list of candidate directories containing standard library modules."""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    meipass = getattr(sys, "_MEIPASS", "")
    candidates = [
        os.path.join(base_abs, "std"),
        os.path.join(exe_dir, "std"),
        os.path.join(exe_dir, "..", "std"),
        os.path.join(meipass, "std") if meipass else "",
        os.path.join(os.path.dirname(__file__), "std"),
        os.path.join(os.path.dirname(__file__), "..", "std"),
        os.path.join(os.path.expanduser("~"), ".pengu", "std"),
    ]
    if os.environ.get("PENGU_STD_PATH"):
        candidates.insert(0, os.environ["PENGU_STD_PATH"])
    return [os.path.abspath(p) for p in candidates if p and os.path.isdir(p)]


def find_module_path(base_dir: str, dot_path: str, from_dir: Optional[str] = None) -> Optional[str]:
    """Finds candidate file for a dotted import path.

    Args:
        base_dir: Base directory path.
        dot_path: Dotted module import path (e.g. 'std.spark' or 'my_module').
        from_dir: Optional directory of the importing file.

    Returns:
        Resolved absolute file path string, or None if not found.
    """
    base_abs = os.path.abspath(base_dir) if base_dir else os.getcwd()
    from_abs = os.path.abspath(from_dir) if from_dir else base_abs
    parts = dot_path.split(".")
    is_std = parts[0] == "std"
    candidates = []

    if is_std:
        rel_without_std = parts[1:]
        stdlib_dirs = get_stdlib_dirs(base_abs)
        for std_dir in stdlib_dirs:
            if rel_without_std:
                candidates.append(os.path.join(std_dir, *rel_without_std) + ".pengu")
                candidates.append(os.path.join(std_dir, *rel_without_std, "__init__.pengu"))
            else:
                candidates.append(os.path.join(std_dir, "__init__.pengu"))

        if rel_without_std:
            candidates.append(os.path.join(base_abs, "std", *rel_without_std) + ".pengu")
            candidates.append(os.path.join(base_abs, "std", *rel_without_std, "__init__.pengu"))
        else:
            candidates.append(os.path.join(base_abs, "std", "__init__.pengu"))

    candidates.extend([
        os.path.join(base_abs, *parts) + ".pengu",
        os.path.join(base_abs, *parts, "__init__.pengu"),
        os.path.join(from_abs, *parts) + ".pengu",
        os.path.join(from_abs, *parts, "__init__.pengu"),
    ])

    for cand in candidates:
        if os.path.isfile(cand):
            return os.path.abspath(cand)

    return None


def resolve_imports(base_dir: str, entry_file: str, parser: Optional[Any] = None) -> List[str]:
    """Resolves all module dependencies starting from an entry point and returns topological order.

    Args:
        base_dir: Base directory path containing source modules.
        entry_file: Relative or absolute path to the main entry file.
        parser: Optional PenguParser instance for parsing import ASTs.
    """
    if parser is None:
        from .pengu_parser import PenguParser
        parser = PenguParser()

    entry_abs = os.path.abspath(os.path.join(base_dir, entry_file)) if not os.path.isabs(entry_file) else os.path.abspath(entry_file)
    base_abs = os.path.abspath(base_dir)

    def extract_imports(file_path: str) -> List[str]:
        """Parses a file and extracts all its direct module imports."""
        if not os.path.isfile(file_path):
            raise SemanticError(f"Module file not found: {file_path}", code="E0004")
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        tree = parser.parse(code)
        deps: List[str] = []

        def walk(node):
            if isinstance(node, Tree):
                if node.data == "import_stmt":
                    path_tree = node.children[0]
                    dot_path = ".".join(str(t) for t in path_tree.children)
                    mod_path = find_module_path(base_abs, dot_path, from_dir=os.path.dirname(file_path))
                    if not mod_path:
                        raise SemanticError(
                            f"Cannot resolve imported module '{dot_path}'",
                            code="E0004",
                            help=f"Ensure '{dot_path}.pengu' exists in source directory '{base_dir}' or stdlib.",
                            note="PenguScript module files must match import path."
                        )
                    deps.append(mod_path)
                for child in node.children:
                    walk(child)

        walk(tree)
        return deps

    visited: Set[str] = set()
    visiting: Set[str] = set()
    order: List[str] = []

    def dfs(node: str, path: List[str]):
        """Performs three-color DFS to detect cycles and topologically sort dependencies."""
        if node in visiting:
            cycle_nodes = path + [node]
            cycle_str = " -> ".join([os.path.basename(p) for p in cycle_nodes])
            raise SemanticError(
                f"Circular dependency detected in imports: {cycle_str}",
                code="E0004",
                help=f"Remove circular import: {cycle_str}",
                note="PenguScript forbids circular module dependencies to guarantee deterministic compilation."
            )
        if node not in visited:
            visiting.add(node)
            dep_files = extract_imports(node)
            for dep in dep_files:
                dfs(dep, path + [node])
            visiting.remove(node)
            visited.add(node)
            order.append(node)

    dfs(entry_abs, [])
    return order
