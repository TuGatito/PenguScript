from __future__ import annotations
import hashlib
import os
import sys
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from lark import Tree, Token

from .pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, OPAQUE_TYPE, AliasType, AnyType,
    ConceptType, SealType,
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
        is_ritual: True if function or symbol is considered a ritual (e.g. comptime/macro).
        const_val: Constant evaluated value if known at compile-time.
        line: Source line of declaration.
        column: Source column of declaration.
        doc: Optional documentation string extracted from preceding comments.
        module_scope: Optional Scope containing exported symbols if this symbol represents an imported module.
        file_path: Optional source file path where the symbol is declared.
        c_name: Optional custom C identifier (e.g. from 'insignia' module prefix).
        concept_bounds: List of concepts that this type must implement.
    """
    name: str
    type: Type
    kind: str = "var"
    is_mutable: bool = False
    is_defined_in_c: bool = False
    is_inline: bool = False
    is_ritual: bool = False
    is_static: bool = False
    const_val: Optional[Any] = None
    line: Optional[int] = None
    column: Optional[int] = None
    doc: Optional[str] = None
    module_scope: Optional[Scope] = None
    file_path: Optional[str] = None
    c_name: Optional[str] = None
    concept_bounds: List[str] = field(default_factory=list)
    is_public: bool = False
    attributes: Dict[str, List[Any]] = field(default_factory=dict)
    #: True when the callable was declared with `antiquus`: its `kind` is still
    #: "weave" (call resolution is identical) but its body is literal C, so the
    #: LSP warns instead of presenting it as type-checked PenguScript.
    is_antiquus: bool = False

    def get_c_name(self) -> str:
        """Returns effective C identifier for this symbol."""
        return self.c_name or self.name


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
        is_ritual: bool = False,
        start_line: int = 0,
        end_line: int = 0,
        loop_label: Optional[str] = None,
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
            is_ritual: True if scope is inside a ritual method.
            start_line: Starting 1-indexed source line of the scope.
            end_line: Ending 1-indexed source line of the scope.
            loop_label: Label of the loop this scope belongs to ('outer:' in
                'outer: for …'), or None for an unlabeled loop.
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
        self.is_ritual = is_ritual
        self.start_line = start_line
        self.end_line = end_line
        self.loop_label = loop_label
        #: Labels declared directly in this scope when it is a function body
        #: (weave / enchanting method): label name -> declaring AST node.  Loop
        #: labels are unique per function (E0069), so they are tracked on the
        #: function scope rather than on the global symbol table.
        self.loop_labels: Dict[str, Any] = {}

    def define(self, symbol: Symbol) -> None:
        """Defines a symbol in this local scope.

        Args:
            symbol: Symbol definition to add.
        """
        if not symbol.name.startswith("_"):
            symbol.is_public = True
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


#: Pseudo receiver key for ``enchanting shard T where T: …:`` methods.
#:
#: A bare shard receiver has no type name to key on, and it is not a primitive
#: either: it is *one* declaration that applies to every type satisfying the
#: bounds.  It therefore gets a key of its own, shared by the checker (where the
#: method is registered), the inferrer (which substitutes the concrete receiver
#: at each call site) and the code generator (which emits one C function per
#: instantiation: ``int_is_even``, ``i64_is_even``).
SHARD_RECEIVER_KEY = "__shard__"


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
        self.seals: Dict[str, SealType] = {}
        self.concepts: Dict[str, ConceptType] = {}
        self.concept_bindings: Dict[Tuple[str, str], Dict[str, FnType]] = {}
        self.functions: Dict[str, FnType] = {}
        self.methods: Dict[Tuple[str, str], FnType] = {}
        self.consts: Dict[str, Tuple[Optional[Type], Any]] = {}
        #: Names registered in the type/function registries *because a module
        #: was imported* (alias-prefixed and C-name spellings).  Completion uses
        #: this to keep an import's whole surface out of the plain identifier
        #: list: `import std.loom` used to add every `loom_*` function/type to
        #: each keystroke's completion, thousands of irrelevant items.
        self.imported_names: Set[str] = set()

        # Generic templates: name -> (type_params, AST node)
        self.generic_runes: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_echos: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_omens: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_aliases: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_concepts: Dict[str, Tuple[List[str], Any]] = {}
        self.generic_functions: Dict[str, Tuple[List[str], Any]] = {}
        #: generic function name -> source file that *defines* it. The
        #: generic table is keyed by both the bare name and module-qualified
        #: names, so a bare key is ambiguous once two modules declare the same
        #: name; this records which module an entry actually came from, which
        #: is what stops one module's generic being attributed to another.
        self.generic_function_owner: Dict[str, str] = {}
        # (receiver_type_params, method_type_params, method_ast).  Older
        # 2-tuples (concatenated params, ast) are still accepted by readers.
        self.generic_methods: Dict[Tuple[str, str], Tuple[List[str], ...]] = {}
        # Coherence: (type, method) -> concept that provides it.  Used to reject
        # two different 'bind' blocks implementing the same method on a type.
        self.bind_method_owner: Dict[Tuple[str, str], str] = {}
        # Coherence for `enchanting int:` methods (Phase 2):
        # (canonical primitive name, method) -> (source file, line) that declared
        # it.  Two modules attaching `clamp` to `int` would both emit the C symbol
        # `int_clamp`, so the pair may only be provided once in the whole program
        # (E0047).  The line is what keeps a re-check of the same file idempotent.
        self.primitive_method_owners: Dict[Tuple[str, str], Tuple[str, Optional[int]]] = {}
        # Bounds declared on a `shard T` method: (SHARD_RECEIVER_KEY, method) ->
        # {type param: [concept, ...]}.  The inferrer enforces them when it
        # monomorphizes for a concrete receiver (`float.is_even` against
        # `where T: Integrum` is E0005, not a C error).
        self.shard_method_bounds: Dict[Tuple[str, str], Dict[str, List[str]]] = {}

        # '@mutates' methods, keyed like `methods`: (receiver key, method name).
        # The value records the two surface forms of the single C function:
        #   * the bare name  -> the call site assigns the result to the receiver;
        #   * 'get_<name>'   -> the pure form, registered in `methods` so ordinary
        #                       expression inference resolves it.
        # `mutating_methods` drives the statement rewrite and E0066; the same
        # entry under the 'get_<name>' key drives the codegen alias lookup.
        self.mutating_methods: Dict[Tuple[str, str], Dict[str, Any]] = {}

        # Monomorphized instances: mangled_name -> instance
        self.monomorphized_types: Dict[str, Type] = {}
        self.monomorphized_functions: Dict[str, Tuple[Any, Dict[str, Type]]] = {}
        self.monomorphized_methods: Dict[str, Tuple[Any, Dict[str, Type]]] = {}
        self._generated_instances: Set[str] = set()

        self.has_includes: bool = False
        self.includes: List[str] = []
        self.links: List[str] = []
        # Raw linker options contributed by a binding (`ldflag "..."`).  These
        # are the flags a C library needs but `link "..."` cannot express, such
        # as Emscripten's `-sUSE_GLFW=3` port selector.
        self.ldflags: List[str] = []
        self.imports: List[str] = []
        self.imported_modules: Set[str] = set()
        self.import_graph: Dict[str, List[str]] = {}
        self.import_order: List[str] = []
        self.insignia: Optional[str] = None

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
        from .pengu_types import BUILTIN_CONCEPTS
        for cname, ctype in BUILTIN_CONCEPTS.items():
            self.concepts[cname] = ctype
            self.global_scope.define(Symbol(name=cname, type=ctype, kind="concept"))


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

        is_ritual = kwargs.get("is_ritual", False)

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
            is_ritual=is_ritual,
            start_line=start_line,
            end_line=end_line,
            loop_label=kwargs.get("loop_label"),
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
        """Resolves type name across aliases, seals, concepts, runes, echos, and omens.

        Args:
            name: Name of custom type.

        Returns:
            Resolved Type object or None.
        """
        if name in self.monomorphized_types:
            return self.monomorphized_types[name]
        if name in self.aliases:
            return self.aliases[name]
        if name in self.seals:
            return self.seals[name]
        if name in self.concepts:
            return self.concepts[name]
        if name in self.runes:
            return self.runes[name]
        if name in self.echos:
            return self.echos[name]
        if name in self.omens:
            return self.omens[name]
        sym = self.lookup(name)
        if sym and sym.kind in ("type", "rune", "echo", "omen", "alias", "seal", "concept"):
            return sym.type
        # Dotted references to imported module types: `rl.Rectangle` resolves
        # to the type registered under the import-prefixed name (`rl_Rectangle`)
        # or through the import symbol's own module scope.
        if "." in name:
            parts = name.split(".")
            joined = "_".join(parts)
            if joined in self.monomorphized_types:
                return self.monomorphized_types[joined]
            if joined in self.aliases:
                return self.aliases[joined]
            if joined in self.seals:
                return self.seals[joined]
            if joined in self.concepts:
                return self.concepts[joined]
            if joined in self.runes:
                return self.runes[joined]
            if joined in self.echos:
                return self.echos[joined]
            if joined in self.omens:
                return self.omens[joined]
            if len(parts) == 2:
                alias_sym = self.lookup(parts[0])
                mod_scope = getattr(alias_sym, "module_scope", None) if alias_sym else None
                if mod_scope is not None:
                    member = mod_scope.symbols.get(parts[1])
                    if member is not None and member.type is not None:
                        return member.type
        if name.isupper() and self.has_includes:
            return BaseType(name=name)
        return None

    def lookup_concept(self, name: str) -> Optional[ConceptType]:
        """Looks up a concept type definition by name."""
        if name in self.concepts:
            return self.concepts[name]
        sym = self.lookup(name)
        if sym and isinstance(sym.type, ConceptType):
            return sym.type
        return None

    def lookup_seal(self, name: str) -> Optional[SealType]:
        """Looks up a seal type definition by name."""
        if name in self.seals:
            return self.seals[name]
        sym = self.lookup(name)
        if sym and isinstance(sym.type, SealType):
            return sym.type
        return None

    def is_top_level(self) -> bool:
        """Returns True if current scope is the global top-level scope."""
        return self.current_scope == self.global_scope

    def is_in_loop(self) -> bool:
        """Returns True if current execution context is inside a loop."""
        return self.current_scope.in_loop

    def current_function_scope(self) -> "Scope":
        """Returns the innermost weave / enchanting body scope.

        Loop labels are unique per *function*, so they are recorded on this
        scope.  Falls back to the global scope for top-level code (where a loop
        cannot appear anyway).
        """
        sc = self.current_scope
        while sc is not None:
            # A lambda body is emitted as its own C function, so it is a function
            # boundary for labels too (`kind == "lambda"`).
            if sc.kind in ("weave", "enchanting", "lambda"):
                return sc
            sc = sc.parent
        return self.global_scope

    def enclosing_loop_label(self, label: str) -> Optional["Scope"]:
        """Returns the scope of the nearest enclosing loop labeled ``label``.

        Walks the lexical scope chain outwards; only scopes created by a
        ``label: for/while`` carry a ``loop_label``, so an unlabeled loop or a
        label from a sibling loop never matches.
        """
        sc = self.current_scope
        while sc is not None:
            if getattr(sc, "loop_label", None) == label:
                return sc
            if sc.kind == "lambda":
                # A lambda body is a separate C function: a `break`/`goto` there
                # cannot reach a loop of the enclosing weave.
                return None
            sc = sc.parent
        return None

    def declare_loop_label(self, label: Optional[str], node: Any) -> bool:
        """Records ``label`` on the current function scope.

        Returns:
            True when the label was free, False when the same name was already
            declared in this function (the caller reports E0069).  Re-declaring
            the *same* node is not a conflict: a value block may be checked more
            than once.
        """
        if not label:
            return True
        fn_scope = self.current_function_scope()
        previous = fn_scope.loop_labels.get(label)
        if previous is not None and previous is not node:
            return False
        fn_scope.loop_labels[label] = node
        return True

    def is_in_or_block(self) -> bool:
        """Returns True if current context is inside an 'or:' block."""
        return self.current_scope.in_or_block

    def is_in_enchanting(self) -> bool:
        """Returns True if currently within an enchanting block."""
        return self.current_scope.enchanting_type is not None

    def is_in_ritual_context(self) -> bool:
        """Returns True if current execution context is inside a ritual method."""
        sc = self.current_scope
        while sc is not None:
            if getattr(sc, "is_ritual", False):
                return True
            if sc.kind in ("weave", "declare") and sc != self.current_scope:
                break
            sc = sc.parent
        return False

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
    candidates: List[str] = []
    try:
        from pengu_paths import std_dirs
        for d in std_dirs():
            s = str(d)
            if os.path.isdir(s):
                ap = os.path.abspath(s)
                if ap not in candidates:
                    candidates.append(ap)
    except ImportError:
        pass

    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    meipass = getattr(sys, "_MEIPASS", "")
    legacy_candidates = [
        os.path.join(base_abs, "std"),
        os.path.join(exe_dir, "std"),
        os.path.join(exe_dir, "..", "std"),
        os.path.join(meipass, "std") if meipass else "",
        os.path.join(os.path.dirname(__file__), "std"),
        os.path.join(os.path.dirname(__file__), "..", "std"),
        os.path.join(os.path.expanduser("~"), ".pengu", "std"),
    ]
    env_std = os.environ.get("PENGU_STD_DIR") or os.environ.get("PENGU_STD_PATH")
    if env_std:
        legacy_candidates.insert(0, env_std)
    for p in legacy_candidates:
        if p and os.path.isdir(p):
            ap = os.path.abspath(p)
            if ap not in candidates:
                candidates.append(ap)
    return candidates


def find_module_path(base_dir: str, dot_path: str, from_dir: Optional[str] = None,
                     lib_dir: str = "lib", src_dir: str = "src") -> Optional[str]:
    """Finds candidate file for a dotted import path.

    Searches in:
    1. Standard library candidate directories (if dot_path starts with 'std').
    2. Relative to the importing file's directory (from_dir).
    3. Project source directory (base_dir/<src_dir>/); ``src_dir`` comes from the
       project's manifest and defaults to 'src'. A project that keeps its
       modules elsewhere (``src_dir = "pengu"``) still resolves them here, which
       is what lets a document outside that directory `import` them.
    4. External bindings directory (base_dir/<lib_dir>/<binding>/pengu/ and
       base_dir/<lib_dir>/<binding>/); ``lib_dir`` comes from the project's
       ``pengu.yaml`` and defaults to 'lib'.
    5. Project root directory (base_dir/).

    Args:
        base_dir: Base directory path of project.
        dot_path: Dotted module import path (e.g. 'std.spark' or 'player').
        from_dir: Optional directory of the importing file.
        lib_dir: External bindings directory name (pengu.yaml 'lib_dir').
        src_dir: Project source directory name (pengu.yaml 'src_dir').

    Returns:
        Resolved absolute file path string, or None if not found.
    """
    base_abs = os.path.abspath(base_dir) if base_dir else os.getcwd()
    from_abs = os.path.abspath(from_dir) if from_dir else base_abs
    parts = dot_path.split(".")
    is_std = parts[0] == "std"
    candidates: List[str] = []

    def _add_candidates(prefix: str):
        candidates.append(prefix + ".pengu")
        candidates.append(prefix + ".d.pengu")
        candidates.append(os.path.join(prefix, "__init__.pengu"))
        candidates.append(os.path.join(prefix, "__init__.d.pengu"))

    # 1. Standard library
    if is_std:
        rel_without_std = parts[1:]
        stdlib_dirs = get_stdlib_dirs(base_abs)
        for std_dir in stdlib_dirs:
            if rel_without_std:
                _add_candidates(os.path.join(std_dir, *rel_without_std))
            else:
                candidates.append(os.path.join(std_dir, "__init__.pengu"))
                candidates.append(os.path.join(std_dir, "__init__.d.pengu"))

        if rel_without_std:
            _add_candidates(os.path.join(base_abs, "std", *rel_without_std))
        else:
            candidates.append(os.path.join(base_abs, "std", "__init__.pengu"))
            candidates.append(os.path.join(base_abs, "std", "__init__.d.pengu"))

    # 2. Relative to importing directory (from_dir)
    if from_dir:
        _add_candidates(os.path.join(from_abs, *parts))

    # 3. Project source directory (manifest 'src_dir', default 'src')
    src_root = os.path.join(base_abs, src_dir or "src")
    if os.path.isdir(src_root):
        _add_candidates(os.path.join(src_root, *parts))
        if parts[0] == src_dir:
            _add_candidates(os.path.join(base_abs, *parts))

    # 4. Project external bindings directory (pengu.yaml 'lib_dir', default 'lib')
    lib_root = os.path.join(base_abs, lib_dir or "lib")
    if os.path.isdir(lib_root):
        binding_name = parts[0]
        binding_rest = parts[1:]
        binding_folder = os.path.join(lib_root, binding_name)

        if os.path.isdir(binding_folder):
            if binding_rest:
                _add_candidates(os.path.join(binding_folder, "pengu", *binding_rest))
                _add_candidates(os.path.join(binding_folder, *binding_rest))
            else:
                candidates.extend([
                    os.path.join(binding_folder, "pengu", f"{binding_name}.pengu"),
                    os.path.join(binding_folder, "pengu", f"{binding_name}.d.pengu"),
                    os.path.join(binding_folder, "pengu", "__init__.pengu"),
                    os.path.join(binding_folder, "pengu", "__init__.d.pengu"),
                    os.path.join(binding_folder, "pengu", "main.pengu"),
                    os.path.join(binding_folder, "pengu", "main.d.pengu"),
                    os.path.join(binding_folder, f"{binding_name}.pengu"),
                    os.path.join(binding_folder, f"{binding_name}.d.pengu"),
                    os.path.join(binding_folder, "__init__.pengu"),
                    os.path.join(binding_folder, "__init__.d.pengu"),
                ])

        # Also search across all <lib_dir>/*/pengu/ and <lib_dir>/*/ for matching module
        try:
            for entry in os.scandir(lib_root):
                if entry.is_dir():
                    _add_candidates(os.path.join(entry.path, "pengu", *parts))
                    _add_candidates(os.path.join(entry.path, *parts))
        except Exception:
            pass

    # 5. Project root directory (backward compatibility)
    _add_candidates(os.path.join(base_abs, *parts))

    for cand in candidates:
        if os.path.isfile(cand):
            return os.path.abspath(cand)

    return None


def companion_binding_path(module_path: str) -> Optional[str]:
    """Returns the companion declaration file of a module, when it exists.

    A wrapper module (``foo.pengu``) may carry its raw C declarations in a
    sibling ``foo.d.pengu``. Only the wrapper is reachable through
    ``import foo`` — ``find_module_path`` tries the non-declaration spelling
    first — so the declaration file would never be compiled on its own. The
    resolver adds it as an implicit dependency of the wrapper: the declarations
    become visible to the wrapper and the bundle receives the
    ``include``/``link`` lines exactly when the wrapper is imported. That keeps
    the binding internal without a second public module name.

    Args:
        module_path: Resolved path of a module file.

    Returns:
        Absolute path of the sibling ``<stem>.d.pengu`` file, or None when the
        module is itself a declaration file or no companion exists.
    """
    if not module_path.endswith(".pengu") or module_path.endswith(".d.pengu"):
        return None
    candidate = module_path[: -len(".pengu")] + ".d.pengu"
    if os.path.isfile(candidate):
        return os.path.abspath(candidate)
    return None


# ---------------------------------------------------------------------------
# Module parsing and import-graph caches
# ---------------------------------------------------------------------------
#
# A language server re-checks a buffer on every pause in typing.  Resolving its
# imports used to re-parse the *whole* transitive import graph each time: a
# 2 000-line document importing five std modules parsed 46 files for one check.
# Parsed trees are immutable while the checker collects symbols from them, so
# they can be shared for as long as the file they came from does not change.
# The key carries the file signature (mtime + size), or a content hash for an
# unsaved editor buffer, which makes every entry self-invalidating.
_MODULE_TREE_CACHE: Dict[Any, Tree] = {}
_MODULE_TREE_CACHE_MAX = 512


def module_source_signature(path: str, source: Optional[str] = None) -> Tuple[Any, ...]:
    """Returns a cache key/version for a module's source text.

    Args:
        path: Module file path (made absolute).
        source: In-memory text (an unsaved editor buffer), or None to use the
            file on disk.

    Returns:
        A tuple that differs whenever the content that would be parsed differs.
        For files on disk it is ``(abspath, mtime_ns, size)``; for in-memory
        text it is ``(abspath, "mem", length, sha1)`` so an override can never
        collide with the disk version of the same path.
    """
    abs_path = os.path.abspath(path)
    if source is not None:
        digest = hashlib.sha1(source.encode("utf-8", "replace")).hexdigest()
        return (abs_path, "mem", len(source), digest)
    st = os.stat(abs_path)
    return (abs_path, st.st_mtime_ns, st.st_size)


def cached_module_tree(path: str, parser: Any, source: Optional[str] = None) -> Tree:
    """Parses a module once per content signature.

    Args:
        path: Module file path.
        parser: A :class:`PenguParser` instance.
        source: In-memory text to parse instead of the file on disk.

    Returns:
        The parsed tree (shared, so callers must treat it as read-only).
    """
    abs_path = os.path.abspath(path)
    try:
        key = module_source_signature(abs_path, source)
    except OSError:
        # Missing file: let the parser/reader raise the contextual error rather
        # than caching an exception.
        if source is None:
            with open(abs_path, "r", encoding="utf-8") as handle:
                source = handle.read()
        return parser.parse(source)
    hit = _MODULE_TREE_CACHE.get(key)
    if hit is not None:
        return hit
    if source is None:
        with open(abs_path, "r", encoding="utf-8") as handle:
            source = handle.read()
    tree = parser.parse(source)
    if len(_MODULE_TREE_CACHE) >= _MODULE_TREE_CACHE_MAX:
        _MODULE_TREE_CACHE.clear()
    _MODULE_TREE_CACHE[key] = tree
    return tree


def clear_module_tree_cache() -> None:
    """Drops every parsed-module tree and cached import order."""
    _MODULE_TREE_CACHE.clear()
    _IMPORT_ORDER_CACHE.clear()


#: ``(base, entry, lib_dir, src_dir) -> (versions, order)``.  ``versions`` is
#: the signature of every file in the order, so adding an import to a dependency
#: (which changes that file's mtime) invalidates the cached order.
_IMPORT_ORDER_CACHE: Dict[Any, Tuple[Tuple[Tuple[Any, ...], ...], List[str]]] = {}
_IMPORT_ORDER_CACHE_MAX = 128


def _resolve_module_text(path: str, entry_abs: str, entry_source: Optional[str],
                         module_sources: Optional[Dict[str, str]]) -> Optional[str]:
    """In-memory text for ``path`` (entry or open buffer), else None."""
    abs_path = os.path.abspath(path)
    if entry_source is not None and abs_path == entry_abs:
        return entry_source
    if module_sources:
        override = module_sources.get(abs_path)
        if override is not None:
            return override
    return None


def resolve_imports(base_dir: str, entry_file: str, parser: Optional[Any] = None,
                    lib_dir: str = "lib", src_dir: str = "src",
                    entry_source: Optional[str] = None,
                    module_sources: Optional[Dict[str, str]] = None) -> List[str]:
    """Resolves all module dependencies starting from an entry point and returns topological order.

    Args:
        base_dir: Base directory path containing source modules.
        entry_file: Relative or absolute path to the main entry file.
        parser: Optional PenguParser instance for parsing import ASTs.
        lib_dir: External bindings directory name (pengu.yaml 'lib_dir').
        src_dir: Project source directory name (pengu.yaml 'src_dir').
        entry_source: Optional in-memory text of ``entry_file``. When given, the
            entry's imports come from this text instead of from disk. An editor
            holds a buffer that is ahead of the file it will be saved to, so
            reading the entry from disk made a freshly typed ``import std.numerus``
            invisible: the module was never collected, its ``enchanting`` methods
            were never registered, and the first ``x.clamp`` failed with
            ``E0004 Type 'f32' has no method 'clamp'`` until the file was saved.
        module_sources: Optional ``{absolute path: text}`` map of other unsaved
            editor buffers. Imports of those modules use the buffer instead of
            the (stale) file on disk.

    Returns:
        Absolute module paths in dependency-first order, ending with the entry.
    """
    if parser is None:
        from .pengu_parser import PenguParser
        parser = PenguParser()

    entry_abs = os.path.abspath(os.path.join(base_dir, entry_file)) if not os.path.isabs(entry_file) else os.path.abspath(entry_file)
    if not os.path.isfile(entry_abs):
        src_cand = os.path.abspath(os.path.join(base_dir, src_dir or "src", entry_file))
        if os.path.isfile(src_cand):
            entry_abs = src_cand

    base_abs = os.path.abspath(base_dir)
    overrides = module_sources or {}

    def _missing(file_path: str, dot_path: Optional[str] = None) -> SemanticError:
        if dot_path is not None:
            return SemanticError(
                f"Cannot resolve imported module '{dot_path}'",
                code="E0004",
                help=f"Ensure '{dot_path}.pengu' exists in source directory '{base_dir}' or stdlib.",
                note="PenguScript module files must match import path."
            )
        return SemanticError(f"Module file not found: {file_path}", code="E0004")

    def extract_imports(file_path: str) -> List[str]:
        """Parses a file and extracts all its direct module imports."""
        override = _resolve_module_text(file_path, entry_abs, entry_source, overrides)
        if override is None and not os.path.isfile(file_path):
            raise _missing(file_path)
        tree = cached_module_tree(file_path, parser, override)
        deps: List[str] = []

        # A wrapper's companion declarations must be checked *before* the
        # wrapper body: `declare` lines register the C signatures the wrapper
        # calls. Appending the companion to the wrapper's own dependency list
        # (rather than to the importer's) keeps the topological order correct:
        # declaration file, then wrapper, then importer.
        own_companion = companion_binding_path(file_path)
        if own_companion is not None:
            deps.append(own_companion)

        def walk(node):
            if isinstance(node, Tree):
                if node.data == "import_stmt":
                    path_tree = node.children[0]
                    def _extract_names(t):
                        if isinstance(t, Token):
                            return [str(t)]
                        if isinstance(t, Tree):
                            res = []
                            for ch in t.children:
                                res.extend(_extract_names(ch))
                            return res
                        return [str(t)]
                    dot_path = ".".join(_extract_names(path_tree))
                    mod_path = find_module_path(base_abs, dot_path,
                                                from_dir=os.path.dirname(file_path),
                                                lib_dir=lib_dir, src_dir=src_dir)
                    if not mod_path:
                        raise _missing(file_path, dot_path)
                    deps.append(mod_path)
                for child in node.children:
                    walk(child)

        walk(tree)
        return deps

    def _signature_of(path: str) -> Optional[Tuple[Any, ...]]:
        override = _resolve_module_text(path, entry_abs, entry_source, overrides)
        if override is not None:
            return module_source_signature(path, override)
        try:
            return module_source_signature(path)
        except OSError:
            return None

    cache_key = (
        base_abs, entry_abs, os.path.abspath(lib_dir or "lib"),
        os.path.abspath(os.path.join(base_abs, src_dir or "src")),
    )
    cached = _IMPORT_ORDER_CACHE.get(cache_key)
    if cached is not None:
        versions, cached_order = cached
        current = tuple(_signature_of(path) for path in cached_order)
        if current == versions:
            return list(cached_order)

    visited: Set[str] = set()
    visiting: Set[str] = set()
    order: List[str] = []

    def dfs(node: str, path: List[str]):
        """Performs three-color DFS to detect cycles and topologically sort dependencies."""
        abs_node = os.path.abspath(node)
        if abs_node in visiting:
            cycle_nodes = path + [abs_node]
            cycle_str = " -> ".join([os.path.basename(p) for p in cycle_nodes])
            raise SemanticError(
                f"Circular dependency detected in imports: {cycle_str}",
                code="E0004",
                help=f"Remove circular import: {cycle_str}",
                note="PenguScript forbids circular module dependencies to guarantee deterministic compilation."
            )
        if abs_node not in visited:
            visiting.add(abs_node)
            dep_files = extract_imports(abs_node)
            for dep in dep_files:
                dfs(dep, path + [abs_node])
            visiting.remove(abs_node)
            visited.add(abs_node)
            order.append(abs_node)

    dfs(entry_abs, [])

    versions = tuple(_signature_of(path) for path in order)
    if len(_IMPORT_ORDER_CACHE) >= _IMPORT_ORDER_CACHE_MAX:
        _IMPORT_ORDER_CACHE.clear()
    _IMPORT_ORDER_CACHE[cache_key] = (versions, list(order))
    return order


def decl_layout(node: Tree) -> Tuple[Optional[Tree], Optional[Tree]]:
    """Extracts (type_node, expr_node) from var_decl, let_decl, or static_var_decl.

    All three rules share one child layout: the declared name (or
    ``var_name_list``), the optional type annotation (a ``None`` placeholder
    when absent) and the initializer expression.  The type therefore lives at
    index 1 and the value at index 2.  The length checks keep the extractor
    working for hand-built trees in tests, where the placeholder for an absent
    annotation may be missing entirely.
    """
    children = node.children
    if len(children) < 2:
        return None, None
    rem = children[1:]
    if len(rem) >= 2:
        return rem[0], rem[1]
    return None, rem[0]

