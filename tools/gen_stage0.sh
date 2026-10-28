#!/usr/bin/env bash
# Regenerate bootstrap/psc_stage0.c from the current compiler sources.
#
# Run it with a working native `psc` (normally ./build/psc) after changing the
# compiler, and commit the resulting bundle. CI uses
# tools/build_bootstrap.sh to turn that C file into a native bootstrap.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
OUT="$ROOT/bootstrap/psc_stage0.c"

[ -x "$PSC" ] || { echo "gen_stage0: missing native compiler: $PSC" >&2; exit 1; }

if [ "${1:-}" = "--check" ]; then
  tmp="$(mktemp "${TMPDIR:-/tmp}/psc-stage0.XXXXXX.c")"
  trap 'rm -f "$tmp"' EXIT
  "$PSC" emit-c "$ROOT/src/main.pengu" --out="$tmp" >/dev/null
  if ! cmp -s "$tmp" "$OUT"; then
    echo "gen_stage0: $OUT is stale; run tools/gen_stage0.sh" >&2
    exit 1
  fi
  echo "gen_stage0: up to date"
  exit 0
fi

"$PSC" emit-c "$ROOT/src/main.pengu" --out="$OUT"
