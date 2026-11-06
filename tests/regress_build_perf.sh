#!/usr/bin/env bash
# A warm build of a small project must be < 2 s and must not call the C compiler.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[build]
entry = "src/main.pengu"
output = "exe"
TOML
cat >"$tmp/src/main.pengu" <<'PENGU'
weave main into int:
    return 0
PENGU
cd "$tmp"
export PSC_CACHE_DIR="$tmp/cache"
"$PSC" build . >/dev/null
start=$(date +%s%N)
out="$("$PSC" build . --verbose 2>&1)"
end=$(date +%s%N)
ms=$(( (end - start) / 1000000 ))
[ "$ms" -lt 2000 ] || { echo "warm build took ${ms} ms (>2000)"; exit 1; }
if printf '%s\n' "$out" | grep -q '^cc:'; then echo "warm build invoked cc"; exit 1; fi
echo "OK warm build ${ms} ms"
