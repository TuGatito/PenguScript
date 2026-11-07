<div align="center">

# 🐧 PenguScript

**A small, fast, self-hosted systems language that compiles to readable C.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.41.0-4c1.svg)](CHANGELOG.md)
[![Platforms](https://img.shields.io/badge/platforms-Linux%20%7C%20macOS%20%7C%20Windows%20%7C%20WASM-2ea44f.svg)](#-supported-platforms)
[![Docs](https://img.shields.io/badge/docs-English%20%2B%20Español-blueviolet.svg)](docs/README.md)

[Documentation](docs/README.md) · [Language reference](docs/LANGUAGE.md) ·
[Standard library](docs/STDLIB.md) · [CLI](docs/psc/CLI.md) ·
[Changelog](CHANGELOG.md) · [Contributing](#-contributing)

</div>

---

PenguScript is a statically typed language with explicit ownership, first-class
coroutines, real threads, generics, pattern matching and painless C interop. It
is **written in itself**: the compiler (`psc`, ~51k lines) is PenguScript that
compiles to C, and a checked-in stage-0 bootstrap keeps the project buildable
from a plain C compiler.

```pengu
weave main into int:
    calling print with "Hello, 🐧!"
    return 0
```

```console
$ psc run hello.pengu
Hello, 🐧!
```

- 🧠 **Predictable semantics.** No garbage collector, no hidden allocations;
  `own`, `ref`, `borrow` and `banish` are checked by the compiler.
- 🪶 **Small runtime.** One static library, no VM, no JIT, sub-second warm builds.
- 🧵 **Concurrency that fits.** Stackful coroutines (`std.coro`), an explicit
  event loop (`std.reactor`) and OS threads with channels and atomics
  (`std.filum`), all first-class.
- 🔌 **C without glue.** `psc bind`, `std.ffi`, `std.cc` and direct `c_dir`
  compilation; headers and libraries come straight from `pengu.toml`.
- 🌐 **WebAssembly.** One flag produces an `.html`/`.js`/`.wasm` bundle.
- 🧰 **Batteries included.** 50+ standard modules: JSON, HTTP, TLS, SQLite,
  compression, regex, dates, crypto, testing, packaging and more.
- 🐧 **Self-hosted and reproducible.** Byte-identical builds for the same
  toolchain, a stage-0 path that needs only `cc`, and a content-addressed cache.

## 📦 Supported platforms

| Platform | Architecture | Status | Notes |
|---|---|---|---|
| 🐧 Linux | x86_64 | ✅ Tier 1 | Primary development and CI target |
| 🐧 Linux | aarch64 | ✅ Tier 1 | Cross-compile with `aarch64-linux-gnu-gcc`; native CI |
| 🍎 macOS | Apple Silicon (arm64) | ✅ Tier 1 | Native `macos-14` CI runner |
| 🍎 macOS | Intel (x86_64) | ✅ Tier 1 | Native CI |
| 🪟 Windows | x86_64 | ⚠️ Best effort | MinGW cross build; no CI runner yet |
| 🌐 WebAssembly | wasm32 (Emscripten) | ✅ Supported | Browsers, Node and workers |
| 🌐 WebAssembly | wasm32-wasi | 🚧 Planned | Recognised and rejected with a clear error |

Requirements to build the compiler: a C11 compiler (`gcc` or `clang`), a POSIX
shell, and `python3` for some tooling. No pre-built `psc` is required — the
bundled stage-0 compiler is plain C.

## 🚀 Installation

### From source (recommended)

```console
$ git clone https://github.com/TuGatito/PenguScript.git
$ cd PenguScript
$ ./tools/build.sh
```

`tools/build.sh` builds the stage-0 bootstrap, the compiler, the native runtime,
the C satellites, the WebAssembly runtime (when `emcc` is available) and writes
a shell environment file. It offers to register that environment in your shell
rc; pass `--no-register` to skip it. To try the compiler in the current shell:

```console
$ export PATH="$PWD/build:$PATH"
$ psc version
psc 0.41.0
```

Useful flags:

```console
$ ./tools/build.sh --debug          # -O0 -g compiler, faster to rebuild
$ ./tools/build.sh --no-wasm        # skip the Emscripten runtime
$ ./tools/build.sh --no-bind        # skip the libclang binding helper
$ ./tools/build.sh --jobs 8         # parallel C compilation
$ ./tools/build.sh --cc clang       # choose the host C compiler
```

### From a release tarball

Download the archive for your platform from
[Releases](https://github.com/TuGatito/PenguScript/releases), unpack it and add
`bin/` to `PATH`:

```console
$ tar xf pengu-0.41.0-linux-x86_64.tar.gz
$ export PATH="$PWD/pengu-0.41.0-linux-x86_64/bin:$PATH"
$ psc doctor
```

The portable layout keeps everything under one directory; the FHS layout
installs into `bin/`, `lib/pengu/`, `include/pengu/` and
`share/pengu/`. Release packaging honours `SOURCE_DATE_EPOCH` for reproducible
archives.

### Editor support

The VS Code extension lives in [`vscode-extension/`](vscode-extension/) and
starts `psc lsp` automatically. Any LSP client works:

```console
$ psc lsp --stdio
$ psc lsp --tcp --host=127.0.0.1 --port=2087
```

## ⚡ Quick start

```console
$ psc init hello
$ cd hello
$ psc run .
```

`psc init` creates:

```
hello/
├── pengu.toml
└── src/
    └── main.pengu
```

```toml
# pengu.toml
[build]
entry = "src/main.pengu"
output = "exe"
name = "hello"
```

A slightly larger example:

```pengu
rune Point:
    x as int
    y as int

weave length with p as Point into float:
    var dx as float is (p.x to float)
    var dy as float is (p.y to float)
    return sqrt with dx * dx + dy * dy

weave main into int:
    var p as Point is with x is 3, y is 4
    calling print with "length = {length with p}"
    return 0
```

## 🛠️ CLI at a glance

| Command | What it does |
|---|---|
| `psc init <name>` | Create a new project. |
| `psc new <template> <name>` | Create from a template. |
| `psc build [TARGET]` | Build the project (incremental, cached). |
| `psc run [TARGET] [-- args]` | Build and run. |
| `psc test [TARGET]` | Build and run `test` blocks. |
| `psc test . --coverage` | Line coverage mapped to `.pengu` files. |
| `psc check <file>` | Parse, resolve and type-check only. |
| `psc expand [TARGET]` | Print the generated C bundle. |
| `psc debug [TARGET]` | Build with DWARF and start `gdb`/`lldb`. |
| `psc fmt [PATHS]` | Format sources. |
| `psc lsp` | Start the language server. |
| `psc doc` | Generate API documentation. |
| `psc add` / `remove` | Manage dependencies (`pengu.lock`). |
| `psc gc` | Prune the artifact cache. |
| `psc doctor` | Diagnose the toolchain. |
| `psc benchmark` | Run the runtime benchmark suite. |

Common build flags: `--profile=debug|release`, `--target=<triple>|wasm`,
`--no-cache`, `--clear-cache`, `--ephemeral`, `--sanitize=address|undefined|thread`,
`--coverage`, `--frozen`, `--locked`, `--verbose`.

```console
$ psc build . --profile=release
$ psc run examples/coroutines.pengu
$ psc test . --sanitize=address
$ psc build . --target=aarch64-unknown-linux-gnu
$ psc build . --target=wasm32-unknown-emscripten
$ psc debug . -- --my-flag
```

## 🌐 WebAssembly

```console
$ psc build . --target=wasm32-unknown-emscripten
$ psc run . --target=wasm32-unknown-emscripten
```

This produces `build/app.html`, `build/app.js` and `build/app.wasm`. Node,
browsers and web workers are supported; `std.web.js` exposes typed calls into
JavaScript. DOM/WebGL programs run with `psc run . --browser`. See
[docs/WASM.md](docs/WASM.md).

## 🐧 Cross-compilation

Native cross builds are supported for the usual C toolchains:

```console
$ psc build . --target=x86_64-unknown-linux-gnu
$ psc build . --target=aarch64-unknown-linux-gnu
$ psc build . --target=aarch64-apple-darwin
$ psc build . --target=x86_64-w64-mingw32   # best effort
```

Linux ARM64 needs a cross gcc and a runtime archive:

```console
$ CC=aarch64-linux-gnu-gcc AR=aarch64-linux-gnu-ar \
  RUNTIME_OUT=build/lib/aarch64-unknown-linux-gnu \
  bash tools/build_runtime.sh
$ psc build . --target=aarch64-unknown-linux-gnu
```

See [docs/CROSS_COMPILE.md](docs/CROSS_COMPILE.md) for the full matrix and CI
recipes.

## 🔁 Reproducible and incremental builds

* A warm build of the compiler itself is **~0.24 s** (down from ~30 s).
* Two builds of the same tree produce **byte-identical** binaries with the same
  toolchain; `SOURCE_DATE_EPOCH` is honoured when packaging.
* The cache key covers sources, headers, flags, runtime and toolchain — but not
  `build/`, so build outputs never invalidate it.
* `psc build --split-codegen --jobs=N` compiles one C unit per module in
  parallel and caches each object (`unit-object-v1`). On the compiler itself a
  split rebuild with all units reused takes ~14.8 s versus ~19.9 s for the
  single translation unit.
* `psc build --frozen` refuses to touch `pengu.lock`; `--locked` refuses to
  update a stale lock.

Run `./tools/bench.sh . --gate-warm 2000 --gate-check 1000` for a reproducible cold/hot
measurement (the same gate runs in CI). Read
[docs/BUILD_CACHE.md](docs/BUILD_CACHE.md) for the key layout, `psc gc` and
troubleshooting.

## 🧪 Testing, coverage and sanitizers

```console
$ psc test .                       # test blocks
$ psc test . --coverage            # gcov mapped to .pengu lines
$ psc test . --sanitize=address    # ASan
$ psc test . --sanitize=undefined  # UBSan
$ psc test . --sanitize=thread     # TSan (threads; not fiber tests)
```

Coverage and sanitizer details: [docs/COVERAGE.md](docs/COVERAGE.md),
[docs/SANITIZERS.md](docs/SANITIZERS.md).

Run the compiler's own suite:

```console
$ ./tests/run.sh
$ ./tests/regress.sh
$ python3 tests/lsp/run_lsp_tests.py
```

## 🧭 Debugging

```console
$ psc debug .                # build with -g, start gdb
$ psc debug . --llvm         # lldb
$ psc debug . -- --verbose   # program arguments
```

Breakpoints work on `.pengu` files and source lines:

```console
(gdb) break src/main.pengu:12
(gdb) run
(gdb) bt
```

See [docs/DEBUGGER.md](docs/DEBUGGER.md) for fibers, sanitizers and release
symbols.

## 📚 Documentation

Everything is in [`docs/`](docs/README.md), in **English and Spanish**:

| Document | Contents |
|---|---|
| [LANGUAGE.md](docs/LANGUAGE.md) | Every construct, its semantics, lowering and diagnostics. |
| [PENGUNIC.md](docs/PENGUNIC.md) | Idioms, ownership, memory, tests, libraries, bindings, performance. |
| [STDLIB.md](docs/STDLIB.md) | Every standard module and where its API lives. |
| [docs/api/](docs/api/) | Generated API reference, one page per module. |
| [WASM.md](docs/WASM.md) | WebAssembly targets, JS interop, browser runners. |
| [LSP.md](docs/LSP.md) | Language server features and protocol. |
| [CROSS_COMPILE.md](docs/CROSS_COMPILE.md) | Native cross builds. |
| [COVERAGE.md](docs/COVERAGE.md) · [SANITIZERS.md](docs/SANITIZERS.md) · [DEBUGGER.md](docs/DEBUGGER.md) | Observability. |
| [BUILD_CACHE.md](docs/BUILD_CACHE.md) | Incremental builds and reproducibility. |
| [psc/](docs/psc/) | Compiler internals: AST, sema, types, codegen, modules, ownership. |
| [CARMEN.md](docs/CARMEN.md) · [EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md) · [LIBRARIES.md](docs/LIBRARIES.md) | ABI, bindings and packaging. |

The Spanish editions are `LANGUAGE.es.md`, `PENGUNIC.es.md`, `STDLIB.es.md` and
`LIBRARIES.es.md` next to their English counterparts.

## 📁 Repository layout

```
src/                 compiler sources (PenguScript)
  main.pengu         CLI entry point
  psc/               lexer, parser, sema, codegen, driver, LSP, cache
std/                 standard library (50+ modules, PenguScript)
runtime/             C runtime (strings, containers, coroutines, threads, JSON)
std_c/               vendored C libraries (SDS, CC, miniz, libffi, minicoro, …)
bootstrap/           stage-0 compiler bundles (C)
tests/               language tests, regressions, LSP suite, wasm suite
docs/                language, stdlib, internals, guides
tools/               build, release, packaging and documentation scripts
vscode-extension/    editor client
```

## 🤝 Contributing

1. Read [docs/PENGUNIC.md](docs/PENGUNIC.md) (house rules) and
   [docs/psc/README.md](docs/psc/README.md) (compiler architecture).
2. Run `./tests/run.sh`, `./tests/regress.sh` and the LSP suite before sending a
   change.
3. Format with `psc fmt src std`; CI checks `--check`.
4. Keep the two documentation languages in sync and run
   `tools/docs/gen_api.sh --check`, `tools/docs/validate_docs.py` and
   `tools/docs/check_links.sh docs`.
5. Security and ownership changes need a regression test; every bug fix lands
   with a test.

Good first issues are labelled
[`good first issue`](https://github.com/TuGatito/PenguScript/labels/good%20first%20issue).
The audit and roadmap for 0.33 live in
[`docs/psc/AUDITORIA_0.33.0.md`](docs/psc/AUDITORIA_0.33.0.md).

## 💚 Acknowledgements

PenguScript stands on excellent open-source work. Thank you to the authors and
maintainers of:

| Project | Used for | License |
|---|---|---|
| [SDS](https://github.com/antirez/sds) | String allocation backend | BSD-2-Clause |
| [CC](https://github.com/JacksonAllan/CC) | `list`, `map`, `set`, `omap` containers | MIT |
| [vaqt](https://github.com/nalgeon/vaqt) | High-precision date/time | BSD-3-Clause |
| [libffi](https://github.com/libffi/libffi) | Dynamic FFI calls | MIT |
| [minicoro](https://github.com/edubart/minicoro) | Stackful coroutines | Unlicense / MIT-0 |
| [miniz](https://github.com/richgel999/miniz) | Deflate/zlib compression | Public domain / Unlicense |
| [tiny-regex-c](https://github.com/kokke/tiny-regex-c) | Small regex engine | Public domain |
| [utf8.h](https://github.com/sheredom/utf8.h) | UTF-8 primitives | Public domain / Unlicense |
| [libsodium](https://github.com/jedisct1/libsodium) | Optional crypto backend | ISC |
| [libclang](https://clang.llvm.org/) | `psc bind` header parsing | Apache-2.0 WITH LLVM-exception |
| [Emscripten](https://emscripten.org/) | WebAssembly toolchain | MIT / University of Illinois |
| [libcurl](https://curl.se/libcurl/) | HTTP client (`std.petitio`) | MIT-like |

Full texts and per-file attribution live in [THIRD_PARTY.md](THIRD_PARTY.md) and
in each vendored directory. PenguScript itself is released under the
[MIT License](LICENSE).

## 🗺️ Roadmap

- ✅ Incremental cache with sub-second hot builds
- ✅ Native cross-compilation plumbing (Linux ARM64, macOS ARM64, Windows BE)
- ✅ Coverage, ASan/UBSan/TSan profiles, DWARF debugging
- ✅ Cross-file rename and go-to-definition in the LSP
- 🚧 Per-module and parallel code generation for cold builds
- 🚧 Fiber-aware DAP debugger
- 🚧 `wasm32-wasi`
- 🚧 Tier-1 Windows CI

See [CHANGELOG.md](CHANGELOG.md) for what shipped in each release.
