#!/usr/bin/env bash
# E0043: un nombre top-level que empieza por `_` es privado de su modulo.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/proj/src"
cat >"$tmp/proj/pengu.toml" <<'TOML'
[package]
name = "priv"
version = "0.1.0"
TOML

cat >"$tmp/proj/src/a.pengu" <<'PENGU1'
rune Box2:
    n as int

rune _Hidden:
    n as int

const _secret as int is 7

weave public_value into int:
    return 1
PENGU1

cat >"$tmp/proj/src/main.pengu" <<'PENGU2'
import a

weave main into int:
    return calling a.public_value
PENGU2

"$PSC" check "$tmp/proj" >/dev/null 2>"$tmp/ok.err" \
  || { echo "FAIL: el caso publico no debe fallar"; cat "$tmp/ok.err"; exit 1; }

cat >"$tmp/proj/src/main.pengu" <<'PENGU3'
import a

weave main into int:
    return a._secret
PENGU3
"$PSC" check "$tmp/proj" >/dev/null 2>"$tmp/val.err" \
  && { echo "FAIL: a._secret debe fallar"; exit 1; }
grep -q "E0043" "$tmp/val.err" \
  || { echo "FAIL: falta E0043 para un valor privado"; cat "$tmp/val.err"; exit 1; }

cat >"$tmp/proj/src/main.pengu" <<'PENGU4'
import a

weave main into int:
    var h as a._Hidden is with n is 1
    return h.n
PENGU4
"$PSC" check "$tmp/proj" >/dev/null 2>"$tmp/ty.err" \
  && { echo "FAIL: a._Hidden debe fallar"; exit 1; }
grep -q "E0043" "$tmp/ty.err" \
  || { echo "FAIL: falta E0043 para un tipo privado"; cat "$tmp/ty.err"; exit 1; }

cat >"$tmp/proj/src/main.pengu" <<'PENGU5'
import a

weave main into int:
    var h as a.Box2 is with n is 1
    return h.n
PENGU5
"$PSC" check "$tmp/proj" >/dev/null 2>"$tmp/pub.err" \
  || { echo "FAIL: a.Box2 (publico) no debe fallar"; cat "$tmp/pub.err"; exit 1; }

# Campos: `_` es privado; `@public` lo abre.
cat >"$tmp/proj/src/a.pengu" <<'PENGU6'
rune Box2:
    n as int
    @public _tag as int
    _hidden as int
PENGU6
cat >"$tmp/proj/src/main.pengu" <<'PENGU7'
import a

weave main into int:
    var b as a.Box2 is with n is 1
    return b.n + b._tag
PENGU7
"$PSC" check "$tmp/proj" >/dev/null 2>"$tmp/pubf.err" \
  || { echo "FAIL: un campo @public debe leerse"; cat "$tmp/pubf.err"; exit 1; }

cat >"$tmp/proj/src/main.pengu" <<'PENGU8'
import a

weave main into int:
    var b as a.Box2 is with n is 1
    return b._hidden
PENGU8
"$PSC" check "$tmp/proj" >/dev/null 2>"$tmp/prif.err" \
  && { echo "FAIL: un campo privado debe fallar"; exit 1; }
grep -q "E0043" "$tmp/prif.err" \
  || { echo "FAIL: falta E0043 para un campo privado"; cat "$tmp/prif.err"; exit 1; }

echo "OK privacy"
