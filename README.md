# PenguScript

![Version](https://img.shields.io/badge/version-0.10.0-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11+-yellow) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**PenguScript** is a statically typed, compiled programming language that combines the clean, indentation-based readability of **Python** (with a nod to MoonScript), the strict scoping and memory-discipline principles of **V**, and the raw speed, tiny footprint, and seamless C interoperability of **C**.

PenguScript compiles directly to clean, human-readable **C99/C11** source code, which is then built into standalone native binaries with `gcc`/`clang` on Windows, Linux, and macOS — no interpreter, no VM, and no runtime overhead beyond the generated C.

> **Status:** active development. CI builds the C runtime, runs `pytest tests/`, and packages a standalone release (compiler + VS Code extension) on **Windows, Linux and macOS** — see `.github/workflows/ci.yml`; tagged releases are published by `.github/workflows/release.yml`.

> [!WARNING]
>
> ### Beta — usable, not yet production-ready
>
> PenguScript today is a **beta**: the language core is stable enough to write real
> programs and to drive C libraries, and the compiler has a green test suite, but
> several language and tooling gaps are still open. The full assessment — with the
> evidence behind every claim, the prioritised roadmap, and the porting
> conventions that work today — is in
> [`PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md).
>
> **What you can do today (all verified against the real toolchain)**
>
> - Compile to readable C99 and link **arbitrary C libraries**: project mode
>   accepts `include_dirs`, `lib_dirs`, `links` and `ldflags` in `pengu.yaml`,
>   plus a `c/` directory for your own glue code.
> - Pass/receive **structs by value** in both directions, use C **`const`** via
>   `frozen`, opaque handles, out-parameters (`sigil of`), `omen` enums,
>   `#define`d constants, **callbacks** (named weaves, lambdas, `void*` user
>   data, `qsort`-style function pointers) and compile-time `when`.
> - Write whole programs with `maybe`/`result`, `defer`/`errdefer`, `shard`
>   generics, `static var` function-local state, and the `std/` library
>   (files, processes, threads/channels, regex, HTTP, SQLite, JSON/CSV/TOML/YAML,
>   hashing/compression, logging, unit tests).
> - Build and run the **core of the raylib corpus**: window, input, 2D shapes,
>   text (`TextFormat`), textures, colours, timing, 3D vector/matrix math
>   via `std.raymath`, and OpenGL immediate-mode rendering via `std.rlgl`. Six raylib examples are ported and verified in `scratch/port/`.
> - **Multidimensional 2D arrays** (`array of array of T with size M with size N`),
>   **memory deallocation** (`banish` on `string`, `list`, `map`, and `ref to T`),
>   **scope-owned locals** (automatic deterministic cleanup on block exit with `borrowed` opt-out),
>   **module state idioms** (`static var` accessors and context structs),
>   **C variadic declarations** (`declare ... with fmt as ref to frozen char, ... into int`),
>   **struct literals in array literals**, **pointer indexing** (`p at i`) and generic
>   slice bridging (`ffi.slice_from_ptr shard T`).
>
> **What is not there yet (do not plan a production project around these)**
>
> - **Pointer arithmetic** (`p + 1`): use indexing `p at i` or create a slice with `std.ffi.slice_from_ptr`.
> - **A bare `printf`/`TextFormat` reached only through `include`** (no `declare` in scope) still
>   type-checks and then fails in C; declare it (`declare printf with fmt as ref to frozen char, ... into int`)
>   — the compiler reports the failure at your `.pengu` line.
> - Tooling limits: `pengu bind` handles real headers (`--define`, `--cpp-flags`,
>   `--system-includes`, `--preprocessed`), but a few vendored headers
>   (`miniaudio`, `xxhash`, `tomlc17`, `yaml`) still need flags or are hand-maintained,
>   and the CLI has no `-I`/`-L`/`-l` flags — use `pengu.yaml`.
>
> P0 (operational hygiene), P1 (the C shapes the raylib corpus needed) and P2
> (breadth and safety: 2-D arrays, `rlgl`, explicit memory release, strict
> pointer typing, real-header bindings) are complete; what remains is P3
> ergonomics. Treat PenguScript as a capable beta — good for internal tools,
> prototypes and C-library work — until P3 lands.

---

## Feature Highlights

- **Pythonic, indentation-based syntax** — no semicolons or braces; blocks are whitespace-delimited.
- **V-style scoping safety** — `const` is strictly global (top-level) and becomes a C `#define`; `var` (mutable) and `let` (immutable) are strictly local to function bodies, so accidental mutable global state is impossible by construction.
- **Expressive type system** — fixed-width integers (`u8`…`u64`, `i8`…`i64`), `f32`/`f64`, `char`, `byte`, `string`, `bool`; arrays, slices, dynamic lists, and hash maps.
- **User types** — `rune` (structs) with `enchanting` method blocks (`self->`), `echo` (C-compatible tagged unions), `omen` (enums / algebraic data types with payloads), and `maybe T` / `or:` optional-and-error handling.
- **Zero-overhead generics** — `shard` declarations specialized with `of`; each instantiation is monomorphized to plain C.
- **Deterministic cleanup** — `defer` (LIFO on scope exit), `errdefer` (on error return), scope-owned locals (automatic `banish` at block exit unless marked `borrowed`), and explicit heap release with `banish`.
- **First-class C FFI** — `include`/`link`/`declare`, opaque types (`alias … as opaque`), `sigil of` (address-of) / `essence of` (deref), zero-copy `bytes of <string>` borrows, and `weave`s that decay to C function pointers (callable from C and usable as coroutine bodies).
- **`pengu bind`** — auto-generates a `.d.pengu` declaration file from any C header (structs → `rune`, unions → `echo`, enums → `omen`, functions → `declare`, callbacks → `alias … as ref to weave`, doc comments preserved). It blanks GNU compiler extensions before parsing, auto-imports the bindings of included headers, and takes `--define/-D`, `--cpp-flags`, `--system-includes`, `--include-paths` and `--preprocessed FILE.i` for headers that need a specific preprocessor setup, with diagnostics that name the offending construct and the flag to try.
- **Bundled C libraries** — SQLite, Raylib, WebUI, libuv, PCRE2, libxml2, zlib, Mbed TLS, cURL, libmicrohttpd, YAML, XLSX (libzip + libexpat + xlsxio), and TOML are compiled once into static archives and linked automatically.
- **Rich standard library** — `std/` ships **52 modules**: 27 implemented in pure PenguScript (I/O, strings, files, math, time, regex bindings, HTTP client/server, JSON, CSV, concurrency, logging, unit testing, …) plus 25 curated C declaration bindings (`*.d.pengu`) for the bundled libraries (including **raylib**, **raymath**, and **rlgl**).
- **Language Server (LSP)** — diagnostics with `help:`/`note:`/line spans, documentation from `#` and `##` doc comments, type & memory-size hovers, module-scoped autocompletion, go-to-definition, formatting, and code actions.
- **Cargo-style project manager** — the `pengu` CLI creates, builds, runs, tests, checks, cleans, and formats projects, runs standalone scripts, and manages external dependencies.
- **Compile-time features** — `when` conditionals, `defined(...)`, `-D name=value` defines, `static var`, and `when main:` guards so a file can act as both an importable module and a runnable script.

---

## Quick Start

### Requirements

- **Python 3.11+** (3.10 also works — `requirements.txt` installs the `tomli` backport automatically there).
- A **C compiler** (`gcc` or `clang`) and static archiver (`ar`/`llvm-ar`) on your `PATH` — on Windows use MinGW-w64 `gcc`.
- **CMake** — required only for the static builds of libuv, libzip, and libexpat; every other bundled library compiles with plain `gcc`/`clang`.
- **Node.js 18+ and npm** — only needed to develop or package the VS Code extension.

### Setup

```bash
git clone https://github.com/pengus-lang/penguscript.git
cd penguscript

# Create a virtual environment and install Python dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build the C runtime and bundled static libraries into build/lib
python build_runtime.py

# Run the test-suite
pytest tests/
```

### Hello, world

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
```

Save it as `hello.pengu` and run it as a standalone script:

```bash
# From a source checkout:
python pengu_project.py run hello.pengu

# With the packaged standalone CLI (see "Building the runtime from source"):
pengu run hello.pengu
```

> The CLI is `pengu_project.py` in a source checkout and the `pengu`/`pengu.exe` executable in a release build. The rest of this document uses `pengu` for brevity.

---

## Usage: the `pengu` CLI

| Command    | Description                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------- |
| `init`     | Create a new project template (`--type exe\|static\|shared\|obj\|c`, `--links`, `--cc`).          |
| `add`      | Add an external dependency or binding (git URL or local folder, optional build script).           |
| `build`    | Compile the project per its config (`--profile release`, `--cc`, `-D`, `--test`, `--verbose`).    |
| `run`      | Build and execute the project target, or run a standalone `.pengu` file directly as a script.     |
| `test`     | Compile in `--test` mode and run the project's integrated unit tests (`--json`, `--watch`).        |
| `check`    | Parse and type-check every module without generating code — CI friendly.                          |
| `update`   | Pull and rebuild each configured dependency.                                                      |
| `bind`     | Generate a `.d.pengu` declaration file from a C header (`--prefix`, `--links`, `--ignore`, …).    |
| `fmt`      | Format `.pengu` files or directories (`--check` only reports; `--tabs`/`--indent`).               |
| `clean`    | Remove the build directory and generated artifacts.                                               |
| `lsp`      | Launch the Language Server (stdio by default; `--tcp --host … --port …`).                        |
| `doc`      | Generate a Markdown API reference from `##` doc comments (`-o` sets the output directory).         |

```bash
pengu init my_app --type exe
cd my_app
pengu build                 # debug profile (bounds-checking active)
pengu build --profile release
pengu run                   # build + run
pengu check                 # type-check everything (CI)
pengu test                  # run integrated unit tests
pengu test --json           # emit JSON Lines events for CI
pengu test --watch          # recompile and re-run on source modifications
pengu fmt src/ tests/       # format sources
pengu clean
pengu lsp                   # stdio language server
pengu doc -o docs/          # generate module reference
```

Projects are configured with `pengu.toml` (or `pengu.yaml`) — entry point, output type/name, includes, links, per-profile `cflags`/`defines`, and compiler selection. Under the `debug` profile (default), automatic bounds checking (`pengu_assert_bounds`) and stack trace frames are active for index access; in `release`, bounds checking carries zero runtime overhead. See [PENGU_BUILD.md](PENGU_BUILD.md) for the full guide.

### VS Code extension

The official extension lives in [`vscode-extension/`](vscode-extension/README.md): TextMate syntax highlighting, LSP-powered diagnostics and hovers (type + byte-size), module-scoped autocompletion, go-to-definition, and Build/Run/Clean/Init commands in the Command Palette.

Install it from the packaged `pengus-<version>.vsix` produced by `python make_release.py`, or build it yourself:

```bash
cd vscode-extension
npm install
npm run package             # runs @vscode/vsce package -> pengus-<version>.vsix
```

Then open VS Code → **Extensions** (`Ctrl+Shift+X`) → **`…`** → **Install from VSIX…** and pick the `.vsix` file. See [vscode-extension/README.md](vscode-extension/README.md) for settings (`pengus.executablePath`, `pengus.defaultProfile`) and development instructions.

---

## Language Overview

A fast tour — the authoritative syntax and C-translation reference is **[CHEATSHEET.md](CHEATSHEET.md)**.

```pengu
import std.spark

const MAX_SPEED as float is 120.0          # global constant -> #define

rune Vehicle:                              # struct
    model as string
    speed as float

enchanting Vehicle:                        # method block; self is a ref
    weave accelerate with delta as float into void:
        if self->speed + delta <= MAX_SPEED:
            set self->speed is self->speed + delta

    weave describe into string:
        return self->model + " at " + (self->speed to string) + " km/h"

weave main into int:
    var car as Vehicle is with model is "Pengu", speed is 0.0
    calling car.accelerate with 45.5
    calling spark.println with calling car.describe
    return 0
```

- **Declarations** — `var` (mutable) / `let` (immutable) locals, top-level `const`, and `weave name with a as T, b as T into R` functions. Values are assigned with `is` and mutated with `set`.
- **Types & collections** — `rune` structs, `omen` (enums with payloads) and `echo` (C unions), `maybe T`/`or:` error handling, fixed-size `array of T`, `slice of T`, dynamic `list of T`, and hash `map of K to V` via `at`. Pattern matching uses `judge … when …`.
- **Generics** — `rune Box shard T:` declarations, specialized with `Box of int`; calls like `calling make_box of int with 42` monomorphize to plain C.
- **Memory** — `defer`/`errdefer` run at scope exit (or on error), `banish` frees heap memory, and `sigil of x` / `essence of p` give explicit address-of and dereference.
- **Compile-time** — `when os == "windows":` / `when main:` blocks, `defined(...)`, and `-D name=value` defines; a `.pengu` file run as a script always compiles with `main` = `true` (imported modules get `false`), enabling script-only code:

  ```pengu
  when main:
      weave main into int:
          calling spark.println with "Running as a script!"
          return 0
  ```

- **C FFI** — declaration files (`*.d.pengu`) glue C straight into PenguScript:

  ```pengu
  # std/xxhash.d.pengu (excerpt)
  include "xxhash.h"
  alias XXH32_state_t as opaque
  rune XXH128_hash_t:
      low64 as u64
      high64 as u64
  declare XXH64 with input as ref to char, length as size_t, seed as u64 into u64
  ```

  …then, from your code:

  ```pengu
  import std.xxhash
  var h as u64 is calling xxhash.XXH64 with "PenguScript", 11, 0
  ```

  Real-world C headers can be turned into such bindings automatically with `pengu bind`.

### Standard library

`std/` contains 52 modules — 27 written in pure PenguScript and 25 curated C bindings (`.d.pengu`). Highlights: **spark** (core I/O & runtime), **scrolls** (strings), **archivum** (files), **compass** (paths), **chronicle** (time), **lot** (randomness), **arithmancy** (math), **oracle** (`Maybe`/`Result`), **atlas**/**coven**/**tally**/**loom** (maps, sets, lists, iterators), **ledger** (CSV), **cipher** (JSON + Base64), **parchment** (XML/HTML via libxml2), **regulus** (regex via PCRE2), **seal** (hashing + compression via Mbed TLS/zlib), **precis** (HTTP client/server via cURL/libmicrohttpd), **filum** (threads & channels), **ward** (assertions), **trial** (unit testing), **whisper** (logging), and **invoke** (CLI argument parsing) — plus bindings such as **sqlite3**, **raylib**, **raymath**, **rlgl**, **webui**, **miniaudio**, **minicoro**, **xxhash** (with the **celeris** wrapper), **uuid**, **imago/scriptor/typis/pactum/datastructura/perlinum** (STB), **nanosvg/nanosvgrast**, **fenestra** (tinyfiledialogs), **rlights**, **yaml**, **tomlum** (TOML validation), and **xlsxio/xlsx** (`.xlsx` writing).

---

## Project Layout

```text
PenguScript/
├── pengu_parser/           # Compiler pipeline (Python):
│                           #   Lark grammar + parser, symbol tables, type checker & inference,
│                           #   comptime (`when`, `-D`, `defined`), codegen to C99/C11,
│                           #   error reporting (help:/note:), and pengu_runtime.c (C runtime impl)
├── pengu_lsp/              # Language Server (pygls): diagnostics, hover/doc, completions,
│                           #   go-to-definition, code actions, formatting
├── pengu_project.py        # Cargo-style CLI & build manager (`pengu init/build/run/test/…`)
├── pengu_bind.py           # `pengu bind`: C header -> .d.pengu binding generator (pycparser)
├── pengu_doc.py            # `pengu doc`: Markdown reference generator from `##` comments
├── pengu_runtime.h         # Public API of the C runtime used by generated code
├── build_runtime.py        # Compiles the C runtime + bundled C libraries into build/lib
├── extern_manifest.py      # Manifest + downloader for external C library sources (-> extern/)
├── make_release.py         # One-shot release packager -> pengucc_build/ (see below)
├── std/                    # Standard library: 26 pure-PenguScript modules +
│                           #   22 C declaration bindings (*.d.pengu)
├── std_c/                  # C implementation units, wrappers_*.c shims, and vendored
│                           #   single-header libraries (STB, nanosvg, xxhash, uuid, …)
├── c_bind_stubs/           # Minimal stub C headers used when `pengu bind` preprocesses
├── extern/                 # Downloaded third-party C library sources (gitignored)
├── build/                  # Generated output (gitignored):
│                           #   build/lib/*.a static archives + build/include/ headers
├── tests/                  # Python test-suite (pytest tests/): compiler, LSP, CLI,
│                           #   bindings, std library & bundled C libraries
├── tests/std_programs/     # One PenguScript exercise program per std module
│                           #   (compiled & run by tests/test_stdlib.py)
├── vscode-extension/       # VS Code extension (grammar, LSP client, project commands)
├── CHANGELOG.md            # Version history & feature log
├── CHEATSHEET.md           # Full language syntax & C-translation reference
├── PENGU_BUILD.md          # Build system & project configuration guide
└── README_RELEASE.md       # Standalone release package (pengucc_build/) documentation
```

---

## Building the Runtime from Source

`build_runtime.py` produces the static archives that `pengu` links into every binary. It runs in two stages:

1. **Download & extract** — `extern_manifest.py` holds the manifest of every external C library (name → URL → expected directory) and downloads/extracts the ones missing into `extern/` (gitignored). It is invoked automatically at the start of `build_runtime.py` and can also be run standalone: `python extern_manifest.py`.
2. **Compile** — `build_runtime.py` then compiles each library with `gcc`/`clang` + `ar` (CMake for libuv, libzip, and libexpat) into `build/lib/*.a`, staging headers into `build/include/`:

```bash
python build_runtime.py            # download externs if needed, build everything
python build_runtime.py --rebuild  # force a clean rebuild
```

The builders (`build_zlib`, `build_pcre2`, `build_libxml2`, `build_mbedtls`, `build_curl`, `build_microhttpd`, `build_sqlite3`, `build_libzip`, `build_libexpat`, `build_xlsxio`, `build_libyaml`, `build_libcyaml`, `build_libuv`, `build_tomlc17`, `build_webui`, `build_raylib`, `build_pengu_stb`, `build_pengu_runtime`) produce, among others, `libz.a`, `libpcre2-8.a`, `libxml2.a`, `libmbedcrypto.a`, `libcurl.a`, `libmicrohttpd.a`, `libsqlite3.a`, `libraylib.a`, `libwebui.a`, `libuv.a`, `libyaml.a`, `libcyaml.a`, `libzip.a`, `libexpat.a`, `libxlsxio_read.a`/`libxlsxio_write.a`, `libtomlc17.a`, `libpengu_stb.a` (the vendored single-header implementations, see below), and `libpengu_runtime.a` (the runtime itself). Any archive present in `build/lib` is linked automatically into projects that link `pengu_runtime`. On POSIX hosts the runtime may use the system libxml2/libcurl/libmicrohttpd instead of the static builds.

> The first run downloads and extracts the external library sources, so it needs internet access; later runs are incremental and skip anything already built.

**Releases** — `make_release.py` automates the whole distribution: it verifies/installs the Python deps, rebuilds the runtime (`--rebuild`), runs smoke tests, packages the CLI + LSP into a standalone executable with PyInstaller (`pengu` / `pengu.exe`), and builds the VS Code extension (`pengus-<version>.vsix`). Everything lands in `pengucc_build/`:

```bash
python make_release.py
```

```text
pengucc_build/
├── pengu (.exe)          # Standalone PenguScript CLI & LSP server
├── pengus-<version>.vsix # VS Code extension
├── std/                  # Complete standard library modules
└── runtime/              # C runtime headers + static libraries (build/lib)
```

See [README_RELEASE.md](README_RELEASE.md) for the distribution's own documentation.

---

## Documentation

| Document                                              | What it covers                                                |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| [CHEATSHEET.md](CHEATSHEET.md)                        | Full language syntax, keywords, and C-translation reference   |
| [PENGU_BUILD.md](PENGU_BUILD.md)                      | `pengu` CLI, project config, and the build system             |
| [CHANGELOG.md](CHANGELOG.md)                          | Version history and per-release feature log                   |
| [README_RELEASE.md](README_RELEASE.md)                | The standalone `pengucc_build/` release package               |
| [vscode-extension/README.md](vscode-extension/README.md) | VS Code extension: features, settings, installation        |

---

## Third-Party Acknowledgements & Credits

PenguScript's toolchain, C runtime, and standard library stand on the shoulders of many excellent open-source projects. We gratefully acknowledge and thank their authors. License names below are as published by each upstream project; vendored code keeps its original copyright/license notices (see the header comments in `std_c/`).

### Python (toolchain) dependencies

Declared in [requirements.txt](requirements.txt):

| Dependency                                                                    | Used for                                                    | License                        |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------ |
| [Lark](https://github.com/lark-parser/lark)                                   | Language grammar & parsing (`pengu_parser`)                 | MIT                            |
| [PyYAML](https://pyyaml.org/)                                                 | `pengu.yaml` project configuration parsing                  | MIT                            |
| [pygls](https://github.com/openlawlibrary/pygls)                              | Language Server Protocol framework (`pengu_lsp`)            | Apache-2.0                     |
| [lsprotocol](https://github.com/microsoft/lsprotocol)                         | LSP protocol types (with pygls)                             | MIT                            |
| [pycparser](https://github.com/eliben/pycparser)                              | C-header parsing in `pengu bind`                            | BSD-3-Clause                   |
| [PyInstaller](https://pyinstaller.org/)                                       | Packaging the standalone `pengu` executable (release step)  | GPL-2.0-or-later (with bootloader exception) |
| [pytest](https://pytest.org/)                                                 | Test runner (`pytest tests/`)                               | MIT                            |
| [tomli](https://github.com/hukkin/tomli)                                      | `tomllib` backport for `pengu.toml` on Python < 3.11        | MIT                            |

### C runtime & standard library

#### Compiled external libraries (built into `build/lib` by `build_runtime.py`)

| Library                                            | Version   | Used by                                     | License                |
| -------------------------------------------------- | --------- | ------------------------------------------- | ---------------------- |
| [zlib](https://zlib.net/)                          | 1.3.2     | `std.seal` (deflate/inflate)                 | zlib                   |
| [PCRE2](https://www.pcre.org/)                     | 10.47     | `std.regulus` (regex)                       | BSD-3-Clause           |
| [libxml2](https://gitlab.gnome.org/GNOME/libxml2)  | 2.9.0     | `std.parchment` (XML/HTML DOM)              | MIT                    |
| [Mbed TLS](https://github.com/Mbed-TLS/mbedtls)    | 4.2.0     | `std.seal` (MD5/SHA1/SHA256/SHA512, CRC)    | Apache-2.0             |
| [cURL](https://curl.se/libcurl/)                   | 8.21.0    | `std.precis` (HTTP client)                  | MIT-like ("curl" license) |
| [GNU libmicrohttpd](https://www.gnu.org/software/libmicrohttpd/) | 1.0.1 | `std.precis` (embedded HTTP server)       | LGPL-2.1-or-later      |
| [SQLite](https://www.sqlite.org/)                  | 3.53.4    | `std.sqlite3`                               | Public domain          |
| [raylib](https://www.raylib.com/)                  | 6.0       | `std.raylib` (also compiles its amalgamated GLFW driver `rglfw.c`, zlib) | zlib |
| [WebUI](https://github.com/webui-dev/webui)        | 2.5.0-beta.3 | `std.webui` (prebuilt static release)     | MIT                    |
| [libuv](https://libuv.org/)                        | 1.52.1    | C-level dependency (no binding yet)         | MIT                    |
| [libyaml](https://github.com/yaml/libyaml)         | 0.2.5     | `std.yaml` (version query; parsing stays C-level) | MIT            |
| [libcyaml](https://github.com/tlsa/libcyaml)       | 1.4.2     | YAML schema layer on libyaml (C-level)      | ISC                    |
| [tomlc17](https://github.com/cktan/tomlc17)        | R260821   | `std.tomlum` (TOML validity shim)           | MIT                    |
| [libzip](https://libzip.org/)                      | 1.11.3    | Zip support (used by xlsxio)                | BSD-3-Clause           |
| [libexpat](https://libexpat.github.io/)            | 2.6.4     | XML parser (used by xlsxio)                 | MIT                    |
| [xlsxio](https://github.com/brechtsanders/xlsxio)  | 0.2.36    | `std.xlsxio` + the pure-Pengu `std.xlsx` writer | BSD-2-Clause       |

#### Vendored single-header libraries (`std_c/`)

Each file keeps its upstream name, version, and license notice in its own comment block. Upstream names differ from the Latinized filenames used to dodge C namespace collisions:

| `std_c/` file                | Upstream library                             | License (from the file header)                                   | PenguScript binding / notes |
| ---------------------------- | -------------------------------------------- | --------------------------------------------------------------- | --------------------------- |
| `imago.h`                    | stb_image v2.30                              | Public domain (Sean Barrett)                                     | `std.imago` (image loading) |
| `scriptor.h`                 | stb_image_write v1.16                        | Public domain                                                    | `std.scriptor` (image writing) |
| `typis.h`                    | stb_truetype v1.26                           | Public domain                                                    | `std.typis` (fonts) |
| `pactum.h`                   | stb_rect_pack v1.01                          | Public domain                                                    | `std.pactum` (rect packing) |
| `datastructura.h`            | stb_ds v0.67                                 | Public domain                                                    | `std.datastructura` (hash maps / dynamic arrays) |
| `perlinum.h`                 | stb_perlin v0.5                              | MIT or public domain (Unlicense) — dual                          | `std.perlinum` (noise) |
| `stb_image_resize2.h`        | stb_image_resize2 v2.18                      | Public domain                                                    | `std.stb_image_resize2` |
| `stb_herringbone_wang_tile.h`| stb_herringbone_wang_tile v0.7               | Public domain / permissive dual grant                            | `std.stb_herringbone_wang_tile` |
| `nanosvg.h` / `nanosvgrast.h`| [nanosvg](https://github.com/memononen/nanosvg) | zlib (© 2013–14 Mikko Mononen)                                | `std.nanosvg` / `std.nanosvgrast` (SVG parse + rasterize) |
| `xxhash.h`                   | [xxHash](https://github.com/Cyan4973/xxHash) | BSD-2-Clause (© 2012–2023 Yann Collet)                           | `std.xxhash` + the `std.celeris` wrapper |
| `uuid.h`                     | [uuid_h](https://github.com/wc-duck/uuid_h)  | zlib-style (© 2016– Fredrik Kihlander; MinGW-patched in this repo) | `std.uuid` |
| `minicoro.h`                 | [minicoro](https://github.com/edubart/minicoro) v0.2.0 | Public domain (Unlicense) or MIT-0 — dual (© 2021–23 Eduardo Bart) | `std.minicoro` (coroutines) |
| `miniaudio.h`                | [miniaudio](https://github.com/mackron/miniaudio) v0.11.25 | Public domain or MIT-0 — dual (David Reid)              | `std.miniaudio` (small subset; header not compiled into the runtime) |
| `raygui.h`                   | [raygui](https://github.com/raysan5/raygui) v5.0 | zlib/libpng (© 2014–2026 Ramon Santamaria)                   | compiled for use with `std.raylib` |
| `rlights.h`                  | raylib-6 "RLG" lighting framework            | No license header embedded (lineage: raylib examples, zlib; cf. [bigfoot71/rlights](https://github.com/bigfoot71/rlights)) | `std.rlights` (subset; not compiled into the runtime) |
| `tinyfiledialogs.h` / `.c`   | [tinyfiledialogs](http://tinyfiledialogs.sourceforge.net) v3.21.3 | zlib (© 2014–2025 Guillaume Vareille)         | `std.fenestra` (file/message dialogs) |
| `tinyfd_moredialogs.h` / `.c`| tinyfiledialogs "more dialogs" v3.9.0        | zlib (© 2014–2023 Guillaume Vareille)                           | part of `std.fenestra` |
| `linmath.h`                  | [linmath.h](https://github.com/datenwolf/linmath.h) | No license header embedded upstream (vector/matrix/quaternion math) | vendored (experimental `scratch/` binding) |
| `fifo_declare.h`             | FIFO / circular-buffer macro header          | LGPL-2.1-or-later (© 2003–2012 Michel Pollet)                   | vendored in `std_c/`; not referenced by the runtime or std yet |

The STB headers above are the well-known single-file libraries by Sean Barrett & contributors ([nothings/stb](https://github.com/nothings/stb)); several also carry the upstream dual "public domain or MIT-0" grant. The `wrappers_*.c` files, `pengu_tomlc17.h`, and the `.pengu` bindings in `std/` are PenguScript's own code.

---

## License

PenguScript is released under the **[MIT License](LICENSE)** — © 2026 TuGatito. Third-party components retain their own licenses as noted above; see each vendored header and the upstream projects for details.
