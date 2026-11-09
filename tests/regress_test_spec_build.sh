#!/usr/bin/env bash
# Regresión C2 (contrato funcional): una especialización creada sólo por un
# bloque `test` no debe romper el build normal. El build puede emitirla de más
# (bloat conocido), pero debe compilar y enlazar; `psc test` debe ejecutarla.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.functor as functor
import std.spark
import std.ward

rune Ctx:
    base as int

weave add_base with c as ref to Ctx, a as int into int:
    return a + c->base

weave is_long with c as ref to Ctx, a as string into bool:
    return a.len > c->base

weave main into int:
    var c as Ctx is with base is 40
    var f as functor.Fn1 of int, int is calling functor.make_fn1 with add_base, (sigil of c)
    var x as int is calling f.call with 2
    calling spark.println with "{x}"
    return 0

test "fn1 string bool only in tests":
    var c as Ctx is with base is 2
    var g as functor.Fn1 of string, bool is calling functor.make_fn1 with is_long, (sigil of c)
    var y as bool is calling g.call with "pengu"
    calling ward.assert_eq_bool with y, true
PENGU
out="$("$PSC" build "$tmp/main.pengu" 2>&1)" || { echo "FAIL: build normal rompe por una spec de test"; echo "$out"; exit 1; }
out="$("$PSC" test "$tmp/main.pengu" 2>&1)" || { echo "FAIL: psc test"; echo "$out"; exit 1; }
printf '%s\n' "$out" | grep -q 'All 1 test(s) passed' || { echo "FAIL: test no ejecutado: $out"; exit 1; }
echo "OK test-only specialization builds"
