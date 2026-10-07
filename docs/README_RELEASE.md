# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

## Directory Structure

```
\
pengucc_build/
├── pengu
├── pengus-1.0.0.vsix
├── std/
└── runtime/
    ├── pengu_runtime.h
    ├── libpengu_runtime.a
    └── include/
```

---

## Quick Start

\
### 1. Add to PATH
Add this directory (the one holding the `pengu` binary) to your system `PATH`
environment variable. It is the `pengucc_build/` directory of the unpacked
archive; the path is relative on purpose so the generated guide does not embed
the build machine's absolute layout (Phase 9, finding F9-N8).


### 2. Install the VS Code Extension
1. Open Visual Studio Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Click the `...` menu (Views and More Actions) in the top-right corner.
4. Select **Install from VSIX...** and choose `pengucc_build/pengus-1.0.0.vsix` (relative to the unpacked archive).

### 3. Create a new project
```bash
pengu init my_app --type exe --links pengu_runtime
cd my_app
```

### 4. Build and Run
```bash
# Build optimized binary
pengu build --profile release

# Build and execute directly
pengu run
```

### 5. Available Commands
- `pengu init <name>` : Initializes a new project template with `pengu.toml`.
- `pengu build`        : Bundles and compiles to executable / static lib / DLL.
- `pengu run`          : Builds and runs the binary immediately.
- `pengu assets`       : Inspects (`--list`) or regenerates (`--force`) embedded project assets.
- `pengu clean`        : Cleans intermediate build artifacts.
- `pengu lsp`          : Starts the Language Server Protocol (LSP) for VS Code / Neovim.
