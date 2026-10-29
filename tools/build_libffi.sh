#!/usr/bin/env bash
# Build the vendored libffi into build/libffi (optional satellite).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/std_c/libffi"
PREFIX="${PREFIX:-$ROOT/build/libffi}"
set -x
( cd "$SRC" && [ -x ./configure ] || autoreconf -fi )
( cd "$SRC" && ./configure --prefix="$PREFIX" --disable-static --enable-shared )
( cd "$SRC" && make -j"${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)}" )
( cd "$SRC" && make install )
echo "[libffi] installed to $PREFIX"
