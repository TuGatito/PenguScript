#!/usr/bin/env bash
# Regresión: `do:` y un `if` multilínea en posición de valor conservan sus
# sentencias y devuelven la última expresión (bug 9).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark
weave main into int:
    let v as int is do:
        var a as int is 5
        a + 4
    let w as int is if v > 0:
        v - 8
    else:
        0
    calling spark.println with "{v} {w}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: bloque en valor no compila"; echo "$out"; exit 1; }
[ "$out" = "9 1" ] || { echo "FAIL: imprimió '$out' (esperado 9 1)"; exit 1; }
echo "OK block value"
