#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/b.pengu" <<'PENGU'
weave main into int:
    var xs as list of int is [1, 2]
    return xs at 9
PENGU
set +e
out="$("$PSC" run "$tmp/b.pengu" --no-cache 2>&1)"
rc=$?
set -e
if [ "$rc" -ne 134 ]; then echo "FAIL: rc=$rc (se esperaba 134)"; echo "$out"; exit 1; fi
case "$out" in
  *"Index out of bounds"*) echo "OK bounds" ;;
  *) echo "FAIL: falta el mensaje de límites"; echo "$out"; exit 1 ;;
esac
