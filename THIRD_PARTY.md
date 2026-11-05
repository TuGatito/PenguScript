# Third-party components

PenguScript is MIT-licensed (see [LICENSE](LICENSE)). The following third-party
components are vendored in this repository and keep their original licenses.

## SDS — Simple Dynamic Strings

- **Location:** [`std_c/sds/`](std_c/sds/)
- **Version:** SDS 2.x (the stand-alone Redis SDS distribution)
- **License:** BSD-2-Clause. Full text in
  [`std_c/sds/LICENSE`](std_c/sds/LICENSE); release packages also ship it as
  `share/doc/pengu/SDS_LICENSE`.
- **Authors / credits:** Salvatore Sanfilippo (`antirez`), Oran Agra and the
  Redis Labs / Redis community.
- **Usage:** the C runtime (`pengu_runtime.h`) uses SDS as the allocation
  backend of every owned `PenguString`. `std_c/sds/sds.c` is compiled into
  `libpengu_runtime.a`; `std_c/sds/sds.h` is installed next to
  `pengu_runtime.h`.

Thank you to the SDS authors and the Redis community for building a small,
battle-tested, permissively licensed string library and for making it available
to the rest of the C ecosystem.

## CC — Convenient Containers

- **Location:** [`std_c/CC-main/`](std_c/CC-main/)
- **Version:** CC v1.4.3 (single header)
- **License:** MIT. Full text in [`std_c/CC-main/LICENSE`](std_c/CC-main/LICENSE);
  release packages also ship it as `share/doc/pengu/CC_LICENSE`.
- **Author / credits:** Jackson L. Allan and the CC contributors.
- **Usage:** `runtime/pengu_containers.c` and `runtime/pengu_cc_extra.c` include
  `cc.h` with `CC_NO_SHORT_NAMES`. CC `vec` backs `list`, CC `map` backs
  `map`, and CC `list`/`set`/`oset`/`omap` back the new `std.ordinal` types.

Thank you to Jackson L. Allan for building CC and releasing it under the MIT
license; its type-erased internals let PenguScript keep its stable runtime
container ABI while replacing the hand-written storage.


## vaqt — high-precision date/time

- **Location:** [`std_c/vaqt/`](std_c/vaqt/)
- **Version:** upstream `nalgeon/vaqt` (BSD-3-Clause), vendored source.
- **License:** BSD-3-Clause. See [`std_c/vaqt/LICENSE`](std_c/vaqt/LICENSE);
  release packages ship it as `share/doc/pengu/VAQT_LICENSE`.
- **Author / credits:** Anton Zhiyanov, based on Go's `time` package
  (Copyright The Go Authors). See the upstream
  [README](https://github.com/nalgeon/vaqt).
- **Usage:** compiled into `libpengu_runtime.a` and exposed through the
  additive [`std/chrono.pengu`](std/chrono.pengu) `Instant`/`Duration` API.
  The historical libc-based `std.chronicle` API is unchanged.

Thank you to Anton Zhiyanov and the Go authors for a small, precise, portable
time library.

## libffi — optional dynamic calls

- **Location:** [`std_c/libffi/`](std_c/libffi/)
- **Version:** upstream `libffi/libffi` (MIT), vendored source.
- **License:** MIT. See [`std_c/libffi/LICENSE`](std_c/libffi/LICENSE).
- **Usage:** optional satellite for
  [`std/ffi_call.pengu`](std/ffi_call.pengu); it is not linked by the core
  runtime. Build with system libffi or `tools/build_libffi.sh`.

## libsodium — optional crypto/random

- **Location:** [`std_c/libsodium/`](std_c/libsodium/)
- **License:** ISC. See [`std_c/libsodium/LICENSE`](std_c/libsodium/LICENSE).
- **Usage:** optional satellite for [`std/secrets.pengu`](std/secrets.pengu);
  it is not linked by the core runtime. The source is not vendored because it
  is large; use a pinned system package or an upstream release.

## libclang — build-time binding generator

- **Usage:** [`tools/pengu-bind-clang.c`](tools/pengu-bind-clang.c), built by
  [`tools/build_bind.sh`](tools/build_bind.sh) against the system libclang.
  Apache-2.0 with LLVM exceptions. It is never linked into `psc` or generated
  programs.
- **Credits:** the LLVM/Clang project.

## minicoro — stackful coroutines

- **Location:** [`std_c/minicoro/`](std_c/minicoro/)
- **Version:** minicoro v0.2.0 (single header), upstream commit
  `ff5321d93fe2a3fb067a8dd97a37dd623337b9c0` (2023-11-15).
- **License:** Unlicense (alternative 1) or MIT No Attribution (alternative 2).
  Full text in [`std_c/minicoro/LICENSE`](std_c/minicoro/LICENSE); release
  packages ship it as `share/doc/pengu/MINICORO_LICENSE`.
- **Author / credits:** Eduardo Bart and the minicoro contributors.
- **Usage:** `runtime/pengu_coro.c` compiles the header once and adds it to
  `libpengu_runtime.a`; `std/coro.pengu` is the only public consumer. Programs
  that do not import `std.coro` do not pull the object in.
- **Provenance:** `std_c/minicoro/SOURCE` records the commit and the upstream
  header SHA-256.

Thank you to Eduardo Bart for a small, portable, permissively licensed
coroutine library that keeps the PenguScript runtime readable.

## miniz — gzip/zlib/deflate

- **Location:** [`std_c/miniz.c`](std_c/miniz.c) and
  [`std_c/miniz.h`](std_c/miniz.h)
- **Version:** miniz 3.1.2 (single-file distribution).
- **License:** public domain / Unlicense. The header states that miniz is
  public domain and includes the Unlicense statement at the end of
  [`std_c/miniz.h`](std_c/miniz.h).
- **Author / credits:** Rich Geldreich and the miniz contributors.
- **Usage:** built as `libminiz.a` and linked only by
  [`std/compressus.pengu`](std/compressus.pengu). Not part of the core runtime.
  Build flags disable archive/stdio/time APIs and zlib-compatible names.

## tiny-regex-c — regular expressions

- **Location:** [`std_c/re.c`](std_c/re.c) and [`std_c/re.h`](std_c/re.h)
- **License:** public domain. The file header credits Rob Pike's regular
  expression code as the inspiration and places the implementation in the
  public domain.
- **Usage:** built as `libre.a` and linked only by
  [`std/regulus.pengu`](std/regulus.pengu). It supports a deliberately small
  subset (no `{n,m}` and no alternation).
- **Caveat:** the upstream header says `[^...]` is broken; this was not
  reproducible in the current version, but the subset limits are real. New code
  should prefer `std.regula` (PCRE2) once the satellite lands.

## utf8.h — UTF-8 primitives

- **Location:** [`std_c/utf8.h`](std_c/utf8.h)
- **License:** public domain / Unlicense ("free and unencumbered software
  released into the public domain").
- **Author / credits:** Neil Henning (`sheredom`).
- **Usage:** header-only; included by the `std.lingua` adapter. No archive and
  no link flag.

## petitio — libcurl transport

- **Location:** [`std_c/petitio.c`](std_c/petitio.c) and
  [`std_c/petitio.h`](std_c/petitio.h)
- **License:** first-party (MIT, same as PenguScript), wrapping libcurl
  (MIT-like). libcurl is a system dependency, not vendored.
- **Usage:** built as `libpetitio.a`; linked by
  [`std/petitio.pengu`](std/petitio.pengu) together with `-lcurl`.

## toml_min — minimal TOML subset

- **Location:** [`std_c/toml_min.h`](std_c/toml_min.h)
- **License:** first-party (MIT, same as PenguScript).
- **Usage:** header-only parser for the TOML 1.0 subset exposed by
  [`std/toml.pengu`](std/toml.pengu); replaced by tomlc99 in the F3 phase.
