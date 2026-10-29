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
  - **Run Tests** (`PenguScript: Run Tests`)
  - **Generate Documentation** (`PenguScript: Generate Documentation`)
  - **Clean Project** (`PenguScript: Clean Project`)
  - **Init New Project** (`PenguScript: Initialize New Project`)
  - **Show Menu** (`PenguScript: Show Menu`)
  - **Restart Language Server** (`PenguScript: Restart Language Server`)
- **Status Bar & QuickPick Menu**: Quick menu with one-click access to build, run, test, doc, clean, init, and server restart.

---

## Configuration Settings

You can customize the extension via VS Code Settings (`Ctrl+,` / `Cmd+,`) under **PenguScript**:

| Setting | Default | Description |
|---|---|---|
| `pengus.executablePath` | `""` | Absolute path to the standalone `psc` binary (`bin/psc` in a release). |
| `pengus.defaultProfile` | `"debug"` | Default build profile (`debug` or `release`). |

---

## Installation

### Method A: Install from `.vsix` package
1. Build the release package:
   ```bash
   cd vscode-extension
   npm ci
   npm run package
   ```
2. In VS Code:
   - Open the Extensions view (`Ctrl+Shift+X`).
   - Click the `...` menu (Views and More Actions) in the top-right.
   - Select **Install from VSIX...** and pick `pengus-3.2.0.vsix`.

### Method B: Development / Local Testing
1. Clone the repository and install npm dependencies:
   ```bash
   cd vscode-extension
   npm ci
   npm run compile
   ```
2. Press `F5` in VS Code to launch the Extension Development Host window.

---

## Convenient Containers (0.13+)

The grammar and snippets know the CC-backed types added in PenguScript 0.13:

- `LinkedList of T` (CC `list`)
- `UnorderedSet of T` (CC `set`)
- `OrderedSet of T` (CC `oset`)
- `OrderedMap of K and V` (CC `omap`)

`T`/`K`/`V` may be `int`, `string`, a user rune, or another value type.

Import `std.ordinal` and use the `linked_list`, `unordered_set`, `ordered_set`,
`ordered_map` or `cc_import` snippets. The existing `list`, `map`, `Set` and
`SetString` APIs are unchanged; they are now backed by CC `vec`/`map`.

## v0.15.0 Feature Support & Enhancements

The grammar, syntax highlighter, and snippet collection cover the modern PenguScript 0.15.0 language specification:

- **Concept & Trait System**:
  - `concept Name:` interface declarations and `bind Type with Concept:` implementation blocks.
  - `derive Concept1, Concept2` for automated structural derivations (`Nexus`, `Imago`, `Equitas`, `Donum`...).
  - `where T: Concept` generic constraint clauses.
  - `ritual weave` static and factory methods.
  - `seal NewType as Type` strong opaque newtype wrappers.
  - Highlighted built-in concepts: `Imago`, `Nexus`, `Donum`, `Equitas`, `Ordo`, `Index`, `IndexSet`, `Iter`, `Len`, `Display`, `Debug`, `Copy`, `Clone`, `Drop`, `Num`, `Integrum`, `Par`, `Vinculum`, `Forma`.
- **Recursive Types & Cycles**:
  - `cyclus` keyword on runes, echos, and omens (`rune Node cyclus shard T:`).
- **Immutability & Manual Memory**:
  - `frozen` modifier for immutable views (`var s as frozen string`, `ref to frozen char`, `frozen int`).
  - `banish x` frees what `x` owns; `defer banish x` schedules the free at scope exit. Nothing is released for you.
  - `donum T` default-value expression for defaultable types.
  - `defer:` and `errdefer:` blocks with proper indentation rules and snippets.
- **Literals & Expressions**:
  - Number formats: binary (`0b101`), octal (`0o755`), hexadecimal (`0xDEAD_BEEF`), and floats with exponents (`1e-6`, `2.5E+3`).
  - Character literals with hex (`'\x41'`) and octal (`'\101'`) escapes.
  - Multi-line raw strings (`r"""..."""`) and formatted strings with embedded `{expression}` interpolation.
- **Over 110+ Interactive Snippets**:
  - Structs & tagged unions (`rune`, `rune_derive`, `rune_cyclus`, `echo`, `echo_derive`, `omen`, `omen_derive`, `omen_string_derive`).
  - Functions & methods (`weave`, `weave_inline`, `weave_ritual`, `weave_where`, `slice_param`, `many_param`).
  - Concepts & bindings (`concept`, `concept_ritual`, `bind`, `bind_where`, `seal`).
  - Control flow & error handling (`judge`, `judge_payload`, `or_else`, `or_return`, `or_block_err`, `defer_block`, `errdefer_block`, `try`).
  - Platform conditionals (`when_os`, `when_arch`, `when_compiler`, `when_defined`, `when_debug`).
  - Testing (`test`, `test_ward`).

### Running PenguScript Tooling

The commands are integrated into the command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and the status bar menu:

- **PenguScript: Run Project** (`psc run`)
- **PenguScript: Build Project** (`psc build`)
- **PenguScript: Run Tests** (`psc test`)
- **PenguScript: Generate Documentation** (`psc doc`)
- **PenguScript: Clean Project** (`psc clean`)
- **PenguScript: Initialize New Project** (`psc init`)
- **PenguScript: Restart Language Server** (`psc lsp`)
- **PenguScript: Show Menu** (interactive quick-pick launcher)
