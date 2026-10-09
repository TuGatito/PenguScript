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
    type_has_derived_nexus, type_owns_heap,
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol, decl_layout
from pengu_parser.pengu_infer import ConstFolder, TypeInferrer, RangeConst
from pengu_parser.pengu_comptime import CompileTimeEnv, default_env, eval_comptime
from pengu_parser.pengu_errors import SemanticError
from pengu_parser.pengu_grammar import SIMPLE_STMT_ALIASES
from pengu_parser.pengu_dce import (
    collect_references as _dce_collect_refs,
    prune_weaves,
    summarize as _dce_summarize,
)

# Public layout extractor lives in pengu_symbols; re-exported so every
# mixin reaches it through this single module.
_decl_layout = decl_layout
