"""Roadmap Phase 5 — LSP regressions (items 5.1-5.10).

Each test pins a behaviour that was verified against the real code before the
fix; every one fails if the corresponding fix is reverted.
"""

import os

import pytest
from lsprotocol.types import (
    CodeActionContext,
    CodeActionKind,
    CodeActionParams,
    DefinitionParams,
    DidChangeConfigurationParams,
    DidChangeWatchedFilesParams,
    DocumentHighlightParams,
    FileChangeType,
    FileEvent,
    Position,
    PrepareRenameParams,
    Range,
    ReferenceContext,
    ReferenceParams,
    RenameParams,
    TextDocumentIdentifier,
    WorkspaceSymbolParams,
)

from tests.test_lsp import checked_symbols


def _register(source, uri, filename="t.pengu"):
    """Seeds the server's per-URI caches (symbols + buffer) directly."""
    from pengu_lsp.server import server

    symbols = checked_symbols(source, filename=filename)
    server._symbols[uri] = symbols
    server._docs[uri] = source
    return symbols


def _silence_publish(monkeypatch):
    """Captures published diagnostics instead of trying to write to a client."""
    from pengu_lsp.server import server

    published = []
    monkeypatch.setattr(server, "publish_diagnostics",
                        lambda uri, diags: published.append((uri, diags)))
    return published


# ---------------------------------------------------------------------------
# 5.1 — global rename must not rewrite a local homonym in another file
# ---------------------------------------------------------------------------

def test_5_1_global_rename_skips_local_homonym_in_other_file(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import server, rename_symbol

    (tmp_path / "pengu.yaml").write_text("name: probe\n", encoding="utf-8")
    a = tmp_path / "a.pengu"
    b = tmp_path / "b.pengu"
    a_source = "weave helper with n as int into int:\n    return n + 1\n"
    b_source = (
        "weave other into int:\n"
        "    var helper as int is 41\n"
        "    return helper\n"
    )
    a.write_text(a_source, encoding="utf-8")
    b.write_text(b_source, encoding="utf-8")
    a_uri = S.path_to_uri(str(a))
    b_uri = S.path_to_uri(str(b))
    _silence_publish(monkeypatch)
    monkeypatch.setattr(S, "_FILE_SYMBOL_CACHE", {})
    S.clear_symbol_caches()

    _register(a_source, a_uri, filename=str(a))
    result = rename_symbol(RenameParams(
        text_document=TextDocumentIdentifier(uri=a_uri),
        position=Position(line=0, character=7),  # `helper` declaration
        new_name="assist",
    ))

    assert result is not None and result.changes
    # The homonym `var helper` in b.pengu is a different symbol: untouched.
    assert b_uri not in result.changes
    edits = result.changes[a_uri]
    assert [(e.range.start.line, e.range.start.character) for e in edits] == [(0, 6)]
    assert all(e.new_text == "assist" for e in edits)


def test_5_1_global_rename_updates_uses_in_declaration_file(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import rename_symbol

    (tmp_path / "pengu.yaml").write_text("name: probe\n", encoding="utf-8")
    a = tmp_path / "a.pengu"
    a_source = (
        "weave helper with n as int into int:\n"
        "    return n + 1\n"
        "\n"
        "weave main into int:\n"
        "    return calling helper with 1\n"
    )
    a.write_text(a_source, encoding="utf-8")
    a_uri = S.path_to_uri(str(a))
    _silence_publish(monkeypatch)
    S.clear_symbol_caches()

    _register(a_source, a_uri, filename=str(a))
    result = rename_symbol(RenameParams(
        text_document=TextDocumentIdentifier(uri=a_uri),
        position=Position(line=0, character=7),
        new_name="assist",
    ))
    assert result is not None and a_uri in result.changes
    lines = {e.range.start.line for e in result.changes[a_uri]}
    assert lines == {0, 4}  # declaration + call


# ---------------------------------------------------------------------------
# 5.2 — definition on an unsaved buffer returns the real URI, not the shadow
# ---------------------------------------------------------------------------

def test_5_2_definition_never_returns_shadow_path(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import definition, validate_document

    _silence_publish(monkeypatch)
    real = tmp_path / "buffer.pengu"  # deliberately NOT written to disk
    uri = S.path_to_uri(str(real))
    source = (
        "weave helper with n as int into int:\n"
        "    return n\n"
        "\n"
        "weave main into int:\n"
        "    return calling helper with 1\n"
    )
    validate_document(uri, source)
    assert not real.exists()

    loc = definition(DefinitionParams(
        text_document=TextDocumentIdentifier(uri=uri),
        position=Position(line=4, character=20),  # `helper` in the call
    ))
    assert loc is not None
    assert ".pengu_lsp_shadow_" not in loc.uri
    assert loc.uri == uri
    # The declaration of `helper` lives on line 0 of the real buffer.
    assert loc.range.start.line == 0
    assert loc.range.end.character == len("helper")


def test_5_2_symbols_of_unsaved_buffer_carry_real_path(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import validate_document

    _silence_publish(monkeypatch)
    real = tmp_path / "buffer2.pengu"
    uri = S.path_to_uri(str(real))
    source = "weave helper into int:\n    return 1\n"
    validate_document(uri, source)
    sym = S.server._symbols[uri].global_scope.symbols["helper"]
    assert sym.file_path == str(real)


# ---------------------------------------------------------------------------
# 5.3 — organize imports action is wired and advertised
# ---------------------------------------------------------------------------

_IMPORTS_SOURCE = (
    "import std.spark\n"
    "import std.loom\n"
    "\n"
    "weave main into int:\n"
    "    calling spark.println with \"hi\"\n"
    "    return 0\n"
)


def test_5_3_organize_imports_offered_for_source_only(monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import code_action

    _silence_publish(monkeypatch)
    uri = "file:///organize.pengu"
    _register(_IMPORTS_SOURCE, uri, filename="organize.pengu")
    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=uri),
        range=Range(start=Position(0, 0), end=Position(0, 0)),
        context=CodeActionContext(diagnostics=[], only=[CodeActionKind.SourceOrganizeImports]),
    )
    actions = code_action(params)
    kinds = [a.kind for a in actions]
    assert CodeActionKind.SourceOrganizeImports in kinds
    action = next(a for a in actions if a.kind == CodeActionKind.SourceOrganizeImports)
    assert action.title == "Organize imports"
    assert action.edit is not None and uri in action.edit.changes
    # `std.loom` is unused: it must be dropped by the edit.
    new_text = action.edit.changes[uri][0].new_text
    assert "std.loom" not in new_text
    assert "std.spark" in new_text


def test_5_3_organize_imports_not_gated_on_cursor_word(monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import code_action

    _silence_publish(monkeypatch)
    uri = "file:///organize2.pengu"
    _register(_IMPORTS_SOURCE, uri, filename="organize2.pengu")
    # Cursor sits on a blank line (no word) — the source action must still come.
    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=uri),
        range=Range(start=Position(2, 0), end=Position(2, 0)),
        context=CodeActionContext(diagnostics=[], only=[CodeActionKind.SourceOrganizeImports]),
    )
    actions = code_action(params)
    assert any(a.kind == CodeActionKind.SourceOrganizeImports for a in actions)


def test_5_3_quickfix_not_returned_when_only_organize_requested(monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import code_action

    _silence_publish(monkeypatch)
    uri = "file:///organize3.pengu"
    _register(_IMPORTS_SOURCE, uri, filename="organize3.pengu")
    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=uri),
        range=Range(start=Position(4, 4), end=Position(4, 4)),
        context=CodeActionContext(diagnostics=[], only=[CodeActionKind.SourceOrganizeImports]),
    )
    actions = code_action(params)
    assert all(a.kind == CodeActionKind.SourceOrganizeImports for a in actions)


# ---------------------------------------------------------------------------
# 5.4 — the code lens command is registered and advertised
# ---------------------------------------------------------------------------

def test_5_4_run_test_command_registered_and_advertised():
    from pengu_lsp.server import server

    fm = server.protocol.fm
    assert "pengu.runTest" in fm.commands


def _server_capabilities(client_capabilities):
    """Computes capabilities exactly as `initialize` does."""
    from pygls.capabilities import ServerCapabilitiesBuilder
    from lsprotocol.types import PositionEncodingKind

    from pengu_lsp.server import server

    fm = server.protocol.fm
    return ServerCapabilitiesBuilder(
        client_capabilities,
        set({**fm.features, **fm.builtin_features}.keys()),
        fm.feature_options,
        list(fm.commands.keys()),
        server._text_document_sync_kind,
        server._notebook_document_sync,
        PositionEncodingKind.Utf16,
    ).build()


def test_5_5_and_5_6_capabilities_advertised():
    """workspace/symbol and prepareRename reach the client's capabilities."""
    from lsprotocol.types import (
        ClientCapabilities,
        RenameClientCapabilities,
        TextDocumentClientCapabilities,
    )

    caps = _server_capabilities(ClientCapabilities(
        text_document=TextDocumentClientCapabilities(
            rename=RenameClientCapabilities(prepare_support=True),
        ),
    ))
    assert caps.workspace_symbol_provider is not None
    assert caps.rename_provider is not None
    assert caps.rename_provider.prepare_provider is True
    # 5.4: the code lens command is advertised so the client can execute it.
    assert caps.execute_command_provider is not None
    assert "pengu.runTest" in caps.execute_command_provider.commands


def test_5_4_run_test_executes_and_reports(monkeypatch, tmp_path):
    import sys

    from pengu_lsp import server as S
    from pengu_lsp.server import run_test, server

    messages = []
    monkeypatch.setattr(server, "window_show_message", lambda params: messages.append(params))
    monkeypatch.setattr(
        S, "_pengu_command",
        lambda: [sys.executable, "-c", "print('ALL TESTS PASSED')"],
    )
    path = tmp_path / "t.pengu"
    path.write_text("weave main into int:\n    return 0\n", encoding="utf-8")

    output = run_test(server, S.path_to_uri(str(path)), "adds")
    assert "ALL TESTS PASSED" in output
    assert messages and "passed" in messages[-1].message


def test_5_4_run_test_reports_missing_executable(monkeypatch, tmp_path):
    from pengu_lsp import server as S
    from pengu_lsp.server import run_test, server

    messages = []
    monkeypatch.setattr(server, "window_show_message", lambda params: messages.append(params))
    monkeypatch.setattr(S, "_pengu_command", lambda: None)

    output = run_test(server, S.path_to_uri(str(tmp_path / "t.pengu")), "x")
    assert output == ""
    assert messages and "not found" in messages[-1].message


def test_5_4_pengu_command_is_discoverable_in_a_checkout():
    """Binary discovery never returns a non-executable path.

    In a source checkout there is no ``pengu`` binary, so the fallback is
    ``python pengu_project.py``; in a frozen build it is ``sys.executable``.
    """
    import os

    from pengu_lsp.server import _pengu_command

    cmd = _pengu_command()
    assert cmd, "no way to invoke the pengu CLI was found"
    assert os.path.isfile(cmd[0])


# ---------------------------------------------------------------------------
# 5.5 — workspace/symbol
# ---------------------------------------------------------------------------

def test_5_5_workspace_symbol_returns_project_symbols(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import server, workspace_symbols

    project = tmp_path / "proj"
    project.mkdir()
    (project / "pengu.yaml").write_text("name: proj\n", encoding="utf-8")
    src = project / "lib.pengu"
    source = (
        "rune Thing:\n"
        "    n as int\n"
        "\n"
        "weave widget with t as Thing into int:\n"
        "    return t.n\n"
    )
    src.write_text(source, encoding="utf-8")
    uri = S.path_to_uri(str(src))
    _silence_publish(monkeypatch)
    S.clear_symbol_caches()
    # No client workspace folders in tests: the handler falls back to open docs.
    server._docs[uri] = source

    out = workspace_symbols(WorkspaceSymbolParams(query="widget"))
    assert out
    project_hits = [s for s in out if s.location.uri == uri]
    assert project_hits, "project symbol missing from workspace/symbol"
    hit = project_hits[0]
    assert hit.name == "widget"
    from lsprotocol.types import SymbolKind

    assert hit.kind == SymbolKind.Function

    rune_hits = workspace_symbols(WorkspaceSymbolParams(query="Thing"))
    assert any(s.name == "Thing" and s.location.uri == uri for s in rune_hits)


def test_5_5_workspace_symbol_empty_query_returns_all(monkeypatch, tmp_path):
    from pengu_lsp import server as S
    from pengu_lsp.server import server, workspace_symbols

    project = tmp_path / "proj2"
    project.mkdir()
    (project / "pengu.yaml").write_text("name: proj2\n", encoding="utf-8")
    src = project / "m.pengu"
    src.write_text("weave unique_symbol_xyz into int:\n    return 1\n", encoding="utf-8")
    _silence_publish(monkeypatch)
    S.clear_symbol_caches()
    server._docs[S.path_to_uri(str(src))] = src.read_text(encoding="utf-8")

    out = workspace_symbols(WorkspaceSymbolParams(query=""))
    assert out and any(s.name == "unique_symbol_xyz" for s in out)


# ---------------------------------------------------------------------------
# 5.6 — prepareRename
# ---------------------------------------------------------------------------

def _prepare(source, line, char, uri="file:///prep.pengu", filename="prep.pengu"):
    from pengu_lsp.server import prepare_rename

    _register(source, uri, filename=filename)
    return prepare_rename(PrepareRenameParams(
        text_document=TextDocumentIdentifier(uri=uri),
        position=Position(line=line, character=char),
    ))


def test_5_6_prepare_rename_returns_range_for_symbol():
    src = "weave helper with n as int into int:\n    return n\n"
    result = _prepare(src, 0, 7)  # cursor inside `helper`
    assert result is not None
    assert (result.start.line, result.start.character) == (0, 6)
    assert (result.end.line, result.end.character) == (0, 12)


def test_5_6_prepare_rename_rejects_keyword():
    src = "weave helper with n as int into int:\n    return n\n"
    assert _prepare(src, 0, 2) is None  # cursor on the `weave` keyword


def test_5_6_prepare_rename_rejects_member_access():
    src = (
        "rune Box:\n"
        "    x as int\n"
        "\n"
        "weave f with b as Box into int:\n"
        "    return b.x\n"
    )
    assert _prepare(src, 4, 13) is None  # cursor on `x` in `b.x`
    # ...but `b` itself is a renameable local.
    assert _prepare(src, 4, 11) is not None


def test_5_6_prepare_rename_rejects_literal():
    src = "weave f into string:\n    return \"hello\"\n"
    assert _prepare(src, 1, 13) is None


# ---------------------------------------------------------------------------
# 5.7 — debug logs stay behind PENGU_LSP_DEBUG
# ---------------------------------------------------------------------------

def test_5_7_publishing_message_needs_debug_env(monkeypatch, capsys):
    from pengu_lsp import server as S

    monkeypatch.delenv("PENGU_LSP_DEBUG", raising=False)
    monkeypatch.setattr(S.server, "text_document_publish_diagnostics",
                        lambda params: None, raising=False)
    S.server.publish_diagnostics("file:///x.pengu", [])
    assert "[LSP] Publishing" not in capsys.readouterr().err

    monkeypatch.setenv("PENGU_LSP_DEBUG", "1")
    S.server.publish_diagnostics("file:///x.pengu", [])
    assert "[LSP] Publishing" in capsys.readouterr().err


def test_5_7_validate_document_is_silent(capsys, monkeypatch):
    from pengu_lsp import server as S

    monkeypatch.delenv("PENGU_LSP_DEBUG", raising=False)
    _silence_publish(monkeypatch)
    S.validate_document("file:///silent.pengu", "weave f into int:\n    return 1\n")
    assert "[LSP]" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 5.8 — version/docstrings read from the single source of truth
# ---------------------------------------------------------------------------

def test_5_8_version_comes_from_pengu_version():
    import pengu_version
    import pengu_lsp
    from pengu_lsp.server import _get_version, server

    assert pengu_lsp.__version__ == pengu_version.__version__
    assert _get_version() == pengu_version.__version__
    assert server.version == f"v{pengu_version.__version__}"


def test_5_8_code_action_docstring_lists_actions():
    from pengu_lsp.server import code_action

    doc = code_action.__doc__ or ""
    for action in ("Add missing import", "Remove unused", "concept", "Organize imports"):
        assert action in doc, f"docstring does not mention {action!r}"


# ---------------------------------------------------------------------------
# 5.10 — didChangeConfiguration / didChangeWatchedFiles
# ---------------------------------------------------------------------------

def test_5_10_configuration_change_updates_settings_and_revalidates(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import did_change_configuration, server

    published = _silence_publish(monkeypatch)
    uri = "file:///cfg.pengu"
    source = "weave f into int:\n    return 1\n"
    _register(source, uri, filename="cfg.pengu")
    # Only this document is open, so revalidation cannot repopulate the module
    # cache from documents opened by other tests.
    monkeypatch.setattr(server, "_docs", {uri: source})
    S._MODULE_CACHE["bogus"] = object()
    S._FILE_SYMBOL_CACHE["/nonexistent.pengu"] = ("hash", None)

    did_change_configuration(DidChangeConfigurationParams(
        settings={"pengus": {"executablePath": "/opt/pengu"}},
    ))

    assert server.get_setting("pengus.executablePath") == "/opt/pengu"
    assert S._MODULE_CACHE == {}
    assert S._FILE_SYMBOL_CACHE == {}
    assert published and published[-1][0] == uri


def test_5_10_watched_files_drops_caches_and_revalidates(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import did_change_watched_files, server

    published = _silence_publish(monkeypatch)
    uri = "file:///watched.pengu"
    source = "weave f into int:\n    return 1\n"
    _register(source, uri, filename="watched.pengu")
    monkeypatch.setattr(server, "_docs", {uri: source})
    watched = tmp_path / "changed.pengu"
    watched.write_text(source, encoding="utf-8")
    watched_uri = S.path_to_uri(str(watched))
    S._FILE_SYMBOL_CACHE[str(watched)] = ("stale", None)

    did_change_watched_files(DidChangeWatchedFilesParams(
        changes=[FileEvent(uri=watched_uri, type=FileChangeType.Changed)],
    ))

    assert str(watched) not in S._FILE_SYMBOL_CACHE
    assert published and published[-1][0] == uri
