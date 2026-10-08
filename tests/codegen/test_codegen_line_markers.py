#!/usr/bin/env python3
"""`#line` marker emission (`pengu_parser/pengu_codegen/line_markers.py`).

These markers are what make a C diagnostic from generated code point back at the
`.pengu` line the user wrote, so their *edge* behaviour is user-visible:

* a node with no usable position yields no marker rather than `#line None`;
* a rebuilt declaration that lost its `meta` block still resolves through its
  first descendant token;
* a path that cannot be made relative (a different Windows drive) falls back to
  the absolute one, and a missing path degrades to a bare `#line N`;
* with markers disabled -- and for generated sections -- the emitter stays
  silent or resets attribution to the bundle.

``LineMarkerMixin`` is a plain mixin: it can be instantiated and its
configuration attributes set directly, which is what these tests do.
"""

from __future__ import annotations

import os

import pytest
from lark import Token, Tree

from pengu_parser.pengu_codegen.line_markers import LineMarkerMixin


def _mixin(tmp_path=None, emit=True, base_dir=None, bundle_path=None,
           current_file=None):
    m = LineMarkerMixin()
    m.emit_line_markers = emit
    m.line_base_dir = base_dir
    m.bundle_display_path = bundle_path
    m.current_source_file = current_file
    return m


class TestNodeLine:
    """`_node_line` picks the first usable line number it can find."""

    def test_none_yields_no_line(self):
        assert LineMarkerMixin._node_line(None) is None

    def test_a_direct_line_attribute_wins(self):
        node = Tree("stmt", [])
        node.line = 12
        assert LineMarkerMixin._node_line(node) == 12

    def test_a_non_numeric_direct_line_is_ignored(self):
        """Some rebuilt nodes carry a placeholder where the line should be."""
        node = Tree("stmt", [])
        node.line = "not-a-number"
        assert LineMarkerMixin._node_line(node) is None

    def test_lark_meta_is_used_when_there_is_no_line_attribute(self):
        node = Tree("stmt", [], meta=None)
        node.meta.line = 34
        assert LineMarkerMixin._node_line(node) == 34

    def test_a_non_numeric_meta_line_is_ignored(self):
        node = Tree("stmt", [], meta=None)
        node.meta.line = "?"
        assert LineMarkerMixin._node_line(node) is None

    def test_a_descendant_token_is_the_last_resort(self):
        """A collector-rebuilt node keeps no position; its tokens still do."""
        token = Token("NAME", "x", line=77)
        node = Tree("stmt", [Tree("expr", [token])], meta=None)
        assert LineMarkerMixin._node_line(node) == 77

    def test_a_descendant_meta_line_is_accepted_too(self):
        child = Tree("expr", [], meta=None)
        child.meta.line = 91
        node = Tree("stmt", [child], meta=None)
        assert LineMarkerMixin._node_line(node) == 91

    def test_unusable_positions_anywhere_yield_no_line(self):
        child = Tree("expr", [], meta=None)
        child.line = "nope"
        child.meta.line = "nope"
        node = Tree("stmt", [child], meta=None)
        assert LineMarkerMixin._node_line(node) is None


class TestDisplayPath:
    """`_display_path` keeps the path short and machine independent."""

    def test_a_missing_path_has_no_display_form(self):
        assert _mixin()._display_path(None) is None
        assert _mixin()._display_path("") is None

    def test_the_path_is_relative_to_the_bundle_directory(self, tmp_path):
        src = tmp_path / "src" / "main.pengu"
        src.parent.mkdir(parents=True)
        src.write_text("", encoding="utf-8")
        shown = _mixin(base_dir=str(tmp_path / "out"))._display_path(str(src))
        assert shown == "../src/main.pengu"

    def test_separators_are_normalised_to_forward_slashes(self, tmp_path):
        shown = _mixin()._display_path(str(tmp_path / "a" / "b.pengu"))
        assert "\\" not in shown

    def test_an_unrelatable_path_falls_back_to_the_absolute_one(self, tmp_path,
                                                              monkeypatch):
        """`os.path.relpath` raises for paths on different Windows drives."""
        def boom(*_args, **_kwargs):
            raise ValueError("path is on mount 'D:', start on mount 'C:'")

        monkeypatch.setattr(os.path, "relpath", boom)
        src = tmp_path / "main.pengu"
        src.write_text("", encoding="utf-8")
        assert _mixin(base_dir="C:/other")._display_path(str(src)) == str(
            os.path.abspath(src)
        )


class TestLineMarker:
    """The directive itself, including the disabled and unknown-line cases."""

    def test_markers_can_be_turned_off(self):
        assert _mixin(emit=False)._line_marker(3, "x.pengu") == ""

    def test_an_unknown_line_emits_nothing(self):
        assert _mixin()._line_marker(None, "x.pengu") == ""

    def test_a_raw_integer_is_accepted_as_the_line(self):
        # `_display_path` normalises through abspath, so the expectation is
        # built the same way instead of hard-coding the checkout location.
        shown = os.path.abspath("src/main.pengu").replace("\\", "/")
        assert _mixin()._line_marker(42, "src/main.pengu") == (
            f'#line 42 "{shown}"'
        )

    def test_a_node_resolves_through_the_node_line_helper(self):
        node = Tree("stmt", [], meta=None)
        node.meta.line = 7
        shown = os.path.abspath("a.pengu").replace("\\", "/")
        assert _mixin()._line_marker(node, "a.pengu") == f'#line 7 "{shown}"'

    def test_without_a_file_the_directive_is_bare(self):
        assert _mixin()._line_marker(5, "") == "#line 5"

    def test_quotes_in_the_path_are_escaped(self):
        path = os.path.abspath('we"ird.pengu').replace("\\", "/")
        marker = _mixin()._line_marker(5, 'we"ird.pengu')
        assert marker == '#line 5 "' + path.replace('"', '\\"') + '"'


class TestGeneratedReset:
    """Generated sections restore attribution to the bundle itself."""

    def test_disabled_markers_emit_nothing(self):
        assert _mixin(emit=False)._generated_c_reset() == ""

    def test_the_bundle_path_is_spelled_when_known(self):
        m = _mixin(bundle_path="build/bundle.c")
        assert m._generated_c_reset() == '#line 1 "build/bundle.c"'

    def test_without_a_bundle_path_a_bare_reset_is_emitted(self):
        assert _mixin()._generated_c_reset() == "#line 1"

    def test_the_current_source_file_is_the_default_for_a_marker(self):
        current = os.path.abspath("src/here.pengu")
        m = _mixin(current_file=current)
        shown = current.replace("\\", "/")
        assert m._line_marker(9) == f'#line 9 "{shown}"'
