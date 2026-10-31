#!/usr/bin/env bash
# Create the skeleton for a new std_c satellite (no upstream source yet).
#
# Usage:
#   tools/satellite_new.sh <name> [--license SPDX] [--version V] [--force]
#
# The generated LICENSE is a placeholder on purpose: tools/license_check.sh
# fails until the real upstream text is copied in.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="${1:-}"
[ -n "$NAME" ] || { echo "usage: tools/satellite_new.sh <name> [--license SPDX] [--version V] [--force]" >&2; exit 2; }
shift || true
case "$NAME" in
  *[!a-z0-9_-]*|"") echo "satellite_new: name must match [a-z0-9_-]+" >&2; exit 2 ;;
esac

LICENSE="UNKNOWN"
VERSION="0.0.0"
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --license) LICENSE="${2:?}"; shift 2 ;;
    --version) VERSION="${2:?}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "satellite_new: unknown option $1" >&2; exit 2 ;;
  esac
done

DEST="$ROOT/std_c/$NAME"
if [ -e "$DEST" ] && [ "$FORCE" -ne 1 ]; then
  echo "satellite_new: $DEST already exists (use --force to extend)" >&2
  exit 1
fi
mkdir -p "$DEST/include" "$DEST/src" "$DEST/patches" "$DEST/tests"

cat > "$DEST/README.md" <<README
# $NAME

Vendored satellite for PenguScript.

- Upstream: TODO (URL, tag/commit)
- License: $LICENSE (replace \`LICENSE\` with the full upstream text)
- Binding: \`std/$NAME.d.pengu\` (original library name)
- Wrapper: \`std/<latin-name>.pengu\` (public PenguScript API)

Checklist before merging:

- [ ] pinned source + \`SOURCE\` (URL, SHA256, version)
- [ ] upstream \`LICENSE\` copied verbatim
- [ ] \`build.sh\` produces \`build/lib/lib$NAME.a\`
- [ ] binding declares \`include\`/\`link\`; wrapper exposes PenguString/PenguSlice
- [ ] ASan/UBSan + fuzz test
- [ ] Windows/macOS/Linux smoke test (document platform gates)
- [ ] \`THIRD_PARTY.md\`, \`std_c/README.md\` and release license bundle updated
- [ ] \`tools/size_report.sh\` shows 0 bytes when the module is imported but unused
README

cat > "$DEST/LICENSE" <<LICENSE
TODO: copy the full upstream license text here.
SPDX identifier: $LICENSE
LICENSE
cat > "$DEST/SOURCE" <<SOURCE
name=$NAME
version=$VERSION
url=TODO
sha256=TODO
license=$LICENSE
fetched=never
SOURCE

cat > "$DEST/pengu.pkg" <<PKG
name = "$NAME"
version = "$VERSION"
license = "$LICENSE"
source = "TODO"
sha256 = "TODO"
include_dirs = ["include"]
libs = ["$NAME"]
wasm = false
PKG

cat > "$DEST/build.sh" <<'BUILD'
#!/usr/bin/env bash
# Build this satellite into build/lib/lib<name>.a. The compiler links it only
# through the module's `link "<name>"` declaration.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
NAME="$(basename "$HERE")"
OUT="$ROOT/build/lib"
OBJ="$ROOT/build/obj/$NAME"
CC="${CC:-cc}"
CFLAGS="${CFLAGS:--O2 -fPIC -ffunction-sections -fdata-sections -Wall}"
mkdir -p "$OUT" "$OBJ"

sources=()
while IFS= read -r f; do sources+=("$f"); done < <(find "$HERE/src" "$HERE" -maxdepth 1 -type f -name '*.c' 2>/dev/null | sort -u)
if [ "${#sources[@]}" -eq 0 ]; then
  echo "build.sh: no .c sources under $HERE/src" >&2
  exit 1
fi
objs=()
for src in "${sources[@]}"; do
  obj="$OBJ/$(basename "${src%.c}").o"
  "$CC" $CFLAGS -I"$HERE/include" -I"$HERE/src" -I"$HERE" -c "$src" -o "$obj"
  objs+=("$obj")
done
ar rcs "$OUT/lib$NAME.a" "${objs[@]}"
echo "built $OUT/lib$NAME.a"
BUILD
chmod +x "$DEST/build.sh"

echo "satellite_new: created $DEST"
echo "next: copy the upstream sources into $DEST/src, the license into $DEST/LICENSE,"
echo "      and write std/$NAME.d.pengu + the Latin wrapper."
