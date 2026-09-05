# PenguScript Visual Studio Code Extension

Official VS Code extension for **PenguScript** — a statically typed programming language that combines the elegance of Python with the speed, memory safety, and performance of C.

---

## Features

- **Language Server Protocol (LSP)**:
  - **Contextual Documentation**: Automatically displays docstrings extracted from `#` and `## ... ##` comments.
  - **Advanced Type & Size Hover**: Real-time memory footprint estimation in bytes (e.g. `rune Vec2 (8 bytes)`), detailed field breakdown, and function signatures.
  - **Module-Scoped Autocompletion**: Type `spark.` or `ledger.` to immediately autocomplete exported module functions, types, and constants.
  - **Go to Definition**: F12 jump to definition across local variables, functions, and external standard library modules.
  - **Diagnostics with Visual Highlights**: Rich compiler error messages with `help:`, `note:`, and line spans.
- **Cargo-like Project Integration**:
  - **Build Project** (`PenguScript: Build Project`)
  - **Run Project** (`PenguScript: Run Project`)
  - **Clean Project** (`PenguScript: Clean Project`)
  - **Init New Project** (`PenguScript: Initialize New Project`)
- **Status Bar Item**: Quick status bar menu with one-click access to build, run, and server restart.

---

## Configuration Settings

You can customize the extension via VS Code Settings (`Ctrl+,` / `Cmd+,`) under **PenguScript**:

| Setting | Default | Description |
|---|---|---|
| `pengus.executablePath` | `""` | Absolute path to the standalone `pengu` or `pengu.exe` binary. |
| `pengus.defaultProfile` | `"debug"` | Default build profile (`debug` or `release`). |

---

## Installation

### Method A: Install from `.vsix` package
1. Build the release package using `python make_release.py` or run:
   ```bash
   cd vscode-extension
   npm install
   npm run package
   ```
2. In VS Code:
   - Open the Extensions view (`Ctrl+Shift+X`).
   - Click the `...` menu (Views and More Actions) in the top-right.
   - Select **Install from VSIX...** and pick `pengus-0.6.0.vsix`.

### Method B: Development / Local Testing
1. Clone the repository and install npm dependencies:
   ```bash
   cd vscode-extension
   npm install
   npm run compile
   ```
2. Press `F5` in VS Code to launch the Extension Development Host window.

---

## v0.3 Feature Support & Extension Notes

The grammar/highlighter and snippets now cover the v0.3 language extensions:

- **New keywords highlighted**: `when` (compile-time conditionals), `test` (unit tests), `static` (`static var`), `defined(...)`, and `omen ... with string`.
- **New snippets**: `when`, `when_expr`, `test`, `test_name`, `static_var`, `map_lit`, `import_as`, `for_i`, `omen_string`.
- **Doc comments**: single-line `## text`, self-closed `## text ##` and multi-line `##` ... `##` doc comments are recognized and feed LSP hover tooltips.

### Running the new tooling

The new commands live in the `pengu` CLI; run them from VS Code's integrated terminal:

```bash
pengu test                    # compile in --test mode and run the unit tests
pengu build --test            # emit a bundle whose main runs the tests
pengu doc                     # generate Markdown docs from ## comments (default ./docs)
pengu doc -o site/docs        # custom output directory
pengu build -D os=linux       # compile-time defines for `when` clauses
```

### Wiring commands into the extension (optional)

To add first-class VS Code commands for `pengu test` / `pengu doc`:

1. `package.json` -> `contributes.commands`: add entries with `command: "pengus.test"` / `command: "pengus.doc"` and matching titles.
2. `src/extension.ts`: register the commands in the activation function using the same `runPengu`/`runCli` helper used by the existing `pengus.build` / `pengus.run` commands, passing `--test` / `doc` arguments (then recompile with `npm run compile`).
3. Optional: surface them in the menu built by `pengus.showMenu`.
