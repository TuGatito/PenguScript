#!/usr/bin/env bash
# Regresión: los inicializadores `with campo is expr` validan el campo en sema
# (P1-d: un campo inexistente debe dar E0004, no un error de gcc) y detectan
# duplicados; los `with` anidados van entre paréntesis (P1-c/D8).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in
  /*) ;;
  *) PSC="$(cd "$(dirname "$PSC")" && pwd)/$(basename "$PSC")" ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

cat >"$tmp/bad_field.pengu" <<'PENGU'
rune P derive Nexus:
    x as int
weave main into int:
    var a as P is with z is 1
    return a.x
PENGU
out="$("$PSC" build "$tmp/bad_field.pengu" --out="$tmp/bad_field" 2>&1)" \
  && { echo "FAIL: un campo inexistente compiló"; exit 1; }
printf '%s' "$out" | grep -q "error\[E0004\]: rune 'P' has no field 'z'" \
  || { echo "FAIL: falta el diagnóstico del campo inexistente"; echo "$out"; exit 1; }
printf '%s' "$out" | grep -q "parenthesized" \
  || { echo "FAIL: falta la ayuda de paréntesis"; echo "$out"; exit 1; }

cat >"$tmp/dup_field.pengu" <<'PENGU'
rune P derive Nexus:
    x as int
    y as int
weave main into int:
    var a as P is with x is 1, x is 2
    return a.x
PENGU
out="$("$PSC" build "$tmp/dup_field.pengu" --out="$tmp/dup_field" 2>&1)" \
  && { echo "FAIL: un campo duplicado compiló"; exit 1; }
printf '%s' "$out" | grep -q "initialized twice" \
  || { echo "FAIL: falta el diagnóstico de duplicado"; echo "$out"; exit 1; }

cat >"$tmp/nested.pengu" <<'PENGU'
import std.spark
rune P derive Nexus:
    x as int
rune Q derive Nexus:
    p as P
    y as int
weave main into int:
    var q as Q is with p is (with x is 1), y is 2
    calling spark.println with "{q.p.x},{q.y}"
    banish q
    return 0
PENGU
out="$(cd "$tmp" && "$PSC" run nested.pengu 2>&1)" \
  || { echo "FAIL: el inicializador anidado parentizado no compila/ejecuta"; echo "$out"; exit 1; }
[ "$out" = "1,2" ] || { echo "FAIL: imprimió '$out'"; exit 1; }

echo "OK with fields"
