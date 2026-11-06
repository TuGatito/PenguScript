#!/usr/bin/env bash
# psc gc --max-size: la caché no debe crecer sin límite.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export PSC_CACHE_DIR="$TMP/cache"
mkdir -p "$PSC_CACHE_DIR/deadbeef"
dd if=/dev/zero of="$PSC_CACHE_DIR/deadbeef/app" bs=1M count=4 status=none
before=$("$PSC" gc --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["bytes_before"])')
[ "$before" -ge 4194304 ] || { echo "unexpected cache size: $before"; exit 1; }
"$PSC" gc --max-size=1 >/dev/null
after=$("$PSC" gc --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["bytes_after"])')
[ "$after" -lt 1048576 ] || { echo "cache not pruned: $after"; exit 1; }
echo "OK gc size cap"
