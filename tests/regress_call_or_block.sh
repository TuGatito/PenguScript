#!/usr/bin/env bash
# Regresión: `or:` tras una llamada se aplica al resultado de la llamada, no
# al último argumento (bug 19).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cat >"$tmp/main.pengu" <<'PENGU'
import std.spark
weave get with path as string, handler as weave with n as int into int into result of int to string:
    return calling ok_of with (calling handler with 7)
weave hello with n as int into int:
    return n
weave main into int:
    var r as int is calling get with "/", hello or:
        return 1
    calling spark.println with "{r}"
    return 0
PENGU
out="$("$PSC" run "$tmp/main.pengu" 2>&1)" || { echo "FAIL: or: tras llamada no compila"; echo "$out"; exit 1; }
[ "$out" = "7" ] || { echo "FAIL: imprimió '$out' (esperado 7)"; exit 1; }
echo "OK call or block"
