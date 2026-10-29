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
