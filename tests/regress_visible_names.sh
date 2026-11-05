#!/usr/bin/env bash
# Regresión: un nombre suelto resuelve al import del módulo actual, no a la
# función homónima de un módulo consumidor (bug 15).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PSC="${PSC:-$ROOT/build/psc}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cat >"$tmp/pengu.toml" <<'TOML'
[project]
name = "visible_names"
version = "0.1.0"
entry = "src/main.pengu"
output = "exe"
[build]
src_dir = "src"
cc = "gcc"
TOML
cat >"$tmp/src/err.pengu" <<'PENGU'
weave not_found into int:
    return 404
PENGU
cat >"$tmp/src/app.pengu" <<'PENGU'
import err
weave call into int:
    return calling not_found
PENGU
cat >"$tmp/src/main.pengu" <<'PENGU'
import std.spark
import app
weave not_found with x as int into int:
    return x
weave main into int:
    calling spark.println with "{calling app.call}"
    return 0
PENGU
out="$(cd "$tmp" && "$PSC" run src/main.pengu 2>&1)" || { echo "FAIL: nombre importado no resuelve"; echo "$out"; exit 1; }
[ "$out" = "404" ] || { echo "FAIL: imprimió '$out' (esperado 404)"; exit 1; }
echo "OK visible names"
