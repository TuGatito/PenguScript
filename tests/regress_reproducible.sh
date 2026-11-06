#!/usr/bin/env bash
# Same sources + same toolchain must produce byte-identical binaries.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
for d in a b; do
    mkdir -p "$tmp/$d/src"
    cat >"$tmp/$d/pengu.toml" <<'TOML'
[build]
entry = "src/main.pengu"
name = "rep"
output = "exe"
TOML
    cat >"$tmp/$d/src/main.pengu" <<'PENGU'
weave main into int:
    calling print with "reproducible"
    return 0
PENGU
    (cd "$tmp/$d" && "$PSC" build . --profile=release --no-cache >/dev/null)
done
ha="$(sha256sum "$tmp/a/build/app" | cut -d' ' -f1)"
hb="$(sha256sum "$tmp/b/build/app" | cut -d' ' -f1)"
[ "$ha" = "$hb" ] || { echo "release hashes differ: $ha != $hb"; exit 1; }
echo "OK reproducible release artifact"
