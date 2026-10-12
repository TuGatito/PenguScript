# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

## Directory Structure

```
\
dist2/
├── pengu
├── pengus-2.0.0.vsix
├── std/                             # 21 pure-PenguScript modules
└── runtime/
    ├── pengu_runtime.h
    ├── libpengu_runtime.a           # self-contained: libc/libm/pthreads only
    └── include/                     # pengu_runtime.h + optional shared PCH
```

---

## Quick Start

\
### 1. Add to PATH
Add this directory (the one holding the `pengu` binary) to your system `PATH`
environment variable. It is the `dist2/` directory of the unpacked
archive; the path is relative on purpose so the generated guide does not embed
the build machine's absolute layout (Phase 9, finding F9-N8).


### 2. Install the VS Code Extension
1. Open Visual Studio Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Click the `...` menu (Views and More Actions) in the top-right corner.
4. Select **Install from VSIX...** and choose `dist2/pengus-2.0.0.vsix` (relative to the unpacked archive).

### 3. Create a new project
```bash
pengu new exe my_app        # templates: exe, cli, lib
cd my_app
```

External C bindings are installed per project from satellite repositories:

```bash
pengu add https://github.com/pengu-lang/pengu-raylib
pengu update
```

### 4. Build and Run
```bash
# Build optimized binary
pengu build --profile release

# Build and execute directly
pengu run
```

### 5. Available Commands
- `pengu init <name>`  : Creates a project (`--template exe|cli|lib`).
- `pengu new <t> <n>`  : Template-first front end for `init`.
- `pengu add <url>`    : Installs a satellite binding/dependency into `lib/<name>/`.
- `pengu update`       : Pulls and rebuilds every configured dependency.
- `pengu build`        : Bundles and compiles to executable / static lib / shared lib / C.
- `pengu run`          : Builds and runs the binary immediately.
- `pengu check`        : Parses and type-checks without generating code.
- `pengu bind <h>`     : Generates a `.d.pengu` binding from a C header.
- `pengu fmt`          : Formats `.pengu` sources.
- `pengu assets`       : Inspects (`--list`) or regenerates (`--force`) embedded project assets.
- `pengu clean`        : Cleans intermediate build artifacts.
- `pengu lsp`          : Starts the Language Server Protocol (LSP) for VS Code / Neovim.
