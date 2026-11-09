#!/usr/bin/env bash
# Regresión C1: un rune genérico cuyos parámetros de tipo solo aparecen dentro
# de tipos de función debe materializar una instancia por sustitución, no
# compartir la plantilla con el último tipo visto.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.functor as functor
import std.spark

rune Ctx:
    base as int

weave add_base with c as ref to Ctx, a as int into int:
    return a + c->base

weave is_long with c as ref to Ctx, a as string into bool:
    return a.len > c->base

weave main into int:
    var c as Ctx is with base is 40
    var f as functor.Fn1 of int, int is calling functor.make_fn1 with add_base, (sigil of c)
    var g as functor.Fn1 of string, bool is calling functor.make_fn1 with is_long, (sigil of c)
    var x as int is calling f.call with 2
    var y as bool is calling g.call with "pengu"
    calling spark.println with "{x}"
    calling spark.println with "{y}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: no compila"; echo "$out"; exit 1; }
printf '%s\n' "$out" | grep -qx '42' || { echo "FAIL: salida '$out' (esperado 42 y false)"; exit 1; }
printf '%s\n' "$out" | grep -qx 'false' || { echo "FAIL: salida '$out' (esperado 42 y false)"; exit 1; }
echo "OK fn-only generic rune"
