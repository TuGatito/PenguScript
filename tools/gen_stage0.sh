#!/usr/bin/env bash
# Regenerate the per-platform stage0 bundles in bootstrap/.
#
# Run it with a working native `psc` (normally ./build/psc) after changing the
# compiler, and commit the resulting C files. CI uses
# tools/build_bootstrap.sh to turn the matching file into a native bootstrap.
#
# `--family=cpp --dir=DIR` emite las mismas tres variantes con el backend C++
# (`psc_stage0_<os>_<arch>.cpp`).  No se commitean todavía: durante F1–F3 el
# bootstrap canónico sigue siendo el C, y duplicar los tres bundles en cada
# cambio del compilador engordaría el repo ~20 MB por commit.  Se usan para
# verificar que el emisor C++ es reproducible en los tres targets (CI) y, en
# F4, pasarán a ser los bundles commiteados.
#
# Uso:
#   tools/gen_stage0.sh                          # regenera bootstrap/*.c
#   tools/gen_stage0.sh --check                  # verifica bootstrap/*.c
#   tools/gen_stage0.sh --family=cpp --dir=build/stage0_cpp [--check]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
if [ ! -x "$PSC" ] && [ -x "$PSC.exe" ]; then
  PSC="$PSC.exe"
fi
OUT="$ROOT/bootstrap"
FAMILY="c"
EXT="c"
CHECK=0

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1 ;;
    --family=*) FAMILY="${1#--family=}" ;;
    --family) shift; FAMILY="${1:-}" ;;
    --dir=*) OUT="${1#--dir=}" ;;
    --dir) shift; OUT="${1:-}" ;;
    -h|--help)
      sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "gen_stage0: unknown argument '$1'" >&2
      exit 2
      ;;
  esac
  shift
done

case "$FAMILY" in
  c) EXT="c" ;;
  cpp) EXT="cpp" ;;
  *) echo "gen_stage0: --family must be 'c' or 'cpp' (got '$FAMILY')" >&2; exit 2 ;;
esac

[ -x "$PSC" ] || { echo "gen_stage0: missing native compiler: $PSC" >&2; exit 1; }

emit() {
  local os="$1" arch="$2" cc="$3" out="$4"
  "$PSC" emit-c "$ROOT/src/main.pengu" \
    --backend="$FAMILY" \
    --target-os="$os" --target-arch="$arch" --target-compiler="$cc" \
    --out="$out"
}

bundles() {
  echo "$OUT/psc_stage0_linux_x64.$EXT linux x64 gcc"
  echo "$OUT/psc_stage0_macos_arm64.$EXT macos arm64 clang"
  echo "$OUT/psc_stage0_windows_x64.$EXT windows x64 gcc"
}

if [ "$CHECK" -eq 1 ]; then
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/psc-stage0.XXXXXX")"
  trap 'rm -rf "$tmpdir"' EXIT
  stale=0
  while read -r file os arch cc; do
    tmp="$tmpdir/$(basename "$file")"
    emit "$os" "$arch" "$cc" "$tmp" >/dev/null
    if [ ! -f "$file" ]; then
      echo "gen_stage0: $file does not exist; run tools/gen_stage0.sh --family=$FAMILY --dir=$OUT" >&2
      stale=1
    elif ! cmp -s "$tmp" "$file"; then
      echo "gen_stage0: $file is stale; run tools/gen_stage0.sh --family=$FAMILY --dir=$OUT" >&2
      stale=1
    fi
  done < <(bundles)
  if [ "$stale" -ne 0 ]; then
    exit 1
  fi
  echo "gen_stage0: up to date ($FAMILY)"
  exit 0
fi

mkdir -p "$OUT"
while read -r file os arch cc; do
  emit "$os" "$arch" "$cc" "$file"
done < <(bundles)
