#!/usr/bin/env bash
# `@mutates` promovido: la mutación se escribe en el campo del embed.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/ok.pengu" <<'PENGU1'
rune Core:
    n as int

enchanting Core:
    @mutates
    weave bumped with dx as int into Core:
        return with n is self->n + dx

rune Mid fundere Core:
    mid as int

weave main into int:
    var m as Mid is with core is (with n is 1), mid is 2
    calling m.bumped with 10
    if m.core.n != 11:
        return 1
    return 0
PENGU1

if ! "$PSC" run "$tmp/ok.pengu" --no-cache >/dev/null 2>"$tmp/err"; then
    echo "FAIL: la mutación promovida no compila ni ejecuta" >&2
    cat "$tmp/err" >&2
    exit 1
fi

# El write-back tiene que apuntar al campo del embed, no al host.
if ! "$PSC" emit-c "$tmp/ok.pengu" 2>/dev/null | grep -q 'm.core = Core_bumped(&(m.core), 10);'; then
    echo "FAIL: el write-back de @mutates promovido no escribe en el embed" >&2
    exit 1
fi

cat >"$tmp/expr.pengu" <<'PENGU2'
rune Core:
    n as int

enchanting Core:
    @mutates
    weave bumped with dx as int into Core:
        return with n is self->n + dx

rune Mid fundere Core:
    mid as int

weave main into int:
    var m as Mid is with core is (with n is 1), mid is 2
    var v as Core is calling m.bumped with 10
    return v.n
PENGU2

if ! "$PSC" check "$tmp/expr.pengu" >"$tmp/out" 2>&1; then
    if ! grep -q 'error\[E0066\]: mutating method used as an expression' "$tmp/out"; then
        echo "FAIL: se esperaba E0066 al usar un @mutates promovido como expresión" >&2
        cat "$tmp/out" >&2
        exit 1
    fi
else
    echo "FAIL: un @mutates promovido usado como expresión debería fallar" >&2
    exit 1
fi

echo "OK fundere @mutates promovido"
