#!/usr/bin/env bash
# `@export` no puede devolver un `Drop` por valor: C no tiene destructor y el
# llamador no tendría forma de liberarlo (E0084).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/e.pengu" <<'PENGU'
rune Label derive Drop:
    name as string

@export("label_new")
weave make_label into Label:
    return with name is "x"
PENGU
out="$("$PSC" check "$tmp/e.pengu" 2>&1)" && { echo "FAIL: @export devolviendo Drop compiló"; exit 1; }
case "$out" in
  *"[E0084]"*"exported weave cannot return a 'Drop' value"*) : ;;
  *) echo "FAIL: diagnóstico inesperado"; echo "$out"; exit 1 ;;
esac
echo "OK export drop"
