#!/usr/bin/env bash
# Compile-time pointer-safety regressions. Requires psc.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

expect_code() {
  local name="$1" want="$2" src="$3"
  printf '%s\n' "$src" >"$TMP/$name.pengu"
  if "$PSC" check "$TMP/$name.pengu" >"$TMP/$name.out" 2>&1; then
    echo "FAIL $name: expected $want, compiled"
    fail=$((fail + 1))
    return
  fi
  if ! grep -q "$want" "$TMP/$name.out"; then
    echo "FAIL $name: expected $want"
    tail -5 "$TMP/$name.out"
    fail=$((fail + 1))
  fi
}

expect_ok() {
  local name="$1" src="$2"
  printf '%s\n' "$src" >"$TMP/$name.pengu"
  if ! "$PSC" check "$TMP/$name.pengu" >"$TMP/$name.out" 2>&1; then
    echo "FAIL $name: expected success"
    tail -5 "$TMP/$name.out"
    fail=$((fail + 1))
  fi
}

expect_code sigil_literal E0008 '
weave main into int:
    var p as ref to int is sigil of 1
    return 0
'
expect_code sigil_const E0008 '
const K as int is 1
weave main into int:
    var p as ref to int is sigil of K
    return 0
'
expect_code essence_value E0005 '
weave main into int:
    var x as int is 1
    return essence of x
'
expect_code frozen_write E0008 '
weave main into int:
    var x as int is 1
    var p as ref to frozen int is sigil of x
    set p is 2
    return x
'
expect_code dangling_direct E0051 '
weave bad into ref to int:
    var x as int is 1
    return sigil of x
weave main into int:
    return 0
'
expect_code dangling_indirect E0051 '
weave bad into ref to int:
    var x as int is 1
    var p as ref to int is sigil of x
    return p
weave main into int:
    return 0
'
expect_code dangling_slice E0051 '
weave bad into slice of int:
    var a as array of int is [1, 2, 3]
    return with data is sigil of (a at 0), len is 3, elem_size is size of int
weave main into int:
    return 0
'
expect_code dangling_decay E0051 '
weave bad into ref to int:
    var a as array of int is [1, 2, 3]
    var p as ref to int is a
    return p
weave main into int:
    return 0
'
expect_code dangling_assigned E0051 '
weave bad into ref to int:
    var x as int is 1
    var p as ref to int is null
    set p is sigil of x
    return p
weave main into int:
    return 0
'
expect_code dangling_field E0051 '
rune Holder:
    p as ref to int
weave bad into ref to int:
    var x as int is 1
    var h as Holder is with p is null
    set h.p is sigil of x
    return h.p
weave main into int:
    return 0
'
expect_code const_address E0008 '
const LIMIT as int is 3
weave main into int:
    var p as ref to int is sigil of LIMIT
    return 0
'
expect_code void_arith E0005 '
weave main into int:
    var p as ref to void is null
    var q as ref to void is p + 1
    return 0
'
expect_code frozen_at E0006 '
weave main into int:
    var a as array of int is [1, 2, 3]
    var p as ref to frozen int is sigil of (a at 0)
    set p at 1 is 4
    return 0
'
expect_code pointer_mul E0005 '
weave main into int:
    var x as int is 1
    var p as ref to int is sigil of x
    var q as ref to int is p * 2
    return 0
'
expect_ok auto_deref '
weave main into int:
    var x as int is 1
    var p as ref to int is sigil of x
    set p is 2
    return x
'

if [ "$fail" -ne 0 ]; then
  echo "$fail pointer guard case(s) failed"
  exit 1
fi
echo "OK pointer_guard"
