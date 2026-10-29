#!/usr/bin/env bash
# Package the just-built compiler and support files for a CI release.
#
# Usage: tools/package_ci.sh [target]
#   target defaults to the host, e.g. linux-x86_64, macos-arm64,
#   windows-x86_64. Writes dist/pengu-<version>-<target>-portable.{tar.gz,zip}.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-$(tr -d '\r\n' < "$ROOT/VERSION")}"
TARGET="${1:-}"

if [ -z "$TARGET" ]; then
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m)"
  case "$os" in
    darwin) os="macos" ;;
    mingw*|msys*|cygwin*) os="windows" ;;
  esac
  case "$arch" in
    x86_64|amd64) arch="x86_64" ;;
    arm64|aarch64) arch="arm64" ;;
  esac
  TARGET="$os-$arch"
fi

case "$TARGET" in
  windows-*) ext="zip" ;;
  *) ext="tar.gz" ;;
esac

NAME="pengu-${VERSION}-${TARGET}-portable"
OUT="$ROOT/dist/$NAME"
ARC="$ROOT/dist/${NAME}.${ext}"

rm -rf "$OUT" "$ARC"
mkdir -p "$OUT/bin" "$OUT/lib" "$OUT/include" "$OUT/std" "$OUT/c_bind_stubs" "$OUT/share/doc/pengu"

if [ -f "$ROOT/build/psc.exe" ]; then
  cp "$ROOT/build/psc.exe" "$OUT/bin/psc.exe"
elif [ -f "$ROOT/build/psc" ]; then
  cp "$ROOT/build/psc" "$OUT/bin/psc"
else
  echo "package_ci: missing build/psc(.exe)" >&2
  exit 1
fi

for bind in "$ROOT/build/pengu-bind.exe" "$ROOT/build/pengu-bind"; do
  if [ -f "$bind" ]; then
    cp "$bind" "$OUT/bin/"
    break
  fi
done

cp -a "$ROOT/build/lib/." "$OUT/lib/"
cp -a "$ROOT/build/include/." "$OUT/include/"
# WebAssembly toolchain artifacts: separate archive and header tree.
if [ -d "$ROOT/build/wasm/lib" ]; then
  mkdir -p "$OUT/lib/wasm" "$OUT/share/pengu"
  cp -a "$ROOT/build/wasm/lib/." "$OUT/lib/wasm/"
fi
if [ -d "$ROOT/build/wasm/include" ]; then
  mkdir -p "$OUT/include/wasm"
  cp -a "$ROOT/build/wasm/include/." "$OUT/include/wasm/"
fi
if [ -f "$ROOT/pengu_wasm_shell.html" ]; then
  mkdir -p "$OUT/share/pengu"
  cp "$ROOT/pengu_wasm_shell.html" "$OUT/share/pengu/pengu_wasm_shell.html"
fi
cp -a "$ROOT/std/." "$OUT/std/"
cp -a "$ROOT/c_bind_stubs/." "$OUT/c_bind_stubs/"

for doc in README.md CHANGELOG.md LICENSE THIRD_PARTY.md; do
  [ -f "$ROOT/$doc" ] && cp "$ROOT/$doc" "$OUT/share/doc/pengu/"
done

echo "$VERSION" > "$OUT/VERSION"
cat > "$OUT/release.toml" <<TOML
[release]
version = "$VERSION"
bind_version = "$VERSION"
layout = "portable"
target = "$TARGET"
TOML

if [ "$ext" = "zip" ]; then
  if command -v zip >/dev/null 2>&1; then
    (cd "$ROOT/dist" && zip -qr "${NAME}.zip" "$NAME")
  else
    powershell.exe -NoProfile -Command \
      "Compress-Archive -LiteralPath '$(cygpath -w "$OUT")' -DestinationPath '$(cygpath -w "$ARC")' -Force"
  fi
else
  tar -czf "$ARC" -C "$ROOT/dist" "$NAME"
fi

rm -rf "$OUT"
echo "package_ci: $ARC"
