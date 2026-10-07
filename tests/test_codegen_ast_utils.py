#!/usr/bin/env python3
"""The shared AST helpers in `pengu_parser/pengu_codegen/ast_utils.py`.

These four functions are called from both the collection pass and the
translation pass, and each of them documents a *shape* tolerance that no test
pinned:

* `_normalize_banish_ident` unwraps only *balanced* outer parentheses, so a C
  expression like `(a) + (b)` keeps its grouping;
* `_extract_attributes_from_node` accepts attribute arguments as INT, string or
  bare tokens, and as nested trees;
* `skip_weave_modifiers` accepts both the grammar's `weave_modifier` wrapper and
  the older bare-token spelling;
* `flatten_at_chain` copes with either association the parser may produce for a
  chained `at`.

They are pure functions over hand-built trees, so the tests need no parser run
and behave identically on every platform.
"""

from __future__ import annotations

from lark import Token, Tree

from pengu_parser.pengu_codegen.ast_utils import (
    _extract_attributes_from_node,
    _normalize_banish_ident,
    flatten_at_chain,
    get_generic_ast_name,
    skip_weave_modifiers,
    unwrap_top_level,
)


class TestNormalizeBanishIdent:
    def test_outer_parentheses_are_stripped_with_whitespace(self):
        assert _normalize_banish_ident("  (( x ))  ") == "x"

    def test_only_balanced_parentheses_are_stripped(self):
        """`(a) + (b)` must keep its grouping: the parens do not enclose it."""
        assert _normalize_banish_ident("(a) + (b)") == "(a) + (b)"

    def test_a_single_character_is_left_alone(self):
        assert _normalize_banish_ident("(") == "("

    def test_inner_parentheses_survive(self):
        assert _normalize_banish_ident("((a)[0])") == "(a)[0]"

    def test_an_unparenthesised_name_is_returned_as_is(self):
        assert _normalize_banish_ident(" value ") == "value"


class TestExtractAttributesFromNode:
    @staticmethod
    def _attributes(*attr_trees):
        return Tree("attributes", list(attr_trees))

    @staticmethod
    def _attribute(name, *args):
        return Tree("attribute", [Token("NAME", name), Tree("attribute_args", list(args))])

    def test_an_integer_argument_is_kept_as_an_int(self):
        children = [self._attributes(self._attribute("size", Token("INT", "8")))]
        attrs, idx = _extract_attributes_from_node(children)
        assert attrs == {"size": [8]}
        assert idx == 1

    def test_string_arguments_lose_their_quotes(self):
        children = [self._attributes(
            self._attribute("doc", Token("STRING", '"hello"')),
            self._attribute("raw", Token("RAW_STRING", '"r"')),
        )]
        attrs, _ = _extract_attributes_from_node(children)
        assert attrs == {"doc": ["hello"], "raw": ["r"]}

    def test_a_bare_token_argument_is_read_as_a_number_when_it_is_one(self):
        children = [self._attributes(
            self._attribute("count", Token("NAME", "12")),
            self._attribute("symbol", Token("NAME", "other")),
        )]
        attrs, _ = _extract_attributes_from_node(children)
        assert attrs == {"count": [12], "symbol": ["other"]}

    def test_a_nested_tree_argument_is_unwrapped_to_its_text(self):
        inner = Tree("string_lit", [Token("STRING", '"nested"')])
        children = [self._attributes(self._attribute("name", inner))]
        attrs, _ = _extract_attributes_from_node(children)
        assert attrs == {"name": ["nested"]}

    def test_a_node_without_attributes_reports_the_start_index(self):
        children = [Tree("weave_decl", [Token("NAME", "f")])]
        attrs, idx = _extract_attributes_from_node(children, start_idx=0)
        assert attrs == {}
        assert idx == 0

    def test_several_attributes_are_collected_together(self):
        children = [self._attributes(
            self._attribute("a", Token("INT", "1")),
            self._attribute("b", Token("INT", "2")),
        )]
        attrs, _ = _extract_attributes_from_node(children)
        assert attrs == {"a": [1], "b": [2]}


class TestSkipWeaveModifiers:
    def test_the_grammar_wrapper_shape_is_recognised(self):
        children = [Tree("weave_modifier", [Token("INLINE", "inline")])]
        assert skip_weave_modifiers(children) == (True, False, 1)

    def test_the_legacy_bare_token_shape_is_still_accepted(self):
        """Older callers put the modifier tokens straight into the child list."""
        assert skip_weave_modifiers([Token("INLINE", "inline")]) == (True, False, 1)
        assert skip_weave_modifiers([Token("RITUAL", "ritual")]) == (False, True, 1)

    def test_both_modifiers_are_reported(self):
        children = [
            Tree("weave_modifier", [Token("INLINE", "inline")]),
            Tree("weave_modifier", [Token("RITUAL", "ritual")]),
        ]
        assert skip_weave_modifiers(children) == (True, True, 2)

    def test_leading_attribute_trees_are_skipped_first(self):
        children = [
            Tree("attributes", []),
            Tree("weave_modifier", [Token("RITUAL", "ritual")]),
            Token("NAME", "f"),
        ]
        assert skip_weave_modifiers(children) == (False, True, 2)

    def test_an_unrelated_child_stops_the_scan(self):
        children = [Token("NAME", "f")]
        assert skip_weave_modifiers(children) == (False, False, 0)


class TestGetGenericAstName:
    def test_a_plain_weave_declaration_yields_its_name(self):
        node = Tree("weave_decl", [Token("NAME", "compute")])
        assert get_generic_ast_name(node) == "compute"

    def test_the_name_is_read_after_the_modifiers(self):
        node = Tree("weave_decl", [
            Tree("weave_modifier", [Token("INLINE", "inline")]),
            Token("NAME", "compute"),
        ])
        assert get_generic_ast_name(node) == "compute"

    def test_a_non_declaration_node_yields_nothing(self):
        assert get_generic_ast_name(Token("NAME", "x")) is None

    def test_a_declaration_without_a_name_yields_nothing(self):
        node = Tree("weave_decl", [Tree("weave_modifier", [Token("INLINE", "inline")])])
        assert get_generic_ast_name(node) is None


class TestUnwrapTopLevel:
    def test_nested_top_stmts_collapse_to_the_declaration(self):
        decl = Tree("weave_decl", [Token("NAME", "f")])
        node = Tree("top_stmt", [Tree("top_stmt", [decl])])
        assert unwrap_top_level(node) is decl

    def test_a_plain_declaration_is_returned_unchanged(self):
        decl = Tree("weave_decl", [])
        assert unwrap_top_level(decl) is decl

    def test_none_passes_through(self):
        assert unwrap_top_level(None) is None


class TestFlattenAtChain:
    def test_a_non_index_expression_is_its_own_chain(self):
        leaf = Token("NAME", "xs")
        assert flatten_at_chain(leaf) == [leaf]

    def test_a_left_nested_chain_is_flattened(self):
        a, b, c = Token("NAME", "a"), Token("INT", "0"), Token("INT", "1")
        node = Tree("at_expr", [Tree("at_expr", [a, b]), c])
        assert flatten_at_chain(node) == [a, b, c]

    def test_a_right_nested_chain_is_flattened(self):
        a, b, c = Token("NAME", "a"), Token("INT", "0"), Token("INT", "1")
        node = Tree("at_expr", [a, Tree("at_expr", [b, c])])
        assert flatten_at_chain(node) == [a, b, c]

    def test_a_single_index_is_a_two_element_chain(self):
        a, b = Token("NAME", "a"), Token("INT", "0")
        assert flatten_at_chain(Tree("at_expr", [a, b])) == [a, b]
