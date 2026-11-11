#!/usr/bin/env bash
# Regresión: `fundere` propaga `Drop` (move-only) y `Nexus` (banishable).
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

expect_ok() { # fichero, descripción
  local file="$1" what="$2"
  "$PSC" build "$file" --out="$tmp/okout" >/dev/null 2>&1 \
    || { echo "FAIL: $what no compila"; "$PSC" build "$file" --out="$tmp/okout" 2>&1 | head -8; exit 1; }
}

# Un embed `Drop` hace el host move-only: copiarlo y seguir usando el origen es
# un uso después de mover.
cat >"$tmp/moved.pengu" <<'PENGU1'
rune P derive Drop:
    note as string

rune H fundere P:
    x as int

weave main into int:
    var a as H is with p is (with note is "n"), x is 1
    var b as H is a
    return a.x
PENGU1
expect_error "$tmp/moved.pengu" "error\[E0080\]" "copiar un host que es Drop por un embed"

# Un embed `Drop` anidado también propaga.
cat >"$tmp/nested.pengu" <<'PENGU2'
rune P derive Drop:
    note as string

rune M fundere P:
    m as int

rune H fundere M:
    x as int

weave main into int:
    var a as H is with m is (with p is (with note is "n"), m is 2), x is 1
    var b as H is a
    return a.x
PENGU2
expect_error "$tmp/nested.pengu" "error\[E0080\]" "Drop propagado por dos niveles"

# `Nexus` no es `Drop`: el host se copia y se banisha.
cat >"$tmp/nexus.pengu" <<'PENGU3'
rune P:
    note as string

rune H fundere P:
    x as int

weave main into int:
    var a as H is with p is (with note is "n"), x is 1
    var b as H is a
    banish a
    banish b
    return 0
PENGU3
expect_ok "$tmp/nexus.pengu" "host con embed Nexus"

# Sin cleanup en ningún embed, el host es trivial.
cat >"$tmp/plain.pengu" <<'PENGU4'
rune P:
    v as int

rune H fundere P:
    x as int

weave main into int:
    var a as H is with p is (with v is 2), x is 1
    var b as H is a
    return a.x + b.p.v
PENGU4
expect_ok "$tmp/plain.pengu" "host sin cleanup"

echo "OK fundere drop"
