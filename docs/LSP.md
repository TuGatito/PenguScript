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
| Diagnostics | Primary/secondary spans, `help:`, `note:`, `relatedInformation`, `source: "psc"`. |
| Hover | Canonical type, signature, `#`/`##` docs, fields/variants, approximate size. |
| Completion | Keywords, types, locals, params, members (`spark.`), `std.*` modules. |
| Definition | Locals, functions, methods, types and imported modules. |
| Inlay hints | Inferred types; explicit `as T` annotations are not duplicated. |
| Semantic tokens | Lexer-driven keyword/type/function/namespace/parameter/property/string/number/comment/operator tokens, UTF-16. |
| Symbols | Document and workspace outline. |
| Code lens | `pengus.run`/`pengus.test` with the document URI and offset. |
| Formatting | `psc fmt` through the language server. |

Rename is deliberately **not advertised** until it is symbol-safe; the textual
fallback could corrupt strings/comments.

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
