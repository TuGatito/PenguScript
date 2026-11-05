#!/usr/bin/env bash
# Regresión: una interpolación con comillas escapadas y `or else` se evalúa
# (el grupo `{...}` se cerraba mal; bug 16).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark
weave main into int:
    let m as maybe string is some ("ada")
    calling spark.println with "hola {m or else \"none\"}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: interpolación escapada no compila"; echo "$out"; exit 1; }
[ "$out" = "hola ada" ] || { echo "FAIL: imprimió '$out' (esperado hola ada)"; exit 1; }
echo "OK interp escaped"
