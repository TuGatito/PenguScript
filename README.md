<p align="center">
  <img src="vscode-extension/icons/pengu_icon.png" width="160" alt="PenguScript logo">
</p>

<h1 align="center">🐧 PenguScript</h1>

<p align="center">
  A small, explicit language that compiles to readable C.<br/>
  No garbage collector, no hidden allocations, no framework: values you can
  point at, memory you can audit, and a compiler you can read.
</p>

<p align="center">
  <a href="docs/LANGUAGE.md">📖 Language reference</a> ·
  <a href="docs/PENGUNIC.md">🐧 Pengunic manual</a> ·
  <a href="docs/STDLIB.md">📚 Standard library</a> ·
  <a href="docs/psc/README.md">🧱 Compiler internals</a> ·
  <a href="CHANGELOG.md">📓 Changelog</a>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-0.27.0-informational">
  <img alt="Compiler" src="https://img.shields.io/badge/compiler-self--hosted%20PSC-blueviolet">
  <img alt="Targets" src="https://img.shields.io/badge/targets-Linux%20%7C%20macOS%20%7C%20wasm-blue">
</p>

---

## Why PenguScript

- **It compiles to C you would write by hand.** One bundle per project, `#line`
  per statement, no runtime reflection, no code generation tricks.
- **Ownership is explicit.** `banish` frees; `defer` and `errdefer` make exit
  paths visible; copying a `string` copies a handle, and the manual tells you
  exactly what that means.
- **Errors are values.** `maybe T` and `result of T to E` instead of exceptions;
  `or else`, `or return`, `try` and `or:` keep the happy path linear.
- **Types are nominal when you want them to be.** `rune`, `echo`, `omen`,
  `seal`, `concept`, `shard` — each one has a precise cost and a precise C
  lowering.
- **The toolchain is one binary.** Build, run, test, format, document, bind C
  headers, drive an LSP and manage dependencies with `psc`.

```pengu
import std.spark

rune Task:
    title as string
    done as bool

weave main into int:
    var tasks as list of Task is list of Task
    defer banish tasks

    var t as Task with:
        set .title is "write docs"
        set .done is false
    calling tasks.push with t

    for task in tasks:
        calling spark.println with "{task.title}"

    return 0
```

## Contents

| | |
| --- | --- |
| [Install](#install) | Build the toolchain and put `psc` on your `PATH` |
| [Quick start](#quick-start) | A project in four commands |
| [CLI guide](#cli-guide) | Every `psc` command, with examples |
| [Platforms and targets](#platforms-and-targets) | Linux, macOS, WebAssembly |
| [Documentation](#documentation) | The three books, in English and Spanish |
| [Repository layout](#repository-layout) | Where everything lives |
| [Dependencies](#dependencies) | `pengu.toml`, `pengu.lock`, vendored C |
| [Status](#status) | What works today |

## Install

### Requirements

| Need | Why |
| --- | --- |
| A C compiler (`cc`, `gcc` or `clang`) and `ar` | the runtime, the bootstrap and every build |
| `bash` (Linux/macOS) or PowerShell (Windows) | the build scripts |
| `git` | dependencies and the checkout itself |
| Emscripten (`emcc`, `emar`) | optional, only for `--target wasm` |
| `libclang` | optional, only for `psc bind` |
| Node.js 20+ | optional, to run wasm builds headlessly |

Nothing else: no Python, no package manager, no pre-installed runtime.

### One command

```bash
git clone https://github.com/TuGatito/PenguScript.git
cd PenguScript
./tools/build.sh
```

`tools/build.sh` is the supported way to install a development toolchain. It:

1. builds the native runtime (`build/lib/libpengu_runtime.a`) and the checked-in
   stage0 bootstrap (`build/psc-stage0`);
2. builds the self-hosted compiler → **`build/psc`**;
3. builds `build/pengu-bind` when libclang is available (optional);
4. builds the WebAssembly runtime when `emcc` is on `PATH` (optional);
5. writes `build/env/pengu.env.{sh,fish,ps1,json}` and **appends a small block
   to your shell startup files** (bash, zsh, fish, PowerShell) that sources it;
6. prepends `build/` to `PATH`, so `psc` works from any directory.

Open a new terminal, or reload the current one:

```bash
. "$HOME/.config/pengu/env.sh"     # bash / zsh
source "$HOME/.config/pengu/env.fish"
```

Verify:

```console
$ psc version
psc 0.27.0 (F13)
$ psc doctor
[ok] gcc: /usr/bin/gcc
[ok] runtime-archive: .../build/lib/libpengu_runtime.a
[ok] std: found
```

`psc doctor --target wasm` checks the Emscripten side as well.

### Options

```text
./tools/build.sh [--debug] [--no-bind] [--no-wasm] [--no-register]
                 [--shells auto|bash,zsh,fish] [--jobs N] [--cc CMD]
```

| Flag | Effect |
| --- | --- |
| `--debug` | build `psc` with the `debug` profile |
| `--no-bind` | skip the optional `pengu-bind` helper |
| `--no-wasm` | skip the optional wasm runtime |
| `--no-register` | write `build/env/*` but do not touch your shell rc files |
| `--shells bash,zsh` | restrict which startup files are edited |
| `--jobs N` | parallel C compilations |
| `--cc CMD` | C compiler to use (`gcc`, `clang`, `cc`, …) |

The environment it exports:

| Variable | Points at |
| --- | --- |
| `PENGU_HOME` | the checkout |
| `PENGU_STD_DIR` | `std/` |
| `PENGU_INCLUDE_DIR` | `build/include` (`pengu_runtime.h`, `sds.h`, …) |
| `PENGU_LIB_DIR` | `build/lib` (`libpengu_runtime.a`, satellites) |
| `PENGU_PSC` | `build/psc` |
| `PENGU_BIND` | `build/pengu-bind`, when built |
| `PENGU_RUNTIME_CROSS` | `build/wasm`, when built |

To keep the toolchain isolated, use `--no-register` and source
`build/env/pengu.env.sh` from the project that needs it. To uninstall, remove
the checkout and delete the `# >>> PenguScript toolchain >>>` block from your
shell startup file.

### Windows

```powershell
.\tools\build.ps1
```

It builds `build\psc.exe`, writes `build\env\pengu.env.ps1`, and registers the
environment in your PowerShell profile. `-NoRegister`, `-NoBind` and `-NoWasm`
behave like their Unix counterparts. Windows support is best-effort: Linux and
macOS are the tested platforms.

### Manual bootstrap (CI, packaging)

```bash
./tools/build_bootstrap.sh      # C runtime + build/psc-stage0
./build/psc-stage0 build .      # self-hosted compiler → build/psc
./build/psc version
```

The compiler is self-hosted and reproducible: stage0 (checked-in C bundles)
builds `psc`, and `psc` must rebuild itself to the same result.
`tools/gen_stage0.sh --check` verifies the committed bundles are current.

Release tarballs unpack into a `bin/` layout with the same environment files,
so the `psc version` check above applies unchanged.

## Quick start

```bash
psc init hello
cd hello
psc build
./build/hello
```

```console
$ ./build/hello
hello, pengu
```

The generated project is small on purpose:

```text
hello/
├── pengu.toml          manifest: name, entry, output, build flags, profiles
├── src/main.pengu      the program
└── build/              artifacts (ignored by git)
```

```toml
# pengu.toml
[project]
name = "hello"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
output_name = "hello"

[build]
src_dir = "src"
cflags = ["-Wall", "-std=c11"]
cc = "gcc"

[profiles.release]
cflags = ["-O3", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"]
defines = ["NDEBUG"]
```

```pengu
# src/main.pengu
import std.spark

weave main into int:
    calling spark.println with "hello, pengu"
    return 0
```

Other templates:

```bash
psc new cli mytool          # argument parsing with std.invoke
psc new pengu-lib mylib     # output = "static", public API + tests
psc new cbind mybind        # C header + .d.pengu skeleton
```

## CLI guide

`psc` is a single binary. `psc <command> --help` prints the exact flags.

```text
psc 0.27.0 — PenguScript compiler

  lex parse check emit-c expand   compiler stages
  build run test                  compile, execute, test
  fmt doc assets                  formatter, API docs, embedded assets
  init new clean doctor metadata  project lifecycle
  add remove update upgrade       dependencies
  verify vendor                   lockfile checks, offline copies
  lsp bind                        editor server, C header bindings
  eval time watch gc tree         inspection and profiling
  benchmark selftest version      health checks
```

### Compile and run

| Command | What it does |
| --- | --- |
| `psc build [TARGET]` | compile a file or project; writes the artifact from `output` |
| `psc run [TARGET] [-- args]` | build and execute, forwarding arguments after `--` |
| `psc check [TARGET]` | lex, parse and check types/semantics only |
| `psc test [TARGET]` | run every `test` block; `--json` for machine output |
| `psc expand [TARGET]` | emit the single C bundle (`--library` for a library) |
| `psc emit-c FILE` | emit C for one file (`--stdout`, `--out=FILE`) |

```bash
psc build                                  # project in the current directory
psc build src/main.pengu --profile=release
psc run -- --verbose --port 8080           # args go to the program
psc test --json
psc emit-c src/main.pengu --stdout | head -40
```

Useful build flags:

| Flag | Meaning |
| --- | --- |
| `--target=TRIPLE\|wasm` | host target or `wasm32-unknown-emscripten` |
| `--profile=debug\|release` | optimisation and checks |
| `--out=PATH` | artifact path |
| `--cc=NAME` | C compiler (`gcc`, `clang`, `cc`, …) |
| `--strict-c99` | portable C99 instead of GNU extensions |
| `--release-unsafe` | disable bounds/overflow checks (release only) |
| `--verbose` | print the exact `cc` command |

`psc check --diagnostics=json` emits machine-readable diagnostics for CI.
Targets are LLVM-style triples (`--target=x86_64-linux-gnu`) or `wasm`.

### Format, document, assets

```bash
psc fmt src/                 # rewrite in place
psc fmt --check --diff       # CI gate: exit 1 if formatting would change
psc fmt --stdin < a.pengu    # filter
psc doc --include-std --html # docs/api for the project and the stdlib
psc assets --list            # files embedded from the assets directory
psc assets                   # regenerate src/<module>.pengu + build/*.c
```

`psc fmt` reads `.pengufmt.toml` upward from the file: `indent`/`tab_size`,
`tabs`, `insert_spaces`, `blank_lines_max`.

### Projects and toolchain health

```bash
psc init hello --template=exe
psc new cli mytool
psc clean --dry-run
psc doctor --json
psc metadata --json
psc version
```

`psc doctor` checks the C compiler, the runtime archive, the headers and the
standard library; with `--target wasm` it checks `emcc`, `emar`, the wasm
runtime and Node.

### Dependencies

```bash
psc add https://example.com/lib.git --version="^1.0"
psc add ../local-lib --name=locallib
psc update --trust
psc upgrade locallib --branch=main
psc verify --verbose
psc vendor
psc build --locked
```

Dependencies live in `lib/`, pinned by `pengu.lock`. `--locked` and `--frozen`
fail with `E0061` when the lockfile is missing or stale. `psc vendor` copies
everything into `vendor/` for offline builds.

### Inspect and profile

```bash
psc eval "1 + 2 * 3"        # evaluate a constant expression
psc time src/main.pengu     # phase timings for one compilation
psc watch src/main.pengu    # rebuild on change
psc tree                    # module/dependency tree
psc gc --all                # prune caches
psc benchmark --help        # micro-benchmark harness
psc selftest                # compiler self-checks
```

### Editors and C interop

```bash
psc lsp                                   # stdio (editors start this)
psc lsp --tcp --port=9257                 # TCP for remote use
psc bind mylib.h --prefix mylib_ --output std/mylib.d.pengu
psc bind mylib.h --print-helper           # show the pengu-bind command
```

`psc bind` needs `build/pengu-bind` (built by `tools/build.sh` when libclang is
present) or a binary named by `PENGU_BIND`. The VS Code client lives in
[`vscode-extension/`](vscode-extension/).

### Exit status

`0` on success. `1` on diagnostics, failed tests or `psc fmt --check`
differences. Diagnostics carry a source span, a note and a help line:

```console
error[E0020]: return value of type 'string' does not match 'int'
  --> src/main.pengu:7:12
   |
 7 |     return name
   |            ^^^^
```

## Platforms and targets

| Platform | Status | Notes |
| --- | --- | --- |
| **Linux x86_64** | Primary | full test suite, `gcc` and `clang` |
| **macOS arm64** | Supported | CI matrix, Apple clang |
| **Windows** | Best-effort | MSYS2 + `tools/build.ps1`; not in CI |
| **WebAssembly** | Supported | `wasm32-unknown-emscripten` via Emscripten |

Build outputs: `exe`, `c`, `obj`, `static` (`output = "…"` in `pengu.toml`, or
`psc init --type=`). `shared` is not supported for wasm.

### WebAssembly

`psc` emits one C11 bundle and `emcc` turns it into `build/<name>.html` +
`build/<name>.js` + `build/<name>.wasm`; the same program runs under Node for
tests.

```bash
# once: install and activate the Emscripten SDK
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk && ./emsdk install latest && ./emsdk activate latest
source ./emsdk_env.sh && cd -

# build the wasm runtime (kept out of build/lib on purpose)
./tools/build_runtime_wasm.sh      # build/wasm/lib/libpengu_runtime.a

# compile, run, test
psc build --target wasm            # build/<name>.html + .js + .wasm
psc run   --target wasm            # runs `node app.js`
psc test  --target wasm
psc doctor --target wasm
```

`wasm`, `wasm32` and `emscripten` are accepted shorthands, and the target can
live in `pengu.toml`:

```toml
[build]
target = "wasm32-unknown-emscripten"
```

With `--target wasm`, `when wasm:`, `when wasm_target == "emscripten":` and
`when compiler == "emcc":` are active, and the browser modules become
available: `std.web.js`, `dom`, `event`, `http`, `websocket`, `storage`,
`canvas`, `crypto`, `browser`, `location`, `history`, `router`, `file`,
`clipboard`, `url` and `security`.

| On wasm | Status |
| --- | --- |
| `std.net`, `std.dynlib`, `std.ffi_call`, `std.secrets`, `std.petitio` | rejected with an actionable message |
| `std.filum` | works with `-pthread`; browsers need COOP/COEP |
| `shared` libraries | refused |
| WASI | recognised and refused |

See [docs/WASM.md](docs/WASM.md) for the full matrix and troubleshooting.

## Documentation

Every document exists in English and Spanish, with identical structure and
examples.

| Document | Answers | Español |
| --- | --- | --- |
| [docs/LANGUAGE.md](docs/LANGUAGE.md) | Every construct: syntax, semantics, lowering to C, diagnostics. | [LANGUAGE.es.md](docs/LANGUAGE.es.md) |
| [docs/PENGUNIC.md](docs/PENGUNIC.md) | How to write safe, idiomatic, fast PenguScript: toolchain, style, memory, tests, libraries, bindings. | [PENGUNIC.es.md](docs/PENGUNIC.es.md) |
| [docs/STDLIB.md](docs/STDLIB.md) | All 67 standard modules: what each is for, when to use it, generated API. | [STDLIB.es.md](docs/STDLIB.es.md) |
| [docs/api/](docs/api/) | API page per module, generated by `psc doc --include-std`. | — |
| [docs/psc/](docs/psc/) | Compiler internals: AST, sema, codegen, modules, parity. | — |

The generated pages are committed and checked in CI
(`tools/docs/gen_api.sh --check`); the three books are validated by
`tools/docs/validate_docs.py` and `tools/docs/check_links.sh`.

## Repository layout

```text
src/                 compiler, self-hosted in PenguScript
std/                 standard library
std_c/               vendored C and C-backed modules
runtime/             C runtime (pengu_runtime.c)
bootstrap/           checked-in stage0 C bundles per platform
c_bind_stubs/        minimal headers for `psc bind`
tests/               PSC tests, conformance corpus, fixtures, wasm suite
tools/               bootstrap, build, release and documentation helpers
docs/                language, manual, stdlib, API and compiler docs
vscode-extension/    editor client
```

## Dependencies

`pengu.toml` is the only manifest format; `pengu.yaml`, `pengu.yml` and
`pengu.json` are rejected.

```toml
[dependencies.mylib]
url = "https://example.com/mylib.git"
version = "^1.0"          # or branch = "main" / tag = "v1.2.0"
```

Local paths use `path = "../mylib"`. Everything is resolved into `lib/` and
pinned by `pengu.lock`.

### Vendored C libraries

The runtime is self-contained: `libpengu_runtime.a` carries the string backend
(**SDS**, BSD-2-Clause), the container adapter (**Convenient Containers**,
MIT), high-precision time (**vaqt**, BSD-3-Clause) and miniz for compression, so
user projects link only `-lpengu_runtime`. See
[docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md) and
[THIRD_PARTY.md](THIRD_PARTY.md).

## Credits

PenguScript's strings are built on **SDS — Simple Dynamic Strings**, created by
[Salvatore Sanfilippo](https://github.com/antirez), improved by Oran Agra and
maintained by the Redis community. Lists, maps and sets use **Convenient
Containers** by [Jackson L. Allan](https://github.com/JacksonAllan).
High-precision time uses **vaqt** by
[Anton Zhiyanov](https://github.com/nalgeon). Optional native calls use
**libffi**; secure randomness uses **libsodium**; header bindings use
**libclang**. Thank you all for building small, sharp, permissively licensed
tools.

## Status

- Lexer, parser, semantic analysis, C codegen, formatter, docs, assets, LSP,
  package manager and test runner are self-hosted PSC.
- The bootstrap and release pipeline use PSC, not Python.
- WebAssembly and the typed `std.web.*` modules are covered by the wasm suite.
- Linux is the primary tested platform; macOS is covered by CI; Windows is
  best-effort.
- `psc test` runs `test` blocks per module; `tests/run.sh` runs the PSC suite.

## License

MIT. See [LICENSE](LICENSE).
