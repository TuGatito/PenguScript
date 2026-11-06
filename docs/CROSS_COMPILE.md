# Cross-compilation

<!-- toc -->
- [Supported targets](#supported-targets)
- [Linux ARM64 from x86_64](#linux-arm64-from-x86_64)
- [macOS ARM64](#macos-arm64)
- [Windows (best effort)](#windows-best-effort)
- [WebAssembly](#webassembly)
- [How it works](#how-it-works)
- [Limitations](#limitations)
<!-- /toc -->

PenguScript compiles to portable C with a small runtime, so cross-compiling is
mostly a matter of choosing a C toolchain and a runtime archive built for the
target.

## Supported targets

| Target triple | Status | Toolchain |
|---|---|---|
| host (no flag) | ✅ supported | system `cc` |
| `x86_64-unknown-linux-gnu` | ✅ supported | `gcc`/`clang` |
| `aarch64-unknown-linux-gnu` | ✅ guaranteed with cross toolchain | `aarch64-linux-gnu-gcc` |
| `aarch64-unknown-linux-musl` | ✅ with musl toolchain | `aarch64-linux-musl-gcc` |
| `x86_64-apple-darwin` | ✅ on macOS | `clang` |
| `aarch64-apple-darwin` | ✅ guaranteed on Apple Silicon runners | `clang` |
| `x86_64-w64-mingw32` | ⚠️ best effort | `x86_64-w64-mingw32-gcc` |
| `wasm32-unknown-emscripten` | ✅ supported | emsdk (`emcc`) |

Anything else is rejected with a clear diagnostic. `wasm32-wasi` is recognised
but not implemented.

Select a target in `pengu.toml` or on the command line:

```toml
[build]
target = "aarch64-unknown-linux-gnu"
```

```console
$ psc build . --target=aarch64-unknown-linux-gnu
$ psc build . --target=aarch64-apple-darwin
$ psc build . --target=x86_64-w64-mingw32
```

## Linux ARM64 from x86_64

Install a cross gcc and build the runtime for the target once:

```console
$ sudo apt install gcc-aarch64-linux-gnu
$ CC=aarch64-linux-gnu-gcc AR=aarch64-linux-gnu-ar \
  RUNTIME_OUT=build/lib/aarch64-unknown-linux-gnu \
  bash tools/build_runtime.sh
$ psc build . --target=aarch64-unknown-linux-gnu
$ file build/app
build/app: ELF 64-bit LSB pie executable, ARM aarch64, ...
```

Run it with `qemu-aarch64` plus the cross sysroot, or on real hardware/CI:

```console
$ qemu-aarch64 -L /usr/aarch64-linux-gnu ./build/app
```

The driver refuses to link if
`build/lib/<triple>/libpengu_runtime.a` is missing and prints the exact command
to build it. `PSC_CC` or `--cc` override the compiler choice;
`aarch64-linux-gnu-gcc`, `x86_64-linux-gnu-gcc` and
`x86_64-w64-mingw32-gcc` are discovered automatically.

## macOS ARM64

Apple's SDK is only redistributable on Apple hardware, so macOS cross builds are
not supported from Linux. The guaranteed path is a native Apple Silicon runner:

```yaml
# .github/workflows/ci.yml (macos-latest = Apple Silicon)
runs-on: macos-latest
steps:
  - run: test "$(uname -m)" = "arm64"   # guard: fail if the runner is x64
  - run: ./tools/build.sh --no-register --no-bind --no-wasm
  - run: ./build/psc build . --target=aarch64-apple-darwin
  - run: ./build/psc test . --target=aarch64-apple-darwin
```

`clang` on macOS targets the host architecture by default; passing the triple
adds `--target=aarch64-apple-darwin`.

## Windows (best effort)

`x86_64-w64-mingw32` is accepted and the driver looks for the MinGW compiler.
A native MSYS2 job builds the bootstrap, the compiler and a hello program on
`windows-latest`; it is **advisory** (`continue-on-error: true`) until
networking, threads and the POSIX-specific runtime pieces have full coverage.
Treat Windows artifacts as experimental.

The cross workflow (`.github/workflows/windows-cross.yml`) builds the runtime with
`mingw-w64` and verifies that `psc build --target=x86_64-w64-mingw32` produces a
`PE32+` executable. Run it from the Actions tab before tagging when touching
Windows paths:

```console
$ CC=x86_64-w64-mingw32-gcc AR=x86_64-w64-mingw32-ar \
  RUNTIME_OUT=build/lib/x86_64-w64-mingw32 bash tools/build_runtime.sh
$ psc build . --target=x86_64-w64-mingw32
```

## WebAssembly

WebAssembly is a first-class target (not a cross build in the traditional
sense); see [WASM.md](WASM.md):

```console
$ psc build . --target=wasm32-unknown-emscripten
$ psc run  . --target=wasm32-unknown-emscripten
```

## How it works

1. `src/psc/driver/target.pengu` parses the triple into `os`, `arch`, `env`.
2. `src/psc/driver/toolchain.pengu` selects the compiler and adds `--target`
   when using clang.
3. `src/psc/driver/build.pengu` links against the target-specific runtime
   archive from `build/lib/<triple>/`.
4. The generated C is architecture-independent; endianness, pointer width and
   struct layout come from the C compiler and are already modelled by the ABI
   layer.

## Limitations

* Cross builds need a target C library and headers (sysroot). The driver does
  not ship one.
* macOS targets require Apple's SDK; build on macOS.
* Windows builds are best effort; see above.
* `std.dynlib`/`std.ffi` and other host-specific modules may not be available on
  every target; `psc build` reports unsupported modules instead of emitting
  broken C.
