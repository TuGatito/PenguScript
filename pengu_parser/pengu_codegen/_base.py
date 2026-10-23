"""Shared imports and constants for the PenguScript C code generator.

Every other module in this package imports what it needs from here, so there
is exactly one place where the generator pulls in the rest of the compiler.
"""
from __future__ import annotations

import os
import re
import sys
import json
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from lark import Tree, Token
try:  # The toolchain root (which holds VERSION) is the parent package directory.
    from pengu_version import __version__ as PENGU_VERSION
except ImportError:  # pragma: no cover - vendored/frozen fallback, guarded by tests
    PENGU_VERSION = "1.0.0"
PENGU_EXPECTED_ABI_VERSION = 2
from pengu_parser.pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ManyType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, AliasType, AnyType, FrozenType,
    TupleType,
    ConceptType, SealType, RangeType,
    TypeParam, NullType, INT_TYPE, I32_TYPE, I64_TYPE, FLOAT_TYPE, F32_TYPE, F64_TYPE, BOOL_TYPE,
    STRING_TYPE, VOID_TYPE, ERROR_TYPE, OPAQUE_TYPE, CVarArgsType, ast_to_type, get_type_base_name,
    type_has_derived_nexus, type_owns_heap, canonical_primitive_name, primitive_lookup_order,
    canonical_type_name,
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol, decl_layout, SHARD_RECEIVER_KEY
from pengu_parser.pengu_infer import ConstFolder, TypeInferrer, RangeConst
from pengu_parser.pengu_comptime import CompileTimeEnv, default_env, eval_comptime
from pengu_parser.pengu_errors import SemanticError
from pengu_parser.pengu_grammar import (
    SIMPLE_STMT_ALIASES, pattern_group_name, split_when_pattern,
)
from pengu_parser.pengu_dce import (
    collect_references as _dce_collect_refs,
    identifiers_in_text as _dce_identifiers_in_text,
    is_prunable_module,
    prune_weaves,
    resolved_std_roots as _dce_resolved_std_roots,
    summarize as _dce_summarize,
)

# Public layout extractor lives in pengu_symbols; re-exported so every
# mixin reaches it through this single module.
_decl_layout = decl_layout


def unwrap_condition(code: str) -> str:
    """Drops one redundant outer parenthesis pair from a branch condition.

    `if a == b:` used to reach the C compiler as ``if ((a == b))``. That is the
    exact shape clang reports as ``-Wparentheses-equality`` ("equality comparison
    with extraneous parentheses") -- the same shape as the classic
    ``if ((a = b))`` typo -- and every comparison in every `std` module went
    through it, so a small program importing one module produced dozens of
    warnings.

    The parentheses are **not** redundant where a comparison is an operand
    (``(a == b) + x``, ``f((a == b))``), so the expression translator keeps
    emitting them. The branch emitters wrap the condition in a pair of their own,
    which is the only place the extra one can be dropped safely.

    A pair is removed only when it encloses the *whole* string, so ``(a) + (b)``
    is returned untouched. String and character literals are skipped, because a
    parenthesised literal -- ``pengu_string_equal(s, "(")`` -- would otherwise
    unbalance the scan.

        '(a == b)'                   -> 'a == b'
        '((a == b))'                 -> '(a == b)'
        '(a) + (b)'                  -> unchanged
        'f(x)'                       -> unchanged
        'pengu_string_equal(s, "(")' -> unchanged
    """
    if len(code) < 2 or code[0] != "(" or code[-1] != ")":
        return code
    depth = 0
    quote = ""
    i = 0
    last = len(code) - 1
    while i <= last:
        ch = code[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in ('"', "'"):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            # The first pair closed before the end: the string is a sequence of
            # expressions, not one wrapped expression. Leave it alone.
            if depth == 0 and i != last:
                return code
        i += 1
    if depth != 0:
        return code
    return code[1:-1]
