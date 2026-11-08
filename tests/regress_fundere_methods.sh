#!/usr/bin/env bash
# Regresión: promoción de métodos de `fundere` (E0088, rituales y ausentes).
#
# Un método presente en dos embeds es ambiguo y exige la ruta explícita. Un
# `ritual` del embed no se promueve: construye el embed, no el host.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
case "$PSC" in
  /*) ;;
  *) PSC="$(cd "$(dirname "$PSC")" && pwd)/$(basename "$PSC")" ;;
esac
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

expect_error() { # fichero, patrón, descripción
  local file="$1" pat="$2" what="$3"
  local out
  out="$("$PSC" build "$file" --out="$tmp/out" 2>&1)" \
    && { echo "FAIL: $what compiló"; exit 1; }
  printf '%s' "$out" | grep -q "$pat" \
    || { echo "FAIL: falta el diagnóstico de $what"; echo "$out"; exit 1; }
}

cat >"$tmp/ambiguous_method.pengu" <<'PENGU1'
rune A:
    x as int

enchanting A:
    weave ping into int:
        return 1

rune B:
    x as int

enchanting B:
    weave ping into int:
        return 2

rune H fundere A, B:
    y as int

weave main into int:
    var h as H is with a is (with x is 1), b is (with x is 2), y is 3
    return calling h.ping
PENGU1
expect_error "$tmp/ambiguous_method.pengu" \
  "error\[E0088\]: ambiguous method 'ping' promoted from 'a', 'b'" \
  "un método promovido desde dos embeds"

cat >"$tmp/ambiguous_with.pengu" <<'PENGU2'
rune A:
    x as int

enchanting A:
    weave ping into int:
        return 1

rune B:
    x as int

enchanting B:
    weave ping into int:
        return 2

rune H fundere A, B:
    y as int

weave main into int:
    var h as H is with a is (with x is 1), b is (with x is 2), y is 3
    with h:
        calling .ping
    return 0
PENGU2
expect_error "$tmp/ambiguous_with.pengu" \
  "error\[E0088\]: ambiguous method 'ping' promoted from 'a', 'b'" \
  "un método ambiguo dentro de 'with:'"

cat >"$tmp/ritual.pengu" <<'PENGU3'
rune P:
    v as int

enchanting P:
    ritual weave make with v as int into P:
        return with v is v

rune Q fundere P:
    w as int

weave main into int:
    var q as Q is with p is (with v is 3), w is 4
    var r as P is calling q.make with 5
    return r.v
PENGU3
expect_error "$tmp/ritual.pengu" \
  "error\[E0004\]: ritual 'make' is not promoted by 'fundere'" \
  "un ritual del embed llamado como método"

cat >"$tmp/unknown.pengu" <<'PENGU4'
rune A:
    x as int

enchanting A:
    weave ping into int:
        return 1

rune H fundere A:
    y as int

weave main into int:
    var h as H is with a is (with x is 1), y is 3
    return calling h.nope
PENGU4
expect_error "$tmp/unknown.pengu" \
  "error\[E0004\]: undefined function 'nope'" \
  "un método que no existe"

echo "OK fundere methods"
