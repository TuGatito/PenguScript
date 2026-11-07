#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/a.pengu" <<'PENGU'
weave main into int:
    set zz is 1
    return 0
PENGU
out="$("$PSC" check "$tmp/a.pengu" 2>&1)" && { echo "FAIL: set a nombre indefinido compiló"; exit 1; }
case "$out" in
  *"E0004"*"assignment to an undeclared name 'zz'"*) : ;;
  *) echo "FAIL: diagnóstico inesperado"; echo "$out"; exit 1 ;;
esac
echo "OK assign undeclared"
