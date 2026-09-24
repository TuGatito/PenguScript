# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

## Directory Structure

```
\
pengucc_build/
├── bin/pengu                        # Standalone CLI + LSP server
├── lib/pengu/*.a                    # Runtime static libraries
├── include/pengu/*.h                # Runtime + dependency headers
├── share/pengu/std/                 # Standard library modules
├── share/pengu/VERSION
├── pengus-0.14.0.vsix     # VS Code extension
├── install.sh                       # FHS installer (PREFIX/DESTDIR aware)
└── uninstall.sh
```

---

## Quick Start

\
### 1. Install

```bash
./install.sh                         # ~/.local
PREFIX=/usr/local sudo ./install.sh  # system-wide
DESTDIR=/tmp/stage PREFIX=/usr ./install.sh   # package-manager staging
```


### 2. Install the VS Code Extension
1. Open Visual Studio Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Click the `...` menu (Views and More Actions) in the top-right corner.
4. Select **Install from VSIX...** and choose `/home/tugatito/Documentos/GitHub/PenguScript/pengucc_build/pengus-0.14.0.vsix`.

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
