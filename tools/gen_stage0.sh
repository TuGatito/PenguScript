#!/usr/bin/env bash
# Regenerate the per-platform stage0 bundles in bootstrap/.
#
# Run it with a working native `psc` (normally ./build/psc) after changing the
# compiler, and commit the resulting C files. CI uses
# tools/build_bootstrap.sh to turn the matching file into a native bootstrap.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
if [ ! -x "$PSC" ] && [ -x "$PSC.exe" ]; then
  PSC="$PSC.exe"
fi
OUT="$ROOT/bootstrap"

[ -x "$PSC" ] || { echo "gen_stage0: missing native compiler: $PSC" >&2; exit 1; }

emit() {
  local os="$1" arch="$2" cc="$3" out="$4"
  "$PSC" emit-c "$ROOT/src/main.pengu" \
    --target-os="$os" --target-arch="$arch" --target-compiler="$cc" \
    --out="$out"
}

bundles() {
  echo "$OUT/psc_stage0_linux_x64.c linux x64 gcc"
  echo "$OUT/psc_stage0_macos_arm64.c macos arm64 clang"
  echo "$OUT/psc_stage0_windows_x64.c windows x64 gcc"
}

if [ "${1:-}" = "--check" ]; then
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/psc-stage0.XXXXXX")"
  trap 'rm -rf "$tmpdir"' EXIT
  stale=0
  while read -r file os arch cc; do
    tmp="$tmpdir/$(basename "$file")"
    emit "$os" "$arch" "$cc" "$tmp" >/dev/null
    if ! cmp -s "$tmp" "$file"; then
      echo "gen_stage0: $file is stale; run tools/gen_stage0.sh" >&2
      stale=1
    fi
  done < <(bundles)
  if [ "$stale" -ne 0 ]; then
    exit 1
  fi
  echo "gen_stage0: up to date"
  exit 0
fi

mkdir -p "$OUT"
while read -r file os arch cc; do
  emit "$os" "$arch" "$cc" "$file"
done < <(bundles)
