# Vendored libffi

Upstream: https://github.com/libffi/libffi (MIT).
Source is vendored unmodified except for the usual `.git`/build artifacts being
removed. Build it with `tools/build_libffi.sh` or use the system `libffi`
(`pkg-config --cflags --libs libffi`).

PenguScript's optional `std.ffi_call` module links `-lffi`; the core runtime
does not. See `THIRD_PARTY.md`.
