#!/usr/bin/env bash
# Regresión: un genérico que reenvía `of T` a otra función instancia la
# llamada con el tipo sustituido, no con `void*` (bug 3).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark
rune Arena:
    used as int
rune Thing:
    id as int
weave arena_alloc_one shard T with a as ref to Arena into ref to T:
    set a->used is a->used + 1
    return null
weave gen_alloc shard T with a as ref to Arena into ref to T:
    return calling arena_alloc_one of T with a
weave main into int:
    var arena as Arena is with used is 0
    var t as ref to Thing is calling gen_alloc of Thing with sigil of arena
    calling spark.println with "{arena.used}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: genérico reenviado no compila"; echo "$out"; exit 1; }
[ "$out" = "1" ] || { echo "FAIL: imprimió '$out' (esperado 1)"; exit 1; }
echo "OK generic arg subst"
