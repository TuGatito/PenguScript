#!/usr/bin/env bash
# Regresión de etiquetas de loop (0.43.0).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fail=0
expect() {
  local name="$1" code="$2" body="$3"
  printf '%s\n' "$body" > "$tmp/$name.pengu"
  local out
  out="$("$PSC" check "$tmp/$name.pengu" 2>&1)"
  if [ $? -eq 0 ]; then
    echo "FAIL: $name compiló (se esperaba $code)"
    fail=1
    return
  fi
  if ! printf '%s' "$out" | grep -q "$code"; then
    echo "FAIL: $name no reportó $code"
    printf '%s\n' "$out" | head -5
    fail=1
    return
  fi
}

expect unknown_break E0004 'weave main into int:
    for i from 0 to 3:
        break nope
    return 0
'

expect unknown_continue E0004 'weave main into int:
    for i from 0 to 3:
        continue nope
    return 0
'

expect duplicate_label E0069 'weave main into int:
    a: for i from 0 to 2:
        a: for j from 0 to 2:
            break a
    return 0
'

expect label_out_of_scope E0007 'weave main into int:
    for i from 0 to 2:
        break inner
    inner: while true:
        break inner
    return 0
'

if [ "$fail" -eq 0 ]; then
  echo "OK labels"
fi
exit "$fail"
