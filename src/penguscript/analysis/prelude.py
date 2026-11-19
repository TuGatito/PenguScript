"""Prelude symbols and builtin types for PenguScript."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from penguscript.analysis.symbols import Scope, ScopeKind, Symbol, SymbolId, SymbolKind
from penguscript.frontend.span import Span

_BUILTIN_PATH = Path("<builtin>")
_DUMMY_SPAN = Span(start_byte=0, end_byte=0, line=1, col=1)

# Complete list of builtin types from docs/cheatsheet.md
BUILTIN_PRIMITIVES: tuple[str, ...] = (
    # C++ standard primitives
    "void",
    "bool",
    "char",
    "signed char",
    "unsigned char",
    "short",
    "unsigned short",
    "int",
    "unsigned int",
    "long",
    "unsigned long",
    "long long",
    "unsigned long long",
    "float",
    "double",
    "long double",
    "wchar_t",
    "char8_t",
    "char16_t",
    "char32_t",
    "nullptr_t",
    # Fixed-size integers
    "int8_t",
    "int16_t",
    "int32_t",
    "int64_t",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
    "size_t",
    "ptrdiff_t",
    "intptr_t",
    "uintptr_t",
    "byte",
    # Shorthand integer aliases
    "i8",
    "i16",
    "i32",
    "i64",
    "u8",
    "u16",
    "u32",
    "u64",
    "uint",
    "ushort",
    "ulong",
    # Strings
    "string",
    "wstring",
    "u8string",
    "u16string",
    "u32string",
    "string_view",
    "wstring_view",
    "u8string_view",
    "u16string_view",
    "u32string_view",
    # Containers
    "vector",
    "array",
    "deque",
    "list",
    "forward_list",
    "set",
    "multiset",
    "unordered_set",
    "unordered_multiset",
    "map",
    "multimap",
    "unordered_map",
    "unordered_multimap",
    "stack",
    "queue",
    "priority_queue",
    "span",
    "pair",
    "tuple",
    "bitset",
    # Smart pointers and references
    "unique",
    "shared",
    "weak",
    "ref",
    "raw",
    "ptr",
    # Utilities and threading
    "optional",
    "variant",
    "any",
    "function",
    "init_list",
    "complex",
    "atomic",
    "mutex",
    "shared_mutex",
    "condition_variable",
    "thread",
)

BUILTIN_CONSTANTS: tuple[str, ...] = (
    "true",
    "false",
    "none",
    "nullopt",
    "nullptr",
)


@lru_cache(maxsize=1)
def get_prelude_symbols() -> dict[str, Symbol]:
    """Return dictionary of all prelude symbols mapped by name."""
    symbols: dict[str, Symbol] = {}

    for name in BUILTIN_PRIMITIVES:
        sym_id = SymbolId(module_path=_BUILTIN_PATH, span=_DUMMY_SPAN)
        symbols[name] = Symbol(
            id=sym_id,
            name=name,
            kind=SymbolKind.BUILTIN_TYPE,
            realm="std",
        )

    for name in BUILTIN_CONSTANTS:
        sym_id = SymbolId(module_path=_BUILTIN_PATH, span=_DUMMY_SPAN)
        symbols[name] = Symbol(
            id=sym_id,
            name=name,
            kind=SymbolKind.CONST,
            realm="std",
        )

    return symbols


def get_prelude_scope() -> Scope:
    """Return the root Scope holding all prelude symbols."""
    scope = Scope(kind=ScopeKind.PRELUDE)
    scope.symbols = get_prelude_symbols().copy()
    return scope


__all__ = [
    "BUILTIN_CONSTANTS",
    "BUILTIN_PRIMITIVES",
    "get_prelude_scope",
    "get_prelude_symbols",
]
