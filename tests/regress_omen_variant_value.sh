#!/usr/bin/env bash
# Regresión: una variante de omen cualificada en posición de valor emite el
# compuesto con `.tag` (bug 10).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark
omen E:
    Empty
    Many with count as int
weave show with e as E into string:
    return judge e:
        when Empty -> "empty"
        when Many with count -> "many {count}"
weave main into int:
    let a as E is with Many is with count is 3
    let b as E is E.Empty
    calling spark.println with "{calling show with a}"
    calling spark.println with "{calling show with b}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: variante de omen en valor no compila"; echo "$out"; exit 1; }
[ "$out" = "many 3
empty" ] || { echo "FAIL: imprimió '$out' (esperado many 3 / empty)"; exit 1; }
echo "OK omen variant value"
