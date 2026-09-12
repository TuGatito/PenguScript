#!/usr/bin/env python3
"""PenguScript C Code Generator (pengu_codegen.py).

Translates verified ASTs from all modules in topological order into a single monolithic bundle.c.
Employs a multi-pass architecture:
1. Declarations collection (runes, echos, omens, aliases, consts, weaves, enchantings).
2. Forward declarations of all types and function prototypes (eliminates circular/ordering issues).
3. Complete type definitions (structs, unions, tagged enums).
4. Function definitions in topological module order.
5. Entry point generation (for executable targets).

The generated C carries `#line` directives that point back at the `.pengu`
sources, so a gcc/clang diagnostic is reported against the file and line the user
actually wrote (see `tests/test_line_directives.py`).
"""

from __future__ import annotations
import os
import sys
from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from lark import Tree, Token

try:  # The toolchain root (which holds VERSION) is the parent package directory.
    from pengu_version import __version__ as PENGU_VERSION
except ImportError:  # pragma: no cover - vendored/frozen fallback, guarded by tests
    PENGU_VERSION = "0.10.0"

from pengu_parser.pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ManyType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, AliasType, AnyType, FrozenType,
    ConceptType, SealType, RangeType,
    TypeParam, NullType, INT_TYPE, I32_TYPE, I64_TYPE, FLOAT_TYPE, F32_TYPE, F64_TYPE, BOOL_TYPE,
    STRING_TYPE, VOID_TYPE, ERROR_TYPE, OPAQUE_TYPE, CVarArgsType, ast_to_type
)
from pengu_parser.pengu_symbols import SymbolTable, Symbol
from pengu_parser.pengu_infer import ConstFolder, TypeInferrer
from pengu_parser.pengu_comptime import CompileTimeEnv, default_env, eval_comptime
from pengu_parser.pengu_errors import SemanticError
from pengu_parser.pengu_grammar import SIMPLE_STMT_ALIASES


class CTypeMapper:
    """Maps PenguScript semantic types to C99 type representations."""

    @staticmethod
    def to_c_type(t: Optional[Type], const: bool = False) -> str:
        """Converts PenguScript Type to C99 type string.

        Args:
            t: PenguScript Type instance.
            const: True to add const qualifier.

        Returns:
            C99 type string.
        """
        if t is None:
            return "void"

        prefix = "const " if const else ""

        if isinstance(t, FrozenType):
            # 'frozen T' is C's 'const T'. The qualification lives on the
            # pointee for 'ref to frozen T' ('const T*'), never on the pointer.
            inner = t.target
            if isinstance(inner, RefType):
                inner_target = inner.target
                if isinstance(inner_target, BaseType) and inner_target.name == "void":
                    return f"{prefix}const void*"
                inner_c = CTypeMapper.to_c_type(inner_target, const=True)
                return f"{prefix}{inner_c}*"
            if isinstance(inner, BaseType) and inner.name == "void":
                # Special-cased because the base mapper returns 'void' verbatim.
                return f"{prefix}const void"
            return CTypeMapper.to_c_type(inner, const=True)

        if isinstance(t, RangeType):
            return f"{prefix}PenguRange"

        if isinstance(t, BaseType):
            name = t.name
            if name in ("int", "i32", "int32", "int32_t"):
                return f"{prefix}int32_t"
            elif name in ("i64", "int64", "int64_t", "long"):
                return f"{prefix}int64_t"
            elif name in ("u32", "uint32", "uint32_t", "uint"):
                return f"{prefix}uint32_t"
            elif name in ("u64", "uint64", "uint64_t", "ulong"):
                return f"{prefix}uint64_t"
            elif name in ("i16", "int16", "int16_t", "short"):
                return f"{prefix}int16_t"
            elif name in ("u16", "uint16", "uint16_t", "ushort"):
                return f"{prefix}uint16_t"
            elif name in ("i8", "int8", "int8_t"):
                return f"{prefix}int8_t"
            elif name in ("byte", "u8", "uint8", "uint8_t"):
                return f"{prefix}uint8_t"
            elif name == "char":
                return f"{prefix}char"
            elif name in ("usize", "size_t"):
                return f"{prefix}size_t"
            elif name in ("isize", "ssize_t"):
                return f"{prefix}intptr_t"
            elif name in ("float", "f32"):
                return f"{prefix}float"
            elif name in ("double", "f64"):
                return f"{prefix}double"
            elif name == "bool":
                return f"{prefix}bool"
            elif name == "string":
                return f"{prefix}PenguString"
            elif name == "void":
                return "void"
            elif name == "opaque":
                return f"{prefix}void*"
            elif name == "error":
                return f"{prefix}const char*"
            return f"{prefix}{name}"

        elif isinstance(t, RefType):
            if isinstance(t.target, FnType):
                # 'ref to weave …' is a function pointer (C callback typedef).
                return CTypeMapper.to_c_type(t.target)
            target_str = CTypeMapper.to_c_type(t.target)
            if target_str == "void":
                return "void*"
            return f"{target_str}*"

        elif isinstance(t, RuneType):
            eff_name = getattr(t, "c_name", None) or t.name
            return f"{prefix}{eff_name}"

        elif isinstance(t, EchoType):
            eff_name = getattr(t, "c_name", None) or t.name
            return f"{prefix}{eff_name}"

        elif isinstance(t, OmenType):
            if t.is_string_valued:
                return f"{prefix}PenguString"
            eff_name = getattr(t, "c_name", None) or t.name
            return f"{prefix}{eff_name}"

        elif isinstance(t, AliasType):
            eff_name = getattr(t, "c_name", None) or t.name
            return f"{prefix}{eff_name}"

        elif isinstance(t, ArrayType):
            elem_str = CTypeMapper.to_c_type(t.element)
            return f"{elem_str}*"

        elif isinstance(t, (SliceType, ManyType)):
            return "PenguSlice"

        elif isinstance(t, ListType):
            return "PenguList"

        elif isinstance(t, MapType):
            return "PenguMap"

        elif isinstance(t, MaybeType):
            return "PenguMaybe"

        elif isinstance(t, ResultType):
            return "PenguResult"

        elif isinstance(t, FnType):
            ret_str = CTypeMapper.to_c_type(t.return_type)
            param_strs = [CTypeMapper.to_c_type(p[1]) for p in t.params] or ["void"]
            return f"{ret_str} (*)({', '.join(param_strs)})"

        elif isinstance(t, SealType):
            eff_name = getattr(t, "c_name", None) or t.name
            return f"{prefix}{eff_name}"

        elif isinstance(t, ConceptType):
            return f"{prefix}void*"

        elif isinstance(t, NullType):
            return f"{prefix}void*"

        return f"{prefix}void*"

    @staticmethod
    def to_c_decl(t: Optional[Type], ident: str = "", const: bool = False, restrict: bool = False) -> str:
        """Declares a variable or parameter with C99 identifier, supporting function pointers and restrict qualifier."""
        if t is None:
            return f"void {ident}".strip()
        if isinstance(t, FnType):
            ret_str = CTypeMapper.to_c_type(t.return_type)
            param_strs = [CTypeMapper.to_c_type(p[1]) for p in t.params] or ["void"]
            return f"{ret_str} (*{ident})({', '.join(param_strs)})" if ident else f"{ret_str} (*)({', '.join(param_strs)})"
        if isinstance(t, RefType) and isinstance(t.target, FnType):
            # 'ref to weave …' is a function pointer, not a pointer to one.
            return CTypeMapper.to_c_decl(t.target, ident, const=const, restrict=restrict)
        if isinstance(t, RefType) and isinstance(t.target, ArrayType):
            dims, base_c = get_array_dims_and_base(t.target)
            dims_str = "".join(f"[{d}]" for d in dims)
            const_prefix = "const " if const else ""
            ptr_qual = " restrict " if restrict else " "
            return f"{const_prefix}{base_c} (*{ptr_qual}{ident}){dims_str}".strip() if ident else f"{const_prefix}{base_c} (*){dims_str}"
        if isinstance(t, RefType) and restrict and ident:
            target_str = CTypeMapper.to_c_type(t.target)
            return f"{target_str}* restrict {ident}"
        if isinstance(t, ArrayType):
            dims, base_c = get_array_dims_and_base(t)
            const_prefix = "const " if const else ""
            if len(dims) == 1:
                ptr_qual = " restrict" if restrict else ""
                return f"{const_prefix}{base_c}*{ptr_qual} {ident}".strip() if ident else f"{const_prefix}{base_c}*"
            else:
                inner_dims_str = "".join(f"[{d}]" for d in dims[1:])
                ptr_qual = " restrict " if restrict else " "
                return f"{const_prefix}{base_c} (*{ptr_qual}{ident}){inner_dims_str}".strip() if ident else f"{const_prefix}{base_c} (*){inner_dims_str}"
        base = CTypeMapper.to_c_type(t, const=const)
        return f"{base} {ident}".strip() if ident else base


def get_array_dims_and_base(t: ArrayType) -> Tuple[List[Any], str]:
    """Flattens nested ArrayType dimensions and resolves the innermost C base type."""
    dims = []
    curr: Any = t
    while isinstance(curr, ArrayType):
        if curr.size is None:
            raise SemanticError(
                f"Unknown array dimension in '{t}'. Expected fixed dimensions or inferable initializer.",
                code="E0015",
                help="Specify all dimensions (e.g. 'array of array of T with size M with size N') or initialize with full literal rows.",
                note="C requires fixed array sizes for all dimensions."
            )
        dims.append(curr.size)
        curr = curr.element
    base_c = CTypeMapper.to_c_type(curr)
    return dims, base_c


def sync_array_sizes(target_t: Any, source_t: Any) -> None:
    """Recursively propagates inferred array dimensions to target array types."""
    if isinstance(target_t, ArrayType) and isinstance(source_t, ArrayType):
        if target_t.size is None and source_t.size is not None:
            target_t.size = source_t.size
        sync_array_sizes(target_t.element, source_t.element)


def skip_weave_modifiers(children, start: int = 0):
    """Parses leading ``inline``/``ritual`` weave modifiers from a weave/declare
    AST node. The grammar wraps each modifier in a ``weave_modifier`` Tree when
    present (``Tree('weave_modifier', [Token('RITUAL','ritual')])``), but older
    callers also tolerated bare ``Token`` modifiers directly in the child list;
    both shapes are handled here.

    Returns ``(is_inline, is_ritual, next_index)``.
    """
    is_inline = False
    is_ritual = False
    idx = start
    while idx < len(children):
        child = children[idx]
        if isinstance(child, Tree) and child.data == "weave_modifier":
            for sub in child.children:
                if isinstance(sub, Token) and str(sub) == "inline":
                    is_inline = True
                elif isinstance(sub, Token) and str(sub) == "ritual":
                    is_ritual = True
            idx += 1
        elif isinstance(child, Token) and str(child) in ("inline", "ritual"):
            if str(child) == "inline":
                is_inline = True
            else:
                is_ritual = True
            idx += 1
        else:
            break
    return is_inline, is_ritual, idx


def unwrap_top_level(node):
    """Descends through top_stmt wrappers to the real declaration."""
    while node is not None and isinstance(node, Tree) and node.data == "top_stmt" and node.children:
        node = node.children[0]
    return node


def flatten_at_chain(node: Any) -> List[Any]:
    """Flattens an 'at' chain into [base, idx1, idx2, ...] regardless of the
    association produced by the parser (left or right nested)."""
    if not (isinstance(node, Tree) and node.data == "at_expr"):
        return [node]
    left = node.children[0]
    right = node.children[1]
    if isinstance(left, Tree) and left.data == "at_expr":
        parts = flatten_at_chain(left)
        parts.append(right)
        return parts
    if isinstance(right, Tree) and right.data == "at_expr":
        return [left] + flatten_at_chain(right)
    return [left, right]


class PenguCodegen:
    """Translates verified PenguScript module ASTs into high-performance C99 code."""
    def __init__(self, symbols: Optional[SymbolTable] = None, import_order: Optional[List[str]] = None, base_dir: str = ".",
                 compile_env: Optional[CompileTimeEnv] = None):
        """Initializes code generator.

        Args:
            symbols: Semantic symbol table with resolved types.
            import_order: List of source files in topological dependency order.
            base_dir: Root directory of project.
            compile_env: Optional compile-time environment for 'when' clauses.
        """
        self.symbols = symbols
        self.import_order = import_order or []
        self.base_dir = base_dir
        self.compile_env = compile_env if compile_env is not None else default_env()
        self.debug_mode: bool = bool(getattr(self.compile_env, "is_debug", False))
        # Entry-as-main mode: only the *entry* module compiles with the
        # compile-time 'main' flag true (see _apply_main_flag). Defaults keep
        # every module compiled with 'main' false.
        self.entry_main_mode = False
        self.entry_file: Optional[str] = None
        # `#line` support: markers are emitted for statements (and top-level
        # items) so gcc/clang diagnostics point at the .pengu source. They are
        # suppressed inside expression contexts, where the generated code may be
        # a GCC statement-expression passed to a function-like macro
        # (`pengu_to_string(x)`), which a directive would break.
        self.emit_line_markers = True
        self.line_base_dir: Optional[str] = None
        self.current_source_file: Optional[str] = None
        self.bundle_display_path: Optional[str] = None
        self._expr_depth = 0
        self.const_folder = ConstFolder(symbols) if symbols else ConstFolder(SymbolTable())

        # Declarations registry
        self.runes: Dict[str, Dict[str, Type]] = {}
        self.echos: Dict[str, Dict[str, Type]] = {}
        self.omens: Dict[str, Dict[str, Dict[str, Type]]] = {}
        self.omen_values: Dict[str, Dict[str, int]] = {}
        self.aliases: Dict[str, Type] = {}
        self.seals: Dict[str, Type] = {}
        self.concepts: Dict[str, Any] = {}
        self.consts: Dict[str, Tuple[Optional[Type], Any]] = {}
        self.declaration_types: Set[str] = set()
        self.declaration_consts: Set[str] = set()
        self.c_defines: List[str] = []
        self.weaves: List[Dict[str, Any]] = []
        self.fn_info: Dict[str, Dict[str, Any]] = {}
        self.tests: List[Dict[str, Any]] = []
        self.includes: List[str] = []
        self.links: List[str] = []
        self.has_main = False
        # Return type of 'weave main', used as the process exit status.
        self.main_return_type: Optional[Type] = None
        # Lambda expressions compile to top-level 'static' C functions (no
        # capture, so no GCC nested functions): 'lambdas' collects their
        # definitions and '_lambda_counter' names them uniquely.
        self.lambdas: List[str] = []
        self._lambda_counter = 0

        # Translation state
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[Type] = None
        self.current_enchanted_type: Optional[Type] = None
        self.local_vars: Dict[str, Type] = {}
        self.indent_level = 0
        self.defer_stack: List[List[str]] = []
        self.errdefer_stack: List[List[str]] = []
        self.with_stack: List[str] = []
        self.auto_banish_stack: List[Tuple[str, List[Tuple[str, Type]]]] = []
        self.temp_counter = 0

    @staticmethod
    def _has_borrowed_modifier(node: Tree) -> Tuple[bool, int]:
        if not node.children:
            return False, 0
        first = node.children[0]
        if first is not None and getattr(first, "type", None) == "BORROWED":
            return True, 1
        if first is None:
            return False, 1
        return False, 0

    def _auto_banish_push(self, kind: str = "block") -> None:
        self.auto_banish_stack.append((kind, []))

    def _auto_banish_register(self, name: str, t: Type) -> None:
        if self.auto_banish_stack:
            self.auto_banish_stack[-1][1].append((name, t))

    def _emit_auto_banish(self, name: str, t: Type) -> str:
        ind = self.indent()
        actual = t
        while isinstance(actual, (AliasType, FrozenType)) and getattr(actual, "target", None):
            actual = actual.target
        if isinstance(actual, BaseType) and actual.name == "string":
            return f"{ind}pengu_banish_string(&{name});"
        if isinstance(actual, ListType):
            return f"{ind}pengu_banish_list(&{name});"
        if isinstance(actual, MapType):
            return f"{ind}pengu_banish_map(&{name});"
        return ""

    def _flush_current_scope_banish(self) -> List[str]:
        out: List[str] = []
        if not self.auto_banish_stack:
            return out
        kind, entries = self.auto_banish_stack[-1]
        for name, t in reversed(entries):
            code = self._emit_auto_banish(name, t)
            if code:
                out.append(code)
        entries.clear()
        return out

    def _translate_nested_block_with_banish(self, node: Tree, kind: str = "block") -> str:
        self._auto_banish_push(kind)
        try:
            body = self._translate_nested_block(node)
            if not self._block_ends_with_jump(node):
                banish = self._flush_current_scope_banish()
                if banish:
                    body = (body + "\n" if body else "") + "\n".join(banish)
            return body
        finally:
            if self.auto_banish_stack and self.auto_banish_stack[-1][0] == kind:
                self.auto_banish_stack.pop()

    @staticmethod
    def _block_ends_with_jump(node: Any) -> bool:
        if not isinstance(node, Tree):
            return False
        stmts = node.children if node.data == "block" else [node]
        if not stmts:
            return False
        last = stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt") and last.children:
            last = last.children[0]
        if isinstance(last, Tree) and last.data in ("return_stmt", "break_stmt", "continue_stmt"):
            return True
        return False

    @staticmethod
    def _stmts_end_with_jump(stmts: List[Tree]) -> bool:
        if not stmts:
            return False
        last = stmts[-1]
        while isinstance(last, Tree) and last.data in ("stmt", "simple_stmt") and last.children:
            last = last.children[0]
        if isinstance(last, Tree) and last.data in ("return_stmt", "break_stmt", "continue_stmt"):
            return True
        return False

    def _lookup_var_type(self, name: str) -> Optional[Type]:
        """Looks up semantic type for identifier in local or symbol context."""
        if name in self.local_vars and self.local_vars[name] is not None:
            return self.local_vars[name]
        sym = self.symbols.lookup(name) if self.symbols else None
        if sym and sym.type:
            return sym.type
        if name in self.runes:
            return RuneType(name, self.runes[name])
        if name in self.seals:
            return SealType(name, self.seals[name])
        return None

    def _expr_is_string(self, node: Any, known_type: Optional[Type] = None) -> bool:
        """Returns True when an expression resolves to the PenguScript string type."""
        t = known_type
        if t is None:
            t = self._infer_node_type(node)
        if isinstance(t, RefType):
            t = t.target
        return isinstance(t, BaseType) and getattr(t, "name", "") == "string"

    def _expr_location(self, node: Any) -> str:
        """Returns 'file.pengu:line' for an AST node (best-effort)."""
        line = self._node_line(node) or 0
        shown = self._display_path(self.current_source_file) or "<unknown>"
        return f"{shown}:{line}"

    def _emit_bounds_check(self, idx_code: str, base_code: str, base_t: Optional[Type], node: Any) -> str:
        """Wraps idx_code in a statement-expression with a bounds check when
        debug_mode is on. Returns the (possibly wrapped) index expression."""
        if not self.debug_mode:
            return idx_code
        loc = self._expr_location(node)
        actual_t = base_t.target if isinstance(base_t, RefType) else base_t
        if isinstance(actual_t, ArrayType) and actual_t.size is not None:
            len_expr = str(actual_t.size)
        elif isinstance(actual_t, (SliceType, ManyType, ListType)):
            sep = "->" if isinstance(base_t, RefType) else "."
            len_expr = f"({base_code}){sep}len"
        elif isinstance(actual_t, BaseType) and getattr(actual_t, "name", "") == "string":
            sep = "->" if isinstance(base_t, RefType) else "."
            len_expr = f"({base_code}){sep}len"
        else:
            return idx_code
        tmp = self.get_temp_name("_p_idx")
        return (
            f"(__extension__({{ int32_t {tmp} = (int32_t)({idx_code}); "
            f"pengu_assert_bounds({tmp}, {len_expr}, \"{loc}\"); {tmp}; }}))"
        )

    def _infer_node_type(self, node: Any, expected_type: Optional[Type] = None) -> Optional[Type]:
        """Infers semantic type for AST node using active local variable context."""
        try:
            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
            for var_name, var_type in self.local_vars.items():
                if var_type is not None:
                    inferrer.symbols.define(Symbol(name=var_name, type=var_type, kind="var", line=0, column=0, file_path="."))
            return inferrer.infer(node, expected_type=expected_type)
        except Exception:
            return None

    def get_temp_name(self, prefix: str = "_tmp") -> str:
        """Generates unique local variable identifier.

        Args:
            prefix: Name prefix.

        Returns:
            Unique identifier string.
        """
        self.temp_counter += 1
        return f"{prefix}_{self.temp_counter}"

    def _is_ref_char_type(self, t: Optional[Type]) -> bool:
        """Returns True if the type is a raw C byte pointer.

        That is ``char*``, ``const char*`` (what a ``.d.pengu`` binding emits
        for C's ``const char*``) and the ``void*`` / ``const void*``
        catch-alls, since a C string literal converts to all of them.

        A `frozen` qualification counts too: string literals must keep
        converting to C string pointers there.
        """
        if t is None:
            return False
        curr = t
        while isinstance(curr, (AliasType, FrozenType)) and getattr(curr, "target", None):
            curr = curr.target
        if isinstance(curr, RefType):
            target = curr.target
            while isinstance(target, (AliasType, FrozenType)) and getattr(target, "target", None):
                target = target.target
            if isinstance(target, BaseType) and target.name in ("char", "const char", "void"):
                return True
        return False

    def _cast_fn_value(self, code: str, expected_type: Optional[Type]) -> str:
        """Casts a function value to the expected function-pointer type.

        C APIs declare callbacks with qualifiers a `.d.pengu` binding cannot
        express (``const void*`` for ``qsort``, ``const char*`` for raylib's
        ``TraceLogCallback``) and GCC 14+ rejects a bare function pointer whose
        signature differs only in those qualifiers. Casting to the declared
        callback type is ABI-neutral and makes those APIs usable.

        Args:
            code: Translated C expression (a function name or lambda name).
            expected_type: The declared parameter/annotation type.

        Returns:
            ``code`` wrapped in a cast when the target is a function pointer.
        """
        target = expected_type
        while isinstance(target, AliasType):
            target = target.target
        is_fn_ptr = (
            isinstance(target, FnType)
            or (isinstance(target, RefType) and isinstance(target.target, FnType))
        )
        if not is_fn_ptr:
            return code
        return f"(({CTypeMapper.to_c_type(expected_type)}){code})"

    def _build_call_args(self, fn_params: List[Any], raw_args: List[Any]) -> List[str]:
        """Formats and translates call arguments, filling defaults and constructing PenguSlice for ManyType."""
        if not fn_params:
            return [self._translate_expr(a) for a in raw_args]

        has_variadic = len(fn_params) > 0 and isinstance(fn_params[-1][1], ManyType)
        has_c_varargs = len(fn_params) > 0 and isinstance(fn_params[-1][1], CVarArgsType)
        if not has_variadic and not has_c_varargs:
            args = [self._translate_expr(a, expected_type=fn_params[i][1] if i < len(fn_params) else None) for i, a in enumerate(raw_args)]
            if len(args) < len(fn_params):
                for p in fn_params[len(args):]:
                    if len(p) >= 3 and p[2] is not None:
                        args.append(self._translate_expr(p[2], expected_type=p[1]))
            return args

        if has_c_varargs:
            fixed_params = fn_params[:-1]
            res_args = []
            for i, p in enumerate(fixed_params):
                if i < len(raw_args):
                    res_args.append(self._translate_expr(raw_args[i], expected_type=p[1]))
                elif len(p) >= 3 and p[2] is not None:
                    res_args.append(self._translate_expr(p[2], expected_type=p[1]))
            for a in raw_args[len(fixed_params):]:
                res_args.append(self._translate_expr(a))
            return res_args

        fixed_params = fn_params[:-1]
        variadic_param = fn_params[-1]
        var_elem_type = variadic_param[1].element
        elem_c = CTypeMapper.to_c_type(var_elem_type)

        res_args = []
        fixed_count = len(fixed_params)

        for i, p in enumerate(fixed_params):
            if i < len(raw_args):
                res_args.append(self._translate_expr(raw_args[i], expected_type=p[1]))
            elif len(p) >= 3 and p[2] is not None:
                res_args.append(self._translate_expr(p[2], expected_type=p[1]))

        var_raw_args = raw_args[fixed_count:]
        if len(var_raw_args) == 1:
            arg_t = self._infer_node_type(var_raw_args[0])
            if isinstance(arg_t, (ManyType, SliceType)):
                res_args.append(self._translate_expr(var_raw_args[0], expected_type=variadic_param[1]))
            else:
                arg_code = self._translate_expr(var_raw_args[0], expected_type=var_elem_type)
                tmp_arr = self.get_temp_name("_tmp_arr")
                tmp_slice = self.get_temp_name("_tmp_slice")
                slice_code = f"({{ {elem_c} {tmp_arr}[] = {{ {arg_code} }}; PenguSlice {tmp_slice} = (PenguSlice){{ .data = {tmp_arr}, .len = 1, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
                res_args.append(slice_code)
        elif len(var_raw_args) == 0:
            tmp_slice = self.get_temp_name("_tmp_slice")
            slice_code = f"({{ PenguSlice {tmp_slice} = (PenguSlice){{ .data = NULL, .len = 0, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
            res_args.append(slice_code)
        else:
            elem_codes = [self._translate_expr(a, expected_type=var_elem_type) for a in var_raw_args]
            elems_str = ", ".join(elem_codes)
            tmp_arr = self.get_temp_name("_tmp_arr")
            tmp_slice = self.get_temp_name("_tmp_slice")
            slice_code = f"({{ {elem_c} {tmp_arr}[] = {{ {elems_str} }}; PenguSlice {tmp_slice} = (PenguSlice){{ .data = {tmp_arr}, .len = {len(var_raw_args)}, .elem_size = sizeof({elem_c}) }}; {tmp_slice}; }})"
            res_args.append(slice_code)

        return res_args

    def indent(self) -> str:
        """Returns current indentation spaces string."""
        return "  " * self.indent_level

    def _lookup_type_fn(self, name: str) -> Optional[Type]:
        """Type lookup resolver for AST conversion during codegen."""
        sym = self.symbols.lookup(name) if self.symbols else None
        if sym and sym.type:
            return sym.type
        if self.symbols is not None:
            resolved = self.symbols.lookup_type(name)
            if resolved is not None:
                return resolved
        if name in self.runes:
            return RuneType(name, self.runes[name])
        if name in self.echos:
            return EchoType(name, self.echos[name])
        if name in self.omens:
            return OmenType(name, self.omens[name])
        if name in self.aliases:
            return self.aliases[name]
        if name in self.seals:
            return SealType(name, self.seals[name])
        if name in self.concepts:
            return self.concepts[name]
        return None

    def _format_const_val(self, val: Any, expected_type: Optional[Type] = None) -> str:
        """Formats evaluated constant Python value into C literal."""
        if isinstance(val, bool):
            return "true" if val else "false"
        elif isinstance(val, int):
            return str(val)
        elif isinstance(val, float):
            return f"{val}f" if abs(val) < 1e7 else str(val)
        elif isinstance(val, str):
            if val.startswith("'") and val.endswith("'"):
                return val
            if self._is_ref_char_type(expected_type):
                return f'"{val}"'
            return f'pengu_string_from_cstr("{val}")'
        return str(val)

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

    def collect_declarations(self, trees: List[Tuple[str, Tree]]) -> None:
        """Two-pass declarations collection to resolve forward and circular references.

        Pass 1: Registers all type and function names.
        Pass 2: Populates complete field definitions and signatures.

        Args:
            trees: List of (module_filepath, AST_tree) tuples in topological order.
        """
        if self.compile_env is not None:
            self.debug_mode = bool(getattr(self.compile_env, "is_debug", False))
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
                name_tok = inner.children[0]
                raw_name = str(name_tok)
                display_name = raw_name[1:-1] if (raw_name.startswith('"') and raw_name.endswith('"')) else raw_name
                body_nodes = [c for c in inner.children[1:] if isinstance(c, Tree)]
                self.tests.append({
                    "name": display_name,
                    "name_token": name_tok,
                    "body_stmts": body_nodes,
                    "filepath": tfile,
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
            has_shards = len(stmt.children) > 1 and isinstance(stmt.children[1], Tree) and stmt.children[1].data == "shard_params"
            if has_shards:
                continue
            if rule == "rune_decl":
                name = str(stmt.children[0])
                c_name = f"{cur_insignia}{name}" if cur_insignia else name
                self.runes[c_name] = {}
            elif rule == "echo_decl":
                name = str(stmt.children[0])
                c_name = f"{cur_insignia}{name}" if cur_insignia else name
                self.echos[c_name] = {}
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

            for m_fn_name, (fn_ast, subst_map) in self.symbols.monomorphized_functions.items():
                if m_fn_name in self.symbols._generated_instances:
                    continue
                self.symbols._generated_instances.add(m_fn_name)
                if not any(w["c_name"] == m_fn_name for w in self.weaves):
                    self._collect_monomorphized_weave(m_fn_name, fn_ast, subst_map, None, filepath=".")

            for m_m_name, (m_ast, subst_map) in self.symbols.monomorphized_methods.items():
                if m_m_name in self.symbols._generated_instances:
                    continue
                self.symbols._generated_instances.add(m_m_name)
                parts = m_m_name.rsplit("_", 1)
                rec_tname = parts[0]
                rec_type = self.symbols.lookup_type(rec_tname) or RuneType(name=rec_tname)
                if not any(w["c_name"] == m_m_name for w in self.weaves):
                    self._collect_monomorphized_weave(m_m_name, m_ast, subst_map, rec_type, filepath=".")

        # Pass 4: register lambda expressions found in weave/test bodies. They
        # become top-level 'static' C functions, so they must be collected before
        # any body is translated.
        for w in self.weaves:
            for st in w.get("body_stmts", []):
                self._register_lambdas_in(st, src_file=w.get("filepath"))
        for t in self.tests:
            for st in t.get("body_stmts", []):
                self._register_lambdas_in(st, src_file=t.get("filepath"))

    def _register_lambdas_in(self, node: Any, src_file: Optional[str] = None) -> None:
        """Pre-scans a statement subtree and registers every lambda inside it.

        Nested lambdas are registered first (inner bodies may mention outer
        parameter names, but registration order only affects naming).
        """
        if not isinstance(node, Tree):
            return
        if node.data in ("lambda_expr", "lambda_no_params"):
            for c in node.children:
                self._register_lambdas_in(c, src_file=src_file)
            self._register_one_lambda(node, src_file=src_file)
            return
        for c in node.children:
            self._register_lambdas_in(c, src_file=src_file)

    def _register_one_lambda(self, node: Tree, src_file: Optional[str] = None) -> None:
        """Emits one top-level 'static' C function for a lambda expression.

        The body is translated in an isolated scope containing only the
        parameters (lambdas have no capture), which is why a plain C function is
        enough — no GCC nested functions are required.
        """
        self._lambda_counter += 1
        name = f"_pengu_lambda_{self._lambda_counter}"
        try:
            setattr(node, "_lambda_name", name)
        except Exception:
            pass

        if node.data == "lambda_no_params":
            pnames: List[str] = []
            ptypes: List[Type] = []
            body = node.children[0]
        else:
            plist = node.children[0]
            body = node.children[1]
            pnames, ptypes = [], []
            for p in plist.children:
                if not isinstance(p, Tree) or len(p.children) < 2:
                    continue
                pnames.append(str(p.children[0]))
                ptypes.append(ast_to_type(p.children[1], self._lookup_type_fn))

        # Return type: infer inside a scope holding only the parameters.
        ret_t: Type = VOID_TYPE
        try:
            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
            for pn, pt in zip(pnames, ptypes):
                inferrer.symbols.define(Symbol(name=pn, type=pt, kind="param"))
            ret_t = inferrer.infer(body)
        except Exception:
            ret_t = AnyType()

        # Translate the body in the same isolated scope.
        saved_locals = dict(self.local_vars)
        saved_ind = self.indent_level
        self.local_vars = dict(zip(pnames, ptypes))
        self.indent_level = 1
        try:
            body_c = self._translate_expr(body, expected_type=ret_t)
        finally:
            self.local_vars = saved_locals
            self.indent_level = saved_ind

        ret_c = CTypeMapper.to_c_type(ret_t)
        decl = ", ".join(CTypeMapper.to_c_decl(pt, pn) for pn, pt in zip(pnames, ptypes)) or "void"
        l_line = self._node_line(node) or 0
        l_file = self._display_path(src_file) or ""
        push_call = f'pengu_frame_push("{name}", "{l_file}", {l_line});'
        pop_call = "pengu_frame_pop();"
        if ret_c == "void":
            self.lambdas.append(f"static void {name}({decl}) {{ {push_call} {body_c}; {pop_call} }}")
        else:
            self.lambdas.append(f"static {ret_c} {name}({decl}) {{ {push_call} {ret_c} _lret = {body_c}; {pop_call} return _lret; }}")

    def generate_lambdas(self) -> str:
        """Emits the top-level 'static' functions generated for lambdas."""
        if not self.lambdas:
            return ""
        lines = ["/* --- Lambdas --- */"]
        lines.extend(self.lambdas)
        lines.append("")
        return "\n".join(lines)

    def _collect_top_stmt(self, top_node: Tree, filepath: str, prefix: Optional[str] = None) -> None:
        """Dispatches top-level statement collection."""
        stmt = unwrap_top_level(top_node)
        if not isinstance(stmt, Tree):
            return

        rule = stmt.data
        has_shards = len(stmt.children) > 1 and isinstance(stmt.children[1], Tree) and stmt.children[1].data == "shard_params"

        if rule == "rune_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            fields = {}
            for f in stmt.children[1:]:
                if isinstance(f, Tree) and f.data == "field_decl":
                    f_name = str(f.children[0])
                    f_type = ast_to_type(f.children[1], self._lookup_type_fn)
                    fields[f_name] = f_type
            self.runes[c_name] = fields
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_types.add(c_name)

        elif rule == "echo_decl":
            if has_shards:
                return
            name = str(stmt.children[0])
            c_name = f"{prefix}{name}" if prefix else name
            fields = {}
            for f in stmt.children[1:]:
                if isinstance(f, Tree) and f.data == "field_decl":
                    f_name = str(f.children[0])
                    f_type = ast_to_type(f.children[1], self._lookup_type_fn)
                    fields[f_name] = f_type
            self.echos[c_name] = fields
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
                c_type = ast_to_type(stmt.children[1], self._lookup_type_fn)
                expr_idx = 2
            expr_node = stmt.children[expr_idx]
            val = self.const_folder.fold(expr_node)
            self.consts[c_name] = (c_type, val)
            if filepath and filepath.endswith(".d.pengu"):
                self.declaration_consts.add(c_name)
            if filepath:
                norm_fp = os.path.abspath(filepath)
                norm_order = [os.path.abspath(p) for p in self.import_order]
                if len(norm_order) > 1 and norm_fp != norm_order[-1]:
                    is_std = "std" in norm_fp.replace("/", "\\").split("\\")
                    if is_std:
                        mod_name = os.path.splitext(os.path.basename(norm_fp))[0]
                        if mod_name and not name.startswith(f"{mod_name}_"):
                            self.consts[f"{mod_name}_{name}"] = (c_type, val)
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
            base_tname = enchanted_type.name.split("_")[0]
            if (self.symbols and base_tname in self.symbols.generic_runes) or getattr(enchanted_type, "type_params", None) or any(isinstance(t, TypeParam) for t in getattr(enchanted_type, "type_args", [])):
                return
            for w in stmt.children[1:]:
                if isinstance(w, Tree) and w.data == "weave_decl":
                    self._collect_weave(w, filepath, enchanted_type, prefix=prefix)

    def _collect_monomorphized_weave(self, specialized_name: str, node: Tree, subst_map: Dict[str, Type], enchanted_type: Optional[Type], filepath: str = ".") -> None:
        """Collects specialized monomorphized function details."""
        is_inline, is_ritual, idx = skip_weave_modifiers(node.children)

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
                "body_stmts": body_stmts,
                "subst_map": subst_map,
                "filepath": filepath,
                # Declaration line of the weave in its .pengu source, used for the
                # '#line' marker emitted before the C definition.
                "line": self._node_line(node),
            })

    def _collect_weave(self, node: Tree, filepath: str, enchanted_type: Optional[Type], prefix: Optional[str] = None) -> None:
        """Collects function declaration details."""
        is_inline, is_ritual, idx = skip_weave_modifiers(node.children)

        name = str(node.children[idx])
        idx += 1

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

        c_name = name
        if enchanted_type is not None:
            t_name = getattr(enchanted_type, "name", str(enchanted_type)).replace(" ", "_")
            # 'insignia' prefixes module-level weaves/declares but NOT methods
            # enchanting primitive/collection types (string, list, map, slice,
            # maybe, result): those keep their plain names (string_len, ...)
            # so they can never collide with the runtime pengu_string_* /
            # pengu_list_* / pengu_map_* primitive families.
            is_primitive_receiver = isinstance(enchanted_type, BaseType) or isinstance(
                enchanted_type, (ListType, MapType, SliceType, MaybeType, ResultType)
            )
            c_name = f"{t_name}_{name}" if is_primitive_receiver else (f"{prefix}{t_name}_{name}" if prefix else f"{t_name}_{name}")
        elif prefix:
            c_name = f"{prefix}{name}"
        elif filepath:
            norm_fp = os.path.abspath(filepath)
            norm_order = [os.path.abspath(p) for p in self.import_order]
            if len(norm_order) > 1 and norm_fp != norm_order[-1]:
                is_std = "std" in norm_fp.replace("/", "\\").split("\\")
                if is_std:
                    mod_name = os.path.splitext(os.path.basename(norm_fp))[0]
                    if mod_name and not name.startswith(f"{mod_name}_"):
                        c_name = f"{mod_name}_{name}"

        if name == "main" and enchanted_type is None:
            self.has_main = True
            # Remembered so the entry wrapper can forward it as the exit status.
            self.main_return_type = ret_type

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
            "is_ritual": is_ritual,
            "body_stmts": body_stmts,
            "filepath": filepath,
            # Declaration line of the weave in its .pengu source, used for the
            # '#line' marker emitted before the C definition.
            "line": self._node_line(node),
        })

    def generate_forward_declarations(self) -> str:
        """Generates consistent forward struct/union/omen declarations and function prototypes."""
        decls = []

        # Runes
        for name in self.runes:
            if name in self.declaration_types:
                continue
            decls.append(f"struct {name};")
            decls.append(f"typedef struct {name} {name};")

        # Echos
        for name in self.echos:
            if name in self.declaration_types:
                continue
            decls.append(f"union {name};")
            decls.append(f"typedef union {name} {name};")

        # Omens
        for name, variants in self.omens.items():
            if name in self.declaration_types:
                continue
            is_algebraic = any(bool(fields) for fields in variants.values())
            is_string_valued = bool(name in self.omen_values and any(isinstance(v, str) for v in self.omen_values[name].values()))
            if is_algebraic:
                decls.append(f"struct {name};")
                decls.append(f"typedef struct {name} {name};")
            elif not is_string_valued:
                decls.append(f"typedef enum {name} {name};")

        # Seals (Newtypes)
        for name, underlying in self.seals.items():
            if name in self.declaration_types:
                continue
            u_str = CTypeMapper.to_c_type(underlying)
            decls.append(f"typedef {u_str} {name};")

        # Range type
        decls.append("#ifndef PENGU_RANGE_DEFINED")
        decls.append("#define PENGU_RANGE_DEFINED")
        decls.append("typedef struct { int64_t start; int64_t end; } PenguRange;")
        decls.append("#endif")

        if not decls:
            return ""

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Forward Declarations",
            " * ------------------------------------------------------------------------- */",
        ] + decls + [""]
        return "\n".join(lines)

    def generate_type_definitions(self) -> str:
        """Generates full struct, union, enum, and typedef definitions."""
        blocks = []

        # 1. Type Aliases
        alias_lines = []
        for name, target in self.aliases.items():
            if name in self.declaration_types:
                continue
            if isinstance(target, BaseType) and target.name == "opaque":
                alias_lines.append(f"typedef struct {name} {name};")
            else:
                target_str = CTypeMapper.to_c_type(target)
                alias_lines.append(f"typedef {target_str} {name};")
        if alias_lines:
            blocks.append("\n".join(alias_lines))

        # 1.5 Seals (Newtypes)
        seal_lines = []
        for name, underlying in self.seals.items():
            if name in self.declaration_types:
                continue
            u_str = CTypeMapper.to_c_type(underlying)
            seal_lines.append(f"typedef {u_str} {name};")
        if seal_lines:
            blocks.append("\n".join(seal_lines))

        # 2. Runes (Structs)
        for name, fields in self.runes.items():
            if name in self.declaration_types:
                continue
            rune_lines = [f"struct {name} {{"]
            for f_name, f_type in fields.items():
                if isinstance(f_type, ArrayType) and f_type.size is not None:
                    elem_str = CTypeMapper.to_c_type(f_type.element)
                    rune_lines.append(f"  {elem_str} {self._c_ident(f_name)}[{f_type.size}];")
                else:
                    f_str = CTypeMapper.to_c_type(f_type)
                    rune_lines.append(f"  {f_str} {self._c_ident(f_name)};")
            rune_lines.append("};")
            blocks.append("\n".join(rune_lines))

        # 3. Echos (Unions)
        for name, fields in self.echos.items():
            if name in self.declaration_types:
                continue
            echo_lines = [f"union {name} {{"]
            for f_name, f_type in fields.items():
                if isinstance(f_type, ArrayType) and f_type.size is not None:
                    elem_str = CTypeMapper.to_c_type(f_type.element)
                    echo_lines.append(f"  {elem_str} {self._c_ident(f_name)}[{f_type.size}];")
                else:
                    f_str = CTypeMapper.to_c_type(f_type)
                    echo_lines.append(f"  {f_str} {self._c_ident(f_name)};")
            echo_lines.append("};")
            blocks.append("\n".join(echo_lines))

        # 4. Omens
        for name, variants in self.omens.items():
            if name in self.declaration_types:
                continue
            is_algebraic = any(bool(fields) for fields in variants.values())
            if is_algebraic:
                enum_name = f"{name}_Tag"
                omen_lines = [
                    f"typedef enum {enum_name} {{",
                    *[f"  {name}_{v_name}," for v_name in variants],
                    f"}} {enum_name};",
                    "",
                    f"struct {name} {{",
                    f"  {enum_name} tag;",
                    "  union {",
                ]
                for v_name, v_fields in variants.items():
                    if v_fields:
                        omen_lines.append("    struct {")
                        for f_name, f_type in v_fields.items():
                            if isinstance(f_type, ArrayType) and f_type.size is not None:
                                elem_str = CTypeMapper.to_c_type(f_type.element)
                                omen_lines.append(f"      {elem_str} {self._c_ident(f_name)}[{f_type.size}];")
                            else:
                                f_str = CTypeMapper.to_c_type(f_type)
                                omen_lines.append(f"      {f_str} {self._c_ident(f_name)};")
                        omen_lines.append(f"    }} {self._c_ident(v_name)};")
                omen_lines.extend([
                    "  } data;",
                    "};",
                ])
                blocks.append("\n".join(omen_lines))
            else:
                is_string_valued = False
                if name in self.omen_values:
                    is_string_valued = any(isinstance(v, str) for v in self.omen_values[name].values())
                if is_string_valued:
                    def _c_esc(s: str) -> str:
                        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
                    omen_lines = [f"/* String-valued omen '{name}' */"]
                    for v_name in variants:
                        val = None
                        if name in self.omen_values and v_name in self.omen_values[name]:
                            val = self.omen_values[name][v_name]
                        if isinstance(val, str):
                            omen_lines.append(f'#define {name}_{v_name} pengu_string_from_cstr("{_c_esc(val)}")')
                        else:
                            omen_lines.append(f"/* {name}_{v_name}: no string value (payload variant) */")
                    blocks.append("\n".join(omen_lines))
                    continue
                omen_lines = [f"typedef enum {name} {{"]
                for v_name in variants:
                    if name in self.omen_values and v_name in self.omen_values[name]:
                        val = self.omen_values[name][v_name]
                        omen_lines.append(f"  {name}_{v_name} = {val},")
                    else:
                        omen_lines.append(f"  {name}_{v_name},")
                omen_lines.append(f"}} {name};")
                blocks.append("\n".join(omen_lines))

        if not blocks:
            return ""

        header = [
            "/* -------------------------------------------------------------------------",
            " * Type Definitions",
            " * ------------------------------------------------------------------------- */",
        ]
        return "\n".join(header) + "\n" + "\n\n".join(blocks) + "\n"

    def generate_global_constants(self) -> str:
        """Generates #define or const statements for global module constants."""
        if not self.consts:
            return ""

        emitted_lines = []
        for name, (c_type, val) in self.consts.items():
            if name in self.declaration_consts:
                continue
            if val is not None:
                if isinstance(val, str):
                    if self._is_ref_char_type(c_type):
                        emitted_lines.append(f'#define {name} "{val}"')
                    else:
                        emitted_lines.append(f'#define {name} pengu_string_from_cstr("{val}")')
                elif isinstance(val, bool):
                    emitted_lines.append(f'#define {name} {"true" if val else "false"}')
                else:
                    emitted_lines.append(f"#define {name} {val}")
            else:
                t_str = CTypeMapper.to_c_type(c_type, const=True)
                emitted_lines.append(f"{t_str} {name};")

        if not emitted_lines:
            return ""

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Global Constants",
            " * ------------------------------------------------------------------------- */",
        ] + emitted_lines + [""]
        return "\n".join(lines)

    def generate_constants(self) -> str:
        """Alias for generate_global_constants."""
        return self.generate_global_constants()

    @staticmethod
    def _c_ident(name: str) -> str:
        if name in (
            "default", "case", "switch", "register", "goto", "volatile", "union", "enum", "struct", "auto",
            "long", "short", "int", "char", "float", "double", "signed", "unsigned", "void", "const",
            "static", "extern", "inline", "restrict", "return", "sizeof", "typedef"
        ):
            return f"_{name}"
        return name

    def _get_omen_variant_c_name(self, omen_name: str, variant_name: str) -> str:
        """Returns the C name emitted for an omen variant.

        Omens declared in a ``.d.pengu`` declaration file mirror a C enum from
        an included header: their C header already defines the enum constants
        under the *simple* variant names (e.g. ``KEY_LEFT``), so the type name
        must NOT be prefixed. Omens defined in normal ``.pengu`` modules are
        compiler-generated and keep the ``Omen_variant`` prefix to avoid
        collisions between different enums.

        Args:
            omen_name: Logical name of the omen.
            variant_name: Simple variant name as written in PenguScript.

        Returns:
            The C identifier to emit for this variant.
        """
        if omen_name in self.declaration_types:
            return variant_name
        return f"{omen_name}_{variant_name}"

    def generate_function_prototypes(self) -> str:
        """Generates all forward function prototypes."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Prototypes",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            c_name = w["c_name"]
            ret_str = CTypeMapper.to_c_type(w["return_type"])
            param_strs = []

            # Self parameter for enchanting methods (only if not ritual)
            if w["enchanted_type"] is not None and not w.get("is_ritual", False):
                self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
                param_strs.append(f"{self_t_str}* self")

            for p_info in w["params"]:
                p_name, p_type = p_info[0], p_info[1]
                param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name)))

            params_formatted = ", ".join(param_strs) if param_strs else "void"
            inline_pfx = "static inline __attribute__((always_inline)) " if w["is_inline"] else ""

            if c_name == "main":
                # Expose main wrapper or standard signature
                lines.append(f"{inline_pfx}{ret_str} pengu_main({params_formatted});")
            else:
                lines.append(f"{inline_pfx}{ret_str} {c_name}({params_formatted});")

        lines.append("")
        return "\n".join(lines)

    def generate_function_definitions(self) -> str:
        """Generates function implementation bodies in topological module order."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Function Definitions",
            " * ------------------------------------------------------------------------- */",
        ]

        for w in self.weaves:
            self._apply_main_flag(w.get("filepath"))
            self.current_source_file = w.get("filepath")
            c_name = w["c_name"]
            ret_str = CTypeMapper.to_c_type(w["return_type"])
            param_strs = []

            if w["enchanted_type"] is not None and not w.get("is_ritual", False):
                self_t_str = CTypeMapper.to_c_type(w["enchanted_type"])
                param_strs.append(f"{self_t_str}* self")

            for p_info in w["params"]:
                p_name, p_type = p_info[0], p_info[1]
                # restrict is opt-in: see CTypeMapper.to_c_decl
                param_strs.append(CTypeMapper.to_c_decl(p_type, self._c_ident(p_name)))

            params_formatted = ", ".join(param_strs) if param_strs else "void"
            inline_pfx = "static inline __attribute__((always_inline)) " if w["is_inline"] else ""
            fn_actual_name = "pengu_main" if c_name == "main" else c_name

            marker = self._line_marker(w.get("line"), w.get("filepath"))
            if marker:
                lines.append(marker)
            lines.append(f"{inline_pfx}{ret_str} {fn_actual_name}({params_formatted}) {{")
            self.indent_level += 1
            push_path = self._display_path(w.get("filepath")) or ""
            push_line = w.get("line") or 0
            lines.append(f'{self.indent()}pengu_frame_push("{fn_actual_name}", "{push_path}", {push_line});')
            self.current_function = fn_actual_name
            self.current_return_type = w["return_type"]
            self.current_enchanted_type = w.get("enchanted_type")
            self.current_subst_map = w.get("subst_map", {})
            self.local_vars = {}
            if w["enchanted_type"] is not None and not w.get("is_ritual", False):
                self.local_vars["self"] = RefType(w["enchanted_type"])
            for p_info in w["params"]:
                self.local_vars[p_info[0]] = p_info[1]

            self.defer_stack.append([])
            self.errdefer_stack.append([])
            self._auto_banish_push("weave")

            body_code = self._translate_block(w["body_stmts"])
            lines.append(body_code)

            # Emit any remaining top-level defers and auto-banishes before function exit
            active_defers = self.defer_stack.pop() if self.defer_stack else []
            if self.errdefer_stack:
                self.errdefer_stack.pop()
            if not self._stmts_end_with_jump(w["body_stmts"]):
                if active_defers:
                    lines.append(f"{self.indent()}/* Deferred cleanup */")
                    for d in reversed(active_defers):
                        if d.endswith("}"):
                            lines.append(f"{self.indent()}{d}")
                        else:
                            lines.append(f"{self.indent()}{d};")

                auto_banish = self._flush_current_scope_banish()
                if auto_banish:
                    lines.extend(auto_banish)
            self.auto_banish_stack.pop()

            lines.append(f"{self.indent()}pengu_frame_pop();")
            self.indent_level -= 1
            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _node_line(node: Any) -> Optional[int]:
        """Returns the 1-based `.pengu` source line of an AST node, or None.

        Collected declarations are sometimes rebuilt by the collector and lose
        their ``meta`` block; the first descendant token that still carries a
        line number is used as a fallback (tokens always keep theirs).
        """
        meta = getattr(node, "meta", None)
        line = getattr(meta, "line", None) if meta is not None else None
        if line:
            try:
                return int(line)
            except (TypeError, ValueError):
                pass

        stack = [node]
        seen = 0
        while stack and seen < 64:
            current = stack.pop(0)
            seen += 1
            tok_line = getattr(current, "line", None)
            if tok_line:
                try:
                    return int(tok_line)
                except (TypeError, ValueError):
                    pass
            children = getattr(current, "children", None)
            if children:
                stack.extend(c for c in children if isinstance(c, (Tree, Token)))
        return None

    def _display_path(self, filepath: Optional[str]) -> Optional[str]:
        """Returns the file name to spell in `#line`.

        Paths are made relative to the bundle directory (e.g.
        ``../src/main.pengu``), which keeps them short and machine-independent;
        the absolute path is only used when a relative one cannot be computed
        (different Windows drive).
        """
        if not filepath:
            return None
        path = os.path.abspath(filepath)
        if self.line_base_dir:
            try:
                path = os.path.relpath(path, self.line_base_dir)
            except ValueError:  # different drive on Windows
                path = os.path.abspath(filepath)
        return str(path).replace("\\", "/")

    def _line_marker(self, node: Any, filepath: Optional[str] = None) -> str:
        """Builds a `#line N "file.pengu"` directive for `node`.

        Args:
            node: AST node carrying Lark position metadata, or a raw line number.
            filepath: Optional explicit source file; defaults to the module
                currently being translated.

        Returns:
            The directive, or an empty string when the line is unknown or
            markers are disabled.
        """
        if not self.emit_line_markers:
            return ""
        line = node if isinstance(node, int) else self._node_line(node)
        if line is None:
            return ""
        shown = self._display_path(filepath or self.current_source_file)
        if not shown:
            return f"#line {line}"
        escaped = shown.replace("\\", "\\\\").replace('"', '\\"')
        return f'#line {line} "{escaped}"'

    def _translate_block(self, stmts: List[Tree]) -> str:
        """Translates a list of statements in a block.

        Each statement is preceded by a `#line` marker (statement context only)
        so compiler diagnostics point at the `.pengu` line that produced the C.
        """
        lines = []
        markers = self.emit_line_markers and self._expr_depth == 0
        for stmt in stmts:
            s_code = self._translate_stmt(stmt)
            if s_code:
                if markers:
                    marker = self._line_marker(stmt)
                    if marker:
                        lines.append(marker)
                lines.append(s_code)
        return "\n".join(lines)

    def _translate_stmt(self, node: Tree) -> str:
        """Translates single statement node to C99."""
        if not isinstance(node, Tree):
            return ""

        if node.data == "stmt" and node.children:
            return self._translate_stmt(node.children[0])

        # Single-line block statements ('if c: return 0') parse as aliased
        # nodes (or a bare 'simple_stmt' holding one expression); normalize them
        # onto the canonical statement rules so they emit the same C as the
        # indented spelling.
        canonical = SIMPLE_STMT_ALIASES.get(node.data)
        if canonical is not None:
            node = Tree(canonical, node.children, meta=node.meta)
        elif node.data == "simple_stmt":
            if len(node.children) != 1:
                return ""
            node = Tree("expr_stmt", [node.children[0]], meta=node.meta)

        rule = node.data
        ind = self.indent()

        if rule == "var_decl":
            is_borrowed, name_idx = self._has_borrowed_modifier(node)
            name = str(node.children[name_idx])
            type_node = None
            if name_idx == 1:
                type_node = node.children[2]
                expr_node = node.children[3]
            else:
                expr_idx = 1
                if len(node.children) == 3:
                    type_node = node.children[1]
                    expr_idx = 2
                expr_node = node.children[expr_idx]

            t = None
            sym = getattr(node, "_pengu_symbol", None)
            if sym is None and self.symbols:
                sym = self.symbols.lookup(name)
            if type_node is not None:
                t = ast_to_type(type_node, self._lookup_type_fn)
                if isinstance(t, ArrayType) and sym and isinstance(sym.type, ArrayType):
                    sync_array_sizes(t, sym.type)
                if isinstance(t, ArrayType) and expr_node is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        inf_t = inferrer.infer(expr_node)
                        if isinstance(inf_t, ArrayType):
                            sync_array_sizes(t, inf_t)
                    except Exception:
                        pass
            else:
                if sym:
                    t = sym.type
                if t is None and expr_node is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        t = inferrer.infer(expr_node)
                    except Exception:
                        pass

            if t is not None:
                self.local_vars[name] = t
            if sym and getattr(sym, "is_auto_banished", False) and t is not None:
                self._auto_banish_register(name, t)

            t_str = CTypeMapper.to_c_type(t) if t is not None else "int32_t"
            if t_str == "void":
                t_str = "int32_t"

            if isinstance(expr_node, Tree) and expr_node.data == "or_block":
                left_op = expr_node.children[0]
                block_stmts = expr_node.children[1:]
                tmp_res = self.get_temp_name("_res")
                left_c = self._translate_expr(left_op)
                prev_error_t = self.local_vars.get("error")
                self.local_vars["error"] = STRING_TYPE
                self._auto_banish_push("block")
                try:
                    self.indent_level += 1
                    inner_body = [self._translate_stmt(bs) for bs in block_stmts]
                    banish = self._flush_current_scope_banish() if not self._stmts_end_with_jump(block_stmts) else []
                    self.indent_level -= 1
                finally:
                    if self.auto_banish_stack and self.auto_banish_stack[-1][0] == "block":
                        self.auto_banish_stack.pop()
                    if prev_error_t is None:
                        self.local_vars.pop("error", None)
                    else:
                        self.local_vars["error"] = prev_error_t
                block_c = "\n".join(inner_body + banish)
                return (
                    f"{ind}PenguResult {tmp_res} = {left_c};\n"
                    f"{ind}if (!pengu_result_is_ok(&{tmp_res})) {{\n"
                    f"{ind}  PenguString error = pengu_string_from_cstr({tmp_res}.err_val ? {tmp_res}.err_val : \"error\");\n"
                    f"{block_c}\n"
                    f"{ind}}}\n"
                    f"{ind}{t_str} {name} = ({t_str})({tmp_res}.ok_val);"
                )

            alloc_comment = " /* stack */" if (isinstance(t, (RuneType, ArrayType)) or (sym and sym.is_stack_alloc)) else ""
            if isinstance(t, ArrayType) and t.size is not None:
                dims, base_c = get_array_dims_and_base(t)
                dims_str = "".join(f"[{d}]" for d in dims)
                if isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                    return f"{ind}{base_c} {name}{dims_str} = {{0}};{alloc_comment}"
                expr_code = self._translate_expr(expr_node, expected_type=t)
                return f"{ind}{base_c} {name}{dims_str} = {expr_code};{alloc_comment}"
            if isinstance(t, ArrayType) and t.size is None and isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                array_size = self._translate_expr(expr_node.children[1])
                elem_str = CTypeMapper.to_c_type(t.element)
                return f"{ind}{elem_str} {name}[{array_size}] = {{0}};{alloc_comment}"
            expr_code = self._translate_expr(expr_node, expected_type=t)
            if isinstance(t, FnType) or (isinstance(t, RefType) and isinstance(t.target, FnType)):
                # Function-pointer values (lambdas, weave refs, C callbacks)
                # need a proper declarator: 'ret (*name)(params) = value;'
                return f"{ind}{CTypeMapper.to_c_decl(t, name)} = {expr_code};{alloc_comment}"
            return f"{ind}{t_str} {name} = {expr_code};{alloc_comment}"


        elif rule == "static_var_decl":
            name = str(node.children[0])
            type_node = None
            expr_idx = 1
            if len(node.children) == 3:
                type_node = node.children[1]
                expr_idx = 2
            expr_node = node.children[expr_idx]

            t = None
            sym = self.symbols.lookup(name) if self.symbols else None
            if type_node is not None:
                t = ast_to_type(type_node, self._lookup_type_fn)
            else:
                if sym:
                    t = sym.type
                if t is None and expr_node is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        t = inferrer.infer(expr_node)
                    except Exception:
                        pass
            if t is not None:
                self.local_vars[name] = t
            t_str = CTypeMapper.to_c_type(t) if t is not None else "int32_t"
            if t_str == "void":
                t_str = "int32_t"

            folded = None
            if expr_node is not None:
                try:
                    folded = self.const_folder.fold(expr_node)
                except Exception:
                    folded = None

            # Scalar compile-time constants can initialize a C static directly.
            if folded is not None and not isinstance(folded, str):
                val_str = self._format_const_val(folded, expected_type=t)
                return f"{ind}static {t_str} {name} = {val_str};"

            # Non-constant (e.g. strings, structs) statics are zero-initialized and
            # lazily assigned on first execution (once per process).
            init_c = self._translate_expr(expr_node, expected_type=t) if expr_node is not None else "0"
            guard = f"{name}_initialized"
            static_decl = (CTypeMapper.to_c_decl(t, name)
                           if (isinstance(t, FnType)
                               or (isinstance(t, RefType) and isinstance(t.target, FnType)))
                           else f"{t_str} {name}")
            return (
                f"{ind}static {static_decl};\n"
                f"{ind}static bool {guard} = false;\n"
                f"{ind}if (!{guard}) {{\n"
                f"{ind}  {name} = {init_c};\n"
                f"{ind}  {guard} = true;\n"
                f"{ind}}}"
            )


        elif rule == "let_decl":
            is_borrowed, name_idx = self._has_borrowed_modifier(node)
            var_names_node = node.children[name_idx]
            names = []
            if isinstance(var_names_node, Tree) and var_names_node.data == "var_name_list":
                names = [str(tok) for tok in var_names_node.children]
            else:
                names = [str(var_names_node)]

            if name_idx == 1:
                type_node = node.children[2]
                expr_node = node.children[3]
            else:
                expr_idx = 1
                type_node = None
                if len(node.children) == 3:
                    type_node = node.children[1]
                    expr_idx = 2
                expr_node = node.children[expr_idx]

            if len(names) == 1:
                name = names[0]
                t = None
                sym = getattr(node, "_pengu_symbol", None)
                if sym is None and self.symbols:
                    sym = self.symbols.lookup(name)
                if type_node is not None:
                    t = ast_to_type(type_node, self._lookup_type_fn)
                    if isinstance(t, ArrayType) and sym and isinstance(sym.type, ArrayType):
                        sync_array_sizes(t, sym.type)
                    if isinstance(t, ArrayType) and expr_node is not None:
                        try:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_name, lv_t in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                            inf_t = inferrer.infer(expr_node)
                            if isinstance(inf_t, ArrayType):
                                sync_array_sizes(t, inf_t)
                        except Exception:
                            pass
                else:
                    if sym:
                        t = sym.type
                    if t is None and expr_node is not None:
                        try:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_name, lv_t in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                            t = inferrer.infer(expr_node)
                        except Exception:
                            pass
                if t is not None:
                    self.local_vars[name] = t
                if sym and getattr(sym, "is_auto_banished", False) and t is not None:
                    self._auto_banish_register(name, t)
                t_str = CTypeMapper.to_c_type(t, const=True)
                if t_str == "void":
                    t_str = "const int32_t"

                if isinstance(expr_node, Tree) and expr_node.data == "or_block":
                    left_op = expr_node.children[0]
                    block_stmts = expr_node.children[1:]
                    tmp_res = self.get_temp_name("_res")
                    left_c = self._translate_expr(left_op)
                    prev_error_t = self.local_vars.get("error")
                    self.local_vars["error"] = STRING_TYPE
                    self._auto_banish_push("block")
                    try:
                        self.indent_level += 1
                        inner_body = [self._translate_stmt(bs) for bs in block_stmts]
                        banish = self._flush_current_scope_banish() if not self._stmts_end_with_jump(block_stmts) else []
                        self.indent_level -= 1
                    finally:
                        if self.auto_banish_stack and self.auto_banish_stack[-1][0] == "block":
                            self.auto_banish_stack.pop()
                        if prev_error_t is None:
                            self.local_vars.pop("error", None)
                        else:
                            self.local_vars["error"] = prev_error_t
                    block_c = "\n".join(inner_body + banish)
                    return (
                        f"{ind}PenguResult {tmp_res} = {left_c};\n"
                        f"{ind}if (!pengu_result_is_ok(&{tmp_res})) {{\n"
                        f"{ind}  PenguString error = pengu_string_from_cstr({tmp_res}.err_val ? {tmp_res}.err_val : \"error\");\n"
                        f"{block_c}\n"
                        f"{ind}}}\n"
                        f"{ind}{t_str} {name} = ({t_str})({tmp_res}.ok_val);"
                    )

                alloc_comment = " /* stack */" if (sym and sym.is_stack_alloc) else ""
                if isinstance(t, ArrayType) and t.size is not None:
                    dims, base_c = get_array_dims_and_base(t)
                    dims_str = "".join(f"[{d}]" for d in dims)
                    if isinstance(expr_node, Tree) and expr_node.data == "array_init_expr":
                        return f"{ind}const {base_c} {name}{dims_str} = {{0}};{alloc_comment}"
                    expr_code = self._translate_expr(expr_node, expected_type=t)
                    return f"{ind}const {base_c} {name}{dims_str} = {expr_code};{alloc_comment}"
                expr_code = self._translate_expr(expr_node, expected_type=t)
                if isinstance(t, FnType) or (isinstance(t, RefType) and isinstance(t.target, FnType)):
                    # Function-pointer binding: 'ret (*name)(params) = value;'
                    return f"{ind}{CTypeMapper.to_c_decl(t, name)} = {expr_code};{alloc_comment}"
                return f"{ind}{t_str} {name} = {expr_code};{alloc_comment}"
            else:
                # Destructuring
                tmp = self.get_temp_name("_destruct")
                expr_type = self._infer_node_type(expr_node)
                expr_code = self._translate_expr(expr_node)

                # Match rune struct
                matched_rune = None
                if isinstance(expr_type, RuneType) and expr_type.name in self.runes:
                    matched_rune = expr_type.name
                elif isinstance(expr_type, BaseType) and expr_type.name in self.runes:
                    matched_rune = expr_type.name
                else:
                    for r_name, r_fields in self.runes.items():
                        if len(r_fields) == len(names):
                            matched_rune = r_name
                            break

                tmp_type = matched_rune if matched_rune else "const void*"
                lines = [f"{ind}{tmp_type} {tmp} = {expr_code};"]

                rune_field_names = list(self.runes[matched_rune].keys()) if (matched_rune and matched_rune in self.runes) else []

                for i, name in enumerate(names):
                    sym = self.symbols.lookup(name) if self.symbols else None
                    var_t = sym.type if sym else None
                    if var_t is None and matched_rune and matched_rune in self.runes and i < len(self.runes[matched_rune]):
                        var_t = list(self.runes[matched_rune].values())[i]
                    if var_t is not None:
                        self.local_vars[name] = var_t
                    if sym and getattr(sym, "is_auto_banished", False) and var_t is not None:
                        self._auto_banish_register(name, var_t)
                    t_str = CTypeMapper.to_c_type(var_t, const=True) if var_t else "const int32_t"
                    if t_str == "void":
                        t_str = "const int32_t"
                    if i < len(rune_field_names):
                        lines.append(f"{ind}{t_str} {name} = {tmp}.{rune_field_names[i]};")
                    else:
                        lines.append(f"{ind}{t_str} {name} = {tmp}[{i}];")
                return "\n".join(lines)

        elif rule == "set_stmt":
            target_node = node.children[0]
            expr_node = node.children[1]
            target_str = self._translate_set_target(target_node)

            inner_target = target_node.children[0] if (isinstance(target_node, Tree) and target_node.data == "set_target" and target_node.children) else target_node
            target_type = self._infer_node_type(inner_target)
            if target_type is None:
                if isinstance(inner_target, Tree) and inner_target.data == "normal_target":
                    obj_name = str(inner_target.children[0])
                    target_type = self._lookup_var_type(obj_name)
                elif isinstance(inner_target, Token):
                    target_type = self._lookup_var_type(str(inner_target))

            expr_str = self._translate_expr(expr_node, expected_type=target_type)

            rune_name = None
            if target_type is not None:
                if isinstance(target_type, RuneType):
                    rune_name = target_type.name
                elif isinstance(target_type, BaseType) and target_type.name in self.runes:
                    rune_name = target_type.name

            if rune_name and rune_name in self.runes and len(self.runes[rune_name]) >= 3:
                return f"{ind}memcpy(&({target_str}), &({expr_str}), sizeof({rune_name}));"

            return f"{ind}{target_str} = {expr_str};"

        elif rule == "compound_set_stmt":
            # 'set target OP value' -> C compound assignment (strings concatenate).
            target_node = node.children[0]
            op = str(node.children[1])
            expr_node = node.children[2]
            target_str = self._translate_set_target(target_node)

            inner_target = target_node.children[0] if (isinstance(target_node, Tree) and target_node.data == "set_target" and target_node.children) else target_node
            target_type = None
            if isinstance(inner_target, Tree) and inner_target.data == "normal_target" and inner_target.children:
                target_type = self._lookup_var_type(str(inner_target.children[0]))
            elif isinstance(inner_target, Token):
                target_type = self._lookup_var_type(str(inner_target))

            expr_str = self._translate_expr(expr_node, expected_type=target_type)

            if op == "+=" and isinstance(target_type, BaseType) and target_type.name == "string":
                return f"{ind}{target_str} = pengu_string_concat({target_str}, {expr_str});"

            return f"{ind}{target_str} {op} {expr_str};"

        elif rule == "calling_stmt":
            call_tree = Tree("calling_expr", node.children)
            expr_code = self._translate_expr(call_tree)
            return f"{ind}{expr_code};"

        elif rule == "named_stmt":
            name = str(node.children[0])
            expr_str = self._translate_expr(node.children[1])
            return f"{ind}{name} = {expr_str};"


        elif rule == "if_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            else_node = node.children[2] if len(node.children) > 2 else None

            binding = self._binding_cond(cond_node)
            if binding is not None:
                # 'if name as T is <maybe>:' — a scoped unwrap, never folded.
                return self._translate_binding_if(node, binding)

            # Dead code elimination for constant condition
            folded = self.const_folder.fold(cond_node)
            if folded is not None:
                if bool(folded) is True:
                    body_str = self._translate_nested_block_with_banish(block_node, "block")
                    return f"{ind}/* dead code eliminated (branch always true) */\n{body_str}"
                else:
                    if else_node:
                        self.indent_level += 1
                        else_str = self._translate_else_block(else_node)
                        self.indent_level -= 1
                        return f"{ind}/* dead code eliminated (branch always false) */\n{else_str}"
                    return f"{ind}/* dead code eliminated (branch always false) */"

            cond_str = self._translate_if_cond(cond_node)
            self.indent_level += 1
            body_str = self._translate_nested_block_with_banish(block_node, "block")
            self.indent_level -= 1

            res = f"{ind}if ({cond_str}) {{\n{body_str}\n{ind}}}"
            if else_node:
                self.indent_level += 1
                else_str = self._translate_else_block(else_node)
                self.indent_level -= 1
                res += f" else {{\n{else_str}\n{ind}}}"
            return res

        elif rule == "unless_stmt":
            cond_node = node.children[0]
            block_node = node.children[1]
            else_node = node.children[2] if len(node.children) > 2 else None

            folded = self.const_folder.fold(cond_node)
            if folded is not None:
                if bool(folded) is False:
                    body_str = self._translate_nested_block_with_banish(block_node, "block")
                    return f"{ind}/* dead code eliminated (unless always true) */\n{body_str}"
                else:
                    if else_node:
                        self.indent_level += 1
                        else_str = self._translate_else_block(else_node)
                        self.indent_level -= 1
                        return f"{ind}/* dead code eliminated (unless always false) */\n{else_str}"
                    return f"{ind}/* dead code eliminated (unless always false) */"

            cond_str = self._translate_expr(cond_node)
            self.indent_level += 1
            body_str = self._translate_nested_block_with_banish(block_node, "block")
            self.indent_level -= 1

            res = f"{ind}if (!({cond_str})) {{\n{body_str}\n{ind}}}"
            if else_node:
                self.indent_level += 1
                else_str = self._translate_else_block(else_node)
                self.indent_level -= 1
                res += f" else {{\n{else_str}\n{ind}}}"
            return res

        elif rule == "when_stmt":
            # Compile-time conditional statement: emit only the active branch.
            cond_node = node.children[0]
            block_node = node.children[1] if (len(node.children) > 1 and isinstance(node.children[1], Tree) and node.children[1].data == "block") else None
            else_node = node.children[2] if (len(node.children) > 2 and isinstance(node.children[2], Tree)) else None
            val = eval_comptime(self.compile_env, cond_node)
            if val is None or not isinstance(val, bool):
                raise SemanticError(
                    "'when' condition must evaluate to a compile-time boolean constant",
                    code="E0039",
                )
            if val is True and block_node is not None:
                return self._translate_nested_block(block_node)
            if val is False and else_node is not None:
                if else_node.data == "when_else_plain":
                    stmt_nodes = [c for c in else_node.children if isinstance(c, Tree)]
                    return self._translate_block(stmt_nodes)
                if else_node.data == "when_else_when":
                    parts = [self._translate_stmt(c) for c in else_node.children if isinstance(c, Tree)]
                    return "\n".join(p for p in parts if p)
            return ""

        elif rule == "while_stmt":
            return self._translate_while(node)

        elif rule in ("for_stmt", "for_range_stmt", "for_in_stmt"):
            if rule == "for_range_stmt":
                return self._translate_for_range(node)
            elif rule == "for_in_stmt":
                return self._translate_for_in(node)
            first_child = node.children[0]
            if isinstance(first_child, Tree) and first_child.data == "for_range_stmt":
                return self._translate_for_range(first_child)
            elif isinstance(first_child, Tree) and first_child.data == "for_in_stmt":
                return self._translate_for_in(first_child)
            return ""

        elif rule == "with_stmt":
            target_expr = node.children[0]
            stmts = node.children[1:]
            target_str = self._translate_expr(target_expr)

            self.with_stack.append(target_str)
            body_lines = []
            for s in stmts:
                code = self._translate_stmt(s)
                if code:
                    body_lines.append(code)
            self.with_stack.pop()

            return "\n".join(body_lines)

        elif rule == "defer_stmt":
            child = node.children[0]
            if isinstance(child, Tree) and child.data == "block":
                self.indent_level += 1
                inner_stmts = [self._translate_stmt(s) for s in child.children]
                self.indent_level -= 1
                block_c = "\n".join(s for s in inner_stmts if s)
                defer_str = f"{{\n{block_c}\n{ind}}}"
            elif isinstance(child, Tree) and (child.data.endswith("_stmt") or child.data == "stmt"):
                stmt_c = self._translate_stmt(child).strip()
                if stmt_c.endswith(";"):
                    stmt_c = stmt_c[:-1]
                defer_str = stmt_c
            else:
                defer_str = self._translate_expr(child)
            if self.defer_stack:
                self.defer_stack[-1].append(defer_str)
            return f"{ind}/* defer */"

        elif rule == "errdefer_stmt":
            child = node.children[0]
            if isinstance(child, Tree) and child.data == "block":
                self.indent_level += 1
                inner_stmts = [self._translate_stmt(s) for s in child.children]
                self.indent_level -= 1
                block_c = "\n".join(s for s in inner_stmts if s)
                errdefer_str = f"{{\n{block_c}\n{ind}}}"
            elif isinstance(child, Tree) and (child.data.endswith("_stmt") or child.data == "stmt"):
                stmt_c = self._translate_stmt(child).strip()
                if stmt_c.endswith(";"):
                    stmt_c = stmt_c[:-1]
                errdefer_str = stmt_c
            else:
                errdefer_str = self._translate_expr(child)
            if self.errdefer_stack:
                self.errdefer_stack[-1].append(errdefer_str)
            return f"{ind}/* errdefer */"

        elif rule == "banish_stmt":
            b_code = self._translate_banish_target(node.children[0])
            return f"{ind}{b_code};"

        elif rule == "return_stmt":
            ret_expr = node.children[0] if node.children else None
            ret_val_str = self._translate_expr(ret_expr, expected_type=self.current_return_type) if ret_expr is not None else ""

            is_err_ret = False
            if "pengu_result_err" in ret_val_str or "error" in ret_val_str:
                is_err_ret = True

            cleanup_lines = []
            if is_err_ret and self.errdefer_stack:
                for d in reversed(self.errdefer_stack[-1]):
                    if d.endswith("}"):
                        cleanup_lines.append(f"{ind}{d}")
                    else:
                        cleanup_lines.append(f"{ind}{d};")

            if self.defer_stack:
                for d in reversed(self.defer_stack[-1]):
                    if d.endswith("}"):
                        cleanup_lines.append(f"{ind}{d}")
                    else:
                        cleanup_lines.append(f"{ind}{d};")

            for _, entries in reversed(self.auto_banish_stack):
                for name, t in reversed(entries):
                    code = self._emit_auto_banish(name, t)
                    if code:
                        cleanup_lines.append(code)

            cleanup_str = "\n".join(cleanup_lines) + ("\n" if cleanup_lines else "")
            pop_stmt = f"{ind}pengu_frame_pop();"
            if ret_expr is not None:
                if cleanup_lines:
                    tmp = self.get_temp_name("_ret")
                    ret_t_str = CTypeMapper.to_c_type(self.current_return_type)
                    return f"{ind}{ret_t_str} {tmp} = {ret_val_str};\n{cleanup_str}{pop_stmt}\n{ind}return {tmp};"
                return f"{pop_stmt}\n{ind}return {ret_val_str};"
            return f"{cleanup_str}{pop_stmt}\n{ind}return;"

        elif rule == "break_stmt":
            cleanup_lines = []
            for kind, entries in reversed(self.auto_banish_stack):
                if kind == "loop":
                    break
                for name, t in reversed(entries):
                    code = self._emit_auto_banish(name, t)
                    if code:
                        cleanup_lines.append(code)
            if cleanup_lines:
                return "\n".join(cleanup_lines) + f"\n{ind}break;"
            return f"{ind}break;"

        elif rule == "continue_stmt":
            cleanup_lines = []
            for kind, entries in reversed(self.auto_banish_stack):
                if kind == "loop":
                    break
                for name, t in reversed(entries):
                    code = self._emit_auto_banish(name, t)
                    if code:
                        cleanup_lines.append(code)
            if cleanup_lines:
                return "\n".join(cleanup_lines) + f"\n{ind}continue;"
            return f"{ind}continue;"

        elif rule == "expr_stmt":
            expr_code = self._translate_expr(node.children[0])
            return f"{ind}{expr_code};"

        return ""

    def _translate_while(self, node: Tree, append_ctx=None) -> str:
        """Translates a while loop; ``append_ctx`` collects the body value."""
        ind = self.indent()
        cond_node = node.children[0]
        block_node = node.children[1]
        cond_str = self._translate_expr(cond_node)

        self.indent_level += 1
        body_str = self._translate_loop_body(block_node, append_ctx)
        self.indent_level -= 1

        return f"{ind}while ({cond_str}) {{\n{body_str}\n{ind}}}"

    def _translate_loop_body(self, block_node: Tree, append_ctx=None) -> str:
        """Body C of a loop.

        With ``append_ctx`` = ``(list_tmp, elem_c, elem_t)`` the body's final
        statement is the iteration's *value*: it is pushed onto the collecting
        list instead of being emitted (so the push sits at the end of the body and
        ``continue`` naturally skips it while ``break`` ends the loop).
        """
        if append_ctx is None:
            return self._translate_nested_block_with_banish(block_node, "loop")
        list_tmp, elem_c, elem_t = append_ctx
        self._auto_banish_push("loop")
        try:
            stmts = [c for c in block_node.children if isinstance(c, Tree)]
            parts, val = self._value_branch(stmts, elem_t)
            if val is not None:
                ind = self.indent()
                tmp_val = self.get_temp_name("_lv")
                parts.append(f"{ind}{elem_c} {tmp_val} = {val};")
                parts.append(f"{ind}pengu_list_push(&{list_tmp}, &{tmp_val});")
            banish = self._flush_current_scope_banish()
            if banish:
                parts.extend(banish)
            return "\n".join(parts)
        finally:
            if self.auto_banish_stack and self.auto_banish_stack[-1][0] == "loop":
                self.auto_banish_stack.pop()

    def _translate_loop_value(self, node: Tree, expected_type: Optional[Type] = None) -> str:
        """GNU statement-expression for a loop used as a value.

        The loop collects its body's value on every iteration into a fresh list
        (``list of T``), e.g. ``for i from 0 to 3: i * 2`` yields three ints.
        """
        v_t = getattr(node, "_pengu_value_type", None) or expected_type
        elem_t = v_t.element if isinstance(v_t, ListType) else AnyType()
        elem_c = CTypeMapper.to_c_type(elem_t)
        list_tmp = self.get_temp_name("_loop_list")
        with_append = (list_tmp, elem_c, elem_t)
        if node.data == "while_stmt":
            loop_c = self._translate_while(node, with_append)
        elif node.data == "for_range_stmt":
            loop_c = self._translate_for_range(node, with_append)
        else:
            loop_c = self._translate_for_in(node, with_append)
        ind = self.indent()
        return (
            f"(__extension__({{\n"
            f"{ind}  PenguList {list_tmp} = pengu_list_new(sizeof({elem_c}), 8);\n"
            f"{loop_c}\n"
            f"{ind}  {list_tmp};\n"
            f"{ind}}}))"
        )

    def _translate_for_range(self, node: Tree, append_ctx=None) -> str:
        """Translates for i from start to end [step s] loop."""
        ind = self.indent()
        var_name = str(node.children[0])
        start_str = self._translate_expr(node.children[1])
        end_str = self._translate_expr(node.children[2])
        step_node = node.children[3] if len(node.children) > 3 and node.children[3] is not None else None
        step_str = self._translate_expr(step_node) if step_node is not None else "1"
        block_node = node.children[4] if len(node.children) > 4 and node.children[4] is not None else node.children[-1]

        self.local_vars[var_name] = INT_TYPE
        self.indent_level += 1
        body_str = self._translate_loop_body(block_node, append_ctx)
        self.indent_level -= 1
        if var_name in self.local_vars:
            del self.local_vars[var_name]

        step_c = f"{var_name}++" if step_str == "1" else f"{var_name} += {step_str}"
        return (
            f"{ind}for (int32_t {var_name} = {start_str}; "
            f"{var_name} < {end_str}; {step_c}) {{\n"
            f"{body_str}\n{ind}}}"
        )

    def _translate_for_in(self, node: Tree, append_ctx=None) -> str:
        """Translates for [i,] item in collection loop.

        Supports the classic single-binding form ('for v in col') and the
        indexed form ('for i, v in col', 'for i, _ in col', 'for _, v in col').
        When an index binding is requested its identifier becomes the C99 loop
        counter so 'i' is visible inside the body; '_' bindings are skipped.
        ``append_ctx`` collects the body's value per iteration (loop as value).
        """
        ind = self.indent()
        if len(node.children) == 4:
            index_name = str(node.children[0])
            elem_name = str(node.children[1])
            col_expr = node.children[2]
            block_node = node.children[3]
        else:
            index_name = None
            elem_name = str(node.children[0])
            col_expr = node.children[1]
            block_node = node.children[2]

        col_str = self._translate_expr(col_expr)
        want_index = index_name is not None and index_name != "_"
        want_elem = elem_name != "_"
        iter_idx = index_name if want_index else self.get_temp_name("_idx")

        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
        for lv_k, lv_v in self.local_vars.items():
            inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))

        col_t = None
        try:
            col_t = inferrer.infer(col_expr)
        except Exception:
            pass

        # Check if Range loop
        is_range = False
        start_str = None
        end_str = None
        if isinstance(col_expr, Tree) and col_expr.data in ("to_expr", "range_dotdot"):
            is_range = True
            start_str = self._translate_expr(col_expr.children[0])
            end_str = self._translate_expr(col_expr.children[-1])
        elif isinstance(col_t, RangeType):
            is_range = True

        if is_range:
            loop_var = elem_name if want_elem else self.get_temp_name("_rv")
            if want_elem:
                self.local_vars[elem_name] = INT_TYPE
            if want_index:
                self.local_vars[index_name] = INT_TYPE
            self.indent_level += 1
            body_str = self._translate_loop_body(block_node, append_ctx)
            self.indent_level -= 1
            if want_elem and elem_name in self.local_vars:
                del self.local_vars[elem_name]
            if want_index and index_name in self.local_vars:
                del self.local_vars[index_name]

            if start_str is not None and end_str is not None:
                if want_index:
                    return (
                        f"{ind}for (int64_t {loop_var} = {start_str}, {index_name} = 0; "
                        f"{loop_var} < {end_str}; {loop_var}++, {index_name}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )
                else:
                    return (
                        f"{ind}for (int64_t {loop_var} = {start_str}; "
                        f"{loop_var} < {end_str}; {loop_var}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )
            else:
                rng_tmp = self.get_temp_name("_rng")
                if want_index:
                    return (
                        f"{ind}PenguRange {rng_tmp} = {col_str};\n"
                        f"{ind}for (int64_t {loop_var} = {rng_tmp}.start, {index_name} = 0; "
                        f"{loop_var} < {rng_tmp}.end; {loop_var}++, {index_name}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )
                else:
                    return (
                        f"{ind}PenguRange {rng_tmp} = {col_str};\n"
                        f"{ind}for (int64_t {loop_var} = {rng_tmp}.start; "
                        f"{loop_var} < {rng_tmp}.end; {loop_var}++) {{\n"
                        f"{body_str}\n{ind}}}"
                    )

        elem_t = col_t.element_type() if col_t and hasattr(col_t, "element_type") and col_t.element_type() else INT_TYPE
        is_string_iter = isinstance(col_t, BaseType) and getattr(col_t, "name", "") == "string"
        if is_string_iter:
            elem_t = STRING_TYPE
        elem_c = CTypeMapper.to_c_type(elem_t)

        # An inline array literal ('for v in [1, 2]') has no storage of its own
        # (its C form is a brace initializer), so materialize it into a temporary
        # array the loop can index.
        lit_decl = ""
        if (isinstance(col_expr, Tree) and col_expr.data == "array_lit"
                and isinstance(col_t, ArrayType) and col_expr.children):
            lit_tmp = self.get_temp_name("_lit")
            elems = ", ".join(self._translate_expr(c) for c in col_expr.children)
            lit_decl = f"{ind}{elem_c} {lit_tmp}[] = {{ {elems} }};\n"
            col_str = lit_tmp
            col_t = ArrayType(element=col_t.element, size=len(col_expr.children))

        if want_index:
            self.local_vars[index_name] = INT_TYPE
        if want_elem:
            self.local_vars[elem_name] = elem_t
        self.indent_level += 1
        body_str = self._translate_loop_body(block_node, append_ctx)
        self.indent_level -= 1
        if want_index and index_name in self.local_vars:
            del self.local_vars[index_name]
        if want_elem and elem_name in self.local_vars:
            del self.local_vars[elem_name]

        elem_decl = f"{ind}  {elem_c} {elem_name} = " if want_elem else f"{ind}  /* discard element */ "
        if isinstance(col_t, ArrayType) and col_t.size is not None:
            if want_elem:
                body_prefix = f"{elem_decl}({col_str})[{iter_idx}];\n"
            else:
                body_prefix = f"{ind}  (void)({col_str})[{iter_idx}];\n"
            return (
                f"{lit_decl}"
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < {col_t.size}; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )
        elif isinstance(col_t, (SliceType, ManyType)):
            if want_elem:
                body_prefix = f"{elem_decl}((({elem_c}*)({col_str}).data)[{iter_idx}]);\n"
            else:
                body_prefix = f"{ind}  (void)((({elem_c}*)({col_str}).data)[{iter_idx}]);\n"
            return (
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < ({col_str}).len; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )
        elif isinstance(col_t, ListType):
            if want_elem:
                body_prefix = f"{elem_decl}(*({elem_c}*)pengu_list_at(&({col_str}), {iter_idx}));\n"
            else:
                body_prefix = f"{ind}  (void)(*({elem_c}*)pengu_list_at(&({col_str}), {iter_idx}));\n"
            return (
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < ({col_str}).len; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )
        elif is_string_iter:
            # Iterating a PenguScript string yields each character as a
            # single-character PenguString (allocated via the char_at primitive).
            if want_elem:
                body_prefix = f"{elem_decl}pengu_string_char_at({col_str}, {iter_idx});\n"
            else:
                body_prefix = f"{ind}  (void)pengu_string_char_at({col_str}, {iter_idx});\n"
            return (
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < ({col_str}).len; {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )
        else:
            if want_elem:
                body_prefix = f"{elem_decl}({col_str})[{iter_idx}];\n"
            else:
                body_prefix = f"{ind}  (void)({col_str})[{iter_idx}];\n"
            return (
                f"{ind}for (int32_t {iter_idx} = 0; {iter_idx} < (int32_t)(sizeof({col_str})/sizeof(({col_str})[0])); {iter_idx}++) {{\n"
                f"{body_prefix}"
                f"{body_str}\n{ind}}}"
            )

    def _translate_nested_block(self, node: Tree) -> str:
        """Translates a block node."""
        if not isinstance(node, Tree):
            return ""
        if node.data == "block":
            if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "simple_stmt":
                return self._translate_stmt(node.children[0])
            return self._translate_block(node.children)
        return self._translate_stmt(node)

    def _translate_else_block(self, node: Tree) -> str:
        """Translates an else block or else if statement."""
        if isinstance(node, Tree) and node.data == "else_block":
            if len(node.children) == 1 and isinstance(node.children[0], Tree) and node.children[0].data == "if_stmt":
                return self._translate_stmt(node.children[0])
            self._auto_banish_push("block")
            try:
                body = self._translate_block(node.children)
                if not self._stmts_end_with_jump(node.children):
                    banish = self._flush_current_scope_banish()
                    if banish:
                        body = (body + "\n" if body else "") + "\n".join(banish)
                return body
            finally:
                if self.auto_banish_stack and self.auto_banish_stack[-1][0] == "block":
                    self.auto_banish_stack.pop()
        elif isinstance(node, Tree) and node.data == "if_stmt":
            return self._translate_stmt(node)
        return ""

    def _value_branch(self, stmts: List[Tree], expected_type: Optional[Type] = None):
        """C code and value expression of a value-position statement list.

        Returns ``(statement_parts, value_expr)``. The last statement supplies
        the block value: an expression statement, a trailing value-position
        ``if``/``unless`` or a collecting loop, or nothing for a void branch.
        """
        parts: List[str] = []
        val: Optional[str] = None
        n = len(stmts)
        for i, st in enumerate(stmts):
            inner = st
            while isinstance(inner, Tree) and inner.data == "stmt" and inner.children:
                inner = inner.children[0]
            if i == n - 1 and isinstance(inner, Tree):
                inner_vt = getattr(inner, "_pengu_value_type", None)
                if (inner.data in ("if_stmt", "unless_stmt") and inner_vt is not None):
                    val = self._translate_expr(inner, expected_type)
                    continue
                if inner.data in ("while_stmt", "for_range_stmt", "for_in_stmt") and isinstance(inner_vt, ListType):
                    val = self._translate_expr(inner, expected_type)
                    continue
                if inner.data == "expr_stmt" and inner.children:
                    val = self._translate_expr(inner.children[0], expected_type)
                    continue
                if (inner.data == "simple_stmt" and len(inner.children) == 1
                        and isinstance(inner.children[0], (Tree, Token))):
                    val = self._translate_expr(inner.children[0], expected_type)
                    continue
            code = self._translate_stmt(st)
            if code:
                parts.append(code.rstrip())
        return parts, val

    def _translate_value_if(self, node: Tree, expected_type: Optional[Type] = None,
                            negate: bool = False,
                            cond_c: Optional[str] = None,
                            then_prologue: Optional[str] = None) -> str:
        """GNU statement-expression for an 'if'/'unless' used as a value.

        Every branch's last statement supplies the branch value; a trailing
        value-position 'if'/'unless' nests recursively, so both
        ``else if <cond>:`` and an ``else:`` block containing a nested block
        work. ``negate`` renders the condition as ``unless`` semantics.
        ``cond_c`` overrides the rendered condition and ``then_prologue`` is
        emitted at the top of the then-branch (used to declare a bound name).
        """
        if cond_c is None:
            cond_c = self._translate_if_cond(node.children[0])
        if negate:
            cond_c = f"!({cond_c})"
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None
        v_t = getattr(node, "_pengu_value_type", None) or expected_type

        saved_vars = set(self.local_vars)
        try:
            then_parts, then_val = self._value_branch(list(block_node.children), v_t)
            if then_prologue:
                then_parts.insert(0, f"  {then_prologue}")
            then_body = "\n".join(then_parts)

            else_parts: List[str] = []
            else_val: Optional[str] = None
            nested_else: Optional[str] = None
            if isinstance(else_node, Tree) and else_node.children:
                ech = [c for c in else_node.children if isinstance(c, Tree)]
                if len(ech) == 1 and ech[0].data in ("if_stmt", "unless_stmt"):
                    # 'else if <cond>:' — nested value block.
                    nested_else = self._translate_expr(ech[0], v_t)
                else:
                    else_parts, else_val = self._value_branch(ech, v_t)
            else_body = "\n".join(else_parts)

            is_void = v_t is None or str(getattr(v_t, "name", "")) == "void"
            if is_void:
                # Side effects only: any branch value is evaluated and dropped.
                then_full = "\n".join(
                    p for p in (then_body, f"{then_val};" if then_val else "") if p
                )
                res = f"(__extension__(({{ if ({cond_c}) {{\n{then_full}\n}}"
                if nested_else is not None:
                    res += f" else {{\n{nested_else};\n}}"
                elif else_body or else_val:
                    else_full = "\n".join(
                        p for p in (else_body, f"{else_val};" if else_val else "") if p
                    )
                    res += f" else {{\n{else_full}\n}}"
                res += "\n})))"
                return res

            c_t = CTypeMapper.to_c_type(v_t)
            tmp = self.get_temp_name("_if")
            res = (
                f"(__extension__(({{ {c_t} {tmp}; if ({cond_c}) {{\n{then_body}\n"
                + (f"  {tmp} = {then_val};\n" if then_val else "")
                + "}"
            )
            if nested_else is not None:
                res += f" else {{\n  {tmp} = {nested_else};\n}}"
            elif else_body or else_val:
                res += (
                    f" else {{\n{else_body}\n"
                    + (f"  {tmp} = {else_val};\n" if else_val else "")
                    + "}"
                )
            else:
                res += f" else {{ {tmp} = ({c_t}){{0}}; }}"
            res += f" {tmp}; }})))"
            return res
        finally:
            for name in list(self.local_vars):
                if name not in saved_vars:
                    self.local_vars.pop(name, None)

    def _translate_set_target(self, node: Any) -> str:
        """Translates the left-hand side target of a set statement."""
        if not isinstance(node, Tree):
            name = str(node)
            sym = self.symbols.lookup(name) if self.symbols else None
            if self.with_stack and (not sym or sym.kind == "field"):
                base_target = self.with_stack[-1]
                base_type = self._lookup_var_type(base_target)
                sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                return f"{base_target}{sep}{name}"
            return name

        if node.data == "set_target":
            return self._translate_set_target(node.children[0])

        if node.data == "with_target":
            field_name = str(node.children[0])
            base_target = self.with_stack[-1] if self.with_stack else "self"
            base_type = self._lookup_var_type(base_target)
            sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
            target_str = f"{base_target}{sep}{field_name}"
            for acc in node.children[1:]:
                target_str = self._translate_access_op(target_str, acc)
            return target_str

        elif node.data == "normal_target":
            base_name = str(node.children[0])
            sym = self.symbols.lookup(base_name) if self.symbols else None
            if self.with_stack and (not sym or sym.kind == "field"):
                base_target = self.with_stack[-1]
                base_type = self._lookup_var_type(base_target)
                sep = "->" if (base_target == "self" or isinstance(base_type, RefType)) else "."
                target_str = f"{base_target}{sep}{base_name}"
            else:
                target_str = base_name
            for acc in node.children[1:]:
                target_str = self._translate_access_op(target_str, acc)
            return target_str

        elif node.data == "essence_target":
            inner_str = self._translate_expr(node.children[0])
            return f"(*{inner_str})"

        return str(node)


    def _translate_access_op(self, base_str: str, acc_node: Tree) -> str:
        """Translates member and index access operators."""
        if acc_node.data == "dot_access":
            var_t = self._lookup_var_type(base_str)
            sep = "->" if (base_str == "self" or isinstance(var_t, RefType)) else "."
            return f"{base_str}{sep}{acc_node.children[0]}"
        elif acc_node.data == "arrow_access":
            return f"{base_str}->{acc_node.children[0]}"
        elif acc_node.data == "at_access":
            idx = self._translate_expr(acc_node.children[0])
            var_t = self._lookup_var_type(base_str)
            idx = self._emit_bounds_check(idx, base_str, var_t, acc_node.children[0])
            if isinstance(var_t, (SliceType, ManyType)):
                elem_t = CTypeMapper.to_c_type(var_t.element)
                return f"((({elem_t}*)({base_str}).data)[{idx}])"
            elif isinstance(var_t, ListType):
                elem_t = CTypeMapper.to_c_type(var_t.element)
                return f"(*({elem_t}*)pengu_list_at(&({base_str}), {idx}))"
            return f"{base_str}[{idx}]"
        return base_str

    def _translate_if_cond(self, node: Any) -> str:
        """Translates a branch condition.

        Binding patterns (``if name as T is <maybe>:``) are not conditions on
        their own — they need a scope for the bound name and are handled by
        :meth:`_translate_binding_if` / :meth:`_translate_binding_value_if`.
        """
        return self._translate_expr(node)

    def _binding_cond(self, node: Any) -> Optional[tuple]:
        """Returns the parts of a binding condition, or None.

        The tuple is ``(bind_name, decl_c, elem_c, expr_c, maybe_c, bind_type)``:
        the bound name, its C type, the C type used to cast the unwrapped value,
        the translated maybe expression, the C type of the maybe value and the
        declared :class:`Type`.
        """
        if not (isinstance(node, Tree)
                and node.data in ("if_cond_binding", "if_cond_binding_present")):
            return None

        bind_name = str(node.children[0])
        bind_type = ast_to_type(
            node.children[1],
            lambda n: self.symbols.lookup(n).type if self.symbols.lookup(n) else None,
        )
        expr_node = getattr(node, "_pengu_bind_source", None) or node.children[2]
        if isinstance(expr_node, Tree) and expr_node.data == "is_present" and expr_node.children:
            # Redundant presence test: the binding implies it.
            expr_node = expr_node.children[0]
        elem_t = getattr(node, "_pengu_bind_elem_type", None) or bind_type
        maybe_t = getattr(node, "_pengu_bind_maybe_type", None) or MaybeType(element=elem_t)
        return (
            bind_name,
            CTypeMapper.to_c_type(bind_type),
            CTypeMapper.to_c_type(elem_t),
            self._translate_expr(expr_node),
            CTypeMapper.to_c_type(maybe_t),
            bind_type,
        )

    def _translate_binding_if(self, node: Tree, binding: tuple) -> str:
        """Emits ``if name as T is <maybe>:`` as a scoped C block.

        The maybe value is evaluated once into a temporary; the branch body runs
        only when the value is present, and the bound name is declared inside it::

            {
                PenguMaybe _maybe_1 = (expr);
                if (pengu_maybe_is_present(&_maybe_1)) {
                    T name = (*(T*)_maybe_1.value);
                    <body>
                } else { <else> }
            }
        """
        bind_name, decl_c, elem_c, expr_c, maybe_c, bind_type = binding
        block_node = node.children[1]
        else_node = node.children[2] if len(node.children) > 2 else None

        ind = self.indent()
        inner = ind + "  "
        inner2 = inner + "  "
        tmp = self.get_temp_name("_maybe")

        prev_type = self.local_vars.get(bind_name)
        self.local_vars[bind_name] = bind_type
        self.indent_level += 2
        try:
            body_str = self._translate_nested_block(block_node)
            else_str = None
            if else_node is not None:
                else_str = self._translate_else_block(else_node)
        finally:
            self.indent_level -= 2
            if prev_type is None:
                self.local_vars.pop(bind_name, None)
            else:
                self.local_vars[bind_name] = prev_type

        parts = [
            f"{ind}{{",
            f"{inner}{maybe_c} {tmp} = {expr_c};",
            f"{inner}if (pengu_maybe_is_present(&{tmp})) {{",
            f"{inner2}{decl_c} {bind_name} = (*({elem_c}*){tmp}.value);",
        ]
        if body_str:
            parts.append(body_str)
        parts.append(f"{inner}}}")
        if else_str is not None:
            parts.append(f"{inner}else {{")
            if else_str:
                parts.append(else_str)
            parts.append(f"{inner}}}")
        parts.append(f"{ind}}}")
        return "\n".join(parts)

    def _translate_binding_value_if(self, node: Tree, binding: tuple,
                                    expected_type: Optional[Type] = None) -> str:
        """Value-position ``if`` with a binding condition.

        The maybe value is evaluated once in the enclosing statement-expression,
        the branch body declares the bound name and the inner value-``if`` is
        guarded by the presence test::

            (__extension__(({
                PenguMaybe _maybe_1 = (expr);
                (__extension__(({ T _if_1; if (pengu_maybe_is_present(&_maybe_1)) {
                    T name = (*(T*)_maybe_1.value); ... _if_1 = <then>; } ...
                } _if_1; })));
            })))
        """
        bind_name, decl_c, elem_c, expr_c, maybe_c, bind_type = binding
        tmp = self.get_temp_name("_maybe")

        prev_type = self.local_vars.get(bind_name)
        self.local_vars[bind_name] = bind_type
        try:
            inner = self._translate_value_if(
                node,
                expected_type,
                cond_c=f"pengu_maybe_is_present(&{tmp})",
                then_prologue=f"{decl_c} {bind_name} = (*({elem_c}*){tmp}.value);",
            )
        finally:
            if prev_type is None:
                self.local_vars.pop(bind_name, None)
            else:
                self.local_vars[bind_name] = prev_type

        return f"(__extension__(({{ {maybe_c} {tmp} = {expr_c}; {inner}; }})))"

    def _translate_string_lit(self, s_val: str, as_c_literal: bool = False) -> str:
        """Translates string literal, generating pengu_string_format call for interpolated expressions or C string literal."""
        from .pengu_parser import extract_string_parts, PenguParser
        is_raw, is_triple, parts = extract_string_parts(s_val)

        def _escape_c(text: str, is_raw_lit: bool) -> str:
            if is_raw_lit:
                res = []
                for ch in text:
                    if ch == '\\':
                        res.append('\\\\')
                    elif ch == '"':
                        res.append('\\"')
                    elif ch == '\n':
                        res.append('\\n')
                    elif ch == '\r':
                        res.append('\\r')
                    elif ch == '\t':
                        res.append('\\t')
                    else:
                        res.append(ch)
                return "".join(res)
            else:
                res = []
                i = 0
                n = len(text)
                while i < n:
                    ch = text[i]
                    if ch == '\\' and i + 1 < n:
                        res.append(ch)
                        res.append(text[i + 1])
                        i += 2
                        continue
                    if ch == '"':
                        res.append('\\"')
                    elif ch == '\n':
                        res.append('\\n')
                    elif ch == '\r':
                        res.append('\\r')
                    else:
                        res.append(ch)
                    i += 1
                return "".join(res)

        has_expr = any(p.is_expr for p in parts)
        if as_c_literal:
            if has_expr:
                raise SemanticError("String interpolation is not supported when expecting a C string literal (ref to char)")
            full_lit = "".join(_escape_c(p.text, is_raw) for p in parts)
            return f'"{full_lit}"'

        if not has_expr:
            full_lit = "".join(_escape_c(p.text, is_raw) for p in parts)
            return f'pengu_string_from_cstr("{full_lit}")'

        parser = PenguParser()
        fmt_parts = []
        c_args = []
        for p in parts:
            if not p.is_expr:
                fmt_parts.append(_escape_c(p.text, is_raw).replace("%", "%%"))
            else:
                expr_str = p.text.strip()
                try:
                    expr_ast = parser.parse_expr(expr_str)
                except Exception:
                    expr_ast = None

                t = None
                expr_c = expr_str
                if expr_ast is not None:
                    try:
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_name, lv_t in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_name, type=lv_t, kind="var"))
                        t = inferrer.infer(expr_ast)
                    except Exception:
                        pass
                    try:
                        expr_c = self._translate_expr(expr_ast)
                    except Exception:
                        expr_c = expr_str

                if t is not None:
                    if t.is_int():
                        fmt_parts.append("%d")
                        c_args.append(f"(int32_t)({expr_c})")
                    elif t.is_float():
                        fmt_parts.append("%f")
                        c_args.append(f"(double)({expr_c})")
                    elif isinstance(t, BaseType) and t.name == "bool":
                        fmt_parts.append("%s")
                        c_args.append(f"(({expr_c}) ? \"true\" : \"false\")")
                    elif isinstance(t, BaseType) and t.name == "string":
                        fmt_parts.append("%s")
                        c_args.append(f"({expr_c}).data")
                    elif isinstance(t, BaseType) and t.name in ("char", "byte"):
                        fmt_parts.append("%c")
                        c_args.append(f"(char)({expr_c})")
                    else:
                        fmt_parts.append("%s")
                        c_args.append(f"({expr_c}).data")
                else:
                    fmt_parts.append("%s")
                    c_args.append(f"({expr_c}).data" if not expr_str.isdigit() else expr_c)

        full_fmt = "".join(fmt_parts)
        return f'pengu_string_format("{full_fmt}", {", ".join(c_args)})'

    def _is_string_expr(self, n: Any) -> bool:
        """Checks if an AST expression node evaluates to a PenguString."""
        if n is None:
            return False
        if isinstance(n, Token):
            return n.type in ("STRING", "TRIPLE_STRING", "RAW_STRING", "RAW_TRIPLE_STRING")
        if isinstance(n, Tree):
            rule = n.data
            if rule in ("string_lit", "interpolated_string"):
                return True
            if rule == "var_ref":
                vt = self._lookup_var_type(str(n.children[0]))
                return vt is not None and getattr(vt, "name", "") == "string"
            if rule == "self_arrow":
                field_name = str(n.children[0])
                if self.current_enchanted_type and isinstance(self.current_enchanted_type, (RuneType, EchoType)):
                    ft = self.current_enchanted_type.fields.get(field_name)
                    return ft is not None and getattr(ft, "name", "") == "string"
                return False
            if rule == "field_access":
                target_node = n.children[0]
                field_name = str(n.children[1])
                target_type = None
                if isinstance(target_node, Tree) and target_node.data == "var_ref":
                    target_type = self._lookup_var_type(str(target_node.children[0]))
                elif isinstance(target_node, Tree) and target_node.data == "self_ref":
                    target_type = self.current_enchanted_type
                if target_type and isinstance(target_type, (RuneType, EchoType)):
                    ft = target_type.fields.get(field_name)
                    return ft is not None and getattr(ft, "name", "") == "string"
                return False
            if rule == "cast_expr":
                t = ast_to_type(n.children[1], lambda name: self.symbols.lookup(name).type if self.symbols and self.symbols.lookup(name) else None)
                return t is not None and getattr(t, "name", "") == "string"
            if rule == "add":
                return self._is_string_expr(n.children[0]) or self._is_string_expr(n.children[1])
            if rule == "calling_expr":
                fn_node = n.children[0]
                fn_name = ""
                if isinstance(fn_node, Token):
                    fn_name = str(fn_node)
                elif isinstance(fn_node, Tree):
                    if fn_node.data == "var_ref":
                        fn_name = str(fn_node.children[0])
                    elif fn_node.data == "field_access":
                        obj_node = fn_node.children[0]
                        m_name = str(fn_node.children[1])
                        if isinstance(obj_node, Tree) and obj_node.data == "var_ref":
                            obj_type = self._lookup_var_type(str(obj_node.children[0]))
                            if obj_type and hasattr(obj_type, "name"):
                                fn_name = f"{obj_type.name}_{m_name}"
                        elif isinstance(obj_node, Tree) and obj_node.data == "self_ref":
                            if self.current_enchanted_type and hasattr(self.current_enchanted_type, "name"):
                                fn_name = f"{self.current_enchanted_type.name}_{m_name}"
                if fn_name:
                    sym = self.symbols.lookup(fn_name) if self.symbols else None
                    if sym and isinstance(sym.type, FnType) and sym.type.return_type:
                        return getattr(sym.type.return_type, "name", "") == "string"
                    if fn_name in self.fn_info:
                        ret_t = self.fn_info[fn_name].get("return_type")
                        return ret_t is not None and getattr(ret_t, "name", "") == "string"
            if rule == "if_expr":
                return self._is_string_expr(n.children[1]) or self._is_string_expr(n.children[2])

            try:
                inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                inferred_t = inferrer.infer(n)
                if inferred_t is not None and getattr(inferred_t, "name", "") == "string":
                    return True
            except Exception:
                pass
        return False

    def _translate_unwrap_expr(self, rule: str, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates 'try', 'or else' and 'or return' unwrapping expressions.

        The grammar accepts these operators on any expression, but they only
        make sense on a ``maybe T`` or ``result of T to E`` operand. Type
        checking already guarantees the operand type (and, for 'try', that the
        enclosing function returns a compatible maybe/result container); this
        method emits the C unwrap using a GNU statement-expression so the
        success value is produced lazily and the failure path can ``return``
        from the enclosing function.
        """
        left_node = node.children[0]
        left_c = self._translate_expr(left_node)
        left_t = self._infer_node_type(left_node)

        if isinstance(left_t, MaybeType):
            container_c = "PenguMaybe"
            ok_c = CTypeMapper.to_c_type(left_t.element)
        elif isinstance(left_t, ResultType):
            container_c = "PenguResult"
            ok_c = CTypeMapper.to_c_type(left_t.ok_type)
        else:
            got = str(left_t) if left_t is not None else "unknown"
            raise SemanticError(
                f"'{rule}' requires a maybe T or result of T to E operand, got '{got}'",
                code="E0005",
            )
        tmp = self.get_temp_name("_unwrap")

        if rule == "or_else":
            right_node = node.children[1]
            right_c = self._translate_expr(right_node)
            if isinstance(left_t, MaybeType):
                is_ok = f"pengu_maybe_is_present(&{tmp})"
                ok_read = f"(*(({ok_c}*){tmp}.value))"
            else:
                is_ok = f"pengu_result_is_ok(&{tmp})"
                ok_read = f"(*(({ok_c}*){tmp}.ok_val))"
            return (
                f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
                f"({is_ok}) ? ({ok_read}) : (({ok_c})({right_c})); }})))"
            )

        if isinstance(left_t, ResultType):
            is_fail = f"!pengu_result_is_ok(&{tmp})"
            ok_read = f"(*(({ok_c}*){tmp}.ok_val))"
        else:
            is_fail = f"!pengu_maybe_is_present(&{tmp})"
            ok_read = f"(*(({ok_c}*){tmp}.value))"

        if rule == "or_return":
            right_c = self._translate_expr(node.children[1],
                                           expected_type=self.current_return_type)
            return (
                f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
                f"if ({is_fail}) {{ pengu_frame_pop(); return ({right_c}); }} {ok_read}; }})))"
            )

        # rule == "try_expr": on failure propagate to the enclosing function.
        fn_ret = self.current_return_type
        if isinstance(left_t, ResultType):
            err_ok = isinstance(fn_ret, AnyType) or (
                isinstance(fn_ret, ResultType)
                and left_t.err_type.is_compatible(fn_ret.err_type))
            if not err_ok:
                raise SemanticError(
                    f"'try' over 'result of T to E' requires the enclosing "
                    f"function to return a compatible result type (error type "
                    f"'{left_t.err_type}'), not "
                    f"'{fn_ret if fn_ret is not None else 'void'}'",
                    code="E0045",
                )
            fail_stmt = f"{{ pengu_frame_pop(); return {tmp}; }}"
        else:
            if not isinstance(fn_ret, (MaybeType, AnyType)):
                raise SemanticError(
                    f"'try' over 'maybe T' requires the enclosing function to "
                    f"return 'maybe T', not "
                    f"'{fn_ret if fn_ret is not None else 'void'}'",
                    code="E0045",
                )
            fail_stmt = "{ pengu_frame_pop(); return pengu_maybe_none(); }"
        return (
            f"(__extension__(({{ {container_c} {tmp} = {left_c}; "
            f"if ({is_fail}) {fail_stmt} {ok_read}; }})))"
        )

    def _translate_expr(self, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates an expression node, tracking that we are in expression context.

        Expression context suppresses `#line` markers: a statement-expression
        built here can end up as the argument of a function-like macro
        (`pengu_to_string(x)`), where a preprocessor directive would break the
        macro invocation.
        """
        self._expr_depth += 1
        try:
            return self._translate_expr_impl(node, expected_type)
        finally:
            self._expr_depth -= 1

    def _translate_banish_target(self, target_expr: Any) -> str:
        """Translates banish target into appropriate runtime free call according to type."""
        target_str = self._translate_expr(target_expr)
        t = self._infer_node_type(target_expr)
        if t is None:
            if isinstance(target_expr, Tree) and target_expr.data == "var_ref":
                t = self._lookup_var_type(str(target_expr.children[0]))
            elif isinstance(target_expr, Token):
                t = self._lookup_var_type(str(target_expr))

        actual_t = t.target if (isinstance(t, FrozenType)) else t
        is_str = isinstance(actual_t, BaseType) and actual_t.name == "string"
        is_lst = isinstance(actual_t, ListType)
        is_map = isinstance(actual_t, MapType)

        ptr = target_str if (target_str.startswith("&") or isinstance(actual_t, RefType)) else (f"&{target_str}" if target_str.isidentifier() else f"&({target_str})")

        if is_str:
            return f"pengu_banish_string({ptr})"
        elif is_lst:
            return f"pengu_banish_list({ptr})"
        elif is_map:
            return f"pengu_banish_map({ptr})"
        return f"pengu_banish((void*)({target_str}))"

    def _translate_expr_impl(self, node: Any, expected_type: Optional[Type] = None) -> str:
        """Translates expression node into C99 expression string."""
        if node is None:
            return ""

        if isinstance(node, Token):
            val = str(node)
            if node.type == "INT":
                return val
            elif node.type == "FLOAT":
                return val
            elif node.type == "CHAR_LIT":
                return val
            elif node.type in ("STRING", "TRIPLE_STRING", "RAW_STRING", "RAW_TRIPLE_STRING"):
                is_c_str = self._is_ref_char_type(expected_type)
                return self._translate_string_lit(val, as_c_literal=is_c_str)
            elif node.type == "NAME":
                for o_name, o_variants in self.omens.items():
                    if val.startswith(f"{o_name}_") and val[len(o_name) + 1:] in o_variants:
                        return val
                    if val in o_variants:
                        return self._get_omen_variant_c_name(o_name, val)
                return val
            return val

        if not isinstance(node, Tree):
            return str(node)

        # Check const folding for entire expression
        if node.data not in ("string_lit", "interpolated_string"):
            folded = self.const_folder.fold(node)
            if folded is not None and not (isinstance(folded, str) and node.data == "add"):
                return self._format_const_val(folded, expected_type=expected_type)

        rule = node.data

        # 1. Literals
        if rule == "int_lit":
            return str(node.children[0])
        elif rule == "float_lit":
            return str(node.children[0])
        elif rule == "char_lit":
            return str(node.children[0])
        elif rule == "string_lit":
            is_c_str = self._is_ref_char_type(expected_type)
            raw_s = str(node.children[0]) if node.children else ""
            return self._translate_string_lit(raw_s, as_c_literal=is_c_str)
        elif rule == "true_lit":
            return "true"
        elif rule == "false_lit":
            return "false"
        elif rule == "null_lit":
            return "NULL"
        elif rule == "maybe_none":
            return "pengu_maybe_none()"
        elif rule == "error_lit":
            return "error"
        elif rule in ("try_expr", "or_else", "or_return"):
            return self._translate_unwrap_expr(rule, node, expected_type)
        elif rule == "var_ref":
            name = str(node.children[0])
            sym = self.symbols.lookup(name) if self.symbols else None
            if sym and hasattr(sym, "const_val") and sym.const_val is not None:
                return self._format_const_val(sym.const_val, expected_type=expected_type)
            if name in self.consts and self.consts[name][1] is not None:
                return self._format_const_val(self.consts[name][1], expected_type=expected_type)
            for o_name, o_variants in self.omens.items():
                if name.startswith(f"{o_name}_") and name[len(o_name) + 1:] in o_variants:
                    return name
                if name in o_variants:
                    return self._get_omen_variant_c_name(o_name, name)
            # Inside a 'with:' scope, a bare name means a field of the target —
            # unless it is a known local (function/loop/block local), which must
            # stay a plain identifier (e.g. a loop variable used in a builder).
            if self.with_stack and (not sym or sym.kind == "field") and name not in self.local_vars:
                base_target = self.with_stack[-1]
                sep = "->" if base_target == "self" else "."
                return f"{base_target}{sep}{name}"
            code = self._c_ident(name)
            is_fn_symbol = (
                getattr(sym, "kind", "") in ("declare", "weave", "function")
                or name in self.fn_info
            )
            if is_fn_symbol:
                # A weave used as a value (callback argument, assignment).
                return self._cast_fn_value(code, expected_type)
            return code

        elif rule == "self_ref":
            return "self"


        elif rule == "bool_and":
            return (f"({self._translate_expr(node.children[0])} && "
                    f"{self._translate_expr(node.children[1])})")
        elif rule == "bool_or":
            return (f"({self._translate_expr(node.children[0])} || "
                    f"{self._translate_expr(node.children[1])})")

        # 2. Binary Arithmetic and Logic
        elif rule == "add":
            left_node, right_node = node.children[0], node.children[1]
            left = self._translate_expr(left_node)
            right = self._translate_expr(right_node)
            if self._is_string_expr(left_node) or self._is_string_expr(right_node):
                left_str = left if self._is_string_expr(left_node) else f"pengu_to_string({left})"
                right_str = right if self._is_string_expr(right_node) else f"pengu_to_string({right})"
                return f"pengu_string_concat({left_str}, {right_str})"
            return f"({left} + {right})"

        elif rule in ("eq", "ne"):
            left_node, right_node = node.children[0], node.children[1]
            left = self._translate_expr(left_node)
            right = self._translate_expr(right_node)
            if self._is_string_expr(left_node) or self._is_string_expr(right_node):
                left_str = left if self._is_string_expr(left_node) else f"pengu_to_string({left})"
                right_str = right if self._is_string_expr(right_node) else f"pengu_to_string({right})"
                if rule == "eq":
                    return f"pengu_string_equal({left_str}, {right_str})"
                else:
                    return f"(!pengu_string_equal({left_str}, {right_str}))"
            op = "==" if rule == "eq" else "!="
            return f"({left} {op} {right})"

        elif rule in ("sub", "mul", "div", "mod", "shl", "shr", "bitwise_and", "bitwise_or", "bitwise_xor",
                      "lt", "le", "gt", "ge"):
            op_map = {
                "sub": "-", "mul": "*", "div": "/", "mod": "%",
                "shl": "<<", "shr": ">>", "bitwise_and": "&", "bitwise_or": "|", "bitwise_xor": "^",
                "lt": "<", "le": "<=", "gt": ">", "ge": ">=",
            }
            left = self._translate_expr(node.children[0])
            right = self._translate_expr(node.children[1])
            return f"({left} {op_map[rule]} {right})"

        elif rule in ("in_expr", "not_in_expr"):
            elem_node = node.children[0]
            col_node = node.children[1]

            col_t = self._infer_node_type(col_node)
            elem_t = self._infer_node_type(elem_node)

            elem_c = self._translate_expr(elem_node)
            col_c = self._translate_expr(col_node)

            is_not = (rule == "not_in_expr")

            # Check if Range
            if isinstance(col_t, RangeType) or (isinstance(col_node, Tree) and col_node.data in ("to_expr", "range_dotdot")):
                if is_not:
                    return f"(__extension__({{ __auto_type _v = ({elem_c}); PenguRange _r = ({col_c}); (_v < _r.start || _v >= _r.end); }}))"
                else:
                    return f"(__extension__({{ __auto_type _v = ({elem_c}); PenguRange _r = ({col_c}); (_v >= _r.start && _v < _r.end); }}))"

            # Check if String
            if (isinstance(col_t, BaseType) and col_t.name == "string") or self._expr_is_string(col_node):
                if (isinstance(elem_t, BaseType) and elem_t.name == "char") or (isinstance(elem_node, Token) and elem_node.type == "CHAR_LIT"):
                    if is_not:
                        return f"(strchr(({col_c}).data, ({elem_c})) == NULL)"
                    return f"(strchr(({col_c}).data, ({elem_c})) != NULL)"
                else:
                    if is_not:
                        return f"(strstr(({col_c}).data, ({elem_c}).data) == NULL)"
                    return f"(strstr(({col_c}).data, ({elem_c}).data) != NULL)"

            # Check if Map
            if isinstance(col_t, MapType):
                k_tmp = self.get_temp_name("_mk")
                k_type_str = CTypeMapper.to_c_type(col_t.key)
                check_str = f"pengu_map_get(&_mc, &{k_tmp}) != NULL" if not is_not else f"pengu_map_get(&_mc, &{k_tmp}) == NULL"
                return f"(__extension__({{ PenguMap _mc = ({col_c}); {k_type_str} {k_tmp} = ({elem_c}); {check_str}; }}))"

            # Check if Array
            if isinstance(col_t, ArrayType) and col_t.size is not None:
                check_code = (
                    f"bool _f = false; "
                    f"for (size_t _i = 0; _i < {col_t.size}; ++_i) {{ "
                    f"  if ((_arr)[_i] == _val) {{ _f = true; break; }} "
                    f"}} "
                    f"{'!_f' if is_not else '_f'};"
                )
                return f"(__extension__({{ __auto_type _val = ({elem_c}); __auto_type _arr = ({col_c}); {check_code} }}))"

            # Fallback
            if is_not:
                return f"(!({elem_c} == {col_c}))"
            return f"({elem_c} == {col_c})"

        # 3. Unary
        elif rule == "neg":
            return f"(-{self._translate_expr(node.children[0])})"
        elif rule == "log_not":
            return f"(!{self._translate_expr(node.children[0])})"
        elif rule == "bit_not":
            return f"(~{self._translate_expr(node.children[0])})"
        elif rule == "sigil_of":
            return f"(&{self._translate_expr(node.children[0])})"
        elif rule == "essence_of":
            child = node.children[0]
            if isinstance(child, Tree) and child.data == "length_expr":
                return self._translate_expr(child)
            return f"(*{self._translate_expr(node.children[0])})"
        elif rule == "transmute":
            expr_str = self._translate_expr(node.children[0])
            def lookup_tp_trans(n):
                if hasattr(self, "current_subst_map") and self.current_subst_map and n in self.current_subst_map:
                    return self.current_subst_map[n]
                sym = self.symbols.lookup(n) if self.symbols else None
                return sym.type if sym else None
            t = ast_to_type(node.children[1], lookup_tp_trans)
            if hasattr(self, "current_subst_map") and self.current_subst_map:
                t = t.substitute(self.current_subst_map)
            t_str = CTypeMapper.to_c_type(t)
            return f"(({t_str})({expr_str}))"
        elif rule == "size_of":
            def lookup_tp_size(n):
                if hasattr(self, "current_subst_map") and self.current_subst_map and n in self.current_subst_map:
                    return self.current_subst_map[n]
                sym = self.symbols.lookup(n) if self.symbols else None
                return sym.type if sym else None
            t = ast_to_type(node.children[0], lookup_tp_size)
            if hasattr(self, "current_subst_map") and self.current_subst_map:
                t = t.substitute(self.current_subst_map)
            t_str = CTypeMapper.to_c_type(t)
            return f"sizeof({t_str})"
        elif rule == "banish_expr":
            return self._translate_banish_target(node.children[0])

        # 3b. 'some expr': heap-box a value into a present PenguMaybe.
        elif rule == "some_expr":
            arg_node = node.children[0]
            arg_c = self._translate_expr(arg_node)
            arg_t = self._infer_node_type(arg_node)
            if arg_t is None:
                if isinstance(arg_node, Tree) and arg_node.data in ("int_lit", "true_lit", "false_lit"):
                    arg_t = INT_TYPE
                elif isinstance(arg_node, Tree) and arg_node.data == "string_lit":
                    arg_t = STRING_TYPE
                elif isinstance(arg_node, Tree) and arg_node.data == "float_lit":
                    arg_t = FLOAT_TYPE
                else:
                    arg_t = INT_TYPE
            t_c = CTypeMapper.to_c_type(arg_t)
            tmp = self.get_temp_name("_some")
            maybe_tmp = self.get_temp_name("_maybe")
            return (
                f"(__extension__({{ {t_c} {tmp} = {arg_c};\n"
                f"  PenguMaybe {maybe_tmp};\n"
                f"  {maybe_tmp}.is_present = true;\n"
                f"  {maybe_tmp}.value = pengu_sigil_alloc(sizeof({t_c}));\n"
                f"  if ({maybe_tmp}.value) memcpy({maybe_tmp}.value, &({tmp}), sizeof({t_c}));\n"
                f"  {maybe_tmp}; }}))"
            )

        # 3c. 'ord expr': byte code of a single-character string.
        elif rule == "ord_expr":
            arg_c = self._translate_expr(node.children[0])
            return f"((int32_t)((unsigned char)(({arg_c}).data[0])))"

        # 3d. 'chr expr': one-character string from an integer byte value.
        elif rule == "chr_expr":
            arg_c = self._translate_expr(node.children[0])
            return f"pengu_string_from_char((char)({arg_c}))"

        # 3e. 'bytes of expr': borrow string characters (read-only) or the first
        # element of an 'array of byte' (writable) as a byte pointer.
        elif rule == "bytes_expr":
            arg_node = node.children[0]
            arg_c = self._translate_expr(arg_node)
            arg_t = self._infer_node_type(arg_node)
            if isinstance(arg_t, ArrayType):
                return f"(&(({arg_c})[0]))"
            return f"((uint8_t*)((({arg_c})).data))"

        # 4. Invocations / Calling
        elif rule == "calling_expr":
            target_node = node.children[0]
            explicit_type_args = []
            args_node = None
            for ch in node.children[1:]:
                if isinstance(ch, Tree):
                    if ch.data == "generic_args":
                        explicit_type_args = [ast_to_type(c, self._lookup_type_fn) for c in ch.children if c is not None]
                    elif ch.data == "arg_list":
                        args_node = ch

            # Translate arguments
            raw_arg_nodes = []
            args = []
            if args_node and isinstance(args_node, Tree) and args_node.data == "arg_list":
                for arg in args_node.children:
                    if isinstance(arg, Tree):
                        if arg.data == "pos_arg":
                            raw_arg_nodes.append(arg.children[0])
                            args.append(self._translate_expr(arg.children[0]))
                        elif arg.data == "named_arg":
                            raw_arg_nodes.append(arg.children[1])
                            args.append(self._translate_expr(arg.children[1]))

            # 1. Normal target method call: obj.method(...) or self->items.method(...)
            if target_node.data == "normal_target" and len(target_node.children) >= 2 and target_node.children[-1].data in ("dot_access", "arrow_access"):
                m_name = str(target_node.children[-1].children[0])
                base_parts = target_node.children[:-1]

                obj_expr_str = str(base_parts[0])
                for part in base_parts[1:]:
                    if isinstance(part, Tree) and part.data == "arrow_access":
                        obj_expr_str += f"->{str(part.children[0])}"
                    elif isinstance(part, Tree) and part.data == "dot_access":
                        obj_expr_str += f".{str(part.children[0])}"

                obj_name = str(base_parts[0]) if len(base_parts) == 1 and isinstance(base_parts[0], (Token, str)) else None

                # Check if this is an imported module call (e.g. spark.println or webui.new_window)
                if obj_name:
                    obj_sym = self.symbols.lookup(obj_name) if self.symbols else None
                    if obj_sym is not None and obj_sym.kind == "import":
                        prefixed = f"{obj_name}_{m_name}"
                        if explicit_type_args:
                            m_suf = "_".join(t.get_mangled_name() for t in explicit_type_args)
                            for cand in (f"{prefixed}_{m_suf}", f"{m_name}_{m_suf}"):
                                if cand in self.symbols.monomorphized_functions or cand in self.fn_info:
                                    prefixed = cand
                                    break
                        elif hasattr(self.symbols, "monomorphized_functions"):
                            m_matches = [m for m in self.symbols.monomorphized_functions if m.startswith(f"{prefixed}_") or m.startswith(f"{m_name}_")]
                            if len(m_matches) == 1:
                                prefixed = m_matches[0]
                        # Prefer the unambiguous module-scoped C name when the code
                        # generator registered it (avoids collisions when another
                        # module exports a function with the same source name).
                        if prefixed in self.fn_info or (hasattr(self.symbols, "monomorphized_functions") and prefixed in self.symbols.monomorphized_functions):
                            fn_entry = self.fn_info.get(prefixed)
                            c_fn_name = fn_entry.get("c_name") if fn_entry and fn_entry.get("c_name") else prefixed
                            if fn_entry and fn_entry.get("params"):
                                args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                            elif fn_entry:
                                fn_params = fn_entry["params"]
                                if len(args) < len(fn_params):
                                    for p in fn_params[len(args):]:
                                        if len(p) >= 3 and p[2] is not None:
                                            args.append(self._translate_expr(p[2]))
                            return f"{c_fn_name}({', '.join(args)})"
                        # Fallback path (aliased imports, insignia-prefixed members):
                        # resolve through the imported module's own member scope.
                        mod_sym = obj_sym.module_scope.lookup(m_name) if obj_sym.module_scope else None
                        c_fn_name = mod_sym.get_c_name() if (mod_sym and hasattr(mod_sym, "get_c_name")) else None
                        if not c_fn_name:
                            if hasattr(self.symbols, "monomorphized_functions"):
                                if prefixed in self.symbols.monomorphized_functions:
                                    c_fn_name = prefixed
                                elif m_name in self.symbols.monomorphized_functions:
                                    c_fn_name = m_name
                            if not c_fn_name:
                                c_fn_name = prefixed if prefixed in self.fn_info else m_name
                        fn_entry = self.fn_info.get(c_fn_name) or self.fn_info.get(prefixed) or self.fn_info.get(m_name)
                        if fn_entry and fn_entry.get("c_name"):
                            c_fn_name = fn_entry["c_name"]
                        if fn_entry and fn_entry.get("params"):
                            args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                        elif fn_entry:
                            fn_params = fn_entry["params"]
                            if len(args) < len(fn_params):
                                for p in fn_params[len(args):]:
                                    if len(p) >= 3 and p[2] is not None:
                                        args.append(self._translate_expr(p[2]))
                        return f"{c_fn_name}({', '.join(args)})"

                # Check if this is a static/ritual method call on a type (e.g. Vec2.zero(...) or Point.create(...))
                if obj_name and (obj_name in self.runes or obj_name in self.echos or obj_name in self.omens or obj_name in self.seals or obj_name in self.concepts or (self.symbols and (self.symbols.lookup_type(obj_name) or self.symbols.lookup_concept(obj_name)))):
                    c_fn_name = f"{obj_name}_{m_name}"
                    fn_entry = self.fn_info.get(c_fn_name)
                    if fn_entry and fn_entry.get("params") is not None:
                        fn_params = fn_entry["params"]
                        call_args = self._build_call_args(fn_params, raw_arg_nodes)
                        return f"{c_fn_name}({', '.join(call_args)})"
                    elif any(w["c_name"] == c_fn_name for w in self.weaves):
                        return f"{c_fn_name}({', '.join(args)})"

                # Lookup object type
                if obj_name:
                    obj_type = self._lookup_var_type(obj_name)
                else:
                    cur_t = self._lookup_var_type(str(base_parts[0]))
                    for part in base_parts[1:]:
                        field_n = str(part.children[0])
                        if cur_t is not None:
                            if isinstance(cur_t, RefType):
                                cur_t = cur_t.target
                            if isinstance(cur_t, RuneType):
                                cur_t = cur_t.fields.get(field_n)
                            elif isinstance(cur_t, BaseType) and cur_t.name in self.runes:
                                cur_t = dict(self.runes[cur_t.name]).get(field_n)
                            else:
                                cur_t = None
                    obj_type = cur_t

                actual_obj_type = obj_type
                if isinstance(actual_obj_type, AliasType):
                    actual_obj_type = actual_obj_type.target
                if isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, AliasType):
                    actual_obj_type = RefType(actual_obj_type.target.target)

                # Built-in ListType methods
                self_ptr = obj_expr_str if (isinstance(obj_type, RefType) or obj_expr_str == "self") else f"&{obj_expr_str}"
                if isinstance(actual_obj_type, ListType) or (isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, ListType)):
                    list_t = actual_obj_type.target if isinstance(actual_obj_type, RefType) else actual_obj_type
                    elem_c = CTypeMapper.to_c_type(list_t.element)
                    arg0 = args[0] if args else ""
                    if elem_c == "PenguString":
                        e_ptr = f"&(({elem_c}){{ ({arg0}).data, ({arg0}).len }})"
                    elif elem_c == "PenguList":
                        e_ptr = f"&(({elem_c}){{ ({arg0}).data, ({arg0}).len, ({arg0}).cap, ({arg0}).elem_size }})"
                    elif elem_c == "PenguMap":
                        e_ptr = f"&(({elem_c}){{ ({arg0}).entries, ({arg0}).len, ({arg0}).cap, ({arg0}).key_size, ({arg0}).val_size }})"
                    elif elem_c in ("int32_t", "int64_t", "float", "double", "bool", "uint8_t", "int8_t", "uint16_t", "int16_t", "uint32_t", "uint64_t"):
                        e_ptr = f"&(({elem_c}){{ {arg0} }})"
                    else:
                        e_ptr = f"&({arg0})"
                    if m_name in ("push", "append"):
                        return f"pengu_list_push({self_ptr}, {e_ptr})"
                    elif m_name == "pop":
                        return f"(*({elem_c}*)pengu_list_pop_val({self_ptr}))"
                    elif m_name == "len":
                        return f"({obj_expr_str}.len)"
                    elif m_name == "is_empty":
                        return f"({obj_expr_str}.len == 0)"
                    elif m_name == "clear":
                        return f"pengu_list_clear({self_ptr})"
                    elif m_name == "contains":
                        return f"pengu_list_contains({self_ptr}, {e_ptr})"
                    elif m_name == "index_of":
                        return f"pengu_list_index_of({self_ptr}, {e_ptr})"
                    elif m_name == "at":
                        return f"(*({elem_c}*)pengu_list_at({self_ptr}, {args[0]}))"

                # Built-in MapType methods
                if isinstance(actual_obj_type, MapType) or (isinstance(actual_obj_type, RefType) and isinstance(actual_obj_type.target, MapType)):
                    map_t = actual_obj_type.target if isinstance(actual_obj_type, RefType) else actual_obj_type
                    key_c = CTypeMapper.to_c_type(map_t.key)
                    val_c = CTypeMapper.to_c_type(map_t.value)
                    arg0 = args[0] if len(args) > 0 else ""
                    arg1 = args[1] if len(args) > 1 else ""
                    k_ptr = f"&(({key_c}){{ ({arg0}).data, ({arg0}).len }})" if key_c == "PenguString" else f"&(({key_c}){{ {arg0} }})"
                    v_ptr = f"&(({val_c}){{ ({arg1}).data, ({arg1}).len }})" if val_c == "PenguString" else f"&(({val_c}){{ {arg1} }})"
                    if m_name in ("put", "insert", "set"):
                        return f"pengu_map_put({self_ptr}, {k_ptr}, {v_ptr})"
                    elif m_name == "get":
                        return f"(*({val_c}*)pengu_map_get({self_ptr}, {k_ptr}))"
                    elif m_name == "remove":
                        return f"pengu_map_remove({self_ptr}, {k_ptr})"
                    elif m_name in ("contains", "contains_key", "has"):
                        return f"pengu_map_contains({self_ptr}, {k_ptr})"
                    elif m_name == "len":
                        return f"({obj_expr_str}.len)"
                    elif m_name == "is_empty":
                        return f"({obj_expr_str}.len == 0)"
                    elif m_name == "clear":
                        return f"pengu_map_clear({self_ptr})"

                t_name = None
                if isinstance(actual_obj_type, RefType):
                    t_name = getattr(actual_obj_type.target, "name", str(actual_obj_type.target))
                elif actual_obj_type is not None:
                    t_name = getattr(actual_obj_type, "name", str(actual_obj_type))

                # Check if this is an enchanting method or concept binding method
                is_enchanting_method = False
                if t_name is not None:
                    if hasattr(self.symbols, "methods") and (t_name, m_name) in self.symbols.methods:
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "monomorphized_methods") and f"{t_name}_{m_name}" in self.symbols.monomorphized_methods:
                        is_enchanting_method = True
                    elif (t_name.split("_")[0], m_name) in getattr(self.symbols, "generic_methods", {}):
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "concept_bindings") and any((b_t == t_name or b_t == t_name.split("_")[0]) and m_name in b_m for (b_t, _), b_m in self.symbols.concept_bindings.items()):
                        is_enchanting_method = True
                    elif hasattr(self.symbols, "functions") and f"{t_name.replace(' ', '_')}_{m_name}" in self.symbols.functions:
                        is_enchanting_method = True
                    elif any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == m_name for w in self.weaves):
                        is_enchanting_method = True

                if is_enchanting_method:
                    c_name = f"{t_name.replace(' ', '_')}_{m_name}"
                    is_ritual = False
                    m_fn = self.symbols.methods.get((t_name, m_name)) if self.symbols else None
                    if m_fn and getattr(m_fn, "is_ritual", False):
                        is_ritual = True
                    if not is_ritual and hasattr(self.symbols, "concept_bindings"):
                        for (b_t, _), b_m in self.symbols.concept_bindings.items():
                            if (b_t == t_name or b_t == t_name.split("_")[0]) and m_name in b_m:
                                if getattr(b_m[m_name], "is_ritual", False):
                                    is_ritual = True
                                    break
                    if not is_ritual and any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == m_name and w.get("is_ritual") for w in self.weaves):
                        is_ritual = True

                    if is_ritual:
                        fn_entry = self.fn_info.get(c_name) or self.fn_info.get(m_name)
                        if fn_entry and fn_entry.get("params"):
                            args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                        return f"{c_name}({', '.join(args)})"

                    if isinstance(obj_type, RefType) or obj_expr_str == "self":
                        self_arg = obj_expr_str
                    else:
                        self_arg = f"&{obj_expr_str}"
                    fn_entry = self.fn_info.get(c_name) or self.fn_info.get(m_name)
                    if fn_entry and fn_entry.get("params"):
                        fn_params = fn_entry["params"]
                        user_params = fn_params[1:] if (len(fn_params) > 0 and fn_params[0][0] in ("self", "restrict self")) else fn_params
                        all_args = [self_arg] + self._build_call_args(user_params, raw_arg_nodes)
                    else:
                        all_args = [self_arg] + args
                    return f"{c_name}({', '.join(all_args)})"
                else:
                    target_str = f"{obj_expr_str}->{m_name}" if isinstance(obj_type, RefType) else f"{obj_expr_str}.{m_name}"
                    return f"{target_str}({', '.join(args)})"

            # 2. With target method call: .method(...)
            elif target_node.data == "with_target":
                field_name = str(target_node.children[0])
                base_target = self.with_stack[-1] if self.with_stack else "self"

                is_enchanting_method = False
                t_name = None
                self_arg = None

                if base_target == "self":
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        self_arg = "self"
                else:
                    base_type = self._lookup_var_type(base_target)
                    if isinstance(base_type, RefType):
                        t_name = getattr(base_type.target, "name", str(base_type.target))
                        self_arg = base_target
                    elif base_type is not None:
                        t_name = getattr(base_type, "name", str(base_type))
                        self_arg = f"&{base_target}"

                if t_name is not None:
                    if hasattr(self.symbols, "methods") and (t_name, field_name) in self.symbols.methods:
                        is_enchanting_method = True
                    elif any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == field_name for w in self.weaves):
                        is_enchanting_method = True

                if is_enchanting_method:
                    c_name = f"{t_name.replace(' ', '_')}_{field_name}"
                    fn_entry = self.fn_info.get(c_name) or self.fn_info.get(field_name)
                    if fn_entry and fn_entry.get("params"):
                        fn_params = fn_entry["params"]
                        user_params = fn_params[1:] if (len(fn_params) > 0 and fn_params[0][0] in ("self", "restrict self")) else fn_params
                        all_args = [self_arg] + self._build_call_args(user_params, raw_arg_nodes)
                    else:
                        all_args = [self_arg] + args
                    return f"{c_name}({', '.join(all_args)})"

                target_str = f"{base_target}.{field_name}"
                return f"{target_str}({', '.join(args)})"

            # 3. Simple function or method inside with block
            elif target_node.data == "normal_target":
                target_str = str(target_node.children[0])

                if target_str == "print":
                    if args:
                        arg_expr = args_node.children[0] if args_node and args_node.children else None
                        if isinstance(arg_expr, Tree) and arg_expr.data in ("pos_arg", "named_arg"):
                            arg_expr = arg_expr.children[-1]
                        inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                        for lv_k, lv_v in self.local_vars.items():
                            inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                        arg_t = None
                        if arg_expr is not None:
                            try:
                                arg_t = inferrer.infer(arg_expr)
                            except Exception:
                                pass
                        if arg_t is None:
                            arg_t = self._lookup_var_type(args[0])

                        if isinstance(arg_t, BaseType):
                            if arg_t.name == "char":
                                return f'printf("%c\\n", (char)({args[0]}))'
                            elif arg_t.name in ("u64", "uint64", "uint64_t", "ulong"):
                                return f'printf("%llu\\n", (unsigned long long)({args[0]}))'
                            elif arg_t.name in ("i64", "int64", "int64_t", "long"):
                                return f'printf("%lld\\n", (long long)({args[0]}))'
                            elif arg_t.name in ("u32", "uint32", "uint32_t", "uint", "u16", "uint16", "uint16_t", "byte", "u8", "uint8", "uint8_t", "usize", "size_t"):
                                return f'printf("%u\\n", (uint32_t)({args[0]}))'
                            elif arg_t.name in ("int", "i32", "i16", "int16", "i8", "int8", "isize"):
                                return f'printf("%d\\n", (int32_t)({args[0]}))'
                            elif arg_t.name in ("float", "f32", "f64", "double"):
                                return f'printf("%f\\n", (double)({args[0]}))'
                            elif arg_t.name in ("bool",):
                                return f'printf("%s\\n", ({args[0]}) ? "true" : "false")'
                            elif arg_t.name in ("string",):
                                return f'printf("%s\\n", ({args[0]}).data)'
                        elif isinstance(arg_t, RefType):
                            if isinstance(arg_t.target, BaseType) and arg_t.target.name == "char":
                                return f'printf("%s\\n", (const char*)({args[0]}))'
                            return f'printf("%p\\n", (void*)({args[0]}))'

                        lv_t = self.local_vars.get(args[0])
                        if lv_t and isinstance(lv_t, BaseType):
                            if lv_t.name == "char":
                                return f'printf("%c\\n", (char)({args[0]}))'
                            elif lv_t.name in ("int", "i32", "i16", "i8"):
                                return f'printf("%d\\n", (int32_t)({args[0]}))'
                            elif lv_t.name in ("u32", "u16", "u8", "byte"):
                                return f'printf("%u\\n", (uint32_t)({args[0]}))'

                        return f'printf("%s\\n", {args[0]}.data)'
                    return 'printf("\\n")'

                if self.with_stack:
                    base_target = self.with_stack[-1]
                    base_sym = self.symbols.lookup(base_target) if self.symbols else None
                    base_type = base_sym.type if base_sym else None
                    t_name = None
                    self_arg = None
                    if base_target == "self":
                        if self.current_enchanted_type is not None:
                            t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                            self_arg = "self"
                    elif base_type is not None:
                        if isinstance(base_type, RefType):
                            t_name = getattr(base_type.target, "name", str(base_type.target))
                            self_arg = base_target
                        else:
                            t_name = getattr(base_type, "name", str(base_type))
                            self_arg = f"&{base_target}"

                    if t_name is not None:
                        if (hasattr(self.symbols, "methods") and (t_name, target_str) in self.symbols.methods) or any(w.get("enchanted_type") is not None and getattr(w["enchanted_type"], "name", str(w["enchanted_type"])) == t_name and w.get("name") == target_str for w in self.weaves):
                            c_name = f"{t_name.replace(' ', '_')}_{target_str}"
                            fn_entry = self.fn_info.get(c_name) or self.fn_info.get(target_str)
                            if fn_entry and fn_entry.get("params"):
                                fn_params = fn_entry["params"]
                                user_params = fn_params[1:] if (len(fn_params) > 0 and fn_params[0][0] in ("self", "restrict self")) else fn_params
                                all_args = [self_arg] + self._build_call_args(user_params, raw_arg_nodes)
                            else:
                                all_args = [self_arg] + args
                            return f"{c_name}({', '.join(all_args)})"

                if (self.symbols and target_str in self.symbols.generic_functions) or (target_str not in self.fn_info and self.symbols):
                    if explicit_type_args:
                        mangled = f"{target_str}_" + "_".join(t.get_mangled_name() for t in explicit_type_args)
                        if mangled in self.symbols.monomorphized_functions:
                            target_str = mangled
                        else:
                            matches = [m for m in self.symbols.monomorphized_functions if m.startswith(f"{target_str}_")]
                            if matches:
                                target_str = matches[0]
                    else:
                        matches = [m for m in self.symbols.monomorphized_functions if m.startswith(f"{target_str}_")]
                        if len(matches) == 1:
                            target_str = matches[0]
                        elif len(matches) > 1:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            arg_types = []
                            if args_node is not None:
                                for c in args_node.children:
                                    val = c.children[1] if c.data == "named_arg" else c.children[0]
                                    arg_types.append(inferrer.infer(val))
                            mangled = f"{target_str}_" + "_".join(t.get_mangled_name() for t in arg_types)
                            if mangled in self.symbols.monomorphized_functions:
                                target_str = mangled
                            elif matches:
                                target_str = matches[0]

                fn_entry = self.fn_info.get(target_str)
                if fn_entry and fn_entry.get("params"):
                    args = self._build_call_args(fn_entry["params"], raw_arg_nodes)
                elif fn_entry:
                    fn_params = fn_entry["params"]
                    if len(args) < len(fn_params):
                        for p in fn_params[len(args):]:
                            if len(p) >= 3 and p[2] is not None:
                                args.append(self._translate_expr(p[2]))
                c_name = fn_entry["c_name"] if fn_entry else target_str
                return f"{c_name}({', '.join(args)})"

            return f"{str(target_node)}({', '.join(args)})"

        # 5. Member and index access
        elif rule == "field_access":
            target_node = node.children[0]
            raw_field = str(node.children[1])
            field_name = self._c_ident(raw_field)
            if isinstance(target_node, Tree) and target_node.data == "var_ref":
                var_name = str(target_node.children[0])
                sym = self.symbols.lookup(var_name) if self.symbols else None
                if sym and sym.kind == "import":
                    if sym.module_scope:
                        mod_field_sym = sym.module_scope.lookup(raw_field)
                        if not mod_field_sym:
                            mod_field_sym = sym.module_scope.lookup(f"{var_name}_{raw_field}")
                        if not mod_field_sym:
                            for s in sym.module_scope.symbols.values():
                                if getattr(s, "kind", "") == "omen_variant" and s.name.endswith(f"_{raw_field}"):
                                    mod_field_sym = s
                                    break
                        if mod_field_sym:
                            m_sym_t = getattr(mod_field_sym, "type", None)
                            if getattr(mod_field_sym, "kind", "") == "omen_variant" and isinstance(m_sym_t, OmenType):
                                o_logical = getattr(m_sym_t, "name", None) or var_name
                                return self._get_omen_variant_c_name(o_logical, raw_field)
                            if getattr(mod_field_sym, "kind", "") == "const":
                                fp = getattr(mod_field_sym, "file_path", "")
                                if fp and fp.endswith(".d.pengu"):
                                    c_val = getattr(mod_field_sym, "const_val", None)
                                    if c_val is not None and isinstance(m_sym_t, (RuneType, EchoType)):
                                        return self._format_const_val(c_val)
                                    if hasattr(mod_field_sym, "get_c_name") and mod_field_sym.get_c_name():
                                        return mod_field_sym.get_c_name()
                                    return raw_field
                            if hasattr(mod_field_sym, "get_c_name"):
                                return mod_field_sym.get_c_name()
                    mod_const_key = f"{var_name}_{raw_field}"
                    if mod_const_key in self.declaration_consts and mod_const_key in self.consts:
                        c_type, val = self.consts[mod_const_key]
                        if val is not None and isinstance(c_type, (RuneType, EchoType)):
                            return self._format_const_val(val)
                        return mod_const_key
                    if raw_field in self.declaration_consts and raw_field in self.consts:
                        c_type, val = self.consts[raw_field]
                        if val is not None and isinstance(c_type, (RuneType, EchoType)):
                            return self._format_const_val(val)
                        return raw_field
                    for o_name, o_vars in self.omens.items():
                        if raw_field in o_vars and (o_name in self.declaration_types or o_name.startswith(f"{var_name}_")):
                            return self._get_omen_variant_c_name(o_name, raw_field)
                    return f"{var_name}_{raw_field}"
                if (sym and isinstance(sym.type, OmenType) and raw_field in sym.type.variants) or (var_name in self.omens and raw_field in self.omens[var_name]):
                    if var_name in self.omens and raw_field in self.omens[var_name]:
                        return self._get_omen_variant_c_name(var_name, raw_field)
                    return f"{var_name}_{raw_field}"
            base = self._translate_expr(target_node)
            if base in self.omens and raw_field in self.omens[base]:
                return self._get_omen_variant_c_name(base, raw_field)
            sym = self.symbols.lookup(base) if self.symbols else None
            if base in self.local_vars and self.local_vars[base] is not None:
                var_t = self.local_vars[base]
            else:
                var_t = sym.type if sym else self._lookup_var_type(base)
            if isinstance(var_t, MaybeType) and raw_field == "value":
                elem_c = CTypeMapper.to_c_type(var_t.element)
                return f"(*({elem_c}*){base}.value)"
            if isinstance(var_t, ResultType) and raw_field == "value":
                elem_c = CTypeMapper.to_c_type(var_t.ok_type)
                return f"(*({elem_c}*){base}.ok_val)"
            if isinstance(var_t, ResultType) and raw_field in ("error", "err"):
                elem_c = CTypeMapper.to_c_type(var_t.err_type)
                return f"(*({elem_c}*){base}.err_val)"
            eff_t = var_t if var_t is not None else (sym.type if sym else None)
            sep = "->" if (base == "self" or isinstance(eff_t, RefType)) else "."
            return f"{base}{sep}{field_name}"
        elif rule == "arrow_access":
            base = self._translate_expr(node.children[0])
            field_name = self._c_ident(str(node.children[1]))
            return f"{base}->{field_name}"
        elif rule == "slice_at_expr":
            base_node = node.children[0]
            slice_range = node.children[1]
            start_c = self._translate_expr(slice_range.children[0])
            end_c = self._translate_expr(slice_range.children[1])
            base_c = self._translate_expr(base_node)
            if self._expr_is_string(base_node):
                return f"pengu_string_substring({base_c}, {start_c}, {end_c})"
            return f"pengu_slice_new(&(({base_c})[{start_c}]), sizeof(({base_c})[0]), (({end_c}) - ({start_c})))"
        elif rule == "for_comp":
            var_name = str(node.children[0])
            iter_node = node.children[1]
            has_cond = (len(node.children) == 4)
            cond_node = node.children[2] if has_cond else None
            then_node = node.children[3] if has_cond else node.children[2]

            iter_c = self._translate_expr(iter_node)

            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
            for lv_k, lv_v in self.local_vars.items():
                inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))

            iter_t = None
            try:
                iter_t = inferrer.infer(iter_node)
            except Exception:
                pass

            iter_elem_t = iter_t.element_type() if iter_t and hasattr(iter_t, "element_type") and iter_t.element_type() else INT_TYPE
            iter_elem_c = CTypeMapper.to_c_type(iter_elem_t)

            self.local_vars[var_name] = iter_elem_t
            inferrer.symbols.define(Symbol(name=var_name, type=iter_elem_t, kind="var"))

            then_t = None
            try:
                then_t = inferrer.infer(then_node)
            except Exception:
                pass
            then_elem_c = CTypeMapper.to_c_type(then_t) if then_t else "int32_t"

            cond_c = self._translate_expr(cond_node) if cond_node else None
            then_c = self._translate_expr(then_node)

            if var_name in self.local_vars:
                del self.local_vars[var_name]

            if isinstance(iter_t, ArrayType) and iter_t.size is not None:
                count_c = str(iter_t.size)
                elem_access = f"({iter_c})[_i]"
            elif isinstance(iter_t, (SliceType, ManyType, ListType)):
                count_c = f"({iter_c}).len"
                if isinstance(iter_t, (SliceType, ManyType)):
                    elem_access = f"((({iter_elem_c}*)({iter_c}).data)[_i])"
                else:
                    elem_access = f"(*({iter_elem_c}*)pengu_list_at(&({iter_c}), _i))"
            else:
                count_c = f"(sizeof({iter_c})/sizeof(({iter_c})[0]))"
                elem_access = f"({iter_c})[_i]"

            tmp_list = self.get_temp_name("_comp_list")
            tmp_val = self.get_temp_name("_comp_val")
            if cond_c:
                return (
                    f"(__extension__({{\n"
                    f"  PenguList {tmp_list} = pengu_list_new(sizeof({then_elem_c}), 8);\n"
                    f"  for (int _i = 0; _i < {count_c}; _i++) {{\n"
                    f"    {iter_elem_c} {var_name} = {elem_access};\n"
                    f"    if ({cond_c}) {{\n"
                    f"      {then_elem_c} {tmp_val} = {then_c};\n"
                    f"      pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                    f"    }}\n"
                    f"  }}\n"
                    f"  {tmp_list};\n"
                    f"}}))"
                )
            else:
                return (
                    f"(__extension__({{\n"
                    f"  PenguList {tmp_list} = pengu_list_new(sizeof({then_elem_c}), {count_c});\n"
                    f"  for (int _i = 0; _i < {count_c}; _i++) {{\n"
                    f"    {iter_elem_c} {var_name} = {elem_access};\n"
                    f"    {then_elem_c} {tmp_val} = {then_c};\n"
                    f"    pengu_list_push(&{tmp_list}, &{tmp_val});\n"
                    f"  }}\n"
                    f"  {tmp_list};\n"
                    f"}}))"
                )
        elif rule == "at_expr":
            parts = flatten_at_chain(node)
            base = self._translate_expr(parts[0])
            var_t = self._lookup_var_type(base) if isinstance(parts[0], Tree) and parts[0].data == "var_ref" else None
            if var_t is None and isinstance(parts[0], Tree):
                t_node = parts[0]
                if t_node.data == "arrow_access":
                    t_field = str(t_node.children[1])
                    if self.current_enchanted_type is not None:
                        t_name = getattr(self.current_enchanted_type, "name", str(self.current_enchanted_type))
                        var_t = self.runes.get(t_name, {}).get(t_field)
                elif t_node.data == "field_access":
                    t_base = str(t_node.children[0])
                    t_field = str(t_node.children[1])
                    b_type = self._lookup_var_type(t_base)
                    if b_type and hasattr(b_type, "name"):
                        var_t = self.runes.get(b_type.name, {}).get(t_field)
            if var_t is None:
                var_t = self._infer_node_type(parts[0])
            for idx_node in parts[1:]:
                current_base = base
                idx = self._translate_expr(idx_node)
                idx = self._emit_bounds_check(idx, current_base, var_t, idx_node)
                if isinstance(var_t, (SliceType, ManyType)):
                    elem_t = CTypeMapper.to_c_type(var_t.element)
                    base = f"((({elem_t}*)({base}).data)[{idx}])"
                    var_t = var_t.element
                elif isinstance(var_t, ListType) or (isinstance(var_t, RefType) and isinstance(var_t.target, ListType)):
                    elem_t = var_t.target.element if isinstance(var_t, RefType) else var_t.element
                    elem_c = CTypeMapper.to_c_type(elem_t)
                    ptr = base if (isinstance(var_t, RefType) and not base.startswith("&")) else f"&({base})"
                    base = f"(*({elem_c}*)pengu_list_at({ptr}, {idx}))"
                    var_t = var_t.element if isinstance(var_t, ListType) else var_t.target.element
                elif isinstance(var_t, ArrayType):
                    base = f"{base}[{idx}]"
                    var_t = var_t.element
                elif isinstance(var_t, RefType):
                    base = f"{base}[{idx}]"
                    tgt = var_t.target
                    while isinstance(tgt, (AliasType, FrozenType)) and getattr(tgt, "target", None):
                        tgt = tgt.target
                    var_t = tgt.element if isinstance(tgt, (ArrayType, SliceType, ManyType, ListType)) else tgt
                elif self._expr_is_string(parts[0], var_t):
                    base = f"pengu_string_char_at({base}, {idx})"
                    var_t = None
                else:
                    base = f"{base}[{idx}]"
                    var_t = None
            return base
        elif rule == "length_expr":
            target_node = node.children[0]
            base = self._translate_expr(target_node)
            var_t = self._infer_node_type(target_node)
            if var_t is None:
                if isinstance(target_node, Tree) and target_node.data == "var_ref":
                    var_t = self._lookup_var_type(str(target_node.children[0]))
                elif isinstance(target_node, Token):
                    var_t = self._lookup_var_type(str(target_node))
                else:
                    var_t = self._lookup_var_type(base)

            actual_t = var_t.target if isinstance(var_t, RefType) else var_t
            if isinstance(actual_t, ArrayType) and actual_t.size is not None:
                return str(actual_t.size)

            sym = self.symbols.lookup(base) if self.symbols else None
            eff_t = var_t if var_t is not None else (sym.type if sym else None)
            sep = "->" if (base == "self" or isinstance(eff_t, RefType)) else "."
            return f"{base}{sep}len"

        # 6. Cast
        elif rule == "cast_expr":
            base = self._translate_expr(node.children[0])
            t = ast_to_type(node.children[1], lambda n: self.symbols.lookup(n).type if self.symbols.lookup(n) else None)
            if isinstance(t, BaseType) and t.name == "string":
                return f"pengu_to_string({base})"
            t_str = CTypeMapper.to_c_type(t)
            return f"(({t_str})({base}))"

        elif rule == "to_expr":
            left_node = node.children[0]
            right_node = node.children[1]
            is_type_cast = False
            cast_target = None
            if isinstance(right_node, Tree):
                if right_node.data in ("base_type", "custom_type", "ref_type", "fn_type", "array_type", "slice_type"):
                    is_type_cast = True
                    cast_target = ast_to_type(right_node, self._lookup_type_fn)
                elif right_node.data == "var_ref":
                    name = str(right_node.children[0])
                    if name in ("int", "i32", "i64", "f32", "f64", "float", "double", "bool", "string", "char", "byte", "u8", "u16", "u32", "u64") or (self.symbols and (name in self.symbols.runes or self.symbols.lookup_type(name))):
                        is_type_cast = True
                        cast_target = ast_to_type(right_node, self._lookup_type_fn)
                    elif name in self.runes or name in self.seals or name in self.aliases:
                        is_type_cast = True
                        cast_target = ast_to_type(right_node, self._lookup_type_fn)
            if is_type_cast and cast_target is not None:
                base = self._translate_expr(left_node)
                if isinstance(cast_target, BaseType) and cast_target.name == "string":
                    return f"pengu_to_string({base})"
                t_str = CTypeMapper.to_c_type(cast_target)
                return f"(({t_str})({base}))"
            else:
                start_c = self._translate_expr(left_node)
                end_c = self._translate_expr(right_node)
                return f"((PenguRange){{ .start = (int64_t)({start_c}), .end = (int64_t)({end_c}) }})"

        elif rule == "range_dotdot":
            start_c = self._translate_expr(node.children[0])
            end_c = self._translate_expr(node.children[-1])
            return f"((PenguRange){{ .start = (int64_t)({start_c}), .end = (int64_t)({end_c}) }})"

        # 7. Ternary if expression: if a then b else c
        elif rule == "if_expr":
            cond = self._translate_expr(node.children[0])
            then_expr = self._translate_expr(node.children[1])
            else_expr = self._translate_expr(node.children[2])
            return f"(({cond}) ? ({then_expr}) : ({else_expr}))"

        # 7b. Compile-time when expression: only the active branch is emitted.
        elif rule == "when_expr":
            val = eval_comptime(self.compile_env, node.children[0])
            if val is None or not isinstance(val, bool):
                raise SemanticError(
                    "'when' condition must evaluate to a compile-time boolean constant",
                    code="E0039",
                )
            if val is True:
                return self._translate_expr(node.children[1], expected_type=expected_type)
            return self._translate_expr(node.children[2], expected_type=expected_type)

        # 8. Struct init: with x is 1 and y is 2
        elif rule == "struct_init":
            if expected_type is None:
                inferred_t = self._infer_node_type(node)
                if isinstance(inferred_t, (RuneType, EchoType, OmenType)):
                    expected_type = inferred_t

            field_inits = []
            unwrapped_struct_t = expected_type
            while isinstance(unwrapped_struct_t, AliasType) and unwrapped_struct_t.target:
                unwrapped_struct_t = unwrapped_struct_t.target

            for f in node.children:
                if isinstance(f, Tree) and f.data == "field_init":
                    f_name = self._c_ident(str(f.children[0]))
                    exp_child_type = None
                    if unwrapped_struct_t is not None:
                        if isinstance(unwrapped_struct_t, (RuneType, EchoType)) and f_name in unwrapped_struct_t.fields:
                            exp_child_type = unwrapped_struct_t.fields[f_name]
                        elif isinstance(unwrapped_struct_t, BaseType) and unwrapped_struct_t.name in self.runes and f_name in self.runes[unwrapped_struct_t.name]:
                            exp_child_type = self.runes[unwrapped_struct_t.name][f_name]
                        elif isinstance(unwrapped_struct_t, BaseType) and unwrapped_struct_t.name in self.echos and f_name in self.echos[unwrapped_struct_t.name]:
                            exp_child_type = self.echos[unwrapped_struct_t.name][f_name]
                        elif isinstance(unwrapped_struct_t, OmenType) and f_name in unwrapped_struct_t.variants:
                            exp_child_type = RuneType(name=f_name, fields=unwrapped_struct_t.variants[f_name])

                    f_val = self._translate_expr(f.children[1], expected_type=exp_child_type) if (len(f.children) > 1 and f.children[1] is not None) else None
                    field_inits.append((f_name, f_val))

            if expected_type is not None and isinstance(expected_type, OmenType):
                if not expected_type.is_algebraic:
                    if field_inits:
                        v_name = field_inits[0][0]
                        return self._get_omen_variant_c_name(expected_type.name, v_name)
                    return f"({expected_type.name})0"
                else:
                    if field_inits:
                        names = [n for n, _ in field_inits]
                        variant_names = set(expected_type.variants)

                        if all(n in variant_names for n in names):
                            # Variant-selected form: `with Connected is with session_id is "x"`
                            distinct = set(names)
                            if len(distinct) > 1:
                                raise SemanticError(
                                    f"omen '{expected_type.name}' initializer selects more than one variant: {sorted(distinct)}",
                                    code="E0041",
                                )
                            v_name, v_val = field_inits[0]
                            v_fields = expected_type.variants.get(v_name, {})
                            tag = self._get_omen_variant_c_name(expected_type.name, v_name)
                            if v_fields and v_val is not None:
                                return f"({expected_type.name}){{ .tag = {tag}, .data.{v_name} = {v_val} }}"
                            return f"({expected_type.name}){{ .tag = {tag} }}"

                        # Bare-payload form: `with code is 404` — resolve each
                        # field to the single variant that owns it.
                        field_to_variants = {}
                        for vn, v_fields in expected_type.variants.items():
                            for fn in v_fields:
                                field_to_variants.setdefault(fn, []).append(vn)
                        variant = None
                        for fn in names:
                            owners = field_to_variants.get(fn, [])
                            if not owners:
                                raise SemanticError(
                                    f"'{fn}' is not a field or variant of omen '{expected_type.name}'",
                                    code="E0041",
                                )
                            if len(owners) > 1:
                                raise SemanticError(
                                    f"omen field '{fn}' is ambiguous: it belongs to variants {owners}; name the variant explicitly",
                                    code="E0041",
                                )
                            if variant is None:
                                variant = owners[0]
                            elif owners[0] != variant:
                                raise SemanticError(
                                    f"omen payload fields belong to different variants "
                                    f"('{variant}' vs '{owners[0]}')",
                                    code="E0041",
                                )
                        payload = ", ".join(f".{fn} = {fv}" for fn, fv in field_inits)
                        tag = self._get_omen_variant_c_name(expected_type.name, variant)
                        return (f"({expected_type.name}){{ .tag = {tag}, "
                                f".data.{variant} = {{{payload}}} }}")
                    return f"({expected_type.name}){{0}}"

            type_name = ""
            if expected_type is not None and isinstance(expected_type, (RuneType, EchoType)):
                is_real_rune = (
                    expected_type.name in self.runes
                    or expected_type.name in self.echos
                    or (self.symbols is not None and (
                        expected_type.name in self.symbols.runes
                        or expected_type.name in self.symbols.echos
                        or (self.symbols.lookup(expected_type.name) and self.symbols.lookup(expected_type.name).kind in ("rune", "echo", "type", "declare"))
                    ))
                )
                if is_real_rune:
                    c_t = CTypeMapper.to_c_type(expected_type)
                    type_name = f"({c_t})"

            field_str = ", ".join(f".{name} = {val}" for name, val in field_inits)
            return f"{type_name}{{{field_str}}}"

        elif rule == "with_init_expr":
            # Block-style construction: build a fresh value through
            # 'set .field is ...' / 'calling .method' statements on an implicit
            # temporary, then yield that temporary as the expression value.
            build_t = expected_type
            if build_t is None:
                build_t = self._infer_node_type(node)
            if not isinstance(build_t, (RuneType, EchoType, OmenType)):
                raise SemanticError(
                    "'with:' block construction requires a struct-like target type "
                    "(rune/echo/omen) from an explicit annotation",
                    code="E0014",
                )
            c_t = CTypeMapper.to_c_type(build_t)
            tmp = self.get_temp_name("_with")
            self.with_stack.append(tmp)
            prev_type = self.local_vars.get(tmp)
            self.local_vars[tmp] = build_t
            try:
                parts = []
                for ch in node.children:
                    if isinstance(ch, Tree):
                        s_code = self._translate_stmt(ch)
                        if s_code:
                            parts.append(s_code.rstrip())
            finally:
                if prev_type is None:
                    self.local_vars.pop(tmp, None)
                else:
                    self.local_vars[tmp] = prev_type
                self.with_stack.pop()
            body = " ".join(parts)
            return f"(__extension__(({{ {c_t} {tmp} = {{0}}; {body} {tmp}; }})))"

        elif rule == "do_expr":
            # General statement-block expression: run the statements in order
            # and evaluate to the last one's value (an expression, or a
            # trailing value-position 'if').
            saved_vars = set(self.local_vars)
            try:
                parts, val = self._value_branch(list(node.children), expected_type)
                if val is not None:
                    parts.append(f"{val};")
            finally:
                for name in list(self.local_vars):
                    if name not in saved_vars:
                        self.local_vars.pop(name, None)
            # The last statement (with its ';') supplies the block value.
            inner_c = "\n".join(parts) if parts else "(void)0;"
            return f"(__extension__(({{\n{inner_c}\n}})))"

        elif rule == "if_stmt":
            # An 'if' reached through an expression position is a value block
            # (the checker recorded the common branch type): emit a GNU
            # statement-expression whose temporary receives the branch value.
            binding = self._binding_cond(node.children[0])
            if binding is not None:
                return self._translate_binding_value_if(node, binding, expected_type)
            return self._translate_value_if(node, expected_type)

        elif rule == "unless_stmt":
            # Same as above with the condition negated ('unless' semantics).
            return self._translate_value_if(node, expected_type, negate=True)

        elif rule in ("while_stmt", "for_range_stmt", "for_in_stmt"):
            # A loop reached through an expression position collects its body's
            # value into a list (the checker recorded 'list of T' on the node).
            return self._translate_loop_value(node, expected_type)

        elif rule == "paren_expr":
            # Keep the grouping visible in the C text; the tree already encodes
            # precedence, so this is only cosmetic.
            return f"({self._translate_expr(node.children[0], expected_type)})"

        elif rule in ("lambda_expr", "lambda_no_params"):
            # Lambdas are emitted as top-level 'static' functions by the
            # pre-scan; the value is the function name, which decays to a
            # function pointer in C.
            name = getattr(node, "_lambda_name", None)
            if name is None:
                raise SemanticError(
                    "lambda no registrada; ejecuta el pre-escaneo antes del codegen",
                    code="E0000")
            return self._cast_fn_value(name, expected_type)

        elif rule == "judge_expr":
            matched_node = node.children[0]
            matched_type = self._infer_node_type(matched_node)
            matched_expr = self._translate_expr(matched_node)

            res_type = expected_type or self._infer_node_type(node)
            res_c_type = CTypeMapper.to_c_type(res_type) if (res_type and not isinstance(res_type, AnyType)) else "__auto_type"
            val_c_type = CTypeMapper.to_c_type(matched_type) if (matched_type and not isinstance(matched_type, AnyType)) else "int32_t"

            clauses = []
            else_val = None
            for c in node.children[1:]:
                if isinstance(c, Tree):
                    if c.data == "when_clause":
                        pat_node = c.children[0]
                        pat = None
                        if isinstance(pat_node, Tree) and pat_node.data == "when_pattern" and pat_node.children:
                            if len(pat_node.children) > 1:
                                pat_parts = [str(p) for p in pat_node.children]
                                pat = "_".join(pat_parts)
                            else:
                                pat_node = pat_node.children[0]
                        if pat is None:
                            pat = self._translate_expr(pat_node)

                        target_omen = None
                        if matched_type and isinstance(matched_type, OmenType):
                            target_omen = matched_type.name
                        elif matched_type and isinstance(matched_type, BaseType) and matched_type.name in self.omens:
                            target_omen = matched_type.name
                        elif matched_expr in self.local_vars and hasattr(self.local_vars[matched_expr], "name") and self.local_vars[matched_expr].name in self.omens:
                            target_omen = self.local_vars[matched_expr].name

                        if target_omen and pat in self.omens.get(target_omen, {}):
                            pat = self._get_omen_variant_c_name(target_omen, pat)

                        val = self._translate_expr(c.children[-1], expected_type=res_type)
                        clauses.append((pat, val))
                    elif c.data == "else_clause":
                        else_val = self._translate_expr(c.children[0], expected_type=res_type)

            if else_val is None:
                if res_type and res_type.is_numeric():
                    else_val = "0"
                elif res_type and res_type.is_string():
                    else_val = 'pengu_string_from_cstr("")'
                else:
                    else_val = f"({res_c_type}){{0}}"

            is_enum_or_int = (matched_type is None or matched_type.is_int() or (isinstance(matched_type, OmenType) and not matched_type.is_algebraic))
            all_switchable = all(pat.lstrip('-').isdigit() or is_enum_or_int for pat, _ in clauses) and len(clauses) > 0
            if all_switchable and is_enum_or_int:
                cases_str = " ".join(f"case {pat}: _res = ({val}); break;" for pat, val in clauses)
                return f"(__extension__({{ {val_c_type} _val = ({matched_expr}); {res_c_type} _res; switch (_val) {{ {cases_str} default: _res = ({else_val}); break; }} _res; }}))"

            # Build ternary chain for non-integer matches
            curr = else_val
            for pat, val in reversed(clauses):
                if matched_type and matched_type.is_string():
                    curr = f"(pengu_string_equal({matched_expr}, {pat}) ? ({val}) : ({curr}))"
                else:
                    curr = f"(({matched_expr} == {pat}) ? ({val}) : ({curr}))"
            return curr

        # 10. Presence checks
        elif rule == "is_present":
            expr_str = self._translate_expr(node.children[0])
            return f"pengu_maybe_is_present(&({expr_str}))"
        elif rule == "is_not_present":
            expr_str = self._translate_expr(node.children[0])
            return f"(!pengu_maybe_is_present(&({expr_str})))"
        elif rule == "is_true":
            expr_str = self._translate_expr(node.children[0])
            return f"(({expr_str}) == true)"
        elif rule == "is_false":
            expr_str = self._translate_expr(node.children[0])
            return f"(({expr_str}) == false)"

        # 11. Collection Inits
        elif rule == "array_lit":
            elem_expected = None
            if expected_type and isinstance(expected_type, (ArrayType, SliceType, ListType, ManyType)):
                elem_expected = expected_type.element
            elems = [self._translate_expr(c, expected_type=elem_expected) for c in node.children]
            return f"{{ {', '.join(elems)} }}"
        elif rule == "array_init_expr":
            elem_type = ast_to_type(node.children[0], self._lookup_type_fn)
            size_expr = self._translate_expr(node.children[1])
            elem_str = CTypeMapper.to_c_type(elem_type)
            return f"({elem_str}[{size_expr}]){{0}}"
        elif rule == "list_init_expr":
            elem_type = ast_to_type(node.children[0], self._lookup_type_fn)
            cap = "8"
            if len(node.children) > 1 and node.children[1] is not None:
                c_trans = self._translate_expr(node.children[1])
                if c_trans:
                    cap = c_trans
            elem_str = CTypeMapper.to_c_type(elem_type)
            return f"pengu_list_new(sizeof({elem_str}), {cap})"

        elif rule == "map_init_expr":
            key_type = ast_to_type(node.children[0], self._lookup_type_fn) if len(node.children) >= 2 else AnyType()
            val_type = ast_to_type(node.children[1], self._lookup_type_fn) if len(node.children) >= 2 else AnyType()
            k_str = CTypeMapper.to_c_type(key_type) if key_type and not isinstance(key_type, AnyType) else "PenguString"
            v_str = CTypeMapper.to_c_type(val_type) if val_type and not isinstance(val_type, AnyType) else "int32_t"
            return f"pengu_map_new(sizeof({k_str}), sizeof({v_str}))"

        # 12. Map literals: { key: value, ... }
        elif rule == "map_lit":
            entries = [c for c in node.children if isinstance(c, Tree) and c.data == "map_entry"]
            map_t = expected_type if (expected_type is not None and isinstance(expected_type, MapType)) else None
            if map_t is None:
                try:
                    inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                    for lv_k, lv_v in self.local_vars.items():
                        inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                    inferred = inferrer.infer(node)
                    if isinstance(inferred, MapType):
                        map_t = inferred
                except Exception:
                    map_t = None
            if map_t is None:
                map_t = MapType(key=STRING_TYPE, value=INT_TYPE)
            key_c = CTypeMapper.to_c_type(map_t.key)
            val_c = CTypeMapper.to_c_type(map_t.value)

            if not entries:
                return f"pengu_map_new(sizeof({key_c}), sizeof({val_c}))"

            m_tmp = self.get_temp_name("_map")
            stmts = [f"PenguMap {m_tmp} = pengu_map_new(sizeof({key_c}), sizeof({val_c}));"]
            for entry in entries:
                key_node = entry.children[0]
                val_node = entry.children[1]

                k_tmp = self.get_temp_name("_mkey")
                if isinstance(key_node, Token) and key_node.type == "STRING":
                    raw_k = str(key_node)
                    k_s = raw_k[1:-1] if (raw_k.startswith('"') and raw_k.endswith('"') and len(raw_k) >= 2) else raw_k
                    key_code = self._translate_string_lit(k_s)
                elif isinstance(key_node, Token):
                    key_code = f'pengu_string_from_cstr("{str(key_node)}")'
                else:
                    key_code = self._translate_expr(key_node, expected_type=map_t.key)
                stmts.append(f"PenguString {k_tmp} = {key_code};")

                v_tmp = self.get_temp_name("_mval")
                val_code = self._translate_expr(val_node, expected_type=map_t.value)
                stmts.append(f"{val_c} {v_tmp} = {val_code};")
                stmts.append(f"pengu_map_put(&{m_tmp}, &{k_tmp}, &{v_tmp});")

            stmts.append(f"{m_tmp};")
            inner = "\n    ".join(stmts)
            return f"(__extension__({{\n    {inner}\n  }}))"

        # 13. Indented literals: 2D/1D arrays, Runes, Maps
        elif rule == "indent_literal":
            child = node.children[0]
            if child.data == "indent_array":
                rows = child.children
                if not rows:
                    return "{0}"

                elem_t = expected_type.element if (expected_type and isinstance(expected_type, ArrayType)) else None
                inner_elem_t = elem_t.element if (elem_t and isinstance(elem_t, ArrayType)) else elem_t

                is_2d = False
                if isinstance(expected_type, ArrayType) and isinstance(expected_type.element, ArrayType):
                    is_2d = True
                elif len(rows) > 1 and len(rows[0].children) > 1:
                    is_2d = True

                if is_2d:
                    row_strs = []
                    for row in rows:
                        elem_strs = [self._translate_expr(e, expected_type=inner_elem_t) for e in row.children]
                        row_strs.append(f"{{ {', '.join(elem_strs)} }}")
                    return f"{{ {', '.join(row_strs)} }}"
                else:
                    elem_strs = []
                    for row in rows:
                        for e in row.children:
                            elem_strs.append(self._translate_expr(e, expected_type=inner_elem_t or elem_t))
                    return f"{{ {', '.join(elem_strs)} }}"

            elif child.data == "indent_entries":
                entries = child.children
                is_rune = False
                rune_name = None
                rune_type = None
                if expected_type is not None:
                    if isinstance(expected_type, (RuneType, EchoType)):
                        is_rune = True
                        rune_name = expected_type.name
                        rune_type = expected_type
                    elif isinstance(expected_type, BaseType) and (expected_type.name in self.runes or expected_type.name in self.echos):
                        is_rune = True
                        rune_name = expected_type.name
                        fields = self.runes.get(rune_name) or self.echos.get(rune_name, {})
                        rune_type = RuneType(name=rune_name, fields=fields)

                if is_rune and rune_name:
                    field_inits = []
                    for entry in entries:
                        f_name = self._c_ident(str(entry.children[0]))
                        f_type = rune_type.fields.get(f_name) if (rune_type and rune_type.fields) else None
                        f_val = self._translate_expr(entry.children[1], expected_type=f_type)
                        field_inits.append(f".{f_name} = {f_val}")
                    return f"({rune_name}){{ {', '.join(field_inits)} }}"
                else:
                    map_t = expected_type if (expected_type is not None and isinstance(expected_type, MapType)) else None
                    if map_t is None:
                        try:
                            inferrer = TypeInferrer(self.symbols, compile_env=self.compile_env)
                            for lv_k, lv_v in self.local_vars.items():
                                inferrer.symbols.define(Symbol(name=lv_k, type=lv_v, kind="var"))
                            inferred = inferrer.infer(node)
                            if isinstance(inferred, MapType):
                                map_t = inferred
                        except Exception:
                            map_t = None
                    if map_t is None:
                        map_t = MapType(key=STRING_TYPE, value=INT_TYPE)

                    key_c = CTypeMapper.to_c_type(map_t.key)
                    val_c = CTypeMapper.to_c_type(map_t.value)

                    if not entries:
                        return f"pengu_map_new(sizeof({key_c}), sizeof({val_c}))"

                    m_tmp = self.get_temp_name("_map")
                    stmts = [f"PenguMap {m_tmp} = pengu_map_new(sizeof({key_c}), sizeof({val_c}));"]
                    for entry in entries:
                        key_node = entry.children[0]
                        val_node = entry.children[1]

                        k_tmp = self.get_temp_name("_mkey")
                        if isinstance(key_node, Token) and key_node.type == "STRING":
                            raw_k = str(key_node)
                            k_s = raw_k[1:-1] if (raw_k.startswith('"') and raw_k.endswith('"') and len(raw_k) >= 2) else raw_k
                            key_code = self._translate_string_lit(k_s)
                        elif isinstance(key_node, Token):
                            key_code = f'pengu_string_from_cstr("{str(key_node)}")'
                        else:
                            key_code = self._translate_expr(key_node, expected_type=map_t.key)
                        stmts.append(f"PenguString {k_tmp} = {key_code};")

                        v_tmp = self.get_temp_name("_mval")
                        val_code = self._translate_expr(val_node, expected_type=map_t.value)
                        stmts.append(f"{val_c} {v_tmp} = {val_code};")
                        stmts.append(f"pengu_map_put(&{m_tmp}, &{k_tmp}, &{v_tmp});")

                    stmts.append(f"{m_tmp};")
                    inner = "\n    ".join(stmts)
                    return f"(__extension__({{\n    {inner}\n  }}))"

        # Fallback to recursively translating first child
        if node.children:
            return self._translate_expr(node.children[0], expected_type)
        return ""


    def _main_is_void(self) -> bool:
        """True when `weave main` is declared `into void` (no value to return)."""
        ret_type = self.main_return_type
        if ret_type is None:
            return True
        try:
            return CTypeMapper.to_c_type(ret_type).strip() == "void"
        except Exception:  # noqa: BLE001 - unknown type: assume it has a value
            return False

    def _main_exit_expression(self) -> str:
        """Returns the C expression whose value becomes the process exit status.

        `weave main` may be declared `into void`, `into bool`, `into u8`, or any
        integer type; the entry wrapper casts whatever it returns to `int` so the
        shell/CI sees the program's status (previously it was discarded and every
        program exited 0).
        """
        return "0" if self._main_is_void() else "(int)pengu_main()"

    def generate_entry_point(self) -> str:
        """Generates standard C main function wrapper for executable output."""
        if not self.has_main:
            return ""

        if self._main_is_void():
            call_lines = ["  pengu_main();"]
            return_lines = ["  return 0;"]
        else:
            call_lines = ["  int pengu_status = (int)pengu_main();"]
            return_lines = ["  return pengu_status;"]

        lines = [
            "/* -------------------------------------------------------------------------",
            " * Entry Point Wrapper",
            " * ------------------------------------------------------------------------- */",
            "int main(int argc, char** argv) {",
            "  /* Expose the program arguments to 'rites.get_args()' etc. */",
            "  pengu_init(argc, argv);",
        ]
        lines += call_lines
        lines += [
            "  fflush(stdout);",
            "  fflush(stderr);",
        ]
        lines += return_lines
        lines += ["}", ""]

        return "\n".join(lines)

    def generate_test_section(self) -> str:
        """Generates test functions and a pengu_run_tests() runner for --test mode."""
        if not self.tests:
            return ""

        def _c_escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

        blocks: List[str] = [
            "/* -------------------------------------------------------------------------",
            " * Integrated Unit Tests (--test mode)",
            " * ------------------------------------------------------------------------- */",
        ]
        # Forward declarations of every test function.
        fwd = [f"static void pengu_test_{i}(void);" for i in range(len(self.tests))]
        blocks.append("\n".join(fwd))

        for i, t in enumerate(self.tests):
            self._apply_main_flag(t.get("filepath"))
            self.current_source_file = t.get("filepath")
            test_file = self._display_path(t.get("filepath")) or ""
            test_line = t.get("line") or 0
            lines = [f"static void pengu_test_{i}(void) {{"]
            self.indent_level += 1
            lines.append(f'{self.indent()}pengu_frame_push("pengu_test_{i}", "{test_file}", {test_line});')
            self.current_function = f"pengu_test_{i}"
            self.current_return_type = VOID_TYPE
            self.current_enchanted_type = None
            self.current_subst_map = {}
            self.local_vars = {}
            self.defer_stack.append([])
            self.errdefer_stack.append([])
            self._auto_banish_push("weave")
            body_code = self._translate_block(t["body_stmts"])
            lines.append(body_code)
            active_defers = self.defer_stack.pop() if self.defer_stack else []
            if self.errdefer_stack:
                self.errdefer_stack.pop()
            if not self._stmts_end_with_jump(t["body_stmts"]):
                if active_defers:
                    lines.append(f"{self.indent()}/* Deferred cleanup */")
                    for d in reversed(active_defers):
                        if d.endswith("}"):
                            lines.append(f"{self.indent()}{d}")
                        else:
                            lines.append(f"{self.indent()}{d};")
                auto_banish = self._flush_current_scope_banish()
                if auto_banish:
                    lines.extend(auto_banish)
            self.auto_banish_stack.pop()
            lines.append(f"{self.indent()}pengu_frame_pop();")
            self.indent_level -= 1
            lines.append("}")
            blocks.append("\n".join(lines))

        names_c = ", ".join(f'"{_c_escape(t["name"])}"' for t in self.tests)
        fns_c = ", ".join(f"pengu_test_{i}" for i in range(len(self.tests)))
        n_tests = len(self.tests)
        runner = (
            "static int pengu_test_json_mode(void) {\n"
            '    const char *v = getenv("PENGU_TEST_JSON");\n'
            "    return v && *v;\n"
            "}\n\n"
            "static void pengu_json_escape_print(const char *s) {\n"
            "    if (!s) return;\n"
            "    for (; *s; s++) {\n"
            '        if (*s == \'"\') printf("\\\\\\\"");\n'
            '        else if (*s == \'\\\\\') printf("\\\\\\\\");\n'
            '        else if (*s == \'\\n\') printf("\\\\n");\n'
            '        else if (*s == \'\\r\') printf("\\\\r");\n'
            '        else if (*s == \'\\t\') printf("\\\\t");\n'
            "        else putchar(*s);\n"
            "    }\n"
            "}\n\n"
            "int pengu_run_tests(void) {\n"
            f"  static const char* pengu_test_names[{n_tests}] = {{ {names_c} }};\n"
            f"  static void (*const pengu_test_fns[{n_tests}])(void) = {{ {fns_c} }};\n"
            "  int i;\n"
            "  if (pengu_test_json_mode()) {\n"
            f'    printf("{{\\"event\\":\\"start\\",\\"total\\":{n_tests}}}\\n");\n'
            "    fflush(stdout);\n"
            f"    for (i = 0; i < {n_tests}; i++) {{\n"
            '      printf("{\\"event\\":\\"test_start\\",\\"name\\":\\"");\n'
            "      pengu_json_escape_print(pengu_test_names[i]);\n"
            '      printf("\\"}\\n");\n'
            "      fflush(stdout);\n"
            "      pengu_test_fns[i]();\n"
            '      printf("{\\"event\\":\\"test_pass\\",\\"name\\":\\"");\n'
            "      pengu_json_escape_print(pengu_test_names[i]);\n"
            '      printf("\\"}\\n");\n'
            "      fflush(stdout);\n"
            "    }\n"
            f'    printf("{{\\"event\\":\\"end\\",\\"total\\":{n_tests},\\"passed\\":{n_tests},\\"failed\\":0}}\\n");\n'
            "    fflush(stdout);\n"
            "    return 0;\n"
            "  }\n"
            f'  printf("Running {n_tests} test(s)...\\n");\n'
            "  fflush(stdout);\n"
            f"  for (i = 0; i < {n_tests}; i++) {{\n"
            '    printf("  [RUN] %s\\n", pengu_test_names[i]);\n'
            "    fflush(stdout);\n"
            "    pengu_test_fns[i]();\n"
            '    printf("  [PASS] %s\\n", pengu_test_names[i]);\n'
            "    fflush(stdout);\n"
            "  }\n"
            f'  printf("All {n_tests} test(s) passed.\\n");\n'
            "  fflush(stdout);\n"
            "  return 0;\n"
            "}\n"
        )
        blocks.append(runner)
        return "\n\n".join(blocks) + "\n"

    def _generated_c_reset(self) -> str:
        """Returns a `#line` marker that restores attribution to the generated C.

        Emitted between compiler-generated sections and `#line`-marked user code
        so that a diagnostic about *generated* code (entry wrapper, test runner,
        lambda trampolines) is not blamed on a random `.pengu` line.
        """
        if not self.emit_line_markers:
            return ""
        if self.bundle_display_path:
            return f'#line 1 "{self.bundle_display_path}"'
        return "#line 1"

    def generate_test_entry_point(self) -> str:
        """Generates a C main that runs the integrated unit tests."""
        lines = [
            "/* -------------------------------------------------------------------------",
            " * Test Entry Point (--test mode)",
            " * ------------------------------------------------------------------------- */",
            "int main(int argc, char** argv) {",
            "  pengu_init(argc, argv);",
            "  int pengu_failed = 0;",
        ]
        if self.tests:
            lines.append("  pengu_failed = pengu_run_tests();")
        else:
            lines.append('  printf("No tests to run.\\n");')
            lines.append("  fflush(stdout);")
        lines.extend([
            "  fflush(stdout);",
            "  fflush(stderr);",
            "  return pengu_failed;",
            "}",
            "",
        ])
        return "\n".join(lines)

    def generate_bundle(
        self,
        custom_includes: Optional[List[str]] = None,
        is_library: bool = False,
        output_path: Optional[str] = None,
        is_test: bool = False
    ) -> str:
        """Generates single monolithic bundle.c combining all modules and runtime header.

        Layout:
        1. Auto-generated header comment.
        2. #include "pengu_runtime.h"
        3. Project custom #include <header.h> directives.
        4. Forward declarations of all types.
        5. Type definitions (runes, echos, omens, aliases, consts).
        6. Function prototypes for all modules.
        7. Function implementations in topological dependency order.
        8. Test section + test entry point (--test mode) or normal entry wrapper.

        Args:
            custom_includes: Additional C headers from pengu.yaml.
            is_library: True if generating static or shared library artifact.
            output_path: Optional destination file path to write bundle.c.
            is_test: True to emit the integrated unit-test runner instead of the
                normal application entry point.

        Returns:
            Generated C code string.
        """
        all_includes = list(self.includes)
        if custom_includes:
            for inc in custom_includes:
                if inc not in all_includes:
                    all_includes.append(inc)

        # `#line` directives are spelled relative to the bundle so the paths stay
        # short and portable; everything else keeps its absolute path.
        if self.compile_env is not None:
            self.debug_mode = bool(getattr(self.compile_env, "is_debug", False))
        self.line_base_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else None
        self.bundle_display_path = os.path.basename(output_path) if output_path else None

        sections = [
            f"/* Auto-generated by PenguScript v{PENGU_VERSION} */",
            '#include "pengu_runtime.h"',
        ]

        for inc in all_includes:
            if inc.startswith("<") or inc.startswith('"'):
                sections.append(f"#include {inc}")
            else:
                sections.append(f'#include "{inc}"')

        sections.append("")
        sections.append("/* Compiled modules in topological order:")
        for mod in self.import_order:
            sections.append(f" * - {os.path.basename(mod)}")
        sections.append(" */")
        sections.append("")


        sections.append(self.generate_forward_declarations())
        sections.append(self.generate_type_definitions())
        sections.append(self.generate_constants())
        sections.append(self.generate_function_prototypes())
        sections.append(self._generated_c_reset())
        sections.append(self.generate_lambdas())
        sections.append(self.generate_function_definitions())
        sections.append(self._generated_c_reset())

        if is_test:
            test_section = self.generate_test_section()
            if test_section:
                sections.append(test_section)
        else:
            test_section = ""

        if not is_library:
            if is_test:
                entry_code = self.generate_test_entry_point()
                if entry_code:
                    sections.append(entry_code)
            else:
                entry_code = self.generate_entry_point()
                if entry_code:
                    sections.append(entry_code)

        bundle_code = "\n".join(sections)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(bundle_code)

        return bundle_code
