#!/usr/bin/env bash
# Fetch, verify and vendor a satellite release tarball.
#
# Usage:
#   tools/fetch_satellite.sh <name> <url> <sha256> \
#       [--version V] [--license SPDX] [--force]
#
# The script:
#   1. downloads the archive to a temp directory (curl);
#   2. verifies sha256 (sha256sum or shasum -a 256);
#   3. extracts it (tar/zip);
#   4. scaffolds std_c/<name>/ when missing (tools/satellite_new.sh);
#   5. copies the upstream tree, LICENSE and SOURCE, and writes pengu.pkg.
#
# It never builds or links the library and it never edits the compiler.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="${1:-}"
URL="${2:-}"
SHA="${3:-}"
[ -n "$NAME" ] && [ -n "$URL" ] && [ -n "$SHA" ] || {
  echo "usage: tools/fetch_satellite.sh <name> <url> <sha256> [--version V] [--license SPDX] [--force]" >&2
  exit 2
}
shift 3 || true
case "$NAME" in
  *[!a-z0-9_-]*|"") echo "fetch_satellite: name must match [a-z0-9_-]+" >&2; exit 2 ;;
esac

VERSION="0.0.0"
LICENSE="UNKNOWN"
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION="${2:?}"; shift 2 ;;
    --license) LICENSE="${2:?}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "fetch_satellite: unknown option $1" >&2; exit 2 ;;
  esac
done

DEST="$ROOT/std_c/$NAME"
if [ -e "$DEST" ] && [ "$FORCE" -ne 1 ]; then
  echo "fetch_satellite: $DEST already exists (use --force to replace the source tree)" >&2
  exit 1
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/pengu-fetch.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
ARCHIVE="$TMP/archive"
echo "fetch_satellite: downloading $URL"
curl -fL --retry 3 --retry-delay 2 -o "$ARCHIVE" "$URL"

got="$(sha256sum "$ARCHIVE" 2>/dev/null | awk '{print $1}')"
if [ -z "$got" ]; then
  got="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
fi
if [ "$got" != "$SHA" ]; then
  echo "fetch_satellite: sha256 mismatch" >&2
  echo "  expected: $SHA" >&2
  echo "  got:      $got" >&2
  exit 1
fi

mkdir -p "$TMP/upstream"
case "$URL" in
  *.zip) unzip -q "$ARCHIVE" -d "$TMP/upstream" ;;
  *.tar.gz|*.tgz) tar -xzf "$ARCHIVE" -C "$TMP/upstream" ;;
  *.tar.xz) tar -xJf "$ARCHIVE" -C "$TMP/upstream" ;;
  *.tar.bz2) tar -xjf "$ARCHIVE" -C "$TMP/upstream" ;;
  *) echo "fetch_satellite: unsupported archive extension in $URL" >&2; exit 1 ;;
esac

# If the archive has a single top-level directory, that is the source root.
SRCROOT="$TMP/upstream"
shopt -s nullglob
entries=("$TMP/upstream"/*)
if [ "${#entries[@]}" -eq 1 ] && [ -d "${entries[0]}" ]; then
  SRCROOT="${entries[0]}"
fi

if [ ! -e "$DEST" ]; then
  "$ROOT/tools/satellite_new.sh" "$NAME" --license "$LICENSE" --version "$VERSION"
fi
mkdir -p "$DEST"
# Copy the upstream tree, but never clobber the metadata files.
while IFS= read -r -d '' f; do
  rel="${f#"$SRCROOT"/}"
  mkdir -p "$DEST/$(dirname "$rel")"
  if [ -d "$f" ]; then
    mkdir -p "$DEST/$rel"
    cp -a "$f/." "$DEST/$rel/"
  else
    cp -a "$f" "$DEST/$rel"
  fi
done < <(find "$SRCROOT" -mindepth 1 -maxdepth 1 -print0)

# Prefer the upstream license text over the placeholder.
for cand in LICENSE LICENSE.md LICENSE.txt LICENCE LICENCE.md COPYING COPYING.txt; do
  if [ -f "$SRCROOT/$cand" ]; then
    cp "$SRCROOT/$cand" "$DEST/LICENSE"
    break
  fi
done

cat > "$DEST/SOURCE" <<SOURCE
name=$NAME
version=$VERSION
url=$URL
sha256=$SHA
license=$LICENSE
fetched=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SOURCE

cat > "$DEST/pengu.pkg" <<PKG
name = "$NAME"
version = "$VERSION"
license = "$LICENSE"
source = "$URL"
sha256 = "$SHA"
include_dirs = ["include"]
libs = ["$NAME"]
wasm = false
PKG

echo "fetch_satellite: vendored $NAME $VERSION into $DEST"
echo "next: review $DEST/build.sh, add std/$NAME.d.pengu and the Latin wrapper, then run"
echo "      bash $DEST/build.sh && bash ./tools/license_check.sh"
