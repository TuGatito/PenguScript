from __future__ import annotations
from typing import Dict, FrozenSet, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from lark import Tree, Token


def mangle_type(t: Optional[Type]) -> str:
    """Generates a consistent, C-compatible mangled name for any Type."""
    if t is None:
        return "void"
    if isinstance(t, TypeParam):
        return t.name
    if isinstance(t, BaseType):
        return t.name
    if isinstance(t, RefType):
        return f"ref_{mangle_type(t.target)}"
    if isinstance(t, ArrayType):
        return f"arr_{t.size}_{mangle_type(t.element)}"
    if isinstance(t, SliceType):
        return f"slice_{mangle_type(t.element)}"
    if isinstance(t, ManyType):
        return f"many_{mangle_type(t.element)}"
    if isinstance(t, ListType):
        return f"list_{mangle_type(t.element)}"
    if isinstance(t, MapType):
        return f"map_{mangle_type(t.key)}_{mangle_type(t.value)}"
    if isinstance(t, MaybeType):
        return f"maybe_{mangle_type(t.element)}"
    if isinstance(t, ResultType):
        return f"result_{mangle_type(t.ok_type)}_{mangle_type(t.err_type)}"
    if isinstance(t, (RuneType, EchoType, OmenType, AliasType)):
        if getattr(t, "type_args", []):
            base = t.get_base_name() if hasattr(t, "get_base_name") else (t.name.split("_")[0] if "_" in t.name and not getattr(t, "type_params", []) else t.name)
            args_str = "_".join(mangle_type(a) for a in t.type_args)
            name = f"{base}_{args_str}"
        else:
            name = t.name
        res = name.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
        if len(res) > 255:
            import hashlib
            h = hashlib.sha256(res.encode('utf-8')).hexdigest()[:8]
            res = f"{res[:240]}_{h}"
        return res

    n = getattr(t, "name", str(t))
    res = n.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
    if len(res) > 255:
        import hashlib
        h = hashlib.sha256(res.encode('utf-8')).hexdigest()[:8]
        res = f"{res[:240]}_{h}"
    return res


class Type:
    """Base class for all PenguScript types.

    Provides core type checking operations, compatibility checks, and casting rules.
    """
    name: str = "unknown"

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        """Substitutes TypeParam instances with concrete types from type_map."""
        return self

    def get_mangled_name(self) -> str:
        """Returns C-compatible mangled name for monomorphization."""
        return mangle_type(self)

    def is_compatible(self, other: Type) -> bool:
        """Checks if this type is implicitly compatible with another type without cast.

        Args:
            other: Target type to check compatibility against.

        Returns:
            True if types are compatible without explicit cast, False otherwise.
        """
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(self, AnyType):
            return True
        if isinstance(other, TypeParam) or isinstance(self, TypeParam):
            return True
        if isinstance(other, AliasType):
            return self.is_compatible(other.target)
        if isinstance(self, AliasType):
            return self.target.is_compatible(other)
        if (isinstance(self, BaseType) and self.name.isupper()) or (isinstance(other, BaseType) and other.name.isupper()):
            return True
        return self == other

    def can_cast_to(self, other: Type) -> bool:
        """Checks if this type can be explicitly converted to another type via 'to'.

        Args:
            other: Target type for explicit cast.

        Returns:
            True if explicit conversion is permitted, False otherwise.
        """
        if self.is_compatible(other):
            return True
        if isinstance(other, SealType):
            return self.can_cast_to(other.underlying) or self.is_compatible(other.underlying)
        if isinstance(self, SealType):
            return self.underlying.can_cast_to(other) or self.underlying.is_compatible(other)
        if self.is_numeric() and other.is_numeric():
            return True
        if isinstance(self, RefType) and isinstance(other, RefType):
            return True
        return False

    def is_numeric(self) -> bool:
        """Returns True if type is a numeric primitive (int or float).

        Returns:
            Boolean indicating if type is numeric.
        """
        return False

    def is_int(self) -> bool:
        """Returns True if type is an integer primitive.

        Returns:
            Boolean indicating if type is integer.
        """
        return False

    def is_float(self) -> bool:
        """Returns True if type is a floating point primitive.

        Returns:
            Boolean indicating if type is floating point.
        """
        return False

    def is_string(self) -> bool:
        """Returns True if type is string.

        Returns:
            Boolean indicating if type is string.
        """
        return False

    def is_bool(self) -> bool:
        """Returns True if type is boolean.

        Returns:
            Boolean indicating if type is boolean.
        """
        return False

    def is_iterable(self) -> bool:
        """Returns True if type can be iterated over in loops/comprehensions.

        Returns:
            Boolean indicating if type supports iteration.
        """
        return False

    def element_type(self) -> Optional[Type]:
        """Returns the element type for collections, or None.

        Returns:
            Contained element Type if iterable collection, None otherwise.
        """
        return None

    def __repr__(self) -> str:
        """Returns the string representation for debugging."""
        return self.name

    def __str__(self) -> str:
        """Returns the human-readable type name."""
        return self.name


@dataclass
class TypeParam(Type):
    """Represents a generic type parameter placeholder (e.g. T, U, E)."""
    name: str
    bounds: List[str] = field(default_factory=list)

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return type_map.get(self.name, self)

    def is_compatible(self, other: Type) -> bool:
        """Checks whether a value of this type parameter fits the ``other`` slot.

        A type parameter without bounds is a wildcard (backwards compatible with
        the pre-bounds behaviour).  With bounds, the target must satisfy every
        bound: ``T: Num`` is not a ``string``, but it *is* compatible with an
        unconstrained ``U`` or with an ``AnyType`` placeholder.
        """
        if isinstance(other, (AnyType, TypeParam, NullType)):
            return True
        if isinstance(other, FrozenType):
            return self.is_compatible(other.target)
        if isinstance(other, AliasType):
            return self.is_compatible(other.target)
        if not self.bounds:
            return True
        for b in self.bounds:
            if not type_implements_builtin_concept(other, b):
                return False
        return True

    def can_cast_to(self, other: Type) -> bool:
        return True

    def bounds_are_open(self) -> bool:
        """True when the parameter is explicitly typed as `any`.

        Only `where T: Any` is open. An *unbounded* `shard T` is not: it is
        instantiable with a rune or a `string`, so `a + b` on it has no defined
        C translation and must be rejected with E0049. That is the established
        behaviour of the generic test corpus
        (`tests/test_generics/fail_bounds_missing.pengu` expects exactly this),
        and it is why `Any` exists as a separate, deliberate escape hatch.
        """
        return "Any" in self.bounds

    def grants(self, operator: str) -> bool:
        """True when the declared bounds enable `operator` (concept-table name).

        Replaces the old per-site `is_numeric()` shortcut, which let `Num` and
        `Integrum` satisfy the `Par`/`Ordo` checks and made those two bounds
        inert (Phase 2 item 2.1).
        """
        if self.bounds_are_open():
            return True
        return any(concept_grants(b, operator) for b in self.bounds)

    def is_numeric(self) -> bool:
        # 'Integrum' refines 'Num': integers are numeric.
        return "Num" in self.bounds or "Integrum" in self.bounds

    def is_int(self) -> bool:
        return "Integrum" in self.bounds

    def is_float(self) -> bool:
        return "Num" in self.bounds and "Integrum" not in self.bounds

    def is_string(self) -> bool:
        return "Forma" in self.bounds

    def is_bool(self) -> bool:
        return "Par" in self.bounds and not self.is_numeric()

    def is_iterable(self) -> bool:
        return "Iterabilis" in self.bounds

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, TypeParam) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("typeparam", self.name))


@dataclass
class AnyType(Type):
    """Represents a wildcard type matching any type during inference."""
    name: str = "any"

    def is_compatible(self, other: Type) -> bool:
        """Checks compatibility with wildcard match."""
        return True

    def can_cast_to(self, other: Type) -> bool:
        """Checks cast permission with wildcard match."""
        return True


@dataclass
class NullType(Type):
    """Null pointer literal type (null) compatible only with references, opaque types, and any."""
    name: str = "null"

    def is_compatible(self, other: Type) -> bool:
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, NullType):
            return True
        if isinstance(other, RefType):
            return True
        if isinstance(other, BaseType) and other.name in ("opaque", "any"):
            return True
        if isinstance(other, AliasType):
            return self.is_compatible(other.target)
        return False

    def can_cast_to(self, other: Type) -> bool:
        return self.is_compatible(other)

    def is_pointer(self) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, NullType)

    def __hash__(self) -> int:
        return hash("null")


NULL_TYPE = NullType()


@dataclass
class BaseType(Type):
    """Primitive base type in PenguScript."""
    name: str

    def is_numeric(self) -> bool:
        """Returns True for numeric primitives (integers, chars, bytes, and floats)."""
        return self.is_int() or self.is_float()

    def is_int(self) -> bool:
        """Returns True for integer and character/byte primitives."""
        return self.name in (
            "int", "i32", "i64", "u32", "u64", "char", "byte", "u8", "i8",
            "u16", "i16", "int8", "uint8", "int16", "uint16", "int32", "uint32",
            "int64", "uint64", "usize", "isize", "size_t", "short", "ushort",
            "long", "ulong", "int8_t", "uint8_t", "int16_t", "uint16_t",
            "int32_t", "uint32_t", "int64_t", "uint64_t", "uint"
        )

    def is_float(self) -> bool:
        """Returns True for float primitives (float, f32, f64, double)."""
        return self.name in ("float", "f32", "f64", "double")

    def is_string(self) -> bool:
        """Returns True for string primitive."""
        return self.name == "string"

    def is_bool(self) -> bool:
        """Returns True for bool primitive."""
        return self.name == "bool"

    def is_compatible(self, other: Type) -> bool:
        """Checks strict compatibility for base primitives without implicit numeric conversion."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType):
            return True
        if isinstance(other, TypeParam):
            # A type parameter is a wildcard for the value direction, but only
            # while its *builtin* bounds hold: 'int' cannot flow into 'T: Forma'
            # unless the primitive table says it implements the concept.
            # User-defined concepts are decided by the checker (which has the
            # symbol table), so they stay permissive here.
            for bound in getattr(other, "bounds", []) or []:
                if bound in BUILTIN_CONCEPTS and not type_implements_builtin_concept(self, bound):
                    return False
            return True
        if self.name in ("opaque", "any") and isinstance(other, NullType):
            return True
        if isinstance(other, AliasType):
            return self.is_compatible(other.target)
        if isinstance(other, OmenType) and other.is_string_valued and self.name == "string":
            return True
        if isinstance(other, BaseType):
            if self.name == other.name:
                return True
            if self.name.isupper() or other.name.isupper():
                return True
            if self.is_int() and other.is_int():
                return True
            if self.is_float() and other.is_float():
                return True
        return False

    def can_cast_to(self, other: Type) -> bool:
        """Checks explicit cast conversion rules."""
        if isinstance(other, AnyType):
            return True
        if self.is_compatible(other):
            return True
        if isinstance(other, SealType):
            return self.can_cast_to(other.underlying) or self.is_compatible(other.underlying)
        if isinstance(other, BaseType):
            if self.is_numeric() and other.is_numeric():
                return True
            if other.name == "string":
                return True
            if self.name == "string" and other.is_numeric():
                return True
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on primitive name."""
        if isinstance(other, BaseType):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        """Returns hash value of primitive name."""
        return hash(self.name)


INT_TYPE = BaseType("int")
I32_TYPE = BaseType("i32")
I64_TYPE = BaseType("i64")
U32_TYPE = BaseType("u32")
U64_TYPE = BaseType("u64")
CHAR_TYPE = BaseType("char")
BYTE_TYPE = BaseType("byte")
U8_TYPE = BaseType("u8")
I8_TYPE = BaseType("i8")
U16_TYPE = BaseType("u16")
I16_TYPE = BaseType("i16")
USIZE_TYPE = BaseType("usize")
ISIZE_TYPE = BaseType("isize")
FLOAT_TYPE = BaseType("float")
F32_TYPE = BaseType("f32")
F64_TYPE = BaseType("f64")
DOUBLE_TYPE = BaseType("double")
BOOL_TYPE = BaseType("bool")
STRING_TYPE = BaseType("string")
VOID_TYPE = BaseType("void")
ERROR_TYPE = BaseType("error")
OPAQUE_TYPE = BaseType("opaque")


def _is_frozen_target(t: Type) -> bool:
    """Reports whether a type is frozen-qualified (looking through aliases)."""
    while isinstance(t, AliasType) and getattr(t, "target", None) is not None:
        t = t.target
    return isinstance(t, FrozenType)


def _same_pointee(a: Type, b: Type) -> bool:
    """Checks whether two pointer target types are strictly compatible.

    Pointees must match strictly (or through typedef aliases):
    - a == b
    - Exception: 'char' <-> 'byte' (and vice versa) for C byte buffer interop.
    - Rejects disparate numeric types (e.g. i32 vs char, u8 vs char, f32 vs f64).
    """
    while isinstance(a, (AliasType, FrozenType)) and getattr(a, "target", None) is not None:
        a = a.target
    while isinstance(b, (AliasType, FrozenType)) and getattr(b, "target", None) is not None:
        b = b.target

    if isinstance(a, (AnyType, TypeParam)) or isinstance(b, (AnyType, TypeParam)):
        return True

    if isinstance(a, RefType) and isinstance(b, RefType):
        if _is_frozen_target(a.target) != _is_frozen_target(b.target):
            return False
        return _same_pointee(a.target, b.target)

    if a == b:
        return True

    if isinstance(a, BaseType) and isinstance(b, BaseType):
        # C byte buffer interoperability exception: char <-> byte
        if (a.name == "char" and b.name == "byte") or (a.name == "byte" and b.name == "char"):
            return True

    return False


def _is_void_pointer_target(target: Type) -> bool:
    """Reports whether a pointer target is the wildcard ``void`` or ``opaque``.

    Both ``ref to void`` (C ``void*``) and ``ref to frozen void`` (C
    ``const void*``), as well as ``ref to opaque``, accept a pointer to any
    object type, so they are checked together whenever two reference types are compared.

    Args:
        target: The pointee type of a :class:`RefType`.

    Returns:
        True when the target is ``void``, ``opaque``, or their ``frozen`` variants.
    """
    if isinstance(target, AliasType):
        return _is_void_pointer_target(target.target)
    if isinstance(target, FrozenType):
        return _is_void_pointer_target(target.target)
    return isinstance(target, BaseType) and target.name in ("void", "opaque")


@dataclass
class RefType(Type):
    """Pointer reference type in PenguScript (ref to T)."""
    target: Type

    @property
    def name(self) -> str:
        """Returns formatted reference type string."""
        return f"ref to {self.target}"

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return RefType(target=self.target.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"ref_{self.target.get_mangled_name()}"

    def is_compatible(self, other: Type) -> bool:
        """Checks reference compatibility with strict pointee typing and const-correctness."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, NullType):
            return True
        if isinstance(other, AliasType):
            return self.is_compatible(other.target)
        if isinstance(other, BaseType) and other.name == "opaque":
            # Widening upcast to the opaque pointer type. This loses no
            # information and cannot truncate -- it is the same conversion C
            # performs implicitly for any object pointer assigned to void*, and
            # the size is a pointer either way. Requiring `transmute` here meant
            # the stdlib had to write an *unsafe* cast to express a safe
            # conversion, which is what made W0001 noisy (Phase 2 §3.8.3).
            return True
        if isinstance(other, RefType):
            # Directional frozen check:
            # ref to frozen T can NEVER flow into ref to mutable T (including mutable void*).
            self_frozen = _is_frozen_target(self.target)
            other_frozen = _is_frozen_target(other.target)
            if self_frozen and not other_frozen:
                return False

            # C treats 'void*' (or 'const void*' if frozen) as the catch-all object
            # pointer: any 'T*' converts to either of them subject to const-correctness.
            if _is_void_pointer_target(self.target) or _is_void_pointer_target(other.target):
                return True

            # Strict pointee check: pointees must match strictly (or char <-> byte exception).
            return _same_pointee(self.target, other.target)
        if isinstance(other, FnType) and isinstance(self.target, FnType):
            # 'ref to weave …' also accepts a bare function value.
            return self.target.is_compatible(other)
        return False

    def can_cast_to(self, other: Type) -> bool:
        """Checks reference cast conversion."""
        if isinstance(other, RefType):
            return True
        return super().can_cast_to(other)

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on reference target type."""
        return isinstance(other, RefType) and self.target == other.target

    def __hash__(self) -> int:
        """Returns hash of reference."""
        return hash(("ref", self.target))


class FrozenType(Type):
    """Read-only qualification of a type: PenguScript's ``frozen T``.

    It is 1:1 with C's ``const``: the value (or pointee) cannot be written
    through this view. ``frozen T`` has the same size and layout as ``T`` and is
    usable as ``T`` in expressions; only assignment is restricted, and it is
    restricted in exactly one direction — a mutable value flows into ``frozen``
    (like C), while ``frozen`` does not flow back into mutable.

    ``frozen ref to T`` is sugar: :func:`ast_to_type` normalises it to
    ``ref to frozen T`` (C ``const T*``), so this class never wraps a ``RefType``
    coming from parsing. It is orthogonal to ``let``/``var``, which qualify the
    *name* (C ``T* const``) rather than the pointee.
    """

    def __init__(self, target: Type):
        """Initializes the qualification around ``target``.

        Args:
            target: The qualified (read-only) type.
        """
        self.target = target

    @property
    def name(self) -> str:
        """Returns the human readable spelling."""
        return f"frozen {self.target}"

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        """Substitutes type parameters inside the qualified type."""
        return FrozenType(target=self.target.substitute(type_map))

    def get_mangled_name(self) -> str:
        """Returns the mangled name used for monomorphization."""
        return f"frozen_{self.target.get_mangled_name()}"

    def is_compatible(self, other: Type) -> bool:
        """Checks assignability of a frozen value.

        Only ``frozen T`` (and anything acceptable to ``T``) is assignable:
        dropping the qualification is an error, matching C's `const` rules.
        """
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, AliasType):
            return self.is_compatible(other.target)
        if isinstance(other, FrozenType):
            return self.target.is_compatible(other.target)
        return False

    def can_cast_to(self, other: Type) -> bool:
        """Explicit casts are decided by the qualified type."""
        return self.target.can_cast_to(other)

    def is_numeric(self) -> bool:
        """Delegates to the qualified type."""
        return self.target.is_numeric()

    def is_int(self) -> bool:
        """Delegates to the qualified type."""
        return self.target.is_int()

    def is_float(self) -> bool:
        """Delegates to the qualified type."""
        return self.target.is_float()

    def is_string(self) -> bool:
        """Delegates to the qualified type."""
        return self.target.is_string()

    def is_bool(self) -> bool:
        """Delegates to the qualified type."""
        return self.target.is_bool()

    def is_iterable(self) -> bool:
        """Delegates to the qualified type."""
        return self.target.is_iterable()

    def element_type(self) -> Optional[Type]:
        """Delegates to the qualified type."""
        return self.target.element_type()

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on the qualified type ('frozen int' != 'int')."""
        return isinstance(other, FrozenType) and self.target == other.target

    def __hash__(self) -> int:
        """Returns hash of the qualification."""
        return hash(("frozen", self.target))


@dataclass
class ArrayType(Type):
    """Fixed-size stack/heap array type (array of T with size N)."""
    element: Type
    size: Optional[Any] = None

    @property
    def name(self) -> str:
        """Returns formatted array type string."""
        if self.size is not None:
            return f"array of {self.element} with size {self.size}"
        return f"array of {self.element}"

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return ArrayType(element=self.element.substitute(type_map), size=self.size)

    def get_mangled_name(self) -> str:
        return f"array_{self.element.get_mangled_name()}"

    def is_iterable(self) -> bool:
        """Arrays are iterable collections."""
        return True

    def element_type(self) -> Optional[Type]:
        """Returns contained element type."""
        return self.element

    def is_compatible(self, other: Type) -> bool:
        """Checks array element compatibility."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, ArrayType):
            if self.size is not None and other.size is not None and self.size != other.size:
                return False
            return self.element.is_compatible(other.element)
        if isinstance(other, RefType):
            # C array-to-pointer decay: 'array of T' is usable where a pointer
            # is expected (e.g. 'calling qsort with xs, …').
            target = other.target
            while isinstance(target, AliasType) and getattr(target, "target", None) is not None:
                target = target.target
            if _is_void_pointer_target(target):
                return True
            return _same_pointee(self.element, target)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on array element type and size."""
        return (
            isinstance(other, ArrayType)
            and self.element == other.element
            and self.size == other.size
        )

    def __hash__(self) -> int:
        """Returns hash of array type."""
        return hash(("array", self.element, self.size))


@dataclass
class RangeType(Type):
    """Integer range type (e.g. 0 to 2 or 0..2)."""
    element: Type = field(default_factory=lambda: INT_TYPE)
    start_val: Optional[Any] = None
    end_val: Optional[Any] = None

    @property
    def name(self) -> str:
        return f"range of {self.element}"

    def is_iterable(self) -> bool:
        return True

    def element_type(self) -> Optional[Type]:
        return self.element

    def is_compatible(self, other: Type) -> bool:
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, (AnyType, TypeParam)):
            return True
        if isinstance(other, RangeType):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, RangeType) and self.element == other.element

    def __hash__(self) -> int:
        return hash(("range", self.element))


@dataclass
class SliceType(Type):

    """Fat-pointer view into contiguous elements (slice of T)."""
    element: Type

    @property
    def name(self) -> str:
        """Returns formatted slice type string."""
        return f"slice of {self.element}"

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return SliceType(element=self.element.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"slice_{self.element.get_mangled_name()}"

    def is_iterable(self) -> bool:
        """Slices are iterable collections."""
        return True

    def element_type(self) -> Optional[Type]:
        """Returns contained element type."""
        return self.element

    def is_compatible(self, other: Type) -> bool:
        """Checks slice compatibility with slices, many types, and arrays."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, (SliceType, ManyType)):
            return self.element.is_compatible(other.element)
        if isinstance(other, ArrayType):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on slice element type."""
        return isinstance(other, (SliceType, ManyType)) and self.element == other.element

    def __hash__(self) -> int:
        """Returns hash of slice type."""
        return hash(("slice", self.element))


@dataclass
class ManyType(Type):
    """Variadic parameter type (many T), behaving as a slice of T."""
    element: Type

    @property
    def name(self) -> str:
        """Returns formatted variadic many type string."""
        return f"many {self.element}"

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return ManyType(element=self.element.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"many_{self.element.get_mangled_name()}"

    def is_iterable(self) -> bool:
        """Variadic many parameters are iterable collections (like slices)."""
        return True

    def element_type(self) -> Optional[Type]:
        """Returns contained element type."""
        return self.element

    def is_compatible(self, other: Type) -> bool:
        """Checks compatibility with ManyType, SliceType, ArrayType."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, (ManyType, SliceType, ArrayType)):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on element type."""
        return isinstance(other, (ManyType, SliceType)) and self.element == other.element

    def __hash__(self) -> int:
        """Returns hash of many type."""
        return hash(("many", self.element))


@dataclass
class CVarArgsType(Type):
    """C variadic parameter marker (...) in declare statements."""

    @property
    def name(self) -> str:
        return "..."

    def __str__(self) -> str:
        return "..."

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return self

    def get_mangled_name(self) -> str:
        return "varargs"

    def is_compatible(self, other: Type) -> bool:
        return True

    def can_cast_to(self, other: Type) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CVarArgsType)

    def __hash__(self) -> int:
        return hash("CVarArgsType")


@dataclass
class ListType(Type):
    """Dynamic growable list type (list of T with capacity C)."""
    element: Type

    @property
    def name(self) -> str:
        """Returns formatted list type string."""
        return f"list of {self.element}"

    @property
    def type_args(self) -> List[Type]:
        return [self.element]

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return ListType(element=self.element.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"list_{self.element.get_mangled_name()}"

    def is_iterable(self) -> bool:
        """Lists are iterable collections."""
        return True

    def element_type(self) -> Optional[Type]:
        """Returns contained element type."""
        return self.element

    def is_compatible(self, other: Type) -> bool:
        """Checks list element compatibility."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, ListType):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on list element type."""
        return isinstance(other, ListType) and self.element == other.element

    def __hash__(self) -> int:
        """Returns hash of list type."""
        return hash(("list", self.element))


@dataclass
class MapType(Type):
    """Key-value hash map type (map of K to V)."""
    key: Type
    value: Type

    @property
    def name(self) -> str:
        """Returns formatted map type string."""
        return f"map of {self.key} to {self.value}"

    @property
    def type_args(self) -> List[Type]:
        return [self.key, self.value]

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return MapType(key=self.key.substitute(type_map), value=self.value.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"map_{self.key.get_mangled_name()}_{self.value.get_mangled_name()}"

    def is_iterable(self) -> bool:
        """Maps are iterable over their keys."""
        return True

    def element_type(self) -> Optional[Type]:
        """Returns map key type."""
        return self.key

    def is_compatible(self, other: Type) -> bool:
        """Checks map key and value type compatibility."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, MapType):
            return self.key.is_compatible(other.key) and self.value.is_compatible(other.value)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on map key and value types."""
        return isinstance(other, MapType) and self.key == other.key and self.value == other.value

    def __hash__(self) -> int:
        """Returns hash of map type."""
        return hash(("map", self.key, self.value))


@dataclass
class MaybeType(Type):
    """Optional maybe type (maybe T) wrapping a value or none."""
    element: Type

    @property
    def name(self) -> str:
        """Returns formatted maybe type string."""
        return f"maybe {self.element}"

    @property
    def type_args(self) -> List[Type]:
        return [self.element]

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return MaybeType(element=self.element.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"maybe_{self.element.get_mangled_name()}"

    def is_compatible(self, other: Type) -> bool:
        """Checks maybe element compatibility."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, MaybeType):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on maybe element type."""
        return isinstance(other, MaybeType) and self.element == other.element

    def __hash__(self) -> int:
        """Returns hash of maybe type."""
        return hash(("maybe", self.element))


@dataclass
class ResultType(Type):
    """Result union type for error handling (result of T to E)."""
    ok_type: Type
    err_type: Type = field(default_factory=lambda: ERROR_TYPE)

    @property
    def name(self) -> str:
        """Returns formatted result type string."""
        return f"result of {self.ok_type} to {self.err_type}"

    @property
    def type_args(self) -> List[Type]:
        return [self.ok_type, self.err_type]

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return ResultType(ok_type=self.ok_type.substitute(type_map), err_type=self.err_type.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"result_{self.ok_type.get_mangled_name()}_{self.err_type.get_mangled_name()}"

    def is_compatible(self, other: Type) -> bool:
        """Checks ok and error type compatibility."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, ResultType):
            return self.ok_type.is_compatible(other.ok_type) and self.err_type.is_compatible(other.err_type)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on ok and err types."""
        return isinstance(other, ResultType) and self.ok_type == other.ok_type and self.err_type == other.err_type

    def __hash__(self) -> int:
        """Returns hash of result type."""
        return hash(("result", self.ok_type, self.err_type))


@dataclass
class RuneType(Type):
    """Struct data type with named fields and methods."""
    name: str
    fields: Dict[str, Type] = field(default_factory=dict)
    methods: Dict[str, FnType] = field(default_factory=dict)
    type_params: List[str] = field(default_factory=list)
    type_args: List[Type] = field(default_factory=list)
    c_name: Optional[str] = None
    base_name: Optional[str] = None
    derived_concepts: List[str] = field(default_factory=list)
    bounds: Dict[str, List[str]] = field(default_factory=dict)
    attributes: Dict[str, List[Any]] = field(default_factory=dict)
    field_attributes: Dict[str, Dict[str, List[Any]]] = field(default_factory=dict)

    def get_base_name(self) -> str:
        if self.base_name:
            return self.base_name
        if self.type_args and "_" in self.name:
            return self.name.split("_")[0]
        return self.name

    def implements(self, concept_name: str) -> bool:
        return concept_name in self.derived_concepts

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    def get_mangled_name(self) -> str:
        return mangle_type(self)

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        if not type_map or (not self.type_params and not self.type_args):
            return self
        new_fields = {k: v.substitute(type_map) for k, v in self.fields.items()}
        new_methods = dict(self.methods) if hasattr(self, 'methods') else {}
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        base = self.get_base_name()
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return RuneType(name=mangled, fields=new_fields, methods=new_methods, type_params=[], type_args=new_args, base_name=base, derived_concepts=list(self.derived_concepts), bounds=dict(self.bounds))
        return RuneType(name=self.name, fields=new_fields, methods=new_methods, type_params=self.type_params, type_args=new_args, base_name=base, derived_concepts=list(self.derived_concepts), bounds=dict(self.bounds))

    def is_compatible(self, other: Type) -> bool:
        """Checks rune compatibility by nominal type name."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, RuneType):
            if self.name == other.name:
                return True
            if self.type_args and other.type_args and len(self.type_args) == len(other.type_args):
                base_self = self.get_base_name()
                base_other = other.get_base_name()
                return base_self == base_other and all(a1.is_compatible(a2) for a1, a2 in zip(self.type_args, other.type_args))
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on rune name."""
        return isinstance(other, RuneType) and self.name == other.name

    def __hash__(self) -> int:
        """Returns hash of rune name."""
        return hash(("rune", self.name))


@dataclass
class EchoType(Type):
    """Union type with overlapping memory representation."""
    name: str
    fields: Dict[str, Type] = field(default_factory=dict)
    type_params: List[str] = field(default_factory=list)
    type_args: List[Type] = field(default_factory=list)
    c_name: Optional[str] = None
    base_name: Optional[str] = None
    derived_concepts: List[str] = field(default_factory=list)
    bounds: Dict[str, List[str]] = field(default_factory=dict)

    def get_base_name(self) -> str:
        if self.base_name:
            return self.base_name
        if self.type_args and "_" in self.name:
            return self.name.split("_")[0]
        return self.name

    def implements(self, concept_name: str) -> bool:
        return concept_name in self.derived_concepts

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    def get_mangled_name(self) -> str:
        return mangle_type(self)

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        if not type_map:
            return self
        new_fields = {k: v.substitute(type_map) for k, v in self.fields.items()}
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        base_name = self.get_base_name()
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return EchoType(name=mangled, fields=new_fields, type_params=[], type_args=new_args, base_name=base_name, derived_concepts=list(self.derived_concepts), bounds=dict(self.bounds))
        return EchoType(name=self.name, fields=new_fields, type_params=self.type_params, type_args=new_args, base_name=base_name, derived_concepts=list(self.derived_concepts), bounds=dict(self.bounds))

    def is_compatible(self, other: Type) -> bool:
        """Checks echo union compatibility by nominal type name."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, EchoType):
            return self.name == other.name
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on echo union name."""
        return isinstance(other, EchoType) and self.name == other.name

    def __hash__(self) -> int:
        """Returns hash of echo union."""
        return hash(("echo", self.name))


@dataclass
class OmenType(Type):
    """Tagged sum type enum with payload variants."""
    name: str
    variants: Dict[str, Dict[str, Type]] = field(default_factory=dict)
    variant_values: Dict[str, int] = field(default_factory=dict)
    type_params: List[str] = field(default_factory=list)
    type_args: List[Type] = field(default_factory=list)
    c_name: Optional[str] = None
    base_name: Optional[str] = None
    derived_concepts: List[str] = field(default_factory=list)
    bounds: Dict[str, List[str]] = field(default_factory=dict)

    def get_base_name(self) -> str:
        if self.base_name:
            return self.base_name
        if self.type_args and "_" in self.name:
            return self.name.split("_")[0]
        return self.name

    def implements(self, concept_name: str) -> bool:
        return concept_name in self.derived_concepts

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    @property
    def is_algebraic(self) -> bool:
        """Returns True if at least one variant has associated payload fields."""
        return any(bool(fields) for fields in self.variants.values())

    @property
    def is_string_valued(self) -> bool:
        """Returns True if this omen maps its variants to string constants."""
        return any(isinstance(v, str) for v in self.variant_values.values())

    def is_numeric(self) -> bool:
        """Simple traditional enums without payload map to C integers."""
        return not self.is_algebraic and not self.is_string_valued

    def is_int(self) -> bool:
        """Simple traditional enums without payload map to C integers."""
        return not self.is_algebraic and not self.is_string_valued

    def is_string(self) -> bool:
        """String-valued omens behave as string types."""
        return self.is_string_valued

    def get_mangled_name(self) -> str:
        return mangle_type(self)

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        if not type_map:
            return self
        new_variants = {}
        for var_name, v_fields in self.variants.items():
            new_variants[var_name] = {k: v.substitute(type_map) for k, v in v_fields.items()}
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        base_name = self.get_base_name()
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            # A specialization is a fresh concrete type: clear the template's
            # c_name so CTypeMapper emits the mangled specialization name
            # (Status_string), not the generic base (Status).
            return OmenType(name=mangled, variants=new_variants, variant_values=self.variant_values,
                            type_params=[], type_args=new_args, c_name=None, base_name=base_name,
                            derived_concepts=list(self.derived_concepts), bounds=dict(self.bounds))
        return OmenType(name=self.name, variants=new_variants, variant_values=self.variant_values,
                        type_params=self.type_params, type_args=new_args, c_name=self.c_name, base_name=base_name,
                        derived_concepts=list(self.derived_concepts), bounds=dict(self.bounds))

    def is_compatible(self, other: Type) -> bool:
        """Checks omen sum type compatibility by nominal type name."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, OmenType):
            return self.name == other.name
        if isinstance(other, BaseType) and other.name == "string" and self.is_string_valued:
            return True
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on omen enum name."""
        return isinstance(other, OmenType) and self.name == other.name

    def __hash__(self) -> int:
        """Returns hash of omen enum."""
        return hash(("omen", self.name))


@dataclass
class FnType(Type):
    """Function signature type (weave with params into return_type)."""
    params: List[Tuple[Optional[str], Type]] = field(default_factory=list)
    return_type: Type = field(default_factory=lambda: VOID_TYPE)
    default_count: int = 0
    type_params: List[str] = field(default_factory=list)
    type_args: List[Type] = field(default_factory=list)
    is_ritual: bool = False
    attributes: Dict[str, List[Any]] = field(default_factory=dict)

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    def substitute(self, type_map: Dict[str, Type]) -> FnType:
        if not type_map:
            return self
        new_params = [(p_name, p_type.substitute(type_map)) for p_name, p_type in self.params]
        new_ret = self.return_type.substitute(type_map)
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        return FnType(
            params=new_params,
            return_type=new_ret,
            default_count=self.default_count,
            type_params=self.type_params,
            type_args=new_args,
            is_ritual=self.is_ritual
        )

    @property
    def name(self) -> str:
        """Returns formatted function signature string."""
        param_strs = []
        for p_name, p_type in self.params:
            if p_name:
                param_strs.append(f"{p_name} as {p_type}")
            else:
                param_strs.append(str(p_type))
        params_formatted = f" with {', '.join(param_strs)}" if param_strs else ""
        prefix = "ritual " if self.is_ritual else ""
        return f"{prefix}weave{params_formatted} into {self.return_type}"

    def is_compatible(self, other: Type) -> bool:
        """Checks function signature parameter and return type compatibility."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, AliasType):
            # A callback typedef ('alias TraceLogCallback as ref to weave …').
            return self.is_compatible(other.target)
        if isinstance(other, RefType):
            # A function value decays to a function pointer in C, so a bare
            # 'weave … into …' is compatible with a declared
            # 'ref to weave … into …' (how C callback parameters are bound).
            if isinstance(other.target, FnType):
                return self.is_compatible(other.target)
            return False
        if isinstance(other, FnType):
            if len(self.params) != len(other.params):
                return False
            for (_, p1), (_, p2) in zip(self.params, other.params):
                if not p1.is_compatible(p2):
                    return False
            return self.return_type.is_compatible(other.return_type)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on parameter types and return type."""
        if not isinstance(other, FnType):
            return False
        if len(self.params) != len(other.params):
            return False
        for (_, p1), (_, p2) in zip(self.params, other.params):
            if p1 != p2:
                return False
        return self.return_type == other.return_type

    def __hash__(self) -> int:
        """Returns hash of function signature."""
        param_types = tuple(p[1] for p in self.params)
        return hash(("fn", param_types, self.return_type))


@dataclass
class ConceptType(Type):
    """Concept / Trait interface type in PenguScript defining method contracts."""
    name: str = ""
    methods: Dict[str, FnType] = field(default_factory=dict)
    ritual_methods: Set[str] = field(default_factory=set)
    type_params: List[str] = field(default_factory=list)
    type_args: List[Type] = field(default_factory=list)
    c_name: Optional[str] = None

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    def get_method(self, name: str) -> Optional[FnType]:
        return self.methods.get(name)

    def get_ritual_methods(self) -> Dict[str, FnType]:
        return {k: v for k, v in self.methods.items() if k in self.ritual_methods or getattr(v, "is_ritual", False)}

    def get_instance_methods(self) -> Dict[str, FnType]:
        return {k: v for k, v in self.methods.items() if k not in self.ritual_methods and not getattr(v, "is_ritual", False)}

    def substitute(self, type_map: Dict[str, Type]) -> ConceptType:
        if not type_map:
            return self
        new_methods = {k: v.substitute(type_map) for k, v in self.methods.items()}
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        base_name = self.name.split("_")[0] if self.type_args else self.name
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return ConceptType(name=mangled, methods=new_methods, ritual_methods=set(self.ritual_methods), type_params=[], type_args=new_args, c_name=self.c_name)
        return ConceptType(name=self.name, methods=new_methods, ritual_methods=set(self.ritual_methods), type_params=self.type_params, type_args=new_args, c_name=self.c_name)

    def is_compatible(self, other: Type) -> bool:
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, ConceptType):
            return self.name == other.name
        return False

    def can_cast_to(self, other: Type) -> bool:
        return self.is_compatible(other)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, ConceptType) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("concept", self.name))


@dataclass
class SealType(Type):
    """Nominal distinct type (newtype) wrapping an underlying type."""
    name: str = ""
    underlying: Optional[Type] = None
    c_name: Optional[str] = None

    def is_compatible(self, other: Type) -> bool:
        """Strict nominal compatibility: only compatible with same SealType."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, SealType):
            return self.name == other.name
        return False

    def can_cast_to(self, other: Type) -> bool:
        """Explicit cast conversion: allows casting to/from underlying type or compatible types."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, SealType):
            return self.name == other.name or self.underlying.can_cast_to(other.underlying)
        if self.underlying.can_cast_to(other) or self.underlying.is_compatible(other):
            return True
        return False

    def is_numeric(self) -> bool:
        return self.underlying.is_numeric()

    def is_int(self) -> bool:
        return self.underlying.is_int()

    def is_float(self) -> bool:
        return self.underlying.is_float()

    def is_string(self) -> bool:
        return self.underlying.is_string()

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        if not type_map:
            return self
        new_underlying = self.underlying.substitute(type_map)
        return SealType(name=self.name, underlying=new_underlying, c_name=self.c_name)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SealType) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("seal", self.name))


class AliasType(Type):
    """Type alias representing a user-defined alias for an underlying target type."""

    def __init__(self, name: str, target: Type, type_params: Optional[List[str]] = None, type_args: Optional[List[Type]] = None, c_name: Optional[str] = None, base_name: Optional[str] = None):
        """Initializes a new Type alias."""
        self.name = name
        self.target = target
        self.type_params = type_params or []
        self.type_args = type_args or []
        self.c_name = c_name
        self.base_name = base_name

    def get_base_name(self) -> str:
        if self.base_name:
            return self.base_name
        if self.type_args and "_" in self.name:
            return self.name.split("_")[0]
        return self.name

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    def get_mangled_name(self) -> str:
        return mangle_type(self)

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        if not type_map:
            return self
        new_target = self.target.substitute(type_map)
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        base_name = self.get_base_name()
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return AliasType(name=mangled, target=new_target, type_params=[], type_args=new_args, base_name=base_name)
        return AliasType(name=self.name, target=new_target, type_params=self.type_params, type_args=new_args, base_name=base_name)

    def is_compatible(self, other: Type) -> bool:
        """Checks compatibility by alias name or underlying target type."""
        if isinstance(other, FrozenType):
            # A mutable value flows into a read-only view (C allows
            # adding 'const'); the reverse is rejected by FrozenType.
            return self.is_compatible(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, AliasType):
            return self.name == other.name or self.target.is_compatible(other.target)
        return self.target.is_compatible(other)

    def can_cast_to(self, other: Type) -> bool:
        """Checks cast conversion on underlying target type."""
        if isinstance(other, FrozenType):
            return self.can_cast_to(other.target)
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, AliasType):
            return self.name == other.name or self.target.can_cast_to(other.target)
        return self.target.can_cast_to(other)

    def is_numeric(self) -> bool:
        """Checks if target type is numeric."""
        return self.target.is_numeric()

    def is_int(self) -> bool:
        """Checks if target type is integer."""
        return self.target.is_int()

    def is_float(self) -> bool:
        """Checks if target type is floating point."""
        return self.target.is_float()

    def is_string(self) -> bool:
        """Checks if target type is string."""
        return self.target.is_string()

    def is_bool(self) -> bool:
        """Checks if target type is boolean."""
        return self.target.is_bool()

    def is_iterable(self) -> bool:
        """Checks if target type is iterable."""
        return self.target.is_iterable()

    def element_type(self) -> Optional[Type]:
        """Returns element type of target type."""
        return self.target.element_type()

    def __eq__(self, other: Any) -> bool:
        """Checks equality by alias name and target type."""
        if isinstance(other, AliasType):
            return self.name == other.name and self.target == other.target
        return False

    def __hash__(self) -> int:
        """Returns hash of type alias."""
        return hash(("alias", self.name))


BUILTIN_CONCEPTS: Dict[str, ConceptType] = {
    "Num": ConceptType(name="Num", methods={}),
    "Integrum": ConceptType(name="Integrum", methods={}),
    "Par": ConceptType(name="Par", methods={}),
    "Ordo": ConceptType(name="Ordo", methods={}),
    "Vinculum": ConceptType(name="Vinculum", methods={}),
    "Imago": ConceptType(name="Imago", methods={}),
    "Nexus": ConceptType(name="Nexus", methods={}),
    "Forma": ConceptType(name="Forma", methods={}),
    "Iterabilis": ConceptType(name="Iterabilis", methods={}),
    "Donum": ConceptType(name="Donum", methods={}),
}

# ---------------------------------------------------------------------------
# Single source of truth: which concept grants which operators on a type
# parameter.  Phase 2 item 2.1 (AUDIT_1.0.md §3.1 / AUDIT_1.0_FASE2.md §1.1).
#
# Before this table the checks in pengu_infer consulted `TypeParam.is_numeric()`
# *in addition to* the correct bound.  Because `Num` and `Integrum` both satisfy
# `is_numeric()`, the `==` and `<`/`>` checks were short-circuited, so `Par` and
# `Ordo` granted nothing on their own and -- worse -- *adding* a bound could
# remove a capability (`T: Num` accepted `a < b`; `T: Par` rejected it).  The
# bound set was therefore not a monotone chain.
#
# The table below is the chain `Num` -> `Integrum` (integers add the integer-only
# operators) with `Par` and `Ordo` as the two orthogonal comparison concepts.
# This is exactly what LANGUAGE.md documents, and it makes the bound set
# monotone: adding a bound can only add capabilities.
#
# Every enforcement site must consult this table rather than a per-site ad-hoc
# check, so a future operator cannot silently reintroduce the inconsistency.
# ---------------------------------------------------------------------------

#: Operators each concept grants on a bare type parameter.
CONCEPT_OPERATORS: Dict[str, FrozenSet[str]] = {
    # Arithmetic.  Not `%`, `&`, `|`, `^`, `<<`, `>>`, `~`: C has no float
    # modulo/bitwise, so those need `Integrum`.
    "Num": frozenset({"add", "sub", "mul", "div", "neg"}),
    # `Integrum` refines `Num`: an integer bound also satisfies numeric needs.
    "Integrum": frozenset({
        "add", "sub", "mul", "div", "neg",
        "mod", "band", "bor", "bxor", "shl", "shr", "bnot",
    }),
    # Equality only.
    "Par": frozenset({"eq", "ne"}),
    # Ordering only.
    "Ordo": frozenset({"lt", "le", "gt", "ge"}),
}

#: Concepts that refine another: the refining concept also grants everything the
#: refined one does.  Kept explicit so the chain is readable and testable.
CONCEPT_REFINES: Dict[str, str] = {
    "Integrum": "Num",
}


def concept_grants(concept: str, operator: str) -> bool:
    """True when `concept` grants `operator` on a type parameter.

    Args:
        concept: Concept name as written in a `where T: Concept` bound.
        operator: Internal operator name (`add`, `mod`, `eq`, `lt`, ...).

    Returns:
        True when the bound enables the operator, following `CONCEPT_REFINES`.
    """
    grants = CONCEPT_OPERATORS.get(concept, frozenset())
    if operator in grants:
        return True
    refined = CONCEPT_REFINES.get(concept)
    if refined is not None:
        return concept_grants(refined, operator)
    return False


def _validate_concept_tables() -> None:
    """Fails loudly at import time if the two tables disagree."""
    for refining, refined in CONCEPT_REFINES.items():
        if refined not in CONCEPT_OPERATORS:
            raise AssertionError(
                f"CONCEPT_REFINES[{refining!r}] = {refined!r} is not in CONCEPT_OPERATORS"
            )
        missing = CONCEPT_OPERATORS[refined] - CONCEPT_OPERATORS[refining]
        if missing:
            raise AssertionError(
                f"{refining!r} refines {refined!r} but does not grant {sorted(missing)}"
            )


_validate_concept_tables()

# Concept sets shared by the primitive tables below.  ``Integrum`` is a strict
# refinement of ``Num``: integer types satisfy both, floating-point types only
# satisfy ``Num``.  That is what makes ``%``/bitwise operators reject ``float``.
# Every primitive is trivially droppable, so they all carry ``Nexus`` (a no-op
# destructor) which is what lets 'rune P derive Nexus' have scalar fields.
_INT_CONCEPTS: Set[str] = {"Num", "Integrum", "Par", "Ordo", "Vinculum", "Imago", "Nexus", "Forma", "Donum"}
_FLOAT_CONCEPTS: Set[str] = {"Num", "Par", "Ordo", "Vinculum", "Imago", "Nexus", "Forma", "Donum"}

_INT_NAMES = (
    "int", "i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64",
    "usize", "isize", "int8", "uint8", "int16", "uint16", "int32",
    "uint32", "int64", "uint64", "size_t", "short", "ushort", "long",
    "ulong", "uint", "int8_t", "uint8_t", "int16_t", "uint16_t",
    "int32_t", "uint32_t", "int64_t", "uint64_t", "ptrdiff_t", "intptr_t",
    "uintptr_t",
)
_FLOAT_NAMES = ("float", "f32", "f64", "double", "float32", "float64")

PRIMITIVE_IMPLS: Dict[str, Set[str]] = {
    name: set(_INT_CONCEPTS) for name in _INT_NAMES
}
PRIMITIVE_IMPLS.update({name: set(_FLOAT_CONCEPTS) for name in _FLOAT_NAMES})
PRIMITIVE_IMPLS.update({
    "bool": {"Par", "Vinculum", "Imago", "Nexus", "Forma", "Donum"},
    "char": {"Par", "Ordo", "Vinculum", "Imago", "Nexus", "Forma"},
    "byte": {"Par", "Integrum", "Ordo", "Vinculum", "Imago", "Nexus"},
    "string": {"Par", "Ordo", "Vinculum", "Imago", "Nexus", "Forma", "Donum", "Iterabilis"},
    "list": {"Par", "Iterabilis", "Imago", "Nexus"},
    "map": {"Par", "Iterabilis", "Imago", "Nexus"},
    "slice": {"Par", "Iterabilis"},
    "maybe": {"Par", "Imago", "Nexus"},
    "result": {"Par", "Imago", "Nexus"},
})


def type_owns_heap(t: Optional[Type], _depth: int = 0, symbols: Any = None) -> bool:
    """True when a value of this type owns memory that must be released.

    Used for the *implicit* Imago/Nexus of a rune whose fields need a deep copy
    or a destructor: otherwise a 'list of Rune' would silently leak every
    element's buffer.
    """
    if t is None or _depth > 12:
        return False
    u = t
    while isinstance(u, (AliasType, FrozenType, SealType)):
        nxt = getattr(u, "target", None) or getattr(u, "underlying", None)
        if nxt is None or nxt is u:
            break
        u = nxt
    if isinstance(u, BaseType):
        return u.name == "string"
    if isinstance(u, (ListType, MapType, MaybeType, ResultType)):
        return True
    if isinstance(u, ArrayType):
        return type_owns_heap(getattr(u, "element", None), _depth + 1, symbols=symbols)
    if isinstance(u, RuneType):
        derived = list(getattr(u, "derived_concepts", []) or [])
        if "Imago" in derived or "Nexus" in derived:
            return True
        fields = dict(getattr(u, "fields", None) or {})
        if not fields and symbols is not None:
            base_n = u.get_base_name() if hasattr(u, "get_base_name") else u.name.split("_")[0]
            for key in (u.name, base_n):
                try:
                    sym = getattr(symbols, "runes", {}).get(key) or (symbols.lookup_type(key) if hasattr(symbols, "lookup_type") else None)
                except Exception:
                    sym = None
                if sym is not None and getattr(sym, "fields", None):
                    fields = dict(sym.fields)
                    break
        return any(type_owns_heap(f, _depth + 1, symbols=symbols) for f in fields.values())
    if isinstance(u, OmenType):
        derived = list(getattr(u, "derived_concepts", []) or [])
        if "Imago" in derived or "Nexus" in derived:
            return True
        variants = dict(getattr(u, "variants", None) or {})
        if not variants and symbols is not None:
            base_n = u.name.split("_")[0] if "_" in u.name else u.name
            for key in (u.name, base_n):
                o_sym = getattr(symbols, "omens", {}).get(key)
                if o_sym is not None and getattr(o_sym, "variants", None):
                    variants = dict(o_sym.variants)
                    break
        for v_fields in variants.values():
            if isinstance(v_fields, dict):
                if any(type_owns_heap(f, _depth + 1, symbols=symbols) for f in v_fields.values()):
                    return True
            elif v_fields is not None:
                if type_owns_heap(v_fields, _depth + 1, symbols=symbols):
                    return True
        return False
    return False


def type_implements_builtin_concept(t: Type, concept_name: str) -> bool:
    """Checks if type inherently implements one of the built-in concepts.

    Covers the primitive tables, container capabilities and the ``derive``
    clause recorded on runes/omens/echos.  Named concept *bindings* live in the
    symbol table and are resolved by :func:`implements_concept` instead.
    """
    if isinstance(t, TypeParam):
        return concept_name in t.bounds
    if isinstance(t, AnyType):
        return True
    if isinstance(t, FrozenType):
        return type_implements_builtin_concept(t.target, concept_name)
    if isinstance(t, AliasType):
        return type_implements_builtin_concept(t.target, concept_name)
    if isinstance(t, BaseType):
        return concept_name in PRIMITIVE_IMPLS.get(t.name, set())
    if isinstance(t, ArrayType):
        # A fixed array borrows its element's capabilities: 'array of string'
        # is an Imago/Nexus field, 'array of int' too.
        if getattr(t, "element", None) is None:
            return False
        return type_implements_builtin_concept(t.element, concept_name)
    if isinstance(t, ListType):
        return concept_name in PRIMITIVE_IMPLS.get("list", set())
    if isinstance(t, MapType):
        return concept_name in PRIMITIVE_IMPLS.get("map", set())
    if isinstance(t, SliceType):
        return concept_name in PRIMITIVE_IMPLS.get("slice", set())
    if isinstance(t, MaybeType):
        return concept_name in PRIMITIVE_IMPLS.get("maybe", set())
    if isinstance(t, ResultType):
        return concept_name in PRIMITIVE_IMPLS.get("result", set())
    derived = getattr(t, "derived_concepts", None)
    if derived:
        concept_base = concept_name.split("_")[0] if "_" in concept_name else concept_name
        if concept_name in derived or concept_base in derived:
            return True
    if isinstance(t, RuneType) and concept_name in ("Imago", "Nexus"):
        # A rune with heap-owning fields gets an implicit deep copy/destructor so
        # that containers and 'some' boxes can own it safely.
        if type_owns_heap(t):
            return True
    t_name = getattr(t, "name", str(t))
    if t_name in PRIMITIVE_IMPLS and concept_name in PRIMITIVE_IMPLS[t_name]:
        return True
    return False


def unwrap_aliasish(t: Optional[Type]) -> Optional[Type]:
    """Strips alias/frozen/seal wrappers, returning the underlying type."""
    seen = 0
    while t is not None and seen < 32:
        if isinstance(t, (AliasType, FrozenType, SealType)):
            nxt = getattr(t, "target", None) or getattr(t, "underlying", None)
            if nxt is None or nxt is t:
                break
            t = nxt
            seen += 1
        else:
            break
    return t


def type_needs_deep_clone(t: Optional[Type], symbols: Any = None) -> bool:
    """True when a value of type ``t`` must be deep-copied to own it.

    Mirrors the codegen's ``_element_clone_fn`` decision: strings, lists, maps
    and runes carrying the ``Imago``/``Nexus`` concept (via ``derive`` or a
    ``bind``) own heap memory and therefore register a clone callback.
    ``TypeParam`` is unknown at check time, so it reports False (conservative).
    """
    u = unwrap_aliasish(t)
    if u is None or isinstance(u, (AnyType, TypeParam)):
        return False
    if isinstance(u, BaseType):
        return u.name == "string"
    if isinstance(u, (ListType, MapType)):
        return True
    if isinstance(u, (MaybeType, ResultType)):
        # The code generator emits a per-type clone helper for these: the
        # payload box must be duplicated even when the payload is a plain
        # scalar, otherwise push/put would alias the box and double-free it.
        return True
    if isinstance(u, (RuneType, EchoType, OmenType)):
        derived = set(getattr(u, "derived_concepts", None) or [])
        base_n = u.get_base_name() if hasattr(u, "get_base_name") else getattr(u, "name", "")
        if symbols is not None:
            runes = getattr(symbols, "runes", None) or {}
            if base_n in runes:
                derived |= set(getattr(runes[base_n], "derived_concepts", None) or [])
            bindings = getattr(symbols, "concept_bindings", None) or {}
            names = {getattr(u, "name", ""), base_n}
            for concept in ("Imago", "Nexus"):
                if any((n, concept) in bindings for n in names if n):
                    derived.add(concept)
        return bool(derived & {"Imago", "Nexus"})
    return False


def type_has_derived_nexus(t: Optional[Type], symbols: Any = None) -> bool:
    """True when ``t`` carries a *derived* ``Nexus`` implementation.

    Only ``derive Nexus`` (or the implicit pairing with ``derive Imago``)
    generates the ``_pengu_cleanup_<C>`` helper that ``banish`` lowers to; a
    concept implemented through ``bind`` provides methods, not that helper.
    """
    u = unwrap_aliasish(t)
    if u is None:
        return False
    if not isinstance(u, (RuneType, EchoType, OmenType)):
        return False
    if isinstance(u, OmenType) and not u.is_algebraic:
        return False
    derived = set(getattr(u, "derived_concepts", None) or [])
    base_n = u.get_base_name() if hasattr(u, "get_base_name") else getattr(u, "name", "")
    if symbols is not None:
        reg = getattr(symbols, "runes", None) or {}
        entry = reg.get(base_n)
        if entry is None:
            reg2 = getattr(symbols, "omens", None) or {}
            entry = reg2.get(base_n)
        if entry is not None:
            derived |= set(getattr(entry, "derived_concepts", None) or [])
    if "Nexus" in derived:
        return True
    # A rune (or algebraic omen) whose fields own heap gets an implicit Nexus, so
    # its generated destructor exists and 'banish' can lower to it.
    return type_owns_heap(u)


def receiver_deep_copies_on_store(t: Optional[Type], symbols: Any = None) -> bool:
    """True when storing into the container ``t`` deep-copies the stored value.

    A ``list``/``map`` built with the ``_owned`` constructors registers
    clone callbacks for its elements, so ``push``/``put`` copy instead of
    aliasing and the source variable keeps ownership of its own buffer.
    A ``ref to list``/``ref to map`` receiver is looked through: the pointer
    does not change the ownership semantics of the container itself.
    """
    u = t
    if isinstance(u, RefType):
        u = u.target
    u = unwrap_aliasish(u)
    if isinstance(u, ListType):
        return type_needs_deep_clone(u.element, symbols)
    if isinstance(u, MapType):
        return (type_needs_deep_clone(u.key, symbols)
                and type_needs_deep_clone(u.value, symbols))
    return False


def implements_concept(t: Type, concept_name: str, symbols: Any) -> bool:
    """Checks if type t implements concept_name via registered concept bindings or built-ins."""
    if t is None:
        return False
    if isinstance(t, AnyType):
        return True
    if isinstance(t, TypeParam):
        if not t.bounds:
            return True
        if concept_name in t.bounds:
            return True
        # 'Integrum' refines 'Num': an integer bound satisfies numeric needs.
        if concept_name == "Num" and "Integrum" in t.bounds:
            return True
        return False
    if type_implements_builtin_concept(t, concept_name):
        return True
    if symbols is None:
        return False

    t_name = getattr(t, "name", str(t))
    base_tname = t.get_base_name() if hasattr(t, "get_base_name") else (t_name.split("_")[0] if "_" in t_name else t_name)
    concept_base = concept_name.split("_")[0] if "_" in concept_name else concept_name

    if hasattr(symbols, "concept_bindings"):
        for key in [(t_name, concept_name), (base_tname, concept_base), (t_name, concept_base), (base_tname, concept_name)]:
            if key in symbols.concept_bindings:
                return True
    if hasattr(t, "derived_concepts") and (concept_name in t.derived_concepts or concept_base in t.derived_concepts):
        return True
    return False


def typeparam_accepts_value(tp: "TypeParam", val_t: Optional[Type], symbols: Any) -> bool:
    """True when ``val_t`` may flow into a bare type-parameter target.

    ``TypeParam`` is a wildcard for the *value* direction
    (``BaseType.is_compatible(TypeParam)`` is always True), so bounds must be
    enforced explicitly: nothing but a bound-satisfying value can flow into
    ``T: Num``.  Unbounded parameters stay fully permissive, and ``any``/``null``
    plus another parameter are accepted (they are resolved later).
    """
    if tp is None or not getattr(tp, "bounds", None):
        return True
    if val_t is None or isinstance(val_t, (AnyType, NullType, TypeParam)):
        return True
    for b in tp.bounds:
        if not implements_concept(val_t, b, symbols):
            return False
    return True


def resolve_concept_method(t: Type, concept_name: str, method_name: str, symbols: Any) -> Optional[FnType]:
    """Retrieves FnType for a concept method implemented on type t."""
    if t is None or symbols is None:
        return None
    t_name = getattr(t, "name", str(t))
    base_tname = t_name.split("_")[0] if "_" in t_name else t_name
    concept_base = concept_name.split("_")[0] if "_" in concept_name else concept_name

    if hasattr(symbols, "concept_bindings"):
        for key in [(t_name, concept_name), (base_tname, concept_base), (t_name, concept_base), (base_tname, concept_name)]:
            if key in symbols.concept_bindings and method_name in symbols.concept_bindings[key]:
                return symbols.concept_bindings[key][method_name]
    return None


def check_generic_bounds(
    base_name: str,
    type_args: List[Type],
    symbols: Any
) -> Optional[Tuple[str, str, str, str]]:
    """Checks whether type arguments satisfy concept bounds declared on generic type base_name.

    Returns (arg_t_display, bound, tp_name, base_name) on violation, or None if satisfied.
    """
    if symbols is None or not type_args:
        return None

    type_params: List[str] = []
    bounds: Dict[str, List[str]] = {}

    t_entry = symbols.lookup_type(base_name) if hasattr(symbols, "lookup_type") else None
    if t_entry is None and hasattr(symbols, "runes"):
        t_entry = symbols.runes.get(base_name)
    if t_entry is not None:
        type_params = getattr(t_entry, "type_params", []) or []
        bounds = getattr(t_entry, "bounds", {}) or {}

    if not bounds or not type_params:
        gen_entry = None
        for reg in ("generic_runes", "generic_echos", "generic_omens", "generic_aliases"):
            if hasattr(symbols, reg):
                d = getattr(symbols, reg)
                if base_name in d:
                    gen_entry = d[base_name]
                    break
        if gen_entry is not None:
            if not type_params:
                type_params = gen_entry[0]
            stmt = gen_entry[1] if len(gen_entry) > 1 else None
            if isinstance(stmt, Tree):
                for ch in stmt.children:
                    if isinstance(ch, Tree) and ch.data == "shard_params":
                        for w in ch.children:
                            if isinstance(w, Tree) and w.data == "where_clause":
                                for wb in w.children:
                                    if isinstance(wb, Tree) and wb.data == "where_bound":
                                        tp_node = wb.children[0]
                                        tp_name = str(tp_node.value if isinstance(tp_node, Token) else (tp_node.children[0] if isinstance(tp_node, Tree) else tp_node))
                                        c_node = wb.children[1]
                                        c_name = str(c_node.children[0] if (isinstance(c_node, Tree) and c_node.children) else c_node)
                                        bounds.setdefault(tp_name, []).append(c_name)

    if not type_params or not bounds:
        return None

    for idx, tp in enumerate(type_params):
        if idx >= len(type_args):
            break
        arg_t = type_args[idx]
        if isinstance(arg_t, TypeParam):
            continue
        for bound in bounds.get(tp, []):
            if not implements_concept(arg_t, bound, symbols):
                t_display = getattr(arg_t, "name", str(arg_t))
                return (t_display, bound, tp, base_name)

    return None


def is_opaque_type(t: Type) -> bool:
    """Checks if a given type is or aliases an opaque type.

    Args:
        t: Type to inspect.

    Returns:
        True if type is opaque, False otherwise.
    """
    if t == OPAQUE_TYPE:
        return True
    if isinstance(t, BaseType) and t.name == "opaque":
        return True
    if isinstance(t, AliasType):
        return is_opaque_type(t.target)
    return False


def _resolve_symbol_table(fn: Any) -> Any:
    if fn is None:
        return None
    st = getattr(fn, "__self__", None)
    if st and hasattr(st, "monomorphized_types"):
        return st
    st = getattr(fn, "symbol_table", None)
    if st and hasattr(st, "monomorphized_types"):
        return st
    if hasattr(fn, "__closure__") and fn.__closure__:
        for cell in fn.__closure__:
            try:
                val = cell.cell_contents
            except ValueError:
                continue
            if hasattr(val, "monomorphized_types"):
                return val
            if hasattr(val, "symbols") and hasattr(val.symbols, "monomorphized_types"):
                return val.symbols
            if callable(val) and getattr(val, "__self__", None) and hasattr(val.__self__, "monomorphized_types"):
                return val.__self__
            if callable(val) and hasattr(val, "__closure__"):
                sub_st = _resolve_symbol_table(val)
                if sub_st is not None:
                    return sub_st
    return None


def ast_to_type(type_node: Any, symbol_lookup_fn: Optional[Any] = None) -> Type:
    """Converts a parsed Lark type AST node into a Type object.

    Args:
        type_node: Lark Tree or Token representing a type expression.
        symbol_lookup_fn: Optional callback to resolve custom types/aliases from symbol table.

    Returns:
        The instantiated Type object.
    """
    if type_node is None:
        return AnyType()

    if isinstance(type_node, Token):
        text = str(type_node)
        if text in (
            "int", "i32", "i64", "float", "f32", "f64", "bool", "string", "void",
            "char", "byte", "u8", "i8", "u16", "i16", "u32", "u64", "int8", "uint8",
            "int16", "uint16", "int32", "uint32", "int64", "uint64", "usize", "isize",
            "size_t", "short", "ushort", "long", "ulong", "double", "int8_t", "uint8_t",
            "int16_t", "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t", "uint"
        ):
            return BaseType(text)
        if text in ("any", "Any"):
            return AnyType()
        if text == "opaque":
            return OPAQUE_TYPE
        if symbol_lookup_fn:
            t = symbol_lookup_fn(text)
            if t is not None:
                return t
        return RuneType(name=text)

    if not isinstance(type_node, Tree):
        return AnyType()

    rule = type_node.data
    if rule == "shard_param_ref":
        return TypeParam(str(type_node.children[0]))

    elif rule == "base_type":
        if type_node.children:
            b_name = str(type_node.children[0])
            if b_name in ("any", "Any"):
                return AnyType()
            return BaseType(b_name)
        return INT_TYPE

    elif rule == "custom_type":
        first = type_node.children[0]
        if isinstance(first, Tree) and first.data == "dotted_path":
            name = ".".join(str(t) for t in first.children)
        else:
            name = str(first)

        type_args = []
        for c in type_node.children[1:]:
            # The optional 'of type …' part leaves a None child behind; treating
            # it as an argument turned every bare custom type into a bogus
            # generic instantiation ('va_list' -> 'va_list_any').
            if c is None:
                continue
            arg_t = ast_to_type(c, symbol_lookup_fn)
            if arg_t is not None:
                type_args.append(arg_t)

        if symbol_lookup_fn:
            t = symbol_lookup_fn(name)
            if t is not None:
                if type_args:
                    t_params = getattr(t, "type_params", [])
                    if t_params:
                        subst_map = dict(zip(t_params, type_args))
                        specialized = t.substitute(subst_map)
                        st = _resolve_symbol_table(symbol_lookup_fn)
                        if st and hasattr(st, "monomorphized_types") and not any(isinstance(a, TypeParam) for a in type_args):
                            st.monomorphized_types[specialized.name] = specialized
                            if hasattr(st, "concept_bindings") and hasattr(specialized, "derived_concepts"):
                                for d_concept in specialized.derived_concepts:
                                    st.concept_bindings[(specialized.name, d_concept)] = {}
                            if isinstance(specialized, RuneType):
                                st.runes[specialized.name] = specialized
                            elif isinstance(specialized, EchoType):
                                st.echos[specialized.name] = specialized
                            elif isinstance(specialized, OmenType):
                                st.omens[specialized.name] = specialized
                            elif isinstance(specialized, AliasType):
                                st.aliases[specialized.name] = specialized
                        return specialized
                    elif isinstance(t, AliasType) and t.type_params:
                        subst_map = dict(zip(t.type_params, type_args))
                        specialized = t.substitute(subst_map)
                        st = _resolve_symbol_table(symbol_lookup_fn)
                        if st and hasattr(st, "monomorphized_types"):
                            st.monomorphized_types[specialized.name] = specialized
                            st.aliases[specialized.name] = specialized
                        return specialized
                return t

        if type_args:
            args_str = "_".join(a.get_mangled_name() for a in type_args)
            mangled = f"{name}_{args_str}"
            return RuneType(name=mangled, type_args=type_args)
        return RuneType(name=name)

    elif rule == "opaque_type":
        return OPAQUE_TYPE

    elif rule == "ref_type":
        inner = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return RefType(target=inner)

    elif rule == "frozen_type":
        inner = ast_to_type(type_node.children[0], symbol_lookup_fn)
        # 'frozen ref to T' is sugar for 'ref to frozen T' (C 'const T*'):
        # the canonical form puts the qualification on the pointee. The pointer
        # itself stays mutable ('T* const' is what 'let' expresses).
        if isinstance(inner, RefType):
            return RefType(target=FrozenType(target=inner.target))
        if isinstance(inner, FrozenType):
            return inner   # 'frozen frozen T' is idempotent
        return FrozenType(target=inner)

    elif rule == "array_type":
        curr = type_node
        array_nodes = []
        while isinstance(curr, Tree) and curr.data == "array_type":
            array_nodes.append(curr)
            curr = curr.children[0]
        base_elem = ast_to_type(curr, symbol_lookup_fn)
        
        def _resolve_sz(sz_tok):
            if sz_tok is None:
                return None
            if isinstance(sz_tok, Token) and sz_tok.type == "INT":
                from .pengu_comptime import parse_int_literal
                try:
                    return parse_int_literal(str(sz_tok))
                except ValueError:
                    return None
            elif isinstance(sz_tok, Token):
                sz_name = str(sz_tok)
                sym = None
                if symbol_lookup_fn:
                    st = _resolve_symbol_table(symbol_lookup_fn)
                    if st and hasattr(st, "lookup"):
                        sym = st.lookup(sz_name)
                    elif st and hasattr(st, "symbols") and hasattr(st.symbols, "lookup"):
                        sym = st.symbols.lookup(sz_name)
                    else:
                        sym = symbol_lookup_fn(sz_name)
                if sym and hasattr(sym, "const_val") and isinstance(sym.const_val, int):
                    return sym.const_val
            return None

        # Depth-based resolution: in right-associative multi-dimensional array types,
        # array_nodes[0] is outermost AST node and array_nodes[-1] is innermost.
        # Following LANGUAGE.md §15.3 (outer dimension first), the first 'with size' in source
        # is held on array_nodes[-1] (outer size), and the last on array_nodes[0] (inner size).
        size_tokens = [an.children[1] if len(an.children) > 1 else None for an in reversed(array_nodes)]

        res = base_elem
        for sz_tok in reversed(size_tokens):
            res = ArrayType(element=res, size=_resolve_sz(sz_tok))
        return res


    elif rule == "slice_type":
        element = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return SliceType(element=element)

    elif rule == "many_type":
        element = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return ManyType(element=element)

    elif rule == "list_type":
        element = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return ListType(element=element)

    elif rule == "map_type":
        key = ast_to_type(type_node.children[0], symbol_lookup_fn)
        val = ast_to_type(type_node.children[1], symbol_lookup_fn)
        return MapType(key=key, value=val)

    elif rule == "maybe_type":
        element = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return MaybeType(element=element)

    elif rule == "result_type":
        ok_type = ast_to_type(type_node.children[0], symbol_lookup_fn)
        err_type = ast_to_type(type_node.children[1], symbol_lookup_fn) if len(type_node.children) > 1 else ERROR_TYPE
        return ResultType(ok_type=ok_type, err_type=err_type)

    elif rule == "fn_type":
        params: List[Tuple[Optional[str], Type]] = []
        ret_type: Type = VOID_TYPE
        for child in type_node.children:
            if isinstance(child, Tree) and child.data == "fn_param_list":
                for p_child in child.children:
                    if isinstance(p_child, Tree) and p_child.data == "fn_param":
                        p_name = None
                        p_type = VOID_TYPE
                        if len(p_child.children) == 2:
                            p_name = str(p_child.children[0])
                            p_type = ast_to_type(p_child.children[1], symbol_lookup_fn)
                        elif len(p_child.children) == 1:
                            p_type = ast_to_type(p_child.children[0], symbol_lookup_fn)
                        params.append((p_name, p_type))
            elif isinstance(child, Tree) and child.data in ("base_type", "custom_type", "ref_type", "array_type", "slice_type", "list_type", "map_type", "maybe_type", "result_type", "opaque_type", "fn_type"):
                ret_type = ast_to_type(child, symbol_lookup_fn)
            elif isinstance(child, Token) and child.type == "NAME":
                ret_type = ast_to_type(child, symbol_lookup_fn)
        return FnType(params=params, return_type=ret_type)

    if len(type_node.children) == 1:
        return ast_to_type(type_node.children[0], symbol_lookup_fn)

    return AnyType()


def estimate_size(t: Optional[Type], custom_types: Optional[Dict[str, Type]] = None, seen: Optional[Set[str]] = None) -> int:
    """Estimates the memory size in bytes for a PenguScript type according to C layout rules.

    Args:
        t: Target Type to measure.
        custom_types: Optional mapping of composite type definitions (runes, echos, omens).
        seen: Internal set to prevent infinite recursion on self-referential types.

    Returns:
        Estimated size in bytes (e.g. 4 for int, 8 for pointers, 16 for string, 24 for list/map).
    """
    if t is None:
        return 0
    if seen is None:
        seen = set()

    if isinstance(t, FrozenType):
        # 'const' does not change size or layout.
        return estimate_size(t.target, custom_types, seen)

    if isinstance(t, BaseType):
        n = t.name.lower()
        if n in ("bool",):
            return 1
        if n in ("int", "i32", "float", "f32"):
            return 4
        if n in ("i64", "f64"):
            return 8
        if n in ("void",):
            return 0
        if n in ("string",):
            return 16  # PenguString (pointer + len + cap)
        if n in ("opaque",):
            return 8
        return 4

    if isinstance(t, RefType):
        return 8  # 64-bit pointer

    if isinstance(t, ArrayType):
        elem_sz = estimate_size(t.element, custom_types, seen)
        sz = t.size
        if isinstance(sz, str) and sz.isdigit():
            sz = int(sz)
        elif not isinstance(sz, int):
            sz = 1
        return max(1, sz) * elem_sz

    if isinstance(t, (SliceType, ManyType)):
        return 24  # PenguSlice: void* data (8) + int len (4) + padding (4) + size_t elem_size (8) = 24 bytes

    if isinstance(t, ListType):
        return 40  # PenguList: data (8) + len (4) + cap (4) + elem_size (8) + cleanup (8) + clone (8) = 40 bytes

    if isinstance(t, MapType):
        return 64  # PenguMap: entries (8) + len (4) + cap (4) + key_sz (8) + val_sz (8) + 4 callbacks (32) = 64 bytes

    if isinstance(t, MaybeType):
        return 16  # PenguMaybe: bool is_present (1) + padding (7) + void* value (8) = 16 bytes

    if isinstance(t, ResultType):
        ok_sz = estimate_size(t.ok_type, custom_types, seen)
        err_sz = estimate_size(t.err_type, custom_types, seen)
        return ok_sz + err_sz + 4

    if isinstance(t, RuneType):
        if t.name in seen:
            return 8
        seen.add(t.name)
        if t.fields:
            return sum(estimate_size(ft, custom_types, seen) for ft in t.fields.values())
        if custom_types and t.name in custom_types:
            cand = custom_types[t.name]
            if isinstance(cand, RuneType) and cand.fields:
                return sum(estimate_size(ft, custom_types, seen) for ft in cand.fields.values())
        return 8

    if isinstance(t, EchoType):
        if t.name in seen:
            return 8
        seen.add(t.name)
        max_v = max((estimate_size(ft, custom_types, seen) for ft in t.fields.values()), default=4)
        return max_v + 4  # tag + largest field

    if isinstance(t, OmenType):
        if t.name in seen:
            return 8
        seen.add(t.name)
        max_v = 0
        for v_fields in t.variants.values():
            v_sz = sum(estimate_size(ft, custom_types, seen) for ft in v_fields.values())
            if v_sz > max_v:
                max_v = v_sz
        return max_v + 4

    if isinstance(t, AliasType):
        key = f"alias::{t.name}"
        if key in seen:
            return 8
        seen.add(key)
        return estimate_size(t.target, custom_types, seen)

    if isinstance(t, SealType):
        key = f"seal::{t.name}"
        if key in seen:
            return 8
        seen.add(key)
        return estimate_size(t.underlying, custom_types, seen)

    if isinstance(t, FnType):
        return 8  # Function pointer

    if isinstance(t, CVarArgsType):
        return 0

    return 8


def get_type_base_name(t: Any) -> str:
    """Returns canonical base type identifier for method lookup (e.g. 'map', 'list', 'Box')."""
    if isinstance(t, str):
        if t.startswith("map of ") or t.startswith("map_"):
            return "map"
        if t.startswith("list of ") or t.startswith("list_"):
            return "list"
        if t.startswith("slice of ") or t.startswith("slice_"):
            return "slice"
        if t.startswith("maybe ") or t.startswith("maybe_"):
            return "maybe"
        if t.startswith("result of ") or t.startswith("result_"):
            return "result"
        return t.split("_")[0]
    if isinstance(t, RefType):
        return get_type_base_name(t.target)
    if isinstance(t, FrozenType):
        return get_type_base_name(t.target)
    if isinstance(t, MapType):
        return "map"
    if isinstance(t, ListType):
        return "list"
    if isinstance(t, SliceType):
        return "slice"
    if isinstance(t, ManyType):
        return "many"
    if isinstance(t, MaybeType):
        return "maybe"
    if isinstance(t, ResultType):
        return "result"
    name = getattr(t, "name", str(t))
    if name.startswith("map of "):
        return "map"
    if name.startswith("list of "):
        return "list"
    if name.startswith("slice of "):
        return "slice"
    if name.startswith("maybe "):
        return "maybe"
    if name.startswith("result of "):
        return "result"
    return name.split("_")[0]


def extract_type_params_from_type(t: Any) -> List[str]:
    """Extracts all TypeParam names found recursively within a type."""
    params: List[str] = []
    def _rec(curr: Any):
        if isinstance(curr, TypeParam):
            if curr.name not in params:
                params.append(curr.name)
        elif isinstance(curr, MapType):
            _rec(curr.key)
            _rec(curr.value)
        elif isinstance(curr, (ListType, SliceType, ManyType, MaybeType)):
            _rec(curr.element)
        elif isinstance(curr, ResultType):
            _rec(curr.ok_type)
            _rec(curr.err_type)
        elif isinstance(curr, (RefType, FrozenType)):
            _rec(curr.target)
        elif isinstance(curr, RuneType) and curr.type_args:
            for a in curr.type_args:
                _rec(a)
    _rec(t)
    return params


