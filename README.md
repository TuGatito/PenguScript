# PenguScript 🐧

[![Version](https://img.shields.io/badge/version-v0.6.0-blue.svg)](https://github.com/pengus-lang/penguscript)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-229%20passed-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

**PenguScript** is a statically typed, compiled programming language that blends the elegant, clean readability of **Python**, the scoping and memory safety principles of **V**, and the raw speed, minimal footprint, and seamless C interop of **C**.

PenguScript compiles directly to highly optimized C99/C11 source code, enabling standalone native binary compilation on Windows, Linux, and macOS with zero runtime overhead.

---

## 🚀 Quick Links

- 📖 **[Language Syntax & C Translation Cheatsheet](CHEATSHEET.md)** — Master the syntax and C mapping in 5 minutes.
- 📦 **[Build System & Project Configuration Guide](PENGU_BUILD.md)** — Cargo-style CLI and project workflow.
- 🔌 **[Visual Studio Code Extension](vscode-extension/README.md)** — Syntax highlighting, LSP intelligence, and project commands.

---

## ✨ Key Features

- **Pythonic Syntax**: Clean indentation-based blocks without semicolons `;` or curly braces `{}`.
- **V-Style Scoping Safety**:
  - `const` is **strictly global** (top-level) and translates directly to `#define`.
  - `var` (mutable) and `let` (immutable) are **strictly local** inside function bodies, preventing accidental mutable global state.
- **Zero-Cost C Transpilation**: Outputs clean, readable, dependency-free C code compiled with GCC, Clang, or MSVC.
- **Expressive Type System & Generics**:
  - `rune` (composite structs) and `enchanting` (method receiver blocks with `self->`).
  - `echo` (C-compatible tagged unions) and `omen` (algebraic data types / enums with payloads).
  - `maybe T` (null-safe optional container) and `or:` error handling blocks.
  - Zero-overhead Generics with `shard` (declaration) and `of` (specialization).
  - Collections: fixed-size `array of T`, `slice of T`, dynamic `list of T`, and hash `map of K to V` accessed with `at`.
- **Memory Safety & Deterministic Cleanup**:
  - `defer` (LIFO execution upon scope exit) and `errdefer` (execution only when an error is returned).
  - `banish` (explicit heap memory deallocation).
  - `sigil of` (`&x` address-of) and `essence of` (`*ptr` dereference).
- **Comprehensive Standard Library**: 24 built-in standard modules covering terminal I/O, regex, XML/HTML, cryptography, compression, HTTP client/server, unit testing, and math.
- **Cargo-Style Project Manager (`pengu`)**: Single command to create, build, run, clean, and launch the Language Server.
- **Language Server Protocol (LSP)**: Real-time diagnostics, documentation extracted from `#` and `##` comments, type sizing hover in bytes, and module-scoped autocomplete.

---

## 💻 Code Showcase

```pengu
import std.spark
import std.ward

# Top-level global constant
const MAX_SPEED as float is 120.0

# Composite Struct
rune Vehicle:
    model as string
    speed as float
    is_running as bool

# Method attachment (self is always passed as ref to Vehicle)
enchanting Vehicle:
    weave accelerate with delta as float into void:
        if self->is_running:
            set self->speed is self->speed + delta
            if self->speed > MAX_SPEED:
                set self->speed is MAX_SPEED

    weave status into string:
        return self->model + " traveling at " + (self->speed to string) + " km/h"

weave main into void:
    # Struct initialization with scoped properties
    var car as Vehicle is with model is "PenguMobile" and speed is 0.0 and is_running is true

    # Invoke method
    calling car.accelerate with 45.5

    # Print output using standard library
    calling spark.println with calling car.status

    # Assert condition
    calling ward.assert with car.speed > 0.0
```

### Generics with `shard` and `of`

```pengu
# Generic Struct declaration
rune Box shard T:
    item as T
    id as int

# Generic Function declaration
weave create_box shard T with val as T and id as int into Box of T:
    return with item is val and id is id

weave demo_generics into void:
    # Monomorphized zero-overhead specialization
    var int_box as Box of int is calling create_box of int with 42 and 1
    var str_box as Box of string is calling create_box of string with "Pengu" and 2
```

---

## 🛠️ The `pengu` CLI & Project Manager

PenguScript includes an integrated build manager (`pengu_project.py` or standalone `pengu` binary):

```bash
# 1. Initialize a new application
pengu init my_game --type exe --links pengu_runtime

# 2. Build the project (default debug profile)
pengu build

# 3. Build optimized release binary
pengu build --profile release

# 4. Build and run immediately
pengu run

# 5. Clean build directory
pengu clean

# 6. Start the Language Server Protocol (LSP)
pengu lsp --stdio
```

### Supported Target Types

| Target Type | Command                           | Description                       | Output Artifact                        |
| ----------- | --------------------------------- | --------------------------------- | -------------------------------------- |
| `exe`       | `pengu init app --type exe`       | Standalone executable application | `build/app.exe` or `build/app`         |
| `static`    | `pengu init lib --type static`    | Static library archive            | `build/lib<name>.a`                    |
| `shared`    | `pengu init plugin --type shared` | Dynamic / Shared library          | `build/<name>.dll` or `.so` / `.dylib` |
| `obj`       | `pengu init obj --type obj`       | Compiled C object file            | `build/<name>.o`                       |
| `c`         | `pengu init bundle --type c`      | Pure bundled C code               | `build/bundle.c`                       |

### Project Configuration (`pengu.toml` / `pengu.yaml`)

```toml
[project]
name = "my_game"
version = "0.1.0"
entry = "main.pengu"
output = "exe"
output_name = "my_game"

[build]
build_dir = "build"
includes = ["raylib.h"]
links = ["raylib", "m", "pthread", "pengu_runtime"]
cflags = ["-Wall", "-std=c11"]
defines = ["PLATFORM_DESKTOP"]
cc = "gcc"

[profiles.debug]
cflags = ["-g", "-O0", "-Wall"]
defines = ["DEBUG"]

[profiles.release]
cflags = ["-O3", "-DNDEBUG"]
defines = ["NDEBUG"]
```

---

## 📦 Standard Library Overview

PenguScript comes equipped with **24 high-performance standard library modules**:

| Module | Import | Description |
|---|---|---|
| **spark** | `import std.spark` | Core runtime and terminal I/O (`print`, `println`, `read_line`, ANSI styling, basic conversions, panic). |
| **scrolls** | `import std.scrolls` | Comprehensive string manipulation (`split`, `join`, `replace`, `trim`, `starts_with`, `ends_with`, `contains`, case conversions). |
| **oracle** | `import std.oracle` | Null-safe optional and functional error types (`MaybeInt`, `MaybeFloat`, `MaybeString`, `ResultInt`, `ResultString`, `is_present`, `is_ok`). |
| **tally** | `import std.tally` | Dynamic array and list manipulation utilities, element indexing, sorting, and transformations. |
| **atlas** | `import std.atlas` | Hash map key-value store structures and mapping utilities. |
| **coven** | `import std.coven` | Dynamic unique set collections (`insert`, `contains`, `remove`, union, intersection, difference). |
| **compass** | `import std.compass` | Cross-platform file path manipulation (`join`, `basename`, `dirname`, `ext`, normalization, absolute paths). |
| **archivum** | `import std.archivum` | Complete file system operations: reading, writing, appending, copying, moving, deleting, directory listing, and metadata. |
| **arithmancy** | `import std.arithmancy` | Advanced mathematical functions: trigonometry (`sin`, `cos`, `tan`), powers, roots, logarithms, rounding, and clamping. |
| **chronicle** | `import std.chronicle` | High-precision time, timestamps, date/time formatting, monotonic clocks, sleep delays, and stopwatch benchmarking. |
| **lot** | `import std.lot` | Pseudorandom number generation, seeds, range-bounded integers/floats, and collection shuffling. |
| **rites** | `import std.rites` | Operating system interface: process execution, environment variables, command running, and exit codes. |
| **invoke** | `import std.invoke` | Command-line argument parsing for CLI applications (flags, options, positional arguments, and automated `--help`). |
| **ledger** | `import std.ledger` | High-performance CSV and TSV parsing, delimiter detection, and tabular row serialization. |
| **cipher** | `import std.cipher` | JSON serialization/deserialization and Base64 encoding/decoding. |
| **parchment** | `import std.parchment` | XML and HTML DOM parsing, node traversal, attribute manipulation, and serialization (powered by `libxml2`). |
| **regulus** | `import std.regulus` | High-performance regular expression compilation, matching, search, replace, and capture groups (powered by `PCRE2 10.47`). |
| **seal** | `import std.seal` | Cryptographic hashing (`MD5`, `SHA1`, `SHA256`, `SHA512`, `CRC32`) and gzip/zlib compression (`deflate`/`inflate`). |
| **precis** | `import std.precis` | Full networking stack: HTTP client (`GET`, `POST`, `PUT`, `DELETE`), embedded HTTP micro-server, TCP sockets, and URL encoding. |
| **filum** | `import std.filum` | Concurrency primitives: thread spawning, communication channels, mutexes, wait groups, and atomics. |
| **loom** | `import std.loom` | Functional collection utilities and iterators (`map`, `filter`, `reduce`, `zip`, chunking, flattening). |
| **ward** | `import std.ward` | Runtime assertions and invariant validations (`assert`, `assert_eq`, `assert_ne`, `assert_present`, `assert_ok`, `panic`). |
| **trial** | `import std.trial` | Automated unit testing framework (suites, test cases, before/after lifecycle hooks, and colored reporting). |
| **whisper** | `import std.whisper` | Structured logging framework with severity levels (`trace`, `debug`, `info`, `warn`, `error`, `fatal`). |

---

## 🧩 Visual Studio Code Extension

The official **PenguScript VS Code Extension** (`pengus-0.6.0.vsix`) provides a first-class developer experience:

- **Syntax Highlighting**: Complete formal TextMate grammar.
- **Live Diagnostics**: Rust-style compile-time errors with `help:`, `note:`, and line spans.
- **Contextual Documentation**: Automatically parses and displays markdown docstrings from `#` and `## ... ##` comments in hover tooltips.
- **Advanced Type & Sizing Hover**: Real-time memory footprint calculation in bytes (e.g. `rune Player (21 bytes)`).
- **Module-Scoped Autocompletion**: Autocompletes exported members when typing `spark.`, `ledger.`, etc.
- **Go-To-Definition (F12)**: Jump across local declarations and standard library `.pengu` module source files.
- **Project Commands**: Build, Run, Clean, and Init directly from the Command Palette (`Ctrl+Shift+P`).

### Installation

1. Download `pengus-0.6.0.vsix` from the [Releases](https://github.com/pengus-lang/penguscript/releases) page or build it locally.
2. In VS Code, go to **Extensions** (`Ctrl+Shift+X`) -> click **`...`** in the top-right -> **Install from VSIX...**.
3. Select `pengus-0.6.0.vsix`.

---

## 🔨 Building from Source & Release Packaging

### Prerequisites

- Python 3.10+
- A C compiler: `gcc`, `clang`, or `msvc` in your `PATH`
- Node.js 18+ and `npm` (for the VS Code extension)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/pengus-lang/penguscript.git
cd penguscript

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Test Suite

```bash
pytest tests/
```

### 3. Build Standalone Release & Package Everything

The automated release script downloads external C libraries (`extern_manifest.py`), compiles the static C runtime (`libpengu_runtime.a`), packages the standalone executable with PyInstaller (`pengu` / `pengu.exe`), and builds the VS Code extension (`pengus-0.6.0.vsix`):

```bash
python make_release.py
```

The resulting distribution is bundled in `pengucc_build/`:

```
pengucc_build/
├── pengu (.exe)              # Standalone PenguScript CLI & LSP
├── pengus-0.6.0.vsix         # VS Code Extension
├── std/                      # Complete Standard Library (25 modules)
└── runtime/                  # C Runtime headers and static library (libpengu_runtime.a)
```

---

## ❤️ Third-Party Acknowledgments & Credits

PenguScript's standard library and tooling stand on the shoulders of giants. We gratefully acknowledge the following open-source projects:

- **[PCRE2](https://www.pcre.org/)** (v10.47) — High-performance Perl-compatible regular expressions for `std.regulus`.
- **[libxml2](https://gitlab.gnome.org/GNOME/libxml2)** (v2.9.0) — Robust XML & HTML parsing engine for `std.parchment`.
- **[zlib](https://zlib.net/)** (v1.3.2) — Industry-standard compression library for `std.seal` and `std.parchment`.
- **[mbedTLS](https://github.com/Mbed-TLS/mbedtls)** (v4.2.0) — Cryptographic hashing algorithms (MD5, SHA1, SHA256, SHA512) for `std.seal`.
- **[libcurl](https://curl.se/libcurl/)** (v8.21.0) — Enterprise HTTP client networking for `std.precis`.
- **[libmicrohttpd](https://www.gnu.org/software/libmicrohttpd/)** (v1.0.1) — Lightweight embedded HTTP server for `std.precis`.
- **[Lark](https://github.com/lark-parser/lark)** — Powerful, elegant parsing library for Python.
- **[pygls](https://github.com/openlawlibrary/pygls)** — Pythonic Language Server Protocol SDK.
- **[PyInstaller](https://pyinstaller.org/)** — Standalone native executable packager.

---

## 📜 License

PenguScript is distributed under the terms of the **[MIT License](LICENSE)**.

```
Copyright (c) 2026 PenguScript Contributors
```
