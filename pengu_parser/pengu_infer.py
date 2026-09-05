from __future__ import annotations
import re
from typing import Optional, List, Dict, Tuple, Any
from lark import Tree, Token

from .pengu_types import (
    Type, BaseType, RefType, ArrayType, SliceType, ManyType, ListType, MapType, MaybeType,
    RuneType, EchoType, OmenType, ResultType, FnType, OPAQUE_TYPE, AliasType, AnyType,
    TypeParam, NullType, NULL_TYPE, INT_TYPE, I32_TYPE, I64_TYPE, U32_TYPE, U64_TYPE, CHAR_TYPE, BYTE_TYPE,
    U8_TYPE, I8_TYPE, U16_TYPE, I16_TYPE, USIZE_TYPE, ISIZE_TYPE, FLOAT_TYPE, F32_TYPE,
    F64_TYPE, DOUBLE_TYPE, BOOL_TYPE, STRING_TYPE, VOID_TYPE, ERROR_TYPE, ConceptType, SealType,
    implements_concept, resolve_concept_method, ast_to_type, is_opaque_type
)
from .pengu_symbols import SymbolTable, Symbol, Scope
from .pengu_comptime import CompileTimeEnv, default_env, eval_comptime
from .pengu_errors import (
    PenguError, SemanticError, UndefinedIdentifierError, SelfDotAccessError, TypeMismatchError,
    ConstInsideWeaveError, VarLetTopLevelError, MutabilityError, InvalidControlFlowError,
    InvalidMemoryOpError, InvalidWithTargetError, ConceptMethodMismatchError,
    UnimplementedConceptMethodError, ConceptBoundNotSatisfiedError,
    InvalidRitualSelfAccessError, InvalidRitualCallError, SealTypeMismatchError,
    suggest_similar_identifier
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


class ConstFolder:
    """Evaluates and folds compile-time constant expressions in the AST.

    Optimizes binary arithmetic, bitwise, and unary operations on literals and constants.
    """

    def __init__(self, symbols: SymbolTable):
        """Initializes constant folder with symbol table.

        Args:
            symbols: Active symbol table for constant symbol lookup.
        """
        self.symbols = symbols

    def fold(self, node: Any) -> Optional[Any]:
        """Attempts to evaluate node as compile-time constant value.

        Args:
            node: Lark AST Token or Tree to evaluate.

        Returns:
            The constant evaluated Python value (int, float, bool, str) or None if non-constant.
        """
        if node is None:
            return None
        if isinstance(node, Token):
            if node.type == "INT":
                return int(str(node), 0)
            elif node.type == "FLOAT":
                return float(str(node))
            elif node.type == "STRING":
                return str(node).strip('"')
            elif node.type == "CHAR_LIT":
                return str(node)
            elif node.type == "NAME":
                sym = self.symbols.lookup(str(node))
                if sym and sym.kind == "const" and hasattr(sym, "const_val"):
                    return sym.const_val
            return None

        if not isinstance(node, Tree):
            return None

        rule = node.data
        if rule == "int_lit":
            return int(str(node.children[0]), 0)
        elif rule == "float_lit":
            return float(str(node.children[0]))
        elif rule == "char_lit":
            return str(node.children[0])
        elif rule == "string_lit":
            return str(node.children[0]).strip('"')
        elif rule == "true_lit":
            return True
        elif rule == "false_lit":
            return False
        elif rule == "var_ref":
            name = str(node.children[0])
            sym = self.symbols.lookup(name)
            if sym and sym.kind == "const" and hasattr(sym, "const_val"):
                return sym.const_val
            return None

        if rule in ("add", "sub", "mul", "div", "mod", "bitwise_or", "bitwise_and", "bitwise_xor", "shl", "shr"):
            left = self.fold(node.children[0])
            right = self.fold(node.children[1])
            if left is not None and right is not None:
                try:
                    if rule == "add": return left + right
                    elif rule == "sub": return left - right
                    elif rule == "mul": return left * right
                    elif rule == "div": return left // right if isinstance(left, int) and isinstance(right, int) else left / right
                    elif rule == "mod": return left % right
                    elif rule == "bitwise_or": return int(left) | int(right)
                    elif rule == "bitwise_and": return int(left) & int(right)
                    elif rule == "bitwise_xor": return int(left) ^ int(right)
                    elif rule == "shl": return int(left) << int(right)
                    elif rule == "shr": return int(left) >> int(right)
                except (ZeroDivisionError, OverflowError, ValueError):
                    return None
            return None

        if rule in ("eq", "ne", "lt", "le", "gt", "ge"):
            left = self.fold(node.children[0])
            right = self.fold(node.children[1])
            if left is not None and right is not None:
                try:
                    if rule == "eq": return left == right
                    elif rule == "ne": return left != right
                    elif rule == "lt": return left < right
                    elif rule == "le": return left <= right
                    elif rule == "gt": return left > right
                    elif rule == "ge": return left >= right
                except Exception:
                    return None
            return None

        elif rule == "if_expr":
            cond = self.fold(node.children[0])
            if cond is True:
                return self.fold(node.children[1])
            elif cond is False:
                return self.fold(node.children[2])
            return None

        elif rule == "bit_not":
            v = self.fold(node.children[0])
            return ~int(v) if v is not None and isinstance(v, int) else None
        elif rule == "neg":
            v = self.fold(node.children[0])
            return -v if v is not None and isinstance(v, (int, float)) else None
        elif rule == "log_not":
            v = self.fold(node.children[0])
            return not bool(v) if v is not None else None

        elif rule == "some_expr":
            # Boxing must happen at run time (heap allocation); never fold it.
            return None

        elif rule == "ord_expr":
            v = self.fold(node.children[0])
            if isinstance(v, str) and len(v) == 1:
                return ord(v)
            if isinstance(v, str) and len(v) != 1:
                return None
            return None

        elif rule == "chr_expr":
            v = self.fold(node.children[0])
            if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255:
                return chr(v)
            return None

        elif rule == "bytes_expr":
            # Bytes view is a runtime pointer cast; never a compile-time value.
            return None

        if len(node.children) == 1:
            return self.fold(node.children[0])

        return None


class TypeInferrer:
    """Performs bottom-up static type inference and semantic rule validation on AST nodes."""

    def __init__(self, symbol_table: SymbolTable, source_code: str = "", filename: str = "main.pengu",
                 compile_env: Optional[CompileTimeEnv] = None):
        """Initializes type inferrer with symbol table and source text.

        Args:
            symbol_table: Symbol table instance for name resolution.
            source_code: Source text for diagnostic snippets.
            filename: Active file path for diagnostics.
            compile_env: Optional compile-time environment for 'when' expressions.
        """
        self.symbols = symbol_table
        self.source_code = source_code
        self.filename = filename
        self.compile_env = compile_env if compile_env is not None else default_env()
        self.const_folder = ConstFolder(symbol_table)
        self.warnings: List[str] = []

    def _get_loc(self, node: Any) -> Tuple[Optional[int], Optional[int]]:
        """Retrieves source line and column numbers from AST node."""
        if isinstance(node, Token):
            return getattr(node, "line", None), getattr(node, "column", None)
        if isinstance(node, Tree) and getattr(node, "meta", None):
            return getattr(node.meta, 'line', None), getattr(node.meta, 'column', None)
        if isinstance(node, Tree):
            for child in node.children:
                if isinstance(child, Token) and getattr(child, "line", None) is not None:
                    return child.line, child.column
                if isinstance(child, Tree):
                    cl, cc = self._get_loc(child)
                    if cl is not None:
                        return cl, cc
        return None, None

    def _make_error(self, err_cls, message: str, node: Any = None, **kwargs) -> PenguError:
        """Constructs a PenguError with rich source context and coordinates."""
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
        is_c_define: bool = False,
        candidates: Optional[List[str]] = None,
        entity_kind: str = "identifier"
    ) -> UndefinedIdentifierError:
        """Constructs an UndefinedIdentifierError with fuzzy name suggestions."""
        if is_c_define:
            return self._make_error(
                UndefinedIdentifierError,
                f"C define '{name}' used without prior 'include' statement",
                node,
                code="E0016",
                help=f'Add \'include "header.h"\' before using C constant \'{name}\'.',
                note="C definitions require an explicit include to be allowed.",
                label="requires include"
            )

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

    def infer(self, node: Any, expected_type: Optional[Type] = None) -> Type:
        """Recursively infers the static type of an expression node.

        Args:
            node: AST node to infer type for.
            expected_type: Optional expected context type (e.g. from variable annotation).

        Returns:
            The resolved Type of the expression.
        """
        if node is None:
            return VOID_TYPE

        if isinstance(node, Token):
            line, col = node.line, node.column
            if node.type == "INT":
                return INT_TYPE
            elif node.type == "FLOAT":
                return FLOAT_TYPE
            elif node.type == "CHAR_LIT":
                return CHAR_TYPE
            elif node.type == "STRING":
                self._check_string_interpolation(str(node), line, col, node)
                return STRING_TYPE
            elif node.type == "NAME":
                val = str(node)
                sym = self.symbols.lookup(val)
                if sym is not None:
                    return sym.type
                if val.isupper() and self.symbols.has_includes:
                    return INT_TYPE
                if val.isupper() and not self.symbols.has_includes:
                    raise self._make_undefined_error(val, node, is_c_define=True)
                raise self._make_undefined_error(val, node)

        if not isinstance(node, Tree):
            return AnyType()

        line, col = self._get_loc(node)
        rule = node.data

        # Literals
        if rule == "int_lit":
            return INT_TYPE
        elif rule == "float_lit":
            return FLOAT_TYPE
        elif rule == "char_lit":
            return CHAR_TYPE
        elif rule == "string_lit":
            str_val = str(node.children[0]) if node.children else ""
            if expected_type is not None:
                unpacked = expected_type
                while isinstance(unpacked, AliasType) and unpacked.target:
                    unpacked = unpacked.target
                if isinstance(unpacked, RefType):
                    tgt = unpacked.target
                    while isinstance(tgt, AliasType) and tgt.target:
                        tgt = tgt.target
                    if isinstance(tgt, BaseType) and tgt.name in ("char", "const char"):
                        import re
                        raw_s = str_val[1:-1] if (str_val.startswith('"') and str_val.endswith('"') and len(str_val) >= 2) else str_val
                        if list(re.finditer(r'\{([^}]+)\}', raw_s)):
                            raise self._make_error(
                                SemanticError,
                                "String interpolation is not supported when expecting a C string literal (ref to char)",
                                node,
                                code="E0005",
                                help="Use the standard 'string' type if you need string interpolation.",
                                note="A 'ref to char' expects a static C string literal without expressions."
                            )
                        return expected_type
            self._check_string_interpolation(str_val, line, col, node)
            return STRING_TYPE
        elif rule in ("true_lit", "false_lit"):
            return BOOL_TYPE
        elif rule == "null_lit":
            if expected_type is not None:
                unpacked = expected_type
                while isinstance(unpacked, AliasType) and unpacked.target:
                    unpacked = unpacked.target
                if isinstance(unpacked, (RefType, AnyType, TypeParam)) or (isinstance(unpacked, BaseType) and unpacked.name in ("opaque", "any")):
                    return expected_type
                return NULL_TYPE
            return NULL_TYPE
        elif rule == "array_lit":
            if not node.children:
                elem_type = expected_type.element if (expected_type and isinstance(expected_type, ArrayType)) else AnyType()
                return ArrayType(element=elem_type, size=0)
            elem_types = [self.infer(c) for c in node.children]
            first_t = elem_types[0]
            for t in elem_types[1:]:
                if not t.is_compatible(first_t):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Array literal elements must have compatible types, got '{first_t}' and '{t}'",
                        node,
                        code="E0005",
                        help="Ensure all elements in the array literal match.",
                        note="Array elements must be homogenous."
                    )
            return ArrayType(element=first_t, size=len(node.children))
        elif rule == "map_lit":
            entries = [c for c in node.children if isinstance(c, Tree) and c.data == "map_entry"]

            def _unify_map_value_types(types, node_ref):
                """Returns a single value type common to all literal values."""
                if not types:
                    return AnyType()
                is_str = all(isinstance(t, (BaseType, AliasType)) and (
                    (getattr(t, "name", "") == "string") or
                    (isinstance(t, AliasType) and t.target and getattr(t.target, "name", "") == "string")
                ) for t in types)
                if is_str:
                    return STRING_TYPE
                if all(t.is_numeric() for t in types):
                    return FLOAT_TYPE if any(t.is_float() for t in types) else types[0]
                first_t = types[0]
                for t in types[1:]:
                    if not (first_t.is_compatible(t) or t.is_compatible(first_t)):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Map literal values must share a common type, got '{first_t}' and '{t}'",
                            node_ref,
                            code="E0005",
                            help="Ensure every value in the map literal has the same type.",
                            note="Map values must be homogenous so the runtime can store them uniformly."
                        )
                return first_t

            if not entries:
                if expected_type is not None and isinstance(expected_type, MapType):
                    return MapType(key=expected_type.key, value=expected_type.value)
                raise self._make_error(
                    TypeMismatchError,
                    "Empty map literal '{}' cannot infer its type; add an explicit type annotation (e.g. 'let m as map of string to int is {}')",
                    node,
                    code="E0014",
                    help="Annotate the empty map literal with 'as map of K to V'.",
                    note="PenguScript requires explicit types for empty collections."
                )

            seen_keys: Dict[str, str] = {}
            value_types: List[Type] = []
            for entry in entries:
                key_node = entry.children[0]
                val_node = entry.children[1]
                if isinstance(key_node, Token) and key_node.type == "STRING":
                    key_text = str(key_node).strip('"')
                else:
                    key_text = str(key_node)
                if key_text in seen_keys:
                    raise self._make_error(
                        SemanticError,
                        f"Duplicate key '{key_text}' in map literal",
                        entry,
                        code="E0038",
                        help="Each key in a map literal must be unique.",
                        note="Map literal keys must not repeat."
                    )
                seen_keys[key_text] = key_text
                value_types.append(self.infer(val_node, expected_type=(expected_type.value if (expected_type and isinstance(expected_type, MapType)) else None)))

            value_t = _unify_map_value_types(value_types, node)
            if expected_type is not None and isinstance(expected_type, MapType):
                if not value_t.is_compatible(expected_type.value) and not (value_t.is_numeric() and expected_type.value.is_numeric()):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Map literal values have type '{value_t}', but the expected map stores '{expected_type.value}'",
                        node,
                        code="E0005",
                        help=f"Annotate the map as 'map of {expected_type.key} to {value_t}' or change the values.",
                        note="Map value types must match the declared map type."
                    )
                return MapType(key=expected_type.key, value=expected_type.value)
            return MapType(key=STRING_TYPE, value=value_t)
        elif rule == "maybe_none":
            if expected_type is not None and isinstance(expected_type, MaybeType):
                return expected_type
            raise self._make_error(
                TypeMismatchError,
                "'maybe none' requires explicit type context (e.g. 'as maybe T')",
                node,
                code="E0014",
                help="Add an explicit type annotation like 'let x as maybe int is maybe none'.",
                note="'maybe none' requires explicit type context - this guarantees safety."
            )
        elif rule == "error_lit":
            if not self.symbols.is_in_or_block():
                raise self._make_error(
                    SemanticError,
                    "'error' is only available inside 'or:' error-handling blocks",
                    node,
                    code="E0015",
                    help="Use 'error' only within an 'or:' block attached to a failing expression.",
                    note="'error' accesses the Result/Maybe error value in an 'or:' block."
                )
            return ERROR_TYPE

        # Identifiers
        elif rule == "var_ref":
            name = str(node.children[0])
            sym = self.symbols.lookup(name)
            if sym is not None:
                if sym.kind == "omen_variant" and isinstance(sym.type, OmenType) and sym.type.is_string_valued:
                    return STRING_TYPE
                return sym.type
            if name.isupper() and self.symbols.has_includes:
                return INT_TYPE
            if name.isupper() and not self.symbols.has_includes:
                raise self._make_undefined_error(name, node, is_c_define=True)
            raise self._make_undefined_error(name, node)

        elif rule == "self_ref":
            if self.symbols.is_in_ritual_context():
                raise self._make_error(
                    InvalidRitualSelfAccessError,
                    "'self' cannot be used inside a 'ritual' method",
                    node,
                    code="E0033",
                    help="Remove 'self' or remove the 'ritual' modifier to make this an instance method.",
                    note="'ritual' methods are static functions and do not have a 'self' reference."
                )
            if not self.symbols.is_in_enchanting():
                raise self._make_error(
                    SemanticError,
                    "'self' is only valid inside 'enchanting' blocks",
                    node,
                    code="E0003",
                    help="Use 'self' only inside methods within an 'enchanting' block.",
                    note="'self' represents the instance reference in enchanting methods."
                )
            ench_type = self.symbols.current_enchanting_type()
            if ench_type is None:
                raise self._make_error(
                    SemanticError,
                    "'self' used outside enchanting context",
                    node,
                    code="E0003",
                    help="Use 'self' only inside methods within an 'enchanting' block.",
                    note="'self' represents the instance reference in enchanting methods."
                )
            return RefType(target=ench_type)

        # Field and Arrow Access
        elif rule == "field_access":
            target_node = node.children[0]
            field_name = str(node.children[1])

            if isinstance(target_node, Tree) and target_node.data == "var_ref":
                var_name = str(target_node.children[0])
                sym = self.symbols.lookup(var_name)
                if sym and sym.kind == "import":
                    c_sym = self.symbols.lookup(f"{var_name}_{field_name}") or self.symbols.lookup(field_name)
                    if c_sym and c_sym.type:
                        return c_sym.type
                    return INT_TYPE
                if sym and isinstance(sym.type, OmenType) and field_name in sym.type.variants:
                    if sym.type.is_string_valued:
                        return STRING_TYPE
                    return sym.type

            if isinstance(target_node, Tree) and target_node.data == "self_ref":
                raise self._make_error(
                    SelfDotAccessError,
                    "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                    node,
                    code="E0003",
                    help="Change 'self.' to 'self->'.",
                    note="'self' in enchanting is always a reference (ref to SelfType)."
                )
            if isinstance(target_node, Token) and str(target_node) == "self":
                raise self._make_error(
                    SelfDotAccessError,
                    "'self' is always a reference in enchanting and must be accessed with '->', not '.'",
                    node,
                    code="E0003",
                    help="Change 'self.' to 'self->'.",
                    note="'self' in enchanting is always a reference (ref to SelfType)."
                )

            target_type = self.infer(target_node)
            if isinstance(target_type, RefType):
                raise self._make_error(
                    SelfDotAccessError,
                    "Reference must be accessed with '->', not '.'",
                    node,
                    code="E0003",
                    help="Change '.' to '->' when accessing fields on a reference.",
                    note="References (ref to T) require arrow operator '->' for field access."
                )

            if isinstance(target_type, RuneType):
                fields = target_type.fields
                if not fields and self.symbols:
                    sym_t = self.symbols.lookup_type(target_type.name)
                    if isinstance(sym_t, RuneType) and sym_t.fields:
                        fields = sym_t.fields
                if field_name not in fields:
                    raise self._make_error(
                        SemanticError,
                        f"Rune '{target_type.name}' has no field '{field_name}'",
                        node,
                        code="E0013",
                        help=f"Check field spelling or verify the definition of rune '{target_type.name}'.",
                        note=f"Rune '{target_type.name}' only exposes its declared fields."
                    )
                return fields[field_name]

            elif isinstance(target_type, EchoType):
                self.warnings.append(f"[W0002] Echo union '{target_type.name}' access is unsafe")
                if field_name not in target_type.fields:
                    raise self._make_error(
                        SemanticError,
                        f"Echo '{target_type.name}' has no field '{field_name}'",
                        node,
                        code="E0013",
                        help=f"Check field spelling or verify the definition of echo '{target_type.name}'.",
                        note=f"Echo '{target_type.name}' only exposes its declared fields."
                    )
                return target_type.fields[field_name]

            elif isinstance(target_type, OmenType):
                if field_name in target_type.variants:
                    return target_type
                raise self._make_error(
                    SemanticError,
                    f"Omen '{target_type.name}' has no variant '{field_name}'",
                    node,
                    code="E0013",
                    help=f"Check variant spelling or verify definition of omen '{target_type.name}'.",
                    note=f"Omen '{target_type.name}' only exposes its declared variants."
                )
            elif isinstance(target_type, (SliceType, ManyType, ListType)) or (isinstance(target_type, BaseType) and target_type.name == "string"):
                if field_name in ("length", "len", "capacity", "cap", "data"):
                    return INT_TYPE
                raise self._make_error(
                    SemanticError,
                    f"Type '{target_type}' has no field '{field_name}'",
                    node,
                    code="E0013",
                    help="Lists, Slices, and Strings support length / len / capacity.",
                    note="These types do not expose arbitrary fields."
                )
            elif isinstance(target_type, MapType):
                if field_name in ("length", "len", "capacity"):
                    return INT_TYPE
                raise self._make_error(
                    SemanticError,
                    f"Map has no field '{field_name}'",
                    node,
                    code="E0013",
                    help="Maps support length / len / capacity.",
                    note="Maps do not expose arbitrary fields."
                )
            elif isinstance(target_type, MaybeType):
                if field_name == "is_present":
                    return BOOL_TYPE
                elif field_name == "value":
                    return target_type.element
                raise self._make_error(
                    SemanticError,
                    f"Maybe has no field '{field_name}'",
                    node,
                    code="E0013",
                    help="Maybe types support 'is_present' and 'value'.",
                    note="Maybe types do not expose arbitrary fields."
                )
            elif isinstance(target_type, ResultType):
                if field_name == "is_ok":
                    return BOOL_TYPE
                elif field_name == "value":
                    return target_type.ok_type
                elif field_name in ("error", "err"):
                    return target_type.err_type
                raise self._make_error(
                    SemanticError,
                    f"Result has no field '{field_name}'",
                    node,
                    code="E0013",
                    help="Result types support 'is_ok', 'value', and 'error'.",
                    note="Result types do not expose arbitrary fields."
                )
            elif isinstance(target_type, AnyType):
                return AnyType()
            raise self._make_error(
                SemanticError,
                f"Cannot access field '{field_name}' on non-struct type '{target_type}'",
                node,
                code="E0013",
                help="Field access is only supported on runes and echos.",
                note=f"Type '{target_type}' has no fields."
            )

        elif rule == "arrow_access":
            target_node = node.children[0]
            field_name = str(node.children[1])
            target_type = self.infer(target_node)

            if not isinstance(target_type, RefType):
                raise self._make_error(
                    SemanticError,
                    f"Arrow access '->' requires reference type (ref to T), got '{target_type}'",
                    node,
                    code="E0003",
                    help="Use '.' for values or ensure target is a reference (ref to T).",
                    note="Arrow access '->' is only for references."
                )

            inner = target_type.target
            if isinstance(inner, RuneType):
                if field_name not in inner.fields:
                    raise self._make_error(
                        SemanticError,
                        f"Rune '{inner.name}' has no field '{field_name}'",
                        node,
                        code="E0013",
                        help=f"Check field spelling or verify the definition of rune '{inner.name}'.",
                        note=f"Rune '{inner.name}' only exposes its declared fields."
                    )
                return inner.fields[field_name]
            elif isinstance(inner, EchoType):
                self.warnings.append(f"[W0002] Echo union '{inner.name}' access is unsafe")
                if field_name not in inner.fields:
                    raise self._make_error(
                        SemanticError,
                        f"Echo '{inner.name}' has no field '{field_name}'",
                        node,
                        code="E0013",
                        help=f"Check field spelling or verify the definition of echo '{inner.name}'.",
                        note=f"Echo '{inner.name}' only exposes its declared fields."
                    )
                return inner.fields[field_name]
            elif inner == OPAQUE_TYPE or isinstance(inner, AnyType):
                return AnyType()
            elif isinstance(inner, BaseType) and inner.name == "void":
                return AnyType()
            raise self._make_error(
                SemanticError,
                f"Cannot access field '{field_name}' on reference to non-struct type '{inner}'",
                node,
                code="E0013",
                help="Arrow field access is only supported on references to runes and echos.",
                note=f"Type '{inner}' has no fields."
            )

        # Struct Initialization: with x is 10 and y is 20
        elif rule == "struct_init":
            field_inits: Dict[str, Type] = {}
            unwrapped_expected = expected_type
            while isinstance(unwrapped_expected, AliasType):
                unwrapped_expected = unwrapped_expected.target

            expected_fields: Dict[str, Type] = {}
            if isinstance(unwrapped_expected, RuneType):
                expected_fields = unwrapped_expected.fields
                if not expected_fields and self.symbols:
                    sym_t = self.symbols.lookup_type(unwrapped_expected.name)
                    if isinstance(sym_t, RuneType) and sym_t.fields:
                        expected_fields = sym_t.fields
            elif isinstance(unwrapped_expected, EchoType):
                expected_fields = unwrapped_expected.fields
                if not expected_fields and self.symbols:
                    sym_t = self.symbols.lookup_type(unwrapped_expected.name)
                    if isinstance(sym_t, EchoType) and sym_t.fields:
                        expected_fields = sym_t.fields
            elif isinstance(unwrapped_expected, OmenType):
                variants = unwrapped_expected.variants
                if not variants and self.symbols:
                    sym_t = self.symbols.lookup_type(unwrapped_expected.name)
                    if isinstance(sym_t, OmenType) and sym_t.variants:
                        variants = sym_t.variants
                for v_name, v_f in variants.items():
                    expected_fields[v_name] = RuneType(name=v_name, fields=v_f)

            for child in node.children:
                if isinstance(child, Tree) and child.data == "field_init":
                    f_name = str(child.children[0])
                    if len(child.children) > 1 and child.children[1] is not None:
                        f_expr = child.children[1]
                        exp_f_type = expected_fields.get(f_name)
                        f_type = self.infer(f_expr, expected_type=exp_f_type)
                        field_inits[f_name] = f_type
                    else:
                        field_inits[f_name] = VOID_TYPE

            # If expected_type is provided
            if expected_type is not None and not isinstance(expected_type, AnyType):
                if is_opaque_type(expected_type):
                    raise self._make_error(
                        SemanticError,
                        f"Cannot instantiate opaque type '{expected_type.name}' with 'with'",
                        node,
                        code="E0012",
                        help="Opaque types cannot be instantiated directly; obtain them via C interop functions.",
                        note="Opaque types represent opaque C handles without known layout."
                    )


                if isinstance(unwrapped_expected, RuneType):
                    fields = unwrapped_expected.fields
                    if not fields and self.symbols:
                        sym_t = self.symbols.lookup_type(unwrapped_expected.name)
                        if isinstance(sym_t, RuneType) and sym_t.fields:
                            fields = sym_t.fields
                    for f_name, f_type in field_inits.items():
                        if f_name not in fields:
                            raise self._make_error(
                                SemanticError,
                                f"Field '{f_name}' does not exist on Rune '{unwrapped_expected.name}'",
                                node,
                                code="E0013",
                                help=f"Remove '{f_name}' or add it to rune '{unwrapped_expected.name}'.",
                                note=f"Rune '{unwrapped_expected.name}' fields are: {', '.join(fields.keys())}."
                            )
                        expected_f_type = fields[f_name]
                        if not f_type.is_compatible(expected_f_type) and not (f_type.is_numeric() and expected_f_type.is_numeric()):
                            raise self._make_error(
                                TypeMismatchError,
                                f"Field '{f_name}' expected '{expected_f_type}', got '{f_type}'",
                                node,
                                code="E0005",
                                help=f"Provide a value of type '{expected_f_type}' for field '{f_name}'.",
                                note="PenguScript requires exact or compatible field types in struct initializers."
                            )
                    return expected_type

                elif isinstance(unwrapped_expected, (EchoType, OmenType)):
                    return expected_type

            # Exact field set matching for rune inference without 'as'
            init_keys = set(field_inits.keys())
            matching: List[RuneType] = [
                r_type for r_type in self.symbols.runes.values()
                if set(r_type.fields.keys()) == init_keys
            ]

            fields_str = "{" + ",".join(sorted(init_keys)) + "}"
            if len(matching) == 0:
                closest_help = f"Define a rune matching fields {fields_str} or write explicit type 'as RuneName'."
                for r_name, r_type in self.symbols.runes.items():
                    r_keys = set(r_type.fields.keys())
                    if init_keys.issubset(r_keys):
                        missing = r_keys - init_keys
                        r_fields_str = "{" + ",".join(sorted(r_keys)) + "}"
                        closest_help = f"Rune '{r_name}' has fields {r_fields_str} but init has {fields_str}. Add {', '.join(sorted(missing))} or specify 'as RuneName'."
                        break

                raise self._make_error(
                    SemanticError,
                    f"Cannot infer rune type for struct init with fields {fields_str}, no rune matches",
                    node,
                    code="E0010",
                    help=closest_help,
                    note="PenguScript infers rune by exact field names to guarantee safety."
                )
            elif len(matching) > 1:
                matches_str = ", ".join(sorted(r.name for r in matching))
                raise self._make_error(
                    SemanticError,
                    f"Ambiguous struct init with fields {fields_str}, matches: {matches_str}",
                    node,
                    code="E0011",
                    help=f"Disambiguate by specifying the rune type explicitly with 'as RuneName'.",
                    note="PenguScript requires explicit type when multiple runes have identical field names."
                )
            else:
                matched_rune = matching[0]
                if is_opaque_type(matched_rune):
                    raise self._make_error(
                        SemanticError,
                        f"Cannot instantiate opaque type '{matched_rune.name}' with 'with'",
                        node,
                        code="E0012",
                        help="Opaque types cannot be instantiated directly; obtain them via C interop functions.",
                        note="Opaque types represent opaque C handles without known layout."
                    )
                for f_name, f_type in field_inits.items():
                    expected_f_type = matched_rune.fields[f_name]
                    if not f_type.is_compatible(expected_f_type) and not (f_type.is_numeric() and expected_f_type.is_numeric()):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Field '{f_name}' expected '{expected_f_type}', got '{f_type}'",
                            node,
                            code="E0005",
                            help=f"Provide a value of type '{expected_f_type}' for field '{f_name}'.",
                            note="PenguScript requires exact or compatible field types in struct initializers."
                        )
                return matched_rune

        # Collections initializers
        elif rule == "list_init_expr":
            elem_type = ast_to_type(node.children[0], self.symbols.lookup_type)
            if len(node.children) > 1 and node.children[1] is not None:
                cap_type = self.infer(node.children[1])
                if not cap_type.is_int():
                    raise self._make_error(
                        TypeMismatchError,
                        f"List capacity must be an integer, got '{cap_type}'",
                        node,
                        code="E0005",
                        help="Use an integer expression for list capacity.",
                        note="Capacities must be integer values."
                    )
            return ListType(element=elem_type)

        elif rule == "map_init_expr":
            key_type = ast_to_type(node.children[0], self.symbols.lookup_type)
            val_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            return MapType(key=key_type, value=val_type)

        elif rule == "array_init_expr":
            elem_type = ast_to_type(node.children[0], self.symbols.lookup_type)
            size_expr = node.children[1]
            size_type = self.infer(size_expr)
            if not size_type.is_int():
                raise self._make_error(
                    TypeMismatchError,
                    f"Array size must be an integer, got '{size_type}'",
                    node,
                    code="E0005",
                    help="Use an integer expression for array size.",
                    note="Array sizes must be integer values."
                )
            folded_size = self.const_folder.fold(size_expr)
            if folded_size is None or not isinstance(folded_size, int) or folded_size <= 0:
                raise self._make_error(
                    TypeMismatchError,
                    f"Array size must be a positive compile-time constant integer, got non-constant '{size_expr}'",
                    node,
                    code="E0005",
                    help="Use a compile-time integer constant or literal for array size.",
                    note="PenguScript requires fixed, compile-time constant array bounds to prevent VLAs."
                )
            return ArrayType(element=elem_type, size=folded_size)

        # Array and Slice indexing
        elif rule == "at_expr":
            target = node.children[0]
            idx_node = node.children[1]
            target_type = self.infer(target)
            idx_type = self.infer(idx_node)

            if isinstance(target_type, (ArrayType, SliceType, ManyType, ListType)):
                if not idx_type.is_int():
                    raise self._make_error(
                        TypeMismatchError,
                        f"Array/Slice index must be an integer, got '{idx_type}'",
                        node,
                        code="E0005",
                        help="Ensure the index expression evaluates to an integer.",
                        note="Collection indexing requires integer offsets."
                    )
                return target_type.element
            elif isinstance(target_type, MapType):
                if not idx_type.is_compatible(target_type.key):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Map key expected '{target_type.key}', got '{idx_type}'",
                        node,
                        code="E0005",
                        help=f"Provide a map key of type '{target_type.key}'.",
                        note="Map indexing requires matching key types."
                    )
                return target_type.value
            elif target_type == STRING_TYPE:
                if not idx_type.is_int():
                    raise self._make_error(
                        TypeMismatchError,
                        f"String index must be an integer, got '{idx_type}'",
                        node,
                        code="E0005",
                        help="Ensure the string index is an integer.",
                        note="String indexing requires integer offsets."
                    )
                return STRING_TYPE
            elif isinstance(target_type, AnyType):
                return AnyType()
            raise self._make_error(
                SemanticError,
                f"Cannot index non-collection type '{target_type}' with 'at'",
                node,
                code="E0005",
                help="Only arrays, slices, lists, maps, and strings can be indexed with 'at'.",
                note="Non-collection types do not support indexing."
            )

        elif rule == "slice_at_expr":
            target = node.children[0]
            slice_range = node.children[1]
            target_type = self.infer(target)

            start_node = slice_range.children[0]
            end_node = slice_range.children[1]
            start_type = self.infer(start_node)
            end_type = self.infer(end_node)

            if not start_type.is_int() or not end_type.is_int():
                raise self._make_error(
                    TypeMismatchError,
                    f"Slice range bounds must be integers, got '{start_type}' to '{end_type}'",
                    node,
                    code="E0005",
                    help="Ensure both start and end bounds evaluate to integers.",
                    note="Slice ranges require integer bounds."
                )

            if isinstance(target_type, (ArrayType, SliceType, ManyType, ListType)):
                return SliceType(element=target_type.element)
            elif target_type == STRING_TYPE:
                return STRING_TYPE
            elif isinstance(target_type, AnyType):
                return SliceType(element=AnyType())
            raise self._make_error(
                SemanticError,
                f"Cannot take slice of non-collection type '{target_type}'",
                node,
                code="E0005",
                help="Only arrays, slices, lists, and strings can be sliced.",
                note="Non-collection types do not support slicing."
            )

        elif rule == "length_expr":
            target = node.children[0]
            target_type = self.infer(target)
            actual_t = target_type.target if isinstance(target_type, RefType) else target_type
            if not actual_t.is_iterable() and actual_t != STRING_TYPE and not isinstance(actual_t, AnyType):
                raise self._make_error(
                    SemanticError,
                    f"Cannot get 'length' of non-collection type '{target_type}'",
                    node,
                    code="E0005",
                    help="Only collections and strings have a 'length'.",
                    note="Non-collection types do not have a length property."
                )
            return INT_TYPE

        # Comprehension: for x in arr when cond then expr
        elif rule == "for_comp":
            var_name = str(node.children[0])
            iter_expr = node.children[1]
            iter_type = self.infer(iter_expr)

            if not iter_type.is_iterable() and not isinstance(iter_type, AnyType):
                raise self._make_error(
                    SemanticError,
                    f"Cannot iterate over non-iterable type '{iter_type}' in comprehension",
                    node,
                    code="E0005",
                    help="Provide an iterable collection like an array, slice, or list.",
                    note="'for ... in' comprehensions require iterable collections."
                )

            elem_type = iter_type.element_type() or AnyType()

            self.symbols.push_scope(kind="for")
            self.symbols.define(Symbol(name=var_name, type=elem_type, kind="var", is_mutable=False))

            cond_expr = node.children[2] if len(node.children) == 4 else None
            then_expr = node.children[3] if len(node.children) == 4 else node.children[2]

            if cond_expr is not None:
                cond_type = self.infer(cond_expr)
                if not cond_type.is_compatible(BOOL_TYPE):
                    raise self._make_error(
                        TypeMismatchError,
                        f"when condition must be bool, got '{cond_type}'",
                        cond_expr,
                        code="E0005",
                        help="Ensure 'when' filter evaluates to a boolean (bool).",
                        note="Filter conditions in comprehensions must be boolean expressions."
                    )

            result_elem_type = self.infer(then_expr)
            self.symbols.pop_scope()

            return ListType(element=result_elem_type)

        # Control flow expressions
        elif rule == "if_expr":
            cond_type = self.infer(node.children[0])
            if not cond_type.is_compatible(BOOL_TYPE):
                raise self._make_error(
                    TypeMismatchError,
                    f"'if' condition must be bool, got '{cond_type}'",
                    node,
                    code="E0005",
                    help="Ensure 'if' condition evaluates to a boolean (bool).",
                    note="Branch conditions must be boolean expressions."
                )
            then_type = self.infer(node.children[1])
            else_type = self.infer(node.children[2])
            if not then_type.is_compatible(else_type) and not else_type.is_compatible(then_type):
                raise self._make_error(
                    TypeMismatchError,
                    f"'if' branches have incompatible types: '{then_type}' vs '{else_type}'",
                    node,
                    code="E0005",
                    help="Ensure both 'then' and 'else' branches return compatible types.",
                    note="If-expressions must produce values of unified type."
                )
            return then_type

        elif rule == "when_expr":
            # Compile-time conditional expression: only the active branch matters.
            cond_val = eval_comptime(self.compile_env, node.children[0])
            if cond_val is None or not isinstance(cond_val, bool):
                raise self._make_error(
                    TypeMismatchError,
                    "'when' expression condition must evaluate to a compile-time boolean constant",
                    node,
                    code="E0039",
                    help="Use expressions such as os == \"windows\" or defined(NAME) in 'when' expressions.",
                    note="Compile-time 'when' expressions require constant conditions."
                )
            if cond_val is True:
                return self.infer(node.children[1], expected_type=expected_type)
            return self.infer(node.children[2], expected_type=expected_type)

        elif rule == "judge_expr":
            matched_type = self.infer(node.children[0])
            branch_types: List[Type] = []
            has_else = False
            covered_variants: Set[str] = set()

            for child in node.children[1:]:
                if isinstance(child, Tree) and child.data == "when_clause":
                    pattern_node = child.children[0]
                    v_name = str(pattern_node.children[0] if isinstance(pattern_node, Tree) else pattern_node)
                    covered_variants.add(v_name)
                    body_expr = child.children[-1]
                    body_type = self.infer(body_expr)
                    branch_types.append(body_type)
                elif isinstance(child, Tree) and child.data == "else_clause":
                    has_else = True
                    body_expr = child.children[0]
                    body_type = self.infer(body_expr)
                    branch_types.append(body_type)

            if isinstance(matched_type, OmenType) and not has_else:
                all_vars = set(matched_type.variants.keys())
                missing = all_vars - covered_variants
                if missing:
                    self.warnings.append(f"[W0003] Non-exhaustive judge, missing variants: {', '.join(sorted(missing))}")

            if not branch_types:
                return VOID_TYPE
            first_type = branch_types[0]
            for bt in branch_types[1:]:
                if not first_type.is_compatible(bt):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Judge branches have incompatible return types: '{first_type}' vs '{bt}'",
                        node,
                        code="E0005",
                        help="Ensure all 'when' branches and 'else' branch return compatible types.",
                        note="Judge expressions must produce values of unified type."
                    )
            return first_type

        # Pointers and memory
        elif rule == "sigil_of":
            target = node.children[0]
            self._validate_addressable(target)
            target_type = self.infer(target)
            return RefType(target=target_type)

        elif rule == "essence_of":
            target = node.children[0]
            if isinstance(target, Tree) and target.data == "length_expr":
                return self.infer(target)
            target_type = self.infer(target)
            if not isinstance(target_type, RefType) and not isinstance(target_type, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"'essence of' requires reference type (ref to T), got '{target_type}'",
                    node,
                    code="E0008",
                    help="Pass a reference type (ref to T) to 'essence of'.",
                    note="'essence of' dereferences a pointer/reference."
                )
            if isinstance(target_type, RefType):
                return target_type.target
            return AnyType()

        elif rule == "transmute":
            src_node = node.children[0]
            target_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            src_type = self.infer(src_node)

            def get_type_size(t: Type) -> Optional[int]:
                if isinstance(t, BaseType):
                    if t.name in ("int", "i32", "float", "f32"): return 4
                    elif t.name in ("i64", "f64"): return 8
                    elif t.name == "bool": return 1
                    elif t.name == "string": return 16
                elif isinstance(t, RefType):
                    return 8
                elif isinstance(t, RuneType):
                    return sum(get_type_size(ft) or 8 for ft in t.fields.values())
                return None

            src_sz = get_type_size(src_type)
            tgt_sz = get_type_size(target_type)
            if src_sz is not None and tgt_sz is not None and src_sz != tgt_sz:
                self.warnings.append(
                    f"[W0001] transmute from '{src_type}' ({src_sz} bytes) to '{target_type}' ({tgt_sz} bytes) has size mismatch and is unsafe"
                )
            else:
                self.warnings.append("[W0001] transmute is unsafe, use 'to' for safe conversions")
            return target_type

        elif rule == "cast_expr":
            src_node = node.children[0]
            target_type = ast_to_type(node.children[1], self.symbols.lookup_type)
            src_type = self.infer(src_node)
            if not src_type.can_cast_to(target_type) and not isinstance(src_type, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Cannot cast '{src_type}' to '{target_type}'",
                    node,
                    code="E0005",
                    help=f"Ensure '{src_type}' can be safely converted to '{target_type}'.",
                    note="PenguScript requires safe, explicit casts."
                )
            return target_type

        elif rule == "size_of":
            target_type_node = node.children[0]
            resolved_t = ast_to_type(target_type_node, self.symbols.lookup_type)
            if isinstance(resolved_t, RuneType) and resolved_t.name not in self.symbols.runes:
                if resolved_t.name not in (
                    "int", "i32", "i64", "float", "f32", "f64", "bool", "string", "void", "opaque", "any",
                    "char", "byte", "u8", "i8", "u16", "i16", "u32", "u64", "int8", "uint8",
                    "int16", "uint16", "int32", "uint32", "int64", "uint64", "usize", "isize",
                    "size_t", "short", "ushort", "long", "ulong", "double", "int8_t", "uint8_t",
                    "int16_t", "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t", "uint"
                ):
                    if not self.symbols.lookup_type(resolved_t.name):
                        raise self._make_error(
                            UndefinedIdentifierError,
                            f"Undefined type '{resolved_t.name}' in 'size of'",
                            node,
                            code="E0004",
                            help=f"Declare type '{resolved_t.name}' before using 'size of'.",
                            note="Types used in 'size of' expressions must be declared."
                        )
            return INT_TYPE

        elif rule == "some_expr":
            # 'some expr' allocates a copy of expr on the heap and wraps it in a
            # present Maybe container:  maybe T.
            inner_t = self.infer(node.children[0])
            if inner_t == VOID_TYPE:
                raise self._make_error(
                    TypeMismatchError,
                    "'some' cannot wrap a void value",
                    node,
                    code="E0005",
                    help="'some' requires a value of a concrete type.",
                    note="'some' boxes a concrete value into a maybe."
                )
            return MaybeType(element=inner_t)

        elif rule == "ord_expr":
            # 'ord s' returns the byte code of the first (and only) character.
            arg = node.children[0]
            arg_t = self.infer(arg)
            if not arg_t.is_string() and not isinstance(arg_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"'ord' expects a string of length 1, got '{arg_t}'",
                    node,
                    code="E0005",
                    help="Pass a single-character string to 'ord'.",
                    note="'ord' reads the byte code of a single character."
                )
            if isinstance(arg, Tree) and arg.data == "string_lit":
                raw = str(arg.children[0]) if arg.children else ""
                s_val = raw[1:-1] if (raw.startswith('"') and raw.endswith('"') and len(raw) >= 2) else raw
                if len(s_val) != 1:
                    raise self._make_error(
                        TypeMismatchError,
                        f"'ord' expects a string of length 1, got {len(s_val)} characters",
                        node,
                        code="E0005",
                        help="Use a single-character string literal with 'ord'.",
                        note="'ord' operates on exactly one character."
                    )
            return INT_TYPE

        elif rule == "chr_expr":
            # 'chr code' builds a one-character string from an int byte value.
            arg = node.children[0]
            arg_t = self.infer(arg)
            if not arg_t.is_int() and not isinstance(arg_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"'chr' expects an integer byte value, got '{arg_t}'",
                    node,
                    code="E0005",
                    help="Pass an integer in the range 0-255 to 'chr'.",
                    note="'chr' maps a byte code to a one-character string."
                )
            folded = self.const_folder.fold(arg)
            if folded is not None and isinstance(folded, int) and not isinstance(folded, bool):
                if folded < 0 or folded > 255:
                    raise self._make_error(
                        TypeMismatchError,
                        f"'chr' byte value {folded} is out of range 0-255",
                        node,
                        code="E0005",
                        help="Use a byte value between 0 and 255.",
                        note="'chr' only supports byte values 0-255."
                    )
            return STRING_TYPE

        elif rule == "bytes_expr":
            # 'bytes of s' exposes a Pengu string's character storage as a
            # read-only 'ref to byte'; 'bytes of a' (a fixed 'array of byte')
            # yields a writable 'ref to byte' to the first element.
            arg_node = node.children[0]
            arg_t = self.infer(arg_node)
            if arg_t.is_string() or isinstance(arg_t, AnyType):
                return RefType(target=BaseType(name="byte"))
            if isinstance(arg_t, ArrayType):
                elem = arg_t.element
                if isinstance(elem, BaseType) and elem.name in ("byte", "u8", "uint8"):
                    return RefType(target=BaseType(name="byte"))
            raise self._make_error(
                TypeMismatchError,
                f"'bytes of' expects a string or an 'array of byte', got '{arg_t}'",
                node,
                code="E0005",
                help="Pass a string (read-only) or an 'array of byte' (writable) to 'bytes of'.",
                note="'bytes of' borrows the internal byte storage of the operand."
            )

        elif rule == "banish_expr":
            target = node.children[0]
            if isinstance(target, Tree) and target.data == "var_ref":
                sym_name = str(target.children[0])
                sym = self.symbols.lookup(sym_name)
                if sym and sym.kind == "const":
                    raise self._make_error(
                        InvalidMemoryOpError,
                        f"Cannot banish constant '{sym_name}'",
                        target,
                        code="E0008",
                        help="Only allocated references can be banished.",
                        note="Constants cannot be banished."
                    )
            t = self.infer(target)
            if not isinstance(t, RefType) and not isinstance(t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"'banish' requires reference type, got '{t}'",
                    node,
                    code="E0008",
                    help="Pass a reference type (ref to T) to 'banish'.",
                    note="'banish' frees memory allocated behind a reference."
                )
            return VOID_TYPE

        # Calling function or method
        elif rule == "calling_expr":
            target_node = node.children[0]
            explicit_type_args = []
            args_tree = None
            for ch in node.children[1:]:
                if isinstance(ch, Tree):
                    if ch.data == "generic_args":
                        explicit_type_args = [ast_to_type(c, self.symbols.lookup_type) for c in ch.children if c is not None]
                    elif ch.data == "arg_list":
                        args_tree = ch

            fn_type, method_self_type = self._resolve_call_target(target_node)
            if fn_type is None:
                return AnyType()

            pos_args: List[Tuple[Type, Any]] = []
            named_args: List[Tuple[str, Tuple[Type, Any]]] = []

            # Determine function and method names
            fn_name = None
            method_name = None
            if target_node.data == "normal_target":
                if len(target_node.children) == 1:
                    fn_name = str(target_node.children[0])
                elif len(target_node.children) >= 2 and isinstance(target_node.children[1], Tree) and target_node.children[1].data == "dot_access":
                    method_name = str(target_node.children[1].children[0])
            elif target_node.data == "with_target":
                method_name = str(target_node.children[0])

            seen_named = False
            param_dict = {p[0]: p[1] for p in fn_type.params if p[0]} if fn_type and fn_type.params else {}
            has_variadic = len(fn_type.params) > 0 and isinstance(fn_type.params[-1][1], ManyType) if fn_type and fn_type.params else False
            pos_idx = 0
            if args_tree is not None:
                for arg_node in args_tree.children:
                    if isinstance(arg_node, Tree):
                        if arg_node.data == "named_arg":
                            seen_named = True
                            arg_name = str(arg_node.children[0])
                            arg_val = arg_node.children[1]
                            exp_t = param_dict.get(arg_name)
                            arg_t = self.infer(arg_val, expected_type=exp_t)
                            named_args.append((arg_name, (arg_t, arg_val)))
                        elif arg_node.data == "pos_arg":
                            if seen_named:
                                raise self._make_error(
                                    TypeMismatchError,
                                    "Positional argument after named argument",
                                    arg_node,
                                    code="E0005",
                                    help="Move positional arguments before named: calling foo with 1 and 2 and x is 3",
                                    note="PenguScript requires positional args before named args for safety"
                                )
                            arg_val = arg_node.children[0]
                            exp_t = None
                            if fn_type and fn_type.params:
                                if pos_idx < len(fn_type.params):
                                    exp_t = fn_type.params[pos_idx][1]
                                elif has_variadic:
                                    exp_t = fn_type.params[-1][1].element if isinstance(fn_type.params[-1][1], ManyType) else None
                            arg_t = self.infer(arg_val, expected_type=exp_t)
                            pos_args.append((arg_t, arg_val))
                            pos_idx += 1

            total_passed = len(pos_args) + len(named_args)
            total_params = len(fn_type.params)
            has_variadic = total_params > 0 and isinstance(fn_type.params[-1][1], ManyType)
            if has_variadic:
                min_params = (total_params - 1) - fn_type.default_count
            else:
                min_params = total_params - fn_type.default_count

            # Generic function / method specialization
            if fn_name and ((fn_name in self.symbols.generic_functions) or (fn_type and fn_type.type_params)):
                type_params = self.symbols.generic_functions[fn_name][0] if (fn_name in self.symbols.generic_functions) else fn_type.type_params
                subst_map: Dict[str, Type] = {}
                if explicit_type_args:
                    for tp, ta in zip(type_params, explicit_type_args):
                        subst_map[tp] = ta

                def unify(param_t: Type, arg_t: Type):
                    if isinstance(param_t, TypeParam):
                        if param_t.name not in subst_map:
                            subst_map[param_t.name] = arg_t
                    elif isinstance(param_t, ManyType):
                        if isinstance(arg_t, (ManyType, SliceType, ArrayType)):
                            unify(param_t.element, arg_t.element)
                        else:
                            unify(param_t.element, arg_t)
                    elif isinstance(param_t, RefType) and isinstance(arg_t, RefType):
                        unify(param_t.target, arg_t.target)
                    elif isinstance(param_t, ArrayType) and isinstance(arg_t, ArrayType):
                        unify(param_t.element, arg_t.element)
                    elif isinstance(param_t, SliceType) and isinstance(arg_t, (SliceType, ManyType, ArrayType)):
                        unify(param_t.element, arg_t.element)
                    elif isinstance(param_t, ListType) and isinstance(arg_t, ListType):
                        unify(param_t.element, arg_t.element)
                    elif isinstance(param_t, MapType) and isinstance(arg_t, MapType):
                        unify(param_t.key, arg_t.key)
                        unify(param_t.value, arg_t.value)
                    elif isinstance(param_t, MaybeType) and isinstance(arg_t, MaybeType):
                        unify(param_t.element, arg_t.element)
                    elif isinstance(param_t, ResultType) and isinstance(arg_t, ResultType):
                        unify(param_t.ok_type, arg_t.ok_type)
                        unify(param_t.err_type, arg_t.err_type)
                    elif isinstance(param_t, RuneType) and isinstance(arg_t, RuneType):
                        if param_t.type_args and arg_t.type_args:
                            for p_a, a_a in zip(param_t.type_args, arg_t.type_args):
                                unify(p_a, a_a)

                for i, (arg_t, _) in enumerate(pos_args):
                    if i < len(fn_type.params):
                        unify(fn_type.params[i][1], arg_t)
                    elif has_variadic:
                        unify(fn_type.params[-1][1], arg_t)

                param_dict = {p[0]: p[1] for p in fn_type.params if p[0]}
                for n_name, (arg_t, _) in named_args:
                    if n_name in param_dict:
                        unify(param_dict[n_name], arg_t)

                unresolved = [tp for tp in type_params if tp not in subst_map]
                if unresolved:
                    raise self._make_error(
                        TypeMismatchError,
                        f"Could not infer type parameter(s) {', '.join(unresolved)} for generic function '{fn_name}'",
                        node,
                        code="E0005",
                        help="Ensure arguments provide enough type information to deduce all type parameters.",
                        note="Generic functions require all type parameters to be inferable."
                    )

                def _extract_shard_params_bounds(shard_node: Tree) -> Tuple[List[str], Dict[str, List[str]]]:
                    t_params: List[str] = []
                    b_dict: Dict[str, List[str]] = {}
                    if not isinstance(shard_node, Tree):
                        return t_params, b_dict
                    for ch in shard_node.children:
                        if isinstance(ch, Token) and ch.type == "NAME":
                            t_params.append(str(ch))
                        elif isinstance(ch, Tree) and ch.data == "where_clause":
                            for wb in ch.children:
                                if isinstance(wb, Tree) and wb.data == "where_bound":
                                    tp_n = _node_to_name(wb.children[0])
                                    c_n = _node_to_name(wb.children[1])
                                    b_dict.setdefault(tp_n, []).append(c_n)
                    return t_params, b_dict

                fn_bounds = {}
                if fn_name and fn_name in self.symbols.generic_functions:
                    fn_ast = self.symbols.generic_functions[fn_name][1]
                    for ch in fn_ast.children:
                        if isinstance(ch, Tree) and ch.data == "shard_params":
                            _, fn_bounds = _extract_shard_params_bounds(ch)
                            break

                for tp, arg_t in subst_map.items():
                    for bound in fn_bounds.get(tp, []):
                        if not implements_concept(arg_t, bound, self.symbols):
                            t_display = getattr(arg_t, "name", str(arg_t))
                            raise self._make_error(
                                ConceptBoundNotSatisfiedError,
                                f"Type '{t_display}' does not implement concept '{bound}' required by generic parameter '{tp}'",
                                node,
                                code="E0032",
                                help=f"Bind concept '{bound}' to type '{t_display}' using 'bind {t_display} with {bound}:'.",
                                note=f"Generic function '{fn_name}' requires '{tp}: {bound}'."
                            )

                specialized_fn_type = fn_type.substitute(subst_map)
                mangled_args = "_".join(subst_map[tp].get_mangled_name() for tp in type_params)
                mangled_fn_name = f"{fn_name}_{mangled_args}"

                if fn_name and fn_name in self.symbols.generic_functions:
                    fn_ast = self.symbols.generic_functions[fn_name][1]
                    self.symbols.monomorphized_functions[mangled_fn_name] = (fn_ast, subst_map)

                self.symbols.functions[mangled_fn_name] = specialized_fn_type
                self.symbols.global_scope.define(Symbol(
                    name=mangled_fn_name,
                    type=specialized_fn_type,
                    kind="function"
                ))
                fn_type = specialized_fn_type

            elif method_name and method_self_type is not None:
                receiver_type = method_self_type.target if isinstance(method_self_type, RefType) else method_self_type
                base_tname = receiver_type.name.split("_")[0] if getattr(receiver_type, "type_args", None) else receiver_type.name
                if (base_tname, method_name) in self.symbols.generic_methods:
                    type_params, method_ast = self.symbols.generic_methods[(base_tname, method_name)]
                    if getattr(receiver_type, "type_args", None) and len(receiver_type.type_args) == len(type_params):
                        subst_map = dict(zip(type_params, receiver_type.type_args))
                        specialized_method_type = fn_type.substitute(subst_map)
                        mangled_args = "_".join(t.get_mangled_name() for t in receiver_type.type_args)
                        mangled_method_name = f"{base_tname}_{mangled_args}_{method_name}"
                        self.symbols.monomorphized_methods[mangled_method_name] = (method_ast, subst_map)
                        self.symbols.methods[(receiver_type.name, method_name)] = specialized_method_type
                        fn_type = specialized_method_type

            if has_variadic:
                if total_passed < min_params:
                    raise self._make_error(
                        SemanticError,
                        f"Function expects at least {min_params} arguments, but received {total_passed}",
                        node,
                        code="E0005",
                        help=f"Provide at least {min_params} arguments.",
                        note="Function call argument counts must match signature."
                    )
            else:
                if not (min_params <= total_passed <= total_params) and total_params > 0:
                    if not (self.symbols.has_includes and total_params == 0):
                        raise self._make_error(
                            SemanticError,
                            f"Function expects between {min_params} and {total_params} arguments, but received {total_passed}",
                            node,
                            code="E0005",
                            help=f"Provide between {min_params} and {total_params} arguments.",
                            note="Function call argument counts must match signature."
                        )

            # Special check for ListType.push
            if isinstance(method_self_type, ListType) and method_name == "push":
                arg_t = pos_args[0][0] if pos_args else (named_args[0][1][0] if named_args else None)
                if arg_t is not None and not arg_t.is_compatible(method_self_type.element):
                    elem_name = str(method_self_type.element)
                    got_name = str(arg_t)
                    raise self._make_error(
                        TypeMismatchError,
                        f"List of {elem_name} push expects {elem_name}, got {got_name}",
                        node,
                        code="E0018",
                        help=f"Pass a value of type '{elem_name}' to 'push'.",
                        note=f"List of {elem_name} only accepts {elem_name} elements."
                    )

            # Special check for MapType.put / set / insert
            elif isinstance(method_self_type, MapType) and method_name in ("put", "insert", "set"):
                if len(pos_args) >= 1:
                    k_t = pos_args[0][0]
                    if not k_t.is_compatible(method_self_type.key):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Map of {method_self_type.key} to {method_self_type.value} put key expects {method_self_type.key}, got {k_t}",
                            node,
                            code="E0005",
                            help=f"Provide key of type '{method_self_type.key}'.",
                            note="Map keys must match declared key type."
                        )
                if len(pos_args) >= 2:
                    v_t = pos_args[1][0]
                    if not v_t.is_compatible(method_self_type.value):
                        raise self._make_error(
                            TypeMismatchError,
                            f"Map of {method_self_type.key} to {method_self_type.value} put value expects {method_self_type.value}, got {v_t}",
                            node,
                            code="E0005",
                            help=f"Provide value of type '{method_self_type.value}'.",
                            note="Map values must match declared value type."
                        )

            return fn_type.return_type

        # Maybe and Result unwrapping
        elif rule == "try_expr":
            inner_expr = node.children[0]
            t = self.infer(inner_expr)
            if isinstance(t, ResultType):
                return t.ok_type
            elif isinstance(t, MaybeType):
                return t.element
            elif isinstance(t, AnyType):
                return AnyType()
            raise self._make_error(
                TypeMismatchError,
                f"'try' requires Result or Maybe type, got '{t}'",
                node,
                code="E0005",
                help="Apply 'try' only to expressions returning Result(...) or maybe T.",
                note="'try' unwraps successful values from error/maybe unions."
            )

        elif rule == "or_else":
            left_type = self.infer(node.children[0])
            right_type = self.infer(node.children[1])
            if isinstance(left_type, MaybeType):
                if not right_type.is_compatible(left_type.element):
                    raise self._make_error(
                        TypeMismatchError,
                        f"'or else' fallback type '{right_type}' incompatible with '{left_type.element}'",
                        node,
                        code="E0005",
                        help=f"Ensure fallback expression has type compatible with '{left_type.element}'.",
                        note="'or else' returns the fallback value when None or Error occurs."
                    )
                return left_type.element
            elif isinstance(left_type, ResultType):
                if not right_type.is_compatible(left_type.ok_type):
                    raise self._make_error(
                        TypeMismatchError,
                        f"'or else' fallback type '{right_type}' incompatible with '{left_type.ok_type}'",
                        node,
                        code="E0005",
                        help=f"Ensure fallback expression has type compatible with '{left_type.ok_type}'.",
                        note="'or else' returns the fallback value when None or Error occurs."
                    )
                return left_type.ok_type
            elif isinstance(left_type, AnyType):
                return right_type
            raise self._make_error(
                TypeMismatchError,
                f"'or else' left operand must be maybe or Result, got '{left_type}'",
                node,
                code="E0005",
                help="Use 'or else' with a maybe T or Result type expression.",
                note="'or else' handles unwrap failures on maybe and Result."
            )

        elif rule == "or_return":
            left_type = self.infer(node.children[0])
            ret_type = self.infer(node.children[1])
            curr_ret = self.symbols.current_return_type()
            if curr_ret and not ret_type.is_compatible(curr_ret) and not ret_type.is_int():
                raise self._make_error(
                    TypeMismatchError,
                    f"'or return' value type '{ret_type}' incompatible with function return type '{curr_ret}'",
                    node,
                    code="E0020",
                    help=f"Ensure 'or return' expression matches function return type '{curr_ret}'.",
                    note="'or return' returns early from the function on failure."
                )
            if isinstance(left_type, MaybeType):
                return left_type.element
            elif isinstance(left_type, ResultType):
                return left_type.ok_type
            return AnyType()

        # Arithmetic and Bitwise
        elif rule in ("add", "sub", "mul", "div", "mod"):
            left_t = self.infer(node.children[0])
            right_t = self.infer(node.children[1])
            if rule == "add" and (left_t.is_string() or right_t.is_string() or isinstance(left_t, AnyType) or isinstance(right_t, AnyType)):
                return STRING_TYPE
            if not left_t.is_numeric() and not isinstance(left_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Arithmetic operator '{rule}' requires numeric type, got '{left_t}'",
                    node,
                    code="E0005",
                    help="Ensure operands are numeric (int, float, etc.).",
                    note="Arithmetic operators only operate on numeric values."
                )
            if not right_t.is_numeric() and not isinstance(right_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Arithmetic operator '{rule}' requires numeric type, got '{right_t}'",
                    node,
                    code="E0005",
                    help="Ensure operands are numeric (int, float, etc.).",
                    note="Arithmetic operators only operate on numeric values."
                )
            if left_t.is_float() or right_t.is_float():
                return FLOAT_TYPE
            return INT_TYPE

        elif rule in ("bitwise_or", "bitwise_and", "bitwise_xor", "shl", "shr"):
            left_t = self.infer(node.children[0])
            right_t = self.infer(node.children[1])
            if not left_t.is_int() and not isinstance(left_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Bitwise operator '{rule}' requires integer type, got '{left_t}'",
                    node,
                    code="E0005",
                    help="Ensure operands are integer types (int, i32, i64).",
                    note="Bitwise operators operate only on integer bit patterns."
                )
            if not right_t.is_int() and not isinstance(right_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Bitwise operator '{rule}' requires integer type, got '{right_t}'",
                    node,
                    code="E0005",
                    help="Ensure operands are integer types (int, i32, i64).",
                    note="Bitwise operators operate only on integer bit patterns."
                )
            return INT_TYPE

        elif rule == "bit_not":
            t = self.infer(node.children[0])
            if not t.is_int() and not isinstance(t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Bitwise not '~' requires integer type, got '{t}'",
                    node,
                    code="E0005",
                    help="Ensure operand is an integer type (int, i32, i64).",
                    note="Bitwise not operates only on integer bit patterns."
                )
            return INT_TYPE

        elif rule == "log_not":
            t = self.infer(node.children[0])
            if not t.is_compatible(BOOL_TYPE) and not isinstance(t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Logical 'not' requires bool type, got '{t}'",
                    node,
                    code="E0005",
                    help="Ensure operand is a boolean expression (bool).",
                    note="Logical not operates only on boolean values."
                )
            return BOOL_TYPE

        elif rule == "neg":
            t = self.infer(node.children[0])
            if not t.is_numeric() and not isinstance(t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"Unary '-' requires numeric type, got '{t}'",
                    node,
                    code="E0005",
                    help="Ensure operand is numeric (int, float, etc.).",
                    note="Unary negation requires a numeric value."
                )
            return t

        # Comparisons
        elif rule in ("eq", "ne", "lt", "le", "gt", "ge"):
            left_t = self.infer(node.children[0])
            right_t = self.infer(node.children[1])
            if rule in ("eq", "ne"):
                if isinstance(left_t, NullType) or isinstance(right_t, NullType):
                    other_t = right_t if isinstance(left_t, NullType) else left_t
                    if isinstance(other_t, NullType):
                        return BOOL_TYPE
                    if isinstance(other_t, (RefType, AnyType, TypeParam)):
                        return BOOL_TYPE
                    if isinstance(other_t, BaseType) and other_t.name in ("opaque", "any"):
                        return BOOL_TYPE
                    if isinstance(other_t, AliasType):
                        curr = other_t
                        while isinstance(curr, AliasType) and curr.target:
                            curr = curr.target
                        if isinstance(curr, (RefType, AnyType, TypeParam)) or (isinstance(curr, BaseType) and curr.name in ("opaque", "any")):
                            return BOOL_TYPE
                    raise self._make_error(
                        TypeMismatchError,
                        f"Cannot compare 'null' with non-pointer type '{other_t}'",
                        node,
                        code="E0005",
                        help="Only references (ref to T) and opaque types can be compared with 'null'.",
                        note="'null' represents a null pointer and can only be compared to pointer/reference types."
                    )
            elif rule in ("lt", "le", "gt", "ge"):
                if isinstance(left_t, NullType) or isinstance(right_t, NullType):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Ordering comparison '{rule}' is not supported for 'null'",
                        node,
                        code="E0005",
                        help="Use '==' or '!=' to compare references with 'null'.",
                        note="'null' only supports equality and inequality comparisons."
                    )
            if not left_t.is_compatible(right_t) and not right_t.is_compatible(left_t):
                if not (left_t.is_numeric() and right_t.is_numeric()):
                    raise self._make_error(
                        TypeMismatchError,
                        f"Comparison '{rule}' on incompatible types: '{left_t}' vs '{right_t}'",
                        node,
                        code="E0005",
                        help=f"Compare values of compatible types, or cast explicitly.",
                        note="Comparisons require compatible operand types."
                    )
            return BOOL_TYPE

        elif rule in ("is_present", "is_not_present"):
            target_t = self.infer(node.children[0])
            return BOOL_TYPE

        elif rule in ("is_false", "is_true"):
            target_t = self.infer(node.children[0])
            if not target_t.is_compatible(BOOL_TYPE) and not isinstance(target_t, AnyType):
                raise self._make_error(
                    TypeMismatchError,
                    f"'is {rule}' check requires bool type, got '{target_t}'",
                    node,
                    code="E0005",
                    help="Ensure operand is a boolean expression.",
                    note="'is true' and 'is false' checks operate on booleans."
                )
            return BOOL_TYPE

        if len(node.children) == 1:
            return self.infer(node.children[0], expected_type)

        return AnyType()

    def _check_string_interpolation(self, text: str, line: Optional[int], col: Optional[int], node: Any = None):
        """Checks that variables interpolated inside {var} exist in symbol table.

        Args:
            text: Raw string literal text.
            line: Source line number.
            col: Source column number.
            node: AST node for diagnostics.
        """
        matches = re.findall(r'\{([^}]+)\}', text)
        for var_name in matches:
            var_name = var_name.strip()
            if var_name:
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name):
                    sym = self.symbols.lookup(var_name)
                    if sym is None:
                        if var_name.isupper() and self.symbols.has_includes:
                            continue
                        raise self._make_error(
                            UndefinedIdentifierError,
                            f"Undefined variable '{var_name}' in string interpolation",
                            node,
                            line=line,
                            col=col,
                            code="E0019",
                            help=f"Ensure variable '{var_name}' is declared before interpolating it in string.",
                            note="String interpolation expressions evaluate variables in current scope."
                        )

    def _validate_addressable(self, node: Any):
        """Validates that a node is addressable for 'sigil of'.

        Args:
            node: Node operand to 'sigil of'.
        """
        line, col = self._get_loc(node)
        if isinstance(node, Token):
            if node.type in ("INT", "FLOAT", "STRING"):
                raise self._make_error(
                    SemanticError,
                    "Cannot take 'sigil of' a literal value",
                    node,
                    code="E0008",
                    help="Take 'sigil of' an addressable variable (e.g. 'sigil of my_var').",
                    note="Pointers can only reference addressable lvalues in memory."
                )
        if isinstance(node, Tree):
            if node.data in ("int_lit", "float_lit", "string_lit", "true_lit", "false_lit", "null_lit", "maybe_none"):
                raise self._make_error(
                    SemanticError,
                    "Cannot take 'sigil of' a literal or temporary expression",
                    node,
                    code="E0008",
                    help="Take 'sigil of' an addressable variable (e.g. 'sigil of my_var').",
                    note="Pointers can only reference addressable lvalues in memory."
                )
            if node.data == "var_ref":
                name = str(node.children[0])
                sym = self.symbols.lookup(name)
                if sym and sym.kind == "const":
                    raise self._make_error(
                        SemanticError,
                        f"Cannot take 'sigil of' constant '{name}'",
                        node,
                        code="E0008",
                        help="Pointers cannot be taken of 'const' items.",
                        note="Constants do not have mutable addresses in memory."
                    )

    def _resolve_call_target(self, target_node: Tree) -> Tuple[Optional[FnType], Optional[Type]]:
        """Resolves target of calling statement/expr to (FnType, method_self_type).

        Args:
            target_node: AST target node (with_target or normal_target).

        Returns:
            Tuple of resolved FnType and optional receiver Type.
        """
        line, col = self._get_loc(target_node)
        rule = target_node.data

        if rule == "with_target":
            method_name = str(target_node.children[0])
            with_type = self.symbols.current_with_type()
            if with_type is None:
                raise self._make_error(
                    SemanticError,
                    f"Method call '.{method_name}' used outside 'with' statement",
                    target_node,
                    code="E0009",
                    help=f"Wrap method call in a 'with' block (e.g. 'with my_obj:') or call explicitly 'calling my_obj.{method_name}'.",
                    note="Leading dot method calls require an active 'with' context."
                )

            base_with_type = with_type
            while isinstance(base_with_type, (RefType, AliasType)):
                base_with_type = base_with_type.target

            t_name = getattr(base_with_type, "name", str(base_with_type))
            if (t_name, method_name) in self.symbols.methods:
                return self.symbols.methods[(t_name, method_name)], with_type

            m_key = f"{t_name}_{method_name}"
            if m_key in self.symbols.functions:
                return self.symbols.functions[m_key], with_type

            if isinstance(with_type, ListType) and method_name in ("push", "pop", "clear"):
                if method_name == "push":
                    return FnType(params=[("item", with_type.element)], return_type=VOID_TYPE), with_type
                elif method_name == "pop":
                    return FnType(params=[], return_type=with_type.element), with_type
                elif method_name == "clear":
                    return FnType(params=[], return_type=VOID_TYPE), with_type

            if isinstance(with_type, MapType) and method_name in ("put", "insert", "set", "get", "remove"):
                if method_name in ("put", "insert", "set"):
                    return FnType(params=[("key", with_type.key), ("value", with_type.value)], return_type=VOID_TYPE), with_type
                elif method_name == "get":
                    return FnType(params=[("key", with_type.key)], return_type=with_type.value), with_type
                elif method_name == "remove":
                    return FnType(params=[("key", with_type.key)], return_type=VOID_TYPE), with_type

            if self.symbols.has_includes:
                return FnType(params=[], return_type=VOID_TYPE), with_type

            raise self._make_error(
                UndefinedIdentifierError,
                f"Type '{with_type}' has no enchanting method '{method_name}'",
                target_node,
                code="E0004",
                help=f"Declare 'weave {method_name}' inside 'enchanting {with_type}:'.",
                note=f"Type '{with_type}' does not define method '{method_name}'."
            )

        elif rule == "normal_target":
            first = target_node.children[0]
            if len(target_node.children) == 1 and isinstance(first, (Token, str)):
                fn_name = str(first)
                if fn_name == "print":
                    return FnType(params=[("msg", AnyType())], return_type=VOID_TYPE), None
                sym = self.symbols.lookup(fn_name)
                if sym is not None:
                    if isinstance(sym.type, FnType):
                        return sym.type, None
                    elif sym.kind in ("function", "declare"):
                        if isinstance(sym.type, FnType):
                            return sym.type, None
                        return FnType(params=[], return_type=sym.type), None
                if fn_name in self.symbols.functions:
                    return self.symbols.functions[fn_name], None
                if fn_name in self.symbols.generic_functions:
                    return self.symbols.functions.get(fn_name), None
                if self.symbols.has_includes:
                    return FnType(params=[], return_type=VOID_TYPE), None
                raise self._make_error(
                    UndefinedIdentifierError,
                    f"Undefined function '{fn_name}'",
                    target_node,
                    code="E0004",
                    help=f"Declare or define 'weave {fn_name}' before calling it.",
                    note="All functions must be declared or defined before call."
                )

            if len(target_node.children) >= 2:
                obj_name = str(target_node.children[0])
                method_acc = target_node.children[1]
                if isinstance(method_acc, Tree) and method_acc.data == "dot_access":
                    m_name = str(method_acc.children[0])
                    obj_sym = self.symbols.lookup(obj_name)
                    if obj_sym is not None and obj_sym.kind not in ("rune", "echo", "omen", "seal", "alias", "concept", "type"):
                        if obj_sym.kind == "import":
                            # Module member calls (e.g. 'calling archivum.write_file')
                            # resolve against the import's module_scope first:
                            # that is where the real FnType signature lives. Then
                            # fall back to the prefixed function registry names
                            # registered during import collection. Never silently
                            # guess 'void' when the member simply does not exist
                            # (that used to turn every missed member into void and
                            # produce spurious E0020 return-type mismatches).
                            scope = getattr(obj_sym, "module_scope", None)
                            if scope is not None:
                                mem_sym = scope.symbols.get(m_name)
                                if mem_sym is not None:
                                    m_type = getattr(mem_sym, "type", None)
                                    if isinstance(m_type, FnType):
                                        return m_type, None
                                    if getattr(mem_sym, "kind", "") in ("function", "declare") and m_type is not None:
                                        return FnType(params=[], return_type=m_type), None
                            for cand_name in (f"{obj_name}_{m_name}", m_name):
                                fn_t = self.symbols.functions.get(cand_name)
                                if fn_t is not None:
                                    return fn_t, None
                                s = self.symbols.lookup(cand_name)
                                if s is not None and isinstance(getattr(s, "type", None), FnType):
                                    return s.type, None
                            if self.symbols.has_includes:
                                return FnType(params=[], return_type=VOID_TYPE), None
                            raise self._make_error(
                                UndefinedIdentifierError,
                                f"Module '{obj_name}' has no exported member '{m_name}'",
                                target_node,
                                code="E0004",
                                help=f"Check the member name or import the module that exports '{m_name}'.",
                                note="Module member calls must resolve to a declared weave/declare in that module."
                            )
                        obj_type = obj_sym.type
                        if isinstance(obj_type, TypeParam):
                            for bound in obj_type.bounds:
                                concept_obj = self.symbols.lookup_concept(bound)
                                if concept_obj and m_name in concept_obj.methods:
                                    return concept_obj.methods[m_name], obj_type

                        if isinstance(obj_type, RefType):
                            t_name = getattr(obj_type.target, "name", str(obj_type.target))
                        else:
                            t_name = getattr(obj_type, "name", str(obj_type))
                        if (t_name, m_name) in self.symbols.methods:
                            m_fn = self.symbols.methods[(t_name, m_name)]
                            if getattr(m_fn, "is_ritual", False):
                                raise self._make_error(
                                    InvalidRitualCallError,
                                    f"Method '{m_name}' is a 'ritual' (static) method and must be called on the type '{t_name}', not an instance",
                                    target_node,
                                    code="E0034",
                                    help=f"Call as '{t_name}.{m_name}(...)' instead.",
                                    note="Ritual methods cannot be called on instances."
                                )
                            return m_fn, obj_type
                        if f"{t_name}_{m_name}" in self.symbols.functions:
                            return self.symbols.functions[f"{t_name}_{m_name}"], obj_type

                        base_tname = t_name.split("_")[0]
                        if (base_tname, m_name) in self.symbols.generic_methods:
                            type_params, method_ast = self.symbols.generic_methods[(base_tname, m_name)]
                            gm_type = self.symbols.methods.get((base_tname, m_name))
                            if not gm_type:
                                for (k_t, k_m), m_fn in self.symbols.methods.items():
                                    if k_t.split("_")[0] == base_tname and k_m == m_name:
                                        gm_type = m_fn
                                        break
                            if gm_type:
                                rec_type = obj_type.target if isinstance(obj_type, RefType) else obj_type
                                t_args = getattr(rec_type, "type_args", [])
                                if not t_args:
                                    sym_t = self.symbols.lookup_type(rec_type.name)
                                    if sym_t:
                                        t_args = getattr(sym_t, "type_args", [])
                                if not t_args and "_" in rec_type.name:
                                    parts = rec_type.name.split("_")[1:]
                                    t_args = [self.symbols.lookup_type(p) or BaseType(p) for p in parts]
                                if t_args and len(t_args) == len(type_params):
                                    subst_map = dict(zip(type_params, t_args))
                                    gm_type = gm_type.substitute(subst_map)
                                return gm_type, obj_type

                        # Concept method resolution on instance
                        for (b_type, b_concept), b_methods in self.symbols.concept_bindings.items():
                            if (b_type == t_name or b_type == base_tname) and m_name in b_methods:
                                m_fn = b_methods[m_name]
                                if getattr(m_fn, "is_ritual", False):
                                    raise self._make_error(
                                        InvalidRitualCallError,
                                        f"Method '{m_name}' is a 'ritual' (static) method and must be called on the type '{t_name}', not an instance",
                                        target_node,
                                        code="E0034",
                                        help=f"Call as '{t_name}.{m_name}(...)' instead.",
                                        note="Ritual methods cannot be called on instances."
                                    )
                                return m_fn, obj_type

                        if isinstance(obj_type, ListType):
                            if m_name in ("push", "append"):
                                return FnType(params=[("item", obj_type.element)], return_type=VOID_TYPE), obj_type
                            elif m_name == "pop":
                                return FnType(params=[], return_type=obj_type.element), obj_type
                            elif m_name == "clear":
                                return FnType(params=[], return_type=VOID_TYPE), obj_type
                            elif m_name == "len":
                                return FnType(params=[], return_type=INT_TYPE), obj_type
                            elif m_name == "is_empty":
                                return FnType(params=[], return_type=BOOL_TYPE), obj_type
                            elif m_name == "contains":
                                return FnType(params=[("item", obj_type.element)], return_type=BOOL_TYPE), obj_type
                            elif m_name == "index_of":
                                return FnType(params=[("item", obj_type.element)], return_type=INT_TYPE), obj_type
                            elif m_name == "at":
                                return FnType(params=[("index", INT_TYPE)], return_type=obj_type.element), obj_type
                        if isinstance(obj_type, MapType):
                            if m_name in ("put", "insert", "set"):
                                return FnType(params=[("key", obj_type.key), ("value", obj_type.value)], return_type=VOID_TYPE), obj_type
                            elif m_name == "get":
                                return FnType(params=[("key", obj_type.key)], return_type=obj_type.value), obj_type
                            elif m_name == "remove":
                                return FnType(params=[("key", obj_type.key)], return_type=BOOL_TYPE), obj_type
                            elif m_name in ("contains", "contains_key", "has"):
                                return FnType(params=[("key", obj_type.key)], return_type=BOOL_TYPE), obj_type
                            elif m_name == "len":
                                return FnType(params=[], return_type=INT_TYPE), obj_type
                            elif m_name == "clear":
                                return FnType(params=[], return_type=VOID_TYPE), obj_type
                            elif m_name == "is_empty":
                                return FnType(params=[], return_type=BOOL_TYPE), obj_type
                        if self.symbols.has_includes:
                            return FnType(params=[], return_type=VOID_TYPE), obj_type
                        raise self._make_error(
                            UndefinedIdentifierError,
                            f"Type '{obj_type}' has no method '{m_name}'",
                            target_node,
                            code="E0004",
                            help=f"Declare 'weave {m_name}' inside 'enchanting {obj_type}:'.",
                            note=f"Type '{obj_type}' does not define method '{m_name}'."
                        )
                    else:
                        # Static / ritual method call on type name (e.g. Vec2.zero)
                        type_resolved = self.symbols.lookup_type(obj_name)
                        if type_resolved is not None or obj_name in self.symbols.runes or obj_name in self.symbols.seals or obj_name in self.symbols.concepts:
                            if (obj_name, m_name) in self.symbols.methods:
                                m_fn = self.symbols.methods[(obj_name, m_name)]
                                return m_fn, None
                            if f"{obj_name}_{m_name}" in self.symbols.functions:
                                return self.symbols.functions[f"{obj_name}_{m_name}"], None
                            for (b_type, b_concept), b_methods in self.symbols.concept_bindings.items():
                                if b_type == obj_name and m_name in b_methods:
                                    return b_methods[m_name], None
                            raise self._make_error(
                                UndefinedIdentifierError,
                                f"Type '{obj_name}' has no ritual method '{m_name}'",
                                target_node,
                                code="E0004",
                                help=f"Declare 'weave ritual {m_name}' inside 'enchanting {obj_name}:'.",
                                note=f"Type '{obj_name}' does not define ritual method '{m_name}'."
                            )
        return None, None

    def _extract_shard_params_bounds(self, shard_node: Tree) -> Tuple[List[str], Dict[str, List[str]]]:
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
                        t_param_node = wb.children[0]
                        t_param_name = str(t_param_node.children[0]) if isinstance(t_param_node, Tree) else str(t_param_node)
                        concept_node = wb.children[1]
                        concept_name = str(concept_node.children[0]) if isinstance(concept_node, Tree) else str(concept_node)
                        bounds.setdefault(t_param_name, []).append(concept_name)
        return type_params, bounds
