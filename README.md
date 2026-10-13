# PenguScript

![Version](https://img.shields.io/badge/version-2.0.0-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11+-yellow) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

**🌍 Languages / Idiomas:** [🇬🇧 English](#-english) · [🇪🇸 Español](#-español)

> **Language policy.** English is the canonical language of this repository's
> documentation; the Spanish sections are **non-normative** translations of the same
> content, kept structurally in step by `tests/compiler/test_language_policy.py`.
> **Política de idioma.** El inglés es el idioma canónico de la documentación de este
> repositorio; las secciones en español son traducciones **no normativas** del mismo
> contenido.

> **Status:** active development. CI builds the C runtime, runs `pytest tests/`, and packages a standalone release (compiler + VS Code extension) on **Windows, Linux and macOS** — see `.github/workflows/ci.yml`; tagged releases are published by `.github/workflows/release.yml`.

> [!WARNING]
>
> ### 2.0.0 — released, with a declared scope
>
> PenguScript **2.0.0** is published. The public surface freezes per
> [`docs/FREEZE.md`](docs/FREEZE.md), and the compatibility contract is pinned by
> programs that **compile and execute**: the compliance corpus under
> `tests/conformance/compliance/` (formerly `tests/compliance/`) for the current
> language, and `tests/migration/` for every published version line. 2.0 is an
> **additive** release — no existing `.pengu` program stops compiling; its one
> genuine contract change is that a source file may now emit C the compiler does
> **not** type-check (`antiquus`, §9.6).
>
> That does **not** mean "everything": borrow checking, async/await, closures
> with capture, AST macros, dynamic dispatch, reflection, a `Result`-only stdlib,
> associated types (LANGUAGE.md §11.7), call-site spread (`f(...xs)`, §8.2) and
> `pengu repl` are **not** in 2.0. Each deferral carries its measurement and an
> explicit ⏸️ marker in `LANGUAGE.md`; `--strict-c99` remains not functional for
> programs that import `std` (see *What's new in 2.0*). The exact 1.0 scope, the
> compiler matrix and the sanitizer/fuzzing coverage actually measured are stated
> in [`docs/ANNOUNCEMENT_1.0.md`](docs/ANNOUNCEMENT_1.0.md); the verified
> assessment behind those claims is `AUDIT_1.0.md` (historical). The older
> readiness snapshot, which describes an earlier release, is kept as a historical
> document in [`docs/archive/`](docs/archive/).
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
>   generics, `static var` function-local state, and the 22 pure `std/` modules
>   (files, processes, threads/channels, JSON/CSV, string algorithms, math,
>   logging, unit tests, generic C bridge, …).
> - **Multidimensional 2D arrays** (`array of array of T with size M with size N`),
>   **manual memory deallocation** (`banish` now, or `defer banish` / `errdefer banish` at scope exit),
>   **module state idioms** (`static var` accessors and context structs),
>   **C variadic declarations** (`declare ... with fmt as ref to frozen char, ... into int`),
>   **struct literals in array literals**, **pointer indexing** (`p at i`), generic
>   slice bridging (`ffi.slice_from_ptr shard T`), and **embedded project assets** (`arca`).
> - Embed **literal C** in a `.pengu` file with `antiquus` (`r"""…"""` bodies,
>   `@export("c_name")` to pin the emitted symbol) and chain methods in one
>   `calling` (`calling x.a.b.c`) — see *What's new in 2.0* below.
>
> Published measurements: [`BENCHMARKS.md`](BENCHMARKS.md). Operational release steps: [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). Security policy: [`SECURITY.md`](SECURITY.md).
>
> **What is not there yet (do not plan a production project around these)**
>
> - **Pointer arithmetic** (`p + 1`): use indexing `p at i` or create a slice with `std.ffi.slice_from_ptr`.
> - **A bare `printf`/`TextFormat` reached only through `include`** (no `declare` in scope) still
>   type-checks and then fails in C; declare it (`declare printf with fmt as ref to frozen char, ... into int`)
>   — the compiler reports the failure at your `.pengu` line.
> - Tooling limits: `pengu bind` handles real headers (`--define`, `--cpp-flags`,
>   `--system-includes`, `--preprocessed`), but some third-party headers still
>   need extra flags or hand-maintained tweaks, and the CLI has no `-I`/`-L`/`-l`
>   flags — use `pengu.yaml`.
>
> P0 (operational hygiene), P1 (the C shapes the C-interop corpus needed), P2
> (breadth and safety: 2-D arrays, explicit memory release, strict
> pointer typing, real-header bindings) and Phase 5 (defined overflow and
> always-on bounds checking, `unsafe:` opt-out, lockfile verification with
> `pengu verify`, a binding sandbox, a trust gate for dependency build scripts,
> deprecation policy with `--deny-deprecated`, and continuous fuzzing) are
> complete. The 1.1 ergonomics tier (method chaining, multiple return values,
> shorthand struct initializers, `@noreturn`/`@export`/`@packed`/`@align`) and the
> 2.0 `antiquus` tier are documented under **What's new in 2.0** below; what
> remains are the features explicitly marked ⏸️ in `LANGUAGE.md`.
>
> **Now guaranteed:** out-of-bounds access and signed overflow have defined
> behaviour in *every* profile; the only opt-out is an explicit `unsafe:` block
> or `--release-unsafe`. See [LANGUAGE.md §5.0](LANGUAGE.md#50-safety-guarantees-and-their-opt-outs).

---

## 🇬🇧 English

### What's new in 2.0

PenguScript 2.0 is an **additive** release: every 1.x program still compiles, and the highlights below are each verified against the real toolchain.

- **Method chaining** — a single `calling` resolves several `.name` links left to right, each against the type produced by the previous one; a chain may span lines when every continuation begins with `.` ([§24](LANGUAGE.md#24-method-chaining)):

  ```pengu
  import std.scrolls

  weave shorten with raw as string into string:
      return calling raw
          .trim
          .substring with 0, 2
  ```

- **Multiple return values** — declare a tuple result with `into (T, U)`, return the values comma-separated, and destructure with `let (q, ok) is …` ([§25](LANGUAGE.md#25-multiple-return-values)):

  ```pengu
  weave divide with a as int, b as int into (int, bool):
      if b == 0:
          return 0, false
      return (a / b), true

  weave use_div into int:
      let (q, ok) is calling divide with 10, 2
      if not ok:
          return 0
      return q
  ```

- **Shorthand struct initializers** — a field whose slot holds a single bare name may omit `is <value>`, so `with name, hp` means `with name is name, hp is hp` ([§26](LANGUAGE.md#26-shorthand-struct-initializers)).
- **Declaration attributes** — `@noreturn` (a `void` weave that never returns; emits `_Noreturn`), `@export("c_name")` (pins the emitted C symbol and makes the declaration a DCE root), `@packed` (no inter-field padding) and `@align(N)` (a power of two from 1 to 128) ([§27](LANGUAGE.md#27-function-attributes-noreturn-and-export), [§28](LANGUAGE.md#28-layout-attributes-packed-and-alignn)):

  ```pengu
  @export("pengu_add")
  weave add with a as int, b as int into int:
      return a + b

  @packed
  rune NetHeader:
      magic as u16
      version as u8
      flags as u8
      length as u32
  ```

- **Embedded C blocks (`antiquus`)** — a declaration whose body is literal C inside a triple-quoted string; prefer `r"""…"""` when the C contains backslashes. The body is emitted verbatim and is **not** type-checked, which is the one genuine 2.0 contract change ([§9.6](LANGUAGE.md#96-antiquus--embedded-c-blocks)):

  ```pengu
  antiquus fast_abs with x as int into int:
      r"""
      return x < 0 ? -x : x;
      """
  ```

- **`cyclus`** — marks an intentionally self-referential type; the cycle must still be broken by pointer indirection (`ref to`, `maybe ref to`, `slice`, `list`, `map`) ([§9.1.1](LANGUAGE.md#911-cyclus--self-referential-types)):

  ```pengu
  rune Node cyclus shard T:
      value as T
      next as maybe ref to Node of T
  ```

- **`unsafe:` blocks** — the only in-language opt-out from bounds checking; each block always warns `[W0007]` so the opt-out is visible in review ([§5.0](LANGUAGE.md#50-safety-guarantees-and-their-opt-outs)):

  ```pengu
  weave sum with xs as array of int, n as int into int:
      var acc as int is 0
      unsafe:
          for i from 0 to n:
              set acc is acc + (xs at i)
      return acc
  ```

- **`many T`** — `with xs as many T` makes a `weave` variadic; call sites list the arguments normally and the compiler packs them into a temporary slice ([§8.2](LANGUAGE.md#82-declare--external-c-functions)):

  ```pengu
  weave count_args with xs as many int into int:
      return (xs length to int)
  ```

- **`--strict-c99`** — ⏸️ **not functional for programs that import `std`** (measured: 34 of the 61 programs in `tests/std_programs/` fail `gcc -std=c99 -pedantic-errors`); deferred to 1.1. Do **not** use it as a CI or release portability gate ([§20.2](LANGUAGE.md#202-compilation--build-profiles-pengu-build)).
- **Cross-compilation** — `pengu build --target x86_64-w64-mingw32 --cc x86_64-w64-mingw32-gcc` selects the target OS from a triple; only **Linux ⇄ Windows** is supported ([§20.2.3](LANGUAGE.md#2023-cross-compilation---target)).
- **Runtime ABI versioning** — `pengu_runtime.h` defines `PENGU_ABI_VERSION`, the frozen layout of the runtime containers; every bundle references `pengu_abi_version()`, so a `libpengu_runtime.a` built against a different ABI fails at link instead of reinterpreting struct fields ([§20.2.1](LANGUAGE.md#2021-runtime-abi-version)).
- **JSON diagnostics** — `pengu check --json` and `pengu build --json` emit one `{"type":"diagnostic",…}` object per problem plus a final summary line, and nothing else on stdout ([§20.2.2](LANGUAGE.md#2022-machine-readable-diagnostics---json)):

  ```bash
  pengu check --json | jq -c 'select(.type=="diagnostic") | {file,line,col,code}'
  ```

- **Conditional linking** — the core runtime has no external C dependencies: it needs only libc, libm and pthreads/Win32 threads, and a program with no native imports links only `libpengu_runtime.a`, which is why a stripped `hello_world` is ~14 KiB (see [BENCHMARKS.md](BENCHMARKS.md)). Native archives for satellite modules (installed with `pengu add`) are linked only when the module that declares them is imported.

### Feature Highlights

- **Pythonic, indentation-based syntax** — no semicolons or braces; blocks are whitespace-delimited ([§3](LANGUAGE.md#3-lexical-structure)).
- **V-style scoping safety** — `const` is strictly global (top-level) and becomes a C `#define`; `var` (mutable) and `let` (immutable) are strictly local to function bodies, preventing accidental mutable global state ([§5](LANGUAGE.md#5-variables-constants--scope)).
- **Expressive type system** — fixed-width integers (`u8`…`u64`, `i8`…`i64`), `f32`/`f64`, `char`, `byte`, `string`, `bool`; fixed-size 1D/2D arrays, non-owning slices, dynamic lists, and hash maps with compile-time layout estimation ([§4](LANGUAGE.md#4-type-system)).
- **User types** — `rune` structs with private `_` fields and `enchanting` method blocks (`self->`), `echo` (C-compatible unions), `omen` (simple enums and algebraic data types with payloads), and `maybe T` / `result of T to E` with statement-expression unwrapping (`or else`, `or return`, `try`) ([§9](LANGUAGE.md#9-composite-types), [§12](LANGUAGE.md#12-optionals--errors)).
- **Primitive methods** — attach methods to `int`, `char`, `bool` and every primitive with `enchanting` (`enchanting int: weave clamp …`); opt-in per module, and zero overhead: `self` is the value (no `&`, no boxing, no vtable), the body is monomorphized to a plain C function (`int32_t int_clamp(int32_t self, …)`), and `enchanting shard T where T: Integrum:` covers every integer type at once ([§10.1](LANGUAGE.md#101-enchanting--métodos-sobre-tipos)).
- **Methods & compile-time concepts** — `enchanting` attaches methods to structs; `concept` defines compile-time interfaces checked statically with `bind` exhaustiveness, zero runtime overhead, and no vtables ([§10](LANGUAGE.md#10-methods-concepts--binding); see [§10.6 Explicit limitations](LANGUAGE.md#106-limitaciones-explícitas-de-los-concepts)).
- **Strings built one way** — dynamic strings are composed **only** with `"{expr}"` interpolation; `+`/`+=` on strings raise `E0005` (no implicit `to string` promotion, no hidden temporaries), and storing a `string` into a struct field or collection element copies its bytes with `memcpy` — releasing the original stays your call ([§15.2](LANGUAGE.md#152-strings)).
- **Zero-overhead generics** — `shard` declarations specialized with `of`; each instantiation is monomorphized to plain C with concept bounds validation (`where T: Printable`) ([§11](LANGUAGE.md#11-generics)).
- **Deterministic, manual cleanup** — `banish` frees a value now; `defer banish` / `errdefer banish` defer the release to scope exit or to an error return (LIFO). Nothing is released behind your back ([§13](LANGUAGE.md#13-manual-memory-management)).
- **First-class C FFI** — `include`/`link`/`declare`, opaque types (`alias … as opaque`), `sigil of` (address-of) / `essence of` (deref), zero-copy `bytes of <string>` borrows, and `weave`s that decay to C function pointers ([§14](LANGUAGE.md#14-modules-imports--c-interop)).
- **`pengu bind`** — auto-generates a `.d.pengu` declaration file from any C header (structs → `rune`, unions → `echo`, enums → `omen`, functions → `declare`, callbacks → `alias … as ref to weave`, doc comments preserved) with preprocessor extension blanking, sibling auto-imports, and flags (`--define`, `--cpp-flags`, `--system-includes`, `--preprocessed`) ([§20.6](LANGUAGE.md#206-c-header-binding-generator-pengu-bind)).
- **Rich standard library** — `std/` ships **22 pure PenguScript modules** and **0 C declaration bindings** (I/O, strings, files, math, time, concurrency, logging, unit testing, …) ([§19](LANGUAGE.md#19-standard-library)). Bindings to external C libraries (raylib, sqlite3, webui, miniaudio, etc.) now live in satellite repositories — see [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).
- **Embedded project assets (`arca`)** — embed binary and text assets (textures, shaders, audio, fonts, HTML/JS/CSS, config files) directly into native `.rodata` sections or stream from disk with zero-copy pointer views and slice accessors ([§19.4](LANGUAGE.md#194-embedded-project-assets-arca)).
- **Language Server (LSP)** — diagnostics with `help:`/`note:`/caret spans, documentation from `#` and `##` doc comments, type & memory-size hovers, module-scoped autocompletion, go-to-definition, formatting, and code actions ([§20.10](LANGUAGE.md#2010-language-server-protocol-pengu-lsp)).
- **Unified project manager** — the `pengu` CLI creates (`init`), builds (`build`), runs (`run`), tests (`test`), checks (`check`), formats (`fmt`), cleans (`clean`), documents (`doc`), generates C bindings (`bind`), and launches the language server (`lsp`) ([§20](LANGUAGE.md#20-tooling--project-layout)).
- **Compile-time features** — `when` conditionals with `else when` / `else`, `defined(...)`, `-D name=value` defines, function `static var` state, and `when main:` guards for dual module/script files ([§16](LANGUAGE.md#16-conditional-compilation-when)).
- **Robust diagnostics** — comprehensive Rust-style error catalog with codes `E0000`–`E0065` (documented in LANGUAGE.md §22.2) and warnings `W0001` (transmute), `W0002` (echo access), `W0004` (unreachable), `W0005` (shadowing), `W0006` (`@deprecated` use), `W0007` (`unsafe:` block) ([§22](LANGUAGE.md#22-appendix-compiler-diagnostic-catalog)).

---

### Quick Start

#### Requirements

- **Python 3.11+** (3.10 also works — `requirements.txt` installs the `tomli` backport automatically there).
- A **C compiler** (`gcc` or `clang`) and static archiver (`ar`/`llvm-ar`) on your `PATH` — on Windows use MinGW-w64 `gcc`. `gcc`/`clang` are the reference backends.
- **CMake and Ninja** — build-system tools for the supported development environments.
- **Node.js 18+ and npm** — only needed to develop or package the VS Code extension.

##### System Dependencies for Linux & macOS

On Linux and macOS, building the language runtime needs only a C toolchain plus the Python and Node tooling — there are no external development libraries to install:

**Fedora / RHEL:**
```bash
sudo dnf install -y @development-tools \
    cmake ninja-build gcc gcc-c++ python3 nodejs
```

**Ubuntu / Debian:**
```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential cmake ninja-build gcc g++ python3 nodejs
```

**Arch Linux:**
```bash
sudo pacman -S --needed base-devel cmake ninja gcc python nodejs
```

**macOS (Homebrew):**
```bash
brew install cmake ninja python node
```

#### Setup

```bash
git clone https://github.com/pengus-lang/penguscript.git
cd penguscript

# Create a virtual environment and install Python dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build the C runtime into build/lib
python build_runtime.py

# Confirm the toolchain version (prints the toolchain version, `pengu 2.0.0`);
# `pengu --version` is an alias.
pengu -V

# Run the test-suite (parallel; see AGENT_TESTING.md before adding tests)
pengu selftest
pytest tests/ -n auto
```

`pengu selftest --smoke` runs the fast tier (<3 s, no C compiler needed);
`pengu selftest --affected` runs only what your changes can affect. The full suite
is ~4 min 37 s parallel against 34 min 19 s serial. `pengu test` is a different
command: it compiles *your* project and runs its integrated `test` blocks.

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
| `add`      | Add an external dependency or binding (git URL or local folder, optional build script); the source tree is copied into `lib/<name>/`. |
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

The core cycle is `init` → `build` → `run`/`test` → `check` → `fmt` → `doc`/`bind`/`lsp`; `pengu -V` (or `pengu --version`) prints the toolchain version.

Projects are configured with `pengu.toml` or `pengu.yaml` (mutually exclusive; if both exist, `pengu.toml` wins; examples in `LANGUAGE.md` §14.4 use YAML for brevity) — entry point, output type/name, includes, links, per-profile `cflags`/`defines`, and compiler selection. Bounds checking is emitted in **every** profile (`--profile release` cannot trade memory safety for speed): `debug` (default) also keeps `-g` and frame-stack traces, while `release` adds `-O3`. The only opt-outs are an explicit `unsafe:` block or `--release-unsafe` ([§5.0](LANGUAGE.md#50-safety-guarantees-and-their-opt-outs)). See [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md) for the full guide.

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
breakdown, `python benches/run_bench.py` for the language/runtime benchmarks, and
`scripts/bench.sh` to reproduce the table above. See
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
  # mylib.d.pengu (excerpt)
  include "mylib.h"
  alias MylibState as opaque
  declare mylib_len with text as ref to char into size_t
  ```

  …then, from your code:

  ```pengu
  import mylib
  var n as size_t is calling mylib.mylib_len with "PenguScript"
  ```

  Real-world C headers can be turned into such bindings automatically with `pengu bind`.

#### Why not ownership?

Rust makes the compiler track every loan and decide when a value dies. PenguScript
does not: it takes the Zig / Odin / Nelua route and makes memory management
**manual**. The compiler refuses to guess, because a wrong guess is either a silent
leak or a use-after-free — both worse than saying what you meant. You allocate with a
constructor or `sigil of`, and you release with `banish`:

```pengu
weave main into int:
    var s is "hello"
    defer banish s          # release at scope exit (LIFO); `banish s` releases now
    calling print with s
    return 0
```

`banish x` frees what `x` owns according to its static type and is a safe no-op on
string literals and non-owning views. `defer banish` / `errdefer banish` schedule the
release at scope exit. When you want a destructor written for you, opt in per type with
`derive Nexus`.

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
- `push`/`put` copy the element bytes with `memcpy` and banish releases only the
  container's own buffer, so a `list of string` needs an explicit
  `pengu_banish_string_list` (or one `banish` per element); see
  [LANGUAGE.md §13.5](LANGUAGE.md#135-containers-memcpy-on-store-explicit-release).
- `derive` works on runes, algebraic omens and generic instantiations; `Imago`
  (deep copy) and `Nexus` (drop) are implied by each other. `echo` unions reject
  `derive` because they are untagged.
- Iterating a bare type parameter (`for x in xs` with `xs as T`) is rejected:
  use `list of T` / `slice of T` (associated types are future work).

The `tests/test_generics/` directory contains one runnable program per feature
plus leak checks; run them with `python -m pytest tests/codegen/test_generics_suite.py`.

#### Standard library

`std/` contains **22 pure PenguScript modules** and **0 C declaration bindings** (verified: `ls std/*.pengu`). See [LANGUAGE.md §19](LANGUAGE.md#19-standard-library) for the full module catalog and code examples.

- **Pure PenguScript modules (22):** `spark` (core I/O, formatted output, typed input, ranges & math helpers), `scrolls` (comprehensive string enchanting algorithms, metrics, casing & three-way string ordering), `oracle` (`Maybe`/`Result` containers with native/legacy interoperability), `compass` (cross-platform paths & pattern matching), `archivum` (files, binary I/O & directory traversal), `cipher` (JSON RFC 8259, Base64/32/Hex & validation), `chronicle` (dates, high-res clocks, timers & duration parsing), `lot` (PRNG, statistical distributions, sampling, shuffling & random strings), `arithmancy` (advanced math), `rites` (OS processes, cross-platform environment & system info), `whisper` (structured leveled logging & `Logger` rune), `ward` (defensive invariants, float/range/container assertions & generic `shard T` tests), `trial` (unit testing), `tally` (functional list operations, reductions, insertion sort & statistics), `atlas` (hash map key-value store, combination, bulk accessors & filters), `coven` (unique `SetString`/`SetInt` collections, ritual constructors & set algebra), `filum` (threads, typed channels, mutexes & atomic operations), `numerus` (universal numeric methods over every primitive via `enchanting shard T where T: Num and T: Ordo and T: Par:` — `abs`, `clamp`, `pow_int`, `floor`, `round`, predicates & conversions, monomorphized to `int_abs`, `f64_clamp`, …), `loom` (sequence pipelines, windowing & generic algorithms), `invoke` (advanced CLI parsing, subcommands, typed flags, multi-options & typo suggestions), `ffi` (C bridge), and `ledger` (CSV/TSV parsing, tabular data & matrix enchantments).
- **Bindings to external C libraries (raylib, sqlite3, webui, miniaudio, etc.) now live in satellite repositories.** See [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md); install one with `pengu add <url>` (the source tree is copied into `lib/<name>/`).

The 22 modules ship comprehensive documentation (`#`/`##` doc comments, audited by `tests/docs/test_std_docs_completeness.py`), full test coverage across `debug` and `release` compilation profiles, 100% backward compatibility across every published version line (pinned by `tests/migration/`), and zero C compiler warnings.

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
├── build_runtime.py        # Compiles the C runtime into build/lib
├── extern_manifest.py      # Manifest + downloader infrastructure reused by satellite modules (-> extern/)
├── make_release.py         # One-shot release packager -> pengucc_build/ (see below)
├── std/                    # Standard library: 22 pure-PenguScript modules (0 C bindings)
├── c_bind_stubs/           # Minimal stub C headers used when `pengu bind` preprocesses
├── extern/                 # Downloaded third-party C library sources (gitignored)
├── build/                  # Generated output (gitignored):
│                           #   build/lib/libpengu_runtime.a + build/include/ headers
├── tests/                  # Python test-suite (pytest tests/): compiler, LSP, CLI,
│                           #   `pengu bind`, the std library & satellite modules
├── tests/std_programs/     # One PenguScript exercise program per std module
│                           #   (compiled & run by tests/stdlib/test_stdlib.py)
├── vscode-extension/       # VS Code extension (grammar, LSP client, project commands)
├── CHANGELOG.md            # Version history & feature log
├── CHEATSHEET.md           # Full language syntax & C-translation reference
└── docs/                   # Build guide, performance/fuzzing notes & archived docs
    ├── PENGU_BUILD.md      # Build system & project configuration guide
    ├── README_RELEASE.md   # Generated: standalone release package documentation
    └── archive/            # Historical, non-normative process documents
```

---

### Building the Runtime from Source

`build_runtime.py` produces the static archive that `pengu` links into every binary. The runtime has **no external C dependencies** — it needs only libc, libm and pthreads/Win32 threads — so there is a single compile stage: `build_pengu_runtime` compiles `pengu_runtime.c` with `gcc`/`clang` + `ar` into `build/lib/libpengu_runtime.a` and stages the headers into `build/include/`:

```bash
python build_runtime.py            # build the runtime
python build_runtime.py --rebuild  # force a clean rebuild (~1.4 s, down from ~5–8 min)
```

`build_pengu_runtime` produces only `libpengu_runtime.a`. Native archives for external C libraries are not bundled here: they are installed per project from satellite repositories with `pengu add` (see [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)).

> `extern_manifest.py` and its now-empty manifest are retained so the satellite repositories can reuse the download/hash infrastructure; the core build neither downloads nor compiles anything.

**Releases** — `make_release.py` automates the whole distribution: it verifies/installs the Python deps, rebuilds the runtime (`--rebuild`), runs smoke tests, packages the CLI + LSP into a standalone executable with PyInstaller (`pengu` / `pengu.exe`), and builds the VS Code extension (`pengus-<version>.vsix`). Everything lands in `pengucc_build/`:

```bash
python make_release.py
```

```text
pengucc_build/
├── pengu (.exe)          # Standalone PenguScript CLI & LSP server
├── pengus-<version>.vsix # VS Code extension
├── std/                  # Complete standard library modules
└── runtime/              # C runtime headers + static library (build/lib)
```

See [docs/README_RELEASE.md](docs/README_RELEASE.md) for the distribution's own documentation.

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

| Document                                                 | What it covers                                                |
| -------------------------------------------------------- | ------------------------------------------------------------- |
| [LANGUAGE.md](LANGUAGE.md)                               | Comprehensive language specification, stdlib, and diagnostics |
| [CHEATSHEET.md](CHEATSHEET.md)                           | Full language syntax, keywords, and C-translation reference   |
| [BENCHMARKS.md](BENCHMARKS.md)                           | Published build/run/artifact-size measurements                |
| [docs/DEPRECATIONS.md](docs/DEPRECATIONS.md)             | Deprecation policy, `@deprecated` aliases and removal windows |
| [docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md)     | Satellite C-binding modules: installing and using them with `pengu add` |
| `MIGRATION.md`                                           | Migration guide across published version lines (named; kept alongside the corpus in `tests/migration/`) |
| [VERSION](VERSION)                                       | The single source of truth for the toolchain version          |
| [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md)               | `pengu` CLI, project config, and the build system             |
| [CHANGELOG.md](CHANGELOG.md)                             | Version history and per-release feature log                   |
| [docs/README_RELEASE.md](docs/README_RELEASE.md)         | The standalone `pengucc_build/` release package               |
| [vscode-extension/README.md](vscode-extension/README.md) | VS Code extension: features, settings, installation           |

---

### Third-Party Acknowledgements & Credits

PenguScript's toolchain, C runtime, and standard library stand on the shoulders of many excellent open-source projects. We gratefully acknowledge and thank their authors. License names below are as published by each upstream project.

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
| [pytest](https://pytest.org/)                                                 | Test runner (`pengu selftest`, `pytest tests/`)             | MIT                            |
| [pytest-xdist](https://github.com/pytest-dev/pytest-xdist)                    | Parallel test execution (`-n auto`; 34 min -> 4 min 37 s)   | MIT                            |
| [pytest-timeout](https://github.com/pytest-dev/pytest-timeout)                | Per-test hang guard (`--timeout=`, `@pytest.mark.timeout`)  | MIT                            |
| [pytest-cov](https://github.com/pytest-dev/pytest-cov) / [coverage](https://coverage.readthedocs.io/) | Coverage ratchet (`fail_under` in `.coveragerc`) | MIT / Apache-2.0 |
| [Hypothesis](https://hypothesis.readthedocs.io/)                              | Property-based tests (formatter idempotency, semantics)     | MPL-2.0                        |
| [ruff](https://docs.astral.sh/ruff/)                                          | The `F821`/`E9` gate (an undefined name is a compiler crash)| MIT                           |
| [tomli](https://github.com/hukkin/tomli)                                      | `tomllib` backport for `pengu.toml` on Python < 3.11        | MIT                            |

---

### License

PenguScript is released under the **[MIT License](LICENSE)** — © 2026 TuGatito. Satellite modules installed from third-party repositories with `pengu add` are separate projects and keep their own licenses (see each satellite repository).

---

## 🇪🇸 Español

> [!WARNING]
>
> ### 2.0.0 — publicada, con un alcance declarado
>
> PenguScript **2.0.0** está publicada. La superficie pública se congela según
> [`docs/FREEZE.md`](docs/FREEZE.md), y el contrato de compatibilidad queda fijado
> por programas que **compilan y se ejecutan**: el corpus de cumplimiento en
> `tests/conformance/compliance/` (antes `tests/compliance/`) para el lenguaje
> actual, y `tests/migration/` para cada línea de versión publicada. La 2.0 es una
> publicación **aditiva** — ningún programa `.pengu` existente deja de compilar;
> su único cambio real de contrato es que un fuente puede emitir C que el
> compilador **no** comprueba (`antiquus`, §9.6).
>
> Eso **no** significa "todo": borrow checking, async/await, closures con captura,
> macros de AST, despacho dinámico, reflexión, una stdlib solo con `Result`, los
> tipos asociados (LANGUAGE.md §11.7), el spread en el punto de llamada
> (`f(...xs)`, §8.2) y `pengu repl` **no** están en la 2.0. Cada aplazamiento
> lleva su medición y un marcador ⏸️ explícito en `LANGUAGE.md`; `--strict-c99`
> sigue sin ser funcional para programas que importan `std` (ver *Novedades de la
> 2.0*). El alcance exacto de la 1.0, la matriz de compiladores y la cobertura de
> sanitizers/fuzzing realmente medidas se detallan en
> [`docs/ANNOUNCEMENT_1.0.md`](docs/ANNOUNCEMENT_1.0.md); la evaluación verificada
> detrás de esas afirmaciones es `AUDIT_1.0.md` (histórico). La instantánea de
> preparación anterior, que describe una publicación más antigua, se conserva como
> documento histórico en [`docs/archive/`](docs/archive/).

### Novedades de la 2.0

PenguScript 2.0 es una publicación **aditiva**: todo programa de la 1.x sigue compilando, y cada novedad de abajo está verificada contra la cadena de herramientas real.

- **Encadenamiento de métodos** — un único `calling` resuelve varios eslabones `.nombre` de izquierda a derecha, cada uno contra el tipo que produce el anterior; la cadena puede repartirse en varias líneas cuando cada continuación empieza por `.` ([§24](LANGUAGE.md#24-method-chaining)):

  ```pengu
  import std.scrolls

  weave shorten with raw as string into string:
      return calling raw
          .trim
          .substring with 0, 2
  ```

- **Retornos múltiples** — declara un resultado tupla con `into (T, U)`, devuelve los valores separados por comas y desestructura con `let (q, ok) is …` ([§25](LANGUAGE.md#25-multiple-return-values)):

  ```pengu
  weave divide with a as int, b as int into (int, bool):
      if b == 0:
          return 0, false
      return (a / b), true

  weave use_div into int:
      let (q, ok) is calling divide with 10, 2
      if not ok:
          return 0
      return q
  ```

- **Inicializadores cortos de struct** — un campo cuyo hueco contiene un único nombre desnudo puede omitir `is <valor>`, así que `with name, hp` equivale a `with name is name, hp is hp` ([§26](LANGUAGE.md#26-shorthand-struct-initializers)).
- **Atributos de declaración** — `@noreturn` (un `weave` `void` que nunca retorna; emite `_Noreturn`), `@export("c_name")` (fija el símbolo C emitido y hace de la declaración una raíz de DCE), `@packed` (sin relleno entre campos) y `@align(N)` (potencia de dos entre 1 y 128) ([§27](LANGUAGE.md#27-function-attributes-noreturn-and-export), [§28](LANGUAGE.md#28-layout-attributes-packed-and-alignn)):

  ```pengu
  @export("pengu_add")
  weave add with a as int, b as int into int:
      return a + b

  @packed
  rune NetHeader:
      magic as u16
      version as u8
      flags as u8
      length as u32
  ```

- **Bloques de C embebidos (`antiquus`)** — una declaración cuyo cuerpo es C literal dentro de un string de comillas triples; usa `r"""…"""` cuando el C contenga barras invertidas. El cuerpo se emite tal cual y **no** se comprueba de tipos, que es el único cambio real de contrato de la 2.0 ([§9.6](LANGUAGE.md#96-antiquus--embedded-c-blocks)):

  ```pengu
  antiquus fast_abs with x as int into int:
      r"""
      return x < 0 ? -x : x;
      """
  ```

- **`cyclus`** — marca un tipo intencionadamente autorreferente; el ciclo debe romperse igualmente con indirección de puntero (`ref to`, `maybe ref to`, `slice`, `list`, `map`) ([§9.1.1](LANGUAGE.md#911-cyclus--self-referential-types)):

  ```pengu
  rune Node cyclus shard T:
      value as T
      next as maybe ref to Node of T
  ```

- **Bloques `unsafe:`** — la única forma en el lenguaje de renunciar a la verificación de límites; cada bloque avisa siempre `[W0007]` para que la exención sea visible en revisión ([§5.0](LANGUAGE.md#50-safety-guarantees-and-their-opt-outs)):

  ```pengu
  weave sum with xs as array of int, n as int into int:
      var acc as int is 0
      unsafe:
          for i from 0 to n:
              set acc is acc + (xs at i)
      return acc
  ```

- **`many T`** — `with xs as many T` hace variádico un `weave`; el punto de llamada enumera los argumentos con normalidad y el compilador los empaqueta en un slice temporal ([§8.2](LANGUAGE.md#82-declare--external-c-functions)):

  ```pengu
  weave count_args with xs as many int into int:
      return (xs length to int)
  ```

- **`--strict-c99`** — ⏸️ **no es funcional para programas que importan `std`** (medido: 34 de los 61 programas de `tests/std_programs/` fallan con `gcc -std=c99 -pedantic-errors`); aplazado a la 1.1. **No** lo uses como puerta de portabilidad en CI o en la publicación ([§20.2](LANGUAGE.md#202-compilation--build-profiles-pengu-build)).
- **Compilación cruzada** — `pengu build --target x86_64-w64-mingw32 --cc x86_64-w64-mingw32-gcc` selecciona el SO destino a partir de un triple; solo se admite **Linux ⇄ Windows** ([§20.2.3](LANGUAGE.md#2023-cross-compilation---target)).
- **Versionado del ABI del runtime** — `pengu_runtime.h` define `PENGU_ABI_VERSION`, el diseño congelado de los contenedores del runtime; cada bundle referencia `pengu_abi_version()`, así que una `libpengu_runtime.a` compilada contra otro ABI falla al enlazar en lugar de reinterpretar los campos de los structs ([§20.2.1](LANGUAGE.md#2021-runtime-abi-version)).
- **Diagnósticos JSON** — `pengu check --json` y `pengu build --json` emiten un objeto `{"type":"diagnostic",…}` por problema más una línea final de resumen, y nada más por stdout ([§20.2.2](LANGUAGE.md#2022-machine-readable-diagnostics---json)):

  ```bash
  pengu check --json | jq -c 'select(.type=="diagnostic") | {file,line,col,code}'
  ```

- **Enlace condicional** — el runtime principal no tiene dependencias externas de C: solo necesita libc, libm y pthreads/hilos de Win32, y un programa sin importaciones nativas enlaza únicamente `libpengu_runtime.a`, y por eso un `hello_world` sin símbolos pesa ~14 KiB (ver [BENCHMARKS.md](BENCHMARKS.md)). Los archivos nativos de los módulos satélite (instalados con `pengu add`) solo se enlazan cuando se importa el módulo que los declara.

### Características destacadas

- **Sintaxis pitónica basada en indentación** — sin puntos y coma ni llaves; los bloques se delimitan con espacios en blanco ([§3](LANGUAGE.md#3-lexical-structure)).
- **Seguridad de ámbito al estilo V** — `const` es estrictamente global (de nivel superior) y se convierte en un `#define` de C; `var` (mutable) y `let` (inmutable) son estrictamente locales al cuerpo de la función, lo que evita estado global mutable accidental ([§5](LANGUAGE.md#5-variables-constants--scope)).
- **Sistema de tipos expresivo** — enteros de ancho fijo (`u8`…`u64`, `i8`…`i64`), `f32`/`f64`, `char`, `byte`, `string`, `bool`; arrays 1D/2D de tamaño fijo, slices sin propiedad, listas dinámicas y mapas hash con estimación de diseño en tiempo de compilación ([§4](LANGUAGE.md#4-type-system)).
- **Tipos de usuario** — `rune` (structs) con campos privados `_` y bloques de métodos `enchanting` (`self->`), `echo` (uniones compatibles con C), `omen` (enumeraciones simples y tipos algebraicos con carga útil), y `maybe T` / `result of T to E` con desenvoltura mediante expresiones de sentencia (`or else`, `or return`, `try`) ([§9](LANGUAGE.md#9-composite-types), [§12](LANGUAGE.md#12-optionals--errors)).
- **Métodos y conceptos en tiempo de compilación** — `enchanting` asocia métodos a los structs; `concept` define interfaces en tiempo de compilación verificadas estáticamente con exhaustividad de `bind`, sin coste en tiempo de ejecución y sin tablas virtuales ([§10](LANGUAGE.md#10-methods-concepts--binding); consulta [§10.6 Limitaciones explícitas](LANGUAGE.md#106-limitaciones-explícitas-de-los-concepts)).
- **Cadenas construidas de una sola forma** — las cadenas dinámicas se componen **solo** con interpolación `"{expr}"`; `+`/`+=` sobre cadenas producen `E0005` (sin promoción implícita `to string` y sin temporales ocultos), y almacenar una `string` en un campo de struct o en un elemento de colección copia sus bytes con `memcpy` — liberar el original sigue siendo decisión tuya ([§15.2](LANGUAGE.md#152-strings)).
- **Genéricos sin coste** — declaraciones `shard` especializadas con `of`; cada instanciación se monomorfiza a C plano con validación de cotas de conceptos (`where T: Printable`) ([§11](LANGUAGE.md#11-generics)).
- **Limpieza determinista y manual** — `banish` libera un valor ahora; `defer banish` / `errdefer banish` difieren la liberación al salir del ámbito o a un retorno de error (LIFO). Nada se libera a tus espaldas ([§13](LANGUAGE.md#13-manual-memory-management)).
- **FFI de C de primera clase** — `include`/`link`/`declare`, tipos opacos (`alias … as opaque`), `sigil of` (dirección de) / `essence of` (desreferencia), préstamos sin copia con `bytes of <string>` y `weave`s que decaen a punteros a función de C ([§14](LANGUAGE.md#14-modules-imports--c-interop)).
- **`pengu bind`** — genera automáticamente un archivo de declaraciones `.d.pengu` a partir de cualquier cabecera de C (structs → `rune`, uniones → `echo`, enumeraciones → `omen`, funciones → `declare`, callbacks → `alias … as ref to weave`, conservando los comentarios de documentación) con blanqueo de extensiones del preprocesador, autoimportación de hermanos y opciones (`--define`, `--cpp-flags`, `--system-includes`, `--preprocessed`) ([§20.6](LANGUAGE.md#206-c-header-binding-generator-pengu-bind)).
- **Biblioteca estándar completa** — `std/` incluye **22 módulos puros de PenguScript** y **0 enlaces de declaraciones de C** (E/S, cadenas, archivos, matemáticas, tiempo, concurrencia, registro de logs, pruebas unitarias, …) ([§19](LANGUAGE.md#19-standard-library)). Los enlaces a bibliotecas externas de C (raylib, sqlite3, webui, miniaudio, etc.) viven ahora en repositorios satélite — consulta [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md).
- **Recursos embebidos del proyecto (`arca`)** — incrusta recursos binarios y de texto (texturas, shaders, audio, fuentes, HTML/JS/CSS, archivos de configuración) directamente en secciones `.rodata` nativas o los lee desde disco con vistas de puntero sin copia y accesores de slice ([§19.4](LANGUAGE.md#194-embedded-project-assets-arca)).
- **Servidor de lenguaje (LSP)** — diagnósticos con `help:`/`note:`/intervalos con cursor, documentación a partir de comentarios `#` y `##`, información emergente de tipos y tamaño en memoria, autocompletado con ámbito de módulo, ir a la definición, formateo y acciones de código ([§20.10](LANGUAGE.md#2010-language-server-protocol-pengu-lsp)).
- **Gestor de proyectos unificado** — la CLI `pengu` crea (`init`), compila (`build`), ejecuta (`run`), prueba (`test`), verifica (`check`), formatea (`fmt`), limpia (`clean`), documenta (`doc`), genera enlaces de C (`bind`) y lanza el servidor de lenguaje (`lsp`) ([§20](LANGUAGE.md#20-tooling--project-layout)).
- **Funciones en tiempo de compilación** — condicionales `when` con `else when` / `else`, `defined(...)`, definiciones `-D name=value`, estado `static var` de función y guardas `when main:` para archivos que sirven como módulo y como script ([§16](LANGUAGE.md#16-conditional-compilation-when)).
- **Diagnósticos robustos** — catálogo completo de errores al estilo de Rust con códigos `E0000`–`E0065` y advertencias `W0001` (transmute), `W0002` (acceso a echo), `W0004` (código inalcanzable), `W0005` (shadowing), `W0006` (uso de `@deprecated`), `W0007` (bloque `unsafe:`) ([§22](LANGUAGE.md#22-appendix-compiler-diagnostic-catalog)).

---

### Inicio rápido

#### Requisitos

- **Python 3.11+** (3.10 también funciona — allí `requirements.txt` instala automáticamente el backport `tomli`).
- Un **compilador de C** (`gcc` o `clang`) y un archivador estático (`ar`/`llvm-ar`) en tu `PATH` — en Windows usa el `gcc` de MinGW-w64. `gcc`/`clang` son los backends de referencia.
- **CMake y Ninja** — herramientas de compilación para los entornos de desarrollo soportados.
- **Node.js 18+ y npm** — solo se necesitan para desarrollar o empaquetar la extensión de VS Code.

##### Dependencias del sistema para Linux y macOS

En Linux y macOS, compilar el runtime del lenguaje solo necesita una cadena de herramientas de C más las herramientas de Python y Node — no hay bibliotecas de desarrollo externas que instalar:

**Fedora / RHEL:**
```bash
sudo dnf install -y @development-tools \
    cmake ninja-build gcc gcc-c++ python3 nodejs
```

**Ubuntu / Debian:**
```bash
sudo apt-get update && sudo apt-get install -y \
    build-essential cmake ninja-build gcc g++ python3 nodejs
```

**Arch Linux:**
```bash
sudo pacman -S --needed base-devel cmake ninja gcc python nodejs
```

**macOS (Homebrew):**
```bash
brew install cmake ninja python node
```

#### Configuración

```bash
git clone https://github.com/pengus-lang/penguscript.git
cd penguscript

# Create a virtual environment and install Python dependencies
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Build the C runtime into build/lib
python build_runtime.py

# Confirma la versión de la cadena de herramientas (imprime `pengu 2.0.0`);
# `pengu --version` es un alias.
pengu -V

# Run the test-suite (en paralelo; lee AGENT_TESTING.md antes de añadir tests)
pengu selftest
pytest tests/ -n auto
```

`pengu selftest --smoke` ejecuta el tier rápido (<3 s, sin compilador de C);
`pengu selftest --affected` ejecuta sólo lo que tus cambios pueden afectar. La
suite completa tarda ~4 min 37 s en paralelo frente a 34 min 19 s en serie.
`pengu test` es otro comando: compila *tu* proyecto y ejecuta sus bloques `test`.

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
| `add`      | Añade una dependencia o enlace externo (URL de git o carpeta local, con script de compilación opcional); el árbol de fuentes se copia en `lib/<name>/`. |
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

El ciclo principal es `init` → `build` → `run`/`test` → `check` → `fmt` → `doc`/`bind`/`lsp`; `pengu -V` (o `pengu --version`) imprime la versión de la cadena de herramientas.

Los proyectos se configuran con `pengu.toml` o `pengu.yaml` (mutuamente excluyentes; si existen ambos, gana `pengu.toml`; los ejemplos de la §14.4 de `LANGUAGE.md` usan YAML por brevedad) — punto de entrada, tipo y nombre de salida, includes, links, `cflags`/`defines` por perfil y selección de compilador. La verificación de límites se emite en **todos** los perfiles (`--profile release` no puede canjear seguridad de memoria por velocidad): `debug` (el predeterminado) conserva además `-g` y las trazas de pila, mientras que `release` añade `-O3`. Las únicas exenciones son un bloque `unsafe:` explícito o `--release-unsafe` ([§5.0](LANGUAGE.md#50-safety-guarantees-and-their-opt-outs)). Consulta [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md) para la guía completa.

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
  # mylib.d.pengu (excerpt)
  include "mylib.h"
  alias MylibState as opaque
  declare mylib_len with text as ref to char into size_t
  ```

  …y después, desde tu código:

  ```pengu
  import mylib
  var n as size_t is calling mylib.mylib_len with "PenguScript"
  ```

  Las cabeceras de C del mundo real se pueden convertir en enlaces así de forma automática con `pengu bind`.

#### ¿Por qué no ownership?

Rust hace que el compilador rastree cada préstamo y decida cuándo muere un valor.
PenguScript no: toma la ruta de Zig / Odin / Nelua y hace que la gestión de memoria sea
**manual**. El compilador se niega a adivinar, porque una suposición equivocada es o una
fuga silenciosa o un use-after-free — ambas peores que decir lo que querías. Asignas con
un constructor o `sigil of`, y liberas con `banish`:

```pengu
weave main into int:
    var s is "hello"
    defer banish s          # libera al salir del ámbito (LIFO); `banish s` libera ahora
    calling print with s
    return 0
```

`banish x` libera lo que `x` posee según su tipo estático y es una operación segura que
no hace nada sobre literales de cadena y vistas sin posesión. `defer banish` /
`errdefer banish` programan la liberación al salir del ámbito. Cuando quieras que un
destructor se escriba por ti, opta por ello por tipo con `derive Nexus`.

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
- `push`/`put` copian los bytes del elemento con `memcpy` y banish libera solo el
  búfer propio del contenedor, así que una `list of string` necesita un
  `pengu_banish_string_list` explícito (o un `banish` por elemento); consulta
  [LANGUAGE.md §13.5](LANGUAGE.md#135-containers-memcpy-on-store-explicit-release).
- `derive` funciona en runes, omens algebraicos e instanciaciones genéricas;
  `Imago` (copia en profundidad) y `Nexus` (drop) se implican mutuamente. Las
  uniones `echo` rechazan `derive` porque no llevan etiqueta.
- Iterar un parámetro de tipo desnudo (`for x in xs` con `xs as T`) se rechaza:
  usa `list of T` / `slice of T` (los tipos asociados son trabajo futuro).

El directorio `tests/test_generics/` contiene un programa ejecutable por
característica más comprobaciones de fugas; ejecútalos con
`python -m pytest tests/codegen/test_generics_suite.py`.

#### Biblioteca estándar

`std/` contiene **22 módulos puros de PenguScript** y **0 enlaces de declaraciones de C** (verificado: `ls std/*.pengu`). Consulta [LANGUAGE.md §19](LANGUAGE.md#19-standard-library) para el catálogo completo de módulos y ejemplos de código.

- **Módulos en PenguScript puro (22):** `spark` (E/S básica, salida formateada, entrada tipada, rangos y ayudas matemáticas), `scrolls` (algoritmos completos de manipulación de cadenas, métricas, capitalización y ordenación de cadenas a tres bandas), `oracle` (contenedores `Maybe`/`Result` con interoperabilidad nativa y heredada), `compass` (rutas multiplataforma y coincidencia de patrones), `archivum` (archivos, E/S binaria y recorrido de directorios), `cipher` (JSON RFC 8259, Base64/32/Hex y validación), `chronicle` (fechas, relojes de alta resolución, temporizadores y análisis de duraciones), `lot` (PRNG, distribuciones estadísticas, muestreo, barajado y cadenas aleatorias), `arithmancy` (matemáticas avanzadas), `rites` (procesos del SO, entorno e información del sistema multiplataforma), `whisper` (registro de logs estructurado por niveles y rune `Logger`), `ward` (invariantes defensivos, aserciones de flotantes/rangos/contenedores y pruebas genéricas `shard T`), `trial` (pruebas unitarias), `tally` (operaciones funcionales sobre listas, reducciones, ordenación por inserción y estadísticas), `atlas` (almacén clave-valor con mapas hash, combinación, accesores masivos y filtros), `coven` (colecciones únicas `SetString`/`SetInt`, constructores rituales y álgebra de conjuntos), `filum` (hilos, canales tipados, mutex y operaciones atómicas), `numerus` (métodos numéricos universales sobre todo primitivo con `enchanting shard T where T: Num and T: Ordo and T: Par:` — `abs`, `clamp`, `pow_int`, `floor`, `round`, predicados y conversiones, monomorfizado a `int_abs`, `f64_clamp`, …), `loom` (pipelines de secuencias, ventanas y algoritmos genéricos), `invoke` (análisis avanzado de CLI, subcomandos, flags tipados, multiopciones y sugerencias ante erratas), `ffi` (puente con C) y `ledger` (análisis de CSV/TSV, datos tabulares y encantamientos de matrices).
- **Los enlaces a bibliotecas externas de C (raylib, sqlite3, webui, miniaudio, etc.) viven ahora en repositorios satélite.** Consulta [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md); instala uno con `pengu add <url>` (el árbol de fuentes se copia en `lib/<name>/`).

Los 22 módulos incluyen documentación completa (docstrings `##`), cobertura de pruebas total en los perfiles de compilación `debug` y `release`, compatibilidad hacia atrás del 100 % con cada línea de versión publicada (fijada por `tests/migration/`) y cero advertencias del compilador de C.

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
├── build_runtime.py        # Compiles the C runtime into build/lib
├── extern_manifest.py      # Manifest + downloader infrastructure reused by satellite modules (-> extern/)
├── make_release.py         # One-shot release packager -> pengucc_build/ (see below)
├── std/                    # Standard library: 22 pure-PenguScript modules (0 C bindings)
├── c_bind_stubs/           # Minimal stub C headers used when `pengu bind` preprocesses
├── extern/                 # Downloaded third-party C library sources (gitignored)
├── build/                  # Generated output (gitignored):
│                           #   build/lib/libpengu_runtime.a + build/include/ headers
├── tests/                  # Python test-suite (pytest tests/): compiler, LSP, CLI,
│                           #   `pengu bind`, the std library & satellite modules
├── tests/std_programs/     # One PenguScript exercise program per std module
│                           #   (compiled & run by tests/stdlib/test_stdlib.py)
├── vscode-extension/       # VS Code extension (grammar, LSP client, project commands)
├── CHANGELOG.md            # Version history & feature log
├── CHEATSHEET.md           # Full language syntax & C-translation reference
└── docs/                   # Build guide, performance/fuzzing notes & archived docs
    ├── PENGU_BUILD.md      # Build system & project configuration guide
    ├── README_RELEASE.md   # Generated: standalone release package documentation
    └── archive/            # Historical, non-normative process documents
```

---

### Compilar el runtime desde el código fuente

`build_runtime.py` produce el archivo estático que `pengu` enlaza en cada binario. El runtime **no tiene dependencias externas de C** — solo necesita libc, libm y pthreads/hilos de Win32 —, así que hay una única etapa de compilación: `build_pengu_runtime` compila `pengu_runtime.c` con `gcc`/`clang` + `ar` en `build/lib/libpengu_runtime.a` y prepara las cabeceras en `build/include/`:

```bash
python build_runtime.py            # build the runtime
python build_runtime.py --rebuild  # force a clean rebuild (~1.4 s, down from ~5–8 min)
```

`build_pengu_runtime` produce únicamente `libpengu_runtime.a`. Los archivos nativos de bibliotecas externas de C no se incluyen aquí: se instalan por proyecto desde repositorios satélite con `pengu add` (consulta [`docs/EXTERNAL_MODULES.md`](docs/EXTERNAL_MODULES.md)).

> `extern_manifest.py` y su manifiesto ahora vacío se conservan para que los repositorios satélite reutilicen la infraestructura de descarga/hash; la compilación principal no descarga ni compila nada.

**Publicaciones** — `make_release.py` automatiza toda la distribución: verifica e instala las dependencias de Python, recompila el runtime (`--rebuild`), ejecuta pruebas de humo, empaqueta la CLI + el LSP en un ejecutable independiente con PyInstaller (`pengu` / `pengu.exe`) y compila la extensión de VS Code (`pengus-<version>.vsix`). Todo queda en `pengucc_build/`:

```bash
python make_release.py
```

```text
pengucc_build/
├── pengu (.exe)          # Standalone PenguScript CLI & LSP server
├── pengus-<version>.vsix # VS Code extension
├── std/                  # Complete standard library modules
└── runtime/              # C runtime headers + static library (build/lib)
```

Consulta [docs/README_RELEASE.md](docs/README_RELEASE.md) para la documentación propia de la distribución.

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

| Documento                                                | Qué cubre                                                                     |
| -------------------------------------------------------- | ----------------------------------------------------------------------------- |
| [LANGUAGE.md](LANGUAGE.md)                               | Especificación completa del lenguaje, biblioteca estándar y diagnósticos      |
| [CHEATSHEET.md](CHEATSHEET.md)                           | Sintaxis completa del lenguaje, palabras clave y referencia de traducción a C |
| [BENCHMARKS.md](BENCHMARKS.md)                           | Mediciones publicadas de compilación, ejecución y tamaño de artefacto         |
| [docs/DEPRECATIONS.md](docs/DEPRECATIONS.md)             | Política de obsolescencia, alias `@deprecated` y ventanas de eliminación      |
| [docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md)     | Módulos satélite de enlaces C: instalación y uso con `pengu add`              |
| `MIGRATION.md`                                           | Guía de migración entre líneas de versión publicadas (nombrada; se conserva junto al corpus en `tests/migration/`) |
| [VERSION](VERSION)                                       | La única fuente de verdad de la versión de la cadena de herramientas          |
| [docs/PENGU_BUILD.md](docs/PENGU_BUILD.md)               | CLI `pengu`, configuración de proyecto y sistema de compilación               |
| [CHANGELOG.md](CHANGELOG.md)                             | Historial de versiones y registro de características por publicación          |
| [docs/README_RELEASE.md](docs/README_RELEASE.md)         | El paquete de publicación independiente `pengucc_build/`                      |
| [vscode-extension/README.md](vscode-extension/README.md) | Extensión de VS Code: características, configuración, instalación             |

---

### Agradecimientos y créditos a terceros

La cadena de herramientas, el runtime de C y la biblioteca estándar de PenguScript se apoyan en muchos proyectos de código abierto excelentes. Agradecemos y reconocemos con gusto a sus autores. Los nombres de licencia que aparecen abajo son los publicados por cada proyecto original.

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

---

### Licencia

PenguScript se publica bajo la **[Licencia MIT](LICENSE)** — © 2026 TuGatito. Los módulos satélite instalados desde repositorios de terceros con `pengu add` son proyectos independientes y conservan sus propias licencias (consulta cada repositorio satélite).
