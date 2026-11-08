#!/usr/bin/env bash
# Regresión: promoción de campos de `fundere` (E0087 y acceso desconocido).
#
# Un campo presente en dos embeds es ambiguo y exige la ruta explícita; el
# compilador no elige "el primero". Un campo que no existe en el rune se
# diagnostica en sema (antes solo fallaba al compilar el C).
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

cat >"$tmp/ambiguous_field.pengu" <<'PENGU1'
rune A:
    value as int

rune B:
    value as int

rune H fundere A, B:
    other as int

weave main into int:
    var h as H is with a is (with value is 1), b is (with value is 2), other is 3
    return h.value
PENGU1
expect_error "$tmp/ambiguous_field.pengu" \
  "error\[E0087\]: ambiguous field 'value' promoted from 'a', 'b'" \
  "un campo promovido desde dos embeds"

cat >"$tmp/ambiguous_with.pengu" <<'PENGU2'
rune A:
    value as int

rune B:
    value as int

rune H fundere A, B:
    other as int

weave main into int:
    var h as H is with a is (with value is 1), b is (with value is 2), other is 3
    with h:
        set .value is 9
    return 0
PENGU2
expect_error "$tmp/ambiguous_with.pengu" \
  "error\[E0087\]: ambiguous field 'value' promoted from 'a', 'b'" \
  "un campo ambiguo dentro de 'with:'"

cat >"$tmp/unknown_field.pengu" <<'PENGU3'
rune A:
    value as int

weave main into int:
    var a as A is with value is 1
    return a.nope
PENGU3
expect_error "$tmp/unknown_field.pengu" \
  "error\[E0004\]: rune 'A' has no field 'nope'" \
  "un campo que no existe"

# La ruta explícita desambigua y compila.
cat >"$tmp/explicit_ok.pengu" <<'PENGU4'
rune A:
    value as int

rune B:
    value as int

rune H fundere A, B:
    other as int

weave main into int:
    var h as H is with a is (with value is 1), b is (with value is 2), other is 3
    return h.a.value + h.b.value
PENGU4
"$PSC" build "$tmp/explicit_ok.pengu" --out="$tmp/ok" >/dev/null 2>&1 \
  || { echo "FAIL: la ruta explícita no compiló"; exit 1; }

# W0009: el shadowing es legal, pero `--lint=shadow` lo reporta.
cat >"$tmp/shadow.pengu" <<'PENGU5'
rune A:
    value as int

rune H fundere A:
    value as int

weave main into int:
    var h as H is with a is (with value is 1), value is 2
    return h.value
PENGU5
"$PSC" check "$tmp/shadow.pengu" >/dev/null 2>"$tmp/plain.err" \
  || { echo "FAIL: el shadowing no debe ser un error"; exit 1; }
if grep -q "W0009" "$tmp/plain.err"; then
  echo "FAIL: W0009 debe estar apagado por defecto"
  exit 1
fi
"$PSC" check --lint=shadow "$tmp/shadow.pengu" >/dev/null 2>"$tmp/shadow.err" \
  || { echo "FAIL: --lint=shadow no debe fallar"; exit 1; }
grep -q "warning\[W0009\]: field 'value' in 'H' shadows a field promoted from 'A'" \
  "$tmp/shadow.err" \
  || { echo "FAIL: falta W0009"; cat "$tmp/shadow.err"; exit 1; }

echo "OK fundere fields"
