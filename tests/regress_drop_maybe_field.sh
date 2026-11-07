#!/usr/bin/env bash
# `maybe`/`result` aun no se clonan: un rune `derive Drop` no puede tenerlos
# como campo (la copia superficial acabaria en doble-free).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/e.pengu" <<'PENGU'
rune Label derive Drop:
    name as maybe string
PENGU
out="$("$PSC" check "$tmp/e.pengu" 2>&1)" && { echo "FAIL: un campo maybe en Drop compiló"; exit 1; }
case "$out" in
  *"'maybe' and 'result' fields cannot be cloned yet"*) : ;;
  *) echo "FAIL: diagnóstico inesperado"; echo "$out"; exit 1 ;;
esac
echo "OK drop maybe field"
