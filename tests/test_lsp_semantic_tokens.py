"""Roadmap Phase 3 / §3.2 (semantic tokens, inlay hints) and §3.9 (code lens)."""

from lsprotocol.types import (
    CodeLensParams,
    InlayHintParams,
    Position,
    Range,
    SemanticTokensParams,
    TextDocumentIdentifier,
)

from tests.test_lsp import checked_symbols

URI = "file:///sem.pengu"


def _register(source, uri=URI, filename="sem.pengu"):
    from pengu_lsp.server import server

    symbols = checked_symbols(source, filename=filename)
    server._symbols[uri] = symbols
    server._docs[uri] = source
    return symbols


def _decode(data):
    """Absolute (line, col, length, type, mods) from the LSP relative encoding."""
    out = []
    line = 0
    col = 0
    i = 0
    while i < len(data):
        dl, dc, length, ttype, mods = data[i:i + 5]
        if dl == 0:
            col += dc
        else:
            line += dl
            col = dc
        out.append((line, col, length, ttype, mods))
        i += 5
    return out


_SRC = (
    "weave add with a as int, b as int into int:\n"
    "    let total is a + b\n"
    "    var msg as string is \"sum\"\n"
    "    return total\n"
    "\n"
    "weave main into int:\n"
    "    return calling add with 1, 2\n"
)


def _token_type_names(data, legend_names):
    return [legend_names[t] for _l, _c, _len, t, _m in _decode(data)]


def test_semantic_tokens_classify_symbols():
    from pengu_lsp.server import _SEMANTIC_TOKEN_TYPES, semantic_tokens_full

    _register(_SRC)
    res = semantic_tokens_full(SemanticTokensParams(
        text_document=TextDocumentIdentifier(uri=URI)))
    assert res is not None and res.data
    kinds = _token_type_names(res.data, _SEMANTIC_TOKEN_TYPES)
    assert "keyword" in kinds
    assert "function" in kinds       # add / main
    assert "parameter" in kinds      # a / b
    assert "variable" in kinds       # total / msg
    assert "string" in kinds
    assert "number" in kinds


def test_semantic_tokens_encoding_is_sorted_and_relative():
    from pengu_lsp.server import semantic_tokens_full

    _register(_SRC)
    res = semantic_tokens_full(SemanticTokensParams(
        text_document=TextDocumentIdentifier(uri=URI)))
    decoded = _decode(res.data)
    assert decoded == sorted(decoded, key=lambda e: (e[0], e[1]))
    assert all(length > 0 for _l, _c, length, _t, _m in decoded)


def test_semantic_tokens_readonly_and_declaration_modifiers():
    from pengu_lsp.server import (
        _SEMANTIC_TOKEN_MODIFIERS, semantic_tokens_full,
    )

    src = (
        "weave f with a as int into int:\n"
        "    let ro is a\n"
        "    var mu as int is 1\n"
        "    return ro + mu\n"
    )
    _register(src)
    res = semantic_tokens_full(SemanticTokensParams(
        text_document=TextDocumentIdentifier(uri=URI)))
    ro_flag = 1 << _SEMANTIC_TOKEN_MODIFIERS.index("readonly")
    decl_flag = 1 << _SEMANTIC_TOKEN_MODIFIERS.index("declaration")
    ro_mods = [m for _l, _c, _len, _t, m in _decode(res.data) if m & ro_flag]
    assert ro_mods, "let-bound symbols must carry the readonly modifier"
    assert any(m & decl_flag for _l, _c, _len, _t, m in _decode(res.data))


def test_inlay_hint_for_untyped_var_only():
    from pengu_lsp.server import inlay_hints

    src = (
        "weave f into int:\n"
        "    var a is 42\n"
        "    var b as int is 7\n"
        "    return a + b\n"
    )
    _register(src)
    res = inlay_hints(InlayHintParams(
        text_document=TextDocumentIdentifier(uri=URI),
        range=Range(start=Position(line=0, character=0), end=Position(line=9, character=0)),
    ))
    labels = [h.label for h in res]
    assert any(str(lb).startswith(": ") for lb in labels)
    # Only the untyped `a` is annotated.
    assert len([lb for lb in labels if str(lb).startswith(": ")]) == 1
    assert res[0].position.line == 1


def test_inlay_hint_call_argument_names():
    from pengu_lsp.server import inlay_hints

    _register(_SRC)
    res = inlay_hints(InlayHintParams(
        text_document=TextDocumentIdentifier(uri=URI),
        range=Range(start=Position(line=0, character=0), end=Position(line=20, character=0)),
    ))
    param_labels = [h.label for h in res if str(h.label).endswith(":")]
    assert param_labels == ["a:", "b:"]


def test_code_lens_per_test_block():
    from pengu_lsp.server import code_lenses

    src = (
        'test "adds":\n'
        "    var x as int is 1\n"
        "\n"
        'test "subtracts":\n'
        "    var y as int is 2\n"
    )
    _register(src)
    res = code_lenses(CodeLensParams(text_document=TextDocumentIdentifier(uri=URI)))
    assert len(res) == 2
    titles = [l.command.title for l in res]
    assert any("adds" in t for t in titles)
    assert any("subtracts" in t for t in titles)
    assert all(l.command.command == "pengu.runTest" for l in res)
    assert [l.range.start.line for l in res] == [0, 3]
    assert res[0].command.arguments == [URI, "adds"]


def test_capabilities_registered():
    """The three features are registered and semantic tokens carry their legend."""
    from pengu_lsp.server import server

    fm = server.protocol.fm
    for feature_name in (
        "textDocument/semanticTokens/full",
        "textDocument/inlayHint",
        "textDocument/codeLens",
    ):
        assert feature_name in fm.features, f"{feature_name} not registered"

    legend = fm.feature_options.get("textDocument/semanticTokens/full")
    assert legend is not None
    assert "keyword" in legend.token_types
    assert "function" in legend.token_types
    assert "readonly" in legend.token_modifiers
