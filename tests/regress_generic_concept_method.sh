#!/usr/bin/env bash
# Regresión C4: un método de concepto implementado en un rune genérico debe
# especializarse con el receptor concreto; antes se emitía `PlainRow__T` y
# `void**`, que C no compila.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark

concept Row shard T:
    weave update with item as ref to T into void

rune PlainRow shard T:
    value as T

bind PlainRow with Row:
    weave update with item as ref to T into void:
        set self->value is essence of item

weave apply_row shard T, R where R: Row with r as ref to R, item as ref to T into void:
    calling r.update with item

weave main into int:
    var r as PlainRow of int is with value is 1
    var v as int is 7
    calling apply_row of int, (PlainRow of int) with (sigil of r), (sigil of v)
    calling spark.println with "{r.value}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: no compila"; echo "$out"; exit 1; }
printf '%s\n' "$out" | grep -qx '7' || { echo "FAIL: salida '$out' (esperado 7)"; exit 1; }
echo "OK generic concept method"
