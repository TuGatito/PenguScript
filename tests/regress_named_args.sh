#!/usr/bin/env bash
# Regresión: argumentos nombrados inválidos (E0071) y aridad (E0005).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

expect() { # nombre, código, cuerpo
    local name="$1" code="$2" body="$3" out
    cat >"$tmp/$name.pengu" <<PENGU
$body
PENGU
    out="$("$PSC" check "$tmp/$name.pengu" 2>&1)" && { echo "FAIL: $name compiló"; echo "$out"; exit 1; }
    echo "$out" | grep -q "$code" || { echo "FAIL: $name no dio $code"; echo "$out"; exit 1; }
}

COMMON='weave f with a as int, b as int into int:
    return a + b

weave g with a as int, b as int is 1 into int:
    return a + b

rune P:
    n as int

enchanting P:
    weave plus with by as int into P:
        return with n is self->n + by

weave main into int:'

expect unknown E0071 "$COMMON
    return calling f with a is 1, z is 2"

expect duplicate E0071 "$COMMON
    return calling f with a is 1, a is 2"

expect twice E0071 "$COMMON
    return calling f with 1, a is 2"

expect positional_after_named E0071 "$COMMON
    return calling f with a is 1, 2"

expect too_many E0005 "$COMMON
    return calling f with 1, 2, 3"

expect too_few E0005 "$COMMON
    return calling f with 1"

expect missing_named E0005 "$COMMON
    return calling f with b is 2"

expect chain_named E0071 "$COMMON
    var p as P is with n is 1
    var q as P is calling p.plus with 1
        .plus with by is 2
    return q.n"

echo "OK named args"
