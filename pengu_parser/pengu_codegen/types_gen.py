"""C struct/union/enum definitions and their forward declarations.

Part of :class:`~pengu_parser.pengu_codegen.main.PenguCodegen`; see
:mod:`pengu_parser.pengu_codegen` for the assembled generator.
"""
from __future__ import annotations

from ._base import (
    AliasType,
    ArrayType,
    BaseType,
    FnType,
    FrozenType,
    OmenType,
    Optional,
    RefType,
    SealType,
    Type,
)
from .ctype import (
    CTypeMapper,
)

class TypesMixin:
    """C struct/union/enum definitions and their forward declarations."""

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
                if isinstance(f_type, ArrayType) and f_type.size is not None:
                    elem_str = CTypeMapper.to_c_type(f_type.element)
                    rune_lines.append(
                        f"  {fa_prefix}{elem_str} {self._c_ident(f_name)}[{f_type.size}]{fa_str};")
                else:
                    f_str = CTypeMapper.to_c_type(f_type)
                    rune_lines.append(f"  {fa_prefix}{f_str} {self._c_ident(f_name)}{fa_str};")
            rune_lines.append("};" + packed_suffix)
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
            is_string_valued = bool(name in self.omen_values and any(isinstance(v, str) for v in self.omen_values[name].values()))
            if not is_algebraic and not is_string_valued:
                # Plain enums have no valid C forward declaration (`typedef enum
                # X X;` is a GNU extension and redefining it is invalid): they
                # are emitted complete in the forward-declarations block.
                continue
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
    @staticmethod
    def _member_sep(obj_type: Optional[Type], obj_expr: str = "") -> str:
        """Returns '.' or '->' for accessing a member of a receiver expression.

        ``self`` is always a pointer inside an enchanting method, and a
        ``ref to T`` receiver is a pointer too, so both need ``->``.
        """
        if obj_expr == "self":
            return "->"
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
