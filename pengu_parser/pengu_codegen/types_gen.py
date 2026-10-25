"""C struct/union/enum definitions and their forward declarations.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

import re

from ._base import (
    AliasType,
    ArrayType,
    BaseType,
    EchoType,
    FnType,
    FrozenType,
    ListType,
    ManyType,
    MapType,
    MaybeType,
    OmenType,
    Optional,
    RefType,
    ResultType,
    RuneType,
    SealType,
    SliceType,
    TupleType,
    Type,
    TypeParam,
)
from .ctype import (
    CTypeMapper,
)

class TypesMixin:
    """C struct/union/enum definitions and their forward declarations."""

    def _contains_type_placeholder(self, t, _seen=None) -> bool:
        """True for a `TypeParam` or a bare `RuneType("T")` placeholder.

        The combined multi-module checker can leave a caller's type parameter
        as a nominal-looking `RuneType` (no fields, no type args) inside
        `symbols.monomorphized_types`.  Emitting that as `struct Pair_T_U`
        produces invalid C (`T first;`).  A placeholder must never reach the
        type sections, even if some earlier pass registered it.
        """
        if t is None or _seen is None:
            _seen = set()
        if isinstance(t, TypeParam):
            return True
        if isinstance(t, (RuneType, EchoType)):
            name = getattr(t, "name", "")
            if (not getattr(t, "fields", None) and not getattr(t, "type_args", None)
                    and isinstance(name, str) and name.isupper() and len(name) <= 2):
                known = (name in self.runes or name in self.echos
                         or name in self.omens or name in self.aliases
                         or name in self.seals)
                if not known and self.symbols is not None:
                    known = (name in self.symbols.runes or name in self.symbols.echos
                             or name in self.symbols.omens or name in self.symbols.aliases
                             or name in self.symbols.seals)
                if not known:
                    return True
        if isinstance(t, BaseType):
            # `ast_to_type` may leave a caller's type parameter as BaseType("T").
            # A real single-letter type (`rune R`, `omen K`) is in one of the
            # declaration tables; only an unknown uppercase name is a
            # placeholder.  Known primitives are lowercase anyway.
            name = getattr(t, "name", "")
            if isinstance(name, str) and name.isupper() and len(name) <= 2:
                known = (name in self.runes or name in self.echos
                         or name in self.omens or name in self.aliases
                         or name in self.seals)
                if not known and self.symbols is not None:
                    known = (name in self.symbols.runes or name in self.symbols.echos
                             or name in self.symbols.omens or name in self.symbols.aliases
                             or name in self.symbols.seals)
                if not known:
                    return True
        if isinstance(t, (list, tuple)):
            return any(self._contains_type_placeholder(i, _seen) for i in t)
        if isinstance(t, dict):
            return any(self._contains_type_placeholder(v, _seen) for v in t.values())
        if not isinstance(t, Type):
            return False
        if id(t) in _seen:
            return False
        _seen.add(id(t))
        for value in vars(t).values():
            if value is None:
                continue
            if self._contains_type_placeholder(value, _seen):
                return True
        return False

    def _fields_have_placeholder(self, fields) -> bool:
        for f_type in fields.values():
            if self._contains_type_placeholder(f_type):
                return True
        return False

    def generate_forward_declarations(self) -> str:
        """Generates consistent forward struct/union/omen declarations and function prototypes."""
        decls = []

        # Runes
        for name in self.runes:
            if name in self.declaration_types or not self._type_is_live(name):
                continue
            if self._fields_have_placeholder(self.runes[name]):
                continue
            decls.append(f"struct {name};")
            decls.append(f"typedef struct {name} {name};")

        # Echos
        for name in self.echos:
            if name in self.declaration_types or not self._type_is_live(name):
                continue
            if self._fields_have_placeholder(self.echos[name]):
                continue
            decls.append(f"union {name};")
            decls.append(f"typedef union {name} {name};")

        # Omens
        for name, variants in self.omens.items():
            if name in self.declaration_types or not self._type_is_live(name):
                continue
            is_algebraic = any(bool(fields) for fields in variants.values())
            is_string_valued = bool(name in self.omen_values and any(isinstance(v, str) for v in self.omen_values[name].values()))
            if is_algebraic:
                decls.append(f"struct {name};")
                decls.append(f"typedef struct {name} {name};")
            elif not is_string_valued:
                # Complete enum definition (C has no enum forward declaration).
                enum_lines = [f"typedef enum {name} {{"]
                for v_name in variants:
                    if name in self.omen_values and v_name in self.omen_values[name]:
                        enum_lines.append(f"  {name}_{v_name} = {self.omen_values[name][v_name]},")
                    else:
                        enum_lines.append(f"  {name}_{v_name},")
                enum_lines.append(f"}} {name};")
                decls.append("\n".join(enum_lines))

        # Seals (Newtypes)
        for name, underlying in self.seals.items():
            if name in self.declaration_types or not self._type_is_live(name):
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
            if name in self.declaration_types or not self._type_is_live(name):
                continue
            if isinstance(target, BaseType) and target.name == "opaque":
                alias_lines.append(f"typedef struct {name} {name};")
            elif isinstance(target, FnType) or (isinstance(target, RefType) and isinstance(target.target, FnType)):
                # Function-pointer alias: C needs the identifier *inside* the
                # declarator ('typedef ret (*Name)(params);'), so 'to_c_type'
                # (which has no identifier) produced invalid C here.
                alias_lines.append(f"typedef {CTypeMapper.to_c_decl(target, name)};")
            else:
                target_str = CTypeMapper.to_c_type(target)
                alias_lines.append(f"typedef {target_str} {name};")
        if alias_lines:
            blocks.append("\n".join(alias_lines))

        # 1.5 Seals (Newtypes)
        seal_lines = []
        for name, underlying in self.seals.items():
            if name in self.declaration_types or not self._type_is_live(name):
                continue
            u_str = CTypeMapper.to_c_type(underlying)
            seal_lines.append(f"typedef {u_str} {name};")
        if seal_lines:
            blocks.append("\n".join(seal_lines))

        # 2. Runes, echos and algebraic omens (dependency order)
        #
        # A by-value field requires the field's type to be *complete*, so all
        # three kinds of user-defined aggregate are emitted in one topological
        # order.  The old split (all runes, then all omens) made a rune that
        # stores an algebraic omen by value -- the shape of a recursive JSON
        # node (`JsonEntry.value as JsonValue`) -- reference an incomplete
        # struct, even though no infinitely-sized type exists.
        #
        # A `list of T`, `map of K to V`, `ref to T`, `maybe T` or `result of T
        # to E` stores only a pointer/size header, so it is deliberately *not*
        # an edge: that is exactly what lets `JsonValue` own
        # `list of JsonEntry` while `JsonEntry` owns a `JsonValue` by value.
        #
        # Tuple product structs and monomorphised generics are registered
        # during code generation, after the module's own runes, so they lead the
        # candidate list; the registration order is the deterministic
        # tie-breaker.
        algebraic_omens = [
            n for n, variants in self.omens.items()
            if any(bool(fields) for fields in variants.values())
        ]
        type_order = [n for n in self.runes if n.startswith("_pengu_tup_")]
        type_order += [n for n in self.runes if not n.startswith("_pengu_tup_")]
        type_order += [n for n in self.echos if n not in self.runes]
        type_order += algebraic_omens
        type_order = [n for n in type_order
                      if n not in self.declaration_types and self._type_is_live(n)]
        type_order = self._order_types_by_value(type_order)
        for name in type_order:
            if name in self.runes:
                fields = self.runes[name]
                if self._fields_have_placeholder(fields):
                    continue
                r_attrs = self.rune_attributes.get(name, {})
                is_msvc = self.target_compiler == "msvc"
                c_struct_attrs = []
                declspec_attr = ""
                packed_prefix = ""
                packed_suffix = ""
                if "packed" in r_attrs:
                    if is_msvc:
                        # MSVC has no __attribute__((packed)); use the pack pragma.
                        packed_prefix = "#pragma pack(push, 1)\n"
                        packed_suffix = "\n#pragma pack(pop)"
                    else:
                        c_struct_attrs.append("packed")
                if "align" in r_attrs and r_attrs["align"]:
                    if is_msvc:
                        declspec_attr = f" __declspec(align({r_attrs['align'][0]}))"
                    else:
                        c_struct_attrs.append(f"aligned({r_attrs['align'][0]})")
                attr_str = f" __attribute__(({', '.join(c_struct_attrs)}))" if c_struct_attrs else ""
                rune_lines = [f"{packed_prefix}struct{declspec_attr}{attr_str} {name} {{"]
                f_attrs_map = self.rune_field_attributes.get(name, {})
                for f_name, f_type in fields.items():
                    fa = f_attrs_map.get(f_name, {})
                    fa_prefix = ""
                    fa_parts = []
                    if "align" in fa and fa["align"]:
                        if is_msvc:
                            # MSVC's __declspec must precede the declared name.  The
                            # GNU-style *trailing* position this used to emit
                            # (`int32_t head __declspec(align(8));`) is not valid MSVC —
                            # measured with `clang -fdeclspec -fms-extensions
                            # -fsyntax-only`, the MSVC-syntax oracle the suite can run
                            # on Linux (Phase 8 finding F8-N3).
                            fa_prefix = f"__declspec(align({fa['align'][0]})) "
                        else:
                            fa_parts.append(f"aligned({fa['align'][0]})")
                    fa_str = (f" __attribute__(({', '.join(fa_parts)}))" if fa_parts else "")
                    member = self._declared_member(f_type, self._c_ident(f_name))
                    rune_lines.append(f"  {fa_prefix}{member}{fa_str};")
                rune_lines.append("};" + packed_suffix)
                blocks.append("\n".join(rune_lines))
            elif name in self.echos:
                fields = self.echos[name]
                if self._fields_have_placeholder(fields):
                    continue
                echo_lines = [f"union {name} {{"]
                for f_name, f_type in fields.items():
                    member = self._declared_member(f_type, self._c_ident(f_name))
                    echo_lines.append(f"  {member};")
                echo_lines.append("};")
                blocks.append("\n".join(echo_lines))
            else:
                variants = self.omens[name]
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
                            member = self._declared_member(f_type, self._c_ident(f_name))
                            omen_lines.append(f"      {member};")
                        omen_lines.append(f"    }} {self._c_ident(v_name)};")
                omen_lines.extend([
                    "  } data;",
                    "};",
                ])
                blocks.append("\n".join(omen_lines))

        # 3. String-valued omens (plain enums are complete in the forward
        # declarations above, so they are not repeated here).
        for name, variants in self.omens.items():
            if name in self.declaration_types or not self._type_is_live(name):
                continue
            is_algebraic = any(bool(fields) for fields in variants.values())
            if is_algebraic:
                continue
            is_string_valued = bool(
                name in self.omen_values
                and any(isinstance(v, str) for v in self.omen_values[name].values())
            )
            if not is_string_valued:
                continue
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

        if not blocks:
            return ""

        header = [
            "/* -------------------------------------------------------------------------",
            " * Type Definitions",
            " * ------------------------------------------------------------------------- */",
        ]
        return "\n".join(header) + "\n" + "\n\n".join(blocks) + "\n"
    def _type_is_live(self, name: str) -> bool:
        """True when a type must be emitted (no filter, or in the live set)."""
        live = getattr(self, "_live_type_names", None)
        return live is None or name in live

    def _add_live_type_name(self, name: str, live: set) -> None:
        """Marks a type and every type its *definition* needs."""
        if not name or name in live:
            return
        if name in self.runes:
            live.add(name)
            for field_type in self.runes[name].values():
                self._walk_type(field_type, live)
            return
        if name in self.echos:
            live.add(name)
            for field_type in self.echos[name].values():
                self._walk_type(field_type, live)
            return
        if name in self.omens:
            live.add(name)
            for variant_fields in self.omens[name].values():
                for field_type in variant_fields.values():
                    self._walk_type(field_type, live)
            return
        if name in self.aliases:
            live.add(name)
            self._walk_type(self.aliases[name], live)
            return
        if name in self.seals:
            live.add(name)
            self._walk_type(self.seals[name], live)

    def _walk_type(self, t: Optional[Type], live: set) -> None:
        """Adds every aggregate/alias needed by ``t`` (transitively)."""
        if t is None or isinstance(t, TypeParam):
            return
        if isinstance(t, FrozenType):
            self._walk_type(t.target, live)
            return
        if isinstance(t, AliasType):
            name = getattr(t, "c_name", None) or getattr(t, "name", "")
            if name in self.aliases:
                self._add_live_type_name(name, live)
            self._walk_type(t.target, live)
            return
        if isinstance(t, SealType):
            name = getattr(t, "c_name", None) or getattr(t, "name", "")
            if name in self.seals:
                self._add_live_type_name(name, live)
            self._walk_type(t.underlying, live)
            return
        if isinstance(t, RuneType):
            name = getattr(t, "c_name", None) or getattr(t, "name", "")
            if name in self.runes:
                self._add_live_type_name(name, live)
            else:
                live.add(name)
                for field_type in (getattr(t, "fields", {}) or {}).values():
                    self._walk_type(field_type, live)
            return
        if isinstance(t, EchoType):
            name = getattr(t, "c_name", None) or getattr(t, "name", "")
            if name in self.echos:
                self._add_live_type_name(name, live)
            else:
                live.add(name)
                for field_type in (getattr(t, "fields", {}) or {}).values():
                    self._walk_type(field_type, live)
            return
        if isinstance(t, OmenType):
            name = getattr(t, "c_name", None) or getattr(t, "name", "")
            if name in self.omens:
                self._add_live_type_name(name, live)
            else:
                live.add(name)
                for variant_fields in (getattr(t, "variants", {}) or {}).values():
                    for field_type in (variant_fields or {}).values():
                        self._walk_type(field_type, live)
            return
        if isinstance(t, TupleType):
            try:
                name = t.c_name()
            except Exception:
                name = ""
            if name in self.runes:
                self._add_live_type_name(name, live)
            for element in t.elements:
                self._walk_type(element, live)
            return
        if isinstance(t, (ListType, SliceType, ManyType)):
            self._walk_type(getattr(t, "element", None), live)
            return
        if isinstance(t, MapType):
            self._walk_type(t.key, live)
            self._walk_type(t.value, live)
            return
        if isinstance(t, MaybeType):
            self._walk_type(t.element, live)
            return
        if isinstance(t, ResultType):
            self._walk_type(t.ok_type, live)
            self._walk_type(t.err_type, live)
            return
        if isinstance(t, ArrayType):
            self._walk_type(t.element, live)
            return
        if isinstance(t, RefType):
            self._walk_type(t.target, live)
            return
        if isinstance(t, FnType):
            for param in (getattr(t, "params", None) or []):
                p_type = param[1] if isinstance(param, tuple) and len(param) >= 2 else param
                self._walk_type(p_type, live)
            self._walk_type(getattr(t, "return_type", None), live)

    def compute_live_types(self, root_texts, extra_types=()) -> set:
        """Computes the transitive set of types the emitted C references.

        Enabled by ``--prune-types`` only.  The roots are type C names mentioned
        by live weave bodies, prototypes, lambdas, kept constants and kept
        derived helpers; a type keeps every type its *definition* needs (field
        types, container elements, alias/seal targets, tuple elements).  Simple
        enum variants (`Color_Red`) also seed their enum (`Color`).

        Args:
            root_texts: C texts that will be emitted outside the type sections.
            extra_types: Type objects whose use is known but whose spelling may
                be absent from the text (constant types).

        Returns:
            The live type-name set (also stored on ``self``).
        """
        live: set = set()
        known = set(self.runes) | set(self.echos) | set(self.omens) | set(self.aliases) | set(self.seals)
        omen_names = list(self.omens)
        for text in root_texts:
            for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", text or ""):
                ident = match.group(0)
                if ident in known:
                    self._add_live_type_name(ident, live)
                elif "_" in ident:
                    for oname in omen_names:
                        if ident.startswith(oname + "_"):
                            self._add_live_type_name(oname, live)
                            break
        for t in extra_types:
            self._walk_type(t, live)
        self._live_type_names = live
        return live

    def _value_deps(self, t: Type, deps: set) -> None:
        """Adds the aggregates that ``t`` needs *complete* when used by value.

        Only a by-value use creates a C dependency: ``ref to T`` is a pointer,
        and ``list``/``map``/``slice``/``maybe``/``result`` all store a header
        or a box pointer, so none of them needs the element type's definition.
        Treating a ``list of T`` as a dependency made every recursive container
        type look like a cycle and emitted the aggregate in the wrong order.
        """
        if isinstance(t, RuneType):
            name = getattr(t, "c_name", None) or t.name
            if name in self.runes:
                deps.add(name)
            return
        if isinstance(t, OmenType):
            if t.is_algebraic:
                name = getattr(t, "c_name", None) or t.name
                if name in self.omens:
                    deps.add(name)
            return
        if isinstance(t, TupleType):
            name = t.c_name()
            if name in self.runes:
                deps.add(name)
            # A tuple embeds its elements by value too: `(Position, Position)`
            # needs `Position` complete before the product struct, exactly like
            # a rune field does.  Returning here used to leave the tuple first
            # in `type_order` and produced an incomplete field type.
            for element in t.elements:
                self._value_deps(element, deps)
            return
        if isinstance(t, FrozenType):
            self._value_deps(t.target, deps)
        elif isinstance(t, AliasType):
            self._value_deps(t.target, deps)
        elif isinstance(t, SealType):
            self._value_deps(t.underlying, deps)
        elif isinstance(t, ArrayType):
            self._value_deps(t.element, deps)

    def _order_types_by_value(self, names: list) -> list:
        """Topologically orders rune, echo and algebraic-omen definitions.

        Every edge means "the target must be complete first" (a by-value
        field).  Cycles through pointers or containers are not edges, so a
        recursive ``JsonValue``/``JsonEntry`` pair orders cleanly; a genuine
        by-value cycle is rejected earlier by the checker.  A ``visit`` that
        re-enters an in-progress name therefore just stops.
        """
        order: list = []
        state: dict = {}

        def visit(name: str) -> None:
            mark = state.get(name, 0)
            if mark:
                return
            state[name] = 1
            deps: set = set()
            if name in self.runes:
                for f_type in self.runes[name].values():
                    self._value_deps(f_type, deps)
            elif name in self.echos:
                for f_type in self.echos[name].values():
                    self._value_deps(f_type, deps)
            elif name in self.omens:
                for v_fields in self.omens[name].values():
                    for f_type in v_fields.values():
                        self._value_deps(f_type, deps)
            for candidate in names:
                if candidate != name and candidate in deps:
                    visit(candidate)
            state[name] = 2
            order.append(name)

        for name in names:
            visit(name)
        return order

    def _declared_member(self, f_type: Type, ident: str) -> str:
        """C declaration of one struct/union member named ``ident``.

        A function-pointer type must keep the name *inside* the declarator
        (``R (*ident)(A)``); appending the name after ``to_c_type`` produced the
        invalid ``R (*)(A) ident``.  Arrays of function pointers need the same
        treatment, with the dimensions after the identifier.  Every other type
        keeps the historical ``<type> <ident>`` shape.
        """
        is_fn_ptr = isinstance(f_type, FnType) or (
            isinstance(f_type, RefType) and isinstance(f_type.target, FnType)
        )
        if isinstance(f_type, ArrayType) and f_type.size is not None:
            inner = f_type.element
            inner_fn = isinstance(inner, FnType) or (
                isinstance(inner, RefType) and isinstance(inner.target, FnType)
            )
            if inner_fn:
                return CTypeMapper.to_c_decl(inner, f"{ident}[{f_type.size}]")
            return f"{CTypeMapper.to_c_type(inner)} {ident}[{f_type.size}]"
        if is_fn_ptr:
            return CTypeMapper.to_c_decl(f_type, ident)
        return f"{CTypeMapper.to_c_type(f_type)} {ident}"
    def _member_sep(self, obj_type: Optional[Type], obj_expr: str = "") -> str:
        """Returns '.' or '->' for accessing a member of a receiver expression.

        ``self`` is a pointer inside an enchanting method of a rune/collection
        and a ``ref to T`` receiver is a pointer too, so both need ``->``.  In a
        method of a *primitive* (or a bare ``shard T``) ``self`` is the value
        itself, so it needs ``.`` -- ``self->x`` is not even reachable there,
        because the checker rejects it with E0003.
        """
        if obj_expr == "self":
            return "." if getattr(self, "current_self_is_value", False) else "->"
        if isinstance(obj_type, RefType):
            return "->"
        return "."
    def _omen_variant_expr(self, omen_name: str, variant_name: str,
                           expected_type: Optional[Type] = None) -> str:
        """C expression for a bare omen variant reference.

        Simple omens are C enums, so the variant *is* the tag.  For an
        algebraic omen a payload-less variant needs to become a value of the
        tagged struct: ``(Shape){ .tag = Shape_Point }``.  Payload variants
        cannot be referenced bare (they are built with ``with Variant is …``),
        and pattern-matching positions receive no ``expected_type``, so they
        keep the raw tag.
        """
        variants = self.omens.get(omen_name, {})
        tag = self._get_omen_variant_c_name(omen_name, variant_name)
        is_algebraic = any(bool(f) for f in variants.values())
        if not is_algebraic or variants.get(variant_name):
            return tag
        et = expected_type
        while isinstance(et, (AliasType, FrozenType, SealType)):
            et = getattr(et, "target", None) or getattr(et, "underlying", None)
        if isinstance(et, OmenType):
            et_name = getattr(et, "c_name", None) or getattr(et, "name", "")
            if et_name in (omen_name, getattr(et, "name", "")):
                return f"({omen_name}){{ .tag = {tag} }}"
        return tag
