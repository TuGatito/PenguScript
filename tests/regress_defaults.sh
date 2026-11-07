#!/usr/bin/env bash
# Defaults: orden (E0072), valor constante y tipo (E0073).
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
expect order E0072 'weave bad with a as int is 1, b as int into int:
    return a + b
'
expect order_three E0072 'weave bad with a as int is 1, b as int is 2, c as int into int:
    return a + b + c
'
expect not_const E0073 'weave bad with a as int, b as int is a + 1 into int:
    return b
'
expect not_const_call E0073 'weave f into int:
    return 1

weave bad with a as int, b as int is calling f into int:
    return b
'
expect type_mismatch E0073 'weave bad with s as string is 3 into int:
    return 0
'
expect type_mismatch_bool E0073 'weave bad with on as bool is "yes" into int:
    return 0
'
expect generic_inst E0073 'weave pick shard T with a as T, b as T is 5 into T:
    return b

weave main into int:
    var s as string is calling pick with "x"
    return 0
'
[ "$fails" -eq 0 ] && echo "OK defaults"
exit "$fails"
