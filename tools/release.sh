#!/usr/bin/env bash
# Package PSC + pengu-bind without Python (F10/F11).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${VERSION:-$("$ROOT/build/psc" version | awk '{print $2}')}"
TARGET="${TARGET:-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)}"
DIST="${DIST:-$ROOT/dist}"
BIND="${PENGU_BIND:-$ROOT/build/pengu-bind}"
LAYOUT="${LAYOUT:-both}"
EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"

[ -x "$ROOT/build/psc" ] || { echo "missing build/psc" >&2; exit 1; }
[ -x "$BIND" ] || { echo "missing pengu-bind: $BIND" >&2; exit 1; }
mkdir -p "$DIST"

pack() {
  local layout="$1" root
  root="$DIST/pengu-$VERSION-$TARGET-$layout"
  rm -rf "$root"
  if [ "$layout" = portable ]; then
    mkdir -p "$root/bin" "$root/lib" "$root/include" "$root/std" "$root/c_bind_stubs" "$root/share/doc/pengu"
  else
    mkdir -p "$root/bin" "$root/lib/pengu" "$root/include/pengu" "$root/share/pengu/std" "$root/share/pengu/c_bind_stubs" "$root/share/doc/pengu"
  fi
  cp "$ROOT/build/psc" "$root/bin/psc"
  cp "$BIND" "$root/bin/pengu-bind"
  cp "$ROOT"/build/lib/*.a "$root/lib/" 2>/dev/null || true
  if [ "$layout" = fhs ]; then
    mv "$root"/lib/*.a "$root/lib/pengu/" 2>/dev/null || true
    cp -a "$ROOT"/build/include/. "$root/include/pengu/"
    cp -a "$ROOT"/std/. "$root/share/pengu/std/"
    cp -a "$ROOT"/c_bind_stubs/. "$root/share/pengu/c_bind_stubs/"
  else
    cp -a "$ROOT"/build/include/. "$root/include/"
    cp -a "$ROOT"/std/. "$root/std/"
    cp -a "$ROOT"/c_bind_stubs/. "$root/c_bind_stubs/"
  fi
  for f in README.md CHANGELOG.md LICENSE; do [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$root/share/doc/pengu/"; done
  echo "$VERSION" > "$root/VERSION"
  cat > "$root/release.toml" <<TOML
[release]
version = "$VERSION"
bind_version = "$VERSION"
layout = "$layout"
target = "$TARGET"
TOML
  local arc
  case "$TARGET" in
    windows-*) arc="$DIST/pengu-$VERSION-$TARGET-$layout.zip" ;;
    *) arc="$DIST/pengu-$VERSION-$TARGET-$layout.tar.gz" ;;
  esac
  if [ "${arc##*.}" = zip ]; then
    (cd "$DIST" && zip -qr "$(basename "$arc")" "$(basename "$root")")
  else
    tar --sort=name --mtime="@$EPOCH" --owner=0 --group=0 --numeric-owner \
      -czf "$arc" -C "$DIST" "$(basename "$root")"
  fi
}

[ "$LAYOUT" = portable ] || [ "$LAYOUT" = fhs ] || [ "$LAYOUT" = both ] || { echo "bad LAYOUT" >&2; exit 2; }
[ "$LAYOUT" = fhs ] || pack portable
[ "$LAYOUT" = portable ] || pack fhs
(cd "$DIST" && sha256sum pengu-*.tar.gz pengu-*.zip 2>/dev/null > SHA256SUMS || true)
echo "release: $DIST"
