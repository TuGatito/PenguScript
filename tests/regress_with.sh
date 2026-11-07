#!/usr/bin/env bash
# Regresión de `with` como sentencia y de los literales de mapa (0.42.0).
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

COMMON='rune P:
    x as int

weave make into P:
    return with x is 1
'

expect non_addressable E0077 "$COMMON
weave main into int:
    with calling make:
        set .x is 2
    return 0
"

expect unknown_field E0004 "$COMMON
weave main into int:
    var p as P is with x is 1
    with p:
        set .nope is 2
    return 0
"

expect undefined_in_first E0004 "$COMMON
weave main into int:
    var p as P is with x is 1
    with p:
        var q as int is zz
        set .x is q
    return 0
"

expect no_with_field E0004 'weave main into int:
    var q as int is .x
    return q
'

expect map_without_type E0076 'weave main into int:
    var m is {"a": 1}
    return m.len
'

if [ "$fail" -ne 0 ]; then
  exit 1
fi
echo "OK with"
