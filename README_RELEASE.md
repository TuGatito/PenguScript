# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

## Directory Structure

```
pengucc_build/
├── pengu .exe                # Standalone PenguScript CLI (Compiler + Build Manager + LSP)
├── pengus-0.6.0.vsix         # VS Code Extension (Syntax, LSP, Go-To-Definition, Cargo Commands)
├── std/                      # Complete Standard Library (24 modules)
│   ├── spark.pengu
│   ├── oracle.pengu
│   ├── ward.pengu
│   ├── trial.pengu
│   └── ... (all .pengu modules)
└── runtime/                  # C Runtime and static dependencies
    ├── pengu_runtime.h       # Master runtime header
    ├── libpengu_runtime.a    # Static runtime library
    └── include/              # Header files for regex, XML, crypto, HTTP, etc.
```

---

## Quick Start

### 1. Add PenguScript to your PATH
Add `D:\Proyectos\PenguScript\pengucc_build` to your system `PATH` environment variable to access `pengu` from any terminal or command prompt.

### 2. Install the VS Code Extension
1. Open Visual Studio Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Click the `...` menu (Views and More Actions) in the top-right corner.
4. Select **Install from VSIX...** and choose `D:\Proyectos\PenguScript\pengucc_build\pengus-0.6.0.vsix`.

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
- `pengu clean`        : Cleans intermediate build artifacts.
- `pengu lsp`          : Starts the Language Server Protocol (LSP) for VS Code / Neovim.
