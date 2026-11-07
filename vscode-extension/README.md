# PenguScript for Visual Studio Code

Official editor support for **PenguScript 0.38.0**: language server, syntax
highlighting, snippets, project commands and a status bar.

## Requirements

- VS Code **1.82** or newer.
- A `psc` binary selected with `pengus.executablePath`, `$PENGU_PSC`, the
  persistent `~/.config/pengu/env.json` written by `tools/build.sh`, `$PATH`, or
  a standard install location (`~/psc/psc`, `~/.local/bin/psc`,
  `/usr/local/bin/psc`, `./bin/psc`, `./build/psc`).

The extension does **not** execute a project-local `psc` in an untrusted
workspace. Trust the folder or select a user-installed binary first.

## Features

### Language Server (`psc lsp --stdio`)

- **Diagnostics** with the compiler's `help:` and `note:` text, primary/secondary
  spans and `relatedInformation`.
- **Hover** with English docs for keywords and built-in types, the resolved
  type/signature, `#`/`##` comments, fields/variants, byte size and alignment.
- **Completion** for keywords, built-in/user types, local variables, parameters,
  imported module members (`spark.`), standard-library modules (`import std.`),
  and receiver members: enchantment methods (`calling s.`), fields and variants.
- **Go to Definition** for locals, functions, methods, types and imported
  modules (including `std/*`).
- **Inlay hints**: inferred types for unannotated `var`/`let`/`static var`, and
  byte-size/alignment hints (`≈ N B`) for named types; annotated bindings are
  not duplicated and variables never get a size hint.
- **Semantic tokens** from the real lexer: keywords, types, functions,
  namespaces, parameters, properties, enum members, strings, numbers, comments
  and operators.
- **Document/workspace symbols**, signature help, folding, document formatting,
  code actions, references and rename where the symbol is safe to rename.
- **Code lens** above `weave main` and `test` blocks; runs the current file.

### C inside `antiquus` blocks

- The `r""" … """` body of an `antiquus` block is highlighted with the **C
  grammar** (`meta.embedded.block.c`), not as a plain string.
- If `clangd` is on your `PATH`, each block also gets a real C language server:
  **diagnostics** mapped back onto the `.pengu` file, **hover**, **definition**,
  **references**, **rename**, **signature help** and **completion**. A shadow
  `.c` file is generated under the extension storage and positions are
  translated in both directions.
- Toggle it with `pengus.antiquus.enabled`; point at a specific binary with
  `pengus.antiquus.clangdPath`. When clangd is missing the feature is silently
  skipped.

### Editor assets

- TextMate grammar for the 0.21.x syntax: `set`, `derive`, `cyclus`,
  `antiquus`, `enchanting`, `bind`, `seal`, concepts (`Real`, `Iterabilis`, …),
  `pipe`, `size of`/`align of`/`sigil of`/`essence of`/`bytes of`/`type of`,
  `at`/`length`, `ref to frozen T`, `@align(N)`, doc blocks and user types.
- 128 snippets: main, runes/echos/omens, concepts/bind, generics, `with`,
  `judge`, `defer`, `antiquus`, tests, docs and standard-library imports.
- Language configuration with indentation, comment continuation and auto-closing.

### Project commands and status bar

- **Run Project**, **Build Project**, **Run Tests**, **Check File**, **Generate
  Documentation**, **Clean Project**, **Initialize Project**, **Select psc** and
  **Restart Language Server**.
- **Status bar** item (`PenguScript (profile)`) that opens the command menu.

## Settings

| Setting | Default | Description |
|---|---|---|
| `pengus.executablePath` | `""` | Path or bare name of `psc`. |
| `pengus.defaultProfile` | `"debug"` | `debug`, `release` or `small` for build/run. |
| `pengus.stdDir` | `""` | Explicit stdlib directory (also `PENGU_STD_DIR` (legacy `PSC_STD_DIR`)). |
| `pengus.trace.server` | `"off"` | LSP trace level (`off`, `messages`, `verbose`). |
| `pengus.inlayHints.enabled` | `true` | Master switch for inlay hints. |
| `pengus.inlayHints.sizes` | `true` | Byte-size/alignment hints for named types. |
| `pengus.inlayHints.types` | `true` | Inferred-type hints for unannotated bindings. |
| `pengus.semanticHighlighting.enabled` | `true` | Use LSP semantic tokens. |
| `pengus.statusBar.enabled` | `true` | Show the status bar item. |
| `pengus.antiquus.enabled` | `true` | C language server (clangd) inside `antiquus` blocks. |
| `pengus.antiquus.clangdPath` | `"clangd"` | Path or name of the clangd executable. |

## Install

### From a VSIX

```bash
cd vscode-extension
npm ci
npm run package
```

Then **Extensions → … → Install from VSIX…** and pick
`pengus-4.1.0.vsix`.

### Development

```bash
cd vscode-extension
npm ci
npm run compile
```

Press `F5` to launch an Extension Development Host window.

## Troubleshooting

- **`cannot resolve imported module 'std.*'`** — check `psc --version`, then set
  `pengus.executablePath` or `PENGU_STD_DIR`. The LSP searches
  `$PENGU_STD_DIR` (legacy `$PSC_STD_DIR`), `<project>/std`, `<psc>/../std`,
  `<psc>/../share/pengu/std` and `$PENGU_HOME/std`.
- **The extension does not start** — open the **PenguScript** output channel;
  the client logs the resolved binary and protocol errors there.
- **No colors** — check `pengus.semanticHighlighting.enabled`; if the LSP is
  unavailable, TextMate still highlights keywords and comments.
- **No snippets** — verify the editor language mode is `PenguScript` (`.pengu`)
  and that `editor.snippetSuggestions` is not `none`.

## Compatibility

| Extension | Compiler |
|---|---|
| 4.9.0 | 0.26.x |
| 4.8.0 | 0.23.x |
| 4.7.0 | 0.22.0 |
| 4.5.0 | 0.21.0 |
| 4.1.0 | 0.17.3 |
| 4.0.0 | 0.15.0 |
| 3.2.x | 0.14.x |
