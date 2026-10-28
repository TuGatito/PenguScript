<p align="center">
  <img src="vscode-extension/icons/pengu_icon.png" width="160" alt="PenguScript logo">
</p>

<h1 align="center">🐧 PenguScript</h1>

<p align="center">
  <strong>A small, explicit programming language with a native, self-hosted compiler.</strong><br>
  Simple syntax · manual memory · zero-cost generics · first-class C interop
</p>

<p align="center">
  <a href="https://github.com/TuGatito/PenguScript/releases"><img alt="Version" src="https://img.shields.io/badge/version-0.11.0-blue"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Compiler" src="https://img.shields.io/badge/compiler-PSC-blueviolet">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey">
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

## Install

Download a release for your platform:

```text
pengu-<version>-<os>-<arch>-portable.tar.gz   # or .zip on Windows
pengu-<version>-<os>-<arch>-fhs.tar.gz
```

Extract it and put `bin/` on `PATH`:

```bash
tar -xzf pengu-0.11.0-linux-x86_64-portable.tar.gz
export PATH="$PWD/pengu-0.11.0-linux-x86_64-portable/bin:$PATH"
psc version
```

The package includes `psc`, `pengu-bind`, the standard library, the C runtime
and the C bindings. No Python installation is required.

## Build from source

Building the compiler needs a **bootstrap `psc`** and a C compiler. Download the
bootstrap release for your platform:

```bash
curl -LO https://github.com/TuGatito/PenguScript/releases/download/v0.10.0/pengu-0.10.0-linux-x86_64-portable.tar.gz
tar -xzf pengu-0.10.0-linux-x86_64-portable.tar.gz
export PENGU_HOME="$PWD/pengu-0.10.0-linux-x86_64-portable"
export PATH="$PENGU_HOME/bin:$PATH"

# Runtime + std_c archives
./tools/build_runtime.sh

# Compile this repository with the bootstrap compiler
psc build .
./build/psc version
```

On Windows use `tools/build_runtime.ps1` and the `.zip` release.

The compiler is self-hosted: `bootstrap psc` builds `psc`, and a fixed point is
checked by rebuilding with the just-built compiler.

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

## Status

- Lexer, parser, semantic analysis, C codegen, CLI, formatter, docs, assets,
  LSP and package manager are implemented in PSC.
- The bootstrap and release pipeline use PSC, not Python.
- The PSC test suite (`tests/run.sh`) passes on the supported corpus.
- Linux is the primary tested platform; macOS/Windows are covered by CI.

## License

MIT. See [LICENSE](LICENSE).
