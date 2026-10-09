"""PenguScript type -> C99 type mapping and the array helpers.

Part of :mod:`pengu_parser.pengu_codegen`; see
:class:`~pengu_parser.pengu_codegen.main.PenguCodegen` for the assembled
generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    Any,
    ArrayType,
    BaseType,
    ConceptType,
    EchoType,
    FnType,
    FrozenType,
    List,
    ListType,
    ManyType,
    MapType,
    MaybeType,
    TupleType,
    NullType,
    OmenType,
    Optional,
    RangeType,
    RefType,
    ResultType,
    RuneType,
    SealType,
    SemanticError,
    SliceType,
    Tuple,
    Type,
)
# `restrict` spelling is a mutable process-wide setting: read it through the
# module so `set_restrict_keyword()` takes effect after this module is imported.
from . import attributes as _attributes

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
            elif name == "isize":
                # `ssize_t` was listed here but the grammar's `base_type` does not
                # produce it, so the arm was unreachable (Phase 2 item 2.10). Use
                # `isize`, which is the supported pointer-sized signed type.
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

        elif isinstance(t, TupleType):
            # Synthetic rune registered by the code generator; the struct
            # definition itself is emitted by the ordinary rune emitter.
            return t.c_name()
        elif isinstance(t, MaybeType):
            return "PenguMaybe"

        elif isinstance(t, ResultType):
            return "PenguResult"

        elif isinstance(t, FnType):
            return CTypeMapper.to_c_decl(t, "")

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
            param_strs = [CTypeMapper.to_c_type(p[1]) for p in t.params] or ["void"]
            inner_decl = f"(*{ident})({', '.join(param_strs)})" if ident else f"(*)({', '.join(param_strs)})"
            if isinstance(t.return_type, FnType):
                return CTypeMapper.to_c_decl(t.return_type, inner_decl)
            ret_str = CTypeMapper.to_c_type(t.return_type)
            return f"{ret_str} {inner_decl}".strip()
        if isinstance(t, RefType) and isinstance(t.target, FnType):
            # 'ref to weave …' is a function pointer, not a pointer to one.
            return CTypeMapper.to_c_decl(t.target, ident, const=const, restrict=restrict)
        if isinstance(t, RefType) and isinstance(t.target, ArrayType):
            curr = t.target
            dims = []
            while isinstance(curr, ArrayType):
                dims.append(curr.size)
                curr = curr.element
            if isinstance(curr, FnType):
                dims_str = "".join(f"[{d}]" for d in dims)
                inner_ident = f"(*{ident}){dims_str}" if ident else f"(*){dims_str}"
                return CTypeMapper.to_c_decl(curr, inner_ident)
            dims, base_c = get_array_dims_and_base(t.target)
            dims_str = "".join(f"[{d}]" for d in dims)
            const_prefix = "const " if const else ""
            ptr_qual = f" {_attributes._RESTRICT_KW} " if restrict else " "
            return f"{const_prefix}{base_c} (*{ptr_qual}{ident}){dims_str}".strip() if ident else f"{const_prefix}{base_c} (*){dims_str}"
        if isinstance(t, RefType) and restrict and ident:
            target_str = CTypeMapper.to_c_type(t.target)
            return f"{target_str}* {_attributes._RESTRICT_KW} {ident}"
        if isinstance(t, ArrayType):
            curr = t
            dims = []
            while isinstance(curr, ArrayType):
                dims.append(curr.size)
                curr = curr.element
            if isinstance(curr, FnType):
                if len(dims) == 1:
                    inner_ident = f"(*{ident})" if ident else "(*)"
                    return CTypeMapper.to_c_decl(curr, inner_ident)
                else:
                    inner_dims_str = "".join(f"[{d}]" for d in dims[1:])
                    inner_ident = f"(*{ident}){inner_dims_str}" if ident else f"(*){inner_dims_str}"
                    return CTypeMapper.to_c_decl(curr, inner_ident)
            dims, base_c = get_array_dims_and_base(t)
            const_prefix = "const " if const else ""
            if len(dims) == 1:
                ptr_qual = f" {_attributes._RESTRICT_KW}" if restrict else ""
                return f"{const_prefix}{base_c}*{ptr_qual} {ident}".strip() if ident else f"{const_prefix}{base_c}*"
            else:
                inner_dims_str = "".join(f"[{d}]" for d in dims[1:])
                ptr_qual = f" {_attributes._RESTRICT_KW} " if restrict else " "
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
def get_array_base_type(t: ArrayType) -> Type:
    """Returns the innermost non-array element type."""
    curr: Any = t
    while isinstance(curr, ArrayType):
        curr = curr.element
    return curr
def sync_array_sizes(target_t: Any, source_t: Any) -> None:
    """Recursively propagates inferred array dimensions to target array types."""
    if isinstance(target_t, ArrayType) and isinstance(source_t, ArrayType):
        if target_t.size is None and source_t.size is not None:
            target_t.size = source_t.size
        sync_array_sizes(target_t.element, source_t.element)
