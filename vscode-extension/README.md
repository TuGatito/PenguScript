# PenguScript for Visual Studio Code

Official editor support for **PenguScript 0.17.3**: language server, syntax
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
- **Hover** with the resolved type, function signature, documentation from `#` /
  `##` comments, fields/variants and an approximate byte size.
- **Completion** for keywords, built-in/user types, local variables, parameters,
  imported module members (`spark.`), standard-library modules (`import std.`)
  and documentation strings.
- **Go to Definition** for locals, functions, methods, types and imported
  modules (including `std/*`).
- **Inferred type inlay hints**; annotated bindings are not duplicated.
- **Semantic tokens** from the real lexer: keywords, types, functions,
  namespaces, parameters, properties, enum members, strings, numbers, comments
  and operators.
- **Document/workspace symbols**, signature help, folding, document formatting,
  code actions, references and rename where the symbol is safe to rename.
- **Code lens** above `weave main` and `test` blocks; runs the current file.

### Editor assets

- TextMate grammar for the 0.17.2 syntax: `set`, `derive`, `cyclus`,
  `antiquus`, `enchanting`, `bind`, `seal`, concepts (`Real`, `Iterabilis`, …),
  doc blocks and user types in type position.
- 120+ snippets: main, runes/echos/omens, concepts/bind, generics, `with`,
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
| `pengus.inlayHints.enabled` | `true` | Show inferred type hints. |
| `pengus.semanticHighlighting.enabled` | `true` | Use LSP semantic tokens. |
| `pengus.statusBar.enabled` | `true` | Show the status bar item. |

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
| 4.1.0 | 0.17.3 |
| 4.0.0 | 0.15.0 |
| 3.2.x | 0.14.x |
