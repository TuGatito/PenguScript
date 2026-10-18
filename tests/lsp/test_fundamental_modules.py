"""LSP surface for the four fundamental std modules.

Completion is the user-visible contract an editor sees while typing
``sb.``/``a.``/``sm.``/``bs.``; hover is the fallback that keeps a method's
docstring discoverable.  Both go through the real server entry points.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import Position

pytestmark = pytest.mark.smoke

SOURCE = '''import std.spark
import std.builder
import std.arena
import std.sourcemap
import std.bitset

weave main into int:
    var sb as StringBuilder is calling StringBuilder.new
    defer banish sb
    calling sb.append with "x"
    var a as Arena is calling Arena.new
    defer calling a.free
    var sm as SourceMap is calling SourceMap.from_source with "x"
    defer banish sm
    var p as Position is calling sm.position_at with 0
    var bs as BitSet is calling BitSet.new with 8
    defer banish bs
    calling bs.set with 0
    return 0
'''


def _position(text: str, needle: str, occurrence: int = 1, offset: int = 1) -> Position:
    seen = 0
    for line_no, line in enumerate(text.splitlines()):
        start = 0
        while True:
            found = line.find(needle, start)
            if found < 0:
                break
            seen += 1
            if seen == occurrence:
                return Position(line=line_no, character=found + offset)
            start = found + len(needle)
    raise AssertionError(f"{needle!r} (occurrence {occurrence}) not found")


def test_builder_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("sb."))
    assert {"append", "append_char", "append_int", "insert_at", "finish", "to_string", "reserve"} <= labels, labels


def test_arena_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("a."))
    assert {"alloc", "alloc_aligned", "alloc_str", "alloc_cstr", "reset", "free"} <= labels, labels


def test_sourcemap_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("sm."))
    assert {"position_at", "offset_of", "line_text", "line_span", "span_at", "clamp_offset"} <= labels, labels


def test_bitset_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("bs."))
    assert {"set", "clear", "toggle", "get", "and_with", "not", "find_first_set", "iter_set", "to_bytes"} <= labels, labels


def test_builder_hover_shows_the_method_signature(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    hover = get_hover(lsp.uri, _position(SOURCE, "sb.append", offset=4), lsp.symbols, SOURCE)
    assert hover is not None
    value = hover.contents.value
    assert "append" in value, value


def test_sourcemap_hover_shows_the_method_signature(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    hover = get_hover(lsp.uri, _position(SOURCE, "SourceMap.from_source", offset=10), lsp.symbols, SOURCE)
    assert hover is not None
    assert "from_source" in hover.contents.value, hover.contents.value

def test_type_definition_jumps_to_the_module_file(lsp):
    from pengu_lsp import server as lsp_server
    from lsprotocol.types import DefinitionParams, TextDocumentIdentifier

    lsp.open(SOURCE)
    params = DefinitionParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=_position(SOURCE, "StringBuilder", occurrence=1),
    )
    location = lsp_server.definition(params)
    assert location is not None
    assert location.uri.endswith("std/builder.pengu"), location
    assert location.range.start.line >= 0, location
