#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/omen.pengu" <<'PENGU'
omen Color with string:
    RED
    GREEN

weave main into int:
    return 0
PENGU
out="$("$PSC" check "$tmp/omen.pengu" 2>&1)" && { echo "FAIL: string omen compiló"; exit 1; }
case "$out" in
  *E0005*"string-valued omens are not implemented yet"*) : ;;
  *) echo "FAIL: falta el diagnóstico"; echo "$out"; exit 1 ;;
esac
echo "OK string omens"
