#!/usr/bin/env bash
# Regresión: un `alias` de tipo función se puede llamar (E0020).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/alias_fn.pengu" <<'PENGU'
import std.spark

rune Context:
    n as int

alias Handler as weave with context as ref to Context into int

weave apply with f as Handler, context as ref to Context into int:
    return calling f with context

weave double_it with context as ref to Context into int:
    return context->n * 2

weave main into int:
    var context as Context is with n is 5
    let r as int is calling apply with double_it, sigil of context
    calling spark.println with "{r}"
    return 0
PENGU
out="$("$PSC" run "$tmp/alias_fn.pengu" 2>&1)" || { echo "FAIL: alias de tipo función no compila"; echo "$out"; exit 1; }
[ "$out" = "10" ] || { echo "FAIL: alias de tipo función imprime '$out' (esperado 10)"; exit 1; }
echo "OK alias fn"
