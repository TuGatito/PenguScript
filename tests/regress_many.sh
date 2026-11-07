#!/usr/bin/env bash
# `many T`: orden (E0024), unicidad (E0023), default (E0074), declare (E0075).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
fails=0
expect() {
  local name="$1" code="$2" body="$3"
  printf '%s\n' "$body" > "$tmp/$name.pengu"
  local out; out="$("$PSC" check "$tmp/$name.pengu" 2>&1)"; local rc=$?
  if [ "$rc" -eq 0 ] || ! grep -q "$code" <<<"$out"; then
    echo "FAIL: $name (rc=$rc, esperaba $code)"; echo "$out" | head -5; fails=$((fails+1))
  fi
}
expect not_last E0024 'weave bad with xs as many int, y as int into int:
    return y
'
expect multiple E0023 'weave bad with xs as many int, ys as many string into int:
    return 0
'
expect with_default E0074 'weave bad with xs as many int is 1 into int:
    return 0
'
expect in_declare E0075 'declare bad with xs as many int into void
'
expect element_type E0005 'weave sum with xs as many int into int:
    return xs.len

weave main into int:
    return calling sum with "x"
'
expect too_many_fixed E0005 'weave one with a as int into int:
    return a

weave main into int:
    return calling one with 1, 2
'
[ "$fails" -eq 0 ] && echo "OK many"
exit "$fails"
