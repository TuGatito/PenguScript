#!/usr/bin/env bash
# Regresiones de `judge` y omens: E0027/E0029/E0044 y variantes sin `else`.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
pass=0
fail=0

expect() {
    local name="$1" code="$2" body="$3"
    printf '%s\n' "$body" > "$tmp/$name.pengu"
    local out
    out="$("$PSC" check "$tmp/$name.pengu" 2>&1)"
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "FAIL: $name compiló"
        fail=$((fail + 1))
        return
    fi
    if ! printf '%s' "$out" | grep -q "$code"; then
        echo "FAIL: $name no reportó $code"
        printf '%s\n' "$out" | head -5
        fail=$((fail + 1))
        return
    fi
    pass=$((pass + 1))
}

expect duplicate E0027 'omen K:
    A is 1
    B is 1
'
expect nonconst E0029 'weave f into int:
    return 1
omen K:
    A is calling f
'
expect missing_branch E0044 'omen K:
    A
    B
weave main into int:
    var k as K is A
    return judge k:
        when A -> 1
'
expect guarded_exhaustive E0044 'omen K:
    A
    B
weave main into int:
    var k as K is A
    return judge k:
        when A if true -> 1
'
if [ "$fail" -ne 0 ]; then
    echo "$fail omen regression(s) failed"
    exit 1
fi
echo "OK omens"
