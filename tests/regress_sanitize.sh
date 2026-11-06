#!/usr/bin/env bash
# ASan/UBSan flags must reach compile and link, and be part of the cache key.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
printf 'int main(void){return 0;}\n' > /tmp/pengu-san-probe.c
if ! "${CC:-cc}" -fsanitize=address /tmp/pengu-san-probe.c -o /tmp/pengu-san-probe 2>/dev/null; then
    echo "SKIP sanitize: no ASan support"
    exit 0
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[build]
entry = "src/main.pengu"
name = "san"
output = "exe"
TOML
cat >"$tmp/src/main.pengu" <<'PENGU'
weave main into int:
    return 7
PENGU
cd "$tmp"
export PSC_CACHE_DIR="$tmp/cache"
"$PSC" build . --sanitize=address --no-cache >/dev/null || { echo "san build failed"; exit 1; }
art="$(find "$tmp/build" -maxdepth 1 -type f -perm -u+x | head -1)"
[ -n "$art" ] || { echo "no artifact"; ls -la build; exit 1; }
if command -v ldd >/dev/null 2>&1; then
    ldd "$art" | grep -q libasan || { echo "ASan runtime not linked"; exit 1; }
fi
set +e
"$art"
code=$?
set -e
[ "$code" -eq 7 ] || { echo "sanitized binary returned $code"; exit 1; }
"$PSC" build . --sanitize=address >/dev/null   # hits the sanitizer entry
"$PSC" build . >/dev/null                      # plain build must not reuse it
if ldd "$art" 2>/dev/null | grep -q libasan; then echo "plain build reused ASan artifact"; exit 1; fi
echo "OK sanitizer profiles"
