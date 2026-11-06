#!/usr/bin/env bash
# Release tarballs: reproducible, self-contained and able to build a project.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
BIND="${PENGU_BIND:-$ROOT/build/pengu-bind}"
if [ ! -x "$BIND" ]; then
  echo "SKIP release: missing pengu-bind"
  exit 0
fi
TMP="$(mktemp -d "${TMPDIR:-/tmp}/psc-release.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export SOURCE_DATE_EPOCH=1700000000
export PENGU_BIND="$BIND"
DIST="$TMP/dist-a" bash "$ROOT/tools/release.sh" >/dev/null
DIST="$TMP/dist-b" bash "$ROOT/tools/release.sh" >/dev/null
VER="$(cat "$ROOT/VERSION")"
hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}
SUM=""
for f in "$TMP"/dist-a/*.tar.gz; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  other="$TMP/dist-b/$base"
  [ -f "$other" ] || { echo "FAIL release: missing $base in second run" >&2; exit 1; }
  a="$(hash_file "$f")"
  b="$(hash_file "$other")"
  [ "$a" = "$b" ] || { echo "FAIL release: $base is not reproducible" >&2; exit 1; }
  SUM="$a"
done
[ -n "$SUM" ] || { echo "FAIL release: no tarball was produced" >&2; exit 1; }
mkdir -p "$TMP/out"
tar -xzf "$TMP"/dist-a/*portable*.tar.gz -C "$TMP/out"
PKG="$(find "$TMP/out" -maxdepth 1 -mindepth 1 -type d | head -1)"
"$PKG/bin/psc" version | grep -q "$VER" || { echo "FAIL release: version mismatch" >&2; exit 1; }
mkdir -p "$TMP/hello/src"
printf 'weave main into int:\n    calling print with "hello release\\n"\n    return 0\n' > "$TMP/hello/src/main.pengu"
printf '[project]\nname = "hello"\n\n[build]\nentry = "src/main.pengu"\n' > "$TMP/hello/pengu.toml"
"$PKG/bin/psc" build "$TMP/hello" >/dev/null
out="$("$TMP/hello/build/hello")"
[ "$out" = "hello release" ] || { echo "FAIL release: smoke output '$out'" >&2; exit 1; }
echo "OK reproducible release tarball"
