# External C libraries and optional std modules

PenguScript keeps the **core** runtime small: `libpengu_runtime.a` contains
SDS, CC, miniz, vaqt, and the small FFI bridges. Larger or platform-specific
libraries are **satellites**: they live in `std_c/<name>/` with their own
license/README and are linked only by projects that import the corresponding
module.

## Layout

```text
std_c/
  sds/                 BSD-2     owned strings
  CC-main/             MIT       list/map/set/ordered containers
  vaqt/                BSD-3     high-precision time
  libffi/              MIT       dynamic calls (optional satellite)
  libsodium/           ISC       crypto/random (optional satellite)
  tomlc99/             MIT       full TOML (optional satellite)
  libyaml/             MIT       full YAML (optional satellite)
  yyjson/              MIT       fast JSON (optional satellite)
  pcre2/               BSD-3     full regex (optional satellite)
  utf8proc/            MIT       Unicode normalization/case folding
  libdeflate/          MIT       fast deflate/gzip
  zstd/                BSD-3     Zstandard
  lz4/                 BSD-2     LZ4
  libuv/               MIT       async I/O/threadpool
  libarchive/          BSD-2     ZIP/TAR/7z
  libbacktrace/        BSD-3     symbols in crash traces
  civetweb/            MIT       embedded HTTP server
```

Each directory must contain:

- `README.md` — upstream version, pinned commit/tag, build notes;
- `LICENSE` — full upstream license;
- the upstream source tree (or a documented fetch script for enormous
  libraries);
- a note in `THIRD_PARTY.md` and in the release package.

Libraries in this list are **not automatically linked**. A module declares
`link "name"` and the project manifest adds the archive/library directory.
The core runtime must not require libsodium, libffi, libuv, libarchive or
libclang to build `psc` itself.

## Current integrations

| Module | Library | Status |
|---|---|---|
| `std.ffi` | none (libc/runtime) | core |
| `std.ffi_call` | libffi | optional; `link "ffi"` |
| `std.dynlib` | libdl/`dlopen` or Win32 | optional; `link "dl"` on POSIX |
| `std.chrono` | vaqt | core (vendored in runtime) |
| `std.digest` | SHA-256 own implementation | core; libsodium adapter planned |
| `std.petitio` | libcurl | existing system dependency |
| `std.regulus` | tiny-regex-c | core |
| `std.lingua` | utf8.h | core |
| `std.compressus` | miniz | core |

## Planned satellites

The audit in `scratch/STD_C_LIBRARY_AUDIT.md` describes the full evaluation and
priority. A satellite is merged only after it has:

1. a permissively licensed vendor directory;
2. a C adapter that does not change the public PenguScript API;
3. ASan/UBSan/fuzz tests;
4. Windows/macOS/Linux coverage (or a documented platform gate);
5. an updated `THIRD_PARTY.md` and release license bundle.

## libclang bind tool

`tools/build_bind.sh` builds `build/pengu-bind` from
`tools/pengu-bind-clang.c` against the system libclang. It is a **build-time**
tool: no runtime dependency, no Python. `psc bind` finds the resulting
`pengu-bind` binary next to `psc` or via `PENGU_BIND`.

The historical Python helper under `tools/pengu-bind-src/` is kept only as a
reference/fallback; release builds use the libclang tool.
