<p align="center">
  <img src="vscode-extension/icons/pengu_icon.png" width="160" alt="PenguScript logo">
</p>

<h1 align="center">🐧 PenguScript</h1>

<p align="center">
  <strong>A small, explicit programming language with a native, self-hosted compiler.</strong><br>
  Simple syntax · manual memory · zero-cost generics · first-class C interop
</p>

<p align="center">
  <a href="https://github.com/TuGatito/PenguScript/releases"><img alt="Version" src="https://img.shields.io/badge/version-0.16.0-blue"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Compiler" src="https://img.shields.io/badge/compiler-PSC-blueviolet">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey">
</p>

<p align="center">
  <a href="LANGUAGE.md">📖 Language reference</a> ·
  <a href="CHEATSHEET.md">🧾 Cheatsheet</a> ·
  <a href="docs/psc/README.md">🧱 Compiler docs</a> ·
  <a href="CHANGELOG.md">📓 Changelog</a>
</p>

---

## What is PenguScript?

PenguScript is a small compiled language designed to stay readable when it talks
to C. The compiler (`psc`) is written in PenguScript and emits readable C11.

This repository contains **only the native compiler** and its standard library.
The legacy Python compiler lives outside `main` as a historical reference; it is
not required to build, test, or run anything here.

## Optional C modules

The core runtime stays on libc/libm/pthreads plus the vendored SDS, CC and
vaqt. Optional native capabilities are explicit modules:

- `std.chrono` — vaqt-backed nanosecond `Instant`/`Duration`;
- `std.dynlib` — `dlopen`/`LoadLibrary` symbol loading;
- `std.ffi_call` — libffi-backed dynamic calls (optional `-lffi`);
- `std.secrets` — libsodium-backed secure random/SHA-256/wipe (optional
  `-lsodium`).

Each module emits its `link` directive; the project manifest only needs the
library available. See [docs/EXTERNAL_MODULES.md](docs/EXTERNAL_MODULES.md).

## Runtime containers (0.13+)

`list of T` is backed by **Convenient Containers `vec`** and `map of K to V` by
**CC `map`**; the legacy `Set`/`SetString` APIs stay map-backed. The additive
`std.ordinal` exposes CC-backed generic `LinkedList of T`, `UnorderedSet of T`,
`OrderedSet of T` and `OrderedMap of K and V`; `T`/`K`/`V` can be built-ins,
strings or user runes. See [LANGUAGE.md](LANGUAGE.md) and
[std/ordinal.pengu](std/ordinal.pengu).

## Install

Download a release for your platform:

```text
pengu-<version>-<os>-<arch>-portable.tar.gz
pengu-<version>-<os>-<arch>-fhs.tar.gz
```

Extract it and put `bin/` on `PATH`:

```bash
tar -xzf pengu-0.16.0-linux-x86_64-portable.tar.gz
export PATH="$PWD/pengu-0.16.0-linux-x86_64-portable/bin:$PATH"
psc version
```

The package includes `psc`, `pengu-bind`, the standard library, the C runtime
and the C bindings. No Python installation is required. GitHub releases also
publish `pengus-<version>.vsix` for the VS Code extension.

## Build from source

Building the compiler needs a **native bootstrap `psc`** and a C compiler. The
repository ships a generated stage0 bundle, so no release download and no
Python are required:

```bash
./tools/build_bootstrap.sh      # builds the C runtime + build/psc-stage0
./build/psc-stage0 build .
./build/psc version
```

`tools/gen_stage0.sh` regenerates the per-platform
`bootstrap/psc_stage0_<os>_<arch>.c` bundles after compiler changes;
`tools/gen_stage0.sh --check` verifies that the committed bundles are up to
date.

Alternatively, use a native portable from the latest release:

```bash
# Linux example: use pengu-macos.tar.gz on macOS.
curl -LO https://github.com/TuGatito/PenguScript/releases/latest/download/pengu-linux-x64.tar.gz
mkdir -p .bootstrap
tar -xzf pengu-linux-x64.tar.gz -C .bootstrap
export PENGU_HOME="$PWD/.bootstrap"
export PATH="$PENGU_HOME/bin:$PENGU_HOME:$PATH"

psc build .
./build/psc version
```

Releases use one of two layouts:

```text
# native packages
pengu-<version>-<os>-<arch>-portable.tar.gz

# flat packages published by older releases
pengu-linux-x64.tar.gz
pengu-macos.tar.gz
```

The compiler is self-hosted: `bootstrap psc` builds `psc`, and a fixed point is
checked by rebuilding with the just-built compiler.

## WebAssembly / web

`psc` can compile to `wasm32-unknown-emscripten` with the Emscripten SDK
installed on the machine. The wasm runtime is separate from the host one:

```bash
source /path/to/emsdk/emsdk_env.sh
./tools/build_runtime_wasm.sh

psc build --target wasm          # build/app.html + app.js + app.wasm
psc run   --target wasm          # build, then run with node
psc test  --target wasm
psc doctor --target wasm
```

`when wasm:`, `when wasm_target == "emscripten":` and `when compiler == "emcc":`
work in both sema and codegen. `std.web` (console, main loop, timers) compiles
on native and wasm. `std.net` and native-library modules are rejected with an
actionable message on wasm. See [docs/WASM.md](docs/WASM.md) for the support
matrix and limitations.

## Quick start

```bash
psc init hello
cd hello
psc build
./build/hello
```

```pengu
import std.spark

weave main into int:
    calling spark.println with "hello, pengu"
    return 0
```

## Commands

```text
psc build/run/check/test     compile, run, check and test
psc fmt/doc/assets           formatter, docs and embedded assets
psc lex/parse/emit-c         compiler stages
psc lsp                      language server (stdio or TCP)
psc bind                     generate .d.pengu from a C header
psc add/remove/...           dependencies and vendor/lock
psc init/new/clean/doctor    project lifecycle
psc version/help
```

## Repository layout

```text
src/                 compiler (PenguScript)
std/                 standard library (PenguScript)
std_c/               C-backed standard modules
runtime/             C runtime source (pengu_runtime.c)
c_bind_stubs/        minimal headers for `psc bind`
tests/               PSC tests, conformance corpus and fixtures
tools/               bootstrap, release and test helpers
docs/                language and compiler documentation
vscode-extension/    editor client
```

## Dependencies

`pengu.toml` is the only manifest format. `pengu.yaml`, `pengu.yml` and
`pengu.json` are rejected. Dependencies are local paths or git repositories,
pinned by `pengu.lock`:

```bash
psc add https://example.com/lib.git --version="^1.0"
psc build --locked
psc vendor
```

### Vendored C libraries

The `string` type is backed by **SDS (Simple Dynamic Strings)** from Redis,
vendored in [`std_c/sds/`](std_c/sds/) under the BSD-2-Clause license. SDS is
compiled into `libpengu_runtime.a`, so projects keep linking only
`-lpengu_runtime`; `sds.h` is installed next to `pengu_runtime.h`.

Container storage is backed by **Convenient Containers (CC)** by Jackson L.
Allan, vendored in [`std_c/CC-main/`](std_c/CC-main/) under the MIT license.
`libpengu_runtime.a` contains the CC adapter (`vec` for `list`, `map` for
`map`, and `set`/`oset`/`omap`/`list` for the new `std.ordinal` types).

## Credits

PenguScript's string backend is built on **SDS — Simple Dynamic Strings**,
created by [Salvatore Sanfilippo](https://github.com/antirez), improved by Oran
Agra and maintained by the Redis community. It is vendored in
[`std_c/sds/`](std_c/sds/) and distributed under its original BSD-2-Clause
license; see [`std_c/sds/LICENSE`](std_c/sds/LICENSE) and
[THIRD_PARTY.md](THIRD_PARTY.md).

**Thank you**, Salvatore, Oran and the Redis community, for building and
sharing such a small, battle-tested library. Your work is what makes
PenguScript's strings safer and faster.

PenguScript's list/map/set storage is built on **Convenient Containers (CC)**,
created by [Jackson L. Allan](https://github.com/JacksonAllan), vendored in
[`std_c/CC-main/`](std_c/CC-main/) under the MIT license. See
[`std_c/CC-main/LICENSE`](std_c/CC-main/LICENSE) and
[THIRD_PARTY.md](THIRD_PARTY.md).

**Thank you**, Jackson, for designing a generic container library that is both
ergonomic and fast, and for making it available under a permissive license.

High-precision time uses **vaqt**, created by
[Anton Zhiyanov](https://github.com/nalgeon) and based on Go's `time` package.
vaqt is vendored in [`std_c/vaqt/`](std_c/vaqt/) under BSD-3-Clause; see
[THIRD_PARTY.md](THIRD_PARTY.md).

Optional native calls use **libffi** (MIT), vendored in
[`std_c/libffi/`](std_c/libffi/). Secure random/SHA helpers use
**libsodium** (ISC) through an optional system package. The libclang-based
binding generator links **libclang** (Apache-2.0 with LLVM exceptions) only at
build time; see [`tools/pengu-bind-clang.c`](tools/pengu-bind-clang.c).

## Status

- Lexer, parser, semantic analysis, C codegen, CLI, formatter, docs, assets,
  LSP and package manager are implemented in PSC.
- The bootstrap and release pipeline use PSC, not Python.
- The PSC test suite (`tests/run.sh`) passes on the supported corpus.
- Linux is the primary tested platform; macOS is covered by CI. Windows is not
  currently supported.

## License

MIT. See [LICENSE](LICENSE).
