#!/usr/bin/env bash
# Build the libclang-based pengu-bind helper. No Python is required.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/build/pengu-bind}"
CC="${CC:-cc}"
CFLAGS=(); LIBS=()
if command -v llvm-config >/dev/null 2>&1; then
  CFLAGS+=($(llvm-config --cflags))
  LIBS+=($(llvm-config --ldflags) -lclang)
elif command -v llvm-config-23 >/dev/null 2>&1; then
  CFLAGS+=($(llvm-config-23 --cflags))
  LIBS+=($(llvm-config-23 --ldflags) -lclang)
else
  # Debian/Ubuntu/Fedora layout; libclang is resolved by the system linker.
  [ -d /usr/include/clang-c ] && CFLAGS+=(-I/usr/include)
  LIBS+=(-lclang)
fi
mkdir -p "$(dirname "$OUT")"
"$CC" -std=c11 -O2 -Wall -Wextra "${CFLAGS[@]}" \
  "$ROOT/tools/pengu-bind-clang.c" "${LIBS[@]}" -o "$OUT"
echo "[bind] built $OUT"
