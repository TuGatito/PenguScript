#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/b.pengu" <<'PENGU'
weave main into int:
    banish "hello"
    return 0
PENGU
out="$("$PSC" check "$tmp/b.pengu" 2>&1)" && { echo "FAIL: banish de un literal compiló"; exit 1; }
case "$out" in
  *"banish needs a place"*) : ;;
  *) echo "FAIL: diagnóstico inesperado"; echo "$out"; exit 1 ;;
esac
echo "OK banish literal"
