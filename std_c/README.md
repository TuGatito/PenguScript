# Vendored and optional C libraries

## Present in this directory

| Path | License | Role | Linked by |
|---|---|---|---|
| `sds/` | BSD-2 | Owned strings | core runtime (`libpengu_runtime.a`) |
| `CC-main/` | MIT | Containers | core runtime (`libpengu_runtime.a`) |
| `vaqt/` | BSD-3 | High-precision time | core runtime (`std.chrono`) |
| `libffi/` | MIT | Dynamic calls | optional `std.ffi_call` |
| `libsodium/` | ISC | Secure random/SHA/wipe | optional `std.secrets` (license only; source is fetched/pinned) |
| `libclang/` | Apache-2.0 + LLVM exception | Build-time binding generator | `tools/pengu-bind-clang.c` |
| `minicoro/` | Unlicense / MIT-0 | Stackful coroutines | `libpengu_runtime.a` -> `std.coro` |
| `miniz.c`, `miniz.h` | public domain / Unlicense | gzip/zlib/deflate | `libminiz.a` -> `std.compressus` |
| `re.c`, `re.h` | public domain | tiny-regex-c | `libre.a` -> `std.regulus` |
| `utf8.h` | public domain / Unlicense | UTF-8 helpers | header-only -> `std.lingua` |
| `petitio.c`, `petitio.h` | first-party (MIT) | libcurl HTTP adapter | `libpetitio.a` -> `std.petitio` |
| `toml_min.h` | first-party (MIT) | Minimal TOML 1.0 subset | header-only -> `std.toml` |
| `miniz_bind.h` | first-party (MIT) | miniz declarations | `std.compressus` |

`std_c/*.c` is built into one archive per file (`libminiz.a`, `libre.a`, ...),
not into `libpengu_runtime.a`. The archives are linked only by modules that
declare `link "name"` and only when one of those modules has a live function
(release builds prune automatically; debug builds use `--prune-native`).

## Planned, not present

`tomlc99/`, `libyaml/`, `yyjson/`, `pcre2/`, `utf8proc/`, `libgrapheme/`,
`libdeflate/`, `zstd/`, `lz4/`, `libuv/`, `libarchive/`, `libbacktrace/`,
`civetweb/`, `libxml2/`, `lexbor/`, `libcbor/`, `msgpack-c/`, `protobuf-c/`,
`inih/`, `cmark/`, `uriparser/`, `sqlite/`, `mbedtls/`, `tzcode/`, `c-ares/`,
`decNumber/`, `libtommath/`, `kissfft/`, `lmdb/`.

Do not create these directories by hand: use `tools/satellite_new.sh` followed
by `tools/fetch_satellite.sh`, and update `THIRD_PARTY.md` plus the release
license bundle. See [`../docs/EXTERNAL_MODULES.md`](../docs/EXTERNAL_MODULES.md)
and the audit in the maintainer scratch directory (not shipped).

## License rules

Only permissive licenses are accepted in this directory: MIT, BSD-2/3, ISC,
Apache-2.0 (with the LLVM exception where applicable), Zlib, CC0, Unlicense,
BSL-1.0, Unicode-3.0, OpenLDAP-2.8 and PostgreSQL. LGPL/MPL may only be used as
an optional **system** dependency, never vendored. GPL/AGPL/SSPL are rejected.
Every directory needs its upstream `LICENSE` and `SOURCE`; `tools/license_check.sh`
enforces this in CI.
