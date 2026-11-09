#!/usr/bin/env bash
# Regresión C3: interpolar una llamada a un método genérico debe usar el tipo
# de retorno concreto, no la plantilla `T` (que antes producía "").
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark

rune Pair shard A, B:
    first as A
    second as B

enchanting Pair shard A, B:
    weave get_a into A:
        return self->first
    weave get_b into B:
        return self->second

weave main into int:
    var p as Pair of int, string is with first is 41, second is "hi"
    calling spark.println with "{calling p.get_a} {calling p.get_b}"
    var a as int is calling p.get_a
    var b as string is calling p.get_b
    calling spark.println with "{a} {b}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: no compila"; echo "$out"; exit 1; }
printf '%s\n' "$out" | grep -qx '41 hi' || { echo "FAIL: salida '$out' (esperado 41 hi)"; exit 1; }
printf '%s\n' "$out" | grep -qx '41 hi' || { echo "FAIL: la segunda línea no es '41 hi'"; exit 1; }
echo "OK generic method interpolation"
