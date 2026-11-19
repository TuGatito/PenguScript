"""Symbol, scope, and realm data structures for PenguScript analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from penguscript.analysis.diagnostics import Diagnostic
from penguscript.frontend.ast_nodes import InvokeDecl
from penguscript.frontend.span import Span


@dataclass(frozen=True, slots=True)
class NodeId:
    """Unique identity of an AST node based on its source path and span."""

    path: Path
    span: Span


@dataclass(frozen=True, slots=True)
class SymbolId:
    """Unique identity of a symbol based on its declaration path and span."""

    module_path: Path
    span: Span


class SymbolKind(Enum):
    """Categorization of symbols in PenguScript."""

    FUNCTION = auto()
    CONST = auto()
    RUNE = auto()
    OMEN = auto()
    ECHO = auto()
    SEAL = auto()
    OPERATOR = auto()
    FREE_OPERATOR = auto()
    CONSTRUCTOR = auto()
    DESTRUCTOR = auto()
    METHOD = auto()
    FIELD = auto()
    OMEN_VARIANT = auto()
    PARAMETER = auto()
    LOCAL = auto()
    SIGIL = auto()
    BUILTIN_TYPE = auto()
    REALM_ALIAS = auto()


@dataclass(frozen=True, slots=True)
class Symbol:
    """A declared entity in the program."""

    id: SymbolId
    name: str
    kind: SymbolKind
    realm: str | None = None
    is_mut: bool = False
    is_unsafe: bool = False
    is_private: bool = False
    sigils: tuple[str, ...] = ()
    decl_node_id: NodeId | None = None


class ScopeKind(Enum):
    """Types of lexical scopes."""

    PRELUDE = auto()
    MODULE = auto()
    RUNE = auto()
    FUNCTION = auto()
    BLOCK = auto()


@dataclass(slots=True)
class Scope:
    """Lexical scope holding local symbols and link to parent scope."""

    kind: ScopeKind
    parent: Scope | None = None
    symbols: dict[str, Symbol] = field(default_factory=dict)
    owner_span: Span | None = None
    enclosing_rune: str | None = None
    in_loop: bool = False
    in_constructor: bool = False

    def define(self, symbol: Symbol) -> None:
        """Add a symbol to this scope."""
        self.symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Symbol | None:
        """Look up a symbol by name in this scope and any enclosing scopes."""
        sym = self.symbols.get(name)
        if sym is not None:
            return sym
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Symbol | None:
        """Look up a symbol defined strictly in this scope."""
        return self.symbols.get(name)


@dataclass(frozen=True, slots=True)
class RealmSymbolTable:
    """Merged symbols and type tables belonging to a realm."""

    name: str
    symbols: Mapping[str, Symbol] = field(default_factory=dict)
    rune_fields: Mapping[str, Mapping[str, Symbol]] = field(default_factory=dict)
    rune_methods: Mapping[str, Mapping[str, Symbol]] = field(default_factory=dict)
    omen_variants: Mapping[str, Mapping[str, Symbol]] = field(default_factory=dict)
    by_path: Mapping[Path, frozenset[str]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolvedImport:
    """A resolved import statement linking to another module/realm."""

    source_span: Span
    target_path: Path
    target_realm: str
    kind: str  # "plain" or "selective"
    local_alias: str | None = None
    imported_symbols: Mapping[str, Symbol] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnnotatedModule:
    """Analysis results for a single module/file."""

    path: Path
    declared_realm: str
    imports: tuple[ResolvedImport, ...] = ()
    visible_realms: Mapping[str, str] = field(default_factory=dict)
    visible_symbols: Mapping[str, Symbol] = field(default_factory=dict)
    local_symbols: Mapping[str, Symbol] = field(default_factory=dict)


@dataclass(slots=True)
class RawModuleDecl:
    """Unprocessed top-level declarations collected during Pass 1."""

    path: Path
    declared_realm: str
    is_explicit_realm: bool
    realm_span: Span | None = None
    imports: list[InvokeDecl] = field(default_factory=list)
    symbols: dict[str, Symbol] = field(default_factory=dict)
    rune_fields: dict[str, dict[str, Symbol]] = field(default_factory=dict)
    rune_methods: dict[str, dict[str, Symbol]] = field(default_factory=dict)
    enchanting_spans: dict[str, Span] = field(default_factory=dict)
    omen_variants: dict[str, dict[str, Symbol]] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class AnnotatedProject:
    """Complete symbol tables, module analysis, and diagnostics for a project."""

    realms: dict[str, RealmSymbolTable]
    modules: dict[Path, AnnotatedModule]
    references: dict[NodeId, Symbol]
    symbols_to_refs: dict[SymbolId, list[NodeId]]
    scopes: dict[NodeId, Scope] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    symbol_types: dict[SymbolId, object] = field(default_factory=dict)
    const_values: dict[SymbolId, object] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """Return True if any diagnostic is an error."""
        return any(d.is_error for d in self.diagnostics)

    @property
    def has_warnings(self) -> bool:
        """Return True if any diagnostic is a warning."""
        return any(d.is_warning for d in self.diagnostics)


__all__ = [
    "AnnotatedModule",
    "AnnotatedProject",
    "NodeId",
    "RawModuleDecl",
    "RealmSymbolTable",
    "ResolvedImport",
    "Scope",
    "ScopeKind",
    "Symbol",
    "SymbolId",
    "SymbolKind",
]
