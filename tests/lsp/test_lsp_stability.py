"""Roadmap Phase 5, item 5.11 — LSP stability at 10 000 lines.

Builds a *valid* `.pengu` file of ~10 000 lines (every line parses and checks
cleanly) and drives the server through initialize + didOpen + the eleven
content requests a real editor sends. The test asserts every request responds
without raising and records a timing baseline in ``BASELINE_MS``.

Baseline measured on a developer machine (Python 3.14, cold checker caches):
didOpen/validate dominates; the largest per-request cost is
``semanticTokens/full``, which is why range/delta tokens are tracked
separately (roadmap 5.9, deferred to 1.1 with measurement).
"""

import time

from lsprotocol.types import (
    ClientCapabilities,
    CodeActionContext,
    CodeActionParams,
    CompletionParams,
    DefinitionParams,
    DocumentFormattingParams,
    DocumentSymbolParams,
    HoverParams,
    Position,
    PositionEncodingKind,
    PrepareRenameParams,
    Range,
    ReferenceContext,
    ReferenceParams,
    RenameParams,
    SemanticTokensParams,
    TextDocumentIdentifier,
    WorkspaceSymbolParams,
)

#: Rough baseline per operation (ms) measured on the reference machine. Kept as
#: documentation; the assertions below only fail on a *pathological* regression
#: (an order of magnitude), never on ordinary machine-to-machine variance.
BASELINE_MS = {
    "initialize": 1,
    "didOpen": 14000,
    "hover": 2,
    "completion": 14,
    "definition": 1,
    "references": 724,
    "documentSymbol": 17,
    "workspaceSymbol": 25,
    "codeAction": 34,
    "rename": 670,
    "prepareRename": 1,
    "formatting": 70,
    "semanticTokens": 1733,
}

#: Ceilings are deliberately loose: CI machines are slower and cold caches are
#: allowed. They catch a hang or an accidental O(n^2), not a 2x slowdown.
CEILING_MS = {name: 60000 for name in BASELINE_MS}
CEILING_MS["semanticTokens"] = 30000
CEILING_MS["didOpen"] = 120000

LINE_TARGET = 10000


def _generate_10k() -> str:
    """A clean ~10 000-line program: many small `weave` functions + `main`."""
    parts = []
    i = 0
    while len(parts) < LINE_TARGET:
        parts.append(f"weave fn_{i} with a as int into int:")
        parts.append(f"    var local_{i} as int is a + {i % 97}")
        parts.append(f"    return local_{i}")
        parts.append("")
        i += 1
    parts.append("weave main into int:")
    parts.append("    var total as int is 0")
    parts.append("    return total")
    return "\n".join(parts) + "\n"


def _initialize_capabilities():
    """Builds the server capabilities exactly as `initialize` would."""
    from pygls.capabilities import ServerCapabilitiesBuilder

    from pengu_lsp.server import server

    fm = server.protocol.fm
    return ServerCapabilitiesBuilder(
        ClientCapabilities(),
        set({**fm.features, **fm.builtin_features}.keys()),
        fm.feature_options,
        list(fm.commands.keys()),
        server._text_document_sync_kind,
        server._notebook_document_sync,
        PositionEncodingKind.Utf16,
    ).build()


def test_stability_13_requests_on_10k_lines(tmp_path, monkeypatch):
    from pengu_lsp import server as S
    from pengu_lsp.server import server

    source = _generate_10k()
    assert len(source.splitlines()) >= LINE_TARGET

    project = tmp_path / "big"
    project.mkdir()
    (project / "pengu.yaml").write_text("name: big\n", encoding="utf-8")
    path = project / "big.pengu"
    path.write_text(source, encoding="utf-8")
    uri = S.path_to_uri(str(path))

    published = []
    monkeypatch.setattr(server, "publish_diagnostics",
                        lambda doc_uri, diags: published.append((doc_uri, diags)))
    monkeypatch.setattr(server, "window_show_message", lambda params: None)
    S.clear_symbol_caches()

    timings = {}
    failures = {}

    def run(name, fn):
        start = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 - recorded, asserted below
            failures[name] = f"{type(exc).__name__}: {exc}"
            result = None
        timings[name] = (time.perf_counter() - start) * 1000
        return result

    ti = TextDocumentIdentifier(uri=uri)

    caps = run("initialize", _initialize_capabilities)
    run("didOpen", lambda: S.validate_document(uri, source))

    run("hover", lambda: S.hover(HoverParams(
        text_document=ti, position=Position(line=0, character=7))))
    run("completion", lambda: S.completions(CompletionParams(
        text_document=ti, position=Position(line=1, character=20))))
    run("definition", lambda: S.definition(DefinitionParams(
        text_document=ti, position=Position(line=2, character=12))))
    run("references", lambda: S.references(ReferenceParams(
        text_document=ti, position=Position(line=1, character=10),
        context=ReferenceContext(include_declaration=True))))
    run("documentSymbol", lambda: S.document_symbols(
        DocumentSymbolParams(text_document=ti)))
    run("workspaceSymbol", lambda: S.workspace_symbols(
        WorkspaceSymbolParams(query="fn_1")))
    run("codeAction", lambda: S.code_action(CodeActionParams(
        text_document=ti,
        range=Range(start=Position(0, 0), end=Position(0, 0)),
        context=CodeActionContext(diagnostics=[]))))
    run("rename", lambda: S.rename_symbol(RenameParams(
        text_document=ti, position=Position(line=1, character=10),
        new_name="renamed_local")))
    run("prepareRename", lambda: S.prepare_rename(PrepareRenameParams(
        text_document=ti, position=Position(line=1, character=10))))
    run("formatting", lambda: S.document_formatting(DocumentFormattingParams(
        text_document=ti, options={"tabSize": 2, "insertSpaces": True})))
    tokens = run("semanticTokens", lambda: S.semantic_tokens_full(
        SemanticTokensParams(text_document=ti)))

    # Baseline report, visible with `pytest -s`.
    report = "\n".join(
        f"  {name:16} {timings[name]:9.1f} ms (baseline {BASELINE_MS[name]} ms)"
        for name in BASELINE_MS
    )
    print(f"[LSP stability @ {len(source.splitlines())} lines]\n{report}")

    assert not failures, f"requests failed at 10k lines: {failures}"
    for name, ceiling in CEILING_MS.items():
        assert timings[name] < ceiling, (
            f"{name} took {timings[name]:.0f} ms (ceiling {ceiling} ms)"
        )

    # The heavy requests must actually have produced work, not silently no-op.
    assert caps is not None and caps.workspace_symbol_provider is not None
    assert caps.execute_command_provider is not None
    assert tokens is not None and tokens.data
    assert len(server._symbols[uri].global_scope.symbols) > 1000

    # The corpus is real code: checking it must publish no diagnostics at all.
    assert published and published[-1][0] == uri
    assert published[-1][1] == [], f"10k corpus is not clean: {published[-1][1][:1]}"
