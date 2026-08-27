from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any, Set
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
            base = t.name.split("_")[0] if "_" in t.name and not getattr(t, "type_params", []) else t.name
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
        if isinstance(other, AnyType) or isinstance(self, AnyType):
            return True
        if isinstance(other, TypeParam) or isinstance(self, TypeParam):
            return True
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

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return type_map.get(self.name, self)

    def is_compatible(self, other: Type) -> bool:
        return True

    def can_cast_to(self, other: Type) -> bool:
        return True

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
class BaseType(Type):
    """Primitive base type in PenguScript (int, i32, i64, float, f32, f64, bool, string, void, opaque, error)."""
    name: str

    def is_numeric(self) -> bool:
        """Returns True for numeric primitives (int, i32, i64, float, f32, f64)."""
        return self.name in ("int", "i32", "i64", "float", "f32", "f64")

    def is_int(self) -> bool:
        """Returns True for integer primitives (int, i32, i64)."""
        return self.name in ("int", "i32", "i64")

    def is_float(self) -> bool:
        """Returns True for float primitives (float, f32, f64)."""
        return self.name in ("float", "f32", "f64")

    def is_string(self) -> bool:
        """Returns True for string primitive."""
        return self.name == "string"

    def is_compatible(self, other: Type) -> bool:
        """Checks strict compatibility for base primitives without implicit numeric conversion."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
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
FLOAT_TYPE = BaseType("float")
F32_TYPE = BaseType("f32")
F64_TYPE = BaseType("f64")
BOOL_TYPE = BaseType("bool")
STRING_TYPE = BaseType("string")
VOID_TYPE = BaseType("void")
ERROR_TYPE = BaseType("error")
OPAQUE_TYPE = BaseType("opaque")


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
        """Checks reference compatibility allowing ref to void polymorphism."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, RefType):
            if self.target == VOID_TYPE or other.target == VOID_TYPE:
                return True
            return self.target.is_compatible(other.target)
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
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, ArrayType):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on array element type."""
        return isinstance(other, ArrayType) and self.element == other.element

    def __hash__(self) -> int:
        """Returns hash of array type."""
        return hash(("array", self.element))


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
        """Checks slice compatibility with slices and arrays."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, SliceType):
            return self.element.is_compatible(other.element)
        if isinstance(other, ArrayType):
            return self.element.is_compatible(other.element)
        return False

    def __eq__(self, other: Any) -> bool:
        """Checks equality based on slice element type."""
        return isinstance(other, SliceType) and self.element == other.element

    def __hash__(self) -> int:
        """Returns hash of slice type."""
        return hash(("slice", self.element))


@dataclass
class ListType(Type):
    """Dynamic growable list type (list of T with capacity C)."""
    element: Type

    @property
    def name(self) -> str:
        """Returns formatted list type string."""
        return f"list of {self.element}"

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

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return MaybeType(element=self.element.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"maybe_{self.element.get_mangled_name()}"

    def is_compatible(self, other: Type) -> bool:
        """Checks maybe element compatibility."""
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

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        return ResultType(ok_type=self.ok_type.substitute(type_map), err_type=self.err_type.substitute(type_map))

    def get_mangled_name(self) -> str:
        return f"result_{self.ok_type.get_mangled_name()}_{self.err_type.get_mangled_name()}"

    def is_compatible(self, other: Type) -> bool:
        """Checks ok and error type compatibility."""
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

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

    def get_mangled_name(self) -> str:
        return mangle_type(self)

    def substitute(self, type_map: Dict[str, Type]) -> Type:
        if not type_map:
            return self
        new_fields = {k: v.substitute(type_map) for k, v in self.fields.items()}
        new_methods = {k: v.substitute(type_map) for k, v in self.methods.items()} if hasattr(self, 'methods') else {}
        new_args = [a.substitute(type_map) for a in self.type_args]
        if not new_args and self.type_params:
            new_args = [type_map.get(tp, TypeParam(tp)) for tp in self.type_params]
        base_name = self.name.split("_")[0] if self.type_args else self.name
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return RuneType(name=mangled, fields=new_fields, methods=new_methods, type_params=[], type_args=new_args)
        return RuneType(name=self.name, fields=new_fields, methods=new_methods, type_params=self.type_params, type_args=new_args)

    def is_compatible(self, other: Type) -> bool:
        """Checks rune compatibility by nominal type name."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, RuneType):
            if self.name == other.name:
                return True
            if self.type_args and other.type_args and len(self.type_args) == len(other.type_args):
                base_self = self.name.split("_")[0]
                base_other = other.name.split("_")[0]
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
        base_name = self.name.split("_")[0] if self.type_args else self.name
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return EchoType(name=mangled, fields=new_fields, type_params=[], type_args=new_args)
        return EchoType(name=self.name, fields=new_fields, type_params=self.type_params, type_args=new_args)

    def is_compatible(self, other: Type) -> bool:
        """Checks echo union compatibility by nominal type name."""
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
    type_params: List[str] = field(default_factory=list)
    type_args: List[Type] = field(default_factory=list)

    @property
    def is_generic(self) -> bool:
        return bool(self.type_params) and not bool(self.type_args)

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
        base_name = self.name.split("_")[0] if self.type_args else self.name
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return OmenType(name=mangled, variants=new_variants, type_params=[], type_args=new_args)
        return OmenType(name=self.name, variants=new_variants, type_params=self.type_params, type_args=new_args)

    def is_compatible(self, other: Type) -> bool:
        """Checks omen sum type compatibility by nominal type name."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, OmenType):
            return self.name == other.name
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
            type_args=new_args
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
        return f"weave{params_formatted} into {self.return_type}"

    def is_compatible(self, other: Type) -> bool:
        """Checks function signature parameter and return type compatibility."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
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


class AliasType(Type):
    """Type alias representing a user-defined alias for an underlying target type."""

    def __init__(self, name: str, target: Type, type_params: Optional[List[str]] = None, type_args: Optional[List[Type]] = None):
        """Initializes a new Type alias."""
        self.name = name
        self.target = target
        self.type_params = type_params or []
        self.type_args = type_args or []

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
        base_name = self.name.split("_")[0] if self.type_args else self.name
        if new_args and not any(isinstance(a, TypeParam) for a in new_args):
            mangled = f"{base_name}_{'_'.join(a.get_mangled_name() for a in new_args)}"
            return AliasType(name=mangled, target=new_target, type_params=[], type_args=new_args)
        return AliasType(name=self.name, target=new_target, type_params=self.type_params, type_args=new_args)

    def is_compatible(self, other: Type) -> bool:
        """Checks compatibility by alias name or underlying target type."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, AliasType):
            return self.name == other.name or self.target.is_compatible(other.target)
        return self.target.is_compatible(other)

    def can_cast_to(self, other: Type) -> bool:
        """Checks cast conversion on underlying target type."""
        if isinstance(other, AnyType) or isinstance(other, TypeParam):
            return True
        if isinstance(other, AliasType):
            return self.target.can_cast_to(other.target)
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

    def is_iterable(self) -> bool:
        """Checks if target type is iterable."""
        return self.target.is_iterable()

    def element_type(self) -> Optional[Type]:
        """Returns element type of target type."""
        return self.target.element_type()

    def __eq__(self, other: Any) -> bool:
        """Checks equality by alias name or target type."""
        if isinstance(other, AliasType):
            return self.name == other.name
        return self.target == other

    def __hash__(self) -> int:
        """Returns hash of type alias."""
        return hash(("alias", self.name))


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
        if text in ("int", "i32", "i64", "float", "f32", "f64", "bool", "string", "void"):
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
    if rule == "base_type":
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
                        st = getattr(symbol_lookup_fn, "__self__", None)
                        if st and hasattr(st, "monomorphized_types"):
                            st.monomorphized_types[specialized.name] = specialized
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
                        st = getattr(symbol_lookup_fn, "__self__", None)
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

    elif rule == "array_type":
        element = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return ArrayType(element=element)

    elif rule == "slice_type":
        element = ast_to_type(type_node.children[0], symbol_lookup_fn)
        return SliceType(element=element)

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
        return max(1, t.size) * elem_sz

    if isinstance(t, (SliceType, ListType, MapType)):
        return 24  # struct { void* ptr; size_t len; size_t cap; }

    if isinstance(t, MaybeType):
        elem_sz = estimate_size(t.element, custom_types, seen)
        return elem_sz + 4  # value + is_present boolean aligned

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
        return estimate_size(t.target, custom_types, seen)

    if isinstance(t, FnType):
        return 8  # Function pointer

    return 8

