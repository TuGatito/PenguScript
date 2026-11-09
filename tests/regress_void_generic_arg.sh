#!/usr/bin/env bash
# Regresión C5: `void` no es un argumento de tipo válido; debe ser un error
# semántico claro, no C inválido (`void fallback`).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.functor as functor
weave main into int:
    var f as functor.Fn1 of int, void is transmute 0 to functor.Fn1 of int, void
    return 0
PENGU
out="$("$PSC" check "$tmp/main.pengu" 2>&1)" && { echo "FAIL: aceptó Fn1 of int, void"; echo "$out"; exit 1; }
printf '%s' "$out" | grep -q "cannot be 'void'" || { echo "FAIL: mensaje inesperado"; echo "$out"; exit 1; }
echo "OK void generic arg rejected"
