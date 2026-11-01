# PenguScript Language Server (`psc lsp`)

`psc lsp` is a JSON-RPC 2.0 language server over stdio or TCP. It uses the
compiler's `SemaProgram` (AST, types, symbols, docs and diagnostics), not text
heuristics.

## Start

```bash
psc lsp --stdio
psc lsp --tcp --host=127.0.0.1 --port=2087
```

VS Code starts it automatically through the extension:

```json
{ "command": "psc", "args": ["lsp", "--stdio"] }
```

## Features

| Feature | Notes |
|---|---|
| Diagnostics | Primary/secondary spans, `help:`, `note:`, `relatedInformation`, `source: "psc"`. Pushed on open, change and save. |
| Hover | Canonical type/signature, English docs for keywords and builtin types, `#`/`##` docs, fields/variants, byte size and alignment (ABI v3, 64-bit). |
| Completion | Keywords, types, locals, params, `std.*` modules, imported-module exports, and **members**: enchantment methods, rune/echo fields and omen variants resolved from the receiver type (`calling s.` offers `string` methods). |
| Definition | Locals, functions, methods, fields and imported modules; jumps to the name, not the whole declaration. |
| References / highlight | Symbol-based (not textual), across open documents; `includeDeclaration` honored. |
| Rename | Symbol-safe; `prepareRename` returns the identifier range. Limited to open documents (cross-file rename needs the workspace loaded). |
| Signature help | `calling f with a, b`; resolves methods and module functions, tracks `activeParameter` after `with`. |
| Inlay hints | Inferred types for `var`/`let`/`static var` without annotation; `≈ N B` size+alignment hints for named types. Variables never get a size hint (hover instead). Filtered by `range` and configurable. |
| Semantic tokens | Keyword/type/function/variable/string/number/comment/namespace/parameter/property/enumMember/operator, UTF-16 (`positionEncoding: "utf-16"`), incremental sync. |
| Symbols | Document outline (deduplicated, name selection range) and workspace symbols. |
| Folding | Indentation regions with `kind: "region"`. |
| Code actions | Format document and “Add documentation comment”. |
| Code lens | `pengus.run`/`pengus.test` with the document URI and offset. |
| Formatting | `psc fmt` through the language server. |

## Configuration

`initializationOptions` (all optional):

```json
{
  "stdDir": "/path/to/std",
  "executablePath": "/path/to/psc",
  "inlayHints": true,
  "inlayHintOptions": { "sizes": true, "types": true },
  "semanticHighlighting": true
}
```

`workspace/didChangeConfiguration` updates the inlay/semantic toggles without a
restart:

```json
{ "settings": { "pengus": { "inlayHints": { "enabled": true, "sizes": true, "types": true }, "semanticHighlighting": true } } }
```

## Stdlib resolution

The checker searches, in order:

1. `$PSC_STD_DIR`, `$PENGU_STD_DIR`;
2. `<project>/std`;
3. `<psc>/../std` (portable release);
4. `<psc>/../share/pengu/std` (FHS release);
5. `$PENGU_HOME/std`, `$PENGU_HOME/share/pengu/std`;
6. `<cwd>/std`.

The LSP also accepts `initializationOptions.stdDir` (the VS Code setting
`pengus.stdDir`).

## Memory and ownership

Every open document owns its `SemaResult`. `didChange` frees the previous
result, `didClose` frees it and the document text. Diagnostics are built from
`std.diagnostic.Diagnostic` directly, without a JSON round-trip.

## Tests

```bash
python3 tests/lsp/run_lsp_tests.py
python3 tests/lsp/test_assets.py
```

`run_lsp_tests.py` starts a real `psc lsp --stdio` in a fixture project and
asserts diagnostics, hover/docs, inlay hints, completion, code lens, semantic
tokens, definition and rich diagnostics.
