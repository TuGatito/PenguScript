#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

expect() {
  local name="$1" code="$2" body="$3"
  printf '%s\n' "$body" > "$tmp/$name.pengu"
  local out
  out="$("$PSC" check "$tmp/$name.pengu" 2>&1)" && { echo "FAIL: $name compiló"; exit 1; }
  case "$out" in
    *"$code"*) : ;;
    *) echo "FAIL: $name no reportó $code"; echo "$out"; exit 1 ;;
  esac
}

expect arity_mismatch E0079 '
rune Pair:
    a as int
    b as int

weave main into int:
    var p as Pair is with a is 1, b is 2
    let (a, b, c) as Pair is p
    return a
'

expect arity_tuple E0079 '
weave pair with a as int, b as int into (int, int):
    return a, b

weave main into int:
    let (a, b, c) is calling pair with 1, 2
    return a
'

expect zero_names E0079 '
rune One:
    a as int

weave main into int:
    let (x, y) as One is with a is 1
    return x
'

expect arity_rune_one E0079 '
rune Pair:
    a as int
    b as int

weave main into int:
    var p as Pair is with a is 1, b is 2
    let (_, _, _) as Pair is p
    return 0
'

echo "OK destructuring"
