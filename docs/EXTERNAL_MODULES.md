# External C libraries and optional std modules

PenguScript keeps the **core** runtime small: `libpengu_runtime.a` contains
SDS, CC, vaqt and the small FFI/VAQT bridges. Compression, regex, TOML and the
other format helpers are built as separate archives and are linked only by
projects that import the corresponding module.

Larger or platform-specific libraries are **satellites**: they live in
`std_c/<name>/` with their own license/README and are linked only when a live
module declares `link "name"`.

## Naming: binding vs wrapper

Every external library is split in two files:

- **Binding** — `std/<library>.d.pengu` (for example `std/pcre2.d.pengu`,
  `std/sqlite3.d.pengu`, `std/mbedtls.d.pengu`). It only contains `declare`,
  `include`, `link`, layout constants and version macros. It never exposes a
  library type to users.
- **Wrapper** — `std/<latin-name>.pengu` (for example `std.regula` for PCRE2,
  `std.codex` for SQLite, `std.tutela` for mbedTLS). It is the public API:
  `PenguString`, `PenguSlice`, `rune`, `omen`, `Result`/`maybe`, explicit limits
  and mapped errors. Users import the wrapper, never the binding.

Existing public modules keep their names for compatibility (`std.json`,
`std.toml`, `std.yaml`, `std.lingua`, `std.petitio`, `std.compressus`,
`std.secrets`, `std.ffi_call`, `std.regulus`); their backend can change without
changing the import. The full naming decision is `D16` in
the current audit (kept in the maintainer scratch directory, not shipped).

## Present in the tree

```text
std_c/
  sds/                 BSD-2     owned strings (core runtime)
  CC-main/             MIT       list/map/set/ordered containers (core runtime)
  vaqt/                BSD-3     high-precision time (core runtime)
  libffi/              MIT       dynamic calls (optional std.ffi_call)
  libsodium/           ISC       license only; source fetched/pinned (optional std.secrets)
  libclang/            Apache-2.0 + LLVM exception  build-time binding generator
  miniz.c/.h           public domain / Unlicense  gzip/zlib/deflate (libminiz.a)
  re.c/.h              public domain   tiny-regex-c (libre.a, std.regulus)
  utf8.h               public domain   sheredom UTF-8 helpers (std.lingua)
  petitio.c/.h         first-party     libcurl HTTP adapter (libpetitio.a, std.petitio)
  toml_min.h           first-party     minimal TOML 1.0 subset (std.toml)
  miniz_bind.h         first-party     miniz declarations for std.compressus
```

Each directory must contain:

- `README.md` — upstream version, pinned commit/tag, build notes;
- `LICENSE` — full upstream license;
- the upstream source tree (or a documented fetch script for enormous
  libraries);
- a note in `THIRD_PARTY.md` and in the release package.

## Link policy

A module declares `link "name"`; the compiler adds `-l<name>` only when that
module has at least one live function. Release builds (`--profile release`)
enable this pruning by default; debug builds opt in with `--prune-native`. The
runtime itself only needs libc, `libpengu_runtime.a` and the platform thread/dl
libraries. The core runtime must not require libsodium, libffi, libuv,
libarchive or libclang to build `psc` itself.

The linker uses `-ffunction-sections -fdata-sections` plus `--gc-sections`
(`-dead_strip` on macOS) and strips symbols in release builds, so unused
functions inside an archive are removed even when the archive is linked.

## Current integrations

| Module | Library | Status |
|---|---|---|
| `std.ffi` | none (libc/runtime) | core |
| `std.ffi_call` | libffi | optional; `link "ffi"` |
| `std.dynlib` | libdl/`dlopen` or Win32 | optional; `link "dl"` on POSIX |
| `std.chrono` | vaqt | core (vendored in runtime) |
| `std.digest` | SHA-256 own implementation | core; libsodium adapter planned |
| `std.petitio` | libcurl | existing system dependency |
| `std.regulus` | tiny-regex-c | satellite archive `libre.a` |
| `std.lingua` | utf8.h | header-only |
| `std.compressus` | miniz | satellite archive `libminiz.a` |
| `std.toml` | toml_min.h | header-only |
| `std.secrets` | libsodium | optional; `link "sodium"` |

## Roadmap (not present yet)

The following directories are **planned**, not shipped. They are listed so
contributors do not mistake the roadmap for the current tree:

`tomlc99/`, `libyaml/`, `yyjson/`, `pcre2/`, `utf8proc/`, `libgrapheme/`,
`libdeflate/`, `zstd/`, `lz4/`, `libuv/`, `libarchive/`, `libbacktrace/`,
`civetweb/`, `libxml2/`, `lexbor/`, `libcbor/`, `msgpack-c/`, `protobuf-c/`,
`inih/`, `cmark/`, `uriparser/`, `sqlite/`, `mbedtls/`, `tzcode/`, `c-ares/`,
`decNumber/`, `libtommath/`, `kissfft/`, `lmdb/`.

The audit in the maintainer scratch directory (not shipped) describes the full
evaluation, the license allowlist, the decisions D1–D16 and
the phased plan F0–F8. A satellite is merged only after it has:

1. a permissively licensed vendor directory with `LICENSE` and `SOURCE`;
2. a `pengu.pkg` with version, license, include/lib dirs and WASM flag;
3. a C adapter that does not change the public PenguScript API;
4. ASan/UBSan/fuzz tests;
5. Windows/macOS/Linux coverage (or a documented platform gate);
6. an updated `THIRD_PARTY.md` and release license bundle;
7. a size test proving that importing it without using it adds 0 bytes and 0
   `-l` flags.

## Tooling

- `tools/fetch_satellite.sh <name> <url> <sha256>` — download, verify, extract
  and write `SOURCE`/`pengu.pkg`.
- `tools/satellite_new.sh <name>` — create the skeleton for a new satellite.
- `tools/license_check.sh` — enforce the license allowlist and attribution.
- `tools/size_report.sh` — measure the size fixtures against
  `tests/baseline/sizes.json`.
- `tests/link_prune.sh` — regression test: an unused satellite import emits no
  `-l` flag; release builds prune by default.

## libclang bind tool

`tools/build_bind.sh` builds `build/pengu-bind` from
`tools/pengu-bind-clang.c` against the system libclang. It is a **build-time**
tool: no runtime dependency, no Python. `psc bind` finds the resulting
`pengu-bind` binary next to `psc` or via `PENGU_BIND`.

The historical Python helper under `tools/pengu-bind-src/` is kept only as a
reference/fallback; release builds use the libclang tool.
