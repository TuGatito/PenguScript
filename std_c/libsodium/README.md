# libsodium (optional satellite)

Upstream: https://github.com/jedisct1/libsodium — ISC license.
The source is intentionally **not** vendored here (it is large and has
platform-specific build steps). Use the system package
(`pkg-config --cflags --libs libsodium`) or a pinned upstream release.

`std.secrets` links `-lsodium` only when imported. The core runtime does
not require libsodium.
