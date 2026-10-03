# PenguScript

![Version](https://img.shields.io/badge/version-0.16.0-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11+-yellow) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**🌍 Languages / Idiomas:** [🇬🇧 English](#-english) · [🇪🇸 Español](#-español)

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
>   **struct literals in array literals**, **pointer indexing** (`p at i`), generic
>   slice bridging (`ffi.slice_from_ptr shard T`), and **embedded project assets** (`arca`).
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

## 🇬🇧 English

### Feature Highlights

- **Pythonic, indentation-based syntax** — no semicolons or braces; blocks are whitespace-delimited ([§3](LANGUAGE.md#3-lexical-structure)).
- **V-style scoping safety** — `const` is strictly global (top-level) and becomes a C `#define`; `var` (mutable) and `let` (immutable) are strictly local to function bodies, preventing accidental mutable global state ([§5](LANGUAGE.md#5-variables-constants--scope)).
- **Expressive type system** — fixed-width integers (`u8`…`u64`, `i8`…`i64`), `f32`/`f64`, `char`, `byte`, `string`, `bool`; fixed-size 1D/2D arrays, non-owning slices, dynamic lists, and hash maps with compile-time layout estimation ([§4](LANGUAGE.md#4-type-system)).
- **User types** — `rune` structs with private `_` fields and `enchanting` method blocks (`self->`), `echo` (C-compatible unions), `omen` (simple enums and algebraic data types with payloads), and `maybe T` / `result of T to E` with statement-expression unwrapping (`or else`, `or return`, `try`) ([§9](LANGUAGE.md#9-composite-types), [§12](LANGUAGE.md#12-optionals--errors)).
- **Methods & compile-time concepts** — `enchanting` attaches methods to structs; `concept` defines compile-time interfaces checked statically with `bind` exhaustiveness, zero runtime overhead, and no vtables ([§10](LANGUAGE.md#10-methods-concepts--binding); see [§10.6 Explicit limitations](LANGUAGE.md#106-limitaciones-explícitas-de-los-concepts)).
- **Strings built one way** — dynamic strings are composed **only** with `"{expr}"` interpolation; `+`/`+=` on strings raise `E0005` (no implicit `to string` promotion, no hidden temporaries), and a `string` stored into a struct field or collection element is deep-copied so ownership stays unambiguous ([§15.2](LANGUAGE.md#152-strings)).
- **Zero-overhead generics** — `shard` declarations specialized with `of`; each instantiation is monomorphized to plain C with concept bounds validation (`where T: Printable`) ([§11](LANGUAGE.md#11-generics)).
- **Deterministic cleanup** — `defer` (LIFO on scope exit), `errdefer` (on error return), scope-owned locals (automatic `banish` at block exit unless marked `borrowed`), and explicit heap release with `banish` ([§13](LANGUAGE.md#13-memory--pointers)).
- **First-class C FFI** — `include`/`link`/`declare`, opaque types (`alias … as opaque`), `sigil of` (address-of) / `essence of` (deref), zero-copy `bytes of <string>` borrows, and `weave`s that decay to C function pointers ([§14](LANGUAGE.md#14-modules-imports--c-interop)).
- **`pengu bind`** — auto-generates a `.d.pengu` declaration file from any C header (structs → `rune`, unions → `echo`, enums → `omen`, functions → `declare`, callbacks → `alias … as ref to weave`, doc comments preserved) with preprocessor extension blanking, sibling auto-imports, and flags (`--define`, `--cpp-flags`, `--system-includes`, `--preprocessed`) ([§20.6](LANGUAGE.md#206-c-header-binding-generator-pengu-bind)).
- **Rich standard library** — `std/` ships **52 modules**: 27 implemented in pure PenguScript (I/O, strings, files, math, time, regex, HTTP client/server, concurrency, logging, unit testing, …) plus 25 curated C declaration bindings (`*.d.pengu`) for bundled native libraries (including **raylib**, **raymath**, **rlgl**, **sqlite3**, **webui**, **miniaudio**, and **stb**) ([§19](LANGUAGE.md#19-standard-library)).
- **Embedded project assets (`arca`)** — embed binary and text assets (textures, shaders, audio, fonts, HTML/JS/CSS, config files) directly into native `.rodata` sections or stream from disk with zero-copy pointer views and slice accessors ([§19.4](LANGUAGE.md#194-embedded-project-assets-arca)).
- **Language Server (LSP)** — diagnostics with `help:`/`note:`/caret spans, documentation from `#` and `##` doc comments, type & memory-size hovers, module-scoped autocompletion, go-to-definition, formatting, and code actions ([§20.10](LANGUAGE.md#2010-language-server-protocol-pengu-lsp)).
- **Unified project manager** — the `pengu` CLI creates (`init`), builds (`build`), runs (`run`), tests (`test`), checks (`check`), formats (`fmt`), cleans (`clean`), and documents (`doc`) projects ([§20](LANGUAGE.md#20-tooling--project-layout)).
- **Compile-time features** — `when` conditionals with `else when` / `else`, `defined(...)`, `-D name=value` defines, function `static var` state, and `when main:` guards for dual module/script files ([§16](LANGUAGE.md#16-conditional-compilation-when)).
- **Robust diagnostics** — comprehensive Rust-style error catalog with codes `E0000`–`E0048` and warnings `W0001`–`W0004` ([§22](LANGUAGE.md#22-appendix-compiler-diagnostic-catalog)).

---

### Quick Start

#### Requirements

- **Python 3.11+** (3.10 also works — `requirements.txt` installs the `tomli` backport automatically there).
- A **C compiler** (`gcc` or `clang`) and static archiver (`ar`/`llvm-ar`) on your `PATH` — on Windows use MinGW-w64 `gcc`.
- **CMake and Ninja** — required for the static builds of libuv, libzip, and libexpat.
- **Node.js 18+ and npm** — only needed to develop or package the VS Code extension.

##### System Dependencies for Linux & macOS

On Linux and macOS, compiling the language runtime and native dependencies requires development packages (including `pkg-config`, `libxml2`, `libcurl`, `mbedtls`, `libmicrohttpd`, `sqlite3`, `openssl`, X11, OpenGL):

**Fedora / RHEL:**
```bash
sudo dnf install -y @development-tools \
    cmake ninja-build pkgconf-pkg-config gcc gcc-c++ \
    zlib-ng-devel pcre2-devel libxml2-devel libcurl-devel \
    mbedtls-devel libmicrohttpd-devel sqlite-devel openssl-devel \
    libX11-devel libXcursor-devel libXrandr-devel libXinerama-devel \
    libXi-devel mesa-libGL-devel
```

**Ubuntu / Debian:**
```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential cmake ninja-build pkg-config gcc g++ \
    libxml2-dev libcurl4-openssl-dev libmbedtls-dev \
    libmicrohttpd-dev libsqlite3-dev libssl-dev \
    libpcre2-dev zlib1g-dev libx11-dev libxcursor-dev \
    libxrandr-dev libxinerama-dev libxi-dev libgl1-mesa-dev
```

**Arch Linux:**
```bash
sudo pacman -S --needed base-devel cmake ninja pkgconf gcc \
    libxml2 curl mbedtls libmicrohttpd sqlite openssl \
    pcre2 zlib libx11 libxcursor libxrandr libxinerama libxi mesa
```

**macOS (Homebrew):**
```bash
brew install cmake ninja pkg-config libxml2 curl mbedtls libmicrohttpd sqlite openssl
```

#### Setup

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

#### Hello, world

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

### Usage: the `pengu` CLI

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
| `doc`      | Generate a Markdown API reference + HTML search from `#`/`##` doc comments (`-o` sets the output directory). |
| `assets`   | Generate or inspect embedded asset modules (`--list`, `--force`).                                 |

```bash
pengu init my_app --type exe
cd my_app
pengu build                 # debug profile (bounds-checking active)
pengu build --profile release
pengu run                   # build + run
pengu assets --list         # inspect tracked embedded assets
pengu check                 # type-check everything (CI)
pengu test                  # run integrated unit tests
pengu test --json           # emit JSON Lines events for CI
pengu test --watch          # recompile and re-run on source modifications
pengu fmt src/ tests/       # format sources
pengu clean
pengu lsp                   # stdio language server
pengu doc -o docs/          # generate module reference
```

Projects are configured with `pengu.toml` or `pengu.yaml` (mutually exclusive; if both exist, `pengu.toml` wins; examples in `LANGUAGE.md` §14.4 use YAML for brevity) — entry point, output type/name, includes, links, per-profile `cflags`/`defines`, and compiler selection. Under the `debug` profile (default), automatic bounds checking (`pengu_assert_bounds`) and stack trace frames are active for index access; in `release`, bounds checking carries zero runtime overhead. See [PENGU_BUILD.md](PENGU_BUILD.md) for the full guide.

#### VS Code extension

The official extension lives in [`vscode-extension/`](vscode-extension/README.md): TextMate syntax highlighting, LSP-powered diagnostics and hovers (type + byte-size), module-scoped autocompletion, go-to-definition, and Build/Run/Clean/Init commands in the Command Palette.

Install it from the packaged `pengus-<version>.vsix` produced by `python make_release.py`, or build it yourself:

```bash
cd vscode-extension
npm install
npm run package             # runs @vscode/vsce package -> pengus-<version>.vsix
```

Then open VS Code → **Extensions** (`Ctrl+Shift+X`) → **`…`** → **Install from VSIX…** and pick the `.vsix` file. See [vscode-extension/README.md](vscode-extension/README.md) for settings (`pengus.executablePath`, `pengus.defaultProfile`) and development instructions.

---

### Performance

`pengu run script.pengu` is meant to feel like running a script, not building a
project. Five independent optimisations, each with a documented off-switch:

| Optimisation | What it does | Disable with |
| ------------ | ------------ | ------------ |
| Parser-table cache | Serializes Lark's LALR tables (~3.9 s → ~0.25 s per process) | `PENGU_CACHE=0` |
| Binary cache | Reuses the linked binary keyed by the *content* hash of the script and every import | `--no-cache`, `--ephemeral` |
| Dead-code elimination | Emits only the `std/`/`lib/` weaves reachable from `main`/tests | `--no-dce`, `PENGU_NO_DCE=1` |
| TinyCC | Bundled in the releases; ~19 ms to compile the bundle vs ~400 ms for gcc | `PENGU_NO_TCC=1`, `PENGU_DEV_CC=gcc` |
| pkg-config memoization | One probe per package per process instead of ~12 spawns | — (always on) |

Measured on the reference machine (Linux x86_64, Python 3.14.7, gcc 16.2.1,
TCC 0.9.28rc, best of 5):

| Scenario | Before | After |
| -------- | -----: | ----: |
| `pengu run hello.pengu` — first run, parser tables cached | 3.88 s | **0.85 s** (gcc) / **0.66 s** (TCC) |
| `pengu run hello.pengu` — second run (cache hit) | 3.88 s | **0.19 s** |
| `bundle.c` of a script using only `std.spark.println` | 432 lines / 19.4 KB | **65 lines / 2.3 KB** (-84%) |
| LALR table construction per process | 3.9 s | **0.25 s** (cached) |
| `compute.pengu` — 10M-iteration loop (run phase) | ~33 ms | 33 ms |

Nothing is written to the project's `build/` by default. Run `pengu doctor` to
see the compiler/TCC/cache status, `pengu time hello.pengu` for a per-phase
breakdown, and `scripts/bench.sh` to reproduce the table above. See
[docs/PERFORMANCE.md](docs/PERFORMANCE.md) for the full design, the
flags/subcommands reference and the known limitations.

If TCC (or any `PENGU_DEV_CC`) fails to compile a bundle, `pengu run` retries
once with the project's configured compiler and warns on stderr instead of
failing the build.

### Language Overview

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
        return "{self->model} at {(self->speed to string)} km/h"

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

#### Generics in practice

Type parameters (`shard`), concept bounds (`where`), automatic concept
implementations (`derive`), default values (`donum T`) and recursive types
(`cyclus`) all monomorphize to plain C — no vtables, no boxing:

```pengu
# Generic numeric sum: 'Num' enables + - * /, 'donum T' is the zero value.
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc

# Integer-only operators (%, &, |, ^, <<, >>) need the stricter 'Integrum'.
weave mod2 shard T where T: Integrum with a as T, b as T into T:
    return a % b

# Derive standard concepts from the fields (Par -> ==, Ordo -> <, ...).
rune Point derive Par, Ordo, Vinculum, Imago:
    x as int
    y as int

# Generic container methods; concrete blocks take priority when both apply.
enchanting map of shard K to shard V where K: Vinculum:
    weave size into int:
        return calling self.len

enchanting Box shard T:
    weave get into T:
        return self->val

# Recursive generic type with pointer indirection.
rune Node cyclus shard T:
    value as T
    next as maybe ref to Node of T
```

Key rules:

- `+ - * /` need `where T: Num`; `% & | ^ << >>` need `where T: Integrum`
  (which also satisfies `Num`); `==` needs `Par`; `< <= > >=` need `Ordo`.
  Missing bounds are reported with the exact clause to add (`E0049`).
- Containers deep-copy on `push`/`put` and release recursively on banish
  (`list of string`, `map of string to list of int`), so nested ownership is
  leak-free without manual `banish`; see [LANGUAGE.md §13.5](LANGUAGE.md#135-container-ownership--deep-copy).
- `derive` works on runes, algebraic omens and generic instantiations; `Imago`
  (deep copy) and `Nexus` (drop) are implied by each other. `echo` unions reject
  `derive` because they are untagged.
- Iterating a bare type parameter (`for x in xs` with `xs as T`) is rejected:
  use `list of T` / `slice of T` (associated types are future work).

The `tests/test_generics/` directory contains one runnable program per feature
plus leak checks; run them with `python -m pytest tests/test_generics_suite.py`.

#### Standard library

`std/` contains **52 modules** — 27 written in pure PenguScript and 25 curated C declaration bindings (`.d.pengu`). See [LANGUAGE.md §19](LANGUAGE.md#19-standard-library) for the full module catalog and code examples.

- **Pure PenguScript modules (27):** `spark` (core I/O, formatted output, typed input, ranges & math helpers), `scrolls` (comprehensive string enchanting algorithms, metrics, casing & three-way string ordering), `oracle` (`Maybe`/`Result` containers with native/legacy interoperability), `compass` (cross-platform paths & pattern matching), `archivum` (files, binary I/O & directory traversal), `cipher` (JSON RFC 8259, Base64/32/Hex & validation), `chronicle` (dates, high-res clocks, timers & duration parsing), `lot` (PRNG, statistical distributions, sampling, shuffling & random strings), `arithmancy` (advanced math), `rites` (OS processes, cross-platform environment & system info), `whisper` (structured leveled logging & `Logger` rune), `ward` (defensive invariants, float/range/container assertions & generic `shard T` tests), `trial` (unit testing), `tally` (functional list operations, reductions, insertion sort & statistics), `atlas` (hash map key-value store, combination, bulk accessors & filters), `coven` (unique `SetString`/`SetInt` collections, ritual constructors & set algebra), `regulus` (PCRE2 regex), `parchment` (libxml2 XML/HTML), `seal` (hashing + compression via Mbed TLS/zlib), `precis` (HTTP client/server & sockets), `filum` (threads, typed channels, mutexes & atomic operations), `loom` (sequence pipelines, windowing & generic algorithms), `invoke` (advanced CLI parsing, subcommands, typed flags, multi-options & typo suggestions), `ffi` (C bridge), `celeris` (profiling), `xlsx` (Excel writing), and `ledger` (CSV/TSV parsing, tabular data & matrix enchantments).
- **C native declaration bindings (25):** `raylib`, `raymath`, `rlgl`, `rlights`, `raygui`, `sqlite3`, `webui`, `miniaudio`, `tomlum`, `yaml`, `uuid`, `xxhash`, `xlsxio`, `imago`, `typis`, `scriptor`, `perlinum`, `stb_image_resize2`, `stb_herringbone_wang_tile`, `nanosvg`, `nanosvgrast`, `minicoro`, `datastructura`, `fenestra`, and `pactum`.

With the completion of **Batch 6 (FINAL)** (`regulus`, `precis`, `parchment`, `seal`, `ffi`, `arithmancy`), the PenguScript 0.15.0 standard library expansion is **🎉 FEATURE-COMPLETE 🎉** across all six planned batches:
1. **Collections & Data Structures:** `tally`, `atlas`, `coven`
2. **System & Filesystem:** `chronicle`, `compass`, `archivum`
3. **Runtime, Concurrency & Logging:** `rites`, `filum`, `whisper`
4. **Data-Processing & Algorithmic Layer:** `cipher`, `loom`, `ledger`
5. **Testing, CLI & Utilities:** `lot`, `ward`, `invoke`
6. **Advanced Integration & Math Tier:** `regulus` (PCRE2 regex), `precis` (HTTP client/server), `parchment` (libxml2 XML/HTML DOM), `seal` (HMAC, SHA/MD5 hashing & compression), `ffi` (null-safe generic C bridge), `arithmancy` (game-ready linear algebra: Vec2/3/4, Mat4, Quat)

All 52 modules ship comprehensive documentation (`#`/`##` doc comments, audited by `tests/test_std_docs_completeness.py`), full test coverage across `debug` and `release` compilation profiles, 100% backward compatibility with PenguScript 0.14.x, and zero C compiler warnings.

---

### Project Layout

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
├── std/                    # Standard library: 27 pure-PenguScript modules +
│                           #   25 C declaration bindings (*.d.pengu) (52 modules total)
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

### Building the Runtime from Source

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

### Documentation

A single entry point to every document in the repository:

| Document | Contents |
| -------- | -------- |
| [README.md](README.md) | This file — project overview, quick start, and credits |
| [PenguScriptGuideEnglish.md](PenguScriptGuideEnglish.md) | Idiomatic PenguScript style guide (English) |
| [PenguScriptGuideSpanish.md](PenguScriptGuideSpanish.md) | Guía de estilo de PenguScript (Español) |
| [LANGUAGE.md](LANGUAGE.md) | General language reference (English) |
| [LANGUAGE_Spanish.md](LANGUAGE_Spanish.md) | Referencia general del lenguaje (Español) |

Additional references:

| Document                                              | What it covers                                                |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| [LANGUAGE.md](LANGUAGE.md)                            | Comprehensive language specification, stdlib, and diagnostics |
| [CHEATSHEET.md](CHEATSHEET.md)                        | Full language syntax, keywords, and C-translation reference   |
| [PENGU_BUILD.md](PENGU_BUILD.md)                      | `pengu` CLI, project config, and the build system             |
| [CHANGELOG.md](CHANGELOG.md)                          | Version history and per-release feature log                   |
| [README_RELEASE.md](README_RELEASE.md)                | The standalone `pengucc_build/` release package               |
| [vscode-extension/README.md](vscode-extension/README.md) | VS Code extension: features, settings, installation        |

---

### Third-Party Acknowledgements & Credits

PenguScript's toolchain, C runtime, and standard library stand on the shoulders of many excellent open-source projects. We gratefully acknowledge and thank their authors. License names below are as published by each upstream project; vendored code keeps its original copyright/license notices (see the header comments in `std_c/`).

#### Python (toolchain) dependencies

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

#### C runtime & standard library

##### Compiled external libraries (built into `build/lib` by `build_runtime.py`)

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

##### Vendored single-header libraries (`std_c/`)

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

### License

PenguScript is released under the **[MIT License](LICENSE)** — © 2026 TuGatito. Third-party components retain their own licenses as noted above; see each vendored header and the upstream projects for details.

---

## 🇪🇸 Español

### Características destacadas

- **Sintaxis pitónica basada en indentación** — sin puntos y coma ni llaves; los bloques se delimitan con espacios en blanco ([§3](LANGUAGE.md#3-lexical-structure)).
- **Seguridad de ámbito al estilo V** — `const` es estrictamente global (de nivel superior) y se convierte en un `#define` de C; `var` (mutable) y `let` (inmutable) son estrictamente locales al cuerpo de la función, lo que evita estado global mutable accidental ([§5](LANGUAGE.md#5-variables-constants--scope)).
- **Sistema de tipos expresivo** — enteros de ancho fijo (`u8`…`u64`, `i8`…`i64`), `f32`/`f64`, `char`, `byte`, `string`, `bool`; arrays 1D/2D de tamaño fijo, slices sin propiedad, listas dinámicas y mapas hash con estimación de diseño en tiempo de compilación ([§4](LANGUAGE.md#4-type-system)).
- **Tipos de usuario** — `rune` (structs) con campos privados `_` y bloques de métodos `enchanting` (`self->`), `echo` (uniones compatibles con C), `omen` (enumeraciones simples y tipos algebraicos con carga útil), y `maybe T` / `result of T to E` con desenvoltura mediante expresiones de sentencia (`or else`, `or return`, `try`) ([§9](LANGUAGE.md#9-composite-types), [§12](LANGUAGE.md#12-optionals--errors)).
- **Métodos y conceptos en tiempo de compilación** — `enchanting` asocia métodos a los structs; `concept` define interfaces en tiempo de compilación verificadas estáticamente con exhaustividad de `bind`, sin coste en tiempo de ejecución y sin tablas virtuales ([§10](LANGUAGE.md#10-methods-concepts--binding); consulta [§10.6 Limitaciones explícitas](LANGUAGE.md#106-limitaciones-explícitas-de-los-concepts)).
- **Cadenas construidas de una sola forma** — las cadenas dinámicas se componen **solo** con interpolación `"{expr}"`; `+`/`+=` sobre cadenas producen `E0005` (sin promoción implícita `to string` y sin temporales ocultos), y una `string` almacenada en un campo de struct o en un elemento de colección se copia en profundidad para que la propiedad quede inequívoca ([§15.2](LANGUAGE.md#152-strings)).
- **Genéricos sin coste** — declaraciones `shard` especializadas con `of`; cada instanciación se monomorfiza a C plano con validación de cotas de conceptos (`where T: Printable`) ([§11](LANGUAGE.md#11-generics)).
- **Limpieza determinista** — `defer` (LIFO al salir del ámbito), `errdefer` (al retornar un error), locales propiedad del ámbito (`banish` automático al salir del bloque salvo que se marquen como `borrowed`) y liberación explícita del heap con `banish` ([§13](LANGUAGE.md#13-memory--pointers)).
- **FFI de C de primera clase** — `include`/`link`/`declare`, tipos opacos (`alias … as opaque`), `sigil of` (dirección de) / `essence of` (desreferencia), préstamos sin copia con `bytes of <string>` y `weave`s que decaen a punteros a función de C ([§14](LANGUAGE.md#14-modules-imports--c-interop)).
- **`pengu bind`** — genera automáticamente un archivo de declaraciones `.d.pengu` a partir de cualquier cabecera de C (structs → `rune`, uniones → `echo`, enumeraciones → `omen`, funciones → `declare`, callbacks → `alias … as ref to weave`, conservando los comentarios de documentación) con blanqueo de extensiones del preprocesador, autoimportación de hermanos y opciones (`--define`, `--cpp-flags`, `--system-includes`, `--preprocessed`) ([§20.6](LANGUAGE.md#206-c-header-binding-generator-pengu-bind)).
- **Biblioteca estándar completa** — `std/` incluye **52 módulos**: 27 implementados en PenguScript puro (E/S, cadenas, archivos, matemáticas, tiempo, regex, cliente/servidor HTTP, concurrencia, registro de logs, pruebas unitarias, …) más 25 enlaces de declaraciones de C (`*.d.pengu`) para bibliotecas nativas incluidas (entre ellas **raylib**, **raymath**, **rlgl**, **sqlite3**, **webui**, **miniaudio** y **stb**) ([§19](LANGUAGE.md#19-standard-library)).
- **Recursos embebidos del proyecto (`arca`)** — incrusta recursos binarios y de texto (texturas, shaders, audio, fuentes, HTML/JS/CSS, archivos de configuración) directamente en secciones `.rodata` nativas o los lee desde disco con vistas de puntero sin copia y accesores de slice ([§19.4](LANGUAGE.md#194-embedded-project-assets-arca)).
- **Servidor de lenguaje (LSP)** — diagnósticos con `help:`/`note:`/intervalos con cursor, documentación a partir de comentarios `#` y `##`, información emergente de tipos y tamaño en memoria, autocompletado con ámbito de módulo, ir a la definición, formateo y acciones de código ([§20.10](LANGUAGE.md#2010-language-server-protocol-pengu-lsp)).
- **Gestor de proyectos unificado** — la CLI `pengu` crea (`init`), compila (`build`), ejecuta (`run`), prueba (`test`), verifica (`check`), formatea (`fmt`), limpia (`clean`) y documenta (`doc`) proyectos ([§20](LANGUAGE.md#20-tooling--project-layout)).
- **Funciones en tiempo de compilación** — condicionales `when` con `else when` / `else`, `defined(...)`, definiciones `-D name=value`, estado `static var` de función y guardas `when main:` para archivos que sirven como módulo y como script ([§16](LANGUAGE.md#16-conditional-compilation-when)).
- **Diagnósticos robustos** — catálogo completo de errores al estilo de Rust con códigos `E0000`–`E0048` y advertencias `W0001`–`W0004` ([§22](LANGUAGE.md#22-appendix-compiler-diagnostic-catalog)).

---

### Inicio rápido

#### Requisitos

- **Python 3.11+** (3.10 también funciona — allí `requirements.txt` instala automáticamente el backport `tomli`).
- Un **compilador de C** (`gcc` o `clang`) y un archivador estático (`ar`/`llvm-ar`) en tu `PATH` — en Windows usa el `gcc` de MinGW-w64.
- **CMake y Ninja** — necesarios para las compilaciones estáticas de libuv, libzip y libexpat.
- **Node.js 18+ y npm** — solo se necesitan para desarrollar o empaquetar la extensión de VS Code.

##### Dependencias del sistema para Linux y macOS

En Linux y macOS, compilar el runtime del lenguaje y las dependencias nativas requiere paquetes de desarrollo (entre ellos `pkg-config`, `libxml2`, `libcurl`, `mbedtls`, `libmicrohttpd`, `sqlite3`, `openssl`, X11 y OpenGL):

**Fedora / RHEL:**
```bash
sudo dnf install -y @development-tools \
    cmake ninja-build pkgconf-pkg-config gcc gcc-c++ \
    zlib-ng-devel pcre2-devel libxml2-devel libcurl-devel \
    mbedtls-devel libmicrohttpd-devel sqlite-devel openssl-devel \
    libX11-devel libXcursor-devel libXrandr-devel libXinerama-devel \
    libXi-devel mesa-libGL-devel
```

**Ubuntu / Debian:**
```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential cmake ninja-build pkg-config gcc g++ \
    libxml2-dev libcurl4-openssl-dev libmbedtls-dev \
    libmicrohttpd-dev libsqlite3-dev libssl-dev \
    libpcre2-dev zlib1g-dev libx11-dev libxcursor-dev \
    libxrandr-dev libxinerama-dev libxi-dev libgl1-mesa-dev
```

**Arch Linux:**
```bash
sudo pacman -S --needed base-devel cmake ninja pkgconf gcc \
    libxml2 curl mbedtls libmicrohttpd sqlite openssl \
    pcre2 zlib libx11 libxcursor libxrandr libxinerama libxi mesa
```

**macOS (Homebrew):**
```bash
brew install cmake ninja pkg-config libxml2 curl mbedtls libmicrohttpd sqlite openssl
```

#### Configuración

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

#### Hola, mundo

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
```

Guárdalo como `hello.pengu` y ejecútalo como script independiente:

```bash
# From a source checkout:
python pengu_project.py run hello.pengu

# With the packaged standalone CLI (see "Building the runtime from source"):
pengu run hello.pengu
```

> La CLI es `pengu_project.py` en una copia del código fuente y el ejecutable `pengu`/`pengu.exe` en una compilación de publicación. El resto de este documento usa `pengu` por brevedad.

---

### Uso: la CLI `pengu`

| Comando    | Descripción                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------- |
| `init`     | Crea una plantilla de proyecto nueva (`--type exe\|static\|shared\|obj\|c`, `--links`, `--cc`).    |
| `add`      | Añade una dependencia o enlace externo (URL de git o carpeta local, con script de compilación opcional). |
| `build`    | Compila el proyecto según su configuración (`--profile release`, `--cc`, `-D`, `--test`, `--verbose`). |
| `run`      | Compila y ejecuta el objetivo del proyecto, o ejecuta un archivo `.pengu` suelto directamente como script. |
| `test`     | Compila en modo `--test` y ejecuta las pruebas unitarias integradas del proyecto (`--json`, `--watch`). |
| `check`    | Analiza y verifica tipos de todos los módulos sin generar código — ideal para CI.                 |
| `update`   | Actualiza y recompila cada dependencia configurada.                                               |
| `bind`     | Genera un archivo de declaraciones `.d.pengu` a partir de una cabecera de C (`--prefix`, `--links`, `--ignore`, …). |
| `fmt`      | Formatea archivos o directorios `.pengu` (`--check` solo informa; `--tabs`/`--indent`).           |
| `clean`    | Elimina el directorio de compilación y los artefactos generados.                                  |
| `lsp`      | Inicia el servidor de lenguaje (stdio por defecto; `--tcp --host … --port …`).                     |
| `doc`      | Genera una referencia de API en Markdown a partir de los comentarios `##` (`-o` fija el directorio de salida). |
| `assets`   | Genera o inspecciona módulos de recursos embebidos (`--list`, `--force`).                         |

```bash
pengu init my_app --type exe
cd my_app
pengu build                 # debug profile (bounds-checking active)
pengu build --profile release
pengu run                   # build + run
pengu assets --list         # inspect tracked embedded assets
pengu check                 # type-check everything (CI)
pengu test                  # run integrated unit tests
pengu test --json           # emit JSON Lines events for CI
pengu test --watch          # recompile and re-run on source modifications
pengu fmt src/ tests/       # format sources
pengu clean
pengu lsp                   # stdio language server
pengu doc -o docs/          # generate module reference
```

Los proyectos se configuran con `pengu.toml` o `pengu.yaml` (mutuamente excluyentes; si existen ambos, gana `pengu.toml`; los ejemplos de la §14.4 de `LANGUAGE.md` usan YAML por brevedad) — punto de entrada, tipo y nombre de salida, includes, links, `cflags`/`defines` por perfil y selección de compilador. Con el perfil `debug` (el predeterminado), la verificación automática de límites (`pengu_assert_bounds`) y los marcos de traza de pila están activos para el acceso por índice; en `release`, la verificación de límites no tiene coste en tiempo de ejecución. Consulta [PENGU_BUILD.md](PENGU_BUILD.md) para la guía completa.

#### Extensión de VS Code

La extensión oficial está en [`vscode-extension/`](vscode-extension/README.md): resaltado de sintaxis con TextMate, diagnósticos e información emergente con el LSP (tipo + tamaño en bytes), autocompletado con ámbito de módulo, ir a la definición y comandos Build/Run/Clean/Init en la paleta de comandos.

Instálala desde el paquete `pengus-<version>.vsix` que produce `python make_release.py`, o compílala tú mismo:

```bash
cd vscode-extension
npm install
npm run package             # runs @vscode/vsce package -> pengus-<version>.vsix
```

Luego abre VS Code → **Extensions** (`Ctrl+Shift+X`) → **`…`** → **Install from VSIX…** y elige el archivo `.vsix`. Consulta [vscode-extension/README.md](vscode-extension/README.md) para la configuración (`pengus.executablePath`, `pengus.defaultProfile`) y las instrucciones de desarrollo.

---

### Rendimiento

`pengu run script.pengu` debe sentirse como ejecutar un script, no como compilar
un proyecto. Cinco optimizaciones independientes, cada una con su interruptor
documentado:

| Optimización | Qué hace | Desactivar con |
| ------------ | -------- | -------------- |
| Caché de tablas del analizador | Serializa las tablas LALR de Lark (~3,9 s → ~0,25 s por proceso) | `PENGU_CACHE=0` |
| Caché de binarios | Reutiliza el binario enlazado según el hash del *contenido* del script y de cada import | `--no-cache`, `--ephemeral` |
| Eliminación de código muerto | Emite solo los `weave` de `std/`/`lib/` alcanzables desde `main`/las pruebas | `--no-dce`, `PENGU_NO_DCE=1` |
| TinyCC | Incluido en las publicaciones; ~19 ms para compilar el paquete frente a ~400 ms con gcc | `PENGU_NO_TCC=1`, `PENGU_DEV_CC=gcc` |
| Memoización de pkg-config | Una consulta por paquete y proceso en lugar de ~12 lanzamientos | — (siempre activa) |

Medido en la máquina de referencia (Linux x86_64, Python 3.14.7, gcc 16.2.1,
TCC 0.9.28rc, mejor de 5):

| Escenario | Antes | Después |
| --------- | ----: | ------: |
| `pengu run hello.pengu` — primera ejecución, tablas del analizador en caché | 3,88 s | **0,85 s** (gcc) / **0,66 s** (TCC) |
| `pengu run hello.pengu` — segunda ejecución (acierto de caché) | 3,88 s | **0,19 s** |
| `bundle.c` de un script que solo usa `std.spark.println` | 432 líneas / 19,4 KB | **65 líneas / 2,3 KB** (-84 %) |
| Construcción de las tablas LALR por proceso | 3,9 s | **0,25 s** (en caché) |
| `compute.pengu` — bucle de 10M iteraciones (fase de ejecución) | ~33 ms | 33 ms |

Por defecto no se escribe nada en el `build/` del proyecto. Ejecuta `pengu doctor`
para ver el estado del compilador, TCC y la caché, `pengu time hello.pengu` para
un desglose por fases, y `scripts/bench.sh` para reproducir la tabla anterior.
Consulta [docs/PERFORMANCE.md](docs/PERFORMANCE.md) para el diseño completo, la
referencia de opciones y subcomandos, y las limitaciones conocidas.

Si TCC (o cualquier `PENGU_DEV_CC`) no consigue compilar un paquete, `pengu run`
lo reintenta una vez con el compilador configurado en el proyecto y avisa por
stderr en lugar de hacer fallar la compilación.

### Visión general del lenguaje

Un recorrido rápido — la referencia autorizada de sintaxis y traducción a C es **[CHEATSHEET.md](CHEATSHEET.md)**.

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
        return "{self->model} at {(self->speed to string)} km/h"

weave main into int:
    var car as Vehicle is with model is "Pengu", speed is 0.0
    calling car.accelerate with 45.5
    calling spark.println with calling car.describe
    return 0
```

- **Declaraciones** — locales `var` (mutables) / `let` (inmutables), `const` de nivel superior y funciones `weave name with a as T, b as T into R`. Los valores se asignan con `is` y se modifican con `set`.
- **Tipos y colecciones** — structs `rune`, `omen` (enumeraciones con carga útil) y `echo` (uniones de C), manejo de errores con `maybe T`/`or:`, `array of T` de tamaño fijo, `slice of T`, `list of T` dinámica y `map of K to V` hash mediante `at`. La coincidencia de patrones usa `judge … when …`.
- **Genéricos** — declaraciones `rune Box shard T:`, especializadas con `Box of int`; llamadas como `calling make_box of int with 42` se monomorfizan a C plano.
- **Memoria** — `defer`/`errdefer` se ejecutan al salir del ámbito (o al producirse un error), `banish` libera memoria del heap, y `sigil of x` / `essence of p` dan dirección de y desreferencia explícitas.
- **Tiempo de compilación** — bloques `when os == "windows":` / `when main:`, `defined(...)` y definiciones `-D name=value`; un archivo `.pengu` ejecutado como script siempre compila con `main` = `true` (los módulos importados reciben `false`), lo que habilita código exclusivo de script:

  ```pengu
  when main:
      weave main into int:
          calling spark.println with "Running as a script!"
          return 0
  ```

- **FFI de C** — los archivos de declaraciones (`*.d.pengu`) conectan C directamente con PenguScript:

  ```pengu
  # std/xxhash.d.pengu (excerpt)
  include "xxhash.h"
  alias XXH32_state_t as opaque
  rune XXH128_hash_t:
      low64 as u64
      high64 as u64
  declare XXH64 with input as ref to char, length as size_t, seed as u64 into u64
  ```

  …y después, desde tu código:

  ```pengu
  import std.xxhash
  var h as u64 is calling xxhash.XXH64 with "PenguScript", 11, 0
  ```

  Las cabeceras de C del mundo real se pueden convertir en enlaces así de forma automática con `pengu bind`.

#### Genéricos en la práctica

Los parámetros de tipo (`shard`), las cotas de conceptos (`where`), las
implementaciones automáticas de conceptos (`derive`), los valores por defecto
(`donum T`) y los tipos recursivos (`cyclus`) se monomorfizan todos a C plano —
sin tablas virtuales ni boxing:

```pengu
# Generic numeric sum: 'Num' enables + - * /, 'donum T' is the zero value.
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc

# Integer-only operators (%, &, |, ^, <<, >>) need the stricter 'Integrum'.
weave mod2 shard T where T: Integrum with a as T, b as T into T:
    return a % b

# Derive standard concepts from the fields (Par -> ==, Ordo -> <, ...).
rune Point derive Par, Ordo, Vinculum, Imago:
    x as int
    y as int

# Generic container methods; concrete blocks take priority when both apply.
enchanting map of shard K to shard V where K: Vinculum:
    weave size into int:
        return calling self.len

enchanting Box shard T:
    weave get into T:
        return self->val

# Recursive generic type with pointer indirection.
rune Node cyclus shard T:
    value as T
    next as maybe ref to Node of T
```

Reglas clave:

- `+ - * /` necesitan `where T: Num`; `% & | ^ << >>` necesitan `where T: Integrum`
  (que también satisface `Num`); `==` necesita `Par`; `< <= > >=` necesitan `Ordo`.
  Cuando faltan cotas, se informa de la cláusula exacta que hay que añadir (`E0049`).
- Los contenedores copian en profundidad en `push`/`put` y liberan de forma
  recursiva al hacer banish (`list of string`, `map of string to list of int`),
  así que la propiedad anidada no tiene fugas sin `banish` manual; consulta
  [LANGUAGE.md §13.5](LANGUAGE.md#135-container-ownership--deep-copy).
- `derive` funciona en runes, omens algebraicos e instanciaciones genéricas;
  `Imago` (copia en profundidad) y `Nexus` (drop) se implican mutuamente. Las
  uniones `echo` rechazan `derive` porque no llevan etiqueta.
- Iterar un parámetro de tipo desnudo (`for x in xs` con `xs as T`) se rechaza:
  usa `list of T` / `slice of T` (los tipos asociados son trabajo futuro).

El directorio `tests/test_generics/` contiene un programa ejecutable por
característica más comprobaciones de fugas; ejecútalos con
`python -m pytest tests/test_generics_suite.py`.

#### Biblioteca estándar

`std/` contiene **52 módulos** — 27 escritos en PenguScript puro y 25 enlaces de declaraciones de C seleccionados (`.d.pengu`). Consulta [LANGUAGE.md §19](LANGUAGE.md#19-standard-library) para el catálogo completo de módulos y ejemplos de código.

- **Módulos en PenguScript puro (27):** `spark` (E/S básica, salida formateada, entrada tipada, rangos y ayudas matemáticas), `scrolls` (algoritmos completos de manipulación de cadenas, métricas, capitalización y ordenación de cadenas a tres bandas), `oracle` (contenedores `Maybe`/`Result` con interoperabilidad nativa y heredada), `compass` (rutas multiplataforma y coincidencia de patrones), `archivum` (archivos, E/S binaria y recorrido de directorios), `cipher` (JSON RFC 8259, Base64/32/Hex y validación), `chronicle` (fechas, relojes de alta resolución, temporizadores y análisis de duraciones), `lot` (PRNG, distribuciones estadísticas, muestreo, barajado y cadenas aleatorias), `arithmancy` (matemáticas avanzadas), `rites` (procesos del SO, entorno e información del sistema multiplataforma), `whisper` (registro de logs estructurado por niveles y rune `Logger`), `ward` (invariantes defensivos, aserciones de flotantes/rangos/contenedores y pruebas genéricas `shard T`), `trial` (pruebas unitarias), `tally` (operaciones funcionales sobre listas, reducciones, ordenación por inserción y estadísticas), `atlas` (almacén clave-valor con mapas hash, combinación, accesores masivos y filtros), `coven` (colecciones únicas `SetString`/`SetInt`, constructores rituales y álgebra de conjuntos), `regulus` (regex PCRE2), `parchment` (XML/HTML con libxml2), `seal` (hashing y compresión con Mbed TLS/zlib), `precis` (cliente/servidor HTTP y sockets), `filum` (hilos, canales tipados, mutex y operaciones atómicas), `loom` (pipelines de secuencias, ventanas y algoritmos genéricos), `invoke` (análisis avanzado de CLI, subcomandos, flags tipados, multiopciones y sugerencias ante erratas), `ffi` (puente con C), `celeris` (perfilado), `xlsx` (escritura de Excel) y `ledger` (análisis de CSV/TSV, datos tabulares y encantamientos de matrices).
- **Enlaces de declaraciones nativas de C (25):** `raylib`, `raymath`, `rlgl`, `rlights`, `raygui`, `sqlite3`, `webui`, `miniaudio`, `tomlum`, `yaml`, `uuid`, `xxhash`, `xlsxio`, `imago`, `typis`, `scriptor`, `perlinum`, `stb_image_resize2`, `stb_herringbone_wang_tile`, `nanosvg`, `nanosvgrast`, `minicoro`, `datastructura`, `fenestra` y `pactum`.

Con la finalización del **Lote 6 (FINAL)** (`regulus`, `precis`, `parchment`, `seal`, `ffi`, `arithmancy`), la ampliación de la biblioteca estándar de PenguScript 0.15.0 está **🎉 COMPLETA 🎉** en los seis lotes previstos:
1. **Colecciones y estructuras de datos:** `tally`, `atlas`, `coven`
2. **Sistema y sistema de archivos:** `chronicle`, `compass`, `archivum`
3. **Runtime, concurrencia y logs:** `rites`, `filum`, `whisper`
4. **Capa de procesamiento de datos y algoritmia:** `cipher`, `loom`, `ledger`
5. **Pruebas, CLI y utilidades:** `lot`, `ward`, `invoke`
6. **Integración avanzada y nivel matemático:** `regulus` (regex PCRE2), `precis` (cliente/servidor HTTP), `parchment` (DOM XML/HTML con libxml2), `seal` (HMAC, hashing SHA/MD5 y compresión), `ffi` (puente genérico con C a prueba de nulos), `arithmancy` (álgebra lineal lista para juegos: Vec2/3/4, Mat4, Quat)

Los 52 módulos incluyen documentación completa (docstrings `##`), cobertura de pruebas total en los perfiles de compilación `debug` y `release`, compatibilidad hacia atrás del 100 % con PenguScript 0.14.x y cero advertencias del compilador de C.

---

### Estructura del proyecto

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
├── std/                    # Standard library: 27 pure-PenguScript modules +
│                           #   25 C declaration bindings (*.d.pengu) (52 modules total)
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

### Compilar el runtime desde el código fuente

`build_runtime.py` produce los archivos estáticos que `pengu` enlaza en cada binario. Se ejecuta en dos etapas:

1. **Descargar y extraer** — `extern_manifest.py` mantiene el manifiesto de cada biblioteca externa de C (nombre → URL → directorio esperado) y descarga/extrae en `extern/` las que faltan (ignorado por git). Se invoca automáticamente al inicio de `build_runtime.py` y también se puede ejecutar por separado: `python extern_manifest.py`.
2. **Compilar** — `build_runtime.py` compila después cada biblioteca con `gcc`/`clang` + `ar` (CMake para libuv, libzip y libexpat) en `build/lib/*.a`, preparando las cabeceras en `build/include/`:

```bash
python build_runtime.py            # download externs if needed, build everything
python build_runtime.py --rebuild  # force a clean rebuild
```

Los constructores (`build_zlib`, `build_pcre2`, `build_libxml2`, `build_mbedtls`, `build_curl`, `build_microhttpd`, `build_sqlite3`, `build_libzip`, `build_libexpat`, `build_xlsxio`, `build_libyaml`, `build_libcyaml`, `build_libuv`, `build_tomlc17`, `build_webui`, `build_raylib`, `build_pengu_stb`, `build_pengu_runtime`) producen, entre otros, `libz.a`, `libpcre2-8.a`, `libxml2.a`, `libmbedcrypto.a`, `libcurl.a`, `libmicrohttpd.a`, `libsqlite3.a`, `libraylib.a`, `libwebui.a`, `libuv.a`, `libyaml.a`, `libcyaml.a`, `libzip.a`, `libexpat.a`, `libxlsxio_read.a`/`libxlsxio_write.a`, `libtomlc17.a`, `libpengu_stb.a` (las implementaciones incluidas de un solo archivo de cabecera, ver más abajo) y `libpengu_runtime.a` (el propio runtime). Cualquier archivo presente en `build/lib` se enlaza automáticamente en los proyectos que enlazan `pengu_runtime`. En hosts POSIX el runtime puede usar el libxml2/libcurl/libmicrohttpd del sistema en lugar de las compilaciones estáticas.

> La primera ejecución descarga y extrae las fuentes de las bibliotecas externas, así que necesita acceso a internet; las siguientes son incrementales y omiten todo lo que ya está compilado.

**Publicaciones** — `make_release.py` automatiza toda la distribución: verifica e instala las dependencias de Python, recompila el runtime (`--rebuild`), ejecuta pruebas de humo, empaqueta la CLI + el LSP en un ejecutable independiente con PyInstaller (`pengu` / `pengu.exe`) y compila la extensión de VS Code (`pengus-<version>.vsix`). Todo queda en `pengucc_build/`:

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

Consulta [README_RELEASE.md](README_RELEASE.md) para la documentación propia de la distribución.

---

### Documentación

Un único punto de entrada a todos los documentos del repositorio:

| Documento | Contenido |
| --------- | --------- |
| [README.md](README.md) | Este archivo — visión general del proyecto, inicio rápido y créditos |
| [PenguScriptGuideEnglish.md](PenguScriptGuideEnglish.md) | Guía de estilo idiomático de PenguScript (English) |
| [PenguScriptGuideSpanish.md](PenguScriptGuideSpanish.md) | Guía de estilo de PenguScript (Español) |
| [LANGUAGE.md](LANGUAGE.md) | Referencia general del lenguaje (English) |
| [LANGUAGE_Spanish.md](LANGUAGE_Spanish.md) | Referencia general del lenguaje (Español) |

Referencias adicionales:

| Documento                                             | Qué cubre                                                     |
| ----------------------------------------------------- | ------------------------------------------------------------- |
| [LANGUAGE.md](LANGUAGE.md)                            | Especificación completa del lenguaje, biblioteca estándar y diagnósticos |
| [CHEATSHEET.md](CHEATSHEET.md)                        | Sintaxis completa del lenguaje, palabras clave y referencia de traducción a C |
| [PENGU_BUILD.md](PENGU_BUILD.md)                      | CLI `pengu`, configuración de proyecto y sistema de compilación |
| [CHANGELOG.md](CHANGELOG.md)                          | Historial de versiones y registro de características por publicación |
| [README_RELEASE.md](README_RELEASE.md)                | El paquete de publicación independiente `pengucc_build/`      |
| [vscode-extension/README.md](vscode-extension/README.md) | Extensión de VS Code: características, configuración, instalación |

---

### Agradecimientos y créditos a terceros

La cadena de herramientas, el runtime de C y la biblioteca estándar de PenguScript se apoyan en muchos proyectos de código abierto excelentes. Agradecemos y reconocemos con gusto a sus autores. Los nombres de licencia que aparecen abajo son los publicados por cada proyecto original; el código incluido conserva sus avisos originales de copyright/licencia (consulta los comentarios de cabecera en `std_c/`).

#### Dependencias de Python (cadena de herramientas)

Declaradas en [requirements.txt](requirements.txt):

| Dependencia                                                                   | Para qué se usa                                            | Licencia                       |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------ |
| [Lark](https://github.com/lark-parser/lark)                                   | Gramática y análisis del lenguaje (`pengu_parser`)         | MIT                            |
| [PyYAML](https://pyyaml.org/)                                                 | Análisis de la configuración de proyecto `pengu.yaml`       | MIT                            |
| [pygls](https://github.com/openlawlibrary/pygls)                              | Framework del Protocolo de Servidor de Lenguaje (`pengu_lsp`) | Apache-2.0                  |
| [lsprotocol](https://github.com/microsoft/lsprotocol)                         | Tipos del protocolo LSP (con pygls)                        | MIT                            |
| [pycparser](https://github.com/eliben/pycparser)                              | Análisis de cabeceras de C en `pengu bind`                 | BSD-3-Clause                   |
| [PyInstaller](https://pyinstaller.org/)                                       | Empaquetar el ejecutable independiente `pengu` (paso de publicación) | GPL-2.0-or-later (con excepción del bootloader) |
| [pytest](https://pytest.org/)                                                 | Ejecutor de pruebas (`pytest tests/`)                      | MIT                            |
| [tomli](https://github.com/hukkin/tomli)                                      | Backport de `tomllib` para `pengu.toml` en Python < 3.11   | MIT                            |

#### Runtime de C y biblioteca estándar

##### Bibliotecas externas compiladas (compiladas en `build/lib` por `build_runtime.py`)

| Biblioteca                                         | Versión   | Usada por                                   | Licencia               |
| -------------------------------------------------- | --------- | ------------------------------------------- | ---------------------- |
| [zlib](https://zlib.net/)                          | 1.3.2     | `std.seal` (deflate/inflate)                 | zlib                   |
| [PCRE2](https://www.pcre.org/)                     | 10.47     | `std.regulus` (regex)                       | BSD-3-Clause           |
| [libxml2](https://gitlab.gnome.org/GNOME/libxml2)  | 2.9.0     | `std.parchment` (DOM XML/HTML)              | MIT                    |
| [Mbed TLS](https://github.com/Mbed-TLS/mbedtls)    | 4.2.0     | `std.seal` (MD5/SHA1/SHA256/SHA512, CRC)    | Apache-2.0             |
| [cURL](https://curl.se/libcurl/)                   | 8.21.0    | `std.precis` (cliente HTTP)                 | Tipo MIT (licencia "curl") |
| [GNU libmicrohttpd](https://www.gnu.org/software/libmicrohttpd/) | 1.0.1 | `std.precis` (servidor HTTP embebido)     | LGPL-2.1-or-later      |
| [SQLite](https://www.sqlite.org/)                  | 3.53.4    | `std.sqlite3`                               | Dominio público        |
| [raylib](https://www.raylib.com/)                  | 6.0       | `std.raylib` (también compila su driver GLFW amalgamado `rglfw.c`, zlib) | zlib |
| [WebUI](https://github.com/webui-dev/webui)        | 2.5.0-beta.3 | `std.webui` (publicación estática precompilada) | MIT              |
| [libuv](https://libuv.org/)                        | 1.52.1    | Dependencia de nivel C (aún sin enlace)     | MIT                    |
| [libyaml](https://github.com/yaml/libyaml)         | 0.2.5     | `std.yaml` (consulta de versión; el análisis sigue en C) | MIT        |
| [libcyaml](https://github.com/tlsa/libcyaml)       | 1.4.2     | Capa de esquema YAML sobre libyaml (nivel C) | ISC                   |
| [tomlc17](https://github.com/cktan/tomlc17)        | R260821   | `std.tomlum` (shim de validez TOML)         | MIT                    |
| [libzip](https://libzip.org/)                      | 1.11.3    | Soporte de zip (usado por xlsxio)           | BSD-3-Clause           |
| [libexpat](https://libexpat.github.io/)            | 2.6.4     | Analizador XML (usado por xlsxio)           | MIT                    |
| [xlsxio](https://github.com/brechtsanders/xlsxio)  | 0.2.36    | `std.xlsxio` + el escritor `std.xlsx` en Pengu puro | BSD-2-Clause    |

##### Bibliotecas incluidas de un solo archivo de cabecera (`std_c/`)

Cada archivo conserva su nombre, versión y aviso de licencia originales en su propio bloque de comentarios. Los nombres originales difieren de los nombres latinizados que se usan para evitar colisiones de espacio de nombres en C:

| Archivo en `std_c/`          | Biblioteca original                          | Licencia (de la cabecera del archivo)                            | Enlace / notas de PenguScript |
| ---------------------------- | -------------------------------------------- | --------------------------------------------------------------- | ----------------------------- |
| `imago.h`                    | stb_image v2.30                              | Dominio público (Sean Barrett)                                   | `std.imago` (carga de imágenes) |
| `scriptor.h`                 | stb_image_write v1.16                        | Dominio público                                                  | `std.scriptor` (escritura de imágenes) |
| `typis.h`                    | stb_truetype v1.26                           | Dominio público                                                  | `std.typis` (fuentes) |
| `pactum.h`                   | stb_rect_pack v1.01                          | Dominio público                                                  | `std.pactum` (empaquetado de rectángulos) |
| `datastructura.h`            | stb_ds v0.67                                 | Dominio público                                                  | `std.datastructura` (mapas hash / arrays dinámicos) |
| `perlinum.h`                 | stb_perlin v0.5                              | MIT o dominio público (Unlicense) — dual                         | `std.perlinum` (ruido) |
| `stb_image_resize2.h`        | stb_image_resize2 v2.18                      | Dominio público                                                  | `std.stb_image_resize2` |
| `stb_herringbone_wang_tile.h`| stb_herringbone_wang_tile v0.7               | Dominio público / concesión dual permisiva                       | `std.stb_herringbone_wang_tile` |
| `nanosvg.h` / `nanosvgrast.h`| [nanosvg](https://github.com/memononen/nanosvg) | zlib (© 2013–14 Mikko Mononen)                                | `std.nanosvg` / `std.nanosvgrast` (análisis + rasterizado de SVG) |
| `xxhash.h`                   | [xxHash](https://github.com/Cyan4973/xxHash) | BSD-2-Clause (© 2012–2023 Yann Collet)                           | `std.xxhash` + el envoltorio `std.celeris` |
| `uuid.h`                     | [uuid_h](https://github.com/wc-duck/uuid_h)  | Estilo zlib (© 2016– Fredrik Kihlander; parcheado para MinGW en este repositorio) | `std.uuid` |
| `minicoro.h`                 | [minicoro](https://github.com/edubart/minicoro) v0.2.0 | Dominio público (Unlicense) o MIT-0 — dual (© 2021–23 Eduardo Bart) | `std.minicoro` (corrutinas) |
| `miniaudio.h`                | [miniaudio](https://github.com/mackron/miniaudio) v0.11.25 | Dominio público o MIT-0 — dual (David Reid)          | `std.miniaudio` (subconjunto pequeño; la cabecera no se compila en el runtime) |
| `raygui.h`                   | [raygui](https://github.com/raysan5/raygui) v5.0 | zlib/libpng (© 2014–2026 Ramon Santamaria)                   | compilado para usarse con `std.raylib` |
| `rlights.h`                  | Framework de iluminación "RLG" de raylib-6   | Sin cabecera de licencia incrustada (linaje: ejemplos de raylib, zlib; cf. [bigfoot71/rlights](https://github.com/bigfoot71/rlights)) | `std.rlights` (subconjunto; no se compila en el runtime) |
| `tinyfiledialogs.h` / `.c`   | [tinyfiledialogs](http://tinyfiledialogs.sourceforge.net) v3.21.3 | zlib (© 2014–2025 Guillaume Vareille)         | `std.fenestra` (diálogos de archivo y mensaje) |
| `tinyfd_moredialogs.h` / `.c`| tinyfiledialogs "more dialogs" v3.9.0        | zlib (© 2014–2023 Guillaume Vareille)                           | parte de `std.fenestra` |
| `linmath.h`                  | [linmath.h](https://github.com/datenwolf/linmath.h) | Sin cabecera de licencia incrustada en el original (matemáticas de vectores/matrices/cuaterniones) | incluida (enlace experimental en `scratch/`) |
| `fifo_declare.h`             | Cabecera de macros FIFO / búfer circular    | LGPL-2.1-or-later (© 2003–2012 Michel Pollet)                   | incluida en `std_c/`; aún no la referencia el runtime ni std |

Las cabeceras STB anteriores son las conocidas bibliotecas de un solo archivo de Sean Barrett y colaboradores ([nothings/stb](https://github.com/nothings/stb)); varias incluyen además la concesión dual original "dominio público o MIT-0". Los archivos `wrappers_*.c`, `pengu_tomlc17.h` y los enlaces `.pengu` de `std/` son código propio de PenguScript.

---

### Licencia

PenguScript se publica bajo la **[Licencia MIT](LICENSE)** — © 2026 TuGatito. Los componentes de terceros conservan sus propias licencias como se indica arriba; consulta cada cabecera incluida y los proyectos originales para más detalles.
