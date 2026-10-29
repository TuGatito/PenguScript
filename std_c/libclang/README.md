# libclang (build-time only)

`tools/pengu-bind-clang.c` uses the system libclang C API to generate
`.d.pengu` bindings. It is compiled by `tools/build_bind.sh`; it is **not**
linked into `psc` or into generated programs.

- Upstream: https://clang.llvm.org/
- License: Apache-2.0 with LLVM exceptions.
- Requirement: `clang-c/Index.h` and `libclang` (development package).

No libclang source is vendored here: distributions ship it, and the tool is a
build dependency rather than a runtime dependency.
