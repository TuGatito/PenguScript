#!/usr/bin/env bash
# Regresión: la cláusula `fundere` solo compone runes (E0085), exige un nombre
# de campo cuando no puede deducirlo (E0089), no admite dos embeds con el mismo
# nombre ni un nombre que choque con un campo propio, y avisa del orden
# `shard`/`fundere` (E0000 con mensaje propio).
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

cat >"$tmp/not_rune.pengu" <<'PENGU'
rune Bad fundere int:
    x as int
PENGU
expect_error "$tmp/not_rune.pengu" "error\[E0085\]: 'fundere' requires a rune, not 'int'" \
  "un embed de tipo base"

cat >"$tmp/multi.pengu" <<'PENGU'
rune Box shard K and V:
    key as K
    val as V
rune Holder fundere Box of string and int:
    x as int
PENGU
expect_error "$tmp/multi.pengu" "error\[E0089\]: this 'fundere' type has no implicit field name" \
  "un embed genérico con dos argumentos sin 'as'"

cat >"$tmp/collide.pengu" <<'PENGU'
rune Point:
    position as int
rune Host fundere Point:
    point as int
PENGU
expect_error "$tmp/collide.pengu" "error\[E0089\]: embed field 'point' collides with a field of 'Host'" \
  "un embed cuyo nombre choque con un campo propio"

cat >"$tmp/duplicate.pengu" <<'PENGU'
rune Point:
    x as int
rune Host fundere Point, Point:
    y as int
PENGU
expect_error "$tmp/duplicate.pengu" "error\[E0089\]: two 'fundere' embeds use the field name 'point'" \
  "dos embeds con el mismo nombre"

cat >"$tmp/order.pengu" <<'PENGU'
rune Box shard K:
    value as K
rune Holder shard T fundere Box of T where T: Num:
    health as int
PENGU
expect_error "$tmp/order.pengu" "error\[E0000\]: 'fundere' comes before 'shard'" \
  "'fundere' escrito después de 'shard'"

# El orden correcto compila y el embed es el primer campo del `struct`.
cat >"$tmp/good.pengu" <<'PENGU'
rune Box shard K:
    value as K
rune Holder fundere Box of T shard T where T: Num:
    health as int
weave main into int:
    var h as Holder of int is with box is (with value is 3), health is 1
    return h.box.value
PENGU
"$PSC" check "$tmp/good.pengu" || { echo "FAIL: el orden canónico no compila"; exit 1; }
"$PSC" emit-c "$tmp/good.pengu" 2>/dev/null | grep -q "Box__int box;" \
  || { echo "FAIL: el embed no es el primer campo del struct"; exit 1; }

echo "OK fundere embeds"
