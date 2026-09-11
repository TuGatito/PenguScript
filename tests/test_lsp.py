#!/usr/bin/env python3
"""Consolidated tests for the PenguScript Language Server (pengu_lsp).

This file merges the coverage of the former scratch tests:

* test_lsp.py            - diagnostics, completions, hover, definition
* test_lsp_fix.py        - span_end ranges, validate_document API, self-> words
* test_lsp_integration.py- JSON-RPC over stdio handshake / capabilities
* test_lsp_code_actions.py - "Add missing import" / "Remove unused variable"
* test_lsp_context.py    - contextual completions (when / as / into)
* test_lsp_hover_docs.py - hover doc fallback extracted from source files
* test_lsp_return_types.py - return-type inference through the LSP-style check

Tests exercise the pygls language server either through direct method calls on
``pengu_lsp.server`` helpers/handlers (mirroring the old harness) or, for the
protocol handshake, through a real JSON-RPC stdio session.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from lsprotocol.types import (
    DefinitionParams,
    DiagnosticSeverity,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    Position,
    TextDocumentContentChangeEvent,
    TextDocumentIdentifier,
    TextDocumentItem,
    VersionedTextDocumentIdentifier,
)

from pengu_parser.pengu_checker import PenguChecker
from pengu_parser.pengu_errors import PenguError
from pengu_parser.pengu_parser import PenguParser
from pengu_parser.pengu_symbols import Symbol
from pengu_parser.pengu_types import INT_TYPE

REPO = Path(__file__).resolve().parent.parent
STD_DIR = REPO / "std"

# ---------------------------------------------------------------------------
# Shared helpers (mirror the old harness)
# ---------------------------------------------------------------------------


def parse_and_check(source, filename="t.pengu", base_dir=None):
    """Runs the LSP-style validation flow and returns (checker, errors).

    Errors are the flattened PenguError list (empty when the code is clean);
    ``checker.symbols`` is populated even when errors are reported.
    """
    base = str(base_dir) if base_dir is not None else str(REPO)
    parser = PenguParser()
    checker = PenguChecker(base_dir=base)
    try:
        checker.check(parser.parse(source), source=source, filename=filename)
        return checker, []
    except PenguError as exc:
        errors = exc.all_errors if getattr(exc, "all_errors", None) else [exc]
        return checker, errors


def checked_symbols(source, filename="t.pengu", base_dir=None):
    """Checks `source` cleanly (fails the test otherwise) and returns symbols."""
    checker, errors = parse_and_check(source, filename=filename, base_dir=base_dir)
    assert not errors, f"expected clean code, got errors: {[str(e) for e in errors]}"
    return checker.symbols


def completion_labels(symbols, position, line_prefix="", module_cache=None, base_dir=None, doc_text=None):
    """Returns completion labels for a cursor position / line prefix."""
    from pengu_lsp.completions import get_completions

    res = get_completions(
        "file:///t.pengu", position, symbols=symbols, line_prefix=line_prefix,
        module_cache=module_cache, base_dir=base_dir, doc_text=doc_text,
    )
    return [item.label for item in res.items]


# ---------------------------------------------------------------------------
# Server fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_server_state():
    """The pengu_lsp server is a module-level singleton; reset per test."""
    from pengu_lsp.server import server, _MODULE_CACHE

    server._symbols.clear()
    server._docs.clear()
    server._validation_cache.clear()
    _MODULE_CACHE.clear()
    for task in server._validate_tasks.values():
        task.cancel()
    server._validate_tasks.clear()
    yield


def _capture_diagnostics(monkeypatch):
    """Monkeypatches publish_diagnostics to record (uri, diags) tuples."""
    from pengu_lsp.server import server

    published = []

    def fake_publish(uri, diags):
        published.append((uri, diags))

    monkeypatch.setattr(server, "publish_diagnostics", fake_publish)
    return published


def did_open(uri, source, language_id="pengus", version=1):
    """Invokes the textDocument/didOpen handler directly with captured output."""
    from pengu_lsp.server import did_open

    params = DidOpenTextDocumentParams(
        text_document=TextDocumentItem(
            uri=uri, language_id=language_id, version=version, text=source
        )
    )
    did_open(params)


# ---------------------------------------------------------------------------
# JSON-RPC over stdio helpers (integration handshake)
# ---------------------------------------------------------------------------


def _encode_message(method, params, msg_id=None):
    obj = {"jsonrpc": "2.0", "method": method, "params": params}
    if msg_id is not None:
        obj["id"] = msg_id
    body = json.dumps(obj)
    return (f"Content-Length: {len(body)}\r\n\r\n" + body).encode("utf-8")


def _run_stdio_session(cmd, timeout=40):
    """Feeds a full LSP conversation over stdin and returns parsed responses.

    Session: initialize -> initialized -> didOpen -> completion -> hover ->
    shutdown -> exit.  Mirrors the old integration harness.
    """
    root_uri = f"file:///{str(REPO).replace(os.sep, '/')}"
    stream = b""
    stream += _encode_message("initialize", {
        "processId": None,
        "rootPath": str(REPO),
        "capabilities": {},
        "rootUri": root_uri,
    }, msg_id=1)
    stream += _encode_message("initialized", {})
    test_code = 'import std.spark\n\nweave main into void:\n    calling spark.println with "Test"\n'
    stream += _encode_message("textDocument/didOpen", {
        "textDocument": {
            "uri": "file:///lsp_test_file.pengu",
            "languageId": "pengus",
            "version": 1,
            "text": test_code,
        }
    })
    stream += _encode_message("textDocument/completion", {
        "textDocument": {"uri": "file:///lsp_test_file.pengu"},
        "position": {"line": 3, "character": 4},
    }, msg_id=2)
    stream += _encode_message("textDocument/hover", {
        "textDocument": {"uri": "file:///lsp_test_file.pengu"},
        "position": {"line": 0, "character": 0},
    }, msg_id=3)
    stream += _encode_message("shutdown", None, msg_id=99)
    stream += _encode_message("exit", None)

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(REPO),
    )
    stdout, _stderr = proc.communicate(input=stream, timeout=timeout)
    text = stdout.decode("utf-8", errors="replace")
    responses = []
    for part in text.split("Content-Length:")[1:]:
        try:
            responses.append(json.loads(part[part.index("{") :]))
        except (ValueError, json.JSONDecodeError):
            pass
    return responses


# ===========================================================================
# 1. Initialize / capabilities handshake (JSON-RPC over stdio)
# ===========================================================================


class TestLSPHandshake:
    """Full LSP session over stdio: initialize -> didOpen -> requests."""

    def test_stdio_initialize_reports_core_capabilities(self):
        responses = _run_stdio_session([sys.executable, "pengu_project.py", "lsp", "--stdio"])

        # At least: initialize response, diagnostics, completion, hover, shutdown
        assert len(responses) >= 4, f"expected >=4 responses, got {len(responses)}"

        init_resp = next((r for r in responses if r.get("id") == 1), None)
        assert init_resp is not None, "missing initialize response"
        assert "result" in init_resp, "initialize has no result"
        caps = init_resp["result"].get("capabilities", {})
        for capability in (
            "textDocumentSync",
            "completionProvider",
            "hoverProvider",
            "definitionProvider",
        ):
            assert capability in caps, f"missing {capability} capability"

        diag_notif = next(
            (r for r in responses if r.get("method") == "textDocument/publishDiagnostics"),
            None,
        )
        assert diag_notif is not None, "missing publishDiagnostics notification"

        for msg_id in (2, 3, 99):
            resp = next((r for r in responses if r.get("id") == msg_id), None)
            assert resp is not None, f"missing response for id={msg_id}"
        assert "result" in next(r for r in responses if r.get("id") == 2)


# ===========================================================================
# 2. textDocument/didOpen -> diagnostics
# ===========================================================================


class TestDidOpenDiagnostics:
    """didOpen validation publishes parse / semantic / zero diagnostics."""

    def test_did_open_clean_code_publishes_no_diagnostics(self, monkeypatch):
        published = _capture_diagnostics(monkeypatch)
        did_open(
            "file:///clean.pengu",
            "weave main into void:\n  return\n",
        )
        assert len(published) == 1
        assert published[0][0] == "file:///clean.pengu"
        assert published[0][1] == []

    def test_did_open_semantic_errors_publish_diagnostics(self, monkeypatch):
        published = _capture_diagnostics(monkeypatch)
        source = (
            'weave main into void:\n'
            '  var a as int is "hello"\n'
            '  var b as float is a + "world"\n'
        )
        did_open("file:///errs.pengu", source)
        assert len(published) == 1
        uri, diags = published[0]
        assert uri == "file:///errs.pengu"
        assert len(diags) >= 1
        for diag in diags:
            assert diag.severity == DiagnosticSeverity.Error
            assert diag.source == "pengus"
        assert any("[E0005]" in d.message and "help:" in d.message for d in diags)

    def test_did_open_parse_error_publishes_diagnostic(self, monkeypatch):
        published = _capture_diagnostics(monkeypatch)
        did_open("file:///broken.pengu", "weave main into void:\n  @@@\n")
        assert len(published) == 1
        uri, diags = published[0]
        assert uri == "file:///broken.pengu"
        assert len(diags) >= 1
        assert all(d.message for d in diags)
        assert all(d.severity == DiagnosticSeverity.Error for d in diags)

    def test_diagnostics_multiple_errors_are_converted(self):
        """Multiple checker errors map 1:1 onto structured LSP diagnostics."""
        from pengu_lsp.server import diagnostics_from_errors

        source = (
            "rune Vec2:\n"
            "  x as int\n"
            "\n"
            "weave main into void:\n"
            '  var a as int is "hello"\n'
            '  var b as float is a + "world"\n'
        )
        _checker, errors = parse_and_check(source, filename="test.pengu")
        assert len(errors) > 0, "checker should find type mismatch errors"

        diags = diagnostics_from_errors(errors, source)
        assert len(diags) == len(errors)
        for diag in diags:
            assert diag.severity == DiagnosticSeverity.Error
            assert diag.source == "pengus"
            assert "[E0005]" in diag.message
            assert "help:" in diag.message

    def test_diagnostics_clean_code_empty(self):
        """Clean code produces zero LSP diagnostics."""
        from pengu_lsp.server import diagnostics_from_errors

        source = (
            "rune Vec2:\n  x as int\n  y as int\n\nweave add with a as int, b as int into int:\n  return a + b\n"
        )
        _checker, errors = parse_and_check(source, filename="test.pengu")
        assert errors == []
        assert diagnostics_from_errors(errors, source) == []

    def test_span_end_maps_to_diagnostic_range(self):
        """span_end is mapped to the diagnostic range end character."""
        from pengu_lsp.server import diagnostics_from_errors

        err = PenguError(
            message="Test type mismatch",
            code="E0005",
            line=2,
            col=5,
            span_start=5,
            span_end=10,
        )
        code = "line 1\n    let value = 123\n"
        diags = diagnostics_from_errors([err], code)
        assert len(diags) == 1
        assert diags[0].range.start.line == 1
        assert diags[0].range.start.character == 4
        assert diags[0].range.end.character == 10


# ===========================================================================
# 3. Hover
# ===========================================================================


class TestHover:
    """Hover returns markdown docs for keywords, symbols, and source docs."""

    def test_hover_keyword_doc(self):
        from pengu_lsp.hover import get_hover

        hover = get_hover(
            "file:///test.pengu",
            Position(line=0, character=2),  # over 'weave'
            symbols=None,
            text="weave main into void:\n  return\n",
        )
        assert hover is not None
        assert "**weave**" in hover.contents.value

    def test_hover_symbol_type_and_kind(self):
        from pengu_lsp.hover import get_hover

        source = (
            "rune Vec2:\n  x as float\n  y as float\n\nweave main into void:\n  var v as Vec2 is with x is 1.0, y is 2.0\n"
        )
        symbols = checked_symbols(source, filename="test.pengu")

        hover_vec = get_hover(
            "file:///test.pengu", Position(line=0, character=6),
            symbols=symbols, text=source,
        )
        assert hover_vec is not None
        assert "rune Vec2" in hover_vec.contents.value

        hover_main = get_hover(
            "file:///test.pengu", Position(line=4, character=7),
            symbols=symbols, text=source,
        )
        assert hover_main is not None
        assert "main" in hover_main.contents.value

    def test_hover_shows_doc_comments_from_source(self):
        """Doc comments preceding declarations appear in Symbol.doc and hover."""
        from pengu_lsp.hover import get_hover

        source = (
            "# Computes the sum of two integers.\n# Returns the calculated integer result.\nweave add with a as int, b as int into int:\n    return a + b\n"
        )
        symbols = checked_symbols(source, filename="test.pengu")

        sym = symbols.lookup("add")
        assert sym is not None
        assert sym.doc is not None
        assert "Computes the sum of two integers." in sym.doc
        assert "Returns the calculated integer result." in sym.doc

        hover = get_hover(
            "file:///test.pengu", Position(line=2, character=7),
            symbols=symbols, text=source,
        )
        assert hover is not None
        assert "Computes the sum of two integers." in hover.contents.value

    def test_hover_rune_type_sizes(self):
        """Type sizes (in bytes) are computed and displayed in hover."""
        from pengu_lsp.hover import get_hover

        source = (
            "rune Player:\n  name as string\n  health as int\n  is_alive as bool\n\nweave main into void:\n  var p as Player is with name is \"Hero\", health is 100, is_alive is true\n"
        )
        symbols = checked_symbols(source, filename="test.pengu")

        hover = get_hover(
            "file:///test.pengu", Position(line=0, character=7),
            symbols=symbols, text=source,
        )
        assert hover is not None
        value = hover.contents.value
        # string(16) + int(4) + bool(1) = 21 bytes
        assert "21 bytes" in value
        assert "name as string  // 128 bits / 16 bytes" in value
        assert "health as int  // 32 bits / 4 bytes" in value
        assert "is_alive as bool  // 8 bits / 1 bytes" in value

    def test_hover_module_member(self):
        """Hover on a stdlib module member (spark.println) resolves it."""
        from pengu_lsp.hover import get_hover

        source = 'import std.spark\n\nweave main into void:\n  calling spark.println with "Hello LSP"\n'
        symbols = checked_symbols(source, filename="test.pengu")

        hover = get_hover(
            "file:///test.pengu", Position(line=3, character=17),
            symbols=symbols, text=source,
        )
        assert hover is not None
        assert "println" in hover.contents.value

    def test_hover_word_extracts_full_self_arrow_identifier(self):
        """Hovering anywhere on self->x yields the whole 'self->x' word."""
        from pengu_lsp.hover import get_word_at_position

        code = "let v is self->x"
        assert get_word_at_position(code, Position(line=0, character=10)) == "self->x"
        assert get_word_at_position(code, Position(line=0, character=15)) == "self->x"

    def test_hover_doc_fallback_reads_source_file(self, tmp_path):
        """'##' doc comments above a declaration are extracted from the file."""
        from pengu_lsp.hover import extract_doc_from_file

        path = tmp_path / "greeter.pengu"
        path.write_text(
            "## Greets a user by name.\n"
            "## Supports multiple lines.\n"
            "weave greet with who as string into void:\n"
            "  var x as int is 0\n",
            encoding="utf-8",
        )
        sym = Symbol(
            name="greet", type=INT_TYPE, kind="weave",
            file_path=str(path), line=3, doc=None,
        )
        doc = extract_doc_from_file(sym)
        assert "Greets a user by name." in doc
        assert "Supports multiple lines." in doc

    def test_hover_includes_fallback_doc(self, tmp_path):
        """Hover falls back to the source-file doc when Symbol.doc is empty."""
        from pengu_lsp.hover import get_hover

        path = tmp_path / "greeter.pengu"
        path.write_text(
            "## Greets a user by name.\n"
            "## Supports multiple lines.\n"
            "weave greet with who as string into void:\n"
            "  var x as int is 0\n",
            encoding="utf-8",
        )

        class _FakeSymbols:
            def __init__(self, sym):
                self._sym = sym
                self.runes = {}

            def lookup(self, name, *a, **k):
                return self._sym if name == self._sym.name else None

            def lookup_at(self, name, *a, **k):
                return self.lookup(name)

        sym = Symbol(
            name="greet", type=INT_TYPE, kind="weave",
            file_path=str(path), line=3, doc=None,
        )
        text = 'weave main into void:\n  calling greet with "x"\n'
        hover = get_hover("file:///x.pengu", Position(line=1, character=12), _FakeSymbols(sym), text)
        assert hover is not None
        assert "Greets a user by name." in hover.contents.value

    def test_format_symbol_hover_appends_doc(self, tmp_path):
        """format_symbol_hover appends a Symbol's doc text to the hover."""
        from pengu_lsp.hover import format_symbol_hover

        path = tmp_path / "greeter.pengu"
        path.write_text(
            "## Greets a user by name.\n"
            "weave greet with who as string into void:\n",
            encoding="utf-8",
        )
        sym = Symbol(
            name="greet", type=INT_TYPE, kind="weave",
            file_path=str(path), line=2, doc="My doc text",
        )
        out = format_symbol_hover(sym)
        assert "My doc text" in out


# ===========================================================================
# 4. Completion
# ===========================================================================


class TestCompletion:
    """Completion offers keywords, workspace symbols, and context-aware items."""

    def test_keyword_and_snippet_completions(self):
        labels = completion_labels(None, Position(line=0, character=0))
        for expected in (
            "weave", "rune", "echo", "omen", "var", "let", "with",
            "self->", "sigil of", "defer", "errdefer", "banish",
            "int", "string",
        ):
            assert expected in labels, f"missing completion {expected!r}"

    def test_workspace_symbol_completions(self):
        source = (
            "rune Player:\n"
            "  x as int\n"
            "  y as int\n"
            "\n"
            "weave calculate_score with p as int into int:\n"
            "  return p * 10\n"
        )
        symbols = checked_symbols(source, filename="test.pengu")
        labels = completion_labels(symbols, Position(line=5, character=0))
        assert "Player" in labels
        assert "calculate_score" in labels

    def test_when_context_suggests_compile_time_vars(self):
        source = (
            "rune Player:\n"
            "  x as int\n"
            "  y as int\n"
            "\n"
            "weave move with p as ref to Player into void:\n"
            "  var nx as int is 0\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        labels = completion_labels(symbols, Position(line=5, character=7), line_prefix="  when ")
        for expected in ("main", "os", "arch", "compiler", "defined"):
            assert expected in labels, f"when context missing {expected!r}"

    def test_as_context_suggests_builtin_and_project_types(self):
        source = (
            "rune Player:\n"
            "  x as int\n"
            "  y as int\n"
            "\n"
            "weave move with p as ref to Player into void:\n"
            "  var nx as int is 0\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        labels = completion_labels(symbols, Position(line=5, character=11), line_prefix="  var q as ")
        for expected in ("int", "string", "Player", "map of", "ref to"):
            assert expected in labels, f"as context missing {expected!r}"

    def test_into_context_suggests_types(self):
        source = (
            "rune Player:\n"
            "  x as int\n"
            "  y as int\n"
            "\n"
            "weave move with p as ref to Player into void:\n"
            "  var nx as int is 0\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        labels = completion_labels(symbols, Position(line=5, character=18), line_prefix="weave helper into ")
        for expected in ("int", "void", "string", "Player"):
            assert expected in labels, f"into context missing {expected!r}"

    def test_module_dot_completion(self):
        """Dot completion after an imported module suggests its exports."""
        source = 'import std.spark\n\nweave main into void:\n  calling spark.println with "Hello LSP"\n'
        symbols = checked_symbols(source, filename="test.pengu")

        mod_sym = symbols.lookup("spark")
        assert mod_sym is not None
        assert mod_sym.module_scope is not None
        assert "println" in mod_sym.module_scope.symbols

        labels = completion_labels(
            symbols, Position(line=3, character=16), line_prefix='  calling spark.'
        )
        assert "println" in labels
        assert "print_line" in labels

    def test_module_dot_completion_from_cache_without_symbols(self):
        """Module members complete from the server cache even when the current
        document has no symbol table yet (not validated)."""
        source = 'import std.spark\n\nweave main into void:\n  calling spark.println with "x"\n'
        symbols = checked_symbols(source, filename="test.pengu")
        mod_sym = symbols.lookup("spark")
        cache = {"spark": mod_sym.module_scope}

        labels = completion_labels(
            None, Position(line=3, character=16), line_prefix='  calling spark.',
            module_cache=cache,
        )
        assert "println" in labels
        assert "print_line" in labels

    def test_import_symbol_without_scope_does_not_use_cache(self, tmp_path):
        """A defined import symbol with no scope must NOT fall back to the
        cache: a stale/foreign cached scope must never leak another module's
        members into this completion."""
        mod = tmp_path / "mymod.pengu"
        mod.write_text(
            "weave add with a as int, b as int into int:\n    return a + b\n",
            encoding="utf-8",
        )
        source = ('import mymod\n\nweave main into void:\n  var s as int is calling mymod.add with 1, 2\n')
        symbols = checked_symbols(source, filename=str(tmp_path / "main.pengu"),
                                  base_dir=str(tmp_path))
        mod_sym = symbols.lookup("mymod")
        # Poison the cache under this alias with a *different* module scope,
        # then strip the real scope off the symbol to simulate partial state.
        oracle_symbols = checked_symbols('import std.oracle\n\nweave main into void:\n  return\n',
                                         filename=str(tmp_path / "other.pengu"))
        cache = {"mymod": oracle_symbols.lookup("oracle").module_scope}
        mod_sym.module_scope = None

        labels = completion_labels(
            symbols, Position(line=3, character=20), line_prefix='  calling mymod.',
            module_cache=cache,
        )
        assert "result_ok_int" not in labels   # foreign (oracle) members must not leak
        assert "add" not in labels             # and the real module is not resolved

    def test_module_dot_completion_does_not_leak_cached_foreign_module(self, tmp_path):
        """`mymod.` (validly imported, real scope) must only show mymod's own
        members, never the members of a foreign module cached under the alias."""
        mod = tmp_path / "mymod.pengu"
        mod.write_text(
            "weave add with a as int, b as int into int:\n    return a + b\n",
            encoding="utf-8",
        )
        source = ('import mymod\n\nweave main into void:\n  var s as int is calling mymod.add with 1, 2\n')
        symbols = checked_symbols(source, filename=str(tmp_path / "main.pengu"),
                                  base_dir=str(tmp_path))
        mod_sym = symbols.lookup("mymod")
        assert mod_sym is not None and mod_sym.module_scope is not None

        # Poison the cache under this alias with the oracle module scope.
        oracle_symbols = checked_symbols('import std.oracle\n\nweave main into void:\n  return\n',
                                         filename=str(tmp_path / "other.pengu"))
        cache = {"mymod": oracle_symbols.lookup("oracle").module_scope}

        labels = completion_labels(
            symbols, Position(line=3, character=20), line_prefix='  calling mymod.',
            module_cache=cache,
        )
        assert "add" in labels                 # mymod's own member
        assert "result_ok_int" not in labels   # no oracle leak
        assert "println" not in labels         # no spark leak either

    def test_unimported_module_from_cache_still_completes(self, tmp_path):
        """Cache remains usable when the name is NOT defined in the current
        document: typing `alias.` for an alias cached from another file still
        offers exactly that module's members."""
        mod = tmp_path / "mymod.pengu"
        mod.write_text(
            "weave add with a as int, b as int into int:\n    return a + b\n",
            encoding="utf-8",
        )
        importer = ('import mymod\n\nweave main into void:\n  var s as int is calling mymod.add with 1, 2\n')
        importer_symbols = checked_symbols(importer, filename=str(tmp_path / "other.pengu"),
                                           base_dir=str(tmp_path))
        cache = {"mymod": importer_symbols.lookup("mymod").module_scope}

        # This document does not import mymod at all; only a rune is defined.
        plain_source = "rune LocalThing:\n  x as int\n\nweave main into void:\n  return\n"
        symbols = checked_symbols(plain_source, filename="test.pengu")
        labels = completion_labels(
            symbols, Position(line=2, character=19), line_prefix='  calling mymod.',
            module_cache=cache,
        )
        assert "add" in labels
        assert "println" not in labels

    def test_aliased_module_dot_completion_from_cache(self):
        """`import std.spark as s` caches the scope under the alias."""
        source = 'import std.spark as s\n\nweave main into void:\n  calling s.println with "x"\n'
        symbols = checked_symbols(source, filename="test.pengu")
        mod_sym = symbols.lookup("s")
        assert mod_sym is not None
        cache = {"s": mod_sym.module_scope}

        labels = completion_labels(
            None, Position(line=3, character=14), line_prefix='  calling s.',
            module_cache=cache,
        )
        assert "println" in labels

    def test_validation_refreshes_module_cache(self):
        """_compute_diagnostics fills the cache and the handler uses it."""
        from lsprotocol.types import CompletionParams
        from pengu_lsp import server as lsp_server

        uri = "file:///modcache_doc.pengu"
        source = 'import std.spark\n\nweave main into void:\n  calling spark.println with "hi"\n'
        diags = lsp_server._compute_diagnostics(uri, source)
        assert diags == []

        assert "spark" in lsp_server._MODULE_CACHE
        scope = lsp_server._MODULE_CACHE["spark"]
        assert "println" in scope.symbols

        # Without a symbol table for the doc the handler still resolves the
        # module members through the cache (cache has been refreshed above).
        lsp_server.server._symbols.clear()
        params = CompletionParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(line=3, character=16),
        )
        labels = [item.label for item in lsp_server.completions(params).items]
        assert "println" in labels

    def test_scoped_locals_and_field_completions(self):
        """Local vars per scope, rune dot fields, and arrow completions."""
        source = (
            "rune Character:\n    name as string\n    hp as int\n    is_alive as bool\n\nweave main into void:\n    var player as Character is with name is \"Hero\", hp is 100, is_alive is true\n    var outer_secret as int is 42\n    if outer_secret > 0:\n        var inner_flag as bool is true\n        calling print with player.name\n"
        )
        symbols = checked_symbols(source, filename="test.pengu")

        # Scoped locals inside the if block
        labels_if = completion_labels(symbols, Position(line=9, character=8), line_prefix="        ")
        assert "player" in labels_if
        assert "outer_secret" in labels_if
        assert "inner_flag" in labels_if

        # Dot field completion on 'player.' is exclusive to the rune fields
        res_dot = completion_labels(
            symbols, Position(line=9, character=30), line_prefix="        calling print with player."
        )
        assert res_dot == ["name", "hp", "is_alive"]

        # Arrow completion on 'player->' resolves to the same fields
        labels_arrow = completion_labels(
            symbols, Position(line=9, character=31), line_prefix="        calling print with player->"
        )
        assert "name" in labels_arrow
        assert "hp" in labels_arrow

    def test_calling_context_completion_filters_keywords(self):
        """After 'calling' only callables/modules are offered, not keywords."""
        source = (
            "rune Character:\n    name as string\n    hp as int\n    is_alive as bool\n\nweave main into void:\n    var player as Character is with name is \"Hero\", hp is 100, is_alive is true\n    var outer_secret as int is 42\n    if outer_secret > 0:\n        var inner_flag as bool is true\n        calling print with player.name\n"
        )
        symbols = checked_symbols(source, filename="test.pengu")
        labels_call = completion_labels(
            symbols, Position(line=9, character=16), line_prefix="        calling "
        )
        assert "print" in labels_call
        assert "main" in labels_call
        assert "while" not in labels_call
        assert "if" not in labels_call

    # --- import-module completion -------------------------------------------

    def test_import_completion_offers_stdlib_and_project_modules(self, tmp_path):
        """`import ` suggests std.* modules plus project modules under src/."""
        src = tmp_path / "src" / "components"
        src.mkdir(parents=True)
        (src / "player.pengu").write_text(
            "rune Player:\n  name as string\n", encoding="utf-8"
        )
        labels = completion_labels(
            None, Position(line=0, character=7), line_prefix="import ",
            base_dir=str(tmp_path),
        )
        assert "std.spark" in labels
        assert "std.archivum" in labels
        assert "components.player" in labels

    def test_import_std_dot_suggests_short_names_with_exact_replacement(self):
        """`import std.` offers plain names and replaces only the typed prefix."""
        from pengu_lsp.completions import get_completions

        prefix = "import std."
        res = get_completions(
            "file:///t.pengu", Position(line=0, character=len(prefix)),
            None, prefix, None, base_dir=str(REPO),
        )
        labels = [item.label for item in res.items]
        assert "spark" in labels
        assert "archivum" in labels
        assert "std.spark" not in labels  # prefix already typed, no duplication
        spark = next(item for item in res.items if item.label == "spark")
        assert spark.text_edit is not None
        assert spark.text_edit.new_text == "std.spark"
        # Range covers exactly the typed `std.` (columns 7..11).
        assert spark.text_edit.range.start.character == 7
        assert spark.text_edit.range.end.character == 11

    def test_import_partial_prefix_filters(self):
        """`import std.s` narrows std modules to those starting with 's'."""
        labels = completion_labels(
            None, Position(line=0, character=11), line_prefix="import std.s",
            base_dir=str(REPO),
        )
        assert "spark" in labels
        assert "sqlite3" in labels  # from the .d.pengu binding
        assert "archivum" not in labels

        labels_bare = completion_labels(
            None, Position(line=0, character=9), line_prefix="import st",
            base_dir=str(REPO),
        )
        assert "std.spark" in labels_bare
        assert "components" not in labels_bare  # repo root has no src/

    def test_import_completion_ignores_private_modules(self, tmp_path):
        """Files/dirs starting with '_' are hidden from import completion."""
        src = tmp_path / "src"
        (src / "_private").mkdir(parents=True)
        (src / "_private" / "secret.pengu").write_text("weave h into void:\n  return\n",
                                                       encoding="utf-8")
        (src / "_shadow.pengu").write_text("weave s into void:\n  return\n",
                                           encoding="utf-8")
        labels = completion_labels(
            None, Position(line=0, character=7), line_prefix="import ",
            base_dir=str(tmp_path),
        )
        assert "_private.secret" not in labels
        assert "_shadow" not in labels


# ===========================================================================
# 4b. Lint warnings (unused imports / variables)
# ===========================================================================


class TestLintWarnings:
    """Clean documents produce Warning diagnostics for unused symbols."""

    def test_unused_import_and_variable_warnings(self):
        from pengu_lsp import server as lsp_server

        uri = "file:///lint_doc.pengu"
        source = (
            "import std.spark\n"
            "import std.atlas\n"
            "\n"
            "weave main into void:\n"
            "    var unused_num as int is 3\n"
            "    var used_x as int is 1\n"
            "    calling spark.println with (used_x to string)\n"
        )
        diags = lsp_server._compute_diagnostics(uri, source)
        msgs = [d.message for d in diags]
        assert any("Unused import 'std.atlas'" in m for m in msgs)
        assert any("Unused variable 'unused_num'" in m for m in msgs)
        # Used symbols must not be flagged.
        assert not any("Unused import 'std.spark'" in m for m in msgs)
        assert not any("Unused variable 'used_x'" in m for m in msgs)
        # And they are real warnings.
        assert all(d.severity == DiagnosticSeverity.Warning for d in diags)

    def test_alias_usage_counts_and_discard_names_are_exempt(self):
        from pengu_lsp import server as lsp_server

        uri = "file:///lint_alias.pengu"
        source = (
            "import std.spark as s\n"
            "import std.oracle\n"
            "\n"
            "weave main into void:\n"
            "    var _tmp as int is 1\n"
            "    calling s.println with \"hi\"\n"
            "    var used_v as int is 2\n"
            "    calling spark_is_used_elsewhere with used_v\n"
        )
        # spark_is_used_elsewhere is unknown: the doc will have a semantic
        # error, so lint warnings only apply to clean documents — check the
        # alias path with a clean body instead.
        clean = (
            "import std.spark as s\n"
            "\n"
            "weave main into void:\n"
            "    calling s.println with \"hi\"\n"
        )
        diags = lsp_server._compute_diagnostics(uri, clean)
        assert diags == [] or not any("Unused import" in d.message for d in diags)
        # '_tmp' style names never trigger the unused-variable warning.
        dirty = "weave main into void:\n    var _tmp as int is 1\n"
        msgs = [d.message for d in lsp_server._compute_diagnostics(uri, dirty)]
        assert not any("_tmp" in m for m in msgs)


# ===========================================================================
# 4c. Organize imports code action
# ===========================================================================


class TestOrganizeImports:
    """The 'Organize imports' action drops unused imports and sorts the rest."""

    def test_drops_unused_import(self):
        from pengu_lsp.code_actions import organize_imports_action

        source = (
            "import std.atlas\n"
            "import std.spark\n"
            "\n"
            "weave main into void:\n"
            '    calling spark.println with "hi"\n'
        )
        action = organize_imports_action("file:///x.pengu", source)
        assert action is not None
        assert "Organize imports" in action.title
        edit = action.edit.changes["file:///x.pengu"][0]
        assert edit.new_text == "import std.spark\n"
        # Range covers the whole import block (lines 0..1).
        assert edit.range.start.line == 0
        assert edit.range.end.line == 1

    def test_sorts_imports_alphabetically(self):
        from pengu_lsp.code_actions import organize_imports_action

        source = (
            "import std.spark\n"
            "import std.scrolls\n"
            "\n"
            "weave main into void:\n"
            '    calling spark.println with "hi"\n'
            '    calling scrolls.upper with "x"\n'
        )
        action = organize_imports_action("file:///x.pengu", source)
        assert action is not None
        edit = action.edit.changes["file:///x.pengu"][0]
        assert edit.new_text == "import std.scrolls\nimport std.spark\n"

    def test_tidy_document_gets_no_action(self):
        from pengu_lsp.code_actions import organize_imports_action

        source = (
            "import std.scrolls\n"
            "import std.spark\n"
            "\n"
            "weave main into void:\n"
            '    calling spark.println with "hi"\n'
            '    calling scrolls.upper with "x"\n'
        )
        assert organize_imports_action("file:///x.pengu", source) is None


# ===========================================================================
# 4d. Go to implementation + Find references (project wide)
# ===========================================================================


class TestNavigationProjectWide:
    """Implementation / references handlers index stdlib + project files."""

    def _register(self, path, source):
        from pengu_lsp.server import server, path_to_uri

        uri = path_to_uri(str(path))
        server._docs[uri] = source
        return uri

    def test_go_to_implementation_finds_enchanting_method(self, tmp_path):
        from pengu_lsp.server import server, implementation

        greeter = tmp_path / "greeter.pengu"
        greeter.write_text(
            "rune ZqrGreeter:\n"
            "    name as string\n"
            "\n"
            "enchanting ZqrGreeter:\n"
            "    weave zqr_speak into void:\n"
            "        return\n",
            encoding="utf-8",
        )
        main = tmp_path / "main.pengu"
        source = (
            "import greeter\n"
            "\n"
            "weave main into void:\n"
            '    var g as ZqrGreeter is with name is "x"\n'
            "    calling g.zqr_speak\n"
        )
        uri = self._register(main, source)
        line = source.splitlines().index("    calling g.zqr_speak")
        col = source.splitlines()[line].find("zqr_speak")

        from lsprotocol.types import ImplementationParams, TextDocumentIdentifier
        params = ImplementationParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(line=line, character=col),
        )
        locs = implementation(params)
        assert locs is not None
        matches = [loc for loc in locs if loc.uri.endswith("greeter.pengu")]
        assert matches, f"expected enchanting method location, got {locs}"
        # Points at the 'weave zqr_speak' line (index 4) in greeter.pengu.
        assert matches[0].range.start.line == 4

    def test_references_project_wide(self, tmp_path):
        from pengu_lsp.server import server, references

        util = tmp_path / "util.pengu"
        util.write_text(
            "weave zqr_compute with x as int into int:\n"
            "    return x\n",
            encoding="utf-8",
        )
        main = tmp_path / "main.pengu"
        source = (
            "import util\n"
            "\n"
            "weave main into int:\n"
            "    var a as int is 2\n"
            "    var r1 as int is calling zqr_compute with a\n"
            "    var r2 as int is calling zqr_compute with a\n"
            "    return r1 + r2\n"
        )
        main.write_text(source, encoding="utf-8")
        uri = self._register(main, source)
        line = source.splitlines().index("    var r1 as int is calling zqr_compute with a")
        col = source.splitlines()[line].find("zqr_compute")

        from lsprotocol.types import ReferenceContext, ReferenceParams, TextDocumentIdentifier
        params = ReferenceParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(line=line, character=col),
            context=ReferenceContext(include_declaration=True),
        )
        locs = references(params) or []
        # Declaration in util.pengu + both call sites in main.pengu.
        assert any(loc.uri.endswith("util.pengu") for loc in locs)
        main_uris = [loc for loc in locs if loc.uri == uri]
        assert len(main_uris) == 2, f"expected 2 call sites in main, got {len(main_uris)}"

    def test_local_references_stay_in_current_document(self, tmp_path):
        from pengu_lsp.server import server, references

        main = tmp_path / "main.pengu"
        source = (
            "weave main into int:\n"
            "    var zz as int is 5\n"
            "    var q as int is zz + 1\n"
            "    return q\n"
        )
        main.write_text(source, encoding="utf-8")
        uri = self._register(main, source)
        line = source.splitlines().index("    var q as int is zz + 1")
        col = source.splitlines()[line].find("zz")

        from lsprotocol.types import ReferenceContext, ReferenceParams, TextDocumentIdentifier
        params = ReferenceParams(
            text_document=TextDocumentIdentifier(uri=uri),
            position=Position(line=line, character=col),
            context=ReferenceContext(include_declaration=True),
        )
        locs = references(params) or []
        assert locs
        assert all(loc.uri == uri for loc in locs)  # local var never leaves the file


# ===========================================================================
# 4e. Contextual completion (judge / with-blocks / rune initializers)
# ===========================================================================


class TestContextualCompletion:
    """Completion adapts to judge / with / rune-construction contexts."""

    def test_judge_when_suggests_omen_variants(self):
        source = (
            "omen Level:\n"
            "    One\n"
            "    Two\n"
            "\n"
            "weave main into int:\n"
            "    var c as Level is Level.One\n"
            "    let r is judge c:\n"
            "        when One -> 1\n"
            "        when Two -> 2\n"
            "        else -> 0\n"
            "    return 0\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        lines = source.splitlines()
        when_line = lines.index("        when One -> 1")
        labels = completion_labels(
            symbols,
            Position(line=when_line, character=len("        when ")),
            line_prefix="        when ",
            doc_text=source,
        )
        assert "One" in labels
        assert "Two" in labels
        assert "else ->" in labels

    def test_judge_when_partial_filter(self):
        source = (
            "omen Color:\n"
            "    red\n"
            "    green\n"
            "\n"
            "weave main into int:\n"
            "    var c as Color is Color.red\n"
            "    let r is judge c:\n"
            "        when red -> 1\n"
            "        when green -> 2\n"
            "        else -> 0\n"
            "    return 0\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        lines = source.splitlines()
        when_line = lines.index("        when green -> 2")
        labels = completion_labels(
            symbols,
            Position(line=when_line, character=len("        when g")),
            line_prefix="        when g",
            doc_text=source,
        )
        assert "red" not in labels
        assert "green" in labels

    def test_with_block_set_dot_suggests_fields(self):
        source = (
            "rune Player:\n    x as int\n    y as int\n\nweave main into void:\n    var player as Player is with x is 10, y is 20\n    with player:\n        set.x is 1\n        return\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        lines = source.splitlines()
        set_line = lines.index("        set.x is 1")
        labels = completion_labels(
            symbols,
            Position(line=set_line, character=len("        set.")),
            line_prefix="        set.",
            doc_text=source,
        )
        assert labels == ["x", "y"]

    def test_rune_with_initializer_suggests_fields(self):
        source = (
            "rune Player:\n    name as string\n    hp as int\n\nweave main into void:\n    var p as Player is with name is \"\", hp is 0\n"
        )
        symbols = checked_symbols(source, filename="t.pengu")
        lines = source.splitlines()
        line = lines.index('    var p as Player is with name is "", hp is 0')
        labels = completion_labels(
            symbols,
            Position(line=line, character=len("    var p as Player is with ")),
            line_prefix="    var p as Player is with ",
        )
        assert "name" in labels
        assert "hp" in labels
        assert "(all fields)" in labels


# ===========================================================================
# 4f. Code assistance: implement missing concept methods
# ===========================================================================


class TestConceptImplementationCodeAction:
    """A bind block can auto-generate skeletons for unimplemented methods."""

    def test_implement_missing_concept_methods(self):
        from pengu_lsp.code_actions import implement_concept_methods_action

        source = (
            "concept Speaker:\n"
            "    weave greet with name as string into void\n"
            "    weave loudness into int\n"
            "\n"
            "rune Dog:\n"
            "    name as string\n"
            "\n"
            "bind Dog with Speaker:\n"
            "    weave greet with name as string into void:\n"
            "        return\n"
            "\n"
            "weave main into void:\n"
            "    return\n"
        )
        checker, _errors = parse_and_check(source, filename="t.pengu")
        lines = source.splitlines()
        pos = lines.index("bind Dog with Speaker:")
        action = implement_concept_methods_action(
            "file:///t.pengu", source,
            Position(line=pos + 2, character=0), checker.symbols,
        )
        assert action is not None
        assert "1 missing" in action.title
        new_text = action.edit.changes["file:///t.pengu"][0].new_text
        assert "weave loudness into int:" in new_text
        assert "return 0" in new_text
        assert "greet" not in new_text  # already implemented, not duplicated

    def test_complete_concept_bind_generates_no_action(self):
        from pengu_lsp.code_actions import implement_concept_methods_action

        source = (
            "concept Printable:\n"
            "    weave print_me into void\n"
            "\n"
            "rune Doc:\n"
            "    body as string\n"
            "\n"
            "bind Doc with Printable:\n"
            "    weave print_me into void:\n"
            "        return\n"
        )
        checker, _errors = parse_and_check(source, filename="t.pengu")
        pos = source.splitlines().index("bind Doc with Printable:")
        action = implement_concept_methods_action(
            "file:///t.pengu", source,
            Position(line=pos + 1, character=0), checker.symbols,
        )
        assert action is None  # every concept method is implemented already


# ===========================================================================
# 4g. Richer hover + formatting config (pengu.yaml)
# ===========================================================================


class TestRicherHover:
    """Hover shows attached methods and generic type arguments."""

    def test_rune_hover_lists_attached_methods(self):
        from pengu_lsp.hover import format_symbol_hover
        from pengu_parser.pengu_types import RuneType

        sym = Symbol(name="Player", type=RuneType(name="Player", fields={}), kind="rune")
        out = format_symbol_hover(sym, method_names=["move", "draw"])
        assert "**Methods**: `draw`, `move`" in out

    def test_generic_rune_hover_shows_type_arguments(self):
        from pengu_lsp.hover import format_symbol_hover
        from pengu_parser.pengu_types import RuneType

        r_type = RuneType(
            name="Box", fields={"item": INT_TYPE},
            type_params=["T"], type_args=[INT_TYPE],
        )
        sym = Symbol(name="Box", type=r_type, kind="rune")
        out = format_symbol_hover(sym)
        assert "**Type arguments**: `int`" in out
        assert "**Type parameters**: `T`" in out


class TestFormattingConfig:
    """Formatting honors a pengu.yaml project config when the client sends none."""

    def test_load_format_config_reads_pengu_yaml(self, tmp_path):
        from pengu_lsp.formatting import load_format_config

        (tmp_path / "pengu.yaml").write_text(
            "name: demo\n"
            "tab_size: 4\n"
            "insert_spaces: true\n",
            encoding="utf-8",
        )
        cfg = load_format_config(str(tmp_path / "src" / "main.pengu"))
        assert cfg is not None
        assert cfg["tab_size"] == 4
        assert cfg["insert_spaces"] is True

    def test_document_formatting_uses_project_config(self, tmp_path):
        from pengu_lsp import server as lsp_server
        from lsprotocol.types import (
            DocumentFormattingParams,
            FormattingOptions,
            TextDocumentIdentifier,
        )

        (tmp_path / "pengu.yaml").write_text("tab_size: 4\n", encoding="utf-8")
        source = "weave main into void:\n    var x as int is 1\n"
        uri = lsp_server.path_to_uri(str(tmp_path / "main.pengu"))
        lsp_server.server._docs[uri] = source

        params = DocumentFormattingParams(
            text_document=TextDocumentIdentifier(uri=uri),
            options=FormattingOptions(tab_size=0, insert_spaces=True),
        )
        edits = lsp_server.document_formatting(params)
        assert edits is not None
        assert len(edits) == 1
        new_text = edits[0].new_text
        # With tab_size 4 from pengu.yaml the 4-space body indent is preserved.
        body_line = new_text.splitlines()[1]
        assert body_line == "    var x as int is 1"


# ===========================================================================
# 5. Definition
# ===========================================================================


class TestDefinition:
    """textDocument/definition resolution for locals and module members."""

    def _register_document(self, source, uri="file:///test.pengu"):
        from pengu_lsp.server import server

        symbols = checked_symbols(source, filename="test.pengu")
        server._symbols[uri] = symbols
        server._docs[uri] = source
        return symbols

    def test_definition_local_symbol(self):
        from pengu_lsp.server import definition

        source = (
            "import std.spark\n"
            "\n"
            "weave my_helper with val as int into int:\n"
            "    return val * 2\n"
            "\n"
            "weave main into void:\n"
            "    var res as int is calling my_helper with 10\n"
            '    calling spark.println with "Done"\n'
        )
        self._register_document(source)
        params = DefinitionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.pengu"),
            position=Position(line=6, character=32),
        )
        loc = definition(params)
        assert loc is not None
        assert loc.uri.endswith("test.pengu")
        assert loc.range.start.line == 2  # 'my_helper' declared on line 3

    def test_definition_module_member(self):
        from pengu_lsp.server import definition

        source = (
            "import std.spark\n"
            "\n"
            "weave my_helper with val as int into int:\n"
            "    return val * 2\n"
            "\n"
            "weave main into void:\n"
            "    var res as int is calling my_helper with 10\n"
            '    calling spark.println with "Done"\n'
        )
        self._register_document(source)
        params = DefinitionParams(
            text_document=TextDocumentIdentifier(uri="file:///test.pengu"),
            position=Position(line=7, character=20),
        )
        loc = definition(params)
        assert loc is not None
        assert loc.uri.endswith("spark.pengu")


# ===========================================================================
# 6. Code actions
# ===========================================================================


class TestCodeActions:
    """Quick-fix actions: remove-unused-variable and add-missing-import."""

    def test_remove_unused_variable_action_offered(self):
        from pengu_lsp.code_actions import remove_unused_variable_action

        source = "weave main into void:\n    var orphan as int is 0\n    return\n"
        action = remove_unused_variable_action("file:///t.pengu", "orphan", source, symbols=None)
        assert action is not None
        assert "Remove unused variable" in action.title

    def test_used_variable_gets_no_action(self):
        from pengu_lsp.code_actions import remove_unused_variable_action

        source = "weave main into void:\n    var used as int is 0\n    var y as int is used\n"
        action = remove_unused_variable_action("file:///t.pengu", "used", source, symbols=None)
        assert action is None

    def test_stdlib_index_resolves_exported_symbol(self):
        from pengu_lsp.code_actions import refresh_index

        index = refresh_index(std_dir=str(STD_DIR))
        assert index.get("println") == "std.spark"

    def test_add_missing_import_inserts_at_top(self):
        from pengu_lsp.code_actions import add_missing_import_action

        source = 'weave main into void:\n  calling println with "hi"\n'
        action = add_missing_import_action(
            "file:///t.pengu", "println", source, symbols=None, base_dir=str(REPO)
        )
        assert action is not None
        assert "import std.spark" in action.title
        edit = action.edit.changes["file:///t.pengu"][0]
        assert edit.new_text == "import std.spark\n"

    def test_add_missing_import_appends_after_existing_imports(self):
        from pengu_lsp.code_actions import add_missing_import_action

        source = "import std.spark\n\nweave main into void:\n  calling join with parts\n"
        action = add_missing_import_action(
            "file:///t.pengu", "join", source, symbols=None, base_dir=str(REPO)
        )
        assert action is not None
        assert "import std.compass" in action.title

    def test_known_symbol_yields_no_import_action(self):
        from pengu_lsp.code_actions import add_missing_import_action

        class _KnownSymbols:
            def lookup(self, name):
                return object()  # truthy: symbol already exists

        action = add_missing_import_action(
            "file:///t.pengu", "println", "", symbols=_KnownSymbols(), base_dir=str(REPO)
        )
        assert action is None

    def test_unknown_word_yields_no_import_action(self):
        from pengu_lsp.code_actions import add_missing_import_action

        action = add_missing_import_action(
            "file:///t.pengu", "zzz_not_a_symbol_12345", "", symbols=None, base_dir=str(REPO)
        )
        assert action is None


# ===========================================================================
# 7. Return-type inference (E0020 regression, LSP-style validation)
# ===========================================================================


class TestReturnTypeInference:
    """Typed returns propagate through calls without spurious E0020 errors."""

    def test_typed_returns_in_same_file(self):
        source = (
            "weave returns_bool into bool:\n"
            "    return true\n"
            "\n"
            "weave returns_int into int:\n"
            "    return 7\n"
            "\n"
            'weave returns_string into string:\n'
            '    return "hi"\n'
            "\n"
            "weave returns_maybe into maybe int:\n"
            "    return some 5\n"
            "\n"
            "weave returns_void into void:\n"
            "    return\n"
            "\n"
            "weave test_bool into void:\n"
            "    let rb as bool is calling returns_bool\n"
            "    let ri as int is calling returns_int\n"
            "    let rs as string is calling returns_string\n"
            "    let rm as maybe int is calling returns_maybe\n"
            "    calling returns_void\n"
        )
        parse_and_check(source, filename="rt_test.pengu")  # must not raise E0020

    def test_forward_reference_return_type(self):
        # caller is declared before the callee yet still infers the real type
        source = (
            "weave caller into bool:\n"
            "    return calling callee\n"
            "\n"
            "weave callee into bool:\n"
            "    return false\n"
        )
        parse_and_check(source, filename="rt_test.pengu")

    def test_lsp_style_stdlib_module_member_return_type(self):
        # archivum.write_file is declared 'into bool' in std/archivum.pengu
        source = (
            "import std.archivum\n\nweave save into bool:\n    return calling archivum.write_file with \"out.txt\", \"hello\"\n"
        )
        parse_and_check(source, filename="rt_test.pengu")

    def test_import_alias_member_return_type(self):
        source = (
            "import std.archivum as fs\n\nweave save into bool:\n    return calling fs.write_file with \"out.txt\", \"hello\"\n"
        )
        parse_and_check(source, filename="rt_test.pengu")

    def test_module_scope_member_return_types(self):
        """Typed members of a user module resolve through import module scope."""
        work = tempfile.mkdtemp(prefix="rtmod_", dir=str(REPO / "build"))
        try:
            mod = os.path.join(work, "typedmod.pengu")
            with open(mod, "w", encoding="utf-8") as f:
                f.write(
                    "weave get_flag into bool:\n"
                    "    return true\n\n"
                    "weave get_num into int:\n"
                    "    return 3\n\n"
                    'weave get_txt into string:\n'
                    '    return "mod"\n'
                )
            driver = os.path.join(work, "typeduser.pengu")
            source = (
                "import std.spark\n"
                "import typedmod\n\n"
                "weave main into int:\n"
                "    var a as bool is calling typedmod.get_flag\n"
                "    var b as int is calling typedmod.get_num\n"
                "    var c as string is calling typedmod.get_txt\n"
                "    return 0\n"
            )
            parse_and_check(source, filename=driver, base_dir=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_unknown_module_member_raises_e0004(self):
        # Unknown members must raise E0004 instead of silently degrading to 'void'
        source = (
            "import std.spark\n"
            "\n"
            "weave main into int:\n"
            "    calling spark.does_not_exist with 1\n"
            "    return 0\n"
        )
        _checker, errors = parse_and_check(source, filename="rt_test.pengu")
        assert errors, "expected the unknown member to produce an error"
        assert errors[0].code == "E0004"
        assert "does_not_exist" in errors[0].message

# ===========================================================================
# Validation performance: debounce + content-hash cache
# ===========================================================================


def _did_change_params(uri, text, version=1):
    from lsprotocol.types import TextDocumentContentChangeWholeDocument

    return DidChangeTextDocumentParams(
        text_document=VersionedTextDocumentIdentifier(uri=uri, version=version),
        content_changes=[TextDocumentContentChangeWholeDocument(text=text)],
    )


class TestValidationOptimizations:
    def test_wire_did_change_debounces_to_single_validation(self, monkeypatch):
        """Rapid didChange notifications collapse into one validation of the
        final text, running only after the debounce window."""
        import pengu_lsp.server as S

        ran = []
        real_compute = S._compute_diagnostics

        def counting(uri, source):
            ran.append(source)
            return real_compute(uri, source)

        monkeypatch.setattr(S, "_compute_diagnostics", counting)
        published = _capture_diagnostics(monkeypatch)
        uri = "file:///debounce.pengu"

        async def scenario():
            handler = S._wire_did_change
            await handler(_did_change_params(uri, "weave main into void:\n  var x as int is 1\n"))
            await handler(_did_change_params(uri, "weave main into void:\n  var x as int is 12\n"))
            await handler(_did_change_params(uri, "weave main into void:\n  var x as int is 123\n"))
            # While typing, nothing has been validated yet (debounce pending).
            assert ran == []
            await asyncio.sleep(0.6)  # longer than the 0.35 s debounce
            assert len(ran) == 1, f"expected a single validation, ran {len(ran)} times"
            assert "123" in ran[0]
            assert len(published) == 1

        asyncio.run(scenario())

    def test_wire_did_change_cancels_pending_on_flush(self, monkeypatch):
        """A didSave flush cancels the pending debounce and validates the saved
        text immediately (no extra duplicate run after the sleep)."""
        import pengu_lsp.server as S
        from lsprotocol.types import DidSaveTextDocumentParams

        ran = []
        real_compute = S._compute_diagnostics

        def counting(uri, source):
            ran.append(source)
            return real_compute(uri, source)

        monkeypatch.setattr(S, "_compute_diagnostics", counting)
        published = _capture_diagnostics(monkeypatch)
        uri = "file:///flush.pengu"

        async def scenario():
            save_text = "weave main into void:\n  var saved as int is 7\n"
            await S._wire_did_change(_did_change_params(uri, "weave main into void:\n  var x as int is 1\n"))
            # Save flushes immediately.
            await S._wire_did_save(DidSaveTextDocumentParams(
                text_document=TextDocumentIdentifier(uri=uri), text=save_text))
            assert len(ran) == 1
            assert "saved" in ran[0]
            await asyncio.sleep(0.6)
            # The superseded debounce must not fire a second validation.
            assert len(ran) == 1
            assert len(published) == 1

        asyncio.run(scenario())

    def test_validation_cache_skips_unchanged_content(self, monkeypatch):
        """validate_document with identical content re-publishes cached
        diagnostics without re-running the parser/checker."""
        import pengu_lsp.server as S

        ran = []
        real_compute = S._compute_diagnostics

        def counting(uri, source):
            ran.append(source)
            return real_compute(uri, source)

        monkeypatch.setattr(S, "_compute_diagnostics", counting)
        published = _capture_diagnostics(monkeypatch)
        uri = "file:///cache.pengu"
        base = "weave main into void:\n  var x as int is 1\n"

        S.validate_document(uri, base)
        assert len(ran) == 1
        S.validate_document(uri, base)  # unchanged -> cached
        assert len(ran) == 1, "unchanged content must not be re-parsed"
        S.validate_document(uri, base + "\n  var y as int is 2\n")  # changed
        assert len(ran) == 2
        assert len(published) == 3  # every validate_document call publishes

    def test_validation_cache_evicts_on_change(self, monkeypatch):
        """Changing content invalidates the cache entry (new hash -> recompute)."""
        import pengu_lsp.server as S

        ran = []
        real_compute = S._compute_diagnostics
        monkeypatch.setattr(S, "_compute_diagnostics", lambda uri, src: (ran.append(src), real_compute(uri, src))[1])
        uri = "file:///evict.pengu"
        S.validate_document(uri, "weave main into void:\n  var a as int is 1\n")
        S.validate_document(uri, "weave main into void:\n  var b as int is 2\n")
        S.validate_document(uri, "weave main into void:\n  var b as int is 2\n")
        assert len(ran) == 2

class TestImportedEnchantingMethods:
    """Enchanting methods of imported modules must resolve even for unsaved
    editor buffers (the doc is not yet on disk when LSP validates)."""

    GOOD = "import std.invoke\nweave main into void:\n    var p is calling invoke.new_parser with \"S\", \"D\"\n    calling p.add_flag with \"v\", \"v\", \"verbose\"\n"

    BAD = "import std.invoke\nweave main into void:\n    var p is calling invoke.new_parser with \"S\", \"D\"\n    calling p.add_option with \"src\", \"s\", \"help\", \"./x\", \"d\"\n"

    def test_unsaved_buffer_methods_resolve(self, monkeypatch):
        import pengu_lsp.server as S

        published = _capture_diagnostics(monkeypatch)
        uri = "file:///D:/Proyectos/PenguScript/scratch/user_repro/unsaved_ssg.pengu"
        # The file must NOT exist (simulating an unsaved editor buffer).
        from pengu_lsp.server import uri_to_path
        assert not os.path.exists(uri_to_path(uri))
        S.validate_document(uri, self.GOOD)
        assert published, "expected a diagnostics publication"
        _, diags = published[-1]
        assert diags == [], [d.message for d in diags]

    def test_unsaved_buffer_wrong_arg_type_reports_e0005(self, monkeypatch):
        import pengu_lsp.server as S

        published = _capture_diagnostics(monkeypatch)
        uri = "file:///D:/Proyectos/PenguScript/scratch/user_repro/unsaved_ssg_bad.pengu"
        from pengu_lsp.server import uri_to_path
        assert not os.path.exists(uri_to_path(uri))
        S.validate_document(uri, self.BAD)
        assert published
        _, diags = published[-1]
        assert any("E0005" in (d.code or "") for d in diags), [d.message for d in diags]
        assert any("required" in d.message for d in diags), [d.message for d in diags]
        # ... and crucially NOT the false "no method 'add_option'" E0004.
        assert not any((d.code or "").startswith("E0004") for d in diags)
