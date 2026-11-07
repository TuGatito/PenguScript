#!/usr/bin/env bash
# Un parametro es un prestamo: moverlo es E0081 (fase 3: move-by-default).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/e.pengu" <<'PENGU'
rune Label derive Drop:
    name as string

weave take with l as Label into int:
    var m as Label is l
    return m.name.len
PENGU
out="$("$PSC" check "$tmp/e.pengu" 2>&1)" && { echo "FAIL: mover un parametro compiló"; exit 1; }
case "$out" in
  *"[E0081]"*"cannot move out of the borrowed parameter"*) : ;;
  *) echo "FAIL: diagnóstico inesperado"; echo "$out"; exit 1 ;;
esac
echo "OK move param"
