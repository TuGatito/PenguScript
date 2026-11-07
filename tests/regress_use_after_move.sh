#!/usr/bin/env bash
# Usar un binding despues de moverlo es E0080 (fase 3: move-by-default).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/e.pengu" <<'PENGU'
rune Label derive Drop:
    name as string

weave main into int:
    var a as Label is with name is "x"
    var b as Label is a
    return a.name.len
PENGU
out="$("$PSC" check "$tmp/e.pengu" 2>&1)" && { echo "FAIL: usar un valor movido compiló"; exit 1; }
case "$out" in
  *"[E0080]"*"was moved and cannot be used again"*) : ;;
  *) echo "FAIL: diagnóstico inesperado"; echo "$out"; exit 1 ;;
esac
echo "OK use after move"
