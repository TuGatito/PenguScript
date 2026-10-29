#!/usr/bin/env bash
# Build a native `psc` bootstrap from the checked-in stage0 C bundles.
#
# The published releases used to ship a legacy `pengu` CLI, which is far too
# slow to compile this tree. `bootstrap/psc_stage0_<os>_<arch>.c` is generated
# by a native `psc` (see tools/gen_stage0.sh) and only needs a C compiler + ar,
# so CI can bootstrap deterministically on Linux, macOS and Windows/MSYS2.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/build/psc-stage0"
if [ -z "${CC:-}" ]; then
  if command -v cc >/dev/null 2>&1; then
    CC=cc
  elif command -v gcc >/dev/null 2>&1; then
    CC=gcc
  elif command -v clang >/dev/null 2>&1; then
    CC=clang
  else
    echo "build_bootstrap: no C compiler found (set CC)" >&2
    exit 1
  fi
fi
export CC
export AR="${AR:-ar}"

raw_os="$(uname -s | tr '[:upper:]' '[:lower:]')"
raw_arch="$(uname -m)"
case "$raw_os" in
  linux*) host_os=linux ;;
  darwin*) host_os=macos ;;
  mingw*|msys*|cygwin*) host_os=windows ;;
  *) echo "build_bootstrap: unsupported OS: $raw_os" >&2; exit 1 ;;
esac
case "$raw_arch" in
  x86_64|amd64) host_arch=x64 ;;
  arm64|aarch64) host_arch=arm64 ;;
  *) host_arch="$raw_arch" ;;
esac
if [ "$host_os" = "windows" ]; then
  OUT="$ROOT/build/psc-stage0.exe"
fi

case "$host_os-$host_arch" in
  linux-x64) STAGE0="$ROOT/bootstrap/psc_stage0_linux_x64.c" ;;
  macos-arm64) STAGE0="$ROOT/bootstrap/psc_stage0_macos_arm64.c" ;;
  windows-x64) STAGE0="$ROOT/bootstrap/psc_stage0_windows_x64.c" ;;
  *)
    echo "build_bootstrap: no stage0 bundle for $host_os-$host_arch" >&2
    exit 1
    ;;
esac

[ -f "$STAGE0" ] || { echo "build_bootstrap: missing $STAGE0" >&2; exit 1; }

"$ROOT/tools/build_runtime.sh"

case "$host_os" in
  linux) libs=(-lm -pthread -ldl) ;;
  windows)
    # MinGW/SDS emit a few harmless warnings while building stage0.
    export PENGU_NO_WERROR=1
    libs=(-lm -lws2_32 -lwinpthread)
    ;;
  *) libs=(-lm -pthread) ;;
esac

"$CC" -std=c11 -O2 \
  -I"$ROOT" -I"$ROOT/build/include" -I"$ROOT/std_c" -I"$ROOT/std_c/sds" \
  "$STAGE0" \
  "$ROOT/build/lib/libpengu_runtime.a" \
  "$ROOT/build/lib/libminiz.a" \
  "$ROOT/build/lib/libre.a" \
  "${libs[@]}" \
  -o "$OUT"

"$OUT" version
