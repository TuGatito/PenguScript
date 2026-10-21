<p align="center">
  <img src="vscode-extension/icons/pengu_icon.png" width="160" alt="PenguScript logo">
</p>

<h1 align="center">🐧 PenguScript</h1>

<p align="center">
  <strong>A small, explicit programming language that compiles to readable C.</strong><br>
  Simple syntax · manual memory · zero-cost generics · first-class C interop
</p>

<p align="center">
  <a href="https://github.com/TuGatito/PenguScript/releases"><img alt="Version" src="https://img.shields.io/badge/version-2.16.4-blue"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <a href="https://github.com/TuGatito/PenguScript/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/TuGatito/PenguScript/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-yellow">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey">
  <img alt="WebAssembly" src="https://img.shields.io/badge/target-WebAssembly-purple">
</p>

<p align="center">
  <a href="#english">🇬🇧 English</a> ·
  <a href="#spanish">🇪🇸 Español</a> ·
  <a href="#en-quickstart">🚀 Quick start</a> ·
  <a href="LANGUAGE.md">📖 Language reference</a>
</p>

---

> [!IMPORTANT]
> ### 💙 A personal project, growing one step at a time
>
> PenguScript is maintained by **TuGatito**, with a lot of help from **DeepSeek (AI)**.
> I don't have all the knowledge or all the time needed to build a language alone, so
> this project moves **slowly, in small releases, and often by trial and error**.
>
> Please don't expect the polish, stability or development speed of a language backed
> by a large team. What you *can* expect is honesty: every release is tested, the
> limitations are written down, and the goal is to make a **fun, understandable
> language** that keeps getting a little better.
>
> Found a bug, a rough edge or an awkward translation? Thank you for reporting it —
> that is exactly how this improves. 🐧
>
> **🇪🇸 ¿Prefieres español?** La misma nota está al principio de la
> [sección en español](#spanish).

> **Language policy.** English is the canonical language of this repository's
> documentation; the Spanish section is a **non-normative** translation of the same
> content.
>
> **Política de idioma.** El inglés es el idioma canónico de la documentación de este
> repositorio; la sección en español es una traducción **no normativa** del mismo
> contenido.

---

<a id="english"></a>
## 🇬🇧 English

<a id="en-toc"></a>
### 📑 Contents

| | |
| --- | --- |
| [🌟 What is PenguScript?](#en-what) | [🧭 Why PenguScript?](#en-why) |
| [🚀 Quick start](#en-quickstart) | [🧰 The `pengu` CLI](#en-cli) |
| [🗣️ A taste of the language](#en-language) | [🔌 C interop & bindings](#en-ffi) |
| [📚 Standard library](#en-stdlib) | [🕸️ WebAssembly](#en-wasm) |
| [⚡ Performance](#en-performance) | [🧪 Tests & CI](#en-tests) |
| [🧩 Editor support](#en-editor) | [📁 Project layout](#en-layout) |
| [🗺️ Roadmap & limits](#en-roadmap) | [📖 Documentation](#en-docs) |
| [🙏 Acknowledgements](#en-thanks) | [⚖️ License](#en-license) |

---

<a id="en-what"></a>
### 🌟 What is PenguScript?

PenguScript is a statically typed, indentation-based language that compiles to
**readable C99/C11**. It is designed to feel small and predictable: no hidden
allocations, no garbage collector, no borrow checker, and no ceremony when you
need to call a C library.

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
```

| At a glance | |
| --- | --- |
| **Syntax** | Python-like indentation, `is`/`set`, no semicolons or braces |
| **Types** | Fixed-width integers, `f32`/`f64`, strings, arrays, slices, lists, maps |
| **Memory** | Manual: `banish`, `defer`, `errdefer`; no GC, no ownership checker |
| **Abstractions** | `rune`, `omen`, `echo`, `concept`, `shard` generics — all lowered to C |
| **Interop** | C headers, structs by value, callbacks, function pointers, `pengu bind` |
| **Targets** | Linux, macOS, Windows and WebAssembly (Emscripten) |
| **Tooling** | One CLI, Language Server, formatter, docs generator and test runner |

<a id="en-why"></a>
### 🧭 Why PenguScript?

- 🪶 **Readable by default.** The syntax is deliberately quiet. A `.pengu` file
  should read like pseudocode that happens to compile.
- 🧠 **Explicit over clever.** Memory is released with `banish`, errors are values
  (`maybe` / `result`), and the compiler does not invent hidden work.
- 🧩 **C is a feature, not a compromise.** Include a header, link a library, bind a
  callback, generate a whole binding with `pengu bind`.
- 🪄 **Zero-cost abstractions.** Generics are monomorphized, concepts are checked
  at compile time, and there are no vtables or boxing by default.
- 🛠️ **One toolchain.** `pengu init`, `build`, `run`, `test`, `check`, `fmt`,
  `doc`, `bind`, `lsp` — the same binary for the whole workflow.
- 🐧 **Built for fun.** Runes, weaves, omens and shards exist because programming
  should still be enjoyable. The language takes the work seriously, not itself.

> PenguScript is not trying to replace Rust, Go or Zig. It is trying to be a
> comfortable bridge between readable code and the C ecosystem — and a pleasant
> place to learn how a compiler works.

<a id="en-quickstart"></a>
### 🚀 Quick start

#### Requirements

- **Python 3.11+** (3.10 also works; `requirements.txt` installs the `tomli`
  backport automatically there).
- A **C compiler** (`gcc` or `clang`) and a static archiver (`ar` / `llvm-ar`) on
  your `PATH`. On Windows, use the MinGW-w64 `gcc`.
- **Node.js 18+** only for the VS Code extension and for running WebAssembly
  builds headlessly.
- Optional: the **Emscripten SDK** (`emcc` + `emar`) for WebAssembly, the
  **libcurl development headers** if your program imports `std.petitio`, and
  **CMake + Ninja** for the release-packaging path.

#### Option A — use a release

Download the archive for your platform from
[**Releases**](https://github.com/TuGatito/PenguScript/releases), unpack it and run
the bundled executable:

```bash
# Linux / macOS (the archive name depends on your platform)
tar xzf pengu-linux-x64.tar.gz
./pengu -V

# Windows: unzip, then
pengu.exe -V
```

#### Option B — build from source

```bash
git clone https://github.com/TuGatito/PenguScript.git
cd PenguScript

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build the C runtime into build/lib
python build_runtime.py

# Confirm the toolchain works
python pengu_project.py -V
```

> In a source checkout the CLI is `pengu_project.py`; in a release it is the
> `pengu` / `pengu.exe` executable. The rest of this document uses `pengu` for
> brevity.

#### Hello, world

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
```

```bash
# From a source checkout
python pengu_project.py run hello.pengu

# From a release
pengu run hello.pengu
```

`pengu run` caches the linked binary by source content, so the second run usually
starts in a fraction of a second. See [Performance](#en-performance).

<a id="en-cli"></a>
### 🧰 The `pengu` CLI

The core cycle is `init` → `build` → `run` / `test` → `check` → `fmt` →
`doc` / `bind` / `lsp`.

#### Create and build

| Command | What it does |
| --- | --- |
| `init` | Create a project (`--type exe\|c\|obj\|static\|shared`, `--template exe\|cli\|pengu-lib\|cbind`, `--format toml\|yaml`, `--force`). |
| `new` | Template-first spelling of `init` (`pengu new cbind pengu_raylib`). |
| `build` | Compile the project (`--profile release`, `--cc`, `-D`, `--target`, `--verbose`). |
| `run` | Build and run the project, or run a standalone `.pengu` script. |
| `test` | Run the project's integrated `test` blocks (`--json`, `--watch`, `--target`). |
| `check` | Parse and type-check every module without generating code. CI-friendly. |
| `fmt` | Format files or directories (`--check`, `--tabs`, `--indent`). |
| `clean` | Remove the build directory and generated artifacts. |
| `doc` | Generate a Markdown API reference from `#` / `##` doc comments. |
| `bind` | Generate a `.d.pengu` declaration file from a C header. |
| `assets` | Generate or inspect embedded asset modules (`--list`, `--force`). |
| `lsp` | Launch the Language Server (stdio by default; `--tcp` also supported). |

#### Dependencies

| Command | What it does |
| --- | --- |
| `add` | Install a dependency or binding from Git or a local folder into `lib/<name>/`. |
| `remove` | Remove an installed dependency and its manifest entry. |
| `upgrade` | Upgrade one dependency (pull, or check out a tag). |
| `update` | Pull and rebuild every configured dependency. |
| `tree` | Show the resolved dependency graph. |
| `metadata` | Print machine-readable project metadata as JSON. |
| `verify` | Verify installed dependencies against `pengu.lock`. |
| `vendor` | Snapshot dependencies into `vendor/` for offline builds. |

`add --trust` runs the dependency's build script; `--rebuild` forces it and
`--no-build` skips it. Since 2.16, the preferred build script is **`build.pengu`**
— ordinary PenguScript, no Python required.

#### Diagnose and optimise

| Command | What it does |
| --- | --- |
| `doctor` | Report toolchain health: compiler, TinyCC, runtime, caches and `std/`. |
| `time` | Run a script and print per-phase timings. |
| `benchmark` | Run the reproducible benchmark suite from `benches/`. |
| `expand` | Print the generated `bundle.c` of a script to stdout. |
| `eval` | Evaluate a one-line PenguScript expression. |
| `watch` | Re-run a script whenever it or its imports change. |
| `gc` | Garbage-collect the global caches. |
| `selftest` | Run the compiler's own test suite (source checkout only). |

```bash
pengu init my_app --template cli
cd my_app
pengu build --profile release
pengu run
pengu test
pengu check
pengu fmt src/ tests/
pengu doc -o docs/api/
```

Projects are configured with `pengu.toml` or `pengu.yaml` (if both exist,
`pengu.toml` wins): entry point, output type and name, include/library paths,
per-profile flags, compiler selection and cross-compilation target. Bounds
checking is emitted in **every** profile; `release` adds `-O3` but never trades
memory safety for speed. See [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md).

<a id="en-language"></a>
### 🗣️ A taste of the language

```pengu
import std.spark

const MAX_SPEED as float is 120.0

rune Vehicle:
    model as string
    speed as float

enchanting Vehicle:
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

- **Declarations** — `var` (mutable) / `let` (immutable) locals, top-level `const`,
  and `weave name with arg as T into R` functions. Assign with `is`, mutate with
  `set`.
- **Types** — `rune` structs, `omen` enums with payloads, `echo` C unions,
  `maybe T` / `result of T to E`, fixed-size `array of T`, `slice of T`,
  `list of T` and `map of K to V`.
- **Pattern matching** — `judge ... when ...`, with exhaustiveness checked at
  compile time.
- **Generics** — `shard T` parameters, `where T: Concept` bounds, `derive` for
  automatic concept implementations, and `donum T` for zero values.
- **Memory** — `banish` releases now; `defer banish` / `errdefer banish` release
  at scope exit (LIFO). Nothing is freed behind your back.
- **Compile time** — `when`, `defined(...)`, `-D name=value`, `static var` state,
  and `when main:` for files that are both a module and a script.
- **C interop** — `include`, `link`, `declare`, opaque handles, `sigil of`
  (address-of), `essence of` (dereference), and callbacks that decay to C
  function pointers.

#### 🧠 Manual memory, on purpose

PenguScript takes the Zig / Odin / Nelua route: the compiler refuses to guess
when a value dies, because a wrong guess is either a silent leak or a
use-after-free.

```pengu
weave main into int:
    var name is "Pengu"
    defer banish name          # release at scope exit
    calling spark.println with name
    return 0
```

`banish x` frees what `x` owns according to its static type and is a safe no-op
on literals and non-owning views. Opt into a generated destructor per type with
`derive Nexus`.

#### 🪄 Generics without the ceremony

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc
```

Each instantiation is monomorphized to a plain C function. There are no vtables,
no boxing and no runtime type information. See
[LANGUAGE.md §11](LANGUAGE.md#11-generics).

<a id="en-ffi"></a>
### 🔌 C interop & bindings

C is part of the language, not an escape hatch. A `.d.pengu` file describes the
boundary:

```pengu
# raylib.d.pengu (excerpt)
include "raylib.h"
link "raylib"

declare InitWindow with width as int, height as int, title as ref to char into void
```

Then import it and call it like any other module:

```pengu
import raylib

weave main into int:
    calling raylib.InitWindow with 800, 600, "Hello from PenguScript"
    return 0
```

`pengu bind include/raylib.h --prefix raylib_ --links raylib` generates the
declarations automatically: structs become `rune`, unions become `echo`, enums
become `omen`, functions become `declare`, and callbacks become function
pointers.

Reusable packages come in two flavours:

- **Pure PenguScript libraries** — `pengu init my_lib --template pengu-lib`
- **C bindings** — `pengu init pengu_raylib --template cbind`

Both use `build.pengu` for native build steps and install with
`pengu add <url> --trust`. Bindings to raylib, SQLite, webui, miniaudio and more
live in satellite repositories — see
[docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md) and
[docs/BINDINGS.md](docs/BINDINGS.md).

<a id="en-stdlib"></a>
### 📚 Standard library

`std/` ships **40 modules**: 34 written entirely in PenguScript, 4 wrappers over
small C engines, and 2 general bridges. Every module has a generated API
reference in [docs/api/](docs/api/README.md).

#### 🧱 Core, files & OS

| Module | What it gives you |
| --- | --- |
| [`spark`](docs/api/spark.md) | Console I/O, formatted output, typed input, ranges and math helpers. |
| [`archivum`](docs/api/archivum.md) | Files, binary I/O, directories and streaming. |
| [`compass`](docs/api/compass.md) | Cross-platform paths and pattern matching. |
| [`chronicle`](docs/api/chronicle.md) | Dates, high-resolution clocks, timers and duration parsing. |
| [`rites`](docs/api/rites.md) | Processes, environment variables and system information. |
| [`whisper`](docs/api/whisper.md) | Structured, leveled logging and the `Logger` rune. |

#### 📝 Text & data

| Module | What it gives you |
| --- | --- |
| [`scrolls`](docs/api/scrolls.md) | String algorithms, metrics, casing, splitting and three-way ordering. |
| [`builder`](docs/api/builder.md) | `StringBuilder` with amortised-O(1) append and explicit ownership. |
| [`cipher`](docs/api/cipher.md) | Base64/32/85, Hex, Z85, Base58, URL encoding, CRC-32 and legacy flat JSON. |
| [`json`](docs/api/json.md) | Strict RFC 8259 parser/serializer, ordered DOM, JSON Pointer and schema subset. |
| [`jsonrpc`](docs/api/jsonrpc.md) | JSON-RPC 2.0 requests, batches and LSP `Content-Length` framing. |
| [`ledger`](docs/api/ledger.md) | CSV/TSV parsing, generation and tabular data helpers. |
| [`sourcemap`](docs/api/sourcemap.md) | Byte offsets ↔ 1-indexed line/column, CRLF-aware. |
| [`diagnostic`](docs/api/diagnostic.md) | Spans, labels, Rust-style ANSI rendering and LSP-compatible JSON. |

#### 🧰 Collections & algorithms

| Module | What it gives you |
| --- | --- |
| [`atlas`](docs/api/atlas.md) | Hash maps, bulk accessors, combination and filters. |
| [`coven`](docs/api/coven.md) | `SetString` / `SetInt` collections and set algebra. |
| [`tally`](docs/api/tally.md) | Functional list operations, reductions, insertion sort and statistics. |
| [`loom`](docs/api/loom.md) | Sequence pipelines, windows, folds, combinations and generic algorithms. |
| [`bitset`](docs/api/bitset.md) | Fixed-length dense bit sets with set algebra and popcount. |
| [`arena`](docs/api/arena.md) | Bump allocator for temporary object graphs. |
| [`memoria`](docs/api/memoria.md) | Manual heap primitives: `alloc`, `resize_array`, `copy`, `fill`, `zero`. |
| [`oracle`](docs/api/oracle.md) | `Maybe` / `Result` containers and interoperability helpers. |

#### 🔢 Math, primitives & randomness

| Module | What it gives you |
| --- | --- |
| [`arithmancy`](docs/api/arithmancy.md) | Advanced math. |
| [`fractio`](docs/api/fractio.md) | Floating-point methods, IEEE 754 classification and `libm` functions. |
| [`integrum`](docs/api/integrum.md) | Integer methods: parity, primality, bits, `gcd`/`lcm`, bases. |
| [`littera`](docs/api/littera.md) | `char` methods and ASCII classification, with no locale dependency. |
| [`logica`](docs/api/logica.md) | `bool` methods such as `toggle`, `xor`, `nand` and `implies`. |
| [`numerus`](docs/api/numerus.md) | Universal numeric methods over every primitive, monomorphized. |
| [`lot`](docs/api/lot.md) | PRNG, distributions, sampling, shuffling and random strings. |
| [`ward`](docs/api/ward.md) | Invariants, assertions and generic test helpers. |

#### 🧵 Concurrency, FFI & the web

| Module | What it gives you |
| --- | --- |
| [`filum`](docs/api/filum.md) | Threads, typed channels, mutexes and atomics. |
| [`ffi`](docs/api/ffi.md) | General C bridge: slices, function pointers and opaque handles. |
| [`web`](docs/api/web.md) | Emscripten/JS bridge: console, main loop, timers, `eval_js`, `IS_WASM`. |

#### 🌐 HTTP, compression & text engines

| Module | What it gives you |
| --- | --- |
| [`petitio`](docs/api/petitio.md) | HTTP/1.1 + HTTP/2 client over libcurl: streaming, cookies, auth, proxies. |
| [`compressus`](docs/api/compressus.md) | gzip, zlib and raw deflate over the vendored miniz. |
| [`lingua`](docs/api/lingua.md) | UTF-8 codepoints over sheredom's `utf8.h`. |
| [`regulus`](docs/api/regulus.md) | Small explicit regex over kokke's `tiny-regex-c`. |

#### 🛠️ CLI, testing & callbacks

| Module | What it gives you |
| --- | --- |
| [`invoke`](docs/api/invoke.md) | CLI parsing, subcommands, typed flags and typo suggestions. |
| [`trial`](docs/api/trial.md) | Unit-testing helpers used by integrated `test` blocks. |
| [`functor`](docs/api/functor.md) | `Fn0`–`Fn3` thick functions: a callback plus explicit context, no closures. |

The four C wrappers are **smart-linked**: `std.petitio` links libcurl only when
imported, `std.compressus` links miniz only when imported, and so on. A program
that imports none of them links only the core runtime.

<a id="en-wasm"></a>
### 🕸️ WebAssembly

The same `.pengu` source can build for the browser (or headless Node) through
Emscripten, with no source changes:

```bash
# One-time setup
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk && ./emsdk install latest && ./emsdk activate latest && source ./emsdk_env.sh

# Runtime for the wasm target (kept separate from the host build)
python build_runtime.py --target emscripten

# Build and run
pengu build --target wasm32-unknown-emscripten
pengu run   --target wasm32-unknown-emscripten
pengu run   --target wasm script.pengu
```

An `exe` build produces `app.html` + `app.js` + `app.wasm`; `node build/app.js`
runs it headlessly. Threads from `std.filum` become real Web Workers, and
`std.web` exposes the JS console, the main loop, timers and `eval_js`.

**WASI is not supported** — `--target wasm32-wasi` is recognised and refused.
See [docs/WASM.md](docs/WASM.md) for the full guide, limitations and
troubleshooting.

<a id="en-performance"></a>
### ⚡ Performance

`pengu run script.pengu` is meant to feel like running a script, not building a
project. Five independent optimisations, each with a documented off-switch:

| Optimisation | What it does | Disable with |
| --- | --- | --- |
| Parser-table cache | Serializes Lark's LALR tables (~3.9 s → ~0.25 s per process) | `PENGU_CACHE=0` |
| Binary cache | Reuses the linked binary keyed by the content hash of the script and imports | `--no-cache`, `--ephemeral` |
| Dead-code elimination | Emits only the `std/` / `lib/` weaves reachable from `main` / tests | `--no-dce`, `PENGU_NO_DCE=1` |
| TinyCC | Bundled in releases; ~19 ms to compile a bundle vs ~400 ms for gcc | `PENGU_NO_TCC=1`, `PENGU_DEV_CC=gcc` |
| pkg-config memoization | One probe per package per process instead of ~12 spawns | always on |

Measured on the reference machine (Linux x86_64, Python 3.14.7, gcc 16.2.1,
TCC 0.9.28rc, best of 5):

| Scenario | Before | After |
| --- | ---: | ---: |
| `pengu run hello.pengu` — first run, tables cached | 3.88 s | **0.85 s** (gcc) / **0.66 s** (TCC) |
| `pengu run hello.pengu` — second run (cache hit) | 3.88 s | **0.19 s** |
| `bundle.c` for a script using only `spark.println` | 432 lines / 19.4 KB | **65 lines / 2.3 KB** (−84%) |
| LALR table construction per process | 3.9 s | **0.25 s** (cached) |
| 10M-iteration loop (run phase) | ~33 ms | 33 ms |

```bash
pengu doctor                 # compiler, TCC, runtime and cache status
pengu time hello.pengu       # per-phase breakdown
pengu benchmark              # reproducible benchmarks from benches/
python scripts/bench.sh      # reproduce the table above
```

Nothing is written to the project's `build/` by default. If TinyCC fails, `pengu
run` retries once with the configured compiler and warns instead of failing. See
[docs/PERFORMANCE.md](docs/PERFORMANCE.md) and [BENCHMARKS.md](BENCHMARKS.md).

<a id="en-tests"></a>
### 🧪 Tests & CI

The compiler has a large pytest suite plus compile-and-run corpora. The default
run is parallel and is expected to stay under a few minutes:

```bash
pengu selftest --smoke       # fast tier, no full rebuild
pengu selftest --affected    # only what your changes can affect
pengu selftest               # full default suite
pytest tests/                # same suite through pytest
```

GitHub Actions builds and tests on **Linux, Windows and macOS**, runs the
compliance and conformance corpora, cross-builds the WebAssembly target, packages
the VS Code extension, and publishes a release when a `v*` tag is created.
Sanitizers, fuzzing and benchmarks run in the nightly workflow. See
[AGENT_TESTING.md](AGENT_TESTING.md) before adding tests.

<a id="en-editor"></a>
### 🧩 Editor support

The official VS Code extension lives in
[`vscode-extension/`](vscode-extension/README.md). It provides:

- TextMate syntax highlighting
- LSP diagnostics with `help:` / `note:` notes and caret spans
- Type and byte-size hovers, module-scoped completion and go-to-definition
- Formatting and code actions
- Build / Run / Clean / Init commands

Install the `pengus-<version>.vsix` from a release, or build it yourself:

```bash
cd vscode-extension
npm install
npm run package            # -> pengus-<version>.vsix
```

The Language Server itself is editor-agnostic: `pengu lsp` speaks stdio by
default and can also listen on TCP. See
[LANGUAGE.md §20.10](LANGUAGE.md#2010-language-server-protocol-pengu-lsp).

<a id="en-layout"></a>
### 📁 Project layout

```text
PenguScript/
├── pengu_parser/          # Compiler: grammar, symbols, type checker/inference,
│                          #   comptime, C99/C11 codegen and diagnostics
├── pengu_lsp/             # Language Server (pygls)
├── pengu_project.py       # `pengu` CLI and build manager
├── pengu_bind.py          # `pengu bind`: C header -> .d.pengu
├── pengu_doc.py           # `pengu doc`: Markdown API reference generator
├── pengu_runtime.h        # Public API of the C runtime
├── build_runtime.py       # Builds the C runtime into build/lib
├── make_release.py        # Packages the standalone release + VSIX
├── std/                   # 40 standard-library modules
├── std_c/                 # Vendored C engines (utf8.h, tiny-regex-c, miniz, …)
├── docs/                  # Guides, architecture notes and generated API docs
├── examples/              # Small runnable examples
├── benches/               # Benchmark programs and harness
├── tests/                 # pytest suite + conformance corpus
├── vscode-extension/      # VS Code extension (grammar, LSP client, commands)
├── LANGUAGE.md            # Language reference (English)
├── LANGUAGE_Spanish.md    # Language reference (Spanish)
├── CHEATSHEET.md          # Syntax and C-translation cheat sheet
├── BENCHMARKS.md          # Published measurements
├── CHANGELOG.md           # Release history
└── VERSION                # Single source of truth for the version
```

Generated output lives in `build/` and is gitignored. Release artifacts are
produced in `pengucc_build/` by `python make_release.py`.

<a id="en-roadmap"></a>
### 🗺️ Roadmap & limits

PenguScript 2.x aims to be **additive**: existing programs should keep compiling,
and deprecations follow a written policy ([docs/DEPRECATIONS.md](docs/DEPRECATIONS.md)).
That said, this is a small project, so please evaluate it for your own use case
instead of assuming production-grade maturity.

**Deliberately not there yet**

- ❌ Borrow checking and automatic ownership (memory is manual by design)
- ❌ `async` / `await`
- ❌ Closures with capture (use `std.functor` thick functions instead)
- ❌ AST macros, reflection and dynamic dispatch
- ❌ Associated types
- ❌ `pengu repl`
- ❌ WASI (`wasm32-wasi` is refused; Emscripten is the only wasm target)

**Known rough edges**

- Pointer arithmetic (`p + 1`) is not supported; use indexing (`p at i`) or
  `std.ffi.slice_from_ptr`.
- `--strict-c99` is **not functional** for programs that import `std`. Do not use
  it as a CI portability gate.
- Some third-party C headers need extra flags or small hand edits in `pengu bind`.
  The CLI has no `-I` / `-L` / `-l` flags; use `pengu.yaml` / `pengu.toml`.
- The API is still young. Read the [CHANGELOG.md](CHANGELOG.md) before upgrading.

The live roadmap is the [issue tracker](https://github.com/TuGatito/PenguScript/issues).
Feature requests and honest bug reports are welcome — especially small,
reproducible ones.

<a id="en-docs"></a>
### 📖 Documentation

| Document | What it covers |
| --- | --- |
| [LANGUAGE.md](LANGUAGE.md) / [LANGUAGE_Spanish.md](LANGUAGE_Spanish.md) | Complete language reference, stdlib and diagnostics. |
| [CHEATSHEET.md](CHEATSHEET.md) | Syntax, keywords and C-translation reference. |
| [PenguScriptGuideEnglish.md](PenguScriptGuideEnglish.md) / [PenguScriptGuideSpanish.md](PenguScriptGuideSpanish.md) | Idiomatic style guide. |
| [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md) | CLI, project configuration and build system. |
| [docs/BINDINGS.md](docs/BINDINGS.md) | Pure libraries, C bindings and `link` propagation. |
| [docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md) | Satellite C-binding repositories. |
| [docs/WASM.md](docs/WASM.md) | WebAssembly/Emscripten target. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Compiler pipeline end to end. |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Performance design, numbers and optimisations. |
| [docs/ABI.md](docs/ABI.md) | Runtime ABI policy and versioning. |
| [docs/api/](docs/api/README.md) | Generated API reference for all 40 std modules. |
| [docs/README.md](docs/README.md) | Index of every supplementary document. |
| [BENCHMARKS.md](BENCHMARKS.md) | Published build/run/artifact measurements. |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute and report issues. |
| [SECURITY.md](SECURITY.md) | Security model and reporting. |
| [AGENT_TESTING.md](AGENT_TESTING.md) | Test-suite rules and timing budget. |
| [vscode-extension/README.md](vscode-extension/README.md) | Extension features, settings and installation. |

Quick links: [Language reference](LANGUAGE.md) ·
[Cheat sheet](CHEATSHEET.md) · [API docs](docs/api/README.md) ·
[Examples](examples/) · [Releases](https://github.com/TuGatito/PenguScript/releases).

<a id="en-thanks"></a>
### 🙏 Acknowledgements

PenguScript stands on the shoulders of many excellent open-source projects.
Thank you to their authors and contributors. License names are as published by
each upstream project.

#### 🐍 Python toolchain

| Project | Used for | License |
| --- | --- | --- |
| [Lark](https://github.com/lark-parser/lark) | Grammar and parsing | MIT |
| [PyYAML](https://pyyaml.org/) | `pengu.yaml` configuration | MIT |
| [pygls](https://github.com/openlawlibrary/pygls) | Language Server framework | Apache-2.0 |
| [lsprotocol](https://github.com/microsoft/lsprotocol) | LSP protocol types | MIT |
| [pycparser](https://github.com/eliben/pycparser) | C-header parsing in `pengu bind` | BSD-3-Clause |
| [PyInstaller](https://pyinstaller.org/) | Standalone `pengu` executable | GPL-2.0-or-later (with bootloader exception) |
| [pytest](https://pytest.org/) | Test runner | MIT |
| [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) | Parallel test execution | MIT |
| [pytest-timeout](https://github.com/pytest-dev/pytest-timeout) | Per-test hang guard | MIT |
| [pytest-cov](https://github.com/pytest-dev/pytest-cov) / [coverage](https://coverage.readthedocs.io/) | Coverage measurement | MIT / Apache-2.0 |
| [Hypothesis](https://hypothesis.readthedocs.io/) | Property-based tests | MPL-2.0 |
| [ruff](https://docs.astral.sh/ruff/) | Static-analysis gate | MIT |
| [tomli](https://github.com/hukkin/tomli) | `tomllib` backport for Python < 3.11 | MIT |

#### 🧩 Vendored C engines (`std_c/`)

| Project | Author | Used by | License |
| --- | --- | --- | --- |
| [`utf8.h`](https://github.com/sheredom/utf8.h) | **sheredom** | `std.lingua` | Public domain / [Unlicense](https://unlicense.org/) |
| [`tiny-regex-c`](https://github.com/kokke/tiny-regex-c) | **kokke** | `std.regulus` | Public domain |
| [`miniz`](https://github.com/richgel999/miniz) | **Rich Geldreich** | `std.compressus` | Public domain / [Unlicense](https://unlicense.org/) |
| [`libcurl`](https://curl.se/libcurl/) | **Daniel Stenberg and contributors** | `std.petitio` | [curl license](https://curl.se/docs/copyright.html) (MIT-like) |

These are small, focused, well-tested engines. Using them keeps the wrappers
thin and the behaviour predictable instead of reimplementing UTF-8, regex,
deflate or HTTP from scratch.

#### 🛠️ Build & tooling

| Project | Used for | License |
| --- | --- | --- |
| [TinyCC](https://bellard.org/tcc/) | Fast compile-and-run backend, bundled in releases | LGPL-2.1 |
| [Emscripten](https://emscripten.org/) | WebAssembly target | MIT |
| [GCC](https://gcc.gnu.org/) / [Clang](https://clang.llvm.org/) | Reference C compilers | GPL-3.0+ with runtime exception / Apache-2.0 with LLVM exceptions |
| [Node.js](https://nodejs.org/) | Headless wasm runs and VS Code tooling | MIT-style |
| [VS Code Language Client](https://github.com/microsoft/vscode-languageserver-node) | LSP client in the extension | MIT |
| [esbuild](https://esbuild.github.io/) | Extension bundling | MIT |
| [TypeScript](https://www.typescriptlang.org/) | Extension source language | Apache-2.0 |

**Special thanks** to sheredom, kokke, Rich Geldreich, Daniel Stenberg and the
curl contributors, the Lark and pygls teams, the Emscripten and TinyCC
communities, and everyone who has reported a bug or sent a kind word. 💙

And, of course, **thank you to DeepSeek** for helping me build, test and write
this project — and for making a one-person language a little more possible. 🤖

<a id="en-license"></a>
### ⚖️ License

PenguScript is released under the **[MIT License](LICENSE)** — © 2026 TuGatito.
Satellite modules installed with `pengu add` are separate projects and keep their
own licenses.

---

<a id="spanish"></a>
## 🇪🇸 Español

> [!IMPORTANT]
> ### 💙 Un proyecto personal, creciendo paso a paso
>
> PenguScript lo mantiene **TuGatito**, con mucha ayuda de **DeepSeek (IA)**. No
> tengo todos los conocimientos ni todo el tiempo para construir un lenguaje yo
> solo, así que este proyecto avanza **despacio, en releases pequeñas y, a
> menudo, por prueba y error**.
>
> No esperes el pulido, la estabilidad ni la velocidad de desarrollo de un
> lenguaje respaldado por un equipo grande. Lo que *sí* puedes esperar es
> honestidad: cada release se prueba, las limitaciones están escritas y el
> objetivo es hacer un **lenguaje divertido y comprensible** que mejore poco a
> poco.
>
> ¿Encontraste un bug, una arista o una traducción rara? Gracias por reportarlo:
> así es exactamente como esto mejora. 🐧

<a id="es-toc"></a>
### 📑 Contenido

| | |
| --- | --- |
| [🌟 ¿Qué es PenguScript?](#es-que) | [🧭 ¿Por qué PenguScript?](#es-porque) |
| [🚀 Inicio rápido](#es-inicio) | [🧰 La CLI `pengu`](#es-cli) |
| [🗣️ Un vistazo al lenguaje](#es-lenguaje) | [🔌 Interoperabilidad con C](#es-ffi) |
| [📚 Biblioteca estándar](#es-stdlib) | [🕸️ WebAssembly](#es-wasm) |
| [⚡ Rendimiento](#es-rendimiento) | [🧪 Pruebas y CI](#es-pruebas) |
| [🧩 Soporte de editor](#es-editor) | [📁 Estructura del proyecto](#es-estructura) |
| [🗺️ Hoja de ruta y límites](#es-roadmap) | [📖 Documentación](#es-docs) |
| [🙏 Agradecimientos](#es-gracias) | [⚖️ Licencia](#es-licencia) |

---

<a id="es-que"></a>
### 🌟 ¿Qué es PenguScript?

PenguScript es un lenguaje tipado estáticamente y basado en indentación que
compila a **C99/C11 legible**. Está pensado para sentirse pequeño y predecible:
sin reservas ocultas de memoria, sin recolector de basura, sin borrow checker y
sin ceremonia cuando necesitas llamar a una biblioteca de C.

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
```

| De un vistazo | |
| --- | --- |
| **Sintaxis** | Indentación tipo Python, `is`/`set`, sin punto y coma ni llaves |
| **Tipos** | Enteros de ancho fijo, `f32`/`f64`, cadenas, arrays, slices, listas y mapas |
| **Memoria** | Manual: `banish`, `defer`, `errdefer`; sin GC ni ownership |
| **Abstracciones** | `rune`, `omen`, `echo`, `concept`, genéricos `shard` — todo baja a C |
| **Interoperabilidad** | Cabeceras C, structs por valor, callbacks, punteros a función, `pengu bind` |
| **Objetivos** | Linux, macOS, Windows y WebAssembly (Emscripten) |
| **Herramientas** | Una CLI, Language Server, formateador, generador de docs y runner de tests |

<a id="es-porque"></a>
### 🧭 ¿Por qué PenguScript?

- 🪶 **Legible por defecto.** La sintaxis es deliberadamente tranquila. Un archivo
  `.pengu` debería leerse como pseudocódigo que, además, compila.
- 🧠 **Explícito antes que ingenioso.** La memoria se libera con `banish`, los
  errores son valores (`maybe` / `result`) y el compilador no inventa trabajo
  oculto.
- 🧩 **C es una característica, no un compromiso.** Incluye una cabecera, enlaza
  una biblioteca, conecta un callback y genera un binding completo con
  `pengu bind`.
- 🪄 **Abstracciones de coste cero.** Los genéricos se monomorfizan, los conceptos
  se comprueban en compilación y no hay vtables ni boxing por defecto.
- 🛠️ **Una sola caja de herramientas.** `pengu init`, `build`, `run`, `test`,
  `check`, `fmt`, `doc`, `bind`, `lsp` — el mismo binario para todo el flujo.
- 🐧 **Hecho para divertirse.** Runes, weaves, omens y shards existen porque
  programar también debería ser entretenido. El lenguaje se toma el trabajo en
  serio, no a sí mismo.

> PenguScript no intenta reemplazar a Rust, Go o Zig. Intenta ser un puente
> cómodo entre el código legible y el ecosistema de C — y un lugar agradable para
> aprender cómo funciona un compilador.

<a id="es-inicio"></a>
### 🚀 Inicio rápido

#### Requisitos

- **Python 3.11+** (3.10 también funciona; allí `requirements.txt` instala
  automáticamente el backport `tomli`).
- Un **compilador de C** (`gcc` o `clang`) y un archivador estático (`ar` /
  `llvm-ar`) en tu `PATH`. En Windows, usa el `gcc` de MinGW-w64.
- **Node.js 18+** solo para la extensión de VS Code y para ejecutar compilaciones
  WebAssembly sin navegador.
- Opcional: el **SDK de Emscripten** (`emcc` + `emar`) para WebAssembly, las
  **cabeceras de desarrollo de libcurl** si tu programa importa `std.petitio`, y
  **CMake + Ninja** para el empaquetado de releases.

#### Opción A — usar una release

Descarga el archivo de tu plataforma desde
[**Releases**](https://github.com/TuGatito/PenguScript/releases), descomprímelo y
ejecuta el binario incluido:

```bash
# Linux / macOS (el nombre del archivo depende de tu plataforma)
tar xzf pengu-linux-x64.tar.gz
./pengu -V

# Windows: descomprime el .zip y ejecuta
pengu.exe -V
```

#### Opción B — compilar desde el código fuente

```bash
git clone https://github.com/TuGatito/PenguScript.git
cd PenguScript

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Compila el runtime de C en build/lib
python build_runtime.py

# Comprueba que la cadena de herramientas funciona
python pengu_project.py -V
```

> En una copia del código fuente la CLI es `pengu_project.py`; en una release es
> el ejecutable `pengu` / `pengu.exe`. El resto del documento usa `pengu` por
> brevedad.

#### Hola, mundo

```pengu
import std.spark

weave main into int:
    calling spark.println with "Hello, world!"
    return 0
```

```bash
# Desde una copia del código fuente
python pengu_project.py run hello.pengu

# Desde una release
pengu run hello.pengu
```

`pengu run` cachea el binario enlazado según el contenido del fuente, así que la
segunda ejecución suele arrancar en una fracción de segundo. Consulta
[Rendimiento](#es-rendimiento).

<a id="es-cli"></a>
### 🧰 La CLI `pengu`

El ciclo principal es `init` → `build` → `run` / `test` → `check` → `fmt` →
`doc` / `bind` / `lsp`.

#### Crear y compilar

| Comando | Qué hace |
| --- | --- |
| `init` | Crea un proyecto (`--type exe\|c\|obj\|static\|shared`, `--template exe\|cli\|pengu-lib\|cbind`, `--format toml\|yaml`, `--force`). |
| `new` | Forma de `init` con la plantilla primero (`pengu new cbind pengu_raylib`). |
| `build` | Compila el proyecto (`--profile release`, `--cc`, `-D`, `--target`, `--verbose`). |
| `run` | Compila y ejecuta el proyecto, o ejecuta un archivo `.pengu` suelto como script. |
| `test` | Ejecuta los bloques `test` integrados del proyecto (`--json`, `--watch`, `--target`). |
| `check` | Analiza y verifica tipos de todos los módulos sin generar código. Ideal para CI. |
| `fmt` | Formatea archivos o directorios (`--check`, `--tabs`, `--indent`). |
| `clean` | Elimina el directorio de compilación y los artefactos generados. |
| `doc` | Genera una referencia de API en Markdown desde comentarios `#` / `##`. |
| `bind` | Genera un archivo de declaraciones `.d.pengu` desde una cabecera de C. |
| `assets` | Genera o inspecciona módulos de recursos embebidos (`--list`, `--force`). |
| `lsp` | Inicia el Language Server (stdio por defecto; también `--tcp`). |

#### Dependencias

| Comando | Qué hace |
| --- | --- |
| `add` | Instala una dependencia o binding desde Git o una carpeta local en `lib/<name>/`. |
| `remove` | Elimina una dependencia instalada y su entrada del manifiesto. |
| `upgrade` | Actualiza una dependencia (pull o checkout de una etiqueta). |
| `update` | Actualiza y recompila todas las dependencias configuradas. |
| `tree` | Muestra el grafo de dependencias resuelto. |
| `metadata` | Imprime metadatos del proyecto en JSON. |
| `verify` | Verifica las dependencias instaladas contra `pengu.lock`. |
| `vendor` | Copia las dependencias a `vendor/` para compilaciones sin conexión. |

`add --trust` ejecuta el script de construcción de la dependencia; `--rebuild` lo
fuerza y `--no-build` lo omite. Desde la 2.16, el script preferido es
**`build.pengu`** — PenguScript normal, sin Python.

#### Diagnosticar y optimizar

| Comando | Qué hace |
| --- | --- |
| `doctor` | Informa del estado de la cadena de herramientas: compilador, TinyCC, runtime, cachés y `std/`. |
| `time` | Ejecuta un script y muestra los tiempos por fase. |
| `benchmark` | Ejecuta la suite reproducible de `benches/`. |
| `expand` | Imprime el `bundle.c` generado de un script. |
| `eval` | Evalúa una expresión de PenguScript de una línea. |
| `watch` | Vuelve a ejecutar un script cuando cambian él o sus imports. |
| `gc` | Limpia las cachés globales. |
| `selftest` | Ejecuta la suite del propio compilador (solo en el código fuente). |

```bash
pengu init my_app --template cli
cd my_app
pengu build --profile release
pengu run
pengu test
pengu check
pengu fmt src/ tests/
pengu doc -o docs/api/
```

Los proyectos se configuran con `pengu.toml` o `pengu.yaml` (si existen ambos,
gana `pengu.toml`): punto de entrada, tipo y nombre de salida, rutas de
include/library, flags por perfil, selección de compilador y objetivo de
compilación cruzada. La verificación de límites se emite en **todos** los
perfiles; `release` añade `-O3`, pero nunca cambia seguridad de memoria por
velocidad. Consulta [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md).

<a id="es-lenguaje"></a>
### 🗣️ Un vistazo al lenguaje

```pengu
import std.spark

const MAX_SPEED as float is 120.0

rune Vehicle:
    model as string
    speed as float

enchanting Vehicle:
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

- **Declaraciones** — locales `var` (mutables) / `let` (inmutables), `const` de
  nivel superior y funciones `weave name with arg as T into R`. Asigna con `is`,
  muta con `set`.
- **Tipos** — structs `rune`, `omen` con carga útil, uniones C `echo`,
  `maybe T` / `result of T to E`, `array of T` de tamaño fijo, `slice of T`,
  `list of T` y `map of K to V`.
- **Coincidencia de patrones** — `judge ... when ...`, con exhaustividad
  comprobada en compilación.
- **Genéricos** — parámetros `shard T`, cotas `where T: Concept`, `derive` para
  implementaciones automáticas de conceptos y `donum T` para valores cero.
- **Memoria** — `banish` libera ahora; `defer banish` / `errdefer banish` liberan
  al salir del ámbito (LIFO). Nada se libera a tus espaldas.
- **Tiempo de compilación** — `when`, `defined(...)`, `-D name=value`, estado
  `static var` y `when main:` para archivos que son módulo y script a la vez.
- **Interoperabilidad con C** — `include`, `link`, `declare`, handles opacos,
  `sigil of` (dirección) y `essence of` (desreferencia), y callbacks que decaen a
  punteros a función de C.

#### 🧠 Memoria manual, a propósito

PenguScript toma la ruta de Zig / Odin / Nelua: el compilador se niega a adivinar
cuándo muere un valor, porque una suposición equivocada es una fuga silenciosa o
un use-after-free.

```pengu
weave main into int:
    var name is "Pengu"
    defer banish name          # libera al salir del ámbito
    calling spark.println with name
    return 0
```

`banish x` libera lo que `x` posee según su tipo estático y es una operación
segura sobre literales y vistas sin posesión. Puedes optar por un destructor
generado por tipo con `derive Nexus`.

#### 🪄 Genéricos sin ceremonia

```pengu
weave sum shard T where T: Num with xs as list of T into T:
    var acc as T is donum T
    for x in xs:
        set acc is acc + x
    return acc
```

Cada instanciación se monomorfiza a una función C plana. Sin vtables, sin boxing
y sin información de tipos en tiempo de ejecución. Consulta
[LANGUAGE.md §11](LANGUAGE.md#11-generics).

<a id="es-ffi"></a>
### 🔌 Interoperabilidad con C

C es parte del lenguaje, no una salida de emergencia. Un archivo `.d.pengu`
describe la frontera:

```pengu
# raylib.d.pengu (extracto)
include "raylib.h"
link "raylib"

declare InitWindow with width as int, height as int, title as ref to char into void
```

Después lo importas y lo llamas como cualquier otro módulo:

```pengu
import raylib

weave main into int:
    calling raylib.InitWindow with 800, 600, "Hello from PenguScript"
    return 0
```

`pengu bind include/raylib.h --prefix raylib_ --links raylib` genera las
declaraciones automáticamente: los structs se convierten en `rune`, las uniones en
`echo`, los enums en `omen`, las funciones en `declare` y los callbacks en
punteros a función.

Los paquetes reutilizables vienen en dos sabores:

- **Bibliotecas puras de PenguScript** — `pengu init my_lib --template pengu-lib`
- **Bindings de C** — `pengu init pengu_raylib --template cbind`

Ambos usan `build.pengu` para los pasos nativos y se instalan con
`pengu add <url> --trust`. Los bindings de raylib, SQLite, webui, miniaudio y
otros viven en repositorios satélite — consulta
[docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md) y
[docs/BINDINGS.md](docs/BINDINGS.md).

<a id="es-stdlib"></a>
### 📚 Biblioteca estándar

`std/` incluye **40 módulos**: 34 escritos íntegramente en PenguScript, 4
wrappers sobre motores C pequeños y 2 puentes generales. Cada módulo tiene su
referencia de API generada en [docs/api/](docs/api/README.md).

#### 🧱 Núcleo, archivos y sistema

| Módulo | Qué ofrece |
| --- | --- |
| [`spark`](docs/api/spark.md) | E/S de consola, salida formateada, entrada tipada, rangos y ayudas matemáticas. |
| [`archivum`](docs/api/archivum.md) | Archivos, E/S binaria, directorios y streaming. |
| [`compass`](docs/api/compass.md) | Rutas multiplataforma y coincidencia de patrones. |
| [`chronicle`](docs/api/chronicle.md) | Fechas, relojes de alta resolución, temporizadores y análisis de duraciones. |
| [`rites`](docs/api/rites.md) | Procesos, variables de entorno e información del sistema. |
| [`whisper`](docs/api/whisper.md) | Logging estructurado por niveles y el rune `Logger`. |

#### 📝 Texto y datos

| Módulo | Qué ofrece |
| --- | --- |
| [`scrolls`](docs/api/scrolls.md) | Algoritmos de cadenas, métricas, capitalización, división y ordenación a tres bandas. |
| [`builder`](docs/api/builder.md) | `StringBuilder` con append amortizado O(1) y posesión explícita. |
| [`cipher`](docs/api/cipher.md) | Base64/32/85, Hex, Z85, Base58, URL encoding, CRC-32 y JSON plano heredado. |
| [`json`](docs/api/json.md) | Parser/serializador estricto RFC 8259, DOM ordenado, JSON Pointer y subconjunto de schema. |
| [`jsonrpc`](docs/api/jsonrpc.md) | JSON-RPC 2.0, lotes y framing `Content-Length` de LSP. |
| [`ledger`](docs/api/ledger.md) | Parseo y generación de CSV/TSV y ayudas para datos tabulares. |
| [`sourcemap`](docs/api/sourcemap.md) | Desplazamientos de byte ↔ línea/columna (1-indexado), compatible con CRLF. |
| [`diagnostic`](docs/api/diagnostic.md) | Spans, etiquetas, render ANSI estilo Rust y JSON compatible con LSP. |

#### 🧰 Colecciones y algoritmos

| Módulo | Qué ofrece |
| --- | --- |
| [`atlas`](docs/api/atlas.md) | Mapas hash, accesores masivos, combinación y filtros. |
| [`coven`](docs/api/coven.md) | Colecciones `SetString` / `SetInt` y álgebra de conjuntos. |
| [`tally`](docs/api/tally.md) | Operaciones funcionales sobre listas, reducciones, ordenación por inserción y estadísticas. |
| [`loom`](docs/api/loom.md) | Pipelines de secuencias, ventanas, folds, combinaciones y algoritmos genéricos. |
| [`bitset`](docs/api/bitset.md) | Conjuntos de bits densos de longitud fija, con álgebra y popcount. |
| [`arena`](docs/api/arena.md) | Asignador bump para grafos de objetos temporales. |
| [`memoria`](docs/api/memoria.md) | Primitivas manuales de heap: `alloc`, `resize_array`, `copy`, `fill`, `zero`. |
| [`oracle`](docs/api/oracle.md) | Contenedores `Maybe` / `Result` y ayudas de interoperabilidad. |

#### 🔢 Matemáticas, primitivos y aleatoriedad

| Módulo | Qué ofrece |
| --- | --- |
| [`arithmancy`](docs/api/arithmancy.md) | Matemáticas avanzadas. |
| [`fractio`](docs/api/fractio.md) | Métodos de flotantes, clasificación IEEE 754 y funciones de `libm`. |
| [`integrum`](docs/api/integrum.md) | Métodos de enteros: paridad, primalidad, bits, `gcd`/`lcm` y bases. |
| [`littera`](docs/api/littera.md) | Métodos de `char` y clasificación ASCII, sin dependencia de locale. |
| [`logica`](docs/api/logica.md) | Métodos de `bool` como `toggle`, `xor`, `nand` e `implies`. |
| [`numerus`](docs/api/numerus.md) | Métodos numéricos universales sobre todo primitivo, monomorfizados. |
| [`lot`](docs/api/lot.md) | PRNG, distribuciones, muestreo, barajado y cadenas aleatorias. |
| [`ward`](docs/api/ward.md) | Invariantes, aserciones y ayudas genéricas para tests. |

#### 🧵 Concurrencia, FFI y web

| Módulo | Qué ofrece |
| --- | --- |
| [`filum`](docs/api/filum.md) | Hilos, canales tipados, mutex y atómicos. |
| [`ffi`](docs/api/ffi.md) | Puente general a C: slices, punteros a función y handles opacos. |
| [`web`](docs/api/web.md) | Puente Emscripten/JS: consola, bucle principal, temporizadores, `eval_js`, `IS_WASM`. |

#### 🌐 HTTP, compresión y motores de texto

| Módulo | Qué ofrece |
| --- | --- |
| [`petitio`](docs/api/petitio.md) | Cliente HTTP/1.1 + HTTP/2 sobre libcurl: streaming, cookies, auth y proxies. |
| [`compressus`](docs/api/compressus.md) | gzip, zlib y deflate crudo sobre el miniz vendorizado. |
| [`lingua`](docs/api/lingua.md) | Codepoints UTF-8 sobre `utf8.h` de sheredom. |
| [`regulus`](docs/api/regulus.md) | Regex pequeño y explícito sobre `tiny-regex-c` de kokke. |

#### 🛠️ CLI, pruebas y callbacks

| Módulo | Qué ofrece |
| --- | --- |
| [`invoke`](docs/api/invoke.md) | Parseo de argumentos, subcomandos, flags tipados y sugerencias ante erratas. |
| [`trial`](docs/api/trial.md) | Ayudas de testing usadas por los bloques `test` integrados. |
| [`functor`](docs/api/functor.md) | Funciones gruesas `Fn0`–`Fn3`: callback más contexto explícito, sin closures. |

Los cuatro wrappers de C usan **smart linking**: `std.petitio` enlaza libcurl solo
al importarse, `std.compressus` enlaza miniz solo al importarse, etc. Un programa
que no importa ninguno enlaza únicamente el runtime básico.

<a id="es-wasm"></a>
### 🕸️ WebAssembly

El mismo fuente `.pengu` puede compilarse para el navegador (o Node sin interfaz)
mediante Emscripten, sin cambiar el código:

```bash
# Configuración inicial
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk && ./emsdk install latest && ./emsdk activate latest && source ./emsdk_env.sh

# Runtime para el objetivo wasm (separado del build nativo)
python build_runtime.py --target emscripten

# Compilar y ejecutar
pengu build --target wasm32-unknown-emscripten
pengu run   --target wasm32-unknown-emscripten
pengu run   --target wasm script.pengu
```

Una compilación `exe` produce `app.html` + `app.js` + `app.wasm`; `node
build/app.js` lo ejecuta sin navegador. Los hilos de `std.filum` se convierten en
Web Workers reales, y `std.web` expone la consola de JS, el bucle principal, los
temporizadores y `eval_js`.

**WASI no está soportado** — `--target wasm32-wasi` se reconoce y se rechaza.
Consulta [docs/WASM.md](docs/WASM.md) para la guía completa, limitaciones y
resolución de problemas.

<a id="es-rendimiento"></a>
### ⚡ Rendimiento

`pengu run script.pengu` debe sentirse como ejecutar un script, no como compilar
un proyecto. Cinco optimizaciones independientes, cada una con su interruptor
documentado:

| Optimización | Qué hace | Desactivar con |
| --- | --- | --- |
| Caché de tablas del parser | Serializa las tablas LALR de Lark (~3,9 s → ~0,25 s por proceso) | `PENGU_CACHE=0` |
| Caché de binarios | Reutiliza el binario enlazado según el hash del contenido del script y sus imports | `--no-cache`, `--ephemeral` |
| Eliminación de código muerto | Emite solo los `weave` de `std/` / `lib/` alcanzables desde `main` / tests | `--no-dce`, `PENGU_NO_DCE=1` |
| TinyCC | Incluido en releases; ~19 ms por bundle frente a ~400 ms con gcc | `PENGU_NO_TCC=1`, `PENGU_DEV_CC=gcc` |
| Memoización de pkg-config | Una consulta por paquete y proceso en vez de ~12 lanzamientos | siempre activa |

Medido en la máquina de referencia (Linux x86_64, Python 3.14.7, gcc 16.2.1,
TCC 0.9.28rc, mejor de 5):

| Escenario | Antes | Después |
| --- | ---: | ---: |
| `pengu run hello.pengu` — primera ejecución, tablas cacheadas | 3,88 s | **0,85 s** (gcc) / **0,66 s** (TCC) |
| `pengu run hello.pengu` — segunda ejecución (acierto de caché) | 3,88 s | **0,19 s** |
| `bundle.c` de un script que solo usa `spark.println` | 432 líneas / 19,4 KB | **65 líneas / 2,3 KB** (−84 %) |
| Construcción de tablas LALR por proceso | 3,9 s | **0,25 s** (caché) |
| Bucle de 10M iteraciones (fase de ejecución) | ~33 ms | 33 ms |

```bash
pengu doctor                 # estado del compilador, TCC, runtime y caché
pengu time hello.pengu       # desglose por fases
pengu benchmark              # benchmarks reproducibles de benches/
python scripts/bench.sh      # reproduce la tabla anterior
```

Por defecto no se escribe nada en el `build/` del proyecto. Si TinyCC falla,
`pengu run` reintenta una vez con el compilador configurado y avisa en vez de
fallar. Consulta [docs/PERFORMANCE.md](docs/PERFORMANCE.md) y
[BENCHMARKS.md](BENCHMARKS.md).

<a id="es-pruebas"></a>
### 🧪 Pruebas y CI

El compilador tiene una suite grande de pytest más corpus de compilación y
ejecución. La ejecución por defecto es en paralelo y debería mantenerse en unos
pocos minutos:

```bash
pengu selftest --smoke       # tier rápido, sin rebuild completo
pengu selftest --affected    # solo lo que tus cambios pueden afectar
pengu selftest               # suite completa por defecto
pytest tests/                # la misma suite a través de pytest
```

GitHub Actions compila y prueba en **Linux, Windows y macOS**, ejecuta los corpus
de cumplimiento y conformidad, compila el objetivo WebAssembly, empaqueta la
extensión de VS Code y publica una release cuando se crea una etiqueta `v*`. Los
sanitizers, el fuzzing y los benchmarks se ejecutan en el workflow nocturno.
Consulta [AGENT_TESTING.md](AGENT_TESTING.md) antes de añadir tests.

<a id="es-editor"></a>
### 🧩 Soporte de editor

La extensión oficial de VS Code vive en
[`vscode-extension/`](vscode-extension/README.md). Ofrece:

- Resaltado de sintaxis con TextMate
- Diagnósticos LSP con notas `help:` / `note:` y spans con caret
- Hover de tipo y tamaño en bytes, autocompletado por módulo e ir a la definición
- Formateo y acciones de código
- Comandos Build / Run / Clean / Init

Instala el `pengus-<version>.vsix` de una release, o compílalo tú mismo:

```bash
cd vscode-extension
npm install
npm run package            # -> pengus-<version>.vsix
```

El Language Server es independiente del editor: `pengu lsp` habla stdio por
defecto y también puede escuchar por TCP. Consulta
[LANGUAGE.md §20.10](LANGUAGE.md#2010-language-server-protocol-pengu-lsp).

<a id="es-estructura"></a>
### 📁 Estructura del proyecto

```text
PenguScript/
├── pengu_parser/          # Compilador: gramática, símbolos, comprobación de tipos,
│                          #   comptime, codegen C99/C11 y diagnósticos
├── pengu_lsp/             # Language Server (pygls)
├── pengu_project.py       # CLI `pengu` y gestor de compilación
├── pengu_bind.py          # `pengu bind`: cabecera C -> .d.pengu
├── pengu_doc.py           # `pengu doc`: generador de referencia Markdown
├── pengu_runtime.h        # API pública del runtime de C
├── build_runtime.py       # Compila el runtime de C en build/lib
├── make_release.py        # Empaqueta la release independiente + VSIX
├── std/                   # 40 módulos de la biblioteca estándar
├── std_c/                 # Motores C vendorizados (utf8.h, tiny-regex-c, miniz, …)
├── docs/                  # Guías, notas de arquitectura y documentación de API
├── examples/              # Ejemplos pequeños y ejecutables
├── benches/               # Programas y arnés de benchmarks
├── tests/                 # Suite de pytest + corpus de conformidad
├── vscode-extension/      # Extensión de VS Code (gramática, cliente LSP, comandos)
├── LANGUAGE.md            # Referencia del lenguaje (inglés)
├── LANGUAGE_Spanish.md    # Referencia del lenguaje (español)
├── CHEATSHEET.md          # Chuleta de sintaxis y traducción a C
├── BENCHMARKS.md          # Mediciones publicadas
├── CHANGELOG.md           # Historial de versiones
└── VERSION                # Única fuente de verdad de la versión
```

La salida generada vive en `build/` y está en `.gitignore`. Los artefactos de
release se producen en `pengucc_build/` con `python make_release.py`.

<a id="es-roadmap"></a>
### 🗺️ Hoja de ruta y límites

PenguScript 2.x pretende ser **aditivo**: los programas existentes deberían seguir
compilando, y las deprecaciones siguen una política escrita
([docs/DEPRECATIONS.md](docs/DEPRECATIONS.md)). Aun así, es un proyecto pequeño:
evalúalo para tu caso de uso en vez de asumir una madurez de producción.

**Deliberadamente todavía no**

- ❌ Borrow checking y ownership automático (la memoria es manual por diseño)
- ❌ `async` / `await`
- ❌ Closures con captura (usa las funciones gruesas de `std.functor`)
- ❌ Macros de AST, reflexión y despacho dinámico
- ❌ Tipos asociados
- ❌ `pengu repl`
- ❌ WASI (`wasm32-wasi` se rechaza; Emscripten es el único objetivo wasm)

**Aristas conocidas**

- La aritmética de punteros (`p + 1`) no está soportada; usa indexación
  (`p at i`) o `std.ffi.slice_from_ptr`.
- `--strict-c99` **no es funcional** para programas que importan `std`. No lo uses
  como puerta de portabilidad en CI.
- Algunas cabeceras C de terceros necesitan flags extra o pequeños ajustes
  manuales en `pengu bind`. La CLI no tiene flags `-I` / `-L` / `-l`; usa
  `pengu.yaml` / `pengu.toml`.
- La API aún es joven. Lee [CHANGELOG.md](CHANGELOG.md) antes de actualizar.

La hoja de ruta viva es el
[gestor de issues](https://github.com/TuGatito/PenguScript/issues). Las
peticiones de características y los informes de bugs honestos son bienvenidos,
especialmente los pequeños y reproducibles.

<a id="es-docs"></a>
### 📖 Documentación

| Documento | Qué cubre |
| --- | --- |
| [LANGUAGE.md](LANGUAGE.md) / [LANGUAGE_Spanish.md](LANGUAGE_Spanish.md) | Referencia completa del lenguaje, stdlib y diagnósticos. |
| [CHEATSHEET.md](CHEATSHEET.md) | Sintaxis, palabras clave y traducción a C. |
| [PenguScriptGuideEnglish.md](PenguScriptGuideEnglish.md) / [PenguScriptGuideSpanish.md](PenguScriptGuideSpanish.md) | Guía de estilo idiomático. |
| [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md) | CLI, configuración de proyecto y sistema de compilación. |
| [docs/BINDINGS.md](docs/BINDINGS.md) | Bibliotecas puras, bindings de C y propagación de `link`. |
| [docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md) | Repositorios satélite de bindings C. |
| [docs/WASM.md](docs/WASM.md) | Objetivo WebAssembly/Emscripten. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline del compilador de principio a fin. |
| [docs/PERFORMANCE.md](docs/PERFORMANCE.md) | Diseño de rendimiento, cifras y optimizaciones. |
| [docs/ABI.md](docs/ABI.md) | Política y versionado del ABI del runtime. |
| [docs/api/](docs/api/README.md) | Referencia de API generada para los 40 módulos de `std`. |
| [docs/README.md](docs/README.md) | Índice de toda la documentación complementaria. |
| [BENCHMARKS.md](BENCHMARKS.md) | Mediciones publicadas de compilación, ejecución y tamaño. |
| [CHANGELOG.md](CHANGELOG.md) | Historial de versiones y notas de release. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Cómo contribuir y reportar problemas. |
| [SECURITY.md](SECURITY.md) | Modelo de seguridad y cómo reportar. |
| [AGENT_TESTING.md](AGENT_TESTING.md) | Reglas y presupuesto de tiempo de la suite. |
| [vscode-extension/README.md](vscode-extension/README.md) | Características, configuración e instalación de la extensión. |

Enlaces rápidos: [Referencia del lenguaje](LANGUAGE_Spanish.md) ·
[Chuleta](CHEATSHEET.md) · [API](docs/api/README.md) ·
[Ejemplos](examples/) · [Releases](https://github.com/TuGatito/PenguScript/releases).

<a id="es-gracias"></a>
### 🙏 Agradecimientos

PenguScript se apoya en muchos proyectos de código abierto excelentes. Gracias a
sus autores y contribuidores. Los nombres de licencia son los publicados por cada
proyecto original.

#### 🐍 Cadena de herramientas en Python

| Proyecto | Para qué se usa | Licencia |
| --- | --- | --- |
| [Lark](https://github.com/lark-parser/lark) | Gramática y análisis sintáctico | MIT |
| [PyYAML](https://pyyaml.org/) | Configuración `pengu.yaml` | MIT |
| [pygls](https://github.com/openlawlibrary/pygls) | Framework del Language Server | Apache-2.0 |
| [lsprotocol](https://github.com/microsoft/lsprotocol) | Tipos del protocolo LSP | MIT |
| [pycparser](https://github.com/eliben/pycparser) | Parseo de cabeceras C en `pengu bind` | BSD-3-Clause |
| [PyInstaller](https://pyinstaller.org/) | Ejecutable independiente `pengu` | GPL-2.0-or-later (con excepción del bootloader) |
| [pytest](https://pytest.org/) | Ejecutor de tests | MIT |
| [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) | Ejecución paralela de tests | MIT |
| [pytest-timeout](https://github.com/pytest-dev/pytest-timeout) | Límite por test | MIT |
| [pytest-cov](https://github.com/pytest-dev/pytest-cov) / [coverage](https://coverage.readthedocs.io/) | Medición de cobertura | MIT / Apache-2.0 |
| [Hypothesis](https://hypothesis.readthedocs.io/) | Tests basados en propiedades | MPL-2.0 |
| [ruff](https://docs.astral.sh/ruff/) | Puerta de análisis estático | MIT |
| [tomli](https://github.com/hukkin/tomli) | Backport de `tomllib` para Python < 3.11 | MIT |

#### 🧩 Motores C vendorizados (`std_c/`)

| Proyecto | Autor | Lo usa | Licencia |
| --- | --- | --- | --- |
| [`utf8.h`](https://github.com/sheredom/utf8.h) | **sheredom** | `std.lingua` | Dominio público / [Unlicense](https://unlicense.org/) |
| [`tiny-regex-c`](https://github.com/kokke/tiny-regex-c) | **kokke** | `std.regulus` | Dominio público |
| [`miniz`](https://github.com/richgel999/miniz) | **Rich Geldreich** | `std.compressus` | Dominio público / [Unlicense](https://unlicense.org/) |
| [`libcurl`](https://curl.se/libcurl/) | **Daniel Stenberg y contribuidores** | `std.petitio` | [curl license](https://curl.se/docs/copyright.html) (tipo MIT) |

Son motores pequeños, centrados y bien probados. Usarlos permite que los wrappers
sean finos y el comportamiento predecible, en vez de reimplementar UTF-8, regex,
deflate o HTTP desde cero.

#### 🛠️ Compilación y herramientas

| Proyecto | Para qué se usa | Licencia |
| --- | --- | --- |
| [TinyCC](https://bellard.org/tcc/) | Backend rápido de compilar y ejecutar, incluido en releases | LGPL-2.1 |
| [Emscripten](https://emscripten.org/) | Objetivo WebAssembly | MIT |
| [GCC](https://gcc.gnu.org/) / [Clang](https://clang.llvm.org/) | Compiladores C de referencia | GPL-3.0+ con excepción de runtime / Apache-2.0 con excepciones de LLVM |
| [Node.js](https://nodejs.org/) | Ejecución wasm sin navegador y herramientas de VS Code | MIT-style |
| [VS Code Language Client](https://github.com/microsoft/vscode-languageserver-node) | Cliente LSP de la extensión | MIT |
| [esbuild](https://esbuild.github.io/) | Empaquetado de la extensión | MIT |
| [TypeScript](https://www.typescriptlang.org/) | Lenguaje fuente de la extensión | Apache-2.0 |

**Gracias especiales** a sheredom, kokke, Rich Geldreich, Daniel Stenberg y los
contribuidores de curl, a los equipos de Lark y pygls, a las comunidades de
Emscripten y TinyCC, y a todas las personas que han reportado un bug o enviado un
mensaje amable. 💙

Y, por supuesto, **gracias a DeepSeek** por ayudarme a construir, probar y
documentar este proyecto — y por hacer que un lenguaje de una sola persona sea un
poco más posible. 🤖

<a id="es-licencia"></a>
### ⚖️ Licencia

PenguScript se distribuye bajo la **[Licencia MIT](LICENSE)** — © 2026 TuGatito.
Los módulos satélite instalados con `pengu add` son proyectos separados y
conservan sus propias licencias.

---

<p align="center">
  <sub>Hecho con 🐧, ☕ y bastante paciencia — por TuGatito y DeepSeek.</sub>
</p>
