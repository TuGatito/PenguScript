#!/usr/bin/env python3
"""
make_release.py - Automated Release & Packaging Script for PenguScript

This script automates:
1. Virtual environment (.venv) verification and dependency installation (PyInstaller, Lark, PyYAML, etc.).
2. Clean static compilation of the C runtime and dependencies (build_runtime.py --rebuild).
3. Assembling the release distribution directory (pengucc_build/).
   - std/ : All standard library PenguScript modules.
   - runtime/ : pengu_runtime.h, static libraries (*.a / *.lib), and dependency headers.
4. Packaging the PenguScript CLI & LSP server with PyInstaller into a standalone executable (pengu / pengu.exe).
5. Automated smoke test: verifying CLI help, project initialization, and end-to-end compilation with the standalone binary.

Usage:
    python make_release.py [--rebuild] [--skip-tests] [--dist-dir DIR]
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
STD_DIR = ROOT_DIR / "std"
DEFAULT_DIST_DIR = ROOT_DIR / "pengucc_build"

IS_WINDOWS = sys.platform.startswith("win")


def log_step(step_num: int, total_steps: int, msg: str):
    print(f"\n[{step_num}/{total_steps}] {msg}")
    sys.stdout.flush()


def run_cmd(cmd, cwd=None, check=True, env=None, capture=False):
    """Executes a command and streams output or fails gracefully."""
    print(f"  [EXEC] {' '.join(str(c) for c in cmd)}")
    sys.stdout.flush()
    if capture:
        res = subprocess.run(cmd, cwd=cwd or str(ROOT_DIR), capture_output=True, text=True, env=env)
        if check and res.returncode != 0:
            print(f"\n[ERROR] Command failed with exit code {res.returncode}: {' '.join(str(c) for c in cmd)}\nStderr: {res.stderr}\nStdout: {res.stdout}")
            sys.exit(res.returncode)
        return res
    else:
        res = subprocess.run(cmd, cwd=cwd or str(ROOT_DIR), check=False, text=True, env=env)
        if check and res.returncode != 0:
            print(f"\n[ERROR] Command failed with exit code {res.returncode}: {' '.join(str(c) for c in cmd)}")
            sys.exit(res.returncode)
        return res


def get_venv_python() -> Path:
    """Finds or creates a virtual environment and returns its python executable."""
    venv_dir = ROOT_DIR / ".venv"
    if not venv_dir.exists():
        print("  [VENV] Creating .venv virtual environment...")
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])

    if IS_WINDOWS:
        py_exe = venv_dir / "Scripts" / "python.exe"
    else:
        py_exe = venv_dir / "bin" / "python"

    if not py_exe.exists():
        # Fallback to current sys.executable
        return Path(sys.executable)
    return py_exe


def ensure_dependencies(py_exe: Path):
    """Ensures all necessary Python dependencies are installed in the venv."""
    packages = [
        "pyinstaller>=6.0",
        "lark>=1.1.0",
        "pyyaml>=6.0",
        "pygls>=2.0.0",
        "lsprotocol>=2023.0.0",
        "pytest>=7.0.0",
    ]
    if sys.version_info < (3, 11):
        packages.append("tomli>=2.0.0")

    print("  [PIP] Checking / installing required packages...")
    cmd = [str(py_exe), "-m", "pip", "install", "--upgrade"] + packages
    run_cmd(cmd)


def ensure_external_libraries():
    """Downloads and unpacks external C libraries defined in extern_manifest.py."""
    from extern_manifest import download_and_extract_externs
    download_and_extract_externs(ROOT_DIR / "extern")


def build_runtime(py_exe: Path, rebuild: bool = True):
    """Compiles all static external libraries and libpengu_runtime.a."""
    ensure_external_libraries()

    build_script = ROOT_DIR / "build_runtime.py"
    if not build_script.exists():
        print(f"[ERROR] build_runtime.py not found in {ROOT_DIR}")
        sys.exit(1)

    cmd = [str(py_exe), str(build_script)]
    if rebuild:
        cmd.append("--rebuild")

    run_cmd(cmd)


def assemble_distribution(dist_dir: Path):
    """Assembles std/ and runtime/ directories into pengucc_build/."""
    dist_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy std/
    dst_std = dist_dir / "std"
    if dst_std.exists():
        shutil.rmtree(dst_std)
    shutil.copytree(STD_DIR, dst_std)
    print(f"  [STD] Copied standard library to {dst_std}")

    # 2. Setup runtime/
    dst_runtime = dist_dir / "runtime"
    dst_runtime.mkdir(parents=True, exist_ok=True)

    # Copy pengu_runtime.h
    runtime_h = ROOT_DIR / "pengu_runtime.h"
    if runtime_h.exists():
        shutil.copy2(runtime_h, dst_runtime / "pengu_runtime.h")

    # Copy all static libraries from build/lib/
    src_lib = BUILD_DIR / "lib"
    if src_lib.exists():
        for lib_file in src_lib.glob("*.*"):
            if lib_file.suffix in (".a", ".lib"):
                shutil.copy2(lib_file, dst_runtime / lib_file.name)
                print(f"  [LIB] Copied {lib_file.name} to runtime/")

    # Copy include directories from build/include/
    src_inc = BUILD_DIR / "include"
    dst_inc = dst_runtime / "include"
    if src_inc.exists():
        if dst_inc.exists():
            shutil.rmtree(dst_inc)
        shutil.copytree(src_inc, dst_inc)
        print(f"  [INC] Copied dependency headers to {dst_inc}")


def get_version() -> str:
    """Reads project version from VERSION file."""
    version_file = ROOT_DIR / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return "0.1.0"


def package_with_pyinstaller(py_exe: Path, dist_dir: Path):
    """Packages pengu_project.py into a standalone pengu / pengu.exe binary."""
    entry_point = ROOT_DIR / "pengu_project.py"
    data_sep = ";" if IS_WINDOWS else ":"

    add_data = [
        f"{str(STD_DIR)}{data_sep}std",
        f"{str(ROOT_DIR / 'pengu_runtime.h')}{data_sep}.",
        f"{str(ROOT_DIR / 'VERSION')}{data_sep}.",
    ]

    # Hidden imports that PyInstaller may not auto-detect
    hidden_imports = [
        "pygls",
        "pygls.lsp",
        "pygls.lsp.server",
        "pygls.protocol",
        "pygls.capabilities",
        "lsprotocol",
        "lsprotocol.types",
        "lsprotocol.converters",
        "cattrs",
        "attrs",
        "lark",
        "lark.parsers",
        "lark.parsers.lalr_parser",
        "pengu_lsp",
        "pengu_lsp.server",
        "pengu_lsp.completions",
        "pengu_lsp.hover",
        "pengu_parser",
        "pengu_parser.pengu_parser",
        "pengu_parser.pengu_checker",
        "pengu_parser.pengu_codegen",
        "pengu_parser.pengu_symbols",
        "pengu_parser.pengu_types",
        "pengu_parser.pengu_errors",
        "pengu_parser.pengu_infer",
        "pengu_parser.pengu_grammar",
    ]

    # Collect all submodules for packages with many internal modules
    collect_submodules = [
        "lsprotocol",
        "pygls",
        "cattrs",
        "attrs",
    ]

    cmd = [
        str(py_exe), "-m", "PyInstaller",
        "--clean",
        "--name", "pengu",
        "--onefile",
        "--console",
        "--distpath", str(dist_dir),
        "--workpath", str(BUILD_DIR / "pyinstaller_work"),
        "--specpath", str(BUILD_DIR),
        "--noconfirm",
    ]

    for item in add_data:
        cmd.extend(["--add-data", item])

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    for pkg in collect_submodules:
        cmd.extend(["--collect-submodules", pkg])

    cmd.append(str(entry_point))
    run_cmd(cmd)


def verify_executable(dist_dir: Path):
    """Runs smoke tests against the generated standalone binary."""
    exe_name = "pengu.exe" if IS_WINDOWS else "pengu"
    exe_path = dist_dir / exe_name

    if not exe_path.exists():
        print(f"[ERROR] Expected binary not found: {exe_path}")
        sys.exit(1)

    print(f"  [TEST 1] Verifying {exe_name} --help...")
    res = run_cmd([str(exe_path), "--help"], capture=True)
    print(res.stdout)
    assert "PenguScript" in res.stdout or "usage:" in res.stdout or "commands:" in res.stdout.lower()

    test_scratch = ROOT_DIR / "scratch" / "smoke_release_test"
    if test_scratch.exists():
        shutil.rmtree(test_scratch)
    test_scratch.mkdir(parents=True, exist_ok=True)

    print("  [TEST 2] Testing project initialization...")
    run_cmd([str(exe_path), "init", "smoke_proj", "--type", "exe", "--links", "pengu_runtime"], cwd=str(test_scratch))

    proj_dir = test_scratch / "smoke_proj"
    assert proj_dir.exists(), "smoke_proj was not created"

    # Add standard library and runtime assertion in test project
    main_pengu = proj_dir / "main.pengu"
    main_pengu.write_text(
        """import std.spark
import std.ward

weave main into void:
    calling spark.println with "Hello from Standalone PenguScript Release!"
    calling ward.assert_eq_int with 40 + 2 and 42
    calling spark.println with "Release smoke test passed!"
""",
        encoding="utf-8",
    )

    print("  [TEST 3] Testing standalone compilation and execution ('pengu run')...")
    run_res = run_cmd([str(exe_path), "run"], cwd=str(proj_dir), capture=True)
    print(run_res.stdout)
    assert "Release smoke test passed!" in run_res.stdout

    print("  [SUCCESS] All smoke tests passed!")


def build_vscode_extension(dist_dir: Path):
    """Builds and packages the VS Code extension into a .vsix artifact."""
    ext_dir = ROOT_DIR / "vscode-extension"
    if not ext_dir.exists():
        print(f"  [WARN] vscode-extension directory not found at {ext_dir}")
        return

    print("  [VSCODE] Packaging VS Code extension...")
    npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
    npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"

    try:
        # Check npm
        run_cmd([npm_cmd, "--version"], capture=True)
    except Exception:
        print("  [WARN] npm not found in system PATH. Skipping automated .vsix packaging.")
        return

    # 1. npm install and compile
    print("  [VSCODE] Installing npm dependencies...")
    run_cmd([npm_cmd, "install"], cwd=str(ext_dir))

    print("  [VSCODE] Bundling extension with esbuild...")
    run_cmd([npm_cmd, "run", "bundle"], cwd=str(ext_dir))

    # 2. Package .vsix
    print("  [VSCODE] Generating .vsix package with vsce...")
    run_cmd([npx_cmd, "-y", "@vscode/vsce", "package"], cwd=str(ext_dir))

    # 3. Copy .vsix to dist_dir
    vsix_files = list(ext_dir.glob("*.vsix"))
    for vf in vsix_files:
        dest_vsix = dist_dir / vf.name
        shutil.copy2(vf, dest_vsix)
        print(f"  [VSCODE] Copied {vf.name} -> {dest_vsix}")


def generate_release_readme(dist_dir: Path):
    """Creates README_RELEASE.md explaining how to use the distribution."""
    version = get_version()
    vsix_name = f"pengus-{version}.vsix"
    readme_content = f"""# PenguScript Standalone Release Package

This directory contains the standalone distribution of the **PenguScript Compiler, Project Manager, Standard Library, and Visual Studio Code Extension**.

---

## Directory Structure

```
{dist_dir.name}/
├── pengu{' .exe' if IS_WINDOWS else ''}                # Standalone PenguScript CLI (Compiler + Build Manager + LSP)
├── {vsix_name}         # VS Code Extension (Syntax, LSP, Go-To-Definition, Cargo Commands)
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
Add `{dist_dir.resolve()}` to your system `PATH` environment variable to access `pengu` from any terminal or command prompt.

### 2. Install the VS Code Extension
1. Open Visual Studio Code.
2. Go to **Extensions** (`Ctrl+Shift+X`).
3. Click the `...` menu (Views and More Actions) in the top-right corner.
4. Select **Install from VSIX...** and choose `{dist_dir.resolve() / vsix_name}`.

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
"""
    (ROOT_DIR / "README_RELEASE.md").write_text(readme_content, encoding="utf-8")
    (dist_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print(f"  [DOCS] Generated README_RELEASE.md and {dist_dir / 'README.md'}")


def main():
    parser = argparse.ArgumentParser(description="Automated Release Packager for PenguScript")
    parser.add_argument("--rebuild", action="store_true", default=True, help="Force clean rebuild of C runtime")
    parser.add_argument("--skip-tests", action="store_true", help="Skip post-packaging smoke tests")
    parser.add_argument("--dist-dir", type=str, default=str(DEFAULT_DIST_DIR), help="Target release directory")
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir).resolve()

    total_steps = 6 if args.skip_tests else 7

    print("================================================================")
    print("  PenguScript Automated Release & PyInstaller Packaging Script")
    print("================================================================")

    # Step 1: Virtual Environment
    log_step(1, total_steps, "Verifying virtual environment (.venv)...")
    py_exe = get_venv_python()
    print(f"  [PYTHON] Using {py_exe}")

    # Step 2: Dependencies
    log_step(2, total_steps, "Installing / verifying build dependencies (PyInstaller, Lark, PyYAML)...")
    ensure_dependencies(py_exe)

    # Step 3: Runtime Static Compilation
    log_step(3, total_steps, "Compiling static runtime libraries (build_runtime.py)...")
    build_runtime(py_exe, rebuild=args.rebuild)

    # Step 4: Assemble distribution folder
    log_step(4, total_steps, f"Assembling distribution assets in {dist_dir}...")
    assemble_distribution(dist_dir)

    # Step 5: Package VS Code extension
    log_step(5, total_steps, "Building and packaging VS Code Extension (.vsix)...")
    build_vscode_extension(dist_dir)

    # Step 6: Package binary with PyInstaller
    log_step(6, total_steps, "Packaging standalone CLI executable with PyInstaller...")
    package_with_pyinstaller(py_exe, dist_dir)
    generate_release_readme(dist_dir)

    # Step 7: Smoke Tests
    if not args.skip_tests:
        log_step(7, total_steps, "Running release verification & smoke tests...")
        verify_executable(dist_dir)

    exe_name = "pengu.exe" if IS_WINDOWS else "pengu"
    vsix_name = f"pengus-{get_version()}.vsix"
    print("\n================================================================")
    print(f"  SUCCESS! PenguScript release packaged at: {dist_dir}")
    print(f"  Executable: {dist_dir / exe_name}")
    print(f"  VS Code Extension: {dist_dir / vsix_name}")
    print("================================================================\n")


if __name__ == "__main__":
    main()
