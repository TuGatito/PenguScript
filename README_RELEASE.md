# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

> **TinyCC is bundled.** Release archives ship a `tcc` binary (under `tcc/`)
> that `pengu run` prefers for development builds; if it is missing the
> toolchain transparently falls back to your system `gcc`/`clang`. Check with
> `pengu doctor`.
>
> **A shared PCH ships too** (`runtime/include/pengu_runtime.h.gch`). It is
> opt-in (`--pch`) and gcc only uses it when the build's `-D`/`-I` set matches
> the one it was built with; otherwise gcc ignores it silently and parses the
> header normally. See `docs/PERFORMANCE.md` §7.

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
- `pengu run`          : Builds and runs the binary immediately (or a standalone `.pengu` script).
- `pengu assets`       : Inspects (`--list`) or regenerates (`--force`) embedded project assets.
- `pengu clean`        : Cleans intermediate build artifacts.
- `pengu lsp`          : Starts the Language Server Protocol (LSP) for VS Code / Neovim.
- `pengu doctor`       : Reports compiler/TCC/runtime/cache health (`--json` for CI).
- `pengu gc`           : Collects unused cached script binaries (`--all`, `--max-age N`).
- `pengu expand`       : Prints the generated `bundle.c` of a script (`-o FILE`).
- `pengu time`         : Per-phase timings for a script build+run.
- `pengu eval "<expr>"`: Evaluates a one-line expression through the binary cache.
- `pengu watch`        : Re-runs a script whenever it or one of its imports changes.

Script runs accept `--keep`, `--no-cache`, `--clear-cache`, `--ephemeral`,
`--pch`/`--no-pch`, `--no-dce`, `--quiet` and `--no-color` (or `NO_COLOR=1`);
everything after `--` is forwarded to the script.
