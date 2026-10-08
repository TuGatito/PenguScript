#!/usr/bin/env python3
"""Hover markdown for `echo`, `omen` and `import` symbols.

`tests/lsp/test_lsp.py` covers hover for weaves, runes, locals and keywords.  The
tagged-union (`echo`), algebraic-data-type (`omen`) and module (`import`) shapes
the checker produces were never rendered through
:func:`pengu_lsp.hover.format_symbol_hover`, so the markdown a user actually
sees for those three declarations was unpinned.

These are unit tests on the renderer itself -- the same function
``get_hover`` hands to the client -- so they need no server session and assert
on the contract the LSP advertises: the declaration echo, the field/variant
listing with its size estimate, and the exported-symbol list of a module.
"""

from __future__ import annotations

from pengu_lsp.hover import format_symbol_hover
from pengu_parser.pengu_symbols import Scope, Symbol
from pengu_parser.pengu_types import (
    BOOL_TYPE,
    EchoType,
    FLOAT_TYPE,
    INT_TYPE,
    OmenType,
    STRING_TYPE,
)


class TestEchoHover:
    """`echo` is a C-compatible tagged union: fields overlap in memory."""

    def test_lists_every_field_with_its_size(self):
        echoed = EchoType(name="Value", fields={"i": INT_TYPE, "f": FLOAT_TYPE})
        md = format_symbol_hover(Symbol(name="Value", type=echoed, kind="echo"))

        assert "**Tagged Union Type**" in md
        assert "echo Value" in md
        assert "i as int" in md
        assert "f as float" in md
        # Each field line carries `N bits / N bytes`.
        assert md.count("bits /") >= 2

    def test_reports_the_union_total_size_in_bits_and_bytes(self):
        echoed = EchoType(name="Small", fields={"b": BOOL_TYPE})
        md = format_symbol_hover(Symbol(name="Small", type=echoed, kind="echo"))
        assert "Total size:" in md
        assert "bits /" in md

    def test_an_empty_union_is_labelled_instead_of_listing_nothing(self):
        md = format_symbol_hover(
            Symbol(name="Opaque", type=EchoType(name="Opaque", fields={}), kind="echo")
        )
        assert "(opaque or empty)" in md


class TestOmenHover:
    """`omen` is the algebraic data type: variants with payload fields."""

    def test_lists_variants_and_their_payloads(self):
        omen = OmenType(
            name="Shape",
            variants={"Circle": {"radius": FLOAT_TYPE}, "Point": {}},
        )
        md = format_symbol_hover(Symbol(name="Shape", type=omen, kind="omen"))

        assert "**Algebraic Data Type / Enum**" in md
        assert "omen Shape" in md
        assert "Circle with radius as float" in md
        # A payload-less variant is listed by name alone.
        assert "Point" in md
        assert "Point with" not in md

    def test_variant_payload_size_is_reported_per_field(self):
        omen = OmenType(name="Node", variants={"Leaf": {"label": STRING_TYPE}})
        md = format_symbol_hover(Symbol(name="Node", type=omen, kind="omen"))
        assert "label as string" in md
        assert "bits /" in md

    def test_a_variant_less_omen_is_labelled(self):
        md = format_symbol_hover(
            Symbol(name="Bare", type=OmenType(name="Bare", variants={}), kind="omen")
        )
        assert "(variants)" in md


class TestImportHover:
    """Hovering an imported module must show what the module exports."""

    @staticmethod
    def _module(path: str):
        scope = Scope(kind="global")
        scope.define(Symbol(name="println", type=INT_TYPE, kind="weave"))
        scope.define(Symbol(name="spark_version", type=STRING_TYPE, kind="weave"))
        scope.define(Symbol(name="_internal", type=INT_TYPE, kind="weave"))
        return Symbol(name=path, type=INT_TYPE, kind="import", module_scope=scope)

    def test_lists_the_public_exports_sorted(self):
        md = format_symbol_hover(self._module("std.spark"))

        assert "**Imported Module**" in md
        assert "import std.spark" in md
        assert "**Exported symbols**" in md
        assert md.index("`println`") < md.index("`spark_version`")

    def test_private_exports_are_not_advertised(self):
        md = format_symbol_hover(self._module("std.spark"))
        assert "_internal" not in md

    def test_a_module_without_a_scope_still_renders(self):
        md = format_symbol_hover(
            Symbol(name="std.empty", type=INT_TYPE, kind="import", module_scope=None)
        )
        assert "import std.empty" in md
        assert "**Exported symbols**" not in md


class TestBindingHover:
    """Locals, constants and C-bound globals share the final fallback branch."""

    def test_mutable_binding_is_marked_mut(self):
        md = format_symbol_hover(
            Symbol(name="counter", type=INT_TYPE, kind="var", is_mutable=True)
        )
        assert "var mut counter as int" in md
        assert "bits /" in md

    def test_immutable_binding_carries_no_mut_marker(self):
        md = format_symbol_hover(
            Symbol(name="limit", type=INT_TYPE, kind="let", is_mutable=False)
        )
        assert "let limit as int" in md
        assert "let mut" not in md

    def test_constant_value_is_shown(self):
        md = format_symbol_hover(
            Symbol(name="MAX_USERS", type=INT_TYPE, kind="const", const_val=1024)
        )
        assert "const MAX_USERS as int" in md
        assert "= 1024" in md

    def test_c_bound_global_is_annotated(self):
        md = format_symbol_hover(
            Symbol(name="errno_like", type=INT_TYPE, kind="const",
                   is_defined_in_c=True)
        )
        assert "*(C header foreign symbol)*" in md

    def test_an_unknown_type_renders_as_unknown(self):
        md = format_symbol_hover(Symbol(name="mystery", type=None, kind="var"))
        assert "as unknown" in md

    def test_method_names_are_attached(self):
        md = format_symbol_hover(
            Symbol(name="items", type=INT_TYPE, kind="var"),
            method_names=["len", "push"],
        )
        assert "**Methods**: `len`, `push`" in md

    def test_doc_text_is_appended_after_a_separator(self):
        md = format_symbol_hover(
            Symbol(name="items", type=INT_TYPE, kind="var", doc="The item list.")
        )
        assert "---" in md
        assert "The item list." in md
