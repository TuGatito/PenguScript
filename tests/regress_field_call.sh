#!/usr/bin/env bash
# Regresión: un campo que guarda un puntero a función se puede llamar
# (`calling route.handler with context`).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/field_call.pengu" <<'PENGU'
import std.spark

rune Context:
    n as int

rune Route:
    handler as weave with context as ref to Context into int

weave double_it with context as ref to Context into int:
    return context->n * 2

weave main into int:
    var route as Route is with handler is double_it
    var context as Context is with n is 5
    let r as int is calling route.handler with sigil of context
    calling spark.println with "{r}"
    return 0
PENGU
out="$("$PSC" run "$tmp/field_call.pengu" 2>&1)" || { echo "FAIL: campo-función no compila"; echo "$out"; exit 1; }
[ "$out" = "10" ] || { echo "FAIL: campo-función imprime '$out' (esperado 10)"; exit 1; }
echo "OK field call"
