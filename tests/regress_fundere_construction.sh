#!/usr/bin/env bash
# Regresión: construcción de un host `fundere` — campos promovidos, ambigüedad
# entre dos embeds, y el conflicto entre inicializar un embed por su nombre y
# por sus campos promovidos.
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
  out="$("$PSC" check "$file" 2>&1)" && { echo "FAIL: $what compiló"; exit 1; }
  printf '%s' "$out" | grep -q "$pat" \
    || { echo "FAIL: falta el diagnóstico de $what"; echo "$out"; exit 1; }
}

expect_ok() { # fichero, descripción
  local file="$1" what="$2"
  "$PSC" check "$file" >/dev/null 2>&1 \
    || { echo "FAIL: $what no compila"; "$PSC" check "$file" 2>&1 | head -8; exit 1; }
}

# El mismo campo en dos embeds: hay que escribir la ruta explícita.
cat >"$tmp/ambiguous.pengu" <<'PENGU1'
rune A:
    v as int

rune B:
    v as int

rune H fundere A, B:
    x as int

weave main into int:
    var h as H is with v is 1, x is 2
    return h.x
PENGU1
expect_error "$tmp/ambiguous.pengu" "error\[E0087\]: ambiguous field 'v'" "campo promovido ambiguo"

# El embed entero y sus campos promovidos a la vez: dos designadores en C.
cat >"$tmp/both.pengu" <<'PENGU2'
rune A:
    v as int

rune H fundere A:
    x as int

weave main into int:
    var h as H is with a is (with v is 1), v is 2
    return h.x
PENGU2
expect_error "$tmp/both.pengu" "error\[E0087\]: field 'a' is initialized explicitly" "embed explícito y promovido"

# Un campo que no existe ni propio ni promovido.
cat >"$tmp/unknown.pengu" <<'PENGU3'
rune A:
    v as int

rune H fundere A:
    x as int

weave main into int:
    var h as H is with nope is 1
    return h.x
PENGU3
expect_error "$tmp/unknown.pengu" "error\[E0004\]: rune 'H' has no field 'nope'" "campo inexistente"

# La ruta explícita desambigua.
cat >"$tmp/explicit.pengu" <<'PENGU4'
rune A:
    v as int

rune B:
    v as int

rune H fundere A, B:
    x as int

weave main into int:
    var h as H is with a is (with v is 1), b is (with v is 2), x is 3
    return h.x
PENGU4
expect_ok "$tmp/explicit.pengu" "ruta explícita"

echo "OK fundere construction"
