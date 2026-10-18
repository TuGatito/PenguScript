"""LSP surface for the three 2.10.0 data modules.

Completion on a `JsonValue`, a `DiagnosticBag` and a `JsonRpcMessage`, plus
hover and go-to-definition into `std/json.pengu`. These go through the real
server entry points, like `test_fundamental_modules.py`.
"""
from __future__ import annotations

import pytest
from lsprotocol.types import Position

pytestmark = pytest.mark.smoke

SOURCE = '''import std.spark
import std.json
import std.diagnostic as diag
import std.jsonrpc as rpc

weave main into int:
    var root as JsonValue is calling JsonValue.null_value
    defer banish root
    var bag as DiagnosticBag is calling DiagnosticBag.new
    defer banish bag
    var msg as JsonRpcMessage is calling rpc.notification with "x", (maybe none)
    defer banish msg
    var is_n as bool is calling root.is_null
    var bag_text as string is calling bag.render_plain
    defer banish bag_text
    var kind as string is calling msg.kind_name
    defer banish kind
    var text as string is calling json.stringify with root
    defer banish text
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


def test_json_value_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("root."))
    assert {"pointer", "get", "at", "as_string", "as_int", "clone", "free", "equals"} <= labels, labels


def test_diagnostic_bag_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("bag."))
    assert {"add", "extend", "render", "render_plain", "render_colored", "render_json", "errors_only", "clear"} <= labels, labels


def test_jsonrpc_message_methods_complete(lsp):
    lsp.open(SOURCE)
    labels = set(lsp.complete_after("msg."))
    assert {"equals", "kind_name"} <= labels, labels


def test_json_value_hover_shows_the_method(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    hover = get_hover(lsp.uri, _position(SOURCE, "root.is_null", offset=5), lsp.symbols, SOURCE)
    assert hover is not None
    assert "is_null" in hover.contents.value, hover.contents.value


def test_json_module_function_hover(lsp):
    from pengu_lsp.hover import get_hover

    lsp.open(SOURCE)
    hover = get_hover(lsp.uri, _position(SOURCE, "json.stringify", offset=5), lsp.symbols, SOURCE)
    assert hover is not None
    assert "stringify" in hover.contents.value, hover.contents.value


def test_json_value_definition_jumps_to_the_module(lsp):
    from pengu_lsp import server as lsp_server
    from lsprotocol.types import DefinitionParams, TextDocumentIdentifier

    lsp.open(SOURCE)
    params = DefinitionParams(
        text_document=TextDocumentIdentifier(uri=lsp.uri),
        position=_position(SOURCE, "JsonValue", occurrence=1),
    )
    location = lsp_server.definition(params)
    assert location is not None
    assert location.uri.endswith("std/json.pengu"), location
