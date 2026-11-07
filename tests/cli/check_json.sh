#!/usr/bin/env bash
# `psc check --json` es un alias de `--diagnostics=json`.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/bad.pengu" <<'PENGU'
weave main into int:
    set zz is 1
    return 0
PENGU
out="$("$PSC" check --json "$tmp/bad.pengu" 2>&1 || true)"
case "$out" in
  \[*\"code\":\"E0004\"*) echo "OK check json" ;;
  *) echo "FAIL: no es JSON con E0004"; echo "$out"; exit 1 ;;
esac
