#!/usr/bin/env bash
# Regresión: llamar a un método genérico (Signal.set) sobre un campo de un
# rune debe resolver la instancia concreta, no pasar el valor como void*.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
rune Cell shard T:
    value as T

enchanting Cell shard T:
    weave set with v as T into void:
        set self->value is v

rune App:
    cell as Cell of int

weave app into ref to App:
    static var a as App is with cell is (with value is 0)
    return sigil of a

weave main into int:
    var a as ref to App is calling app
    calling a->cell.set with 5
    return a->cell.value
PENGU
"$PSC" build "$tmp/main.pengu" >/dev/null 2>&1 || { echo "FAIL: método genérico sobre campo no compila"; exit 1; }
echo "OK generic field method"
