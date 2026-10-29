# Vendored and optional C libraries

| Directory | License | Role | Linked by |
|---|---|---|---|
| `sds/` | BSD-2 | Owned strings | core runtime |
| `CC-main/` | MIT | Containers | core runtime |
| `vaqt/` | BSD-3 | High-precision time | core runtime (`std.chrono`) |
| `libffi/` | MIT | Dynamic calls | optional `std.ffi_call` |
| `libsodium/` | ISC | Secure random/SHA/wipe | optional `std.secrets` |
| `libclang/` | Apache-2.0 + LLVM exception | Build-time binding generator | `tools/pengu-bind-clang.c` |

Every directory carries its upstream README and LICENSE. Optional libraries are
not part of `libpengu_runtime.a` unless explicitly built/used; see
[`../docs/EXTERNAL_MODULES.md`](../docs/EXTERNAL_MODULES.md).

Planned satellites and the full evaluation are in
[`../scratch/STD_C_LIBRARY_AUDIT.md`](../scratch/STD_C_LIBRARY_AUDIT.md).
